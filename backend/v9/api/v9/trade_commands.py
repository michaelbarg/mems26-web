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


def _write_result(result: dict):
    """Write result to signals dir."""
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(RESULT_FILE, "w") as f:
            json.dump(result, f, indent=2)
    except IOError as e:
        logger.warning(f"[trade_cmd_api] Failed to write result: {e}")
