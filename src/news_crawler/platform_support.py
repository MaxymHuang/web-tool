"""Cross-platform helpers (Windows, macOS, Linux)."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path


def configure_platform() -> None:
    """Apply OS-specific settings before Qt / Playwright start."""
    system = platform.system()
    if system == "Darwin":
        os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")
    if sys.platform == "win32":
        os.environ.setdefault("PYTHONUTF8", "1")


def default_output_dir() -> Path:
    return Path.home() / "news_crawler_output"


def http_user_agent() -> str:
    system = platform.system()
    if system == "Darwin":
        return (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    if system == "Windows":
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    return (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )


def playwright_launch_args() -> list[str]:
    """Extra Chromium flags per OS (Linux CI/docker often needs --no-sandbox)."""
    if sys.platform.startswith("linux"):
        return ["--no-sandbox", "--disable-dev-shm-usage"]
    return []


def subprocess_run_kwargs() -> dict:
    """Extra subprocess.run() options (e.g. hide console on Windows)."""
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def browser_locale() -> str:
    import locale

    try:
        code = locale.getlocale()[0]
        if code:
            return code.replace("_", "-")
    except Exception:
        pass
    return "en-US"
