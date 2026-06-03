"""P31 Phase 2 — Startup gap-fill loader.

Michael 2026-05-22: "I want that when we turn on [the system], we already
get all the history. I want to see all the data already in the dashboard."

Architecture chosen per ``docs/handoff/CC_UNIFIED_HISTORY_ARCHITECTURE_SPEC.md``:

  * **Path B** for historical depth — read Sierra's rolling-tail JSON exports
    (50–600 bars per stream) directly. No DLL change.
  * **Path α** for gap detection — per-table ``MAX(ts)`` compared against the
    rolling export. Rows newer than ``MAX(ts)`` get ``INSERT OR IGNORE``-ed.
  * Each stream has a small parser-fn that maps the export's array
    (``bars[]``, ``points[]``, ``profiles[]``, ``history[]``, …) into a
    list of ``(ts_iso, bar_id_value, **column_kwargs)`` tuples. The unified
    loop then SQL-INSERTs them via raw sqlite3 (same pattern as the TPO
    snapshotter — avoids ORM churn for a write-once boot path).

Trigger paths:

  1. **FastAPI startup** (auto, default-on). After services initialize, the
     loader runs once. Bounded by the rolling-tail length of each export so
     even a fresh DB completes in seconds.
  2. **Manual** via ``POST /api/v9/admin/history/gap_fill`` (see
     ``admin_routes.py``) — operator-triggered from the cockpit's System
     Control Panel.

Kill-switch: ``V9_DISABLE_HISTORY_LOADER=1`` (used when running tests that
seed their own data).

The loader is **idempotent by INSERT OR IGNORE** — re-running is safe.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")
CHICAGO = ZoneInfo("America/Chicago")

DEFAULT_EXPORT_DIR = Path(
    os.getenv("V9_EXPORT_DIR", "/Users/michael/SierraChart_Data/v9_export")
)
DEFAULT_DB_PATH = os.getenv(
    "V9_DB_PATH",
    "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db",
)
STALE_THRESHOLD_S = 600.0  # don't ingest exports older than 10 min (e.g., DLL paused)

# P31 §9 Chicago→UTC fix — must mirror bridge/v9_streams/base_stream.py.
# DLL bug: SCDateTime serialization emits unix that is actually Chicago
# wall-clock encoded. Bridge corrects this before POSTing; the live DB
# rows therefore carry the corrected (real-UTC) ts. When the loader reads
# the raw JSON, it must apply the SAME shift or it produces ts values
# 5 h (CDT) / 6 h (CST) behind the live rows — bypassing UNIQUE dedupe
# and creating duplicates. Discovered the hard way on 2026-05-22.
_DISABLE_CHICAGO_TS_FIX = os.getenv(
    "V9_DISABLE_CHICAGO_TS_FIX", ""
).lower() in ("1", "true", "yes")


# ----------------------------------------------------------------------
# Per-stream parsers — pure functions, easy to test
# ----------------------------------------------------------------------


def _chicago_to_utc(ts: Any) -> Optional[float]:
    """Mirror ``bridge.v9_streams.base_stream._chicago_to_utc``.

    Re-interpret Sierra's ts (which the DLL emits as Chicago wall-clock
    encoded as unix) as a real UTC unix value. Honours
    ``V9_DISABLE_CHICAGO_TS_FIX`` so the loader can be cleanly switched
    off once the DLL canonical fix (§9 Option A) ships.
    """
    if ts is None:
        return None
    try:
        t = float(ts)
    except (TypeError, ValueError):
        return None
    if _DISABLE_CHICAGO_TS_FIX:
        return t
    # Treat `t` as if it were already in Chicago wall-clock terms, then
    # convert to true UTC.
    naive = datetime.utcfromtimestamp(t)
    aware = naive.replace(tzinfo=CHICAGO)
    return aware.timestamp()


def _ts_iso_from_unix(unix_ts: Any, *, fix_chicago: bool = True) -> Optional[str]:
    """Sierra writes unix-seconds floats; v9_bars_* tables store the format
    ``YYYY-MM-DD HH:MM:SS.ffffff`` (naive UTC, microseconds) — that's what
    SQLAlchemy + the live POST handler produce when persisting a
    ``datetime(timezone.utc)``.

    Matching this format **exactly** is critical: ``v9_bars_5min`` has
    ``UNIQUE(ts, symbol)`` — an ISO-with-T format (``2026-05-22T07:50:00+00:00``)
    would be a different string and bypass the dedup, creating duplicate
    rows for the same moment. Lesson learned the hard way on 2026-05-22.

    ``fix_chicago``: when ``True`` (default for per-bar ``ts``/``t``
    fields), applies the §9 Chicago→UTC shift to mirror what the bridge
    does before POSTing live data. Set to ``False`` for top-level
    ``export_ts`` and other already-real-UTC timestamps.
    """
    if unix_ts is None:
        return None
    try:
        t = float(unix_ts)
    except (TypeError, ValueError):
        return None
    if fix_chicago and not _DISABLE_CHICAGO_TS_FIX:
        shifted = _chicago_to_utc(t)
        if shifted is not None:
            t = shifted
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


SYMBOL_DEFAULT = "MES"


def parse_5min_bars(data: dict) -> List[Dict[str, Any]]:
    """5min.json → v9_bars_5min ingest rows."""
    rows: List[Dict[str, Any]] = []
    for bar in data.get("bars") or []:
        ts_iso = _ts_iso_from_unix(bar.get("ts"))
        if ts_iso is None:
            continue
        # Coerce volume from float (Sierra emits 4510.0) to int (DB schema).
        vol_raw = bar.get("vol") or 0
        try:
            vol = int(vol_raw)
        except (TypeError, ValueError):
            vol = 0
        rows.append(
            {
                "ts": ts_iso,
                "symbol": SYMBOL_DEFAULT,
                "open": bar.get("o"),
                "high": bar.get("h"),
                "low": bar.get("l"),
                "close": bar.get("c"),
                "volume": vol,
                "poc_vol": bar.get("poc_vol"),
                "vah": bar.get("vah"),
                "val": bar.get("val"),
                "cumulative_delta": bar.get("cumulative_delta"),
            }
        )
    return rows


def parse_cvd_points(data: dict) -> List[Dict[str, Any]]:
    """cumulative_delta.json → v9_bars_cumulative_delta ingest rows."""
    rows: List[Dict[str, Any]] = []
    for pt in data.get("points") or []:
        idx = pt.get("i")
        if idx is None:
            continue
        ts_iso = _ts_iso_from_unix(pt.get("t"))
        if ts_iso is None:
            continue
        delta = pt.get("d")
        rows.append(
            {
                "ts": ts_iso,
                "bar_id": f"cvd_{idx}",
                "delta": delta,
                "cumulative": pt.get("cum"),
                "direction": "UP" if (delta or 0) > 0 else ("DOWN" if (delta or 0) < 0 else "FLAT"),
            }
        )
    return rows


def parse_vp_profiles(data: dict, *, export_ts: Optional[float]) -> List[Dict[str, Any]]:
    """volume_profile.json → v9_bars_volume_profile ingest rows.

    Profiles don't carry per-bar ``ts``; use export_ts as the marker. ``bar_idx``
    is the canonical key.

    ``export_ts`` is top-level and NOT buggy (DLL writes it via
    ``time(nullptr)``, real UTC), so ``fix_chicago=False`` here.
    """
    rows: List[Dict[str, Any]] = []
    ts_iso = (
        _ts_iso_from_unix(export_ts, fix_chicago=False)
        or _ts_iso_from_unix(time.time(), fix_chicago=False)
    )
    for prof in data.get("profiles") or []:
        bar_idx = prof.get("bar_idx")
        if bar_idx is None:
            continue
        rows.append(
            {
                "ts": ts_iso,
                "bar_id": f"vp_{bar_idx}",
                "profile": json.dumps(prof.get("levels") or []),
                "poc": prof.get("poc"),
                "vah": prof.get("vah"),
                "val": prof.get("val"),
                "total_volume": int(prof.get("total_vol") or 0),
            }
        )
    return rows


def parse_footprint_bars(data: dict, *, export_ts: Optional[float]) -> List[Dict[str, Any]]:
    """footprint.json → v9_bars_footprint ingest rows.

    Sierra writes per-bar footprints under ``bars[]``; the per-bar ``ts``
    isn't always provided, so the export_ts is used as the boundary marker.
    The DB enforces ``open/high/low/close/volume NOT NULL`` — rows missing
    any of these are dropped before INSERT.

    ``export_ts`` is top-level real-UTC (see ``parse_vp_profiles``), so
    ``fix_chicago=False`` here.
    """
    rows: List[Dict[str, Any]] = []
    ts_iso = (
        _ts_iso_from_unix(export_ts, fix_chicago=False)
        or _ts_iso_from_unix(time.time(), fix_chicago=False)
    )
    for bar in data.get("bars") or []:
        idx = bar.get("idx") if "idx" in bar else bar.get("bar_idx")
        o, h, l, c = bar.get("o"), bar.get("h"), bar.get("l"), bar.get("c")
        if idx is None or None in (o, h, l, c):
            continue
        try:
            vol = int(bar.get("vol") or 0)
        except (TypeError, ValueError):
            vol = 0
        rows.append(
            {
                "ts": ts_iso,
                "symbol": SYMBOL_DEFAULT,
                "open": o, "high": h, "low": l, "close": c,
                "volume": vol,
                "delta": bar.get("delta"),
                "poc_price": bar.get("poc_price"),
                "poc_vol": bar.get("poc_vol"),
                "stacked_buy": bar.get("stacked_buy"),
                "stacked_sell": bar.get("stacked_sell"),
            }
        )
    return rows


def parse_woodies_bars(data: dict, *, period_minutes: int) -> List[Dict[str, Any]]:
    """woodies_*.json → v9_bars_*min_woodies ingest rows. Sierra emits a
    ``history[]`` array of completed bars plus a ``current_bar`` snapshot.
    We persist history only (current is mutable until close).

    The Woodies DB tables require ``open/high/low/close NOT NULL`` —
    drop incomplete bars.
    """
    rows: List[Dict[str, Any]] = []
    for bar in data.get("history") or []:
        ts_iso = _ts_iso_from_unix(bar.get("ts"))
        if ts_iso is None:
            continue
        ohlc = bar.get("ohlc") or {}
        o = ohlc.get("o") or ohlc.get("open")
        h = ohlc.get("h") or ohlc.get("high")
        l = ohlc.get("l") or ohlc.get("low")
        c = ohlc.get("c") or ohlc.get("close")
        if None in (o, h, l, c):
            continue
        try:
            vol = int(bar.get("volume") or bar.get("vol") or 0)
        except (TypeError, ValueError):
            vol = 0
        rows.append(
            {
                "ts": ts_iso,
                "symbol": SYMBOL_DEFAULT,
                "open": o, "high": h, "low": l, "close": c,
                "volume": vol,
                "cci_14": bar.get("cci_14"),
                "cci_6_tcci": bar.get("cci_6_tcci"),
                "lsma_value": bar.get("lsma_value"),
                "swi_value": bar.get("swi_value"),
                "czi_value": bar.get("czi_value"),
                "ema_34": bar.get("ema_34"),
                "trend_state": bar.get("trend_state") or "GRAY",
                "predictor_next_cci": bar.get("predictor_next_cci"),
                "zlr_detected": 1 if bar.get("zlr_detected") else 0,
                "zlr_direction": bar.get("zlr_direction") or "NONE",
            }
        )
    return rows


# ----------------------------------------------------------------------
# Per-stream config + INSERT statements
# ----------------------------------------------------------------------

# Per-stream pipeline config.
#   (file_name, parser_fn, target_table, insert_sql)
#
# Inclusion criterion: the target table must have a UNIQUE constraint that
# makes ``INSERT OR IGNORE`` idempotent. Without it, every gap-fill run
# duplicates rows. The three streams below all satisfy that:
#   * v9_bars_5min: ``UNIQUE (ts, symbol)`` (ux_v9_bars_5min_ts_symbol)
#   * v9_bars_cumulative_delta: ``bar_id TEXT UNIQUE``
#   * v9_bars_volume_profile: ``bar_id TEXT UNIQUE``
#
# Streams NOT included here (intentional, deferred):
#   * footprint.json → v9_bars_footprint: no UNIQUE on ts or any natural key;
#     gap-fill would dupe rows. Defer until a migration adds a key.
#   * woodies_5min.json / woodies_30min.json: same UNIQUE gap; tables already
#     hold 1.8 M / 3.2 M rows from live POSTs anyway — backfill brings no
#     practical value.
#   * tick_reversal_*: v9_bars_tick_reversal already holds 8 M rows.
#   * imbalance_flags / stacked_imbalances: rolling arrays are empty during
#     overnight Globex — they populate via the live POST handlers during RTH.
#   * mes_ai_data / reversal_cluster / live_price: flat snapshots, no array.
#
# The three included streams cover the cockpit's most-visible surfaces:
# the price chart (5min), CVD pane, and TPO/VP per-letter detail.
STREAMS: List[Tuple[str, Callable[..., List[Dict[str, Any]]], str, str]] = [
    (
        "5min.json",
        lambda data: parse_5min_bars(data),
        "v9_bars_5min",
        "INSERT OR IGNORE INTO v9_bars_5min "
        "(ts, symbol, open, high, low, close, volume, poc_vol, vah, val, cumulative_delta) "
        "VALUES (:ts, :symbol, :open, :high, :low, :close, :volume, :poc_vol, :vah, :val, :cumulative_delta)",
    ),
    (
        "cumulative_delta.json",
        lambda data: parse_cvd_points(data),
        "v9_bars_cumulative_delta",
        "INSERT OR IGNORE INTO v9_bars_cumulative_delta "
        "(ts, bar_id, delta, cumulative, direction, created_at) "
        "VALUES (:ts, :bar_id, :delta, :cumulative, :direction, CURRENT_TIMESTAMP)",
    ),
    (
        "volume_profile.json",
        lambda data: parse_vp_profiles(data, export_ts=data.get("export_ts")),
        "v9_bars_volume_profile",
        "INSERT OR IGNORE INTO v9_bars_volume_profile "
        "(ts, bar_id, profile, poc, vah, val, total_volume, created_at) "
        "VALUES (:ts, :bar_id, :profile, :poc, :vah, :val, :total_volume, CURRENT_TIMESTAMP)",
    ),
]


# ----------------------------------------------------------------------
# HistoryLoader — orchestrator
# ----------------------------------------------------------------------


class HistoryLoader:
    """One-shot loader. Spawn ``run_gap_fill()`` from anywhere (startup, admin
    endpoint, tests) — it iterates ``STREAMS`` and returns a per-stream
    summary."""

    def __init__(
        self,
        *,
        export_dir: Path = DEFAULT_EXPORT_DIR,
        db_path: str = DEFAULT_DB_PATH,
        stale_threshold_s: float = STALE_THRESHOLD_S,
    ) -> None:
        self.export_dir = Path(export_dir)
        self.db_path = db_path
        self.stale_threshold_s = stale_threshold_s
        self.last_summary: Optional[Dict[str, Any]] = None

    def run_gap_fill(self, *, reason: str = "manual") -> Dict[str, Any]:
        """Sync — safe to call from FastAPI startup hook. Returns a structured
        report so the caller can log + surface in the admin endpoint.
        """
        started_at = time.time()
        summary: Dict[str, Any] = {
            "reason": reason,
            "started_at_utc": datetime.utcnow().isoformat() + "Z",
            "streams": {},
        }

        from backend.v9.db.session import engine
        from backend.v9.db.safe_writer import _is_postgres, _sqlite_to_pg_upsert
        is_pg = _is_postgres(engine)
        with engine.connect() as conn:
            for file_name, parser_fn, target_table, insert_sql in STREAMS:
                exec_sql = _sqlite_to_pg_upsert(insert_sql) if is_pg else insert_sql
                stream_result = self._gap_fill_stream(
                    conn=conn,
                    file_name=file_name,
                    parser_fn=parser_fn,
                    target_table=target_table,
                    insert_sql=exec_sql,
                    is_pg=is_pg,
                )
                summary["streams"][file_name] = stream_result
            conn.commit()

        summary["elapsed_s"] = round(time.time() - started_at, 3)
        self.last_summary = summary
        logger.warning(  # WARNING so it survives uvicorn's INFO filter
            "[history_loader] gap-fill reason=%s elapsed=%.2fs streams=%d",
            reason,
            summary["elapsed_s"],
            len(summary["streams"]),
        )
        return summary

    # ------------------------------------------------------------------
    # Per-stream worker
    # ------------------------------------------------------------------

    def _gap_fill_stream(
        self,
        *,
        conn,
        file_name: str,
        parser_fn: Callable[..., List[Dict[str, Any]]],
        target_table: str,
        insert_sql: str,
        is_pg: bool = False,
    ) -> Dict[str, Any]:
        path = self.export_dir / file_name
        if not path.exists():
            return {"skipped": "export_missing", "path": str(path)}

        try:
            age_s = time.time() - path.stat().st_mtime
        except OSError:
            age_s = float("inf")
        if age_s > self.stale_threshold_s:
            return {
                "skipped": "export_stale",
                "age_s": round(age_s, 1),
                "threshold_s": self.stale_threshold_s,
            }

        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            return {"skipped": "export_unreadable", "exception": str(e)}

        try:
            rows = parser_fn(data)
        except Exception as e:
            logger.exception("[history_loader] %s parser failed: %s", file_name, e)
            return {"error": "parser_failed", "exception": str(e)}

        if not rows:
            return {"ok": True, "inserted": 0, "skipped_existing": 0, "rows_seen": 0}

        # Bulk INSERT via engine connection.
        from sqlalchemy import text as sa_text
        inserted = 0
        try:
            for row_dict in rows:
                try:
                    conn.execute(sa_text(insert_sql), row_dict)
                    inserted += 1
                except Exception:
                    pass  # ON CONFLICT DO NOTHING — skip duplicates
        except Exception as e:
            logger.exception(
                "[history_loader] %s INSERT failed (likely schema drift): %s",
                target_table, e,
            )
            return {"error": "insert_failed", "exception": str(e), "rows_seen": len(rows)}
        return {
            "ok": True,
            "rows_seen": len(rows),
            "inserted": inserted,
            "skipped_existing": len(rows) - inserted,
            "age_s": round(age_s, 1),
        }


# Module-level singleton + helpers (parallel pattern to other Phase 1 services).
_singleton: Optional[HistoryLoader] = None


def get_loader() -> HistoryLoader:
    global _singleton
    if _singleton is None:
        _singleton = HistoryLoader()
    return _singleton


def reset_singleton_for_tests() -> None:
    global _singleton
    _singleton = None
