"""structural_targets — resolve day-type targets to structural price levels.

When daytype_style[day_type].target == "location" (Normal, Variation,
Neutral_Center, Neutral_Extreme), this resolver computes C1/C2/C3 from
TPO structural levels (IB edges, POC, VAH, VAL) instead of R-multiples.

Michael's spec (S1_TRADE_MANAGEMENT_3CONTRACTS.md, 2026-06-20):
  Normal day SHORT from IBH: C1=IB-center, C2=VAL, C3=IBL (trail)
  Normal day LONG from IBL:  C1=IB-center, C2=VAH, C3=IBH (trail)

Flag: DAYTYPE_TARGETS_STRUCTURAL (default OFF). When OFF, returns None
(caller falls back to R-based targets). Fail-safe: any missing level
→ returns None.

Reads daytype_style from config/daytype_playbook.yaml (same file as
the playbook — no duplicate config).
"""
from __future__ import annotations

import logging
import os
from typing import Dict, Literal, Optional

logger = logging.getLogger(__name__)

# Lazy-load the YAML config (same file as daytype_playbook)
_daytype_style: Optional[Dict] = None


def _load_style() -> Dict:
    global _daytype_style
    if _daytype_style is not None:
        return _daytype_style
    try:
        import yaml
        with open("config/daytype_playbook.yaml", "r") as f:
            cfg = yaml.safe_load(f)
        _daytype_style = cfg.get("daytype_style", {})
    except Exception as e:
        logger.warning("[structural_targets] YAML load failed: %s — disabled", e)
        _daytype_style = {}
    return _daytype_style


def resolve_structural_targets(
    *,
    day_type: Optional[str],
    direction: Literal["LONG", "SHORT"],
    entry_price: float,
    stop_price: float,
    tpo_ctx: Optional[Dict],
) -> Optional[Dict]:
    """Resolve structural targets for location-based day types.

    Returns dict with c1/c2/c3 prices, contracts, time_stop, trail flag.
    Returns None when:
      - flag OFF (default)
      - day_type is not location-based
      - required TPO levels missing (fail-safe)

    The caller should fall back to R-based targets when this returns None.
    """
    if not os.getenv("DAYTYPE_TARGETS_STRUCTURAL", "0").lower() in ("1", "true", "yes"):
        return None

    if day_type is None or tpo_ctx is None:
        return None

    style = _load_style().get(day_type)
    if style is None:
        return None
    target_type = style.get("target")
    if target_type not in ("location", "movement"):
        return None

    # Extract structural levels from TPO context
    ib_high = tpo_ctx.get("ib_high")
    ib_low = tpo_ctx.get("ib_low")
    poc = tpo_ctx.get("poc")
    vah = tpo_ctx.get("vah")
    val = tpo_ctx.get("val")

    # All IB levels required for Normal; fail-safe if missing
    if ib_high is None or ib_low is None or poc is None:
        logger.debug(
            "[structural_targets] missing levels for %s (ibh=%s ibl=%s poc=%s) — fail-safe to R-based",
            day_type, ib_high, ib_low, poc,
        )
        return None

    ib_center = (ib_high + ib_low) / 2.0

    # Resolve per day-type + direction
    if day_type == "Normal":
        return _resolve_normal(direction, entry_price, stop_price,
                               ib_high, ib_low, ib_center, poc, vah, val)
    elif day_type == "Variation":
        return _resolve_variation(direction, entry_price, stop_price,
                                  ib_high, ib_low, ib_center, poc, vah, val)
    elif day_type == "Neutral_Extreme":
        return _resolve_neutral_extreme(direction, entry_price, stop_price,
                                         ib_high, ib_low, ib_center, poc, vah, val)
    elif day_type == "Neutral_Center":
        return _resolve_neutral_center(direction, entry_price, stop_price,
                                        ib_high, ib_low, ib_center, poc, vah, val)
    elif day_type == "Trend_Normal":
        return _resolve_trend_normal(direction, entry_price, stop_price,
                                      ib_high, ib_low, ib_center, poc, vah, val,
                                      tpo_ctx)
    elif day_type == "Trend_DD":
        return _resolve_trend_dd(direction, entry_price, stop_price,
                                  ib_high, ib_low, ib_center, poc, vah, val,
                                  tpo_ctx)
    return None


def _resolve_normal(
    direction: str, entry: float, stop: float,
    ibh: float, ibl: float, ib_center: float,
    poc: float, vah: Optional[float], val: Optional[float],
) -> Dict:
    """Normal day: fade IB edges. 3 contracts.

    SHORT from IBH area: C1=IB-center, C2=VAL, C3=IBL (trail)
    LONG from IBL area:  C1=IB-center, C2=VAH, C3=IBH (trail)
    """
    if direction == "SHORT":
        c1 = ib_center
        c2 = val if val is not None else ibl
        c3 = ibl
    else:  # LONG
        c1 = ib_center
        c2 = vah if vah is not None else ibh
        c3 = ibh

    return _build_result(
        direction=direction, entry=entry,
        c1=c1, c2=c2, c3=c3,
        contracts=3,
        time_stop_minutes=30,
        trail_after_c2=True,
        day_type="Normal",
    )


def _resolve_variation(
    direction: str, entry: float, stop: float,
    ibh: float, ibl: float, ib_center: float,
    poc: float, vah: Optional[float], val: Optional[float],
) -> Dict:
    """Variation day: go WITH IB expansion (not fade). 3 contracts.

    LONG (IB expanding up): C1=half IB extension, C2=1×IB above IBH, C3=trail
    SHORT (IB expanding down): C1=half IB extension, C2=1×IB below IBL, C3=trail
    """
    ib_width = ibh - ibl
    if ib_width <= 0:
        return None

    if direction == "LONG":
        c1 = ibh + ib_width * 0.5   # half extension above IBH
        c2 = ibh + ib_width         # 1×IB above IBH
        c3 = ibh + ib_width * 1.5   # trail target
    else:  # SHORT
        c1 = ibl - ib_width * 0.5
        c2 = ibl - ib_width
        c3 = ibl - ib_width * 1.5

    return _build_result(
        direction=direction, entry=entry,
        c1=c1, c2=c2, c3=c3,
        contracts=3,
        time_stop_minutes=60,
        trail_after_c2=True,
        day_type="Variation",
    )


def _resolve_neutral_extreme(
    direction: str, entry: float, stop: float,
    ibh: float, ibl: float, ib_center: float,
    poc: float, vah: Optional[float], val: Optional[float],
) -> Dict:
    """Neutral Extreme: fade VA edges to POC, trail toward winner. 3 contracts.

    SHORT from VAH area: C1=POC, C2=opposite edge (VAL/IBL), C3=winning extreme (trail)
    LONG from VAL area:  C1=POC, C2=opposite edge (VAH/IBH), C3=winning extreme (trail)
    """
    if direction == "SHORT":
        c1 = poc
        c2 = val if val is not None else ibl
        c3 = ibl  # trail toward winning extreme
    else:
        c1 = poc
        c2 = vah if vah is not None else ibh
        c3 = ibh

    return _build_result(
        direction=direction, entry=entry,
        c1=c1, c2=c2, c3=c3,
        contracts=3,
        time_stop_minutes=45,
        trail_after_c2=True,
        day_type="Neutral_Extreme",
    )


def _resolve_neutral_center(
    direction: str, entry: float, stop: float,
    ibh: float, ibl: float, ib_center: float,
    poc: float, vah: Optional[float], val: Optional[float],
) -> Dict:
    """Neutral Center: fade edges to center. 3 contracts.

    SHORT: C1=POC, C2=opposite IB edge (IBL), C3=trail
    LONG:  C1=POC, C2=opposite IB edge (IBH), C3=trail
    """
    if direction == "SHORT":
        c2 = ibl
        c3 = ibl  # same as C2 for NeuC (no runner beyond)
    else:
        c2 = ibh
        c3 = ibh

    return _build_result(
        direction=direction, entry=entry,
        c1=poc, c2=c2, c3=c3,
        contracts=3,
        time_stop_minutes=30,
        trail_after_c2=False,
        day_type="Neutral_Center",
    )


def _resolve_trend_normal(
    direction: str, entry: float, stop: float,
    ibh: float, ibl: float, ib_center: float,
    poc: float, vah: Optional[float], val: Optional[float],
    tpo_ctx: Optional[Dict],
) -> Optional[Dict]:
    """Trend Normal: WITH trend from open; structural checkpoints. 3 contracts.

    LONG (uptrend): C1=remote checkpoint (2×IB above IBH), C2=PDH, C3=hold-to-close (trail)
    SHORT (downtrend): C1=remote checkpoint (2×IB below IBL), C2=PDL, C3=hold-to-close (trail)
    Movement-based but uses IB/PD levels as structural anchors.
    """
    ib_width = ibh - ibl
    if ib_width <= 0:
        return None

    pdh = tpo_ctx.get("pd_high") if tpo_ctx else None
    pdl = tpo_ctx.get("pd_low") if tpo_ctx else None

    if direction == "LONG":
        c1 = ibh + ib_width * 2.0  # remote checkpoint
        c2 = pdh if pdh is not None and pdh > c1 else c1 + ib_width
        c3 = c2 + ib_width  # trail target
    else:  # SHORT
        c1 = ibl - ib_width * 2.0
        c2 = pdl if pdl is not None and pdl < c1 else c1 - ib_width
        c3 = c2 - ib_width

    return _build_result(
        direction=direction, entry=entry,
        c1=c1, c2=c2, c3=c3,
        contracts=3,
        time_stop_minutes=None,  # no time stop on Trend_Normal
        trail_after_c2=True,
        day_type="Trend_Normal",
    )


def _resolve_trend_dd(
    direction: str, entry: float, stop: float,
    ibh: float, ibl: float, ib_center: float,
    poc: float, vah: Optional[float], val: Optional[float],
    tpo_ctx: Optional[Dict],
) -> Optional[Dict]:
    """Trend DD: CONT after breakout from structure. 3 contracts.

    LONG: C1=distribution POC (or IBH+IB), C2=measured move, C3=trail behind structure
    SHORT: mirror
    """
    ib_width = ibh - ibl
    if ib_width <= 0:
        return None

    if direction == "LONG":
        c1 = ibh + ib_width  # distribution POC proxy
        c2 = ibh + ib_width * 2.0  # measured move
        c3 = c2 + ib_width  # trail
    else:
        c1 = ibl - ib_width
        c2 = ibl - ib_width * 2.0
        c3 = c2 - ib_width

    return _build_result(
        direction=direction, entry=entry,
        c1=c1, c2=c2, c3=c3,
        contracts=3,
        time_stop_minutes=90,
        trail_after_c2=True,
        day_type="Trend_DD",
    )


def _build_result(
    *,
    direction: str,
    entry: float,
    c1: Optional[float],
    c2: Optional[float],
    c3: Optional[float],
    contracts: int,
    time_stop_minutes: Optional[int],
    trail_after_c2: bool,
    day_type: str,
) -> Optional[Dict]:
    """Build result dict. Validates targets are on correct side of entry."""
    # Sanity: targets must be on the correct side of entry
    if c1 is not None:
        if direction == "LONG" and c1 <= entry:
            logger.debug("[structural_targets] %s LONG c1=%.2f <= entry=%.2f — fail-safe",
                         day_type, c1, entry)
            return None
        if direction == "SHORT" and c1 >= entry:
            logger.debug("[structural_targets] %s SHORT c1=%.2f >= entry=%.2f — fail-safe",
                         day_type, c1, entry)
            return None

    return {
        "t1_price": c1,
        "t2_price": c2,
        "t3_price": c3,
        "contracts": contracts,
        "time_stop_minutes": time_stop_minutes,
        "trail_after_t2": trail_after_c2,
        "structural": True,  # marker for audit
        "day_type": day_type,
        "no_trade": False,
    }
