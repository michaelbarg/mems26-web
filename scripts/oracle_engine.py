#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""oracle_engine.py — F14 · T-408 — Oracle as discovery engine in the nightly scan.

Comprehensive, standalone oracle analysis: labels every RTH 5-min bar,
computes MFE/MAE, causal conditions (head-shoulders, cup-handle, pullback,
break-from-value-area, zone-vs-developing-VA), $/trade per condition,
phase/day_type splits.

CLI:
    python3 scripts/oracle_engine.py                          # all clean sessions
    python3 scripts/oracle_engine.py --session 2026-09-15     # one session
    python3 scripts/oracle_engine.py --horizon 6 --target-atr 2.0  # sweep params

# NOTE: for CPU courtesy, run with nice -n 15 during RTH.
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
# Excluded sessions (from oracle_study + SUSPECT/ROLL from gap_analysis)
# ---------------------------------------------------------------------------
EXC: Set[str] = {
    '2026-06-09', '2026-06-10', '2026-06-11', '2026-06-12',
    '2026-06-17', '2026-06-18', '2026-06-19', '2026-06-26',
    '2026-07-10', '2026-07-24', '2026-07-28', '2026-07-29',
    '2026-09-16', '2026-09-17',
}

# Roll dates (3rd Friday quarter-month ± 2 trading days)
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
# Constants
# ---------------------------------------------------------------------------
TICK_SIZE = 0.25
TICK_USD = 5.0            # $5 per point per contract (MES)
SLIPPAGE_PTS = 0.50       # 1 tick each way = 0.25 * 2
COMMISSION_RT = 1.30      # $1.30 per round-turn per contract
RISK_BUDGET = 225.0
MIN_STOP_PTS = 5.0


def size_for(risk_pts: float) -> int:
    """n = min(5, floor(225 / (5 * risk))); n < 3 -> skip (return 0)."""
    if risk_pts <= 0:
        return 0
    n = min(5, int(RISK_BUDGET // (TICK_USD * risk_pts)))
    return n if n >= 3 else 0


# ---------------------------------------------------------------------------
# Day-type classifier (from gap_analysis)
# ---------------------------------------------------------------------------
def classify_day_type_from_bars(bars: List[Dict]) -> str:
    """Simplified day-type from IB width vs range."""
    if not bars or len(bars) < 7:
        return "UNRESOLVED"
    ib_bars = bars[:6]
    ib_high = max(b['h'] for b in ib_bars)
    ib_low = min(b['l'] for b in ib_bars)
    ib_width = ib_high - ib_low
    if ib_width <= 0:
        return "UNRESOLVED"
    session_high = max(b['h'] for b in bars)
    session_low = min(b['l'] for b in bars)
    session_range = session_high - session_low
    session_close = bars[-1]['c']
    ext_up = max(0.0, session_high - ib_high)
    ext_down = max(0.0, ib_low - session_low)
    if session_range > 0:
        close_pos = (session_close - session_low) / session_range
    else:
        close_pos = 0.5
    if session_range > 2.0 * ib_width:
        if close_pos > 0.7 or close_pos < 0.3:
            return "Trend"
    if ext_up > ib_width and ext_down <= ib_width * 0.5:
        return "Variation"
    if ext_down > ib_width and ext_up <= ib_width * 0.5:
        return "Variation"
    if session_range < 1.5 * ib_width:
        return "Normal"
    return "UNRESOLVED"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_bars(session_date: Optional[str] = None) -> List[Dict]:
    """Load RTH 5-min bars with delta from DB."""
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
        LEFT JOIN (SELECT DISTINCT ON (ts) ts, delta
                   FROM v9_bars_cumulative_delta
                   ORDER BY ts, created_at DESC) cd ON cd.ts = b.ts
        WHERE {where_clause}
          AND (b.ts AT TIME ZONE 'Asia/Jerusalem')::time BETWEEN '16:30' AND '23:00'
        ORDER BY b.ts""",
        params
    )


def load_previous_day_context(session_dates: List[str]) -> Dict[str, Dict]:
    """Load previous-day VAL/VAH for break_from_value_area condition.

    Returns {date_str: {val: float, vah: float, poc: float}}.
    """
    # For each session, compute a simplified VA from that session's bars,
    # then the NEXT session uses it as pd_ctx.
    return {}  # Populated during processing


# ---------------------------------------------------------------------------
# ATR computation (causal, on closed bars)
# ---------------------------------------------------------------------------
def compute_atr(bars: List[Dict], idx: int, period: int = 14) -> Optional[float]:
    """Compute ATR at bar index idx using only bars [0..idx] (causal)."""
    if idx < period:
        return None
    trs = []
    for k in range(idx - period + 1, idx + 1):
        tr = max(
            bars[k]['h'] - bars[k]['l'],
            abs(bars[k]['h'] - bars[k - 1]['c']),
            abs(bars[k]['l'] - bars[k - 1]['c']),
        )
        trs.append(tr)
    return sum(trs) / len(trs)


# ---------------------------------------------------------------------------
# Labeling: GOOD_SHORT / GOOD_LONG / BAD / AMBIG / NONE
# ---------------------------------------------------------------------------
def label_bar(bars: List[Dict], i: int, atr: float,
              K: int = 12, target_mult: float = 1.5,
              stop_mult: float = 1.0) -> Tuple[str, str]:
    """Label bar i by what happens in the next K bars.

    Returns (label_short, label_long).
    """
    c = bars[i]['c']
    T = max(8.0, target_mult * atr)
    S = max(5.0, stop_mult * atr)
    res_s = res_l = 'NONE'
    for j in range(i + 1, min(i + 1 + K, len(bars))):
        hi, lo = bars[j]['h'], bars[j]['l']
        if res_s == 'NONE':
            if hi >= c + S and lo <= c - T:
                res_s = 'AMBIG'
            elif hi >= c + S:
                res_s = 'BAD'
            elif lo <= c - T:
                res_s = 'GOOD'
        if res_l == 'NONE':
            if lo <= c - S and hi >= c + T:
                res_l = 'AMBIG'
            elif lo <= c - S:
                res_l = 'BAD'
            elif hi >= c + T:
                res_l = 'GOOD'
        if res_s != 'NONE' and res_l != 'NONE':
            break
    return res_s, res_l


# ---------------------------------------------------------------------------
# MFE / MAE within K-bar window
# ---------------------------------------------------------------------------
def compute_mfe_mae(bars: List[Dict], i: int, K: int, direction: str
                    ) -> Tuple[float, float]:
    """Compute MFE (Maximum Favorable Excursion) and MAE (Maximum Adverse
    Excursion) for bar i within the next K bars.

    direction: 'SHORT' or 'LONG'
    Returns (mfe, mae) in points.
    """
    c = bars[i]['c']
    mfe = 0.0
    mae = 0.0
    for j in range(i + 1, min(i + 1 + K, len(bars))):
        hi, lo = bars[j]['h'], bars[j]['l']
        if direction == 'SHORT':
            mfe = max(mfe, c - lo)
            mae = max(mae, hi - c)
        else:  # LONG
            mfe = max(mfe, hi - c)
            mae = max(mae, c - lo)
    return round(mfe, 2), round(mae, 2)


# ---------------------------------------------------------------------------
# Causal conditions
# ---------------------------------------------------------------------------

def _vol_ratio(bar: Dict, minute_key: str, prior_vol: Dict) -> Optional[float]:
    pv = prior_vol.get(minute_key, [])
    if len(pv) < 5:
        return None
    med = statistics.median(pv[-10:])
    if med <= 0:
        return None
    return float(bar['v']) / med


def _delta_ratio(bar: Dict, deltas: List[float]) -> Optional[float]:
    dl = bar['delta']
    if dl is None or len(deltas) < 6:
        return None
    med_d = statistics.median(deltas[:-1])
    if not med_d or med_d == 0:
        return None
    return float(dl) / med_d


def detect_head_shoulders_short(bars: List[Dict], i: int, atr: float) -> bool:
    """3 highs in 15-bar window, middle is highest, neckline broken by close."""
    win = bars[max(0, i - 15):i + 1]
    if len(win) < 7:
        return False
    # Find 3 local highs: split window into thirds
    third = len(win) // 3
    if third < 2:
        return False
    seg1 = win[:third]
    seg2 = win[third:2 * third]
    seg3 = win[2 * third:]

    h1_idx = max(range(len(seg1)), key=lambda k: seg1[k]['h'])
    h2_idx = max(range(len(seg2)), key=lambda k: seg2[k]['h'])
    h3_idx = max(range(len(seg3)), key=lambda k: seg3[k]['h'])

    h1, h2, h3 = seg1[h1_idx]['h'], seg2[h2_idx]['h'], seg3[h3_idx]['h']

    # Head (middle) must be highest
    if not (h2 > h1 and h2 > h3):
        return False
    # Shoulders roughly equal (within 1 ATR)
    if abs(h1 - h3) > atr:
        return False

    # Neckline: min low between left-shoulder and right-shoulder
    global_h1_idx = h1_idx
    global_h3_idx = 2 * third + h3_idx
    neckline_bars = win[global_h1_idx:global_h3_idx + 1]
    if not neckline_bars:
        return False
    neckline = min(b['l'] for b in neckline_bars)

    # Current close breaks neckline
    return bars[i]['c'] < neckline


def detect_head_shoulders_long(bars: List[Dict], i: int, atr: float) -> bool:
    """Mirror of short: 3 lows, middle lowest, neckline broken upward."""
    win = bars[max(0, i - 15):i + 1]
    if len(win) < 7:
        return False
    third = len(win) // 3
    if third < 2:
        return False
    seg1 = win[:third]
    seg2 = win[third:2 * third]
    seg3 = win[2 * third:]

    l1_idx = min(range(len(seg1)), key=lambda k: seg1[k]['l'])
    l2_idx = min(range(len(seg2)), key=lambda k: seg2[k]['l'])
    l3_idx = min(range(len(seg3)), key=lambda k: seg3[k]['l'])

    l1, l2, l3 = seg1[l1_idx]['l'], seg2[l2_idx]['l'], seg3[l3_idx]['l']

    if not (l2 < l1 and l2 < l3):
        return False
    if abs(l1 - l3) > atr:
        return False

    global_l1_idx = l1_idx
    global_l3_idx = 2 * third + l3_idx
    neckline_bars = win[global_l1_idx:global_l3_idx + 1]
    if not neckline_bars:
        return False
    neckline = max(b['h'] for b in neckline_bars)

    return bars[i]['c'] > neckline


def detect_cup_handle_long(bars: List[Dict], i: int, atr: float) -> bool:
    """Low point at least 8 bars back, handle <=4 bars, breakout."""
    if i < 10:
        return False
    win = bars[max(0, i - 20):i + 1]
    if len(win) < 10:
        return False

    # Find the cup low (at least 8 bars back from current)
    cup_region = win[:len(win) - 4]
    if len(cup_region) < 8:
        return False
    cup_low_idx = min(range(len(cup_region)), key=lambda k: cup_region[k]['l'])
    cup_low = cup_region[cup_low_idx]['l']

    # Left rim and right rim should be above cup low
    left_rim = max(b['h'] for b in win[:cup_low_idx + 1]) if cup_low_idx > 0 else win[0]['h']
    # Handle region: last 4 bars
    handle = win[-4:]
    handle_low = min(b['l'] for b in handle)

    # Handle should not go below cup low
    if handle_low < cup_low:
        return False
    # Handle retrace should be shallow (< 50% of cup depth)
    right_rim = max(b['h'] for b in win[cup_low_idx:len(win) - 4]) if cup_low_idx < len(win) - 4 else cup_low
    cup_depth = right_rim - cup_low
    if cup_depth <= 0:
        return False
    handle_retrace = right_rim - handle_low
    if handle_retrace > 0.5 * cup_depth:
        return False

    # Breakout: close above right rim
    return bars[i]['c'] > right_rim


def detect_pullback_in_trend(bars: List[Dict], i: int, atr: float,
                             bse: int, move_open: float,
                             close_pos: float, vol_ratio: Optional[float],
                             direction: str) -> bool:
    """bars_since_extreme 2-6, retrace 30-60% of the leg, close in correct
    third, vol_ratio >= 1.0.
    """
    if not (2 <= bse <= 6):
        return False
    if vol_ratio is None or vol_ratio < 1.0:
        return False

    if direction == 'SHORT':
        if not (close_pos <= 0.33):
            return False
        if move_open > -1.0:
            return False
    else:
        if not (close_pos >= 0.67):
            return False
        if move_open < 1.0:
            return False

    # Check retrace: from the extreme to current close vs the full leg
    extreme_idx = i - bse
    if extreme_idx < 1:
        return False

    if direction == 'SHORT':
        extreme_price = bars[extreme_idx]['l']
        leg_start = bars[0]['o']  # session open
        leg_size = leg_start - extreme_price
        if leg_size <= 0:
            return False
        retrace = bars[i]['c'] - extreme_price
    else:
        extreme_price = bars[extreme_idx]['h']
        leg_start = bars[0]['o']
        leg_size = extreme_price - leg_start
        if leg_size <= 0:
            return False
        retrace = extreme_price - bars[i]['c']

    retrace_pct = retrace / leg_size if leg_size > 0 else 0
    return 0.30 <= retrace_pct <= 0.60


def compute_developing_va(bars: List[Dict], i: int) -> Dict[str, float]:
    """Compute simplified developing VA from today's bars up to index i.

    POC = most common close (rounded to 0.25), VAH/VAL = 70% range around POC.
    """
    if i < 3:
        return {}
    closes = [round(b['c'] / TICK_SIZE) * TICK_SIZE for b in bars[:i + 1]]
    if not closes:
        return {}

    # POC = mode of closes (rounded to nearest tick)
    counter = collections.Counter(closes)
    poc = counter.most_common(1)[0][0]

    # Sort all prices, find 70% range centered on POC
    all_prices = sorted(closes)
    n = len(all_prices)
    va_count = max(1, int(n * 0.70))

    # Find the window of va_count prices that is closest to containing POC
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
    val = va_prices[0]
    vah = va_prices[-1]
    return {'poc': poc, 'val': val, 'vah': vah}


def detect_break_from_value_area(bars: List[Dict], i: int,
                                 pd_ctx: Optional[Dict],
                                 delta: Optional[float]) -> Tuple[bool, bool]:
    """Close crosses previous-day VAL/VAH with confirming delta.

    Returns (break_short, break_long).
    """
    if pd_ctx is None or not pd_ctx:
        return False, False
    val = pd_ctx.get('val')
    vah = pd_ctx.get('vah')
    if val is None or vah is None:
        return False, False

    c = bars[i]['c']
    # Need confirming delta
    has_neg_delta = delta is not None and float(delta) < 0
    has_pos_delta = delta is not None and float(delta) > 0

    break_short = c < val and has_neg_delta
    break_long = c > vah and has_pos_delta
    return break_short, break_long


def classify_zone_vs_developing_va(price: float, dev_va: Dict) -> str:
    """Classify price relative to developing VA."""
    if not dev_va:
        return 'UNKNOWN'
    vah = dev_va.get('vah', 0)
    val = dev_va.get('val', 0)
    if price > vah:
        return 'ABOVE_VA'
    elif price < val:
        return 'BELOW_VA'
    else:
        return 'IN_VA'


# ---------------------------------------------------------------------------
# $/trade walk-forward calculation
# ---------------------------------------------------------------------------
def compute_dollar_per_trade(bars: List[Dict], i: int, atr: float,
                             direction: str) -> Optional[Dict]:
    """Walk-forward $/trade for a signal at bar i.

    Entry: open of next bar + slippage.
    Stop: 1*ATR beyond signal bar extreme (min 5 pts).
    T1: 1.5*ATR, T2: 2.5*ATR, BE after T1.
    EOD close at session end. AMBIG not attributed.
    """
    if i + 1 >= len(bars):
        return None

    entry_bar = bars[i + 1]
    entry_raw = float(entry_bar['o'])

    if direction == 'SHORT':
        entry = entry_raw - SLIPPAGE_PTS / 2  # worse fill for short
        stop_raw = max(MIN_STOP_PTS, 1.0 * atr)
        stop = entry + stop_raw
        t1 = entry - 1.5 * atr
        t2 = entry - 2.5 * atr
    else:
        entry = entry_raw + SLIPPAGE_PTS / 2
        stop_raw = max(MIN_STOP_PTS, 1.0 * atr)
        stop = entry - stop_raw
        t1 = entry + 1.5 * atr
        t2 = entry + 2.5 * atr

    risk_pts = abs(entry - stop)
    n = size_for(risk_pts)
    if n == 0:
        return {'skip': True, 'reason': 'size<3', 'n': 0, 'pnl_usd': 0.0}

    # Walk forward: 2 contracts, T1 and T2
    current_stop = stop
    be_activated = False
    results = []  # (event, pts)

    # Contract 1 -> T1, Contract 2 -> T2
    targets = [t1, t2]
    resolved = [False, False]

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
                    current_stop = entry  # BE
            elif hit_s:
                pts = -abs(entry - current_stop)
                results.append(('STOP', pts))
                resolved[c_idx] = True
        if all(resolved):
            break

    # EOD for unresolved
    if bars:
        last_close = float(bars[-1]['c'])
        for c_idx in range(2):
            if not resolved[c_idx]:
                if direction == 'SHORT':
                    pts = entry - last_close
                else:
                    pts = last_close - entry
                results.append(('EOD', pts))
                resolved[c_idx] = True

    total_pts = sum(pts for ev, pts in results if ev != 'AMBIG')
    total_usd = total_pts * TICK_USD - COMMISSION_RT * 2  # 2 contracts
    # Slippage already embedded in entry

    return {
        'skip': False,
        'n': n,
        'entry': round(entry, 2),
        'stop': round(stop, 2),
        't1': round(t1, 2),
        't2': round(t2, 2),
        'risk_pts': round(risk_pts, 2),
        'events': results,
        'total_pts': round(total_pts, 2),
        'pnl_usd': round(total_usd, 2),
    }


# ---------------------------------------------------------------------------
# Main analysis pipeline
# ---------------------------------------------------------------------------
def analyze_all(session_date: Optional[str] = None,
                K: int = 12,
                target_mult: float = 1.5,
                stop_mult: float = 1.0) -> Tuple[List[Dict], Dict]:
    """Run the full oracle analysis. Returns (rows, summary_dict)."""

    bars_raw = load_bars(session_date)
    by_day: Dict[str, List[Dict]] = collections.defaultdict(list)
    for b in bars_raw:
        by_day[str(b['d'])].append(b)
    days = sorted(by_day)

    # Build full exclusion set
    exc = EXC | ROLL_DATES

    rows: List[Dict] = []
    prior_vol: Dict[str, List[float]] = {}
    prev_day_va: Optional[Dict] = None  # pd_ctx for break_from_value_area

    for d in days:
        bs = by_day[d]
        if d in exc or len(bs) < 40:
            # Still accumulate vol data
            for b in bs:
                prior_vol.setdefault(str(b['t'])[:5], []).append(float(b['v'] or 0))
            continue

        day_type = classify_day_type_from_bars(bs)
        deltas: List[float] = []

        for i, b in enumerate(bs):
            atr = compute_atr(bs, i)
            dl = b['delta']
            if dl is not None:
                deltas.append(abs(float(dl)))

            if atr is None or i < 5 or i > len(bs) - 3:
                continue

            m = str(b['t'])[:5]
            vr = _vol_ratio(b, m, prior_vol)
            dr = _delta_ratio(b, deltas)
            rng = b['h'] - b['l']
            cp = ((b['c'] - b['l']) / rng) if rng > 0 else 0.5

            # Structure break with varying windows (F16 Fix 1)
            prev5 = bs[i - 5:i]
            break_dn = b['c'] < min(x['l'] for x in prev5)
            break_up = b['c'] > max(x['h'] for x in prev5)

            # Pre-compute break for window 3, 5, 8
            break_dn_w3 = b['c'] < min(x['l'] for x in bs[max(0, i - 3):i]) if i >= 3 else False
            break_dn_w5 = break_dn  # already computed above
            break_dn_w8 = b['c'] < min(x['l'] for x in bs[max(0, i - 8):i]) if i >= 8 else False
            break_up_w3 = b['c'] > max(x['h'] for x in bs[max(0, i - 3):i]) if i >= 3 else False
            break_up_w5 = break_up
            break_up_w8 = b['c'] > max(x['h'] for x in bs[max(0, i - 8):i]) if i >= 8 else False

            # Bars since session extreme
            hi_i = max(range(i + 1), key=lambda k: bs[k]['h'])
            lo_i = min(range(i + 1), key=lambda k: bs[k]['l'])
            bsh = i - hi_i
            bsl = i - lo_i

            # Move from open in ATR
            move_open = (b['c'] - bs[0]['o']) / atr

            # Double bottom/top (from oracle_study) — with varying tolerance/min_dist (F16 Fix 1)
            win = bs[max(0, i - 15):i + 1]
            dbl_b = dbl_t = False
            lows = sorted(range(len(win)), key=lambda k: win[k]['l'])[:2]
            highs = sorted(range(len(win)), key=lambda k: -win[k]['h'])[:2]
            if len(win) >= 8 and abs(lows[0] - lows[1]) >= 3 and abs(win[lows[0]]['l'] - win[lows[1]]['l']) <= 0.3 * atr:
                neck = max(x['h'] for x in win[min(lows):max(lows) + 1])
                dbl_b = b['c'] > neck and (len(win) - 1 - max(lows)) <= 3
            if len(win) >= 8 and abs(highs[0] - highs[1]) >= 3 and abs(win[highs[0]]['h'] - win[highs[1]]['h']) <= 0.3 * atr:
                neck = min(x['l'] for x in win[min(highs):max(highs) + 1])
                dbl_t = b['c'] < neck and (len(win) - 1 - max(highs)) <= 3

            # Pre-compute double bottom/top variants with varying tolerance and min_dist
            dbl_variants = {}
            for tol_key, tol_mult in [('t02', 0.2), ('t03', 0.3), ('t05', 0.5)]:
                for dist_key, min_dist in [('d3', 3), ('d5', 5)]:
                    # Double bottom
                    db_key = f'dbl_b_{tol_key}_{dist_key}'
                    db_val = False
                    if len(win) >= 8 and abs(lows[0] - lows[1]) >= min_dist and abs(win[lows[0]]['l'] - win[lows[1]]['l']) <= tol_mult * atr:
                        neck_b = max(x['h'] for x in win[min(lows):max(lows) + 1])
                        db_val = b['c'] > neck_b and (len(win) - 1 - max(lows)) <= 3
                    dbl_variants[db_key] = db_val
                    # Double top
                    dt_key = f'dbl_t_{tol_key}_{dist_key}'
                    dt_val = False
                    if len(win) >= 8 and abs(highs[0] - highs[1]) >= min_dist and abs(win[highs[0]]['h'] - win[highs[1]]['h']) <= tol_mult * atr:
                        neck_t = min(x['l'] for x in win[min(highs):max(highs) + 1])
                        dt_val = b['c'] < neck_t and (len(win) - 1 - max(highs)) <= 3
                    dbl_variants[dt_key] = dt_val

            # New F14 conditions
            hs_short = detect_head_shoulders_short(bs, i, atr)
            hs_long = detect_head_shoulders_long(bs, i, atr)
            cup_handle = detect_cup_handle_long(bs, i, atr)

            pullback_short = detect_pullback_in_trend(
                bs, i, atr, bsl, move_open, cp, vr, 'SHORT')
            pullback_long = detect_pullback_in_trend(
                bs, i, atr, bsh, move_open, cp, vr, 'LONG')

            # Break from previous-day value area
            bfva_short, bfva_long = detect_break_from_value_area(
                bs, i, prev_day_va, dl)

            # Developing VA zone classification
            dev_va = compute_developing_va(bs, i)
            zone = classify_zone_vs_developing_va(float(b['c']), dev_va)

            # Labels
            ls, ll = label_bar(bs, i, atr, K=K,
                               target_mult=target_mult, stop_mult=stop_mult)

            # MFE/MAE for GOOD bars
            mfe_s, mae_s, mfe_l, mae_l = 0.0, 0.0, 0.0, 0.0
            if ls == 'GOOD':
                mfe_s, mae_s = compute_mfe_mae(bs, i, K, 'SHORT')
            if ll == 'GOOD':
                mfe_l, mae_l = compute_mfe_mae(bs, i, K, 'LONG')

            # Phase
            ph = 'A' if i < 3 else 'B' if i < 12 else 'C' if i < 54 else 'D'

            row = dict(
                d=d, t=m, bar_idx=i, ph=ph, day_type=day_type,
                atr=round(atr, 2),
                vr=round(vr, 4) if vr is not None else None,
                dr=round(dr, 4) if dr is not None else None,
                cp=round(cp, 4),
                break_dn=break_dn, break_up=break_up,
                # F16: pre-computed break variants by window
                break_dn_w3=break_dn_w3, break_dn_w5=break_dn_w5, break_dn_w8=break_dn_w8,
                break_up_w3=break_up_w3, break_up_w5=break_up_w5, break_up_w8=break_up_w8,
                bsh=bsh, bsl=bsl,
                move_open=round(move_open, 4),
                dbl_b=dbl_b, dbl_t=dbl_t,
                # F16: pre-computed double variants by tolerance/min_dist
                **dbl_variants,
                hs_short=hs_short, hs_long=hs_long,
                cup_handle=cup_handle,
                pullback_short=pullback_short, pullback_long=pullback_long,
                bfva_short=bfva_short, bfva_long=bfva_long,
                zone=zone,
                ls=ls, ll=ll,
                mfe_s=mfe_s, mae_s=mae_s,
                mfe_l=mfe_l, mae_l=mae_l,
            )
            rows.append(row)

        # Build pd_ctx for next day from this session's VA
        if len(bs) >= 10:
            dev_va_full = compute_developing_va(bs, len(bs) - 1)
            prev_day_va = dev_va_full if dev_va_full else None

        # Accumulate vol for future sessions
        for b in bs:
            prior_vol.setdefault(str(b['t'])[:5], []).append(float(b['v'] or 0))

    # Build condition table and $/trade
    summary = _build_summary(rows, K, target_mult, stop_mult, by_day, exc)
    return rows, summary


def _build_summary(rows: List[Dict], K: int, target_mult: float,
                   stop_mult: float, by_day: Dict, exc: Set) -> Dict:
    """Compute lift table and $/trade for all conditions."""

    def rate(sel, side):
        sub = [r for r in rows if sel(r)]
        lab = 'ls' if side == 'S' else 'll'
        g = sum(1 for r in sub if r[lab] == 'GOOD')
        b = sum(1 for r in sub if r[lab] == 'BAD')
        a = sum(1 for r in sub if r[lab] == 'AMBIG')
        n = len(sub)
        dec = g + b
        return n, (100 * g / dec if dec else 0), g, b, a

    base_s = rate(lambda r: True, 'S')
    base_l = rate(lambda r: True, 'L')

    conditions = {
        'break_dn': (lambda r: r['break_dn'], 'S'),
        'break_dn+delta<=-2': (lambda r: r['break_dn'] and r['dr'] is not None and r['dr'] <= -2, 'S'),
        'break_dn+delta+vol>=1.3': (lambda r: r['break_dn'] and r['dr'] is not None and r['dr'] <= -2 and r['vr'] and r['vr'] >= 1.3, 'S'),
        'break_dn+delta+vol+cp<=0.3': (lambda r: r['break_dn'] and r['dr'] is not None and r['dr'] <= -2 and r['vr'] and r['vr'] >= 1.3 and r['cp'] <= 0.3, 'S'),
        'break_dn+delta+vol+bsl>=2': (lambda r: r['break_dn'] and r['dr'] is not None and r['dr'] <= -2 and r['vr'] and r['vr'] >= 1.3 and r['bsl'] >= 2, 'S'),
        'break_dn_fresh_low_mo>=3atr': (lambda r: r['break_dn'] and r['bsl'] == 0 and r['move_open'] <= -3, 'S'),
        'pullback_short_classic': (lambda r: 2 <= r['bsl'] <= 6 and r['move_open'] <= -1.5 and r['cp'] <= 0.35, 'S'),
        'double_top': (lambda r: r['dbl_t'], 'S'),
        'head_shoulders_short': (lambda r: r['hs_short'], 'S'),
        'pullback_in_trend_short': (lambda r: r['pullback_short'], 'S'),
        'break_from_va_short': (lambda r: r['bfva_short'], 'S'),

        'break_up': (lambda r: r['break_up'], 'L'),
        'break_up+delta>=2': (lambda r: r['break_up'] and r['dr'] is not None and r['dr'] >= 2, 'L'),
        'break_up+delta+vol>=1.3': (lambda r: r['break_up'] and r['dr'] is not None and r['dr'] >= 2 and r['vr'] and r['vr'] >= 1.3, 'L'),
        'break_up+delta+vol+bsh>=2': (lambda r: r['break_up'] and r['dr'] is not None and r['dr'] >= 2 and r['vr'] and r['vr'] >= 1.3 and r['bsh'] >= 2, 'L'),
        'break_up_fresh_high_mo>=3atr': (lambda r: r['break_up'] and r['bsh'] == 0 and r['move_open'] >= 3, 'L'),
        'pullback_long_classic': (lambda r: 2 <= r['bsh'] <= 6 and r['move_open'] >= 1.5 and r['cp'] >= 0.65, 'L'),
        'double_bottom': (lambda r: r['dbl_b'], 'L'),
        'head_shoulders_long': (lambda r: r['hs_long'], 'L'),
        'cup_handle_long': (lambda r: r['cup_handle'], 'L'),
        'pullback_in_trend_long': (lambda r: r['pullback_long'], 'L'),
        'break_from_va_long': (lambda r: r['bfva_long'], 'L'),
    }

    # Compute $/trade per condition
    cond_results = {}
    for cname, (cfunc, side) in conditions.items():
        n, good_pct, G, B, A = rate(cfunc, side)
        base = base_s[1] if side == 'S' else base_l[1]
        lift = good_pct - base

        # $/trade: walk through matching rows
        dollar_trades = []
        direction = 'SHORT' if side == 'S' else 'LONG'
        matching = [r for r in rows if cfunc(r)]
        for r in matching:
            d = r['d']
            if d not in by_day:
                continue
            bs = by_day[d]
            atr = r['atr']
            bar_idx = r['bar_idx']
            result = compute_dollar_per_trade(bs, bar_idx, atr, direction)
            if result and not result.get('skip'):
                dollar_trades.append(result['pnl_usd'])

        avg_dollar = (sum(dollar_trades) / len(dollar_trades)
                      if dollar_trades else 0.0)

        cond_results[cname] = {
            'side': side,
            'N': n,
            'good_pct': round(good_pct, 1),
            'G': G, 'B': B, 'A': A,
            'lift': round(lift, 1),
            'dollar_trades': len(dollar_trades),
            'avg_dollar_per_trade': round(avg_dollar, 2),
        }

    return {
        'K': K,
        'target_mult': target_mult,
        'stop_mult': stop_mult,
        'total_bars': len(rows),
        'base_short': {'N': base_s[0], 'good_pct': round(base_s[1], 1),
                       'G': base_s[2], 'B': base_s[3], 'A': base_s[4]},
        'base_long': {'N': base_l[0], 'good_pct': round(base_l[1], 1),
                      'G': base_l[2], 'B': base_l[3], 'A': base_l[4]},
        'conditions': cond_results,
    }


def print_report(summary: Dict) -> None:
    """Print the lift table to stdout."""
    print(f"\nOracle Engine Report — K={summary['K']}, "
          f"target={summary['target_mult']}×ATR, "
          f"stop={summary['stop_mult']}×ATR")
    print(f"Total bars: {summary['total_bars']}")
    bs = summary['base_short']
    bl = summary['base_long']
    print(f"BASE  short: N={bs['N']} good={bs['good_pct']}% "
          f"(G{bs['G']}/B{bs['B']}/A{bs['A']})  "
          f"long: good={bl['good_pct']}% (G{bl['G']}/B{bl['B']})")

    conds = summary['conditions']
    sorted_conds = sorted(conds.items(), key=lambda x: x[1]['lift'], reverse=True)

    print(f"\n{'condition':48} {'side':4} {'N':>5} {'good%':>6} "
          f"{'lift':>6} {'$/trade':>10} {'n_trades':>8}")
    print("-" * 90)
    for cname, c in sorted_conds:
        print(f"{cname:48} {c['side']:4} {c['N']:5d} {c['good_pct']:6.1f} "
              f"{c['lift']:+6.1f} {c['avg_dollar_per_trade']:10.2f} "
              f"{c['dollar_trades']:8d}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="F14 Oracle Engine — T-408")
    parser.add_argument("--session", type=str, default=None,
                        help="Single session date (YYYY-MM-DD)")
    parser.add_argument("--horizon", type=int, default=12,
                        help="Lookahead horizon K (bars)")
    parser.add_argument("--target-atr", type=float, default=1.5,
                        help="Target multiplier of ATR")
    parser.add_argument("--stop-atr", type=float, default=1.0,
                        help="Stop multiplier of ATR")
    args = parser.parse_args()

    rows, summary = analyze_all(
        session_date=args.session,
        K=args.horizon,
        target_mult=args.target_atr,
        stop_mult=args.stop_atr,
    )

    # Write output
    out_dir = os.path.join(_ROOT, 'harness_out', 'oracle')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'oracle_v1.json')
    with open(out_path, 'w') as f:
        json.dump({'rows': rows, 'summary': summary}, f, default=str, indent=2)
    print(f"Wrote {out_path} ({len(rows)} bars)")

    print_report(summary)


if __name__ == '__main__':
    main()
