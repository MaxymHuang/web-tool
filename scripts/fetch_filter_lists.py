#!/usr/bin/env python3
"""Download adblock filter lists into src/news_crawler/capture/filter_lists/."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "src" / "news_crawler" / "capture" / "filter_lists"

FILTER_SOURCES: tuple[tuple[str, str | tuple[str, ...]], ...] = (
    ("easylist.txt", "https://easylist.to/easylist/easylist.txt"),
    ("easyprivacy.txt", "https://easylist.to/easylist/easyprivacy.txt"),
    ("fanboy-annoyance.txt", "https://easylist.to/easylist/fanboy-annoyance.txt"),
    (
        "easylist-japan.txt",
        (
            # Legacy EasyList Japan mirrors are often 404; AdGuard Japanese is maintained.
            "https://filters.adtidy.org/extension/chromium/filters/7.txt",
            "https://easylist-downloads.adblockplus.org/easylistjapan.txt",
        ),
    ),
)

MIN_BYTES = 1024


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_one(client: httpx.Client, name: str, url: str | tuple[str, ...]) -> bool:
    dest = OUT_DIR / name
    urls = (url,) if isinstance(url, str) else url
    last_error: Exception | None = None
    for candidate in urls:
        print(f"Fetching {candidate} -> {dest.name} ...")
        try:
            response = client.get(candidate, follow_redirects=True)
            response.raise_for_status()
            data = response.content
            if len(data) < MIN_BYTES:
                raise ValueError(f"response too small ({len(data)} bytes)")
            digest = sha256_bytes(data)
            dest.write_bytes(data)
            print(f"  wrote {len(data):,} bytes (sha256 {digest[:12]}...)")
            return True
        except Exception as exc:
            last_error = exc
            print(f"  failed: {exc}", file=sys.stderr)
    if last_error is not None:
        print(f"  warning: all sources failed for {name}", file=sys.stderr)
    return dest.is_file()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ok = True
    headers = {"Accept-Encoding": "identity"}
    with httpx.Client(timeout=120.0, headers=headers) as client:
        for name, url in FILTER_SOURCES:
            try:
                if not fetch_one(client, name, url):
                    ok = False
            except Exception as exc:
                print(f"  error: {name}: {exc}", file=sys.stderr)
                ok = False
    if not ok:
        print(
            "warning: some filter lists failed to download; starter lists in filter_lists/ are used as fallback",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
