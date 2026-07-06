import asyncio
import datetime as dt
import os
from pathlib import Path

import inngest
from agno.agent import Agent
from agno.models.dashscope import DashScope
from dotenv import load_dotenv
from edgar import set_identity
from inngest import PydanticSerializer
from lagom import Container

from finance_report.reporting_core.domain.shared_values import Ticker
from finance_report.reporting_core.infrastructure.adapters.edgar_insider_adapter import EdgarInsiderAdapter

container = Container()
_is_production = os.getenv("INNGEST_IS_PRODUCTION", "false").lower() == "true"
_inngest_client = inngest.Inngest(
    app_id="finance-report-app", is_production=_is_production, serializer=PydanticSerializer()
)

env_path: Path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    raise ValueError("DASHSCOPE_API_KEY not set in environment. Please set it (e.g., in .env).")

#
# async def main_pydantic_ai():
#     from pydantic_ai import Agent
#     from pydantic_ai.models.openai import OpenAIChatModel
#     from pydantic_ai.providers.alibaba import AlibabaProvider
#     model = OpenAIChatModel(
#         'qwen-max',
#         provider=AlibabaProvider(api_key='your-api-key'),
#     )
#     agent = Agent(model)


async def main():
    # Load the API key from environment variables
    ali_api_key = os.getenv("DASHSCOPE_API_KEY")

    # Initialize the Agno Agent with Qwen Plus (DashScope)
    agent = Agent(
        model=DashScope(
            id="qwen3.7-plus",
            api_key=ali_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            # base_url="https://dashscope.aliyuncs.com/api/v1"
        ),
        markdown=True,
    )

    # Example usage:
    agent.print_response("Hello, what is capital of France?")


async def main1():
    adapter = EdgarInsiderAdapter()

    today = dt.datetime.today()
    start_date = (today - dt.timedelta(days=90)).date()
    end_date = dt.datetime.today().date()

    insiders, provenance = adapter.fetch_transactions(Ticker(symbol="TSLA"), start_date, end_date)
    print(len(insiders))
    print(provenance)


if __name__ == "__main__":
    print("ya2")
    set_identity("user@exampe.com")
    asyncio.run(main())
