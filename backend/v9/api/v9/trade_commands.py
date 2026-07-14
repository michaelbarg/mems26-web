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

VALID_ACTIONS = {"BUY", "SELL", "CANCEL", "MODIFY", "STATUS", "FLATTEN",
                 # FIX-11 (2026-07-10, orphan 8704): account-level flatten —
                 # NOT gated on an armed bracket in the DLL. Closes manual/
                 # orphan positions the bracket-scoped ops can't touch.
                 "FLATTEN_ACCOUNT",
                 # EXIT (2026-07-13): the automated partial-exit op (write_exit →
                 # op="EXIT" → DLL sc.SellExit/BuyExit). Exposed so the DLL EXIT
                 # handler is testable via the API (was internal-only → the fix
                 # was never verified end-to-end; the 07-13 report tested raw SELL
                 # = op=PLACE entry, a different path). Routed to write_exit below.
                 "EXIT"}


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
        # EXIT — the PARTIAL-EXIT op the automated path uses (manager.py write_exit
        # → op="EXIT" → DLL sc.SellExit/BuyExit). It was reachable ONLY internally,
        # so the DLL EXIT handler could never be tested end-to-end via the API
        # (07-13 regression report: the tester fell back to raw SELL = op=PLACE
        # entry, a DIFFERENT path). Route action=EXIT to the real write_exit so a
        # SIM test can prove the ScaleOut/TIF fix on the actual production op.
        if action == "EXIT":
            from backend.v9.services.sierra_command import write_exit
            _dir = None
            if isinstance(cmd.context, dict):
                _dir = cmd.context.get("direction")
            command = write_exit(
                trade_id=str(cmd.trade_id or ""),
                order_id=int(cmd.sierra_bracket_id or 0),
                contracts=int(cmd.contracts or 1),
                direction=_dir,
                mode=(cmd.context or {}).get("mode", "demo") if isinstance(cmd.context, dict) else "demo",
            )
        else:
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
def debug_gateway_fire(request: _FReq, classification: str = "SIM_TEST",
                       pattern: str = "", stop_pts: float = 8.0,
                       sizing: str = "full", direction: str = "LONG"):
    """SIM-ONLY: fire a minimal setup through the LIVE gateway to create a TM trade.

    This proves the full round-trip: gateway → accept_setup → trade_command.json →
    Sierra → trade_fills.json → FillPoller → TM trade captured. Remove after SIM proof.

    Query params (SIM test harness, 2026-07-14): classification/pattern (e.g. ZLR to
    exercise ZLR_MGMT_V1), stop_pts (wide stop → exercise SIZE_CAP_OVER_FIXED_V1),
    sizing (full/half/quarter), direction. Defaults reproduce the original SIM_TEST.
    """
    gw = getattr(request.app.state, "trading_gateway", None)
    if gw is None:
        raise HTTPException(status_code=500, detail="No trading_gateway on app.state")

    # Read live price
    lp_path = Path("/Users/michael/SierraChart_Data/v9_export/live_price.json")
    if not lp_path.exists():
        raise HTTPException(status_code=500, detail="No live_price.json")
    lp = json.load(open(lp_path))
    # 2026-07-09 drill finding: the DLL's "price" (last-trade) field can freeze
    # while bid/ask keep updating (trade 326 fired 24pt off-market → the whole
    # bracket insta-filled). Prefer the bid/ask mid, tick-rounded.
    if lp.get("bid") and lp.get("ask"):
        price = round((float(lp["bid"]) + float(lp["ask"])) / 2 / 0.25) * 0.25
    else:
        price = float(lp["price"])

    _sign = 1.0 if str(direction).upper() == "LONG" else -1.0
    setup = {
        "firing_system": 4,
        "direction": str(direction).upper(),
        "classification": classification,
        "confidence": 0.90,
        "entry_price": price,
        "stop": round(price - _sign * float(stop_pts), 2),
        "t1": round(price + _sign * 8, 2),
        "t2": round(price + _sign * 16, 2),
        "t3": round(price + _sign * 24, 2),
        "metadata": {"pattern": pattern or classification, "sizing": sizing, "sim_proof": True},
    }

    # Try route_setup first (respects all gates). If blocked by session_gate
    # (market closed), fall back to direct _execute_demo for SIM proof.
    result = gw.route_setup(setup, system_id=4)
    if result.get("blocked_by") in ("session_gate_closed", "eod_entry_cutoff"):
        # SIM proof bypass: call _execute_demo directly (creates TM trade + Sierra command)
        logger.warning("[debug_gateway_fire] %s — bypassing for SIM proof", result["blocked_by"])
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
