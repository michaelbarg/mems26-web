"""opening_type_gate — blocks counter-drive fires during the opening window.

#68 FIX B. Governs ONLY RTH open → IB-lock (~60min). After IB-lock, inert.

Rules:
  OPEN_DRIVE / OPEN_TEST_DRIVE → ALLOW with-drive, BLOCK counter-drive.
  OPEN_AUCTION / rotation       → HOLD all fires (no edge).
  Drive fails (returned_through_open) → release.

Flag: OPENING_TYPE_GATE (default OFF). Fail-open on missing data.
"""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# How many bars constitute a "drive detection window" (30 min = 6 bars of 5min)
_DRIVE_DETECT_BARS = 6


def _enabled() -> bool:
    return os.environ.get("OPENING_TYPE_GATE", "0").lower() in ("1", "true", "yes")


def decide(
    *,
    direction: str,
    rth_bars: List[Dict],
    ib_locked: bool,
    opening_print: Optional[float] = None,
) -> Tuple[bool, str]:
    """Decide whether to allow/block a fire based on opening-type analysis.

    Args:
        direction: "LONG" or "SHORT"
        rth_bars: RTH 5-min bars accumulated so far [{o,h,l,c,...}]
        ib_locked: True after IB lock (60 min) → gate becomes inert
        opening_print: first RTH bar's open price

    Returns:
        (allow: bool, reason: str)
    """
    if not _enabled():
        return (True, "gate OFF")

    # After IB lock → inert (position gate takes over)
    if ib_locked:
        return (True, "post-IB-lock (inert)")

    if not rth_bars:
        return (True, "no RTH bars yet (fail-open)")

    dir_upper = direction.upper()

    # Determine opening print
    if opening_print is None:
        opening_print = rth_bars[0].get("o", rth_bars[0].get("open"))
    if opening_print is None:
        return (True, "no opening print (fail-open)")

    n = len(rth_bars)

    # Detect drive direction
    _cvd_flag = os.environ.get("OPENING_FIRE_CVD_V1", "0").lower() in ("1", "true", "yes")
    if n >= _DRIVE_DETECT_BARS:
        # Use opening_detector_v2 for classification
        drive_type, drive_dir = _detect_from_bars(
            rth_bars[:_DRIVE_DETECT_BARS], opening_print, cvd_confirm=_cvd_flag,
        )
    else:
        # Early bars: use running bias = sign(last_close − opening_print)
        drive_type, drive_dir = _early_bias(rth_bars, opening_print)

    # Check if drive has failed (price returned through opening print)
    if _drive_failed(rth_bars, opening_print):
        return (True, f"drive failed (returned through open) — released")

    # Apply rules based on opening type
    if drive_type in ("OPEN_DRIVE", "OPEN_TEST_DRIVE", "EARLY_BIAS"):
        if drive_dir == "UP":
            if dir_upper == "SHORT":
                return (False, f"counter-drive: SHORT against {drive_type} UP")
            return (True, f"with-drive: LONG with {drive_type} UP")
        elif drive_dir == "DOWN":
            if dir_upper == "LONG":
                return (False, f"counter-drive: LONG against {drive_type} DOWN")
            return (True, f"with-drive: SHORT with {drive_type} DOWN")
        # NEUTRAL direction on a drive → fail-open
        return (True, f"{drive_type} direction NEUTRAL (fail-open)")

    if drive_type in ("OPEN_AUCTION_IN", "OPEN_AUCTION_OUT", "OPEN_AUCTION"):
        return (False, f"HOLD: {drive_type} — no opening edge (rotation)")

    if drive_type == "OPEN_REJECTION_REVERSE":
        # ORR: the reversal direction is the drive direction
        if drive_dir == "UP" and dir_upper == "SHORT":
            return (False, f"counter-drive: SHORT against ORR UP")
        if drive_dir == "DOWN" and dir_upper == "LONG":
            return (False, f"counter-drive: LONG against ORR DOWN")
        return (True, f"with-drive: {dir_upper} with ORR {drive_dir}")

    # UNKNOWN → fail-open
    return (True, f"opening_type={drive_type} (fail-open)")


def _compute_opening_cvd_pos() -> Optional[float]:
    """Read CVD for today's RTH opening window from v9_bars_cumulative_delta.

    Uses the dedicated CVD stream table (fresher than v9_bars_5min.cumulative_delta
    which can go stale). Includes a freshness guard: if the newest CVD row in the
    window is older than 10 minutes, return None (stale data = no CVD confirmation).

    Returns cvd_pos ∈ [0..1] (>0.5 = buy-dominant), or None if unavailable/stale.
    Fail-safe: any error → None (caller proceeds without CVD).
    """
    try:
        from backend.v9.db.read import read_all
        import datetime as _dt
        from zoneinfo import ZoneInfo as _ZI
        _et = _ZI("America/New_York")
        _now_et = _dt.datetime.now(_et)
        _today = _now_et.date().isoformat()
        # I-53 fix (2026-07-03): ts column is TEXT in this table — a bare
        # "ts AT TIME ZONE" raises UndefinedFunction on varchar and the except
        # swallowed it, leaving OPENING_FIRE_CVD_V1 silently inert (STATUS_BOARD
        # 07-01). ::timestamptz is a no-op on real timestamptz columns.
        rows = read_all(
            "SELECT cumulative, ts FROM v9_bars_cumulative_delta "
            "WHERE (ts::timestamptz AT TIME ZONE 'America/New_York')::date = :d "
            "  AND (ts::timestamptz AT TIME ZONE 'America/New_York')::time >= '09:30' "
            "ORDER BY ts::timestamptz ASC LIMIT :n",
            {"d": _today, "n": _DRIVE_DETECT_BARS},
        )
        cum = [float(r["cumulative"]) for r in rows
               if r.get("cumulative") is not None]
        if not cum:
            return None
        # Freshness guard: newest row must be within 10 minutes of now
        last_ts = rows[-1].get("ts")
        if last_ts is not None:
            if isinstance(last_ts, str):
                last_ts = _dt.datetime.fromisoformat(last_ts)
            if hasattr(last_ts, "tzinfo") and last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=_dt.timezone.utc)
            age = (_now_et - last_ts.astimezone(_et)).total_seconds()
            if age > 600:  # 10 minutes
                logger.warning("[OPENING_FIRE_CVD] CVD data stale (%.0fs old) — skipping", age)
                return None
        mx, mn = max(cum), min(cum)
        return round((cum[-1] - mn) / (mx - mn), 4) if mx > mn else 0.5
    except Exception:
        return None


def _detect_from_bars(
    bars: List[Dict], opening_print: float, *, cvd_confirm: bool = False,
) -> Tuple[str, str]:
    """Use opening_detector_v2 on the first 6 RTH bars.

    When cvd_confirm=True (OPENING_FIRE_CVD_V1 ON), computes cvd_pos from
    v9_bars_5min.cumulative_delta and requires CVD alignment for OPEN_DRIVE.
    """
    try:
        from backend.v9.systems.day_type.opening_detector_v2 import detect_opening_type
        kwargs: Dict = {}
        if cvd_confirm:
            cvd_pos = _compute_opening_cvd_pos()
            if cvd_pos is not None:
                kwargs["cvd_pos"] = cvd_pos
                kwargs["cvd_confirm_drive"] = True
                logger.info("[OPENING_FIRE_CVD] cvd_pos=%.4f for opening window", cvd_pos)
            else:
                logger.warning("[OPENING_FIRE_CVD] cvd_pos unavailable — proceeding without CVD confirmation")
        result = detect_opening_type(bars, opening_print, **kwargs)
        return result.get("opening_type", "UNKNOWN"), result.get("direction", "NEUTRAL")
    except Exception:
        return "UNKNOWN", "NEUTRAL"


def _early_bias(
    bars: List[Dict], opening_print: float
) -> Tuple[str, str]:
    """Before 6 bars: running bias from sign(last_close − opening_print).

    H14 fix (Michael 13.08, after the gate blocked a +12pt winner): the bias
    used to be read off whatever the last element was — including a bar still
    FORMING. On 13.08 the opening bar spiked down to 7785 and then closed at
    its high (7798.5); the gate had latched "DOWN" from the intrabar spike and
    blocked the correct responsive LONG at 16:34 while the market ran +12pt.
    Two corrections, both structural:
      1. only CLOSED bars vote (the forming bar is dropped when we can tell);
      2. a bar that closes in the top/bottom third of its own range flips the
         bias to that side — a failed spike that closes at the high is an UP
         signal, not a DOWN one.
    Flag: OPENING_BIAS_BAR_CLOSE_REFRESH_V1 (default OFF → byte-identical to
    the old behaviour until replayed and ruled).
    """
    import os as _b_os
    closed = bars
    if (_b_os.environ.get("OPENING_BIAS_BAR_CLOSE_REFRESH_V1", "0").lower()
            in ("1", "true", "yes")) and len(bars) >= 2:
        # drop a still-forming last bar when the caller passes one
        if bars[-1].get("closed") is False or bars[-1].get("is_partial"):
            closed = bars[:-1]

    last = closed[-1] if closed else None
    if last is None:
        return "UNKNOWN", "NEUTRAL"
    last_close = last.get("c", last.get("close"))
    if last_close is None:
        return "UNKNOWN", "NEUTRAL"

    diff = last_close - opening_print
    if abs(diff) < 1.0:  # less than 1pt → no clear bias
        return "UNKNOWN", "NEUTRAL"

    direction = "UP" if diff > 0 else "DOWN"

    if _b_os.environ.get("OPENING_BIAS_BAR_CLOSE_REFRESH_V1", "0").lower() in ("1", "true", "yes"):
        h = last.get("h", last.get("high"))
        l = last.get("l", last.get("low"))
        try:
            rng = float(h) - float(l)
            if rng > 0:
                pos = (float(last_close) - float(l)) / rng   # 1.0 = closed at high
                if pos >= 0.66 and direction == "DOWN":
                    logger.info("[OpeningGate] H14: close in top third (%.2f) → bias DOWN→UP", pos)
                    direction = "UP"
                elif pos <= 0.34 and direction == "UP":
                    logger.info("[OpeningGate] H14: close in bottom third (%.2f) → bias UP→DOWN", pos)
                    direction = "DOWN"
        except (TypeError, ValueError):
            pass

    return "EARLY_BIAS", direction


# ---------------------------------------------------------------------------
# Item-10 · OPENING_WINDOW_FIRE_V1 (Michael standing order, 2026-07-02):
# "לצורך עסקה ראשונה, ברגע שהמערכת מזהה לפי סוג הפתיחה עסקה — לבצע גם בחצי
# השעה הראשונה." During the first 30 minutes of RTH the day-type label is an
# immature stage-1 guess. Live incidents (2026-07-02): 16:35:04 IL gateway
# "ZLR SKIP on Nontrend" 5 min after open · 16:45:03 IL in-system S2
# "T1Setup skipped: INITIATIVE_LONG day_type=UNKNOWN · Auth Table SKIP".
# This override lets a fire through those DAY-TYPE-based refusals ONLY on
# POSITIVE with-drive confirmation from the opening-type machinery. It never
# fail-opens. Every other gate (session, kill-switch, feed-watchdog, dedup,
# risk-cap, target-side guards, OPENING_TYPE_GATE counter-drive block) still
# applies unchanged.
# Flag: OPENING_WINDOW_FIRE_V1 (default OFF — enable only with Michael's word).
# ---------------------------------------------------------------------------

_OW_WINDOW_START_MIN = 8 * 60 + 30  # 08:30 America/Chicago = RTH open (TZ explicit, Rule 4)
_OW_WINDOW_END_MIN = 9 * 60         # 09:00 America/Chicago = end of first 30 minutes


def _ow_enabled() -> bool:
    return os.environ.get("OPENING_WINDOW_FIRE_V1", "0").lower() in ("1", "true", "yes")


def _load_rth_bars_from_db(limit: int = _DRIVE_DETECT_BARS) -> List[Dict]:
    """First `limit` RTH bars today from canonical v9_bars_5min_woodies (SoT).

    ts cast defensively (::timestamptz is a no-op on timestamptz columns,
    fixes TEXT — I-53 class). Fail-safe: any error → [] (no override).
    """
    try:
        from backend.v9.db.read import read_all
        rows = read_all(
            "SELECT open AS o, high AS h, low AS l, close AS c "
            "FROM v9_bars_5min_woodies "
            "WHERE (ts::timestamptz AT TIME ZONE 'America/Chicago')::date = "
            "      (now() AT TIME ZONE 'America/Chicago')::date "
            "  AND (ts::timestamptz AT TIME ZONE 'America/Chicago')::time >= '08:30' "
            "ORDER BY ts::timestamptz ASC LIMIT :n",
            {"n": limit},
        )
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("[OPENING_WINDOW] RTH-bars DB read failed (no override): %s", e)
        return []


def opening_window_override(
    *,
    direction: str,
    rth_bars: Optional[List[Dict]] = None,
    opening_print: Optional[float] = None,
    now_min_ct: Optional[int] = None,
) -> Tuple[bool, str]:
    """POSITIVE-confirmation override for day-type refusals in the first 30 min.

    Returns (True, reason) ONLY when ALL hold: flag ON · now ∈ [08:30, 09:00)
    America/Chicago · an opening drive is detected (OPEN_DRIVE / OPEN_TEST_DRIVE
    / OPEN_REJECTION_REVERSE / EARLY_BIAS) · the fire direction is WITH the
    drive · the drive has not failed (no return through the opening print).
    Anything missing or ambiguous → (False, reason). Never fail-open.

    Consumers: setup_emitter (S2 Auth-Table SKIP + NO_TRADE refuse) and
    trading_gateway (day-type playbook SKIP) — the two live choke points.
    """
    if not _ow_enabled():
        return (False, "OPENING_WINDOW_FIRE_V1 off")
    if now_min_ct is None:
        import datetime as _dt
        from zoneinfo import ZoneInfo as _ZI
        _n = _dt.datetime.now(_ZI("America/Chicago"))
        now_min_ct = _n.hour * 60 + _n.minute
    if not (_OW_WINDOW_START_MIN <= now_min_ct < _OW_WINDOW_END_MIN):
        return (False, "outside first-30min window (08:30-09:00 CT)")
    if rth_bars is None:
        rth_bars = _load_rth_bars_from_db()
    if not rth_bars:
        return (False, "no RTH bars")
    if opening_print is None:
        opening_print = rth_bars[0].get("o", rth_bars[0].get("open"))
    if opening_print is None:
        return (False, "no opening print")
    if _drive_failed(rth_bars, opening_print):
        return (False, "drive failed (returned through open)")
    _cvd_flag = os.environ.get("OPENING_FIRE_CVD_V1", "0").lower() in ("1", "true", "yes")
    if len(rth_bars) >= _DRIVE_DETECT_BARS:
        drive_type, drive_dir = _detect_from_bars(
            rth_bars[:_DRIVE_DETECT_BARS], opening_print, cvd_confirm=_cvd_flag,
        )
    else:
        drive_type, drive_dir = _early_bias(rth_bars, opening_print)
    if drive_type not in ("OPEN_DRIVE", "OPEN_TEST_DRIVE", "OPEN_REJECTION_REVERSE", "EARLY_BIAS"):
        return (False, f"opening_type={drive_type} — no directional edge")
    _want = "UP" if direction.upper() == "LONG" else "DOWN"
    if drive_dir != _want:
        return (False, f"counter-drive: {direction.upper()} vs {drive_type} {drive_dir}")
    return (True, f"WITH-drive {drive_type} {drive_dir} (first-30min window)")


def _drive_failed(bars: List[Dict], opening_print: float) -> bool:
    """Check if the drive has failed: price drove away then returned through the open.

    A failed drive = at least 3 bars of directional move from the open,
    then the close returns to the other side of the opening print.
    """
    if len(bars) < 4:
        return False

    closes = [b.get("c", b.get("close")) for b in bars]
    closes = [c for c in closes if c is not None]
    if len(closes) < 4:
        return False

    # Check first 3 closes for a directional move
    first_3 = closes[:3]
    all_above = all(c > opening_print for c in first_3)
    all_below = all(c < opening_print for c in first_3)

    if not (all_above or all_below):
        return False

    # Check if later close returned through the open
    last_close = closes[-1]
    if all_above and last_close < opening_print:
        return True
    if all_below and last_close > opening_print:
        return True

    return False
