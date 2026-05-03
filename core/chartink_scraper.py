import logging
import os
from urllib.parse import urlencode, urlparse

import httpx

logger = logging.getLogger("chartink_scraper")

_CHARTINK_DOMAIN = "chartink.com"
_SCRAPER_URL = os.getenv("SCRAPER_URL", "http://scraper:8080")
_REQUEST_TIMEOUT = 60.0  # seconds — scraper may take up to 30s to render the page


def _validate_chartink_url(url: str) -> None:
    parsed = urlparse(url)
    domain = parsed.netloc.lower().lstrip("www.")
    if domain != _CHARTINK_DOMAIN:
        raise ValueError(f"Not a Chartink URL: '{url}'")
    if not parsed.path.startswith("/screener/"):
        raise ValueError(f"Not a Chartink screener URL: '{url}' — path must start with /screener/")


def fetch_chartink_symbols(
    screener_url: str,
    timeout: float = _REQUEST_TIMEOUT,
) -> list[str]:
    """
    Fetch NSE symbols from a Chartink screener via the scraper sidecar service.
    Returns [] (never raises) so callers can fall back to static instruments on failure.
    """
    try:
        _validate_chartink_url(screener_url)
    except ValueError as exc:
        logger.error("Chartink URL validation failed: %s", exc)
        return []

    endpoint = f"{_SCRAPER_URL}/scrape?{urlencode({'url': screener_url})}"
    try:
        response = httpx.get(endpoint, timeout=timeout)
        response.raise_for_status()
        symbols: list[str] = response.json().get("symbols", [])
        logger.info("Chartink: resolved %d symbols from %s", len(symbols), screener_url)
        return symbols
    except httpx.HTTPStatusError as exc:
        logger.error("Chartink scraper returned HTTP %s for %s", exc.response.status_code, screener_url)
    except httpx.RequestError as exc:
        logger.error("Chartink scraper unreachable: %s", exc)
    except Exception as exc:
        logger.error("Chartink: unexpected error fetching %s: %s", screener_url, exc)

    return []
