"""SQLite measurement history window with BPM and rejection trend plots."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
from PySide6.QtWidgets import QFileDialog, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from database.storage import Storage
from interface.signal_graph import SignalGraph


class HistoryWindow(QWidget):
    def __init__(self, storage: Storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.setWindowTitle("Measurement history")
        self.resize(900, 650)
        self.summary = QLabel()
        self.bpm_graph = SignalGraph("Stored BPM", "Measurement time", "BPM")
        self.rejection_graph = SignalGraph("Rolling rejection rate (20 measurements)", "Measurement time", "Rejected (%)")
        self.export_button = QPushButton("Export history CSV…")
        self.export_button.clicked.connect(self.export_csv)
        layout = QVBoxLayout(self)
        layout.addWidget(self.summary)
        layout.addWidget(self.bpm_graph)
        layout.addWidget(self.rejection_graph)
        layout.addWidget(self.export_button)
        self.refresh()

    def refresh(self) -> None:
        data = self.storage.records(limit=10000)[::-1]
        if not data:
            self.summary.setText("No stored measurements yet.")
            self.bpm_graph.set_data(np.array([]), np.array([]))
            self.rejection_graph.set_data(np.array([]), np.array([]))
            return
        accepted = np.array([bool(row["accepted"]) for row in data])
        rejected = int((~accepted).sum())
        total = len(data)
        self.summary.setText(f"{total} measurements · {rejected} rejected ({100.0 * rejected / total:.1f}%)")
        x = np.array([datetime.fromisoformat(row["ts"].replace("Z", "+00:00")).timestamp() for row in data])
        bpm = np.array([row["bpm"] if row["accepted"] and row["bpm"] is not None else np.nan for row in data], dtype=float)
        self.bpm_graph.set_data(x, bpm)
        rejected_flags = (~accepted).astype(float)
        rolling = np.array([100 * rejected_flags[max(0, i - 19):i + 1].mean() for i in range(total)])
        self.rejection_graph.set_data(x, rolling)

    def export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export measurement history", "heartbeat_history.csv", "CSV files (*.csv)")
        if not path:
            return
        try:
            self.storage.export_csv(Path(path), limit=10000)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        QMessageBox.information(self, "History exported", f"Saved {path}")