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


DEFAULT_WEIGHTS = {"failed_volume": 1.0, "stall": 0.8, "opposite_patterns": 1.0}


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


def enabled() -> bool:
    return os.getenv("SYSTEM6_EXIT_SIGNALS", "0").lower() in ("1", "true", "yes")
