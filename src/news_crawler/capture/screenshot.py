import argparse
import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
import trafilatura
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from news_crawler.capture.adblock_strategy import (
    AdblockStrategy,
    DEFAULT_ADBLOCK_STRATEGY,
    normalize_adblock_strategy,
)
from news_crawler.platform_support import (
    browser_locale,
    http_user_agent,
    playwright_launch_args,
    screenshot_subprocess_batch_command,
    screenshot_subprocess_command,
    subprocess_run_kwargs,
)
from news_crawler.capture.page_shield import PageShield

NAV_TIMEOUT_MS = 45_000
RENDER_WAIT_MS = 2_000
SCREENSHOT_TIMEOUT_MS = 60_000
SUBPROCESS_TIMEOUT_SEC = 120
READER_TIMEOUT_SEC = 15.0


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    slug = re.sub(r"[\s_-]+", "-", slug.strip()).strip("-")
    return (slug[:max_len] if slug else "") or "page"


def capture_url_to_file(
    url: str,
    output_path: Path,
    locale: str | None = None,
    adblock_strategy: AdblockStrategy = DEFAULT_ADBLOCK_STRATEGY,
) -> tuple[bool, str]:
    """Capture a full-page screenshot (must run in main process or subprocess)."""
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    page_locale = locale or browser_locale()

    ok_list, err_list = capture_many_to_files(
        [(url, output_path)],
        locale=page_locale,
        adblock_strategy=adblock_strategy,
    )
    ok = bool(ok_list and ok_list[0])
    err = err_list[0] if err_list else ""
    if not ok and output_path.exists() and output_path.stat().st_size == 0:
        output_path.unlink(missing_ok=True)
    return ok, err


def capture_many_to_files(
    jobs: list[tuple[str, Path]],
    locale: str | None = None,
    adblock_strategy: AdblockStrategy = DEFAULT_ADBLOCK_STRATEGY,
) -> tuple[list[bool], list[str]]:
    if not jobs:
        return [], []
    page_locale = locale or browser_locale()
    strategy = normalize_adblock_strategy(adblock_strategy)
    if strategy == "reader_mode":
        return _capture_many_reader_mode(jobs, page_locale)

    ok_results: list[bool] = []
    err_results: list[str] = []
    shield = PageShield()
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
                bypass_csp=True,
            )
            try:
                shield.attach_to_context(context)
                for url, output_path in jobs:
                    output_path = output_path.resolve()
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    page = context.new_page()
                    try:
                        shield.prepare_page(page)
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
                        shield.apply_cosmetic(page, url)
                        page.wait_for_timeout(500)
                        page.screenshot(
                            path=str(output_path),
                            full_page=True,
                            timeout=SCREENSHOT_TIMEOUT_MS,
                        )
                        ok_results.append(True)
                        err_results.append("")
                    except Exception as exc:
                        if output_path.exists() and output_path.stat().st_size == 0:
                            output_path.unlink(missing_ok=True)
                        ok_results.append(False)
                        err_results.append(str(exc))
                    finally:
                        page.close()
            finally:
                context.close()
                browser.close()
    except Exception as exc:
        return [False] * len(jobs), [str(exc)] * len(jobs)
    return ok_results, err_results


def _capture_many_reader_mode(
    jobs: list[tuple[str, Path]],
    page_locale: str,
) -> tuple[list[bool], list[str]]:
    ok_results: list[bool] = []
    err_results: list[str] = []
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
                bypass_csp=True,
            )
            try:
                for url, output_path in jobs:
                    output_path = output_path.resolve()
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    page = context.new_page()
                    try:
                        reader_html = _build_reader_html(url)
                        page.set_content(reader_html, wait_until="domcontentloaded")
                        page.wait_for_timeout(300)
                        page.screenshot(
                            path=str(output_path),
                            full_page=True,
                            timeout=SCREENSHOT_TIMEOUT_MS,
                        )
                        ok_results.append(True)
                        err_results.append("")
                    except Exception as exc:
                        if output_path.exists() and output_path.stat().st_size == 0:
                            output_path.unlink(missing_ok=True)
                        ok_results.append(False)
                        err_results.append(str(exc))
                    finally:
                        page.close()
            finally:
                context.close()
                browser.close()
    except Exception as exc:
        return [False] * len(jobs), [str(exc)] * len(jobs)
    return ok_results, err_results


def _navigate(page, url: str) -> None:
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


def _build_reader_html(url: str) -> str:
    page_title = url
    body_text = ""
    with httpx.Client(
        timeout=READER_TIMEOUT_SEC,
        follow_redirects=True,
        headers={"User-Agent": http_user_agent()},
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        source_html = response.text
    metadata = trafilatura.extract_metadata(source_html)
    if metadata and metadata.title:
        page_title = metadata.title.strip()
    extracted = trafilatura.extract(source_html, url=url, include_comments=False) or ""
    body_text = re.sub(r"\s+", " ", extracted).strip()
    if not body_text:
        raise RuntimeError("Reader-mode extraction failed for this page.")

    paras = [p.strip() for p in re.split(r"\n\s*\n", extracted) if p.strip()]
    if not paras:
        paras = [body_text]
    para_html = "\n".join(
        f"<p>{html.escape(paragraph)}</p>" for paragraph in paras[:250]
    )
    title_html = html.escape(page_title)
    source_html = html.escape(url)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{title_html}</title>"
        "<style>"
        "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
        "line-height:1.7;color:#111;background:#fff;margin:0;padding:0;}"
        ".wrap{max-width:860px;margin:0 auto;padding:40px 28px;}"
        "h1{font-size:34px;line-height:1.2;margin:0 0 12px;}"
        ".src{color:#666;font-size:13px;margin:0 0 24px;word-break:break-all;}"
        "p{font-size:18px;margin:0 0 14px;}"
        "</style></head><body>"
        f"<main class='wrap'><h1>{title_html}</h1><div class='src'>{source_html}</div>"
        f"{para_html}</main></body></html>"
    )


def capture_url_subprocess(
    url: str,
    output_path: Path,
    locale: str | None = None,
    adblock_strategy: AdblockStrategy = DEFAULT_ADBLOCK_STRATEGY,
) -> tuple[bool, str]:
    """Run Playwright in a child process (safe when called from a QThread)."""
    cmd = screenshot_subprocess_command(
        url,
        output_path,
        locale,
        adblock_strategy=adblock_strategy,
    )
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


def capture_batch_subprocess(
    jobs: list[tuple[str, Path]],
    locale: str | None = None,
    adblock_strategy: AdblockStrategy = DEFAULT_ADBLOCK_STRATEGY,
) -> tuple[list[bool], list[str]]:
    if not jobs:
        return [], []
    payload = {
        "jobs": [{"url": url, "output_path": str(path.resolve())} for url, path in jobs],
        "locale": locale,
        "adblock_strategy": adblock_strategy,
    }
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as temp:
        json.dump(payload, temp)
        temp_path = Path(temp.name)
    try:
        cmd = screenshot_subprocess_batch_command(
            temp_path,
            locale,
            adblock_strategy=adblock_strategy,
        )
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(SUBPROCESS_TIMEOUT_SEC, len(jobs) * 60),
            check=False,
            **subprocess_run_kwargs(),
        )
        output = json.loads(result.stdout or "{}")
        raw_results = output.get("results", [])
        ok_results: list[bool] = []
        err_results: list[str] = []
        for index in range(len(jobs)):
            entry = raw_results[index] if index < len(raw_results) else {}
            ok_results.append(bool(entry.get("ok")))
            err_results.append(str(entry.get("error", "")))
        if result.returncode != 0 and not any(ok_results):
            err = (result.stderr or result.stdout or "Screenshot subprocess failed").strip()
            return [False] * len(jobs), [err] * len(jobs)
        return ok_results, err_results
    except Exception as exc:
        return [False] * len(jobs), [str(exc)] * len(jobs)
    finally:
        temp_path.unlink(missing_ok=True)


class ScreenshotCapture:
    """Captures screenshots via subprocess (compatible with Qt worker threads)."""

    def __init__(
        self,
        locale: str | None = None,
        adblock_strategy: AdblockStrategy = DEFAULT_ADBLOCK_STRATEGY,
    ) -> None:
        self._locale = locale
        self._adblock_strategy = normalize_adblock_strategy(adblock_strategy)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def capture(self, url: str, output_path: Path) -> tuple[bool, str]:
        return capture_url_subprocess(
            url,
            output_path,
            locale=self._locale,
            adblock_strategy=self._adblock_strategy,
        )

    def capture_many(self, jobs: list[tuple[str, Path]]) -> tuple[list[bool], list[str]]:
        return capture_batch_subprocess(
            jobs,
            locale=self._locale,
            adblock_strategy=self._adblock_strategy,
        )


def _load_manifest(
    manifest_path: Path,
) -> tuple[list[tuple[str, Path]], str | None, AdblockStrategy]:
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    jobs: list[tuple[str, Path]] = []
    for item in raw.get("jobs", []):
        url = str(item.get("url", "")).strip()
        output_path = str(item.get("output_path", "")).strip()
        if not url or not output_path:
            continue
        jobs.append((url, Path(output_path)))
    return (
        jobs,
        raw.get("locale"),
        normalize_adblock_strategy(raw.get("adblock_strategy")),
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture one or many screenshots.",
    )
    parser.add_argument("url", nargs="?", help="Single capture URL")
    parser.add_argument("output_path", nargs="?", help="Single capture output path")
    parser.add_argument("locale", nargs="?", help="Single capture locale override")
    parser.add_argument(
        "--locale",
        dest="locale_flag",
        help="Locale override for batch mode.",
    )
    parser.add_argument(
        "--batch-manifest",
        dest="batch_manifest",
        help="JSON file containing {jobs:[{url,output_path}], locale}.",
    )
    parser.add_argument(
        "--adblock-strategy",
        dest="adblock_strategy",
        default=DEFAULT_ADBLOCK_STRATEGY,
        choices=list((
            "layered_native",
            "reader_mode",
        )),
        help="Adblock strategy: layered_native|reader_mode.",
    )
    return parser.parse_args(argv)


def _cli_main(argv: list[str] | None = None) -> None:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if args.batch_manifest:
        jobs, manifest_locale, manifest_strategy = _load_manifest(Path(args.batch_manifest))
        locale = manifest_locale or args.locale_flag or args.locale
        adblock_strategy = normalize_adblock_strategy(
            manifest_strategy or args.adblock_strategy
        )
        ok_list, err_list = capture_many_to_files(
            jobs,
            locale=locale,
            adblock_strategy=adblock_strategy,
        )
        results = [
            {"ok": ok, "error": err}
            for ok, err in zip(ok_list, err_list, strict=False)
        ]
        print(json.dumps({"results": results}, ensure_ascii=True))
        if not all(ok_list):
            sys.exit(1)
        return

    if not args.url or not args.output_path:
        print("Usage: python -m news_crawler.capture.screenshot <url> <output.png> [locale]")
        print("   or: python -m news_crawler.capture.screenshot --batch-manifest manifest.json")
        sys.exit(2)

    strategy = normalize_adblock_strategy(args.adblock_strategy)
    ok, err = capture_url_to_file(
        args.url,
        Path(args.output_path),
        locale=args.locale,
        adblock_strategy=strategy,
    )
    if not ok:
        print(err, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli_main()
