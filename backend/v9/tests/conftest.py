"""conftest — test isolation for backend/v9/tests/.

CRITICAL (2026-08-12): pytest runs MUST NOT write to live production files.
Two incidents (08-11 19:26 + 08-12 07:00): test fixtures polluted the live
gateway_decisions.jsonl with 510 phantom lines, corrupting the radar and
gate-decision panels during RTH.

This conftest redirects ALL gateway decision writes to a per-test temp
directory. It also sets a sentinel env var (MEMS26_TEST_MODE=1) that any
code path can check to avoid touching production state.
"""
import os
import pytest


@pytest.fixture(autouse=True)
def _isolate_gateway_decisions(tmp_path, monkeypatch):
    """Redirect gateway_decisions.jsonl to tmp_path for EVERY test.

    Also sets MEMS26_TEST_MODE=1 so any code that checks can bail out
    of production-only side effects (file writes, Sierra commands, etc.).
    """
    decisions_file = str(tmp_path / "gateway_decisions.jsonl")
    monkeypatch.setenv("GATEWAY_DECISIONS_PATH", decisions_file)
    monkeypatch.setenv("MEMS26_TEST_MODE", "1")
    # Ensure hydration is OFF in tests (don't read stale production data)
    monkeypatch.delenv("GATEWAY_DECISIONS_HYDRATE", raising=False)
    yield
    # tmp_path is cleaned up by pytest automatically


@pytest.fixture(autouse=True)
def _isolate_sierra_commands(tmp_path, monkeypatch):
    """Prevent tests from writing Sierra trade commands to the real export dir."""
    monkeypatch.setenv("V9_EXPORT_DIR", str(tmp_path / "v9_export"))
    os.makedirs(str(tmp_path / "v9_export"), exist_ok=True)
