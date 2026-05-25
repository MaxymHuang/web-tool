"""Headless Playwright worker for frozen bundles (no Qt)."""

import sys
from pathlib import Path

from news_crawler.platform_support import configure_platform


def main() -> None:
    configure_platform()
    if len(sys.argv) < 3:
        print(
            "Usage: news-crawler-screenshot <url> <output.png> [locale]",
            file=sys.stderr,
        )
        sys.exit(2)
    from news_crawler.capture.screenshot import capture_url_to_file

    locale = sys.argv[3] if len(sys.argv) > 3 else None
    ok, err = capture_url_to_file(sys.argv[1], Path(sys.argv[2]), locale=locale)
    if not ok:
        print(err, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
