"""Central configuration. Change defaults here, not inside modules."""
from __future__ import annotations

import json
from dataclasses import dataclass, fields
from pathlib import Path


@dataclass(frozen=True)
class Config:
    sample_rate_hz: float = 100.0
    window_seconds: float = 30.0
    n_subcarriers: int = 30

    # Physiological bands (Hz)
    heart_band_hz: tuple[float, float] = (0.7, 2.2)    # 42-132 BPM (outer 0.1 Hz is a guard band)
    breath_band_hz: tuple[float, float] = (0.1, 0.5)   # 6-30 breaths/min

    # Breathing harmonics up to this order are notched out of the heart band.
    # Higher orders catch more breathing artefacts but also hide more real heart rates.
    max_breath_harmonic: int = 6

    # Windows with a packet gap longer than this (seconds) are rejected
    max_gap_s: float = 0.5

    # Quality gate: readings scoring below this are rejected, not displayed
    min_quality: float = 0.5

    data_dir: Path = Path("data")
    db_path: Path = Path("data/heartbeat.db")

    @classmethod
    def from_file(cls, path) -> "Config":
        """Load overrides from a JSON file; unspecified fields keep their defaults."""
        data = json.loads(Path(path).read_text())
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"unknown config keys: {sorted(unknown)}")
        for key in ("heart_band_hz", "breath_band_hz"):
            if key in data:
                data[key] = tuple(data[key])
        for key in ("data_dir", "db_path"):
            if key in data:
                data[key] = Path(data[key])
        return cls(**data)


DEFAULT_CONFIG = Config()
