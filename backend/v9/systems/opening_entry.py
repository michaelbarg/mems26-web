"""Opening-type ENTRY triggers (Dalton) — REVISED per the 31-session historical
validation (2026-07-22 agent report) and run in SHADOW first.

Michael (07-22): "לפי דלתון יש סוגי פתיחה — המערכת צריכה לבצע ירי בהתאם...
תבצע בניה עכשיו... תשלח סוכן שיבדוק האם זה נכון גם על העבר."
The agent's verdict on the NAIVE spec was −6.12R/31 sessions → NOT enabled live.
This module implements the REVISED rules the evidence pointed to, emitting
SHADOW-only setups (metadata.shadow_only) to collect forward evidence:

  • OPEN_DRIVE   — close beyond the opening-range extreme, one-directional,
                   ONLY when the opening bar is NARROW (or_width <= narrow_max;
                   the single historical winner had OR 4.75pt; wide-OR drives
                   were noise: avg bar-1 range 16.5pt, 06-12 lost on 51pt R).
  • OPEN_TEST_DRIVE — excursion beyond the session open of >= td_frac * OR
                   measured from bar 2 onward (bar-1 wick does NOT arm — the
                   'weak' artifact fired 84% of days historically), then a
                   close back through the open → entry on the reclaim side.
  • OPEN_REJECTION_REVERSE — a drive-close happened (any OR width), then a
                   bar closes back through the open OPPOSITE → reversal entry.
                   SUPERSEDES an earlier drive entry (historically the only
                   trigger >50% to +1R: 4/5, avg MFE 4.67R — but must BANK,
                   so T1 = +1R, not hold-to-EOD).
  • OPEN_AUCTION — none of the above by the window end → no entry (honest).

One DRIVE/TEST_DRIVE entry max per session; ORR may follow once as the
superseding reversal. Pure logic — no env reads, no I/O; caller gates on
OPENING_ENTRY_V1 (shadow|1) and provides the session bars.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Revised parameters (agent report §4; YAML-tunable later if promoted)
OR_NARROW_MAX_PTS = 10.0     # DRIVE fires only when bar-1 range <= this
TD_EXCURSION_FRAC = 0.5      # TEST excursion >= 50% of OR width, from bar 2
WINDOW_LAST_BAR = 6          # bars 2..6 (first 30 min)
ORR_FIRST_BAR = 3            # reversal earliest at bar 3


def _f(bar: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        v = bar.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def evaluate_opening_entry(session_bars: List[Dict[str, Any]],
                           already_fired: Optional[set] = None) -> Optional[Dict[str, Any]]:
    """Evaluate the LAST bar of `session_bars` (closed 5-min RTH bars, bar 1 =
    the 16:30 IL open bar) for an opening entry. Returns a trigger dict or None.
    `already_fired` = set of trigger types already emitted this session
    (enforces one DRIVE/TD + at most one superseding ORR)."""
    fired = already_fired or set()
    n = len(session_bars)
    if n < 2 or n > WINDOW_LAST_BAR:
        return None

    b1 = session_bars[0]
    or_high = _f(b1, "h", "high")
    or_low = _f(b1, "l", "low")
    open_price = _f(b1, "o", "open")
    if None in (or_high, or_low, open_price):
        return None
    or_width = or_high - or_low
    last = session_bars[-1]
    close = _f(last, "c", "close")
    if close is None:
        return None

    closes = [_f(b, "c", "close") for b in session_bars[1:]]  # bars 2..n
    prior_closes = closes[:-1]  # bars 2..n-1

    drove_up_before = any(c is not None and c > or_high for c in prior_closes)
    drove_dn_before = any(c is not None and c < or_low for c in prior_closes)

    # ── ORR: a prior drive-close + this bar closes back through the OPEN
    # opposite. Supersedes an earlier DRIVE/TD entry (one ORR max).
    if "ORR" not in fired and n >= ORR_FIRST_BAR:
        if drove_up_before and close < open_price:
            return {"type": "ORR", "direction": "SHORT", "entry": close,
                    "or_width": or_width, "reverses": "UP_DRIVE"}
        if drove_dn_before and close > open_price:
            return {"type": "ORR", "direction": "LONG", "entry": close,
                    "or_width": or_width, "reverses": "DOWN_DRIVE"}

    # only one initiating entry (DRIVE or TD) per session
    if fired & {"DRIVE", "TEST_DRIVE"}:
        return None

    # ── DRIVE: close beyond OR extreme, one-directional, NARROW OR only.
    if or_width <= OR_NARROW_MAX_PTS:
        if close > or_high and not drove_dn_before:
            return {"type": "DRIVE", "direction": "LONG", "entry": close,
                    "or_width": or_width}
        if close < or_low and not drove_up_before:
            return {"type": "DRIVE", "direction": "SHORT", "entry": close,
                    "or_width": or_width}

    # ── EXTREME_REJECT (Michael's opening rule, 07-22 "מדויק" — validated on
    # 31 sessions): a bar tests the RUNNING session extreme (touch ≤0.5,
    # rejection close >0.5 back), the NEXT bar CONFIRMS (closes further away).
    # Validation verdicts applied: confirm-filter kept (12/14 to +1R),
    # stop widened to extreme ∓10T (6T re-probed routinely; sweep 10-16T
    # flips expectancy), entry at confirm close, bank at +1R (setup t1).
    # SHADOW evidence collection — one per session.
    if "EXTREME_REJECT" not in fired and n >= 3:
        test_i = n - 2   # candidate test bar = previous bar (index n-2)
        if test_i >= 1:  # bar 2+
            prior = session_bars[:test_i]
            prior_low = min((_f(b, "l", "low") or open_price) for b in prior)
            prior_high = max((_f(b, "h", "high") or open_price) for b in prior)
            tb = session_bars[test_i]
            tb_l, tb_h, tb_c = _f(tb, "l", "low"), _f(tb, "h", "high"), _f(tb, "c", "close")
            if None not in (tb_l, tb_h, tb_c):
                # low test + confirm
                if tb_l <= prior_low + 0.5 and tb_c > prior_low + 0.5 and close > tb_c:
                    return {"type": "EXTREME_REJECT", "direction": "LONG",
                            "entry": close, "or_width": or_width,
                            "extreme": min(prior_low, tb_l), "stop_offset_ticks": 10}
                # high test + confirm
                if tb_h >= prior_high - 0.5 and tb_c < prior_high - 0.5 and close < tb_c:
                    return {"type": "EXTREME_REJECT", "direction": "SHORT",
                            "entry": close, "or_width": or_width,
                            "extreme": max(prior_high, tb_h), "stop_offset_ticks": 10}

    # ── TEST_DRIVE: excursion beyond open (>= frac*OR) measured from BAR 2
    # onward on one side, no drive-close on that side, then close through the
    # open to the other side.
    need = TD_EXCURSION_FRAC * or_width
    if need > 0 and n >= 3:  # excursion bars 2..n-1, reclaim on bar n
        exc_up = max((_f(b, "h", "high") or open_price) - open_price
                     for b in session_bars[1:-1])
        exc_dn = max(open_price - (_f(b, "l", "low") or open_price)
                     for b in session_bars[1:-1])
        if exc_up >= need and not drove_up_before and close < open_price:
            return {"type": "TEST_DRIVE", "direction": "SHORT", "entry": close,
                    "or_width": or_width, "excursion": exc_up}
        if exc_dn >= need and not drove_dn_before and close > open_price:
            return {"type": "TEST_DRIVE", "direction": "LONG", "entry": close,
                    "or_width": or_width, "excursion": exc_dn}

    return None


def build_opening_setup(trigger: Dict[str, Any], session_bars: List[Dict[str, Any]],
                        shadow_only: bool, offset_ticks: int = 6) -> Optional[Dict[str, Any]]:
    """Gateway setup from a trigger: stop behind the session-structure extreme
    (+offset), T1 = +1R (BANK — the historical ORR lesson: hold-to-EOD gives
    the move back). All normal gateway gates still apply."""
    from backend.v9.systems.stop_anchors import resolver as SA

    direction = trigger["direction"]
    entry = float(trigger["entry"])
    if trigger.get("extreme") is not None:
        # EXTREME_REJECT: stop behind the TESTED extreme, wider offset per the
        # 31-session sweep (6T re-probed routinely; 10T+ flips expectancy).
        anchor = float(trigger["extreme"])
        offset_ticks = int(trigger.get("stop_offset_ticks", offset_ticks))
    else:
        lows = [_f(b, "l", "low") for b in session_bars]
        highs = [_f(b, "h", "high") for b in session_bars]
        if direction == "LONG":
            anchor = min(v for v in lows if v is not None)
        else:
            anchor = max(v for v in highs if v is not None)
    stop = SA.apply_offset(anchor, direction, offset_ticks)
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    t1 = entry + risk if direction == "LONG" else entry - risk
    return {
        "firing_system": 2,
        "direction": direction,
        "classification": f"OPENING_{trigger['type']}",
        "confidence": 0.6,
        "entry_price": entry,
        "stop": stop,
        "t1": round(t1, 2),
        "t2": None,
        "t3": None,
        "metadata": {
            "opening_entry": trigger["type"],
            "shadow_only": bool(shadow_only),
            "or_width": trigger.get("or_width"),
            "reverses": trigger.get("reverses"),
        },
    }
