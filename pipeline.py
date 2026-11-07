"""Glue: one CSI window in, one BPMResult out."""
from __future__ import annotations

import logging

import numpy as np

from acquisition.data_validator import ensure_valid
from acquisition.resampler import is_uniform, resample_uniform
from core.config import Config, DEFAULT_CONFIG
from core.data_models import BPMResult, CSIRecording
from detection.bpm_estimator import aggregate_psd, estimate_bpm, estimate_breath_hz
from detection.heartbeat_extractor import extract_breathing, extract_heartbeat, heart_band_matrix
from detection.quality_assessor import assess_quality, detect_motion

log = logging.getLogger(__name__)


def process_window(rec: CSIRecording, cfg: Config = DEFAULT_CONFIG, min_duration_s: float = 10.0):
    """Returns (BPMResult, heartbeat_signal, freqs, psd)."""
    ensure_valid(rec, min_duration_s)

    if rec.timestamps is not None and not is_uniform(rec.timestamps, rec.sample_rate_hz):
        rec = resample_uniform(rec)
        gap = rec.metadata["max_gap_s"]
        if gap > cfg.max_gap_s:
            log.debug("rejected: packet gap %.2fs", gap)
            result = BPMResult(None, 0.0, False, reason=f"packet gap of {gap:.2f}s (too much data missing)")
            return result, np.zeros(rec.n_samples), np.array([]), np.array([])

    fs = rec.sample_rate_hz
    breath_hz = estimate_breath_hz(extract_breathing(rec, cfg), fs, cfg.breath_band_hz)
    harmonics = tuple(k * breath_hz for k in range(2, cfg.max_breath_harmonic + 1) if k * breath_hz <= cfg.heart_band_hz[1] + 0.1)

    signal = extract_heartbeat(rec, cfg)
    bpm, peak, freqs, psd = estimate_bpm(signal, fs, cfg.heart_band_hz, exclude_hz=harmonics)
    multi = aggregate_psd(heart_band_matrix(rec, cfg), fs, cfg.heart_band_hz, exclude_hz=harmonics)
    quality, ok, reason = assess_quality(freqs, psd, peak, cfg.min_quality, multi_psd=multi)

    if detect_motion(rec.amplitude, fs):
        ok, reason = False, "body motion detected"

    if not ok:
        log.debug("rejected: %s", reason)
    return BPMResult(
        bpm=round(bpm, 1) if ok else None,
        quality=quality,
        accepted=ok,
        peak_freq_hz=float(peak),
        reason=reason,
        breath_bpm=round(breath_hz * 60, 1),
    ), signal, freqs, psd
