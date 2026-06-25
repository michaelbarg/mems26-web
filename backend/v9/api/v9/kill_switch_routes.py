"""Kill-switch API — engage/disengage/status.

POST /api/v9/admin/kill    → engage (halt all fires)
POST /api/v9/admin/resume  → disengage (resume fires)
GET  /api/v9/admin/kill    → current status
"""
from fastapi import APIRouter

from backend.v9.services.kill_switch import engage, disengage, status

router = APIRouter(prefix="/api/v9/admin", tags=["admin"])


@router.post("/kill")
def kill_engage(reason: str = "manual", by: str = "api"):
    engage(reason=reason, by=by)
    return {"status": "engaged", **status()}


@router.post("/resume")
def kill_resume(by: str = "api"):
    disengage(by=by)
    return {"status": "disengaged", **status()}


@router.get("/kill")
def kill_status():
    return status()
