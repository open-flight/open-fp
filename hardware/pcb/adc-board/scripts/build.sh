#!/usr/bin/env bash
# Regenerate the whole ADC board: schematic -> ERC -> netlist -> placement -> autoroute -> DRC.
# Usage (from anywhere):  hardware/pcb/adc-board/scripts/build.sh /path/to/freerouting.jar
# Then:                   hardware/pcb/adc-board/scripts/export.sh
# Env overrides: KICAD_CLI, KPY (KiCad's Python with pcbnew), JAVA.
set -euo pipefail
cd "$(dirname "$0")/.."
KICAD_CLI=${KICAD_CLI:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}
KPY=${KPY:-/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3}
JAR=${1:?usage: build.sh /path/to/freerouting.jar}
mkdir -p .scratch

python3 scripts/gen_sch.py
"$KICAD_CLI" sch erc --exit-code-violations -o .scratch/erc.rpt adc-board.kicad_sch
"$KICAD_CLI" sch export netlist --format kicadsexpr -o adc-board.net adc-board.kicad_sch
python3 scripts/check_netlist.py adc-board.net
"$KPY" scripts/gen_pcb.py
"$KPY" scripts/route.py "$JAR" 40
"$KICAD_CLI" pcb drc --schematic-parity --severity-error --exit-code-violations \
    -o .scratch/drc.rpt adc-board.kicad_pcb
echo "ERC + DRC clean"
