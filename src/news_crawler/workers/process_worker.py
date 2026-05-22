import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from news_crawler.capture.screenshot import ScreenshotCapture
from news_crawler.export.excel import export_to_excel
from news_crawler.i18n import t
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
        ui_lang: str = "en",
        browser_locale: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._articles = articles
        self._output_dir = output_dir
        self._ui_lang = ui_lang
        self._browser_locale = browser_locale
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        if not self._articles:
            self.finished_error.emit("No articles in queue for export.")
            return

        screenshots_dir = self._output_dir / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        total = len(self._articles)
        capture = ScreenshotCapture(locale=self._browser_locale)

        try:
            capture.start()
            for index, article in enumerate(self._articles, start=1):
                if self._cancelled:
                    self.finished_cancelled.emit()
                    return

                title_preview = article.title[:60]
                self.progress.emit(
                    index,
                    total,
                    t(
                        self._ui_lang,
                        "processing",
                        current=str(index),
                        total=str(total),
                        title=title_preview,
                    ),
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

            self.progress.emit(total, total, t(self._ui_lang, "writing_excel"))
            excel_path = export_to_excel(
                self._articles, self._output_dir, ui_lang=self._ui_lang
            )
            self.finished_ok.emit(str(excel_path), str(screenshots_dir))
        except Exception as exc:
            self.finished_error.emit(str(exc))
        finally:
            capture.stop()
