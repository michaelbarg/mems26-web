"""RELEASE_ENTRY_GATE_V1 — enter when price LEAVES the zone, not when it touches it.

Michael 2026-07-28: "אתמול הכניסה של הסים לעסקת לונג הייתה טובה אבל מוקדמת …
אפשר היה לזהות ולבצע כניסה בשלב אחר שהמחיר הפסיק להיות תקוע באותו אזור".

The 07-27 session is the specimen (a day whose bar timestamps are verified clean):

    19:15   low 7416.25                       vol 8235   ← the extreme
    19:20   higher low 7418.75                vol 6439
    19:25   higher low 7419.50                vol 4552   ← volume drying up
    19:35   higher low 7423.25                vol 4666
    19:45   higher low 7423.50                vol 4489   ← driest
    19:50   closes 7433.00, above the zone    vol 6239   ← THE RELEASE
    then    7436.50 … 7455.75

The system entered at 19:24 — inside the sticky zone, 26 minutes early, with a
9pt stop, and was stopped out before the move it had correctly predicted.

Three conditions, all required, all measured on closed 5-min bars:

  1. STRUCTURE  — `min_higher_lows` consecutive higher lows since the extreme
                  (mirrored: lower highs for a short). The market stops probing.
  2. EXHAUSTION — volume contracts: the mean of the last `vol_window` bars is
                  below `vol_ratio` × the volume of the extreme bar. Sellers
                  finish.
  3. RELEASE    — a bar CLOSES beyond the rotation zone, with volume above the
                  contracted mean. Price actually leaves.

A side effect that matters as much as the timing: entering on the release puts
the structural stop under the real extreme. On 07-27 that is 7433 with a stop
below 7416 — a 17pt stop, exactly the GB100 profile that survived, instead of
ZLR's 9pt that did not. Waiting for the release and sizing the stop correctly
are the same act.

This gate can only DELAY or SKIP a signal the system already produced. It never
creates one, never changes direction, never widens risk on its own.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Sequence

logger = logging.getLogger(__name__)


def enabled() -> bool:
    return os.getenv("RELEASE_ENTRY_GATE_V1", "0").strip().lower() in ("1", "true", "yes")


def _f(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _i(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass
class Bar:
    high: float
    low: float
    close: float
    volume: float
    delta: Optional[float] = None


@dataclass
class ReleaseVerdict:
    released: bool
    reason: str
    structural_stop: Optional[float] = None   # beyond the extreme, for the caller
    higher_lows: int = 0
    vol_ratio: Optional[float] = None


def _delta_breakout_release(
    bars: Sequence[Bar], direction: str,
    accepted_break: Optional[str],
) -> Optional[ReleaseVerdict]:
    """§7 DELTA_BREAKOUT_RELEASE_V1: release on delta conviction, no structure wait.

    Returns ReleaseVerdict if this path decides; None if it can't (Rule 1).
    Only runs when the flag is ON and accepted_break is present.
    """
    flag = os.getenv("DELTA_BREAKOUT_RELEASE_V1", "0").strip().lower()
    if flag not in ("1", "shadow", "true", "yes"):
        return None
    if not accepted_break:
        return None

    is_long = str(direction).upper() == "LONG"
    # Delta must confirm the break direction
    if (is_long and accepted_break == "DOWN") or (not is_long and accepted_break == "UP"):
        return None

    # Need bars with delta data
    bars_with_delta = [(i, b) for i, b in enumerate(bars) if b.delta is not None]
    if len(bars_with_delta) < 2:
        return None  # Rule 1: insufficient data → no decision

    # Session max delta (in break direction) and max volume
    if is_long:
        max_delta = max(b.delta for _, b in bars_with_delta)
    else:
        max_delta = min(b.delta for _, b in bars_with_delta)
    max_vol = max(b.volume for _, b in bars_with_delta) if bars_with_delta else 0

    # Check the latest bar
    last_i, last = bars_with_delta[-1]
    if last.delta is None or max_vol <= 0:
        return None

    # Conditions: delta ≥ session max AND volume ≥ 0.7 × session max
    delta_ok = (last.delta >= max_delta) if is_long else (last.delta <= max_delta)
    vol_ok = last.volume >= 0.7 * max_vol
    is_shadow = flag == "shadow"

    if delta_ok and vol_ok:
        buf = _f("RELEASE_STOP_BUFFER_POINTS", 1.0)
        ext = min(b.low for b in bars) if is_long else max(b.high for b in bars)
        stop = round((ext - buf) if is_long else (ext + buf), 2)
        verdict = ReleaseVerdict(
            True,
            f"released (delta-breakout): delta={last.delta:.0f} "
            f"(session {'max' if is_long else 'min'}={max_delta:.0f}), "
            f"vol={last.volume:.0f} (≥70% of {max_vol:.0f})"
            + (" [SHADOW]" if is_shadow else ""),
            structural_stop=stop)
        if is_shadow:
            logger.warning("[ReleaseGate] §7 SHADOW: %s", verdict.reason)
            return None  # shadow: log but don't release
        return verdict

    return None  # conditions not met → fall through to structure path


def check_release(bars: Sequence[Bar], direction: str,
                  accepted_break: Optional[str] = None) -> ReleaseVerdict:
    """Pure. `bars` are closed 5-min bars, oldest → newest, covering the window
    from the extreme to now. Returns whether price has released from the zone.

    Unknown / insufficient data → released=False. A gate that fails open would
    reproduce exactly the early entry it exists to prevent (Rule 1)."""
    min_hl = _i("RELEASE_MIN_HIGHER_LOWS", 2)
    vol_window = _i("RELEASE_VOL_WINDOW", 3)
    vol_ratio_max = _f("RELEASE_VOL_RATIO", 0.75)
    zone_pts = _f("RELEASE_ZONE_POINTS", 8.0)
    max_bars = _i("RELEASE_MAX_BARS", 24)          # give up after ~2h

    if not bars or len(bars) < min_hl + vol_window:
        return ReleaseVerdict(False, f"not enough bars ({len(bars)})")

    # §7 DELTA_BREAKOUT_RELEASE_V1: try delta-based release FIRST
    _dbr = _delta_breakout_release(bars, direction, accepted_break)
    if _dbr is not None:
        return _dbr

    is_long = str(direction).upper() == "LONG"
    window = list(bars)[-max_bars:]

    # 1 — the extreme, and the rotation zone above/below it
    if is_long:
        ext = min(b.low for b in window)
        ext_i = max(i for i, b in enumerate(window) if b.low == ext)
        zone_hi, zone_lo = ext + zone_pts, ext
    else:
        ext = max(b.high for b in window)
        ext_i = max(i for i, b in enumerate(window) if b.high == ext)
        zone_hi, zone_lo = ext, ext - zone_pts

    after = window[ext_i + 1:]
    if len(after) < max(min_hl, vol_window):
        return ReleaseVerdict(False, f"only {len(after)} bars since the extreme")

    # 2 — structure: consecutive higher lows (or lower highs)
    hl = 0
    prev = window[ext_i]
    for b in after:
        better = (b.low > prev.low) if is_long else (b.high < prev.high)
        hl = hl + 1 if better else 0
        prev = b
    if hl < min_hl:
        return ReleaseVerdict(False, f"structure not turning ({hl}/{min_hl} higher lows)",
                              higher_lows=hl)

    # 3 — exhaustion: volume contracting versus the extreme bar
    ext_vol = window[ext_i].volume or 0.0
    recent = [b.volume or 0.0 for b in after[-vol_window:]]
    mean_recent = sum(recent) / len(recent) if recent else 0.0
    ratio = (mean_recent / ext_vol) if ext_vol > 0 else None
    if ratio is None:
        return ReleaseVerdict(False, "no volume on the extreme bar — cannot judge exhaustion",
                              higher_lows=hl)
    last = after[-1]
    if ratio > vol_ratio_max:
        # V-REVERSAL PATH (2026-07-29). The contraction requirement models a slow
        # rotational turn (07-27). A V-reversal turns on HIGH volume — demanding
        # dry-up meant today's bottom (low 7373 19:15, structure + closes beyond
        # the zone by 19:25) was never "released" and every long into the +62pt
        # recovery was held. If the structure has turned AND price has CLOSED
        # decisively beyond the zone (1.5× zone-width past the edge), conviction
        # replaces contraction. A close barely past the edge on flat volume is
        # NOT a V-reversal — the market is still trading the level.
        v_factor = _f("RELEASE_V_REVERSAL_CLOSE_FACTOR", 1.5)
        v_threshold = zone_pts * v_factor
        decisive = (last.close > zone_hi + v_threshold) if is_long else (last.close < zone_lo - v_threshold)
        if hl >= min_hl and decisive:
            buf = _f("RELEASE_STOP_BUFFER_POINTS", 1.0)
            stop = round((ext - buf) if is_long else (ext + buf), 2)
            return ReleaseVerdict(
                True,
                f"released (V-reversal): {hl} higher lows, closed a full zone "
                f"beyond ({last.close}) on active volume {ratio:.2f}",
                structural_stop=stop, higher_lows=hl, vol_ratio=ratio)
        return ReleaseVerdict(False,
                              f"still active in the zone (vol {ratio:.2f} > {vol_ratio_max})",
                              higher_lows=hl, vol_ratio=ratio)

    # 4 — release: the last CLOSED bar leaves the zone on returning volume
    last = after[-1]
    left = (last.close > zone_hi) if is_long else (last.close < zone_lo)
    if not left:
        return ReleaseVerdict(False,
                              f"has not left the zone (close {last.close} vs "
                              f"{zone_hi if is_long else zone_lo})",
                              higher_lows=hl, vol_ratio=ratio)
    if (last.volume or 0.0) <= mean_recent:
        return ReleaseVerdict(False, "left the zone without volume — not convincing",
                              higher_lows=hl, vol_ratio=ratio)

    buf = _f("RELEASE_STOP_BUFFER_POINTS", 1.0)
    stop = round((ext - buf) if is_long else (ext + buf), 2)
    return ReleaseVerdict(
        True,
        f"released: {hl} higher lows, vol {ratio:.2f} of the extreme, "
        f"closed {last.close} beyond the zone",
        structural_stop=stop, higher_lows=hl, vol_ratio=ratio)


def bars_from_rows(rows: Sequence[dict], delta_map: Optional[dict] = None) -> List[Bar]:
    """Adapt DB rows (high/low/close/volume) — skips anything unusable.
    delta_map: optional {ts_str: delta_value} for §7 delta-breakout path.
    """
    out: List[Bar] = []
    for r in rows or []:
        try:
            _d = None
            if delta_map and r.get("ts"):
                _d = delta_map.get(str(r["ts"]))
            out.append(Bar(float(r["high"]), float(r["low"]),
                           float(r["close"]), float(r.get("volume") or 0.0),
                           delta=_d))
        except (KeyError, TypeError, ValueError):
            continue
    return out

def trend_bypass(session_open: Optional[float], last_price: Optional[float],
                 direction: str, pts: Optional[float] = None) -> bool:
    """With-move entries skip the gate once the session is DISPLACED (2026-07-29).

    The audit that forced this: 29 validated winners blocked today, the release
    gate responsible for 16 of them, on an 80pt trend-down + 62pt V-reversal.
    Root: this gate models a ROTATION (higher lows, drying volume, then exit).
    A trending session has no zone to release FROM — price just keeps going —
    so the gate held every with-trend short all the way down. Yesterday, a
    rotation day, the same gate saved 7/0. Right tool, wrong regime.

    Bypass rule: when |last - session_open| >= RELEASE_TREND_BYPASS_PTS (15)
    AND the signal points WITH the displacement, the market is trending and the
    rotation model does not apply. Counter-move entries keep the gate (that is
    where it earned its 7/0). Unknown inputs -> no bypass (fail-closed)."""
    try:
        if session_open is None or last_price is None:
            return False
        thr = pts if pts is not None else float(os.getenv("RELEASE_TREND_BYPASS_PTS", "15"))
        disp = float(last_price) - float(session_open)
        if abs(disp) < thr:
            return False
        d = str(direction).upper()
        return (disp < 0 and d == "SHORT") or (disp > 0 and d == "LONG")
    except Exception:
        return False

