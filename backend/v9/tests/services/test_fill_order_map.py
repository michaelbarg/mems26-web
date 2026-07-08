"""L2-residual / N3 tests (2026-07-08) — order-id map + no-silent-emit-drops.

Anti-tautological: each test FAILS on the pre-fix code (verified by stashing the
fix and re-running):
  1. ORDER_SUBMITTED ack → order-id map + sierra_order_id persisted (old code
     ignored SUBMITTED entirely → ENTRY fill needed the I-58 fallback).
  2. Fallback-resolved ENTRY → the parent order id itself is mapped (old code
     deliberately skipped it → later events re-entered the fallback).
  3. A live trade with no sierra_order_id → MODIFY_STOP skip WARNS (old code:
     silent return → DB recorded stop-moves Sierra never saw, live trade 299).
  4. Shadow skip stays SILENT (by design — not a failure).
Runnable standalone: `python3 test_fill_order_map.py` (repo root auto-added).
"""
import importlib.util
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

# --- import fill_poller standalone (stdlib-only module) ---
_FP = os.path.join(_REPO, "backend", "v9", "services", "fill_poller.py")
_spec = importlib.util.spec_from_file_location("fill_poller_under_test", _FP)
fp_mod = importlib.util.module_from_spec(_spec)
sys.modules["fill_poller_under_test"] = fp_mod
_spec.loader.exec_module(fp_mod)


class StubTM:
    """Minimal TradeManager interface for FillPoller tests."""

    def __init__(self, trades):
        self._trades = trades
        self.stored_ids = {}   # trade_id -> ids dict (set_sierra_order_ids calls)
        self.fills = []

    def get_active_trades(self):
        return list(self._trades)

    def set_sierra_order_ids(self, trade_id, ids):
        merged = self.stored_ids.setdefault(trade_id, {})
        merged.update({k: v for k, v in ids.items() if v is not None})

    def on_fill(self, trade_id, price):
        self.fills.append((trade_id, price))

    def _get_trade(self, trade_id):
        for t in self._trades:
            if t.id == trade_id:
                return t
        return None


def _poller_with(trades):
    p = fp_mod.FillPoller(trade_manager=StubTM(trades))
    return p, p._tm


# 1 — ORDER_SUBMITTED ack registers the full order-id map + persists ids.
def test_submit_ack_registers_map():
    trade = SimpleNamespace(id=305, mode="live", state="PENDING", quality={})
    p, tm = _poller_with([trade])
    with tempfile.TemporaryDirectory() as d:
        res = Path(d) / "trade_result.json"
        res.write_text(json.dumps({
            "status": "ORDER_SUBMITTED", "ts": 1783500000,
            "parent_id": 8500, "target_id": 8501, "stop_id": 8502,
        }))
        fp_mod.RESULT_PATH = res
        p._check_result()
        # map: all three ids resolve to the trade → no I-58 fallback needed
        assert p._order_map.get(8500) == 305, p._order_map
        assert p._order_map.get(8501) == 305 and p._order_map.get(8502) == 305
        # persisted: _emit_modify_stop's oid source is populated at submit time
        assert tm.stored_ids[305]["sierra_order_id"] == 8500
        assert tm.stored_ids[305]["c1_stop_id"] == 8502
        # NOT cleared (reconcile + /trade_result API still read it)
        assert res.read_text().strip() != ""
        # idempotent on re-read of the same ack
        p._check_result()
        assert p._order_map.get(8500) == 305


# 2 — fallback-resolved ENTRY maps the parent order id itself.
def test_entry_fallback_stores_ids_and_maps_parent():
    trade = SimpleNamespace(id=306, mode="live", state="PENDING", quality={})
    p, tm = _poller_with([trade])
    p._process_fill({"kind": "ENTRY", "order_id": 8600, "price": 7530.25,
                     "ts": 1783500001, "c1_target_id": 8601, "c1_stop_id": 8602})
    assert tm.fills == [(306, 7530.25)]
    assert tm.stored_ids[306]["sierra_order_id"] == 8600  # existing behavior guard
    assert p._order_map.get(8601) == 306 and p._order_map.get(8602) == 306
    assert p._order_map.get(8600) == 306  # NEW: parent id mapped too


# 3 + 4 — skipped Sierra emits warn on the live path, stay silent for shadow.
def _manager_for_emit_tests():
    from backend.v9.services.trade_manager.manager import TradeManager
    return TradeManager(db=None)


class _Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record.getMessage())


def test_modify_stop_warns_when_oid_missing():
    os.environ["LIVE_EXECUTION_V1"] = "1"
    tm = _manager_for_emit_tests()
    lg = logging.getLogger("backend.v9.services.trade_manager.manager")
    cap = _Capture()
    lg.addHandler(cap)
    try:
        trade = SimpleNamespace(id=307, mode="live", quality={})  # no sierra_order_id
        tm._emit_modify_stop(trade, 7525.0)
        warned = [m for m in cap.records if "MODIFY_STOP SKIPPED" in m]
        assert len(warned) == 1, cap.records  # old code: silent → 0 → FAIL
        assert "no sierra_order_id" in warned[0]
        tm._emit_modify_stop(trade, 7526.0)  # within rate-limit window
        assert len([m for m in cap.records if "MODIFY_STOP SKIPPED" in m]) == 1
    finally:
        lg.removeHandler(cap)
        os.environ.pop("LIVE_EXECUTION_V1", None)


def test_shadow_skip_stays_silent():
    tm = _manager_for_emit_tests()
    lg = logging.getLogger("backend.v9.services.trade_manager.manager")
    cap = _Capture()
    lg.addHandler(cap)
    try:
        trade = SimpleNamespace(id=308, mode="shadow", quality={})
        tm._emit_modify_stop(trade, 7525.0)
        tm._emit_exit(trade, 1)
        assert not any("SKIPPED" in m for m in cap.records), cap.records
    finally:
        lg.removeHandler(cap)


def test_live_flag_off_warns():
    os.environ.pop("LIVE_EXECUTION_V1", None)  # flag OFF
    tm = _manager_for_emit_tests()
    lg = logging.getLogger("backend.v9.services.trade_manager.manager")
    cap = _Capture()
    lg.addHandler(cap)
    try:
        trade = SimpleNamespace(id=309, mode="live", quality={"sierra_order_id": 8700})
        tm._emit_modify_stop(trade, 7525.0)
        warned = [m for m in cap.records if "MODIFY_STOP SKIPPED" in m]
        assert len(warned) == 1 and "flag OFF" in warned[0], cap.records
    finally:
        lg.removeHandler(cap)


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
    print(f"\ntest_fill_order_map.py: {len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
