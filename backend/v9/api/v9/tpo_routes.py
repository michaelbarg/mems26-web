"""API: /api/v9/tpo/* — System 5 TPO Profile."""
from datetime import datetime, time as _time, timedelta
from fastapi import APIRouter, Request
import json
import logging
import os
from pathlib import Path
import sqlite3
import time
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

router = APIRouter(prefix="/api/v9/tpo", tags=["tpo"])
_ET = ZoneInfo("America/New_York")
_UTC = ZoneInfo("UTC")
logger = logging.getLogger(__name__)

SIERRA_TPO_PATH = Path(
    os.getenv("V9_TPO_EXPORT_PATH", "/Users/michael/SierraChart_Data/v9_export/tpo.json")
)
SIERRA_TPO_MAX_AGE_S = float(os.getenv("V9_TPO_MAX_AGE_S", "30"))


def _norm_session_ts(ts) -> Optional[str]:
    """Align with chart bar ts: `YYYY-MM-DD HH:MM:SS` in America/New_York."""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        from datetime import datetime
        from zoneinfo import ZoneInfo

        return datetime.fromtimestamp(float(ts), tz=ZoneInfo("America/New_York")).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    s = str(ts).strip()
    if "T" in s:
        s = s.replace("T", " ")[:19]
    return s


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


def _rth_open_ts_today() -> Optional[str]:
    """RTH open (09:30 ET) of the current trading day, as `YYYY-MM-DD HH:MM:SS`.

    Required so the chart anchors the current-session POC at RTH start
    instead of the first visible bar. Sierra `tpo.json` omits session
    opened_ts (only POC/VAH/VAL are exported); using `now_et`'s date
    matches the trading_date that Sierra uses to build `session`.
    Pre-09:30 the value still points to today's upcoming open, which
    the frontend clamps to firstBar via `tsToBarT0`.
    """
    try:
        from datetime import datetime, time
        from zoneinfo import ZoneInfo

        now_et = datetime.now(tz=ZoneInfo("America/New_York"))
        open_et = datetime.combine(now_et.date(), time(9, 30), tzinfo=ZoneInfo("America/New_York"))
        return open_et.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        logger.warning("[tpo] rth_open_ts compute failed: %s", e)
        return None


DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"


def _load_periods_from_history(limit: int = 26) -> list:
    """Per-30-min snapshots from ``v9_tpo_history`` (P31 Issue B / B1 path).

    Each row is one TPO letter boundary captured by
    ``TPOHistorySnapshotter``. Frontend renders these as a stepped POC/VAH/VAL
    line matching Sierra Study ID:3 (developing TPO). Default ``limit=26``
    covers two full RTH sessions (13 letters × 2 days) — enough for today +
    yesterday on the chart.

    Returns a list shaped like ``v9_tpo_sessions`` periods (the frontend
    contract): ``opened_ts``, ``closed_ts``, ``poc_price``, ``vah_price``,
    ``val_price``. ``closed_ts`` is synthesized as opened_ts + 30 min so
    downstream consumers that filter by closed time still work.

    Returns ``[]`` (silent fall-through to the legacy sessions source) if
    the table is empty, the schema is unexpected, or any row-level access
    fails. This keeps the fallback path inside ``_load_tpo_periods`` simple.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT ts, poc, vah, val FROM v9_tpo_history "
            "WHERE poc IS NOT NULL "
            "ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
    except Exception as e:
        logger.warning("[tpo] _load_periods_from_history failed: %s", e)
        return []

    out: list = []
    for r in rows:
        try:
            ts_raw = r["ts"]
            poc = r["poc"]
        except (KeyError, IndexError):
            # Schema mismatch (e.g., legacy row coming from a shared mock or
            # an older table state) — bail out so the caller falls back to
            # `_load_periods_from_sessions`.
            return []
        opened_ts = _norm_session_ts(ts_raw)
        closed_ts = None
        # Synthesize closed_ts = opened_ts + 30 min so the frontend's
        # interval math has both endpoints.
        try:
            opened_dt = datetime.strptime(str(opened_ts), "%Y-%m-%d %H:%M:%S")
            closed_ts = (opened_dt + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError):
            closed_ts = None
        out.append(
            {
                "opened_ts": opened_ts,
                "closed_ts": closed_ts,
                "poc_price": poc,
                "vah_price": r["vah"] if "vah" in r.keys() else None,
                "val_price": r["val"] if "val" in r.keys() else None,
            }
        )
    # Frontend expects oldest → newest for stepped rendering (`buildStepData`
    # sorts ascending anyway, but matching here keeps the API contract obvious).
    out.reverse()
    return out


def _load_periods_from_sessions(limit: int = 12) -> list:
    """Legacy fallback: per-session daily rows from ``v9_tpo_sessions``.

    Used only when ``v9_tpo_history`` is empty (e.g., the snapshotter has
    not yet captured the current session — fresh deploy, replay startup,
    half-day where snapshotter was paused). Provides daily-granularity POC
    so the chart has *something* to render instead of a blank.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT opened_ts, closed_ts, poc_price, vah_price, val_price FROM v9_tpo_sessions "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
    except Exception as e:
        logger.warning("[tpo] _load_periods_from_sessions failed: %s", e)
        return []

    cutoff = time.time() - 48 * 3600
    out: list = []
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


def _load_tpo_periods(limit: int = 12) -> list:
    """Periods for the stepped POC overlay.

    Prefers ``v9_tpo_history`` (per-30-min snapshots from
    ``TPOHistorySnapshotter`` — Sierra Study ID:3 fidelity). Falls back to
    the legacy daily ``v9_tpo_sessions`` rows when history is empty so the
    chart still has data during the rollout window or when the snapshotter
    is disabled (``V9_DISABLE_TPO_SNAPSHOTTER=1``).
    """
    # B1 path — preferred. ``limit*2`` so we still expose ~13 today + ~13
    # yesterday letters when callers pass the legacy limit=12.
    history = _load_periods_from_history(limit=max(limit, 26))
    if history:
        return history
    # Legacy fallback.
    return _load_periods_from_sessions(limit=limit)


def _parse_previous_session_block(raw: dict) -> Optional[dict]:
    if not raw or raw.get("found") is False:
        return None
    poc, vah, val = raw.get("poc"), raw.get("vah"), raw.get("val")
    if poc is None and vah is None and val is None:
        return None
    return {
        "found": True,
        "poc": poc,
        "vah": vah,
        "val": val,
        "opened_ts": _norm_session_ts(raw.get("opened_ts")),
        "closed_ts": _norm_session_ts(raw.get("closed_ts")),
    }


def _load_previous_cash_session() -> Optional[dict]:
    """Last completed CASH TPO row — white Sierra reference lines (interim until DLL exports previous_session)."""
    try:
        conn = sqlite3.connect("/Users/michael/Downloads/mems26_web_git/data/mems26_local.db")
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT trading_date, poc_price, vah_price, val_price, opened_ts, closed_ts "
            "FROM v9_tpo_sessions WHERE session_type='CASH' AND poc_price IS NOT NULL "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if not row or row["poc_price"] is None:
            return None
        return {
            "found": True,
            "poc": float(row["poc_price"]),
            "vah": float(row["vah_price"]) if row["vah_price"] is not None else None,
            "val": float(row["val_price"]) if row["val_price"] is not None else None,
            "opened_ts": _norm_session_ts(row["opened_ts"]),
            "closed_ts": _norm_session_ts(row["closed_ts"]),
            "session_date": row["trading_date"],
        }
    except Exception as e:
        logger.warning("[tpo] previous cash session load failed: %s", e)
        return None


def _mes_price_ok(p: Optional[float]) -> bool:
    try:
        v = float(p)
        return 3000.0 <= v <= 10000.0
    except (TypeError, ValueError):
        return False


def _va_spread_ok(poc: Optional[float], vah: Optional[float], val: Optional[float], min_pts: float = 2.0) -> bool:
    if not (_mes_price_ok(poc) and _mes_price_ok(vah) and _mes_price_ok(val)):
        return False
    try:
        return (float(vah) - float(val)) >= min_pts and float(vah) >= float(poc) >= float(val)
    except (TypeError, ValueError):
        return False


def _merge_previous_session(raw: Optional[dict]) -> Optional[dict]:
    """Prefer DB cash session when Sierra previous_session block has corrupt prices."""
    db = _load_previous_cash_session()
    if not raw or raw.get("found") is False:
        return db
    out = {
        "found": True,
        "poc": raw.get("poc"),
        "vah": raw.get("vah"),
        "val": raw.get("val"),
        "opened_ts": _norm_session_ts(raw.get("opened_ts")),
        "closed_ts": _norm_session_ts(raw.get("closed_ts")),
    }
    if db:
        for key in ("poc", "vah", "val"):
            if not _mes_price_ok(out.get(key)) and _mes_price_ok(db.get(key)):
                out[key] = db[key]
        for key in ("opened_ts", "closed_ts"):
            if not out.get(key) and db.get(key):
                out[key] = db[key]
    if _va_spread_ok(out.get("poc"), out.get("vah"), out.get("val")):
        return out
    return db if db and _va_spread_ok(db.get("poc"), db.get("vah"), db.get("val")) else out


def _ib_from_bars() -> Optional[Tuple[float, float]]:
    """IB high/low from v9_bars_5min for today's 09:30-10:30 ET window.

    Returns (ib_high, ib_low) or None if no bars in window yet.
    More accurate than tpo.json because bars update every 5 min from Sierra.
    """
    try:
        today_et = datetime.now(_ET).date()
        rth_open = datetime.combine(today_et, _time(9, 30), tzinfo=_ET)
        ib_end = rth_open + timedelta(hours=1)
        rth_utc = rth_open.astimezone(_UTC).strftime("%Y-%m-%d %H:%M:%S")
        ib_utc = ib_end.astimezone(_UTC).strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect("/Users/michael/Downloads/mems26_web_git/data/mems26_local.db")
        row = conn.execute(
            "SELECT MAX(high), MIN(low) FROM v9_bars_5min "
            "WHERE symbol='MES' AND ts >= ? AND ts < ?",
            (rth_utc, ib_utc),
        ).fetchone()
        conn.close()
        if row and row[0] is not None and row[1] is not None:
            return (float(row[0]), float(row[1]))
    except Exception as e:
        logger.warning("[tpo] IB from bars failed: %s", e)
    return None


def _normalize_sierra_tpo(data: dict, age_s: float, *, stale: bool = False) -> dict:
    session = data.get("session") or {}
    ib = data.get("ib") or {}
    prior_day = data.get("prior_day") or {}
    prev_sess = _merge_previous_session(
        _parse_previous_session_block(data.get("previous_session") or data.get("prior_session") or {})
    )

    ib_found = bool(ib.get("found"))
    ib_high = ib.get("high") if ib_found else None
    ib_low = ib.get("low") if ib_found else None
    ib_mid = ib.get("mid") if ib_found else None

    # P31 IB accuracy fix: override DLL IB with v9_bars_5min which tracks
    # Sierra tick-by-tick and is always current. DLL tpo.json ib can lag.
    bars_ib = _ib_from_bars()
    if bars_ib is not None:
        ib_high, ib_low = bars_ib
        ib_found = True
        ib_mid = (ib_high + ib_low) / 2.0

    ib_width = None
    if ib_high is not None and ib_low is not None:
        ib_width = ib_high - ib_low

    poc, vah, val = session.get("poc"), session.get("vah"), session.get("val")
    session_va_ok = _va_spread_ok(poc, vah, val)
    if not session_va_ok:
        # Memorial Day fix #3: reject-and-warn (was: silent synthesis from DB).
        # Per CLAUDE.md "Source of truth: live values come from Sierra Chart
        # exports ... not from backend ... synthesizing OHLC, TPO, CVD, or
        # Woodies study fields." When Sierra session VA is invalid, return
        # None and let downstream consumers handle the degraded state.
        logger.warning(
            "[tpo] Sierra session VA invalid (poc=%r vah=%r val=%r) — "
            "rejecting · NO synthesis from DB",
            poc, vah, val,
        )
        poc, vah, val = None, None, None

    session_opened_ts = _norm_session_ts(
        session.get("opened_ts") or data.get("session_opened_ts")
    ) or _rth_open_ts_today()

    return {
        "running": True,
        "hydrated": True,
        "source": "sierra_tpo_json",
        "version": data.get("version"),
        "export_ts": data.get("export_ts"),
        "age_s": round(age_s, 3),
        "stale": stale,
        "session_type": "SIERRA",
        "poc": poc,
        "vah": vah,
        "val": val,
        "session_opened_ts": session_opened_ts,
        "session_va_ok": session_va_ok,
        "session_high": session.get("session_high"),
        "session_low": session.get("session_low"),
        "total_volume": session.get("total_volume"),
        "ib_high": ib_high,
        "ib_mid": ib_mid,
        "ib_low": ib_low,
        "ib_locked": ib_found,
        "ib_found": ib_found,
        "ib_width": ib_width,
        "prior_day": {
            "found": bool(prior_day.get("found")),
            "high": prior_day.get("high"),
            "low": prior_day.get("low"),
            "close": prior_day.get("close"),
        },
        "previous_session": prev_sess,
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
        logger.warning("[tpo] Sierra export missing: %s", path)
        return None
    age_s = time.time() - path.stat().st_mtime
    stale = age_s > max_age_s
    if stale:
        logger.warning(
            "[tpo] Sierra tpo.json stale age=%.1fs > %.1fs — serving anyway (no TPOSystem fallback)",
            age_s,
            max_age_s,
        )
    try:
        with path.open() as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("[tpo] Sierra tpo.json read error: %s", e)
        return None
    if data.get("type") != "tpo":
        logger.warning("[tpo] Unexpected Sierra TPO type=%s path=%s", data.get("type"), path)
        return None
    out = _normalize_sierra_tpo(data, age_s, stale=stale)
    out["periods"] = _load_tpo_periods()
    if stale:
        out["error"] = f"Sierra TPO export stale ({age_s:.0f}s > {max_age_s:.0f}s)"
    return out


@router.get("/current")
async def tpo_current(request: Request):
    sierra_tpo = _load_sierra_tpo()
    if sierra_tpo is not None:
        return sierra_tpo

    logger.warning("[tpo] Sierra export unavailable — returning empty TPO (no in-memory fallback)")
    return {
        "running": False,
        "hydrated": False,
        "source": "missing",
        "error": "Sierra tpo.json missing or unreadable",
        "poc": None,
        "vah": None,
        "val": None,
        "session_va_ok": False,
        "periods": [],
        "previous_session": _load_previous_cash_session(),
    }


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
    from backend.v9.systems.day_type.prev_day import load_tpo_previous_day_summary

    return load_tpo_previous_day_summary()
