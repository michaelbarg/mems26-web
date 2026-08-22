"""API: /api/v9/tpo/* — System 5 TPO Profile."""
from datetime import datetime, time as _time, timedelta
from fastapi import APIRouter, Request
import json
import logging
import os
from pathlib import Path
import time
from typing import Optional
from zoneinfo import ZoneInfo

from backend.v9.db.read import read_all, read_one, read_scalar

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
    rows = read_all(
        "SELECT ts, poc, vah, val FROM v9_tpo_history "
        "WHERE poc IS NOT NULL "
        "ORDER BY ts DESC LIMIT :limit",
        {"limit": limit},
    )

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
    rows = read_all(
        "SELECT opened_ts, closed_ts, poc_price, vah_price, val_price FROM v9_tpo_sessions "
        "ORDER BY id DESC LIMIT :limit",
        {"limit": limit},
    )

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
    # Step 9 (2026-05-28): DLL emits previous_session.ib_high/ib_low when
    # Sierra Input 19 (Yesterday IB Study ID) points at a configured study.
    # Treat 0/None or `ib_found:false` as missing (no synthesis).
    ib_found = bool(raw.get("ib_found"))
    ib_high = raw.get("ib_high") if ib_found else None
    ib_low = raw.get("ib_low") if ib_found else None
    if not _mes_price_ok(ib_high):
        ib_high = None
    if not _mes_price_ok(ib_low):
        ib_low = None
    return {
        "found": True,
        "poc": poc,
        "vah": vah,
        "val": val,
        "ib_high": ib_high,
        "ib_low": ib_low,
        "ib_found": ib_high is not None and ib_low is not None,
        "opened_ts": _norm_session_ts(raw.get("opened_ts")),
        "closed_ts": _norm_session_ts(raw.get("closed_ts")),
    }


def _load_previous_cash_session() -> Optional[dict]:
    """Last completed CASH TPO row — white Sierra reference lines (interim until DLL exports previous_session)."""
    try:
        from backend.v9.common.trading_date import et_today as _et_today
        row = read_one(
            "SELECT trading_date, poc_price, vah_price, val_price, opened_ts, closed_ts "
            "FROM v9_tpo_sessions WHERE session_type='CASH' AND poc_price IS NOT NULL "
            "AND trading_date < :today "
            "ORDER BY id DESC LIMIT 1",
            {"today": _et_today().isoformat()},
        )
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
        # Step 9: DB cash session has no IB data — fall through with ib_*=None.
        if db is not None:
            db.setdefault("ib_high", None)
            db.setdefault("ib_low", None)
            db.setdefault("ib_found", False)
        return db
    out = {
        "found": True,
        "poc": raw.get("poc"),
        "vah": raw.get("vah"),
        "val": raw.get("val"),
        # Step 9 (2026-05-28): pass-through Sierra Y IB. DB has no IB data,
        # so we never synthesise — None when DLL did not export it.
        "ib_high": raw.get("ib_high"),
        "ib_low": raw.get("ib_low"),
        "ib_found": bool(raw.get("ib_found")),
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
    if db and _va_spread_ok(db.get("poc"), db.get("vah"), db.get("val")):
        # Falling back to DB → drop any Sierra IB to avoid mixing sources.
        db.setdefault("ib_high", None)
        db.setdefault("ib_low", None)
        db.setdefault("ib_found", False)
        return db
    return out



def _normalize_sierra_tpo(data: dict, age_s: float, *, stale: bool = False) -> dict:
    session = data.get("session") or {}
    ib = data.get("ib") or {}
    prior_day = data.get("prior_day") or {}
    prev_sess = _merge_previous_session(
        _parse_previous_session_block(data.get("previous_session") or data.get("prior_session") or {})
    )

    # IB source: Sierra Initial Balance Study only (2026-05-28 evening revocation).
    # No bars-derived synthesis — per CLAUDE.md Rule 1 (honest failure > synthetic value).
    ib_found = bool(ib.get("found"))
    if ib_found:
        ib_high = ib.get("high")
        ib_low = ib.get("low")
        ib_mid = ib.get("mid")
        ib_source = "sierra_live"
    else:
        ib_high = None
        ib_low = None
        ib_mid = None
        ib_source = "missing"

    # ── IB_BARS_VALIDATE_V1 (2026-08-14, Michael: "IB תתוקן שם … הוא צריך
    # להיות מקביל של מק-1"). NOT synthesis — VALIDATION.
    # Rule 1 (honest failure > synthetic value) forbids inventing an IB when the
    # study is SILENT. Here the study is not silent, it is WRONG: mac-2's Sierra
    # reported ib 7817.50/7808.00 for a session whose real 09:30-10:30 ET range
    # (from the ingested canonical bars, byte-identical on both machines) is
    # 7830.75/7813.75 — a window an hour late. That bogus ib_low became the T1
    # target and killed every candidate on R:R (last one: R:R 0.19, T1 1.0pt).
    # CLAUDE.md explicitly allows "trading logic on ingested bars"; the extremes
    # of the first twelve RTH bars ARE the initial balance. When Sierra's value
    # disagrees with the bars by more than a tick we serve the bars value and
    # SAY SO in ib_source (no flag-laundering — the provenance stays honest).
    # Only runs once the window is complete (>=10:30 ET) and bars exist.
    if os.getenv("IB_BARS_VALIDATE_V1", "0").lower() in ("1", "true", "yes"):
        try:
            from datetime import datetime as _ib_dt, time as _ib_t
            from zoneinfo import ZoneInfo as _ib_zi
            _et_now = _ib_dt.now(_ib_zi("America/New_York"))
            if _et_now.time() >= _ib_t(10, 30):
                from backend.v9.db.read import read_one as _ib_read
                _row = _ib_read(
                    "SELECT MAX(high) AS h, MIN(low) AS l, COUNT(*) AS n "
                    "FROM v9_bars_5min_woodies "
                    "WHERE (ts AT TIME ZONE 'America/New_York')::date = "
                    "(now() AT TIME ZONE 'America/New_York')::date "
                    "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
                    "AND (ts AT TIME ZONE 'America/New_York')::time < '10:30'", {})
                _bh = float(_row["h"]) if _row and _row.get("h") is not None else None
                _bl = float(_row["l"]) if _row and _row.get("l") is not None else None
                _bn = int(_row["n"]) if _row and _row.get("n") is not None else 0
                if _bh is not None and _bl is not None and _bn >= 12:
                    _mismatch = (
                        ib_high is None or ib_low is None
                        or abs(float(ib_high) - _bh) > 0.25
                        or abs(float(ib_low) - _bl) > 0.25
                    )
                    if _mismatch:
                        logger.warning(
                            "[tpo] IB CORRECTION: Sierra reported %s/%s but the "
                            "ingested RTH bars (%d) give %s/%s — serving the bars "
                            "value (ib_source=bars_derived_correction)",
                            ib_high, ib_low, _bn, _bh, _bl)
                        ib_high, ib_low = _bh, _bl
                        ib_mid = round((_bh + _bl) / 2.0, 2)
                        ib_found = True
                        ib_source = "bars_derived_correction"
        except Exception as _ib_err:
            logger.warning("[tpo] IB validation errored (Sierra value kept): %s", _ib_err)

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
        "ib_source": ib_source,
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
        "extremes": _extremes_for_tpo(),
    }


def _extremes_for_tpo() -> Optional[dict]:
    """Excess/Poor extremes for TPO panel display (Dalton Step 1)."""
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


def _load_sierra_tpo(path: Path = SIERRA_TPO_PATH, max_age_s: float = SIERRA_TPO_MAX_AGE_S) -> Optional[dict]:
    if not path.exists():
        logger.warning("[tpo] Sierra export missing: %s", path)
        return None
    age_s = time.time() - path.stat().st_mtime
    stale = age_s > max_age_s
    if stale:
        # Gap #5: demoted to INFO — fires on every frontend poll (229/828)
        logger.info(
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
    try:
        if session_id:
            rows = read_all(
                "SELECT * FROM v9_tpo_journal WHERE session_id=:session_id ORDER BY id DESC LIMIT :limit",
                {"session_id": session_id, "limit": limit},
            )
        else:
            rows = read_all(
                "SELECT * FROM v9_tpo_journal ORDER BY id DESC LIMIT :limit",
                {"limit": limit},
            )
        return {"entries": rows}
    except Exception as e:
        return {"entries": [], "error": str(e)}


@router.get("/sessions")
async def tpo_sessions(request: Request, date: str = ""):
    try:
        if date:
            rows = read_all(
                "SELECT * FROM v9_tpo_sessions WHERE trading_date=:date",
                {"date": date},
            )
        else:
            rows = read_all(
                "SELECT * FROM v9_tpo_sessions ORDER BY id DESC LIMIT 10"
            )
        return {"sessions": rows}
    except Exception as e:
        return {"sessions": [], "error": str(e)}


@router.get("/previous_day")
async def tpo_previous_day():
    """Previous trading day TPO summary (POC/VAH/VAL/IB/shape) from v9_tpo_sessions DB.

    Uses market_clock.get_previous_trading_day to skip weekends + holidays (D-070).
    """
    from backend.v9.systems.day_type.prev_day import load_tpo_previous_day_summary

    return load_tpo_previous_day_summary()
