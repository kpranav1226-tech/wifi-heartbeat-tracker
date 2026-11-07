from core.data_models import BPMResult
from detection.tracker import BPMTracker


def ok(bpm):
    return BPMResult(bpm=bpm, quality=0.9, accepted=True)


def bad():
    return BPMResult(bpm=None, quality=0.1, accepted=False, reason="x")


def test_starts_searching_then_tracks():
    t = BPMTracker()
    assert t.update(bad()).state == "searching" and t.update(bad()).bpm is None
    assert t.update(ok(70)).bpm == 70


def test_smooths_small_changes():
    t = BPMTracker(alpha=0.5)
    t.update(ok(70))
    assert abs(t.update(ok(74)).bpm - 72) < 1e-9


def test_single_outlier_is_ignored():
    t = BPMTracker()
    t.update(ok(70))
    r = t.update(ok(110))
    assert r.state == "holding" and abs(r.bpm - 70) < 1e-9
    assert abs(t.update(ok(71)).bpm - 70.3) < 1e-9


def test_relocks_after_consistent_new_value():
    t = BPMTracker(relock_after=4)
    t.update(ok(70))
    states = [t.update(ok(100)).state for _ in range(4)]
    assert states[-1] == "relocked" and abs(t.update(ok(100)).bpm - 100) < 1


def test_holds_then_reports_lost():
    t = BPMTracker(hold_updates=3)
    t.update(ok(70))
    assert [t.update(bad()).state for _ in range(3)] == ["holding"] * 3
    r = t.update(bad())
    assert r.state == "lost" and r.bpm is None
