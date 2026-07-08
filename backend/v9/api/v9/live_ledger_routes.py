"""LIVE ledger endpoint (journal L8) — what Sierra ACTUALLY executed.

GET /api/v9/live_ledger → the Sierra-sourced ground-truth ledger for the LIVE
account: each trade reconstructed from `trade_fills.json` fills alone (entry,
exits, contracts, realized P&L from fill prices), reconciled against the backend
DB row (CRITICAL divergences flagged), with manual interventions tagged.

This is the record to show investors — it reflects reality, not backend claims.
Read-only. Flag-gated LIVE_LEDGER_V1 (default OFF → {enabled:false}) so it stays
inert until Michael/CC enable it. Fail-safe: any error is returned, never crashes.
"""
from __future__ import annotations

import json
import logging
import os

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v9/live_ledger", tags=["live_ledger"])

_DEFAULT_FILLS = "/Users/michael/SierraChart_Data/v9_export/trade_fills.json"


def _enabled() -> bool:
    return os.getenv("LIVE_LEDGER_V1", "0").lower() in ("1", "true", "yes")


@router.get("")
@router.get("/")
async def live_ledger():
    if not _enabled():
        return {"enabled": False,
                "note": "LIVE_LEDGER_V1 off — enable to serve the Sierra-sourced ledger"}

    out = {"enabled": True, "source": "trade_fills.json", "trades": [], "generated_at": None}
    try:
        from datetime import datetime, timezone
        from backend.v9.services import sierra_ledger as sl

        out["generated_at"] = datetime.now(timezone.utc).isoformat()
        live_account = os.getenv("SIERRA_LIVE_ACCOUNT") or None
        fills_path = os.getenv("TRADE_FILLS_PATH", _DEFAULT_FILLS)

        # L8 journal (2026-07-08): the poller consumes+clears trade_fills.json —
        # read the durable journal (all history) PLUS any unconsumed lines, and
        # dedupe. Without this the ledger showed 0 trades while live trades ran.
        lines = []
        _journal = os.path.join(os.path.dirname(fills_path), "trade_fills_journal.jsonl")
        for p in (_journal, fills_path):
            try:
                with open(p, "r") as fh:
                    lines.extend(fh.readlines())
            except FileNotFoundError:
                continue
        if not lines:
            return {**out, "trades": [],
                    "note": f"no fills yet (journal {_journal} + {fills_path} empty)"}
        _seen = set()
        _deduped = []
        for ln in lines:
            ln = ln.strip()
            if ln and ln not in _seen:
                _seen.add(ln)
                _deduped.append(ln)
        lines = _deduped

        ledger = sl.build_ledger(sl.parse_fills(lines), live_account=live_account)

        # Index backend LIVE rows by their stored Sierra order id (quality JSON).
        backend_by_oid = {}
        try:
            from backend.v9.db.read import read_all
            rows = read_all(
                "SELECT id, mode, direction, entry_price, stop, t1, t2, t3, state, "
                "exit_price, pnl_usd, quality FROM v9_trades "
                "WHERE mode = 'live' ORDER BY id DESC LIMIT 100", {})
            for r in rows:
                q = r.get("quality")
                if isinstance(q, str):
                    try:
                        q = json.loads(q)
                    except (ValueError, TypeError):
                        q = {}
                oid = (q or {}).get("sierra_order_id")
                if oid is not None:
                    backend_by_oid[str(oid)] = {**dict(r), "_sierra_stop": None}
        except Exception as e:  # DB optional — ledger still returns Sierra truth
            logger.warning("[LiveLedger] backend join skipped: %s", e)

        for lt in ledger:
            row = lt.to_dict()
            b = backend_by_oid.get(str(lt.entry_order_id))
            if b is not None:
                sierra_stop = b.get("_sierra_stop")  # from TradeActivityLog (CC feeds later)
                row["divergences"] = [d.__dict__ for d in
                                      sl.reconcile(lt, b, sierra_stop=sierra_stop)]
                row["manual_events"] = [m.__dict__ for m in
                                        sl.detect_manual(lt, b, sierra_stop=sierra_stop)]
                row["backend_trade_id"] = b.get("id")
            else:
                row["divergences"] = []
                row["manual_events"] = []
                row["backend_trade_id"] = None
            out["trades"].append(row)

        out["divergence_count"] = sum(len(t["divergences"]) for t in out["trades"])
        return out
    except Exception as e:
        logger.warning("[LiveLedger] failed: %s", e)
        return {**out, "error": str(e)}
