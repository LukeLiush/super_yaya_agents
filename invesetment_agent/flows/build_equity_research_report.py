import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Literal, cast

from agno.tools.websearch import WebSearchTools
from ddgs.exceptions import DDGSException
from dotenv import load_dotenv
from prefect import flow, get_run_logger, task
from prefect.artifacts import create_table_artifact
from prefect.cache_policies import DEFAULT, INPUTS
from pydantic import BaseModel, Field
from pydantic_ai import Agent, Tool
from pydantic_ai.durable_exec.prefect import PrefectAgent, TaskConfig
from tenacity import Retrying, before_sleep_log, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

env_path: Path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

google_api_key = os.environ.get("GOOGLE_API_KEY")
if not google_api_key:
    raise RuntimeError("GOOGLE_API_KEY not set in environment. Please set it (e.g., in .env).")


class MetadataTextSearchResult(BaseModel):
    """Structured, validated output."""

    title: str
    body: str
    url: str


TimeRange = Literal["day", "week", "month", "year"]
_TIMELIMIT_MAP: dict[str, str] = {
    "day": "d",
    "week": "w",
    "month": "m",
    "year": "y",
}
_BACKENDS: list[str] = [
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


class EmptyNewsResults(Exception):
    """Raised when the news search returns no items, to trigger a retry."""


def _to_timelimit(time_range: TimeRange) -> Literal["d", "w", "m", "y"]:
    _map: dict[str, Literal["d", "w", "m", "y"]] = {
        "day": "d",
        "week": "w",
        "month": "m",
        "year": "y",
    }
    try:
        return _map[time_range]
    except KeyError as err:
        raise ValueError(f"invalid time_range: {time_range!r} (use day/week/month/year)") from err


def _build_ddg(timelimit: str, backend: str) -> WebSearchTools:
    # timelimit/backend are fixed at construction time, so build per-call to vary them.
    return WebSearchTools(
        enable_news=True,
        enable_search=False,
        timelimit=cast(Any, timelimit),
        region="us-en",
        backend=backend,
    )


def _do_search(query: str, max_results: int, timelimit: str, backend: str):
    logger = get_run_logger()
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


def _search_news_with_retry(query: str, max_results: int, max_attempts: int, timelimit: str, backend: str):
    logger = cast(Any, get_run_logger())
    retryer = Retrying(
        retry=retry_if_exception_type((DDGSException, EmptyNewsResults)),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=2, max=20),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    return retryer(_do_search, query, max_results, timelimit, backend)


def web_search_with_ddg(
    query: str,
    max_results: int = 50,
    max_attempts: int = 10,
    time_range: TimeRange = "month",
    backend: str = "auto",
) -> str:
    """
    Args:
        query: The search query.
        max_results: Maximum number of search results to return.
        max_attempts: How many times to retry on throttling or empty results.
        time_range: How far back to search: "day", "week", "month", or "year".
        backend: The search engine backend to use (e.g., "duckduckgo", "google", "yahoo", "yandex", or "auto"
            to let the library decide).
    """
    logger = get_run_logger()
    logger.info(
        "TOOL CALL web_search_with_ddg | query=%r max_results=%d time_range=%s backend=%s",
        query,
        max_results,
        time_range,
        backend,
    )
    timelimit = _to_timelimit(time_range)
    try:
        items = _search_news_with_retry(query, max_results, max_attempts, timelimit, backend)
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


def create_fetch_agent(backend: str) -> PrefectAgent[str, list[MetadataTextSearchResult]]:
    from pydantic_ai.models.google import GoogleModel
    from pydantic_ai.providers.google import GoogleProvider

    model = GoogleModel("gemini-2.5-flash-lite", provider=GoogleProvider(api_key=google_api_key))
    agent = Agent(
        model,
        name=f"web_search_agent_with_backend_{backend}",
        output_type=list[MetadataTextSearchResult],
        deps_type=str,
        tools=[
            Tool(web_search_with_ddg, takes_ctx=False),
        ],
        system_prompt=(
            "You are an expert web search researcher.  "
            f"based on the query, fetch relevant information with the search engine {backend}"
        ),
    )
    return PrefectAgent(
        agent,
        model_task_config=TaskConfig(retries=3, retry_delay_seconds=[1.0, 2.0, 4.0], timeout_seconds=60.0),
        tool_task_config=TaskConfig(retries=2, retry_delay_seconds=[0.5, 1.0]),
    )


@task(persist_result=True, cache_policy=DEFAULT, name="fetch_ddg_search_engine")
async def fetch_ddg_search_engine() -> list[str]:
    backends = [
        "brave",
        "duckduckgo",
        "google",
        "grokipedia",
        "mojeek",
        "wikipedia",
        "yahoo",
        # "yandex",
        # "auto",
    ]
    await cast(Any, create_table_artifact)(
        key="tool-io-fetch-ddgs-backends",
        table=[{"backend": backends}],
        description="Search backends",
    )
    return backends


@task(
    persist_result=True, cache_policy=DEFAULT, name="run_backend_search"
)  # ensures the return value is stored & viewable
async def run_backend_search(backend: str, query: str) -> list[dict]:
    logger = get_run_logger()
    agent = create_fetch_agent(backend)
    result = await agent.run(query)

    # result.output is List[MetadataTextSearchResult] -> make it serializable
    output = [item.model_dump() for item in result.output]

    logger.info("backend=%s returned %d results", backend, len(output))
    await cast(Any, create_table_artifact)(
        key=f"tool-io-{backend}",
        table=[{"backend": backend, "query": query, "results": len(output)}],
        description="Search tool inputs and result counts",
    )
    return output  # <-- this is what appears in the UI "Result"


@flow(name="equity_research_report", log_prints=True)
async def build_equity_research_report() -> dict[str, list[dict]]:
    backends = await cast(Any, fetch_ddg_search_engine)()

    tasks = [run_backend_search(b, "latest news on AAPL stock") for b in backends]
    results = await asyncio.gather(*tasks)

    report = dict(zip(backends, results, strict=False))
    return report  # flow result also persisted & viewable


# --------------------------------------------------------------------------
# Entry point.
# --------------------------------------------------------------------------
if __name__ == "__main__":
    # Simplest way to run end-to-end:
    asyncio.run(build_equity_research_report())
