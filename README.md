# open-fp

Open source force plates for golf performance.

Two low-profile golf force plates, one per foot. Each plate has four load cells, eight in total. A single Arduino UNO Q reads them, and a web dashboard on the LAN shows live weight shift and swing replay.

> **Status:** The pure-Python processing (`app/python/open_fp/`) is written and tested: protocol, clock, pipeline, calibration, swing detection, and storage. Run it with `pytest`; it needs no hardware. The web UI and a desktop simulator also work: run `python tools/sim/sim_server.py` and open http://localhost:7070 to see live weight shift, swing capture, replay, and diagnostics fed by synthetic swings. The MCU firmware and the board-side `main.py` glue are not written yet. See the milestone plan in [`docs/PROJECT_INIT.md` §12](docs/PROJECT_INIT.md#12-milestones-and-acceptance-checks).

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
- Assembly: [`docs/assembly.md`](docs/assembly.md) · Wiring: [`docs/wiring.md`](docs/wiring.md) · System wiring, step by step: [`docs/harness.md`](docs/harness.md) · One-cell bench test: [`docs/bench-single-cell.md`](docs/bench-single-cell.md) · Calibration: [`docs/calibration.md`](docs/calibration.md)

## Repository layout

```
app/        Arduino App Lab app: MCU sketch, Python processing, static web UI
bench/      bring-up sketches for the ADS1220s
docs/       project spec, assembly, wiring, calibration, VERIFIED log
hardware/   BOM and CAD (STL/STEP in Git LFS)
tools/      deploy scripts, desktop simulator, offline analysis
tests/      pytest suite, runs without hardware
```

## Setup

Full walkthrough from a fresh clone and an unboxed board: **[`docs/SETUP.md`](docs/SETUP.md)**. The short version:

```bash
tools/dev_setup.sh          # dev machine: git-lfs, arduino-cli + UNO Q core, CAD files, .venv
# App Lab: first-boot the board as "open-fp", then create app "open-fp" with the WebUI - HTML brick
tools/board_setup.sh        # install your SSH key on the board
tools/deploy.sh             # push app/ and restart; UI at http://open-fp.local:7000
tools/logs.sh               # follow the app's Python logs
```

## License

[AGPL-3.0](LICENSE), the same license as [OpenFlight](https://github.com/open-flight/openflight).
