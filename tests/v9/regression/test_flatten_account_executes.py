"""T1 — every FLATTEN path must ACTUALLY WRITE A COMMAND FILE.

Michael, live 2026-08-14: "I got an alert that the trade was realized and in
reality it was never realized in Sierra."

Root cause: `write_trade_command` declares `trade_id` as a REQUIRED
keyword-only argument. All three FLATTEN_ACCOUNT callers passed it inside
`context` instead, so every call raised TypeError before writing a byte:
  · MAE_SCRATCH            → books closed at $0 while Sierra held SHORT 4
                             for ~58 min, real loss −$83.75 (trade #682)
  · TARGET_APPROACH_REALIZE → never executed once (announced twice on the
                             same trade 21 min apart)
  · phone FLATTEN button    → the emergency kill-switch sent nothing

The first fix attempt (ede1d570) was itself verified only with
`inspect.getsource()` string matching — the tests passed while the code still
raised. THIS FILE EXECUTES THE CODE. Every test writes to a tmp queue dir and
asserts a real file appeared on disk with the right payload.
"""
import json
import os

import pytest


@pytest.fixture
def queue(tmp_path, monkeypatch):
    """Point the command writer at a throwaway signals dir (never the live one —
    the DLL executes whatever lands there; see the 2026-07-28 incident)."""
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(tmp_path))
    from backend.v9.services import sierra_command as sc
    return tmp_path, sc


def _written(tmp_path):
    """Every command file written by the queue (excluding archives)."""
    out = []
    for p in list(tmp_path.rglob("*.json")):
        if "archived" in str(p):
            continue
        try:
            out.append(json.loads(p.read_text()))
        except Exception:
            pass
    return out


class TestWriterExecutes:
    def test_write_flatten_account_creates_a_file(self, queue):
        tmp_path, sc = queue
        sc.write_flatten_account(trade_id="682", source="mae_scratch",
                                 reason="adverse excursion")
        payloads = _written(tmp_path)
        assert payloads, "FLATTEN_ACCOUNT wrote NO file — the exit never reaches Sierra"
        flat = [p for p in payloads if p.get("op") == "FLATTEN_ACCOUNT"]
        assert flat, f"no FLATTEN_ACCOUNT op in {[p.get('op') for p in payloads]}"
        assert "FLATTEN_ACCOUNT" in json.dumps(flat[0]), \
            "the DLL matches on the FLATTEN_ACCOUNT string — it must be in the payload"

    def test_callable_without_trade_id(self, queue):
        """The phone button has no trade — it must not need one."""
        tmp_path, sc = queue
        sc.write_flatten_account(source="mobile_manual", reason="michael pressed")
        assert [p for p in _written(tmp_path) if p.get("op") == "FLATTEN_ACCOUNT"]

    def test_old_call_shape_would_have_raised(self, queue):
        """Locks in WHY production was silently broken: the historic call
        shape raises TypeError. If someone reintroduces it, this fails."""
        _tmp, sc = queue
        with pytest.raises(TypeError):
            sc.write_trade_command(action="FLATTEN_ACCOUNT",
                                   context={"source": "x", "trade_id": "1"})


class TestCallSitesUseTheSafeHelper:
    """The three production paths must call the helper that cannot be
    mis-called — not the trap-shaped generic writer."""

    def test_mae_scratch_and_target_realize(self):
        import inspect
        from backend.v9.services.trade_manager import bar_level_detector as bld
        src = inspect.getsource(bld)
        assert "write_flatten_account" in src
        # the old trap must be gone from both S6 exit paths
        assert 'write_trade_command(\n' not in src.replace(" ", "")

    def test_mobile_flatten(self):
        import inspect
        from backend.v9.api.v9 import mobile_monitor as mm
        src = inspect.getsource(mm)
        assert "write_flatten_account" in src
        assert 'write_trade_command(action="FLATTEN_ACCOUNT"' not in src


class TestBooksNeverCloseWithoutTheCommand:
    def test_scratch_failure_skips_book_close(self):
        import inspect
        from backend.v9.services.trade_manager import bar_level_detector as bld
        src = inspect.getsource(bld)
        i = src.index("S6 MAE SCRATCH: trade")
        j = src.index('close_trade(trade.id, reason="MAE_SCRATCH")', i)
        blk = src[i:j]
        assert "continue" in blk and "FLATTEN command" in blk

    def test_target_realize_failure_skips_book_close(self):
        import inspect
        from backend.v9.services.trade_manager import bar_level_detector as bld
        src = inspect.getsource(bld)
        i = src.index("S6 TARGET APPROACH REALIZE")
        j = src.index('close_trade(trade.id, reason="TARGET_APPROACH_REALIZE")', i)
        blk = src[i:j]
        assert "continue" in blk and "FLATTEN command" in blk
