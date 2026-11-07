"""Reject unreliable readings instead of showing a misleading BPM."""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, find_peaks, sosfiltfilt

from processing.filtering import hampel


def detect_motion(amplitude: np.ndarray, fs: float, window_s: float = 1.0, ratio: float = 4.0) -> bool:
    """True if some 1-second stretch is far more energetic than the typical one.

    Looks above 0.6 Hz (above breathing) at per-window RMS across subcarriers.
    Limitation: movement lasting more than about half the window raises the
    median too and can slip through.
    """
    x = hampel(amplitude)
    x = x - x.mean(axis=0, keepdims=True)
    sos = butter(2, 0.6, btype="highpass", fs=fs, output="sos")
    hp = sosfiltfilt(sos, x, axis=0)
    w = max(1, int(fs * window_s))
    n_win = len(hp) // w
    if n_win < 6:
        return False
    r2 = (hp[: n_win * w] ** 2).mean(axis=1).reshape(n_win, w).mean(axis=1)
    rms = np.sqrt(r2)[1:-1]  # first/last window carry filter and median-filter edge effects
    return bool(rms.max() > ratio * np.median(rms))


def competing_peak_ratio(freqs: np.ndarray, psd: np.ndarray, peak_hz: float, exclusion_hz: float = 0.15) -> float:
    """Power of the strongest other peak relative to the main peak (0 = none)."""
    idx, _ = find_peaks(psd)
    idx = [i for i in idx if abs(freqs[i] - peak_hz) > exclusion_hz]
    if not idx:
        return 0.0
    return float(psd[idx].max() / psd.max())


def assess_quality(
    freqs: np.ndarray,
    psd: np.ndarray,
    peak_hz: float,
    min_quality: float = 0.5,
    peak_halfwidth_hz: float = 0.1,
    competing_threshold: float = 0.4,
    edge_guard_hz: float = 0.1,
    multi_psd: tuple[np.ndarray, np.ndarray] | None = None,
) -> tuple[float, bool, str]:
    """Quality = share of in-band power concentrated around the spectral peak (0..1)."""
    total = psd.sum()
    if total <= 0:
        return 0.0, False, "no power in heart band"
    near = np.abs(freqs - peak_hz) <= peak_halfwidth_hz
    quality = float(psd[near].sum() / total)
    if peak_hz <= freqs[0] + edge_guard_hz or peak_hz >= freqs[-1] - edge_guard_hz:
        return quality, False, "peak at band edge (likely leakage)"
    if multi_psd is not None:
        mf, mp = multi_psd
        if mp.max() > 0 and competing_peak_ratio(mf, mp, mf[int(np.argmax(mp))]) > competing_threshold:
            return quality, False, "multiple competing periodic sources (second person?)"
    if competing_peak_ratio(freqs, psd, peak_hz) > competing_threshold:
        return quality, False, "multiple competing periodic sources (second person?)"
    if quality < min_quality:
        return quality, False, f"no dominant periodic component (quality {quality:.2f})"
    return quality, True, ""
