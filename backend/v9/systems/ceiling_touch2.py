"""T-328 §4: CEILING_TOUCH2_REJECT / FLOOR_TOUCH2_REJECT.

Entry at the SECOND TOUCH rejection, not at the neckline break.
The trader enters when the second peak is rejected (closes below
the first peak's close) — stop tight above both peaks, target to POC.

Pure function. Same input contract as ceiling_floor_state.detect_ceiling_floor.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Sequence, Set

logger = logging.getLogger(__name__)

TICK = 0.25  # MES

# Defaults — same shape as ceiling_floor_state.DEFAULTS
DEFAULTS = {
    "tol_atr": 0.25,
    "edge_tol_atr": 0.15,
    "max_bars_between": 12,
    "min_bars_between": 1,
}


def _f(bar, *keys):
    for k in keys:
        v = bar.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


def _ohlc(bars):
    highs, lows, closes = [], [], []
    for b in bars:
        h = _f(b, "h", "high")
        l = _f(b, "l", "low")
        c = _f(b, "c", "close")
        if h is None or l is None or c is None:
            return None
        highs.append(h)
        lows.append(l)
        closes.append(c)
    return highs, lows, closes


def _argmax(values, lo, hi):
    best = lo
    for i in range(lo + 1, hi + 1):
        if values[i] > values[best]:
            best = i
    return best


def _argmin(values, lo, hi):
    best = lo
    for i in range(lo + 1, hi + 1):
        if values[i] < values[best]:
            best = i
    return best


_EDGE_KEYS = {
    "VAH": ("vah", "val"),
    "SESSION_HIGH": ("session_high", "session_low"),
    "IB_HIGH": ("ib_high", "ib_low"),
}


def _scan_ceiling_touch2(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    edge: float,
    tol: float,
    edge_tol: float,
    cfg: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Detect CEILING_TOUCH2_REJECT on the LAST bar.

    The last bar is the TOUCH-2 candidate. Fires when:
    1. TOUCH-1 near edge (within edge_tol)
    2. TOUCH-2 in same area (|P2-P1| <= tol)
    3. TOUCH-2 bar closes BELOW TOUCH-1 bar close (rejection confirmed)
    """
    last = len(highs) - 1
    if last < 2:
        return None

    min_gap = cfg.get("min_bars_between", 1)
    max_gap = cfg.get("max_bars_between", 12)

    # P1 window: bar_last is the touch-2 candidate, so P1 is before it
    p1_hi = last - min_gap
    if p1_hi < 0:
        return None
    p1_lo = max(0, last - max_gap)
    if p1_lo > p1_hi:
        return None

    # TOUCH-1: highest high in the window
    i1 = _argmax(highs, p1_lo, p1_hi)
    p1 = highs[i1]
    if p1 < edge - edge_tol:
        return None  # not near edge

    # TOUCH-2 = the LAST bar
    i2 = last
    p2 = highs[i2]
    if abs(p2 - p1) > tol:
        return None  # not same area

    # TOUCH-2 near edge too
    if p2 < edge - edge_tol:
        return None

    # REJECTION: touch-2 bar closes BELOW touch-1 bar close
    c1 = closes[i1]
    c2 = closes[i2]
    if c2 >= c1:
        return None  # no rejection — touch-2 closed at or above touch-1

    # Rejection between touches: at least one close below edge
    has_rejection = any(closes[k] < edge for k in range(i1, i2 + 1))
    if not has_rejection:
        return None

    return {
        "p1": p1,
        "p2": p2,
        "p1_index": i1,
        "p2_index": i2,
        "p1_close": c1,
        "p2_close": c2,
        "confirm_close": c2,  # entry = close of touch-2 bar
        "bars_between": i2 - i1,
    }


def _scan_floor_touch2(highs, lows, closes, edge, tol, edge_tol, cfg):
    """FLOOR = CEILING on sign-flipped chart."""
    res = _scan_ceiling_touch2(
        [-x for x in lows],
        [-x for x in highs],
        [-x for x in closes],
        -edge, tol, edge_tol, cfg,
    )
    if res is None:
        return None
    for k in ("p1", "p2", "p1_close", "p2_close", "confirm_close"):
        res[k] = -res[k]
    return res


CEILING_TOUCH2 = "CEILING_TOUCH2_REJECT"
FLOOR_TOUCH2 = "FLOOR_TOUCH2_REJECT"


def detect_touch2(
    bars: Sequence[Dict[str, Any]],
    levels: Optional[Dict[str, Any]],
    atr: Optional[float],
    ib_width: Optional[float] = None,
    cfg: Optional[Dict[str, Any]] = None,
    *,
    already_fired: Optional[Set[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Detect CEILING_TOUCH2_REJECT / FLOOR_TOUCH2_REJECT on the last bar.

    Same interface as ceiling_floor_state.detect_ceiling_floor.
    """
    if atr is None or not bars or len(bars) < 3:
        return None
    try:
        atr_f = float(atr)
    except (TypeError, ValueError):
        return None
    if not (atr_f > 0):
        return None

    parsed = _ohlc(bars)
    if parsed is None:
        return None
    highs, lows, closes = parsed

    conf = dict(DEFAULTS)
    if cfg:
        conf.update(cfg)

    tol = conf["tol_atr"] * atr_f
    # Edge tolerance: max(edge_tol_atr × ATR, 0.15 × IB_width) — T-327a
    _edge_tol_atr = conf.get("edge_tol_atr", 0.15) * atr_f
    _edge_tol_ib = 0.15 * float(ib_width) if ib_width and float(ib_width) > 0 else 0
    edge_tol = max(_edge_tol_atr, _edge_tol_ib)

    lv = levels if isinstance(levels, dict) else {}
    fired = already_fired or set()

    last_bar = bars[-1]
    signal_bar_ts = last_bar.get("ts", last_bar.get("ets"))

    edge_sources = conf.get("edge_sources", ["VAH", "SESSION_HIGH", "IB_HIGH"])

    for source in edge_sources:
        keys = _EDGE_KEYS.get(str(source).upper())
        if not keys:
            continue
        hi_key, lo_key = keys
        for state, level_key, scan in (
            (CEILING_TOUCH2, hi_key, _scan_ceiling_touch2),
            (FLOOR_TOUCH2, lo_key, _scan_floor_touch2),
        ):
            raw = lv.get(level_key)
            if raw is None:
                continue
            try:
                edge_val = float(raw)
            except (TypeError, ValueError):
                continue
            res = scan(highs, lows, closes, edge_val, tol, edge_tol, conf)
            if res is None:
                continue
            key = f"T2_{state}_{res['p1_index']}_{res['p2_index']}"
            if key in fired:
                continue
            res["state"] = state
            res["edge"] = edge_val
            res["edge_source"] = source
            res["signal_bar_ts"] = signal_bar_ts
            res["key"] = key
            return res

    return None
