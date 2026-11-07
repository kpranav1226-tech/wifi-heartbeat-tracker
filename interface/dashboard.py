"""PySide6 dashboard. Streams a simulated recording through a sliding window."""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget,
)

from acquisition.simulator import SCENARIOS, scenario_kwargs, simulate_csi
from core.config import Config, DEFAULT_CONFIG
from database.storage import Storage
from detection.tracker import BPMTracker
from interface.history_view import HistoryWindow
from interface.signal_graph import SignalGraph
from pipeline import process_window

STEP_S = 0.5


class Dashboard(QMainWindow):
    def __init__(self, cfg: Config = DEFAULT_CONFIG):
        super().__init__()
        self.cfg = cfg
        self.setWindowTitle("Wi-Fi Heartbeat Tracker (experimental, not a medical device)")
        self.storage = Storage(cfg.db_path)
        self.rec = None
        self.pos_s = 0.0
        self.tracker = BPMTracker()
        self.history_window = None

        self.bpm_label = QLabel("-- BPM")
        self.bpm_label.setStyleSheet("font-size: 48px; font-weight: bold;")
        self.status_label = QLabel("Idle")

        self.true_bpm = QDoubleSpinBox()
        self.true_bpm.setRange(45, 130)
        self.true_bpm.setValue(72)
        self.true_bpm.setSuffix(" BPM (simulated)")
        self.scenario = QComboBox()
        self.scenario.addItems(SCENARIOS)
        self.start_btn = QPushButton("Start simulation")
        self.start_btn.clicked.connect(self.toggle)
        self.history_btn = QPushButton("History / export")
        self.history_btn.clicked.connect(self.show_history)

        self.raw_graph = SignalGraph("Raw amplitude (subcarrier 0)", "Time (s)")
        self.hb_graph = SignalGraph("Heartbeat-band signal", "Time (s)")
        self.spec_graph = SignalGraph("Spectrum (heart band)", "Frequency (Hz)", "Power")

        controls = QHBoxLayout()
        controls.addWidget(self.true_bpm)
        controls.addWidget(self.scenario)
        controls.addWidget(self.start_btn)
        controls.addWidget(self.history_btn)
        controls.addStretch()
        layout = QVBoxLayout()
        layout.addLayout(controls)
        layout.addWidget(self.bpm_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.raw_graph)
        layout.addWidget(self.hb_graph)
        layout.addWidget(self.spec_graph)
        root = QWidget()
        root.setLayout(layout)
        self.setCentralWidget(root)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

    def toggle(self) -> None:
        if self.timer.isActive():
            self.timer.stop()
            self.start_btn.setText("Start simulation")
            return
        self.rec = simulate_csi(
            duration_s=300, sample_rate_hz=self.cfg.sample_rate_hz,
            n_subcarriers=self.cfg.n_subcarriers, heart_bpm=self.true_bpm.value(),
            **scenario_kwargs(self.scenario.currentText(), self.true_bpm.value()),
        )
        self.pos_s = 0.0
        self.tracker.reset()
        self.start_btn.setText("Stop")
        self.timer.start(int(STEP_S * 1000))

    def tick(self) -> None:
        w = self.cfg.window_seconds
        if self.pos_s + w > self.rec.duration_s:
            self.toggle()
            return
        window = self.rec.window(self.pos_s, w)
        self.pos_s += STEP_S
        result, sig, freqs, psd = process_window(window, self.cfg)
        t = np.arange(window.n_samples) / window.sample_rate_hz
        self.raw_graph.set_data(t, window.amplitude[:, 0])
        self.hb_graph.set_data(t, sig)
        self.spec_graph.set_data(freqs, psd)
        tracked = self.tracker.update(result)
        self.bpm_label.setText(f"{tracked.bpm:.0f} BPM" if tracked.bpm is not None else "-- BPM")
        breath = f" | breathing ~{result.breath_bpm:.0f}/min" if result.breath_bpm else ""
        if result.accepted:
            self.status_label.setText(f"{tracked.state} | quality {result.quality:.2f}{breath}")
        else:
            self.status_label.setText(f"{tracked.state} | window rejected: {result.reason}")
        self.storage.add(result, source="simulator")
        if self.history_window is not None and self.history_window.isVisible():
            self.history_window.refresh()

    def show_history(self) -> None:
        self.history_window = HistoryWindow(self.storage, self)
        self.history_window.show()

    def closeEvent(self, event) -> None:
        self.timer.stop()
        self.storage.close()
        super().closeEvent(event)
