import asyncio
import logging
import os
from pathlib import Path
from typing import Any, cast

from agno.tools.slack import SlackTools
from dotenv import load_dotenv
from edgar import set_identity
from prefect import flow, get_run_logger

from invesetment_agent.flows.equity_daily_report.synthesize_slack_report import (
    SlackReportPayload,
    synthesize_slack_report_task,
)


def init(logger: logging.Logger):
    _env_path: Path = Path(__file__).parent.parent / ".env"
    if _env_path.exists():
        logger.debug("Loading environment from %s", _env_path)
        load_dotenv(dotenv_path=_env_path)
    else:
        logger.warning("Environment file not found at %s", _env_path)

    set_identity("user@exampe.com")


@flow
async def build_flow(tickers: list[str]):
    logger = cast(Any, get_run_logger())
    init(logger)
    logger.info("Starting build_flow with tickers: %s", tickers)
    slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")
    if slack_bot_token is None:
        raise ValueError("SLACK_BOT_TOKEN not set in environment")
    slack_tools = SlackTools(token=slack_bot_token)

    futures = [
        synthesize_slack_report_task.submit(ticker=ticker, slack_tools=slack_tools, slack_channel="#super-yaya")
        for ticker in tickers
    ]
    for future in futures:
        # In Prefect, .result() on a future in an async flow returns the result directly.
        res = future.result()
        if asyncio.iscoroutine(res):
            await res


if __name__ == "__main__":
    asyncio.run(
        build_flow(
            tickers=[
                # "TSLA",
                "AMZN"
            ]
        )
    )
