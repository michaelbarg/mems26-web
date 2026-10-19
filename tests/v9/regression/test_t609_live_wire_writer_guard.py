"""T-609 (2026-10-20) — the live wire is default-deny for every process but the backend.

19.10 23:27:59 IL: `cmd_000404.json` (PLACE LONG 3 around the live price, stop -20,
targets +5/+10/+15) was written into the LIVE command queue by a process that was not
the backend — the backend's own first command after its 23:01 restart was #404 (the
FLATTEN of 20.10 00:34). Sierra filled it in Sim1 and the backend raised ORPHAN FILL.
The 07-28 lock only fired when PYTEST_CURRENT_TEST was set, which a script, a harness,
a mutation driver, a REPL or a test's background thread never sets.

These tests never touch the real ~/SierraChart_Data: the in-process cases monkeypatch
LIVE_SIGNALS_DIR to a tmp dir; the subprocess cases run a clean interpreter (no pytest
loaded, no PYTEST_CURRENT_TEST) with HOME pointed at a tmp dir, so its LIVE dir is fake.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

import backend.v9.services.sierra_command as sc

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture
def fake_live(tmp_path, monkeypatch):
    live = tmp_path / "SierraChart_Data" / "v9_export"
    live.mkdir(parents=True)
    monkeypatch.setattr(sc, "LIVE_SIGNALS_DIR", live)
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(live))
    return live


# ── in-process: the verdict table ────────────────────────────────────────────

def test_running_test_is_refused(monkeypatch):
    assert os.getenv("PYTEST_CURRENT_TEST")
    monkeypatch.setattr(sys, "argv", ["/x/uvicorn/__main__.py", "backend.main:app"])
    ok, why = sc.live_wire_writer_status()
    assert ok is False and "test process" in why          # even with a backend argv


def test_backend_argv_is_allowed(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(sys, "argv", ["/lib/site-packages/uvicorn/__main__.py",
                                      "backend.main:app", "--host", "0.0.0.0", "--port", "8000"])
    ok, why = sc.live_wire_writer_status()
    assert ok is True and "backend process" in why


def test_pytest_loaded_is_refused_even_with_opt_in(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(sys, "argv", ["/x/pytest"])
    monkeypatch.setenv("MEMS26_ALLOW_LIVE_COMMAND", "1")
    monkeypatch.setenv("LIVE_WIRE_WRITER_GUARD_V1", "0")
    ok, why = sc.live_wire_writer_status()
    assert ok is False and "pytest is loaded" in why


def test_live_write_from_a_test_raises_and_writes_nothing(fake_live):
    with pytest.raises(RuntimeError, match="REFUSING to write"):
        sc.write_flatten_account(source="t609", reason="must be refused")
    assert not list(fake_live.rglob("*.json"))


def test_non_live_dir_is_untouched_by_the_guard(tmp_path, monkeypatch):
    other = tmp_path / "signals"
    other.mkdir()
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(other))
    sc.write_flatten_account(source="t609", reason="tmp dir is fine")
    assert (other / "trade_command.json").exists()


# ── subprocess: a clean interpreter, exactly the 19.10 writer's situation ────

_WRITE = (
    "import sys\n"
    "{argv}"
    "from backend.v9.services.sierra_command import write_flatten_account\n"
    "write_flatten_account(source='t609', reason='subprocess')\n"
    "print('WROTE')\n"
)


def _run(tmp_path, *, argv_line="", extra_env=None):
    home = tmp_path / "home"
    live = home / "SierraChart_Data" / "v9_export"
    live.mkdir(parents=True, exist_ok=True)
    env = {"HOME": str(home), "PATH": os.environ.get("PATH", ""),
           "PYTHONPATH": str(REPO), "MEMS26_SIGNALS_DIR": str(live),
           "LC_ALL": "en_US.UTF-8", "PYTHONIOENCODING": "utf-8"}
    env.update(extra_env or {})
    assert "PYTEST_CURRENT_TEST" not in env
    p = subprocess.run([sys.executable, "-c", _WRITE.format(argv=argv_line)],
                       cwd=str(REPO), env=env, capture_output=True, text=True, timeout=60)
    return p, live


def test_plain_script_is_refused(tmp_path):
    p, live = _run(tmp_path)
    assert p.returncode != 0
    assert "REFUSING to write" in p.stderr and "not the backend process" in p.stderr
    assert not (live / "trade_command.json").exists()
    assert not list((live / "command_queue").glob("cmd_*.json")) if (live / "command_queue").exists() else True


def test_explicit_opt_in_is_allowed(tmp_path):
    p, live = _run(tmp_path, extra_env={"MEMS26_ALLOW_LIVE_COMMAND": "1"})
    assert p.returncode == 0, p.stderr[-800:]
    assert "WROTE" in p.stdout and (live / "trade_command.json").exists()


def test_backend_process_is_allowed(tmp_path):
    p, live = _run(tmp_path, argv_line="sys.argv = ['/x/uvicorn/__main__.py', 'backend.main:app']\n")
    assert p.returncode == 0, p.stderr[-800:]
    assert (live / "trade_command.json").exists()


def test_escape_hatch_allows(tmp_path):
    p, live = _run(tmp_path, extra_env={"LIVE_WIRE_WRITER_GUARD_V1": "0"})
    assert p.returncode == 0, p.stderr[-800:]
    assert (live / "trade_command.json").exists()
