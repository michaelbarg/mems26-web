"""Sierra command file writer for DEMO/LIVE execution paths.

Writes the command format consumed by the Bridge/DLL through
`trade_command.json`. This module has no network or broker side effects.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_SIGNALS_DIR = Path("/tmp/mems26_signals")


def signals_dir() -> Path:
    return Path(os.getenv("MEMS26_SIGNALS_DIR", str(DEFAULT_SIGNALS_DIR)))


def command_file() -> Path:
    return signals_dir() / "trade_command.json"


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
    """Write a Sierra command and return the exact payload."""
    action = action.upper()
    payload = {
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
    out = command_file()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    return payload


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

