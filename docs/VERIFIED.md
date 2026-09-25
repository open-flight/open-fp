# VERIFIED

This file records the answer to every **VERIFY** item in [`PROJECT_INIT.md`](PROJECT_INIT.md). For each answer, give the tool, library, or datasheet version it was checked against and the date.

| # | Item | Answer | Checked against | Date |
|---|---|---|---|---|
| 1 | Arduino_RouterBridge: binary arg support in `notify()`, blocking behavior, max message size | | | |
| 2 | Router baud default (`arduino-router.service`); can it be raised on both sides? | **115200** on `/dev/ttyHS1`, set via `--serial-baudrate` in `/run/systemd/generator/arduino-router.service.d/10-imola.conf`. Whether it can be raised is still open. | `systemctl cat arduino-router` | 2026-09-23 |
| 3 | Zephyr core: `attachInterrupt` on D2, SPI on D11–D13 at 2 MHz, `micros()` resolution | D11/D12/D13 = PB15/PB14/PB13 = SPI2 MOSI/MISO/SCK (default `SPI`). D2 = PB3, `attachInterrupt` implemented (`WInterrupts.cpp`). **D10 = PB9 is in SPI2's pinctrl as hardware NSS**, so R4's CS moved to A2 (PA6, which only the ADC claims and has no pinctrl). Avoid A0 (DAC1 claims PA4), A1 (DAC out2), D0/D1 (USART1 console), A4/A5 (I2C3). D4/D5 are FDCAN1 pins, but CAN is deferred-init, so they work as GPIO unless CAN is started. **Hardware, 2026-09-25:** SPI at 2 MHz works (ADS1220 register readback OK), and `attachInterrupt` on D2 (FALLING) counts DRDY at ~950 Hz. About 9 edges are lost in each 100 ms window containing a Monitor RPC, so the router RPC appears to block interrupts briefly. Still open: `micros()` resolution. | arduino:zephyr 1.0.0 variant overlay and generated devicetree | 2026-09-23 |
| 4 | WebUI brick: Socket.IO event naming, `expose_api` path params + POST bodies, bind address, static asset path | Binds `0.0.0.0:7000`; assets from `/app/assets` (needs `index.html`). `expose_api(method, path, fn)` = FastAPI `add_api_route`, so path params and body models work the standard FastAPI way; `ui.app` is the FastAPI instance. `send_message(event, dict\|str, room=None)` → `sio.emit(event, …)`; browser uses `libs/arduino.js` `WebUI.on_message(event, cb)` on raw socket.io. Server started only when `WebUI()` is instantiated in `main.py`. | `python-apps-base:0.12.0`, `arduino/app_bricks/web_ui/web_ui.py` | 2026-09-23 |
| 5 | App container: persistent data path, `requirements.txt` support, numpy preinstalled? | numpy 2.5.1, fastapi 0.141.1, uvicorn 0.52.1, msgpack 1.2.1 preinstalled (CPython 3.13.14). App venv lives in `<app>/.cache/.venv`. Persistence and `requirements.txt` handling are still open. | `docker run python-apps-base:0.12.0` | 2026-09-23 |
| 6 | `arduino-app-cli`: start/stop/logs/autostart commands; App Lab app dir on the board | App dir `/home/arduino/ArduinoApps/open-fp`. `app start\|stop\|restart <path>`, `app logs <path> [--follow] [--tail N] [--all]`, `monitor` (MCU serial). Autostart candidate: `properties set default <path>` (boot behavior untested). **No `rsync` on board**: deploy uses tar. | `arduino-app-cli` 0.13.0 | 2026-09-23 |
| 7 | ADS1220 module: exposed pins (CLK, REFP0/REFN0, AVDD/DVDD), onboard regulator, hole spacing | Purple ADS1220 breakout. Left edge: DRDY, MISO, MOSI, SCLK, CS, CLK, DVDD, DGND. Right edge: AIN0–AIN3, REFN0, REFP0, AVDD, AGND. Supplies and grounds are split (DVDD/AVDD, DGND/AGND), so both pairs must be wired; CLK is broken out, so tie it to GND. **Still open:** onboard regulator, board size and hole spacing. | owner's photo of the board | 2026-09-25 |
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

## Bench tooling

| Item | Answer | Checked against | Date |
|---|---|---|---|
| `Monitor` for bench sketches | `Arduino_RouterBridge` 0.4.3 `Monitor` (a `Stream`) sends output to the Linux side as `mon/write` RPCs; read it with `arduino-app-cli monitor` | library source `src/monitor.h` | 2026-09-24 |
| `bench/ads1220_single` builds | compiles for `arduino:zephyr:unoq` (89 KB flash, 36 KB RAM) | arduino-cli 1.5.1, arduino:zephyr 1.0.0, Arduino_RouterBridge 0.4.3 | 2026-09-24 |
| USB upload + monitor | **Works end to end.** `tools/bench/flash.sh` uploads over USB: arduino-cli → adb → OpenOCD on the Linux side, which flashes the STM32U585 (2 MB, dual-bank, RDP 0). `ssh arduino@open-fp.local arduino-app-cli monitor` streams the sketch's `Monitor` output, including without a TTY (what `single_cell.py` uses), and keystrokes sent to it reach the sketch (`r` re-runs the readback). With no ADC wired: `R,0,00,00,00,00` (D12 floats low), then `E,no DRDY` every 500 ms. | arduino-cli 1.5.1, UNO Q over USB | 2026-09-24 |

## Bench findings

| Item | Result | Checked against | Date |
|---|---|---|---|
| Monitor RPC cost | Each `Monitor.available()`/`println` call blocks the MCU loop for roughly 13 ms (a loop polling DRDY captured ~150 of 1000 samples/s when checking `Monitor.available()` every loop). **The firmware must not call the router in the sampling loop;** batch sends as the spec plans (`Bridge.notify` at 20 Hz) and check whether they block the same way. | bench/ads1220_single on hardware | 2026-09-25 |
| ADC self-test ('v') on L1, wired except R1/R2 | AVDD 3333 mV, external REF 3316 mV (REFP0/REFN0 OK), AIN1 552 mV (floating, no R1/R2 yet), **AIN0 > 2048 mV: at the 3.3 V rail, not the ~1650 mV centre-tap voltage.** Either S/E+ are swapped or E− isn't grounded. | bench/ads1220_single voltage check | 2026-09-25 |

## Performance

| Item | Result | Checked against | Date |
|---|---|---|---|
| Pipeline and SwingDetector CPU cost on the board | 41.9 s of synthetic 200 Hz data (5 swings, all captured) processed in 6.35 s, about 15 % of one core | `python-apps-base:0.12.0` on the UNO Q (Python 3.13.14, numpy 2.5.1) | 2026-09-23 |

## Mechanical fixes

- **2026-09-23, cable notch didn't break through.** The test print showed a wall in the cradle's cable notch. Measured from the STL: the notch spanned y −28…−18 and the pocket wall is at y −17.3, leaving a 0.7 mm wall through the notch's full 7.2 mm depth. The retainer's notch (y −28…−18) also stopped 4 mm short of its window (y −14), so it would clamp the wires against the cell. The owner confirmed the wall shouldn't be there. Fixed by loading the STEP files in CadQuery 2.8 and cutting 7 mm wide slots to join each notch to the pocket or window. Removed 35.3 mm³ (cradle) and 44.8 mm³ (retainer), both still single valid solids. STL and STEP re-exported.

- **2026-09-23, locating hub foot.** The owner asked for a foot that locates on the cell. The cell's load point is a riveted strap across the centre tongue with a dome in the middle, and it faces the floor. The new `10_hub_foot_tpu` (from `hardware/cad/src/hub_foot.py`) is Ø18 × 4.7 mm with an 11.4 × 1.2 mm channel for the strap and a Ø6 × 0.6 mm dimple for the dome. It keeps 3.5 mm of foot below the load point, so floor clearance is unchanged. The strap width (11.0) and dome diameter (5.5) were estimated from photos. **The test print fits well (owner, 2026-09-23)**, so the estimated dimensions stand.

- **2026-09-23, cell rattles vertically under the retainer.** The raised centre strap faces out, so the frame's outer edge sits a few mm below the rim and the flat retainer doesn't touch it. Added a TPU shim ring (`11_cell_shim_tpu`, from `hardware/cad/src/cell_shim.py`): 34 mm outside, 28.6 mm inside, so it rests only on the frame and stays clear of the tongue and strap, with a 9 mm gap at the cable notch. It comes as a tuning set of 1.5–3.5 mm; The fit test found the tightest stack was **3.5 mm under the cell plus 1.5 mm over it**, so the frame is about 3.2 mm thick. The 3.5 mm moved into the cradle as a rigid PETG ledge, keeping TPU out of the load path, and **the 1.5 mm TPU shim goes on top**.

- **2026-09-23, relief too small for the cell's tongue.** The Ø24 relief didn't clear the tongue, which is about 21 × 19 mm with a ~28 mm diagonal (estimated from a photo, frame = 34 mm). Anything touching the tongue carries load around the strain gauges and the reading comes out low. Replaced it with a 28 × 28 mm rounded-square relief (r 3), same 1.5 mm depth: 485.8 mm³ removed, still a single valid solid. The frame now bears on a 3 mm band all round, directly opposite the shim ring and retainer lip. **Confirmed by the owner:** the tongue does reach the old Ø24 cradle, so that print is retired and all 8 cradles are being printed from the new file.

- **2026-09-23, cradle bearing ledge.** Added a 3.5 mm PETG ledge to the pocket, between the 28 mm relief and the 34.6 mm pocket wall, so the frame bears at 4.7 mm from the open face: 1457 mm³ added, still a single valid solid, and the notch was re-cut clear. The tongue now has 5 mm of clearance to the relief ceiling. **Still to measure:** the gap between the retainer and the floor with a corner assembled. Assuming the cell's 7.8 mm total height, it is about 5 mm, which puts the plate top about 3.5 mm above the spec's ~22 mm standing height. If that matters for the edge ramps, reduce `BASE_T` in `hub_foot.py`.

## Notes found during scaffolding

- App Lab's generated skeleton puts the web client libs in `app/assets/libs/` (`arduino.js`, `socket.io.min.js`), not `assets/vendor/` as §2 planned. Keep `libs/` from the brick and put uPlot in `vendor/`.

- **CAD sources are not runnable as committed.** The scripts in `hardware/cad/src/` write to hard-coded output paths (`/home/claude`, `/home/claude/extras`). `assembly.py` also imports `cairosvg`. `forceplate_parts.py` exports `03_enclosure_base` and `04_enclosure_lid`, but the committed files are named `03_centre_enclosure_base` and `04_centre_enclosure_lid`. The sources are unchanged for now; ask the owner before editing them.
- **The CAD sources are an older revision than the STL/STEP files.** `forceplate_parts.py` has a cradle height of 14 mm (STL: 11.2), a relief depth of 2 mm (STL: 1.5), and a 2 mm retainer (STL: 1.6). Its enclosure is 150 × 70 mm, while the spec says 295 × 61 × 22. The STL/STEP files match the spec and are what gets printed. Update the sources before regenerating any part. Measured 2026-09-23 from the STL: the cradle is 54 × 54 × 11.2 with the pocket open at z=0, the pocket ceiling at 8.2, the relief ceiling at 9.7, the notch ceiling at 7.2, M2 holes 4 deep, and M4 holes 6.5 deep from the top.
