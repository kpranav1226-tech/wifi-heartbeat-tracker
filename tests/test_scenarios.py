"""Hard-case behaviour. The rule: never show a wrong BPM; rejecting is acceptable."""
import numpy as np
import pytest

from acquisition.simulator import SCENARIOS, scenario_kwargs, simulate_csi
from core.config import DEFAULT_CONFIG as CFG
from pipeline import process_window


def run(**kw):
    rec = simulate_csi(duration_s=CFG.window_seconds, **kw)
    return process_window(rec, CFG)[0]


def test_motion_burst_is_rejected():
    res = run(heart_bpm=75, motion_bursts=2, motion_amp=1.5, seed=3)
    assert not res.accepted and "motion" in res.reason


def test_two_equal_people_not_reported_as_one():
    res = run(heart_bpm=70, second_person_bpm=88, second_heart_amp=0.02, seed=5)
    assert not res.accepted


def test_strong_breathing_harmonics_never_give_wrong_bpm():
    for seed in range(8):
        bpm = 60 + 6 * seed
        res = run(heart_bpm=bpm, breath_harmonics=6, harmonic_decay=0.7, seed=seed)
        if res.accepted:
            assert abs(res.bpm - bpm) <= 3


def test_breathing_rate_is_estimated():
    res = run(heart_bpm=80, breath_bpm=16, seed=2)
    assert abs(res.breath_bpm - 16) <= 1.5


@pytest.mark.parametrize("name", SCENARIOS)
def test_no_false_accepts(name):
    for seed in range(6):
        bpm = 58 + 9 * seed
        rec = simulate_csi(duration_s=CFG.window_seconds, heart_bpm=bpm, seed=seed, **scenario_kwargs(name, bpm))
        res = process_window(rec, CFG)[0]
        if res.accepted:
            assert name != "no_subject"
            targets = [bpm]
            if name == "two_people":
                # Known limitation: if the other person's signal dominates, their BPM
                # can be reported. It must still match one of the two real heartbeats.
                targets.append(scenario_kwargs(name, bpm)["second_person_bpm"])
            assert min(abs(res.bpm - t) for t in targets) <= 3
