"""Shared helpers for inspector rows (live / required / freshness).

Centralises three concerns so every inspector emits a consistent row shape:

1. `parse_ts_to_utc()` — robust parser that accepts ISO strings (naive
   or aware), epoch seconds (int / string), and known broken layouts.
   Returns a tz-aware UTC datetime or None.

2. `freshness_*()` — small builders for `Freshness` objects so the
   inspectors don't each re-implement the now/ts math. The lag is
   always clamped to >= 0; ts values that resolve to a clearly-future
   moment are treated as garbage (lag_s = None) so the UI surfaces it
   rather than silently rendering a -72-year lag (the very bug that
   appeared on `5min_bar_recency` for v9_bars_5min_woodies, where bad
   "2099-01-02 ..." rows poison MAX(ts)).

3. `latest_valid_db_ts()` — DB query that mirrors `MAX(ts)` but
   excludes future timestamps. Used by the recency rows so the inspector
   no longer reports astronomical negative lags when corrupt sentinel
   rows exist in the table.
"""

from __future__ import annotations

import json
import logging
from datetime import date as _date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.v9.common.trading_date import et_today as _et_today

from .types import Freshness, FreshnessSource

logger = logging.getLogger(__name__)

# Maximum future skew tolerated when parsing a ts. Anything further into
# the future is treated as corrupt sentinel data (see module docstring).
_FUTURE_SKEW_S = 5.0

# Per-(firing_system, today_date_str) cache for fires_today(). TTL keeps
# back-to-back Build Status polls from hammering the DB while preserving
# sub-second responsiveness to brand-new fires.
_FIRES_TODAY_CACHE: Dict[Tuple[int, str], Dict[str, Any]] = {}
_FIRES_TODAY_TTL_S = 5.0

# Pattern_id tokens we don't want to credit as Woodies/S2 patterns when
# they appear in cross_context (S3 footprint triggers, lifecycle events).
_NON_PATTERN_TOKENS = {
    "FIRE_EXHAUSTION",
    "STOP_MOVE",
    "EVENT",
    "BE+1T",
    "BE",
}


def parse_ts_to_utc(ts_raw) -> Optional[datetime]:
    """Parse a timestamp value (str/int/float/datetime) → aware UTC datetime.

    Accepts:
      - ISO8601 strings (naive or aware)
      - "YYYY-MM-DD HH:MM:SS[.ffffff]" SQLite-style strings
      - epoch seconds as int / float / numeric-string
      - already-aware datetimes
    Returns None on any failure (caller decides fallback).
    """
    if ts_raw is None:
        return None

    if isinstance(ts_raw, datetime):
        dt = ts_raw
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    if isinstance(ts_raw, (int, float)):
        try:
            return datetime.fromtimestamp(float(ts_raw), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    s = str(ts_raw).strip()
    if not s:
        return None

    if s.replace(".", "", 1).lstrip("-").isdigit():
        try:
            return datetime.fromtimestamp(float(s), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        pass

    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            continue
    return None


def _lag_seconds(ts: Optional[datetime], now: Optional[datetime] = None) -> Optional[float]:
    """now - ts in seconds, with future ts -> None (poisoned data)."""
    if ts is None:
        return None
    if now is None:
        now = datetime.now(timezone.utc)
    delta = (now - ts).total_seconds()
    if delta < -_FUTURE_SKEW_S:
        return None
    return max(0.0, delta)


def make_freshness(
    ts_raw,
    source: FreshnessSource,
    *,
    now: Optional[datetime] = None,
) -> Freshness:
    """Build a Freshness from a raw ts (any format parse_ts_to_utc handles).

    If `ts_raw` is None or unparseable, the returned object still records
    the source so the UI knows where to look — only ts/lag_s are None.
    """
    parsed = parse_ts_to_utc(ts_raw)
    if parsed is None:
        return Freshness(ts=str(ts_raw) if ts_raw is not None else None,
                         lag_s=None, source=source)
    iso = parsed.isoformat()
    return Freshness(ts=iso, lag_s=_lag_seconds(parsed, now), source=source)


def freshness_now(source: FreshnessSource = "inspector_eval",
                  now: Optional[datetime] = None) -> Freshness:
    """Freshness object anchored at the inspector wall-clock (lag_s == 0)."""
    if now is None:
        now = datetime.now(timezone.utc)
    return Freshness(ts=now.isoformat(), lag_s=0.0, source=source)


def latest_valid_db_ts(
    conn_or_table,
    table: str = "",
    *,
    where: str = "",
    params: tuple = (),
    lookback: int = 50,
    now: Optional[datetime] = None,
) -> Tuple[Optional[str], Optional[datetime], Optional[float]]:
    """Return (raw_ts, parsed_utc, lag_seconds) for the latest non-future row.

    `MAX(ts)` lex-sorts text columns, which means a stray "2099-01-02 ..."
    row will beat every real timestamp. We instead scan the top `lookback`
    rows ORDER BY ts DESC and pick the first one whose ts parses to a
    non-future moment (within `_FUTURE_SKEW_S`).

    Returns (None, None, None) when no usable row exists.

    Accepts either (conn, table, ...) for backward compat or just (table, ...).
    When first arg is a string (table name), uses read_all helper.
    """
    from backend.v9.db.read import read_all as _read_all

    # Backward compat: if first arg is a connection object, use second arg as table
    if isinstance(conn_or_table, str):
        # Called as latest_valid_db_ts("table_name", ...)
        _table = conn_or_table
    else:
        # Called as latest_valid_db_ts(conn, "table_name", ...)
        _table = table

    if now is None:
        now = datetime.now(timezone.utc)
    sql = f"SELECT ts FROM {_table}"
    if where:
        sql += f" WHERE {where}"
    sql += f" ORDER BY ts DESC LIMIT {int(lookback)}"
    try:
        # Convert positional params to named params for read_all
        named_params = {}
        if params:
            # Replace ? placeholders with :p0, :p1, etc.
            parts = sql.split("?")
            new_parts = []
            for i, part in enumerate(parts):
                new_parts.append(part)
                if i < len(parts) - 1:
                    named_params[f"p{i}"] = params[i]
                    new_parts.append(f":p{i}")
            sql = "".join(new_parts)
        rows = _read_all(sql, named_params)
    except Exception as e:
        logger.warning("[BuildStatus/row_helpers] latest_valid_db_ts %s failed: %s", _table, e)
        return None, None, None

    for r in rows:
        raw = r.get("ts") if isinstance(r, dict) else None
        if raw is None:
            continue
        parsed = parse_ts_to_utc(raw)
        if parsed is None:
            continue
        delta = (now - parsed).total_seconds()
        if delta < -_FUTURE_SKEW_S:
            # future sentinel — skip, keep looking
            continue
        return str(raw), parsed, max(0.0, delta)
    return None, None, None


def _extract_pattern_ids_from_cross_context(raw_json) -> List[str]:
    """Pull every plausible upper-cased pattern_id out of a v9_trades.cross_context.

    The trade_manager writes cross_context in two observed layouts:

      A. Array variant — the "primary event" wrapped in a list, with
         everything underneath:
            [{"trigger": "GB100",
              "metadata": {"pattern": "GB100"},
              "systems": {"woodies_system": {"active_patterns": [...]}}}]

      B. Flat dict variant — systems hoisted to the top level:
            {"woodies_system": {"active_patterns": [...]},
             "five_min_system": {...}}

    The cross_context can ALSO be a list of trade-lifecycle event dicts
    (e.g. `[{"event": "stop_move", ...}]`) which carry no pattern_id.
    Those rows yield [] — the caller skips them. Returns an empty list
    for any parse / shape failure (no exceptions).
    """
    if raw_json is None:
        return []
    try:
        if isinstance(raw_json, (list, dict)):
            parsed = raw_json
        else:
            parsed = json.loads(str(raw_json))
    except (ValueError, TypeError):
        return []

    if isinstance(parsed, list):
        primary = parsed[0] if parsed and isinstance(parsed[0], dict) else None
    elif isinstance(parsed, dict):
        primary = parsed
    else:
        primary = None
    if not isinstance(primary, dict):
        return []

    pids: List[str] = []

    systems = primary.get("systems")
    if not isinstance(systems, dict):
        systems = primary  # variant B: systems hoisted to top level

    for sys_key in ("woodies_system", "five_min_system"):
        sub = systems.get(sys_key) if isinstance(systems, dict) else None
        if not isinstance(sub, dict):
            continue
        for ap in sub.get("active_patterns") or []:
            if isinstance(ap, dict):
                pid = ap.get("pattern_id")
                if isinstance(pid, str) and pid:
                    pids.append(pid.upper())
        last_pattern = sub.get("last_pattern")
        if isinstance(last_pattern, str) and last_pattern:
            pids.append(last_pattern.upper())

    for fld in ("trigger", "classification"):
        v = primary.get(fld)
        if isinstance(v, str) and v:
            pids.append(v.upper())
    meta = primary.get("metadata")
    if isinstance(meta, dict):
        p = meta.get("pattern")
        if isinstance(p, str) and p:
            pids.append(p.upper())

    pids = [p for p in pids if p not in _NON_PATTERN_TOKENS]

    seen = set()
    out: List[str] = []
    for p in pids:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def clear_fires_today_cache() -> None:
    """Wipe the cache. Tests use this between cases; production never calls it."""
    _FIRES_TODAY_CACHE.clear()


def fires_today(
    conn_or_firing_system,
    firing_system: int = 0,
    *,
    today: Optional[str] = None,
    now: Optional[datetime] = None,
    signals_table: Optional[str] = None,  # reserved for future last_signal_ts cross-check
) -> Dict[str, Dict[str, Any]]:
    """Read today's fires from `v9_trades` and return per-pattern counts.

    Authoritative "fired today" source (per the Build Status surface spec):
    `v9_trades` rows where `firing_system = ?` and `date(entry_ts) = today`.

    Returns:
        Dict mapping UPPER-CASED pattern_id -> {"count": int, "last_ts": str},
        where `last_ts` is the newest ISO entry_ts seen for that pattern.
        Empty dict on DB error (logged warning) or when no rows match.

    Accepts either (conn, firing_system, ...) for backward compat or just
    (firing_system, ...) when conn is no longer needed.
    """
    from backend.v9.db.read import read_all as _read_all

    # Backward compat: if first arg is an int, it's the firing_system directly
    if isinstance(conn_or_firing_system, int):
        _firing_system = conn_or_firing_system
    else:
        # Called as fires_today(conn, firing_system, ...)
        _firing_system = firing_system

    if now is None:
        now = datetime.now(timezone.utc)
    if today is None:
        today = _et_today().isoformat()
    key = (int(_firing_system), today)

    cached = _FIRES_TODAY_CACHE.get(key)
    if cached is not None:
        fetched_at: datetime = cached["fetched_at"]
        if (now - fetched_at).total_seconds() < _FIRES_TODAY_TTL_S:
            return cached["data"]

    # Prune stale-day entries so the cache can't grow unbounded across
    # midnight (firing_system unchanged, today_str advances).
    for k in list(_FIRES_TODAY_CACHE.keys()):
        if k[1] != today:
            _FIRES_TODAY_CACHE.pop(k, None)

    try:
        rows = _read_all(
            "SELECT entry_ts, cross_context FROM v9_trades "
            "WHERE firing_system = :firing_system AND date(entry_ts) = :today "
            "ORDER BY entry_ts",
            {"firing_system": int(_firing_system), "today": today},
        )
    except Exception as e:
        logger.warning(
            "[BuildStatus/row_helpers] fires_today firing_system=%s today=%s failed: %s",
            _firing_system, today, e,
        )
        _FIRES_TODAY_CACHE[key] = {"fetched_at": now, "data": {}}
        return {}

    result: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        entry_ts_raw = row["entry_ts"]
        cross_context = row["cross_context"]
        pids = _extract_pattern_ids_from_cross_context(cross_context)
        if not pids:
            continue
        parsed = parse_ts_to_utc(entry_ts_raw)
        ts_iso = parsed.isoformat() if parsed is not None else str(entry_ts_raw)
        for pid in pids:
            entry = result.setdefault(pid, {"count": 0, "last_ts": None})
            entry["count"] += 1
            if entry["last_ts"] is None or ts_iso > entry["last_ts"]:
                entry["last_ts"] = ts_iso

    _FIRES_TODAY_CACHE[key] = {"fetched_at": now, "data": result}
    return result
