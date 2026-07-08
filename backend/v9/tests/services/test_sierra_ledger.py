"""Sierra-sourced ledger tests (journal L8) — the 7 spec cases.

Anti-tautological: each asserts the ledger reflects SIERRA fills, not backend
claims. Runnable standalone (`python3 test_sierra_ledger.py`) or via pytest.
"""
import importlib.util
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_MOD = os.path.abspath(os.path.join(_HERE, "..", "..", "services", "sierra_ledger.py"))
_spec = importlib.util.spec_from_file_location("sierra_ledger", _MOD)
sl = importlib.util.module_from_spec(_spec)
sys.modules["sierra_ledger"] = sl  # required so dataclasses can resolve annotations
_spec.loader.exec_module(sl)


def _jl(rows):
    return [json.dumps(r) for r in rows]


# 1 — Ledger reconstruction from fills alone (SHORT: T1 below entry).
def test_ledger_reconstruction():
    fills = _jl([
        {"kind": "ENTRY", "order_id": 100, "price": 7536.25, "ts": 1, "contracts": 2,
         "c1_stop_id": 101, "c1_target_id": 102},
        {"kind": "T1", "order_id": 102, "price": 7522.0, "ts": 2},
        {"kind": "STOP", "order_id": 101, "price": 7524.0, "ts": 3},
    ])
    lt = sl.build_ledger(sl.parse_fills(fills))
    assert len(lt) == 1
    t = lt[0]
    assert t.entry_price == 7536.25 and t.contracts == 2
    assert t.direction == "SHORT" and t.direction_source == "t_fill"
    assert [e.kind for e in t.exits] == ["T1", "STOP"]
    assert t.closed is True


# 2 — P&L uses the actual fill price, not the intended level.
def test_pnl_from_fill_price():
    # SHORT entry 7536.25; T1 filled 7522 (14.25 pt), STOP filled 7524 (12.25 pt).
    fills = _jl([
        {"kind": "ENTRY", "order_id": 1, "price": 7536.25, "ts": 1, "contracts": 2},
        {"kind": "T1", "order_id": 1, "price": 7522.0, "ts": 2, "contracts": 1},
        {"kind": "STOP", "order_id": 1, "price": 7524.0, "ts": 3, "contracts": 1},
    ])
    t = sl.build_ledger(sl.parse_fills(fills), point_value=5.0)[0]
    # (7536.25-7522)*5*1 + (7536.25-7524)*5*1 = 71.25 + 61.25 = 132.5
    assert t.realized_pnl == 132.5 and t.pnl_basis == "fill_qty"
    # proof it followed the FILL not the level: change fill → P&L changes
    fills2 = _jl([
        {"kind": "ENTRY", "order_id": 1, "price": 7536.25, "ts": 1, "contracts": 1},
        {"kind": "T1", "order_id": 1, "price": 7500.0, "ts": 2, "contracts": 1},
    ])
    t2 = sl.build_ledger(sl.parse_fills(fills2), point_value=5.0)[0]
    assert t2.realized_pnl == round((7536.25 - 7500.0) * 5.0, 2)  # 181.25


# 3 — Reconcile raises CRITICAL when backend stop ≠ Sierra stop (the L2 catch).
def test_reconcile_divergence():
    fills = _jl([{"kind": "ENTRY", "order_id": 1, "price": 7540.0, "ts": 1, "contracts": 2}])
    t = sl.build_ledger(sl.parse_fills(fills))[0]
    backend = {"entry_price": 7540.0, "stop": 7544.75, "state": "PARTIAL", "contracts": 2}
    divs = sl.reconcile(t, backend, sierra_stop=7551.0)
    fields = {d.field for d in divs}
    assert "stop" in fields
    assert all(d.severity == "CRITICAL" for d in divs)
    # aligned → MATCH (no divergence)
    assert sl.reconcile(t, {"entry_price": 7540.0, "stop": 7551.0, "state": "PARTIAL",
                            "contracts": 2}, sierra_stop=7551.0) == []


# 4 — Manual stop-move: Sierra stop the backend never commanded → MANUAL_STOP_MOVE.
def test_manual_stop_move():
    fills = _jl([{"kind": "ENTRY", "order_id": 1, "price": 7540.0, "ts": 1, "contracts": 2}])
    t = sl.build_ledger(sl.parse_fills(fills))[0]
    ev = sl.detect_manual(t, {"state": "PARTIAL"},
                          commanded_stops=[7532.0, 7540.0], sierra_stop=7548.0)
    assert len(ev) == 1 and ev[0].kind == "MANUAL_STOP_MOVE"
    assert ev[0].tag == "MANUAL" and ev[0].price == 7548.0


# 5 — Manual close: Sierra flat but backend still open → MANUAL_CLOSE at fill.
def test_manual_close():
    fills = _jl([
        {"kind": "ENTRY", "order_id": 1, "price": 7540.0, "ts": 1, "contracts": 2},
        {"kind": "FLATTEN", "order_id": 1, "price": 7538.5, "ts": 2},
    ])
    t = sl.build_ledger(sl.parse_fills(fills))[0]
    ev = sl.detect_manual(t, {"state": "FILLED"})
    kinds = [e.kind for e in ev]
    assert "MANUAL_CLOSE" in kinds
    mc = [e for e in ev if e.kind == "MANUAL_CLOSE"][0]
    assert mc.price == 7538.5 and mc.tag == "MANUAL"


# 6 — MANUAL vs SYSTEM: a commanded stop is NOT flagged manual.
def test_system_not_flagged_manual():
    fills = _jl([{"kind": "ENTRY", "order_id": 1, "price": 7540.0, "ts": 1, "contracts": 2}])
    t = sl.build_ledger(sl.parse_fills(fills))[0]
    ev = sl.detect_manual(t, {"state": "PARTIAL"},
                          commanded_stops=[7541.0], sierra_stop=7541.0)
    assert all(e.kind != "MANUAL_STOP_MOVE" for e in ev)  # system move → not manual


# 7 — Live-account filter: demo/shadow fills excluded from the live ledger.
def test_live_account_filter():
    fills = _jl([
        {"kind": "ENTRY", "order_id": 1, "price": 7540.0, "ts": 1, "contracts": 2, "account": "37138283"},
        {"kind": "ENTRY", "order_id": 2, "price": 7500.0, "ts": 1, "contracts": 2, "account": "PA-APEX-125218-01"},
    ])
    lt = sl.build_ledger(sl.parse_fills(fills), live_account="37138283")
    assert len(lt) == 1 and lt[0].entry_order_id == 1


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in tests:
        fn()
        passed += 1
        print(f"  ok - {fn.__name__}")
    print(f"\ntest_sierra_ledger.py: {passed}/{len(tests)} passed")
