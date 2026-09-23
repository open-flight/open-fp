#!/usr/bin/env bash
# Sync the app to the board and (re)start it. First start compiles + flashes the MCU sketch
# and pulls brick containers, so the board needs internet access on the first run.
# Uses tar over ssh because the board image has no rsync.
set -euo pipefail
HOST="${1:-open-fp.local}"
APP=open-fp
REMOTE="/home/arduino/ArduinoApps/${APP}"
cd "$(dirname "$0")/.."
# Replace everything except runtime data and App Lab's cache, like rsync --delete --exclude.
COPYFILE_DISABLE=1 tar cf - --exclude '.gitkeep' --exclude '.DS_Store' --exclude 'data' --exclude '.cache' -C app . \
  | ssh "arduino@${HOST}" "
      set -e
      mkdir -p ${REMOTE} && cd ${REMOTE}
      find . -mindepth 1 -maxdepth 1 ! -name data ! -name .cache -exec rm -rf {} +
      tar xf -
    "
ssh "arduino@${HOST}" "arduino-app-cli app restart ${REMOTE}"
echo "UI: http://${HOST}:7000"
