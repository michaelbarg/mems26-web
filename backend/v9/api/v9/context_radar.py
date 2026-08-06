"""GET /api/v9/context/radar — one call, the whole picture (Michael 2026-07-29:
"שיהיה לי רדאר זיהוי מסודר").

Aggregates what already exists — day-type state, opening panel, account state,
gateway decisions, bar integrity — into ONE stable shape for the frontend radar.
When CC's System-0 (`MARKET_CONTEXT_V1`) lands, this route switches to
`get_market_context()` WITHOUT changing the response shape (the contract is in
CC_SYSTEM0_MARKET_CONTEXT_2026-07-29.md §Phase E).

Missing source = null, never a guess (Rule 1).
"""
from __future__ import annotations

import json
import os
import re as _re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/v9/context", tags=["v9-context"])

_EXPORT = Path(os.path.expanduser("~/SierraChart_Data/v9_export"))
_DECISIONS = _EXPORT / "gateway_decisions.jsonl"
_STATE = _EXPORT / "sierra_state.json"
_MES_MARGIN = 276.21          # fallback; live value derives from the account block


def _sierra() -> Dict[str, Any]:
    try:
        raw = _re.sub(r':\s*-?inf\b', ':null', _STATE.read_text().strip() or "{}")
        d = json.loads(raw)
        if (time.time() - _STATE.stat().st_mtime) > 15:
            d["_stale"] = True
        return d
    except Exception:
        return {}


def _day_state() -> Dict[str, Any]:
    try:
        from backend.v9.db.read import read_one
        # Prefer today's row; fallback to the latest regardless of date.
        # NOTE (nit-TZ): ts is naive-UTC stored in PG without timezone qualifier.
        # PG interprets naive as its session TZ (UTC by default on our setup).
        # The AT TIME ZONE converts for ET-date comparison. Edge: between
        # midnight-UTC and midnight-ET (~04:00/05:00 UTC) we may see
        # yesterday's ET date — display-only, not a trading concern.
        r = read_one(
            "SELECT day_type, stage, confidence, direction, opening_type, lock_state "
            "FROM v9_day_type_state "
            "WHERE (ts AT TIME ZONE 'America/New_York')::date = "
            "(now() AT TIME ZONE 'America/New_York')::date "
            "ORDER BY id DESC LIMIT 1", {})
        if not r:
            r = read_one(
                "SELECT day_type, stage, confidence, direction, opening_type, lock_state "
                "FROM v9_day_type_state ORDER BY id DESC LIMIT 1", {})
        if not r:
            # Rehydrate from live bars when DB state is empty (post-restart)
            try:
                from backend.v9.db.read import read_all
                from backend.v9.systems.day_type.classifier_core import classify_session
                bars = read_all(
                    "SELECT open, high, low, close, volume FROM v9_bars_5min_woodies "
                    "WHERE (ts AT TIME ZONE 'America/New_York')::date = "
                    "(now() AT TIME ZONE 'America/New_York')::date "
                    "ORDER BY ts", {})
                if bars and len(bars) >= 6:
                    bar_dicts = [{"o": float(b["open"]), "h": float(b["high"]),
                                  "l": float(b["low"]), "c": float(b["close"]),
                                  "v": int(b["volume"] or 0)} for b in bars]
                    ib_bars = bar_dicts[:12] if len(bar_dicts) >= 12 else bar_dicts
                    ib_h = max(b["h"] for b in ib_bars)
                    ib_l = min(b["l"] for b in ib_bars)
                    cls = classify_session(bars=bar_dicts, ib_high=ib_h, ib_low=ib_l,
                                           open_price=bar_dicts[0]["o"])
                    return {"day_type": cls.get("day_type"), "stage": cls.get("status"),
                            "confidence": cls.get("confidence"),
                            "direction": cls.get("direction"),
                            "opening_type": cls.get("opening_type"),
                            "lock_state": None}
            except Exception:
                pass
        return dict(r) if r else {}
    except Exception:
        return {}


def _leg(direction: Optional[str]) -> Optional[str]:
    """'with_extension(UP)' → 'UP'. No leg → null, never a guess."""
    if not direction:
        return None
    m = _re.search(r"\((UP|DOWN)\)", str(direction))
    return m.group(1) if m else None


def _gates_last_hour() -> Dict[str, Any]:
    out = {"blocked": 0, "passed": 0, "top": [], "last_block": None}
    try:
        if not _DECISIONS.exists():
            return out
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        counts: Dict[str, int] = {}
        # tail-read: the file grows all day; last ~1500 lines cover an hour easily
        lines = _DECISIONS.read_text(encoding="utf-8").splitlines()[-1500:]
        for ln in lines:
            try:
                d = json.loads(ln)
                ts = datetime.fromisoformat(str(d.get("ts")))
            except Exception:
                continue
            if ts < cutoff:
                continue
            b = d.get("blocked_by")
            if b:
                out["blocked"] += 1
                counts[b] = counts.get(b, 0) + 1
                out["last_block"] = {"gate": b, "pattern": d.get("pattern"),
                                     "direction": d.get("direction"),
                                     "ts": str(d.get("ts"))[11:16]}
            else:
                out["passed"] += 1
        out["top"] = sorted(counts.items(), key=lambda x: -x[1])[:4]
    except Exception:
        pass
    return out


def _release_state() -> Dict[str, Any]:
    """The release gate's current posture, judged from the freshest decision."""
    try:
        lines = _DECISIONS.read_text(encoding="utf-8").splitlines()[-200:]
        for ln in reversed(lines):
            try:
                d = json.loads(ln)
            except Exception:
                continue
            if d.get("blocked_by") == "awaiting_release":
                ts = datetime.fromisoformat(str(d.get("ts")))
                age_min = (datetime.now(timezone.utc) - ts).total_seconds() / 60
                if age_min <= 15:
                    return {"state": "holding", "reason": d.get("reason"),
                            "age_min": round(age_min)}
                break
    except Exception:
        pass
    return {"state": "idle", "reason": None, "age_min": None}


def _bar_integrity() -> str:
    """Seam scan over today's bars (ET). suspect ⇒ nothing downstream is trustworthy."""
    try:
        from backend.v9.db.read import read_all
        rows = read_all(
            "SELECT high, low FROM v9_bars_5min_woodies "
            "WHERE (ts AT TIME ZONE 'America/New_York')::date = "
            "(now() AT TIME ZONE 'America/New_York')::date ORDER BY ts", {})
        prev = None
        for r in rows:
            h, l = float(r["high"]), float(r["low"])
            if prev is not None:
                gap = max(l - prev[0], prev[1] - h)
                if gap > 15.0:
                    return "suspect"
            prev = (h, l)
        return "clean" if rows else "no_data"
    except Exception:
        return "unknown"


def _delta_features() -> Dict[str, Any]:
    """P2.1-2 delta features from live cumulative_delta export."""
    out: Dict[str, Any] = {"cvd_directionality": None, "delta_confirms_ext": None}
    if os.getenv("DELTA_FEATURES_V1", "0").lower() not in ("1", "true", "yes"):
        return out
    try:
        _dp = _EXPORT / "cumulative_delta.json"
        if not _dp.exists():
            return out
        _dexport = json.loads(_dp.read_text().strip() or "{}")
        from backend.v9.systems.delta_features import (
            cvd_directionality, delta_confirms_extension,
        )
        _pts = _dexport.get("points", [])
        out["cvd_directionality"] = cvd_directionality(_pts)
        # delta_confirms_ext needs the break direction from day_type state
        # — only if we have one
        out["dll_trend"] = _dexport.get("trend")
        out["dll_divergence"] = _dexport.get("divergence")
    except Exception:
        pass
    return out


def _system0_fields() -> Dict[str, Any]:
    """balance/acceptance from System-0 when its flag is on; nulls otherwise."""
    if os.getenv("MARKET_CONTEXT_V1", "0").strip().lower() not in ("1", "true", "yes"):
        return {"balance_state": None, "acceptance": None}
    try:
        from backend.v9.services.market_context import get_market_context
        mc = get_market_context()
        if mc is None:
            return {"balance_state": None, "acceptance": None}
        bs = getattr(mc, "balance_state", None)
        ac = getattr(mc, "acceptance", None)
        return {"balance_state": None if bs in (None, "UNKNOWN") else bs,
                "acceptance": ac}
    except Exception:
        return {"balance_state": None, "acceptance": None}


def _regime_toggle() -> Optional[Dict[str, Any]]:
    """Unified Balance↔Imbalance regime (Dalton Step 3)."""
    try:
        from backend.v9.systems.balance_imbalance_toggle import assess_regime_live
        return assess_regime_live()
    except Exception:
        return None


def _extremes_quality() -> Optional[Dict[str, Any]]:
    """Excess/Poor high/low from today's session bars (Dalton Step 1)."""
    try:
        from backend.v9.db.read import read_all
        from backend.v9.systems.extremes_quality import classify_extremes_live
        rows = read_all(
            "SELECT open, high, low, close FROM v9_bars_5min_woodies "
            "WHERE (ts AT TIME ZONE 'America/New_York')::date = "
            "(now() AT TIME ZONE 'America/New_York')::date "
            "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30:00' "
            "ORDER BY ts", {},
        )
        if not rows or len(rows) < 3:
            return None
        bars = [{"open": float(r["open"]), "high": float(r["high"]),
                 "low": float(r["low"]), "close": float(r["close"])}
                for r in rows]
        return classify_extremes_live(bars)
    except Exception:
        return None


@router.get("/radar")
def radar(request: Request) -> Dict[str, Any]:
    st = _sierra()
    ds = _day_state()

    # opening block — prefer the live opening panel machinery already serving the UI
    opening: Dict[str, Any] = {"type": ds.get("opening_type"), "dir": None, "conf": None}
    try:
        from backend.v9.services.trade_context import get_opening_dir_fusion
        fu = get_opening_dir_fusion() or {}
        if fu.get("direction"):
            opening["dir"] = fu.get("direction")
        if fu.get("confidence") is not None:
            opening["conf"] = fu.get("confidence")
    except Exception:
        pass

    contracts_allowed: Optional[int] = None
    try:
        avail = st.get("acct_available_funds")
        req, qty = st.get("acct_margin_req"), abs(int(st.get("position_qty") or 0))
        per = (float(req) / qty) if (req and qty) else _MES_MARGIN
        if isinstance(avail, (int, float)) and abs(avail) < 1e15:
            contracts_allowed = max(0, int((float(avail) - 50) // per))
    except Exception:
        contracts_allowed = None

    return {
        "day_type": ds.get("day_type"),
        "stage": ds.get("stage"),
        "confidence": ds.get("confidence"),
        "leg": _leg(ds.get("direction")),
        "direction_raw": ds.get("direction"),
        "lock_state": ds.get("lock_state"),
        "opening_type": opening["type"],
        "opening_dir": opening["dir"],
        "opening_conf": opening["conf"],
        # System-0 fields — live from get_market_context() when MARKET_CONTEXT_V1
        # is on (enabled by Michael's 07-29 ruling); null otherwise. Same shape.
        **_system0_fields(),
        # P2.1-2 delta features (DEV_PLAN 02.08) — live from cumulative_delta export
        **_delta_features(),
        "release_gate": _release_state(),
        "gates_last_hour": _gates_last_hour(),
        "trading": {
            "armed": st.get("order_placement_armed"),
            "is_sim": st.get("is_sim"),
            "sendorders": st.get("send_orders_to_trade_service"),
            "position_qty": st.get("position_qty"),
            "contracts_allowed": contracts_allowed,
            "stale": bool(st.get("_stale")),
        },
        "bar_integrity": _bar_integrity(),
        # MULTIDAY_CONTEXT_V1 (Michael 02.08): the 7-day Dalton balance in
        # radar-compact form — range/value, value migration, today's open
        # location. Sourced from the cached /context/multiday compute.
        "balance7": _balance7_summary(),
        "extremes": _extremes_quality(),
        "regime": _regime_toggle(),
        "updated_ts": time.time(),
    }


def _balance7_summary() -> Optional[Dict[str, Any]]:
    try:
        from backend.v9.api.v9.context_multiday import multiday as _md
        d = _md()
        comp = d.get("composite")
        if not comp:
            return None
        vm = d.get("value_migration") or {}
        return {
            "range": [comp.get("range_low"), comp.get("range_high")],
            "value": [comp.get("val"), comp.get("vah")],
            "poc": comp.get("poc"),
            "migration": vm.get("direction"),
            "migration_slope": vm.get("slope"),
            "overlap": d.get("va_overlap_pct"),
            "open_location": d.get("open_location"),
            "n_days": d.get("n_days_used"),
        }
    except Exception:
        return None
