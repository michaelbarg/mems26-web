"""V9 API: System configs — GET/PUT per system."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.v9.db.session import get_db
from backend.v9.db.models import V9SystemConfig
from backend.v9.api.v9.auth import verify_bridge_token

router = APIRouter(prefix="/api/v9/configs", tags=["v9-configs"])


class ConfigUpdate(BaseModel):
    params: dict
    locked_by: Optional[str] = None


@router.get("")
def get_all_configs(
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    rows = db.query(V9SystemConfig).order_by(V9SystemConfig.system_id).all()
    return {"configs": [
        {"id": r.id, "system_id": r.system_id, "mode": r.mode,
         "params": r.params,
         "locked_at": r.locked_at.isoformat() if r.locked_at else None,
         "locked_by": r.locked_by}
        for r in rows
    ]}


@router.get("/{system_id}/{mode}")
def get_config(
    system_id: int,
    mode: str,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    row = db.query(V9SystemConfig).filter(
        V9SystemConfig.system_id == system_id,
        V9SystemConfig.mode == mode,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Config not found")
    return {
        "system_id": row.system_id, "mode": row.mode,
        "params": row.params,
        "locked_at": row.locked_at.isoformat() if row.locked_at else None,
        "locked_by": row.locked_by,
    }


@router.put("/{system_id}/{mode}")
def upsert_config(
    system_id: int,
    mode: str,
    update: ConfigUpdate,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    row = db.query(V9SystemConfig).filter(
        V9SystemConfig.system_id == system_id,
        V9SystemConfig.mode == mode,
    ).first()

    if row:
        if row.locked_at:
            raise HTTPException(status_code=409, detail="Config is locked")
        row.params = update.params
        row.updated_at = datetime.now(timezone.utc)
        if update.locked_by:
            row.locked_at = datetime.now(timezone.utc)
            row.locked_by = update.locked_by
    else:
        row = V9SystemConfig(
            system_id=system_id,
            mode=mode,
            params=update.params,
        )
        if update.locked_by:
            row.locked_at = datetime.now(timezone.utc)
            row.locked_by = update.locked_by
        db.add(row)

    db.commit()
    return {"ok": True, "system_id": system_id, "mode": mode}
