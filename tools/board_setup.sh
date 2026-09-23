#!/usr/bin/env bash
# One-time: install SSH key, sanity-check the board.
set -euo pipefail
HOST="${1:-open-fp.local}"
ssh-copy-id "arduino@${HOST}"
ssh "arduino@${HOST}" '
  set -e
  uname -a
  which arduino-app-cli && arduino-app-cli --help | head -20
  systemctl status arduino-router --no-pager | head -5 || true
  mkdir -p ~/ArduinoApps
'
