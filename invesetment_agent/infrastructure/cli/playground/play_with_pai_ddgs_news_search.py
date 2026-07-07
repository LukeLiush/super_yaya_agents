# pip install "pydantic-ai[prefect,google]"
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent, AgentRunResult
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool
from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)


def create_model() -> Model:
    env_path: Path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

    # Setup database for storage
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        raise RuntimeError("GOOGLE_API_KEY not set in environment. Please set it (e.g., in .env).")

    return GoogleModel(
        model_name="gemini-2.5-flash-lite",
        # model_name="gemini-3.1-pro-preview",
        provider=GoogleProvider(api_key=google_api_key),
    )


def create_websearch_agent(
    model: Model,
) -> Agent:
    return Agent(
        name="Web Research Agent",
        model=model,
        tools=[duckduckgo_search_tool()],
        system_prompt=(
            "You are a helpful research assistant. "
            "Use the duckduckgo_search tool to find information when asked. "
            "If the user asks for a specific timeframe, try to include that in your search query."
        ),
    )


def main() -> None:
    # agent_os.serve(app="finance_agent_team:app", reload=True,)
    web_query = "Search DuckDuckGo for TSLA stock news from the last 3 months."
    model: Model = create_model()
    search_agent = create_websearch_agent(model)
    print(f"Running query: {web_query}")
    result: AgentRunResult = search_agent.run_sync(web_query)
    print(f"Result: {result.output}")


async def call_search_news() -> None:
    ddg = duckduckgo_search_tool()
    results = await ddg.function("TSLA stock news in the last 3 months")
    print(results)


if __name__ == "__main__":
    import asyncio

    # print("--- Running main() (Agent Flow) ---")
    # main()
    print("\n--- Running call_search_news() (Direct Tool Call) ---")
    asyncio.run(call_search_news())
