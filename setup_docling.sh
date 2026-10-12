#!/usr/bin/env bash
# ============================================================
#  setup_docling.sh - Moli-Tutor optional feature: Docling
#  Converts PDF / complex HTML into structured Markdown
#  (used by tutor_cli.py ingest).
#
#  Usage:
#    ./setup_docling.sh [install-dir]
#    default: ${XDG_DATA_HOME:-$HOME/.local/share}/moli-tutor/docling
#    NOTE: do NOT install into a cloud-synced folder (Google Drive, Dropbox...).
# ============================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQ="$REPO/requirements-docling.txt"
POINTER="$REPO/docling.path"

TARGET="${1:-${XDG_DATA_HOME:-$HOME/.local/share}/moli-tutor/docling}"

if [ -z "${1:-}" ] && [ -f "$POINTER" ]; then
  EXISTING="$(cat "$POINTER")"
  if [ -x "$EXISTING" ]; then
    echo "[info] Docling is already configured: $EXISTING"
    echo "       Delete docling.path or pass an install dir to change it."
    echo
    echo "Usage: python -X utf8 tutor_cli.py ingest <pdf> --out <dir>"
    exit 0
  fi
fi

echo "[1/5] install dir: $TARGET"
mkdir -p "$TARGET"

# --- find Python 3.10-3.13 ---
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3 python; do
  if command -v "$c" >/dev/null 2>&1; then
    if "$c" -c 'import sys; raise SystemExit(0 if (3,10) <= sys.version_info[:2] <= (3,13) else 1)' 2>/dev/null; then
      PY="$c"; break
    fi
  fi
done
if [ -z "$PY" ]; then
  echo "[error] Python 3.10-3.13 not found." >&2
  exit 1
fi

VENV="$TARGET/venv"
DOCLING_EXE="$VENV/bin/docling"

if [ -x "$DOCLING_EXE" ]; then
  echo "[2/5] reusing existing venv"
else
  echo "[2/5] creating venv: $VENV"
  "$PY" -m venv "$VENV"
  echo "[3/5] installing docling (first run takes a few minutes)"
  "$VENV/bin/python" -m pip install --upgrade pip >/dev/null 2>&1 || true
  "$VENV/bin/python" -m pip install -r "$REQ"
fi

echo "[4/5] pre-downloading models for offline/portable use (~0.4GB, first run only)"
if [ -x "$VENV/bin/docling-tools" ]; then
  "$VENV/bin/docling-tools" models download layout tableformer rapidocr -o "$TARGET/models"
fi

echo "[5/5] writing docling.path"
printf '%s' "$DOCLING_EXE" > "$POINTER"

echo
echo "Usage: python -X utf8 tutor_cli.py ingest <pdf> --out <dir>"
