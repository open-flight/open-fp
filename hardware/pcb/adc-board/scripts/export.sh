#!/usr/bin/env bash
# Fabrication + assembly outputs for PCBWay, renders, and the schematic PDF.
# Usage: hardware/pcb/adc-board/scripts/export.sh      (after build.sh)
set -euo pipefail
cd "$(dirname "$0")/.."
KICAD_CLI=${KICAD_CLI:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}
PCB=adc-board.kicad_pcb
mkdir -p .scratch gerbers assembly renders
rm -f gerbers/*

"$KICAD_CLI" pcb export gerbers --use-drill-file-origin \
    --layers F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
    -o gerbers/ "$PCB"
"$KICAD_CLI" pcb export drill --format excellon --drill-origin plot --excellon-separate-th \
    --excellon-units mm -o gerbers/ "$PCB"
rm -f adc-board-gerbers.zip
(cd gerbers && zip -q ../adc-board-gerbers.zip ./*)

"$KICAD_CLI" pcb export pos --format csv --units mm --side both --use-drill-file-origin \
    -o .scratch/pos.csv "$PCB"
python3 scripts/make_assembly.py .scratch/pos.csv

"$KICAD_CLI" pcb render --side top --quality high --width 3000 --height 900 --zoom 3.3 \
    -o renders/adc-board-top.png "$PCB"
"$KICAD_CLI" pcb render --side bottom --quality high --width 3000 --height 900 --zoom 3.3 \
    -o renders/adc-board-bottom.png "$PCB"
"$KICAD_CLI" pcb render --side bottom --quality high --width 2400 --height 1400 \
    --rotate "-35,0,20" --zoom 2.2 --perspective -o renders/adc-board-3d.png "$PCB"
"$KICAD_CLI" sch export pdf -o adc-board-schematic.pdf adc-board.kicad_sch
echo "exports done"
