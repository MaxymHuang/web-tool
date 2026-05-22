from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from news_crawler.gui.results_table import ResultsTableWidget
from news_crawler.platform_support import default_output_dir
from news_crawler.workers.process_worker import ProcessWorker
from news_crawler.workers.search_worker import SearchWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("News Crawler Tool")
        self.resize(1000, 720)

        self._search_worker: SearchWorker | None = None
        self._process_worker: ProcessWorker | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        search_group = QGroupBox("Search")
        search_layout = QVBoxLayout(search_group)

        prompt_row = QHBoxLayout()
        prompt_row.addWidget(QLabel("Prompt:"))
        self._prompt_input = QPlainTextEdit()
        self._prompt_input.setPlaceholderText("Enter your news search prompt...")
        self._prompt_input.setMaximumHeight(80)
        prompt_row.addWidget(self._prompt_input, stretch=1)
        search_layout.addLayout(prompt_row)

        opts_row = QHBoxLayout()
        opts_row.addWidget(QLabel("Max results:"))
        self._max_results = QSpinBox()
        self._max_results.setRange(5, 30)
        self._max_results.setValue(15)
        opts_row.addWidget(self._max_results)
        opts_row.addStretch()

        self._search_btn = QPushButton("Search")
        self._search_btn.clicked.connect(self._on_search)
        opts_row.addWidget(self._search_btn)

        self._new_search_btn = QPushButton("New Search")
        self._new_search_btn.clicked.connect(self._on_new_search)
        self._new_search_btn.setEnabled(False)
        opts_row.addWidget(self._new_search_btn)

        search_layout.addLayout(opts_row)
        root.addWidget(search_group)

        results_group = QGroupBox("Results — select sources to export")
        results_layout = QVBoxLayout(results_group)

        self._results_table = ResultsTableWidget()
        self._results_table.selection_changed.connect(self._update_export_state)

        sel_row = QHBoxLayout()
        self._select_all_btn = QPushButton("Select all")
        self._select_all_btn.clicked.connect(
            lambda: self._results_table.set_all_selected(True)
        )
        self._select_all_btn.setEnabled(False)
        sel_row.addWidget(self._select_all_btn)

        self._select_none_btn = QPushButton("Select none")
        self._select_none_btn.clicked.connect(
            lambda: self._results_table.set_all_selected(False)
        )
        self._select_none_btn.setEnabled(False)
        sel_row.addWidget(self._select_none_btn)

        self._invert_btn = QPushButton("Invert selection")
        self._invert_btn.clicked.connect(self._results_table.invert_selection)
        self._invert_btn.setEnabled(False)
        sel_row.addWidget(self._invert_btn)
        sel_row.addStretch()
        results_layout.addLayout(sel_row)

        results_layout.addWidget(self._results_table)
        root.addWidget(results_group, stretch=1)

        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group)

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Output folder:"))
        self._output_dir = QLineEdit()
        self._output_dir.setText(str(default_output_dir()))
        folder_row.addWidget(self._output_dir, stretch=1)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_output)
        folder_row.addWidget(browse_btn)
        export_layout.addLayout(folder_row)

        action_row = QHBoxLayout()
        self._export_btn = QPushButton("Export Selected")
        self._export_btn.clicked.connect(self._on_export)
        self._export_btn.setEnabled(False)
        action_row.addWidget(self._export_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._cancel_btn.setEnabled(False)
        action_row.addWidget(self._cancel_btn)
        action_row.addStretch()
        export_layout.addLayout(action_row)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        export_layout.addWidget(self._progress)

        self._status_label = QLabel("Enter a prompt and click Search.")
        export_layout.addWidget(self._status_label)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(100)
        self._log.setPlaceholderText("Log messages...")
        export_layout.addWidget(self._log)

        root.addWidget(export_group)

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select output folder")
        if path:
            self._output_dir.setText(path)

    def _set_search_phase(self, searching: bool) -> None:
        self._search_btn.setEnabled(not searching)
        self._prompt_input.setEnabled(not searching)
        self._max_results.setEnabled(not searching)
        if searching:
            self._progress.setVisible(True)
            self._progress.setRange(0, 0)

    def _set_export_phase(self, exporting: bool) -> None:
        self._search_btn.setEnabled(not exporting)
        self._export_btn.setEnabled(not exporting and self._results_table.selected_count() > 0)
        self._cancel_btn.setEnabled(exporting)
        has_rows = self._results_table.row_count() > 0
        self._select_all_btn.setEnabled(not exporting and has_rows)
        self._select_none_btn.setEnabled(not exporting and has_rows)
        self._invert_btn.setEnabled(not exporting and has_rows)
        self._results_table.setEnabled(not exporting)
        self._output_dir.setEnabled(not exporting)
        self._new_search_btn.setEnabled(not exporting)

    def _update_export_state(self) -> None:
        count = self._results_table.selected_count()
        total = self._results_table.row_count()
        self._export_btn.setEnabled(count > 0 and self._process_worker is None)
        if total > 0:
            self._status_label.setText(f"{count} of {total} sources selected for export.")

    def _on_search(self) -> None:
        prompt = self._prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "Search", "Please enter a search prompt.")
            return

        self._log.clear()
        self._set_search_phase(True)
        self._status_label.setText("Searching...")

        self._search_worker = SearchWorker(prompt, self._max_results.value(), self)
        self._search_worker.progress.connect(self._status_label.setText)
        self._search_worker.finished_ok.connect(self._on_search_done)
        self._search_worker.finished_error.connect(self._on_search_error)
        self._search_worker.finished.connect(lambda: self._set_search_phase(False))
        self._search_worker.start()

    def _on_search_done(self, results: list) -> None:
        self._progress.setVisible(False)
        self._progress.setRange(0, 100)
        self._results_table.set_articles(results)
        self._select_all_btn.setEnabled(True)
        self._select_none_btn.setEnabled(True)
        self._invert_btn.setEnabled(True)
        self._new_search_btn.setEnabled(True)
        self._status_label.setText(
            f"Found {len(results)} sources. Review and select, then Export Selected."
        )
        self._update_export_state()

    def _on_search_error(self, message: str) -> None:
        self._progress.setVisible(False)
        self._progress.setRange(0, 100)
        QMessageBox.warning(self, "Search failed", message)
        self._status_label.setText(message)

    def _on_new_search(self) -> None:
        self._results_table.clear()
        self._select_all_btn.setEnabled(False)
        self._select_none_btn.setEnabled(False)
        self._invert_btn.setEnabled(False)
        self._export_btn.setEnabled(False)
        self._new_search_btn.setEnabled(False)
        self._status_label.setText("Enter a prompt and click Search.")
        self._prompt_input.setFocus()

    def _on_export(self) -> None:
        output = Path(self._output_dir.text().strip())
        if not output:
            QMessageBox.warning(self, "Export", "Please choose an output folder.")
            return

        articles = self._results_table.get_articles()
        selected = [a for a in articles if a.selected]
        if not selected:
            QMessageBox.warning(self, "Export", "Select at least one source to export.")
            return

        self._log.clear()
        self._set_export_phase(True)
        self._progress.setVisible(True)
        self._progress.setRange(0, len(selected))
        self._progress.setValue(0)

        self._process_worker = ProcessWorker(articles, output, self)
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
        selected = self._results_table.selected_count()
        QMessageBox.information(
            self,
            "Export complete",
            f"Exported {selected} articles.\n\n"
            f"Excel: {excel_path}\n"
            f"Screenshots: {screenshots_dir}",
        )
        self._status_label.setText("Export complete.")

    def _on_export_error(self, message: str) -> None:
        QMessageBox.critical(self, "Export failed", message)
        self._status_label.setText(message)

    def _on_export_cancelled(self) -> None:
        self._status_label.setText("Export cancelled.")
        self._log.appendPlainText("Export cancelled by user.")

    def _on_process_finished(self) -> None:
        self._process_worker = None
        self._progress.setVisible(False)
        self._set_export_phase(False)
        self._update_export_state()

    def _on_cancel(self) -> None:
        if self._process_worker:
            self._process_worker.cancel()
            self._status_label.setText("Cancelling after current article...")
