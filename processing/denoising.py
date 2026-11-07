from __future__ import annotations

import numpy as np
from scipy.signal import detrend as _detrend


def detrend(x: np.ndarray) -> np.ndarray:
    """Remove linear trend (and mean) along axis 0."""
    return _detrend(x, axis=0, type="linear")


def pca_first_component(x: np.ndarray) -> np.ndarray:
    """Combine subcarriers (n_samples, n_subcarriers) into one signal via PCA."""
    x = x - x.mean(axis=0, keepdims=True)
    _, _, vt = np.linalg.svd(x, full_matrices=False)
    return x @ vt[0]


def select_subcarriers(matrix: np.ndarray, min_rel_power: float = 0.1, min_keep: int = 3) -> np.ndarray:
    """Boolean mask of subcarriers worth keeping (shape (n_subcarriers,)).

    Drops dead or insensitive subcarriers whose band power is below
    `min_rel_power` x the median, so they do not add noise to PCA.
    """
    power = matrix.var(axis=0)
    mask = power >= min_rel_power * np.median(power)
    if mask.sum() < min_keep:
        mask = np.zeros_like(mask)
        mask[np.argsort(power)[-min_keep:]] = True
    return mask
