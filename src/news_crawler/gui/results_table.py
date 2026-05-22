from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from news_crawler.models import ArticleResult

COL_CHECK = 0
COL_MEDIA = 1
COL_TITLE = 2
COL_URL = 3
COL_SNIPPET = 4
COL_SCORE = 5


class ResultsTableWidget(QWidget):
    selection_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._articles: list[ArticleResult] = []
        self._updating = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["", "メディア", "揭載タイトル", "URL", "Snippet", "Score"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            COL_MEDIA, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            COL_TITLE, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            COL_URL, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            COL_SNIPPET, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            COL_CHECK, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            COL_SCORE, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.cellChanged.connect(self._on_cell_changed)
        self._table.doubleClicked.connect(self._on_double_click)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self._table)

    def set_articles(self, articles: list[ArticleResult]) -> None:
        self._articles = articles
        self._updating = True
        self._table.setRowCount(len(articles))

        for row, article in enumerate(articles):
            check = QCheckBox()
            check.setChecked(article.selected)
            check.stateChanged.connect(
                lambda _state, r=row: self._on_check_changed(r)
            )
            wrapper = QWidget()
            check_layout = QHBoxLayout(wrapper)
            check_layout.addWidget(check)
            check_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            check_layout.setContentsMargins(0, 0, 0, 0)
            self._table.setCellWidget(row, COL_CHECK, wrapper)

            media_item = QTableWidgetItem(article.media)
            title_item = QTableWidgetItem(article.title)
            url_item = QTableWidgetItem(article.url)
            snippet_item = QTableWidgetItem(article.snippet[:200])
            score_item = QTableWidgetItem(f"{article.score:.0f}")

            for item in (media_item, title_item, url_item, snippet_item, score_item):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self._table.setItem(row, COL_MEDIA, media_item)
            self._table.setItem(row, COL_TITLE, title_item)
            self._table.setItem(row, COL_URL, url_item)
            self._table.setItem(row, COL_SNIPPET, snippet_item)
            self._table.setItem(row, COL_SCORE, score_item)

        self._updating = False
        self.selection_changed.emit()

    def clear(self) -> None:
        self._articles = []
        self._table.setRowCount(0)
        self.selection_changed.emit()

    def get_articles(self) -> list[ArticleResult]:
        self._sync_from_table()
        return self._articles

    def row_count(self) -> int:
        return self._table.rowCount()

    def selected_count(self) -> int:
        self._sync_from_table()
        return sum(1 for a in self._articles if a.selected)

    def set_all_selected(self, selected: bool) -> None:
        self._updating = True
        for row in range(self._table.rowCount()):
            wrapper = self._table.cellWidget(row, COL_CHECK)
            if wrapper:
                check = wrapper.findChild(QCheckBox)
                if check:
                    check.setChecked(selected)
            if row < len(self._articles):
                self._articles[row].selected = selected
        self._updating = False
        self.selection_changed.emit()

    def invert_selection(self) -> None:
        self._updating = True
        for row in range(self._table.rowCount()):
            wrapper = self._table.cellWidget(row, COL_CHECK)
            if wrapper:
                check = wrapper.findChild(QCheckBox)
                if check:
                    check.setChecked(not check.isChecked())
            if row < len(self._articles):
                self._articles[row].selected = not self._articles[row].selected
        self._updating = False
        self.selection_changed.emit()

    def _sync_from_table(self) -> None:
        for row in range(self._table.rowCount()):
            if row >= len(self._articles):
                break
            wrapper = self._table.cellWidget(row, COL_CHECK)
            if wrapper:
                check = wrapper.findChild(QCheckBox)
                if check:
                    self._articles[row].selected = check.isChecked()

    def _on_check_changed(self, row: int) -> None:
        if self._updating or row >= len(self._articles):
            return
        wrapper = self._table.cellWidget(row, COL_CHECK)
        if wrapper:
            check = wrapper.findChild(QCheckBox)
            if check:
                self._articles[row].selected = check.isChecked()
        self.selection_changed.emit()

    def _on_cell_changed(self, _row: int, _col: int) -> None:
        if not self._updating:
            self.selection_changed.emit()

    def _on_double_click(self, index) -> None:
        row = index.row()
        if row < len(self._articles):
            import webbrowser

            webbrowser.open(self._articles[row].url)

    def _show_context_menu(self, pos) -> None:
        index = self._table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        if row >= len(self._articles):
            return

        menu = self._table.createStandardContextMenu()
        open_action = QAction("Open URL in browser", self)
        open_action.triggered.connect(
            lambda: __import__("webbrowser").open(self._articles[row].url)
        )
        menu.addAction(open_action)
        menu.exec(self._table.viewport().mapToGlobal(pos))
