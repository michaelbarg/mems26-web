"""Sierra command file writer for DEMO/LIVE execution paths.

Writes the command format consumed by the Bridge/DLL through
`trade_command.json`. This module has no network or broker side effects.

Pipeline 5 Phase 2: extended with op-based dispatch:
  PLACE     — entry bracket (existing BUY/SELL)
  MODIFY_STOP   — move stop on tracked order
  MODIFY_TARGET — move target on tracked order
  EXIT          — market exit N contracts (partial or full)
  CANCEL        — kill working orders / flatten
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("sierra_command")

DEFAULT_SIGNALS_DIR = Path("/tmp/mems26_signals")


def signals_dir() -> Path:
    return Path(os.getenv("MEMS26_SIGNALS_DIR", str(DEFAULT_SIGNALS_DIR)))


def command_file() -> Path:
    return signals_dir() / "trade_command.json"


def _write_command(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Write a command payload to the command file."""
    out = command_file()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    logger.info("[SierraCmd] wrote %s (op=%s)", out, payload.get("op") or payload.get("action"))
    return payload


def write_trade_command(
    *,
    action: str,
    trade_id: Optional[str],
    direction: Optional[str] = None,
    price: Optional[float] = None,
    contracts: Optional[int] = None,
    stop_price: Optional[float] = None,
    target_price: Optional[float] = None,
    account: Optional[str] = None,
    mode: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Write a PLACE (entry bracket) Sierra command."""
    action = action.upper()
    payload = {
        "op": "PLACE",
        "action": action,
        "trade_id": trade_id,
        "direction": direction,
        "price": price,
        "contracts": contracts,
        "stop_price": stop_price,
        "target_price": target_price,
        "account": account,
        "mode": mode,
        "context": context or {},
        "ts_submitted": time.time(),
    }
    return _write_command(payload)


def write_modify_stop(
    *,
    trade_id: str,
    order_id: int,
    new_stop: float,
    mode: str = "demo",
) -> Dict[str, Any]:
    """Write a MODIFY_STOP command — trail/re-anchor the protective stop."""
    return _write_command({
        "op": "MODIFY_STOP",
        "trade_id": trade_id,
        "order_id": order_id,
        "new_stop": new_stop,
        "mode": mode,
        "ts_submitted": time.time(),
    })


def write_modify_target(
    *,
    trade_id: str,
    order_id: int,
    new_target: float,
    mode: str = "demo",
) -> Dict[str, Any]:
    """Write a MODIFY_TARGET command — re-anchor the next target."""
    return _write_command({
        "op": "MODIFY_TARGET",
        "trade_id": trade_id,
        "order_id": order_id,
        "new_target": new_target,
        "mode": mode,
        "ts_submitted": time.time(),
    })


def write_exit(
    *,
    trade_id: str,
    order_id: int,
    contracts: int,
    mode: str = "demo",
) -> Dict[str, Any]:
    """Write an EXIT command — market exit N contracts (partial or full)."""
    return _write_command({
        "op": "EXIT",
        "trade_id": trade_id,
        "order_id": order_id,
        "contracts": contracts,
        "mode": mode,
        "ts_submitted": time.time(),
    })


def write_cancel(
    *,
    trade_id: str,
    order_id: Optional[int] = None,
    mode: str = "demo",
) -> Dict[str, Any]:
    """Write a CANCEL command — kill working orders / flatten."""
    return _write_command({
        "op": "CANCEL",
        "trade_id": trade_id,
        "order_id": order_id,
        "mode": mode,
        "ts_submitted": time.time(),
    })


def command_from_setup(
    setup: Dict[str, Any],
    *,
    trade_id: str,
    account: str,
    mode: str,
) -> Dict[str, Any]:
    direction = (setup.get("direction") or "").upper()
    if direction not in {"LONG", "SHORT"}:
        raise ValueError(f"Unsupported direction for Sierra command: {direction}")
    action = "BUY" if direction == "LONG" else "SELL"
    return write_trade_command(
        action=action,
        trade_id=trade_id,
        direction=direction,
        price=setup.get("entry_price"),
        contracts=int(setup.get("contracts") or setup.get("size") or 1),
        stop_price=setup.get("stop") or setup.get("stop_price"),
        target_price=setup.get("t1") or setup.get("target_price"),
        account=account,
        mode=mode,
        context={
            "firing_system": setup.get("firing_system"),
            "classification": setup.get("classification"),
            "confidence": setup.get("confidence"),
            "t2": setup.get("t2"),
            "t3": setup.get("t3"),
            "metadata": setup.get("metadata", {}),
        },
    )

