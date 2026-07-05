import asyncio
from pathlib import Path
from typing import List
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from prefect import flow, get_run_logger

from query_transformation_task import SearchQueries, SearchQuery, query_transformation_task
from web_scraping_task import web_scrapping_task, HtmlSearchResult
from web_search_task import web_search_task, SearchResult


def normalize(url: str) -> str:
    p = urlparse(url)
    return urlunparse((p.scheme, p.netloc.lower(), p.path.rstrip("/"), "", "", ""))


def dedupe_by_url(results: list[SearchResult]) -> list[SearchResult]:
    seen: set[str] = set()
    unique: list[SearchResult] = []
    for r in results:
        normalized_url = normalize(r.url)
        if normalized_url and normalized_url not in seen:
            seen.add(normalized_url)
            unique.append(r)
    return unique


@flow
async def build_flow(query: str):
    logger = get_run_logger()
    logger.info("Starting build_flow with query: '%s'", query)

    _env_path: Path = Path(__file__).parent.parent / ".env"
    if _env_path.exists():
        logger.debug("Loading environment from %s", _env_path)
        load_dotenv(dotenv_path=_env_path)
    else:
        logger.warning("Environment file not found at %s", _env_path)

    search_queries_list: List[SearchQueries] = await query_transformation_task(query=query)
    # Flatten SearchQueries list to a list of SearchQuery objects if needed, 
    # though the task seems to return List[SearchQueries] where each has a list of queries.
    # Actually, query_transformation_task returns result.output which is List[SearchQueries].

    all_queries: List[SearchQuery] = []
    for sq in search_queries_list:
        all_queries.extend(sq.queries)

    logger.info("Transformed query into %d sub-queries", len(all_queries))
    for i, sq in enumerate(all_queries, 1):
        logger.debug("Query %d: [%s] (time_range: %s)", i, sq.query, sq.time_range)
    web_search_futures = [web_search_task.submit(b, top_n=10) for b in all_queries]

    # Extract results first to allow logging count
    all_search_results = [r for f in web_search_futures for r in f.result()]
    logger.info("Collected %d raw search results from %d queries", len(all_search_results), len(all_queries))
    unique_results: list[SearchResult] = dedupe_by_url(all_search_results)
    logger.info("Successfully completed web search. Total unique items found: %d (filtered out %d duplicates)",
                len(unique_results),
                len(all_search_results) - len(unique_results))

    scrape_futures = [web_scrapping_task.submit(r) for r in unique_results]
    scraped_results: List[HtmlSearchResult] = [f.result() for f in scrape_futures]
    logger.info("Successfully completed web scraping. Total items found: %d across %d queries",
                len(scraped_results),
                len(search_queries_list))
    # Log the total bytes
    # Calculate total HTML bytes
    total_html_bytes = sum(len(r.html) for r in scraped_results if r.html)
    logger.info("Total HTML bytes scraped: %d bytes (%.2f KB)",
                total_html_bytes,
                total_html_bytes / 1024)


if __name__ == "__main__":
    #asyncio.run(build_flow(query="what is the latest news on tesla stock? and why stock recently dropped recently?"))
    asyncio.run(build_flow(query="what is the latest news on parkinson disease? any breakthru medications?"))
    #asyncio.run(build_flow(query="what is the price across amazon, walmart, target for corsair ddr4 3200mhz 16gb ram? and what is the price trend for the last 3 months?"))
