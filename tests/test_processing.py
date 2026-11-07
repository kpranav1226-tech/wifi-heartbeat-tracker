import numpy as np

from processing.filtering import bandpass, hampel
from processing.normalisation import zscore


def test_bandpass_keeps_in_band_and_kills_out_of_band():
    fs = 100.0
    t = np.arange(0, 30, 1 / fs)
    inband, outband = np.sin(2 * np.pi * 1.2 * t), np.sin(2 * np.pi * 0.2 * t)
    y = bandpass(inband + outband, fs, 0.8, 2.0)
    assert np.corrcoef(y, inband)[0, 1] > 0.99


def test_hampel_removes_spike():
    x = np.sin(np.linspace(0, 6, 300))
    x[150] = 50.0
    assert abs(hampel(x)[150]) < 2.0


def test_zscore():
    z = zscore(np.random.default_rng(0).normal(5, 3, 1000))
    assert abs(z.mean()) < 1e-9 and abs(z.std() - 1) < 1e-6
