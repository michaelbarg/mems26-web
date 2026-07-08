"""SYS-3 — the 2026-07-08 orphan chain (trade 308/310) must never repeat.

Live incident: ENTRY was submit-acked (parent id stored) → a later bare
ORDER_FAILED (child stop/target) made the backend CANCEL the live trade row →
Sierra kept the real position with no tracking (NAKED) → Michael flattened
manually; the cockpit exit then left the gateway slot stuck.

Anti-tautological: test 1 FAILS on the old code (it cancelled the trade).
Runnable standalone: python3 test_orphan_chain_guard.py
"""
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

_FP = os.path.join(_REPO, "backend", "v9", "services", "fill_poller.py")
_spec = importlib.util.spec_from_file_location("fp_orphan", _FP)
fp = importlib.util.module_from_spec(_spec)
sys.modules["fp_orphan"] = fp
_spec.loader.exec_module(fp)


class TM:
    def __init__(self, trades):
        self._trades = trades
        self.closed = []

    def get_active_trades(self):
        return list(self._trades)

    def close_trade(self, tid, reason=None, **kw):
        self.closed.append((tid, reason))

    def set_sierra_order_ids(self, *a, **k):
        pass

    class _DB:  # noqa: D401 — stub
        def flush(self):
            pass
    _db = _DB()


def _run_failed_result(trade):
    p = fp.FillPoller(trade_manager=TM([trade]))
    with tempfile.TemporaryDirectory() as d:
        res = Path(d) / "trade_result.json"
        res.write_text(json.dumps({"status": "ORDER_FAILED", "ts": 1, "error": -1,
                                   "error_text": "GENERAL_ERROR"}))
        fp.RESULT_PATH = res
        p._check_result()
        return p, p._tm


# 1 — submit-acked trade (has sierra_order_id) must NOT be cancelled on a bare ORDER_FAILED.
def test_submitted_trade_not_cancelled_on_child_failure():
    t = SimpleNamespace(id=320, mode="live", state="PENDING",
                        quality={"sierra_order_id": 9100}, pnl_usd=None, outcome=None)
    p, tm = _run_failed_result(t)
    assert tm.closed == [], f"submit-acked trade must NOT be cancelled: {tm.closed}"
    assert t.state == "PENDING"  # untouched — reconcile/System6 own the position now


# 2 — a never-acked trade (no sierra_order_id) is still cancelled (original behavior).
def test_unacked_trade_still_cancelled():
    t = SimpleNamespace(id=321, mode="live", state="PENDING", quality={},
                        pnl_usd=None, outcome=None)
    p, tm = _run_failed_result(t)
    assert tm.closed and tm.closed[0][0] == 321, tm.closed
    assert t.state == "CANCELLED"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ok - {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL - {t.__name__}: {e!r}")
    print(f"\ntest_orphan_chain_guard.py: {len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
