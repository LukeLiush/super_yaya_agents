from agno.tools.yfinance import YFinanceTools
from prefect import get_run_logger, task
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.durable_exec.prefect import PrefectAgent

from invesetment_agent.infrastructure.models.factory import ConfiguredModelProvider


class GetNewsArgs(BaseModel):
    ticker: str = Field(
        description="The stock ticker symbol (e.g., 'AAPL'). Must be uppercase.", pattern=r"^[A-Z]{1,5}$"
    )
    num_stories: int = Field(
        description=(
            "Number of stories to request. Note: The underlying source (yfinance) is typically capped at 10 items."
        ),
        default=10,
        le=50,  # Example upper bound for safety
    )


class AnalyzedNewsArticle(BaseModel):
    ticker: str = Field(description="The stock ticker symbol for the company.")
    title: str = Field(description="The headline of the article.")
    url: str = Field(description="The URL link to the original article.")
    summary: str = Field(description="A 1-2 sentence distillation of the core facts or event mentioned.")
    sentiment: str = Field(description="Must be strictly one of: 'Bullish', 'Bearish', or 'Neutral'.")


class News(BaseModel):
    ticker: str = Field(description="The stock ticker symbol for the company.")
    articles: list[AnalyzedNewsArticle] = Field(description="A list of news articles related to the ticker.")

    def slack_message(self) -> str:
        # Define a mapping for sentiments to emojis
        sentiment_emojis = {"Bullish": "🚀", "Bearish": "📉", "Neutral": "⚖️"}

        # Header for the ticker
        header = f"*Latest News for {self.ticker}* 📰\n"

        # Format each article line
        lines = []
        for article in self.articles:
            emoji = sentiment_emojis.get(article.sentiment, "📝")
            lines.append(f"{emoji} *[{article.sentiment}]* {article.summary}")

        return header + "\n".join(lines)

    @staticmethod
    def empty(ticker: str) -> "News":
        return News(ticker=ticker, articles=[])


def yfinance_get_company_news(ctx: RunContext[YFinanceTools], get_news_args: GetNewsArgs) -> str:
    """
       Fetches the most recent news articles, press releases, and market updates for a specific stock ticker.

    This tool is intended for gathering raw news data to perform sentiment analysis, identifying
    corporate catalysts, or monitoring significant market events.

    Returns:
        A JSON-formatted string containing a list of news objects. Each object includes
        metadata such as the headline, publication date, source provider, and a link
        to the full article.
    """
    logger = get_run_logger()
    logger.info(f"Fetching news for ticker: {get_news_args.ticker}, requested stories: {get_news_args.num_stories}")

    try:
        result: str = ctx.deps.get_company_news(symbol=get_news_args.ticker, num_stories=get_news_args.num_stories)
        cleaned = " ".join(result.split())

        if not cleaned:
            logger.warning(f"No news content found for ticker: {get_news_args.ticker}")
        else:
            logger.info(f"Successfully retrieved and cleaned news for {get_news_args.ticker}")

        return cleaned
    except Exception as e:
        logger.error(f"Error fetching news for {get_news_args.ticker}: {e!s}")
        raise


async def build_fetch_news_agent() -> PrefectAgent:
    provider = ConfiguredModelProvider(prefer_env_first=True)
    model = provider.get_model("pydantic:gemini-2.5-flash-lite")
    agent = Agent(
        name="Finance Agent",
        model=model,
        output_type=News,
        tools=[yfinance_get_company_news],
        deps_type=YFinanceTools,  # <--- Add this line
        system_prompt=(
            "You are a financial research assistant. Your task is to fetch the latest "
            "news articles related to a given stock ticker and analyze their sentiments."
        ),
    )
    return PrefectAgent(agent)


@task
async def fetch_asset_news(ticker: str) -> News:
    logger = get_run_logger()  # Initialize Prefect logger
    num_stories = 10
    logger.info(f"Starting news fetch and analysis for ticker: {ticker} and num_stories: {num_stories}")

    yfinance_tools = YFinanceTools(
        enable_company_news=False, enable_company_info=False, enable_historical_prices=False, enable_stock_price=True
    )
    prefect_agent: PrefectAgent = await build_fetch_news_agent()
    result = await prefect_agent.run(
        f"Get the latest news articles for the stock ticker [{ticker}] and analyze {num_stories} stories.",
        deps=yfinance_tools,
    )

    if result and result.output:
        logger.info(f"Successfully analyzed {len(result.output.articles)} articles for {ticker}.")
        return result.output

    logger.warning(f"No news articles were found or analyzed for ticker: {ticker}")
    return News.empty(ticker)
