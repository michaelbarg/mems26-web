"""Root-logging configuration for the MEMS26 backend — the INFO layer (T-61).

WHY THIS FILE EXISTS (Michael 2026-08-20, fix F3)
--------------------------------------------------
Nothing in the served app ever configured the **root** logger.

* `uvicorn.config.LOGGING_CONFIG` (verified on the installed uvicorn 0.39.0)
  configures exactly three loggers — `uvicorn`, `uvicorn.error`, `uvicorn.access` —
  and **never gives root a handler**.  It is applied in `Config.__init__` (line 99,
  `self.configure_logging()`), i.e. *before* `Config.load()` imports
  `backend.main`.
* The only `logging.basicConfig()` reachable from the served app lives in
  `backend/v9/audit/runner.py:14` — and that module is imported **lazily**, inside
  `_check_audit()` at `backend/v9/api/v9/status.py:172`.  So the app's whole logging
  configuration was an accidental side effect of somebody opening the dashboard.

Until that lazy import happened, every `backend.*` / `mems26*` record propagated to
a handler-less root and fell through to `logging.lastResort`
(`<_StderrHandler <stderr> (WARNING)>`, `formatter=None`) — **WARNING and above only,
printed bare with no timestamp, no level, no logger name.**

That is precisely the 2026-08-19 signature: after the 16:09 restart nobody opened the
dashboard, so the entire session ran on `lastResort`.  `[ExitVerify]`,
`OPENING_DIR_FUSION` and `SHADOW trade TM` are all INFO, so 22 shadow trades sat in
the books with **zero** matching log lines — the "0 lines" readings that day were
blindness, not findings.  Measured live on 2026-08-20: the backend booted 11:52:33
and the first timestamped line appeared only at 14:29:47, the moment the frontend
opened WebSockets and hit the status route.

WHAT THIS FILE GUARANTEES
-------------------------
1. Root is configured at **import time of `backend.main`** — before any `backend.v9`
   module is imported, so import-time records are captured too.  Robust to import
   order and to whoever wins the race with uvicorn's `dictConfig` (that config never
   touches root, and ours is idempotent + re-asserted at startup).
2. INFO reaches stderr — which the LaunchAgent redirects to `/tmp/backend.err.log` —
   with `timestamp [LEVEL] [logger.name] message`.
3. uvicorn's own loggers are untouched: `uvicorn` and `uvicorn.access` carry
   `propagate: False`, and `uvicorn.error` stops at its `uvicorn` parent, so nothing
   double-prints.
4. A permanent boot probe (`[boot] logging OK …`) that `scripts/fire_drill.py`
   asserts for the *currently running* PID, so this blindness can never return
   unnoticed.
5. An explicit, documented noise cap (see `_NOISE_RULES`) so the restored INFO layer
   cannot flood the way the 13k NAKED_STOP_SUSPECT bug did on 2026-08-19.

No trading behavior is touched by anything in this module.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from typing import Dict, List, Optional, Tuple

# ── Defaults (env-overridable, ops-only — none of these is a trading flag) ────

DEFAULT_LEVEL = "INFO"
DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"

#: Grep anchor for the boot probe. `scripts/fire_drill.py` imports THIS constant —
#: one source of truth, so the check can never drift from the emitter.
BOOT_PROBE_PREFIX = "[boot] logging OK"

#: Default application log file (LaunchAgent `StandardErrorPath`). NOT `/tmp/backend.log`
#: — that one is uvicorn's access log (COWORK_DAILY_READ §3.1).
DEFAULT_LOG_FILE = "/tmp/backend.err.log"

_HANDLER_TAG = "_mems26_root_handler"
_ANNOTATED_TAG = "_mems26_noise_annotated"


# ── Noise cap ────────────────────────────────────────────────────────────────
#
# Measured on the live process on 2026-08-20 over the 22 minutes in which the INFO
# layer happened to be alive (14:29:47 → 14:52): 2,492 INFO records, of which 2,330
# (93.5%) came from the four signatures below.  Left alone that is ~113 lines/min ≈
# 163k lines/day of pure telemetry burying every real line.
#
# Each rule is (logger-name prefix, message substring, level it applies to, min seconds
# between emissions).  ONLY these four are throttled; everything else passes untouched.
# Nothing is silently dropped: the next line that does get through carries a
# `[+N identical suppressed …]` suffix, so the count is always visible.
#
#  1. EventDispatcher routing  — 1,465/22min.  Says "a bar was handed to a subscribed
#     system"; carries no decision, no outcome.  976 of them route to system 3
#     (footprint), which is disabled by env (`FOOTPRINT_DISABLED=true`).
#  2. [TPO] VA from Sierra     —   488/22min.  All three values byte-identical every
#     time (POC=7738.25 VAH=7747.00 VAL=7726.75) — re-logged per push, not per change.
#  3. BarRouter: dispatch      —   377/22min.  Per-dispatch latency telemetry.  INFO
#     only: the ">50ms" WARNING variant is a DIFFERENT level and is NOT throttled,
#     so slow-dispatch alarms stay fully intact.
#  4. [System0] SHADOW DIR     —   147/22min.  Identical payload each time; the reading
#     it reports only changes on a new bar (5 min), so 1/min loses nothing.
#
# Projection after the cap: ~250 INFO/22min (≈11/min) — a 90% cut with zero loss of
# signal.  Set MEMS26_LOG_NOISE_CAP=0 to disable the cap entirely.
_NOISE_RULES: Tuple[Tuple[str, str, int, float], ...] = (
    ("backend.v9.services.event_dispatcher.dispatcher",
     "[EventDispatcher] routing ", logging.INFO, 60.0),
    ("backend.v9.systems.tpo.tpo_system",
     "[TPO] VA from Sierra:", logging.INFO, 60.0),
    ("backend.v9.services.bar_router",
     "BarRouter: dispatch ", logging.INFO, 60.0),
    ("backend.v9.services.trade_manager.bar_level_detector",
     "[System0] SHADOW DIR:", logging.INFO, 60.0),
)


class NoiseRateLimiter(logging.Filter):
    """Rate-limit an explicit allow-list of pure-telemetry log signatures.

    Deliberately NOT a generic dedup filter: a generic one would eventually swallow a
    real trading line.  Only signatures listed in `_NOISE_RULES` are ever throttled,
    and the suppressed count is reported on the next line that passes.
    """

    def __init__(self, rules=_NOISE_RULES):
        super().__init__()
        self._rules = tuple(rules)
        self._state: Dict[int, List[float]] = {}
        self._lock = threading.Lock()

    def _match(self, record: logging.LogRecord) -> Optional[Tuple[int, float]]:
        # `record.msg` is the %-style template for lazy logging and the already-
        # formatted string for f-string logging — matching on it covers both.
        msg = record.msg if isinstance(record.msg, str) else str(record.msg)
        for idx, (name, needle, level, interval) in enumerate(self._rules):
            if record.levelno == level and needle in msg and record.name.startswith(name):
                return idx, interval
        return None

    def filter(self, record: logging.LogRecord) -> bool:
        hit = self._match(record)
        if hit is None:
            return True
        idx, interval = hit
        now = time.monotonic()
        with self._lock:
            state = self._state.setdefault(idx, [0.0, 0.0])
            last, dropped = state
            if last and (now - last) < interval:
                state[1] = dropped + 1
                return False
            state[0] = now
            state[1] = 0.0
        if dropped and not getattr(record, _ANNOTATED_TAG, False):
            record.msg = "%s  [+%d identical suppressed in the last %.0fs — T-61 noise cap]" % (
                record.getMessage(), int(dropped), interval,
            )
            record.args = ()
            setattr(record, _ANNOTATED_TAG, True)
        return True


# ── Configuration ────────────────────────────────────────────────────────────

_configured = False
_lock = threading.Lock()


def _env_level() -> int:
    """MEMS26_LOG_LEVEL → logging level int. Unknown/garbage falls back to INFO
    (never to a *higher* level — a typo must not re-create the blindness)."""
    raw = (os.getenv("MEMS26_LOG_LEVEL") or DEFAULT_LEVEL).strip().upper()
    value = getattr(logging, raw, None)
    return value if isinstance(value, int) else logging.INFO


def _root_handler() -> Optional[logging.Handler]:
    for h in logging.getLogger().handlers:
        if getattr(h, _HANDLER_TAG, False):
            return h
    return None


def configure_logging(force: bool = False, stream=None) -> logging.Logger:
    """Install the MEMS26 root handler. Idempotent; safe to call from anywhere.

    Returns the root logger.  Called at import time of `backend.main` *and* again from
    the FastAPI startup event — the second call is a cheap no-op re-assertion that
    survives any third party that re-runs `dictConfig` between the two.
    """
    global _configured
    with _lock:
        root = logging.getLogger()
        level = _env_level()

        existing = _root_handler()
        if existing is not None and not force:
            # Re-assert level only — a `dictConfig` run between our two calls can
            # reset root.level while leaving handlers in place.
            root.setLevel(level)
            existing.setLevel(level)
            _configured = True
            return root

        if existing is not None:
            root.removeHandler(existing)

        handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(
            os.getenv("MEMS26_LOG_FORMAT") or DEFAULT_FORMAT,
            datefmt=os.getenv("MEMS26_LOG_DATEFMT") or DEFAULT_DATEFMT,
        ))
        if (os.getenv("MEMS26_LOG_NOISE_CAP", "1") or "1").strip().lower() not in ("0", "false", "no"):
            handler.addFilter(NoiseRateLimiter())
        setattr(handler, _HANDLER_TAG, True)

        root.addHandler(handler)
        root.setLevel(level)
        _configured = True
        return root


def is_configured() -> bool:
    return _configured and _root_handler() is not None


# ── Boot probe ───────────────────────────────────────────────────────────────

_commit_cache: Optional[str] = None


def _git_commit(repo_root: Optional[str] = None) -> str:
    """Short HEAD sha read straight off `.git` — no subprocess, cannot hang or fail."""
    global _commit_cache
    if _commit_cache is not None:
        return _commit_cache
    root = repo_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sha = "unknown"
    try:
        with open(os.path.join(root, ".git", "HEAD"), "r") as fh:
            head = fh.read().strip()
        if head.startswith("ref:"):
            ref = head.split(" ", 1)[1].strip()
            try:
                with open(os.path.join(root, ".git", ref), "r") as fh:
                    sha = fh.read().strip()
            except OSError:
                with open(os.path.join(root, ".git", "packed-refs"), "r") as fh:
                    for line in fh:
                        if line.rstrip().endswith(" " + ref):
                            sha = line.split(" ", 1)[0]
                            break
        else:
            sha = head
    except OSError:
        pass
    _commit_cache = sha[:8] if sha and sha != "unknown" else "unknown"
    return _commit_cache


def boot_probe(logger: Optional[logging.Logger] = None) -> str:
    """Emit the single permanent INFO line that proves the INFO layer is alive.

    `scripts/fire_drill.py` fails NO-GO when this line is missing from the log for the
    PID that is actually running — the guard that makes T-61 blindness impossible to
    miss again.
    """
    log = logger or logging.getLogger("mems26.boot")
    level_name = logging.getLevelName(_env_level())
    msg = "%s level=%s pid=%d commit=%s stream=stderr" % (
        BOOT_PROBE_PREFIX, level_name, os.getpid(), _git_commit(),
    )
    log.info(msg)
    return msg


# ── Verification helper (used by scripts/fire_drill.py) ──────────────────────

def find_boot_probe(path: str = DEFAULT_LOG_FILE, pid: Optional[int] = None,
                    max_bytes: int = 64 * 1024 * 1024) -> dict:
    """Scan a log file BACKWARDS for the newest boot probe.

    Backwards because the app log is tens of MB of history and the probe we care about
    is the most recent one.  Returns a dict — never raises — with:
        found        bool   a probe line was located at all
        pid_match    bool   that probe belongs to `pid`
        pid          int    pid parsed off the probe line
        line         str    the raw probe line
        info_after   int    timestamped [INFO] lines seen after the probe (proves the
                            level is genuinely INFO in the running process, not just
                            that one line got through)
        reason       str    why it failed, when it did
    """
    out = {"found": False, "pid_match": False, "pid": None, "line": "",
           "info_after": 0, "reason": ""}
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        out["reason"] = f"cannot stat {path}: {exc}"
        return out

    block = 1 << 20
    tail = b""
    read = 0
    try:
        with open(path, "rb") as fh:
            pos = size
            while pos > 0 and read < max_bytes:
                step = min(block, pos)
                pos -= step
                fh.seek(pos)
                tail = fh.read(step) + tail
                read += step
                if BOOT_PROBE_PREFIX.encode() in tail:
                    break
    except OSError as exc:
        out["reason"] = f"cannot read {path}: {exc}"
        return out

    text = tail.decode("utf-8", "replace")
    idx = text.rfind(BOOT_PROBE_PREFIX)
    if idx < 0:
        out["reason"] = (
            f"no '{BOOT_PROBE_PREFIX}' line in the last {read // (1 << 20)}MB of {path} — "
            "the backend booted without a configured INFO layer (T-61 blindness)")
        return out

    line_start = text.rfind("\n", 0, idx) + 1
    line_end = text.find("\n", idx)
    line = text[line_start:line_end if line_end > 0 else len(text)].strip()
    out["found"] = True
    out["line"] = line

    for token in line.split():
        if token.startswith("pid="):
            try:
                out["pid"] = int(token[4:])
            except ValueError:
                pass
    after = text[line_end if line_end > 0 else len(text):]
    out["info_after"] = after.count("[INFO]")

    if pid is None:
        out["pid_match"] = True
    else:
        out["pid_match"] = (out["pid"] == pid)
        if not out["pid_match"]:
            out["reason"] = (
                f"newest boot probe is pid={out['pid']} but the running backend is "
                f"pid={pid} — that process booted with NO INFO layer (T-61)")
    return out
