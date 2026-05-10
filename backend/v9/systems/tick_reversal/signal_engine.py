"""Unified signal detection engine for tick_reversal observer.

Combines micro-patterns (5) + signal detectors (10) into actionable SignalResult objects.
Main entry: detect_all_signals(bars, footprint_data) -> list[SignalResult]

Per spec Section 6 Steps 5-7:
- Patterns provide structure context
- Signals measure order-flow conditions
- Confluence scoring determines classification + confidence
"""

from __future__ import annotations
from typing import Dict, List, Optional

from .schemas import (
    BarInput, ContextResult, TickReversalConfig,
    MicroPatternResult, SignalResult,
)
from .micro_patterns import detect_all_micro_patterns, ALL_MICRO_PATTERNS
from .signal_detectors import ALL_SIGNAL_DETECTORS


def _build_context(bars: List[BarInput], config: TickReversalConfig) -> ContextResult:
    """Build context analysis from bar history (Step 4)."""
    tick = 0.25

    # Accumulation detection
    accum_active = False
    accum_bars = 0
    accum_range = 0
    if len(bars) >= config.accumulation_min_bars:
        for n in range(config.accumulation_min_bars, len(bars) + 1):
            window = bars[-n:]
            high = max(b.h for b in window)
            low = min(b.l for b in window)
            range_ticks = int((high - low) / tick)
            if range_ticks <= config.accumulation_range_ticks:
                accum_active = True
                accum_bars = n
                accum_range = range_ticks
            else:
                break

    # Jumps detection
    jumps_count = 0
    jumps_dir = None
    if len(bars) >= 2:
        current_dir = "UP" if bars[-1].c > bars[-1].o else "DOWN"
        jumps_count = 1
        jumps_dir = current_dir
        for b in reversed(bars[:-1]):
            d = "UP" if b.c > b.o else "DOWN"
            if d == current_dir:
                jumps_count += 1
            else:
                break

    # OTF clarity
    otf = 4
    if len(bars) >= 3:
        recent = bars[-3:]
        ups = sum(1 for b in recent if b.c > b.o)
        downs = sum(1 for b in recent if b.c < b.o)
        if ups >= 2 and downs >= 1:
            otf = 1
        elif ups == 0 and downs >= 2:
            otf = 2
        elif downs == 0 and ups >= 2:
            otf = 3

    return ContextResult(
        accumulation_active=accum_active,
        accumulation_bars=accum_bars,
        accumulation_range_ticks=accum_range,
        jumps_count=jumps_count,
        jumps_direction=jumps_dir,
        otf_state=otf,
    )


def _infer_direction(
    bar: BarInput,
    patterns: List[MicroPatternResult],
    signal_results: List[Dict],
) -> Optional[str]:
    """Infer overall direction from detected patterns and signals."""
    # Detected patterns have priority
    for p in patterns:
        if p.detected and p.direction:
            return p.direction

    # Count signal directions
    long_votes = 0
    short_votes = 0
    for s in signal_results:
        if s.get("active"):
            d = s.get("direction")
            w = abs(s.get("weight", 1))
            if d == "LONG":
                long_votes += w
            elif d == "SHORT":
                short_votes += w

    if long_votes > short_votes:
        return "LONG"
    if short_votes > long_votes:
        return "SHORT"

    # Bar direction as tiebreaker
    if bar.c > bar.o:
        return "LONG"
    if bar.c < bar.o:
        return "SHORT"
    return None


def _calc_confidence(
    patterns: List[MicroPatternResult],
    signal_results: List[Dict],
    ctx: ContextResult,
) -> float:
    """Calculate confidence score 0.0-1.0 from patterns + signals + context."""
    score = 0.0
    max_score = 0.0

    # Patterns contribute up to 0.3
    detected_patterns = [p for p in patterns if p.detected]
    if detected_patterns:
        best_strength = max(p.strength for p in detected_patterns)
        score += best_strength * 0.3
    max_score += 0.3

    # Signals contribute up to 0.5
    active_signals = [s for s in signal_results if s.get("active")]
    total_weight = sum(abs(s.get("weight", 1)) for s in signal_results if s.get("weight", 0) > 0)
    if total_weight > 0:
        active_weight = 0
        for s in active_signals:
            w = s.get("weight", 1)
            if w > 0:
                active_weight += w
            else:
                # Negative weight signals (exhaustion) reduce score
                active_weight += w
        signal_pct = max(0.0, active_weight / total_weight)
        score += signal_pct * 0.5
    max_score += 0.5

    # Context contributes up to 0.2
    ctx_score = 0.0
    if ctx.jumps_count >= 3:
        ctx_score += 0.07
    if ctx.accumulation_active:
        ctx_score += 0.07
    if ctx.otf_state in (1, 2, 3):
        ctx_score += 0.06
    score += ctx_score
    max_score += 0.2

    return round(min(1.0, score / max_score) if max_score > 0 else 0.0, 3)


def _calc_trigger_price(
    bar: BarInput,
    direction: str,
    patterns: List[MicroPatternResult],
) -> float:
    """Determine trigger price from pattern or bar close."""
    for p in patterns:
        if p.detected and p.trigger_price is not None:
            return p.trigger_price
    return round(bar.c, 2)


def _calc_invalidation_price(
    bar: BarInput,
    direction: str,
    patterns: List[MicroPatternResult],
) -> float:
    """Determine invalidation price from pattern or bar extreme."""
    for p in patterns:
        if p.detected and p.invalidation_price is not None:
            return p.invalidation_price
    if direction == "LONG":
        return round(bar.l, 2)
    return round(bar.h, 2)


def detect_all_signals(
    bars: List[BarInput],
    footprint_data: Optional[dict] = None,
    config: Optional[TickReversalConfig] = None,
) -> List[SignalResult]:
    """Main entry point: run all pattern + signal detectors on bar history.

    Args:
        bars: List of recent BarInput objects (most recent last).
        footprint_data: Additional footprint data (merged into last bar if provided).
        config: Configuration parameters.

    Returns:
        List of SignalResult objects (may be empty if no setup detected).
    """
    if not bars:
        return []

    cfg = config or TickReversalConfig()
    bar = bars[-1]

    # Merge footprint_data into bar if provided
    if footprint_data and bar.footprint is None:
        bar = bar.model_copy(update={"footprint": footprint_data})

    # Step 4: Context
    ctx = _build_context(bars, cfg)

    # Step 5: Micro-patterns
    pattern_results = detect_all_micro_patterns(bar, bars, ctx)

    # Step 6: Signal detectors
    sig_config = {
        "belly_dominance_ratio": cfg.belly_dominance_ratio,
        "volume_drop_pct": cfg.volume_drop_pct,
        "imbalance_ratio": cfg.imbalance_ratio,
        "stacked_imbalance_count": cfg.stacked_imbalance_count,
    }
    signal_results = []
    for _name, detect_fn in ALL_SIGNAL_DETECTORS:
        signal_results.append(detect_fn(bar, bars, sig_config))

    # Determine direction
    direction = _infer_direction(bar, pattern_results, signal_results)
    if direction is None:
        return []

    # Calculate confluence (Step 7)
    active_signals = [s for s in signal_results if s.get("active")]
    active_positive = [s for s in active_signals if s.get("weight", 1) > 0]
    boosters = sum(s.get("weight", 1) for s in active_positive if s.get("weight", 1) > 1)
    base_count = sum(1 for s in active_positive if s.get("weight", 1) == 1)

    penalties = 0
    for s in signal_results:
        if s.get("signal_id") == "exhaustion" and s.get("active"):
            penalties += 1
        if s.get("signal_id") == "cumulative_delta" and not s.get("active"):
            penalties += 1

    confluence_total = base_count + boosters - penalties

    # Step 8: Classification
    if confluence_total < cfg.confluence_tactical_min:
        return []  # NO_SETUP

    # Calculate confidence
    confidence = _calc_confidence(pattern_results, signal_results, ctx)

    # Build trigger + invalidation prices
    trigger = _calc_trigger_price(bar, direction, pattern_results)
    invalidation = _calc_invalidation_price(bar, direction, pattern_results)

    # Build signal ID
    detected_pattern_ids = [p.pattern_id for p in pattern_results if p.detected]
    active_signal_ids = [s.get("signal_id", "") for s in active_signals]

    classification = "STRATEGIC" if confluence_total >= cfg.confluence_strategic_min else "TACTICAL"
    signal_id = f"tr_{classification.lower()}_{bar.tick_size}_{bar.ts}"

    return [SignalResult(
        signal_id=signal_id,
        direction=direction,
        confidence=confidence,
        trigger_price=trigger,
        invalidation_price=invalidation,
        pattern_ids=detected_pattern_ids,
        signal_ids=active_signal_ids,
        metadata={
            "confluence_total": confluence_total,
            "classification": classification,
            "boosters": boosters,
            "penalties": penalties,
            "context": {
                "accumulation": ctx.accumulation_active,
                "jumps": ctx.jumps_count,
                "otf_state": ctx.otf_state,
            },
        },
    )]
