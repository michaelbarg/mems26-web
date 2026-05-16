"""API route: POST /api/v9/pre_fire/validate — D-063 pre-fire validation."""

from fastapi import APIRouter
from backend.v9.services.pre_fire_validator.schemas import FireRequest, ValidationResult
from backend.v9.services.pre_fire_validator.validator import PreFireValidator

router = APIRouter(prefix="/api/v9/pre_fire", tags=["pre-fire"])

_validator = PreFireValidator()


@router.post("/validate", response_model=ValidationResult)
def validate_fire(req: FireRequest):
    """Validate a fire request before trade signal emission."""
    return _validator.validate(req)
