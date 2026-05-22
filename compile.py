#!/usr/bin/env python3
"""Build a native News Crawler executable for the current OS (Windows, macOS, Linux)."""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENTRY = ROOT / "src" / "news_crawler" / "main.py"
SRC = ROOT / "src"
DEFAULT_NAME = "news-crawler"
MIN_PYTHON = (3, 11)

HIDDEN_IMPORTS = [
    "news_crawler",
    "news_crawler.gui.main_window",
    "news_crawler.gui.styles",
    "news_crawler.workers.search_worker",
    "news_crawler.workers.process_worker",
    "news_crawler.search.ddg",
    "news_crawler.capture.screenshot",
    "news_crawler.export.excel",
    "news_crawler.extract.article",
    "ddgs",
    "ddgs.exceptions",
    "trafilatura",
    "openpyxl",
    "playwright",
    "playwright.sync_api",
    "httpx",
]


def detect_os() -> str:
    """Return platform.system(): Windows, Darwin, or Linux."""
    return platform.system()


def os_label(system: str) -> str:
    if system == "Windows":
        return "Windows"
    if system == "Darwin":
        return "macOS"
    if system == "Linux":
        return "Linux"
    return system


def artifact_hint(system: str, name: str, onedir: bool) -> str:
    dist = ROOT / "dist"
    if system == "Darwin":
        return str(dist / f"{name}.app")
    if onedir:
        suffix = ".exe" if system == "Windows" else ""
        return str(dist / name / f"{name}{suffix}")
    suffix = ".exe" if system == "Windows" else ""
    return str(dist / f"{name}{suffix}")


def require_uv() -> str:
    uv = shutil.which("uv")
    if not uv:
        print("error: uv is not installed or not on PATH", file=sys.stderr)
        print("  https://docs.astral.sh/uv/", file=sys.stderr)
        sys.exit(1)
    return uv


def validate_project() -> None:
    if not ENTRY.is_file():
        print(f"error: entry script not found: {ENTRY}", file=sys.stderr)
        sys.exit(1)
    if sys.version_info < MIN_PYTHON:
        ver = ".".join(map(str, MIN_PYTHON))
        print(f"error: Python {ver}+ required (got {sys.version.split()[0]})", file=sys.stderr)
        sys.exit(1)


def pyinstaller_argv(args: argparse.Namespace, system: str) -> list[str]:
    name = args.name
    distpath = (ROOT / args.output_dir).resolve()
    workpath = (ROOT / "build" / name).resolve()
    specpath = ROOT / "build"

    cmd: list[str] = [
        "uv",
        "run",
        "pyinstaller",
        "--noconfirm",
        str(ENTRY),
        "--name",
        name,
        "--paths",
        str(SRC),
        "--distpath",
        str(distpath),
        "--workpath",
        str(workpath),
        "--specpath",
        str(specpath),
    ]

    if args.clean:
        cmd.append("--clean")

    if args.onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    # GUI app: no console window
    if system in ("Windows", "Darwin", "Linux"):
        cmd.append("--windowed")

    for mod in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", mod])

    cmd.extend(["--collect-all", "PySide6"])

    if args.extra:
        cmd.extend(args.extra)

    return cmd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compile News Crawler into a native executable for this OS.",
    )
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Single-file bundle (default: one-folder / onedir)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean PyInstaller cache before building",
    )
    parser.add_argument(
        "--name",
        default=DEFAULT_NAME,
        help=f"Executable / app name (default: {DEFAULT_NAME})",
    )
    parser.add_argument(
        "--output-dir",
        default="dist",
        help="Output directory relative to project root (default: dist)",
    )
    parser.add_argument(
        "extra",
        nargs=argparse.REMAINDER,
        help="Extra arguments passed to pyinstaller (prefix with --)",
    )
    return parser.parse_args()


def run_build(cmd: list[str]) -> None:
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        sys.exit(result.returncode)


def print_post_build(system: str, name: str, onedir: bool) -> None:
    artifact = artifact_hint(system, name, onedir)
    print()
    print(f"Build finished ({os_label(system)}).")
    print(f"  Artifact: {artifact}")
    print()
    print("Playwright Chromium is not bundled. On the target machine, install browsers once:")
    print("  uv run playwright install chromium")
    print("  (Linux: uv run playwright install-deps chromium if Chromium fails to start)")
    print()
    if system == "Darwin":
        print("If macOS blocks the app, allow it in System Settings → Privacy & Security.")


def main() -> None:
    args = parse_args()
    system = detect_os()

    if system not in ("Windows", "Darwin", "Linux"):
        print(f"error: unsupported OS: {system}", file=sys.stderr)
        sys.exit(1)

    require_uv()
    validate_project()

    print(f"Target OS: {os_label(system)} ({system})")
    print(f"Project:   {ROOT}")
    print(f"Entry:     {ENTRY}")
    print(f"Mode:      {'onefile' if args.onefile else 'onedir'}")
    print()

    cmd = pyinstaller_argv(args, system)
    run_build(cmd)
    print_post_build(system, args.name, not args.onefile)


if __name__ == "__main__":
    main()
