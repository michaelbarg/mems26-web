"""A1 wrong-side veto × the 27.08 trend-day exemption — label source contract.

Ruling (מייקל 27.08, "תבטל דגלים הורסים"): on a PUBLISHED trend day the
wrong-side veto is exempt — a continuation entry at the session edge has ALL
structure behind it by construction. On a balance day the veto stays (the #655
saver, −$63.75).

Doctrine (מייקל 27.08 ~19:10): "היום יכול להשתנות תוך-כדי וזה בסדר — כל תווית
חדשה = סט-הזדמנויות חדש שנפתח מיד". Therefore the exemption keys on the label
PUBLISHED at fire time (trade_context.get_live_day_type — a STRING, T-109), and
only falls back to the detection-frozen day_type_at_entry when the live read is
unavailable. Live case pinned here: 27.08 20:10:05 — ZLR LONG vetoed with
day_type_at_entry=Variation two seconds AFTER Trend_Normal was promoted
(20:10:03 [S1-NEW-CLS] / [DayType] Classification changed).

Mutation contract:
  * balance day (live+snapshot both non-Trend)      -> veto holds
  * snapshot Trend, live unavailable (None)          -> exempt via fallback
  * snapshot Variation, live Trend_Normal (the 20:10 case) -> EXEMPT
  * snapshot Trend, live says Variation (downgrade)  -> veto restored
  * live read raises                                 -> fail-closed to snapshot
"""
from __future__ import annotations

import zoneinfo

import pytest

from backend.v9.gateway import trading_gateway as tg
from backend.v9.services import trade_context as tc

# The 08-14 11:50 ET ZLR SHORT @7800.75 geometry (the archived SAVER): a short
# at the session low — every structural level ABOVE it => all_wrong_side.
ENTRY = 7800.75
STOP = ENTRY + 4.5
TPO_VARIATION = {
    "ib_high": 7840.0, "ib_low": 7820.0, "poc": 7830.0,
    "vah": 7835.0, "val": 7825.0, "ib_width": 20.0,
}

_EXTERNAL_GATE_FLAGS = (
    "RELEASE_ENTRY_GATE_V1", "NEWS_BLACKOUT_V1", "S2_ADAPTIVE_THRESHOLDS_V1",
    "OPENING_WINDOW_FIRE_V1", "PATTERN_LOSS_BREAKER_V1", "EXTREME_CHASE_GUARD",
    "DIRECTION_COMPASS_V1", "LIVE_EXECUTION_V1", "LIVE_TRADING_ARMED",
)
_UNDER_TEST = (
    "DAYTYPE_TARGETS_STRUCTURAL", "STRUCTURAL_TARGETS_WRONG_SIDE_VETO_V1",
)


class _TZBoom:
    def __init__(self, *a, **k):
        raise RuntimeError("test: force IB-locked fail-open")


def _isolate_gates(monkeypatch):
    import inspect
    import re
    src = inspect.getsource(tg)
    found = set(re.findall(r'os\.getenv\(\s*"([A-Z0-9_]+)"\s*,\s*"0"\s*\)', src))
    for flag in sorted(found | set(_EXTERNAL_GATE_FLAGS)):
        if flag in _UNDER_TEST:
            continue
        monkeypatch.setenv(flag, "0")
    from backend.v9.services import feed_watchdog as _fw
    from backend.v9.services import kill_switch as _ks
    monkeypatch.setattr(_fw, "is_feed_alive", lambda *a, **k: (True, "test"))
    monkeypatch.setattr(_ks, "is_engaged", lambda *a, **k: (False, None))


def _gw(monkeypatch, snapshot_dt, live_dt):
    """Gateway with day_type_at_entry=snapshot_dt and a published live label
    of live_dt (None => unavailable; Exception instance => the read raises)."""
    _isolate_gates(monkeypatch)
    monkeypatch.setenv("DAYTYPE_TARGETS_STRUCTURAL", "1")
    monkeypatch.setenv("STRUCTURAL_TARGETS_WRONG_SIDE_VETO_V1", "1")
    monkeypatch.setattr(zoneinfo, "ZoneInfo", _TZBoom)
    monkeypatch.setattr(tg, "is_within_firing_window", lambda: True)
    monkeypatch.setattr(
        tg, "extract_g1_entry_context",
        lambda cc: {"day_type_at_entry": snapshot_dt})
    monkeypatch.setattr(tg, "resolve_pattern_id", lambda setup, g1: "ZLR")
    if isinstance(live_dt, Exception):
        def _boom():
            raise live_dt
        monkeypatch.setattr(tc, "get_live_day_type", _boom)
    else:
        monkeypatch.setattr(tc, "get_live_day_type", lambda: live_dt)
    gw = tg.TradingGateway()
    monkeypatch.setattr(gw, "_execute_shadow", lambda *a, **k: {"trade_id": "t"})
    monkeypatch.setattr(
        gw, "_capture_cross_context",
        lambda: {
            "day_type_machine": {"day_type": snapshot_dt},
            "woodies_system": {"trend_state": "GREEN"},
            "tpo_system": dict(TPO_VARIATION),
        },
    )
    return gw


def _setup():
    return {
        "firing_system": 4,
        "direction": "SHORT",
        "classification": "ZLR",
        "entry_price": ENTRY,
        "stop": STOP,
        "t1": ENTRY - 6.0,
        "metadata": {"pattern": "ZLR"},
    }


def _route(gw):
    return gw.route_setup(_setup(), 4)


# ─────────────────────────── the veto is real ────────────────────────────────

def test_balance_day_veto_holds(monkeypatch):
    """Mutation guard: live+snapshot both Variation — the #655 saver stands."""
    gw = _gw(monkeypatch, snapshot_dt="Variation", live_dt="Variation")
    res = _route(gw)
    assert res.get("blocked_by") == "structural_targets_wrong_side", res


def test_normal_day_veto_holds(monkeypatch):
    gw = _gw(monkeypatch, snapshot_dt="Normal", live_dt="Normal")
    assert _route(gw).get("blocked_by") == "structural_targets_wrong_side"


# ─────────────────────── the trend-day exemption ─────────────────────────────

@pytest.mark.parametrize("trend", ["Trend_Normal", "Trend_DD"])
def test_published_trend_day_exempts(monkeypatch, trend):
    """Live published label is Trend_* -> continuation objective, no veto."""
    gw = _gw(monkeypatch, snapshot_dt=trend, live_dt=trend)
    res = _route(gw)
    assert res.get("blocked_by") is None, (
        "trend-day exemption (ruling 27.08) is dead: %s / %s"
        % (res.get("blocked_by"), res.get("reason")))


def test_the_2010_case_live_label_wins_over_stale_snapshot(monkeypatch):
    """27.08 20:10:05 — the candidate carried day_type_at_entry=Variation, but
    Trend_Normal had been PUBLISHED at 20:10:03. Doctrine: the new label opens
    its opportunity set immediately -> the exemption must fire."""
    gw = _gw(monkeypatch, snapshot_dt="Variation", live_dt="Trend_Normal")
    res = _route(gw)
    assert res.get("blocked_by") is None, (
        "the published label did not win over the detection snapshot: %s" % res)


def test_downgrade_restores_the_veto(monkeypatch):
    """Symmetric doctrine: published label says the trend is GONE -> the
    balance-day protection is back, even if the snapshot still says Trend.

    The structural resolver is pinned here because under a Trend snapshot it
    legitimately produces continuation targets (not all_wrong_side), which
    would make the branch unreachable — this test is about the LABEL CHOICE,
    not the trend-day geometry."""
    from backend.v9.systems import structural_targets as st_mod
    monkeypatch.setattr(
        st_mod, "resolve_structural_targets",
        lambda **k: {"all_wrong_side": True, "t1_price": ENTRY + 4.5,
                     "t2_price": ENTRY + 9.0, "t3_price": ENTRY + 13.5,
                     "day_type": k.get("day_type")})
    gw = _gw(monkeypatch, snapshot_dt="Trend_Normal", live_dt="Variation")
    assert _route(gw).get("blocked_by") == "structural_targets_wrong_side"


# ─────────────────────────── fail-closed fallback ────────────────────────────

def test_live_unavailable_falls_back_to_snapshot_trend(monkeypatch):
    gw = _gw(monkeypatch, snapshot_dt="Trend_DD", live_dt=None)
    assert _route(gw).get("blocked_by") is None


def test_live_unavailable_falls_back_to_snapshot_balance(monkeypatch):
    gw = _gw(monkeypatch, snapshot_dt="Variation", live_dt=None)
    assert _route(gw).get("blocked_by") == "structural_targets_wrong_side"


def test_live_read_raising_is_fail_closed_to_snapshot(monkeypatch):
    gw = _gw(monkeypatch, snapshot_dt="Variation",
             live_dt=RuntimeError("live read down"))
    assert _route(gw).get("blocked_by") == "structural_targets_wrong_side"


@pytest.mark.parametrize("junk", ["UNKNOWN", "FORMING", "None", ""])
def test_junk_live_values_do_not_override(monkeypatch, junk):
    gw = _gw(monkeypatch, snapshot_dt="Variation", live_dt=junk)
    assert _route(gw).get("blocked_by") == "structural_targets_wrong_side"


def test_exempt_is_loud_and_countable(monkeypatch, caplog):
    import logging
    gw = _gw(monkeypatch, snapshot_dt="Variation", live_dt="Trend_Normal")
    with caplog.at_level(logging.WARNING,
                         logger="backend.v9.gateway.trading_gateway"):
        res = _route(gw)
    assert res.get("blocked_by") is None
    hits = [r for r in caplog.records
            if "wrong-side veto EXEMPT" in r.getMessage()]
    assert len(hits) == 1, "expected exactly one countable EXEMPT WARNING"
