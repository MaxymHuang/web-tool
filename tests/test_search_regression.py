"""Regression tests for DDG search result underfill bugs."""

import pytest

from news_crawler.search.ddg import search_news

EXAMPLE_PROMPTS = [
    "nvidia earnings",
    "semiconductor supply chain",
    "electric vehicle battery news",
    "federal reserve rate decision",
    "global inflation outlook",
    "renewable energy policy",
    "japan stock market update",
    "china property market",
    "cybersecurity breach report",
]


def _item(url: str) -> dict[str, str]:
    return {
        "title": f"title-{url.rsplit('/', 1)[-1]}",
        "url": url,
        "body": "snippet",
        "source": "src",
        "date": "",
    }


@pytest.mark.parametrize("prompt", EXAMPLE_PROMPTS)
def test_search_news_fills_to_max_with_text_fallback(monkeypatch, prompt):
    max_results = 30
    news_items = [_item(f"https://news.example/{i}") for i in range(21)]
    text_items = [_item(f"https://text.example/{i}") for i in range(9)]

    def fake_fetch_news_results(query, *, region, max_results, timelimit):
        return news_items, None

    def fake_ddg_text_search(query, *, region, max_results, timelimit):
        return text_items, None

    monkeypatch.setattr(
        "news_crawler.search.ddg.fetch_news_results", fake_fetch_news_results
    )
    monkeypatch.setattr(
        "news_crawler.search.ddg._ddg_text_search", fake_ddg_text_search
    )

    results = search_news(prompt, max_results=max_results, market_id="zh_tw")

    assert len(results) == max_results
    assert len({r.url for r in results}) == max_results


@pytest.mark.parametrize("prompt", EXAMPLE_PROMPTS)
def test_search_news_uses_alt_query_when_primary_fallback_overlaps(monkeypatch, prompt):
    max_results = 30
    base_news = [_item(f"https://base.example/{i}") for i in range(18)]
    primary_overlap = base_news[:8] + [_item(f"https://extra.example/{i}") for i in range(2)]
    alt_unique = [_item(f"https://alt.example/{i}") for i in range(5)]

    def fake_fetch_news_results(query, *, region, max_results, timelimit):
        return list(base_news), None

    calls = {"count": 0}

    def fake_ddg_text_search(query, *, region, max_results, timelimit):
        calls["count"] += 1
        if calls["count"] == 1:
            return primary_overlap, None
        return alt_unique, None

    monkeypatch.setattr(
        "news_crawler.search.ddg.fetch_news_results", fake_fetch_news_results
    )
    monkeypatch.setattr(
        "news_crawler.search.ddg._ddg_text_search", fake_ddg_text_search
    )

    results = search_news(prompt, max_results=max_results, market_id="zh_tw")

    assert len(results) == 25
    assert any(r.url.startswith("https://alt.example/") for r in results)
    assert len({r.url for r in results}) == len(results)
