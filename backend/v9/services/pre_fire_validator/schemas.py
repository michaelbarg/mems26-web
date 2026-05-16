"""Pre-fire validator schemas — D-063."""

from typing import List, Optional
from pydantic import BaseModel


class FireRequest(BaseModel):
    """Request to validate before firing a trade signal."""
    system_id: str          # "S2", "S3", "S4"
    direction: str          # "LONG", "SHORT"
    entry_price: float
    stop_price: float
    targets: List[float] = []
    pattern_name: Optional[str] = None
    reasoning_notes: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of pre-fire validation."""
    passed: bool
    reasons: List[str] = []
    checks_run: int = 0
    checks_passed: int = 0
