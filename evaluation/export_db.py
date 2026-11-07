"""Export the tracker's SQLite log to CSV, ready for evaluation.compare.

    python -m evaluation.export_db data/heartbeat.db wifi_bpm.csv
"""
from __future__ import annotations

import sys

from database.storage import Storage


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: python -m evaluation.export_db <database.db> <output.csv>", file=sys.stderr)
        return 1
    store = Storage(args[0])
    df = store.to_dataframe(limit=1_000_000).sort_values("ts")
    df.rename(columns={"ts": "timestamp"}).to_csv(args[1], index=False)
    store.close()
    print(f"Wrote {len(df)} rows to {args[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
