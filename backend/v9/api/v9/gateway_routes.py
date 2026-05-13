"""API routes for Trading Gateway status + manual route_setup (P-TG.5)."""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v9/gateway", tags=["gateway"])


@router.get("/status")
async def gateway_status(request: Request):
    """Return gateway slot states, daily PnL, trade count."""
    gw = getattr(request.app.state, "trading_gateway", None)
    if gw is None:
        return {"running": False, "error": "TradingGateway not initialized"}
    return gw.get_status()


class RouteSetupIn(BaseModel):
    firing_system: int
    direction: str
    classification: Optional[str] = None
    confidence: Optional[float] = 0.75
    entry_price: Optional[float] = None
    stop: Optional[float] = 0.0
    t1: Optional[float] = 0.0
    t2: Optional[float] = 0.0
    t3: Optional[float] = 0.0


@router.post("/route_setup")
async def gateway_route_setup(request: Request, payload: RouteSetupIn):
    """Manually route a trade setup through the gateway (for testing)."""
    gw = getattr(request.app.state, "trading_gateway", None)
    if gw is None:
        return {"error": "TradingGateway not initialized"}
    result = gw.route_setup(payload.dict(), payload.firing_system)
    return {"routed": result}
