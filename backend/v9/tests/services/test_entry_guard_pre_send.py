"""F1 (2026-08-12) — ORDER_FAILED:-1 root-fix regression.

48-session audit: 18/57 live routes (32%) died `ORDER_FAILED:-1` because the
entry was sent while the account carried an unmanaged standing position
(orphan / manual) — Sierra's recipe rejects it synchronously
(AllowOppositeEntryWithOpposingPositionOrOrders=0, MaximumPositionAllowed=10).

Covers:
  1. entry_guard blocks on standing position / working orders / stale state.
  2. Kill-switch PRE_SEND_ENTRY_GUARD_V1=0 restores pass-through.
  3. FillPoller retries a LIVE ORDER_FAILED exactly once when the account is
     clear, then cancels on the second failure.
  4. No retry into a standing position (would fail again) — straight cancel.

Runnable standalone: python3 test_entry_guard_pre_send.py
"""
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

import backend.v9.services.entry_guard as eg  # noqa: E402
from backend.v9.services import fill_poller as fpmod  # noqa: E402
from backend.v9.services import sierra_command as sc  # noqa: E402


def _write_state(dirpath: Path, *, age_s: float = 0.0, **fields) -> Path:
    d = {"ts": int(time.time()), "position_qty": 0, "working_orders": 0,
         "order_placement_armed": 1, "is_sim": 0}
    d.update(fields)
    p = Path(dirpath) / "sierra_state.json"
    p.write_text(json.dumps(d))
    if age_s:
        old = time.time() - age_s
        os.utime(p, (old, old))
    return p


class _TM:
    def __init__(self, trades):
        self._trades = trades
        self.closed = []

    def get_active_trades(self):
        return list(self._trades)

    def close_trade(self, tid, reason=None, **kw):
        self.closed.append((tid, reason))

    class _DB:
        def flush(self):
            pass
    _db = _DB()


def _fresh_env(monkeypatch, tmp_path):
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(tmp_path / "signals"))
    monkeypatch.delenv("PRE_SEND_ENTRY_GUARD_V1", raising=False)
    monkeypatch.delenv("NTFY_TOPIC", raising=False)


# ── 1. guard verdicts ────────────────────────────────────────────────────────

def test_blocks_on_standing_position(tmp_path, monkeypatch):
    _fresh_env(monkeypatch, tmp_path)
    monkeypatch.setattr(eg, "STATE", _write_state(tmp_path, position_qty=-4))
    ok, why, _ = eg.check_live_entry("LONG", 4)
    assert not ok and "standing position -4" in why


def test_blocks_on_working_orders(tmp_path, monkeypatch):
    _fresh_env(monkeypatch, tmp_path)
    monkeypatch.setattr(eg, "STATE", _write_state(tmp_path, working_orders=3))
    ok, why, _ = eg.check_live_entry("SHORT", 4)
    assert not ok and "working order" in why


def test_blocks_on_stale_state(tmp_path, monkeypatch):
    _fresh_env(monkeypatch, tmp_path)
    monkeypatch.setattr(eg, "STATE", _write_state(tmp_path, age_s=120.0))
    ok, why, _ = eg.check_live_entry("LONG", 4)
    assert not ok and "stale" in why


def test_blocks_on_missing_state(tmp_path, monkeypatch):
    _fresh_env(monkeypatch, tmp_path)
    monkeypatch.setattr(eg, "STATE", tmp_path / "nope.json")
    ok, why, _ = eg.check_live_entry("LONG", 4)
    assert not ok


def test_passes_flat_and_warns_disarmed(tmp_path, monkeypatch):
    _fresh_env(monkeypatch, tmp_path)
    monkeypatch.setattr(eg, "STATE",
                        _write_state(tmp_path, order_placement_armed=0, is_sim=1))
    ok, why, warns = eg.check_live_entry("LONG", 4)
    assert ok, why
    assert any("ACK_SHADOW" in w for w in warns)
    assert any("SIM" in w for w in warns)


def test_kill_switch_restores_passthrough(tmp_path, monkeypatch):
    _fresh_env(monkeypatch, tmp_path)
    monkeypatch.setenv("PRE_SEND_ENTRY_GUARD_V1", "0")
    monkeypatch.setattr(eg, "STATE", _write_state(tmp_path, position_qty=-12))
    ok, why, _ = eg.check_live_entry("LONG", 4)
    assert ok and "off" in why


# ── 2. FillPoller retry-once ─────────────────────────────────────────────────

def _order_failed_result(path: Path, ts: float) -> None:
    path.write_text(json.dumps({"status": "ORDER_FAILED", "ts": 1, "error": -1,
                                "error_text": "GENERAL_ERROR_OR_NOT_ENABLED"}))
    os.utime(path, (ts, ts))


def test_live_order_failed_retries_once_then_cancels(tmp_path, monkeypatch):
    _fresh_env(monkeypatch, tmp_path)
    monkeypatch.setattr(eg, "STATE", _write_state(tmp_path))  # flat + fresh
    sc._LAST_PLACE.clear()
    sc._LAST_PLACE["322"] = {"op": "PLACE", "action": "BUY", "trade_id": "322",
                             "direction": "LONG", "price": 7500.0, "contracts": 4,
                             "stop_price": 7495.0, "target_price": 7503.0,
                             "account": "TEST", "mode": "live", "context": {}}
    t = SimpleNamespace(id=322, mode="live", state="PENDING", quality={},
                        pnl_usd=None, outcome=None)
    tm = _TM([t])
    p = fpmod.FillPoller(trade_manager=tm)
    res = tmp_path / "trade_result.json"
    monkeypatch.setattr(fpmod, "RESULT_PATH", res)

    _order_failed_result(res, time.time())
    p._check_result()  # 1st failure → retry, NOT cancel
    assert tm.closed == [], f"first ORDER_FAILED must retry, not cancel: {tm.closed}"
    assert 322 in p._order_failed_retried
    queued = list((tmp_path / "signals" / "command_queue").glob("cmd_*.json"))
    assert len(queued) == 1, f"expected exactly one resubmitted PLACE, got {queued}"
    resent = json.loads(queued[0].read_text())
    assert resent["op"] == "PLACE" and resent["trade_id"] == "322"

    _order_failed_result(res, time.time() + 2)
    p._check_result()  # 2nd failure → cancel
    assert tm.closed and tm.closed[0][0] == 322, tm.closed
    assert t.state == "CANCELLED"


def test_no_retry_into_standing_position(tmp_path, monkeypatch):
    _fresh_env(monkeypatch, tmp_path)
    monkeypatch.setattr(eg, "STATE", _write_state(tmp_path, position_qty=-4))
    sc._LAST_PLACE.clear()
    sc._LAST_PLACE["323"] = {"op": "PLACE", "action": "SELL", "trade_id": "323",
                             "direction": "SHORT", "price": 7500.0, "contracts": 4,
                             "stop_price": 7505.0, "target_price": 7497.0,
                             "account": "TEST", "mode": "live", "context": {}}
    t = SimpleNamespace(id=323, mode="live", state="PENDING", quality={},
                        pnl_usd=None, outcome=None)
    tm = _TM([t])
    p = fpmod.FillPoller(trade_manager=tm)
    res = tmp_path / "trade_result.json"
    monkeypatch.setattr(fpmod, "RESULT_PATH", res)

    _order_failed_result(res, time.time())
    p._check_result()  # guard says the account is NOT clear → straight cancel
    assert tm.closed and tm.closed[0][0] == 323, tm.closed
    qdir = tmp_path / "signals" / "command_queue"
    assert not qdir.exists() or not list(qdir.glob("cmd_*.json")), \
        "must not resubmit into a standing position"


def test_demo_order_failed_keeps_old_behavior(tmp_path, monkeypatch):
    _fresh_env(monkeypatch, tmp_path)
    monkeypatch.setattr(eg, "STATE", _write_state(tmp_path))
    sc._LAST_PLACE.clear()
    t = SimpleNamespace(id=324, mode="demo", state="PENDING", quality={},
                        pnl_usd=None, outcome=None)
    tm = _TM([t])
    p = fpmod.FillPoller(trade_manager=tm)
    res = tmp_path / "trade_result.json"
    monkeypatch.setattr(fpmod, "RESULT_PATH", res)
    _order_failed_result(res, time.time())
    p._check_result()
    assert tm.closed and tm.closed[0][0] == 324, tm.closed


if __name__ == "__main__":
    import inspect
    import tempfile

    class _MP:
        def setenv(self, k, v):
            os.environ[k] = v

        def delenv(self, k, raising=True):
            os.environ.pop(k, None)

        def setattr(self, obj, name, value):
            setattr(obj, name, value)

    failed = 0
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        with tempfile.TemporaryDirectory() as d:
            try:
                kwargs = {}
                params = inspect.signature(fn).parameters
                if "tmp_path" in params:
                    kwargs["tmp_path"] = Path(d)
                if "monkeypatch" in params:
                    kwargs["monkeypatch"] = _MP()
                fn(**kwargs)
                print(f"  ok - {fn.__name__}")
            except Exception as e:
                failed += 1
                print(f"  FAIL - {fn.__name__}: {e!r}")
    print(f"\ntest_entry_guard_pre_send.py: {len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
