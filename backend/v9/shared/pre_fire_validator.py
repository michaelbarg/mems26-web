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
    t2_price: float = Field(gt=0)
    time_stop_minutes: int = Field(ge=1, le=180)
    confidence: int = Field(ge=0, le=100)


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
    reward = abs(req.t1_price - req.entry_price)
    if risk <= 0 or (reward / risk) < 1.0:
        return _fail(f"R:R < 1.0 (risk={risk:.2f} reward={reward:.2f})")

    return FireResponse(valid=True, fail_reason=None, validated_at=datetime.now(timezone.utc))


def _fail(reason: str) -> FireResponse:
    return FireResponse(valid=False, fail_reason=reason, validated_at=datetime.now(timezone.utc))
