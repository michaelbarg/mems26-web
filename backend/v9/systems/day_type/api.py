"""Day Type Engine API — GET state, GET history, POST process, GET current."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.v9.db.session import get_db
from .models import V9DayTypeState
from .schemas import (
    BarInput, DayTypeState, DayTypeStateResponse,
    DayTypeHistoryResponse, ProcessBarResponse,
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
    """Return current Day Type Engine state."""
    engine = _get_engine()
    state = engine._build_state(
        BarInput(ts=0, session_min=0, open=0, high=0, low=0, close=0)
    )
    return DayTypeStateResponse(state=state)


@router.get("/history")
def get_history(limit: int = Query(20, ge=1, le=100)):
    """Return recent day type state history from DB (raw sqlite3 for reliability)."""
    import sqlite3
    DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT ts, stage, day_type, confidence, lock_state, opening_type, ib_width_class, behavior FROM v9_day_type_state ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
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

    Returns dict with all 6 day types possible, or None if not classified yet.
    """
    import sqlite3
    DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM v9_day_type_state WHERE lock_state='LOCKED' AND date(ts)=date('now') ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
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
        day_type = "Neutral"
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
    """Current Day Type classification — state machine primary, V1 fallback (D-071).

    State machine provides all 6 types (incl Trend_DD).
    V1 classifier is fallback-only (5 types, simpler rules).
    """
    global _today_classification, _today_date
    from datetime import date
    import requests

    today = date.today().isoformat()

    # Clear stale cache on new trading day
    if _today_date and _today_date != today:
        _today_classification = None
        _today_date = None
        reset_engine()

    # Return cached if already classified today
    if _today_date == today and _today_classification and _today_classification.get("classified"):
        return _today_classification

    # PRIMARY: Try state machine (via app.state.day_type_machine set by main.py)
    try:
        sm_result = _get_state_machine_classification()
        if sm_result and sm_result.get("classified"):
            _today_classification = sm_result
            _today_date = today
            return sm_result
    except Exception:
        pass

    # FALLBACK: V1 simple classifier (D-071)
    result = _classify_v1_from_tpo()

    if result.get("classified"):
        _today_classification = result
        _today_date = today

        # Persist to DB (once per day)
        try:
            from backend.v9.db.session import SessionLocal
            from backend.v9.db.models.day_type_history import V9DayTypeHistory
            db = SessionLocal()
            existing = db.query(V9DayTypeHistory).filter(
                V9DayTypeHistory.date == date.today()
            ).first()
            if not existing:
                row = V9DayTypeHistory(
                    date=date.today(),
                    day_type=result["day_type"],
                    status="LOCKED",
                    confidence=result["confidence"],
                    ib_high=result["ib_h"],
                    ib_low=result["ib_l"],
                    ib_width_ticks=int(result["ib_range"] * 4) if result["ib_range"] else None,
                    reasoning_notes=f"V1 rules: ext_ratio={result['extension_ratio']}",
                )
                db.add(row)
                db.commit()
            db.close()
        except Exception as e:
            import logging
            logging.getLogger("mems26.day_type").warning("V1 persist error: %s", e)

        return result

    # γ.1: Fallback — if V1 can't classify, return PENDING (not stale state machine data)
    # State machine may carry stale classification from previous session
    engine = _get_engine()
    if not engine.ib_locked:
        # Pre-IB: deterministic PENDING state
        return {
            "day_type": "PENDING", "confidence": 0,
            "stage": "PRE_IB" if engine.bar_count == 0 else "IB_BUILDING",
            "reason": "Awaiting IB lock @ 10:30 ET",
            "classified": False,
        }
    state = engine._build_state(
        BarInput(ts=0, session_min=0, open=0, high=0, low=0, close=0)
    )
    return {
        "day_type": state.day_type.value if hasattr(state.day_type, 'value') else str(state.day_type),
        "status": state.lock_state.value if hasattr(state.lock_state, 'value') else str(state.lock_state),
        "confidence": state.confidence,
        "ib_width": state.ib_width.value if hasattr(state.ib_width, 'value') else str(state.ib_width),
        "opening_type": state.opening_type.value if hasattr(state.opening_type, 'value') else str(state.opening_type),
        "stage": state.stage.value if hasattr(state.stage, 'value') else str(state.stage),
        "classified": False,
    }


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

    # Persist to DB
    record = V9DayTypeState(
        ts=datetime.fromtimestamp(bar.ts, tz=timezone.utc),
        stage=state.stage.value,
        day_type=state.day_type.value,
        classification=state.day_type.value if state.lock_state == "LOCKED" else None,
        confidence=state.confidence,
        ib_width_class=state.ib_width.value if state.ib_width else None,
        opening_type=state.opening_type.value if state.opening_type else None,
        behavior=state.behavior.value if state.behavior else None,
        lock_state=state.lock_state.value if state.lock_state else None,
        meta=state.meta,
    )
    db.add(record)
    db.commit()

    return ProcessBarResponse(state=state, stage_changed=stage_changed)
