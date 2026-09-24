"""Channel map, stance geometry, handedness and tunable thresholds.

Stance frame (mm, viewed from above): origin midway between plate centres, +x from
Plate L toward Plate R, +y toward the ball. See docs/PROJECT_INIT.md §5.
"""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path

CHANNEL_IDS = ("L1", "L2", "L3", "L4", "R1", "R2", "R3", "R4")
N_CH = len(CHANNEL_IDS)
PLATES = ("L", "R")

# Corner of each channel as (outward, toe) unit signs relative to its plate centre.
# "outward" is away from the stance centre: -x on Plate L, +x on Plate R.
_CORNERS = {
    "L1": (1, 1), "L2": (-1, 1), "L3": (-1, -1), "L4": (1, -1),
    "R1": (-1, 1), "R2": (1, 1), "R3": (1, -1), "R4": (-1, -1),
}


@dataclass
class SwingThresholds:
    """Swing state machine thresholds (§9.6). Tune on real data."""
    idle_total_pct_bw: float = 20.0      # below this total load -> idle
    idle_total_n: float = 100.0          # idle threshold when BW is not yet known
    address_foot_pct: float = 10.0       # each foot above this % of total
    address_total_tol_pct: float = 5.0   # total within +-this % while quiet
    address_cop_speed_mm_s: float = 20.0
    address_hold_s: float = 0.8
    motion_speed_mm_s: float = 50.0      # lateral CoP speed to start a swing
    motion_sustain_s: float = 0.05
    trigger_speed_mm_s: float = 300.0    # lateral CoP speed toward lead
    min_backswing_shift_pct: float = 5.0  # lead % must drop this far below address first
    min_foot_pct_bw: float = 2.0         # a foot below this before trigger = stepped, abort
    pre_roll_s: float = 0.5
    post_trigger_s: float = 1.5
    max_capture_s: float = 6.0
    finish_speed_mm_s: float = 30.0
    finish_hold_s: float = 0.3


@dataclass
class Config:
    golfer: str = "RH"                   # "RH" | "LH"
    plate_spacing_mm: float = 369.6      # plate centre to plate centre; measure after setup
    cell_offset_mm: float = 122.4        # cell centre from plate centre, in x and y
    positions_mm: list[list[float]] | None = None  # explicit per-channel (x, y) override
    signs: list[int] = field(default_factory=lambda: [1] * N_CH)
    bw_override_n: float | None = None
    cop_min_force_n: float = 20.0        # CoP is NaN below this plate load
    swing: SwingThresholds = field(default_factory=SwingThresholds)

    def __post_init__(self):
        if self.golfer not in ("RH", "LH"):
            raise ValueError(f"golfer must be 'RH' or 'LH', got {self.golfer!r}")
        if len(self.signs) != N_CH or any(s not in (1, -1) for s in self.signs):
            raise ValueError("signs must be 8 values of +1 or -1")
        if self.positions_mm is not None and (
            len(self.positions_mm) != N_CH or any(len(p) != 2 for p in self.positions_mm)
        ):
            raise ValueError("positions_mm must be 8 [x, y] pairs")

    def positions(self) -> list[tuple[float, float]]:
        if self.positions_mm is not None:
            return [(float(x), float(y)) for x, y in self.positions_mm]
        half = self.plate_spacing_mm / 2
        out = []
        for ch in CHANNEL_IDS:
            outward, toe = _CORNERS[ch]
            side = -1 if ch[0] == "L" else 1
            out.append((side * (half + outward * self.cell_offset_mm), toe * self.cell_offset_mm))
        return out

    def plate_channels(self, plate: str) -> list[int]:
        return [i for i, ch in enumerate(CHANNEL_IDS) if ch[0] == plate]

    @property
    def lead_plate(self) -> str:
        return "L" if self.golfer == "RH" else "R"

    @property
    def trail_plate(self) -> str:
        return "R" if self.golfer == "RH" else "L"

    @property
    def lead_dir_x(self) -> int:
        """Sign of x pointing from trail foot toward lead foot."""
        return -1 if self.lead_plate == "L" else 1

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def updated(self, changes: dict) -> "Config":
        """New validated Config with `changes` merged in (nested for `swing`)."""
        return _from_dict(_merge(self.to_dict(), changes))


def _merge(base: dict, changes: dict) -> dict:
    out = dict(base)
    for k, v in changes.items():
        if k not in out:
            raise ValueError(f"unknown config key {k!r}")
        if isinstance(out[k], dict) and isinstance(v, dict):
            unknown = set(v) - set(out[k])
            if unknown:
                raise ValueError(f"unknown config keys {sorted(unknown)} in {k!r}")
            out[k] = {**out[k], **v}
        else:
            out[k] = v
    return out


def _from_dict(d: dict) -> Config:
    return Config(**{**d, "swing": SwingThresholds(**d["swing"])})


def load_config(path: str | Path) -> Config:
    path = Path(path)
    if not path.exists():
        return Config()
    return Config().updated(json.loads(path.read_text(encoding="utf-8")))


def save_config(cfg: Config, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg.to_dict(), indent=2), encoding="utf-8")
    tmp.replace(path)
