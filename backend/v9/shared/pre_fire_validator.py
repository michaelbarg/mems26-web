"""pre_fire_validator — M18 · D-063 · SHARED.

Gates every fire from T1/T2/T3.

7 checks per Strategic Chat S2 spec:
  1. system_id in {T1_NUMBER_BAR, T2_WOODIES, T3_FOOTPRINT}
  2. direction in {LONG, SHORT}
  3. stop side: LONG stop<entry · SHORT stop>entry
  4. T1/T2 ordering valid
  5. R:R >= 1.0
  6. confidence in [0,100]
  7. time_stop in [1,180]
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


VALID_SYSTEM_IDS = {'T1_NUMBER_BAR', 'T2_WOODIES', 'T3_FOOTPRINT'}


class FireRequest(BaseModel):
    system_id: Literal['T1_NUMBER_BAR', 'T2_WOODIES', 'T3_FOOTPRINT']
    direction: Literal['LONG', 'SHORT']
    entry_price: float = Field(gt=0)
    stop_price: float = Field(gt=0)
    t1_price: float = Field(gt=0)
    t2_price: Optional[float] = None  # None when CCI-cross targets deferred (§1.6)
    time_stop_minutes: int = Field(ge=1, le=180)
    confidence: int = Field(ge=0, le=100)
    # Expected runner multiplier (T2 ≈ expected_t2_r_mult × risk).
    # Used for R:R check when t2_price is None (CCI-cross deferred).
    # Default 2.0 = continuation patterns; 1.5 = reversal patterns.
    expected_t2_r_mult: float = Field(default=2.0, ge=1.0)


class FireResponse(BaseModel):
    valid: bool
    fail_reason: Optional[str] = None
    validated_at: datetime


def validate_fire(req: FireRequest) -> FireResponse:
    """Run 7 checks. Return valid + fail_reason."""
    if req.direction == 'LONG' and req.stop_price >= req.entry_price:
        return _fail("LONG: stop must be < entry")
    if req.direction == 'SHORT' and req.stop_price <= req.entry_price:
        return _fail("SHORT: stop must be > entry")

    # T2 may be None (CCI-cross targets deferred §1.6) — skip monotonicity when absent
    if req.t1_price is not None and req.t2_price is not None:
        if req.direction == 'LONG' and not (req.entry_price < req.t1_price < req.t2_price):
            return _fail("LONG: must have entry < t1 < t2")
        if req.direction == 'SHORT' and not (req.entry_price > req.t1_price > req.t2_price):
            return _fail("SHORT: must have entry > t1 > t2")
    elif req.t1_price is not None:
        if req.direction == 'LONG' and req.t1_price <= req.entry_price:
            return _fail("LONG: t1 must be > entry")
        if req.direction == 'SHORT' and req.t1_price >= req.entry_price:
            return _fail("SHORT: t1 must be < entry")

    risk = abs(req.entry_price - req.stop_price)
    # Stop-sanity gates (flag-gated, default OFF — env unset → no behaviour change).
    #   MEMS_MIN_RISK_POINTS — reject degenerate near-zero stops (the S2 1-pt
    #     Initiative/Bull-Flag stops that instant-stop for −1pt noise).
    #   MEMS_MAX_RISK_POINTS — reject oversized stops (e.g. a 110pt reversal
    #     swing anchor); the size gate can only shrink such a trade to 1
    #     contract, not refuse it. Applies to S2 + S4 (shared validator).
    _min_risk = float(os.getenv("MEMS_MIN_RISK_POINTS", "0") or 0)
    _max_risk = float(os.getenv("MEMS_MAX_RISK_POINTS", "0") or 0)
    if _min_risk > 0 and risk < _min_risk:
        return _fail(f"risk {risk:.2f}pt < min {_min_risk:.2f}pt (degenerate stop)")
    if _max_risk > 0 and risk > _max_risk:
        return _fail(f"risk {risk:.2f}pt > max {_max_risk:.2f}pt (oversized stop)")
    # R:R is measured against the RUNNER target (T2), not the scalp (T1).
    # T1 is a partial exit at 0.4-0.8R by design — using it for R:R would
    # block every valid trade. When T2 is None (CCI-cross deferred §1.6),
    # use the expected runner multiplier from the pattern spec.
    if req.t2_price is not None:
        reward = abs(req.t2_price - req.entry_price)
    else:
        reward = risk * req.expected_t2_r_mult
    if risk <= 0 or (reward / risk) < 1.0:
        # RR_BREAKOUT_MM_V1 (Michael ruling 2026-07-30 "תבצע אתה"; P5.1):
        # a concrete t2 anchored at the OLD session extreme measures zero room
        # exactly when the market is making NEW extremes — 07-29 21:40
        # DOUBLE_BOTTOM_EE_LONG @7444 rejected (reward 16.34 = distance to the
        # old high) and the market ran +38. When the capped t2 fails but the
        # PATTERN's expected runner multiple clears 1R, fall back to the spec
        # multiplier, conservatively capped at 1.5R. The trade still carries
        # its real (modest) t2 — this only stops the veto, it invents no
        # target. Loudly logged so the nightly counterfactual judges it.
        _bmm_on = os.getenv("RR_BREAKOUT_MM_V1", "0").lower() in ("1", "true", "yes")
        # Only genuine runner-class patterns rescue: spec mult must EXCEED
        # RR_BREAKOUT_MIN_MULT (1.5) — continuation=2.0 passes, reversal=1.5
        # does not. Without this, schema ge=1.0 would make the rescue universal.
        _mm_min = float(os.getenv("RR_BREAKOUT_MIN_MULT", "1.5") or 1.5)
        _mm_reward = risk * min(float(req.expected_t2_r_mult or 0.0), 1.5)
        if (_bmm_on and risk > 0 and req.t2_price is not None
                and float(req.expected_t2_r_mult or 0.0) > _mm_min
                and (_mm_reward / risk) >= 1.0):
            import logging as _bmm_logging
            _bmm_logging.getLogger(__name__).warning(
                "[pre_fire] RR_BREAKOUT_MM: capped-t2 R:R %.2f rescued by spec "
                "multiplier (risk=%.2f t2_reward=%.2f mm_reward=%.2f)",
                reward / risk, risk, reward, _mm_reward)
            return FireResponse(valid=True, fail_reason=None,
                                validated_at=datetime.now(timezone.utc))
        return _fail(f"R:R < 1.0 (risk={risk:.2f} reward={reward:.2f})")

    return FireResponse(valid=True, fail_reason=None, validated_at=datetime.now(timezone.utc))


def _fail(reason: str) -> FireResponse:
    return FireResponse(valid=False, fail_reason=reason, validated_at=datetime.now(timezone.utc))
