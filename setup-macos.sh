#!/usr/bin/env bash
# One-shot macOS setup: check prerequisites, install deps, build news-crawler.app
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { printf "${BLUE}==>${NC} %s\n" "$*"; }
ok()    { printf "${GREEN}✓${NC} %s\n" "$*"; }
warn()  { printf "${YELLOW}!${NC} %s\n" "$*"; }
fail()  { printf "${RED}error:${NC} %s\n" "$*" >&2; exit 1; }

SKIP_BUILD=0
OPEN_APP=0

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Set up the News Crawler environment on macOS and build dist/news-crawler.app.

Options:
  --skip-build   Install dependencies only; do not run compile.py
  --open         Open news-crawler.app after a successful build
  -h, --help     Show this help
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-build) SKIP_BUILD=1; shift ;;
        --open)       OPEN_APP=1; shift ;;
        -h|--help)    usage; exit 0 ;;
        *)            fail "Unknown option: $1 (use --help)" ;;
    esac
done

if [[ "$(uname -s)" != "Darwin" ]]; then
    fail "This script is for macOS only."
fi

info "News Crawler macOS setup"
info "Project: $ROOT"
echo

# ---------------------------------------------------------------------------
# Git (optional for running the app; useful for cloning/updating the repo)
# ---------------------------------------------------------------------------
if command -v git >/dev/null 2>&1; then
    ok "git $(git --version | awk '{print $3}')"
else
    warn "git not found. Install Xcode Command Line Tools:"
    echo "       xcode-select --install"
fi

# ---------------------------------------------------------------------------
# uv
# ---------------------------------------------------------------------------
ensure_uv() {
    if command -v uv >/dev/null 2>&1; then
        ok "uv $(uv --version | awk '{print $2}')"
        return
    fi

    info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    export PATH="$HOME/.local/bin:$PATH"
    if ! command -v uv >/dev/null 2>&1; then
        fail "uv install finished but 'uv' is not on PATH. Add \$HOME/.local/bin to PATH and re-run."
    fi
    ok "uv installed ($(uv --version | awk '{print $2}'))"
}

export PATH="$HOME/.local/bin:$PATH"
ensure_uv

# ---------------------------------------------------------------------------
# Python 3.11+ (uv manages the project interpreter)
# ---------------------------------------------------------------------------
info "Ensuring Python 3.11+ is available..."
uv python install 3.11 >/dev/null
PYTHON_VERSION="$(uv run python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')"
ok "Python $PYTHON_VERSION (via uv)"

# ---------------------------------------------------------------------------
# Project dependencies (includes dev group for PyInstaller)
# ---------------------------------------------------------------------------
info "Syncing project dependencies..."
uv sync --all-groups
ok "Dependencies installed"

# ---------------------------------------------------------------------------
# Build native app
# ---------------------------------------------------------------------------
APP_PATH="$ROOT/dist/news-crawler.app"

if [[ "$SKIP_BUILD" -eq 1 ]]; then
    info "Skipping build (--skip-build)."
    echo
    ok "Dev environment ready. Run: uv run news-crawler"
    exit 0
fi

info "Building news-crawler.app (this may take several minutes)..."
uv run python compile.py
echo

if [[ ! -d "$APP_PATH" ]]; then
    fail "Build finished but app not found at: $APP_PATH"
fi

ok "Build complete: $APP_PATH"
echo
echo "Launch the app:"
echo "  open \"$APP_PATH\""
echo
echo "If macOS blocks the app, allow it in System Settings → Privacy & Security."
echo "Default export folder: ~/news_crawler_output"

if [[ "$OPEN_APP" -eq 1 ]]; then
    info "Opening news-crawler.app..."
    open "$APP_PATH"
fi
