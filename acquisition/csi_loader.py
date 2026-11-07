"""CSI sources. Everything downstream only sees a CSIRecording."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from core.data_models import CSIRecording


class CSISource(ABC):
    @abstractmethod
    def load(self) -> CSIRecording: ...


class FileCSISource(CSISource):
    """Loads a recording saved with `save_recording` (.npz)."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> CSIRecording:
        with np.load(self.path, allow_pickle=False) as f:
            ts = f["timestamps"] if "timestamps" in f.files else None
            return CSIRecording(f["csi"], float(f["sample_rate_hz"]), ts)


class HardwareCSISource(CSISource):
    """Placeholder for a real capture device (Intel 5300, Atheros, Nexmon, ESP32...)."""

    def load(self) -> CSIRecording:
        raise NotImplementedError("Hardware capture not implemented yet.")


def save_recording(rec: CSIRecording, path: str | Path) -> None:
    arrays = {"csi": rec.csi, "sample_rate_hz": np.array(rec.sample_rate_hz)}
    if rec.timestamps is not None:
        arrays["timestamps"] = rec.timestamps
    np.savez_compressed(path, **arrays)
