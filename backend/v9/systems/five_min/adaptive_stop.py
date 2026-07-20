"""adaptive_stop.py — Adaptive Stop Engine per D-091 (with 2026-05-23 bug corrections).

Replaces static `bar.low - 2.0pt` with 3-layer adaptive computation:
  A) structural anchor (per pattern · anchor ± 1 tick)
  B) ATR cap (per family · today_typical × multiplier · the volatility ceiling)
  C) floor (4 ticks · the 1.0pt MES noise minimum)

LONG  stop is below entry · final = min(max(A, B), floor)   (clamp · never tighter than C)
SHORT stop is above entry · final = max(min(A, B), floor)   (mirror)

V2 addition (STOP_ANCHORS_V2 flag):
  compute_stop_v2() — structural stop always wins; ATR cap is a size gate only.
  Mirrors S4's atr_stop.compute_stop_v2 but uses today_typical × family_mult
  instead of raw ATR-14 ticks.
"""

import logging
import statistics
from dataclasses import dataclass
from typing import List, Literal, Optional

logger = logging.getLogger(__name__)

# ── Hardcoded defaults (fallback) ────────────────────────────────────
MES_TICK = 0.25
FLOOR_TICKS = 4
FLOOR_TICKS_MIN_BACKSTOP = 32  # absolute minimum regardless of ATR — Michael 2026-07-20:
# was 4 (1.0pt) → too close. Trade #420 (S2 REACTIVE_SHORT) got a 5.25pt stop = 1.75×ATR5m
# when ATR5m dipped to ~3pt at fire, and a normal pullback stopped it out. 32T = 8pt ≈
# 0.75×ATR14 hard minimum (still capped above by per-pattern max_risk_points). Config-tunable
# via stop_anchors.yaml s2.floor_ticks_min_backstop.

# S2 ATR-relative floor (E2E 2/2 · shadow only)
from backend.v9.shared.atr import S2_ATR_RELATIVE  # noqa: E402
_FLOOR_ATR_K = 1.75  # prior: 1.75×ATR5m

ATR_MULTIPLIERS = {
    "Reactive": 1.0,
    "OFA": 1.5,
    "Flag": 1.5,
    "Double_BT": 2.0,
    "HnS": 2.0,
}

# ── YAML override with fallback ──────────────────────────────────────
def _try_load_yaml_stop() -> None:
    """Attempt to load stop params from YAML; override module globals on success."""
    global MES_TICK, FLOOR_TICKS, FLOOR_TICKS_MIN_BACKSTOP, _FLOOR_ATR_K, ATR_MULTIPLIERS
    try:
        from backend.v9.config_loader import load_stop_params
        data = load_stop_params()
        if data is None:
            return
        s2 = data.get("s2_adaptive", {})
        if s2:
            MES_TICK = float(s2.get("mes_tick", MES_TICK))
            FLOOR_TICKS = int(s2.get("floor_ticks", FLOOR_TICKS))
            FLOOR_TICKS_MIN_BACKSTOP = int(s2.get("floor_ticks_min_backstop", FLOOR_TICKS_MIN_BACKSTOP))
            _FLOOR_ATR_K = float(s2.get("floor_atr_k", _FLOOR_ATR_K))
            atr_mult = s2.get("atr_multipliers")
            if isinstance(atr_mult, dict) and len(atr_mult) >= 5:
                ATR_MULTIPLIERS = {k: float(v) for k, v in atr_mult.items()}
            logger.info("[adaptive_stop] loaded stop params from YAML")
    except Exception as e:
        logger.warning("[adaptive_stop] YAML load failed (%s) — using hardcoded", e)

_try_load_yaml_stop()


def get_floor_ticks(atr_5m=None) -> int:
    """Floor distance in ticks — ATR-relative with absolute backstop when flag ON."""
    if S2_ATR_RELATIVE and atr_5m is not None:
        atr_ticks = max(1, round(_FLOOR_ATR_K * atr_5m / MES_TICK))
        return max(atr_ticks, FLOOR_TICKS_MIN_BACKSTOP)
    return FLOOR_TICKS


@dataclass
class StopComputation:
    """Output of compute_stop · all layers visible for audit."""
    stop_price: float
    structural_anchor: float
    stop_structural: float
    adaptive_cap: float
    floor_price: float
    binding_layer: Literal["A", "B", "C"]
    reduce_size_signal: bool
    today_typical: float


def compute_baseline_atr(yesterday_bars: List[dict]) -> float:
    """Pre-session ATR-14 from yesterday's 5-min bars (D-091 §Pre-session phase).

    Uses Wilder's smoothed ATR-14:
      TR_i = max(h_i - l_i, |h_i - c_{i-1}|, |l_i - c_{i-1}|)
      ATR_1..14 = mean(TR_1..14)
      ATR_i = (ATR_{i-1} * 13 + TR_i) / 14   for i > 14

    Raises:
        RuntimeError: if fewer than 14 bars provided
    """
    if len(yesterday_bars) < 14:
        raise RuntimeError(
            f"baseline_atr requires ≥14 prior bars, got {len(yesterday_bars)}"
        )

    true_ranges: List[float] = []
    for i, bar in enumerate(yesterday_bars):
        h = bar["h"]
        l = bar["l"]
        bar_range = h - l
        if i > 0:
            prev_c = yesterday_bars[i - 1]["c"]
            tr = max(bar_range, abs(h - prev_c), abs(l - prev_c))
        else:
            tr = bar_range
        true_ranges.append(tr)

    # Wilder's smoothing: seed with SMA of first 14, then EMA-style
    atr = sum(true_ranges[:14]) / 14
    for tr in true_ranges[14:]:
        atr = (atr * 13 + tr) / 14

    return atr


def compute_rolling_atr(today_bars_so_far: List[dict]) -> float:
    """During-IB rolling ATR (D-091 §During IB phase).

    Simple moving average of bar ranges (h - l).
    """
    if not today_bars_so_far:
        logger.warning("[adaptive_stop] compute_rolling_atr called with 0 bars")
        return 0.0
    ranges = [bar["h"] - bar["l"] for bar in today_bars_so_far]
    return sum(ranges) / len(ranges)


def compute_today_typical(today_bars: List[dict]) -> float:
    """Post-IB · 75th percentile of today's bar ranges (D-091 §Post-IB phase).

    Uses statistics.quantiles with n=4 (quartiles); P75 = quantiles[2].
    Falls back to simple mean if fewer than 2 bars (quantiles requires ≥2).
    """
    if not today_bars:
        logger.warning("[adaptive_stop] compute_today_typical called with 0 bars")
        return 0.0
    ranges = [bar["h"] - bar["l"] for bar in today_bars]
    if len(ranges) < 2:
        return ranges[0]
    quartiles = statistics.quantiles(ranges, n=4)
    return quartiles[2]  # P75


def compute_today_max(today_bars: List[dict]) -> float:
    """Post-IB · max of today's bar ranges (D-091 §Post-IB phase)."""
    if not today_bars:
        logger.warning("[adaptive_stop] compute_today_max called with 0 bars")
        return 0.0
    return max(bar["h"] - bar["l"] for bar in today_bars)


def compute_stop(
    *,
    entry_price: float,
    direction: Literal["LONG", "SHORT"],
    structural_anchor: float,
    family: Literal["Reactive", "OFA", "Flag", "Double_BT", "HnS"],
    today_typical: float,
) -> StopComputation:
    """Compute final stop per D-091 §Stop calculation (3 layers · CORRECTED formulas).

    LONG (stop below entry · higher price = tighter):
        stop_structural = structural_anchor - 1 × MES_TICK
        adaptive_cap    = entry_price       - ATR_MULTIPLIERS[family] × today_typical
        floor_price     = entry_price       - FLOOR_TICKS × MES_TICK
        candidate       = max(stop_structural, adaptive_cap)
        stop_price      = min(candidate, floor_price)

    SHORT (stop above entry · lower price = tighter):
        stop_structural = structural_anchor + 1 × MES_TICK
        adaptive_cap    = entry_price       + ATR_MULTIPLIERS[family] × today_typical
        floor_price     = entry_price       + FLOOR_TICKS × MES_TICK
        candidate       = min(stop_structural, adaptive_cap)
        stop_price      = max(candidate, floor_price)
    """
    multiplier = ATR_MULTIPLIERS[family]  # KeyError for unknown family is intentional

    if today_typical <= 0:
        logger.warning(
            "[adaptive_stop] today_typical=%.4f ≤ 0 · falling back to floor only",
            today_typical,
        )

    if direction == "LONG":
        stop_structural = structural_anchor - MES_TICK
        adaptive_cap = entry_price - multiplier * today_typical
        floor_price = entry_price - FLOOR_TICKS * MES_TICK
        candidate = max(stop_structural, adaptive_cap)
        stop_price = min(candidate, floor_price)
    else:
        stop_structural = structural_anchor + MES_TICK
        adaptive_cap = entry_price + multiplier * today_typical
        floor_price = entry_price + FLOOR_TICKS * MES_TICK
        candidate = min(stop_structural, adaptive_cap)
        stop_price = max(candidate, floor_price)

    # Binding layer determination (C > A > B precedence for ties)
    if stop_price == floor_price:
        binding_layer: Literal["A", "B", "C"] = "C"
    elif stop_price == stop_structural:
        binding_layer = "A"
    else:
        binding_layer = "B"

    reduce_size_signal = (binding_layer == "A")

    return StopComputation(
        stop_price=stop_price,
        structural_anchor=structural_anchor,
        stop_structural=stop_structural,
        adaptive_cap=adaptive_cap,
        floor_price=floor_price,
        binding_layer=binding_layer,
        reduce_size_signal=reduce_size_signal,
        today_typical=today_typical,
    )


# ═══════════════════════════════════════════════════════════════════════
# Stop-Anchor V2 (STOP_ANCHORS_V2 flag) — structural stop wins, ATR=size gate
# Mirrors S4's atr_stop.compute_stop_v2 for the S2 five-min system.
# Spec: config/stop_anchors.yaml. Flag-gated at the CALL SITE; this is pure.
# Legacy compute_stop() above is unchanged.
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class StopComputationV2:
    """V2 stop output — structural stop wins; ATR is size gate only."""
    stop_price: float           # = structural anchor (never moved by ATR)
    risk_ticks: int             # |entry - stop| in ticks (after floor)
    atr_cap_ticks: int          # the ATR ceiling in ticks, for downstream sizing
    cap_exceeded: bool          # structural risk > ATR cap → fewer contracts
    floor_applied: bool         # structural was inside the floor → pushed to floor
    today_typical: float        # audit: the volatility measure used


def compute_stop_v2(
    *,
    entry_price: float,
    direction: Literal["LONG", "SHORT"],
    structural_stop_price: float,
    family: Literal["Reactive", "OFA", "Flag", "Double_BT", "HnS"],
    today_typical: float,
    atr_5m: Optional[float] = None,
) -> StopComputationV2:
    """V2: the structural anchor IS the stop (ATR never moves it).

    Difference from legacy compute_stop():
      - Legacy takes max(structural, ATR cap) then min(floor) — the cap could
        pull the stop INTO the bar on a large candle.
      - V2 keeps the structural stop price and reports cap_exceeded so the
        sizing layer cuts contracts (ATR cap = SIZE gate, per Michael 2026-06-07).
      - The 4-tick floor still applies (never tighter than tick-noise).

    Args:
        entry_price: Trade entry price.
        direction: "LONG" or "SHORT".
        structural_stop_price: Resolved anchor from resolver (already offset).
        family: S2 pattern family (determines ATR multiplier for the cap).
        today_typical: 75th percentile of today's 5-min bar ranges.
        atr_5m: Optional 5-min ATR for ATR-relative floor (when S2_ATR_RELATIVE on).
    """
    multiplier = ATR_MULTIPLIERS[family]
    floor = get_floor_ticks(atr_5m)

    # structural distance from entry, in ticks
    raw_ticks = int(round(abs(entry_price - structural_stop_price) / MES_TICK))
    floor_applied = raw_ticks < floor
    risk_ticks = max(raw_ticks, floor)

    if floor_applied:
        stop_price = (entry_price - risk_ticks * MES_TICK) if direction == "LONG" \
            else (entry_price + risk_ticks * MES_TICK)
    else:
        stop_price = structural_stop_price  # structural wins — untouched

    # ATR cap in ticks (today_typical × family_mult, converted to ticks)
    if today_typical > 0:
        atr_cap_ticks = int(multiplier * today_typical / MES_TICK)
    else:
        atr_cap_ticks = floor  # degenerate: no cap applied

    return StopComputationV2(
        stop_price=round(stop_price, 10),
        risk_ticks=risk_ticks,
        atr_cap_ticks=atr_cap_ticks,
        cap_exceeded=risk_ticks > atr_cap_ticks,
        floor_applied=floor_applied,
        today_typical=today_typical,
    )
