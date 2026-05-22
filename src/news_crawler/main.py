import sys

from PySide6.QtWidgets import QApplication

from news_crawler.gui.main_window import MainWindow
from news_crawler.gui.styles import apply_app_style
from news_crawler.platform_support import configure_platform


def main() -> None:
    configure_platform()
    app = QApplication(sys.argv)
    app.setApplicationName("News Crawler Tool")
    apply_app_style(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
