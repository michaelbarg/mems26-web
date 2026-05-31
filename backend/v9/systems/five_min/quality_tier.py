"""Quality Tier V2 · Auth Table V1 (pattern x day_type x tier) -> contracts.

V1 signature retained as DeprecationWarning wrapper (Lock #6).
Production must use get_quality_tier_v2.

Pkg 8 · Quality V2 · Phase A mechanical · DEMO+ parametric calibration.
"""
from __future__ import annotations

import logging
import warnings
from typing import Literal, Optional, Tuple

import requests

from backend.v9.systems.five_min.auth_table_v1 import get_auth_cell

logger = logging.getLogger(__name__)

TPO_ENDPOINT: str = "http://localhost:8000/api/v9/tpo/current"
TPO_TIMEOUT_S: float = 2.0
PROXIMITY_PT: float = 2.0

# S2 ATR-relative proximity (E2E 2/2 · shadow only)
from backend.v9.shared.atr import S2_ATR_RELATIVE  # noqa: E402
_PROXIMITY_ATR_K = 1.25  # prior: 1.25×ATR5m


def get_proximity_pt(atr_5m=None) -> float:
    """Proximity threshold in points — ATR-relative when flag ON."""
    if S2_ATR_RELATIVE and atr_5m is not None:
        return _PROXIMITY_ATR_K * atr_5m
    return PROXIMITY_PT

QualityVerdict = Literal['FULL', 'REDUCED', 'SKIP']
QualityTier = Literal['HIGH', 'MEDIUM', 'LOW']

_V1_TIER_TO_CONTRACTS: dict = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}


def _classify_tier(price: float, tpo_data: Optional[dict]) -> QualityTier:
    if tpo_data is None:
        return 'MEDIUM'
    poc = tpo_data.get("poc") or tpo_data.get("poc_tpo")
    vah = tpo_data.get("vah")
    val = tpo_data.get("val")
    if poc is None or vah is None or val is None:
        return 'MEDIUM'
    for level in (poc, vah, val):
        if level is not None and abs(price - level) <= PROXIMITY_PT:
            return 'HIGH'
    if val <= price <= vah:
        return 'MEDIUM'
    return 'LOW'


def _fetch_tpo() -> Optional[dict]:
    try:
        r = requests.get(TPO_ENDPOINT, timeout=TPO_TIMEOUT_S)
        if r.status_code == 200:
            return r.json()
        logger.warning("[Pkg8/quality_tier] TPO status=%d · falling back to MEDIUM", r.status_code)
    except Exception as e:
        logger.warning("[Pkg8/quality_tier] TPO fetch failed: %s · falling back to MEDIUM", e)
    return None


def get_quality_tier_v2(
    pattern_name: str, day_type: str, price: float,
    *, tpo_data: Optional[dict] = None,
) -> Tuple[QualityVerdict, QualityTier, int]:
    """Return (verdict, tier, contracts) for (pattern x day_type x tier) cell."""
    if tpo_data is None:
        tpo_data = _fetch_tpo()
    tier: QualityTier = _classify_tier(price, tpo_data)
    verdict, high_c, med_c, low_c = get_auth_cell(pattern_name, day_type)
    contracts: int = {'HIGH': high_c, 'MEDIUM': med_c, 'LOW': low_c}[tier]
    return (verdict, tier, contracts)


def get_quality_tier(
    price: float, *, tpo_data: Optional[dict] = None,
) -> Tuple[QualityTier, int]:
    """DEPRECATED · V1 wrapper · use get_quality_tier_v2."""
    warnings.warn(
        "get_quality_tier() is deprecated · use get_quality_tier_v2(pattern_name, day_type, "
        "price, ...) per S2_AUTH_TABLE_V1.md §7.",
        DeprecationWarning, stacklevel=2,
    )
    if tpo_data is None:
        tpo_data = _fetch_tpo()
    tier: QualityTier = _classify_tier(price, tpo_data)
    return (tier, _V1_TIER_TO_CONTRACTS[tier])
