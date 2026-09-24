"""Swing persistence (§9.7): <id>.json (metadata, events, metrics) + <id>.npz (arrays)."""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

import numpy as np

from .config import CHANNEL_IDS
from .swing import Swing

ID_RE = re.compile(r"^\d{8}-\d{6}-\d{3}(-\d{1,4})?$")
ARRAY_KEYS = ("t", "forces", "fz_L", "fz_R", "cop_L", "cop_R", "cop_C", "lead_pct")


class SwingStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _paths(self, swing_id: str) -> tuple[Path, Path]:
        if not isinstance(swing_id, str) or not ID_RE.match(swing_id):
            raise KeyError(swing_id)
        return self.root / f"{swing_id}.json", self.root / f"{swing_id}.npz"

    def save(self, sw: Swing) -> None:
        meta_path, npz_path = self._paths(sw.id)
        meta = {**sw.summary(), "t0_host": sw.t0_host}
        tmp_npz = npz_path.with_name(npz_path.stem + ".tmp.npz")
        np.savez_compressed(tmp_npz, **{k: sw.arrays[k] for k in ARRAY_KEYS})
        tmp_npz.replace(npz_path)
        tmp = meta_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(meta, allow_nan=False), encoding="utf-8")
        tmp.replace(meta_path)

    def _meta(self, swing_id: str) -> dict:
        meta_path, _ = self._paths(swing_id)
        if not meta_path.exists():
            raise KeyError(swing_id)
        return json.loads(meta_path.read_text(encoding="utf-8"))

    def load_swing(self, swing_id: str) -> Swing:
        meta = self._meta(swing_id)
        _, npz_path = self._paths(swing_id)
        with np.load(npz_path) as z:
            arrays = {k: z[k] for k in ARRAY_KEYS}
        return Swing(id=meta["id"], created=meta["created"], golfer=meta["golfer"],
                     bw_n=meta["bw_n"], t0_host=meta["t0_host"], arrays=arrays,
                     events=meta["events"], metrics=meta["metrics"],
                     impact_source=meta.get("impact_source"))

    def get(self, swing_id: str) -> dict:
        return self.load_swing(swing_id).to_dict()

    def list(self) -> list[dict]:
        out = []
        for p in self.root.glob("*.json"):
            if not ID_RE.match(p.stem):
                continue
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        out.sort(key=lambda m: (m.get("created") or "", m["id"]), reverse=True)
        return out

    def delete(self, swing_id: str) -> bool:
        paths = self._paths(swing_id)
        found = False
        for p in paths:
            if p.exists():
                p.unlink()
                found = True
        return found

    def csv(self, swing_id: str) -> str:
        a = self.load_swing(swing_id).arrays
        header = (["t_s", "lead_pct", "fz_L_n", "fz_R_n"]
                  + [f"cop_{k}_{c}_mm" for k in ("L", "R", "C") for c in ("x", "y")]
                  + [f"{ch}_n" for ch in CHANNEL_IDS])
        cols = np.column_stack([a["t"], a["lead_pct"], a["fz_L"], a["fz_R"],
                                a["cop_L"], a["cop_R"], a["cop_C"], a["forces"]])
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(header)
        for row in cols:
            w.writerow([_csv_cell(v, 4 if i == 0 else 2) for i, v in enumerate(row)])
        return buf.getvalue()


def _csv_cell(v: float, digits: int) -> str:
    return "" if np.isnan(v) else f"{v:.{digits}f}"
