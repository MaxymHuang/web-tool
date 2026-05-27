"""Direct DuckDuckGo News API (news.js) without the ddgs metasearch layer."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urljoin

import httpx

from news_crawler.platform_support import http_user_agent

NEWS_URL = "https://duckduckgo.com/news.js"
HOME_URL = "https://duckduckgo.com/"
TIMEOUT_SEC = 25.0
_PAGE_SIZE = 30

_VQD_MARKERS: tuple[tuple[bytes, int, bytes], ...] = (
    (b'vqd="', 5, b'"'),
    (b"vqd=", 4, b"&"),
    (b"vqd='", 5, b"'"),
)


def _extract_vqd(html: bytes, query: str) -> str:
    for start_marker, offset, end_marker in _VQD_MARKERS:
        try:
            start = html.index(start_marker) + offset
            end = html.index(end_marker, start)
            return html[start:end].decode()
        except ValueError:
            continue
    raise ValueError(f"Could not extract vqd for query {query!r}")


def _normalize_result(item: dict[str, Any]) -> dict[str, str]:
    return {
        "title": str(item.get("title") or ""),
        "body": str(item.get("excerpt") or item.get("body") or ""),
        "url": str(item.get("url") or ""),
        "date": str(item.get("date") or ""),
        "source": str(item.get("source") or ""),
        "image": str(item.get("image") or ""),
    }


def fetch_news_results(
    query: str,
    *,
    region: str,
    max_results: int,
    timelimit: str | None = None,
) -> tuple[list[dict[str, str]], str | None]:
    """
    Fetch news from duckduckgo.com/news.js with pagination.

    Returns (items, error_message). error_message is set only when no items were fetched.
    """
    merged: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    last_error: str | None = None
    headers = {
        "User-Agent": http_user_agent(),
        "Accept": "application/json, text/javascript, */*; q=0.1",
        "Referer": "https://duckduckgo.com/",
    }

    try:
        with httpx.Client(
            timeout=TIMEOUT_SEC,
            headers=headers,
            follow_redirects=True,
        ) as client:
            home = client.get(HOME_URL, params={"q": query})
            home.raise_for_status()
            vqd = _extract_vqd(home.content, query)

            page = 1
            next_url: str | None = None
            while len(merged) < max_results and page <= 3:
                if next_url:
                    resp = client.get(urljoin(HOME_URL, next_url))
                else:
                    params: dict[str, str] = {
                        "l": region,
                        "o": "json",
                        "noamp": "1",
                        "q": query,
                        "vqd": vqd,
                        "p": "-1",
                    }
                    if timelimit:
                        params["df"] = timelimit
                    resp = client.get(NEWS_URL, params=params)
                resp.raise_for_status()
                payload = resp.json()
                batch = payload.get("results") or []
                if not isinstance(batch, list):
                    last_error = "news.js returned unexpected payload"
                    break
                next_marker = payload.get("next")
                next_url = str(next_marker).strip() if next_marker else None

                added = 0
                for item in batch:
                    if not isinstance(item, dict):
                        continue
                    row = _normalize_result(item)
                    url = row["url"].strip()
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    merged.append(row)
                    added += 1
                    if len(merged) >= max_results:
                        break

                if added == 0:
                    break
                if not next_url:
                    break
                page += 1
    except (httpx.HTTPError, ValueError, json.JSONDecodeError, KeyError) as exc:
        last_error = f"{type(exc).__name__}: {exc}"

    if merged:
        return merged[:max_results], None
    return [], last_error
