"""contract_split — per-pattern T1/T2/T3 contract split percentages per D-091 §Contract Distribution.

Pure lookup module · no state · no I/O. Used by setup_emitter at emit time
to populate T1Setup.t1_pct / t2_pct / t3_pct fields.

Pkg 3c · emit-only. Pkg 6 (TradeManager) consumes these percentages and
applies rounding to integer contract counts based on T1Setup.sizing_contracts.

Authority: D-091 §Contract Distribution (lines 175-183 of D-091_S2_LIVE_SCOPE.md).
"""
from __future__ import annotations
from typing import Dict, Tuple

# Per-pattern split (T1, T2, T3) · each value in [0.0, 1.0] · sum = 1.0 ± 0.001
_SPLIT_MAP: Dict[str, Tuple[float, float, float]] = {
    # OFA family (Zohar 25/50/25)
    "REACTIVE_LONG":          (0.25, 0.50, 0.25),
    "REACTIVE_SHORT":         (0.25, 0.50, 0.25),
    "INITIATIVE_LONG":        (0.25, 0.50, 0.25),
    "INITIATIVE_SHORT":       (0.25, 0.50, 0.25),
    # H&S family (33/33/34)
    "INVERSE_HNS_LONG":       (0.33, 0.33, 0.34),
    "HNS_TOP_SHORT":          (0.33, 0.33, 0.34),
    # Double family (33/33/34)
    "DOUBLE_BOTTOM_EE_LONG":  (0.33, 0.33, 0.34),
    "DOUBLE_TOP_AA_SHORT":    (0.33, 0.33, 0.34),
    # Flag family (50/50 · no T3 · continuation)
    "BULL_FLAG_LONG":         (0.50, 0.50, 0.00),
    "BEAR_FLAG_SHORT":        (0.50, 0.50, 0.00),
}

# Import-time invariant: every entry sums to 1.0 ± 0.001
for _name, _split in _SPLIT_MAP.items():
    _sum = sum(_split)
    assert abs(_sum - 1.0) < 0.001, f"contract_split: {_name} sums to {_sum:.4f} != 1.0"


def get_contract_split(pattern_name: str) -> Tuple[float, float, float]:
    """Return (t1_pct, t2_pct, t3_pct) for the given pattern.

    Raises ValueError if pattern_name is not registered.
    NO silent fallback — pre-LIVE protocol forbids silent failures.
    """
    split = _SPLIT_MAP.get(pattern_name)
    if split is None:
        raise ValueError(
            f"contract_split: pattern_name={pattern_name!r} not registered. "
            f"Known patterns: {sorted(_SPLIT_MAP.keys())}"
        )
    return split
