#!/usr/bin/env bash
# Sync the app to the board and (re)start it. First start compiles + flashes the MCU sketch
# and pulls brick containers, so the board needs internet access on the first run.
set -euo pipefail
HOST="${1:-forceplates.local}"
APP=forceplates
REMOTE="/home/arduino/ArduinoApps/${APP}"      # VERIFY path App Lab uses
rsync -az --delete --exclude 'data/' app/ "arduino@${HOST}:${REMOTE}/"
ssh "arduino@${HOST}" "
  arduino-app-cli app stop ${REMOTE} 2>/dev/null || true
  arduino-app-cli app start ${REMOTE}
"
echo "UI: http://${HOST}:7000"
