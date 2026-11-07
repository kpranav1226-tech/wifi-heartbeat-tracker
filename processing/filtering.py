from __future__ import annotations

import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import butter, sosfiltfilt


def bandpass(x: np.ndarray, fs: float, low: float, high: float, order: int = 4) -> np.ndarray:
    """Zero-phase Butterworth bandpass along axis 0."""
    sos = butter(order, [low, high], btype="bandpass", fs=fs, output="sos")
    return sosfiltfilt(sos, x, axis=0)


def hampel(x: np.ndarray, window: int = 11, n_sigmas: float = 3.0) -> np.ndarray:
    """Replace outliers (vs. rolling median/MAD) with the rolling median, along axis 0."""
    size = (window,) + (1,) * (x.ndim - 1)
    med = median_filter(x, size=size, mode="nearest")
    mad = 1.4826 * median_filter(np.abs(x - med), size=size, mode="nearest")
    outliers = np.abs(x - med) > n_sigmas * np.maximum(mad, 1e-12)
    return np.where(outliers, med, x)
