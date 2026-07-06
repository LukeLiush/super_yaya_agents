import asyncio
import json
import tempfile
import webbrowser
from pathlib import Path

from prefect import flow, get_run_logger, task
from prefect.cache_policies import DEFAULT
from pydantic import BaseModel
from scrapling import DynamicFetcher, Fetcher, StealthyFetcher, TextHandler
from scrapling.engines.toolbelt.custom import Response
from web_search_task import SearchResult

from invesetment_agent.flows.equity_web_resarch_report.naming import run_name_from


class HtmlSearchResult(BaseModel):
    search_result: SearchResult
    text: str = ""  # extracted visible text — what the LLM actually needs
    html: str | None = None  # optional, only if you truly need the markup


async def scrape(url: str, mode: str = "static") -> Response:
    """
    mode: "static" (fast HTTP), "dynamic" (JS render), "stealth" (anti-bot).
    """
    if mode == "stealth":
        # Use asyncio.to_thread to run sync fetcher in a separate thread
        page = await asyncio.to_thread(
            StealthyFetcher.fetch,
            url,
            headless=True,
            solve_cloudflare=True,
            network_idle=True,
        )
        return page
    if mode == "dynamic":
        return await asyncio.to_thread(
            DynamicFetcher.fetch,
            url,
            headless=True,
            network_idle=True,
        )
    return await asyncio.to_thread(
        Fetcher.get,
        url,
        allow_redirects=True,
    )


async def _is_good_enough(page: Response) -> bool:
    """A fetch is 'good' only if it returned real content, not a JS shell or block page."""
    if page is None:
        return False

    # NEW: Check for 404 or other permanent failures
    # Assuming the Response object has a status_code attribute
    if getattr(page, "status_code", None) == 404:
        return False

    text = str(page.get_all_text() or "").strip()
    lowered = text.lower()
    blockers = (
        "enable javascript",
        "captcha",
        "are you a robot",
        "verify you are human",
        "access denied",
        "checking your browser",
        "please turn on javascript",
    )
    return not any(b in lowered for b in blockers)


async def scrape_auto(url: str) -> tuple[Response, str]:
    """
    Escalate static -> dynamic -> stealth, stopping at the first mode
    that passes the quality check. If none pass, return the last page
    that at least didn't throw. Returns (page, mode_used).
    """
    last_page: Response | None = None
    last_mode = "none"

    for mode in ("static", "dynamic", "stealth"):
        try:
            page = await scrape(url, mode=mode)
        except Exception:
            continue  # this mode failed outright, try the next

        last_page, last_mode = page, mode  # remember it as a fallback

        if await _is_good_enough(page):
            return page, mode  # success, stop escalating

    # Instead of raising, return what we have (even if it's "not good enough")
    # or return (None, "failed")
    return last_page, last_mode


@task(
    task_run_name=run_name_from(lambda p: f"{p['query_result'].url}", prefix="scrape"),
    log_prints=True,
    cache_policy=DEFAULT,
    persist_result=True,
    retries=3,
    retry_delay_seconds=[10.0, 30.0, 60.0],
    timeout_seconds=600.0,
)
async def web_scrapping_task(query_result: SearchResult) -> HtmlSearchResult:
    logger = get_run_logger()

    # 1. Log the input for better traceability
    logger.info("Starting web_scrapping_task with input: %s", json.dumps(query_result.model_dump()))

    try:
        # 2. Log intent and execute scrape
        logger.info("Scraping URL: %s", query_result.url)
        page, mode_used = await scrape_auto(query_result.url)

        if page is None:
            logger.error("Total failure: Could not even get a response from %s", query_result.url)
            return HtmlSearchResult(search_result=query_result, text="", html="")

        # Check if it was a 404 or just bad content
        if not await _is_good_enough(page):
            logger.warning("Scrape finished for %s but content is poor/blocked (Mode: %s)", query_result.url, mode_used)
            # You still return it so the flow doesn't crash,
            # but the LLM will just see empty/minimal text.

        html: TextHandler = page.html_content
        text_content = page.get_all_text()

        # 3. Robust logging of results and content length
        content_len = len(str(html))
        logger.info(
            "Successfully scraped URL: %s (HTML length: %d, Text length: %d) with mode: %s",
            query_result.url,
            content_len,
            len(str(text_content)),
            mode_used,
        )
        # 4. Preview the structure
        # soup = BeautifulSoup(str(html), "html.parser")
        # pretty: Union[str | bytes] = soup.prettify()
        # logger.info("Pretty HTML preview (first 3000 chars):\n%s", pretty[:3000])

        # 5. Create an artifact to view in Prefect UI
        # We wrap it in triple backticks and 'html' tag for syntax highlighting
        # Improved sanitization for the artifact key
        # sanitized_url = query_result.url.split('//')[-1].replace('.', '-').replace('/', '-')
        # artifact_key = f"scraped-html-{sanitized_url}"[:50].lower().rstrip('-')
        #
        # await acreate_markdown_artifact(
        #     key=artifact_key,
        #     markdown=f"### Scraped HTML from {query_result.url}\n\n```html\n{pretty}\n```",
        #     description=f"HTML content captured from {query_result.url}"
        # )

        return HtmlSearchResult(
            search_result=query_result,
            text=str(text_content) or "",
            html=str(html) or "",
        )

    except Exception as e:
        # 5. Log the error with context before re-raising for Prefect retries
        logger.error("Failed to scrape URL: %s. Error: %s", query_result.url, str(e), exc_info=True)
        raise


@task
def debug_html_locally(html_content: str):
    # Create a temporary file
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html") as f:
        f.write(html_content)
        file_path = Path(f.name).absolute()

    print(f"HTML saved to: {file_path}")
    # Automatically open in default browser
    webbrowser.open(f"file://{file_path}")


@flow
async def test_webscraping_flow():
    future = web_scrapping_task.submit(
        SearchResult(
            title="TSLA Stock Quote Price and Forecast | CNN",
            snippet=(
                "13 hours ago · View Tesla, Inc. TSLA stock quote prices, financial information, "
                "real-time forecasts, and company news from CNN "
            ),
            url="https://www.cnn.com/markets/stocks/TSLA",
        )
    )
    # Correctly retrieve the result
    result = future.result()
    # if asyncio.iscoroutine(result):
    #     result = await result
    debug_html_locally(result.html)
    # print(result[:100])


if __name__ == "__main__":
    asyncio.run(test_webscraping_flow())
