"""Guards against the 07-17 v9_bars_5min contamination class.

Finding: docs/handoff/FINDING_BARS5MIN_CONTAMINATION_2026-07-18.md
Two layers, both pinned here:
  1. _hour_shift_fix tightened — a NOMADIC source-lag (age drifts 3610s→3897s)
     must NOT be treated as a TZ offset (which is a CONSTANT ~3600s).
  2. _contradicts_woodies — a v9_bars_5min bar > band off the same-ts woodies
     row is rejected loudly, not written silently. Fail-open on absence.

Also pins that the live stop/size ATR path already reads the CLEAN woodies
table (it does — this is a guard against a future regression that would point
it back at the contaminated table).
"""
import importlib
from datetime import datetime, timedelta, timezone

import backend.v9.api.v9.bars as bars


def _payload(newest_age_sec: float, n: int = 3):
    """A push whose NEWEST bar sits `newest_age_sec` behind now."""
    now = datetime.now(timezone.utc).timestamp()
    newest = now - newest_age_sec
    return [{"ts": newest - 300 * (n - 1 - i)} for i in range(n)]


# ── Layer 1: TS-HOUR tighten ────────────────────────────────────────────────

def test_tzoffset_exactly_1h_is_still_fixed(monkeypatch):
    """A TRUE chartbook-TZ offset (~exactly 3600s) must still be corrected."""
    monkeypatch.delenv("WOODIES_TS_HOUR_FIX", raising=False)
    monkeypatch.delenv("TS_HOUR_FIX_TOL_SEC", raising=False)
    p = _payload(3600.0)
    before = [b["ts"] for b in p]
    shift = bars._hour_shift_fix(p, "test")
    assert shift == 3600
    assert [b["ts"] for b in p] == [t + 3600.0 for t in before]


def test_nomadic_drift_is_NOT_shifted(monkeypatch):
    """The 07-17 injector: newest bar 3897s old (drifted, stale) is in the OLD
    wide [3300,3900] band but OUTSIDE 3600±120 → must NOT shift (would stamp a
    stale bar at a current ts)."""
    monkeypatch.delenv("WOODIES_TS_HOUR_FIX", raising=False)
    monkeypatch.delenv("TS_HOUR_FIX_TOL_SEC", raising=False)
    for age in (3750.0, 3897.0, 3450.0):
        p = _payload(age)
        before = [b["ts"] for b in p]
        shift = bars._hour_shift_fix(p, "test")
        assert shift == 0, f"age={age} should not shift"
        assert [b["ts"] for b in p] == before, f"age={age} bars must be untouched"


def test_killswitch_off(monkeypatch):
    monkeypatch.setenv("WOODIES_TS_HOUR_FIX", "0")
    p = _payload(3600.0)
    before = [b["ts"] for b in p]
    assert bars._hour_shift_fix(p, "test") == 0
    assert [b["ts"] for b in p] == before


# ── Layer 2: cross-source guard ─────────────────────────────────────────────

def _fake_woodies(close):
    def _read_one(sql, params):
        return {"high": close + 2, "low": close - 2, "close": close}
    return _read_one


def test_ghost_bar_rejected(monkeypatch):
    """The 07-17 case: v9_bars_5min close 7535.5 vs woodies 7508.25 (dev 27.25
    > 15pt band) → rejected."""
    monkeypatch.setattr("backend.v9.db.read.read_one", _fake_woodies(7508.25))
    ts = datetime.now(timezone.utc)
    reason = bars._contradicts_woodies(ts, 7538.0, 7530.0, 7535.5, "MES")
    assert reason is not None and "contradicts_woodies" in reason


def test_normal_bar_passes(monkeypatch):
    """A price within band of woodies is fine."""
    monkeypatch.setattr("backend.v9.db.read.read_one", _fake_woodies(7508.25))
    ts = datetime.now(timezone.utc)
    assert bars._contradicts_woodies(ts, 7511.0, 7506.0, 7509.0, "MES") is None


def test_fail_open_when_no_woodies_row(monkeypatch):
    """Never reject on ABSENCE (bar-boundary race) — only on a proven contradiction."""
    monkeypatch.setattr("backend.v9.db.read.read_one", lambda sql, params: None)
    ts = datetime.now(timezone.utc)
    assert bars._contradicts_woodies(ts, 9999.0, 9990.0, 9995.0, "MES") is None


def test_guard_never_raises(monkeypatch):
    def _boom(sql, params):
        raise RuntimeError("db down")
    monkeypatch.setattr("backend.v9.db.read.read_one", _boom)
    ts = datetime.now(timezone.utc)
    # must swallow and fail-open
    assert bars._contradicts_woodies(ts, 1.0, 1.0, 1.0, "MES") is None


# ── Pin: live ATR path uses the CLEAN table ─────────────────────────────────

def test_gateway_atr_reads_woodies_not_contaminated_table():
    """The stop/size ATR queries in the gateway must read v9_bars_5min_woodies.
    Regression guard: if someone repoints them at v9_bars_5min they inherit the
    contamination that poisons stop size + risk caps."""
    import backend.v9.gateway.trading_gateway as tg
    src = __import__("inspect").getsource(tg)
    # every ATR/stop bar-read in the gateway is the woodies table
    assert 'FROM v9_bars_5min_woodies' in src
    # and there is NO bare contaminated-table read feeding those paths
    import re
    bare = re.findall(r'FROM v9_bars_5min\b(?!_woodies)', src)
    assert not bare, f"gateway must not read the contaminated table for ATR/stops: {bare}"
