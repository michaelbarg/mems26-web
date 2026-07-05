"""System 6 — exit-signal engine (the "smart manager", Michael 2026-07-05).

While a trade is open, score — SEPARATELY — the reasons it might be time to exit,
so the manager (and Michael) can decide with context and the system can LEARN
which signals to trust over time.

Three signals Michael specified:
  1. failed_reaction_volume — price reached a zone where a reaction was expected
     (support/resistance from the target zones) but the confirming order-flow
     (CVD/volume in the trade's direction) did NOT show up / got absorbed → the
     anticipated continuation is losing conviction.
  2. price_stall — price is stuck: no new favorable extreme for N bars and the
     range is compressing → the move can't continue.
  3. opposite_patterns — two or more counter-direction patterns have fired
     recently → the other side is taking over.

Each returns an ExitSignal with an independent score (0..1), a fired flag, a
plain reason, and a suggested action. `evaluate_exit` aggregates them WITHOUT
losing the per-signal detail (Michael: "יחס וכל אחד בנפרד עם אפשרות החלטה").
Nothing here executes an exit — it produces recommendations for System 6's panel
and the decision journal. Pure + fail-safe.

Flag: SYSTEM6_EXIT_SIGNALS (default OFF).

NOTE (needs Michael's confirmation): the failed_reaction_volume semantics below
assume "confirming flow in the trade's direction is absent near an expected
level = exit". If instead you mean "opposing volume SHOWED UP to defend the
level = exit", flip `flow_aligned` — one line. Flagged in the design doc.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ExitSignal:
    kind: str
    score: float          # 0..1, higher = stronger reason to exit
    fired: bool
    reason: str
    action: str = ""      # suggested action label for the panel


def price_stall(
    *,
    direction: str,
    bars: List[Dict],
    lookback: int = 6,
    stall_bars: int = 3,
) -> ExitSignal:
    """No new favorable extreme for `stall_bars` bars within the lookback window."""
    d = direction.upper()
    window = bars[-lookback:]
    if len(window) < stall_bars + 1:
        return ExitSignal("stall", 0.0, False, "not enough bars", "")
    if d == "SHORT":
        extremes = [b.get("l", b.get("low")) for b in window]
        best = min(e for e in extremes if e is not None)
        idx = max(i for i, e in enumerate(extremes) if e == best)
    else:
        extremes = [b.get("h", b.get("high")) for b in window]
        best = max(e for e in extremes if e is not None)
        idx = max(i for i, e in enumerate(extremes) if e == best)
    bars_since = (len(window) - 1) - idx
    score = round(min(1.0, bars_since / float(lookback)), 2)
    fired = bars_since >= stall_bars
    return ExitSignal(
        "stall", score, fired,
        f"no new favorable extreme for {bars_since} bars",
        "לשקול מימוש חלקי — המהלך נעצר" if fired else "",
    )


def opposite_patterns(
    *,
    trade_direction: str,
    recent_fire_directions: List[str],
    min_count: int = 2,
) -> ExitSignal:
    """Count recent counter-direction pattern fires."""
    d = trade_direction.upper()
    counter = sum(1 for x in recent_fire_directions if str(x).upper() != d)
    score = round(min(1.0, counter / float(max(1, min_count))), 2)
    fired = counter >= min_count
    return ExitSignal(
        "opposite_patterns", score, fired,
        f"{counter} counter-direction pattern(s) fired",
        f"{counter} תבניות לצד השני — סיכון היפוך, לשקול יציאה" if fired else "",
    )


def failed_reaction_volume(
    *,
    direction: str,
    price: float,
    level: Optional[float],
    level_tol: float,
    flow_aligned: Optional[float],
    weak_below: float = 0.4,
) -> ExitSignal:
    """Near an expected reaction level, the confirming flow is absent/weak.

    `flow_aligned` ∈ [0..1] = how much the live order-flow (CVD/volume) confirms
    the trade's direction (1 = fully with us, 0 = none/against). When price is
    within `level_tol` of the expected `level` and flow_aligned < weak_below →
    the anticipated continuation isn't being supported.
    """
    if level is None or flow_aligned is None:
        return ExitSignal("failed_volume", 0.0, False, "no level / no flow data", "")
    dist = abs(price - level)
    if dist > level_tol:
        return ExitSignal("failed_volume", 0.0, False, "not near the expected level", "")
    if flow_aligned >= weak_below:
        return ExitSignal("failed_volume", 0.0, False, "flow still confirms", "")
    closeness = 1.0 - (dist / level_tol) if level_tol > 0 else 1.0
    weakness = 1.0 - (flow_aligned / weak_below)
    score = round(min(1.0, closeness * weakness), 2)
    return ExitSignal(
        "failed_volume", score, score >= 0.4,
        f"expected reaction volume absent at {level} (flow {flow_aligned:.2f})",
        "הווליום לא הגיע ברמה — לשקול מימוש",
    )


def counter_flow_wins(
    *,
    direction: str,
    cvd_series: List[float],
    window: int = 3,
    threshold: float = 1500.0,
) -> ExitSignal:
    """Opposing order-flow is WINNING (Michael's confirmed semantic 2026-07-05:
    "מתי הווליום הנגדי מנצח → כדאי לצאת").

    cvd_series = cumulative-delta values during the trade, oldest→newest. Over
    the last `window` bars, the net CVD change AGAINST the trade exceeding
    `threshold` means the other side is taking over → exit.
      SHORT: our side is sellers (CVD should fall) → counter = CVD rising.
      LONG:  our side is buyers (CVD should rise) → counter = CVD falling.
    """
    if len(cvd_series) < window + 1:
        return ExitSignal("counter_flow", 0.0, False, "not enough CVD bars", "")
    recent = cvd_series[-(window + 1):]
    delta = recent[-1] - recent[0]
    counter = delta if direction.upper() == "SHORT" else -delta
    if counter < threshold:
        return ExitSignal("counter_flow", 0.0, False,
                          f"our side still leads (counter Δ {counter:.0f})", "")
    score = round(min(1.0, counter / (2.0 * threshold)), 2)
    return ExitSignal(
        "counter_flow", score, True,
        f"opposing volume winning (counter CVD +{counter:.0f} over {window} bars)",
        "הווליום הנגדי מנצח — לשקול יציאה",
    )


DEFAULT_WEIGHTS = {"counter_flow": 1.0, "failed_volume": 1.0,
                   "stall": 0.8, "opposite_patterns": 1.0}


@dataclass
class ExitEvaluation:
    signals: List[ExitSignal] = field(default_factory=list)
    weighted_score: float = 0.0
    recommend_exit: bool = False
    top_reason: str = ""

    @property
    def fired(self) -> List[ExitSignal]:
        return [s for s in self.signals if s.fired]


def evaluate_exit(
    signals: List[ExitSignal],
    *,
    weights: Optional[Dict[str, float]] = None,
    exit_threshold: float = 0.6,
) -> ExitEvaluation:
    """Aggregate WITHOUT losing the per-signal detail. weighted_score is the
    max-normalised weighted blend; each signal stays independently inspectable."""
    w = weights or DEFAULT_WEIGHTS
    if not signals:
        return ExitEvaluation([], 0.0, False, "")
    num = sum(s.score * w.get(s.kind, 1.0) for s in signals)
    den = sum(w.get(s.kind, 1.0) for s in signals) or 1.0
    weighted = round(num / den, 3)
    top = max(signals, key=lambda s: s.score * w.get(s.kind, 1.0))
    return ExitEvaluation(
        signals=signals, weighted_score=weighted,
        recommend_exit=(weighted >= exit_threshold) or any(s.fired for s in signals),
        top_reason=top.reason if top.score > 0 else "",
    )


# ---------------------------------------------------------------------------
# HOLD side — pattern-continuation scan (Michael 2026-07-05: "לדרוש מהמערכת
# סריקה של התבנית ולראות שהיא לא נשברת וממשיכה עם המגמה"). This is the master
# gate OVER the exit signals: while the entered structure is intact AND the
# move one-timeframes in the trade direction, HOLD (dampen the exit blips); the
# moment the pattern breaks, exit hard. Resolves the give-back-vs-let-it-run
# tension with STRUCTURE instead of a fixed %.
# ---------------------------------------------------------------------------


@dataclass
class HoldScan:
    intact: bool           # invalidation level not violated
    continuing: bool       # still one-timeframing in the trade direction
    score: float           # 0..1 confidence the thesis holds
    reason: str
    broke: bool = False    # True = structure broke → strong exit


def pattern_intact(
    *,
    direction: str,
    invalidation_level: Optional[float],
    last_close: Optional[float],
) -> bool:
    """The entered pattern is intact while price has not CLOSED through its
    invalidation level (structural stop / key level). Fail-safe: unknown → True
    (don't force an exit on missing data)."""
    if invalidation_level is None or last_close is None:
        return True
    if direction.upper() == "SHORT":
        return last_close < invalidation_level
    return last_close > invalidation_level


def trend_continues(
    *,
    direction: str,
    bars: List[Dict],
    lookback: int = 5,
) -> HoldScan:
    """One-timeframing check: the move keeps making lower highs (SHORT) / higher
    lows (LONG) and has not taken out the recent 2-bar swing against the trade.
    A break of that swing = structure broke → exit."""
    window = bars[-lookback:]
    if len(window) < 3:
        return HoldScan(True, True, 0.5, "not enough bars (neutral)")
    highs = [b.get("h", b.get("high")) for b in window]
    lows = [b.get("l", b.get("low")) for b in window]
    if any(h is None for h in highs) or any(l is None for l in lows):
        return HoldScan(True, True, 0.5, "missing OHLC (neutral)")
    d = direction.upper()
    if d == "SHORT":
        swing = max(highs[:-1][-2:])          # recent 2-bar swing high
        broke = highs[-1] > swing
        steps = sum(1 for i in range(1, len(highs)) if highs[i] <= highs[i - 1])
    else:
        swing = min(lows[:-1][-2:])            # recent 2-bar swing low
        broke = lows[-1] < swing
        steps = sum(1 for i in range(1, len(lows)) if lows[i] >= lows[i - 1])
    score = round(steps / float(len(window) - 1), 2)
    continuing = (not broke) and score >= 0.5
    reason = ("structure broke — swing taken out against the trade" if broke
              else f"one-timeframing intact ({steps}/{len(window) - 1} steps)")
    return HoldScan(not broke, continuing, score, reason, broke=broke)


def hold_confirmation(
    *,
    direction: str,
    invalidation_level: Optional[float],
    bars: List[Dict],
    lookback: int = 5,
) -> HoldScan:
    """Combine pattern-intact + trend-continuation into the master HOLD gate.

    strong hold  → intact AND continuing (let the runner run; dampen exits)
    broke        → invalidation violated OR swing taken out (exit hard)
    """
    last_close = bars[-1].get("c", bars[-1].get("close")) if bars else None
    intact = pattern_intact(direction=direction, invalidation_level=invalidation_level,
                            last_close=last_close)
    tc = trend_continues(direction=direction, bars=bars, lookback=lookback)
    broke = (not intact) or tc.broke
    continuing = intact and tc.continuing
    if not intact:
        reason = "pattern invalidated — price closed through the invalidation level"
        score = 0.0
    else:
        reason = tc.reason
        score = tc.score if continuing else round(tc.score * 0.5, 2)
    return HoldScan(intact=intact, continuing=continuing, score=score,
                    reason=reason, broke=broke)


def enabled() -> bool:
    return os.getenv("SYSTEM6_EXIT_SIGNALS", "0").lower() in ("1", "true", "yes")
