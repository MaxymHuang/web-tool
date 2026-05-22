import time

from ddgs import DDGS
from ddgs.exceptions import DDGSException
from rapidfuzz import fuzz

from news_crawler.models import ArticleResult
from news_crawler.platform_support import http_user_agent
from news_crawler.utils import resolve_media

RELEVANCE_THRESHOLD = 50
MAX_RETRIES = 3
RETRY_DELAY_SEC = 3.0
USER_AGENT = http_user_agent()


def search_news(prompt: str, max_results: int = 15) -> list[ArticleResult]:
    """Search DuckDuckGo News and rank by relevance to the prompt."""
    prompt = prompt.strip()
    if not prompt:
        return []

    raw: list[dict] = []
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            raw = DDGS().news(prompt, max_results=max_results)
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
        url = (item.get("url") or item.get("link") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        title = (item.get("title") or "").strip() or "Untitled"
        snippet = (item.get("body") or item.get("snippet") or "").strip()
        text = f"{title} {snippet}"
        score = float(fuzz.token_set_ratio(prompt, text))

        if score < RELEVANCE_THRESHOLD:
            continue

        articles.append(
            ArticleResult(
                title=title,
                url=url,
                snippet=snippet,
                media=resolve_media(item, url),
                score=score,
                selected=True,
            )
        )

    articles.sort(key=lambda a: a.score, reverse=True)
    return articles
