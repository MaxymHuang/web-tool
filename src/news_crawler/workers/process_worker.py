import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from news_crawler.capture.screenshot import ScreenshotCapture
from news_crawler.export.excel import export_to_excel
from news_crawler.models import ArticleResult


class ProcessWorker(QThread):
    progress = Signal(int, int, str)
    log_message = Signal(str)
    finished_ok = Signal(str, str)
    finished_error = Signal(str)
    finished_cancelled = Signal()

    def __init__(
        self,
        articles: list[ArticleResult],
        output_dir: Path,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._articles = articles
        self._output_dir = output_dir
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        selected = [a for a in self._articles if a.selected]
        if not selected:
            self.finished_error.emit("No articles selected for export.")
            return

        screenshots_dir = self._output_dir / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        total = len(selected)
        capture = ScreenshotCapture()

        try:
            capture.start()
            for index, article in enumerate(selected, start=1):
                if self._cancelled:
                    self.finished_cancelled.emit()
                    return

                self.progress.emit(
                    index,
                    total,
                    f"Processing ({index}/{total}): {article.title[:60]}...",
                )

                filename = f"{index:03d}.png"
                shot_path = screenshots_dir / filename
                ok, err = capture.capture(article.url, shot_path)
                if ok:
                    article.screenshot_path = str(shot_path)
                else:
                    self.log_message.emit(
                        f"Screenshot failed: {article.url}"
                        + (f" — {err}" if err else "")
                    )

                if index < total:
                    time.sleep(1)

            if self._cancelled:
                self.finished_cancelled.emit()
                return

            self.progress.emit(total, total, "Writing Excel file...")
            excel_path = export_to_excel(selected, self._output_dir)
            self.finished_ok.emit(str(excel_path), str(screenshots_dir))
        except Exception as exc:
            self.finished_error.emit(str(exc))
        finally:
            capture.stop()
