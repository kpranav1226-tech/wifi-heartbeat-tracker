"""Compare the tracker's BPM log against a reference (e.g. pulse oximeter).

    python -m evaluation.compare wifi_bpm.csv pulse_oximeter.csv --output-csv results/evaluation.csv

Each CSV needs a time column and a BPM column; common names are detected
automatically (override with the --*-col options). Time can be numeric seconds
or date/time strings. Both devices must use the same clock: if the reference is
off by a known amount, pass --offset (seconds added to the reference times).

Rows the tracker rejected (empty BPM, or accepted = 0/False) are not scored as
errors; they count against coverage instead.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

TIME_NAMES = ("timestamp", "time", "ts", "datetime", "date_time", "time_s", "seconds", "t")
BPM_NAMES = ("bpm", "heart_rate", "heartrate", "hr", "pulse", "pulse_rate", "pulserate")
VALID_REF_RANGE = (30.0, 220.0)   # oximeters often log 0 or 255 when the finger is off


def _pick(columns, names, explicit, kind, path) -> str:
    lower = {str(c).lower().strip(): c for c in columns}
    if explicit:
        if explicit in columns:
            return explicit
        if explicit.lower().strip() in lower:
            return lower[explicit.lower().strip()]
        raise ValueError(f"{path}: no column named '{explicit}'. Columns: {list(columns)}")
    for n in names:
        if n in lower:
            return lower[n]
    raise ValueError(f"{path}: could not find a {kind} column. Columns: {list(columns)}. "
                     f"Name it explicitly with the --*-col options.")


def _to_seconds(series: pd.Series, path) -> tuple[pd.Series, str]:
    num = pd.to_numeric(series, errors="coerce")
    if num.notna().all():
        return num.astype(float), "numeric"
    dt = pd.to_datetime(series, utc=True, errors="coerce")
    if dt.isna().any():
        raise ValueError(f"{path}: some timestamps could not be parsed")
    return (dt - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds(), "datetime"


def load_series(path, time_col=None, bpm_col=None):
    """Load a CSV into a frame with columns time_s, bpm (+ accepted/quality if present)."""
    df = pd.read_csv(path)
    tcol = _pick(df.columns, TIME_NAMES, time_col, "time", path)
    bcol = _pick(df.columns, BPM_NAMES, bpm_col, "BPM", path)
    secs, kind = _to_seconds(df[tcol], path)
    out = pd.DataFrame({"time_s": secs, "bpm": pd.to_numeric(df[bcol], errors="coerce")})
    for extra in ("accepted", "quality"):
        if extra in df.columns:
            out[extra] = df[extra]
    return out.sort_values("time_s").reset_index(drop=True), kind


def _accepted_mask(wifi: pd.DataFrame) -> pd.Series:
    ok = wifi["bpm"].notna()
    if "accepted" in wifi.columns:
        ok &= wifi["accepted"].astype(str).str.lower().isin(["1", "1.0", "true", "t", "yes"])
    return ok


def compare(wifi: pd.DataFrame, ref: pd.DataFrame, tolerance_s: float = 5.0, offset_s: float = 0.0):
    """Pair each tracker row with the nearest reference reading. Returns (paired, summary)."""
    ref = ref.copy()
    ref["time_s"] = ref["time_s"] + offset_s
    ref = ref[(ref["bpm"] >= VALID_REF_RANGE[0]) & (ref["bpm"] <= VALID_REF_RANGE[1])]
    ref = ref.rename(columns={"bpm": "ref_bpm"})[["time_s", "ref_bpm"]].assign(ref_time_s=lambda d: d["time_s"])

    wifi = wifi.copy()
    wifi["wifi_accepted"] = _accepted_mask(wifi)
    wifi = wifi.rename(columns={"bpm": "wifi_bpm"})
    wifi.loc[~wifi["wifi_accepted"], "wifi_bpm"] = np.nan

    paired = pd.merge_asof(wifi.sort_values("time_s"), ref.sort_values("time_s"),
                           on="time_s", direction="nearest", tolerance=tolerance_s)
    paired["error"] = paired["wifi_bpm"] - paired["ref_bpm"]
    paired["abs_error"] = paired["error"].abs()

    scored = paired.dropna(subset=["error"])
    err = scored["error"].to_numpy()
    n = len(err)
    summary = {
        "tracker_rows": len(wifi),
        "reference_rows_used": len(ref),
        "tracker_accepted": int(wifi["wifi_accepted"].sum()),
        "coverage_pct": 100.0 * wifi["wifi_accepted"].mean() if len(wifi) else float("nan"),
        "paired_readings": n,
    }
    if n:
        sd = float(err.std(ddof=1)) if n > 1 else float("nan")
        bias = float(err.mean())
        summary.update(
            bias_bpm=bias,
            mae_bpm=float(np.abs(err).mean()),
            rmse_bpm=float(np.sqrt((err ** 2).mean())),
            error_sd_bpm=sd,
            loa_low_bpm=bias - 1.96 * sd,
            loa_high_bpm=bias + 1.96 * sd,
            within_3_bpm_pct=100.0 * float((np.abs(err) <= 3).mean()),
            within_5_bpm_pct=100.0 * float((np.abs(err) <= 5).mean()),
            pearson_r=float(np.corrcoef(scored["wifi_bpm"], scored["ref_bpm"])[0, 1])
            if n >= 3 and scored["wifi_bpm"].std() > 0 and scored["ref_bpm"].std() > 0 else float("nan"),
        )
    return paired, summary


def format_summary(s: dict) -> str:
    lines = [
        f"Tracker rows:        {s['tracker_rows']}  (accepted {s['tracker_accepted']}, coverage {s['coverage_pct']:.0f}%)",
        f"Reference readings:  {s['reference_rows_used']}",
        f"Paired readings:     {s['paired_readings']}",
    ]
    if s["paired_readings"] == 0:
        lines.append("No accepted tracker readings fall within the time tolerance of a reference reading.")
        lines.append("Check that both clocks match (try --offset) or raise --tolerance.")
        return "\n".join(lines)
    lines += [
        f"Bias (tracker - ref): {s['bias_bpm']:+.2f} BPM",
        f"MAE:                  {s['mae_bpm']:.2f} BPM",
        f"RMSE:                 {s['rmse_bpm']:.2f} BPM",
        f"95% limits of agreement: {s['loa_low_bpm']:+.2f} to {s['loa_high_bpm']:+.2f} BPM",
        f"Within +/-3 BPM:      {s['within_3_bpm_pct']:.0f}%",
        f"Within +/-5 BPM:      {s['within_5_bpm_pct']:.0f}%",
        f"Correlation (r):      {s['pearson_r']:.3f}",
    ]
    if s["paired_readings"] < 30:
        lines.append(f"Note: only {s['paired_readings']} paired readings; treat these figures as rough.")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Compare tracker BPM against a reference device.")
    ap.add_argument("wifi_csv", help="tracker log (time + bpm, optional accepted/quality columns)")
    ap.add_argument("reference_csv", help="reference log, e.g. pulse oximeter (time + bpm)")
    ap.add_argument("--output-csv", help="write the paired rows and errors here")
    ap.add_argument("--tolerance", type=float, default=5.0, help="max seconds between paired readings (default 5)")
    ap.add_argument("--offset", type=float, default=0.0, help="seconds added to reference times to align clocks")
    ap.add_argument("--wifi-time-col"); ap.add_argument("--wifi-bpm-col")
    ap.add_argument("--ref-time-col"); ap.add_argument("--ref-bpm-col")
    a = ap.parse_args(argv)

    try:
        wifi, k1 = load_series(a.wifi_csv, a.wifi_time_col, a.wifi_bpm_col)
        ref, k2 = load_series(a.reference_csv, a.ref_time_col, a.ref_bpm_col)
        if k1 != k2:
            raise ValueError("One file has numeric times and the other has date/time strings; "
                             "convert them to the same form first.")
        paired, summary = compare(wifi, ref, a.tolerance, a.offset)
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(format_summary(summary))
    if a.output_csv:
        out = Path(a.output_csv)
        out.parent.mkdir(parents=True, exist_ok=True)
        paired.to_csv(out, index=False)
        print(f"\nWrote {len(paired)} rows to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
