# News Crawler Tool

PySide6 desktop app: search news via DuckDuckGo, review ranked results, select sources, then export to Excel with full-page screenshots.

Works on **macOS** (Intel and Apple Silicon), **Windows**, and **Linux**.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) package manager
- Python 3.11+

### macOS

```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

cd /path/to/web-tool
uv sync
uv run playwright install chromium
uv run news-crawler
```

On first run, macOS may prompt to allow network access for Python/Chromium — approve for search and screenshots.

Default export folder: `~/news_crawler_output`

### Windows

```powershell
cd /repo/path
uv sync
uv run playwright install chromium
uv run news-crawler
```

Default export folder: `%USERPROFILE%\news_crawler_output`

### Linux

```bash
uv sync
uv run playwright install chromium
# If Chromium fails to start, install system deps:
uv run playwright install-deps chromium
uv run news-crawler
```

## Usage

1. Enter a search prompt and choose a **Market** (English US, Japanese, or Taiwan).
2. Optionally change **Display language** for UI labels and Excel column headers.
3. Click **Search**.
4. Review results in the table; uncheck sources you do not want.
5. Choose an output folder and click **Export Selected**.

### Markets

| Market | DuckDuckGo region | Typical sources |
|--------|-------------------|-----------------|
| English (US) | `us-en` | International / US news |
| Japanese | `jp-jp` | NHK, Yahoo Japan, Nikkei, Asahi, etc. |
| Traditional Chinese (Taiwan) | `tw-tzh` | UDN, CNA, Liberty Times, ETtoday, etc. |

### Search prompts (multilingual)

Prompts accept **English**, **Japanese**, or **Traditional Chinese** (UTF-8). Results are shown in **DuckDuckGo News return order** with no local re-ranking or filtering.

Optional **Date** range (search bar) is passed to DuckDuckGo only. Search status appears in the window status bar at the bottom.

## Output

- `news_results_<timestamp>.xlsx` — localized columns: No., Media, Title, URL, Market
- `screenshots/` — one PNG per queued article (`001.png`, `002.png`, …)

Click result rows to add or remove articles from the **Queue** tab; export runs only from the Queue tab.

## Build executable

One script builds a native app for the OS you run it on (build on each target platform separately).

```bash
uv sync
python compile.py
```

Options: `--onefile` (single file), `--clean`, `--name NAME`, `--output-dir DIR`. Extra PyInstaller flags after `--`, e.g. `python compile.py -- --debug all`.

| OS | Default output |
|----|----------------|
| Windows | `dist/news-crawler/news-crawler.exe` |
| macOS | `dist/news-crawler.app` |
| Linux | `dist/news-crawler/news-crawler` |

`compile.py` bundles Playwright Chromium into the app (`Contents/Resources/ms-playwright` on macOS). Rebuild after upgrading Playwright in `pyproject.toml`.

## Tests

```bash
uv run pytest tests/
```

## Notes

- DuckDuckGo news search is unofficial; empty results or rate limits may occur — wait and retry or lower max results.
- Some sites block automated access; screenshots may fail for those URLs (see the log panel).

## License

GPL-3.0-or-later (see [LICENSE](LICENSE)).
