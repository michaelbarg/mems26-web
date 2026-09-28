"""T-505 · fire_drill's T-61 probe must find the boot line in EITHER app log.

Root cause measured 28.09 15:41 (cowork-dev, gate run 48): `check_logging_layer()`
read only `DEFAULT_LOG_FILE` (/tmp/backend.err.log), but `scripts/start_all.sh:76`
starts the backend under `screen` with `2>&1 | tee /tmp/backend.log`, so the
RUNNING process's boot line lands in backend.log while backend.err.log holds only
the boot lines of transient probe processes (fire_drill / pytest import the app).
The gate reported `newest boot probe is pid=15052 but the running backend is
pid=14900` -> NO-GO, while backend.log held `pid=14904 ... level=INFO` plus 126
INFO lines after it. A false NO-GO is as dangerous as a false GO: it halts a
legitimate trading day, or trains agents to wave past a red gate.

These tests pin the candidate list, not the cosmetics of the message.
"""
import os
import re

import pytest

FIRE_DRILL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))),
    "scripts", "fire_drill.py")

BOOT_LINE = ("2026-09-28 15:40:27 [INFO] [mems26.boot] [boot] logging OK "
             "level=INFO pid={pid} commit=aae6954e stream=stderr\n")


def _source():
    with open(FIRE_DRILL, encoding="utf-8") as fh:
        return fh.read()


def test_both_app_logs_are_candidates():
    """backend.log must be probed alongside DEFAULT_LOG_FILE (the regression)."""
    src = _source()
    assert "log_candidates" in src, "T-505 candidate list is gone"
    assert "/tmp/backend.log" in src, (
        "backend.log dropped from the T-61 probe — start_all.sh restarts will "
        "again report a false NO-GO (T-505)")
    assert "DEFAULT_LOG_FILE" in src, "backend.err.log (LaunchAgent path) dropped"


def test_env_override_still_wins():
    """MEMS26_LOG_FILE stays authoritative — it is how the gate was proven."""
    src = _source()
    m = re.search(r"_env_log\s*=\s*os\.getenv\(\s*[\"']MEMS26_LOG_FILE[\"']", src)
    assert m, "MEMS26_LOG_FILE override removed from check_logging_layer"
    assert re.search(r"\[_env_log\]\s*if\s*_env_log", src), (
        "MEMS26_LOG_FILE must REPLACE the candidate list, not extend it")


def test_find_boot_probe_matches_running_pid_in_second_candidate(tmp_path):
    """The real shape: err-log has a stale pid, backend.log has the live one."""
    from backend.logging_setup import find_boot_probe

    err_log = tmp_path / "backend.err.log"
    app_log = tmp_path / "backend.log"
    err_log.write_text(BOOT_LINE.format(pid=15052), encoding="utf-8")
    app_log.write_text(
        BOOT_LINE.format(pid=14904)
        + "2026-09-28 15:40:28 [INFO] [fill_poller] [FillPoller] started\n",
        encoding="utf-8")

    running = 14904
    assert find_boot_probe(str(err_log), pid=running).get("pid_match") is False, (
        "fixture wrong: err-log must NOT match the running pid")

    res = find_boot_probe(str(app_log), pid=running)
    assert res.get("found") and res.get("pid_match"), (
        "find_boot_probe cannot see the running pid in backend.log")
    assert res["info_after"] > 0, "INFO must be flowing after the boot line"


def test_first_candidate_still_wins_when_it_matches(tmp_path):
    """Negative control: LaunchAgent layout must not regress to backend.log."""
    from backend.logging_setup import find_boot_probe

    err_log = tmp_path / "backend.err.log"
    err_log.write_text(
        BOOT_LINE.format(pid=649)
        + "2026-09-28 10:59:25 [INFO] [mems26] [Startup] ok\n", encoding="utf-8")
    res = find_boot_probe(str(err_log), pid=649)
    assert res.get("pid_match"), "LaunchAgent path (backend.err.log) broke"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
