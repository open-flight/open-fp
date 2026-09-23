#!/usr/bin/env bash
# Follow the Python app's logs on the board. Extra args pass through (e.g. --tail 500, --all).
set -euo pipefail
HOST="${HOST:-open-fp.local}"
ssh -t "arduino@${HOST}" "arduino-app-cli app logs /home/arduino/ArduinoApps/open-fp --follow $*"
