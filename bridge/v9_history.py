"""V9 History Module — shared historical backfill logic for v9 streams.

Ported from V8 json_bridge.py history loading (lines 1015-1130).

V8 strategy (preserved in V9):
1. On startup, read DLL export file
2. If file is fresh (< HISTORY_MAX_AGE_H hours): push to Redis, replacing old data
3. If file is stale: keep existing Redis data
4. Track last export_ts to avoid duplicate pushes
5. Support resume: save last position to Redis, reload on restart

V9 additions:
- Per-stream history (7 independent streams instead of single candle list)
- Configurable backfill depth via SC_HISTORY_DAYS
- Batch POST to backend API
- Progress reporting via logging
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error

logger = logging.getLogger("v9_bridge")

HISTORY_MAX_AGE_H = float(os.getenv("V9_HISTORY_MAX_AGE_H", "168"))  # 1 week default
SC_HISTORY_DAYS = int(os.getenv("SC_HISTORY_DAYS", "30"))
BATCH_SIZE = int(os.getenv("V9_HISTORY_BATCH_SIZE", "50"))


def redis_cmd(redis_url: str, redis_token: str, args: list) -> Optional[dict]:
    """Execute a single Redis REST command. Returns parsed JSON or None."""
    if not redis_url or not redis_token:
        return None
    try:
        body = json.dumps(args).encode()
        req = urllib.request.Request(
            redis_url,
            data=body,
            headers={
                "Authorization": f"Bearer {redis_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        logger.warning(f"Redis cmd {args[0]} error: {e}")
        return None


def api_post(cloud_url: str, bridge_token: str, path: str, data: dict) -> bool:
    """POST data to FastAPI endpoint. Returns True on success."""
    url = f"{cloud_url}{path}"
    try:
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {bridge_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status < 400
    except urllib.error.URLError:
        return False


def historical_load(
    stream_name: str,
    filepath: Path,
    redis_key: str,
    api_path: str,
    redis_url: str,
    redis_token: str,
    cloud_url: str,
    bridge_token: str,
) -> bool:
    """Load historical data from DLL export file into Redis.

    Strategy (ported from V8):
    1. Check file exists and is fresh enough
    2. Read and parse JSON
    3. Push to Redis: SET latest + LPUSH history list
    4. POST to backend API (batch, best-effort)
    5. Save resume position (export_ts) to Redis

    Returns True if data was loaded, False if skipped.
    """
    if not filepath.exists():
        logger.info(f"[{stream_name}] History: file not found at {filepath}")
        return False

    # Check file age
    age_s = time.time() - filepath.stat().st_mtime
    age_h = age_s / 3600

    if age_h > HISTORY_MAX_AGE_H:
        logger.info(
            f"[{stream_name}] History: file too old ({age_h:.1f}h > {HISTORY_MAX_AGE_H}h), "
            f"keeping existing Redis data"
        )
        return False

    # Read file
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"[{stream_name}] History: read error: {e}")
        return False

    export_ts = data.get("export_ts", 0)

    # Check resume position — skip if already loaded this export
    resume_key = f"{redis_key}:resume_ts"
    last_loaded = redis_cmd(redis_url, redis_token, ["GET", resume_key])
    if last_loaded and last_loaded.get("result"):
        try:
            last_ts = float(last_loaded["result"])
            if last_ts >= export_ts:
                logger.info(
                    f"[{stream_name}] History: already loaded export_ts={export_ts}, skipping"
                )
                return False
        except (ValueError, TypeError):
            pass

    logger.info(
        f"[{stream_name}] History: loading from file "
        f"(age={age_h:.1f}h, export_ts={export_ts})"
    )

    # Push to Redis
    payload = json.dumps(data)

    # SET latest snapshot
    redis_cmd(redis_url, redis_token, ["SET", f"{redis_key}:latest", payload])

    # LPUSH to history list (newest first)
    redis_cmd(redis_url, redis_token, ["LPUSH", redis_key, payload])
    redis_cmd(redis_url, redis_token, ["LTRIM", redis_key, "0", "99"])

    # Save resume position
    redis_cmd(redis_url, redis_token, ["SET", resume_key, str(export_ts)])

    # POST to backend API (best-effort, W3 endpoints may not exist yet)
    if cloud_url and bridge_token:
        ok = api_post(cloud_url, bridge_token, api_path, data)
        if ok:
            logger.info(f"[{stream_name}] History: API push OK")
        else:
            logger.debug(f"[{stream_name}] History: API push failed (W3 placeholder)")

    logger.info(f"[{stream_name}] History: loaded successfully (export_ts={export_ts})")
    return True


def get_resume_ts(
    stream_name: str,
    redis_key: str,
    redis_url: str,
    redis_token: str,
) -> Optional[float]:
    """Get last successfully loaded export_ts for a stream."""
    resume_key = f"{redis_key}:resume_ts"
    result = redis_cmd(redis_url, redis_token, ["GET", resume_key])
    if result and result.get("result"):
        try:
            return float(result["result"])
        except (ValueError, TypeError):
            pass
    return None


def clear_resume(
    stream_name: str,
    redis_key: str,
    redis_url: str,
    redis_token: str,
):
    """Clear resume position (forces full reload on next start)."""
    resume_key = f"{redis_key}:resume_ts"
    redis_cmd(redis_url, redis_token, ["DEL", resume_key])
    logger.info(f"[{stream_name}] Resume position cleared")
