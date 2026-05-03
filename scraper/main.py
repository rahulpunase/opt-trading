import logging
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chartink_scraper")

app = FastAPI(title="Chartink Scraper")

_CHARTINK_DOMAIN = "chartink.com"
_PAGE_TIMEOUT = 30_000
_TABLE_TIMEOUT = 20_000

_TABLE_ROW_SELECTOR = "div[style*='max-height: 800px'] table tbody tr"
_SYMBOL_CELL_INDEX = 2


def _validate_chartink_url(url: str) -> None:
    parsed = urlparse(url)
    domain = parsed.netloc.lower().lstrip("www.")
    if domain != _CHARTINK_DOMAIN:
        raise ValueError(f"Not a Chartink URL: '{url}'")
    if not parsed.path.startswith("/screener/"):
        raise ValueError(f"Not a Chartink screener URL: '{url}' — path must start with /screener/")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/scrape")
def scrape(url: str = Query(..., description="Chartink screener URL")) -> dict:
    try:
        _validate_chartink_url(url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    symbols: list[str] = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="en-US",
            )
            page = ctx.new_page()

            logger.debug("navigating to %s", url)
            page.goto(url, wait_until="networkidle", timeout=_PAGE_TIMEOUT)

            try:
                page.wait_for_selector(_TABLE_ROW_SELECTOR, timeout=_TABLE_TIMEOUT)
            except PlaywrightTimeout:
                logger.warning("results table did not appear within %dms for %s", _TABLE_TIMEOUT, url)
                return {"symbols": []}

            for row in page.locator(_TABLE_ROW_SELECTOR).all():
                try:
                    cells = row.locator("td").all()
                    if len(cells) > _SYMBOL_CELL_INDEX:
                        text = cells[_SYMBOL_CELL_INDEX].inner_text().strip().upper()
                        if text and text not in ("SYMBOL", "SR.", "-", ""):
                            symbols.append(text)
                except Exception as exc:
                    logger.warning("skipping row due to error: %s", exc)

    except PlaywrightTimeout:
        logger.warning("page load timed out for %s", url)
        return {"symbols": []}
    except Exception as exc:
        logger.error("unexpected error scraping %s: %s", url, exc)
        return {"symbols": []}

    logger.info("resolved %d symbols from %s", len(symbols), url)
    return {"symbols": symbols}
