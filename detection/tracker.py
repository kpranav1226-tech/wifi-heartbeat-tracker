"""Smooth BPM over successive windows and ignore isolated jumps."""
from __future__ import annotations

from dataclasses import dataclass

from core.data_models import BPMResult


@dataclass
class TrackedBPM:
    bpm: float | None      # smoothed value to display, None when nothing trustworthy
    state: str             # searching | tracking | holding | relocked | lost


class BPMTracker:
    """Exponential smoothing with outlier gating.

    * An accepted reading within `max_jump_bpm` of the current value updates it.
    * A bigger jump is ignored (value held) unless `relock_after` consecutive
      readings agree with each other, in which case the tracker re-locks.
    * Rejected windows hold the last value for `hold_updates` updates, then the
      tracker reports "lost" rather than showing a stale number.
    """

    def __init__(self, alpha: float = 0.3, max_jump_bpm: float = 10.0,
                 relock_after: int = 6, hold_updates: int = 20):
        self.alpha, self.max_jump = alpha, max_jump_bpm
        self.relock_after, self.hold_updates = relock_after, hold_updates
        self.reset()

    def reset(self) -> None:
        self._value: float | None = None
        self._missed = 0
        self._candidates: list[float] = []

    def update(self, result: BPMResult) -> TrackedBPM:
        if result.accepted and result.bpm is not None:
            self._missed = 0
            x = float(result.bpm)
            if self._value is None:
                self._value, self._candidates = x, []
                return TrackedBPM(self._value, "tracking")
            if abs(x - self._value) <= self.max_jump:
                self._value += self.alpha * (x - self._value)
                self._candidates = []
                return TrackedBPM(self._value, "tracking")
            self._candidates.append(x)
            recent = self._candidates[-self.relock_after:]
            if len(recent) >= self.relock_after and max(recent) - min(recent) <= self.max_jump:
                self._value = sum(recent) / len(recent)
                self._candidates = []
                return TrackedBPM(self._value, "relocked")
            return TrackedBPM(self._value, "holding")

        self._missed += 1
        if self._value is None:
            return TrackedBPM(None, "searching")
        if self._missed > self.hold_updates:
            self._value, self._candidates = None, []
            return TrackedBPM(None, "lost")
        return TrackedBPM(self._value, "holding")
