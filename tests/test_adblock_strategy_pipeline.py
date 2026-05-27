import json
from pathlib import Path

from news_crawler.capture.adblock_strategy import (
    DEFAULT_ADBLOCK_STRATEGY,
    normalize_adblock_strategy,
)
from news_crawler.capture.screenshot import _build_reader_html, _load_manifest
from news_crawler.models import ArticleResult
from news_crawler.platform_support import (
    screenshot_subprocess_batch_command,
    screenshot_subprocess_command,
)
from news_crawler.workers.process_worker import ProcessWorker


def test_normalize_adblock_strategy_defaults_to_layered_native():
    assert normalize_adblock_strategy(None) == DEFAULT_ADBLOCK_STRATEGY
    assert normalize_adblock_strategy("invalid") == DEFAULT_ADBLOCK_STRATEGY
    assert normalize_adblock_strategy("reader_mode") == "reader_mode"


def test_load_manifest_reads_adblock_strategy(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    payload = {
        "jobs": [
            {"url": "https://example.com", "output_path": str(tmp_path / "1.png")},
        ],
        "locale": "en-US",
        "adblock_strategy": "reader_mode",
    }
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    jobs, locale, strategy = _load_manifest(manifest_path)
    assert jobs == [("https://example.com", tmp_path / "1.png")]
    assert locale == "en-US"
    assert strategy == "reader_mode"


def test_subprocess_commands_include_adblock_strategy(tmp_path: Path):
    cmd_single = screenshot_subprocess_command(
        "https://example.com",
        tmp_path / "shot.png",
        locale="ja-JP",
        adblock_strategy="reader_mode",
    )
    assert "--adblock-strategy" in cmd_single
    assert cmd_single[-1] == "reader_mode"

    cmd_batch = screenshot_subprocess_batch_command(
        tmp_path / "manifest.json",
        locale="en-US",
        adblock_strategy="reader_mode",
    )
    assert "--adblock-strategy" in cmd_batch
    assert cmd_batch[-1] == "reader_mode"


def test_process_worker_forwards_adblock_strategy(monkeypatch, tmp_path: Path):
    captured: dict[str, str] = {}

    class _FakeCapture:
        def __init__(self, locale=None, adblock_strategy=None):
            captured["locale"] = locale
            captured["strategy"] = adblock_strategy

        def start(self):
            return None

        def stop(self):
            return None

        def capture_many(self, jobs):
            return [True for _ in jobs], ["" for _ in jobs]

    monkeypatch.setattr("news_crawler.workers.process_worker.ScreenshotCapture", _FakeCapture)
    monkeypatch.setattr(
        "news_crawler.workers.process_worker.export_to_excel",
        lambda articles, output_dir, ui_lang="en": output_dir / "result.xlsx",
    )

    article = ArticleResult(
        title="title",
        url="https://example.com",
        snippet="snippet",
    )
    worker = ProcessWorker(
        [article],
        tmp_path,
        ui_lang="en",
        browser_locale="en-US",
        adblock_strategy="reader_mode",
    )
    worker.run()
    assert captured["locale"] == "en-US"
    assert captured["strategy"] == "reader_mode"
    assert article.screenshot_path.endswith("001.png")


def test_build_reader_html_uses_extracted_content(monkeypatch):
    class _Response:
        text = "<html><head><title>ignored</title></head><body>raw</body></html>"

        def raise_for_status(self):
            return None

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, _url):
            return _Response()

    class _Meta:
        title = "Reader Title"

    monkeypatch.setattr("news_crawler.capture.screenshot.httpx.Client", lambda **_: _Client())
    monkeypatch.setattr(
        "news_crawler.capture.screenshot.trafilatura.extract_metadata",
        lambda _html: _Meta(),
    )
    monkeypatch.setattr(
        "news_crawler.capture.screenshot.trafilatura.extract",
        lambda _html, url=None, include_comments=False: "para one\n\npara two",
    )
    rendered = _build_reader_html("https://example.com/article")
    assert "Reader Title" in rendered
    assert "<p>para one</p>" in rendered
    assert "<p>para two</p>" in rendered
