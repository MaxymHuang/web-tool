from dataclasses import dataclass


@dataclass
class ArticleResult:
    title: str
    url: str
    snippet: str
    media: str = ""
    score: float = 0.0
    selected: bool = True
    summary: str = ""
    screenshot_path: str = ""
