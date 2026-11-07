"""Accuracy benchmark over the simulator scenarios.

    python benchmark.py            # 30 trials per scenario
    python benchmark.py --trials 100

'false accept' = a BPM was shown that is wrong by more than 3 BPM
(or any BPM at all when there is no heartbeat). This is the number to minimise.
"""
from __future__ import annotations

import argparse

import numpy as np

from acquisition.simulator import SCENARIOS, scenario_kwargs, simulate_csi
from core.config import DEFAULT_CONFIG as CFG
from pipeline import process_window


def run(trials: int, tol: float = 3.0) -> None:
    rng = np.random.default_rng(0)
    print(f"{'scenario':<18}{'accepted':>10}{'MAE':>8}{'false accepts':>15}")
    for name in SCENARIOS:
        accepted, errs, false_acc = 0, [], 0
        for i in range(trials):
            bpm = float(rng.uniform(55, 110))
            rec = simulate_csi(
                duration_s=CFG.window_seconds, sample_rate_hz=CFG.sample_rate_hz,
                n_subcarriers=CFG.n_subcarriers, heart_bpm=bpm,
                breath_bpm=float(rng.uniform(10, 22)), seed=i, **scenario_kwargs(name, bpm),
            )
            res, *_ = process_window(rec, CFG)
            if not res.accepted:
                continue
            accepted += 1
            if name == "no_subject":
                false_acc += 1
                continue
            err = abs(res.bpm - bpm)
            errs.append(err)
            false_acc += err > tol
        mae = f"{np.mean(errs):.2f}" if errs else "-"
        print(f"{name:<18}{accepted / trials:>9.0%}{mae:>8}{false_acc:>15}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=30)
    run(ap.parse_args().trials)
