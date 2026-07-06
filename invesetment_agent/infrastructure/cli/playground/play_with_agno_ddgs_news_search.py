import json
import logging
import os
from pathlib import Path
from typing import Literal

from agno.agent import Agent
from agno.models.base import Model
from agno.models.google import Gemini
from agno.tools import tool
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.websearch import WebSearchTools
from ddgs.exceptions import DDGSException
from dotenv import load_dotenv
from tenacity import (
    Retrying,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)
_BACKENDS: list[str] = [
    "auto",
    # "brave",
    # "duckduckgo",
    # "google",
    # "grokipedia",
    # "mojeek",
    # "wikipedia",
    "yahoo",
    "yandex",
    "auto",
]
TimeRange = Literal["day", "week", "month", "year"]

_TIMELIMIT_MAP: dict[str, str] = {
    "day": "d",
    "week": "w",
    "month": "m",
    "year": "y",
}


class EmptyNewsResults(Exception):
    """Raised when the news search returns no items, to trigger a retry."""


def _to_timelimit(time_range: TimeRange) -> str:
    try:
        return _TIMELIMIT_MAP[time_range]
    except KeyError as err:
        raise ValueError(f"invalid time_range: {time_range!r} (use day/week/month/year)") from err


def _build_ddg(
    timelimit: str,
    backend: str,
) -> WebSearchTools:
    # timelimit/backend are fixed at construction time, so build per-call to vary them.
    return WebSearchTools(
        enable_news=True,
        enable_search=False,
        timelimit=timelimit,
        region="us-en",
        backend=backend,
    )


def _do_search(query: str, max_results: int, timelimit: str):
    for backend in _BACKENDS:
        logger.info(
            "news search using backend=%r",
            backend,
        )
        ddg: WebSearchTools = _build_ddg(timelimit, backend)
        raw = ddg.web_search(query, max_results=max_results)
        items = json.loads(raw) if isinstance(raw, str) else raw
        if items:
            return items
    raise EmptyNewsResults(query)


def _search_news_with_retry(query: str, max_results: int, max_attempts: int, timelimit: str):
    retryer = Retrying(
        retry=retry_if_exception_type((DDGSException, EmptyNewsResults)),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=2, max=20),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    return retryer(_do_search, query, max_results, timelimit)


@tool(description="Search recent news for any query using DuckDuckGo, with retry on empty/failed results.")
def search_news_with_ddg(
    query: str,
    max_results: int = 50,
    max_attempts: int = 10,
    time_range: TimeRange = "month",
) -> str:
    """
    Args:
        query: The search query.
        max_results: Maximum number of news articles to return.
        max_attempts: How many times to retry on throttling or empty results.
        time_range: How far back to search: "day", "week", "month", or "year".
    """
    timelimit = _to_timelimit(time_range)
    try:
        items = _search_news_with_retry(query, max_results, max_attempts, timelimit)
    except (DDGSException, EmptyNewsResults) as e:
        return json.dumps({"query": query, "error": str(e), "results": []})

    return json.dumps(
        {
            "query": query,
            "time_range": f"{time_range} (timelimit={timelimit})",
            "count": len(items),
            "results": items,
        },
        indent=2,
    )


def create_model() -> Model:
    env_path: Path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

    # Setup database for storage
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        raise RuntimeError("GOOGLE_API_KEY not set in environment. Please set it (e.g., in .env).")

    return Gemini(
        id="gemini-2.5-flash-lite",
        # id="gemini-3.1-pro-preview",
        api_key=google_api_key,
    )


def create_websearch_agent(
    model: Model,
) -> Agent:
    return Agent(
        name="Web Research Agent",
        # When an agent is a member of a Team, the team leader uses each member's role
        # to decide which member to delegate a task to. So role is essentially a short label,
        # describing what this agent is for, written so the leader can route work to it.
        # It's meant to be a concise capability descriptor, not a full persona or behavioral instruction.
        # For a standalone agent that isn't in a team, role has little to no effect on behavior.
        role="Get Company stock news and sentiments",
        model=model,
        tools=[search_news_with_ddg],
        instructions=[
            "You are a stock news research assistant.",
            "When given a ticker and a time window, use DuckDuckGo to search for recent news about that stock.",
            "Search for news, then summarize the overall sentiment.",
            "For EACH news item, report: the headline, the source, the publication date, "
            "and a sentiment label (positive, negative, or neutral) with a brief rationale.",
            "Sort results by relevance.",
            "Present the results as a table.",
        ],
        markdown=True,
    )


def main():
    # agent_os.serve(app="finance_agent_team:app", reload=True,)
    web_query = """
        for TSLA stock, can you conduct web search to tell the all of the news within recent 3 months, 
        sorted by relevance, 
        and summarize the sentiment of the news? Please also include the source and date of each news.
        """
    model: Model = create_model()
    search_agent = create_websearch_agent(model)
    search_agent.print_response(
        web_query,
        stream=False,
    )


def call_search_news():
    result: str = search_news_with_ddg.entrypoint(
        "tesla stock news",
        max_results=100,
        max_attempts=10,
        time_range="month",
    )
    print(result)


if __name__ == "__main__":
    # main()
    call_search_news()
