"""Synthetic CSI generator with known ground truth.

Model per subcarrier k:
    m_k(t)   = g_k * motion(t) + g2_k * motion2(t)
    csi_k(t) = static_k * (1 + m_k) * exp(j * coupling * m_k) + drift + noise

`g_k` is a random per-subcarrier sensitivity, so some subcarriers respond
strongly to chest motion and others barely at all (as in real CSI).

Hard-case switches:
  * breath_harmonics / harmonic_decay : breathing harmonics that land in the heart band
  * motion_bursts / motion_amp        : short bursts of large body movement
  * second_person_bpm                 : a second subject with their own heartbeat
  * drop_rate / jitter_std_s          : lost packets and irregular arrival times
"""
from __future__ import annotations

import numpy as np

from core.data_models import CSIRecording


def _band_noise(rng: np.random.Generator, n: int, fs: float, low: float, high: float) -> np.ndarray:
    spec = np.fft.rfft(rng.normal(size=n))
    f = np.fft.rfftfreq(n, 1 / fs)
    spec[(f < low) | (f > high)] = 0
    x = np.fft.irfft(spec, n)
    return x / (x.std() + 1e-12)


def simulate_csi(
    duration_s: float = 60.0,
    sample_rate_hz: float = 100.0,
    n_subcarriers: int = 30,
    heart_bpm: float = 72.0,
    breath_bpm: float = 15.0,
    heart_amp: float = 0.02,
    breath_amp: float = 0.2,
    breath_harmonics: int = 2,
    harmonic_decay: float = 0.3,
    noise_std: float = 0.02,
    drift_std: float = 0.002,
    outlier_rate: float = 0.0,
    phase_coupling: float = 0.5,
    motion_bursts: int = 0,
    motion_burst_s: float = 2.0,
    motion_amp: float = 1.0,
    second_person_bpm: float | None = None,
    second_heart_amp: float = 0.02,
    second_breath_bpm: float = 18.0,
    drop_rate: float = 0.0,
    jitter_std_s: float = 0.0,
    seed: int | None = None,
) -> CSIRecording:
    rng = np.random.default_rng(seed)
    n = int(duration_s * sample_rate_hz)
    t = np.arange(n) / sample_rate_hz
    fs = sample_rate_hz
    if jitter_std_s > 0:                       # packets arrive at slightly irregular times
        t = np.sort(t + rng.normal(0, jitter_std_s, n))
    if drop_rate > 0:                          # packets lost in transit
        keep = rng.random(n) >= drop_rate
        keep[[0, -1]] = True
        t = t[keep]
        n = len(t)

    f_h, f_b = heart_bpm / 60.0, breath_bpm / 60.0
    heart = np.sin(2 * np.pi * f_h * t + rng.uniform(0, 2 * np.pi))
    breath = np.zeros(n)
    for h in range(1, breath_harmonics + 1):
        breath += harmonic_decay ** (h - 1) * np.sin(2 * np.pi * h * f_b * t + rng.uniform(0, 2 * np.pi))
    motion = breath_amp * breath + heart_amp * heart                      # (n,)

    if motion_bursts > 0:
        L = int(motion_burst_s * fs)
        for _ in range(motion_bursts):
            s = int(rng.uniform(0.05, 0.95) * (n - L))
            env = np.hanning(L)
            motion[s:s + L] += motion_amp * env * _band_noise(rng, L, fs, 0.3, 4.0)

    gains = rng.uniform(0.2, 1.0, n_subcarriers) * rng.choice([-1.0, 1.0], n_subcarriers)
    static = rng.uniform(0.8, 1.2, n_subcarriers) * np.exp(
        1j * rng.uniform(-np.pi, np.pi, n_subcarriers)
    )
    mod = np.outer(motion, gains)

    if second_person_bpm is not None:
        g2 = rng.uniform(0.2, 1.0, n_subcarriers) * rng.choice([-1.0, 1.0], n_subcarriers)
        h2 = np.sin(2 * np.pi * second_person_bpm / 60 * t + rng.uniform(0, 2 * np.pi))
        b2 = np.sin(2 * np.pi * second_breath_bpm / 60 * t + rng.uniform(0, 2 * np.pi))
        mod = mod + np.outer(breath_amp * 0.5 * b2 + second_heart_amp * h2, g2)

    csi = static * (1.0 + mod) * np.exp(1j * phase_coupling * mod)

    drift = np.cumsum(rng.normal(0, drift_std, (n, n_subcarriers)), axis=0)  # slow random walk
    sigma = noise_std / np.sqrt(2)
    noise = rng.normal(0, sigma, csi.shape) + 1j * rng.normal(0, sigma, csi.shape)
    csi = csi + drift + noise

    if outlier_rate > 0:
        mask = rng.random(csi.shape) < outlier_rate
        csi = csi + mask * rng.normal(0, 1.0, csi.shape) * 5 * noise_std * 10

    return CSIRecording(
        csi=csi.astype(np.complex128),
        sample_rate_hz=sample_rate_hz,
        timestamps=t,
        metadata={
            "source": "simulator", "true_bpm": heart_bpm, "true_breath_bpm": breath_bpm,
            "second_person_bpm": second_person_bpm, "seed": seed,
        },
    )


SCENARIOS = ("clean", "noisy", "strong_harmonics", "motion", "two_people", "no_subject", "packet_loss")


def scenario_kwargs(name: str, heart_bpm: float) -> dict:
    """Simulator settings for a named scenario."""
    if name == "clean":
        return {}
    if name == "noisy":
        return {"noise_std": 0.2}
    if name == "strong_harmonics":
        return {"breath_harmonics": 6, "harmonic_decay": 0.7}
    if name == "motion":
        return {"motion_bursts": 2, "motion_amp": 1.5}
    if name == "two_people":
        other = heart_bpm + 18 if heart_bpm <= 90 else heart_bpm - 18
        return {"second_person_bpm": other, "second_heart_amp": 0.02}
    if name == "packet_loss":
        return {"drop_rate": 0.2, "jitter_std_s": 0.002}
    if name == "no_subject":
        return {"heart_amp": 0.0}
    raise ValueError(f"unknown scenario: {name}")
