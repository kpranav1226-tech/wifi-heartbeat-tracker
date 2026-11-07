"""Robust rolling-median BPM smoother with a simple jump gate."""
from __future__ import annotations

from collections import deque


class BPMTracker:
    """Smooth accepted values and hold the last value across outliers/rejections.

    A value farther than max_jump_bpm from the current median is rejected. A
    rejected/None value does not alter state. `reset` starts a new recording.
    """
    def __init__(self, window_size: int = 5, max_jump_bpm: float = 15.0):
        if window_size < 1:
            raise ValueError("window_size must be at least 1")
        if max_jump_bpm <= 0:
            raise ValueError("max_jump_bpm must be positive")
        self.window_size = window_size
        self.max_jump_bpm = max_jump_bpm
        self._values: deque[float] = deque(maxlen=window_size)

    @property
    def value(self) -> float | None:
        return self._median() if self._values else None

    def _median(self) -> float:
        ordered = sorted(self._values)
        mid = len(ordered) // 2
        return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2

    def update(self, bpm: float | None) -> float | None:
        if bpm is None:
            return self.value
        bpm = float(bpm)
        if not 0 < bpm < 300:
            raise ValueError("bpm must be between 0 and 300")
        if self._values and abs(bpm - self._median()) > self.max_jump_bpm:
            return self.value
        self._values.append(bpm)
        return self.value

    def reset(self) -> None:
        self._values.clear()