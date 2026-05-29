"""API: /api/v9/key_levels — aggregated key price levels for dashboard panel.

Single source of truth: Sierra Chart exports via `tpo.json` (DLL).
This endpoint reuses `_load_sierra_tpo()` so KeyLevelsStrip + per-system
KeyLevelsCard see the exact same numbers Sierra displays in the chart.

Returned blocks (after RTH open):
- today:    POC/VAH/VAL (Study ID:3) + IB (Study ID:6) + session range
- prev_day: POC/VAH/VAL (Study ID:1, previous_session) + range (prior_day)
            + IB (Sierra Input 19 → Yesterday IB study, exported by DLL
            in previous_session.ib_high/ib_low; NULL until configured).

Pre-RTH guards (so the strip never invents numbers):
- `today.ib_*`         None unless Sierra `ib.found=true`
- `today.rth_*`        None pre 09:30 ET (no v9_bars_5min synthesis)
- `today.poc/vah/val`  None unless Sierra `session.va_ok=true`

Polling floor: 15 s (matches Layer0Strip cadence).
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, time, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter

from backend.v9.api.v9.tpo_routes import _load_sierra_tpo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v9/key_levels", tags=["key_levels"])

DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
_ET = ZoneInfo("America/New_York")
_UTC = ZoneInfo("UTC")


def _f(val: Optional[float], dec: int = 2) -> Optional[float]:
    if val is None:
        return None
    try:
        return round(float(val), dec)
    except (TypeError, ValueError):
        return None


def _classify_ib_width(width: Optional[float]) -> Optional[str]:
    """Mind Over Markets thresholds (matches tpo_system._classify_ib_width)."""
    if width is None:
        return None
    if width < 15.0:
        return "NARROW"
    if width <= 25.0:
        return "MEDIUM"
    return "WIDE"


def _utc_str(dt: datetime) -> str:
    return dt.astimezone(_UTC).strftime("%Y-%m-%d %H:%M:%S")


def _day_type_row() -> Optional[dict]:
    """Today's day_type + opening_type from S1 history (UI pills only — NOT IB)."""
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro&immutable=1", uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT day_type, opening_type FROM v9_day_type_history "
            "WHERE date = date('now') LIMIT 1"
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.warning("[key_levels] day_type read failed: %s", e)
        return None


@router.get("")
def get_key_levels() -> dict[str, Any]:
    """Return all key levels for the dashboard panel.

    Single-source: Sierra `tpo.json` via `_load_sierra_tpo()`.
    """
    try:
        sierra = _load_sierra_tpo() or {}
        if not sierra.get("hydrated") and not sierra.get("running"):
            logger.warning("[key_levels] Sierra tpo.json unavailable — returning empty")
            return _empty_response(reason=sierra.get("error") or "sierra_missing")

        prev_sess = sierra.get("previous_session") or {}
        prior_day = sierra.get("prior_day") or {}

        # Pre-RTH guard for today.rth_*
        now_et = datetime.now(_ET)
        rth_open_et = datetime.combine(now_et.date(), time(9, 30), tzinfo=_ET)
        ib_end_et = rth_open_et + timedelta(hours=1)
        pre_rth = now_et < rth_open_et
        ib_window = rth_open_et <= now_et < ib_end_et

        # ── Today IB — Sierra Study OR v9_bars_5min 09:30-10:30 ET ─────────────
        # Michael approved 2026-05-28 18:31 IDT to use bars-derived IB as
        # fallback (bars come from Sierra DLL — aggregation, not synthesis).
        # `_normalize_sierra_tpo` already merges sierra+bars and sets
        # `ib_source`; we just surface it transparently.
        today_ib_high = _f(sierra.get("ib_high"))
        today_ib_low = _f(sierra.get("ib_low"))
        today_ib_width = _f(sierra.get("ib_width"))
        today_ib_source = sierra.get("ib_source") or "missing"
        today_ib_class = _classify_ib_width(today_ib_width)
        if pre_rth:
            ib_status = "pre_open"
        elif today_ib_high is not None and today_ib_low is not None:
            ib_status = "developing" if ib_window else "locked"
        else:
            ib_status = "missing"

        # ── Today POC/VAH/VAL — ONLY from Sierra Study ID:3 ────────────────────
        today_poc = _f(sierra.get("poc"))
        today_vah = _f(sierra.get("vah"))
        today_val = _f(sierra.get("val"))

        # ── Today Range — ONLY from Sierra chart H/L ───────────────────────────
        rth_high = _f(sierra.get("session_high"))
        rth_low = _f(sierra.get("session_low"))
        rth_range = (
            _f(rth_high - rth_low)
            if rth_high is not None and rth_low is not None
            else None
        )

        # ── Globex range — Sierra does NOT export this; keep computed but
        # gated to bars strictly before today's RTH open.
        globex_high, globex_low, globex_range = _globex_range(rth_open_et)

        # ── Prev day POC/VAH/VAL — Sierra previous_session (Study ID:1) ────────
        prev_poc = _f(prev_sess.get("poc"))
        prev_vah = _f(prev_sess.get("vah"))
        prev_val = _f(prev_sess.get("val"))
        prev_session_date = (
            prev_sess.get("session_date")
            or _normalize_prev_date_from_ts(prev_sess.get("opened_ts"))
        )

        # ── Prev day Range — Sierra prior_day high/low/close ───────────────────
        prev_range_high = _f(prior_day.get("high"))
        prev_range_low = _f(prior_day.get("low"))
        prev_range_close = _f(prior_day.get("close"))
        prev_range = (
            _f(prev_range_high - prev_range_low)
            if prev_range_high is not None and prev_range_low is not None
            else None
        )

        # ── Prev IB — Sierra Study ID:1 via DLL Input 19 (Step 9, 2026-05-28) ──
        # Source: tpo.json previous_session.ib_high/ib_low (subgraphs 6/8 of the
        # Sierra "Yesterday Initial Balance" study). Backend already validated
        # MES range and dropped corrupt values to None — never synthesised.
        prev_ib_high = _f(prev_sess.get("ib_high"))
        prev_ib_low = _f(prev_sess.get("ib_low"))
        prev_ib_width = (
            _f(prev_ib_high - prev_ib_low)
            if prev_ib_high is not None and prev_ib_low is not None
            else None
        )
        prev_ib_class = _classify_ib_width(prev_ib_width)

        # ── Day type + opening pills — UI only ─────────────────────────────────
        dt_row = _day_type_row() or {}
        today_day_type = dt_row.get("day_type")
        today_opening_type = dt_row.get("opening_type")

        return {
            "today": {
                "ib_high": today_ib_high,
                "ib_low": today_ib_low,
                "ib_width": today_ib_width,
                "ib_class": today_ib_class,
                "ib_status": ib_status,
                "globex_high": globex_high,
                "globex_low": globex_low,
                "globex_range": globex_range,
                "rth_high": rth_high,
                "rth_low": rth_low,
                "rth_range": rth_range,
                "poc": today_poc,
                "vah": today_vah,
                "val": today_val,
                "day_type": today_day_type,
                "opening_type": today_opening_type,
            },
            "prev_day": {
                "session_date": prev_session_date,
                "poc": prev_poc,
                "vah": prev_vah,
                "val": prev_val,
                "ib_high": prev_ib_high,
                "ib_low": prev_ib_low,
                "ib_width": prev_ib_width,
                "ib_class": prev_ib_class,
                "range_high": prev_range_high,
                "range_low": prev_range_low,
                "range": prev_range,
                "close": prev_range_close,
            },
            "sources": {
                "ib": (
                    "sierra.tpo.ib (Study ID:6, live)"
                    if today_ib_source == "sierra_live"
                    else (
                        "sierra.tpo.ib (pre_open)"
                        if pre_rth
                        else "missing (Sierra IB not available)"
                    )
                ),
                "poc_vah_val": "sierra.tpo.session (Study ID:3)",
                "rth_range": "sierra.tpo.session.session_high/low",
                "globex_range": "v9_bars_5min (pre-RTH bars)",
                "day_type": "v9_day_type_history (pills only)",
                "prev_day_va": "sierra.tpo.previous_session (Study ID:1)",
                "prev_day_range": "sierra.tpo.prior_day",
                "prev_day_ib": (
                    "sierra.tpo.previous_session.ib_* (Input 19 → Yesterday IB Study)"
                    if prev_ib_high is not None and prev_ib_low is not None
                    else "dll_missing (Input 19 not configured or Sierra Y IB study reported 0)"
                ),
            },
            "meta": {
                "pre_rth": pre_rth,
                "ib_status": ib_status,
                "sierra_age_s": sierra.get("age_s"),
                "sierra_stale": sierra.get("stale", False),
            },
        }

    except Exception as e:
        logger.exception("[key_levels] query failed: %s", e)
        return _empty_response(reason=str(e))


def _globex_range(rth_open_et: datetime) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Min/Max of v9_bars_5min strictly before today's 09:30 ET.

    Globex is the only field we still compute from bars because Sierra DLL
    does not export an `overnight` block. Bars are still authoritative
    Sierra exports (just aggregated to 5 min by the bridge).
    """
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro&immutable=1", uri=True, timeout=5)
        rth_utc = _utc_str(rth_open_et)
        row = conn.execute(
            "SELECT MIN(low) AS g_low, MAX(high) AS g_high, COUNT(*) AS n "
            "FROM v9_bars_5min "
            "WHERE symbol='MES' AND date(ts) = date('now') AND ts < ?",
            (rth_utc,),
        ).fetchone()
        conn.close()
        if not row or not row[2]:
            return None, None, None
        g_low = _f(row[0])
        g_high = _f(row[1])
        g_range = _f(g_high - g_low) if g_high is not None and g_low is not None else None
        return g_high, g_low, g_range
    except Exception as e:
        logger.warning("[key_levels] globex range failed: %s", e)
        return None, None, None


def _normalize_prev_date_from_ts(ts: Optional[str]) -> Optional[str]:
    """Extract YYYY-MM-DD from an opened_ts like '2026-05-27 13:30:00+00:00'."""
    if not ts:
        return None
    s = str(ts)
    return s[:10] if len(s) >= 10 else None


def _empty_response(reason: str = "unavailable") -> dict[str, Any]:
    return {
        "today": {},
        "prev_day": {},
        "sources": {},
        "meta": {"error": reason},
    }
