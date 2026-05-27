"""Headless Playwright worker for frozen bundles (no Qt)."""

from news_crawler.platform_support import configure_platform


def main() -> None:
    configure_platform()
    from news_crawler.capture.screenshot import _cli_main

    _cli_main()


if __name__ == "__main__":
    main()
