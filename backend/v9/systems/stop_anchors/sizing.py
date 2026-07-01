"""V2 sizing pipeline — wraps resolver.final_contracts + classify_mode + auth lookup.

One function: `compute_v2_sizing()` returns (contracts, t1_price, mode_result).
Called from the V2 branch in pattern wiring; pure except for config reads.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from backend.v9.systems.stop_anchors import resolver as SA

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class V2SizingResult:
    contracts: int
    t1_price: float
    mode: str               # "strategic" | "tactical"
    mode_cap: int
    mode_reason: str
    auth_verdict: str       # "FULL" | "INITIATIVE" | "SKIP"
    auth_contracts: int     # from Table B for this confidence tier
    ladder_contracts: int   # from the risk ladder alone
    risk_points: float


def compute_v2_sizing(
    *,
    entry_price: float,
    stop_price: float,
    direction: str,
    pattern_key: str,        # YAML anchor key (e.g. "ZLR", "OFA_Initiative")
    day_type: str,           # current day_type classification
    confidence_tier: str,    # "high" | "medium" | "low"
    day_has_direction: bool,
    trade_with_trend: Optional[bool],
    value_area_full_traverse: Optional[bool],
    cfg: Dict[str, Any],     # loaded stop_anchors.yaml
    auth_matrix: Optional[Dict[Tuple[str, str], Tuple[str, int, int, int]]] = None,
    reversal: bool = False,
    ladder_shift: int = 0,
) -> Optional[V2SizingResult]:
    """Full V2 sizing: risk → contracts + T1.

    Returns None if auth verdict is SKIP (no trade).
    """
    risk_pts = SA.risk_points(entry_price, stop_price)

    # ── Auth matrix lookup ──
    auth_verdict = "FULL"
    auth_contracts = cfg.get("guardrails", {}).get("max_contracts", 3)
    if auth_matrix:
        cell = auth_matrix.get((pattern_key, day_type))
        if cell:
            verdict, high, medium, low = cell
            auth_verdict = verdict
            if auth_verdict == "SKIP":
                return None
            tier_map = {"high": high, "medium": medium, "low": low}
            auth_contracts = tier_map.get(confidence_tier, low)
        else:
            logger.warning("[V2Sizing] no auth cell for (%s, %s) — using max", pattern_key, day_type)

    # ── Mode classification ──
    mode_result = SA.classify_mode(
        day_has_direction=day_has_direction,
        trade_with_trend=trade_with_trend,
        value_area_full_traverse=value_area_full_traverse,
        strategic_cap=cfg["mode_caps"]["strategic"],
        tactical_cap=cfg["mode_caps"]["tactical"],
    )

    # ── Contract ladder ──
    ladder_contracts = SA.contracts_from_risk(risk_pts, cfg["contract_ladder"])

    # ── Final contracts (most conservative wins) ──
    contracts = SA.final_contracts(risk_pts, cfg["contract_ladder"],
                                   auth_contracts, mode_result.cap)

    # FIXED_CONTRACTS_3 (Michael 2026-07-01): every trade that FIRES uses 3
    # contracts — override the risk-ladder/auth/mode minimum. Reject (0) is
    # preserved so invalid setups still don't fire. Applies to S2 + S4 (both
    # route through compute_v2_sizing). Trading-risk → flag-gated.
    import os as _fc_os
    if _fc_os.environ.get("FIXED_CONTRACTS_3", "0").lower() in ("1", "true", "yes") and contracts > 0:
        contracts = 3

    # ── T1 price ──
    anchor_cfg = cfg["anchors"].get(pattern_key, {})
    t1_shift = anchor_cfg.get("t1_ladder_shift", ladder_shift)
    import os as _sz_os
    _sz_v2 = _sz_os.environ.get("T1_LADDER_V2", "0").lower() in ("1", "true", "yes")
    t1 = SA.t1_price(
        entry_price, stop_price, direction,
        t1_ladder_cont=cfg.get("t1_ladder_continuation_v2", cfg["t1_ladder_continuation"]) if _sz_v2 else cfg["t1_ladder_continuation"],
        reversal=reversal,
        reversal_mult=cfg.get("t1_reversal_multiplier_v2", 0.8) if _sz_v2 else cfg.get("t1_reversal_multiplier", 0.8),
        t1_floor_points=cfg.get("t1_floor_points", 3.0),
        ladder_shift=t1_shift,
    )

    return V2SizingResult(
        contracts=contracts,
        t1_price=t1,
        mode=mode_result.mode,
        mode_cap=mode_result.cap,
        mode_reason=mode_result.reason,
        auth_verdict=auth_verdict,
        auth_contracts=auth_contracts,
        ladder_contracts=ladder_contracts,
        risk_points=risk_pts,
    )
