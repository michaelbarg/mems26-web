#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""setup_engine.py — F17 · T-411 — Multi-bar setup detection engine.

Detects multi-bar setups on historical bars according to the grammar
defined in docs/spec_authority/SETUP_GRAMMAR_2026-09-17.md.

Setups implemented:
  1. DBL_BOTTOM_ABS  — Double bottom at value edge with absorption
  2. ROTATION_BREAK  — Rotation break after drive

CLI:
    python3 scripts/setup_engine.py                        # all clean sessions
    python3 scripts/setup_engine.py --session 2026-09-17   # golden session
    python3 scripts/setup_engine.py --validate             # run oracle_validate on hits
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import statistics
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from backend.env_loader import load_dotenv_file
load_dotenv_file(os.path.join(_ROOT, '.env'), override=False)

from backend.v9.db.read import read_all

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TICK_SIZE = 0.25
TICK_USD = 5.0
SLIPPAGE_PTS = 0.50
COMMISSION_RT = 1.30

# Excluded sessions (from oracle_engine)
EXC: Set[str] = {
    '2026-06-09', '2026-06-10', '2026-06-11', '2026-06-12',
    '2026-06-17', '2026-06-18', '2026-06-19', '2026-06-26',
    '2026-07-10', '2026-07-24', '2026-07-28', '2026-07-29',
    '2026-09-16',
}

# Roll dates
def _third_friday(year: int, month: int):
    from datetime import date, timedelta
    first = date(year, month, 1)
    days_to_friday = (4 - first.weekday()) % 7
    return first + timedelta(days=days_to_friday + 14)

def _roll_dates(year: int = 2026) -> Set[str]:
    from datetime import timedelta
    roll_set: Set[str] = set()
    for month in (3, 6, 9, 12):
        expiry = _third_friday(year, month)
        d = expiry
        count = 0
        while count < 3:
            if d.weekday() < 5:
                roll_set.add(d.strftime("%Y-%m-%d"))
                count += 1
            d -= timedelta(days=1)
    return roll_set

ROLL_DATES = _roll_dates(2026)

# ---------------------------------------------------------------------------
# Default parameters
# ---------------------------------------------------------------------------
DEFAULT_PARAMS: Dict[str, Any] = {
    # DBL_BOTTOM_ABS
    "dbl_tol_atr": 1.0,
    "dbl_spring_atr": 1.0,
    "dbl_min_dist": 3,
    "dbl_max_dist": 12,
    "dbl_absorption_mult": 1.5,
    "dbl_progress_atr": 1.0,
    "dbl_trigger_delta_mult": 1.0,
    "dbl_trigger_vol_ratio": 0.8,
    "dbl_trigger_close_pct": 0.30,
    "dbl_location_atr": 0.5,
    "dbl_move_from_open_atr": 2.0,
    # ROTATION_BREAK
    "rot_min_bars": 4,
    "rot_max_bars": 8,
    "rot_max_range_atr": 2.0,
    "rot_overlap_atr": 0.2,
    "rot_vol_decay": True,
    "rot_trigger_vol_mult": 1.3,
    "rot_trigger_delta_mult": 2.0,
    "rot_trigger_close_pct": 0.30,
    "rot_drive_atr": 2.0,
}


# ---------------------------------------------------------------------------
# Data loading (reuse oracle_engine patterns)
# ---------------------------------------------------------------------------
def load_bars(session_date: Optional[str] = None) -> List[Dict]:
    """Load RTH 5-min bars with delta from DB. Delta dedup via DISTINCT ON."""
    where_clause = "b.ts >= '2026-06-01'"
    params: Dict[str, Any] = {}
    if session_date:
        where_clause += " AND (b.ts at time zone 'Asia/Jerusalem')::date = (:d)::date"
        params['d'] = session_date

    return read_all(
        f"""SELECT b.ts,
               (b.ts AT TIME ZONE 'Asia/Jerusalem')::date d,
               (b.ts AT TIME ZONE 'Asia/Jerusalem')::time t,
               b.open o, b.high h, b.low l, b.close c, b.volume v,
               cd.delta
        FROM v9_bars_5min_woodies b
        LEFT JOIN LATERAL (
            SELECT delta FROM v9_bars_cumulative_delta
            WHERE ts = b.ts
            ORDER BY created_at DESC
            LIMIT 1
        ) cd ON true
        WHERE {where_clause}
          AND (b.ts AT TIME ZONE 'Asia/Jerusalem')::time BETWEEN '16:30' AND '23:00'
        ORDER BY b.ts""",
        params
    )


def load_previous_day_levels(session_date: str) -> Optional[Dict]:
    """Load previous session levels from v9_tpo_history or compute from bars."""
    row = read_all(
        """SELECT vah, val, poc
        FROM v9_tpo_history
        WHERE (ts AT TIME ZONE 'Asia/Jerusalem')::date < (:d)::date
        ORDER BY ts DESC
        LIMIT 1""",
        {'d': session_date}
    )
    if row and row[0].get('vah') is not None:
        return {
            'pd_vah': float(row[0]['vah']),
            'pd_val': float(row[0]['val']),
            'pd_poc': float(row[0]['poc']),
        }
    return None


# ---------------------------------------------------------------------------
# Causal ATR (from oracle_engine)
# ---------------------------------------------------------------------------
def compute_atr(bars: List[Dict], idx: int, period: int = 14) -> Optional[float]:
    """Compute ATR at bar index idx using only bars [0..idx] (causal).

    Falls back to a shorter window (min 5 bars) when the full period
    is not yet available — important for early-session detection.
    """
    effective_period = period
    if idx < period:
        if idx >= 5:
            effective_period = idx
        else:
            return None
    trs = []
    for k in range(idx - effective_period + 1, idx + 1):
        tr = max(
            bars[k]['h'] - bars[k]['l'],
            abs(bars[k]['h'] - bars[k - 1]['c']),
            abs(bars[k]['l'] - bars[k - 1]['c']),
        )
        trs.append(tr)
    return sum(trs) / len(trs)


# ---------------------------------------------------------------------------
# Developing value area (from oracle_engine)
# ---------------------------------------------------------------------------
def compute_developing_va(bars: List[Dict], i: int) -> Dict[str, float]:
    """POC = mode of closes (tick-rounded), VAH/VAL = 70% range around POC."""
    if i < 3:
        return {}
    closes = [round(b['c'] / TICK_SIZE) * TICK_SIZE for b in bars[:i + 1]]
    if not closes:
        return {}
    counter = collections.Counter(closes)
    poc = counter.most_common(1)[0][0]
    all_prices = sorted(closes)
    n = len(all_prices)
    va_count = max(1, int(n * 0.70))
    best_start = 0
    best_dist = float('inf')
    for start in range(n - va_count + 1):
        window = all_prices[start:start + va_count]
        if window[0] <= poc <= window[-1]:
            dist = 0
        else:
            dist = min(abs(poc - window[0]), abs(poc - window[-1]))
        if dist < best_dist:
            best_dist = dist
            best_start = start
    va_prices = all_prices[best_start:best_start + va_count]
    return {'poc': poc, 'val': va_prices[0], 'vah': va_prices[-1]}


# ---------------------------------------------------------------------------
# IB levels (first 6 RTH bars = 16:30-17:00)
# ---------------------------------------------------------------------------
def compute_ib(bars: List[Dict]) -> Dict[str, float]:
    """IB = first 6 bars (30 minutes from 16:30)."""
    ib_bars = bars[:6]
    if len(ib_bars) < 6:
        return {}
    return {
        'ib_high': max(b['h'] for b in ib_bars),
        'ib_low': min(b['l'] for b in ib_bars),
    }


# ---------------------------------------------------------------------------
# Phase classifier (simple, from oracle_engine)
# ---------------------------------------------------------------------------
def classify_phase(i: int) -> str:
    if i < 3:
        return 'A'
    if i < 12:
        return 'B'
    if i < 54:
        return 'C'
    return 'D'


# ---------------------------------------------------------------------------
# Helper: vol_ratio relative to session median
# ---------------------------------------------------------------------------
def _vol_ratio(bar: Dict, session_bars: List[Dict], i: int,
               window: Optional[int] = None) -> Optional[float]:
    """Volume of bar relative to median volume of prior bars.

    If window is given, use the last `window` bars before bar i.
    Otherwise use all prior bars in the session.
    """
    if i < 3:
        return None
    if window is not None:
        start = max(0, i - window)
    else:
        start = 0
    vols = [float(b['v'] or 0) for b in session_bars[start:i]]
    if not vols:
        return None
    med = statistics.median(vols)
    if med <= 0:
        return None
    return float(bar['v'] or 0) / med


# ---------------------------------------------------------------------------
# Helper: check proximity to value levels
# ---------------------------------------------------------------------------
def _near_level(price: float, levels: Dict, atr: float,
                tolerance_atr: float) -> Tuple[bool, str]:
    """Check if price is within tolerance_atr * ATR of any value level.
    Returns (near, level_name).
    """
    tol = tolerance_atr * atr
    check_levels = [
        ('pd_val', levels.get('pd_val')),
        ('pd_vah', levels.get('pd_vah')),
        ('pd_poc', levels.get('pd_poc')),
        ('ib_low', levels.get('ib_low')),
        ('ib_high', levels.get('ib_high')),
        ('developing_val', levels.get('developing_val')),
        ('developing_vah', levels.get('developing_vah')),
    ]
    for name, lvl in check_levels:
        if lvl is not None and abs(price - lvl) <= tol:
            return True, name
    return False, ''


# ---------------------------------------------------------------------------
# Helper: find nearest level for T1/T2
# ---------------------------------------------------------------------------
def _nearest_level_above(price: float, levels: Dict) -> Optional[float]:
    """Find the nearest level above price."""
    candidates = []
    for key in ('pd_vah', 'pd_poc', 'ib_high', 'developing_vah'):
        lvl = levels.get(key)
        if lvl is not None and lvl > price:
            candidates.append(lvl)
    # Also IB mid
    ib_h = levels.get('ib_high')
    ib_l = levels.get('ib_low')
    if ib_h is not None and ib_l is not None:
        mid = (ib_h + ib_l) / 2
        if mid > price:
            candidates.append(mid)
    return min(candidates) if candidates else None


def _nearest_level_below(price: float, levels: Dict) -> Optional[float]:
    """Find the nearest level below price."""
    candidates = []
    for key in ('pd_val', 'pd_poc', 'ib_low', 'developing_val'):
        lvl = levels.get(key)
        if lvl is not None and lvl < price:
            candidates.append(lvl)
    ib_h = levels.get('ib_high')
    ib_l = levels.get('ib_low')
    if ib_h is not None and ib_l is not None:
        mid = (ib_h + ib_l) / 2
        if mid < price:
            candidates.append(mid)
    return max(candidates) if candidates else None


# ---------------------------------------------------------------------------
# Setup #1: DBL_BOTTOM_ABS — Double bottom at value edge with absorption
# ---------------------------------------------------------------------------
def _detect_dbl_bottom_abs(bars: List[Dict], levels: Dict, params: Dict
                           ) -> List[Dict]:
    """Detect double bottom (LONG) and double top (SHORT) setups."""
    hits: List[Dict] = []
    p = {**DEFAULT_PARAMS, **params}

    for i in range(p['dbl_min_dist'] + 2, len(bars) - 1):
        atr = compute_atr(bars, i)
        if atr is None or atr <= 0:
            continue

        phase = classify_phase(i)
        if phase not in ('B', 'C', 'D'):
            continue

        # Move from open check
        move_from_open = (bars[i]['c'] - bars[0]['o']) / atr

        # Collect session deltas for median
        session_deltas = []
        for k in range(i + 1):
            d = bars[k].get('delta')
            if d is not None:
                session_deltas.append(abs(float(d)))

        if len(session_deltas) < 3:
            continue
        median_delta = statistics.median(session_deltas)
        if median_delta <= 0:
            continue

        # Use a 6-bar rolling window for vol_ratio to avoid the drive bar
        # inflating the median (the drive bar is NOT part of the setup sequence)
        vr_i = _vol_ratio(bars[i], bars, i, window=6)

        # Try LONG: double bottom
        hit = _try_dbl_bottom_long(bars, i, atr, levels, p,
                                   session_deltas, median_delta, vr_i,
                                   move_from_open, phase)
        if hit:
            hits.append(hit)

        # Try SHORT: double top (mirror)
        hit = _try_dbl_top_short(bars, i, atr, levels, p,
                                 session_deltas, median_delta, vr_i,
                                 move_from_open, phase)
        if hit:
            hits.append(hit)

    return hits


def _try_dbl_bottom_long(bars, i, atr, levels, p,
                         session_deltas, median_delta, vr_i,
                         move_from_open, phase) -> Optional[Dict]:
    """Try to detect a LONG double bottom at bar i (the trigger)."""

    # Context: move from open >= threshold (was a meaningful move down)
    if move_from_open > -p['dbl_move_from_open_atr']:
        return None

    # Trigger bar checks
    bar = bars[i]
    rng = bar['h'] - bar['l']
    if rng <= 0:
        return None
    close_pos = (bar['c'] - bar['l']) / rng
    if close_pos < (1.0 - p['dbl_trigger_close_pct']):
        return None  # close must be in top 30%

    # Delta on trigger must be positive and strong
    trigger_delta = bar.get('delta')
    if trigger_delta is None:
        return None
    trigger_delta = float(trigger_delta)
    if trigger_delta < p['dbl_trigger_delta_mult'] * median_delta:
        return None

    # Vol ratio check
    if vr_i is not None and vr_i < p['dbl_trigger_vol_ratio']:
        return None

    # Strategy: find two low-zones (first touch / second push) in the lookback.
    # First, collect all candidate "low bars" — bars with lows near a value level.
    # Then find pairs where the second low retests the first, with absorption.
    lookback_start = max(0, i - p['dbl_max_dist'])
    lookback_end = i  # trigger bar itself is not a low

    # Find the lowest-low bar in each "push" zone near a level
    # Approach: find all bars whose low is near a value level, then group by
    # proximity and pick the deepest in each group as a candidate.
    best_first = None
    best_second = None
    best_neckline = None
    best_location = None

    # Collect bars with lows near any value level
    low_candidates = []
    for idx in range(lookback_start, lookback_end):
        bar_low = bars[idx]['l']
        near, level_name = _near_level(bar_low, levels, atr,
                                       p['dbl_location_atr'])
        if near:
            low_candidates.append((idx, bar_low, level_name))

    # Also consider bars that are near the lowest low of near-level bars
    # (the second push may spring below and still be valid)
    if low_candidates:
        ref_low = min(lc[1] for lc in low_candidates)
        for idx in range(lookback_start, lookback_end):
            if any(lc[0] == idx for lc in low_candidates):
                continue
            bar_low = bars[idx]['l']
            # Within tolerance of the reference low
            if abs(bar_low - ref_low) <= p['dbl_tol_atr'] * atr:
                low_candidates.append((idx, bar_low, 'spring'))

    if len(low_candidates) < 2:
        return None

    # Sort by index
    low_candidates.sort(key=lambda x: x[0])

    # Try all pairs (first, second) where second is 3-12 bars after first
    best_score = -1
    for fi, (first_idx, first_low, first_level) in enumerate(low_candidates):
        for si in range(fi + 1, len(low_candidates)):
            second_idx, second_low, _ = low_candidates[si]

            dist = second_idx - first_idx
            if dist < p['dbl_min_dist'] or dist > p['dbl_max_dist']:
                continue

            # Second low within tolerance of first
            diff = second_low - first_low
            if diff < -p['dbl_tol_atr'] * atr:
                continue
            if diff > 0.3 * atr:
                continue

            # Spring check
            progress_below = first_low - second_low
            if progress_below > p['dbl_spring_atr'] * atr:
                continue

            # The second low should be the deepest low in its local push.
            # Find the actual min-low bar around second_idx (±1 bar).
            actual_second_idx = second_idx
            actual_second_low = second_low
            for adj in range(max(lookback_start, second_idx - 1),
                             min(lookback_end, second_idx + 2)):
                if bars[adj]['l'] < actual_second_low:
                    actual_second_low = bars[adj]['l']
                    actual_second_idx = adj

            # Neckline: highest high between first and second lows
            neckline_bars_slice = bars[first_idx:actual_second_idx + 1]
            neckline = max(b['h'] for b in neckline_bars_slice)

            # Absorption check: in the second push area, heavy |delta|
            # with limited price progress below first low
            absorption = False
            push_start = max(first_idx + 1, actual_second_idx - 2)
            push_end = min(actual_second_idx + 2, i)
            for pk in range(push_start, push_end):
                d_val = bars[pk].get('delta')
                if d_val is not None:
                    if abs(float(d_val)) >= p['dbl_absorption_mult'] * median_delta:
                        progress = first_low - bars[pk]['l']
                        if progress <= p['dbl_progress_atr'] * atr:
                            absorption = True
                            break

            if not absorption:
                continue

            # Trigger close check: above neckline or above prev bar's high
            neckline_dist = neckline - actual_second_low
            if neckline_dist <= 1.5 * atr:
                trigger_level = max(neckline, bars[i - 1]['h'])
            else:
                trigger_level = bars[i - 1]['h']

            if bar['c'] < trigger_level:
                continue

            # Score: prefer deeper second lows (better absorption signal)
            score = first_low - actual_second_low
            if score > best_score or best_first is None:
                best_score = score
                best_first = first_idx
                best_second = actual_second_idx
                best_neckline = neckline
                best_location = first_level

    if best_first is None:
        return None

    # Build the hit — stop below the sequence extreme (deepest low)
    seq_low = min(bars[k]['l'] for k in range(best_first, i + 1))
    entry = float(bars[i + 1]['o']) if i + 1 < len(bars) else float(bar['c'])
    stop = seq_low - TICK_SIZE

    # T1: nearest level above entry (POC/IB-mid/VAH)
    t1 = _nearest_level_above(entry, levels)
    if t1 is None:
        t1 = entry + abs(best_neckline - seq_low)

    # T2: measured move (height of pattern) or next level
    pattern_height = best_neckline - seq_low
    t2 = best_neckline + pattern_height
    next_lvl = _nearest_level_above(t1, levels) if t1 else None
    if next_lvl is not None:
        t2 = max(t2, next_lvl)

    # Sequence bars
    seq_bars = list(range(best_first, i + 1))
    delta_seq = []
    for si in seq_bars:
        d_val = bars[si].get('delta')
        delta_seq.append(float(d_val) if d_val is not None else 0.0)

    return {
        "setup_id": "DBL_BOTTOM_ABS",
        "direction": "LONG",
        "trigger_idx": i,
        "trigger_il": str(bars[i].get('t', ''))[:5],
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "t1": round(t1, 2),
        "t2": round(t2, 2),
        "sequence_bars": seq_bars,
        "location": f"near {best_location}",
        "evidence": {
            "delta_seq": delta_seq,
            "delta_trigger": trigger_delta,
            "vol_ratio_trigger": round(vr_i, 4) if vr_i else None,
            "absorption": True,
        },
    }


def _try_dbl_top_short(bars, i, atr, levels, p,
                       session_deltas, median_delta, vr_i,
                       move_from_open, phase) -> Optional[Dict]:
    """Mirror of double bottom: double top at upper value edge -> SHORT."""

    # Context: move from open >= threshold upward
    if move_from_open < p['dbl_move_from_open_atr']:
        return None

    bar = bars[i]
    rng = bar['h'] - bar['l']
    if rng <= 0:
        return None
    close_pos = (bar['c'] - bar['l']) / rng
    if close_pos > p['dbl_trigger_close_pct']:
        return None  # close must be in bottom 30%

    trigger_delta = bar.get('delta')
    if trigger_delta is None:
        return None
    trigger_delta = float(trigger_delta)
    # For short, delta should be strongly negative
    if trigger_delta > -p['dbl_trigger_delta_mult'] * median_delta:
        return None

    if vr_i is not None and vr_i < p['dbl_trigger_vol_ratio']:
        return None

    lookback_start = max(0, i - p['dbl_max_dist'])
    lookback_end = i

    # Collect candidate high bars near value levels
    high_candidates = []
    for idx in range(lookback_start, lookback_end):
        bar_high = bars[idx]['h']
        near, level_name = _near_level(bar_high, levels, atr,
                                       p['dbl_location_atr'])
        if near:
            high_candidates.append((idx, bar_high, level_name))

    if high_candidates:
        ref_high = max(hc[1] for hc in high_candidates)
        for idx in range(lookback_start, lookback_end):
            if any(hc[0] == idx for hc in high_candidates):
                continue
            bar_high = bars[idx]['h']
            if abs(bar_high - ref_high) <= p['dbl_tol_atr'] * atr:
                high_candidates.append((idx, bar_high, 'spring'))

    if len(high_candidates) < 2:
        return None

    high_candidates.sort(key=lambda x: x[0])

    best_first = None
    best_second = None
    best_neckline = None
    best_location = None
    best_score = -1

    for fi, (first_idx, first_high, first_level) in enumerate(high_candidates):
        for si in range(fi + 1, len(high_candidates)):
            second_idx, second_high, _ = high_candidates[si]
            dist = second_idx - first_idx
            if dist < p['dbl_min_dist'] or dist > p['dbl_max_dist']:
                continue
            diff = second_high - first_high
            if diff > p['dbl_tol_atr'] * atr or diff < -0.3 * atr:
                continue
            progress_above = second_high - first_high
            if progress_above > p['dbl_spring_atr'] * atr:
                continue

            actual_second_idx = second_idx
            actual_second_high = second_high
            for adj in range(max(lookback_start, second_idx - 1),
                             min(lookback_end, second_idx + 2)):
                if bars[adj]['h'] > actual_second_high:
                    actual_second_high = bars[adj]['h']
                    actual_second_idx = adj

            neckline_bars_slice = bars[first_idx:actual_second_idx + 1]
            neckline = min(b['l'] for b in neckline_bars_slice)

            absorption = False
            push_start = max(first_idx + 1, actual_second_idx - 2)
            push_end = min(actual_second_idx + 2, i)
            for pk in range(push_start, push_end):
                d_val = bars[pk].get('delta')
                if d_val is not None:
                    if abs(float(d_val)) >= p['dbl_absorption_mult'] * median_delta:
                        progress = bars[pk]['h'] - first_high
                        if progress <= p['dbl_progress_atr'] * atr:
                            absorption = True
                            break
            if not absorption:
                continue

            neckline_dist = actual_second_high - neckline
            if neckline_dist <= 1.5 * atr:
                trigger_level = min(neckline, bars[i - 1]['l'])
            else:
                trigger_level = bars[i - 1]['l']
            if bar['c'] > trigger_level:
                continue

            score = actual_second_high - first_high
            if score > best_score or best_first is None:
                best_score = score
                best_first = first_idx
                best_second = actual_second_idx
                best_neckline = neckline
                best_location = first_level

    if best_first is None:
        return None

    seq_high = max(bars[k]['h'] for k in range(best_first, i + 1))
    entry = float(bars[i + 1]['o']) if i + 1 < len(bars) else float(bar['c'])
    stop = seq_high + TICK_SIZE

    t1 = _nearest_level_below(entry, levels)
    if t1 is None:
        t1 = entry - abs(seq_high - best_neckline)

    pattern_height = seq_high - best_neckline
    t2 = best_neckline - pattern_height
    next_lvl = _nearest_level_below(t1, levels) if t1 else None
    if next_lvl is not None:
        t2 = min(t2, next_lvl)

    seq_bars = list(range(best_first, i + 1))
    delta_seq = []
    for si in seq_bars:
        d_val = bars[si].get('delta')
        delta_seq.append(float(d_val) if d_val is not None else 0.0)

    return {
        "setup_id": "DBL_BOTTOM_ABS",
        "direction": "SHORT",
        "trigger_idx": i,
        "trigger_il": str(bars[i].get('t', ''))[:5],
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "t1": round(t1, 2),
        "t2": round(t2, 2),
        "sequence_bars": seq_bars,
        "location": f"near {best_location}",
        "evidence": {
            "delta_seq": delta_seq,
            "delta_trigger": trigger_delta,
            "vol_ratio_trigger": round(vr_i, 4) if vr_i else None,
            "absorption": True,
        },
    }


# ---------------------------------------------------------------------------
# Setup #2: ROTATION_BREAK — Rotation break after drive
# ---------------------------------------------------------------------------
def _detect_rotation_break(bars: List[Dict], levels: Dict, params: Dict
                           ) -> List[Dict]:
    """Detect rotation break setups."""
    hits: List[Dict] = []
    p = {**DEFAULT_PARAMS, **params}

    for i in range(p['rot_min_bars'] + 2, len(bars) - 1):
        atr = compute_atr(bars, i)
        if atr is None or atr <= 0:
            continue

        bar = bars[i]
        vr_i = _vol_ratio(bar, bars, i)

        # Session deltas for median
        session_deltas = []
        for k in range(i + 1):
            d = bars[k].get('delta')
            if d is not None:
                session_deltas.append(abs(float(d)))
        if len(session_deltas) < 3:
            continue
        median_delta = statistics.median(session_deltas)
        if median_delta <= 0:
            continue

        # Try SHORT rotation break
        hit = _try_rotation_short(bars, i, atr, levels, p,
                                  median_delta, vr_i)
        if hit:
            hits.append(hit)

        # Try LONG rotation break (mirror)
        hit = _try_rotation_long(bars, i, atr, levels, p,
                                 median_delta, vr_i)
        if hit:
            hits.append(hit)

    return hits


def _try_rotation_short(bars, i, atr, levels, p,
                        median_delta, vr_i) -> Optional[Dict]:
    """Detect SHORT rotation break: rotation then break below."""
    bar = bars[i]
    rng = bar['h'] - bar['l']
    if rng <= 0:
        return None

    # Trigger close in bottom 30%
    close_pos = (bar['c'] - bar['l']) / rng
    if close_pos > p['rot_trigger_close_pct']:
        return None

    # Trigger delta must be strongly negative
    trigger_delta = bar.get('delta')
    if trigger_delta is None:
        return None
    trigger_delta = float(trigger_delta)
    if abs(trigger_delta) < p['rot_trigger_delta_mult'] * median_delta:
        return None
    if trigger_delta > 0:
        return None  # must be negative for SHORT

    # Look for rotation ending just before bar i
    for rot_len in range(p['rot_max_bars'], p['rot_min_bars'] - 1, -1):
        rot_start = i - rot_len
        if rot_start < 1:
            continue
        rot_bars = bars[rot_start:i]

        # Rotation range check
        rot_high = max(b['h'] for b in rot_bars)
        rot_low = min(b['l'] for b in rot_bars)
        rot_range = rot_high - rot_low
        if rot_range > p['rot_max_range_atr'] * atr:
            continue

        # Overlap check: all bars within tolerance of rotation range
        overlap_ok = True
        for rb in rot_bars:
            if rb['h'] > rot_high + p['rot_overlap_atr'] * atr:
                overlap_ok = False
                break
            if rb['l'] < rot_low - p['rot_overlap_atr'] * atr:
                overlap_ok = False
                break
        if not overlap_ok:
            continue

        # Volume decay check
        if p['rot_vol_decay'] and len(rot_bars) >= 6:
            first_3_vols = [float(b['v'] or 0) for b in rot_bars[:3]]
            last_3_vols = [float(b['v'] or 0) for b in rot_bars[-3:]]
            if statistics.median(last_3_vols) >= statistics.median(first_3_vols):
                continue
        elif p['rot_vol_decay'] and len(rot_bars) >= 4:
            half = len(rot_bars) // 2
            first_vols = [float(b['v'] or 0) for b in rot_bars[:half]]
            last_vols = [float(b['v'] or 0) for b in rot_bars[half:]]
            if statistics.median(last_vols) >= statistics.median(first_vols):
                continue

        # Volume of trigger vs median of rotation
        rot_vols = [float(b['v'] or 0) for b in rot_bars]
        rot_vol_med = statistics.median(rot_vols)
        if rot_vol_med > 0:
            trigger_vol_ratio = float(bar['v'] or 0) / rot_vol_med
            if trigger_vol_ratio < p['rot_trigger_vol_mult']:
                continue
        else:
            continue

        # Trigger must close below rotation low
        if bar['c'] >= rot_low:
            continue

        # Drive check: preceding the rotation, price must have moved
        # at least rot_drive_atr * ATR in the direction we're breaking
        if rot_start >= 1:
            pre_drive_high = max(b['h'] for b in bars[:rot_start])
            drive = pre_drive_high - rot_low
            if drive < p['rot_drive_atr'] * atr:
                continue
        else:
            continue

        # Build hit
        entry = float(bars[i + 1]['o']) if i + 1 < len(bars) else float(bar['c'])
        stop = rot_high + TICK_SIZE

        # T1: 1x rotation range below break point
        t1 = rot_low - rot_range
        # T2: next level below
        t2_level = _nearest_level_below(t1, levels)
        t2 = t2_level if t2_level is not None else t1 - rot_range

        seq_bars = list(range(rot_start, i + 1))
        delta_seq = []
        for si in seq_bars:
            d_val = bars[si].get('delta')
            delta_seq.append(float(d_val) if d_val is not None else 0.0)

        return {
            "setup_id": "ROTATION_BREAK",
            "direction": "SHORT",
            "trigger_idx": i,
            "trigger_il": str(bars[i].get('t', ''))[:5],
            "entry": round(entry, 2),
            "stop": round(stop, 2),
            "t1": round(t1, 2),
            "t2": round(t2, 2),
            "sequence_bars": seq_bars,
            "location": f"rotation {rot_low:.2f}-{rot_high:.2f}",
            "evidence": {
                "delta_seq": delta_seq,
                "delta_trigger": trigger_delta,
                "vol_ratio_trigger": round(trigger_vol_ratio, 4),
                "absorption": False,
            },
        }

    return None


def _try_rotation_long(bars, i, atr, levels, p,
                       median_delta, vr_i) -> Optional[Dict]:
    """Mirror: LONG rotation break — rotation then break above."""
    bar = bars[i]
    rng = bar['h'] - bar['l']
    if rng <= 0:
        return None

    # Trigger close in top 30%
    close_pos = (bar['c'] - bar['l']) / rng
    if close_pos < (1.0 - p['rot_trigger_close_pct']):
        return None

    trigger_delta = bar.get('delta')
    if trigger_delta is None:
        return None
    trigger_delta = float(trigger_delta)
    if abs(trigger_delta) < p['rot_trigger_delta_mult'] * median_delta:
        return None
    if trigger_delta < 0:
        return None  # must be positive for LONG

    for rot_len in range(p['rot_max_bars'], p['rot_min_bars'] - 1, -1):
        rot_start = i - rot_len
        if rot_start < 1:
            continue
        rot_bars = bars[rot_start:i]

        rot_high = max(b['h'] for b in rot_bars)
        rot_low = min(b['l'] for b in rot_bars)
        rot_range = rot_high - rot_low
        if rot_range > p['rot_max_range_atr'] * atr:
            continue

        overlap_ok = True
        for rb in rot_bars:
            if rb['h'] > rot_high + p['rot_overlap_atr'] * atr:
                overlap_ok = False
                break
            if rb['l'] < rot_low - p['rot_overlap_atr'] * atr:
                overlap_ok = False
                break
        if not overlap_ok:
            continue

        if p['rot_vol_decay'] and len(rot_bars) >= 6:
            first_3_vols = [float(b['v'] or 0) for b in rot_bars[:3]]
            last_3_vols = [float(b['v'] or 0) for b in rot_bars[-3:]]
            if statistics.median(last_3_vols) >= statistics.median(first_3_vols):
                continue
        elif p['rot_vol_decay'] and len(rot_bars) >= 4:
            half = len(rot_bars) // 2
            first_vols = [float(b['v'] or 0) for b in rot_bars[:half]]
            last_vols = [float(b['v'] or 0) for b in rot_bars[half:]]
            if statistics.median(last_vols) >= statistics.median(first_vols):
                continue

        rot_vols = [float(b['v'] or 0) for b in rot_bars]
        rot_vol_med = statistics.median(rot_vols)
        if rot_vol_med > 0:
            trigger_vol_ratio = float(bar['v'] or 0) / rot_vol_med
            if trigger_vol_ratio < p['rot_trigger_vol_mult']:
                continue
        else:
            continue

        if bar['c'] <= rot_high:
            continue

        # Drive check: preceding rotation, price dropped at least drive_atr
        if rot_start >= 1:
            pre_drive_low = min(b['l'] for b in bars[:rot_start])
            drive = rot_high - pre_drive_low
            if drive < p['rot_drive_atr'] * atr:
                continue
        else:
            continue

        entry = float(bars[i + 1]['o']) if i + 1 < len(bars) else float(bar['c'])
        stop = rot_low - TICK_SIZE

        t1 = rot_high + rot_range
        t2_level = _nearest_level_above(t1, levels)
        t2 = t2_level if t2_level is not None else t1 + rot_range

        seq_bars = list(range(rot_start, i + 1))
        delta_seq = []
        for si in seq_bars:
            d_val = bars[si].get('delta')
            delta_seq.append(float(d_val) if d_val is not None else 0.0)

        return {
            "setup_id": "ROTATION_BREAK",
            "direction": "LONG",
            "trigger_idx": i,
            "trigger_il": str(bars[i].get('t', ''))[:5],
            "entry": round(entry, 2),
            "stop": round(stop, 2),
            "t1": round(t1, 2),
            "t2": round(t2, 2),
            "sequence_bars": seq_bars,
            "location": f"rotation {rot_low:.2f}-{rot_high:.2f}",
            "evidence": {
                "delta_seq": delta_seq,
                "delta_trigger": trigger_delta,
                "vol_ratio_trigger": round(trigger_vol_ratio, 4),
                "absorption": False,
            },
        }

    return None


# ---------------------------------------------------------------------------
# Main detection function
# ---------------------------------------------------------------------------
def detect_setups(bars_with_delta: List[Dict], levels: Dict,
                  params: Dict) -> List[Dict]:
    """Detect all multi-bar setups.

    Args:
        bars_with_delta: List of bar dicts with keys:
            il (HH:MM), open, high, low, close, volume, delta
        levels: Dict with keys:
            pd_vah, pd_val, pd_poc, ib_high, ib_low,
            developing_vah, developing_val
        params: Parameter overrides (merged with DEFAULT_PARAMS)

    Returns:
        List of SetupHit dicts.
    """
    # Normalize bar keys if needed (support both 'o'/'h'/'l'/'c' and full names)
    normalized = []
    for b in bars_with_delta:
        nb = dict(b)
        if 'open' in nb and 'o' not in nb:
            nb['o'] = nb['open']
        if 'high' in nb and 'h' not in nb:
            nb['h'] = nb['high']
        if 'low' in nb and 'l' not in nb:
            nb['l'] = nb['low']
        if 'close' in nb and 'c' not in nb:
            nb['c'] = nb['close']
        if 'volume' in nb and 'v' not in nb:
            nb['v'] = nb['volume']
        if 'il' in nb and 't' not in nb:
            nb['t'] = nb['il'] + ':00'
        normalized.append(nb)

    hits: List[Dict] = []
    hits.extend(_detect_dbl_bottom_abs(normalized, levels, params))
    hits.extend(_detect_rotation_break(normalized, levels, params))

    # Deduplicate: same setup_id + direction + trigger_idx
    seen = set()
    deduped = []
    for h in hits:
        key = (h['setup_id'], h['direction'], h['trigger_idx'])
        if key not in seen:
            seen.add(key)
            deduped.append(h)

    return sorted(deduped, key=lambda h: h['trigger_idx'])


# ---------------------------------------------------------------------------
# $/trade calculation (simplified from oracle_engine)
# ---------------------------------------------------------------------------
def compute_dollar_per_trade(bars: List[Dict], hit: Dict) -> Optional[Dict]:
    """Compute $/trade for a setup hit using walk-forward."""
    i = hit['trigger_idx']
    if i + 1 >= len(bars):
        return None

    direction = hit['direction']
    entry = hit['entry']
    stop = hit['stop']
    t1 = hit['t1']
    t2 = hit['t2']
    risk_pts = abs(entry - stop)

    if risk_pts <= 0:
        return {'pnl_usd': 0.0, 'events': [], 'skip': True}

    n = min(5, int(225.0 // (TICK_USD * risk_pts)))
    if n < 3:
        return {'pnl_usd': 0.0, 'events': [], 'skip': True, 'reason': 'size<3'}

    current_stop = stop
    be_activated = False
    targets = [t1, t2]
    resolved = [False, False]
    results = []

    for j in range(i + 2, len(bars)):
        hi, lo = bars[j]['h'], bars[j]['l']
        for c_idx in range(2):
            if resolved[c_idx]:
                continue
            t = targets[c_idx]
            if direction == 'SHORT':
                hit_t = lo <= t
                hit_s = hi >= current_stop
            else:
                hit_t = hi >= t
                hit_s = lo <= current_stop
            if hit_t and hit_s:
                results.append(('AMBIG', 0.0))
                resolved[c_idx] = True
            elif hit_t:
                pts = abs(t - entry)
                results.append((f'T{c_idx + 1}', pts))
                resolved[c_idx] = True
                if c_idx == 0 and not be_activated:
                    be_activated = True
                    current_stop = entry
            elif hit_s:
                pts = -abs(entry - current_stop)
                results.append(('STOP', pts))
                resolved[c_idx] = True
        if all(resolved):
            break

    if bars:
        last_close = float(bars[-1]['c'])
        for c_idx in range(2):
            if not resolved[c_idx]:
                if direction == 'SHORT':
                    pts = entry - last_close
                else:
                    pts = last_close - entry
                results.append(('EOD', pts))

    total_pts = sum(pts for ev, pts in results if ev != 'AMBIG')
    total_usd = total_pts * TICK_USD - COMMISSION_RT * 2
    return {
        'pnl_usd': round(total_usd, 2),
        'events': results,
        'skip': False,
        'n': n,
    }


# ---------------------------------------------------------------------------
# Session analysis pipeline
# ---------------------------------------------------------------------------
def analyze_session(session_bars: List[Dict], pd_levels: Optional[Dict],
                    params: Dict) -> Tuple[List[Dict], Dict]:
    """Analyze a single session for setups.

    Returns (hits, levels_used).
    """
    if len(session_bars) < 15:
        return [], {}

    # Compute IB
    ib = compute_ib(session_bars)

    # Compute developing VA at the end (for reference)
    dev_va = compute_developing_va(session_bars, len(session_bars) - 1)

    # Build levels dict
    levels: Dict[str, Optional[float]] = {}
    if pd_levels:
        levels.update(pd_levels)
    levels.update(ib)
    if dev_va:
        levels['developing_vah'] = dev_va.get('vah')
        levels['developing_val'] = dev_va.get('val')

    hits = detect_setups(session_bars, levels, params)

    # Compute $/trade for each hit
    for h in hits:
        dollar = compute_dollar_per_trade(session_bars, h)
        if dollar:
            h['pnl'] = dollar

    return hits, levels


def analyze_all(session_date: Optional[str] = None,
                params: Optional[Dict] = None) -> Tuple[List[Dict], Dict]:
    """Run setup detection on all clean sessions or a single session.

    Returns (all_hits, summary).
    """
    if params is None:
        params = {}

    bars_raw = load_bars(session_date)
    by_day: Dict[str, List[Dict]] = collections.defaultdict(list)
    for b in bars_raw:
        by_day[str(b['d'])].append(b)
    days = sorted(by_day)

    exc = EXC | ROLL_DATES

    all_hits: List[Dict] = []
    prev_day_va: Optional[Dict] = None

    for d in days:
        bs = by_day[d]
        if d in exc and session_date is None:
            # Still compute VA for next day
            if len(bs) >= 10:
                va = compute_developing_va(bs, len(bs) - 1)
                if va:
                    prev_day_va = {
                        'pd_vah': va['vah'],
                        'pd_val': va['val'],
                        'pd_poc': va['poc'],
                    }
            continue

        if len(bs) < 15:
            continue

        # Try loading previous day from DB first
        pd_levels = load_previous_day_levels(d)
        if pd_levels is None and prev_day_va is not None:
            pd_levels = prev_day_va

        hits, levels = analyze_session(bs, pd_levels, params)

        for h in hits:
            h['session'] = d

        all_hits.extend(hits)

        # Update prev_day VA for next session
        if len(bs) >= 10:
            va = compute_developing_va(bs, len(bs) - 1)
            if va:
                prev_day_va = {
                    'pd_vah': va['vah'],
                    'pd_val': va['val'],
                    'pd_poc': va['poc'],
                }

    # Build summary
    summary = _build_summary(all_hits)
    return all_hits, summary


def _build_summary(hits: List[Dict]) -> Dict:
    """Build summary table per setup."""
    by_setup: Dict[str, List[Dict]] = collections.defaultdict(list)
    for h in hits:
        by_setup[h['setup_id']].append(h)

    summary = {'total_hits': len(hits), 'setups': {}}
    for sid, setup_hits in by_setup.items():
        pnls = [h['pnl']['pnl_usd'] for h in setup_hits
                if 'pnl' in h and h['pnl'] and not h['pnl'].get('skip')]
        long_n = sum(1 for h in setup_hits if h['direction'] == 'LONG')
        short_n = sum(1 for h in setup_hits if h['direction'] == 'SHORT')
        phases = collections.Counter(
            classify_phase(h['trigger_idx']) for h in setup_hits)

        summary['setups'][sid] = {
            'N': len(setup_hits),
            'LONG': long_n,
            'SHORT': short_n,
            'phases': dict(phases),
            'avg_pnl_usd': round(statistics.mean(pnls), 2) if pnls else 0.0,
            'total_pnl_usd': round(sum(pnls), 2) if pnls else 0.0,
            'n_trades': len(pnls),
        }

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def print_report(hits: List[Dict], summary: Dict) -> None:
    """Print summary table to stdout."""
    print(f"\nSetup Engine Report — T-411")
    print(f"Total hits: {summary['total_hits']}")

    for sid, s in summary.get('setups', {}).items():
        print(f"\n  {sid}:")
        print(f"    N={s['N']}  LONG={s['LONG']}  SHORT={s['SHORT']}")
        print(f"    phases: {s['phases']}")
        print(f"    trades={s['n_trades']}  avg $/trade={s['avg_pnl_usd']:.2f}"
              f"  total={s['total_pnl_usd']:.2f}")

    # Detail table
    if hits:
        print(f"\n{'session':12} {'setup':20} {'dir':5} {'trigger':6} "
              f"{'entry':>9} {'stop':>9} {'T1':>9} {'T2':>9} {'$/trade':>10}")
        print("-" * 95)
        for h in hits:
            pnl = h.get('pnl', {})
            pnl_str = f"{pnl.get('pnl_usd', 0):.2f}" if pnl and not pnl.get('skip') else 'skip'
            print(f"{h.get('session', '?'):12} {h['setup_id']:20} "
                  f"{h['direction']:5} {h['trigger_il']:6} "
                  f"{h['entry']:9.2f} {h['stop']:9.2f} "
                  f"{h['t1']:9.2f} {h['t2']:9.2f} {pnl_str:>10}")


def main():
    parser = argparse.ArgumentParser(description="F17 Setup Engine — T-411")
    parser.add_argument("--session", type=str, default=None,
                        help="Single session date (YYYY-MM-DD)")
    parser.add_argument("--validate", action="store_true",
                        help="Run oracle_validate on hits")
    args = parser.parse_args()

    hits, summary = analyze_all(session_date=args.session)

    # Write output
    out_dir = os.path.join(_ROOT, 'harness_out', 'setups')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'hits.json')
    with open(out_path, 'w') as f:
        json.dump({'hits': hits, 'summary': summary}, f, default=str, indent=2)
    print(f"Wrote {out_path} ({len(hits)} hits)")

    print_report(hits, summary)

    if args.validate and hits:
        print("\n[validate mode requested — integration with oracle_validate TBD]")


if __name__ == '__main__':
    main()
