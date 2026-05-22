"""Unit tests for DDG date parsing."""

from news_crawler.search.filters import parse_published_date


def test_parse_published_date_unix():
    display, ts = parse_published_date(1_700_000_000)
    assert display
    assert ts is not None
