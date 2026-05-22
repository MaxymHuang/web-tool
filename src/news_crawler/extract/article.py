import re

import httpx
import trafilatura

from news_crawler.i18n import MARKETS
from news_crawler.platform_support import http_user_agent

SUMMARY_MAX_LEN = 300
TIMEOUT_SEC = 10.0
SENTENCE_SPLIT = re.compile(r"(?<=[.!?。！？])\s*")


def _first_sentences(text: str, max_len: int = SUMMARY_MAX_LEN) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    sentences = SENTENCE_SPLIT.split(text)
    summary = ""
    for sentence in sentences:
        candidate = f"{summary} {sentence}".strip() if summary else sentence
        if len(candidate) > max_len:
            break
        summary = candidate
    if not summary:
        summary = text[:max_len]
    if len(summary) > max_len:
        summary = summary[: max_len - 3].rstrip() + "..."
    return summary


def fetch_summary(
    url: str,
    fallback_snippet: str = "",
    market_id: str = "en",
) -> str:
    """Fetch article page and build a short summary."""
    market = MARKETS.get(market_id, MARKETS["en"])
    try:
        with httpx.Client(
            timeout=TIMEOUT_SEC,
            follow_redirects=True,
            headers={"User-Agent": http_user_agent()},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            html = response.text
    except Exception:
        return _first_sentences(fallback_snippet) if fallback_snippet else ""

    extracted = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        target_language=market.trafilatura_lang,
    )
    if extracted:
        return _first_sentences(extracted)
    return _first_sentences(fallback_snippet) if fallback_snippet else ""
