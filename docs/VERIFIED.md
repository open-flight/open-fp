# VERIFIED

This file records the answer to every **VERIFY** item in [`PROJECT_INIT.md`](PROJECT_INIT.md). For each answer, give the tool, library, or datasheet version it was checked against and the date.

| # | Item | Answer | Checked against | Date |
|---|---|---|---|---|
| 1 | Arduino_RouterBridge: binary arg support in `notify()`, blocking behavior, max message size | | | |
| 2 | Router baud default (`arduino-router.service`); can it be raised on both sides? | | | |
| 3 | Zephyr core: `attachInterrupt` on D2, SPI on D11–D13 at 2 MHz, `micros()` resolution | | | |
| 4 | WebUI brick: Socket.IO event naming, `expose_api` path params + POST bodies, bind address, static asset path | | | |
| 5 | App container: persistent data path, `requirements.txt` support, numpy preinstalled? | | | |
| 6 | `arduino-app-cli`: start/stop/logs/autostart commands; App Lab app dir on the board | | | |
| 7 | ADS1220 module: exposed pins (CLK, REFP0/REFN0, AVDD/DVDD), onboard regulator, hole spacing | | | |
| 8 | Load cell wire colors (per cell, see `wiring.md`) | | | |
| 9 | App Lab first-boot steps (§11.1) | | | |

## Bench measurements (M1/M2)

| Channel | Unloaded mean (counts) | Std dev (counts) | Register readback | Notes |
|---|---|---|---|---|
| L1 | | | | |
| L2 | | | | |
| L3 | | | | |
| L4 | | | | |
| R1 | | | | |
| R2 | | | | |
| R3 | | | | |
| R4 | | | | |

Achieved loop rate: — · `drdyMissed` over 10 min: —

## Toolchain

| Item | Answer | Checked against | Date |
|---|---|---|---|
| FQBN for `arduino-cli` | `arduino:zephyr:unoq` (core `arduino:zephyr`, "Arduino Q Boards") | arduino-cli 1.5.1, arduino:zephyr 1.0.0, `arduino-cli board list` | 2026-09-23 |
| Board ports | USB serial `/dev/cu.usbmodem*` and network port (mDNS `open-fp.local`), both detected as Arduino UNO Q | `arduino-cli board list` | 2026-09-23 |

## Notes found during scaffolding

- **CAD sources are not runnable as committed.** The scripts in `hardware/cad/src/` write to hard-coded output paths (`/home/claude`, `/home/claude/extras`). `assembly.py` also imports `cairosvg`. `forceplate_parts.py` exports `03_enclosure_base` and `04_enclosure_lid`, but the committed files are named `03_centre_enclosure_base` and `04_centre_enclosure_lid`. The sources are unchanged for now; ask the owner before editing them.
