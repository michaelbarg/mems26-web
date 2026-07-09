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
    stop_ids: Optional[list] = None,
    mode: str = "demo",
) -> Dict[str, Any]:
    """Write a MODIFY_STOP command — trail/re-anchor the protective stop.

    stop_ids: per-contract stop order IDs [c1_stop, c2_stop, c3_stop].
    The DLL reads these directly instead of relying on persistent slots
    (which Pipeline 5 may clear). Falls back to order_id if absent.
    """
    payload: Dict[str, Any] = {
        "op": "MODIFY_STOP",
        "trade_id": trade_id,
        "order_id": order_id,
        "new_stop": new_stop,
        "mode": mode,
        "ts_submitted": time.time(),
    }
    if stop_ids:
        payload["stop_ids"] = stop_ids
    return _write_command(payload)


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


def effective_contracts(setup: Dict[str, Any]) -> int:
    """The LIVE contract count for a setup — single source of truth (L7, 2026-07-08).

    Extracted verbatim from command_from_setup so accept_setup can persist the
    SAME number the Sierra command sends (symmetry: bracket = DB = display).

    Contract count lives in metadata.sizing (numeric) for the firing systems; the old
    top-level "contracts"/"size" lookup missed it → demo placed 1 contract instead of the
    N-contract per-contract bracket (verified 06-29: trade 257 placed C1 only).

    FIXED_CONTRACTS_3 (Michael 2026-07-01): single command choke point — guarantee
    every fire sends 3 contracts to Sierra for BOTH S2 and S4, demo + live. Belt-and-
    suspenders over the sizing-source overrides (quality_tier / compute_v2_sizing) so
    no path can send !=3 when the flag is on. Only setups that reached command-write
    have already passed the fire decision, so the count is always >0 here.
    FIXED_CONTRACTS_2 (Michael 2026-07-06): 2-contract choke point, PRECEDENCE over _3.
    """
    _sz = setup.get("contracts") or setup.get("size") or (setup.get("metadata") or {}).get("sizing")
    try:
        _contracts = max(1, int(_sz))
    except (TypeError, ValueError):
        _contracts = {"full": 3, "half": 2, "quarter": 1}.get(str(_sz).lower().strip(), 1)
    import os as _fc3_os
    if _fc3_os.environ.get("FIXED_CONTRACTS_2", "0").lower() in ("1", "true", "yes") and _contracts > 0:
        _contracts = 2
    elif _fc3_os.environ.get("FIXED_CONTRACTS_3", "0").lower() in ("1", "true", "yes") and _contracts > 0:
        _contracts = 3
    return _contracts


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
    # L7 (2026-07-08): count comes from effective_contracts — same source accept_setup
    # persists, so the Sierra bracket and the DB row can never disagree.
    _contracts = effective_contracts(setup)
    return write_trade_command(
        action=action,
        trade_id=trade_id,
        direction=direction,
        price=setup.get("entry_price"),
        contracts=_contracts,
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

