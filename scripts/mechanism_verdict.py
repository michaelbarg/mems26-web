#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§9ג mechanism_verdict — daily gate-by-gate verdict.

T-204 steps 4-5 (ruling 01.09): every evening, for each gate — what it
refused (blocked_candidate_audit.py exists) and t1_before_stop on the
corrected slot. NOT_JUDGEABLE on n < 10. Push only on CANDIDATE_*.

    python3 scripts/mechanism_verdict.py [--date 2026-09-04]

Writes docs/reports/DAILY_VERDICT.md with per-gate stats.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load .env
_env_path = ROOT / ".env"
if _env_path.exists():
    for _ln in open(_env_path, encoding="utf-8"):
        _ln = _ln.strip()
        if _ln and not _ln.startswith("#") and "=" in _ln:
            _k, _v = _ln.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.split("#")[0].strip())

if "postgres" not in os.environ.get("DATABASE_URL", ""):
    sys.exit("DATABASE_URL is not Postgres")

from backend.v9.db.read import read_all  # noqa: E402

LEDGER = Path.home() / "SierraChart_Data" / "v9_export" / "gateway_decisions.jsonl"
ARCHIVE_DIR = Path.home() / "SierraChart_Data" / "v9_export" / "decisions_archive"
VERDICT_PATH = ROOT / "docs" / "reports" / "DAILY_VERDICT.md"
MIN_N = 10


def _load_decisions(archives: bool = True):
    """Load blocked candidates from the ledger + archives."""
    import glob
    files = []
    if archives and ARCHIVE_DIR.exists():
        files = sorted(glob.glob(str(ARCHIVE_DIR / "gateway_decisions.*.jsonl")))
    if LEDGER.exists():
        files.append(str(LEDGER))

    rows = []
    for path in files:
        try:
            for ln in open(path, encoding="utf-8"):
                ln = ln.strip()
                if not ln:
                    continue
                d = json.loads(ln)
                if d.get("blocked_by") and d.get("entry"):
                    rows.append(d)
        except Exception:
            continue
    return rows


def _judge(bars, entry, stop, t1, direction):
    """t1 or stop first. Same logic as blocked_candidate_audit.py."""
    long = (direction or "").upper() == "LONG"
    for b in bars:
        hi, lo = float(b["high"]), float(b["low"])
        if long:
            hit_t1, hit_st = hi >= t1, lo <= stop
        else:
            hit_t1, hit_st = lo <= t1, hi >= stop
        if hit_st:
            return False
        if hit_t1:
            return True
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", type=str, default=None,
                    help="date to report on (default: yesterday)")
    ap.add_argument("--all", action="store_true",
                    help="report on all dates in the archive")
    args = ap.parse_args()

    rows = _load_decisions()
    print(f"Loaded {len(rows)} blocked candidates")

    # Load bars for walk-forward judgment
    bars = read_all(
        "SELECT ts, high, low FROM v9_bars_5min_woodies "
        "WHERE ts >= (SELECT min(ts) FROM v9_bars_5min_woodies) ORDER BY ts", {}
    ) or []
    if not bars:
        print("No bars in DB")
        return 1

    # Index bars by date
    bars_by_ts = {}
    for i, b in enumerate(bars):
        bars_by_ts[str(b["ts"])] = i

    # Group by gate
    by_gate = defaultdict(list)
    for d in rows:
        gate = d.get("blocked_by", "unknown")
        by_gate[gate].append(d)

    # Compute per-gate stats
    lines = []
    lines.append("# DAILY_VERDICT — mechanism-level gate analysis")
    lines.append(f"\nGenerated: {date.today().isoformat()}")
    lines.append(f"Total blocked candidates: {len(rows)}")
    lines.append(f"Bars available: {len(bars)}")
    lines.append("")

    for gate in sorted(by_gate.keys()):
        candidates = by_gate[gate]
        n = len(candidates)
        judgeable = 0
        t1_first = 0
        not_judgeable = 0

        for c in candidates:
            mfe = c.get("mfe_track", {})
            stop = mfe.get("stop")
            t1 = mfe.get("t1")
            entry = c.get("entry")
            direction = c.get("direction")

            if stop is None or t1 is None or entry is None:
                not_judgeable += 1
                continue

            # Find the bar closest to the candidate's timestamp
            ts = c.get("ts")
            if ts is None:
                not_judgeable += 1
                continue

            # Walk forward from the candidate's timestamp
            start_idx = None
            for ii, b in enumerate(bars):
                if str(b["ts"]) >= str(ts):
                    start_idx = ii
                    break
            if start_idx is None:
                not_judgeable += 1
                continue

            window = bars[start_idx:start_idx + 12]  # 60 min
            result = _judge(window, float(entry), float(stop), float(t1), direction)
            if result is None:
                not_judgeable += 1
                continue

            judgeable += 1
            if result:
                t1_first += 1

        pct = round(100 * t1_first / judgeable, 1) if judgeable > 0 else 0
        status = "NOT_JUDGEABLE" if judgeable < MIN_N else f"{pct}%"

        lines.append(f"## {gate}")
        lines.append(f"  n={n}, judgeable={judgeable}, t1_first={t1_first}, "
                     f"not_judgeable={not_judgeable}")
        lines.append(f"  t1_before_stop: **{status}**"
                     + (f" (n={judgeable})" if judgeable >= MIN_N else f" (n={judgeable} < {MIN_N})"))
        lines.append("")

    # Write verdict
    VERDICT_PATH.parent.mkdir(parents=True, exist_ok=True)
    VERDICT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nVerdict written to {VERDICT_PATH}")
    print("\n".join(lines[-20:]))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
