"""
Pattern Scanner — identifies classic chart patterns on 960 × 3min candles.
Called from json_bridge.py every 60 seconds.

Candle format: {ts, o, h, l, c, buy, sell, vol, delta, ...}
"""

import time as time_module
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class PatternResult:
    pattern:    str          # "HS" | "IHS" | "DT" | "DB" | "CUP" | "TRI_ASC" | "TRI_DESC"
    direction:  str          # "LONG" | "SHORT"
    start_ts:   int
    end_ts:     int
    entry:      float
    stop:       float
    t1:         float
    t2:         float
    neckline:   float
    confidence: int          # 0-100
    label:      str

LABELS = {
    "HS":       "ראש וכתפיים",
    "IHS":      "ראש וכתפיים הפוך",
    "DT":       "תקרה כפולה",
    "DB":       "רצפה כפולה",
    "CUP":      "כוס וידית",
    "TRI_ASC":  "משולש עולה",
    "TRI_DESC": "משולש יורד",
}

# ─── Helpers ──────────────────────────────────────────

def _hi(c: dict) -> float:
    return c.get("h", c.get("high", 0))

def _lo(c: dict) -> float:
    return c.get("l", c.get("low", 0))

def _cl(c: dict) -> float:
    return c.get("c", c.get("close", 0))

def _ts(c: dict) -> int:
    return int(c.get("ts", 0))

def find_pivots(candles: list, window: int = 5):
    highs, lows = [], []
    for i in range(window, len(candles) - window):
        hi = _hi(candles[i])
        lo = _lo(candles[i])
        if all(hi >= _hi(candles[j]) for j in range(i - window, i + window + 1) if j != i):
            highs.append((i, hi, _ts(candles[i])))
        if all(lo <= _lo(candles[j]) for j in range(i - window, i + window + 1) if j != i):
            lows.append((i, lo, _ts(candles[i])))
    return highs, lows

def pct_diff(a: float, b: float) -> float:
    avg = (a + b) / 2
    if avg == 0:
        return 0
    return abs(a - b) / avg * 100

def avg_vol(candles: list, start: int, end: int) -> float:
    chunk = candles[max(0, start):end]
    return sum(c.get("vol", c.get("volume", 0)) or 0 for c in chunk) / max(len(chunk), 1)

# ─── Head & Shoulders ─────────────────────────────────

def detect_hs(candles: list) -> Optional[PatternResult]:
    highs, lows = find_pivots(candles, window=4)
    if len(highs) < 3:
        return None

    for i in range(len(highs) - 2):
        li, lh, lts = highs[i]
        hi, hh, hts = highs[i + 1]
        ri, rh, rts = highs[i + 2]

        if not (hh > lh and hh > rh):
            continue
        if pct_diff(lh, rh) > 8:
            continue

        mid_lows = [_lo(c) for c in candles[li:hi] + candles[hi:ri]]
        if not mid_lows:
            continue
        neckline = min(mid_lows)
        height = hh - neckline

        vol_head = avg_vol(candles, li, hi)
        vol_rsh = avg_vol(candles, hi, ri)
        if vol_rsh > vol_head * 0.95:
            continue

        entry = neckline - 0.25
        stop = rh + 0.25
        t1 = neckline - height * 0.5
        t2 = neckline - height

        conf = 60
        if pct_diff(lh, rh) < 4: conf += 10
        if vol_rsh < vol_head * 0.7: conf += 10
        if len([c for c in candles[ri:ri + 5] if _cl(c) < neckline]) >= 2: conf += 20

        return PatternResult(
            pattern="HS", direction="SHORT",
            start_ts=lts, end_ts=rts,
            entry=entry, stop=stop, t1=t1, t2=t2,
            neckline=neckline, confidence=min(conf, 95),
            label=LABELS["HS"]
        )
    return None

# ─── Inverse H&S ──────────────────────────────────────

def detect_ihs(candles: list) -> Optional[PatternResult]:
    highs, lows = find_pivots(candles, window=4)
    if len(lows) < 3:
        return None

    for i in range(len(lows) - 2):
        li, ll, lts = lows[i]
        hi, hl, hts = lows[i + 1]
        ri, rl, rts = lows[i + 2]

        if not (hl < ll and hl < rl):
            continue
        if pct_diff(ll, rl) > 8:
            continue

        mid_highs = [_hi(c) for c in candles[li:hi] + candles[hi:ri]]
        if not mid_highs:
            continue
        neckline = max(mid_highs)
        height = neckline - hl

        vol_head = avg_vol(candles, li, hi)
        vol_rsh = avg_vol(candles, hi, ri)

        entry = neckline + 0.25
        stop = rl - 0.25
        t1 = neckline + height * 0.5
        t2 = neckline + height

        conf = 60
        if pct_diff(ll, rl) < 4: conf += 10
        if vol_rsh < vol_head * 0.7: conf += 10
        if len([c for c in candles[ri:ri + 5] if _cl(c) > neckline]) >= 2: conf += 20

        return PatternResult(
            pattern="IHS", direction="LONG",
            start_ts=lts, end_ts=rts,
            entry=entry, stop=stop, t1=t1, t2=t2,
            neckline=neckline, confidence=min(conf, 95),
            label=LABELS["IHS"]
        )
    return None

# ─── Double Top ───────────────────────────────────────

def detect_double_top(candles: list) -> Optional[PatternResult]:
    highs, _ = find_pivots(candles, window=5)
    if len(highs) < 2:
        return None

    for i in range(len(highs) - 1):
        p1i, p1h, p1ts = highs[i]
        p2i, p2h, p2ts = highs[i + 1]

        if pct_diff(p1h, p2h) > 0.8:
            continue
        mid = candles[p1i:p2i]
        if not mid:
            continue
        valley = min(_lo(c) for c in mid)
        if pct_diff(max(p1h, p2h), valley) < 1.5:
            continue

        neckline = valley
        height = max(p1h, p2h) - neckline
        entry = neckline - 0.25
        stop = max(p1h, p2h) + 0.25
        t1 = neckline - height * 0.5
        t2 = neckline - height

        vol1 = avg_vol(candles, p1i - 3, p1i + 3)
        vol2 = avg_vol(candles, p2i - 3, p2i + 3)
        conf = 65
        if vol2 < vol1 * 0.85: conf += 15
        if pct_diff(p1h, p2h) < 0.4: conf += 10

        return PatternResult(
            pattern="DT", direction="SHORT",
            start_ts=p1ts, end_ts=p2ts,
            entry=entry, stop=stop, t1=t1, t2=t2,
            neckline=neckline, confidence=min(conf, 95),
            label=LABELS["DT"]
        )
    return None

# ─── Double Bottom ────────────────────────────────────

def detect_double_bottom(candles: list) -> Optional[PatternResult]:
    _, lows = find_pivots(candles, window=5)
    if len(lows) < 2:
        return None

    for i in range(len(lows) - 1):
        p1i, p1l, p1ts = lows[i]
        p2i, p2l, p2ts = lows[i + 1]

        if pct_diff(p1l, p2l) > 0.8:
            continue
        mid = candles[p1i:p2i]
        if not mid:
            continue
        peak = max(_hi(c) for c in mid)
        if pct_diff(min(p1l, p2l), peak) < 1.5:
            continue

        neckline = peak
        height = neckline - min(p1l, p2l)
        entry = neckline + 0.25
        stop = min(p1l, p2l) - 0.25
        t1 = neckline + height * 0.5
        t2 = neckline + height

        vol1 = avg_vol(candles, p1i - 3, p1i + 3)
        vol2 = avg_vol(candles, p2i - 3, p2i + 3)
        conf = 65
        if vol2 < vol1 * 0.85: conf += 15
        if pct_diff(p1l, p2l) < 0.4: conf += 10

        return PatternResult(
            pattern="DB", direction="LONG",
            start_ts=p1ts, end_ts=p2ts,
            entry=entry, stop=stop, t1=t1, t2=t2,
            neckline=neckline, confidence=min(conf, 95),
            label=LABELS["DB"]
        )
    return None

# ─── Cup & Handle ─────────────────────────────────────

def detect_cup(candles: list) -> Optional[PatternResult]:
    if len(candles) < 40:
        return None

    n = len(candles)
    third = n // 3
    left = candles[:third]
    bottom = candles[third:2 * third]
    right = candles[2 * third:]

    left_high = max(_hi(c) for c in left)
    right_high = max(_hi(c) for c in right)
    bottom_low = min(_lo(c) for c in bottom)

    cup_depth = pct_diff(left_high, bottom_low)
    if not (1.5 < cup_depth < 12):
        return None
    if pct_diff(left_high, right_high) > 5:
        return None

    handle = right[-len(right) // 3:]
    if not handle:
        return None
    handle_high = max(_hi(c) for c in handle)
    handle_low = min(_lo(c) for c in handle)
    handle_depth = pct_diff(handle_high, handle_low)
    if handle_depth > cup_depth * 0.6:
        return None

    neckline = max(left_high, right_high)
    height = neckline - bottom_low
    entry = neckline + 0.25
    stop = handle_low - 0.25
    t1 = entry + height * 0.5
    t2 = entry + height

    conf = 70
    if handle_depth < cup_depth * 0.35: conf += 15

    return PatternResult(
        pattern="CUP", direction="LONG",
        start_ts=_ts(candles[0]), end_ts=_ts(candles[-1]),
        entry=entry, stop=stop, t1=t1, t2=t2,
        neckline=neckline, confidence=min(conf, 92),
        label=LABELS["CUP"]
    )

# ─── Triangle ─────────────────────────────────────────

def detect_triangle(candles: list) -> Optional[PatternResult]:
    if len(candles) < 20:
        return None
    highs, lows = find_pivots(candles, window=3)
    if len(highs) < 3 or len(lows) < 3:
        return None

    recent_highs = highs[-4:]
    recent_lows = lows[-4:]
    high_vals = [h[1] for h in recent_highs]
    low_vals = [l[1] for l in recent_lows]

    highs_flat = max(high_vals) - min(high_vals) < 1.5 if high_vals else False
    lows_rising = all(low_vals[i] > low_vals[i - 1] for i in range(1, len(low_vals)))
    lows_flat = max(low_vals) - min(low_vals) < 1.5 if low_vals else False
    highs_falling = all(high_vals[i] < high_vals[i - 1] for i in range(1, len(high_vals)))

    if highs_flat and lows_rising:
        resistance = sum(high_vals) / len(high_vals)
        support = low_vals[-1]
        height = resistance - support
        entry = resistance + 0.25
        stop = support - 0.25
        t1 = entry + height * 0.5
        t2 = entry + height
        return PatternResult(
            pattern="TRI_ASC", direction="LONG",
            start_ts=_ts(candles[recent_highs[0][0]]),
            end_ts=_ts(candles[-1]),
            entry=entry, stop=stop, t1=t1, t2=t2,
            neckline=resistance, confidence=72,
            label=LABELS["TRI_ASC"]
        )

    if lows_flat and highs_falling:
        support = sum(low_vals) / len(low_vals)
        resistance = high_vals[-1]
        height = resistance - support
        entry = support - 0.25
        stop = resistance + 0.25
        t1 = entry - height * 0.5
        t2 = entry - height
        return PatternResult(
            pattern="TRI_DESC", direction="SHORT",
            start_ts=_ts(candles[recent_lows[0][0]]),
            end_ts=_ts(candles[-1]),
            entry=entry, stop=stop, t1=t1, t2=t2,
            neckline=support, confidence=72,
            label=LABELS["TRI_DESC"]
        )
    return None

# ─── Main scanner ─────────────────────────────────────

def scan_patterns(candles: list) -> list[dict]:
    """
    Run all detectors on multiple windows of the candle data.
    Returns top 3 unique patterns sorted by confidence.
    """
    results = []
    windows = [120, 240, 480, 960]
    detectors = [
        detect_hs,
        detect_ihs,
        detect_double_top,
        detect_double_bottom,
        detect_cup,
        detect_triangle,
    ]

    for w in windows:
        subset = candles[-w:] if len(candles) >= w else candles
        for detect in detectors:
            try:
                r = detect(subset)
                if r and r.confidence >= 60:
                    results.append(asdict(r))
            except Exception:
                pass

    # Sort by confidence, deduplicate by pattern type
    results.sort(key=lambda x: x["confidence"], reverse=True)
    seen = set()
    unique = []
    for r in results:
        if r["pattern"] not in seen:
            seen.add(r["pattern"])
            unique.append(r)

    # Filter: recency — pattern must have ended within 90 minutes
    now_ts = int(time_module.time())
    MAX_AGE_SEC = 90 * 60
    current_price = _cl(candles[-1]) if candles else 0

    time_filtered = [
        r for r in unique
        if now_ts - r["end_ts"] <= MAX_AGE_SEC
    ]

    # Filter: actionable — price must be near neckline, not already ran past or invalidated
    def is_actionable(r: dict) -> bool:
        entry = r["entry"]
        stop = r["stop"]
        neckline = r["neckline"]
        direction = r["direction"]
        price = current_price

        if direction == "LONG":
            already_ran = price > entry + 5
            invalidated = price < stop
            near_entry = abs(price - neckline) <= 8
        else:
            already_ran = price < entry - 5
            invalidated = price > stop
            near_entry = abs(price - neckline) <= 8

        return near_entry and not already_ran and not invalidated

    actionable = [r for r in time_filtered if is_actionable(r)]
    return actionable[:3]
