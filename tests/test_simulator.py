import numpy as np

from acquisition.simulator import simulate_csi


def test_shape_dtype_and_metadata():
    rec = simulate_csi(duration_s=10, sample_rate_hz=100, n_subcarriers=8, heart_bpm=70, seed=1)
    assert rec.csi.shape == (1000, 8)
    assert np.iscomplexobj(rec.csi)
    assert rec.metadata["true_bpm"] == 70


def test_seed_is_deterministic():
    a = simulate_csi(duration_s=5, seed=42)
    b = simulate_csi(duration_s=5, seed=42)
    assert np.array_equal(a.csi, b.csi)


def test_different_seeds_differ():
    assert not np.array_equal(simulate_csi(duration_s=5, seed=1).csi, simulate_csi(duration_s=5, seed=2).csi)
