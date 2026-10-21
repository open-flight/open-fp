#!/usr/bin/env python3
"""The app's web UI on the real plates, before the production firmware exists.

Flash bench/ads1220_stream first (tools/bench/flash.sh bench/ads1220_stream), keep the plates
empty, then run:

    .venv/bin/python tools/bench/live_plates.py          # http://localhost:7070

The sketch streams all 8 channels as 200 Hz frames over `arduino-app-cli monitor` (SSH). This
script feeds them into the same Core the board will run (pipeline, swing detection, calibration
wizard, REST + Socket.IO) and serves app/assets, like tools/sim/sim_server.py does with synthetic
swings. It zeroes the plates a few seconds after the stream starts, so nobody may stand on them
then; the UI's Zero button does it again at any time.

The cells read lower under load, so a fresh data dir gets `signs` of -1 on every channel. Until
the calibration wizard has been run, forces use a nominal gain (about 20 % off); the lead/trail
split and the centre of pressure are ratios, so they are already close.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import signal
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "app" / "python"), str(ROOT / "tools" / "sim")]
# The imports below need the sys.path entries above, so they can't be at the top.
# pylint: disable=wrong-import-position

import numpy as np  # noqa: E402
import uvicorn  # noqa: E402
from multi_cell import ChanReadback, parse_line as parse_bench_line  # noqa: E402
from single_cell import Monitor, SketchError  # noqa: E402

from open_fp.app import Core  # noqa: E402
from open_fp.config import CHANNEL_IDS, N_CH, Config, save_config  # noqa: E402
from open_fp.protocol import Batch, encode_batch  # noqa: E402
from open_fp.web import register  # noqa: E402
from sim_server import SimWebUI  # noqa: E402

DATA_DIR = ROOT / "bench" / "live"   # git-ignored, like bench/results
ZERO_AFTER_S = 6.0                   # after the 'r' re-check at 3 s has settled
RECHECK_AFTER_S = 3.0                # a key sent before ssh attaches to the monitor is lost


def parse_stream_line(line: str):
    """A `B,...` batch line as a protocol Batch; readback, error and other lines as multi_cell's."""
    line = line.strip()
    if not line.startswith("B,"):
        return parse_bench_line(line)
    parts = line.split(",")
    if len(parts) != 6:
        return None
    try:
        seq, t_first, period, flags = (int(p) for p in parts[1:5])
        raw = bytes.fromhex(parts[5])
    except ValueError:
        return None
    if not raw or len(raw) % (3 * N_CH):
        return None
    b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
    v = (b[:, 0] << 16) | (b[:, 1] << 8) | b[:, 2]
    v = np.where(v & 0x800000, v - (1 << 24), v)
    return Batch(seq, t_first, period, flags, v.reshape(-1, N_CH).astype(np.int32))


def seed_config(data_dir: Path) -> None:
    """A fresh data dir gets signs of -1: these cells read lower under load (bench press tests)."""
    path = data_dir / "config.json"
    if not path.exists():
        save_config(Config(signs=[-1] * N_CH), path)


def feed(mon: Monitor, core: Core, readbacks: dict[str, bool]) -> None:
    """Thread: batches into the core, readbacks into `readbacks`, until the monitor closes."""
    while (item := mon.q.get()) is not None:
        if isinstance(item, Batch):
            core.on_payload(encode_batch(item), time.monotonic())
        elif isinstance(item, ChanReadback):
            readbacks[item.ch] = item.ok
        elif isinstance(item, SketchError):
            pass  # Monitor already printed it


async def push(core: Core, ui: SimWebUI) -> None:
    """Emit whatever the core has for the page (it rate-limits itself to 30 Hz)."""
    while True:
        for event, payload in core.tick(time.monotonic()):
            await ui.emit(event, payload)
        await asyncio.sleep(0.01)


async def startup(mon: Monitor, core: Core, readbacks: dict[str, bool], zero: bool) -> None:
    """Re-check the boards once ssh is attached, report who answers, then zero the empty plates."""
    await asyncio.sleep(RECHECK_AFTER_S)
    mon.send("r")
    await asyncio.sleep(ZERO_AFTER_S - RECHECK_AFTER_S)
    answering = [ch for ch in CHANNEL_IDS if readbacks.get(ch)]
    missing = [ch for ch in CHANNEL_IDS if not readbacks.get(ch)]
    print(f"  answering: {' '.join(answering) or 'none'}"
          + (f"; missing: {' '.join(missing)}" if missing else ""))
    st = core.status()
    if not st.get("frames"):
        print("  no frames yet: is bench/ads1220_stream flashed? "
              "(tools/bench/flash.sh bench/ads1220_stream)")
        return
    if zero:
        core.zero()
        print("  zeroed (plates empty). Step on.")


def main() -> int:
    """Serve the UI on --port and stream the plates into it until Ctrl-C."""
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--host", default="open-fp.local", help="the UNO Q")
    ap.add_argument("--port", type=int, default=7070, help="default 7070: macOS AirPlay uses 7000")
    ap.add_argument(
        "--bind", default="127.0.0.1", help="0.0.0.0 to open the UI from another device"
    )
    ap.add_argument("--data", default=str(DATA_DIR), help="config, calibration and swings")
    ap.add_argument("--no-zero", action="store_true", help="don't zero a few seconds after start")
    args = ap.parse_args()

    data_dir = Path(args.data)
    data_dir.mkdir(parents=True, exist_ok=True)
    seed_config(data_dir)
    core = Core(data_dir)
    mon = Monitor(args.host, parse=parse_stream_line)
    # On SIGTERM (e.g. pkill), exit through the normal path so the ssh monitor is closed too.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    readbacks: dict[str, bool] = {}
    threading.Thread(target=feed, args=(mon, core, readbacks), daemon=True).start()

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        tasks = [asyncio.create_task(push(core, ui)),
                 asyncio.create_task(startup(mon, core, readbacks, not args.no_zero))]
        yield
        for t in tasks:
            t.cancel()

    ui = SimWebUI(ROOT / "app" / "assets", lifespan=lifespan)
    register(ui, core)
    ui.mount_assets()
    print(f"open-fp live plates: http://localhost:{args.port}  (data: {data_dir}; Ctrl-C to stop)")
    print(f"Keep the plates empty for the first {ZERO_AFTER_S:.0f} s while it zeroes.")
    try:
        uvicorn.run(ui.app, host=args.bind, port=args.port, log_level="warning")
    finally:
        mon.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
