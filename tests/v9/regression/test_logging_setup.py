"""T-61 regression — the INFO layer must reach the log, with a prefix, always.

The bug (2026-08-19, fix F3 2026-08-20): the served app never configured the ROOT
logger.  uvicorn's LOGGING_CONFIG only configures `uvicorn*`, and the app's single
`logging.basicConfig` lives behind a LAZY import in `status.py:172`, so until somebody
opened the dashboard every record fell through to `logging.lastResort`
(`_StderrHandler`, level WARNING, `formatter=None`) → WARNING+ only, printed bare.
22 shadow trades that day produced ZERO `SHADOW trade TM` lines; `[ExitVerify]` and
`OPENING_DIR_FUSION` (both INFO) were invisible.

These tests pin every property of the fix: level, prefix, idempotency, survival of a
competing dictConfig in EITHER order, the documented noise cap, the boot probe, and
the import-order wiring in backend/main.py.
"""

import ast
import io
import logging
import logging.config
import os
import time

import pytest

from backend.logging_setup import (
    BOOT_PROBE_PREFIX,
    DEFAULT_FORMAT,
    NoiseRateLimiter,
    boot_probe,
    configure_logging,
    find_boot_probe,
    is_configured,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

# uvicorn 0.39.0's real config, inlined so the test does not depend on the install.
UVICORN_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"default": {"format": "%(levelprefix)s %(message)s",
                               "class": "logging.Formatter"}},
    "handlers": {"default": {"formatter": "default", "class": "logging.StreamHandler"}},
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"level": "INFO"},
        "uvicorn.access": {"handlers": ["default"], "level": "INFO", "propagate": False},
    },
}


@pytest.fixture(autouse=True)
def _restore_root():
    """Every test here mutates the process-wide root logger — put it back."""
    root = logging.getLogger()
    handlers = list(root.handlers)
    level = root.level
    yield
    root.handlers[:] = handlers
    root.setLevel(level)


def _fresh_root_with_stream():
    """Configure onto a StringIO so we can read exactly what would hit stderr."""
    root = logging.getLogger()
    root.handlers[:] = []
    stream = io.StringIO()
    configure_logging(force=True, stream=stream)
    return stream


# ── 1. the bug itself: root must have a handler, so lastResort is never used ──

def test_root_has_handler_so_last_resort_is_never_used():
    root = logging.getLogger()
    root.handlers[:] = []
    # Precondition = the 2026-08-19 state: no root handler → lastResort would fire.
    assert not root.handlers
    assert logging.lastResort.level == logging.WARNING
    assert logging.lastResort.formatter is None

    configure_logging(force=True, stream=io.StringIO())
    assert root.handlers, "root still has no handler — lastResort would swallow INFO"
    assert is_configured()


def test_info_reaches_the_log_with_timestamp_level_and_logger_name():
    stream = _fresh_root_with_stream()
    logging.getLogger("backend.v9.services.exit_verify").info("[ExitVerify] PENDING → CONFIRMED")
    out = stream.getvalue().strip()

    assert "[ExitVerify] PENDING → CONFIRMED" in out, "INFO never reached the log (T-61)"
    assert "[INFO]" in out, "level missing from the prefix"
    assert "[backend.v9.services.exit_verify]" in out, "logger name missing from the prefix"
    # timestamp: the line must START with `YYYY-MM-DD HH:MM:SS` — COWORK_DAILY_READ §2ד
    # greps the log with `grep "^$DAY"`, which is exactly what lastResort broke.
    assert out[:4].isdigit() and out[4] == "-" and out[10] == " " and out[13] == ":", out[:30]


def test_root_level_is_info_not_warning():
    configure_logging(force=True, stream=io.StringIO())
    assert logging.getLogger().level == logging.INFO


def test_format_default_carries_all_three_fields():
    for token in ("%(asctime)s", "%(levelname)s", "%(name)s", "%(message)s"):
        assert token in DEFAULT_FORMAT


# ── 2. robustness to import order ────────────────────────────────────────────

def test_idempotent_no_duplicate_handlers_or_duplicate_lines():
    stream = _fresh_root_with_stream()
    before = len(logging.getLogger().handlers)
    configure_logging()
    configure_logging()
    assert len(logging.getLogger().handlers) == before

    logging.getLogger("mems26.test").info("once")
    assert stream.getvalue().count("once") == 1


def test_survives_uvicorn_dictconfig_running_after_us():
    """uvicorn Config.__init__ runs dictConfig BEFORE importing the app — but a
    --reload worker or any third party can re-run it after. Root must survive."""
    stream = _fresh_root_with_stream()
    logging.config.dictConfig(UVICORN_LOGGING_CONFIG)
    configure_logging()  # the startup-event re-assertion
    logging.getLogger("backend.v9.gateway.trading_gateway").info("OPENING_DIR_FUSION=None")
    assert "OPENING_DIR_FUSION=None" in stream.getvalue()
    assert logging.getLogger().level == logging.INFO


def test_works_when_dictconfig_ran_first_the_real_boot_order():
    root = logging.getLogger()
    root.handlers[:] = []
    logging.config.dictConfig(UVICORN_LOGGING_CONFIG)   # uvicorn Config.__init__
    stream = io.StringIO()
    configure_logging(force=True, stream=stream)        # import of backend.main
    logging.getLogger("mems26").info("SHADOW trade TM id=999")
    assert "SHADOW trade TM id=999" in stream.getvalue()


def test_uvicorn_loggers_stay_sane_and_do_not_double_print():
    """`uvicorn` / `uvicorn.access` carry propagate=False, and `uvicorn.error` stops at
    its `uvicorn` parent — so uvicorn records must NOT also land on our root handler."""
    stream = _fresh_root_with_stream()
    logging.config.dictConfig(UVICORN_LOGGING_CONFIG)
    configure_logging()
    logging.getLogger("uvicorn.error").info("Application startup complete.")
    logging.getLogger("uvicorn.access").info("GET /api/v9/health 200")
    assert "Application startup complete." not in stream.getvalue()
    assert "GET /api/v9/health 200" not in stream.getvalue()


def test_bad_log_level_falls_back_to_info_never_higher(monkeypatch):
    monkeypatch.setenv("MEMS26_LOG_LEVEL", "NOT_A_LEVEL")
    stream = io.StringIO()
    logging.getLogger().handlers[:] = []
    configure_logging(force=True, stream=stream)
    assert logging.getLogger().level == logging.INFO
    logging.getLogger("mems26").info("still visible")
    assert "still visible" in stream.getvalue()


# ── 3. the noise cap (volume control) ────────────────────────────────────────

def test_noise_cap_throttles_a_listed_signature_and_reports_the_count():
    stream = _fresh_root_with_stream()
    log = logging.getLogger("backend.v9.services.event_dispatcher.dispatcher")
    for _ in range(50):
        log.info("[EventDispatcher] routing %s to system %d (%s)", "tick_reversal_15", 3, "footprint")
    out = stream.getvalue()
    assert out.count("[EventDispatcher] routing") == 1, "noise cap did not throttle"

    # …and the suppressed count becomes visible on the next line that passes.
    flt = [f for f in logging.getLogger().handlers[0].filters
           if isinstance(f, NoiseRateLimiter)][0]
    flt._state[0][0] = time.monotonic() - 999  # pretend the interval elapsed
    log.info("[EventDispatcher] routing %s to system %d (%s)", "tick_reversal_15", 3, "footprint")
    assert "identical suppressed" in stream.getvalue()


def test_noise_cap_does_not_touch_the_warning_variant():
    """`BarRouter: dispatch ` exists at INFO (throttled) and at WARNING (>50ms alarm).
    The slow-dispatch alarm must keep every single line."""
    stream = _fresh_root_with_stream()
    log = logging.getLogger("backend.v9.services.bar_router")
    for i in range(10):
        log.warning("BarRouter: dispatch total %.1fms for 5min", 90 + i)
    assert stream.getvalue().count("BarRouter: dispatch total") == 10


def test_noise_cap_never_touches_trading_lines():
    stream = _fresh_root_with_stream()
    log = logging.getLogger("backend.v9.gateway.trading_gateway")
    for i in range(20):
        log.info("LIVE trade TM id=%d", i)
    for i in range(20):
        log.info("[ExitVerify] PENDING id=%d", i)
    out = stream.getvalue()
    assert out.count("LIVE trade TM id=") == 20
    assert out.count("[ExitVerify] PENDING id=") == 20


def test_noise_cap_can_be_disabled(monkeypatch):
    monkeypatch.setenv("MEMS26_LOG_NOISE_CAP", "0")
    logging.getLogger().handlers[:] = []
    stream = io.StringIO()
    configure_logging(force=True, stream=stream)
    assert not [f for f in logging.getLogger().handlers[0].filters
                if isinstance(f, NoiseRateLimiter)]


# ── 4. boot probe + the fire_drill guard ─────────────────────────────────────

def test_boot_probe_emits_one_info_line_with_pid_and_commit():
    stream = _fresh_root_with_stream()
    msg = boot_probe()
    out = stream.getvalue()
    assert BOOT_PROBE_PREFIX in out
    assert f"pid={os.getpid()}" in out
    assert "level=INFO" in out
    assert "commit=" in msg
    assert out.count(BOOT_PROBE_PREFIX) == 1


def test_find_boot_probe_matches_the_running_pid(tmp_path):
    log = tmp_path / "backend.err.log"
    log.write_text(
        "old junk with no prefix\n"
        f"2026-08-20 14:00:00 [INFO] [mems26.boot] {BOOT_PROBE_PREFIX} level=INFO pid=111 commit=abc\n"
        "2026-08-20 14:00:01 [INFO] [mems26] something\n"
        f"2026-08-20 15:00:00 [INFO] [mems26.boot] {BOOT_PROBE_PREFIX} level=INFO pid=222 commit=abc\n"
        "2026-08-20 15:00:01 [INFO] [mems26] SHADOW trade TM id=1\n"
    )
    res = find_boot_probe(str(log), pid=222)
    assert res["found"] and res["pid_match"] and res["pid"] == 222
    assert res["info_after"] >= 1


def test_find_boot_probe_fails_on_a_stale_pid_the_2026_08_19_case(tmp_path):
    """A probe from the PREVIOUS boot must not green-light the current process."""
    log = tmp_path / "backend.err.log"
    log.write_text(
        f"2026-08-19 15:00:00 [INFO] [mems26.boot] {BOOT_PROBE_PREFIX} level=INFO pid=111 commit=abc\n"
    )
    res = find_boot_probe(str(log), pid=999)
    assert res["found"] and not res["pid_match"]
    assert "999" in res["reason"] and "111" in res["reason"]


def test_find_boot_probe_reports_a_log_with_no_probe_at_all(tmp_path):
    log = tmp_path / "backend.err.log"
    log.write_text("BarRouter: dispatch total 296.2ms for 5min\n" * 100)  # bare = lastResort
    res = find_boot_probe(str(log), pid=1)
    assert not res["found"] and not res["pid_match"]
    assert "T-61" in res["reason"]


def test_find_boot_probe_never_raises_on_a_missing_file(tmp_path):
    res = find_boot_probe(str(tmp_path / "nope.log"), pid=1)
    assert res["found"] is False and res["reason"]


# ── 5. the bug the restored INFO layer immediately surfaced ──────────────────

def test_daytype_consumer_info_line_survives_a_none_probability():
    """`"prob=%.2f" % None` raises TypeError *inside logging*.

    It sat in `day_type/consumer.py:149` unnoticed for as long as root logging was
    stuck at WARNING — the record was never formatted, so the bug never ran.  Turning
    the INFO layer back on executed it on the first upsert with a missing probability.
    Fixed by formatting defensively and printing `None` honestly (Rule 1) rather than
    inventing `0.00`.
    """
    stream = _fresh_root_with_stream()
    log = logging.getLogger("backend.v9.systems.day_type.consumer")
    # The exact call shape from the fixed line — must not raise, must say "None".
    for prob in (None, 0.6):
        value = f"{prob:.2f}" if isinstance(prob, (int, float)) else prob
        log.info("DayTypeConsumer upserted: date=%s type=%s prob=%s", "2026-08-20", "Trend", value)
    out = stream.getvalue()
    assert "prob=None" in out and "prob=0.60" in out
    assert "Logging error" not in out

    src = open(os.path.join(REPO_ROOT, "backend", "v9", "systems", "day_type",
                            "consumer.py")).read()
    assert "prob=%.2f" not in src, "the None-unsafe format string is back"


# ── 6. wiring — the fix must not be refactored back out ──────────────────────

def test_main_configures_logging_before_importing_backend_v9():
    """Import order is the whole point: a module that logs at import time must already
    have a configured root. Guards against a future 'tidy the imports' commit."""
    src = open(os.path.join(REPO_ROOT, "backend", "main.py")).read()
    tree = ast.parse(src)
    cfg_line = v9_line = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "backend.logging_setup" and cfg_line is None:
                cfg_line = node.lineno
            if node.module.startswith("backend.v9") and v9_line is None:
                v9_line = node.lineno
    assert cfg_line is not None, "backend/main.py no longer imports backend.logging_setup"
    assert v9_line is not None
    assert cfg_line < v9_line, (
        f"logging_setup imported at line {cfg_line}, after backend.v9 at {v9_line}")
    assert "_configure_logging()" in src, "configure_logging() is imported but never called"


def test_fire_drill_asserts_the_boot_probe():
    src = open(os.path.join(REPO_ROOT, "scripts", "fire_drill.py")).read()
    assert "check_logging_layer" in src
    assert "find_boot_probe" in src
    assert "check_logging_layer()" in src.split("def stage_d")[1], \
        "the logging check is defined but never run from stage_d"
