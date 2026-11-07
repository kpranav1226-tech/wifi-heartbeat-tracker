from __future__ import annotations

import numpy as np
import pyqtgraph as pg


class SignalGraph(pg.PlotWidget):
    """Thin wrapper: a titled line plot with set_data(x, y)."""

    def __init__(self, title: str, x_label: str, y_label: str = "", parent=None):
        super().__init__(parent)
        self.setTitle(title)
        self.setLabel("bottom", x_label)
        if y_label:
            self.setLabel("left", y_label)
        self.showGrid(x=True, y=True, alpha=0.3)
        self._curve = self.plot(pen=pg.mkPen(width=2))

    def set_data(self, x: np.ndarray, y: np.ndarray) -> None:
        self._curve.setData(x, y)
