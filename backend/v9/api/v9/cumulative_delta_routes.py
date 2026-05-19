"""API: /api/v9/cumulative_delta — read Sierra cumulative_delta.json export.

Direct file read for lowest latency (same machine). No bridge dependency.
Pattern mirrors price_routes.py and tpo_routes.py.
"""

import json
import logging
import os
import time
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(tags=["cumulative-delta"])
logger = logging.getLogger(__name__)

EXPORT_PATH = Path(
    os.getenv(
        "V9_CUMDELTA_EXPORT_PATH",
        "/Users/michael/SierraChart_Data/v9_export/cumulative_delta.json",
    )
)
MAX_AGE_S = float(os.getenv("V9_CUMDELTA_MAX_AGE_S", "30"))


@router.get("/api/v9/cumulative_delta/current")
async def cumulative_delta_current():
    """Return current cumulative delta from Sierra DLL export.

    File: cumulative_delta.json (written every ~3s by DLL)
    Shape: { type, version, export_ts, points[], current_delta, session_delta, peak, trough }
    """
    if not EXPORT_PATH.exists():
        logger.warning("[CVD] cumulative_delta.json not found at %s", EXPORT_PATH)
        return {"source": "missing", "error": "cumulative_delta.json not found"}

    try:
        mtime = EXPORT_PATH.stat().st_mtime
        age_s = time.time() - mtime

        if age_s > MAX_AGE_S:
            logger.warning("[CVD] cumulative_delta.json stale: age=%.1fs > %.1fs", age_s, MAX_AGE_S)
            return {
                "source": "sierra_cumulative_delta_json",
                "stale": True,
                "age_s": round(age_s, 1),
                "error": f"File stale ({age_s:.0f}s > {MAX_AGE_S:.0f}s threshold)",
            }

        with open(EXPORT_PATH, "r") as f:
            data = json.load(f)

        points = data.get("points", [])

        return {
            "source": "sierra_cumulative_delta_json",
            "version": data.get("version"),
            "age_s": round(age_s, 1),
            "stale": False,
            "current_delta": data.get("current_delta"),
            "session_delta": data.get("session_delta"),
            "peak": data.get("peak"),
            "trough": data.get("trough"),
            "point_count": len(points),
            "points": points,
        }
    except json.JSONDecodeError:
        logger.warning("[CVD] cumulative_delta.json parse error")
        return {"source": "sierra_cumulative_delta_json", "error": "JSON parse error"}
    except Exception as e:
        logger.warning("[CVD] cumulative_delta.json read error: %s", e)
        return {"source": "sierra_cumulative_delta_json", "error": str(e)}
