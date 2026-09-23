#!/usr/bin/env bash
# One-time dev machine setup (macOS + Homebrew): git-lfs, arduino-cli + UNO Q core,
# CAD files, Python venv. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/.."

command -v brew >/dev/null || { echo "Install Homebrew first: https://brew.sh" >&2; exit 1; }
brew list git-lfs >/dev/null 2>&1 || brew install git-lfs
brew list arduino-cli >/dev/null 2>&1 || brew install arduino-cli

git lfs install
git lfs pull

arduino-cli core update-index
arduino-cli core list | grep -q '^arduino:zephyr ' || arduino-cli core install arduino:zephyr

if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q fastapi uvicorn python-socketio fastapi-socketio httpx numpy pytest pyflakes

echo
echo "Dev machine ready. Boards currently visible:"
arduino-cli board list
