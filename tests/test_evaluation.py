import numpy as np
import pandas as pd

from evaluation.compare import compare, load_series, main


def _write(path, **cols):
    pd.DataFrame(cols).to_csv(path, index=False)
    return str(path)


def test_metrics_on_known_errors(tmp_path):
    t = np.arange(0, 100, 2.0)
    wifi = _write(tmp_path / "w.csv", timestamp=t, bpm=72 + 2.0)       # constant +2 error
    ref = _write(tmp_path / "r.csv", time=t, hr=np.full_like(t, 72.0))
    w, _ = load_series(wifi); r, _ = load_series(ref)
    paired, s = compare(w, r)
    assert s["paired_readings"] == len(t)
    assert abs(s["bias_bpm"] - 2.0) < 1e-9 and abs(s["mae_bpm"] - 2.0) < 1e-9
    assert s["within_3_bpm_pct"] == 100.0


def test_rejected_rows_lower_coverage_but_are_not_errors(tmp_path):
    t = np.arange(0, 20, 2.0)
    acc = [1, 1, 0, 1, 1, 0, 1, 1, 1, 1]
    wifi = _write(tmp_path / "w.csv", timestamp=t, bpm=[70.0] * 10, accepted=acc)
    ref = _write(tmp_path / "r.csv", time=t, bpm=[70.0] * 10)
    _, s = compare(load_series(wifi)[0], load_series(ref)[0])
    assert s["tracker_accepted"] == 8 and abs(s["coverage_pct"] - 80.0) < 1e-9
    assert s["paired_readings"] == 8 and s["mae_bpm"] == 0.0


def test_tolerance_and_offset(tmp_path):
    wifi = _write(tmp_path / "w.csv", time=[100.0, 110.0], bpm=[70.0, 70.0])
    ref = _write(tmp_path / "r.csv", time=[0.0, 10.0], bpm=[70.0, 70.0])
    w, _ = load_series(wifi); r, _ = load_series(ref)
    assert compare(w, r)[1]["paired_readings"] == 0                 # clocks 100 s apart
    assert compare(w, r, offset_s=100.0)[1]["paired_readings"] == 2


def test_invalid_reference_values_dropped(tmp_path):
    wifi = _write(tmp_path / "w.csv", time=[0.0, 2.0], bpm=[70.0, 70.0])
    ref = _write(tmp_path / "r.csv", time=[0.0, 2.0], bpm=[255.0, 70.0])   # 255 = no finger
    _, s = compare(load_series(wifi)[0], load_series(ref)[0], tolerance_s=0.5)
    assert s["paired_readings"] == 1


def test_datetime_timestamps(tmp_path):
    ts = ["2026-10-31T10:00:00+00:00", "2026-10-31T10:00:02+00:00"]
    wifi = _write(tmp_path / "w.csv", timestamp=ts, bpm=[70.0, 71.0])
    ref = _write(tmp_path / "r.csv", Time=["2026-10-31 10:00:01", "2026-10-31 10:00:03"], Pulse=[70.0, 71.0])
    _, s = compare(load_series(wifi)[0], load_series(ref)[0], tolerance_s=2)
    assert s["paired_readings"] == 2


def test_cli_writes_output_and_creates_folder(tmp_path, capsys):
    t = np.arange(0, 60, 2.0)
    wifi = _write(tmp_path / "wifi_bpm.csv", timestamp=t, bpm=t * 0 + 75)
    ref = _write(tmp_path / "pulse_oximeter.csv", timestamp=t, bpm=t * 0 + 74)
    out = tmp_path / "results" / "evaluation.csv"
    assert main([wifi, ref, "--output-csv", str(out)]) == 0
    assert out.exists() and "error" in pd.read_csv(out).columns
    assert "MAE" in capsys.readouterr().out


def test_cli_reports_missing_column(tmp_path, capsys):
    wifi = _write(tmp_path / "w.csv", timestamp=[0.0], foo=[1.0])
    ref = _write(tmp_path / "r.csv", timestamp=[0.0], bpm=[70.0])
    assert main([wifi, ref]) == 1
    assert "BPM column" in capsys.readouterr().err
