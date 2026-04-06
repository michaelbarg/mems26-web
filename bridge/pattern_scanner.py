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
    "LSR":      "שבירה וחזרה",
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

# ─── Support / Resistance Retest ──────────────────────

def detect_retest(candles: list) -> Optional[PatternResult]:
    """
    מזהה רמת support/resistance שנבדקת 2+ פעמים.
    חלון: 20 נרות אחרונים.
    """
    if len(candles) < 6:
        return None

    window = candles[-20:]
    TOLERANCE = 0.5   # ±0.5 נקודות = אותה רמה

    # מצא כל השפלים והשיאים
    lows  = [(i, _lo(c), _ts(c)) for i, c in enumerate(window)]
    highs = [(i, _hi(c), _ts(c)) for i, c in enumerate(window)]

    # קבץ שפלים קרובים → רמות support
    support_levels = []
    used = set()
    for i, lo, ts in lows:
        if i in used:
            continue
        group = [(i, lo, ts)]
        for j, lo2, ts2 in lows:
            if j != i and j not in used and abs(lo - lo2) <= TOLERANCE:
                group.append((j, lo2, ts2))
        if len(group) >= 2:
            avg_price = sum(g[1] for g in group) / len(group)
            support_levels.append({
                "price": avg_price,
                "touches": len(group),
                "first_ts": group[0][2],
                "last_ts":  group[-1][2],
                "direction": "LONG",
            })
            used.update(g[0] for g in group)

    # קבץ שיאים קרובים → רמות resistance
    resist_levels = []
    used2 = set()
    for i, hi, ts in highs:
        if i in used2:
            continue
        group = [(i, hi, ts)]
        for j, hi2, ts2 in highs:
            if j != i and j not in used2 and abs(hi - hi2) <= TOLERANCE:
                group.append((j, hi2, ts2))
        if len(group) >= 2:
            avg_price = sum(g[1] for g in group) / len(group)
            resist_levels.append({
                "price": avg_price,
                "touches": len(group),
                "first_ts": group[0][2],
                "last_ts":  group[-1][2],
                "direction": "SHORT",
            })
            used2.update(g[0] for g in group)

    # בחר הרמה עם הכי הרבה נגיעות וקרובה לנר האחרון
    all_levels = support_levels + resist_levels
    if not all_levels:
        return None

    last_price = _cl(candles[-1])
    # מיין: הכי הרבה נגיעות + הכי קרוב למחיר
    all_levels.sort(
        key=lambda l: (l["touches"] * 2 - abs(l["price"] - last_price) / 10),
        reverse=True
    )
    best = all_levels[0]

    # וודא שהנר האחרון קרוב לרמה (בדיקה פעילה)
    if abs(last_price - best["price"]) > 3.0:
        return None

    # חשב entry/stop/targets
    risk     = 4.0  # ברירת מחדל
    is_long  = best["direction"] == "LONG"
    entry    = best["price"] + (0.25 if is_long else -0.25)
    stop     = best["price"] - (risk if is_long else -risk)
    t1       = entry + (risk if is_long else -risk)
    t2       = entry + (risk * 2 if is_long else -risk * 2)

    conf = 50
    if best["touches"] >= 3: conf += 20
    if best["touches"] >= 4: conf += 10
    vol_last  = candles[-1].get("vol", 0)
    vol_prev  = sum(c.get("vol", 0) for c in candles[-5:-1]) / 4
    if vol_last < vol_prev * 0.8: conf += 10  # נפח יורד = חלש יותר
    if abs(last_price - best["price"]) < 1.0: conf += 10

    return PatternResult(
        pattern   = "RETEST",
        direction = best["direction"],
        start_ts  = best["first_ts"],
        end_ts    = best["last_ts"],
        entry     = entry,
        stop      = stop,
        t1        = t1,
        t2        = t2,
        neckline  = best["price"],
        confidence= min(conf, 90),
        label     = f"בדיקת {'Support' if is_long else 'Resistance'} ({best['touches']} נגיעות)",
    )


# ─── Base Candles (צבירה לפני פריצה) ─────────────────

def detect_base(candles: list) -> Optional[PatternResult]:
    """
    מזהה 3+ נרות רצופים עם טווח צר (≤3 נקודות) = base/צבירה.
    """
    if len(candles) < 5:
        return None

    window = candles[-15:]
    BASE_MAX_RANGE = 3.0
    MIN_BASE_BARS  = 3

    # חפש רצף נרות צרים
    best_base = None
    best_len  = 0

    i = 0
    while i < len(window):
        base_candles = []
        j = i
        while j < len(window):
            c = window[j]
            bar_range = _hi(c) - _lo(c)
            if bar_range <= BASE_MAX_RANGE:
                base_candles.append(c)
                j += 1
            else:
                break

        if len(base_candles) >= MIN_BASE_BARS and len(base_candles) > best_len:
            best_len  = len(base_candles)
            best_base = base_candles
        i = j + 1 if j == i else j

    if not best_base:
        return None

    # רמת הbase
    base_high = max(_hi(c) for c in best_base)
    base_low  = min(_lo(c) for c in best_base)
    base_mid  = (base_high + base_low) / 2

    # כיוון — לפי המחיר לפני הbase
    pre_candles = candles[:-best_len-1]
    if not pre_candles:
        return None
    pre_price = _cl(pre_candles[-1])
    is_long   = pre_price < base_mid  # מגיע מלמטה → LONG

    # נפח יורד בbase = צבירה טובה
    vols = [c.get("vol", 0) for c in best_base]
    vol_declining = vols[-1] < vols[0] * 0.8 if vols[0] > 0 else False

    risk  = base_high - base_low + 1.0
    entry = (base_high + 0.25) if is_long else (base_low - 0.25)
    stop  = (base_low  - 0.25) if is_long else (base_high + 0.25)
    t1    = entry + (risk if is_long else -risk)
    t2    = entry + (risk * 2 if is_long else -risk * 2)

    conf = 55
    if best_len >= 4:     conf += 15
    if best_len >= 5:     conf += 10
    if vol_declining:     conf += 15
    if risk < 2.0:        conf += 10  # base צר = טוב

    return PatternResult(
        pattern   = "BASE",
        direction = "LONG" if is_long else "SHORT",
        start_ts  = best_base[0]["ts"],
        end_ts    = best_base[-1]["ts"],
        entry     = entry,
        stop      = stop,
        t1        = t1,
        t2        = t2,
        neckline  = base_high if is_long else base_low,
        confidence= min(conf, 88),
        label     = f"Base {best_len} נרות {'▲' if is_long else '▼'}",
    )


# ─── Sweep + Return (LSR) ─────────────────────────────

def detect_sweep_return(candles: list) -> Optional[PatternResult]:
    """
    שבירת רמה (sweep) וחזרה מהירה — Liquidity Sweep Return.
    מחפש נר שפרץ שפל/שיא של 10+ נרות ואז סגר בחזרה מעבר לרמה.
    """
    if len(candles) < 12:
        return None

    window = candles[-30:] if len(candles) >= 30 else candles
    LOOKBACK = 10  # כמה נרות אחורה לחפש רמה

    best = None
    best_conf = 0

    for i in range(LOOKBACK, len(window)):
        c = window[i]
        hi = _hi(c)
        lo = _lo(c)
        cl = _cl(c)
        op = c.get("o", c.get("open", 0))
        prior = window[max(0, i - LOOKBACK):i]

        if not prior:
            continue

        prior_high = max(_hi(p) for p in prior)
        prior_low = min(_lo(p) for p in prior)

        # --- Sweep HIGH then close back below (SHORT) ---
        sweep_above = hi > prior_high + 0.5
        closed_back_below = cl < prior_high
        if sweep_above and closed_back_below:
            wick_above = hi - max(cl, op)
            body = abs(cl - op)
            long_wick = wick_above > body * 0.8 if body > 0 else wick_above > 1.0

            neckline = prior_high
            risk = hi - neckline + 1.0
            entry = neckline - 0.25
            stop = hi + 0.25
            t1 = entry - risk
            t2 = entry - risk * 2

            conf = 60
            if long_wick: conf += 10
            delta = c.get("delta", 0)
            if delta < -50: conf += 10  # דלתא שלילית = מוכרים חזקים
            vol = c.get("vol", c.get("volume", 0)) or 0
            avg_v = sum((p.get("vol", p.get("volume", 0)) or 0) for p in prior) / len(prior)
            if vol > avg_v * 1.3: conf += 10  # נפח גבוה בשבירה

            if conf > best_conf:
                best_conf = conf
                best = PatternResult(
                    pattern="LSR", direction="SHORT",
                    start_ts=_ts(prior[0]), end_ts=_ts(c),
                    entry=entry, stop=stop, t1=t1, t2=t2,
                    neckline=neckline, confidence=min(conf, 92),
                    label=f"Sweep High {hi:.1f} → חזרה",
                )

        # --- Sweep LOW then close back above (LONG) ---
        sweep_below = lo < prior_low - 0.5
        closed_back_above = cl > prior_low
        if sweep_below and closed_back_above:
            wick_below = min(cl, op) - lo
            body = abs(cl - op)
            long_wick = wick_below > body * 0.8 if body > 0 else wick_below > 1.0

            neckline = prior_low
            risk = neckline - lo + 1.0
            entry = neckline + 0.25
            stop = lo - 0.25
            t1 = entry + risk
            t2 = entry + risk * 2

            conf = 60
            if long_wick: conf += 10
            delta = c.get("delta", 0)
            if delta > 50: conf += 10  # דלתא חיובית = קונים חזקים
            vol = c.get("vol", c.get("volume", 0)) or 0
            avg_v = sum((p.get("vol", p.get("volume", 0)) or 0) for p in prior) / len(prior)
            if vol > avg_v * 1.3: conf += 10

            if conf > best_conf:
                best_conf = conf
                best = PatternResult(
                    pattern="LSR", direction="LONG",
                    start_ts=_ts(prior[0]), end_ts=_ts(c),
                    entry=entry, stop=stop, t1=t1, t2=t2,
                    neckline=neckline, confidence=min(conf, 92),
                    label=f"Sweep Low {lo:.1f} → חזרה",
                )

    return best


# ─── Main scanner ─────────────────────────────────────

def scan_patterns(candles: list) -> list[dict]:
    """
    Run all detectors on multiple windows of the candle data.
    Returns top 3 unique patterns sorted by confidence.
    """
    results = []
    windows = [20, 60, 120, 240, 480, 960]
    detectors = [
        detect_hs,
        detect_ihs,
        detect_double_top,
        detect_double_bottom,
        detect_cup,
        detect_triangle,
        detect_retest,
        detect_sweep_return,
        detect_base,
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
