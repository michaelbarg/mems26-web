#!/usr/bin/env python3
"""
v9_export_promoter.py — native-macOS `.tmp`→`.json` promoter.
Workaround for the Wine rename-replace failure that freezes the Sierra bar feed.

ROOT CAUSE (2026-06-25, verified Rule 2/5)
------------------------------------------
Sierra Chart runs under CrossOver/Wine on this Mac. The DLL's atomic write helper
(`sc_study/v9_types.h::v9_write_json`) does:

    write  <name>.json.tmp        (ofstream — works under Wine)
    std::rename(tmp, <name>.json) (REPLACE existing — FAILS under Wine)

Wine's rename() can CREATE a new file but cannot REPLACE an existing one. So the
very first write of `<name>.json` succeeds, but every promotion afterwards fails:
the `<name>.json.tmp` working file stays fresh (Sierra keeps computing) while the
final `<name>.json` that the bridge → DB reads FREEZES. `live_price.json` /
`mes_ai_data.json` are written directly (no `.tmp`), so a live tick feed MASKS the
frozen bar feed — the silent-staleness class CLAUDE.md warns about.

WHAT THIS DOES
--------------
Runs natively on macOS (where rename-replace works) and promotes Sierra's own
validated `.tmp` content to the final `.json`, fully bypassing Wine. It NEVER
synthesizes or derives data (CLAUDE.md Rule 1 — honest source only): it only
promotes the exact bytes Sierra wrote, and only after the `.tmp` parses as
complete JSON (torn-read safe). The final write uses os.replace (atomic).

It only READS Sierra's `.tmp` (never deletes/moves it) — Sierra keeps owning the
`.tmp` lifecycle; this sidecar just publishes each fresh one to `.json`.

Permanent source-level fix is in the DLL (use Win32 MoveFileEx with
MOVEFILE_REPLACE_EXISTING instead of std::rename) — handed to CC. Until that ships
and is verified, this sidecar keeps the bar feed live 24/7.

Run via LaunchAgent `com.mems26.export_promoter` (RunAtLoad + KeepAlive) for
24/7 + reboot survival.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from pathlib import Path

EXPORT_DIR = Path(os.getenv(
    "MEMS26_SIGNALS_DIR",
    os.path.expanduser("~/SierraChart_Data/v9_export"),
))
INTERVAL = float(os.getenv("V9_PROMOTER_INTERVAL", "0.5"))   # seconds between sweeps
HEARTBEAT_SEC = float(os.getenv("V9_PROMOTER_HEARTBEAT", "300"))
LOG_PATH = os.getenv("V9_PROMOTER_LOG", "/tmp/v9_export_promoter.log")

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("v9_promoter")


def promote_once() -> int:
    """One sweep: promote every *.json.tmp that is newer than its final .json.
    Returns the number of files promoted this sweep."""
    promoted = 0
    try:
        tmps = list(EXPORT_DIR.glob("*.json.tmp"))
    except OSError as e:
        log.warning("glob failed: %s", e)
        return 0

    for tmp in tmps:
        final = tmp.with_suffix("")  # strip ".tmp" → "<name>.json"
        try:
            tmp_mtime = tmp.stat().st_mtime
        except OSError:
            continue
        try:
            final_mtime = final.stat().st_mtime
        except OSError:
            final_mtime = -1.0  # final missing → always promote

        # Only act when Sierra has rewritten the .tmp since the last promotion.
        if tmp_mtime <= final_mtime:
            continue

        try:
            content = tmp.read_text()
        except OSError:
            continue
        if not content.strip():
            continue

        # Torn-read guard: skip a .tmp caught mid-write (incomplete JSON).
        try:
            json.loads(content)
        except (json.JSONDecodeError, ValueError):
            continue

        # Atomic native publish: our own temp in the same dir → os.replace.
        mypath = None
        try:
            fd, mypath = tempfile.mkstemp(dir=str(EXPORT_DIR), prefix=".prom_")
            with os.fdopen(fd, "w") as f:
                f.write(content)
            os.replace(mypath, final)   # native atomic rename-replace (works on macOS)
            promoted += 1
        except OSError as e:
            log.warning("promote %s failed: %s", final.name, e)
            if mypath:
                try:
                    os.unlink(mypath)
                except OSError:
                    pass
    return promoted


def main() -> None:
    log.info("v9_export_promoter START dir=%s interval=%.2fs", EXPORT_DIR, INTERVAL)
    total = 0
    last_hb = 0.0
    # Clean any orphaned .prom_ temps from a prior crash.
    try:
        for orphan in EXPORT_DIR.glob(".prom_*"):
            try:
                orphan.unlink()
            except OSError:
                pass
    except OSError:
        pass

    while True:
        try:
            total += promote_once()
        except Exception as e:  # never let the loop die
            log.warning("loop error (continuing): %s", e)
        now = time.time()
        if now - last_hb >= HEARTBEAT_SEC:
            log.info("heartbeat: promoted_total=%d", total)
            last_hb = now
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
