from PySide6.QtCore import QThread, Signal

from news_crawler.models import ArticleResult
from news_crawler.search.ddg import search_news


class SearchWorker(QThread):
    finished_ok = Signal(list)
    finished_error = Signal(str)
    progress = Signal(str)

    def __init__(self, prompt: str, max_results: int, parent=None) -> None:
        super().__init__(parent)
        self._prompt = prompt
        self._max_results = max_results

    def run(self) -> None:
        try:
            self.progress.emit("Searching DuckDuckGo News...")
            results: list[ArticleResult] = search_news(self._prompt, self._max_results)
            if not results:
                self.finished_error.emit(
                    "No matching news found. Try a different prompt or lower the relevance threshold."
                )
                return
            self.finished_ok.emit(results)
        except Exception as exc:
            self.finished_error.emit(str(exc))
