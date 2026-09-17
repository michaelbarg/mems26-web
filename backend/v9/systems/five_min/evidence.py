#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evidence.py — F17b / T-412: setup evidence for the EXISTING S2 producers.

Michael 17.09 19:40: *"לבחון על התבניות שלנו — בעיקר ריאקטיב ואיניאטיב — ולדייק,
לא לבנות מחדש"*.  Authority for what counts as evidence:
``docs/spec_authority/SETUP_GRAMMAR_2026-09-17.md`` (location · context ·
sequence · trigger · volume).

Everything here is **pure and causal**:
  * no I/O, no DB, no ``os.environ``, no ``datetime.now`` — the caller supplies
    every number, and only from CLOSED bars up to (and including) the trigger;
  * an input that is missing propagates as ``None`` (CLAUDE.md Rule 1 — honest
    failure beats a synthetic value).  Callers that need a boolean gate get the
    falsiness of ``None`` for free, while the recorded evidence stays honest.

The measurement that motivated it (``scripts/pattern_evidence_study.py``,
164 REACTIVE/INITIATIVE entries, June→, fixed 2-leg model):

    REACTIVE LONG     with trigger_ok  N=11 win 64% +$41.7 | without N=28 win 11% −$70.6
    INITIATIVE SHORT  with trigger_ok  N= 9 win 78% +$52.8 | without N=30 win 10% −$32.0

Consumers: ``five_min_system._detect_reactive`` / ``_detect_initiative`` (live,
flag ``S2_TRIGGER_QUALITY_V1``, default ``shadow``) and
``scripts/pattern_evidence_study.py`` (the historical replay) — **the same code
on both sides**, which is the point of the module.

Shape detectors: ``detect_head_shoulders_short/long`` and
``detect_cup_handle_long`` are byte-identical copies of the ones in
``scripts/oracle_engine.py`` (same signature).  They are COPIED, not moved:
oracle_engine.py is frozen for another agent's in-flight F16 work, so removing
them there is not mine to do (noted in LIVE_CHANNEL 17.09).
"""
from __future__ import annotations

import collections
import statistics
from typing import Dict, List, Optional, Sequence

TICK_SIZE = 0.25

__all__ = [
    "trigger_quality", "delta_with", "vol_trigger", "location", "absorption",
    "double_bottom", "double_top", "detect_head_shoulders_short",
    "detect_head_shoulders_long", "detect_cup_handle_long",
    "median_abs_delta", "bar_val",
]


# ── bar accessors ───────────────────────────────────────────────────────────
# Live S2 bars carry both short ('c') and long ('close') keys; the study's DB
# rows carry the short ones only.  One accessor keeps the module usable from
# both without either caller reshaping its bars.
_ALIAS = {"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}


def bar_val(bar: Dict, key: str) -> Optional[float]:
    """Read ``key`` ('o'/'h'/'l'/'c'/'v') from a bar, tolerating long names."""
    if bar is None:
        return None
    v = bar.get(key)
    if v is None:
        v = bar.get(_ALIAS.get(key, key))
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def median_abs_delta(deltas: Sequence[Optional[float]],
                     min_n: int = 5) -> Optional[float]:
    """Median |delta| of the session so far — the yardstick every delta test uses.

    ``None`` (not 0.0) when fewer than ``min_n`` usable values: a yardstick of
    zero would make every bar "heavy".
    """
    vals = [abs(float(d)) for d in deltas if d is not None]
    if len(vals) < min_n:
        return None
    med = statistics.median(vals)
    return med if med > 0 else None


# ── 1. trigger ──────────────────────────────────────────────────────────────
def trigger_quality(bar: Dict, direction: str,
                    atr: Optional[float] = None) -> Dict:
    """Strength of the trigger bar — the single evidence that separated the
    winners from the losers in the 164-entry census.

    ``cp`` = close position inside the bar range (0 = on the low, 1 = on the
    high).  ``ok`` = closes in the extreme 30% in the trade's direction
    (LONG ``cp >= 0.7``, SHORT ``cp <= 0.3``) — the grammar's "trigger" row.

    Returns ``{cp, body_ratio, range_atr, ok}``; every value is ``None`` when
    its input is missing (a zero-range bar has no close position).
    """
    o, h, l, c = (bar_val(bar, k) for k in ("o", "h", "l", "c"))
    out: Dict[str, Optional[float]] = {"cp": None, "body_ratio": None,
                                       "range_atr": None, "ok": None}
    if None in (h, l, c):
        return out
    rng = h - l
    if rng <= 0:
        # Doji-flat bar: no close position exists.  Honest None, not 0.5.
        out["range_atr"] = 0.0 if atr else None
        return out
    cp = (c - l) / rng
    out["cp"] = round(cp, 4)
    if o is not None:
        out["body_ratio"] = round(abs(c - o) / rng, 4)
    if atr:
        out["range_atr"] = round(rng / float(atr), 4)
    out["ok"] = bool(cp >= 0.7) if direction == "LONG" else bool(cp <= 0.3)
    return out


# ── 2. delta ────────────────────────────────────────────────────────────────
def delta_with(bar_delta: Optional[float], median_abs: Optional[float],
               direction: str, mult: float = 1.0) -> Optional[bool]:
    """Trigger-bar delta confirms the direction: ``|δ| >= mult × median|δ|``
    and signed WITH the trade.  ``None`` when delta or the yardstick is missing.
    """
    if bar_delta is None or not median_abs:
        return None
    d = float(bar_delta)
    thr = float(mult) * float(median_abs)
    return bool(d >= thr) if direction == "LONG" else bool(d <= -thr)


# ── 3. volume ───────────────────────────────────────────────────────────────
def vol_trigger(bar_v: Optional[float], prev5_median: Optional[float],
                mult: float = 1.3) -> Optional[bool]:
    """Trigger-bar volume expands: ``v >= mult × median(previous 5 bars)``."""
    if bar_v is None or not prev5_median:
        return None
    return bool(float(bar_v) >= float(mult) * float(prev5_median))


def median_volume(bars: Sequence[Dict]) -> Optional[float]:
    """Median volume of the given (previous) bars — the ``vol_trigger`` yardstick."""
    vals = [v for v in (bar_val(b, "v") for b in bars or []) if v and v > 0]
    if not vals:
        return None
    med = statistics.median(vals)
    return med if med > 0 else None


# ── 4. location ─────────────────────────────────────────────────────────────
def location(price: Optional[float], dev_va: Optional[Dict],
             prev_va: Optional[Dict], ib: Optional[Dict],
             atr: Optional[float], tol_atr: float = 0.5) -> Dict:
    """Where the setup sits versus structure — **direction-aware**.

    F17b fix (order 17.09 19:40): a LONG is at its edge next to **VAL / the
    lower edge**, a SHORT next to **VAH / the upper edge**.  The previous
    definition used ``zone == BELOW_VA`` for longs, which is "beyond value",
    not "at the edge" — a long 20 points under VAL scored the same as one
    sitting on it.

    ``price`` is the structure the sequence is anchored on (the producers pass
    ``structural_anchor``: min low of b1..b3 for LONG, max high for SHORT), not
    the trigger close.  ``dev_va``/``prev_va`` take ``{vah, val, poc}``, ``ib``
    takes ``{high, low}`` (``ib_high``/``ib_low`` also accepted).

    Returns ``{zone, near_prev_edge, dist_to_edge_atr, at_edge_for}`` where
    ``at_edge_for`` is a plain ``{"LONG": bool, "SHORT": bool}`` dict — the
    result is JSON-serialisable because it travels into ``info["evidence"]`` →
    trade metadata.
    """
    out: Dict = {"zone": "UNKNOWN", "near_prev_edge": None,
                 "dist_to_edge_atr": None,
                 "at_edge_for": {"LONG": None, "SHORT": None}}
    if price is None:
        return out
    price = float(price)

    def _lv(d, *keys):
        for k in keys:
            if d and d.get(k) not in (None, ""):
                try:
                    v = float(d[k])
                except (TypeError, ValueError):
                    continue
                if v > 0:
                    return v
        return None

    dev_vah, dev_val, dev_poc = (_lv(dev_va, "vah"), _lv(dev_va, "val"),
                                 _lv(dev_va, "poc"))
    p_vah, p_val, p_poc = (_lv(prev_va, "vah"), _lv(prev_va, "val"),
                           _lv(prev_va, "poc"))
    ib_hi, ib_lo = _lv(ib, "high", "ib_high"), _lv(ib, "low", "ib_low")

    if dev_vah is not None and dev_val is not None:
        out["zone"] = ("ABOVE_VA" if price > dev_vah
                       else "BELOW_VA" if price < dev_val else "IN_VA")

    if not atr or float(atr) <= 0:
        return out                      # no yardstick → no "near" claim (Rule 1)
    tol = float(tol_atr) * float(atr)

    prev_levels = [x for x in (p_vah, p_val, p_poc) if x is not None]
    if prev_levels:
        out["near_prev_edge"] = bool(
            min(abs(price - x) for x in prev_levels) <= tol)

    lower = [x for x in (dev_val, ib_lo) + tuple(prev_levels) if x is not None]
    upper = [x for x in (dev_vah, ib_hi) + tuple(prev_levels) if x is not None]
    # "half of value" guard: a level only counts as the LOWER edge when the
    # price is in the lower half of the developing value (and vice versa).
    # Without it yesterday's VAH would make a long at today's high "at edge".
    mid = dev_poc if dev_poc is not None else (
        (dev_vah + dev_val) / 2 if (dev_vah is not None and dev_val is not None)
        else None)
    if lower:
        d_lo = min(abs(price - x) for x in lower)
        out["at_edge_for"]["LONG"] = bool(
            d_lo <= tol and (mid is None or price <= mid))
    if upper:
        d_hi = min(abs(price - x) for x in upper)
        out["at_edge_for"]["SHORT"] = bool(
            d_hi <= tol and (mid is None or price >= mid))
    all_lv = lower + upper
    if all_lv:
        out["dist_to_edge_atr"] = round(
            min(abs(price - x) for x in all_lv) / float(atr), 4)
    return out


def at_edge_for(loc: Optional[Dict], direction: str) -> Optional[bool]:
    """Convenience reader for ``location(...)['at_edge_for'][direction]``."""
    if not loc:
        return None
    return (loc.get("at_edge_for") or {}).get(direction)


# ── 5. absorption ───────────────────────────────────────────────────────────
def absorption(bars: Sequence[Dict], direction: str,
               median_abs: Optional[float], atr: Optional[float],
               heavy_mult: float = 1.5,
               max_progress_atr: float = 1.0) -> Optional[bool]:
    """Effort versus result — heavy delta AGAINST the trade with no progress.

    **Corrected definition** (order 17.09 19:40; the previous one produced N=0
    on 164 entries because it demanded that BOTH bars be heavy AND both signed
    against): at least ONE of the two bars before the trigger carries
    ``|δ| >= heavy_mult × median|δ|`` **against** the trade direction, and the
    price progress in that counter direction is ``<= max_progress_atr × ATR``.

    17.09 17:00/17:05 (Michael's example, LONG): δ −2,855 / −1,372 with the
    price only 3.25 pts below the previous low ⇒ ``True``.

    ``bars`` is the window ending at the bar BEFORE the trigger.  Called as the
    order writes it — ``absorption(bars[-3:-1], ...)`` — the pair's own first
    bar is the reference; pass one extra bar (``bars[-4:-1]``) and the bar
    before the pair becomes the reference, which is the stricter reading.
    """
    if not bars or len(bars) < 2 or not median_abs or not atr or float(atr) <= 0:
        return None
    pair = list(bars[-2:])
    ref = bars[-3] if len(bars) >= 3 else pair[0]
    thr = float(heavy_mult) * float(median_abs)
    long_side = direction == "LONG"

    heavy = False
    for b in pair:
        d = b.get("delta")
        if d is None:
            continue
        d = float(d)
        if (d <= -thr) if long_side else (d >= thr):
            heavy = True
            break
    if not heavy:
        return False

    if long_side:                       # counter direction = down
        lows = [x for x in (bar_val(b, "l") for b in pair) if x is not None]
        ref_lvl = bar_val(ref, "l")
        if not lows or ref_lvl is None:
            return None
        progress = max(0.0, ref_lvl - min(lows))
    else:                               # counter direction = up
        highs = [x for x in (bar_val(b, "h") for b in pair) if x is not None]
        ref_lvl = bar_val(ref, "h")
        if not highs or ref_lvl is None:
            return None
        progress = max(0.0, max(highs) - ref_lvl)
    return bool(progress <= float(max_progress_atr) * float(atr))


# ── 6. shapes ───────────────────────────────────────────────────────────────
# double_bottom/double_top moved here from scripts/pattern_evidence_study.py;
# the H&S / cup-handle triple are copies of scripts/oracle_engine.py (frozen —
# see the module docstring).  Signatures unchanged so both callers agree.

def double_bottom(win: List[Dict], atr: float) -> bool:
    """Two lows within 0.3×ATR, >=3 bars apart, neckline closed through."""
    if len(win) < 8:
        return False
    lows = sorted(range(len(win)), key=lambda k: bar_val(win[k], 'l'))[:2]
    if abs(lows[0] - lows[1]) < 3 or abs(bar_val(win[lows[0]], 'l') - bar_val(win[lows[1]], 'l')) > 0.3 * atr:
        return False
    neck = max(bar_val(x, 'h') for x in win[min(lows):max(lows) + 1])
    return bar_val(win[-1], 'c') > neck and (len(win) - 1 - max(lows)) <= 3


def double_top(win: List[Dict], atr: float) -> bool:
    """Mirror of :func:`double_bottom`."""
    if len(win) < 8:
        return False
    highs = sorted(range(len(win)), key=lambda k: -bar_val(win[k], 'h'))[:2]
    if abs(highs[0] - highs[1]) < 3 or abs(bar_val(win[highs[0]], 'h') - bar_val(win[highs[1]], 'h')) > 0.3 * atr:
        return False
    neck = min(bar_val(x, 'l') for x in win[min(highs):max(highs) + 1])
    return bar_val(win[-1], 'c') < neck and (len(win) - 1 - max(highs)) <= 3


def detect_head_shoulders_short(bars: List[Dict], i: int, atr: float) -> bool:
    """3 highs in 15-bar window, middle is highest, neckline broken by close."""
    win = bars[max(0, i - 15):i + 1]
    if len(win) < 7:
        return False
    third = len(win) // 3
    if third < 2:
        return False
    seg1, seg2, seg3 = win[:third], win[third:2 * third], win[2 * third:]

    h1_idx = max(range(len(seg1)), key=lambda k: bar_val(seg1[k], 'h'))
    h2_idx = max(range(len(seg2)), key=lambda k: bar_val(seg2[k], 'h'))
    h3_idx = max(range(len(seg3)), key=lambda k: bar_val(seg3[k], 'h'))
    h1, h2, h3 = bar_val(seg1[h1_idx], 'h'), bar_val(seg2[h2_idx], 'h'), bar_val(seg3[h3_idx], 'h')

    if not (h2 > h1 and h2 > h3):
        return False
    if abs(h1 - h3) > atr:
        return False

    neckline_bars = win[h1_idx:2 * third + h3_idx + 1]
    if not neckline_bars:
        return False
    neckline = min(bar_val(b, 'l') for b in neckline_bars)
    return bar_val(bars[i], 'c') < neckline


def detect_head_shoulders_long(bars: List[Dict], i: int, atr: float) -> bool:
    """Mirror of short: 3 lows, middle lowest, neckline broken upward."""
    win = bars[max(0, i - 15):i + 1]
    if len(win) < 7:
        return False
    third = len(win) // 3
    if third < 2:
        return False
    seg1, seg2, seg3 = win[:third], win[third:2 * third], win[2 * third:]

    l1_idx = min(range(len(seg1)), key=lambda k: bar_val(seg1[k], 'l'))
    l2_idx = min(range(len(seg2)), key=lambda k: bar_val(seg2[k], 'l'))
    l3_idx = min(range(len(seg3)), key=lambda k: bar_val(seg3[k], 'l'))
    l1, l2, l3 = bar_val(seg1[l1_idx], 'l'), bar_val(seg2[l2_idx], 'l'), bar_val(seg3[l3_idx], 'l')

    if not (l2 < l1 and l2 < l3):
        return False
    if abs(l1 - l3) > atr:
        return False

    neckline_bars = win[l1_idx:2 * third + l3_idx + 1]
    if not neckline_bars:
        return False
    neckline = max(bar_val(b, 'h') for b in neckline_bars)
    return bar_val(bars[i], 'c') > neckline


def detect_cup_handle_long(bars: List[Dict], i: int, atr: float) -> bool:
    """Low point at least 8 bars back, handle <=4 bars, breakout."""
    if i < 10:
        return False
    win = bars[max(0, i - 20):i + 1]
    if len(win) < 10:
        return False

    cup_region = win[:len(win) - 4]
    if len(cup_region) < 8:
        return False
    cup_low_idx = min(range(len(cup_region)), key=lambda k: bar_val(cup_region[k], 'l'))
    cup_low = bar_val(cup_region[cup_low_idx], 'l')

    handle = win[-4:]
    handle_low = min(bar_val(b, 'l') for b in handle)
    if handle_low < cup_low:
        return False

    right_rim = (max(bar_val(b, 'h') for b in win[cup_low_idx:len(win) - 4])
                 if cup_low_idx < len(win) - 4 else cup_low)
    cup_depth = right_rim - cup_low
    if cup_depth <= 0:
        return False
    if (right_rim - handle_low) > 0.5 * cup_depth:
        return False
    return bar_val(bars[i], 'c') > right_rim


def compute_developing_va(bars: List[Dict], i: int) -> Dict[str, float]:
    """Developing VA from today's closes up to ``i`` (same maths as
    ``oracle_engine.compute_developing_va``; copied, not moved — frozen file).
    """
    if i < 3:
        return {}
    closes = [round(bar_val(b, 'c') / TICK_SIZE) * TICK_SIZE for b in bars[:i + 1]
              if bar_val(b, 'c') is not None]
    if not closes:
        return {}
    poc = collections.Counter(closes).most_common(1)[0][0]
    all_prices = sorted(closes)
    n = len(all_prices)
    va_count = max(1, int(n * 0.70))
    best_start, best_dist = 0, float('inf')
    for start in range(n - va_count + 1):
        window = all_prices[start:start + va_count]
        dist = 0 if window[0] <= poc <= window[-1] else min(
            abs(poc - window[0]), abs(poc - window[-1]))
        if dist < best_dist:
            best_dist, best_start = dist, start
    va = all_prices[best_start:best_start + va_count]
    return {'poc': poc, 'val': va[0], 'vah': va[-1]}
