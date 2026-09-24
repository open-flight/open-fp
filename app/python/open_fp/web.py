"""HTTP API (§9.8) registered on anything with WebUI's `expose_api(method, path, fn)`.

Used with the board's WebUI brick and the simulator's stand-in. Handlers are FastAPI
routes, so path params and JSON bodies work the usual FastAPI way (VERIFIED.md #4).
Errors: unknown swing -> 404, invalid config -> 400, wizard/zero out of order -> 409.
"""
from __future__ import annotations

import functools

from fastapi import Body, HTTPException
from fastapi.responses import Response

from .app import Core


def _guard(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except KeyError as e:
            raise HTTPException(404, f"not found: {e.args[0] if e.args else ''}") from None
        except ValueError as e:
            raise HTTPException(400, str(e)) from None
        except RuntimeError as e:
            raise HTTPException(409, str(e)) from None
    return wrapper


def register(ui, core: Core) -> None:
    def api(method: str, path: str):
        def deco(fn):
            ui.expose_api(method, path, _guard(fn))
            return fn
        return deco

    @api("GET", "/api/status")
    def status():
        return core.status()

    @api("POST", "/api/zero")
    def zero():
        return core.zero()

    @api("GET", "/api/config")
    def get_config():
        return core.get_config()

    @api("PUT", "/api/config")
    def put_config(changes: dict = Body(...)):
        return core.put_config(changes)

    @api("POST", "/api/calib/start")
    def calib_start(body: dict = Body(...)):
        return core.calib_start(float(body["mass_kg"]))

    @api("POST", "/api/calib/capture")
    def calib_capture(step: dict = Body(...)):
        return core.calib_capture(step)

    @api("POST", "/api/calib/solve")
    def calib_solve():
        return core.calib_solve()

    @api("POST", "/api/calib/save")
    def calib_save():
        return core.calib_save()

    @api("POST", "/api/record/arm")
    def record_arm():
        return core.record_arm()

    @api("POST", "/api/record/trigger")
    def record_trigger():
        return core.record_trigger()

    @api("POST", "/api/events/shot")
    def shot(body: dict = Body(...)):
        return core.shot_event(float(body["t_unix_ms"]))

    @api("GET", "/api/swings")
    def swings():
        return core.swings()

    # Registered before /api/swings/{swing_id} so the .csv suffix isn't taken as an id.
    @api("GET", "/api/swings/{swing_id}.csv")
    def swing_csv(swing_id: str):
        disposition = f'attachment; filename="swing-{swing_id}.csv"'
        return Response(core.swing_csv(swing_id), media_type="text/csv",
                        headers={"Content-Disposition": disposition})

    @api("GET", "/api/swings/{swing_id}")
    def swing(swing_id: str):
        return core.swing(swing_id)

    @api("DELETE", "/api/swings/{swing_id}")
    def delete_swing(swing_id: str):
        return core.delete_swing(swing_id)
