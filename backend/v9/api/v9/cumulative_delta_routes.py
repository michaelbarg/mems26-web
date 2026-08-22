"""API: /api/v9/cumulative_delta — read Sierra cumulative_delta.json export.

Direct file read for lowest latency (same machine). No bridge dependency.
Pattern mirrors price_routes.py and tpo_routes.py.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter

router = APIRouter(tags=["cumulative-delta"])
logger = logging.getLogger(__name__)

EXPORT_PATH = Path(
    os.getenv(
        "V9_CUMDELTA_EXPORT_PATH",
        "/Users/michael/SierraChart_Data/v9_export/cumulative_delta_continuous.json",
    )
)
MAX_AGE_S = float(os.getenv("V9_CUMDELTA_MAX_AGE_S", "30"))

# P31 §A — DLL TZ workaround mirrors the bridge fix in
# ``bridge/v9_streams/cumulative_delta_stream.py``. This endpoint reads
# cumulative_delta.json directly (not from the bridge-pushed DB rows), so the
# bridge workaround has no effect here and we have to repeat it. Once the
# canonical DLL fix (§9 Option A) ships, set ``V9_DISABLE_CHICAGO_TS_FIX=1``.
_DISABLE_CHICAGO_TS_FIX = os.getenv("V9_DISABLE_CHICAGO_TS_FIX", "0") == "1"
try:  # zoneinfo is the stdlib path (Python 3.9+); pytz fallback for old envs
    from zoneinfo import ZoneInfo as _ZI  # type: ignore[import-not-found]
    _CHICAGO_TZ = _ZI("America/Chicago")
    _CHICAGO_TZ_USES_LOCALIZE = False
except Exception:
    try:
        import pytz  # type: ignore[import-not-found]
        _CHICAGO_TZ = pytz.timezone("America/Chicago")
        _CHICAGO_TZ_USES_LOCALIZE = True
    except Exception:
        _CHICAGO_TZ = None
        _CHICAGO_TZ_USES_LOCALIZE = False


def _chicago_to_utc(ts):
    """Re-interpret a Chicago-wall-clock unix value as true UTC unix."""
    if ts is None or _CHICAGO_TZ is None:
        return ts
    try:
        t = float(ts)
    except (TypeError, ValueError):
        return ts
    naive = datetime.utcfromtimestamp(t)
    if _CHICAGO_TZ_USES_LOCALIZE:  # pytz
        aware = _CHICAGO_TZ.localize(naive)  # type: ignore[attr-defined]
    else:  # zoneinfo
        aware = naive.replace(tzinfo=_CHICAGO_TZ)
    fixed = int(aware.timestamp())
    return float(fixed) if isinstance(ts, float) else fixed


def _fix_chicago_points(points: list) -> list:
    """Walk CVD `points` and rewrite each `t` from buggy Chicago-encoded to
    real UTC unix. ``export_ts`` is NOT touched (already true UTC via
    ``time(nullptr)`` in the DLL). Returns the same list (mutates in place).
    """
    if _DISABLE_CHICAGO_TS_FIX or not isinstance(points, list):
        return points
    for p in points:
        if isinstance(p, dict) and "t" in p:
            p["t"] = _chicago_to_utc(p["t"])
    return points

# Sierra DLL canonical source emits `t` (unix UTC) and top-level
# `output_interval` per CVD point as of v9.4.2 (see sc_study/v9_exports.h).
# Backend prefers those when present.
#
# For older DLL builds where `output_interval` is missing, we derive the
# period from the observed `i`-step between consecutive points multiplied
# by the host-chart bar period (5 min = 300 s by default — the host that
# MES_AI_DataExport is attached to). This auto-corrects whether the DLL
# is still using the `% 5` filter (i-step ≈ 5 → 1500 s/point) or the new
# unfiltered emission (i-step ≈ 1 → 300 s/point).
HOST_BAR_S = float(os.getenv("V9_CVD_HOST_BAR_S", "300"))
# Legacy alias — preserved so existing tests/configs that set V9_CVD_PERIOD_S
# directly continue to control the per-point cadence used as the absolute
# fallback when both `output_interval` and `i` are missing.
CVD_PERIOD_S = float(os.getenv("V9_CVD_PERIOD_S", str(HOST_BAR_S)))


def _derive_period_s(data: dict, points: list) -> float:
    """Resolve seconds-per-point in priority order:
    1. DLL top-level `output_interval` (canonical post-v9.4.2)
    2. Observed `i`-step between consecutive points × HOST_BAR_S
    3. CVD_PERIOD_S env default

    Returning a float so float arithmetic in `_augment_points_with_t`
    survives unchanged.
    """
    explicit = data.get("output_interval")
    if explicit is not None:
        try:
            v = float(explicit)
            if v > 0:
                return v
        except (TypeError, ValueError):
            pass
    if isinstance(points, list) and len(points) >= 2:
        try:
            first_i = int(points[0]["i"])
            last_i = int(points[-1]["i"])
            n = len(points) - 1
            if n > 0:
                step = max(1, abs(last_i - first_i) // n)
                return float(step) * HOST_BAR_S
        except (KeyError, TypeError, ValueError):
            pass
    return CVD_PERIOD_S


def _augment_points_with_t(points: list, export_ts: float, period_s: float = CVD_PERIOD_S) -> list:
    """Assign a timestamp to each point so the CVD chart shares an X axis with
    the price chart. Last point anchors at export_ts; earlier points step back
    by period_s. Skip silently if DLL already ships its own `t` (the canonical
    path post-v9.4.2).
    """
    if not points:
        return points
    if all("t" in p for p in points):
        return points
    n = len(points)
    last_ts = int(export_ts)
    for idx, p in enumerate(points):
        if "t" not in p:
            p["t"] = int(last_ts - (n - 1 - idx) * period_s)
    return points


# P31 §B — CVD history depth. Frontend chart shows up to 600 5-min bars
# (5h on a 5m chart). The rolling JSON tail is only ~14 points (~1h), leaving
# the older 46 CVD candles blank. Backfill from ``v9_bars_cumulative_delta``
# (DB-persisted by ``bars.py::post_cumulative_delta``) when callers ask for
# a wider window via ``?history=1``.
DEFAULT_HISTORY_LIMIT = int(os.getenv("V9_CVD_HISTORY_LIMIT", "600"))


def _parse_ts_to_unix(ts):
    """Convert DB ``ts`` (naive UTC ``YYYY-MM-DD HH:MM:SS.ffffff`` or ISO with
    ``+00:00`` / ``Z``) to UTC unix seconds. Mirrors the frontend's
    ``parseSierraTsToMs`` so chart axis alignment stays consistent.

    Returns int or None; types kept implicit so the module imports cleanly
    on Python 3.9 (no PEP 604 ``str | None``).
    """
    if not ts:
        return None
    raw = str(ts).strip().replace(" ", "T")
    # Detect explicit TZ suffix; default to UTC otherwise (post-§9 convention).
    has_tz = raw.endswith("Z") or raw.endswith("z") or len(raw) >= 6 and raw[-6] in "+-" and ":" in raw[-6:]
    iso = raw if has_tz else raw + "Z"
    try:
        from datetime import datetime as _dt
        if iso.endswith("Z") or iso.endswith("z"):
            iso = iso[:-1] + "+00:00"
        return int(_dt.fromisoformat(iso).timestamp())
    except Exception:
        return None


def _load_db_history(before_unix: int, limit: int) -> List[dict]:
    """Pull DB rows older than ``before_unix`` so the chart can render the
    full CVD pane width. Returns rows shaped like Sierra JSON points
    (``{i, t, d, cum, p}``) sorted ascending by ``t``.

    Failures are non-fatal — the live JSON points always win and the
    endpoint never breaks on a DB issue.
    """
    if limit <= 0:
        return []
    try:
        from backend.v9.db.session import SessionLocal
        from sqlalchemy import text as _text
    except Exception as e:
        logger.warning("[CVD] history DB import failed: %s", e)
        return []
    rows: List[dict] = []
    session = None
    try:
        session = SessionLocal()
        result = session.execute(
            _text(
                "SELECT ts, delta, cumulative FROM v9_bars_cumulative_delta "
                "ORDER BY ts DESC LIMIT :lim"
            ),
            {"lim": int(limit)},
        )
        for idx, row in enumerate(result.fetchall()):
            ts = row[0]
            t = _parse_ts_to_unix(ts)
            if t is None or t >= before_unix:
                continue
            rows.append(
                {
                    "i": -idx - 1,  # negative idx marks DB-sourced points
                    "t": t,
                    "d": float(row[1]) if row[1] is not None else 0.0,
                    "cum": float(row[2]) if row[2] is not None else 0.0,
                    "p": 0.0,  # price not stored in this table; not used by chart
                }
            )
    except Exception as e:
        logger.warning("[CVD] history DB query failed: %s", e)
        return []
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:
                pass
    rows.sort(key=lambda r: r["t"])
    return rows


@router.get("/api/v9/cumulative_delta/current")
async def cumulative_delta_current(history: int = 0, limit: int = DEFAULT_HISTORY_LIMIT):
    """Return current cumulative delta from Sierra DLL export.

    File: cumulative_delta.json (written every ~3s by DLL)
    Shape: { type, version, export_ts, points[], current_delta, session_delta, peak, trough }

    Query params:
      - ``history=1`` — prepend DB-persisted points from
        ``v9_bars_cumulative_delta`` so the chart's CVD pane renders the
        full window (not just the rolling 14-point tail). Default off so
        legacy callers keep the lightweight response.
      - ``limit`` — max DB history rows to fetch (default 600 → 5h @ 5m).
    """
    if not EXPORT_PATH.exists():
        logger.warning("[CVD] cumulative_delta.json not found at %s", EXPORT_PATH)
        return {"source": "missing", "error": "cumulative_delta.json not found"}

    try:
        mtime = EXPORT_PATH.stat().st_mtime
        age_s = time.time() - mtime

        stale = age_s > MAX_AGE_S
        if stale:
            # Gap #5: demoted to INFO — fires on every frontend poll (184/828)
            logger.info("[CVD] cumulative_delta.json stale: age=%.1fs > %.1fs — serving anyway", age_s, MAX_AGE_S)

        with open(EXPORT_PATH, "r") as f:
            data = json.load(f)

        points = data.get("points", [])
        export_ts = data.get("export_ts") or mtime
        # Resolve cadence: explicit `output_interval` > observed i-step > env default.
        period_s = _derive_period_s(data, points)
        points = _augment_points_with_t(points, float(export_ts), period_s)
        # P31 §A — rewrite Chicago-encoded `t` to true UTC unix so the chart
        # CVD pane lines up with price bars on the shared timeScale. Safe
        # no-op when `V9_DISABLE_CHICAGO_TS_FIX=1`.
        points = _fix_chicago_points(points)

        history_count = 0
        if history and points:
            first_live_t = min(int(p["t"]) for p in points if isinstance(p.get("t"), (int, float)))
            db_points = _load_db_history(before_unix=first_live_t, limit=int(limit))
            history_count = len(db_points)
            if db_points:
                # DB points first (older), then live JSON points (newer).
                points = db_points + points

        out = {
            "source": "sierra_cumulative_delta_json",
            "version": data.get("version"),
            "age_s": round(age_s, 1),
            "stale": stale,
            "current_delta": data.get("current_delta"),
            "session_delta": data.get("session_delta"),
            "peak": data.get("peak"),
            "trough": data.get("trough"),
            "point_count": len(points),
            "history_count": history_count,
            "points": points,
            "period_s": period_s,
        }
        if stale:
            out["error"] = f"File stale ({age_s:.0f}s > {MAX_AGE_S:.0f}s threshold)"
        return out
    except json.JSONDecodeError:
        logger.warning("[CVD] cumulative_delta.json parse error")
        return {"source": "sierra_cumulative_delta_json", "error": "JSON parse error"}
    except Exception as e:
        logger.warning("[CVD] cumulative_delta.json read error: %s", e)
        return {"source": "sierra_cumulative_delta_json", "error": str(e)}
