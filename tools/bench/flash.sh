#!/usr/bin/env bash
# Compile and flash a bench sketch to the UNO Q's MCU over USB, then show how to watch it.
#   tools/bench/flash.sh                     # bench/ads1220_single
#   tools/bench/flash.sh bench/ads1220_all
# This replaces the MCU sketch of the deployed app; run tools/deploy.sh to put the app back.
set -euo pipefail
cd "$(dirname "$0")/../.."
SKETCH="${1:-bench/ads1220_single}"
FQBN=arduino:zephyr:unoq

PORT="$(arduino-cli board list --format json | python3 -c '
import json, sys
for p in json.load(sys.stdin).get("detected_ports", []):
    boards = p.get("matching_boards") or []
    if p["port"]["protocol"] == "serial" and any(b.get("fqbn") == "arduino:zephyr:unoq" for b in boards):
        print(p["port"]["address"]); break
')"
if [ -z "${PORT}" ]; then
  echo "No UNO Q found on USB. Plug it into this computer with a data USB-C cable and retry." >&2
  echo "(arduino-cli board list should show 'Arduino UNO Q' on a /dev/cu.usbmodem* port.)" >&2
  exit 1
fi
# Arduino's ctags (used only to generate function prototypes) is an Intel binary; on an Apple
# Silicon Mac without Rosetta it can't run. The bench sketches define every function before use,
# so a do-nothing stand-in is safe.
EXTRA=()
CTAGS="${HOME}/Library/Arduino15/packages/builtin/tools/ctags/5.8-arduino11/ctags"
if [ -e "${CTAGS}" ] && ! "${CTAGS}" --version >/dev/null 2>&1; then
  STUB="$(mktemp -d)"
  printf '#!/bin/sh\nexit 0\n' > "${STUB}/ctags"
  chmod +x "${STUB}/ctags"
  EXTRA=(--build-property "tools.ctags.path=${STUB}" --build-property "tools.ctags.cmd.path=${STUB}/ctags")
  echo "(Arduino's ctags can't run here, e.g. no Rosetta; using a no-op stand-in.)"
fi
echo "Compiling ${SKETCH}..."
arduino-cli compile --fqbn "${FQBN}" ${EXTRA[@]+"${EXTRA[@]}"} "${SKETCH}"
echo "Uploading to ${PORT}..."
arduino-cli upload --fqbn "${FQBN}" -p "${PORT}" "${SKETCH}"
echo
echo "Flashed. Watch the output with:  ssh -t arduino@open-fp.local arduino-app-cli monitor"
if [ "${SKETCH%/}" = "bench/ads1220_all" ]; then
  echo "Or run the guided test:        .venv/bin/python tools/bench/multi_cell.py"
else
  echo "Or run the guided test:        .venv/bin/python tools/bench/single_cell.py"
fi
