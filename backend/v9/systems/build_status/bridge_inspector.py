"""Bridge Live Feed Inspector — per-stream freshness indicators for Build Status.

Reads last-pushed timestamp directly from DB tables.
No self-HTTP calls. Read-only sqlite3 URI mode.

Staleness thresholds (RTH-aware):
  FRESH  — last push < 60 s ago
  STALE  — last push 60–300 s ago
  DEAD   — last push > 300 s OR no data

Each stream is presented as a GlobalGate in the returned SystemStatus.
"""

import logging
import sqlite3
import time
from datetime import datetime, timezone
from typing import Optional

from .types import SystemStatus, GlobalGate, DataFreshness
from .row_helpers import make_freshness, freshness_now

logger = logging.getLogger(__name__)

DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"

# ── Stream → DB table config ──────────────────────────────────────────────────
# Each entry: (stream_label, table_name, ts_column, stale_threshold_sec)
# Thresholds are generous (bridge fires every 5-15s in RTH).
STREAM_CHECKS = [
    ("woodies_5min",       "v9_bars_5min_woodies",      "ts",         90),
    ("footprint",          "v9_bars_footprint",          "ts",         90),
    ("cumulative_delta",   "v9_bars_cumulative_delta",   "ts",        360),
    ("volume_profile",     "v9_bars_volume_profile",     "ts",        360),
    ("tick_reversal",      "v9_bars_tick_reversal",      "ts",         90),
    ("imbalance",          "v9_bars_imbalance",          "ts",         90),
    ("tpo_bars",           "v9_tpo_bars",                "ts",        360),
    ("5min_bars",          "v9_bars_5min",               "ts",        360),
]


def _parse_ts(ts_raw: str) -> Optional[float]:
    """Parse various timestamp formats → UTC epoch float. Returns None on failure."""
    if not ts_raw:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f+00:00",
        "%Y-%m-%dT%H:%M:%S+00:00",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S+%f",
    ):
        try:
            dt = datetime.strptime(ts_raw[:26], fmt[:len(ts_raw)])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except (ValueError, TypeError):
            continue
    try:
        # Last resort: truncate to 26 chars and try
        return datetime.fromisoformat(ts_raw[:25]).replace(tzinfo=timezone.utc).timestamp()
    except Exception:
        return None


def _check_stream(conn: sqlite3.Connection, table: str, ts_col: str, threshold: int) -> dict:
    """Query a single stream table and return freshness dict."""
    try:
        row = conn.execute(
            f"SELECT {ts_col} FROM {table} ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        if row is None or row[0] is None:
            return {"age_sec": None, "status": "DEAD", "last_ts": None}

        epoch = _parse_ts(str(row[0]))
        if epoch is None:
            return {"age_sec": None, "status": "DEAD", "last_ts": str(row[0])}

        age = time.time() - epoch
        # Clamp negative ages to 0 (can happen when DB stores local time as if UTC)
        age_display = max(0.0, age)
        if 0 <= age < 60:
            status = "FRESH"
        elif 0 <= age < threshold:
            status = "STALE"
        elif age < 0:
            # Future timestamp — likely local-time stored as UTC; treat as FRESH
            status = "FRESH"
            age_display = 0.0
        else:
            status = "DEAD"
        return {"age_sec": round(age_display, 1), "status": status, "last_ts": str(row[0])[:19]}

    except Exception as e:
        return {"age_sec": None, "status": "ERROR", "last_ts": None, "err": str(e)}


def inspect(db_path: Optional[str] = None) -> SystemStatus:
    """Return a SystemStatus representing bridge stream freshness.

    Each stream is represented as a GlobalGate:
      present=True  → FRESH (< 60s)
      present=False → STALE / DEAD / ERROR
    """
    db = db_path or DB_PATH
    gates: list[GlobalGate] = []
    all_fresh = True

    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True, timeout=2)

        for label, table, ts_col, threshold in STREAM_CHECKS:
            result = _check_stream(conn, table, ts_col, threshold)
            status = result["status"]
            age = result["age_sec"]
            last_ts = result.get("last_ts", "—")
            is_fresh = status == "FRESH"
            if not is_fresh:
                all_fresh = False

            if age is not None:
                age_str = f"{int(age)}s ago" if age < 3600 else f"{int(age/60)}min ago"
                value = f"[{status}] {age_str} · {last_ts}"
            else:
                value = f"[{status}] no data"

            # Build a Freshness for the stream — anchor at the raw last_ts
            # so the UI shows when the bridge last wrote, with 'sierra_export'
            # as the provenance (these tables are bridge → DB sinks).
            _bridge_fresh = (
                make_freshness(last_ts, "sierra_export") if last_ts and last_ts != "—"
                else freshness_now("sierra_export")
            )
            gates.append(GlobalGate(
                key=label,
                spec=f"Bridge push < {threshold}s",
                present=is_fresh,
                value=value,
                live=f"{int(age)}s" if age is not None else "no_data",
                required=f"< {threshold}s",
                freshness=_bridge_fresh,
            ))

        conn.close()

    except Exception as e:
        logger.warning("[BridgeInspector] DB read failed: %s", e)
        gates.append(GlobalGate(
            key="bridge_db",
            spec="DB accessible",
            present=False,
            value=f"DB error: {e}",
            live=f"error: {e}",
            required="accessible",
            freshness=freshness_now("inspector_eval"),
        ))
        all_fresh = False

    # Overall freshness: freshest stream (woodies_5min) determines data_freshness
    first_fresh = next((g for g in gates if g.present), None)
    data_fresh = DataFreshness(
        fresh=all_fresh,
        threshold_seconds=90,
    )
    if gates and gates[0].value:
        # Parse age from first gate (woodies_5min)
        try:
            first_result = _get_single_age(db, STREAM_CHECKS[0])
            if first_result is not None:
                data_fresh = DataFreshness(
                    fresh=first_result < 60,
                    lag_seconds=first_result,
                    threshold_seconds=90,
                )
        except Exception:
            pass

    running = any(g.present for g in gates)

    return SystemStatus(
        id="bridge",
        name="Bridge · Live Data Feed",
        running=running,
        hydrated=True,
        mode="LIVE" if running else "OFFLINE",
        data_freshness=data_fresh,
        global_gates=gates,
        patterns=[],
    )


def _get_single_age(db: str, stream_cfg: tuple) -> Optional[float]:
    _, table, ts_col, _ = stream_cfg
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True, timeout=2)
        row = conn.execute(
            f"SELECT {ts_col} FROM {table} ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if row and row[0]:
            epoch = _parse_ts(str(row[0]))
            if epoch:
                return time.time() - epoch
    except Exception:
        pass
    return None
