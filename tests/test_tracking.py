import pytest

from tracking.bpm_smoother import BPMTracker


def test_median_smooths_values_and_holds_during_rejection():
    tracker = BPMTracker(window_size=3, max_jump_bpm=15)
    assert tracker.update(70) == 70
    assert tracker.update(72) == 71
    assert tracker.update(71) == 71
    assert tracker.update(110) == 71
    assert tracker.update(None) == 71


def test_tracker_reset_and_validation():
    tracker = BPMTracker()
    tracker.update(80)
    tracker.reset()
    assert tracker.value is None
    with pytest.raises(ValueError):
        BPMTracker(window_size=0)