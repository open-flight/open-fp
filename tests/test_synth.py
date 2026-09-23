import numpy as np
import pytest

from open_fp.config import Config
from synth import corner_forces


@pytest.mark.parametrize("plate", ["L", "R"])
def test_corner_forces_reproduce_total_and_cop(plate):
    cfg = Config()
    idx = cfg.plate_channels(plate)
    pos = np.asarray(cfg.positions())[idx]
    for xy in [pos.mean(axis=0), pos[0], pos.mean(axis=0) + [30, -50]]:
        f = corner_forces(cfg, plate, xy, 700.0)
        assert f.shape == (8,)
        assert f.sum() == pytest.approx(700.0)
        assert f[idx] @ pos / f.sum() == pytest.approx(xy)
        other = [i for i in range(8) if i not in idx]
        assert np.all(f[other] == 0)
