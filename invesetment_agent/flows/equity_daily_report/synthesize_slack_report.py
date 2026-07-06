import datetime
import json
from zoneinfo import ZoneInfo

from agno.tools.slack import SlackTools
from agno.tools.yfinance import YFinanceTools
from fetch_asset_news import AnalyzedNewsArticle, News, fetch_asset_news
from fetch_insider_activities import (
    GetInsiderActivityArg,
    InsiderTradingActivities,
    get_insider_trading_activities_task,
)
from fetch_price_histories import HistoricalPriceReport, fetch_historical_ranges_task
from prefect import get_run_logger, task
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.durable_exec.prefect import PrefectAgent

from invesetment_agent.infrastructure.models.factory import ConfiguredModelProvider


class SlackReportPayload(BaseModel):
    ticker: str = Field(description="The uppercase ticker symbol.")
    channel: str = Field(default="#super-yaya", description="The target Slack channel destination.")

    # Tables are small (5 rows), 1000 chars is plenty and safe
    slack_friendly_price_matrix: str = Field(
        # max_length=1000,
        description=(
            "A beautifully formatted plaintext table optimized for a Slack monospaced "
            "block (wrapped in triple backticks). "
            "Columns must line up perfectly using whitespace padding: Window, High ($), Low ($). "
            "STRICT LIMIT: Must be under 1,000 characters."
        )
    )

    # Insider activities can get long; cap tightly at Slack's absolute block limit
    slack_friendly_insider_text: str = Field(
        # max_length=3000,
        description=(
            "A clean list of recent insider trading activities formatted as bullet points. "
            "STRICT LIMIT: This string must not exceed 3,000 characters to comply with Slack block limits. "
            "If there are too many logs, truncate or summarize the oldest records to stay under the limit."
        )
    )

    # News feeds get long quickly; cap tightly at Slack's absolute block limit
    slack_friendly_news: str = Field(
        # max_length=3000,
        description=(
            "A bulleted list summarizing recent news articles and their sentiment. "
            "Each item must use Slack's native link syntax: • *[SENTIMENT]* <URL|Title> - _Summary_. "
            "STRICT LIMIT: This string must not exceed 3,000 characters to comply with Slack block limits. "
            "Prioritize the most important or recent news items to stay under the limit."
        )
    )


def _build_synthesis_agent() -> PrefectAgent:
    provider = ConfiguredModelProvider(prefer_env_first=True)
    model = provider.get_model("pydantic:gemini-2.5-flash-lite")

    agent = Agent(
        name="Slack Report Synthesis Agent",
        model=model,
        output_type=SlackReportPayload,
        system_prompt=(
            "You are a master financial technical writer and UI presentation specialist. "
            "Your job is to compile raw data blocks into an exceptionally clean, "
            "readable, and professional Slack message layout.\n\n"
            "CRITICAL FORMATTING GUIDELINES:\n"
            "1. STRUCTURE: Combine the information into these explicit sections using bold titles:\n"
            "   - *📈 Financial Report: [Company/Ticker]*\n"
            "   - *Price Performance Matrix:*\n"
            "   - *Insider Trading Summary:*\n"
            "   - *Recent News & Sentiment Analysis:*\n"
            "2. MATRIX LAYOUT: Render the high/low window table inside a code fence block "
            "(wrapped in triple backticks) so the monospaced font aligns columns perfectly.\n"
            "3. INSIDER & NEWS LAYOUT: Present these items as clean bullet points. "
            "For news, ensure you map them using Slack's native link markdown formatting: "
            "• *[SENTIMENT]* <URL|Title> - _Summary_.\n"
            "4. FILLERS: Do not introduce conversational chatter, introductory remarks "
            "('Here is your report...'), or corporate disclaimers. "
            "Provide only the styled markdown contents."
        ),
    )
    return PrefectAgent(agent)


@task
def send_attractive_thread_subject(
    ticker: str, company_info: str, current_price: float, slack_tools: SlackTools, slack_channel: str
) -> str | None:
    logger = get_run_logger()
    # --- 1. Generate an Attractive Thread Subject ---
    zone_info = ZoneInfo("America/Los_Angeles")
    pst_time = datetime.datetime.now(zone_info)
    date_str = pst_time.strftime("%B %d, %Y")

    # Highlighted subject and inclusion of company_info and current_price
    initial_message = (
        f"🚀 *DAILY EQUITY INTELLIGENCE BRIEF* | {date_str}\n"
        f"Targeting: *{company_info}* (`{ticker}`) | Current Price: *${current_price:,.2f}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Greetings! 👋 I'm diving deep into the markets to bring you the latest "
        f"price action, insider moves, and breaking news for *{company_info}*. "
        f"Hang tight while I crunch the numbers! 📈💎🙌"
    )

    # --- 2. Send Initial Message and Get Thread ID ---
    response_json = slack_tools.send_message(channel=slack_channel, text=initial_message)
    response_data = json.loads(response_json)
    if "ts" not in response_data:
        logger.error(f"Failed to start Slack thread: {response_json}")
        return None

    return response_data["ts"]


@task
async def synthesize_slack_report_task(ticker: str, slack_tools: SlackTools, slack_channel: str):
    logger = get_run_logger()
    logger.info("Synthesizing final Slack payload compilation for %s...", ticker)

    yfinance_tools = YFinanceTools(
        enable_company_info=True,
    )
    company_info = json.loads(yfinance_tools.get_company_info(ticker))
    company_name: str = company_info.get("longName", ticker)
    current_stock_price: str = yfinance_tools.get_current_stock_price(ticker)
    current_price: float = float(current_stock_price) if current_stock_price else 0.0

    thread_ts: str = send_attractive_thread_subject(
        ticker=ticker,
        company_info=company_name,
        current_price=current_price,
        slack_tools=slack_tools,
        slack_channel=slack_channel,
    )

    news_future = fetch_asset_news.submit(ticker=ticker)
    insider_future = get_insider_trading_activities_task.submit(GetInsiderActivityArg(ticker=ticker, recent_days=90))
    price_future = fetch_historical_ranges_task.submit(ticker=ticker)

    insider: InsiderTradingActivities = insider_future.result()
    slack_tools.send_message_thread(channel=slack_channel, text=insider.slack_insider_activities, thread_ts=thread_ts)

    news: News = news_future.result()
    slack_tools.send_message_thread(channel=slack_channel, text=news.slack_message(), thread_ts=thread_ts)

    prices: HistoricalPriceReport = price_future.result()
    slack_tools.send_message_thread(channel=slack_channel, text=prices.slack_message(), thread_ts=thread_ts)

    # # 1. Instantiate the single-purpose rendering agent
    # synthesis_agent = _build_synthesis_agent()
    #
    # # 2. Build a clear, structured prompt containing the raw data blocks
    # user_prompt = f"""
    #     You are tasked with transforming raw financial data packets for ticker symbol {ticker} "
    #     "into clean, separate, Slack-ready markdown string blocks.
    #
    #     --- UPSTREAM RAW DATA PANELS ---
    #
    #     [ASSET PROFILE]
    #     Ticker: {prices.ticker}
    #     Company Name: {prices.company_name}
    #     Current Price: {prices.currency} {prices.current_price}
    #
    #     [HISTORICAL PRICING MATRIX DATA]
    #     {json.dumps([w.model_dump() for w in prices.price_matrix], indent=2)}
    #
    #     [INSIDER TRADING ACTIONS RAW LOGS]
    #     {insider.slack_insider_activities}
    #
    #     [RECENT NEWS DATA FEEDS]
    #     {json.dumps([n.model_dump() for n in news], indent=2)}
    #
    #     --------------------------------
    #
    #     EXECUTION INSTRUCTIONS:
    #     1. Parse the [HISTORICAL PRICING MATRIX DATA] array and map it to "
    #     "`slack_friendly_price_matrix`. Render it as a beautifully padded monospaced "
    #     "plaintext table wrapped in triple backticks.
    #     2. Clean and distill the [INSIDER TRADING ACTIONS RAW LOGS] block into a concise "
    #     "bulleted narrative for `slack_friendly_insider_text`. If the raw log indicates "
    #     "no records or empty sets, use a clean fallback bullet.
    #     3. Iterate through the items inside [RECENT NEWS DATA FEEDS] to populate "
    #     "`slack_friendly_news`. Synthesize the summary into 1-2 tight sentences and "
    #     "format the links exactly using Slack's '<URL|Title>' syntax.
    #     4. Continuously monitor your character budget! Ensure `slack_friendly_insider_text` "
    #     "and `slack_friendly_news` strictly adhere to their respective character caps by "
    #     "truncating older or lower-priority line items if needed.
    #     5. Convert the news feed items into `slack_friendly_news` using the '<URL|Title>' format.
    #        BUDGET CONSTRAINT: You are explicitly forbidden from outputting more than 5 news bullets.
    #        Pick the top 5 highest-impact articles and discard everything else to guarantee "
    #        "you stay well under the 3,000 character limit.
    #     """
    #
    # logger.debug("Executing synthesis transformation run loop...")
    # result = await synthesis_agent.run(user_prompt=user_prompt)
    # logger.info("Slack visual mapping completed successfully for ticker %s.", ticker)
