from __future__ import annotations

import numpy as np


def zscore(x: np.ndarray, axis: int = 0, eps: float = 1e-12) -> np.ndarray:
    return (x - x.mean(axis=axis, keepdims=True)) / (x.std(axis=axis, keepdims=True) + eps)
