"""P30 G6 / P31 Phase 1 — End-of-day archiver for MEMS26 Sierra exports.

Doc 06 §3 (Michael 2026-05-19): "No historical continuity — yesterday's
data is gone, can't replay yesterday in the cockpit."

Sierra DLL writes live JSONs to `~/SierraChart_Data/v9_export/`. At 16:00 ET
(RTH close) the next day's session starts overwriting them. This service
copies the closing snapshots to `~/SierraChart_Data/v9_archive/<YYYY-MM-DD>/`
so the cockpit's "Hist" tab can replay yesterday.

Design choices:
  * Filesystem archive (not DB schema) — exactly what Sierra wrote, no lossy
    transformation. Fast snapshots, no migrations.
  * One sub-directory per trading day (ET). Each file keeps its original name.
  * Idempotent — re-running on the same date overwrites the archive folder
    safely. So Michael can hit `archive_now` repeatedly while debugging.
  * P31 Phase 1 (Michael 2026-05-22): the archiver now auto-fires once per
    trading day at 15:55 ET via `EODArchiveScheduler` (see
    `eod_archive_scheduler.py`). Manual `POST /api/v9/history/archive_now`
    still works for ad-hoc capture and is the primary path during dev.
  * 90-day retention (Michael 2026-05-22 — selected `90_days` in the
    `CC_UNIFIED_HISTORY_ARCHITECTURE_SPEC` review): old archive folders
    are pruned by `prune_old_archives()` after each successful new archive.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

EXPORT_DIR = Path(
    os.getenv("V9_EXPORT_DIR", "/Users/michael/SierraChart_Data/v9_export")
)
ARCHIVE_DIR = Path(
    os.getenv("V9_ARCHIVE_DIR", "/Users/michael/SierraChart_Data/v9_archive")
)

# Files archived per session. Add/remove here as DLL exports evolve —
# the contract is "every file the cockpit's Hist tab might need".
#
# P31 Phase 1 (Michael 2026-05-22): added the 4 missing exports flagged by
# `CC_UNIFIED_HISTORY_ARCHITECTURE_SPEC.md` so the archive captures every
# live JSON file (live_price for tick-by-tick replay, tick_reversal_* for
# S3 footprint backtests, reversal_cluster for setup forensics).
ARCHIVED_FILES = (
    "5min.json",
    "cumulative_delta.json",
    "tpo.json",
    "woodies_5min.json",
    "woodies_30min.json",
    "volume_profile.json",
    "footprint.json",
    "imbalance_flags.json",
    "stacked_imbalances.json",
    "mes_ai_data.json",
    # P31 Phase 1 additions (2026-05-22) — full Sierra export coverage:
    "live_price.json",
    "tick_reversal_12.json",
    "tick_reversal_15.json",
    "reversal_cluster.json",
)

# Retention policy — Michael picked 90 days in the unified-history review.
# Disk cost ~200 KB/day × 90 = ~18 MB. Override with V9_ARCHIVE_RETENTION_DAYS.
ARCHIVE_RETENTION_DAYS = int(os.getenv("V9_ARCHIVE_RETENTION_DAYS", "90"))


def _et_today_date_str() -> str:
    return datetime.now(tz=ZoneInfo("America/New_York")).strftime("%Y-%m-%d")


def archive_today(target_date: Optional[str] = None) -> Dict[str, Any]:
    """Copy current Sierra exports into the archive folder for `target_date`.

    Args:
        target_date: YYYY-MM-DD (ET). Defaults to today's ET date.

    Returns:
        Dict with `date`, `archived` (list of filenames written), and
        `skipped` (list of filenames absent in the live export).
    """
    date_str = target_date or _et_today_date_str()
    dest = ARCHIVE_DIR / date_str
    dest.mkdir(parents=True, exist_ok=True)

    archived: List[str] = []
    skipped: List[str] = []
    for fname in ARCHIVED_FILES:
        src = EXPORT_DIR / fname
        if not src.exists():
            skipped.append(fname)
            continue
        try:
            shutil.copy2(src, dest / fname)
            archived.append(fname)
        except Exception as e:
            logger.warning("[eod_archiver] copy %s -> %s failed: %s", src, dest, e)
            skipped.append(fname)
    # A7: archive gateway_decisions.jsonl alongside the Sierra exports
    # (backup for the in-process rotation that missed 08-21 because the
    # backend was restarted after midnight UTC → mday >= today → no rotation)
    _DECISIONS_LIVE = EXPORT_DIR / "gateway_decisions.jsonl"
    if _DECISIONS_LIVE.exists():
        try:
            shutil.copy2(_DECISIONS_LIVE, dest / f"gateway_decisions.{date_str}.jsonl")
            archived.append(f"gateway_decisions.{date_str}.jsonl")
        except Exception as e:
            logger.warning("[eod_archiver] decisions copy failed: %s", e)

    # A7: archive backend.err.log before it gets overwritten by next restart
    _BACKEND_ERR_LOG = Path(os.getenv("BACKEND_ERR_LOG", "/tmp/backend.err.log"))
    if _BACKEND_ERR_LOG.exists():
        try:
            shutil.copy2(_BACKEND_ERR_LOG, dest / f"backend.err.{date_str}.log")
            archived.append(f"backend.err.{date_str}.log")
        except Exception as e:
            logger.warning("[eod_archiver] backend.err.log copy failed: %s", e)

    logger.info(
        "[eod_archiver] %s — archived=%d skipped=%d at %s",
        date_str, len(archived), len(skipped), dest,
    )
    return {"date": date_str, "archive_dir": str(dest), "archived": archived, "skipped": skipped}


def list_archived_dates() -> List[str]:
    """Return sorted (newest first) list of dates present in the archive."""
    if not ARCHIVE_DIR.exists():
        return []
    return sorted(
        (p.name for p in ARCHIVE_DIR.iterdir() if p.is_dir() and len(p.name) == 10),
        reverse=True,
    )


def read_archive(date_str: str, filename: str) -> Optional[Dict[str, Any]]:
    """Read a single archived JSON file. Returns None if missing or unparsable."""
    f = ARCHIVE_DIR / date_str / filename
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("[eod_archiver] read %s failed: %s", f, e)
        return None


def read_session(date_str: str) -> Dict[str, Any]:
    """Bundle the most-used exports for a session into a single payload.

    Cockpit's "Hist" tab loads this in one round-trip.
    """
    out: Dict[str, Any] = {"date": date_str, "archive_dir": str(ARCHIVE_DIR / date_str)}
    available: List[str] = []
    for fname in ARCHIVED_FILES:
        data = read_archive(date_str, fname)
        if data is not None:
            key = fname[:-5] if fname.endswith(".json") else fname  # strip .json
            out[key] = data
            available.append(fname)
    out["available_files"] = available
    return out


def prune_old_archives(retention_days: int = ARCHIVE_RETENTION_DAYS) -> Dict[str, Any]:
    """Delete archive folders older than ``retention_days`` (default 90).

    Safe to call after every successful archive. Folders are matched by
    name pattern ``YYYY-MM-DD``; anything that doesn't parse as a date is
    skipped (defensive against operator-created sub-folders). Returns a
    dict describing what was kept and what was deleted so the scheduler
    can log a one-liner per run.
    """
    if not ARCHIVE_DIR.exists():
        return {"retention_days": retention_days, "deleted": [], "kept": [], "skipped": []}

    cutoff = datetime.now(tz=ZoneInfo("America/New_York")).date() - timedelta(days=retention_days)
    deleted: List[str] = []
    kept: List[str] = []
    skipped: List[str] = []
    for child in ARCHIVE_DIR.iterdir():
        if not child.is_dir():
            continue
        try:
            d = datetime.strptime(child.name, "%Y-%m-%d").date()
        except ValueError:
            skipped.append(child.name)
            continue
        if d < cutoff:
            try:
                shutil.rmtree(child)
                deleted.append(child.name)
            except OSError as e:
                logger.warning("[eod_archiver] prune failed for %s: %s", child, e)
                skipped.append(child.name)
        else:
            kept.append(child.name)
    if deleted:
        logger.info(
            "[eod_archiver] prune retention=%dd kept=%d deleted=%d (oldest_kept=%s)",
            retention_days,
            len(kept),
            len(deleted),
            min(kept) if kept else None,
        )
    return {
        "retention_days": retention_days,
        "deleted": sorted(deleted),
        "kept": sorted(kept),
        "skipped": sorted(skipped),
    }
