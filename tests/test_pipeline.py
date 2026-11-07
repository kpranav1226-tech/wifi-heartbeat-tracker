import pytest

from acquisition.simulator import simulate_csi
from core.config import DEFAULT_CONFIG as CFG
from pipeline import process_window


@pytest.mark.parametrize("bpm", [55, 72, 95, 110])
def test_estimates_simulated_bpm(bpm):
    rec = simulate_csi(duration_s=CFG.window_seconds, heart_bpm=bpm, outlier_rate=0.001, seed=7)
    result, *_ = process_window(rec, CFG)
    assert result.accepted
    assert abs(result.bpm - bpm) <= 2.0


def test_rejects_when_no_heartbeat_present():
    rec = simulate_csi(duration_s=CFG.window_seconds, heart_amp=0.0, seed=7)
    result, *_ = process_window(rec, CFG)
    assert not result.accepted and result.bpm is None
