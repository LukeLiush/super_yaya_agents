import asyncio
import datetime
import os
from pathlib import Path

import pandas as pd
from agno.tools.slack import SlackTools
from agno.tools.yfinance import YFinanceTools
from dotenv import load_dotenv
from edgar import Company, set_identity
from edgar.entity import EntityFilings
from edgar.ownership import Form4
from prefect import flow, get_run_logger
from pydantic import BaseModel, Field
from pydantic_ai import Agent, FunctionToolset, RunContext
from pydantic_ai.durable_exec.prefect import PrefectAgent

from invesetment_agent.infrastructure.models.factory import ConfiguredModelProvider


class PriceWindow(BaseModel):
    window_name: str = Field(description="The timeframe name, e.g., 'Current', '7-Day', '30-Day', '3-Months', '1-Year'")
    high: float = Field(description="The highest price observed during this window period.")
    low: float = Field(description="The lowest price observed during this window period.")


# 1. Define structured data for individual parsed news items
class AnalyzedNewsArticle(BaseModel):
    title: str = Field(description="The headline of the article.")
    url: str = Field(description="The URL link to the original article.")
    summary: str = Field(description="A 1-2 sentence distillation of the core facts or event mentioned.")
    sentiment: str = Field(description="Must be strictly one of: 'Bullish', 'Bearish', or 'Neutral'.")


class FinancialReport(BaseModel):
    ticker: str
    company_name: str
    current_price: float
    currency: str = "USD"
    price_matrix: list[PriceWindow] = Field(
        description="List containing the high/low matrix for all requested windows."
    )

    # Clean structured data if you ever need to save to a database downstream
    news_analysis: list[AnalyzedNewsArticle] = Field(
        description="List of the extracted news articles with summaries and sentiments."
    )

    # --- SLACK OPTIMIZED LAYOUT STRINGS ---
    slack_monospaced_table: str = Field(
        description=(
            "A beautifully formatted plaintext table optimized for a Slack monospaced block "
            "(wrapped in triple backticks). "
            "Columns must be padded to line up exactly: Window, High ($), Low ($)."
        )
    )

    slack_news_feed: str = Field(
        description=(
            "A Slack-friendly block string containing the news feed. "
            "Format each article exactly as a clean bullet point: "
            "• *[SENTIMENT]* <URL|Title> - _Summary text here_"
        )
    )

    # ADDED THIS FIELD
    slack_insider_activities: str = Field(
        description=(
            "A summary of recent insider trading activities. Format as a clean list or table for Slack. "
            "Include key transactions (Buy/Sell), the person involved, and the date."
        )
    )


def get_1_year_historical_stock_prices(
    ctx: RunContext[YFinanceTools],
    ticker: str,
) -> str:
    """
    Fetch the last 1 year of historical daily stock prices for a given ticker.
    Returns a JSON string of historical OHLC data.
    """
    return ctx.deps.get_historical_stock_prices(ticker, period="1y", interval="1d")


def get_insider_trading_activities(ticker: str, recent_days: int = 90) -> str:
    """
    Retrieves recent insider trading activities (SEC Form 4 filings) for a specific stock ticker
    within a look-back window.

    This tool helps identify buying and selling patterns by company executives and directors (insiders),
    which can provide insights into internal sentiment and potential future stock performance.
    """
    company = Company(ticker)

    today = datetime.datetime.today()
    # Pull the widest window once (90 days) and bucket in memory
    start = (today - datetime.timedelta(days=recent_days)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")

    filings: EntityFilings = company.get_filings(form="4", filing_date=(start, end))
    dataframes = []
    for filing in filings:
        f4: Form4 = filing.obj()
        df = f4.to_dataframe()
        dataframes.append(df)

    if not dataframes:
        return "[]"  # Return empty JSON array string

        # Concatenate all filings
    combined_df = pd.concat(dataframes, ignore_index=True)

    # CONVERSION STEP: Convert DataFrame to JSON string for Pydantic compatibility
    return combined_df.to_json(orient="records", date_format="iso")


def _build_agent(yfinance_tools: YFinanceTools) -> PrefectAgent:
    provider = ConfiguredModelProvider(prefer_env_first=True)
    model = provider.get_model("pydantic:gemini-2.5-flash-lite")
    yfinance_toolset = FunctionToolset(
        tools=[
            yfinance_tools.get_company_info,
            get_1_year_historical_stock_prices,
            yfinance_tools.get_current_stock_price,
            yfinance_tools.get_company_news,
        ]
    )
    edgar_toolset = FunctionToolset(tools=[get_insider_trading_activities])
    agent = Agent(
        name="Finance Agent",
        model=model,
        output_type=FinancialReport,
        toolsets=[yfinance_toolset, edgar_toolset],
        deps_type=YFinanceTools,  # <--- Add this line
        system_prompt=(
            "You are an expert financial data retrieval and analysis assistant. "
            "Your sole responsibility is to extract, verify, summarize, and return data "
            "conforming strictly to the requested schema.\n\n"
            "CRITICAL EXECUTION RULES:\n"
            "1. TOOL USAGE: Utilize the provided yfinance and EDGAR tools to fetch all requested data. "
            "Use the insider trading tool to identify significant moves by company executives.\n"
            "2. DATA INTEGRITY: Report all numerical values exactly as returned by the tools.\n"
            "3. NEWS SUMMARIZATION & SENTIMENT: For each news item found, summarize core facts. "
            "Determine market sentiment: 'Bullish', 'Bearish', or 'Neutral'.\n"
            "4. INSIDER ACTIVITIES: Summarize the most relevant Form 4 filings. "
            "Highlight significant buys or sells by high-ranking officers (CEO, CFO, etc.).\n"
            "5. SLACK BLOCKS TEMPLATE FORMATTING:\n"
            "   - 'slack_monospaced_table' must be wrapped in triple backticks, "
            "keeping columns padded cleanly.\n"
            "   - 'slack_news_feed' must use the bullet format: "
            "• *[Sentiment]* <URL|Headline Title> - _Summary_\n"
            "   - 'slack_insider_activities' should be a concise summary of the last 12 months "
            "of insider trades."
        ),
    )
    return PrefectAgent(agent)


@flow
async def test_flow():
    logger = get_run_logger()
    set_identity("your.email@example.com")
    _env_path: Path = Path(__file__).parent.parent / ".env"
    if _env_path.exists():
        logger.debug("Loading environment from %s", _env_path)
        load_dotenv(dotenv_path=_env_path)
    else:
        logger.warning("Environment file not found at %s", _env_path)
    # test = equity_price_research_task.submit("VTSAX")
    # ticker = "VTSAX"
    ticker = "TSLA"
    number_of_recent_news = 10
    report_period = "30 days"

    yfinance_tools = YFinanceTools(
        enable_company_news=True, enable_company_info=True, enable_historical_prices=True, enable_stock_price=True
    )
    agent = _build_agent(yfinance_tools)
    user_prompt: str = f"""
            Analyze the asset ticker: {ticker} .

        Using the historical stock prices tool, calculate the High and Low prices for:
        - Current, 7-Day, 30-Day, 3-Months, and 1-Year windows.
    
        Also extract:
        1. Company info.
        2. The {number_of_recent_news} most recent news articles with sentiment analysis "
        f"focusing on the last {report_period}.
        3. Insider trading activities (SEC Form 4) for the last {report_period}. 
       (Set 'recent_days' accordingly in the tool call).
            """

    result = await agent.run(user_prompt=user_prompt, deps=yfinance_tools)
    report: FinancialReport = result.output

    print("--- SLACK READY COMPOSITE OUTPUT ---")
    print(f"*📈 Financial Report: {report.company_name} ({report.ticker})*")
    print(f"Current Price: `{report.current_price} {report.currency}`\n")
    print("*Price Performance Matrix:*")
    print(report.slack_monospaced_table)
    print("\n*Recent News & Sentiment Analysis:*")
    print(report.slack_news_feed)

    slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")
    if slack_bot_token is None:
        raise ValueError("SLACK_BOT_TOKEN not set in environment")
    slack_tools = SlackTools(token=slack_bot_token)
    slack_tools.send_message(
        channel="#super-yaya",
        text=(
            f"*📈 Financial Report: {report.company_name} ({report.ticker})*\n"
            f"Current Price: `{report.current_price} {report.currency}`\n\n"
            "*Price Performance Matrix:*\n"
            f"{report.slack_monospaced_table}\n\n"
            "*Insider Activities :*\n"
            f"{report.slack_insider_activities}\n\n"
            "*Recent News & Sentiment Analysis:*\n"
            f"{report.slack_news_feed}"
        ),
    )


if __name__ == "__main__":
    asyncio.run(test_flow())
