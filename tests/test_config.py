import json

import pytest

from core.config import Config
from processing.denoising import select_subcarriers
import numpy as np


def test_config_from_file(tmp_path):
    f = tmp_path / "c.json"
    f.write_text(json.dumps({"window_seconds": 20, "heart_band_hz": [0.8, 2.0], "db_path": "x/y.db"}))
    c = Config.from_file(f)
    assert c.window_seconds == 20 and c.heart_band_hz == (0.8, 2.0) and c.sample_rate_hz == 100.0


def test_config_rejects_unknown_keys(tmp_path):
    f = tmp_path / "c.json"
    f.write_text(json.dumps({"windw_seconds": 20}))
    with pytest.raises(ValueError):
        Config.from_file(f)


def test_select_subcarriers_drops_dead_ones():
    rng = np.random.default_rng(0)
    m = rng.normal(0, 1.0, (500, 10))
    m[:, 3] *= 0.01                      # dead subcarrier
    mask = select_subcarriers(m)
    assert not mask[3] and mask.sum() == 9
