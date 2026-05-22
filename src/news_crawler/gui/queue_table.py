"""Queue panel: card list with row selection for removal."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from news_crawler.gui.article_list import ArticleListWidget
from news_crawler.models import ArticleResult


class QueueTableWidget(QWidget):
    selection_changed = Signal()

    def __init__(self, ui_lang: str = "en", parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._list = ArticleListWidget(
            ui_lang,
            toggle_on_click=False,
            show_queue_badge=False,
        )
        self._list.set_empty_message_key("queue_empty")
        self._list.selection_changed.connect(self.selection_changed.emit)
        self._list.article_double_clicked.connect(self._open_url)
        layout.addWidget(self._list)

    def set_ui_language(self, ui_lang: str) -> None:
        self._list.set_ui_language(ui_lang)

    def set_articles(self, articles: list[ArticleResult]) -> None:
        self._list.set_articles(articles)

    def clear(self) -> None:
        self._list.clear()

    def row_count(self) -> int:
        return self._list.row_count()

    def selected_row(self) -> int:
        return self._list.selected_row()

    def article_at(self, row: int) -> ArticleResult | None:
        return self._list.article_at(row)

    def get_articles(self) -> list[ArticleResult]:
        return self._list.get_articles()

    @staticmethod
    def _open_url(article: ArticleResult) -> None:
        import webbrowser

        webbrowser.open(article.url)
