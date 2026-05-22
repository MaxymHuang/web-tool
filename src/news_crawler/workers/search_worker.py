from PySide6.QtCore import QThread, Signal

from news_crawler.i18n import t
from news_crawler.models import ArticleResult
from news_crawler.search.ddg import search_news
from news_crawler.search.filters import SearchFilters


class SearchWorker(QThread):
    finished_ok = Signal(list)
    finished_error = Signal(str)
    progress = Signal(str)

    def __init__(
        self,
        prompt: str,
        max_results: int,
        market_id: str,
        ui_lang: str,
        filters: SearchFilters | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._prompt = prompt
        self._max_results = max_results
        self._market_id = market_id
        self._ui_lang = ui_lang
        self._filters = filters or SearchFilters()

    def run(self) -> None:
        try:
            market_name = t(self._ui_lang, f"market_{self._market_id}")
            self.progress.emit(
                t(self._ui_lang, "status_searching", market=market_name)
            )
            results: list[ArticleResult] = search_news(
                self._prompt,
                self._max_results,
                market_id=self._market_id,
                filters=self._filters,
            )
            self.finished_ok.emit(results)
        except Exception as exc:
            self.finished_error.emit(str(exc))
