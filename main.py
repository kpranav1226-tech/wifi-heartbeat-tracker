"""Entry point.

    python main.py                                  # launch the dashboard
    python main.py --cli --bpm 72                   # headless run on simulated data
    python main.py --config config.json --verbose   # custom settings, debug logging
"""
from __future__ import annotations

import argparse
import logging
import sys

from core.config import Config, DEFAULT_CONFIG


def run_cli(cfg: Config, bpm: float, seed: int | None) -> None:
    from acquisition.simulator import simulate_csi
    from pipeline import process_window

    rec = simulate_csi(
        duration_s=cfg.window_seconds, sample_rate_hz=cfg.sample_rate_hz,
        n_subcarriers=cfg.n_subcarriers, heart_bpm=bpm, seed=seed,
    )
    result, *_ = process_window(rec, cfg)
    print(f"True BPM:      {bpm}")
    print(f"Estimated BPM: {result.bpm}")
    print(f"Quality:       {result.quality:.2f}  accepted={result.accepted}  {result.reason}")


def run_gui(cfg: Config) -> None:
    from PySide6.QtWidgets import QApplication
    from interface.dashboard import Dashboard

    app = QApplication(sys.argv)
    win = Dashboard(cfg)
    win.resize(1000, 800)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--cli", action="store_true", help="run headless on simulated data")
    p.add_argument("--bpm", type=float, default=72.0)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--config", help="JSON file overriding defaults in core/config.py")
    p.add_argument("--verbose", action="store_true", help="log why windows are rejected")
    args = p.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    cfg = Config.from_file(args.config) if args.config else DEFAULT_CONFIG
    run_cli(cfg, args.bpm, args.seed) if args.cli else run_gui(cfg)
