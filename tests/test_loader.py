import numpy as np
import pytest

from acquisition.csi_loader import FileCSISource, save_recording
from acquisition.data_validator import ValidationError, ensure_valid, find_issues
from acquisition.simulator import simulate_csi


def test_roundtrip(tmp_path):
    rec = simulate_csi(duration_s=12, seed=3)
    path = tmp_path / "rec.npz"
    save_recording(rec, path)
    back = FileCSISource(path).load()
    assert np.allclose(back.csi, rec.csi)
    assert back.sample_rate_hz == rec.sample_rate_hz


def test_validator_accepts_good_data():
    ensure_valid(simulate_csi(duration_s=12, seed=3))


def test_validator_rejects_nan_and_short():
    rec = simulate_csi(duration_s=12, seed=3)
    rec.csi[5, 2] = np.nan
    assert any("NaN" in i for i in find_issues(rec))
    with pytest.raises(ValidationError):
        ensure_valid(simulate_csi(duration_s=2, seed=3))
