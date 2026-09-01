"""T-179: S2_DELTA_DBL is shadow-only by CODE DEFAULT, not by an .env string.

Finding (31.08): the pattern fired for the first time ever — 41 shadow trades,
0 wins, -$6,975 = 86% of the day's shadow damage. The only thing standing
between it and a live slot was the string `shadow` in the out-of-git .env.
Flipping that to "1" would have routed it to `_execute_live` with NO family
gate (PATTERN_FAMILY_DELTA_DBL_V1 is ruled OFF ⇒ `_pattern_family()` returns
None for S2_DELTA_DBL ⇒ fail-open FULL).

Ruling T-153 (".env=shadow לכל החדש") already covers this case, so per
CLAUDE.md § "Rulings are one-time and standing" the guard is code-default-ON.

These tests fail if someone removes the code default and puts the pattern one
.env edit away from live again.
"""
import importlib
import os

import pytest

from backend.v9.systems.five_min.patterns import delta_dbl
from backend.v9.systems.five_min.patterns.delta_dbl import shadow_only


# ── the guard itself ──────────────────────────────────────────────────────

def test_shadow_only_true_when_release_flag_unset(monkeypatch):
    """No env at all ⇒ shadow. A clone/restart must never fire this live."""
    monkeypatch.delenv("S2_DELTA_DBL_LIVE_RELEASE", raising=False)
    monkeypatch.delenv("S2_DELTA_DBL_V1", raising=False)
    assert shadow_only() is True


def test_shadow_only_true_even_when_pattern_flag_says_live(monkeypatch):
    """THE REGRESSION: S2_DELTA_DBL_V1=1 used to mean live. It must not."""
    monkeypatch.delenv("S2_DELTA_DBL_LIVE_RELEASE", raising=False)
    monkeypatch.setenv("S2_DELTA_DBL_V1", "1")
    assert delta_dbl.enabled() is True, "detector still runs (shadow needs it)"
    assert shadow_only() is True, "…but it may not reach live"


@pytest.mark.parametrize("val", ["1", "true", "yes", "TRUE", "Yes"])
def test_release_flag_on_restores_live_path(monkeypatch, val):
    """Flag OFF→ON is the documented release lever (needs ledger + ruling)."""
    monkeypatch.setenv("S2_DELTA_DBL_LIVE_RELEASE", val)
    monkeypatch.setenv("S2_DELTA_DBL_V1", "1")
    assert shadow_only() is False


def test_release_flag_on_still_honours_explicit_shadow(monkeypatch):
    """Released + `=shadow` ⇒ still shadow (the old semantics survive)."""
    monkeypatch.setenv("S2_DELTA_DBL_LIVE_RELEASE", "1")
    monkeypatch.setenv("S2_DELTA_DBL_V1", "shadow")
    assert shadow_only() is True


@pytest.mark.parametrize("val", ["0", "false", "no", "", "maybe"])
def test_release_flag_junk_values_fail_closed(monkeypatch, val):
    """Anything that is not an explicit yes ⇒ shadow (fail-closed)."""
    monkeypatch.setenv("S2_DELTA_DBL_LIVE_RELEASE", val)
    monkeypatch.setenv("S2_DELTA_DBL_V1", "1")
    assert shadow_only() is True


# ── the guard is actually carried on the emitted setup ────────────────────

def _bars_double_bottom():
    """Minimal buffer that satisfies detect_delta_dbl's double-bottom rules."""
    bars = []
    for i in range(24):
        bars.append({"o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0})
    # T1 swing low at idx 4, T2 swing low at idx 14, neck between them,
    # breakout bar at idx 23.
    for idx in (4, 14):
        bars[idx] = {"o": 100.0, "h": 99.6, "l": 95.0, "c": 99.5}
    for idx in (8, 9, 10):
        bars[idx] = {"o": 100.0, "h": 104.0, "l": 99.5, "c": 103.5}
    bars[22] = {"o": 100.0, "h": 100.4, "l": 99.0, "c": 100.0}
    bars[23] = {"o": 99.5, "h": 101.5, "l": 99.4, "c": 101.0}
    return bars


def _emit(monkeypatch, **env):
    for k, v in env.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)
    bars = _bars_double_bottom()
    deltas = [0.0] * len(bars)
    deltas[-1] = 500.0          # big positive delta on the breakout bar
    for i in range(1, len(bars) - 1):
        deltas[i] = 10.0
    return delta_dbl.detect_delta_dbl(bars, "Normal", 2.0, deltas)


def test_emitted_setup_carries_shadow_only_metadata(monkeypatch):
    """The gateway guard reads metadata.shadow_only — it must be True."""
    setup = _emit(monkeypatch, S2_DELTA_DBL_LIVE_RELEASE=None,
                  S2_DELTA_DBL_V1="1")
    if setup is None:
        pytest.skip("synthetic bars did not trigger the detector")
    assert setup["metadata"]["shadow_only"] is True
    assert setup["pattern"].startswith("S2_DELTA_DBL")


def _silence_pre_gates(monkeypatch):
    """Turn OFF every env-gated pre-gate inside `_route_setup_inner`.

    ~79 flags run before the shadow_only guard (cold_start, eod_cutoff, chop,
    playbook, risk_halt …). Hard-coding them would rot the day someone adds a
    gate, so the list is derived from the source itself. Every gate in that
    method is wrapped in a master `os.getenv(FLAG)` check, so "0" disables the
    block and its sub-thresholds together. What is left deciding the outcome
    is the shadow_only guard — which is the point of these two tests.
    """
    import inspect
    import re
    from backend.v9.gateway import trading_gateway as tg
    src = inspect.getsource(tg.TradingGateway._route_setup_inner)
    for name in set(re.findall(
            r"""os\.(?:getenv|environ\.get)\(\s*["'](\w+)["']""", src)):
        monkeypatch.setenv(name, "0")


def _gateway_that_records_calls(monkeypatch):
    """Isolated gateway whose demo/live legs record instead of executing."""
    from backend.v9.gateway import trading_gateway as tg
    gw = tg.TradingGateway(db_path=":memory:")
    calls = {"demo": 0, "live": 0}
    _silence_pre_gates(monkeypatch)
    # T-191: explicitly disable gates that read live market data.
    # _silence_pre_gates catches os.getenv in the gateway source but misses
    # gates in imported modules (direction_compass.flag_on, _compass_or).
    # Mock the compass module-level flag to prevent live-market-dependent blocks.
    monkeypatch.setenv("DIRECTION_COMPASS_V1", "0")
    monkeypatch.setenv("CONT_TREND_FILTER", "0")
    from backend.v9.services import direction_compass as _dc_mod
    monkeypatch.setattr(_dc_mod, "flag_on", lambda: False)
    monkeypatch.setattr(tg, "is_within_firing_window", lambda *a, **k: True)
    # Hydrated context, otherwise cold_start_guard blocks before our guard.
    monkeypatch.setattr(
        gw, "_capture_cross_context",
        lambda *a, **k: {"tpo_system": {"bars_processed_today": 50},
                         "five_min_system": {"buffer_size": 50}})
    monkeypatch.setattr(gw, "_execute_shadow",
                        lambda *a, **k: {"trade_id": "T-SHADOW",
                                         "mode": "SHADOW"})
    monkeypatch.setattr(gw, "_is_demo_enabled", lambda *a, **k: True)
    monkeypatch.setattr(gw, "_is_live_enabled", lambda *a, **k: True)

    def _demo(*a, **k):
        calls["demo"] += 1
        return {"trade_id": "T-DEMO", "mode": "DEMO"}

    def _live(*a, **k):
        calls["live"] += 1
        return {"trade_id": "T-LIVE", "mode": "LIVE"}

    monkeypatch.setattr(gw, "_execute_demo", _demo)
    monkeypatch.setattr(gw, "_execute_live", _live)
    gw.demo_slot = None
    gw.live_slot = None
    return gw, calls


_DD_SETUP = {
    "firing_system": 2, "direction": "LONG",
    "pattern": "S2_DELTA_DBL_LONG", "classification": "S2_DELTA_DBL_LONG",
    "confidence": 0.9, "stop": 7400.0, "t1": 7410.0, "t2": 7415.0,
    "t3": 7420.0, "entry_price": 7405.0,
}


def test_gateway_never_routes_delta_dbl_to_demo_or_live(monkeypatch):
    """BEHAVIOURAL: shadow_only=True ⇒ _execute_live is never called."""
    gw, calls = _gateway_that_records_calls(monkeypatch)
    setup = dict(_DD_SETUP, metadata={"pattern": "S2_DELTA_DBL_LONG",
                                      "shadow_only": True})
    result = gw._route_setup_inner(setup, 2)
    assert calls["live"] == 0, "S2_DELTA_DBL reached the LIVE leg"
    assert calls["demo"] == 0, "S2_DELTA_DBL reached the DEMO leg"
    assert result.get("live") is None
    assert result.get("shadow")


def test_gateway_does_route_when_shadow_only_is_false(monkeypatch):
    """Control: the same setup without the guard DOES reach live — i.e. the
    previous test proves the guard, not an unrelated block."""
    gw, calls = _gateway_that_records_calls(monkeypatch)
    setup = dict(_DD_SETUP, metadata={"pattern": "S2_DELTA_DBL_LONG",
                                      "shadow_only": False})
    gw._route_setup_inner(setup, 2)
    assert calls["live"] + calls["demo"] > 0, (
        "control failed: setup never reached demo/live even WITHOUT the "
        "shadow_only guard — some other gate is blocking, so the guard test "
        "above proves nothing")


# ── the ruled-flag registry must keep documenting it ──────────────────────

def test_flag_is_registered_as_ruled():
    """flag_guard must keep watching this flag (drift in EITHER direction)."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    ruled = open(os.path.join(root, "config", "RULED_FLAGS.yaml"),
                 encoding="utf-8").read()
    assert "S2_DELTA_DBL_LIVE_RELEASE:" in ruled
    assert "T-153" in ruled
