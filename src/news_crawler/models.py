from dataclasses import dataclass


@dataclass
class ArticleResult:
    title: str
    url: str
    snippet: str
    media: str = ""
    queued: bool = False
    summary: str = ""
    screenshot_path: str = ""
    market: str = ""
    published_at: str = ""
    published_ts: float | None = None
