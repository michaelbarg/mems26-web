"""V9 API: Trade command/result endpoints for DLL communication.

POST /api/v9/trade/command — submit a trade command (bridge forwards to DLL)
GET  /api/v9/trade/result  — read the latest trade result
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.v9.api.v9.auth import verify_bridge_token
from backend.v9.services.sierra_command import command_file, signals_dir, write_trade_command

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v9/trade", tags=["v9-trade-commands"])

SIGNALS_DIR = signals_dir()
COMMAND_FILE = command_file()
RESULT_FILE = SIGNALS_DIR / "trade_result.json"

VALID_ACTIONS = {"BUY", "SELL", "CANCEL", "MODIFY", "STATUS", "FLATTEN"}


class TradeCommandIn(BaseModel):
    action: str
    trade_id: Optional[str] = None
    price: Optional[float] = None
    contracts: Optional[int] = None
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    sierra_bracket_id: Optional[str] = None
    context: Optional[dict] = None


@router.post("/command")
def submit_trade_command(
    cmd: TradeCommandIn,
    _token: str = Depends(verify_bridge_token),
):
    """Submit a trade command. Writes to trade_command.json for bridge/DLL.

    For STATUS commands, returns ACK immediately.
    For execution commands, the bridge polls DLL for result.
    """
    action = cmd.action.upper()
    if action not in VALID_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action: {action}. Valid: {', '.join(sorted(VALID_ACTIONS))}",
        )

    try:
        command = write_trade_command(
            action=action,
            trade_id=cmd.trade_id,
            price=cmd.price,
            contracts=cmd.contracts,
            stop_price=cmd.stop_price,
            target_price=cmd.target_price,
            context={**(cmd.context or {}), "sierra_bracket_id": cmd.sierra_bracket_id},
        )
        logger.info(f"[trade_cmd_api] Command written: {action} trade_id={cmd.trade_id}")
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Failed to write command: {e}")

    # STATUS returns ACK immediately
    if action == "STATUS":
        result = {
            "status": "ACK",
            "action": action,
            "trade_id": cmd.trade_id,
            "ts": time.time(),
            "message": "Status request acknowledged",
        }
        _write_result(result)
        return result

    # For other commands, return ACK — bridge will process asynchronously
    return {
        "status": "ACK",
        "action": action,
        "trade_id": cmd.trade_id,
        "ts": time.time(),
        "message": f"Command {action} queued for bridge processing",
    }


@router.get("/result")
def get_trade_result(
    _token: str = Depends(verify_bridge_token),
):
    """Read the latest trade result from trade_result.json."""
    if not RESULT_FILE.exists():
        return {"status": "NO_RESULT", "ts": time.time(), "message": "No trade result available"}

    try:
        with open(RESULT_FILE, "r") as f:
            result = json.load(f)
        return result
    except (json.JSONDecodeError, IOError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to read result: {e}")


from fastapi import Request as _FReq

@router.post("/debug_gateway_fire")
def debug_gateway_fire(request: _FReq):
    """SIM-ONLY: fire a minimal setup through the LIVE gateway to create a TM trade.

    This proves the full round-trip: gateway → accept_setup → trade_command.json →
    Sierra → trade_fills.json → FillPoller → TM trade captured. Remove after SIM proof.
    """
    gw = getattr(request.app.state, "trading_gateway", None)
    if gw is None:
        raise HTTPException(status_code=500, detail="No trading_gateway on app.state")

    # Read live price
    lp_path = Path("/Users/michael/SierraChart_Data/v9_export/live_price.json")
    if not lp_path.exists():
        raise HTTPException(status_code=500, detail="No live_price.json")
    lp = json.load(open(lp_path))
    price = float(lp["price"])

    setup = {
        "firing_system": 4,
        "direction": "LONG",
        "classification": "SIM_TEST",
        "confidence": 0.90,
        "entry_price": price,
        "stop": round(price - 8, 2),
        "t1": round(price + 8, 2),
        "t2": round(price + 16, 2),
        "t3": round(price + 24, 2),
        "metadata": {"pattern": "SIM_TEST", "sizing": "full", "sim_proof": True},
    }

    # Try route_setup first (respects all gates). If blocked by session_gate
    # (market closed), fall back to direct _execute_demo for SIM proof.
    result = gw.route_setup(setup, system_id=4)
    if result.get("blocked_by") == "session_gate_closed":
        # SIM proof bypass: call _execute_demo directly (creates TM trade + Sierra command)
        logger.warning("[debug_gateway_fire] session_gate_closed — bypassing for SIM proof")
        demo_result = gw._execute_demo(setup, system_id=4, cross_context={})
        return {
            "status": "FIRED_DIRECT",
            "setup": setup,
            "demo_result": demo_result,
            "ts": time.time(),
        }
    return {
        "status": "FIRED",
        "setup": setup,
        "gateway_result": result,
        "ts": time.time(),
    }


def _write_result(result: dict):
    """Write result to signals dir."""
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(RESULT_FILE, "w") as f:
            json.dump(result, f, indent=2)
    except IOError as e:
        logger.warning(f"[trade_cmd_api] Failed to write result: {e}")
