"""Shared data structures passed between pipeline stages."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class CSIRecording:
    """Complex CSI over time. Shape of `csi`: (n_samples, n_subcarriers)."""

    csi: np.ndarray
    sample_rate_hz: float
    timestamps: np.ndarray | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def n_samples(self) -> int:
        return self.csi.shape[0]

    @property
    def n_subcarriers(self) -> int:
        return self.csi.shape[1]

    @property
    def duration_s(self) -> float:
        if self.timestamps is not None and len(self.timestamps) > 1:
            return float(self.timestamps[-1] - self.timestamps[0]) + 1.0 / self.sample_rate_hz
        return self.n_samples / self.sample_rate_hz

    @property
    def amplitude(self) -> np.ndarray:
        return np.abs(self.csi)

    @property
    def phase(self) -> np.ndarray:
        """Phase unwrapped along time, per subcarrier."""
        return np.unwrap(np.angle(self.csi), axis=0)

    def window(self, start_s: float, length_s: float) -> "CSIRecording":
        if self.timestamps is not None:
            t0 = self.timestamps[0] + start_s
            i0 = int(np.searchsorted(self.timestamps, t0, side="left"))
            i1 = int(np.searchsorted(self.timestamps, t0 + length_s, side="left"))
            return CSIRecording(self.csi[i0:i1], self.sample_rate_hz, self.timestamps[i0:i1], dict(self.metadata))
        i0 = int(round(start_s * self.sample_rate_hz))
        i1 = i0 + int(round(length_s * self.sample_rate_hz))
        ts = None if self.timestamps is None else self.timestamps[i0:i1]
        return CSIRecording(self.csi[i0:i1], self.sample_rate_hz, ts, dict(self.metadata))


@dataclass
class BPMResult:
    bpm: float | None          # None when rejected
    quality: float             # 0..1
    accepted: bool
    peak_freq_hz: float | None = None
    reason: str = ""
    breath_bpm: float | None = None
