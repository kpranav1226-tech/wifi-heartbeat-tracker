import csv

from core.data_models import BPMResult
from database.storage import Storage


def test_storage_history_and_csv_export(tmp_path):
    db = Storage(tmp_path / "history.db")
    db.add(BPMResult(bpm=72.0, quality=0.9, accepted=True), source="test")
    db.add(BPMResult(bpm=None, quality=0.2, accepted=False, reason="low quality"), source="test")
    rows = db.records()
    assert len(rows) == 2
    assert [row["accepted"] for row in rows] == [0, 1]
    output = db.export_csv(tmp_path / "history.csv")
    with output.open(newline="", encoding="utf-8") as handle:
        exported = list(csv.DictReader(handle))
    assert len(exported) == 2
    assert exported[0]["bpm"] == "72.0"
    db.close()