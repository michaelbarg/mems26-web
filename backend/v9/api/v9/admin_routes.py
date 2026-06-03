"""P31 Phase 2 — Admin / operator endpoints for the cockpit System Control Panel.

Michael 2026-05-22 (Hebrew): "תוסיף כפתור הפעלה, כיבוי, ריסטרט, גאפ פיל,
בדאשבורד - אני רוצה שאם עכשיו מדליקים כבר נקבל את כל ההיסטוריה."
("Add Start / Stop / Restart / Gap-fill buttons in the dashboard — I want
that when we turn on [the system], we already get all the history.")

Endpoints:

  * ``GET  /api/v9/admin/services/status`` — list managed background services
    (TPO snapshotter, EOD archive scheduler) with their running state and
    last-known result so the cockpit panel renders Start/Stop/Restart hints.
  * ``POST /api/v9/admin/services/{name}/start`` — start a stopped service.
  * ``POST /api/v9/admin/services/{name}/stop``  — stop a running service.
  * ``POST /api/v9/admin/services/{name}/restart`` — stop + start.
  * ``POST /api/v9/admin/history/gap_fill`` — invoke the gap-fill loader on
    demand. Same code path as the FastAPI startup hook, so the operator
    can re-sync the DB to Sierra at any time (e.g., after a desktop reboot
    or a Sierra Chart restart).
  * ``GET  /api/v9/admin/history/last_gap_fill`` — last gap-fill summary.
  * ``GET  /api/v9/admin/history/db_state`` — per-table row counts +
    MAX(ts) for the cockpit panel's "Data Health" display.

All endpoints require the bridge token (same `verify_bridge_token` guard
the rest of the v9 API uses). This is an operator surface; not exposed to
unauthenticated clients.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.v9.api.v9.auth import verify_bridge_token
from backend.v9.services import eod_archiver
from backend.v9.services.eod_archive_scheduler import get_scheduler as _get_eod_sched
from backend.v9.services.history_loader import (
    DEFAULT_DB_PATH,
    get_loader as _get_history_loader,
)
from backend.v9.db.read import read_scalar
from backend.v9.services.tpo_history_snapshotter import (
    get_snapshotter as _get_tpo_snap,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v9/admin", tags=["admin"])

# Note: the loader instance itself caches its last summary on
# ``HistoryLoader.last_summary``. We read through that so the startup
# gap-fill (which Cursor's `main.py` runs at boot) is visible to this
# endpoint without needing to share a module-level variable.


# ----------------------------------------------------------------------
# Service registry — single place to add/remove operator-managed services
# ----------------------------------------------------------------------


def _service_handles():
    """Return a name → (getter, description) registry. ``getter`` returns
    the singleton instance which exposes ``.start()``, ``.stop()`` (async),
    ``.is_running``."""
    return {
        "tpo_snapshotter": (
            _get_tpo_snap,
            "TPO history snapshotter — writes v9_tpo_history every 30 min during RTH",
        ),
        "eod_archive_scheduler": (
            _get_eod_sched,
            "EOD archive scheduler — copies Sierra exports to ~/v9_archive at 15:55 ET",
        ),
    }


def _serialize_service(name: str, instance, description: str) -> Dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "running": bool(getattr(instance, "is_running", False)),
        "class": instance.__class__.__name__,
    }


# ----------------------------------------------------------------------
# GET /api/v9/admin/services/status
# ----------------------------------------------------------------------


@router.get("/services/status")
def services_status(_token: str = Depends(verify_bridge_token)) -> Dict[str, Any]:
    services = []
    for name, (getter, description) in _service_handles().items():
        try:
            inst = getter()
            services.append(_serialize_service(name, inst, description))
        except Exception as e:  # never fail the status endpoint
            services.append(
                {"name": name, "description": description, "running": False, "error": str(e)}
            )
    return {"services": services, "as_of_utc": datetime.utcnow().isoformat() + "Z"}


# ----------------------------------------------------------------------
# POST /api/v9/admin/services/{name}/{action}
# ----------------------------------------------------------------------


@router.post("/services/{name}/start")
def service_start(name: str, _token: str = Depends(verify_bridge_token)) -> Dict[str, Any]:
    inst = _resolve_service(name)
    try:
        inst.start()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"start failed: {e}")
    return {"ok": True, "name": name, "running": inst.is_running}


@router.post("/services/{name}/stop")
async def service_stop(name: str, _token: str = Depends(verify_bridge_token)) -> Dict[str, Any]:
    inst = _resolve_service(name)
    try:
        await inst.stop()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"stop failed: {e}")
    return {"ok": True, "name": name, "running": inst.is_running}


@router.post("/services/{name}/restart")
async def service_restart(name: str, _token: str = Depends(verify_bridge_token)) -> Dict[str, Any]:
    inst = _resolve_service(name)
    try:
        await inst.stop()
    except Exception as e:
        logger.warning("[admin] %s stop during restart failed (continuing): %s", name, e)
    try:
        inst.start()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"restart failed at start step: {e}")
    return {"ok": True, "name": name, "running": inst.is_running}


def _resolve_service(name: str):
    handles = _service_handles()
    if name not in handles:
        raise HTTPException(
            status_code=404,
            detail=f"unknown service '{name}'. Available: {list(handles.keys())}",
        )
    getter, _desc = handles[name]
    return getter()


# ----------------------------------------------------------------------
# POST /api/v9/admin/history/gap_fill — manual trigger
# ----------------------------------------------------------------------


@router.post("/history/gap_fill")
def history_gap_fill(_token: str = Depends(verify_bridge_token)) -> Dict[str, Any]:
    """Run the gap-fill loader once and return the per-stream summary.

    Synchronous + bounded (rolling-tail exports complete in <1 s wall-clock
    on the dev machine). Safe to invoke from a button click — operator
    sees the summary in the same response. The loader caches the result
    on ``HistoryLoader.last_summary`` so ``GET /history/last_gap_fill``
    returns the same payload without re-running.
    """
    loader = _get_history_loader()
    return loader.run_gap_fill(reason="admin_manual")


@router.get("/history/last_gap_fill")
def history_last_gap_fill(_token: str = Depends(verify_bridge_token)) -> Dict[str, Any]:
    loader = _get_history_loader()
    if loader.last_summary is None:
        return {"never_run": True}
    return loader.last_summary


# ----------------------------------------------------------------------
# GET /api/v9/admin/history/db_state — per-table row counts + MAX(ts)
# ----------------------------------------------------------------------


# Tables the cockpit displays as "data health".
#
# Each entry: ``(table, ts_column)``. The query stays small (4 tables) so
# the endpoint completes in < 3 s even under bridge-POST contention on the
# single-worker uvicorn. Long history tables (woodies, tick_reversal,
# system_signals) are intentionally excluded — the dashboard surfaces
# them via separate, dedicated endpoints if needed, and they aren't part
# of the "is my data flowing right now" health signal.
_DB_STATE_TABLES = (
    ("v9_bars_5min", "ts"),
    ("v9_bars_cumulative_delta", "ts"),
    ("v9_bars_volume_profile", "ts"),
    ("v9_tpo_history", "ts"),
    ("v9_trades", "entry_ts"),
)


@router.get("/history/db_state")
def history_db_state(_token: str = Depends(verify_bridge_token)) -> Dict[str, Any]:
    """Per-table exact COUNT(*) + MAX(ts) for the cockpit Data Health panel.

    Targets the 5 cockpit-critical tables; total wall time < 3 s under
    bridge-POST contention on single-worker uvicorn. Avoids ``MAX(id)``
    because the dedicated tables use ``INSERT OR IGNORE``, which still
    advances the auto-increment id on rejected duplicates — id high
    water is not a reliable row-count proxy.
    """
    out = {"tables": []}
    for table, ts_col in _DB_STATE_TABLES:
        try:
            row = read_scalar(
                f"SELECT COUNT(*) FROM {table}"
            )
            max_ts = read_scalar(
                f"SELECT MAX({ts_col}) FROM {table}"
            )
            out["tables"].append(
                {
                    "table": table,
                    "ts_col": ts_col,
                    "rows": row,
                    "max_ts": max_ts,
                }
            )
        except Exception as e:
            out["tables"].append(
                {"table": table, "ts_col": ts_col, "error": str(e)}
            )
    out["as_of_utc"] = datetime.utcnow().isoformat() + "Z"
    return out


# ----------------------------------------------------------------------
# GET /api/v9/admin/archive_state — archiver status for the panel
# ----------------------------------------------------------------------


@router.get("/archive_state")
def archive_state(_token: str = Depends(verify_bridge_token)) -> Dict[str, Any]:
    dates = eod_archiver.list_archived_dates()
    return {
        "archive_dir": str(eod_archiver.ARCHIVE_DIR),
        "retention_days": eod_archiver.ARCHIVE_RETENTION_DAYS,
        "files_per_archive": list(eod_archiver.ARCHIVED_FILES),
        "dates_present": dates[:30],  # cap for UI
        "total_archived_days": len(dates),
    }
