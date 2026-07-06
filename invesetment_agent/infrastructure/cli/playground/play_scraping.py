"""
uv add browserforge
uv add msgspec
uv add markdownify
uv add patchright
uv add playwright
uv run playwright install chromium
"""

from scrapling import DynamicFetcher, Fetcher, StealthyFetcher
from scrapling.engines.toolbelt.custom import Response


def scrape(url: str, mode: str = "static") -> Response:
    """
    mode: "static" (fast HTTP), "dynamic" (JS render), "stealth" (anti-bot).
    Returns a parsed page object you can .css()/.xpath() on,
    or use .html_content / .get_all_text().
    """
    if mode == "stealth":
        # return StealthyFetcher.fetch(url, headless=True, solve_cloudflare=True, network_idle=True)
        page = StealthyFetcher.fetch(
            url,
            headless=True,
            solve_cloudflare=True,  # drop it — Yahoo isn't using Cloudflare here
            network_idle=True,  # wait for JS/XHR to finish
            # if your version supports it, wait for a specific element that only exists on the real page:
            # wait_selector='[data-symbol="TSLA"]',
        )
        return page
    if mode == "dynamic":
        return DynamicFetcher.fetch(url, headless=True, network_idle=True)
    return Fetcher.get(url)


def main():
    import logging

    logging.basicConfig(level=logging.DEBUG)
    from markdownify import markdownify as md
    from scrapling.fetchers import DynamicFetcher

    page = scrape(
        "https://www.amazon.com/s?k=amd+ryzen+7+5700x&crid=1M6LBMFK9L5NZ&sprefix=AMD+Ryzen%2Caps%2C978&ref=nb_sb_ss_saint-nlq-prefix_ci_hl-bn-left_1_10",
        mode="stealth",
    )
    md(page.html_content)
    # print(page.html_content)
    print(page.body)


if __name__ == "__main__":
    main()
