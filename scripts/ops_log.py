#!/usr/bin/env python3
"""Central ops log (N12 — Michael 2026-07-16: "קובץ לוג שמקבל את הכל").

ONE append-only daily log that every watcher / scheduler / agent writes to, so
there is a single chronological place to see what happened across the whole
stack. Replaces the scattered per-script logs Michael was chasing.

CLI:
    python3 scripts/ops_log.py -s feed_watchdog -l WARN "HALT: bars frozen 12m"
    python3 scripts/ops_log.py session-watch INFO "run 18 complete"   # positional
    python3 scripts/ops_log.py --tail 20                              # read back

Import:
    from scripts.ops_log import log_event
    log_event("bar_gap_monitor", "INFO", "opening bars complete 29/29")

File:  docs/reports/OPS_LOG_<YYYY-MM-DD>.md   (day = America/New_York trading day)
Line:  [2026-07-16T23:59:01-04:00] [feed_watchdog] [WARN] HALT: bars frozen 12m

Append is atomic under an fcntl file lock so concurrent writers never interleave.
log_event() NEVER raises to the caller — logging must not break the thing logged.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    _ET = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover
    _ET = None

_REPO = Path(__file__).resolve().parent.parent
_LOG_DIR = _REPO / "docs" / "reports"
VALID_LEVELS = ("DEBUG", "INFO", "WARN", "ERROR", "CRITICAL")


def _now():
    return _dt.datetime.now(_ET) if _ET else _dt.datetime.now()


def log_path(day: str | None = None) -> Path:
    d = day or _now().date().isoformat()
    return _LOG_DIR / f"OPS_LOG_{d}.md"


def log_event(source: str, level: str, message: str) -> bool:
    """Append one line to today's central ops log. True on success, never raises."""
    try:
        ts = _now().isoformat(timespec="seconds")
        source = (source or "unknown").strip().replace("]", ")").replace("[", "(")
        level = (level or "INFO").strip().upper()
        if level not in VALID_LEVELS:
            level = "INFO"
        message = (message or "").replace("\n", " ").replace("\r", " ").strip()
        line = f"[{ts}] [{source}] [{level}] {message}\n"

        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not path.exists()
        with open(path, "a", encoding="utf-8") as f:
            try:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            except Exception:
                pass
            if is_new:
                f.write(f"# OPS LOG — {_now().date().isoformat()}\n\n")
                f.write("לוג-תפעול מרכזי (N12): כל הוואצ'רים/המתזמנים/הסוכנים כותבים לכאן. "
                        "append-only, מסודר כרונולוגית.\n\n")
            f.write(line)
            f.flush()
            try:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
        return True
    except Exception as e:  # last resort — never break the caller
        try:
            sys.stderr.write(f"[ops_log] write failed: {e}\n")
        except Exception:
            pass
        return False


def _tail(n: int) -> int:
    path = log_path()
    if not path.exists():
        print(f"(no ops log yet at {path})")
        return 0
    lines = path.read_text(encoding="utf-8").splitlines()
    print("\n".join(lines[-n:]))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Append a line to the central daily ops log.")
    p.add_argument("--source", "-s")
    p.add_argument("--level", "-l", default="INFO")
    p.add_argument("--tail", type=int, metavar="N", help="print last N lines and exit")
    p.add_argument("rest", nargs="*", help="[source] [level] message  (positional fallback)")
    a = p.parse_args(argv)

    if a.tail:
        return _tail(a.tail)

    source, level = a.source, a.level
    rest = list(a.rest)
    if source is None and rest:            # positional: source first
        source = rest.pop(0)
    if a.level == "INFO" and rest and rest[0].upper() in VALID_LEVELS:
        level = rest.pop(0)                # positional: optional level second
    message = " ".join(rest)
    if not message:
        p.error("no message given")

    ok = log_event(source, level, message)
    if ok:
        print(f"ops_log <- [{source}] [{level.upper()}] {message}   ({log_path().name})")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
