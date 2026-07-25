"""higher_low_second_test — W6 (2026-07-25): "ירידה בפעם השנייה → רכישה בחלק הגבוה".

Michael mandate: detect a second pullback that stops ABOVE the first pullback's low
(higher-low L2 > L1), and enter on a rejection bar at the higher level.

Structure (LONG, S2 system):
  (1) Directional push >= MIN_PUSH_PTS points
  (2) First pullback → low L1
  (3) Recovery >= RECOVERY_PCT of the push
  (4) Second dip that stops ABOVE L1 (higher-low: L2 > L1 + MARGIN_TICKS * TICK_SIZE)
  (5) Rejection bar: close above L2 → LONG at the close of the rejection bar

Symmetric SHORT: inverted (lower-high test on a down-push).

Flag: HIGHER_LOW_SECOND_TEST_V1 (default OFF). When OFF, returns (None, 0.0, {}).
RTH only (gated upstream by DAY_TYPE_MODE). One trade per structure (dedup upstream).

Detection geometry defaults (SHADOW-calibratable):
  MIN_PUSH_PTS       = 8.0    # minimum directional push magnitude
  RECOVERY_PCT       = 0.33   # min 33% recovery from L1
  MARGIN_TICKS       = 2      # L2 must be >= L1 + MARGIN_TICKS * TICK_SIZE above
  SEARCH_WINDOW      = 24     # last N bars for structure detection
  TICK_SIZE           = 0.25   # MES
"""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Literal, Optional, Tuple

logger = logging.getLogger(__name__)

Direction = Literal["LONG", "SHORT"]

# Detection geometry — SHADOW-calibratable
MIN_PUSH_PTS = float(os.environ.get("HLST_MIN_PUSH_PTS", "8.0"))
RECOVERY_PCT = float(os.environ.get("HLST_RECOVERY_PCT", "0.33"))
MARGIN_TICKS = int(os.environ.get("HLST_MARGIN_TICKS", "2"))
SEARCH_WINDOW = int(os.environ.get("HLST_SEARCH_WINDOW", "24"))
TICK_SIZE = 0.25


def _flag_on() -> bool:
    return os.environ.get("HIGHER_LOW_SECOND_TEST_V1", "").lower() in ("1", "true", "yes")


def _find_push_and_pullbacks_long(
    bars: List[Dict],
) -> Optional[Dict]:
    """Scan bars for: push-up → L1 (first pullback low) → recovery → L2 (higher low).

    Returns info dict if the 5-phase structure is found, else None.
    """
    if len(bars) < 6:
        return None

    window = bars[-SEARCH_WINDOW:] if len(bars) > SEARCH_WINDOW else bars

    highs = [float(b.get("high", b.get("h", 0))) for b in window]
    lows = [float(b.get("low", b.get("l", 0))) for b in window]
    closes = [float(b.get("close", b.get("c", 0))) for b in window]

    n = len(window)
    if n < 6:
        return None

    # Phase 1: find the push-up peak (highest high in the window)
    peak_idx = max(range(n), key=lambda i: highs[i])
    if peak_idx < 2:
        return None  # need bars before the peak for the push

    # Push start: lowest low before the peak
    push_start_idx = min(range(peak_idx + 1), key=lambda i: lows[i])
    push_pts = highs[peak_idx] - lows[push_start_idx]
    if push_pts < MIN_PUSH_PTS:
        return None

    # Phase 2: first pullback L1 — lowest low after the peak
    remaining = range(peak_idx + 1, n)
    if len(list(remaining)) < 3:
        return None
    remaining = list(range(peak_idx + 1, n))

    l1_idx = min(remaining, key=lambda i: lows[i])
    L1 = lows[l1_idx]

    # Phase 3: recovery from L1 — highest high between L1 and end
    if l1_idx >= n - 2:
        return None  # need room for L2 + rejection
    recovery_range = list(range(l1_idx + 1, n))
    if not recovery_range:
        return None

    recovery_peak_idx = max(recovery_range, key=lambda i: highs[i])
    recovery_pts = highs[recovery_peak_idx] - L1
    recovery_pct = recovery_pts / push_pts if push_pts > 0 else 0
    if recovery_pct < RECOVERY_PCT:
        return None

    # Phase 4: second dip L2 — lowest low after recovery peak
    l2_range = list(range(recovery_peak_idx + 1, n))
    if not l2_range:
        return None

    l2_idx = min(l2_range, key=lambda i: lows[i])
    L2 = lows[l2_idx]

    # Higher-low check: L2 must be ABOVE L1 + margin
    margin = MARGIN_TICKS * TICK_SIZE
    if L2 <= L1 + margin:
        return None

    # Phase 5: rejection bar — the current (last) bar must close above L2
    last_bar = window[-1]
    last_close = closes[-1]
    last_low = lows[-1]

    # The rejection bar should show buying pressure: close in upper half
    last_high = highs[-1]
    bar_range = last_high - last_low
    if bar_range <= 0:
        return None
    close_position = (last_close - last_low) / bar_range
    if close_position < 0.5:
        return None  # not a rejection bar (close not in upper half)

    if last_close <= L2:
        return None  # must close above L2

    # The rejection bar should be at or near L2 (within the second dip zone)
    if last_low > L2 + push_pts * 0.5:
        return None  # too far from the dip — not testing L2

    entry_price = last_close

    return {
        "kind": "HIGHER_LOW_SECOND_TEST",
        "pattern_name": "HIGHER_LOW_SECOND_TEST_LONG",
        "structural_anchor": L2,
        "stage": 5,
        "push_pts": round(push_pts, 2),
        "L1": round(L1, 2),
        "L2": round(L2, 2),
        "recovery_pct": round(recovery_pct, 3),
        "entry_price": round(entry_price, 2),
        "peak": round(highs[peak_idx], 2),
    }


def _find_push_and_pullbacks_short(
    bars: List[Dict],
) -> Optional[Dict]:
    """Symmetric SHORT: push-down → H1 (first rally high) → drop → H2 (lower high)."""
    if len(bars) < 6:
        return None

    window = bars[-SEARCH_WINDOW:] if len(bars) > SEARCH_WINDOW else bars

    highs = [float(b.get("high", b.get("h", 0))) for b in window]
    lows = [float(b.get("low", b.get("l", 0))) for b in window]
    closes = [float(b.get("close", b.get("c", 0))) for b in window]

    n = len(window)
    if n < 6:
        return None

    # Phase 1: push-down trough (lowest low)
    trough_idx = min(range(n), key=lambda i: lows[i])
    if trough_idx < 2:
        return None

    push_start_idx = max(range(trough_idx + 1), key=lambda i: highs[i])
    push_pts = highs[push_start_idx] - lows[trough_idx]
    if push_pts < MIN_PUSH_PTS:
        return None

    # Phase 2: first rally H1 — highest high after the trough
    remaining = list(range(trough_idx + 1, n))
    if len(remaining) < 3:
        return None

    h1_idx = max(remaining, key=lambda i: highs[i])
    H1 = highs[h1_idx]

    # Phase 3: drop from H1
    if h1_idx >= n - 2:
        return None
    drop_range = list(range(h1_idx + 1, n))
    if not drop_range:
        return None

    drop_trough_idx = min(drop_range, key=lambda i: lows[i])
    drop_pts = H1 - lows[drop_trough_idx]
    recovery_pct = drop_pts / push_pts if push_pts > 0 else 0
    if recovery_pct < RECOVERY_PCT:
        return None

    # Phase 4: second rally H2 — highest high after drop trough
    h2_range = list(range(drop_trough_idx + 1, n))
    if not h2_range:
        return None

    h2_idx = max(h2_range, key=lambda i: highs[i])
    H2 = highs[h2_idx]

    # Lower-high check: H2 must be BELOW H1 - margin
    margin = MARGIN_TICKS * TICK_SIZE
    if H2 >= H1 - margin:
        return None

    # Phase 5: rejection bar — close in lower half, below H2
    last_close = closes[-1]
    last_low = lows[-1]
    last_high = highs[-1]
    bar_range = last_high - last_low
    if bar_range <= 0:
        return None
    close_position = (last_close - last_low) / bar_range
    if close_position > 0.5:
        return None  # not a bearish rejection

    if last_close >= H2:
        return None

    if last_high < H2 - push_pts * 0.5:
        return None

    entry_price = last_close

    return {
        "kind": "HIGHER_LOW_SECOND_TEST",
        "pattern_name": "HIGHER_LOW_SECOND_TEST_SHORT",
        "structural_anchor": H2,
        "stage": 5,
        "push_pts": round(push_pts, 2),
        "L1": round(H1, 2),  # H1 for SHORT (first rally high)
        "L2": round(H2, 2),  # H2 for SHORT (lower high)
        "recovery_pct": round(recovery_pct, 3),
        "entry_price": round(entry_price, 2),
        "peak": round(lows[trough_idx], 2),
    }


def detect_higher_low_second_test_long(
    bars: List[Dict],
) -> Tuple[Optional[Direction], float, Dict]:
    """Detect Higher-Low Second Test — LONG.

    Returns (direction, confidence, info) or (None, 0.0, {}).
    Flag-gated: HIGHER_LOW_SECOND_TEST_V1 (default OFF).
    """
    if not _flag_on():
        return (None, 0.0, {})

    info = _find_push_and_pullbacks_long(bars)
    if info is None:
        return (None, 0.0, {})

    logger.info(
        "[HLST] DETECTED LONG: push=%.1fpt L1=%.2f L2=%.2f (HL margin=%.2f) "
        "recovery=%.0f%% entry=%.2f",
        info["push_pts"], info["L1"], info["L2"],
        info["L2"] - info["L1"], info["recovery_pct"] * 100,
        info["entry_price"],
    )
    return ("LONG", 0.75, info)


def detect_higher_low_second_test_short(
    bars: List[Dict],
) -> Tuple[Optional[Direction], float, Dict]:
    """Detect Higher-Low Second Test — SHORT (symmetric: lower-high test).

    Returns (direction, confidence, info) or (None, 0.0, {}).
    Flag-gated: HIGHER_LOW_SECOND_TEST_V1 (default OFF).
    """
    if not _flag_on():
        return (None, 0.0, {})

    info = _find_push_and_pullbacks_short(bars)
    if info is None:
        return (None, 0.0, {})

    logger.info(
        "[HLST] DETECTED SHORT: push=%.1fpt H1=%.2f H2=%.2f (LH margin=%.2f) "
        "recovery=%.0f%% entry=%.2f",
        info["push_pts"], info["L1"], info["L2"],
        info["L1"] - info["L2"], info["recovery_pct"] * 100,
        info["entry_price"],
    )
    return ("SHORT", 0.75, info)
