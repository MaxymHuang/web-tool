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

1. Enter a search prompt and click **Search**.
2. Review results in the table; uncheck sources you do not want.
3. Choose an output folder and click **Export Selected**.

## Output

- `news_results_<timestamp>.xlsx` — columns: No., メディア, 揭載タイトル, URL
- `screenshots/` — one PNG per selected article (`001.png`, `002.png`, …)

## Notes

- DuckDuckGo news search is unofficial; empty results or rate limits may occur — wait and retry or lower max results.
- Some sites block automated access; screenshots may fail for those URLs (see the log panel).

## License

GPL-3.0-or-later (see [LICENSE](LICENSE)).
