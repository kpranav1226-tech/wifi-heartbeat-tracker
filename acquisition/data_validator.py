"""Sanity checks before any processing."""
from __future__ import annotations

import numpy as np

from core.data_models import CSIRecording


class ValidationError(ValueError):
    pass


def find_issues(rec: CSIRecording, min_duration_s: float = 10.0) -> list[str]:
    issues: list[str] = []
    if rec.csi.ndim != 2:
        return [f"csi must be 2-D (samples, subcarriers), got {rec.csi.ndim}-D"]
    if not np.iscomplexobj(rec.csi):
        issues.append("csi must be complex-valued")
    if not np.all(np.isfinite(rec.csi)):
        issues.append("csi contains NaN or inf")
    if rec.sample_rate_hz <= 0:
        issues.append("sample rate must be positive")
    if rec.duration_s < min_duration_s:
        issues.append(f"recording too short ({rec.duration_s:.1f}s < {min_duration_s}s)")
    if rec.timestamps is not None:
        if len(rec.timestamps) != rec.n_samples:
            issues.append("timestamps length does not match samples")
        elif np.any(np.diff(rec.timestamps) <= 0):
            issues.append("timestamps must be strictly increasing")
    return issues


def ensure_valid(rec: CSIRecording, min_duration_s: float = 10.0) -> None:
    issues = find_issues(rec, min_duration_s)
    if issues:
        raise ValidationError("; ".join(issues))
