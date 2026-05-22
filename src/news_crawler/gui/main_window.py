from copy import copy
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from news_crawler.gui.styles import TEXT_MUTED, TEXT_SECONDARY

from news_crawler.gui.queue_table import QueueTableWidget
from news_crawler.gui.results_table import ResultsTableWidget
from news_crawler.i18n import MARKET_IDS, MARKETS, UI_LANGUAGES, market_label, t
from news_crawler.models import ArticleResult
from news_crawler.platform_support import default_output_dir
from news_crawler.search.filters import TIMELIMIT_CHOICES, SearchFilters
from news_crawler.workers.process_worker import ProcessWorker
from news_crawler.workers.search_worker import SearchWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._ui_lang = "en"
        self._all_articles: list[ArticleResult] = []
        self._queue: list[ArticleResult] = []
        self._search_worker: SearchWorker | None = None
        self._process_worker: ProcessWorker | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self._search_group = QGroupBox()
        search_layout = QVBoxLayout(self._search_group)

        prompt_row = QHBoxLayout()
        self._prompt_label = QLabel()
        prompt_row.addWidget(self._prompt_label)
        self._prompt_input = QPlainTextEdit()
        self._prompt_input.setMaximumHeight(96)
        self._prompt_input.setMinimumHeight(56)
        prompt_row.addWidget(self._prompt_input, stretch=1)
        search_layout.addLayout(prompt_row)

        opts_row = QHBoxLayout()
        self._max_results_label = QLabel()
        opts_row.addWidget(self._max_results_label)
        self._max_results = QSpinBox()
        self._max_results.setRange(5, 30)
        self._max_results.setValue(15)
        opts_row.addWidget(self._max_results)

        self._market_label = QLabel()
        opts_row.addWidget(self._market_label)
        self._market_combo = QComboBox()
        for market_id in MARKET_IDS:
            self._market_combo.addItem("", market_id)
        self._market_combo.currentIndexChanged.connect(self._on_market_changed)
        opts_row.addWidget(self._market_combo)

        self._language_label = QLabel()
        opts_row.addWidget(self._language_label)
        self._language_combo = QComboBox()
        for lang_id in UI_LANGUAGES:
            self._language_combo.addItem("", lang_id)
        self._language_combo.currentIndexChanged.connect(self._on_language_changed)
        opts_row.addWidget(self._language_combo)

        self._filter_date_label = QLabel()
        opts_row.addWidget(self._filter_date_label)
        self._date_combo = QComboBox()
        for tl in TIMELIMIT_CHOICES:
            self._date_combo.addItem("", tl)
        opts_row.addWidget(self._date_combo)

        self._filter_news_label = QLabel()
        opts_row.addWidget(self._filter_news_label)
        self._news_pref_combo = QComboBox()
        self._news_pref_combo.addItem("", False)
        self._news_pref_combo.addItem("", True)
        opts_row.addWidget(self._news_pref_combo)

        opts_row.addStretch()

        self._search_btn = QPushButton()
        self._search_btn.setDefault(True)
        self._search_btn.clicked.connect(self._on_search)
        opts_row.addWidget(self._search_btn)

        search_layout.addLayout(opts_row)
        root.addWidget(self._search_group)

        self._tabs = QTabWidget()

        results_page = QWidget()
        results_layout = QVBoxLayout(results_page)
        results_layout.setContentsMargins(10, 10, 10, 10)
        results_layout.setSpacing(8)

        results_header = QVBoxLayout()
        results_header.setSpacing(4)
        self._results_count_label = QLabel()
        self._results_count_label.setStyleSheet("font-weight: 600; font-size: 14px;")
        results_header.addWidget(self._results_count_label)
        self._results_hint = QLabel()
        self._results_hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        self._results_hint.setWordWrap(True)
        results_header.addWidget(self._results_hint)
        results_layout.addLayout(results_header)

        self._results_table = ResultsTableWidget(ui_lang=self._ui_lang)
        self._results_table.article_toggle_requested.connect(self._on_toggle_queue)
        results_layout.addWidget(self._results_table, stretch=1)
        self._tabs.addTab(results_page, "")

        queue_page = QWidget()
        queue_outer = QVBoxLayout(queue_page)
        queue_outer.setContentsMargins(10, 10, 10, 10)
        queue_outer.setSpacing(0)

        queue_btn_row = QHBoxLayout()
        self._remove_queue_btn = QPushButton()
        self._remove_queue_btn.clicked.connect(self._on_remove_from_queue)
        self._remove_queue_btn.setEnabled(False)
        queue_btn_row.addWidget(self._remove_queue_btn)

        self._clear_queue_btn = QPushButton()
        self._clear_queue_btn.clicked.connect(self._on_clear_queue)
        self._clear_queue_btn.setEnabled(False)
        queue_btn_row.addWidget(self._clear_queue_btn)
        queue_btn_row.addStretch()
        queue_outer.addLayout(queue_btn_row)

        queue_splitter = QSplitter()
        queue_splitter.setOrientation(Qt.Orientation.Vertical)

        queue_list_host = QWidget()
        queue_list_layout = QVBoxLayout(queue_list_host)
        queue_list_layout.setContentsMargins(0, 8, 0, 0)
        self._queue_table = QueueTableWidget(ui_lang=self._ui_lang)
        self._queue_table.selection_changed.connect(self._update_queue_buttons)
        queue_list_layout.addWidget(self._queue_table)
        queue_splitter.addWidget(queue_list_host)

        self._export_group = QGroupBox()
        export_layout = QVBoxLayout(self._export_group)

        folder_row = QHBoxLayout()
        self._output_folder_label = QLabel()
        folder_row.addWidget(self._output_folder_label)
        self._output_dir = QLineEdit()
        self._output_dir.setText(str(default_output_dir()))
        folder_row.addWidget(self._output_dir, stretch=1)
        self._browse_btn = QPushButton()
        self._browse_btn.clicked.connect(self._browse_output)
        folder_row.addWidget(self._browse_btn)
        export_layout.addLayout(folder_row)

        action_row = QHBoxLayout()
        self._export_btn = QPushButton()
        self._export_btn.clicked.connect(self._on_export)
        self._export_btn.setEnabled(False)
        action_row.addWidget(self._export_btn)

        self._cancel_btn = QPushButton()
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._cancel_btn.setEnabled(False)
        action_row.addWidget(self._cancel_btn)
        action_row.addStretch()
        export_layout.addLayout(action_row)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        export_layout.addWidget(self._progress)

        self._status_label = QLabel()
        self._status_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self._status_label.setWordWrap(True)
        export_layout.addWidget(self._status_label)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(80)
        self._log.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        export_layout.addWidget(self._log)

        queue_splitter.addWidget(self._export_group)
        queue_splitter.setStretchFactor(0, 3)
        queue_splitter.setStretchFactor(1, 1)
        queue_outer.addWidget(queue_splitter, stretch=1)
        self._tabs.addTab(queue_page, "")

        root.addWidget(self._tabs, stretch=1)

        search_status = self.statusBar()
        search_status.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self._search_status_label = QLabel()
        search_status.addWidget(self._search_status_label, stretch=1)
        self._search_progress = QProgressBar()
        self._search_progress.setMaximumWidth(220)
        self._search_progress.setMinimumWidth(120)
        self._search_progress.setTextVisible(False)
        self._search_progress.setVisible(False)
        search_status.addPermanentWidget(self._search_progress)

        self._language_combo.setCurrentIndex(UI_LANGUAGES.index("en"))
        self._apply_ui_language()
        self._set_search_status(t(self._ui_lang, "status_initial"))

    def _queue_urls(self) -> set[str]:
        return {a.url for a in self._queue}

    def _refresh_queue_ui(self) -> None:
        self._queue_table.set_articles(self._queue)
        urls = self._queue_urls()
        self._results_table.set_queued_urls(urls)
        self._update_tab_labels()
        self._update_queue_state()

    def _update_tab_labels(self) -> None:
        lang = self._ui_lang
        self._tabs.setTabText(0, t(lang, "tab_results"))
        q = len(self._queue)
        self._tabs.setTabText(
            1,
            t(lang, "tab_queue_count", count=str(q)) if q else t(lang, "tab_queue"),
        )

    def _set_search_status(self, message: str) -> None:
        self._search_status_label.setText(message)

    def _update_results_header(self, count: int) -> None:
        self._results_count_label.setText(
            t(self._ui_lang, "results_count", count=str(count))
        )

    def _show_results(self, articles: list[ArticleResult]) -> None:
        self._all_articles = list(articles)
        self._results_table.set_articles(articles)
        self._results_table.set_queued_urls(self._queue_urls())
        self._update_results_header(len(articles))

    def _update_queue_state(self) -> None:
        count = len(self._queue)
        self._export_btn.setEnabled(count > 0 and self._process_worker is None)
        self._clear_queue_btn.setEnabled(count > 0 and self._process_worker is None)
        self._remove_queue_btn.setEnabled(
            count > 0
            and self._queue_table.selected_row() >= 0
            and self._process_worker is None
        )
        if count > 0:
            self._status_label.setText(
                t(self._ui_lang, "status_queued", count=str(count))
            )

    def _update_queue_buttons(self) -> None:
        has_selection = self._queue_table.selected_row() >= 0
        self._remove_queue_btn.setEnabled(
            len(self._queue) > 0
            and has_selection
            and self._process_worker is None
        )

    def _on_toggle_queue(self, article: ArticleResult) -> None:
        if self._process_worker is not None:
            return
        urls = self._queue_urls()
        if article.url in urls:
            self._queue = [a for a in self._queue if a.url != article.url]
        else:
            self._queue.append(copy(article))
        self._refresh_queue_ui()

    def _on_remove_from_queue(self) -> None:
        row = self._queue_table.selected_row()
        if row < 0 or row >= len(self._queue):
            return
        del self._queue[row]
        self._refresh_queue_ui()

    def _on_clear_queue(self) -> None:
        self._queue.clear()
        self._refresh_queue_ui()

    def _on_market_changed(self, _index: int) -> None:
        if self._process_worker is not None or self._search_worker is not None:
            return
        market_id = self._market_combo.currentData()
        if market_id in UI_LANGUAGES:
            lang_index = UI_LANGUAGES.index(market_id)
            if self._language_combo.currentIndex() != lang_index:
                self._language_combo.blockSignals(True)
                self._language_combo.setCurrentIndex(lang_index)
                self._language_combo.blockSignals(False)
                self._ui_lang = market_id
                self._apply_ui_language()

    def _on_language_changed(self, index: int) -> None:
        if index < 0:
            return
        self._ui_lang = self._language_combo.currentData()
        self._apply_ui_language()

    def _apply_ui_language(self) -> None:
        lang = self._ui_lang
        self.setWindowTitle(t(lang, "window_title"))
        self.resize(1000, 720)

        self._search_group.setTitle(t(lang, "search_group"))
        self._prompt_label.setText(t(lang, "prompt_label"))
        self._prompt_input.setPlaceholderText(t(lang, "prompt_placeholder"))
        self._max_results_label.setText(t(lang, "max_results"))
        self._market_label.setText(t(lang, "market_label"))
        self._language_label.setText(t(lang, "language_label"))
        self._search_btn.setText(t(lang, "search_btn"))

        self._filter_date_label.setText(t(lang, "filter_date_label"))
        date_keys = (
            "filter_date_any",
            "filter_date_day",
            "filter_date_week",
            "filter_date_month",
            "filter_date_year",
        )
        for i, key in enumerate(date_keys):
            self._date_combo.setItemText(i, t(lang, key))
        self._filter_news_label.setText(t(lang, "filter_news_label"))
        self._news_pref_combo.setItemText(0, t(lang, "filter_news_general"))
        self._news_pref_combo.setItemText(1, t(lang, "filter_news_prefer"))

        for i, market_id in enumerate(MARKET_IDS):
            self._market_combo.setItemText(i, market_label(lang, market_id))
        for i, ui_lang in enumerate(UI_LANGUAGES):
            self._language_combo.setItemText(i, t(lang, f"lang_{ui_lang}"))

        self._results_hint.setText(t(lang, "results_hint"))
        self._results_table.set_ui_language(lang)
        self._queue_table.set_ui_language(lang)
        self._update_tab_labels()
        self._update_results_header(self._results_table.row_count())

        self._remove_queue_btn.setText(t(lang, "remove_from_queue"))
        self._clear_queue_btn.setText(t(lang, "clear_queue"))
        self._export_group.setTitle(t(lang, "queue_group"))
        self._output_folder_label.setText(t(lang, "output_folder"))
        self._browse_btn.setText(t(lang, "browse_btn"))
        self._export_btn.setText(t(lang, "export_btn"))
        self._cancel_btn.setText(t(lang, "cancel_btn"))
        self._log.setPlaceholderText(t(lang, "log_placeholder"))

        if self._results_table.row_count() == 0:
            self._set_search_status(t(lang, "status_initial"))
        if len(self._queue) == 0:
            self._status_label.setText(t(lang, "export_status_idle"))
        self._update_queue_state()

    def _current_market_id(self) -> str:
        market_id = self._market_combo.currentData()
        return market_id if market_id in MARKETS else "en"

    def _build_filters(self) -> SearchFilters:
        return SearchFilters(
            timelimit=self._date_combo.currentData() or None,
            prefer_news=bool(self._news_pref_combo.currentData()),
        )

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, t(self._ui_lang, "browse_dialog")
        )
        if path:
            self._output_dir.setText(path)

    def _set_search_phase(self, searching: bool) -> None:
        self._search_btn.setEnabled(not searching)
        self._prompt_input.setEnabled(not searching)
        self._max_results.setEnabled(not searching)
        self._market_combo.setEnabled(not searching)
        self._date_combo.setEnabled(not searching)
        self._news_pref_combo.setEnabled(not searching)
        self._results_table.setEnabled(not searching)
        self._search_progress.setVisible(searching)
        if searching:
            self._search_progress.setRange(0, 0)

    def _set_export_phase(self, exporting: bool) -> None:
        self._search_btn.setEnabled(not exporting)
        self._export_btn.setEnabled(not exporting and len(self._queue) > 0)
        self._cancel_btn.setEnabled(exporting)
        self._results_table.setEnabled(not exporting)
        self._queue_table.setEnabled(not exporting)
        self._output_dir.setEnabled(not exporting)
        self._browse_btn.setEnabled(not exporting)
        self._remove_queue_btn.setEnabled(not exporting and len(self._queue) > 0)
        self._clear_queue_btn.setEnabled(not exporting and len(self._queue) > 0)

    def _on_search(self) -> None:
        prompt = self._prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(
                self,
                t(self._ui_lang, "warn_search_title"),
                t(self._ui_lang, "warn_search_prompt"),
            )
            return

        self._set_search_phase(True)
        market_name = market_label(self._ui_lang, self._current_market_id())
        self._set_search_status(
            t(self._ui_lang, "status_searching", market=market_name)
        )

        self._search_worker = SearchWorker(
            prompt,
            self._max_results.value(),
            self._current_market_id(),
            self._ui_lang,
            self._build_filters(),
            self,
        )
        self._search_worker.progress.connect(self._set_search_status)
        self._search_worker.finished_ok.connect(self._on_search_done)
        self._search_worker.finished_error.connect(self._on_search_error)
        self._search_worker.finished.connect(self._on_search_worker_finished)
        self._search_worker.start()

    def _on_search_worker_finished(self) -> None:
        self._search_worker = None
        self._set_search_phase(False)

    def _on_search_done(self, results: list) -> None:
        self._show_results(results)
        count = len(results)
        if count == 0:
            self._set_search_status(t(self._ui_lang, "err_no_results"))
        else:
            self._set_search_status(
                t(self._ui_lang, "status_found", count=str(count))
            )
        self._refresh_queue_ui()
        self._tabs.setCurrentIndex(0)

    def _on_search_error(self, message: str) -> None:
        QMessageBox.warning(self, t(self._ui_lang, "warn_search_failed"), message)
        self._set_search_status(message)

    def _on_export(self) -> None:
        if self._tabs.currentIndex() != 1:
            self._tabs.setCurrentIndex(1)

        output = Path(self._output_dir.text().strip())
        if not output:
            QMessageBox.warning(
                self,
                t(self._ui_lang, "warn_export_title"),
                t(self._ui_lang, "warn_export_folder"),
            )
            return

        queued = self._queue_table.get_articles()
        if not queued:
            QMessageBox.warning(
                self,
                t(self._ui_lang, "warn_export_title"),
                t(self._ui_lang, "warn_export_select"),
            )
            return

        self._log.clear()
        self._set_export_phase(True)
        self._progress.setVisible(True)
        self._progress.setRange(0, len(queued))
        self._progress.setValue(0)

        market = MARKETS.get(self._current_market_id(), MARKETS["en"])
        self._process_worker = ProcessWorker(
            queued,
            output,
            ui_lang=self._ui_lang,
            browser_locale=market.browser_locale,
            parent=self,
        )
        self._process_worker.progress.connect(self._on_process_progress)
        self._process_worker.log_message.connect(
            lambda msg: self._log.appendPlainText(msg)
        )
        self._process_worker.finished_ok.connect(self._on_export_done)
        self._process_worker.finished_error.connect(self._on_export_error)
        self._process_worker.finished_cancelled.connect(self._on_export_cancelled)
        self._process_worker.finished.connect(self._on_process_finished)
        self._process_worker.start()

    def _on_process_progress(self, current: int, total: int, message: str) -> None:
        self._progress.setMaximum(total)
        self._progress.setValue(current)
        self._status_label.setText(message)

    def _on_export_done(self, excel_path: str, screenshots_dir: str) -> None:
        count = len(self._queue)
        QMessageBox.information(
            self,
            t(self._ui_lang, "info_export_title"),
            t(
                self._ui_lang,
                "info_export_body",
                count=str(count),
                excel=excel_path,
                screenshots=screenshots_dir,
            ),
        )
        self._status_label.setText(t(self._ui_lang, "status_export_complete"))

    def _on_export_error(self, message: str) -> None:
        QMessageBox.critical(self, t(self._ui_lang, "warn_export_failed"), message)
        self._status_label.setText(message)

    def _on_export_cancelled(self) -> None:
        self._status_label.setText(t(self._ui_lang, "status_cancelled"))
        self._log.appendPlainText(t(self._ui_lang, "status_cancelled"))

    def _on_process_finished(self) -> None:
        self._process_worker = None
        self._progress.setVisible(False)
        self._set_export_phase(False)
        self._update_queue_state()

    def _on_cancel(self) -> None:
        if self._process_worker:
            self._process_worker.cancel()
            self._status_label.setText(t(self._ui_lang, "status_cancelling"))
