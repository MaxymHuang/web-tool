#!/usr/bin/env python3
"""Build a native News Crawler executable for the current OS (Windows, macOS, Linux)."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENTRY = ROOT / "src" / "news_crawler" / "main.py"
SCREENSHOT_ENTRY = ROOT / "src" / "news_crawler" / "capture" / "screenshot_worker.py"
SRC = ROOT / "src"
FILTER_LISTS_DIR = SRC / "news_crawler" / "capture" / "filter_lists"
DEFAULT_NAME = "news-crawler"
SCREENSHOT_SUFFIX = "-screenshot"
PLAYWRIGHT_STAGING = ROOT / "build" / "playwright-browsers"
BROWSERS_RESOURCE = "ms-playwright"
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
    "adblock",
    "playwright_cookie_blocker",
]

WORKER_HIDDEN_IMPORTS = [
    "news_crawler.capture.screenshot",
    "playwright",
    "playwright.sync_api",
    "adblock",
    "playwright_cookie_blocker",
]


def screenshot_worker_name(main_name: str) -> str:
    return f"{main_name}{SCREENSHOT_SUFFIX}"


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
    if not SCREENSHOT_ENTRY.is_file():
        print(f"error: screenshot worker not found: {SCREENSHOT_ENTRY}", file=sys.stderr)
        sys.exit(1)
    if sys.version_info < MIN_PYTHON:
        ver = ".".join(map(str, MIN_PYTHON))
        print(f"error: Python {ver}+ required (got {sys.version.split()[0]})", file=sys.stderr)
        sys.exit(1)


def pyinstaller_argv(
    *,
    entry: Path,
    name: str,
    distpath: Path,
    workpath: Path,
    specpath: Path,
    onefile: bool,
    onedir: bool,
    windowed: bool,
    hidden_imports: list[str],
    collect_pyside6: bool,
    clean: bool,
    extra: list[str],
) -> list[str]:
    cmd: list[str] = [
        "uv",
        "run",
        "pyinstaller",
        "--noconfirm",
        str(entry),
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

    if clean:
        cmd.append("--clean")

    if onefile:
        cmd.append("--onefile")
    elif onedir:
        cmd.append("--onedir")

    if windowed:
        cmd.append("--windowed")

    for mod in hidden_imports:
        cmd.extend(["--hidden-import", mod])

    if collect_pyside6:
        cmd.extend(["--collect-all", "PySide6"])

    if FILTER_LISTS_DIR.is_dir():
        sep = ";" if platform.system() == "Windows" else ":"
        data_spec = f"{FILTER_LISTS_DIR}{sep}news_crawler/capture/filter_lists"
        cmd.extend(["--add-data", data_spec])

    if extra:
        cmd.extend(extra)

    return cmd


def pyinstaller_main_argv(args: argparse.Namespace, system: str) -> list[str]:
    name = args.name
    distpath = (ROOT / args.output_dir).resolve()
    return pyinstaller_argv(
        entry=ENTRY,
        name=name,
        distpath=distpath,
        workpath=(ROOT / "build" / name).resolve(),
        specpath=ROOT / "build",
        onefile=args.onefile,
        onedir=not args.onefile,
        windowed=True,
        hidden_imports=HIDDEN_IMPORTS,
        collect_pyside6=True,
        clean=args.clean,
        extra=args.extra,
    )


def pyinstaller_worker_argv(args: argparse.Namespace) -> list[str]:
    worker = screenshot_worker_name(args.name)
    distpath = (ROOT / args.output_dir).resolve()
    return pyinstaller_argv(
        entry=SCREENSHOT_ENTRY,
        name=worker,
        distpath=distpath,
        workpath=(ROOT / "build" / worker).resolve(),
        specpath=ROOT / "build",
        onefile=True,
        onedir=False,
        windowed=False,
        hidden_imports=WORKER_HIDDEN_IMPORTS,
        collect_pyside6=False,
        clean=False,
        extra=[],
    )


def install_screenshot_worker(
    system: str,
    main_name: str,
    output_dir: str,
    *,
    onedir: bool,
) -> None:
    """Copy the onefile screenshot worker next to the main GUI executable."""
    dist = (ROOT / output_dir).resolve()
    worker_name = screenshot_worker_name(main_name)
    worker_src = dist / (f"{worker_name}.exe" if system == "Windows" else worker_name)
    if not worker_src.is_file():
        print(f"warning: screenshot worker not found: {worker_src}", file=sys.stderr)
        return

    if system == "Darwin":
        dest_dir = dist / f"{main_name}.app" / "Contents" / "MacOS"
    elif onedir:
        dest_dir = dist / main_name
    else:
        dest_dir = dist

    if not dest_dir.is_dir():
        print(f"warning: cannot install screenshot worker; missing {dest_dir}", file=sys.stderr)
        return

    dest = dest_dir / worker_src.name
    shutil.copy2(worker_src, dest)
    worker_src.unlink()
    print(f"  Screenshot worker: {dest}")


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


def run_build(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    print("Running:", " ".join(cmd))
    merged = os.environ.copy()
    if env:
        merged.update(env)
    result = subprocess.run(cmd, cwd=ROOT, env=merged)
    if result.returncode != 0:
        sys.exit(result.returncode)


def install_playwright_browsers(staging: Path) -> None:
    """Download Chromium into a fixed folder for copying into the app bundle."""
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)
    print(f"Installing Playwright Chromium into {staging} ...")
    run_build(
        ["uv", "run", "playwright", "install", "chromium"],
        env={"PLAYWRIGHT_BROWSERS_PATH": str(staging)},
    )


def bundle_browsers(
    system: str,
    main_name: str,
    output_dir: str,
    *,
    onedir: bool,
    staging: Path,
) -> None:
    """Copy staged browsers next to the frozen app executable."""
    if not staging.is_dir() or not any(staging.iterdir()):
        print("warning: no staged Playwright browsers to bundle", file=sys.stderr)
        return

    dist = (ROOT / output_dir).resolve()
    if system == "Darwin":
        dest = dist / f"{main_name}.app" / "Contents" / "Resources" / BROWSERS_RESOURCE
    elif onedir:
        dest = dist / main_name / BROWSERS_RESOURCE
    else:
        dest = dist / BROWSERS_RESOURCE

    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(staging, dest)
    print(f"  Bundled browsers: {dest}")


def print_post_build(system: str, name: str, onedir: bool) -> None:
    artifact = artifact_hint(system, name, onedir)
    print()
    print(f"Build finished ({os_label(system)}).")
    print(f"  Artifact: {artifact}")
    print()
    print("Playwright Chromium is bundled under ms-playwright in the app folder.")
    print()
    if system == "Darwin":
        print("If macOS blocks the app, allow it in System Settings → Privacy & Security.")


def fetch_filter_lists() -> None:
    """Download full EasyList sets before bundling (falls back to committed starters)."""
    script = ROOT / "scripts" / "fetch_filter_lists.py"
    if not script.is_file():
        print(f"warning: {script} not found, using committed filter_lists/", file=sys.stderr)
        return
    print("Fetching adblock filter lists ...")
    result = subprocess.run(
        ["uv", "run", "python", str(script)],
        cwd=ROOT,
    )
    if result.returncode != 0:
        print(
            "warning: filter list download failed; using committed filter_lists/",
            file=sys.stderr,
        )


def main() -> None:
    args = parse_args()
    system = detect_os()

    if system not in ("Windows", "Darwin", "Linux"):
        print(f"error: unsupported OS: {system}", file=sys.stderr)
        sys.exit(1)

    require_uv()
    validate_project()
    fetch_filter_lists()

    print(f"Target OS: {os_label(system)} ({system})")
    print(f"Project:   {ROOT}")
    print(f"Entry:     {ENTRY}")
    print(f"Mode:      {'onefile' if args.onefile else 'onedir'}")
    print()

    cmd = pyinstaller_main_argv(args, system)
    run_build(cmd)

    print()
    print("Building headless screenshot worker (onefile)...")
    worker_cmd = pyinstaller_worker_argv(args)
    run_build(worker_cmd)
    install_screenshot_worker(
        system,
        args.name,
        args.output_dir,
        onedir=not args.onefile,
    )

    install_playwright_browsers(PLAYWRIGHT_STAGING)
    bundle_browsers(
        system,
        args.name,
        args.output_dir,
        onedir=not args.onefile,
        staging=PLAYWRIGHT_STAGING,
    )

    print_post_build(system, args.name, not args.onefile)


if __name__ == "__main__":
    main()
