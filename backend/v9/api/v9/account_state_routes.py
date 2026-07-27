"""W1b: GET /api/v9/account/state — Sierra account truth via bridge file.

Source: sierra_state.json (NOT DB synthesis) per docs/SOURCE_OF_TRUTH.md.
Missing fields = None (Rule 1: honest failure, never synthesize).
Polling floor: 15000ms (P30 — no faster).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/v9/account", tags=["v9-account"])

STATE = Path(os.path.expanduser("~/SierraChart_Data/v9_export/sierra_state.json"))
STALE_S = 10.0


def _read_state() -> Dict[str, Any]:
    try:
        if not STATE.exists():
            return {"ok": False, "stale": True, "error": "sierra_state.json not found"}
        age = time.time() - STATE.stat().st_mtime
        raw = STATE.read_text().strip() or "{}"
        # Sierra writes -inf/inf for high/low_during_pos when flat — not valid JSON.
        # Replace with null so json.loads succeeds (Rule 1: honest None, not a lie).
        import re
        raw = re.sub(r':\s*-?inf\b', ':null', raw)
        data = json.loads(raw)
        return {"ok": True, "stale": age > STALE_S, "age_s": round(age, 1), **data}
    except Exception as e:
        return {"ok": False, "stale": True, "error": str(e)}


@router.get("/state")
def account_state(request: Request) -> Dict[str, Any]:
    st = _read_state()

    def _get(key, cast=None):
        v = st.get(key)
        if v is None:
            return None
        try:
            return cast(v) if cast else v
        except Exception:
            return None

    sierra = {
        "ok": st.get("ok", False),
        "stale": st.get("stale", True),
        "age_s": st.get("age_s"),
        "error": st.get("error"),
        # Existing fields
        "position_qty": _get("position_qty", int),
        "avg_price": _get("avg_price", float),
        "working_orders": _get("working_orders", int),
        "is_sim": _get("is_sim"),
        "order_placement_armed": _get("order_placement_armed"),
        # W1 new fields (None until DLL rebuilt Monday)
        "open_pnl": _get("open_pnl", float),
        "daily_pnl": _get("daily_pnl", float),
        "high_during_pos": _get("high_during_pos", float),
        "low_during_pos": _get("low_during_pos", float),
        "trade_account": _get("trade_account"),
        "symbol": _get("symbol"),
        "daily_total_qty_filled": _get("daily_total_qty_filled", float),
        "last_price": _get("last_price", float),
    }

    # Open system trade from TradeManager (if any)
    open_trade: Optional[Dict] = None
    tm = getattr(getattr(request.app, "state", None), "trade_manager", None)
    if tm is not None:
        try:
            active = tm.get_active_trades() if hasattr(tm, "get_active_trades") else []
            for t in (active or []):
                if getattr(t, "mode", "shadow") not in ("demo", "live"):
                    continue
                if getattr(t, "state", "") in ("CLOSED", "CANCELLED"):
                    continue
                open_trade = {
                    k: getattr(t, k, None) for k in (
                        "id", "direction", "entry_price", "stop",
                        "t1", "t2", "t3", "state", "mode", "pattern",
                    )
                }
                q = getattr(t, "quality", None)
                if isinstance(q, dict):
                    open_trade["contracts"] = q.get("contracts")
                break
        except Exception:
            pass

    # Verdict: manual / system / flat / divergence / unknown
    qty = sierra.get("position_qty")
    if not st.get("ok") or st.get("stale"):
        verdict = "unknown"
    elif qty == 0 and open_trade is None:
        verdict = "flat"
    elif qty is not None and qty != 0 and open_trade is not None:
        verdict = "system"
    elif qty is not None and qty != 0 and open_trade is None:
        verdict = "manual"
    else:
        verdict = "divergence"

    return {
        "sierra_state": sierra,
        "open_trade": open_trade,
        "verdict": verdict,
        "source": "sierra_state.json",
    }
