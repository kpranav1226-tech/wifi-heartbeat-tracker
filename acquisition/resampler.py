"""Turn irregularly timed packets into an evenly sampled recording."""
from __future__ import annotations

import numpy as np

from core.data_models import CSIRecording


def is_uniform(timestamps: np.ndarray, fs: float, tol: float = 0.25) -> bool:
    """True if every sample interval is within `tol` (fraction) of 1/fs."""
    dt = np.diff(timestamps)
    return bool(len(dt) > 0 and np.all(np.abs(dt * fs - 1.0) < tol))


def resample_uniform(rec: CSIRecording, fs: float | None = None) -> CSIRecording:
    """Linear interpolation of real and imaginary parts onto a uniform grid.

    The longest gap between received packets is stored in metadata["max_gap_s"]
    so callers can refuse windows where too much data is missing.
    """
    if rec.timestamps is None:
        raise ValueError("recording has no timestamps to resample")
    fs = fs or rec.sample_rate_hz
    ts = np.asarray(rec.timestamps, dtype=float)
    rel = ts - ts[0]
    grid = np.arange(int(np.floor(rel[-1] * fs)) + 1) / fs
    out = np.empty((len(grid), rec.n_subcarriers), dtype=complex)
    for k in range(rec.n_subcarriers):
        out[:, k] = np.interp(grid, rel, rec.csi[:, k].real) + 1j * np.interp(grid, rel, rec.csi[:, k].imag)
    meta = {**rec.metadata, "resampled": True, "max_gap_s": float(np.max(np.diff(rel)))}
    return CSIRecording(out, fs, grid + ts[0], meta)
