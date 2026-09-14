"""T-328 §4: CEILING_TOUCH2_REJECT / FLOOR_TOUCH2_REJECT.

Entry at the SECOND TOUCH rejection, not at the neckline break.
The trader enters when the second peak is rejected (closes below
the first peak's close) — stop tight above both peaks, target to POC.

Pure function. Same input contract as ceiling_floor_state.detect_ceiling_floor.
"""
from __future__ import annotations

import logging
import os
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

    # TOUCH-2 = the LAST bar; it must sit near the edge.
    i2 = last
    p2 = highs[i2]
    if p2 < edge - edge_tol:
        return None
    c2 = closes[i2]

    # TOUCH-1: the LATEST earlier bar in the window whose high is in the
    # same area as touch-2 (|P1-P2| <= tol), near the edge, whose close
    # touch-2 rejected (c2 < c1), with nothing in between advancing above
    # the pair (max(P1,P2)+tol) and at least one close back below the edge.
    # cowork 14.09 (item-1 follow-up): the previous rule took P1 = argmax of
    # the window, so Michael's 11.09 17:20/17:25 equal-high double top
    # (7678.75 = 7678.75, 3.25 under the 16:55 session high 7682) could never
    # match — P1 always snapped to 7682 and |P2-P1| = 3.25 > tol. A double
    # top is two touches of the SAME area near the edge, not "the max".
    i1 = None
    for cand in range(p1_hi, p1_lo - 1, -1):
        p1c = highs[cand]
        if abs(p2 - p1c) > tol:
            continue  # not same area
        if p1c < edge - edge_tol:
            continue  # not near edge
        if c2 >= closes[cand]:
            continue  # no rejection — touch-2 closed at or above touch-1
        cap = max(p1c, p2) + tol
        if any(highs[k] > cap for k in range(cand + 1, i2)):
            continue  # something between the touches advanced past the pair
        if not any(closes[k] < edge for k in range(cand, i2 + 1)):
            continue  # never closed back below the edge
        i1 = cand
        break
    if i1 is None:
        return None
    p1 = highs[i1]
    c1 = closes[i1]

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
    lv = levels if isinstance(levels, dict) else {}
    # Edge tolerance: max(edge_tol_atr × ATR, 0.15 × IB_width) — T-327a.
    # Item-1 follow-up (cowork 14.09): before the IB locks, ib_width is None
    # and the tolerance collapsed to 0.15×ATR (~1.2 pt), so Michael's 11.09
    # 17:20/17:25 equal-high double top (7678.75, 3.25 pt under the session
    # high 7682) was NOT-FIRED in the harness. The developing session range
    # (session_high − session_low, both bar-derived running RTH extremes) is
    # the pre-lock stand-in for the IB width — geometry, not a guess.
    _range_w = None
    if not (ib_width and float(ib_width) > 0):
        try:
            _sh, _sl = lv.get("session_high"), lv.get("session_low")
            if _sh is not None and _sl is not None and float(_sh) > float(_sl):
                _range_w = float(_sh) - float(_sl)
        except (TypeError, ValueError):
            _range_w = None
    _edge_w = float(ib_width) if (ib_width and float(ib_width) > 0) else _range_w
    _edge_tol_atr = conf.get("edge_tol_atr", 0.15) * atr_f
    _edge_tol_ib = 0.15 * _edge_w if _edge_w and _edge_w > 0 else 0
    edge_tol = max(_edge_tol_atr, _edge_tol_ib)
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
            # Dedup key by the touch bars' TIMESTAMPS, not window indices.
            # cowork 14.09: with a 120-bar sliding window every adjacent-bar
            # pattern has indices 118/119, so the first fire (16:40) silenced
            # every later one — including Michael's 17:20/17:25 double top.
            def _bar_id(b):
                return str(b.get("ets") or b.get("ts") or b.get("ets_utc") or "")
            _b1, _b2 = bars[res["p1_index"]], bars[res["p2_index"]]
            _id1, _id2 = _bar_id(_b1), _bar_id(_b2)
            if _id1 and _id2:
                key = f"T2_{state}_{_id1}_{_id2}"
            else:
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
