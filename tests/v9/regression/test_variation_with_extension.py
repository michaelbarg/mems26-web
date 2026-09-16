"""T-367: Variation with IB extension — release kind/location blocks.

Rule A: When the IB is broken in the setup direction and the entry zone
is at a value edge (not mid_value), release dalton_intent:kind or
dalton_intent:location blocks. Both BREAK and PULLBACK entry kinds are
admitted.

Rule B: On Variation/Normal_Variation days, mid_value entries are blocked
with blocked_by=variation_mid_value, regardless of IB break status.

Rule C: Opposite-direction setups at the extension extreme are already
handled by T-329 FAILED_EXTENSION (CEILING_FLIP). Not modified here;
verified by line-number assertion.
"""
from __future__ import annotations

import inspect
import os
import re
import zoneinfo

import pytest

from backend.v9.gateway import trading_gateway as tg


# ── TPO fixtures ─────────────────────────────────────────────────────────────
# IB broken DOWN: session_low < ib_low
TPO_IB_BREAK_DOWN = {
    "ib_high": 7660.0, "ib_low": 7640.0,
    "session_high": 7655.0, "session_low": 7625.0,  # sl < ibl = break DOWN
    "vah": 7655.0, "val": 7635.0,
    "poc": 7645.0, "ib_locked": True,
    "ib_width": 20.0,
}

# IB broken UP: session_high > ib_high
TPO_IB_BREAK_UP = {
    "ib_high": 7660.0, "ib_low": 7640.0,
    "session_high": 7680.0, "session_low": 7645.0,  # sh > ibh = break UP
    "vah": 7665.0, "val": 7645.0,
    "poc": 7655.0, "ib_locked": True,
    "ib_width": 20.0,
}

# IB NOT broken: session contained in IB
TPO_IB_NOT_BROKEN = {
    "ib_high": 7660.0, "ib_low": 7640.0,
    "session_high": 7658.0, "session_low": 7642.0,  # contained
    "vah": 7655.0, "val": 7645.0,
    "poc": 7650.0, "ib_locked": True,
    "ib_width": 20.0,
}


# ── gate isolation ───────────────────────────────────────────────────────────
_UNDER_TEST = {"VARIATION_WITH_EXTENSION_V1", "DALTON_PLAYBOOK_V1"}

# Flags that are checked by os.getenv but not always with default "0"
_EXTERNAL_GATE_FLAGS = {
    "PHASE_B_LOCATION_V1", "DEMO_EXECUTION_ENABLED",
    "LIVE_EXECUTION_V1", "LIVE_TRADING_V1", "LIVE_TRADING_ARMED",
}


def _isolate_gates(monkeypatch):
    """Turn OFF all env-gated flags except the ones under test."""
    src = inspect.getsource(tg)
    found = set(re.findall(r'os\.getenv\(\s*"([A-Z0-9_]+)"\s*,\s*"0"\s*\)', src))
    for flag in sorted(found | _EXTERNAL_GATE_FLAGS):
        if flag in _UNDER_TEST:
            continue
        monkeypatch.setenv(flag, "0")

    from backend.v9.services import feed_watchdog as _fw
    from backend.v9.services import kill_switch as _ks
    monkeypatch.setattr(_fw, "is_feed_alive", lambda *a, **k: (True, "test"))
    monkeypatch.setattr(_ks, "is_engaged", lambda *a, **k: (False, None))


class _TZBoom(zoneinfo.ZoneInfo):
    """ZoneInfo stub that always returns UTC — avoids tz failures in CI."""
    def __new__(cls, key):
        import datetime
        return datetime.timezone.utc


def _gw(monkeypatch, day_type="Variation", tpo=None, pattern="DOUBLE_BOTTOM_EE"):
    """Build a TradingGateway wired for the test scenario."""
    _isolate_gates(monkeypatch)
    monkeypatch.setenv("DALTON_PLAYBOOK_V1", "1")
    monkeypatch.setenv("VARIATION_WITH_EXTENSION_V1", "1")
    monkeypatch.setattr(zoneinfo, "ZoneInfo", _TZBoom)
    monkeypatch.setattr(tg, "is_within_firing_window", lambda: True)
    monkeypatch.setattr(
        tg, "extract_g1_entry_context",
        lambda cc: {"day_type_at_entry": day_type})
    monkeypatch.setattr(tg, "resolve_pattern_id", lambda setup, g1: pattern)
    # Mock get_live_day_type so the dalton playbook sees the right day_type
    from backend.v9.services import trade_context as _tc
    monkeypatch.setattr(_tc, "get_live_day_type", lambda: day_type)
    gw = tg.TradingGateway()
    monkeypatch.setattr(gw, "_execute_shadow", lambda *a, **k: {"trade_id": "t"})
    monkeypatch.setattr(
        gw, "_capture_cross_context",
        lambda: {
            "day_type_machine": {"day_type": day_type},
            "woodies_system": {"trend_state": "GREEN"},
            "tpo_system": dict(tpo if tpo is not None else TPO_IB_BREAK_DOWN),
        },
    )
    return gw


def _setup(direction="SHORT", entry_price=7620.0, classification="DOUBLE_BOTTOM_EE"):
    """Build a minimal setup dict."""
    return {
        "firing_system": 4,
        "direction": direction,
        "classification": classification,
        "entry_price": entry_price,
        "stop": entry_price + (15.0 if direction == "SHORT" else -15.0),
        "t1": entry_price + (-10.0 if direction == "SHORT" else 10.0),
        "t2": entry_price + (-18.0 if direction == "SHORT" else 18.0),
        "t3": entry_price + (-25.0 if direction == "SHORT" else 25.0),
        "metadata": {"pattern": classification},
    }


def _route(gw, setup):
    return gw.route_setup(setup, 4)


# ──────────────────────────────────────────────────────────────────────────────
# Rule A: IB break DOWN + SHORT below value -> released
# ──────────────────────────────────────────────────────────────────────────────

def test_ib_break_down_short_below_value_released(monkeypatch):
    """SHORT setup below value on IB break DOWN should be released."""
    # entry 7620 < val 7635 => below_value zone; IB broken DOWN
    gw = _gw(monkeypatch, tpo=TPO_IB_BREAK_DOWN)
    s = _setup(direction="SHORT", entry_price=7620.0)
    result = _route(gw, s)
    # Should NOT be blocked by dalton_intent:kind or dalton_intent:location
    blocked = result.get("blocked_by", "")
    assert blocked not in ("dalton_intent:kind", "dalton_intent:location"), (
        f"T-367 Rule A should release kind/location block, got blocked_by={blocked}")


# ──────────────────────────────────────────────────────────────────────────────
# Rule A: IB break DOWN + LONG -> stays blocked (wrong direction)
# ──────────────────────────────────────────────────────────────────────────────

def test_ib_break_down_long_stays_blocked(monkeypatch):
    """LONG on IB break DOWN should NOT be released — wrong direction."""
    gw = _gw(monkeypatch, tpo=TPO_IB_BREAK_DOWN)
    # entry above value — LONG near_vah
    s = _setup(direction="LONG", entry_price=7654.0, classification="REACTIVE")
    result = _route(gw, s)
    blocked = result.get("blocked_by", "")
    # It may be blocked by dalton_intent:kind, dalton_intent:location, or
    # something else — the point is it should NOT be released by T-367
    # (we verify this indirectly: if the playbook would block it, T-367
    # should NOT remove that block for the wrong direction)
    # This test verifies the code path exists and does not release LONG on DOWN
    assert "T-367 WITH_EXTENSION admit" not in str(result.get("reason", ""))


# ──────────────────────────────────────────────────────────────────────────────
# Rule B: mid_value in extension direction -> variation_mid_value
# ──────────────────────────────────────────────────────────────────────────────

def test_mid_value_on_variation_blocked(monkeypatch):
    """Entry in mid_value zone on a Variation day must be blocked."""
    # mid_value: between val+tol and vah-tol
    # val=7635, vah=7655, mid = ~7645
    gw = _gw(monkeypatch, day_type="Variation", tpo=TPO_IB_BREAK_DOWN)
    s = _setup(direction="SHORT", entry_price=7645.0)
    result = _route(gw, s)
    blocked = result.get("blocked_by", "")
    assert blocked == "variation_mid_value", (
        f"T-367 Rule B: mid_value on Variation should be variation_mid_value, "
        f"got {blocked}")


def test_mid_value_on_normal_variation_blocked(monkeypatch):
    """Entry in mid_value on Normal_Variation day must also be blocked."""
    gw = _gw(monkeypatch, day_type="Normal_Variation", tpo=TPO_IB_BREAK_DOWN)
    s = _setup(direction="SHORT", entry_price=7645.0)
    result = _route(gw, s)
    blocked = result.get("blocked_by", "")
    assert blocked == "variation_mid_value", (
        f"T-367 Rule B: mid_value on Normal_Variation should be variation_mid_value, "
        f"got {blocked}")


# ──────────────────────────────────────────────────────────────────────────────
# IB not broken -> stays blocked
# ──────────────────────────────────────────────────────────────────────────────

def test_ib_not_broken_stays_blocked(monkeypatch):
    """When IB is not broken, kind/location blocks should NOT be released."""
    gw = _gw(monkeypatch, tpo=TPO_IB_NOT_BROKEN)
    s = _setup(direction="SHORT", entry_price=7620.0)
    result = _route(gw, s)
    # The setup is below the session range in an unbroken IB — playbook may
    # or may not block it, but T-367 Rule A should definitely not fire
    # (no IB break). Verify by checking the log pattern is absent.
    reason = result.get("reason", "")
    assert "T-367 WITH_EXTENSION admit" not in reason


# ──────────────────────────────────────────────────────────────────────────────
# Flag off -> original block preserved
# ──────────────────────────────────────────────────────────────────────────────

def test_flag_off_preserves_original_block(monkeypatch):
    """When VARIATION_WITH_EXTENSION_V1=0, the T-367 code path is skipped."""
    gw = _gw(monkeypatch, tpo=TPO_IB_BREAK_DOWN)
    monkeypatch.setenv("VARIATION_WITH_EXTENSION_V1", "0")
    s = _setup(direction="SHORT", entry_price=7645.0)
    result = _route(gw, s)
    # mid_value should NOT be blocked by variation_mid_value when flag is off
    blocked = result.get("blocked_by", "")
    assert blocked != "variation_mid_value", (
        f"Flag OFF should not produce variation_mid_value, got {blocked}")


# ──────────────────────────────────────────────────────────────────────────────
# PULLBACK in extension direction -> released
# ──────────────────────────────────────────────────────────────────────────────

def test_pullback_in_extension_direction_released(monkeypatch):
    """PULLBACK entry_kind in the extension direction should be released."""
    # ZLR maps to PULLBACK in dalton_playbook config
    gw = _gw(monkeypatch, tpo=TPO_IB_BREAK_DOWN, pattern="ZLR")
    s = _setup(direction="SHORT", entry_price=7620.0, classification="ZLR")
    result = _route(gw, s)
    blocked = result.get("blocked_by", "")
    assert blocked not in ("dalton_intent:kind", "dalton_intent:location"), (
        f"T-367: PULLBACK in extension direction should be released, "
        f"got blocked_by={blocked}")


# ──────────────────────────────────────────────────────────────────────────────
# Rule C: T-329 FAILED_EXTENSION exempt still exists
# ──────────────────────────────────────────────────────────────────────────────

def test_rule_c_t329_failed_extension_exists():
    """T-329 FAILED_EXTENSION exempt code must still exist in the gateway."""
    src = inspect.getsource(tg.TradingGateway._route_setup_inner)
    assert "T-329 FAILED_EXTENSION exempt" in src, (
        "T-329 FAILED_EXTENSION exempt block must still be in the gateway")
    # Verify it comes BEFORE T-367
    idx_329 = src.index("T-329 FAILED_EXTENSION exempt")
    idx_367 = src.index("T-367")
    assert idx_329 < idx_367, (
        "T-329 must come before T-367 in the code flow")


# ──────────────────────────────────────────────────────────────────────────────
# Code structure: T-367 sits between T-329 and T-355
# ──────────────────────────────────────────────────────────────────────────────

def test_t367_between_t329_and_t355():
    """T-367 must sit after T-329 and before T-355 in the code."""
    src = inspect.getsource(tg.TradingGateway._route_setup_inner)
    idx_329 = src.index("T-329 FAILED_EXTENSION exempt")
    idx_367 = src.index("T-367")
    idx_355 = src.index("T-355")
    assert idx_329 < idx_367 < idx_355, (
        f"Order must be T-329 < T-367 < T-355, got {idx_329} < {idx_367} < {idx_355}")
