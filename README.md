# OpenFlight Force Plates

Two low-profile golf force plates, one per foot. Each plate has four load cells, eight in total. A single Arduino UNO Q reads them, and a web dashboard on the LAN shows live weight shift and swing replay.

> **Status:** M0, scaffold only. The firmware, Python pipeline, and web UI are not written yet. See the milestone plan in [`docs/PROJECT_INIT.md` §12](docs/PROJECT_INIT.md#12-milestones-and-acceptance-checks).

## What it measures

| Output | Notes |
|---|---|
| Vertical force per foot (Fz) | N and %BW |
| Centre of pressure (CoP) per foot and combined | mm, in the stance frame |
| Lead/trail weight % | set by handedness (RH/LH) |
| Swing capture and metrics | address, max trail, transition, max lead, finish |

## Limitations

- **Vertical force only.** Each plate has four vertical cells, which give Fz and CoP (x, y) per plate. The plates cannot measure shear (horizontal) forces or torque about the vertical axis, so the app does not report ground torque or horizontal force.
- **Inter-channel skew up to ~1 ms.** Each ADC runs on its own oscillator. All eight are read on the DRDY signal of one board.
- **200 Hz stream.** The MCU↔Linux router link runs at 115200 baud. That is enough for weight shift but too slow for impact transients.
- **Temperature drift.** Half-bridge cells and their completion resistors drift with temperature. The app auto-zeros when the plates are empty.
- **Impact timing is external.** Impact is known only when the OpenFlight launch monitor sends a shot event or you mark it by hand. Over Wi-Fi with NTP, expect 5–20 ms of error.

## Hardware

- 2 × 12" × 12" × 1/4" 6061 aluminum plates, 8 × 50 kg half-bridge load cells, 8 × ADS1220 24-bit ADCs, 1 × Arduino UNO Q
- Bill of materials: [`hardware/bom.md`](hardware/bom.md)
- Print files: [`hardware/cad/`](hardware/cad/) (STL, STEP, and the CadQuery sources)
- Assembly: [`docs/assembly.md`](docs/assembly.md) · Wiring: [`docs/wiring.md`](docs/wiring.md) · Calibration: [`docs/calibration.md`](docs/calibration.md)

## Repository layout

```
app/        Arduino App Lab app: MCU sketch, Python processing, static web UI
bench/      bring-up sketches for the ADS1220s
docs/       project spec, assembly, wiring, calibration, VERIFIED log
hardware/   BOM and CAD (STL/STEP in Git LFS)
tools/      deploy scripts, desktop simulator, offline analysis
tests/      pytest suite, runs without hardware
```

## Quickstart (development, no hardware)

```bash
git lfs install && git lfs pull          # fetch CAD files
python -m venv .venv && . .venv/bin/activate
pip install fastapi uvicorn python-socketio numpy pytest
python tools/sim/sim_server.py           # (M5) open http://localhost:7000
pytest
```

## Deploy to the board

See [`docs/PROJECT_INIT.md` §11](docs/PROJECT_INIT.md#11-install-and-deploy-on-a-fresh-uno-q). In short:

```bash
tools/board_setup.sh forceplates.local   # once: SSH key and sanity checks
tools/deploy.sh forceplates.local        # sync and start; UI at http://forceplates.local:7000
```

## License

TBD: to match OpenFlight's license.
