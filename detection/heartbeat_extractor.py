"""Turn a CSI window into heartbeat-band and breathing-band signals."""
from __future__ import annotations

import numpy as np

from core.config import Config, DEFAULT_CONFIG
from core.data_models import CSIRecording
from processing.denoising import detrend, pca_first_component, select_subcarriers
from processing.filtering import bandpass, hampel
from processing.normalisation import zscore


def _filtered(rec: CSIRecording, band: tuple[float, float]) -> np.ndarray:
    amp = detrend(hampel(rec.amplitude))
    return bandpass(amp, rec.sample_rate_hz, *band)


def _extract(rec: CSIRecording, band: tuple[float, float]) -> np.ndarray:
    return zscore(pca_first_component(_filtered(rec, band)))


def heart_band_matrix(rec: CSIRecording, cfg: Config = DEFAULT_CONFIG) -> np.ndarray:
    """Heart-band filtered amplitude per subcarrier, shape (n_samples, n_subcarriers)."""
    m = _filtered(rec, cfg.heart_band_hz)
    return m[:, select_subcarriers(m)]


def extract_heartbeat(rec: CSIRecording, cfg: Config = DEFAULT_CONFIG) -> np.ndarray:
    """amplitude -> outlier removal -> detrend -> heart-band filter -> PCA -> z-score."""
    return zscore(pca_first_component(heart_band_matrix(rec, cfg)))


def extract_breathing(rec: CSIRecording, cfg: Config = DEFAULT_CONFIG) -> np.ndarray:
    """Same chain in the breathing band; used to locate breathing harmonics."""
    return _extract(rec, cfg.breath_band_hz)
