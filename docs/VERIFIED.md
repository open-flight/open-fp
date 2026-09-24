# VERIFIED

This file records the answer to every **VERIFY** item in [`PROJECT_INIT.md`](PROJECT_INIT.md). For each answer, give the tool, library, or datasheet version it was checked against and the date.

| # | Item | Answer | Checked against | Date |
|---|---|---|---|---|
| 1 | Arduino_RouterBridge: binary arg support in `notify()`, blocking behavior, max message size | | | |
| 2 | Router baud default (`arduino-router.service`); can it be raised on both sides? | **115200** on `/dev/ttyHS1`, set via `--serial-baudrate` in `/run/systemd/generator/arduino-router.service.d/10-imola.conf`. Whether it can be raised is still open. | `systemctl cat arduino-router` | 2026-09-23 |
| 3 | Zephyr core: `attachInterrupt` on D2, SPI on D11–D13 at 2 MHz, `micros()` resolution | D11/D12/D13 = PB15/PB14/PB13 = SPI2 MOSI/MISO/SCK (default `SPI`). D2 = PB3, `attachInterrupt` implemented (`WInterrupts.cpp`). **D10 = PB9 is in SPI2's pinctrl as hardware NSS**, so R4's CS moved to A2 (PA6, which only the ADC claims and has no pinctrl). Avoid A0 (DAC1 claims PA4), A1 (DAC out2), D0/D1 (USART1 console), A4/A5 (I2C3). D4/D5 are FDCAN1 pins, but CAN is deferred-init, so they work as GPIO unless CAN is started. Still open: 2 MHz SPI on hardware, `micros()` resolution, DRDY interrupt latency. | arduino:zephyr 1.0.0 variant overlay and generated devicetree | 2026-09-23 |
| 4 | WebUI brick: Socket.IO event naming, `expose_api` path params + POST bodies, bind address, static asset path | Binds `0.0.0.0:7000`; assets from `/app/assets` (needs `index.html`). `expose_api(method, path, fn)` = FastAPI `add_api_route`, so path params and body models work the standard FastAPI way; `ui.app` is the FastAPI instance. `send_message(event, dict\|str, room=None)` → `sio.emit(event, …)`; browser uses `libs/arduino.js` `WebUI.on_message(event, cb)` on raw socket.io. Server started only when `WebUI()` is instantiated in `main.py`. | `python-apps-base:0.12.0`, `arduino/app_bricks/web_ui/web_ui.py` | 2026-09-23 |
| 5 | App container: persistent data path, `requirements.txt` support, numpy preinstalled? | numpy 2.5.1, fastapi 0.141.1, uvicorn 0.52.1, msgpack 1.2.1 preinstalled (CPython 3.13.14). App venv lives in `<app>/.cache/.venv`. Persistence and `requirements.txt` handling are still open. | `docker run python-apps-base:0.12.0` | 2026-09-23 |
| 6 | `arduino-app-cli`: start/stop/logs/autostart commands; App Lab app dir on the board | App dir `/home/arduino/ArduinoApps/open-fp`. `app start\|stop\|restart <path>`, `app logs <path> [--follow] [--tail N] [--all]`, `monitor` (MCU serial). Autostart candidate: `properties set default <path>` (boot behavior untested). **No `rsync` on board**: deploy uses tar. | `arduino-app-cli` 0.13.0 | 2026-09-23 |
| 7 | ADS1220 module: exposed pins (CLK, REFP0/REFN0, AVDD/DVDD), onboard regulator, hole spacing | | | |
| 8 | Load cell wire colors (per cell, see `wiring.md`) | | | |
| 9 | App Lab first-boot steps (§11.1) | Board name, Wi-Fi, `arduino` password, updates, exactly as in §11.1. Board reachable at `open-fp.local`. OS: Debian 13 (trixie), kernel 6.16.7, aarch64. | App Lab (owner), `uname -a` | 2026-09-23 |

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

## Performance

| Item | Result | Checked against | Date |
|---|---|---|---|
| Pipeline and SwingDetector CPU cost on the board | 41.9 s of synthetic 200 Hz data (5 swings, all captured) processed in 6.35 s, about 15 % of one core | `python-apps-base:0.12.0` on the UNO Q (Python 3.13.14, numpy 2.5.1) | 2026-09-23 |

## Mechanical fixes

- **2026-09-23, cable notch didn't break through.** The test print showed a wall in the cradle's cable notch. Measured from the STL: the notch spanned y −28…−18 and the pocket wall is at y −17.3, leaving a 0.7 mm wall through the notch's full 7.2 mm depth. The retainer's notch (y −28…−18) also stopped 4 mm short of its window (y −14), so it would clamp the wires against the cell. The owner confirmed the wall shouldn't be there. Fixed by loading the STEP files in CadQuery 2.8 and cutting 7 mm wide slots to join each notch to the pocket or window. Removed 35.3 mm³ (cradle) and 44.8 mm³ (retainer), both still single valid solids. STL and STEP re-exported.

- **2026-09-23, locating hub foot.** The owner asked for a foot that locates on the cell. The cell's load point is a riveted strap across the centre tongue with a dome in the middle, and it faces the floor. The new `10_hub_foot_tpu` (from `hardware/cad/src/hub_foot.py`) is Ø18 × 4.7 mm with an 11.4 × 1.2 mm channel for the strap and a Ø6 × 0.6 mm dimple for the dome. It keeps 3.5 mm of foot below the load point, so floor clearance is unchanged. The strap width (11.0) and dome diameter (5.5) are **estimated from photos**; measure them with calipers and regenerate.

- **2026-09-23, cell rattles vertically under the retainer.** The raised centre strap faces out, so the frame's outer edge sits a few mm below the rim and the flat retainer doesn't touch it. Added a TPU shim ring (`11_cell_shim_tpu`, from `hardware/cad/src/cell_shim.py`): 34 mm outside, 28.6 mm inside, so it rests only on the frame and stays clear of the tongue and strap, with a 9 mm gap at the cable notch. It comes as a tuning set of 1.5–3.5 mm; record the thickness that works here: ___ mm.

## Notes found during scaffolding

- App Lab's generated skeleton puts the web client libs in `app/assets/libs/` (`arduino.js`, `socket.io.min.js`), not `assets/vendor/` as §2 planned. Keep `libs/` from the brick and put uPlot in `vendor/`.

- **CAD sources are not runnable as committed.** The scripts in `hardware/cad/src/` write to hard-coded output paths (`/home/claude`, `/home/claude/extras`). `assembly.py` also imports `cairosvg`. `forceplate_parts.py` exports `03_enclosure_base` and `04_enclosure_lid`, but the committed files are named `03_centre_enclosure_base` and `04_centre_enclosure_lid`. The sources are unchanged for now; ask the owner before editing them.
- **The CAD sources are an older revision than the STL/STEP files.** `forceplate_parts.py` has a cradle height of 14 mm (STL: 11.2), a relief depth of 2 mm (STL: 1.5), and a 2 mm retainer (STL: 1.6). Its enclosure is 150 × 70 mm, while the spec says 295 × 61 × 22. The STL/STEP files match the spec and are what gets printed. Update the sources before regenerating any part. Measured 2026-09-23 from the STL: the cradle is 54 × 54 × 11.2 with the pocket open at z=0, the pocket ceiling at 8.2, the relief ceiling at 9.7, the notch ceiling at 7.2, M2 holes 4 deep, and M4 holes 6.5 deep from the top.
