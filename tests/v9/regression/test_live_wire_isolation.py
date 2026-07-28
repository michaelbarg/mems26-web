"""The live wire must be unreachable from a test process (2026-07-28).

`trade_command.json` is the one file the Sierra DLL polls and EXECUTES. On
2026-07-28 the regression suite wrote to it: MEMS26_SIGNALS_DIR was unset in
tests and defaulted to the real ~/SierraChart_Data/v9_export, so a run placed a
real bracketed entry on Michael's live account. Sierra's activity log for that
day holds six "Order reject — Insufficient Account Value (NLV) for margin"
entries; the account being under-margined is the only reason none of them filled.

Two locks, tested here:
  1. conftest redirects the signals dir for the whole session.
  2. _write_command refuses outright if a pytest process aims at the live dir.
"""
import os
from pathlib import Path

import pytest

import backend.v9.services.sierra_command as sc_cmd

LIVE = Path(os.path.expanduser("~/SierraChart_Data/v9_export"))


# ── lock 1: the session is redirected ────────────────────────────────────────

def test_signals_dir_is_not_the_live_dir():
    assert sc_cmd.signals_dir().resolve() != LIVE.resolve(), (
        "tests are pointed at the LIVE signals dir — conftest isolation is gone")


def test_command_file_is_not_the_live_command_file():
    assert sc_cmd.command_file().resolve() != (LIVE / "trade_command.json").resolve()


@pytest.mark.parametrize("var", ["MEMS26_SIGNALS_DIR", "V9_EXPORT_DIR"])
def test_env_redirect_is_set_for_the_session(var):
    val = os.getenv(var)
    assert val, f"{var} must be set by conftest before any module import"
    assert Path(val).resolve() != LIVE.resolve()


# ── lock 2: the choke point refuses ──────────────────────────────────────────

def test_write_command_refuses_the_live_dir_under_pytest(monkeypatch):
    """Even if the redirect is removed mid-run, the write must not happen."""
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(LIVE))
    assert os.getenv("PYTEST_CURRENT_TEST")          # pytest marks its own runs
    with pytest.raises(RuntimeError, match="REFUSING to write"):
        sc_cmd._write_command({"op": "PLACE", "qty": 4})


def test_live_command_file_is_not_created_by_the_refusal(monkeypatch):
    before = None
    live_cmd = LIVE / "trade_command.json"
    if live_cmd.exists():
        before = live_cmd.stat().st_mtime
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(LIVE))
    with pytest.raises(RuntimeError):
        sc_cmd._write_command({"op": "PLACE", "qty": 4})
    after = live_cmd.stat().st_mtime if live_cmd.exists() else None
    assert after == before, "the refusal still touched the live file"


def test_writes_are_allowed_to_a_tmp_dir(monkeypatch, tmp_path):
    """The guard must not block legitimate isolated writes."""
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(tmp_path))
    sc_cmd._write_command({"op": "PLACE", "qty": 4})
    assert (tmp_path / "trade_command.json").exists()


def test_guard_is_inert_outside_pytest(monkeypatch, tmp_path):
    """Production must be unaffected: no PYTEST_CURRENT_TEST → no refusal."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(tmp_path))
    sc_cmd._write_command({"op": "FLATTEN_ACCOUNT"})
    assert (tmp_path / "trade_command.json").exists()


# ── the sim-verification scripts must gate on is_sim ─────────────────────────

@pytest.mark.parametrize("script", [
    "scripts/verify_place_stop_v2_sim.py",
    "scripts/sim_matrix_e2e.py",
    "scripts/verify_t17_e2e_4contract_sim.py",
])
def test_sim_scripts_check_is_sim_before_sending(script):
    """These write real commands by design. Each must read Sierra's is_sim and
    refuse on a live account — a 'sim' script run against live is an order."""
    p = Path(script)
    if not p.exists():
        pytest.skip(f"{script} not present")
    src = p.read_text(encoding="utf-8")
    assert "is_sim" in src, f"{script} sends commands without checking is_sim"
