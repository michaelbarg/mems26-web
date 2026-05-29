#!/usr/bin/env python3
"""Bridge Data Monitor — snapshots every 15 min, logs to file.

Run: python3 scripts/bridge_monitor.py
Ctrl+C to stop.

Output: /tmp/bridge_monitor_YYYYMMDD.log
Each entry shows freshness of all bridge streams at the snapshot time.
View live: tail -f /tmp/bridge_monitor_YYYYMMDD.log
"""

import sqlite3
import sys
import time
import os
from datetime import datetime, timezone

DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
INTERVAL_SEC = 900  # 15 minutes
LOG_DIR = "/tmp"

STREAM_CHECKS = [
    ("woodies_5min",     "v9_bars_5min_woodies",    "ts"),
    ("footprint",        "v9_bars_footprint",        "ts"),
    ("cumul_delta",      "v9_bars_cumulative_delta", "ts"),
    ("vol_profile",      "v9_bars_volume_profile",   "ts"),
    ("tick_reversal",    "v9_bars_tick_reversal",    "ts"),
    ("imbalance",        "v9_bars_imbalance",        "ts"),
    ("tpo_bars",         "v9_tpo_bars",              "ts"),
    ("5min_bars",        "v9_bars_5min",             "ts"),
    ("woodies_sigs",     "v9_woodies_signals",       "ts"),
    ("day_type_hist",    "v9_day_type_history",      "last_updated_at"),
]


def _parse_ts_to_epoch(ts_raw: str) -> float | None:
    if not ts_raw:
        return None
    for fmt in [
        "%Y-%m-%dT%H:%M:%S.%f+00:00",
        "%Y-%m-%dT%H:%M:%S+00:00",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ]:
        try:
            dt = datetime.strptime(ts_raw[:26], fmt[:len(ts_raw)])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except (ValueError, TypeError):
            continue
    return None


def snapshot() -> dict:
    """Read current state from DB. Returns dict of stream → info."""
    now = time.time()
    results = {}
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        for label, table, ts_col in STREAM_CHECKS:
            try:
                row = conn.execute(
                    f"SELECT {ts_col} FROM {table} ORDER BY rowid DESC LIMIT 1"
                ).fetchone()
                if row and row[0]:
                    epoch = _parse_ts_to_epoch(str(row[0]))
                    if epoch:
                        age = now - epoch
                        if age < 60:
                            status = "🟢 FRESH"
                        elif age < 300:
                            status = "🟡 STALE"
                        else:
                            status = "🔴 DEAD"
                        results[label] = {
                            "status": status,
                            "age_s": round(age),
                            "last_ts": str(row[0])[:19],
                        }
                    else:
                        results[label] = {"status": "⚪ PARSE_ERR", "age_s": None, "last_ts": str(row[0])[:19]}
                else:
                    results[label] = {"status": "⚫ NO_DATA", "age_s": None, "last_ts": None}
            except Exception as e:
                results[label] = {"status": f"❌ ERR", "age_s": None, "last_ts": str(e)[:50]}
        conn.close()
    except Exception as e:
        results["_db"] = {"status": f"❌ DB_ERROR: {e}", "age_s": None, "last_ts": None}
    return results


def format_snapshot(snap: dict, ts: str) -> str:
    lines = [
        f"\n{'='*70}",
        f"  BRIDGE SNAPSHOT @ {ts} IL",
        f"{'='*70}",
    ]
    for label, info in snap.items():
        status = info.get("status", "?")
        age = info.get("age_s")
        last_ts = info.get("last_ts", "—")
        age_str = f"{age}s ago" if age is not None else "—"
        lines.append(f"  {label:<20} {status}  {age_str:<12} {last_ts}")
    lines.append(f"{'='*70}\n")
    return "\n".join(lines)


def main():
    today = datetime.now().strftime("%Y%m%d")
    log_path = os.path.join(LOG_DIR, f"bridge_monitor_{today}.log")

    print(f"Bridge Monitor started — logging to {log_path}")
    print(f"Snapshot interval: {INTERVAL_SEC}s ({INTERVAL_SEC//60} min)")
    print("Ctrl+C to stop\n")

    while True:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        snap = snapshot()
        output = format_snapshot(snap, ts)

        # Print to console
        print(output)
        sys.stdout.flush()

        # Append to log file
        try:
            with open(log_path, "a") as f:
                f.write(output + "\n")
        except Exception as e:
            print(f"[WARN] Log write failed: {e}")

        # Wait for next snapshot
        try:
            time.sleep(INTERVAL_SEC)
        except KeyboardInterrupt:
            print("\nMonitor stopped.")
            break


if __name__ == "__main__":
    main()
