"""Micro-pattern detection engine for tick_reversal observer.

5 micro-patterns from spec Section 6 Step 5:
1. Accumulation + Breakout
2. V-Shape Reversal
3. Failed Test
4. Stair-step (HH/HL)
5. Compression + Pop

Each pattern: detect(footprint_bar, context) -> MicroPatternResult
"""

from __future__ import annotations
from typing import List, Optional

from .schemas import BarInput, ContextResult, MicroPatternResult


# ── Pattern 1: Accumulation + Breakout ──────────────────────────

def detect_accumulation_breakout(
    bar: BarInput,
    bars: List[BarInput],
    ctx: ContextResult,
) -> MicroPatternResult:
    """Detect accumulation (5+ bars tight range) then breakout.

    Zohar: 'To explode, you need accumulation.'
    """
    result = MicroPatternResult(pattern_id="accumulation_breakout")

    if len(bars) < 6 or not ctx.accumulation_active or ctx.accumulation_bars < 5:
        return result

    # Build accumulation zone from bars before current
    accum_end = min(ctx.accumulation_bars + 1, len(bars))
    accum_bars = bars[-accum_end:-1]
    if not accum_bars:
        return result

    accum_high = max(b.h for b in accum_bars)
    accum_low = min(b.l for b in accum_bars)
    accum_range = accum_high - accum_low

    if accum_range <= 0:
        return result

    breakout_up = bar.c > accum_high
    breakout_down = bar.c < accum_low

    if not (breakout_up or breakout_down):
        return result

    direction = "LONG" if breakout_up else "SHORT"
    overshoot = (bar.c - accum_high) if breakout_up else (accum_low - bar.c)
    strength = min(1.0, overshoot / accum_range)

    # Trigger at close, invalidation at opposite side of accumulation zone
    trigger = bar.c
    invalidation = accum_low if breakout_up else accum_high

    return MicroPatternResult(
        pattern_id="accumulation_breakout",
        detected=True,
        direction=direction,
        strength=round(strength, 3),
        trigger_price=round(trigger, 2),
        invalidation_price=round(invalidation, 2),
        metadata={
            "accum_bars": ctx.accumulation_bars,
            "accum_range_ticks": ctx.accumulation_range_ticks,
            "overshoot": round(overshoot, 2),
        },
    )


# ── Pattern 2: V-Shape Reversal ──────────────────────────────────

def detect_v_shape_reversal(
    bar: BarInput,
    bars: List[BarInput],
    ctx: ContextResult,
) -> MicroPatternResult:
    """Detect V-shape: sharp move one direction then sharp reversal."""
    result = MicroPatternResult(pattern_id="v_shape_reversal")

    if len(bars) < 5:
        return result

    recent = bars[-5:]

    # V-bottom: 2+ down bars then 2+ up bars
    down_phase = []
    pivot_idx = -1
    for i in range(len(recent)):
        if recent[i].c < recent[i].o:
            down_phase.append(i)
        else:
            if len(down_phase) >= 2:
                pivot_idx = i
            break

    if pivot_idx > 0:
        up_count = sum(1 for b in recent[pivot_idx:] if b.c > b.o)
        if up_count >= 2:
            low_at_pivot = min(b.l for b in recent[:pivot_idx + 1])
            drop = recent[0].o - low_at_pivot
            recovery = bar.c - low_at_pivot
            strength = min(1.0, recovery / drop) if drop > 0 else 0.0

            return MicroPatternResult(
                pattern_id="v_shape_reversal",
                detected=True,
                direction="LONG",
                strength=round(strength, 3),
                trigger_price=round(bar.c, 2),
                invalidation_price=round(low_at_pivot, 2),
                metadata={"pivot_low": round(low_at_pivot, 2), "recovery_pct": round(strength * 100, 1)},
            )

    # Inverted-V: 2+ up bars then 2+ down bars
    up_phase = []
    pivot_idx = -1
    for i in range(len(recent)):
        if recent[i].c > recent[i].o:
            up_phase.append(i)
        else:
            if len(up_phase) >= 2:
                pivot_idx = i
            break

    if pivot_idx > 0:
        dn_count = sum(1 for b in recent[pivot_idx:] if b.c < b.o)
        if dn_count >= 2:
            high_at_pivot = max(b.h for b in recent[:pivot_idx + 1])
            rise = high_at_pivot - recent[0].o
            drop_from_high = high_at_pivot - bar.c
            strength = min(1.0, drop_from_high / rise) if rise > 0 else 0.0

            return MicroPatternResult(
                pattern_id="v_shape_reversal",
                detected=True,
                direction="SHORT",
                strength=round(strength, 3),
                trigger_price=round(bar.c, 2),
                invalidation_price=round(high_at_pivot, 2),
                metadata={"pivot_high": round(high_at_pivot, 2), "drop_pct": round(strength * 100, 1)},
            )

    return result


# ── Pattern 3: Failed Test ───────────────────────────────────────

def detect_failed_test(
    bar: BarInput,
    bars: List[BarInput],
    ctx: ContextResult,
) -> MicroPatternResult:
    """Detect failed test: bar pokes beyond prior extreme then reverses.

    Classic false breakout / stop hunt pattern.
    """
    result = MicroPatternResult(pattern_id="failed_test")

    if len(bars) < 4:
        return result

    lookback = bars[-4:-1]
    prior_high = max(b.h for b in lookback)
    prior_low = min(b.l for b in lookback)
    bar_range = bar.h - bar.l

    if bar_range <= 0:
        return result

    # Failed test high: wick above prior high, close back inside
    if bar.h > prior_high and bar.c < prior_high:
        rejection_pct = (bar.h - bar.c) / bar_range
        if rejection_pct > 0.5:
            return MicroPatternResult(
                pattern_id="failed_test",
                detected=True,
                direction="SHORT",
                strength=round(rejection_pct, 3),
                trigger_price=round(bar.c, 2),
                invalidation_price=round(bar.h, 2),
                metadata={"test_level": round(prior_high, 2), "overshoot": round(bar.h - prior_high, 2)},
            )

    # Failed test low: wick below prior low, close back inside
    if bar.l < prior_low and bar.c > prior_low:
        rejection_pct = (bar.c - bar.l) / bar_range
        if rejection_pct > 0.5:
            return MicroPatternResult(
                pattern_id="failed_test",
                detected=True,
                direction="LONG",
                strength=round(rejection_pct, 3),
                trigger_price=round(bar.c, 2),
                invalidation_price=round(bar.l, 2),
                metadata={"test_level": round(prior_low, 2), "overshoot": round(prior_low - bar.l, 2)},
            )

    return result


# ── Pattern 4: Stair-step (HH/HL or LL/LH) ──────────────────────

def detect_stair_step(
    bar: BarInput,
    bars: List[BarInput],
    ctx: ContextResult,
) -> MicroPatternResult:
    """Detect stair-step: 3+ bars making HH/HL (up) or LL/LH (down)."""
    result = MicroPatternResult(pattern_id="stair_step")

    if len(bars) < 4:
        return result

    recent = bars[-4:]

    # Bullish stair-step: HH + HL
    hh_count = 0
    hl_count = 0
    for i in range(1, len(recent)):
        if recent[i].h > recent[i - 1].h:
            hh_count += 1
        if recent[i].l > recent[i - 1].l:
            hl_count += 1

    if hh_count >= 3 and hl_count >= 2:
        strength = min(1.0, min(hh_count, hl_count) / 3.0)
        return MicroPatternResult(
            pattern_id="stair_step",
            detected=True,
            direction="LONG",
            strength=round(strength, 3),
            trigger_price=round(bar.c, 2),
            invalidation_price=round(min(b.l for b in recent), 2),
            metadata={"hh_count": hh_count, "hl_count": hl_count},
        )

    # Bearish stair-step: LL + LH
    ll_count = 0
    lh_count = 0
    for i in range(1, len(recent)):
        if recent[i].l < recent[i - 1].l:
            ll_count += 1
        if recent[i].h < recent[i - 1].h:
            lh_count += 1

    if ll_count >= 3 and lh_count >= 2:
        strength = min(1.0, min(ll_count, lh_count) / 3.0)
        return MicroPatternResult(
            pattern_id="stair_step",
            detected=True,
            direction="SHORT",
            strength=round(strength, 3),
            trigger_price=round(bar.c, 2),
            invalidation_price=round(max(b.h for b in recent), 2),
            metadata={"ll_count": ll_count, "lh_count": lh_count},
        )

    return result


# ── Pattern 5: Compression + Pop ─────────────────────────────────

def detect_compression_pop(
    bar: BarInput,
    bars: List[BarInput],
    ctx: ContextResult,
) -> MicroPatternResult:
    """Detect compression (shrinking ranges) then pop (expansion bar)."""
    result = MicroPatternResult(pattern_id="compression_pop")

    if len(bars) < 4:
        return result

    lookback = bars[-4:-1]
    ranges = [b.h - b.l for b in lookback]
    current_range = bar.h - bar.l

    if any(r <= 0 for r in ranges) or current_range <= 0:
        return result

    # Compression: each bar's range <= previous
    is_compressing = all(ranges[i] <= ranges[i - 1] for i in range(1, len(ranges)))
    if not is_compressing:
        return result

    # Pop: current range >= 1.5x smallest compression bar
    min_compressed = min(ranges)
    if current_range < min_compressed * 1.5:
        return result

    avg_compressed = sum(ranges) / len(ranges)
    expansion_ratio = current_range / avg_compressed
    strength = min(1.0, expansion_ratio / 2.0)

    direction = "LONG" if bar.c > bar.o else "SHORT"

    return MicroPatternResult(
        pattern_id="compression_pop",
        detected=True,
        direction=direction,
        strength=round(strength, 3),
        trigger_price=round(bar.c, 2),
        invalidation_price=round(bar.l if direction == "LONG" else bar.h, 2),
        metadata={"expansion_ratio": round(expansion_ratio, 2), "compressed_bars": len(lookback)},
    )


# ── Registry ─────────────────────────────────────────────────────

ALL_MICRO_PATTERNS = [
    ("accumulation_breakout", detect_accumulation_breakout),
    ("v_shape_reversal", detect_v_shape_reversal),
    ("failed_test", detect_failed_test),
    ("stair_step", detect_stair_step),
    ("compression_pop", detect_compression_pop),
]


def detect_all_micro_patterns(
    bar: BarInput,
    bars: List[BarInput],
    ctx: ContextResult,
) -> List[MicroPatternResult]:
    """Run all 5 micro-pattern detectors. Returns list of results (detected or not)."""
    results = []
    for _name, detect_fn in ALL_MICRO_PATTERNS:
        results.append(detect_fn(bar, bars, ctx))
    return results
