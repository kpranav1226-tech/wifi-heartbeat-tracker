import numpy as np

from acquisition.resampler import is_uniform, resample_uniform
from acquisition.simulator import scenario_kwargs, simulate_csi
from core.config import DEFAULT_CONFIG as CFG
from core.data_models import CSIRecording
from pipeline import process_window


def test_uniform_detection():
    assert is_uniform(np.arange(0, 10, 0.01), 100.0)
    assert not is_uniform(np.sort(np.random.default_rng(0).uniform(0, 10, 500)), 100.0)


def test_resample_recovers_sine_from_irregular_samples():
    rng = np.random.default_rng(1)
    t = np.sort(rng.uniform(0, 20, 1500))
    csi = np.exp(2j * np.pi * 1.0 * t)[:, None]
    out = resample_uniform(CSIRecording(csi, 100.0, t))
    expected = np.exp(2j * np.pi * 1.0 * (out.timestamps - t[0]) + 2j * np.pi * 1.0 * t[0])
    assert np.abs(out.csi[:, 0] - expected)[50:-50].max() < 0.05
    assert is_uniform(out.timestamps, 100.0)


def test_pipeline_handles_packet_loss():
    rec = simulate_csi(duration_s=30, heart_bpm=80, seed=4, **scenario_kwargs("packet_loss", 80))
    assert not is_uniform(rec.timestamps, rec.sample_rate_hz)
    res = process_window(rec, CFG)[0]
    assert res.accepted and abs(res.bpm - 80) <= 3


def test_long_gap_is_rejected():
    rec = simulate_csi(duration_s=30, heart_bpm=80, seed=4)
    keep = np.ones(rec.n_samples, bool)
    keep[1000:1200] = False                       # 2 s of missing packets
    gappy = CSIRecording(rec.csi[keep], rec.sample_rate_hz, rec.timestamps[keep])
    res = process_window(gappy, CFG)[0]
    assert not res.accepted and "gap" in res.reason


def test_window_uses_timestamps():
    rec = simulate_csi(duration_s=30, seed=1, **scenario_kwargs("packet_loss", 72))
    w = rec.window(5.0, 10.0)
    assert 9.5 <= w.timestamps[-1] - w.timestamps[0] <= 10.0
