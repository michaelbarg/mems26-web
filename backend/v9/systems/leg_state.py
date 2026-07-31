"""LEG_RIDE_V1 — intraday LEG detection (Michael's ruling, 2026-07-31 21:45).

Michael, with a screenshot of Friday evening's tape: "מה שחשוב אנחנו לא מזהים."
The screenshot: stair-stepping candles riding a rising LSMA, shallow pullbacks
holding it, CCI holding the positive side — the textbook Woodies up-leg — and
the system blocked nine ZLR longs inside it, reasoning at DAY level ("high in
range", "small displacement", stale dir_sustained) while the tradeable object
was the LEG.

**The system thought in day-units; the market trades in leg-units.**

Definition (from Michael's Woodies doctrine — all on CLOSED bars, canonical
Sierra values from v9_bars_5min_woodies, never locally synthesized):

  UP leg, all three required (mirror for DOWN):
    1. LSMA rising: lsma_value strictly higher over the last LEG_LSMA_BARS (4).
    2. Structure: >= LEG_MIN_HIGHER_LOWS (2) consecutive higher lows, and the
       last close is above the LSMA (the pullbacks HOLD the line).
    3. CCI holds the side: cci_14 > 0 across the window, tolerating at most
       one momentary dip <= 0 (that dip IS the zero-line reject ZLR is made of).

  Leg dies when: two consecutive closes across the LSMA, or the last leg swing
  low/high breaks.

Consumers (gateway): a WITH-leg continuation entry (ZLR / pullback-to-LSMA) is
exempt from the DAY-level direction/location gates — cont_trend_filter (its
dir_sustained lagged three documented days), location_gate ("high in range" is
meaningless inside a leg; the location is the LSMA), extreme-chase. It stays
fully subject to margin, risk caps, R:R, news and risk-halt. AGAINST the leg,
every gate applies untouched — fading a live leg is the forbidden trade.

Pure module: no env, no I/O. Caller gates on LEG_RIDE_V1 and provides rows.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

LEG_LSMA_BARS = 4          # LSMA must rise/fall across this many closed bars
LEG_MIN_SWINGS = 2         # NET higher-lows (UP) / lower-highs (DOWN) in window
LEG_CCI_DIP_TOLERANCE = 1  # bars allowed across zero inside the window
# Calibrated on the 31.07 19:15-20:20 truth tape (Michael's screenshot leg):
# the LSMA endpoint RUNS AHEAD in a fast climb — closes kissed it from below
# by up to 2.4pt at 20:05-20:15 while the leg was fully alive; the dead window
# (20:45-21:10) had closes 6-10pt under a flat LSMA. 2.5pt separates them.
LEG_LSMA_TOL_PTS = 2.5


def _f(row: Dict[str, Any], key: str) -> Optional[float]:
    v = row.get(key)
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def detect_leg(rows: Sequence[Dict[str, Any]],
               lsma_bars: int = LEG_LSMA_BARS,
               min_swings: int = LEG_MIN_SWINGS) -> Tuple[Optional[str], int, str]:
    """rows = closed 5-min bars oldest→newest with high/low/close/lsma_value/
    cci_14 (canonical Sierra columns). Returns (leg, age_bars, reason):
    leg in {"UP","DOWN",None}. Missing canonical values ⇒ None (Rule 1 —
    honest missing, never synthesized)."""
    need = lsma_bars + 1
    if not rows or len(rows) < max(need, min_swings + 1):
        return None, 0, f"only {len(rows or [])} bars"

    win = list(rows)[-(max(lsma_bars, min_swings) + 2):]
    lsma = [_f(r, "lsma_value") for r in win]
    cci = [_f(r, "cci_14") for r in win]
    close = [_f(r, "close") for r in win]
    lows = [_f(r, "low") for r in win]
    highs = [_f(r, "high") for r in win]
    if any(v is None for v in lsma[-need:]) or close[-1] is None:
        return None, 0, "canonical LSMA/close missing — no leg (Rule 1)"

    # 1 — LSMA direction over the last `lsma_bars` transitions
    seg = lsma[-need:]
    rising = all(b > a for a, b in zip(seg, seg[1:]))
    falling = all(b < a for a, b in zip(seg, seg[1:]))
    if not (rising or falling):
        return None, 0, "LSMA not one-directional"
    direction = "UP" if rising else "DOWN"

    # 2 — structure: NET ascent of the lows (descent of highs for DOWN). A real
    #     leg breathes — single-bar dips (19:40-19:45 on the truth tape) must
    #     not reset it. Require >= min_swings up-transitions in the window AND
    #     the newest swing above the oldest (net progress), no consecutiveness.
    series = [v for v in (lows if direction == "UP" else highs) if v is not None]
    if len(series) < min_swings + 1:
        return None, 0, "structure series too short"
    ups = sum(1 for a, b in zip(series[:-1], series[1:])
              if (b > a if direction == "UP" else b < a))
    net = series[-1] > series[0] if direction == "UP" else series[-1] < series[0]
    if ups < min_swings or not net:
        return None, 0, f"structure {ups}/{min_swings} swings, net={'ok' if net else 'no'}"
    # holding the line: the LSMA endpoint runs AHEAD in a fast move — price may
    # kiss it from behind by up to LEG_LSMA_TOL_PTS while the leg lives.
    held = (close[-1] >= lsma[-1] - LEG_LSMA_TOL_PTS if direction == "UP"
            else close[-1] <= lsma[-1] + LEG_LSMA_TOL_PTS)
    if not held:
        return None, 0, f"last close {close[-1]} lost the LSMA {lsma[-1]:.2f} (>{LEG_LSMA_TOL_PTS}pt)"

    # 3 — CCI holds the side (tolerate one momentary cross — the ZLR dip)
    cci_win = [c for c in cci[-need:] if c is not None]
    if cci_win:
        wrong = sum(1 for c in cci_win
                    if (c <= 0 if direction == "UP" else c >= 0))
        if wrong > LEG_CCI_DIP_TOLERANCE:
            return None, 0, f"CCI not holding the side ({wrong} bars across zero)"

    # age: walk back while LSMA keeps the direction
    age = 0
    for a, b in zip(lsma[:-1], lsma[1:]):
        if a is None or b is None:
            break
        if (b > a) if direction == "UP" else (b < a):
            age += 1
        else:
            age = 0
    return direction, age, (
        f"{direction} leg: LSMA {'rising' if rising else 'falling'} x{lsma_bars}, "
        f"{ups} net swings holding it, close on-side")
