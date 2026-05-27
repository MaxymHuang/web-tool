import time

from ddgs import DDGS
from ddgs.exceptions import DDGSException
from news_crawler.i18n import MARKETS
from news_crawler.models import ArticleResult
from news_crawler.search.ddg_news_http import fetch_news_results
from news_crawler.search.filters import SearchFilters, parse_published_date
from news_crawler.utils import resolve_media

MAX_RETRIES = 2
RETRY_DELAY_SEC = 2.0

def _ddg_text_search(
    query: str,
    *,
    region: str,
    max_results: int,
    timelimit: str | None,
) -> tuple[list[dict], str | None]:
    last_error: str | None = None
    merged: list[dict] = []
    seen_urls: set[str] = set()
    page = 1
    while len(merged) < max_results and page <= 3:
        page_raw: list[dict] = []
        page_error: str | None = None
        for attempt in range(MAX_RETRIES):
            try:
                page_raw = DDGS(timeout=25).text(
                    query,
                    region=region,
                    max_results=max_results - len(merged),
                    timelimit=timelimit,
                    page=page,
                )
                page_error = None
                break
            except DDGSException as exc:
                page_error = repr(exc)
                last_error = page_error
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY_SEC)

        # Some DDGS backend mixes return empty/no-results with pagination params.
        # Probe a non-paged call before giving up on fallback for this query.
        if page == 1 and not page_raw:
            for attempt in range(MAX_RETRIES):
                try:
                    page_raw = DDGS(timeout=25).text(
                        query,
                        region=region,
                        max_results=max_results - len(merged),
                        timelimit=timelimit,
                    )
                    page_error = None
                    break
                except DDGSException as exc:
                    page_error = repr(exc)
                    last_error = page_error
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY_SEC)

        added = 0
        for item in page_raw:
            url = (item.get("url") or item.get("link") or item.get("href") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            merged.append(item)
            added += 1
            if len(merged) >= max_results:
                break

        if page_error is not None or added == 0:
            break
        page += 1

    return merged, last_error


def _merge_unique_results(base: list[dict], incoming: list[dict], *, limit: int) -> int:
    seen = {
        (item.get("url") or item.get("link") or item.get("href") or "").strip()
        for item in base
    }
    added = 0
    for item in incoming:
        url = (item.get("url") or item.get("link") or item.get("href") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        base.append(item)
        added += 1
        if len(base) >= limit:
            break
    return added


def search_news(
    prompt: str,
    max_results: int = 15,
    market_id: str = "en",
    filters: SearchFilters | None = None,
) -> list[ArticleResult]:
    """Search DuckDuckGo News via news.js, with ddgs web search as fallback."""
    prompt = prompt.strip()
    if not prompt:
        return []

    filters = filters or SearchFilters()
    market = MARKETS.get(market_id, MARKETS["en"])
    region = market.ddg_region
    timelimit = filters.ddg_timelimit
    query = prompt if not filters.prefer_news else f"{prompt} news"

    raw, _news_error = fetch_news_results(
        query,
        region=region,
        max_results=max_results,
        timelimit=timelimit,
    )

    if len(raw) < max_results:
        remaining = max_results - len(raw)
        text_raw, _text_error = _ddg_text_search(
            query,
            region=region,
            max_results=remaining,
            timelimit=timelimit,
        )
        if text_raw:
            _merge_unique_results(raw, text_raw, limit=max_results)

    if len(raw) < max_results:
        alternate_query = f"{prompt} news" if not filters.prefer_news else prompt
        alternate_query = alternate_query.strip()
        if alternate_query and alternate_query != query:
            remaining = max_results - len(raw)
            overfetch_target = min(max_results, max(remaining + 6, remaining * 3))
            alt_raw, _alt_error = _ddg_text_search(
                alternate_query,
                region=region,
                max_results=overfetch_target,
                timelimit=timelimit,
            )
            _merge_unique_results(raw, alt_raw, limit=max_results)

    if not raw:
        raise RuntimeError(
            "DuckDuckGo search failed. Wait a moment and try again."
        ) from None

    articles: list[ArticleResult] = []
    seen_urls: set[str] = set()

    for item in raw:
        url = (item.get("url") or item.get("link") or item.get("href") or "").strip()
        if not url:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)

        title = (item.get("title") or "").strip() or "Untitled"
        snippet = (item.get("body") or item.get("snippet") or "").strip()
        media = resolve_media(item, url) or (item.get("source") or "").strip()
        published_at, published_ts = parse_published_date(item.get("date"))

        articles.append(
            ArticleResult(
                title=title,
                url=url,
                snippet=snippet,
                media=media,
                queued=False,
                market=market_id,
                published_at=published_at,
                published_ts=published_ts,
            )
        )

    return articles
