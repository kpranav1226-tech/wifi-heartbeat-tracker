from __future__ import annotations

import numpy as np
from scipy.signal import periodogram


def estimate_bpm(
    signal: np.ndarray,
    fs: float,
    band_hz: tuple[float, float],
    nfft: int = 2**16,
    exclude_hz: tuple[float, ...] = (),
    exclude_halfwidth_hz: float = 0.05,
):
    """Return (bpm, peak_freq_hz, freqs_in_band, psd_in_band).

    Frequencies in `exclude_hz` (e.g. breathing harmonics) are zeroed before the
    peak is chosen so they cannot be mistaken for the heartbeat.
    """
    freqs, psd = periodogram(signal, fs=fs, window="hann", nfft=nfft)
    mask = (freqs >= band_hz[0]) & (freqs <= band_hz[1])
    freqs, psd = freqs[mask], psd[mask].copy()
    for f in exclude_hz:
        psd[np.abs(freqs - f) <= exclude_halfwidth_hz] = 0.0
    peak = freqs[int(np.argmax(psd))]
    return peak * 60.0, peak, freqs, psd


def estimate_breath_hz(signal: np.ndarray, fs: float, band_hz: tuple[float, float], nfft: int = 2**16) -> float:
    freqs, psd = periodogram(signal, fs=fs, window="hann", nfft=nfft)
    mask = (freqs >= band_hz[0]) & (freqs <= band_hz[1])
    return float(freqs[mask][int(np.argmax(psd[mask]))])


def aggregate_psd(matrix: np.ndarray, fs: float, band_hz: tuple[float, float], nfft: int = 2**16,
                  exclude_hz: tuple[float, ...] = (), exclude_halfwidth_hz: float = 0.05):
    """Sum of per-subcarrier spectra. Unlike PCA it shows every periodic source,
    which is what the multi-person check needs. Returns (freqs_in_band, psd_in_band)."""
    freqs, psd = periodogram(matrix, fs=fs, window="hann", nfft=nfft, axis=0)
    psd = psd.sum(axis=1)
    mask = (freqs >= band_hz[0]) & (freqs <= band_hz[1])
    freqs, psd = freqs[mask], psd[mask].copy()
    for f in exclude_hz:
        psd[np.abs(freqs - f) <= exclude_halfwidth_hz] = 0.0
    return freqs, psd
