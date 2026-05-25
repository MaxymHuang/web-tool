import re
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from news_crawler.platform_support import (
    browser_locale,
    http_user_agent,
    playwright_launch_args,
    screenshot_subprocess_command,
    subprocess_run_kwargs,
)

NAV_TIMEOUT_MS = 45_000
RENDER_WAIT_MS = 2_000
SCREENSHOT_TIMEOUT_MS = 60_000
SUBPROCESS_TIMEOUT_SEC = 120


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    slug = re.sub(r"[\s_-]+", "-", slug.strip()).strip("-")
    return (slug[:max_len] if slug else "") or "page"


def capture_url_to_file(url: str, output_path: Path, locale: str | None = None) -> tuple[bool, str]:
    """Capture a full-page screenshot (must run in main process or subprocess)."""
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    page_locale = locale or browser_locale()

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=playwright_launch_args(),
            )
            context = browser.new_context(
                user_agent=http_user_agent(),
                viewport={"width": 1280, "height": 900},
                locale=page_locale,
            )
            page = context.new_page()
            try:
                loaded = False
                for wait_until in ("domcontentloaded", "load", "commit"):
                    try:
                        page.goto(url, wait_until=wait_until, timeout=NAV_TIMEOUT_MS)
                        loaded = True
                        break
                    except PlaywrightTimeout:
                        continue
                if not loaded:
                    page.goto(url, timeout=NAV_TIMEOUT_MS)

                page.wait_for_timeout(RENDER_WAIT_MS)
                page.screenshot(
                    path=str(output_path),
                    full_page=True,
                    timeout=SCREENSHOT_TIMEOUT_MS,
                )
                return True, ""
            finally:
                context.close()
                browser.close()
    except Exception as exc:
        if output_path.exists() and output_path.stat().st_size == 0:
            output_path.unlink(missing_ok=True)
        return False, str(exc)


def capture_url_subprocess(
    url: str,
    output_path: Path,
    locale: str | None = None,
) -> tuple[bool, str]:
    """Run Playwright in a child process (safe when called from a QThread)."""
    cmd = screenshot_subprocess_command(url, output_path, locale)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_TIMEOUT_SEC,
        check=False,
        **subprocess_run_kwargs(),
    )
    if result.returncode == 0:
        return True, ""
    err = (result.stderr or result.stdout or "Screenshot subprocess failed").strip()
    return False, err


class ScreenshotCapture:
    """Captures screenshots via subprocess (compatible with Qt worker threads)."""

    def __init__(self, locale: str | None = None) -> None:
        self._locale = locale

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def capture(self, url: str, output_path: Path) -> tuple[bool, str]:
        return capture_url_subprocess(url, output_path, locale=self._locale)


def _cli_main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python -m news_crawler.capture.screenshot <url> <output.png> [locale]")
        sys.exit(2)
    locale = sys.argv[3] if len(sys.argv) > 3 else None
    ok, err = capture_url_to_file(sys.argv[1], Path(sys.argv[2]), locale=locale)
    if not ok:
        print(err, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli_main()
