from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from core.data_models import BPMResult


class Storage:
    def __init__(self, db_path: str | Path = "data/heartbeat.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, bpm REAL,
                quality REAL NOT NULL, accepted INTEGER NOT NULL, reason TEXT, source TEXT
            )"""
        )
        self.conn.commit()

    def add(self, result: BPMResult, source: str = "") -> None:
        self.conn.execute(
            "INSERT INTO measurements (ts, bpm, quality, accepted, reason, source) VALUES (?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), result.bpm, result.quality,
             int(result.accepted), result.reason, source),
        )
        self.conn.commit()

    def to_dataframe(self, limit: int = 1000):
        """Return the most recent measurements, newest first."""
        if limit < 1:
            raise ValueError("limit must be positive")
        import pandas as pd
        return pd.read_sql_query(
            "SELECT * FROM measurements ORDER BY id DESC LIMIT ?", self.conn, params=(limit,)
        )

    def records(self, limit: int = 1000) -> list[dict]:
        """Return recent measurements as plain dictionaries, newest first."""
        if limit < 1:
            raise ValueError("limit must be positive")
        self.conn.row_factory = sqlite3.Row
        try:
            rows = self.conn.execute(
                "SELECT * FROM measurements ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            self.conn.row_factory = None

    def export_csv(self, path: str | Path, limit: int = 10000) -> Path:
        """Export recent measurements in chronological order."""
        import csv
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        records = list(reversed(self.records(limit)))
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["id", "ts", "bpm", "quality", "accepted", "reason", "source"])
            writer.writeheader()
            writer.writerows(records)
        return output

    def close(self) -> None:
        self.conn.close()