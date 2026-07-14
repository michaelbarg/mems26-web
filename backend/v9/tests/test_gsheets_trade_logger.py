"""Tests for the real-time Google-Sheets LIVE-trade logger.

Anti-tautological: every case proves the logger (a) is a no-op unless flag+url are
set, (b) maps a Sierra `LedgerTrade` to the right columns, (c) can NEVER raise on a
Sheets outage, and (d) skips non-live (shadow/demo) trades — i.e. it cannot stall or
crash the trading loop and only records real Sierra-executed LIVE trades.

Runnable standalone (`python3 test_gsheets_trade_logger.py`) or via pytest — loads
the modules by path like test_sierra_ledger.py, so it needs no package import chain.
"""
import importlib.util
import json
import os
import tempfile
import urllib.error

_HERE = os.path.dirname(os.path.abspath(__file__))
_SERVICES = os.path.abspath(os.path.join(_HERE, "..", "services"))


def _load(mod_name, filename):
    path = os.path.join(_SERVICES, filename)
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[mod_name] = mod  # so dataclasses can resolve annotations
    spec.loader.exec_module(mod)
    return mod


gs = _load("gsheets_trade_logger", "gsheets_trade_logger.py")
sl = _load("sierra_ledger", "sierra_ledger.py")


# --------------------------------------------------------------- utilities

class _Recorder:
    def __init__(self):
        self.calls = []

    def __call__(self, url, row, **kw):
        self.calls.append((url, row))
        return True


class _EnvPatch:
    """Set/restore env vars around a block (works under pytest or standalone)."""
    def __init__(self, **kw):
        self._kw = kw
        self._orig = {}

    def __enter__(self):
        for k, v in self._kw.items():
            self._orig[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return self

    def __exit__(self, *a):
        for k, v in self._orig.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _short_trade():
    """A SHORT LIVE trade reconstructed from Sierra fills alone (entry+T1+STOP)."""
    fills = [json.dumps(r) for r in [
        {"kind": "ENTRY", "order_id": 8600, "price": 7536.25, "ts": 1,
         "contracts": 2, "account": "37138283"},
        {"kind": "T1", "order_id": 8600, "price": 7522.0, "ts": 2, "contracts": 1,
         "account": "37138283"},
        {"kind": "STOP", "order_id": 8600, "price": 7524.0, "ts": 3, "contracts": 1,
         "account": "37138283"},
    ]]
    return sl.build_ledger(sl.parse_fills(fills), point_value=5.0)[0]


# ------------------------------------------------------------------- tests

# (a) Flag OFF → the logger is a complete no-op; push is never attempted.
def test_flag_off_is_noop():
    rec = _Recorder()
    orig = gs.push_row
    gs.push_row = rec
    try:
        with _EnvPatch(GSHEETS_TRADE_LOG=None, GSHEETS_TRADE_LOG_URL=None):
            assert gs.is_enabled() is False
            dispatched = gs.log_live_fill(
                fill={"kind": "ENTRY", "order_id": 8600, "price": 7536.25, "ts": 1},
                mode="live", block=True)
            assert dispatched is False
        assert rec.calls == [], "flag OFF must never push"
    finally:
        gs.push_row = orig
    # And push_row itself no-ops on an empty url (never raises).
    assert gs.push_row("", {"a": 1}) is False


# (b) format_trade_row maps a Sierra LedgerTrade to the documented columns.
def test_format_trade_row_columns():
    lt = _short_trade()
    row = gs.format_trade_row(lt, fill_kind="t1", mode="live")

    # exact column set + order == the Apps Script header row
    assert list(row.keys()) == list(gs.ROW_COLUMNS)

    assert row["entry_order_id"] == 8600          # idempotency key
    assert row["fill_kind"] == "T1"               # current triggering fill
    assert row["direction"] == "SHORT"            # inferred from Sierra fills
    assert row["entry"] == 7536.25
    assert row["contracts"] == 2
    assert row["t1"] == 7522.0
    assert row["t2"] is None and row["t3"] is None
    assert row["stop"] == 7524.0
    assert row["exit"] == 7524.0                  # last Sierra fill price
    assert row["realized_pnl"] == 132.5           # (14.25 + 12.25) * 5
    assert row["closed"] is True
    assert row["account"] == "37138283"
    assert row["source"] == "sierra"              # never backend-synthesized
    assert row["manual_tag"] == ""                # no FLATTEN → system-managed
    assert row["ts"].startswith("1970-01-01")     # entry_ts=1 → ISO UTC


# (b2) A Sierra FLATTEN (opposite/operator close) is tagged MANUAL from fills alone.
def test_manual_tag_from_flatten():
    fills = [json.dumps(r) for r in [
        {"kind": "ENTRY", "order_id": 9000, "price": 7540.0, "ts": 1, "contracts": 2},
        {"kind": "FLATTEN", "order_id": 9000, "price": 7538.5, "ts": 2},
    ]]
    lt = sl.build_ledger(sl.parse_fills(fills))[0]
    row = gs.format_trade_row(lt, fill_kind="FLATTEN")
    assert row["manual_tag"] == "MANUAL"
    assert row["exit"] == 7538.5


# (c) push_row swallows a connection error and returns False — never raises.
def test_push_row_swallows_connection_error():
    def _boom(*a, **k):
        raise urllib.error.URLError("connection refused (test)")

    orig = urllib.request.urlopen
    urllib.request.urlopen = _boom
    try:
        result = gs.push_row("http://127.0.0.1:9/unreachable", {"entry_order_id": 1})
        assert result is False, "a broken endpoint must return False, not raise"
    finally:
        urllib.request.urlopen = orig


# (c2) push_row happy path returns True on a 200 (proves the POST is wired).
def test_push_row_success_path():
    captured = {}

    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"OK"

        def getcode(self):
            return 200

    def _fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["ctype"] = req.headers.get("Content-type")
        return _Resp()

    orig = urllib.request.urlopen
    urllib.request.urlopen = _fake_urlopen
    try:
        ok = gs.push_row("https://script.google.com/exec", {"entry_order_id": 42})
        assert ok is True
        assert captured["url"] == "https://script.google.com/exec"
        assert captured["body"] == {"entry_order_id": 42}
        assert captured["ctype"] == "application/json"
    finally:
        urllib.request.urlopen = orig


# (d) A shadow/demo trade is skipped even when flag+url are ON.
def test_shadow_and_demo_skipped():
    rec = _Recorder()
    orig = gs.push_row
    gs.push_row = rec
    try:
        with _EnvPatch(GSHEETS_TRADE_LOG="1",
                       GSHEETS_TRADE_LOG_URL="https://script.google.com/exec"):
            assert gs.is_enabled() is True
            for m in ("shadow", "demo", "SIM"):
                out = gs.log_live_fill(
                    fill={"kind": "ENTRY", "order_id": 8600, "price": 7536.25, "ts": 1},
                    mode=m, block=True)
                assert out is False, f"mode={m} must be skipped"
        assert rec.calls == [], "non-live modes must never push"
    finally:
        gs.push_row = orig


# (d2) A LIVE fill DOES dispatch a Sierra-sourced row (end-to-end, block=True).
def test_live_fill_dispatches_sierra_row():
    rec = _Recorder()
    orig = gs.push_row
    gs.push_row = rec
    # durable Sierra journal with an ENTRY + T1 for a live trade
    with tempfile.TemporaryDirectory() as d:
        journal = os.path.join(d, "trade_fills_journal.jsonl")
        with open(journal, "w", encoding="utf-8") as f:
            f.write(json.dumps({"kind": "ENTRY", "order_id": 8600, "price": 7536.25,
                                "ts": 1, "contracts": 2, "account": "37138283"}) + "\n")
            f.write(json.dumps({"kind": "T1", "order_id": 8600, "price": 7522.0,
                                "ts": 2, "contracts": 1, "account": "37138283"}) + "\n")
        try:
            with _EnvPatch(GSHEETS_TRADE_LOG="1",
                           GSHEETS_TRADE_LOG_URL="https://script.google.com/exec",
                           TRADE_FILLS_PATH=os.path.join(d, "trade_fills.json"),
                           SIERRA_LIVE_ACCOUNT=None):
                dispatched = gs.log_live_fill(
                    fill={"kind": "T1", "order_id": 8600, "price": 7522.0, "ts": 2},
                    mode="live", entry_order_id=8600, journal_path=journal, block=True)
                assert dispatched is True
            assert len(rec.calls) == 1, "one live fill → one push"
            url, row = rec.calls[0]
            assert url == "https://script.google.com/exec"
            assert row["entry_order_id"] == 8600      # reconstructed from Sierra
            assert row["direction"] == "SHORT"
            assert row["entry"] == 7536.25
            assert row["t1"] == 7522.0
            assert row["fill_kind"] == "T1"
            assert row["source"] == "sierra"
        finally:
            gs.push_row = orig


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in tests:
        fn()
        passed += 1
        print(f"  ok - {fn.__name__}")
    print(f"\ntest_gsheets_trade_logger.py: {passed}/{len(tests)} passed")
