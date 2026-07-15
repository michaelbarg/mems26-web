"""Day Type Engine API — GET state, GET history, POST process, GET current."""

from datetime import datetime, timezone
from typing import Optional

from backend.v9.common.trading_date import et_today

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.v9.db.session import get_db
from .models import V9DayTypeState
from .schemas import (
    BarInput, DayTypeState, DayTypeStateResponse,
    DayTypeHistoryResponse, ProcessBarResponse,
    Stage, DayType, OpeningType, IBWidth, Behavior,
)
from .state_machine import DayTypeStateMachine

router = APIRouter(prefix="/api/v9/day_type", tags=["v9-day-type"])

# Module-level state machine instance (reset daily by bridge)
_engine: Optional[DayTypeStateMachine] = None


def _get_engine() -> DayTypeStateMachine:
    global _engine
    if _engine is None:
        _engine = DayTypeStateMachine()
    return _engine


def reset_engine():
    """Reset the state machine (called at session start)."""
    global _engine
    _engine = DayTypeStateMachine()


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("/state", response_model=DayTypeStateResponse)
def get_state():
    """Return current Day Type Engine state.

    Reads from v9_day_type_state DB (populated by main.py day_type_machine)
    rather than the dead api.py _engine singleton, which never receives bars.
    """
    from backend.v9.db.read import read_one
    try:
        row = read_one(
            "SELECT ts, stage, day_type, confidence, lock_state, opening_type, "
            "ib_width_class, behavior FROM v9_day_type_state ORDER BY id DESC LIMIT 1",
            {},
        )
        if row:
            state = DayTypeState(
                stage=Stage(row["stage"]) if row["stage"] else Stage.A1,
                day_type=DayType(row["day_type"]) if row["day_type"] and row["day_type"] != "UNKNOWN" else DayType.UNKNOWN,
                confidence=float(row["confidence"] or 0),
                lock_state=row["lock_state"] or "PENDING",
                opening_type=OpeningType(row["opening_type"]) if row["opening_type"] and row["opening_type"] != "NA" else OpeningType.UNKNOWN,
                ib_width=IBWidth(row["ib_width_class"]) if row["ib_width_class"] and row["ib_width_class"] != "UNKNOWN" else IBWidth.UNKNOWN,
                behavior=Behavior(row["behavior"]) if row["behavior"] else Behavior.DEVELOPING,
            )
            return DayTypeStateResponse(state=state)
    except Exception:
        pass
    # Fallback: empty state
    engine = _get_engine()
    state = engine._build_state(
        BarInput(ts=0, session_min=0, open=0, high=0, low=0, close=0)
    )
    return DayTypeStateResponse(state=state)


@router.get("/history")
def get_history(limit: int = Query(20, ge=1, le=100)):
    """Return recent day type state history from DB."""
    from backend.v9.db.read import read_all
    try:
        rows = read_all(
            "SELECT ts, stage, day_type, confidence, lock_state, opening_type, ib_width_class, behavior FROM v9_day_type_state ORDER BY id DESC LIMIT :limit",
            {"limit": limit},
        )
        items = [
            {
                "ts": r["ts"],
                "stage": r["stage"] or "A1",
                "day_type": r["day_type"] or "UNKNOWN",
                "confidence": float(r["confidence"] or 0),
                "lock_state": r["lock_state"] or "PENDING",
                "opening_type": r["opening_type"] or "UNKNOWN",
                "ib_width": r["ib_width_class"] or "UNKNOWN",
                "behavior": r["behavior"] or "DEVELOPING",
            }
            for r in rows
        ]
        return {"items": items, "count": len(items)}
    except Exception as e:
        return {"items": [], "count": 0, "error": str(e)}


def _get_state_machine_classification() -> Optional[dict]:
    """Read state machine classification from v9_day_type_state DB (primary path per D-071).

    Returns dict with all 7 day types possible, or None if not classified yet.
    """
    from backend.v9.db.read import read_one
    try:
        row = read_one(
            "SELECT * FROM v9_day_type_state WHERE lock_state='LOCKED' AND date(ts)=:today ORDER BY id DESC LIMIT 1",
            {"today": et_today().isoformat()},
        )
        if not row:
            return None
        r = dict(row)
        dt = r.get("day_type", "UNKNOWN")
        if dt == "UNKNOWN":
            return None
        conf = r.get("confidence", 0)
        return {
            "day_type": dt,
            "confidence": conf if isinstance(conf, (int, float)) else 0,
            "stage": r.get("stage", ""),
            "ib_width": r.get("ib_width_class", "UNKNOWN"),
            "opening_type": r.get("opening_type", "UNKNOWN"),
            "lock_state": r.get("lock_state", "PENDING"),
            "classified": True,
            "source": "state_machine",
        }
    except Exception:
        return None


def _classify_v1_from_tpo() -> dict:
    """V1 simple classifier — reads IB + bars from TPO system.

    Rules (🟡 thresholds: CAL-006=1.5x, CAL-007=0.3x — calibrate post-SHADOW):
      Both sides breached   → NEUTRAL
      Neither breached      → NORMAL
      Extension > 1.5x IB  → TREND_NORMAL
      Extension < 0.3x IB  → NONTREND
      Single side moderate  → VARIATION

    Gate (Wave A1.6 Worker B): only classify during RTH cash session.
    Pre-RTH classification violates Constitution V3 Part 3 Layer 2.
    """
    import requests

    # Session gate: only classify during RTH (Bootstrap Red Flag #4)
    try:
        kz = requests.get("http://localhost:8000/api/v9/killzone/current", timeout=2).json()
        zone_name = kz.get("current_zone", {}).get("name", "UNKNOWN")
        rth_zones = {"NY_OPEN", "MIDDAY", "NY_PM"}
        if zone_name not in rth_zones:
            return {"day_type": "PENDING", "confidence": 0, "ib_h": None, "ib_l": None,
                    "ib_range": None, "extension_ratio": None, "classified": False,
                    "stage": f"PRE_RTH ({zone_name})", "reason": "Awaiting RTH session for IB lock"}
    except Exception:
        pass  # If killzone unavailable, fall through to IB lock check

    try:
        tpo = requests.get("http://localhost:8000/api/v9/tpo/current", timeout=2).json()
    except Exception:
        return {"day_type": "UNKNOWN", "confidence": 0, "ib_h": None, "ib_l": None,
                "ib_range": None, "extension_ratio": None, "classified": False}

    ib_h = tpo.get("ib_high")
    ib_l = tpo.get("ib_low")
    ib_locked = tpo.get("ib_locked", False)

    if not ib_locked or ib_h is None or ib_l is None:
        # γ.2: Return PENDING with stage info, not UNKNOWN (Constitution V3 Part 3 Layer 2)
        if ib_h is not None and ib_l is not None:
            stage = "IB_BUILDING"
        else:
            stage = "PRE_IB"
        return {"day_type": "PENDING", "confidence": 0, "ib_h": ib_h, "ib_l": ib_l,
                "ib_range": None, "extension_ratio": None, "classified": False,
                "stage": stage, "reason": "Awaiting IB lock @ 10:30 ET"}

    ib_range = ib_h - ib_l
    if ib_range <= 0:
        return {"day_type": "UNKNOWN", "confidence": 0, "ib_h": ib_h, "ib_l": ib_l,
                "ib_range": 0, "extension_ratio": None, "classified": False}

    # Read bars for post-IB extension
    try:
        bars = requests.get("http://localhost:8000/api/v9/chart/bars5min?limit=60", timeout=2).json()
    except Exception:
        bars = []

    if not isinstance(bars, list) or not bars:
        return {"day_type": "UNKNOWN", "confidence": 0, "ib_h": ib_h, "ib_l": ib_l,
                "ib_range": ib_range, "extension_ratio": None, "classified": False}

    post_ib_high = max(b.get("h", 0) for b in bars)
    post_ib_low = min(b.get("l", float("inf")) for b in bars)
    extension_up = max(0, post_ib_high - ib_h)
    extension_down = max(0, ib_l - post_ib_low)
    max_extension = max(extension_up, extension_down)
    extension_ratio = max_extension / ib_range

    ib_breached_up = post_ib_high > ib_h
    ib_breached_down = post_ib_low < ib_l
    both_sides = ib_breached_up and ib_breached_down

    # Classification (🟡 V1 rules — CAL-006/007)
    if both_sides:
        from backend.v9.systems.day_type.neutral_classifier import classify_neutral_subtype
        from backend.v9.systems.day_type.prev_day import load_tpo_previous_day_summary
        prev_day = load_tpo_previous_day_summary()
        # session_open_price = first bar open; session_date from market clock
        _session_open = bars[0].get("o", bars[0].get("open")) if bars else None
        from backend.v9.services.market_clock import now_et
        _session_date_str = now_et().date().isoformat()
        subtype = classify_neutral_subtype(
            session_open_price=_session_open,
            prev_vah=prev_day.get("vah"),
            prev_val=prev_day.get("val"),
            session_date=_session_date_str,
        )
        day_type = subtype.value
        conf = 60
    elif not ib_breached_up and not ib_breached_down:
        day_type = "Normal"
        conf = 70
    elif extension_ratio > 1.5:  # 🟡 CAL-006
        day_type = "Trend_Normal"
        conf = 65
    elif extension_ratio < 0.3:  # 🟡 CAL-007
        day_type = "Nontrend"
        conf = 55
    else:
        day_type = "Variation"
        conf = 60

    return {
        "day_type": day_type, "confidence": conf,
        "ib_h": ib_h, "ib_l": ib_l, "ib_range": round(ib_range, 2),
        "extension_ratio": round(extension_ratio, 3), "classified": True,
    }


# Module-level cache for today's classification
_today_classification: Optional[dict] = None
_today_date: Optional[str] = None


@router.get("/current")
def get_current():
    """Current Day Type classification — V9 canonical source (Prompt 20).

    Priority order:
      1. V9 state machine (app.state.day_type_machine) — live in-memory
      2. V9 DB (v9_day_type_history for today) — persisted classification
      3. V1 fallback (only if V9 has never classified today)

    Shape: always returns {day_type, confidence, stage, classified, ...}
    """
    import requests
    today = et_today().isoformat()

    # ── SOURCE 1: V9 state machine via /v9/current (canonical per Prompt 20) ──
    try:
        v9_resp = requests.get("http://localhost:8000/api/v9/day_type/v9/current", timeout=2).json()
        if v9_resp.get("classified") and v9_resp.get("data"):
            d = v9_resp["data"]
            return {
                "day_type": d.get("day_type", "UNKNOWN"),
                "confidence": int((d.get("probability") or 0) * 100),
                "ib_h": d.get("ib_h"),
                "ib_l": d.get("ib_l"),
                "ib_range": (d["ib_h"] - d["ib_l"]) if d.get("ib_h") and d.get("ib_l") else None,
                "extension_ratio": None,
                "classified": True,
                "stage": "C3",
                "opening_type": d.get("opening_type"),
                "ib_width_class": d.get("ib_width_class"),
                "source": "v9",
            }
    except Exception:
        pass

    # ── SOURCE 2: State machine DB (LOCKED row today) ──
    try:
        sm_result = _get_state_machine_classification()
        if sm_result and sm_result.get("classified"):
            return sm_result
    except Exception:
        pass

    # ── SOURCE 3: V1 for pre-IB/pre-RTH gating ONLY (Prompt 20b) ──
    # V1 may NOT produce a classified=True result; it only provides PENDING states.
    # If V9 hasn't classified today, the system is not yet ready — return PENDING.
    result = _classify_v1_from_tpo()
    if result.get("classified"):
        # V1 would classify — but V9 is canonical. Demote to PENDING with reason.
        result["classified"] = False
        result["source"] = "v1_demoted"
        result["reason"] = "V9 has not classified today; V1 result available but not canonical"
    return result


@router.get("/stats")
def get_stats(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """Day type distribution over last N days."""
    try:
        rows = (
            db.query(V9DayTypeState.day_type, func.count(V9DayTypeState.id))
            .filter(V9DayTypeState.lock_state == "LOCKED")
            .group_by(V9DayTypeState.day_type)
            .all()
        )
        return {
            "distribution": {dt: count for dt, count in rows},
            "total_days": sum(count for _, count in rows),
        }
    except Exception:
        return {"distribution": {}, "total_days": 0}


@router.post("/process", response_model=ProcessBarResponse)
def process_bar(bar: BarInput, db: Session = Depends(get_db)):
    """Process a single bar through the Day Type Engine.

    Used by the bridge to feed bars into the state machine.
    """
    engine = _get_engine()
    prev_stage = engine.stage

    state = engine.process_bar(bar)
    stage_changed = state.stage != prev_stage

    # 07-15 Michael decision 4/6 (single-brain/single-writer): this endpoint's
    # WRAPPER engine is a second, legacy brain — its rows interleaved with the
    # canonical on-bar writer (backend/main.py) and produced the 07-14
    # duplicate rows + frozen confidence. v9_day_type_state now has exactly ONE
    # writer: the canonical per-bar path. This endpoint still processes and
    # responds (API contract kept) but no longer persists.
    _ = db  # session unused by design — kept for signature compatibility

    return ProcessBarResponse(state=state, stage_changed=stage_changed)
