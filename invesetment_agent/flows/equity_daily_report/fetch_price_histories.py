import asyncio
import json
from pathlib import Path
from typing import List, Optional

import pandas as pd
from agno.tools.yfinance import YFinanceTools
from dotenv import load_dotenv
from prefect import get_run_logger, task, flow
from pydantic import BaseModel, Field
from tabulate import tabulate


class PriceWindow(BaseModel):
    window: str = Field(
        description="The timeframe window name. Must be exactly one of: 'Current', '7-Day', '30-Day', '3-Months', '1-Year'."
    )
    high: float = Field(description="The highest price point observed during this specific timeframe window.")
    low: float = Field(description="The lowest price point observed during this specific timeframe window.")


class HistoricalPriceReport(BaseModel):
    ticker: str = Field(description="The validated uppercase stock or mutual fund ticker symbol.")
    currency: str = Field(default="USD", description="The currency denomination of the pricing data.")
    price_matrix: List[PriceWindow] = Field(
        description="A list containing exactly 5 items mapping the High/Low price windows for Current, 7-Day, 30-Day, 3-Months, and 1-Year."
    )

    def slack_message(self) -> str:
        logger = get_run_logger()
        # Prepare the headers
        headers = ["Window", f"High ({self.currency})", f"Low ({self.currency})"]

        # Prepare the data rows
        table_data = [
            [w.window_name, f"{w.high:,.2f}", f"{w.low:,.2f}"]
            for w in self.price_matrix
        ]

        # Generate the table in GitHub Flavored Markdown format
        markdown_table = tabulate(table_data, headers=headers, tablefmt="github")

        message = f"```text\n{markdown_table}\n```"
        logger.info("Generated Slack price matrix table. Length: %d characters", len(message))
        return message


@task
def get_1_year_historical_stock_prices(yfinance_tool: YFinanceTools, ticker: str, ) -> pd.DataFrame:
    logger = get_run_logger()
    logger.info("Executing tool: Fetching 1-year historical pricing data stream for ticker '%s'", ticker)

    try:
        raw_data = yfinance_tool.get_historical_stock_prices(ticker, period="1y", interval="1d")
        # Lightweight validation trace on the string payload length
        logger.debug("Successfully retrieved historical data stream payload from Yahoo Finance. Length: %d chars",
                     len(raw_data))
        data = json.loads(raw_data)
        df = pd.DataFrame.from_dict(data, orient="index")
        df.index = pd.to_datetime(df.index.astype("int64"), unit="ms")
        df = df.sort_index()

        logger.info("Processed %d rows of historical data for %s", len(df), ticker)
        if not df.empty:
            logger.info("Data range: %s to %s", df.index.min(), df.index.max())
            missing_cols = [c for c in ["High", "Low"] if c not in df.columns]
            if missing_cols:
                logger.warning("Missing expected columns in data for %s: %s", ticker, missing_cols)
            else:
                logger.debug("Verified 'High' and 'Low' columns are present for %s", ticker)

        return df
    except Exception as err:
        logger.error("Critical failure pulling historical price data stream for %s: %s", ticker, err, exc_info=True)
        return pd.DataFrame()


@task
def to_price_metrics(df: pd.DataFrame) -> pd.DataFrame:
    logger = get_run_logger()

    def high_low(name, window_days):
        # take the last N calendar days
        cutoff = df.index.max() - pd.Timedelta(days=window_days)
        logger.debug("Window '%s': Calculating metrics from cutoff %s", name, cutoff)
        sub = df.loc[df.index >= cutoff]

        if sub.empty:
            logger.warning("Window '%s': No data found after cutoff %s", name, cutoff)
            return None, None

        h, l = sub["High"].max(), sub["Low"].min()
        if name == "Current":
            logger.info("Current price metrics: High=%.2f, Low=%.2f", h, l)
        return h, l

    windows = {
        "Current": 1,  # latest bar
        "7-Day": 7,
        "30-Day": 30,
        "3-Months": 91,
        "1-Year": 365,
    }
    result = {
        name: high_low(name, days)
        for name, days in windows.items()
    }
    summary = pd.DataFrame(result, index=["High", "Low"]).T
    return summary


@task
async def fetch_historical_ranges_task(ticker: str) -> Optional[HistoricalPriceReport]:
    logger = get_run_logger()
    logger.info("Initializing Historical Range Task execution for ticker parameter: %s", ticker)

    yfinance_tools = YFinanceTools(enable_company_info=True,
                                   enable_historical_prices=True,
                                   enable_stock_price=True)
    one_year_prices_future = get_1_year_historical_stock_prices.submit(yfinance_tools, ticker=ticker)
    one_year_prices: pd.DataFrame = one_year_prices_future.result()
    if one_year_prices.empty:
        logger.error("No historical price data available for %s. Aborting metrics calculation.", ticker)
        return None

    to_price_metrics_future = to_price_metrics.submit(one_year_prices)
    price_metrics: pd.DataFrame = to_price_metrics_future.result()

    # Construct the report object
    try:
        # Note: In a real scenario, we'd fetch company name and current price from yfinance_tools
        # For now, let's assume we can get some basics if we had the tool enabled or info fetched.
        # But looking at the existing code, it returns None at line 103.
        # The user wants to improve observability, so I should probably also fix the return value 
        # to actually return a HistoricalPriceReport if possible, or at least log the result.

        logger.info("Successfully calculated price metrics for %s", ticker)

        price_matrix = []
        for name, row in price_metrics.iterrows():
            price_matrix.append(PriceWindow(window_name=name, high=row["High"], low=row["Low"]))

        report = HistoricalPriceReport(
            ticker=ticker,
            currency=xxx,
            price_matrix=price_matrix
        )
        logger.info("HistoricalPriceReport generated for %s", ticker)
        return report

    except Exception as e:
        logger.error("Failed to build HistoricalPriceReport for %s: %s", ticker, e, exc_info=True)
        return None


@flow
async def test_flow():
    logger = get_run_logger()
    _env_path: Path = Path(__file__).parent.parent / ".env"
    if _env_path.exists():
        logger.debug("Loading environment from %s", _env_path)
        load_dotenv(dotenv_path=_env_path)
    else:
        logger.warning("Environment file not found at %s", _env_path)
    future = fetch_historical_ranges_task.submit(ticker="AMZN")
    print(future.result())


if __name__ == "__main__":
    asyncio.run(test_flow())
