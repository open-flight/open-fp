#!/usr/bin/env python3
"""Desktop simulator (§11.5): the real app core fed with synthetic swings.

Serves app/assets and the same REST routes + Socket.IO messages as the board, using the
same FastAPI/fastapi_socketio setup as the WebUI brick (Socket.IO at /socket.io, API
routes unprefixed). Streams 200 Hz frames in real time through Pipeline + SwingDetector,
and sends launch-monitor shot events for some swings so impact labelling can be seen.

    python tools/sim/sim_server.py            # http://localhost:7000
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "app" / "python"), str(Path(__file__).parent)]

import numpy as np  # noqa: E402
import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from fastapi_socketio import SocketManager  # noqa: E402

from open_fp.app import Core  # noqa: E402
from open_fp.calibration import Calibration, save_calibration  # noqa: E402
from open_fp.protocol import encode_batch  # noqa: E402
from open_fp.web import register  # noqa: E402
from synth import RATE_HZ, Scenario, generate, to_batches  # noqa: E402

# The simulated hardware's "true" calibration. Seeded into the sim data dir on first run.
SIM_HARDWARE = Calibration(
    tares=[31000.0, -12000.0, 4500.0, 88000.0, -52000.0, 7000.0, 19000.0, -2500.0],
    gains=[4.41e-4, 4.63e-4, 4.52e-4, 4.70e-4, 4.48e-4, 4.39e-4, 4.66e-4, 4.57e-4],
    created="2026-09-23T00:00:00", mass_kg=20.0,
)


class SimWebUI:
    """Stand-in for arduino.app_bricks.web_ui.WebUI with the same server wiring."""

    def __init__(self, assets_dir: str | Path, lifespan=None):
        self.assets_dir = Path(assets_dir)
        self.app = FastAPI(openapi_url=None, lifespan=lifespan)
        self.sio = SocketManager(app=self.app, mount_location="/socket.io", socketio_path="")

    def expose_api(self, method: str, path: str, fn):
        self.app.add_api_route(path, fn, methods=[method])

    async def emit(self, event: str, data):
        await self.sio.emit(event, data)

    def mount_assets(self):
        self.app.mount("/", StaticFiles(directory=self.assets_dir, html=True), name="assets")


def session(rng: np.random.Generator, swings: int) -> list[Scenario]:
    out = [Scenario("empty", 2.0), Scenario("step_on", 1.0), Scenario("stance", 3.0)]
    for _ in range(swings):
        out.append(Scenario("swing", params={"address_s": float(rng.uniform(1.8, 3.0))}))
        out.append(Scenario("stance", float(rng.uniform(3.0, 6.0))))
        if rng.random() < 0.15:
            out += [Scenario("sway", 5.0), Scenario("stance", 2.5)]
    return out + [Scenario("empty", 3.0)]


async def stream(core: Core, ui: SimWebUI, args) -> None:
    rng = np.random.default_rng(args.seed)
    seq, t_us = 0, 0
    while True:
        data = generate(session(rng, args.swings), core.cfg, cal=SIM_HARDWARE, bw_kg=args.bw_kg,
                        seed=int(rng.integers(1 << 31)))
        start = time.monotonic() + 0.05
        shots = [s["impact"] for s in data.truth["swings"] if rng.random() < args.shot_prob]
        for b in to_batches(data.counts, seq0=seq, t0_us=t_us):
            t_end = (b.t_first_us - t_us) % 2**32 / 1e6 + b.n / RATE_HZ   # session time after batch
            due = start + t_end / args.speed
            await asyncio.sleep(max(0.0, due - time.monotonic()))
            core.on_payload(encode_batch(b), time.monotonic())
            while shots and shots[0] + 0.03 <= t_end:        # shot message arrives ~30 ms after impact
                impact_mono = start + shots.pop(0) / args.speed
                core.shot_event((time.time() - (time.monotonic() - impact_mono)) * 1000)
            for event, payload in core.tick(time.monotonic()):
                await ui.emit(event, payload)
            seq += 1
        t_us = (t_us + len(data.counts) * 5000) % 2**32


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=7000)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--data", default=str(Path(__file__).parent / ".data"))
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--swings", type=int, default=8, help="swings per generated session before it loops")
    ap.add_argument("--bw-kg", type=float, default=82.0)
    ap.add_argument("--shot-prob", type=float, default=0.5, help="fraction of swings that get a shot event")
    ap.add_argument("--speed", type=float, default=1.0, help="playback speed (1 = real time)")
    args = ap.parse_args()

    data_dir = Path(args.data)
    if not (data_dir / "calibration.json").exists():
        save_calibration(SIM_HARDWARE, data_dir / "calibration.json")
    core = Core(data_dir)

    @contextlib.asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(stream(core, ui, args))
        yield
        task.cancel()

    ui = SimWebUI(ROOT / "app" / "assets", lifespan=lifespan)
    register(ui, core)
    ui.mount_assets()
    print(f"open-fp simulator: http://localhost:{args.port}  (data: {data_dir})")
    uvicorn.run(ui.app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
