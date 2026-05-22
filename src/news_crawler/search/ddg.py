import time

from ddgs import DDGS
from ddgs.exceptions import DDGSException
from news_crawler.i18n import MARKETS
from news_crawler.models import ArticleResult
from news_crawler.platform_support import http_user_agent
from news_crawler.search.filters import SearchFilters, parse_published_date
from news_crawler.utils import resolve_media

MAX_RETRIES = 3
RETRY_DELAY_SEC = 3.0
USER_AGENT = http_user_agent()


def search_news(
    prompt: str,
    max_results: int = 15,
    market_id: str = "en",
    filters: SearchFilters | None = None,
) -> list[ArticleResult]:
    """Search DuckDuckGo Web; optionally boost with a news-focused query."""
    prompt = prompt.strip()
    if not prompt:
        return []

    filters = filters or SearchFilters()
    market = MARKETS.get(market_id, MARKETS["en"])
    region = market.ddg_region
    timelimit = filters.ddg_timelimit

    query = prompt if not filters.prefer_news else f"{prompt} news"

    raw: list[dict] = []
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            raw = DDGS().text(
                query,
                region=region,
                max_results=max_results,
                timelimit=timelimit,
            )
            break
        except DDGSException as exc:
            last_error = exc
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SEC * (attempt + 1))
            else:
                raise RuntimeError(
                    "DuckDuckGo rate limit or search error. Wait a moment and try again."
                ) from exc
    if last_error and not raw:
        raise RuntimeError(
            "DuckDuckGo search failed. Wait a moment and try again."
        ) from last_error

    articles: list[ArticleResult] = []
    seen_urls: set[str] = set()

    for item in raw:
        url = (item.get("url") or item.get("link") or item.get("href") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        title = (item.get("title") or "").strip() or "Untitled"
        snippet = (item.get("body") or item.get("snippet") or "").strip()
        media = resolve_media(item, url)
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
