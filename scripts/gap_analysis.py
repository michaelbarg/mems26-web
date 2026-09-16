#!/usr/bin/env python3
"""Gap Analysis — "if we made 10 points and the range was 200, there were lots
of trades we missed."

For each RTH session (June–September 2026), decomposes the price range into
zigzag moves, classifies each move vs. actual live/shadow trades, and produces
a report showing where opportunities were missed and why.

CLI:
    python3 scripts/gap_analysis.py                          # all sessions
    python3 scripts/gap_analysis.py --session 2026-09-15 --verbose
    python3 scripts/gap_analysis.py --dry                    # one session, no file write
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Bootstrap: standalone script, load .env then backend imports
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from backend.env_loader import load_dotenv_file
load_dotenv_file(os.path.join(_ROOT, '.env'), override=False)

from backend.v9.db.read import read_all

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — fixed evaluation model (mirrors replay_admits.py)
# ---------------------------------------------------------------------------
TICK_USD = 5.0        # $5 per point per contract (MES)
RISK_BUDGET = 225.0   # maximum risk budget in $
RTH_START = "16:30"   # Israel time
RTH_END = "23:00"     # Israel time

# Import the evaluation model from replay_admits if available
try:
    from scripts.replay_admits import size_for, walk as _walk_admits, TICK_USD as _TU
    _HAS_REPLAY_ADMITS = True
except ImportError:
    _HAS_REPLAY_ADMITS = False


# ===== Evaluation model (local fallback if replay_admits unavailable) =====

def size_for(risk_pts: float) -> int:
    """n = min(5, floor(225 / (5 * risk))); n < 3 -> skip."""
    if risk_pts <= 0:
        return 0
    return min(5, int(RISK_BUDGET // (TICK_USD * risk_pts)))


def walk_forward(bars: List[Dict], start_il: str, direction: str,
                 entry: float, stop: float, targets: List[float]
                 ) -> List[Dict]:
    """Walk forward through bars from start_il, check target/stop hits.

    Full ladder: C1->T0(entry +/-3 ticks), C2->T1, C3->T2, C4->T3.
    BE (stop to entry) after T1 hit.
    Both hit same bar -> AMBIG (not attributed).

    Returns list of contract results: [{contract, event, bar_il, pts}].
    """
    results = []
    remaining_targets = list(targets)  # mutable copy
    current_stop = stop
    active_contracts = len(targets)
    be_activated = False
    seen_start = False

    for bar in bars:
        il = bar["il"]
        if il < start_il:
            continue
        if not seen_start:
            seen_start = True
            continue  # skip entry bar

        h, l = bar["high"], bar["low"]

        # Check each remaining target
        new_remaining = []
        for i, t in enumerate(remaining_targets):
            if direction == "LONG":
                hit_t = h >= t
                hit_s = l <= current_stop
            else:  # SHORT
                hit_t = l <= t
                hit_s = h >= current_stop

            if hit_t and hit_s:
                results.append({
                    "contract": i, "event": "AMBIG",
                    "bar_il": il, "pts": 0.0
                })
            elif hit_t:
                pts = abs(t - entry)
                results.append({
                    "contract": i, "event": f"T{i}",
                    "bar_il": il, "pts": pts
                })
                # BE after T1 (index 1 in the 0-based target list)
                if i >= 1 and not be_activated:
                    be_activated = True
                    current_stop = entry
            elif hit_s:
                pts = -(abs(entry - current_stop))
                results.append({
                    "contract": i, "event": "STOP",
                    "bar_il": il, "pts": pts
                })
            else:
                new_remaining.append(t)
                continue
            # If we get here, this target was resolved (hit or stop)
            continue

        # Rebuild remaining (only those not resolved)
        remaining_after = []
        resolved_indices = {r["contract"] for r in results}
        for i, t in enumerate(remaining_targets):
            if i not in resolved_indices:
                remaining_after.append(t)
        remaining_targets = remaining_after

        if not remaining_targets:
            break

    # EOD: close remaining at last bar close
    if remaining_targets and bars:
        last_close = bars[-1]["close"]
        for i, t in enumerate(remaining_targets):
            if direction == "LONG":
                pts = last_close - entry
            else:
                pts = entry - last_close
            idx = len(targets) - len(remaining_targets) + i
            results.append({
                "contract": idx, "event": "EOD",
                "bar_il": bars[-1]["il"] if bars else "-", "pts": pts
            })

    return results


def evaluate_trade_fixed(bars: List[Dict], trade: Dict) -> Dict:
    """Run the fixed evaluation model on a single trade.

    Returns: {n, total_pts, total_usd, events: [...], skip_reason}
    """
    entry = trade.get("entry_price")
    stop = trade.get("stop")
    t1 = trade.get("t1")
    direction = trade.get("direction", "").upper()

    if not (entry and stop and t1):
        return {"n": 0, "total_pts": 0.0, "total_usd": 0.0,
                "events": [], "skip_reason": "missing_levels"}

    risk_pts = abs(entry - stop)
    n = size_for(risk_pts)
    if n < 3:
        return {"n": n, "total_pts": 0.0, "total_usd": 0.0,
                "events": [], "skip_reason": "size_too_small"}

    # Build ladder: T0 = entry +/- 3 ticks (0.75 pts on MES),
    # T1, T2 = T1 + (T1-entry), T3 = T2 + (T1-entry)
    t0_offset = 0.75  # 3 ticks at 0.25/tick
    if direction == "LONG":
        t0 = entry + t0_offset
    else:
        t0 = entry - t0_offset

    t1_val = t1
    span = abs(t1_val - entry)
    if direction == "LONG":
        t2 = t1_val + span
        t3 = t2 + span
    else:
        t2 = t1_val - span
        t3 = t2 - span

    # targets: C1->T0, C2->T1, C3->T2, C4->T3 (up to n contracts)
    all_targets = [t0, t1_val, t2, t3]
    targets = all_targets[:min(n, 4)]

    entry_il = _trade_entry_il(trade)
    if not entry_il:
        return {"n": n, "total_pts": 0.0, "total_usd": 0.0,
                "events": [], "skip_reason": "no_entry_time"}

    results = walk_forward(bars, entry_il, direction, entry, stop, targets)

    total_pts = sum(r["pts"] for r in results if r["event"] != "AMBIG")
    total_usd = total_pts * TICK_USD

    return {
        "n": n,
        "total_pts": round(total_pts, 2),
        "total_usd": round(total_usd, 2),
        "events": results,
        "skip_reason": None
    }


def _trade_entry_il(trade: Dict) -> Optional[str]:
    """Extract IL-time HH:MM from trade entry_ts."""
    ts = trade.get("entry_ts")
    if ts is None:
        return None
    if isinstance(ts, str):
        # Try to parse "YYYY-MM-DD HH:MM:SS" or similar
        for fmt in ("%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S",
                     "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(ts, fmt)
                return dt.strftime("%H:%M")
            except ValueError:
                continue
        return ts[:5] if len(ts) >= 5 else None
    if isinstance(ts, datetime):
        return ts.strftime("%H:%M")
    return None


# ===== Data loaders =====

def load_session_bars(session_date: str) -> List[Dict]:
    """Load RTH 5-min bars for a session from v9_bars_5min_woodies.

    Returns list of dicts with keys: il (HH:MM), open, high, low, close.
    """
    rows = read_all(
        "SELECT (ts AT TIME ZONE 'Asia/Jerusalem') AS il, "
        "       open, high, low, close "
        "FROM v9_bars_5min_woodies "
        "WHERE (ts AT TIME ZONE 'Asia/Jerusalem')::date = (:d)::date "
        "AND (ts AT TIME ZONE 'Asia/Jerusalem')::time >= '16:30' "
        "AND (ts AT TIME ZONE 'Asia/Jerusalem')::time <= '23:00' "
        "ORDER BY ts",
        {"d": session_date}
    )
    return [{
        "il": str(r["il"])[11:16] if len(str(r["il"])) > 16 else str(r["il"]),
        "open": float(r.get("open", 0) or 0),
        "high": float(r["high"]),
        "low": float(r["low"]),
        "close": float(r["close"]),
    } for r in rows]


def load_session_trades(session_date: str) -> List[Dict]:
    """Load trades (live+shadow) for a session from v9_trades.

    Returns list of dicts with all trade columns.
    """
    rows = read_all(
        "SELECT id, mode, firing_system, direction, state, "
        "       entry_ts AT TIME ZONE 'Asia/Jerusalem' AS entry_ts_il, "
        "       entry_price, stop, t1, t2, t3, t4, "
        "       exit_ts, exit_price, exit_reason, "
        "       pnl_usd, pnl_r, outcome, "
        "       cross_context, "
        "       day_type_at_entry, pattern_id_at_entry, session_at_entry "
        "FROM v9_trades "
        "WHERE mode IN ('live', 'shadow') "
        "AND (entry_ts AT TIME ZONE 'Asia/Jerusalem')::date = (:d)::date "
        "ORDER BY entry_ts",
        {"d": session_date}
    )
    result = []
    for r in rows:
        d = dict(r)
        # Parse cross_context from JSON string if needed
        cc = d.get("cross_context")
        if isinstance(cc, str):
            try:
                d["cross_context"] = json.loads(cc)
            except (json.JSONDecodeError, TypeError):
                d["cross_context"] = {}
        elif cc is None:
            d["cross_context"] = {}
        # Normalize entry_ts for IL time
        d["entry_ts"] = d.pop("entry_ts_il", d.get("entry_ts"))
        d["entry_price"] = float(d["entry_price"]) if d.get("entry_price") else None
        d["stop"] = float(d["stop"]) if d.get("stop") else None
        d["t1"] = float(d["t1"]) if d.get("t1") else None
        result.append(d)
    return result


def load_all_session_dates(start: str = "2026-06-01",
                           end: str = "2026-09-15") -> List[str]:
    """Return distinct RTH session dates that have bars."""
    rows = read_all(
        "SELECT DISTINCT (ts AT TIME ZONE 'Asia/Jerusalem')::date AS d "
        "FROM v9_bars_5min_woodies "
        "WHERE (ts AT TIME ZONE 'Asia/Jerusalem')::date >= (:start)::date "
        "AND (ts AT TIME ZONE 'Asia/Jerusalem')::date <= (:end)::date "
        "ORDER BY d",
        {"start": start, "end": end}
    )
    return [str(r["d"]) for r in rows]


# ===== Zigzag decomposition =====

def compute_atr14_causal(bars: List[Dict]) -> float:
    """Compute ATR-14 causally (using only closed bars).

    Uses standard Wilder smoothing on true range.
    """
    if len(bars) < 2:
        return 0.0

    trs = []
    for i in range(1, len(bars)):
        h = bars[i]["high"]
        l = bars[i]["low"]
        pc = bars[i - 1]["close"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)

    if not trs:
        return 0.0

    period = min(14, len(trs))
    # Initial ATR = simple average of first `period` TRs
    atr = sum(trs[:period]) / period
    # Wilder smoothing for the rest
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period

    return atr


def compute_zigzag(bars: List[Dict], threshold: float) -> List[Dict]:
    """Decompose bar series into zigzag moves.

    A move ends when price reverses by >= threshold from the current
    extreme. Only uses closed bars (no intra-bar lookahead).

    Returns list of moves: [{t_start, t_end, start_price, end_price,
                             pts, direction, start_idx, end_idx}]
    """
    if len(bars) < 2 or threshold <= 0:
        return []

    # Build zigzag pivot points
    pivots = []  # (idx, price, type='H'|'L')

    # Start with the first bar
    current_dir = None  # 'UP' or 'DOWN'
    high_idx, high_price = 0, bars[0]["high"]
    low_idx, low_price = 0, bars[0]["low"]

    for i in range(1, len(bars)):
        h = bars[i]["high"]
        l = bars[i]["low"]

        if current_dir is None:
            # Determine initial direction
            if h - low_price >= threshold:
                pivots.append((low_idx, low_price, "L"))
                current_dir = "UP"
                high_idx, high_price = i, h
            elif high_price - l >= threshold:
                pivots.append((high_idx, high_price, "H"))
                current_dir = "DOWN"
                low_idx, low_price = i, l
            else:
                if h > high_price:
                    high_idx, high_price = i, h
                if l < low_price:
                    low_idx, low_price = i, l
        elif current_dir == "UP":
            if h > high_price:
                high_idx, high_price = i, h
            if high_price - l >= threshold:
                pivots.append((high_idx, high_price, "H"))
                current_dir = "DOWN"
                low_idx, low_price = i, l
        elif current_dir == "DOWN":
            if l < low_price:
                low_idx, low_price = i, l
            if h - low_price >= threshold:
                pivots.append((low_idx, low_price, "L"))
                current_dir = "UP"
                high_idx, high_price = i, h

    # Final pivot
    if current_dir == "UP":
        pivots.append((high_idx, high_price, "H"))
    elif current_dir == "DOWN":
        pivots.append((low_idx, low_price, "L"))

    # Convert pivots to moves
    moves = []
    for i in range(1, len(pivots)):
        p0_idx, p0_price, p0_type = pivots[i - 1]
        p1_idx, p1_price, p1_type = pivots[i]

        direction = "UP" if p1_price > p0_price else "DOWN"
        pts = abs(p1_price - p0_price)

        moves.append({
            "t_start": bars[p0_idx]["il"],
            "t_end": bars[p1_idx]["il"],
            "start_price": round(p0_price, 2),
            "end_price": round(p1_price, 2),
            "pts": round(pts, 2),
            "direction": direction,
            "start_idx": p0_idx,
            "end_idx": p1_idx,
        })

    # Sort by size descending
    moves.sort(key=lambda m: m["pts"], reverse=True)
    return moves


# ===== Move classification =====

def classify_move(move: Dict, trades: List[Dict], bars: List[Dict]) -> Dict:
    """Classify a move vs. actual trades.

    Returns: {status, trade_id, model_result, blocked_by, details}

    Status is one of:
      FIRED_LIVE — a live trade entered in the first 30% of the move
      FIRED_SHADOW_ONLY — a shadow trade entered (with model result)
      BLOCKED:<reason> — a setup existed but was blocked
      NO_SETUP — no setup at all (producer gap)
    """
    move_dir = move["direction"]
    trade_dir = "LONG" if move_dir == "UP" else "SHORT"
    t_start = move["t_start"]
    t_end = move["t_end"]
    pts = move["pts"]

    # First 30% of the move time window
    start_idx = move["start_idx"]
    end_idx = move["end_idx"]
    window_size = end_idx - start_idx
    cutoff_idx = start_idx + max(1, int(window_size * 0.3))

    # Map bar indices to IL times for the cutoff
    if cutoff_idx < len(bars):
        cutoff_il = bars[cutoff_idx]["il"]
    else:
        cutoff_il = t_end

    matching_trades = []
    for trade in trades:
        td = (trade.get("direction") or "").upper()
        if td != trade_dir:
            continue
        entry_il = _trade_entry_il(trade)
        if entry_il is None:
            continue
        if t_start <= entry_il <= cutoff_il:
            matching_trades.append(trade)

    if not matching_trades:
        # Check for blocked setups in shadow trades
        blocked_trades = []
        for trade in trades:
            td = (trade.get("direction") or "").upper()
            if td != trade_dir:
                continue
            entry_il = _trade_entry_il(trade)
            if entry_il is None:
                continue
            if t_start <= entry_il <= cutoff_il:
                cc = trade.get("cross_context", {})
                blocked_by = cc.get("blocked_by")
                if blocked_by:
                    blocked_trades.append(trade)

        if blocked_trades:
            t = blocked_trades[0]
            cc = t.get("cross_context", {})
            return {
                "status": f"BLOCKED:{cc.get('blocked_by', 'unknown')}",
                "trade_id": t.get("id"),
                "model_result": None,
                "blocked_by": cc.get("blocked_by"),
                "details": f"blocked at {_trade_entry_il(t)}"
            }

        return {
            "status": "NO_SETUP",
            "trade_id": None,
            "model_result": None,
            "blocked_by": None,
            "details": "no setup fired in first 30% of move"
        }

    # Check for live trades first
    live_trades = [t for t in matching_trades if t.get("mode") == "live"]
    if live_trades:
        t = live_trades[0]
        model_result = evaluate_trade_fixed(bars, t)
        return {
            "status": "FIRED_LIVE",
            "trade_id": t.get("id"),
            "model_result": model_result,
            "blocked_by": None,
            "details": f"live entry at {_trade_entry_il(t)}"
        }

    # Shadow only
    shadow_trades = [t for t in matching_trades if t.get("mode") == "shadow"]
    if shadow_trades:
        t = shadow_trades[0]
        model_result = evaluate_trade_fixed(bars, t)
        return {
            "status": "FIRED_SHADOW_ONLY",
            "trade_id": t.get("id"),
            "model_result": model_result,
            "blocked_by": None,
            "details": f"shadow entry at {_trade_entry_il(t)}"
        }

    return {
        "status": "NO_SETUP",
        "trade_id": None,
        "model_result": None,
        "blocked_by": None,
        "details": "no qualifying trade found"
    }


# ===== Loss vector extraction =====

def extract_loss_vector(trade: Dict) -> Optional[Dict]:
    """For a live loss, extract the entry vector."""
    if trade.get("mode") != "live":
        return None
    if trade.get("outcome") not in ("LOSS",):
        return None

    cc = trade.get("cross_context", {})
    return {
        "trade_id": trade.get("id"),
        "day_type": cc.get("day_type_final") or trade.get("day_type_at_entry"),
        "day_type_conf": cc.get("day_type_confidence"),
        "opening_type": cc.get("opening_type"),
        "zone": cc.get("zone"),
        "extension": cc.get("extension"),
        "bars_since_extreme": cc.get("bars_since_extreme"),
        "direction": trade.get("direction"),
        "entry_price": trade.get("entry_price"),
        "stop": trade.get("stop"),
        "pnl_usd": trade.get("pnl_usd"),
    }


# ===== Session analysis =====

def analyze_session(session_date: str, verbose: bool = False) -> Dict:
    """Full analysis for one session.

    Returns dict with all session data: bars, trades, zigzag, move
    classifications, loss vectors, etc.
    """
    bars = load_session_bars(session_date)
    trades = load_session_trades(session_date)

    if not bars:
        if verbose:
            print(f"  [{session_date}] No bars found, skipping.")
        return {
            "session": session_date,
            "bar_count": 0,
            "trade_count": 0,
            "range_pts": 0.0,
            "day_type_final": None,
            "opening_type": None,
            "captured_live_usd": 0.0,
            "captured_live_pts": 0.0,
            "moves": [],
            "loss_vectors": [],
            "skipped": True,
        }

    # Session range
    session_high = max(b["high"] for b in bars)
    session_low = min(b["low"] for b in bars)
    range_pts = round(session_high - session_low, 2)

    # Day type and opening type from cross_context of first trade
    day_type_final = None
    opening_type = None
    if trades:
        first_cc = trades[0].get("cross_context", {})
        day_type_final = (first_cc.get("day_type_final")
                          or trades[0].get("day_type_at_entry"))
        opening_type = first_cc.get("opening_type")

    # Live P&L through fixed evaluation model
    live_trades = [t for t in trades if t.get("mode") == "live"]
    captured_live_pts = 0.0
    captured_live_usd = 0.0
    live_evaluations = []
    for t in live_trades:
        result = evaluate_trade_fixed(bars, t)
        live_evaluations.append(result)
        captured_live_pts += result["total_pts"]
        captured_live_usd += result["total_usd"]

    # Zigzag decomposition
    atr14 = compute_atr14_causal(bars)
    zigzag_threshold = max(8.0, 1.0 * atr14)
    all_moves = compute_zigzag(bars, zigzag_threshold)

    # Take top 3 largest moves
    top_moves = all_moves[:3]

    # Classify each move
    classified_moves = []
    for move in top_moves:
        classification = classify_move(move, trades, bars)
        classified_moves.append({
            **move,
            **classification,
        })

    # Loss vectors for live losses
    loss_vectors = []
    for t in live_trades:
        lv = extract_loss_vector(t)
        if lv:
            loss_vectors.append(lv)

    session_data = {
        "session": session_date,
        "bar_count": len(bars),
        "trade_count": len(trades),
        "live_trade_count": len(live_trades),
        "range_pts": range_pts,
        "session_high": round(session_high, 2),
        "session_low": round(session_low, 2),
        "day_type_final": day_type_final,
        "opening_type": opening_type,
        "atr14": round(atr14, 2),
        "zigzag_threshold": round(zigzag_threshold, 2),
        "captured_live_pts": round(captured_live_pts, 2),
        "captured_live_usd": round(captured_live_usd, 2),
        "moves": classified_moves,
        "all_moves_count": len(all_moves),
        "loss_vectors": loss_vectors,
        "skipped": False,
    }

    if verbose:
        _print_session_verbose(session_data, bars, trades, live_evaluations)

    return session_data


def _print_session_verbose(data: Dict, bars: List[Dict],
                           trades: List[Dict],
                           live_evals: List[Dict]) -> None:
    """Print detailed session info to stdout."""
    s = data["session"]
    print(f"\n{'=' * 70}")
    print(f"Session: {s}  |  Day type: {data['day_type_final']}  |  "
          f"Opening: {data['opening_type']}")
    print(f"Bars: {data['bar_count']}  |  Range: {data['range_pts']} pts  |  "
          f"ATR14: {data['atr14']}  |  ZZ threshold: {data['zigzag_threshold']}")
    print(f"Trades: {data['trade_count']} total, {data['live_trade_count']} live")
    print(f"Captured (live, fixed model): {data['captured_live_pts']} pts / "
          f"${data['captured_live_usd']}")

    if data["moves"]:
        print(f"\nTop {len(data['moves'])} moves (of {data['all_moves_count']}):")
        for i, m in enumerate(data["moves"], 1):
            print(f"  {i}. {m['direction']:5} {m['t_start']}-{m['t_end']}  "
                  f"{m['pts']:6.1f} pts  |  {m['status']}")
            if m.get("model_result") and m["model_result"].get("events"):
                mr = m["model_result"]
                print(f"     Model: n={mr['n']}, {mr['total_pts']} pts, "
                      f"${mr['total_usd']}")

    if data["loss_vectors"]:
        print(f"\nLive losses:")
        for lv in data["loss_vectors"]:
            print(f"  trade {lv['trade_id']}: {lv['direction']} "
                  f"dt={lv['day_type']} zone={lv['zone']} "
                  f"ext={lv['extension']} P&L=${lv['pnl_usd']}")

    print(f"{'=' * 70}")


# ===== Report generation =====

def generate_report(sessions_data: List[Dict]) -> str:
    """Generate the markdown report."""
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines.append(f"# Gap Analysis Report")
    lines.append(f"Generated: {now}")
    lines.append(f"Sessions analyzed: {len(sessions_data)}")
    lines.append("")

    valid = [s for s in sessions_data if not s.get("skipped")]
    if not valid:
        lines.append("No valid sessions found.")
        return "\n".join(lines)

    # ---------- Table by day_type_final ----------
    lines.append("## By Day Type")
    lines.append("")

    by_dt = defaultdict(list)
    for s in valid:
        dt = s.get("day_type_final") or "UNKNOWN"
        by_dt[dt].append(s)

    lines.append("| Day Type | N | Avg Range | Avg Captured (pts) | "
                 "Captured/Range | Move Status Distribution |")
    lines.append("|----------|---|-----------|--------------------|-"
                 "--------------|-------------------------|")

    for dt in sorted(by_dt.keys()):
        ss = by_dt[dt]
        n = len(ss)
        avg_range = sum(s["range_pts"] for s in ss) / n
        avg_captured = sum(s["captured_live_pts"] for s in ss) / n
        ratio = avg_captured / avg_range if avg_range > 0 else 0

        # Move status distribution
        status_counts = defaultdict(int)
        for s in ss:
            for m in s.get("moves", []):
                st = m.get("status", "UNKNOWN")
                # Collapse BLOCKED:* to BLOCKED
                if st.startswith("BLOCKED:"):
                    st = "BLOCKED"
                status_counts[st] += 1

        status_str = ", ".join(f"{k}:{v}" for k, v in
                               sorted(status_counts.items()))

        lines.append(f"| {dt} | {n} | {avg_range:.1f} | {avg_captured:.1f} | "
                     f"{ratio:.1%} | {status_str} |")

    lines.append("")

    # ---------- 20 largest missed moves ----------
    lines.append("## 20 Largest Missed Moves")
    lines.append("")

    all_moves = []
    for s in valid:
        for m in s.get("moves", []):
            if m.get("status") not in ("FIRED_LIVE",):
                all_moves.append({**m, "session": s["session"],
                                  "day_type": s.get("day_type_final")})

    all_moves.sort(key=lambda m: m["pts"], reverse=True)
    top_missed = all_moves[:20]

    lines.append("| # | Session | Dir | Pts | Time | Status | Day Type |")
    lines.append("|---|---------|-----|-----|------|--------|----------|")
    for i, m in enumerate(top_missed, 1):
        lines.append(f"| {i} | {m['session']} | {m['direction']} | "
                     f"{m['pts']:.1f} | {m['t_start']}-{m['t_end']} | "
                     f"{m['status']} | {m.get('day_type', '')} |")

    lines.append("")

    # ---------- Candidate branches ----------
    lines.append("## Candidate Branches")
    lines.append("")
    lines.append("Groups of missed moves + losses by "
                 "(day_type, phase, zone, extension, dir_vs_move), N >= 15.")
    lines.append("")

    # Collect grouping keys from missed moves and loss vectors
    branch_groups = defaultdict(lambda: {"n": 0, "missed_pts": 0.0,
                                          "loss_usd": 0.0, "entries": []})

    for s in valid:
        for m in s.get("moves", []):
            if m.get("status") == "FIRED_LIVE":
                continue
            dt = s.get("day_type_final") or "UNKNOWN"
            # We don't have phase/zone on moves directly, use what we can
            key = (dt, m["direction"], m.get("status", "UNKNOWN"))
            bg = branch_groups[key]
            bg["n"] += 1
            bg["missed_pts"] += m["pts"]
            bg["entries"].append({
                "session": s["session"],
                "pts": m["pts"],
                "status": m["status"]
            })

        for lv in s.get("loss_vectors", []):
            dt = lv.get("day_type") or "UNKNOWN"
            zone = lv.get("zone") or "?"
            ext = lv.get("extension") or "?"
            d = lv.get("direction") or "?"
            key = (dt, d, f"LOSS:zone={zone},ext={ext}")
            bg = branch_groups[key]
            bg["n"] += 1
            bg["loss_usd"] += abs(lv.get("pnl_usd") or 0)

    qualifying = {k: v for k, v in branch_groups.items() if v["n"] >= 15}

    if qualifying:
        lines.append("| Group Key | N | Missed Pts | Loss $ | "
                     "Proposed Branch |")
        lines.append("|-----------|---|------------|--------|--"
                     "--------------|")
        for key, data in sorted(qualifying.items(),
                                key=lambda x: x[1]["n"], reverse=True):
            key_str = " / ".join(str(k) for k in key)
            proposed = f"expr: {key[0]}.{key[1]}.filter"
            lines.append(f"| {key_str} | {data['n']} | "
                         f"{data['missed_pts']:.1f} | "
                         f"${data['loss_usd']:.0f} | {proposed} |")
    else:
        lines.append("No groups with N >= 15 found. "
                     "(May need more sessions or lower threshold.)")

    lines.append("")

    # ---------- TREND_STEP / RE_ACCEPTANCE answer ----------
    lines.append("## TREND_STEP and RE_ACCEPTANCE Analysis")
    lines.append("")

    trend_normal_sessions = [s for s in valid
                             if (s.get("day_type_final") or "").lower()
                             in ("trend", "normal", "trend_normal")]
    shadow_in_trend = 0
    shadow_usd_in_trend = 0.0
    for s in trend_normal_sessions:
        for m in s.get("moves", []):
            if m.get("status") == "FIRED_SHADOW_ONLY":
                shadow_in_trend += 1
                mr = m.get("model_result")
                if mr:
                    shadow_usd_in_trend += mr.get("total_usd", 0)

    lines.append(f"- Trend/Normal days: {len(trend_normal_sessions)} sessions")
    lines.append(f"- Missed moves with shadow setups: {shadow_in_trend}")
    lines.append(f"- Total model $ (shadow, fixed eval): "
                 f"${shadow_usd_in_trend:,.2f}")
    lines.append("")

    # Summary
    total_range = sum(s["range_pts"] for s in valid)
    total_captured = sum(s["captured_live_pts"] for s in valid)
    overall_ratio = total_captured / total_range if total_range > 0 else 0

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total sessions: {len(valid)}")
    lines.append(f"- Total range (sum): {total_range:.1f} pts")
    lines.append(f"- Total captured (live, fixed model): "
                 f"{total_captured:.1f} pts")
    lines.append(f"- Overall captured/range: {overall_ratio:.1%}")
    lines.append(f"- Total missed moves (top 3 per session): "
                 f"{len(all_moves)}")
    lines.append("")

    return "\n".join(lines)


# ===== Main =====

def main():
    parser = argparse.ArgumentParser(
        description="Gap analysis: missed opportunities vs. price range"
    )
    parser.add_argument("--session", type=str, default=None,
                        help="Single session date (YYYY-MM-DD)")
    parser.add_argument("--verbose", action="store_true",
                        help="Detailed output per session")
    parser.add_argument("--dry", action="store_true",
                        help="One session (today or --session), no file write")
    parser.add_argument("--start", type=str, default="2026-06-01",
                        help="Start date for multi-session run")
    parser.add_argument("--end", type=str, default="2026-09-15",
                        help="End date for multi-session run")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    if args.dry:
        # Single session, no file write
        session = args.session or datetime.now().strftime("%Y-%m-%d")
        print(f"[dry run] Analyzing session {session}...")
        data = analyze_session(session, verbose=True)
        print(json.dumps(data, indent=2, default=str))
        return

    if args.session:
        # Single session
        data = analyze_session(args.session, verbose=args.verbose)
        sessions_data = [data]
    else:
        # All sessions
        dates = load_all_session_dates(args.start, args.end)
        print(f"Found {len(dates)} sessions from {args.start} to {args.end}")
        sessions_data = []
        for i, d in enumerate(dates):
            if args.verbose:
                print(f"[{i + 1}/{len(dates)}] {d}")
            data = analyze_session(d, verbose=args.verbose)
            sessions_data.append(data)
            if not args.verbose:
                status = "ok" if not data.get("skipped") else "skip"
                moves_info = (f" {len(data.get('moves', []))} moves"
                              if not data.get("skipped") else "")
                print(f"  {d}: {status}{moves_info}  "
                      f"range={data['range_pts']}  "
                      f"captured={data.get('captured_live_pts', 0)}")

    # Write outputs
    gap_dir = os.path.join(_ROOT, "harness_out", "gap")
    os.makedirs(gap_dir, exist_ok=True)

    sessions_path = os.path.join(gap_dir, "gap_sessions.json")
    with open(sessions_path, "w") as f:
        json.dump(sessions_data, f, indent=2, default=str)
    print(f"\nWrote {sessions_path}")

    # Generate report
    report = generate_report(sessions_data)
    report_dir = os.path.join(_ROOT, "docs", "reports")
    os.makedirs(report_dir, exist_ok=True)
    report_date = datetime.now().strftime("%Y-%m-%d")
    report_path = os.path.join(report_dir,
                               f"GAP_ANALYSIS_{report_date}.md")
    with open(report_path, "w") as f:
        f.write(report)
    print(f"Wrote {report_path}")

    # Print summary
    valid = [s for s in sessions_data if not s.get("skipped")]
    if valid:
        total_range = sum(s["range_pts"] for s in valid)
        total_captured = sum(s["captured_live_pts"] for s in valid)
        ratio = total_captured / total_range if total_range > 0 else 0
        print(f"\n=== Summary: {len(valid)} sessions, "
              f"captured/range = {ratio:.1%} ===")


if __name__ == "__main__":
    main()
