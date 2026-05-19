"""API: /api/v9/tpo/* — System 5 TPO Profile."""
from fastapi import APIRouter, Request
import json
import logging
import os
from pathlib import Path
import sqlite3
import time
from typing import Optional

router = APIRouter(prefix="/api/v9/tpo", tags=["tpo"])
logger = logging.getLogger(__name__)

SIERRA_TPO_PATH = Path(
    os.getenv("V9_TPO_EXPORT_PATH", "/Users/michael/SierraChart_Data/v9_export/tpo.json")
)
SIERRA_TPO_MAX_AGE_S = float(os.getenv("V9_TPO_MAX_AGE_S", "30"))


def _norm_session_ts(ts) -> Optional[str]:
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ts))
    return str(ts)


def _session_ts_epoch(ts) -> Optional[float]:
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return float(ts)
    try:
        from datetime import datetime

        s = str(ts).replace(" ", "T")
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return None


def _load_tpo_periods(limit: int = 12) -> list:
    """Recent TPO session slices for stepped POC overlay (30m periods from DB)."""
    try:
        conn = sqlite3.connect("/Users/michael/Downloads/mems26_web_git/data/mems26_local.db")
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT opened_ts, closed_ts, poc_price, vah_price, val_price FROM v9_tpo_sessions "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        cutoff = time.time() - 48 * 3600
        out = []
        for r in rows:
            if r["poc_price"] is None:
                continue
            opened_epoch = _session_ts_epoch(r["opened_ts"])
            if opened_epoch is not None and opened_epoch < cutoff:
                continue
            out.append(
                {
                    "opened_ts": _norm_session_ts(r["opened_ts"]),
                    "closed_ts": _norm_session_ts(r["closed_ts"]),
                    "poc_price": r["poc_price"],
                    "vah_price": r["vah_price"],
                    "val_price": r["val_price"],
                }
            )
        return out
    except Exception as e:
        logger.warning("[tpo] failed to load periods: %s", e)
        return []


def _normalize_sierra_tpo(data: dict, age_s: float) -> dict:
    session = data.get("session") or {}
    ib = data.get("ib") or {}
    prior_day = data.get("prior_day") or {}

    ib_found = bool(ib.get("found"))
    ib_high = ib.get("high") if ib_found else None
    ib_low = ib.get("low") if ib_found else None
    ib_mid = ib.get("mid") if ib_found else None
    ib_width = None
    if ib_high is not None and ib_low is not None:
        ib_width = ib_high - ib_low

    return {
        "running": True,
        "hydrated": True,
        "source": "sierra_tpo_json",
        "version": data.get("version"),
        "export_ts": data.get("export_ts"),
        "age_s": round(age_s, 3),
        "session_type": "SIERRA",
        "poc": session.get("poc"),
        "vah": session.get("vah"),
        "val": session.get("val"),
        "session_high": session.get("session_high"),
        "session_low": session.get("session_low"),
        "total_volume": session.get("total_volume"),
        "ib_high": ib_high,
        "ib_mid": ib_mid,
        "ib_low": ib_low,
        "ib_locked": ib_found,
        "ib_width": ib_width,
        "prior_day": {
            "found": bool(prior_day.get("found")),
            "high": prior_day.get("high"),
            "low": prior_day.get("low"),
            "close": prior_day.get("close"),
        },
        "profile_shape": "NA",
        "opening_type": "NA",
        "poc_migration": {
            "direction": "UNKNOWN",
            "magnitude_pts": None,
            "stuck_minutes": 0,
            "previous_poc": None,
        },
    }


def _load_sierra_tpo(path: Path = SIERRA_TPO_PATH, max_age_s: float = SIERRA_TPO_MAX_AGE_S) -> Optional[dict]:
    if not path.exists():
        return None
    age_s = time.time() - path.stat().st_mtime
    if age_s > max_age_s:
        logger.warning("[tpo] Sierra tpo.json stale: age=%.1fs path=%s", age_s, path)
        return None
    with path.open() as f:
        data = json.load(f)
    if data.get("type") != "tpo":
        logger.warning("[tpo] Unexpected Sierra TPO type=%s path=%s", data.get("type"), path)
        return None
    out = _normalize_sierra_tpo(data, age_s)
    out["periods"] = _load_tpo_periods()
    return out


@router.get("/current")
async def tpo_current(request: Request):
    sierra_tpo = _load_sierra_tpo()
    if sierra_tpo is not None:
        return sierra_tpo

    sys = getattr(request.app.state, "tpo_system", None)
    if sys is None:
        return {"running": False, "error": "TPOSystem not initialized"}
    return sys.get_current()


@router.get("/journal")
async def tpo_journal(request: Request, session_id: str = "", limit: int = 50):
    db_path = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        if session_id:
            rows = conn.execute(
                "SELECT * FROM v9_tpo_journal WHERE session_id=? ORDER BY id DESC LIMIT ?",
                (session_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM v9_tpo_journal ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        conn.close()
        return {"entries": [dict(r) for r in rows]}
    except Exception as e:
        return {"entries": [], "error": str(e)}


@router.get("/sessions")
async def tpo_sessions(request: Request, date: str = ""):
    db_path = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        if date:
            rows = conn.execute(
                "SELECT * FROM v9_tpo_sessions WHERE trading_date=?", (date,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM v9_tpo_sessions ORDER BY id DESC LIMIT 10"
            ).fetchall()
        conn.close()
        return {"sessions": [dict(r) for r in rows]}
    except Exception as e:
        return {"sessions": [], "error": str(e)}


@router.get("/previous_day")
async def tpo_previous_day():
    """Previous trading day TPO summary (POC/VAH/VAL/IB/shape) from v9_tpo_sessions DB.

    Uses market_clock.get_previous_trading_day to skip weekends + holidays (D-070).
    """
    from backend.v9.services.market_clock import get_previous_trading_day
    db_path = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"

    prev_date = get_previous_trading_day()

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM v9_tpo_sessions WHERE trading_date=? AND session_type='CASH' ORDER BY id DESC LIMIT 1",
            (prev_date.isoformat(),),
        ).fetchone()
        conn.close()

        if not row:
            return {
                "session_date": prev_date.isoformat(),
                "found": False,
                "poc": None, "vah": None, "val": None,
                "ib_high": None, "ib_low": None, "ib_width": None,
                "profile_shape": None, "opening_type": None,
            }

        r = dict(row)
        return {
            "session_date": prev_date.isoformat(),
            "found": True,
            "poc": r.get("poc_price"),
            "vah": r.get("vah_price"),
            "val": r.get("val_price"),
            "ib_high": r.get("ib_high"),
            "ib_low": r.get("ib_low"),
            "ib_width": r.get("ib_width"),
            "profile_shape": r.get("profile_shape"),
            "opening_type": r.get("opening_type"),
            "range_high": r.get("range_high"),
            "range_low": r.get("range_low"),
        }
    except Exception as e:
        return {"session_date": prev_date.isoformat(), "found": False, "error": str(e)}
