from typing import List, Literal

from prefect import task, get_run_logger
from prefect.cache_policies import DEFAULT
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.durable_exec.prefect import PrefectAgent, TaskConfig

from invesetment_agent.infrastructure.models.factory import ConfiguredModelProvider
from invesetment_agent.flows.equity_web_resarch_report.naming import run_name_from

TimeRange = Literal["day", "week", "month", "year"]


class SearchQuery(BaseModel):
    query: str = Field(
        description="A specific, single-intent, entity-disambiguated search query "
                    "with varied phrasing relative to the other queries."
    )
    time_range: TimeRange = Field(
        description="The best recency window for THIS query: 'day'/'week' for "
                    "breaking/time-sensitive angles, 'month' for general recent "
                    "activity, 'year' for background/contextual angles."
    )


class SearchQueries(BaseModel):
    queries: list[SearchQuery] = Field(
        min_length=3, max_length=5,
        description="3-5 specific, single-intent, entity-disambiguated queries "
                    "covering different facets of the topic, each with its own "
                    "appropriate time range.",
    )


def create_query_transform_agent() -> PrefectAgent[str, List[SearchQueries]]:
    provider = ConfiguredModelProvider(prefer_env_first=True)  # local dev with .env
    model = provider.get_model("pydantic:gemini-2.5-flash-lite")
    agent = Agent(
        model,
        name=f"query_transformation",
        output_type=List[SearchQueries],
        tools=[],
        system_prompt=(
            """
You are a search query expansion engine. Your job is to transform a user's topic \
into a small set of specific, diverse search queries that together retrieve \
comprehensive, high-quality results.

Produce between 3 and 5 queries that follow these rules:

1. DISAMBIGUATE the subject. Identify the most likely intended entity and use its \
precise, searchable name. Include disambiguating identifiers when the term is \
ambiguous (e.g. for "apple stock" use "Apple Inc." and the ticker "AAPL", not just \
"Apple"; for "mercury" specify "Mercury planet" vs "Mercury element" based on context).

2. COVER DISTINCT FACETS. Each query must target a DIFFERENT aspect of the topic so \
the set as a whole is comprehensive. Infer the relevant facets from the topic itself \
(do not assume a fixed domain). Avoid two queries that ask for essentially the same thing.

3. BE SPECIFIC AND SINGLE-INTENT. Each query should express ONE clear intent and be \
specific and self-contained. Prefer concrete entities, events, and qualifiers over \
broad generic terms. Avoid vague queries like "apple information".

4. VARY THE PHRASING. Use different terminology and synonyms across the queries \
(e.g. "earnings" vs "financial results", "layoffs" vs "job cuts") so you capture \
sources that use different words.

5. CHOOSE A TIME RANGE PER QUERY. For each query, set `time_range` to the window that \
best fits THAT query's facet:
   - "day" or "week": breaking news, current prices, latest developments, rapidly \
changing topics.
   - "month": general recent activity, ongoing situations, recent reports.
   - "year": background, context, established facts, historical or reference angles \
that are NOT time-sensitive.
   Vary the time_range across the set when the facets differ in how time-sensitive \
they are. You MAY add a soft text anchor like "latest" or the current year to SOME \
queries, but do NOT put overly specific dates (like an exact quarter) in the query \
text, as that can exclude relevant undated results. Keep at least one query without \
any text time anchor.

6. KEEP QUERIES SEARCH-FRIENDLY. Write them as search queries (keyword-rich phrases), \
not as full questions or sentences. Do not include explanations, numbering, or commentary.

If the input is too vague to identify any subject, produce your best literal \
interpretation as queries rather than refusing.

Return only the queries.
            """
        ),
    )
    return PrefectAgent(
        agent,
        model_task_config=TaskConfig(
            retries=3, retry_delay_seconds=[1.0, 2.0, 4.0], timeout_seconds=60.0
        ),
    )


@task(
    name="query_transformation",
    task_run_name=run_name_from(lambda p: p["query"], prefix="expand"),
    log_prints=True,
    cache_policy=DEFAULT,
    persist_result=True,
    retries=3,
    retry_delay_seconds=[1.0, 2.0, 4.0],
    timeout_seconds=60.0)
async def query_transformation_task(query: str = "what is the latest news on tesla stock?") -> List[SearchQueries]:
    logger = get_run_logger()
    logger.info("Starting query transformation for: '%s'", query)
    agent = create_query_transform_agent()
    result = await agent.run(query)

    output_queries = []
    if result.output:
        for sq in result.output:
            output_queries.extend(sq.queries)

    logger.info("Query transformation completed. Generated %d queries", len(output_queries))
    for i, sq in enumerate(output_queries, 1):
        logger.debug("  %d. [%s] (time_range: %s)", i, sq.query, sq.time_range)
    return result.output
