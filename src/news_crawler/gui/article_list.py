"""Card-style article list for scannable results and queue views."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from news_crawler.gui.styles import (
    QUEUED_BG,
    QUEUED_BORDER,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    meta_font,
    snippet_font,
    title_font,
)
from news_crawler.i18n import t
from news_crawler.models import ArticleResult

CARD_MIN_HEIGHT = 88
SNIPPET_MAX_CHARS = 220


class ArticleCardWidget(QWidget):
    """Single article row: title (primary), meta (secondary), snippet (tertiary)."""

    def __init__(
        self,
        article: ArticleResult,
        *,
        queued: bool,
        ui_lang: str,
        show_queue_badge: bool,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.article = article

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(12)

        if show_queue_badge:
            self._badge = QLabel()
            self._badge.setFixedWidth(28)
            self._badge.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
            root.addWidget(self._badge)
        else:
            self._badge = None

        body = QVBoxLayout()
        body.setSpacing(4)

        self._title = QLabel(article.title or "—")
        self._title.setFont(title_font())
        self._title.setWordWrap(True)
        self._title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        body.addWidget(self._title)

        meta_parts = [p for p in (article.media, article.published_at) if p]
        meta_text = " · ".join(meta_parts) if meta_parts else "—"
        self._meta = QLabel(meta_text)
        self._meta.setFont(meta_font())
        self._meta.setStyleSheet(f"color: {TEXT_SECONDARY};")
        body.addWidget(self._meta)

        snippet = (article.snippet or "").strip()
        if snippet:
            if len(snippet) > SNIPPET_MAX_CHARS:
                snippet = snippet[: SNIPPET_MAX_CHARS - 1].rstrip() + "…"
            self._snippet = QLabel(snippet)
            self._snippet.setFont(snippet_font())
            self._snippet.setWordWrap(True)
            self._snippet.setStyleSheet(f"color: {TEXT_MUTED};")
            body.addWidget(self._snippet)
        else:
            self._snippet = None

        body.addStretch()
        root.addLayout(body, stretch=1)

        self.setToolTip(article.url)
        self.set_queued(queued, ui_lang)

    def set_queued(self, queued: bool, ui_lang: str) -> None:
        if self._badge is not None:
            self._badge.setText("✓" if queued else "+")
            self._badge.setToolTip(
                t(ui_lang, "badge_queued") if queued else t(ui_lang, "badge_add")
            )
            color = QUEUED_BORDER if queued else TEXT_MUTED
            self._badge.setStyleSheet(
                f"color: {color}; font-size: 16px; font-weight: bold;"
            )

        if queued:
            self.setStyleSheet(
                f"background-color: {QUEUED_BG};"
                f"border-left: 3px solid {QUEUED_BORDER};"
            )
        else:
            self.setStyleSheet("background: transparent; border-left: 3px solid transparent;")


class ArticleListWidget(QWidget):
    """Scrollable list of article cards."""

    article_clicked = Signal(ArticleResult)
    article_double_clicked = Signal(ArticleResult)
    selection_changed = Signal()

    def __init__(
        self,
        ui_lang: str = "en",
        *,
        toggle_on_click: bool = False,
        show_queue_badge: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._ui_lang = ui_lang
        self._toggle_on_click = toggle_on_click
        self._show_queue_badge = show_queue_badge
        self._articles: list[ArticleResult] = []
        self._queued_urls: set[str] = set()
        self._cards: list[ArticleCardWidget] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._empty_label = QLabel()
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        self._empty_label.setStyleSheet(f"color: {TEXT_MUTED}; padding: 32px;")
        self._empty_label.hide()

        self._list = QListWidget()
        self._list.setSpacing(0)
        self._list.setUniformItemSizes(False)
        self._list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._list.setSelectionMode(
            QListWidget.SelectionMode.SingleSelection
            if not toggle_on_click
            else QListWidget.SelectionMode.NoSelection
        )
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        if not toggle_on_click:
            self._list.itemSelectionChanged.connect(self.selection_changed.emit)

        layout.addWidget(self._empty_label)
        layout.addWidget(self._list, stretch=1)

    def set_ui_language(self, ui_lang: str) -> None:
        self._ui_lang = ui_lang
        self._refresh_empty_text()

    def set_empty_message_key(self, key: str) -> None:
        self._empty_key = key
        self._refresh_empty_text()

    def _refresh_empty_text(self) -> None:
        key = getattr(self, "_empty_key", "results_empty")
        self._empty_label.setText(t(self._ui_lang, key))

    def set_queued_urls(self, urls: set[str]) -> None:
        self._queued_urls = urls
        for card in self._cards:
            card.set_queued(card.article.url in urls, self._ui_lang)

    def set_articles(self, articles: list[ArticleResult]) -> None:
        self._articles = list(articles)
        self._list.clear()
        self._cards.clear()

        for article in articles:
            queued = article.url in self._queued_urls
            card = ArticleCardWidget(
                article,
                queued=queued,
                ui_lang=self._ui_lang,
                show_queue_badge=self._show_queue_badge,
            )
            item = QListWidgetItem(self._list)
            hint = card.sizeHint()
            if hint.height() < CARD_MIN_HEIGHT:
                hint = QSize(hint.width(), CARD_MIN_HEIGHT)
            item.setSizeHint(hint)
            self._list.addItem(item)
            self._list.setItemWidget(item, card)
            self._cards.append(card)

        has_items = bool(articles)
        self._list.setVisible(has_items)
        self._empty_label.setVisible(not has_items)

    def clear(self) -> None:
        self._articles = []
        self._cards = []
        self._list.clear()
        self._list.setVisible(False)
        self._empty_label.setVisible(True)

    def row_count(self) -> int:
        return len(self._articles)

    def selected_row(self) -> int:
        row = self._list.currentRow()
        return row if row >= 0 else -1

    def article_at(self, row: int) -> ArticleResult | None:
        if 0 <= row < len(self._articles):
            return self._articles[row]
        return None

    def get_articles(self) -> list[ArticleResult]:
        return list(self._articles)

    def _article_for_item(self, item: QListWidgetItem) -> ArticleResult | None:
        row = self._list.row(item)
        return self.article_at(row)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        article = self._article_for_item(item)
        if article is None:
            return
        self.article_clicked.emit(article)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        article = self._article_for_item(item)
        if article is None:
            return
        self.article_double_clicked.emit(article)
