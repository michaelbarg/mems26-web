"""head_shoulders — Inverse H&S (LONG) + H&S Top (SHORT) detectors per D-091 §5+§6.

Geometric Bulkowski-style detection · 3 swing points · neckline · breakout trigger.
Stage 3 only · gated upstream in five_min_system.process_bar.

Detection geometry defaults (Cursor-seeded per Michael 24/5 16:32 IL · SHADOW-calibratable):
  MIN_BARS_REQUIRED  = 12       # Path B seed · Bulkowski "15-25 bar pattern" short end
  SEARCH_WINDOW      = 30       # Path B seed · last N bars searched for pivots
  PIVOT_LOOKBACK     = 2        # Bulkowski standard
  SHOULDER_SYM_PCT   = 0.05     # 5% of head-to-avg-shoulder distance
  HEAD_MIN_EXT_TICKS = 2        # head must be >= 2T beyond both shoulders
  TICK_SIZE          = 0.25     # MES (matches adaptive_stop.py)

These 5 constants are SHADOW-calibratable. Adjust based on hit-rate analysis after
>=20 H&S fires per direction. Re-validate via the 16-test golden suite — any change
must keep all 16 green or update fixtures with rationale. Do NOT hardcode at call sites.
"""
from __future__ import annotations
import logging
import time
from typing import List, Dict, Tuple, Optional, Literal

logger = logging.getLogger(__name__)

# ── Module constants · SHADOW-calibratable ──
MIN_BARS_REQUIRED = 12
SEARCH_WINDOW = 30
PIVOT_LOOKBACK = 2
SHOULDER_SYM_PCT = 0.05
HEAD_MIN_EXT_TICKS = 2
TICK_SIZE = 0.25

# S2 ATR-relative head extension (E2E 2/2 · shadow only)
# Head extension proportional to pattern height rather than fixed ticks
from backend.v9.shared.atr import S2_ATR_RELATIVE  # noqa: E402
_HEAD_EXT_PATTERN_RATIO = 0.15  # head extends ≥ 15% of shoulder-to-head height


def get_head_min_ext_ticks(pattern_height: float = 0.0, atr_5m=None) -> int:
    """Head minimum extension in ticks — proportional when flag ON."""
    if S2_ATR_RELATIVE and pattern_height > 0:
        ext_pts = _HEAD_EXT_PATTERN_RATIO * pattern_height
        return max(1, round(ext_pts / TICK_SIZE))
    return HEAD_MIN_EXT_TICKS

Direction = Literal["LONG", "SHORT"]

# Rate limiter for warning logs (1/min per category)
_last_warn_ts: Dict[str, float] = {}


def _rate_limited_warn(category: str, msg: str, *args) -> None:
    now = time.monotonic()
    last = _last_warn_ts.get(category, 0.0)
    if now - last >= 60.0:
        logger.warning(msg, *args)
        _last_warn_ts[category] = now


# ── Pivot helpers ──


def _swing_lows(bars: List[Dict], lookback: int = PIVOT_LOOKBACK) -> List[Tuple[int, float]]:
    """Find swing low pivots: bar[i].l < all neighbors within lookback."""
    pivots = []
    for i in range(lookback, len(bars) - lookback):
        low_i = bars[i]["l"]
        is_pivot = True
        for j in range(1, lookback + 1):
            if bars[i - j]["l"] <= low_i or bars[i + j]["l"] <= low_i:
                is_pivot = False
                break
        if is_pivot:
            pivots.append((i, low_i))
    return pivots


def _swing_highs(bars: List[Dict], lookback: int = PIVOT_LOOKBACK) -> List[Tuple[int, float]]:
    """Find swing high pivots: bar[i].h > all neighbors within lookback."""
    pivots = []
    for i in range(lookback, len(bars) - lookback):
        high_i = bars[i]["h"]
        is_pivot = True
        for j in range(1, lookback + 1):
            if bars[i - j]["h"] >= high_i or bars[i + j]["h"] >= high_i:
                is_pivot = False
                break
        if is_pivot:
            pivots.append((i, high_i))
    return pivots


def _shoulders_symmetric(left: float, right: float, head: float, direction: str) -> bool:
    """Check shoulder symmetry within SHOULDER_SYM_PCT of head-to-avg-shoulder distance."""
    avg_shoulder = (left + right) / 2.0
    if direction == "LONG":
        head_to_avg = avg_shoulder - head  # positive (head is lowest)
    else:
        head_to_avg = head - avg_shoulder  # positive (head is highest)
    if head_to_avg <= 0:
        return False
    asymmetry = abs(left - right) / head_to_avg
    return asymmetry <= SHOULDER_SYM_PCT


def _head_extends_beyond(head: float, left: float, right: float, direction: str) -> int:
    """Return head extension beyond avg shoulder in ticks. Negative = not extended."""
    avg_shoulder = (left + right) / 2.0
    if direction == "LONG":
        extension_pts = avg_shoulder - head  # head lower than shoulders
    else:
        extension_pts = head - avg_shoulder  # head higher than shoulders
    return round(extension_pts / TICK_SIZE)


def _confidence(left: float, right: float, head: float, direction: str) -> float:
    """Compute confidence per FIELD 4 formula."""
    avg_shoulder = (left + right) / 2.0
    if direction == "LONG":
        head_to_avg = avg_shoulder - head
    else:
        head_to_avg = head - avg_shoulder
    if head_to_avg <= 0:
        return 0.0

    # Shoulder symmetry score
    asymmetry = abs(left - right) / head_to_avg
    sym_score = max(0.0, 1.0 - asymmetry / SHOULDER_SYM_PCT)

    # Head extension score
    ext_ticks = _head_extends_beyond(head, left, right, direction)
    ext_score = min(1.0, max(0.0, (ext_ticks / HEAD_MIN_EXT_TICKS - 1) / 4))

    conf = 0.60 + 0.20 * sym_score + 0.20 * ext_score
    return max(0.0, min(1.0, conf))


# ── Public detectors ──


def detect_inverse_hns(bars: List[Dict]) -> Tuple[Optional[Direction], float, Dict]:
    """Detect Inverse Head & Shoulders (bullish reversal).

    Pattern shape: low(LS) > low(H) < low(RS), shoulders within SHOULDER_SYM_PCT.
    Neckline: max of intermediate highs between LS<->H and H<->RS.
    Fire trigger: last bar close > neckline + 1T.
    """
    if len(bars) < MIN_BARS_REQUIRED:
        return (None, 0.0, {})

    window = bars[-min(len(bars), SEARCH_WINDOW):]
    lows = _swing_lows(window)
    highs = _swing_highs(window)

    if len(lows) < 3:
        return (None, 0.0, {})

    # Try triplets of swing lows: LS, Head, RS
    for i in range(len(lows) - 2):
        ls_idx, ls_price = lows[i]
        h_idx, h_price = lows[i + 1]
        rs_idx, rs_price = lows[i + 2]

        # Head must be lowest
        if h_price >= ls_price or h_price >= rs_price:
            continue

        # Shoulder symmetry
        if not _shoulders_symmetric(ls_price, rs_price, h_price, "LONG"):
            continue

        # Head extension check
        ext_ticks = _head_extends_beyond(h_price, ls_price, rs_price, "LONG")
        if ext_ticks < HEAD_MIN_EXT_TICKS:
            continue

        # Neckline: max of intermediate highs between LS and RS
        nl_highs = [h for idx, h in highs if ls_idx < idx < rs_idx]
        if not nl_highs:
            # Fallback: max high of bars between LS and RS
            nl_highs = [window[j]["h"] for j in range(ls_idx + 1, rs_idx) if j < len(window)]
        if not nl_highs:
            continue
        neckline = max(nl_highs)

        # Breakout: last bar close > neckline + 1T
        last_close = window[-1]["c"]
        if last_close <= neckline + TICK_SIZE:
            continue

        bar_count = rs_idx - ls_idx + 1
        pattern_measure = neckline - h_price  # positive
        conf = _confidence(ls_price, rs_price, h_price, "LONG")

        return ("LONG", conf, {
            "kind": "INVERSE_HNS",
            "pattern_name": "INVERSE_HNS_LONG",
            "structural_anchor": rs_price - TICK_SIZE,
            "pattern_measure": pattern_measure,
            "neckline_price": neckline,
            "head_price": h_price,
            "left_shoulder_price": ls_price,
            "right_shoulder_price": rs_price,
            "bar_count": bar_count,
            "stage": 3,
        })

    return (None, 0.0, {})


def detect_hns_top(bars: List[Dict]) -> Tuple[Optional[Direction], float, Dict]:
    """Detect Head & Shoulders Top (bearish reversal).

    Pattern shape: high(LS) < high(H) > high(RS), shoulders within SHOULDER_SYM_PCT.
    Neckline: min of intermediate lows.
    Fire trigger: last bar close < neckline - 1T.
    """
    if len(bars) < MIN_BARS_REQUIRED:
        return (None, 0.0, {})

    window = bars[-min(len(bars), SEARCH_WINDOW):]
    highs = _swing_highs(window)
    lows = _swing_lows(window)

    if len(highs) < 3:
        return (None, 0.0, {})

    # Try triplets of swing highs: LS, Head, RS
    for i in range(len(highs) - 2):
        ls_idx, ls_price = highs[i]
        h_idx, h_price = highs[i + 1]
        rs_idx, rs_price = highs[i + 2]

        # Head must be highest
        if h_price <= ls_price or h_price <= rs_price:
            continue

        # Shoulder symmetry
        if not _shoulders_symmetric(ls_price, rs_price, h_price, "SHORT"):
            continue

        # Head extension check
        ext_ticks = _head_extends_beyond(h_price, ls_price, rs_price, "SHORT")
        if ext_ticks < HEAD_MIN_EXT_TICKS:
            continue

        # Neckline: min of intermediate lows between LS and RS
        nl_lows = [lo for idx, lo in lows if ls_idx < idx < rs_idx]
        if not nl_lows:
            nl_lows = [window[j]["l"] for j in range(ls_idx + 1, rs_idx) if j < len(window)]
        if not nl_lows:
            continue
        neckline = min(nl_lows)

        # Breakout: last bar close < neckline - 1T
        last_close = window[-1]["c"]
        if last_close >= neckline - TICK_SIZE:
            continue

        bar_count = rs_idx - ls_idx + 1
        pattern_measure = h_price - neckline  # positive
        conf = _confidence(ls_price, rs_price, h_price, "SHORT")

        return ("SHORT", conf, {
            "kind": "HNS_TOP",
            "pattern_name": "HNS_TOP_SHORT",
            "structural_anchor": rs_price + TICK_SIZE,
            "pattern_measure": pattern_measure,
            "neckline_price": neckline,
            "head_price": h_price,
            "left_shoulder_price": ls_price,
            "right_shoulder_price": rs_price,
            "bar_count": bar_count,
            "stage": 3,
        })

    return (None, 0.0, {})
