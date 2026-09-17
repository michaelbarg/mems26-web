"""T-390: SituationVector — frozen dataclass capturing all decision-relevant
state at each bar.  Computed once per setup in the gateway, stored in trade
metadata, and logged to ``v9_decision_vectors``.

Every field that cannot be computed defaults to ``None`` (fail-open).  The
``compute_situation_vector`` function is **pure** (no side-effects, no DB
queries, no look-ahead) and must **never throw**.
"""

from __future__ import annotations

import logging
import os
import statistics
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SituationVector
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SituationVector:
    ts: str                      # ISO UTC of bar
    price: float
    day_type: str | None         # live label at decision time (not final)
    day_type_conf: float | None
    phase: str | None            # A/B/C/D from _resolve_phase
    opening_type: str | None
    zone: str | None             # zone_of(price, vah, val, ib_width) on developing VA
    prior_zone: str | None       # zone_of vs previous session VA
    ib_locked: bool
    ib_width: float | None
    extension: str               # 'up'|'down'|'both'|'none'
    extension_pts: float         # max(session_high-ib_high, ib_low-session_low, 0)
    vol_ratio: float | None      # bar volume / median volume of same-minute-of-day
    bars_since_high: int | None  # RTH bars closed since session high
    bars_since_low: int | None
    dir_hint: str | None         # dp_dir_hint from gateway / S1DayDir
    atr_causal: float | None     # ATR14 on closed bars only
    # T-392b/F5: fields for expr: conditions in decision tree
    classification_prefix: str | None = None  # first 12 chars of classification
    direction: str | None = None              # LONG/SHORT from setup
    entry_kind: str | None = None             # BREAK/PULLBACK/etc from setup


# ---------------------------------------------------------------------------
# Pure computation
# ---------------------------------------------------------------------------


def compute_situation_vector(
    *,
    cross_context: Dict[str, Any],
    price: float,
    ts: str,
    bars_rth_today: Optional[List[Dict]] = None,
    prior_sessions_bars: Optional[List[List[Dict]]] = None,
    phase: Optional[str] = None,
    dir_hint: Optional[str] = None,
    day_type: Optional[str] = None,
    day_type_conf: Optional[float] = None,
    opening_type: Optional[str] = None,
    classification_prefix: Optional[str] = None,
    direction: Optional[str] = None,
    entry_kind: Optional[str] = None,
) -> SituationVector:
    """Compute the full SituationVector.  Fail-open: any field that cannot be
    computed → ``None``; never throws.
    """
    try:
        return _compute_inner(
            cross_context=cross_context or {},
            price=price,
            ts=ts,
            bars_rth_today=bars_rth_today,
            prior_sessions_bars=prior_sessions_bars,
            phase=phase,
            dir_hint=dir_hint,
            day_type=day_type,
            day_type_conf=day_type_conf,
            opening_type=opening_type,
            classification_prefix=classification_prefix,
            direction=direction,
            entry_kind=entry_kind,
        )
    except Exception as exc:
        logger.warning("[SituationVector] compute failed (returning defaults): %s", exc)
        return SituationVector(
            ts=ts, price=price, day_type=day_type, day_type_conf=day_type_conf,
            phase=phase, opening_type=opening_type, zone=None, prior_zone=None,
            ib_locked=False, ib_width=None, extension="none", extension_pts=0.0,
            vol_ratio=None, bars_since_high=None, bars_since_low=None,
            dir_hint=dir_hint, atr_causal=None,
            classification_prefix=classification_prefix,
            direction=direction, entry_kind=entry_kind,
        )


def _compute_inner(
    *,
    cross_context: dict,
    price: float,
    ts: str,
    bars_rth_today: Optional[List[Dict]],
    prior_sessions_bars: Optional[List[List[Dict]]],
    phase: Optional[str],
    dir_hint: Optional[str],
    day_type: Optional[str],
    day_type_conf: Optional[float],
    opening_type: Optional[str],
    classification_prefix: Optional[str] = None,
    direction: Optional[str] = None,
    entry_kind: Optional[str] = None,
) -> SituationVector:
    # -- TPO data --
    tpo = cross_context.get("tpo_system") or {}
    if not isinstance(tpo, dict):
        tpo = {}

    vah = _f(tpo.get("vah"))
    val = _f(tpo.get("val"))
    ib_high = _f(tpo.get("ib_high"))
    ib_low = _f(tpo.get("ib_low"))
    ib_locked = bool(tpo.get("ib_locked"))
    session_high = _f(tpo.get("session_high") or tpo.get("rth_high"))
    session_low = _f(tpo.get("session_low") or tpo.get("rth_low"))

    ib_width: Optional[float] = None
    if ib_high is not None and ib_low is not None and ib_high > 0 and ib_low > 0:
        ib_width = ib_high - ib_low

    # -- zone (current developing VA) --
    zone = _safe_zone_of(price, vah, val, ib_width)

    # -- prior_zone (previous session VA) --
    prior_zone: Optional[str] = None
    try:
        prev_sess = tpo.get("previous_session") or {}
        if isinstance(prev_sess, dict):
            p_vah = _f(prev_sess.get("vah"))
            p_val = _f(prev_sess.get("val"))
            p_ibw: Optional[float] = None
            p_ibh = _f(prev_sess.get("ib_high"))
            p_ibl = _f(prev_sess.get("ib_low"))
            if p_ibh is not None and p_ibl is not None and p_ibh > 0 and p_ibl > 0:
                p_ibw = p_ibh - p_ibl
            prior_zone = _safe_zone_of(price, p_vah, p_val, p_ibw)
    except Exception:
        pass

    # -- extension --
    extension = "none"
    extension_pts = 0.0
    if ib_locked and ib_high and ib_low:
        ext_up = max(0.0, (session_high or 0) - ib_high)
        ext_dn = max(0.0, ib_low - (session_low or ib_low))
        if ext_up > 0 and ext_dn > 0:
            extension = "both"
        elif ext_up > 0:
            extension = "up"
        elif ext_dn > 0:
            extension = "down"
        extension_pts = max(ext_up, ext_dn, 0.0)

    # -- vol_ratio --
    vol_ratio = _compute_vol_ratio(ts, bars_rth_today, prior_sessions_bars)

    # -- bars_since_high / bars_since_low --
    bars_since_high, bars_since_low = _compute_bars_since(bars_rth_today)

    # -- atr_causal --
    atr_causal = _compute_atr_causal(bars_rth_today)

    return SituationVector(
        ts=ts,
        price=price,
        day_type=day_type,
        day_type_conf=day_type_conf,
        phase=phase,
        opening_type=opening_type,
        zone=zone,
        prior_zone=prior_zone,
        ib_locked=ib_locked,
        ib_width=ib_width,
        extension=extension,
        extension_pts=extension_pts,
        vol_ratio=vol_ratio,
        bars_since_high=bars_since_high,
        bars_since_low=bars_since_low,
        dir_hint=dir_hint,
        atr_causal=atr_causal,
        classification_prefix=classification_prefix,
        direction=direction,
        entry_kind=entry_kind,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _f(v: Any) -> Optional[float]:
    """Safe float conversion, returns None on failure."""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _safe_zone_of(price: float, vah: Optional[float], val: Optional[float],
                  ib_width: Optional[float]) -> Optional[str]:
    """Call location_gate.zone_of safely, return None on any failure."""
    if vah is None or val is None or vah <= 0 or val <= 0:
        return None
    try:
        from backend.v9.systems.location_gate import zone_of
        return zone_of(price, vah, val, ib_width)
    except Exception:
        return None


def _compute_vol_ratio(
    ts: str,
    bars_rth_today: Optional[List[Dict]],
    prior_sessions_bars: Optional[List[List[Dict]]],
) -> Optional[float]:
    """Bar volume / median of same minute-of-day across prior sessions.
    Causal: only prior sessions, >=5 required.  None if not computable."""
    if not bars_rth_today or not prior_sessions_bars or len(prior_sessions_bars) < 5:
        return None
    try:
        # Current bar volume = last bar in today's list
        current_bar = bars_rth_today[-1] if bars_rth_today else None
        if current_bar is None:
            return None
        cur_vol = float(current_bar.get("v") or current_bar.get("volume") or 0)
        if cur_vol <= 0:
            return None

        # Extract minute-of-day from the CLOSED bar itself (cowork 17.09 14:50):
        # the decision timestamp is seconds into the next bar (18:53:07Z while
        # the bar is 18:50:00Z), so keyed on `ts` no prior bar ever matched and
        # vol_ratio was always None. Both sides are floored to the 5-min bucket.
        cur_minute = _minute_of_day(str(current_bar.get("ts") or ts))
        if cur_minute is not None:
            cur_minute -= cur_minute % 5
        if cur_minute is None:
            return None

        # Collect volumes at same minute from prior sessions
        same_minute_vols: list[float] = []
        for session_bars in prior_sessions_bars:
            for bar in session_bars:
                bar_ts = bar.get("ts") or bar.get("timestamp") or ""
                bar_minute = _minute_of_day(str(bar_ts))
                if bar_minute is not None:
                    bar_minute -= bar_minute % 5
                if bar_minute == cur_minute:
                    bv = float(bar.get("v") or bar.get("volume") or 0)
                    if bv > 0:
                        same_minute_vols.append(bv)
                    break  # one bar per session at this minute

        if len(same_minute_vols) < 5:
            return None
        median_vol = statistics.median(same_minute_vols)
        if median_vol <= 0:
            return None
        return round(cur_vol / median_vol, 4)
    except Exception:
        return None


def _minute_of_day(ts_str: str) -> Optional[int]:
    """Extract minute-of-day (0..1439) from an ISO timestamp string."""
    try:
        # Handle various formats
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.hour * 60 + dt.minute
    except Exception:
        return None


def _compute_bars_since(bars_rth_today: Optional[List[Dict]]) -> tuple:
    """Return (bars_since_high, bars_since_low) from closed bars."""
    if not bars_rth_today or len(bars_rth_today) < 1:
        return None, None
    try:
        bars = bars_rth_today  # all closed bars
        if not bars:
            return None, None

        high_val = float("-inf")
        low_val = float("inf")
        high_idx = 0
        low_idx = 0

        for i, b in enumerate(bars):
            h = float(b.get("h") or b.get("high") or 0)
            l = float(b.get("l") or b.get("low") or float("inf"))
            if h >= high_val:
                high_val = h
                high_idx = i
            if l <= low_val:
                low_val = l
                low_idx = i

        n = len(bars)
        bars_since_high = (n - 1) - high_idx
        bars_since_low = (n - 1) - low_idx
        return bars_since_high, bars_since_low
    except Exception:
        return None, None


def _compute_atr_causal(bars_rth_today: Optional[List[Dict]]) -> Optional[float]:
    """ATR14 on the last 14 closed bars (true range)."""
    if not bars_rth_today or len(bars_rth_today) < 2:
        return None
    try:
        bars = bars_rth_today[-15:]  # need 15 bars for 14 true-range values
        if len(bars) < 2:
            return None
        true_ranges: list[float] = []
        for i in range(1, len(bars)):
            h = float(bars[i].get("h") or bars[i].get("high") or 0)
            l = float(bars[i].get("l") or bars[i].get("low") or 0)
            prev_c = float(bars[i - 1].get("c") or bars[i - 1].get("close") or 0)
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            true_ranges.append(tr)
        if not true_ranges:
            return None
        # Use the last 14 true-ranges
        tr14 = true_ranges[-14:]
        return round(sum(tr14) / len(tr14), 4)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Bars for the live vector (cowork 17.09 14:50, replaces the F4 wiring that
# read `five_min_system._cf_bars` — a LOCAL variable in that module, never an
# attribute — and a prior-sessions query that dropped `ts`, so vol_ratio /
# bars_since_* / atr_causal stayed None live). One DB read per 5-minute
# bucket, cached; closed bars only (ts <= now - 5 min); RTH 09:30-16:00 ET.
# ---------------------------------------------------------------------------

_BARS_CACHE: Dict[str, Any] = {"bucket": None, "today": None, "prior": None}
_BARS_LOCK = threading.Lock()


def load_bars_for_vector(now_utc: Optional[datetime] = None):
    """Return (bars_rth_today, prior_sessions_bars) for compute_situation_vector.

    Fail-open: any error → (None, None). Bars are dicts with ts (ISO UTC),
    o/h/l/c/v so both key styles used by the helpers above resolve.
    """
    try:
        now = now_utc or datetime.now(timezone.utc)
        bucket = now.strftime("%Y-%m-%d %H:") + f"{(now.minute // 5) * 5:02d}"
        with _BARS_LOCK:
            if _BARS_CACHE["bucket"] == bucket:
                return _BARS_CACHE["today"], _BARS_CACHE["prior"]
        from backend.v9.db.read import read_all
        rows = read_all(
            "SELECT ts, (ts AT TIME ZONE 'America/New_York')::date AS d, "
            "       open, high, low, close, volume "
            "FROM v9_bars_5min_woodies "
            "WHERE ts >= (:now)::timestamptz - INTERVAL '21 day' "
            "  AND ts <= (:now)::timestamptz - INTERVAL '5 minute' "
            "  AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
            "  AND (ts AT TIME ZONE 'America/New_York')::time <= '16:00' "
            "ORDER BY ts",
            {"now": now.isoformat()},
        )
        by_date: Dict[str, List[Dict]] = {}
        for r in rows or []:
            ts = r.get("ts")
            ts_iso = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
            bar = {
                "ts": ts_iso,
                "o": r.get("open"), "h": r.get("high"), "l": r.get("low"),
                "c": r.get("close"), "v": r.get("volume"),
                "open": r.get("open"), "high": r.get("high"), "low": r.get("low"),
                "close": r.get("close"), "volume": r.get("volume"),
            }
            by_date.setdefault(str(r.get("d")), []).append(bar)
        dates = sorted(by_date)
        # today = the ET date of `now`; prior = up to 10 sessions before it
        try:
            from zoneinfo import ZoneInfo
            today_et = now.astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
        except Exception:
            today_et = dates[-1] if dates else None
        today_bars = by_date.get(today_et) or None
        prior = [by_date[d] for d in dates if d < (today_et or "")][-10:] or None
        with _BARS_LOCK:
            _BARS_CACHE.update({"bucket": bucket, "today": today_bars, "prior": prior})
        return today_bars, prior
    except Exception as exc:
        logger.warning("[SituationVector] load_bars_for_vector failed (fail-open): %s", exc)
        return None, None


# ---------------------------------------------------------------------------
# Non-blocking DB logger
# ---------------------------------------------------------------------------

_SV_LOG_ENABLED = os.getenv("SITUATION_VECTOR_LOG_V1", "1").lower() in ("1", "true", "yes")


def log_decision_vector(
    *,
    ts: str,
    kind: str = "DECISION",
    system: Optional[int] = None,
    classification: Optional[str] = None,
    direction: Optional[str] = None,
    entry: Optional[float] = None,
    phase: Optional[str] = None,
    blocked_by: Optional[str] = None,
    reason: Optional[str] = None,
    mode_result: Optional[dict] = None,
    vector: Optional[dict] = None,
) -> None:
    """Write one row to ``v9_decision_vectors``.  Non-blocking via background
    thread, error-swallowed.  Gated behind ``SITUATION_VECTOR_LOG_V1`` (default ON).
    """
    if not _SV_LOG_ENABLED:
        return

    def _do_write():
        try:
            import json as _sv_json
            from backend.v9.db.safe_writer import safe_execute
            safe_execute(
                """INSERT INTO v9_decision_vectors
                (ts, kind, system, classification, direction, entry,
                 phase, blocked_by, reason, mode_result, vector, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ts, kind, system, classification, direction, entry,
                    phase, blocked_by, reason,
                    _sv_json.dumps(mode_result, default=str) if mode_result else None,
                    _sv_json.dumps(vector, default=str) if vector else None,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        except Exception as exc:
            logger.warning("[SituationVector] log_decision_vector failed (swallowed): %s", exc)

    # T-390b: non-blocking write via background thread
    t = threading.Thread(target=_do_write, daemon=True)
    t.start()
