"""DuckDuckGo search options and date parsing for news results."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

# DuckDuckGo news timelimit values
TIMELIMIT_ANY = ""
TIMELIMIT_DAY = "d"
TIMELIMIT_WEEK = "w"
TIMELIMIT_MONTH = "m"
TIMELIMIT_YEAR = "y"

TIMELIMIT_CHOICES = (
    TIMELIMIT_ANY,
    TIMELIMIT_DAY,
    TIMELIMIT_WEEK,
    TIMELIMIT_MONTH,
    TIMELIMIT_YEAR,
)


@dataclass
class SearchFilters:
    """Options passed to the DDGS search API (no post-search filtering)."""

    timelimit: str | None = None  # d, w, m, y for DDG API
    prefer_news: bool = False

    @property
    def ddg_timelimit(self) -> str | None:
        if self.timelimit and self.timelimit in TIMELIMIT_CHOICES[1:]:
            return self.timelimit
        return None


_RELATIVE_DATE = re.compile(
    r"(\d+)\s*(second|minute|hour|day|week|month|year)s?\s*ago",
    re.IGNORECASE,
)


def parse_published_date(raw: Any) -> tuple[str, float | None]:
    """
    Parse DDG date field into display string and UTC timestamp (seconds).

    Returns ("", None) when unknown.
    """
    if raw is None or raw == "":
        return "", None

    if isinstance(raw, (int, float)):
        ts = float(raw)
        if ts > 1e12:
            ts /= 1000.0
        if ts > 1e9:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            return dt.strftime("%Y-%m-%d"), ts

    text = str(raw).strip()
    if not text:
        return "", None

    if text.isdigit():
        return parse_published_date(int(text))

    match = _RELATIVE_DATE.search(text)
    if match:
        amount = int(match.group(1))
        unit = match.group(2).lower()
        delta = {
            "second": timedelta(seconds=amount),
            "minute": timedelta(minutes=amount),
            "hour": timedelta(hours=amount),
            "day": timedelta(days=amount),
            "week": timedelta(weeks=amount),
            "month": timedelta(days=amount * 30),
            "year": timedelta(days=amount * 365),
        }.get(unit, timedelta(days=amount))
        dt = datetime.now(timezone.utc) - delta
        return dt.strftime("%Y-%m-%d"), dt.timestamp()

    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%m/%d/%Y",
    ):
        try:
            parsed = datetime.strptime(text[:26], fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.strftime("%Y-%m-%d"), parsed.timestamp()
        except ValueError:
            continue

    return text[:32], None
