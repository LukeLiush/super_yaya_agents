import asyncio
import datetime
from datetime import date
from pathlib import Path
from typing import Any, cast

import pandas as pd
from dotenv import load_dotenv
from edgar import Company, set_identity
from edgar.entity import EntityFilings
from edgar.ownership import Form4
from prefect import flow, get_run_logger, task
from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent
from pydantic_ai.durable_exec.prefect import PrefectAgent

from invesetment_agent.infrastructure.models.factory import ConfiguredModelProvider


class GetInsiderActivityArg(BaseModel):
    ticker: str = Field(
        description="The stock ticker symbol (e.g., 'AAPL'). Must be uppercase.", pattern=r"^[A-Z]{1,5}$"
    )
    recent_days: int = Field(
        description="Number of days to look back for insider trading activities.", default=90, ge=1, le=365
    )


class InsiderTransaction(BaseModel):
    transaction_type: str = Field(
        alias="Transaction Type",
        description="The nature of the transaction. Common values include 'Acquisition' (Buy) or 'Disposition' (Sell).",
    )
    code: str = Field(
        alias="Code",
        description=(
            "SEC transaction code (e.g., 'P' for open market purchase, "
            "'S' for open market sale, 'M' for exercise of derivatives, 'G' for gift)."
        ),
    )
    description: str = Field(
        alias="Description",
        description=(
            "A human-readable explanation of the transaction code "
            "(e.g., 'Open Market Sale' or 'Grant, award or other acquisition')."
        ),
    )
    shares: float = Field(alias="Shares", description="The number of shares involved in the specific transaction.")
    price: float | None = Field(
        alias="Price",
        description="The price per share at which the transaction was executed. May be 0.0 for grants or gifts.",
    )
    value: float | None = Field(alias="Value", description="Total monetary value of the transaction (Shares * Price).")
    transaction_date: date = Field(alias="Date", description="The date the transaction took place.")
    form: str = Field(alias="Form", description="The SEC form type, typically 'Form 4' for changes in ownership.")
    issuer: str = Field(
        alias="Issuer", description="The full legal name of the company issuing the stock (e.g., 'Tesla, Inc.')."
    )
    insider: str = Field(
        alias="Insider", description="The name of the individual or entity performing the trade (e.g., 'Elon Musk')."
    )
    position: str = Field(
        alias="Position",
        description=(
            "The job title or relationship of the insider to the company "
            "(e.g., 'Chief Executive Officer', 'Director', or '10% Owner')."
        ),
    )
    remaining_shares: float = Field(
        alias="Remaining Shares",
        description="The total number of shares owned by the insider after this transaction was completed.",
    )

    model_config = ConfigDict(populate_by_name=True)


class InsiderTradingActivities(BaseModel):
    ticker: str = Field(description="The validated uppercase stock ticker symbol.")
    transactions: list[InsiderTransaction] = Field(
        description="A list of detailed insider transaction records derived from Form 4 filings."
    )
    slack_insider_activities: str

    @staticmethod
    def empty(ticker: str) -> "InsiderTradingActivities":
        return InsiderTradingActivities(
            ticker=ticker,
            transactions=[],
            slack_insider_activities="• _No recent Form 4 insider trading actions filed within this lookback window._",
        )


def get_insider_trading_activities(get_insider_activity_arg: GetInsiderActivityArg) -> str:
    """
    Retrieves recent SEC Form 4 insider trading filing records for a given corporate stock ticker.

    Args:
        get_insider_activity_arg: An object containing the 'ticker' and 'recent_days'.

    Returns:
        A JSON-formatted string containing a list of insider transaction records. Each record includes
        details such as transaction type, code, description, shares, price, value, date, form type, issuer,
        insider name, position, and remaining shares owned. If no filings are found
    """
    # Grab the logger within the tool execution context
    logger = get_run_logger()
    logger.info("Executing SEC Form 4 tool lookup for ticker: %s", get_insider_activity_arg.ticker)
    empty_result = "• _No recent Form 4 insider trading actions filed within this lookback window._"
    try:
        company = Company(get_insider_activity_arg.ticker)

        today = datetime.datetime.today()
        # Pull the widest window once (90 days) and bucket in memory
        start = (today - datetime.timedelta(days=get_insider_activity_arg.recent_days)).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")

        filings: EntityFilings = company.get_filings(form="4", filing_date=(start, end))
        if not filings:
            logger.warning(
                "No Form 4 filings discovered for %s in the specified timeframe", get_insider_activity_arg.ticker
            )
            return empty_result

        logger.info("Discovered %d raw filings. Parsing dataframes...", len(filings))

        dataframes = []
        for filing in filings:
            f4: Form4 = filing.obj()
            df = f4.to_dataframe()
            dataframes.append(df)

        if not dataframes:
            return ""

            # Concatenate all filings
        combined_df = pd.concat(dataframes, ignore_index=True)
        sanitized_df = combined_df.replace({pd.NA: None, float("nan"): None})

        return str(sanitized_df.to_json(orient="records", date_format="iso"))
    except Exception as e:
        logger.error(
            "Critical failure pulling SEC records for %s: %s", get_insider_activity_arg.ticker, e, exc_info=True
        )
        return empty_result


def _build_agent() -> PrefectAgent:
    provider = ConfiguredModelProvider(prefer_env_first=True)
    # model = provider.get_model("pydantic:gemini-1.5-flash")
    model = provider.get_model("pydantic:gemini-2.5-flash-lite")
    agent = Agent(
        name="Finance Agent",
        model=model,
        output_type=InsiderTradingActivities,
        tools=[get_insider_trading_activities],
        system_prompt=(
            "You are an expert senior financial analyst specializing in corporate governance "
            "and SEC data analysis.\n\n"
            "CRITICAL OPERATING PROCEDURES:\n"
            "1. DATA COLLECTION: Use the 'get_insider_trading_activities' tool immediately. "
            "Extract numerical metrics exactly as returned by the tool.\n"
            "2. DATA PROCESSING & STANDARDIZATION:\n"
            "   - Standardize titles: Use 'CEO' instead of 'Chief Executive Officer', "
            "'CFO' for 'Chief Financial Officer', etc.\n"
            "   - Priority: If multiple titles exist (e.g., 'Director, CEO'), use the most senior one ('CEO').\n"
            "3. SLACK SUMMARY GENERATION (`slack_insider_activities`):\n"
            "   - Trade Signals: 🟢 for Open Market Purchases (Code P), 🔴 for Open Market Sales (Code S).\n"
            "   - Roles: 👔 for C-Suite (CEO/CFO/COO), 👥 for Directors, 🏦 for 10% Owners.\n"
            "   - Format: • [Role Emoji] *[Name]* ([Title]): [Signal Emoji] [Type] [Shares] shares "
            "at $[Price] on [Date].\n"
            "   - No Data: If the tool returns '[]', set this field to: "
            "'• _No recent Form 4 insider trading actions filed within this lookback window._'\n\n"
            "4. STRUCTURED DATA: Ensure the 'transactions' list is populated with all valid records found."
        ),
    )
    return PrefectAgent(agent)


@task
async def get_insider_trading_activities_task(
    get_insider_activity_arg: GetInsiderActivityArg,
) -> InsiderTradingActivities:
    logger = get_run_logger()
    preferred_agent: PrefectAgent = _build_agent()
    user_prompt = (
        f"Extract and summarize all SEC Form 4 insider transaction history for ticker: "
        f"{get_insider_activity_arg.ticker}. "
        f"Focus on filings from the last {get_insider_activity_arg.recent_days} days. "
        "Populate the 'transactions' list and generate the 'slack_insider_activities' "
        "summary based on the results."
    )
    logger.debug("Executing agent run loop...")
    result = await preferred_agent.run(user_prompt=user_prompt)
    logger.info("Agent execution completed successfully for %s", get_insider_activity_arg.ticker)
    return cast(InsiderTradingActivities, result.output)


@flow
async def test_flow() -> None:
    logger = get_run_logger()
    _env_path: Path = Path(__file__).parent.parent / ".env"
    if _env_path.exists():
        logger.debug("Loading environment from %s", _env_path)
        load_dotenv(dotenv_path=_env_path)
    else:
        logger.warning("Environment file not found at %s", _env_path)
    args = GetInsiderActivityArg(ticker="AAPL", recent_days=90)
    logger.info("Submitting insider trading pipeline job parameter values: %s", args.model_dump())

    future = get_insider_trading_activities_task.submit(args)
    result: InsiderTradingActivities = await future.result()

    logger.info(
        "Job pipeline completed. Final Slack text generation payload len: %d",
        len(result.slack_insider_activities),
    )
    print("\n--- FINAL OUTPUT OBJECT RESULT ---")
    print(f"Ticker: {result.ticker}")
    print(result.slack_insider_activities)


if __name__ == "__main__":
    from typing import Any, cast

    set_identity("user@exampe.com")
    asyncio.run(cast(Any, test_flow)())
