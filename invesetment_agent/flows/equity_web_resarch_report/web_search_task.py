import json
from typing import Any

from agno.tools.websearch import WebSearchTools
from prefect import get_run_logger, task
from prefect.cache_policies import DEFAULT
from pydantic import AliasChoices, BaseModel, Field

from invesetment_agent.flows.equity_web_resarch_report.naming import run_name_from
from invesetment_agent.flows.equity_web_resarch_report.query_transformation_task import SearchQuery, TimeRange

_TIMELIMIT_MAP: dict[str, str] = {
    "day": "d",
    "week": "w",
    "month": "m",
    "year": "y",
}


class SearchResult(BaseModel):
    title: str = ""
    url: str = Field(default="", validation_alias=AliasChoices("url", "href", "link"))
    snippet: str = Field(default="", validation_alias=AliasChoices("body", "snippet"))
    model_config = {"extra": "ignore"}  # tolerate unknown/new source keys


class EmptyResults(Exception):
    """Raised when the news search returns no items, to trigger a retry."""


def _to_timelimit(time_range: TimeRange) -> str:
    try:
        return _TIMELIMIT_MAP[time_range]
    except KeyError as err:
        raise ValueError(f"invalid time_range: {time_range!r} (use day/week/month/year)") from err


def _build_ddg(time_range: TimeRange, backend: str) -> WebSearchTools:
    # timelimit/backend are fixed at construction time, so build per-call to vary them.
    timelimit = _to_timelimit(time_range)
    return WebSearchTools(
        enable_news=True,
        enable_search=False,
        timelimit=timelimit,
        region="us-en",
        backend=backend,
    )


@task(
    task_run_name=run_name_from(
        lambda p: f"[{p['search_query'].time_range}] {p['search_query'].query}", prefix="search"
    ),
    log_prints=True,
    cache_policy=DEFAULT,
    persist_result=True,
    retries=3,
    retry_delay_seconds=[1.0, 2.0, 4.0],
    timeout_seconds=60.0,
)
async def web_search_task(search_query: SearchQuery, top_n=10) -> list[SearchResult]:
    logger = get_run_logger()
    logger.info("Executing web search for: [%s] (time_range: %s)", search_query.query, search_query.time_range)
    ddg: WebSearchTools = _build_ddg(search_query.time_range, "auto")

    raw: str = ddg.web_search(search_query.query, max_results=50)
    items: list[dict[str, Any]] = json.loads(raw) if isinstance(raw, str) else raw

    if not items:
        logger.warning("No results found for: [%s]", search_query.query)
        raise EmptyResults(search_query.query)

    # --- Parse raw dicts into typed, validated SearchResult objects ---
    results: list[SearchResult] = [SearchResult.model_validate(item) for item in items]
    top_n_results = results[:top_n]
    logger.info("Found %d results for: [%s]", len(top_n_results), search_query.query)

    # --- Preview the first 3: log + table artifact ---
    preview = top_n_results[:3]
    logger.info("Preview (first %d of %d): %s", len(preview), len(results), [r.model_dump() for r in preview])

    # await acreate_table_artifact(
    #     key=f"search-preview-{uuid.uuid4().hex[:8]}",
    #     table=[r.model_dump() for r in preview],  # artifact needs dicts, not models
    #     description=(
    #         f"Top {len(preview)} of {len(results)} results for "
    #         f"[{search_query.time_range}] {search_query.query}"
    #     ),
    # )

    return results
