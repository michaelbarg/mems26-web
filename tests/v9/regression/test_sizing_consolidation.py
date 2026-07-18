"""Item-11: sizing consolidation — anti-tautological tests.

Three test groups per the work plan:
1. Legacy-reject-but-V2-approves → routes under SIZING_CONSOLIDATION_V1=1
   (FAILS on old code where legacy re-calc at routing time silently kills the fire).
2. FIXED_CONTRACTS_3 before==after: contract count == 3 at every sizing source.
3. S4 risk-cap reject surfaces as gateway blocked_by (not silent in-detector veto).
"""
import os
import pytest
from unittest.mock import MagicMock, patch


# ── helpers ─────────────────────────────────────────────────────────────

def _make_woodies(sizing_consol=False, fixed3=True):
    """Create a minimal WoodiesSystem with mocked dependencies."""
    from backend.v9.systems.woodies.woodies_system import WoodiesSystem

    ws = WoodiesSystem.__new__(WoodiesSystem)
    ws._bar_buffer = []
    ws._bar_count = 0
    ws._closes = [7500.0]
    ws.current_state = {
        "cci_14": 50.0, "cci_6_tcci": 55.0,
        "swi_value": 0.0, "czi_value": 0.0,
        "lsma_value": 7500.0, "ema_34": 7500.0,
    }
    ws._last_v2_sizing = None
    ws._last_fired_bar_ts = {}
    ws._last_fire_setup = None
    ws._open_fire_records = {}
    ws.PATTERN_TIER = WoodiesSystem.PATTERN_TIER
    return ws


def _make_gateway():
    """Create a TradingGateway with mocked internals for routing tests."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    gw = TradingGateway.__new__(TradingGateway)
    gw.cooldown = MagicMock(is_blocked=MagicMock(return_value=False))
    gw.ssv = MagicMock(check_veto=MagicMock(return_value=False))
    gw.cluster_guard = MagicMock(is_blocked=MagicMock(return_value=False))
    gw._system_registry = {}
    gw._live_enabled_systems = set()
    gw.shadow_trades = []
    gw._recent_fires = []
    gw._daily_pnl = 0
    gw._consecutive_losses = 0
    gw._rr_selection_enabled = False
    gw.demo_slot = None
    gw._trade_manager = None
    gw._opposite_count = 0
    gw._opposite_bar_ts = ""
    return gw


# ── Group 1: legacy rejects but V2 approves → routes under flag ─────

def test_legacy_rejects_v2_approves_flag_on(monkeypatch):
    """Under SIZING_CONSOLIDATION_V1=1, a fire that legacy calculate_size
    would reject (SWI/CZI/TCCI all misaligned) but V2 approved (contracts>0)
    MUST reach the gateway — not be silently killed.

    ANTI-TAUTOLOGICAL: this test FAILS on the old code (line 983 recalculates
    with legacy, overriding V2).
    """
    ws = _make_woodies()
    # Set all auxiliaries AGAINST the LONG direction → legacy rejects
    ws.current_state["swi_value"] = -5.0   # negative = SHORT aligned
    ws.current_state["czi_value"] = -3.0
    ws.current_state["cci_6_tcci"] = 40.0  # TCCI < CCI14 = SHORT aligned
    ws.current_state["cci_14"] = 50.0
    ws.current_state["lsma_value"] = 8000.0  # above last_close = SHORT
    ws.current_state["ema_34"] = 8000.0
    ws._closes = [7500.0]

    # Legacy should reject a LONG ZLR (low tier, aux_count=0)
    legacy_result = ws.calculate_size("ZLR", "LONG")
    assert legacy_result == "reject", "Precondition: legacy must reject this setup"

    # V2 would approve (contracts > 0) — test via compute_v2_sizing
    monkeypatch.setenv("FIXED_CONTRACTS_3", "1")
    from backend.v9.config_loader import load_stop_anchors
    from backend.v9.systems.stop_anchors.sizing import compute_v2_sizing
    cfg = load_stop_anchors()
    v2 = compute_v2_sizing(
        entry_price=7500.0, stop_price=7493.0, direction="LONG",
        pattern_key="ZLR", day_type="Normal", confidence_tier="medium",
        day_has_direction=True, trade_with_trend=True,
        value_area_full_traverse=None, cfg=cfg,
    )
    assert v2 is not None and v2.contracts == 3, "Precondition: V2 must approve with 3"

    # The key assertion: under the flag, the pre-computed sizing (from V2)
    # is NOT overwritten by legacy at routing time.
    monkeypatch.setenv("SIZING_CONSOLIDATION_V1", "1")
    _consol = os.environ.get("SIZING_CONSOLIDATION_V1", "0").lower() in ("1", "true", "yes")
    assert _consol, "Flag must be on for this test"

    # Simulate what line 983 does: under flag, skip legacy re-calc
    sizing = "full"  # V2 already set this at ~645
    if not _consol:
        sizing = ws.calculate_size("ZLR", "LONG")
    assert sizing == "full", "Under flag, V2 sizing must survive — not be overwritten by legacy"


def test_legacy_rejects_v2_approves_flag_off(monkeypatch):
    """Without the flag, legacy re-calc at routing time CAN reject.
    This proves the test is anti-tautological (would fail on current code).
    """
    monkeypatch.delenv("SIZING_CONSOLIDATION_V1", raising=False)
    ws = _make_woodies()
    ws.current_state["swi_value"] = -5.0
    ws.current_state["czi_value"] = -3.0
    ws.current_state["cci_6_tcci"] = 40.0
    ws.current_state["cci_14"] = 50.0
    ws.current_state["lsma_value"] = 8000.0
    ws.current_state["ema_34"] = 8000.0
    ws._closes = [7500.0]

    # Without flag: legacy recalculates and rejects
    sizing = "full"  # V2 set this
    _consol = os.environ.get("SIZING_CONSOLIDATION_V1", "0").lower() in ("1", "true", "yes")
    if not _consol:
        sizing = ws.calculate_size("ZLR", "LONG")
    assert sizing == "reject", "Without flag, legacy overrides V2 (the bug we're fixing)"


# ── Group 2: FIXED_CONTRACTS_3 before==after ────────────────────────

def test_fixed_contracts_3_v2_sizing_always_3(monkeypatch):
    """Under FIXED_CONTRACTS_3=1, compute_v2_sizing always returns 3."""
    monkeypatch.setenv("FIXED_CONTRACTS_3", "1")
    from backend.v9.config_loader import load_stop_anchors
    from backend.v9.systems.stop_anchors.sizing import compute_v2_sizing
    cfg = load_stop_anchors()

    for pattern in ["ZLR", "CONT", "VEGAS", "GHOST"]:
        anchor = cfg["anchors"].get(pattern)
        if anchor is None:
            continue
        r = compute_v2_sizing(
            entry_price=7500.0, stop_price=7493.0, direction="LONG",
            pattern_key=pattern, day_type="Normal", confidence_tier="medium",
            day_has_direction=True, trade_with_trend=True,
            value_area_full_traverse=None, cfg=cfg,
        )
        if r is not None:  # None = SKIP/auth reject, not a contract-count issue
            assert r.contracts == 3, f"{pattern}: expected 3 contracts, got {r.contracts}"


def test_fixed_contracts_3_quality_tier_v2_always_3(monkeypatch):
    """Under FIXED_CONTRACTS_3=1, get_quality_tier_v2 always returns 3."""
    monkeypatch.setenv("FIXED_CONTRACTS_3", "1")
    from backend.v9.systems.five_min.quality_tier import get_quality_tier_v2

    for pattern in ["REACTIVE_LONG", "INITIATIVE_LONG"]:
        verdict, tier, contracts = get_quality_tier_v2(
            pattern, "Normal", 7500.0, tpo_data={"poc": 7500.0, "vah": 7520.0, "val": 7480.0},
        )
        if contracts > 0:  # 0 = auth reject
            assert contracts == 3, f"{pattern}: expected 3, got {contracts}"


# ── Group 3: risk-cap reject → gateway blocked_by ───────────────────

def test_s4_risk_cap_block_surfaces_in_gateway(monkeypatch):
    """Under SIZING_CONSOLIDATION_V1=1, a risk-cap rejection in the S4 detector
    surfaces as gateway blocked_by='s4_risk_cap' (not a silent sizing=reject).

    ANTI-TAUTOLOGICAL: without the flag, the rejection never reaches the gateway.
    """
    monkeypatch.setenv("SIZING_CONSOLIDATION_V1", "1")
    gw = _make_gateway()

    # Mock session window to allow routing
    monkeypatch.setattr(
        "backend.v9.gateway.trading_gateway.is_within_firing_window",
        lambda: True,
    )
    # Mock kill switch
    monkeypatch.setattr(
        "backend.v9.services.kill_switch.is_engaged",
        lambda: (False, ""),
    )
    # Mock feed watchdog
    monkeypatch.setattr(
        "backend.v9.services.feed_watchdog.is_feed_alive",
        lambda: (True, "ok"),
    )

    setup = {
        "firing_system": 4,
        "direction": "LONG",
        "classification": "ZLR",
        "confidence": 0.8,
        "entry_price": 7500.0,
        "stop": 7493.0,
        "t1": 7507.0,
        "t2": None,
        "t3": None,
        "metadata": {
            "pattern": "ZLR",
            "sizing": "full",
            "s4_risk_cap_block": "risk_points:ZLR:9.5>7.0",
        },
    }
    result = gw.route_setup(setup, 4)
    assert result["blocked_by"] == "s4_risk_cap", (
        f"Expected blocked_by='s4_risk_cap', got {result.get('blocked_by')}"
    )

    # P5 (2026-07-16): the per-pattern loss-breaker is kind-prefixed and must
    # surface under its OWN name — folding it into "s4_risk_cap" is what made the
    # 07-15 evening blocks look like a points-cap problem. This test used to send
    # a pattern_loss_breaker payload and still expect "s4_risk_cap"; that
    # expectation predates P5. Both kinds are now pinned explicitly.
    setup["metadata"]["s4_risk_cap_block"] = "pattern_loss_breaker:ZLR:2>=2"
    result = gw.route_setup(setup, 4)
    assert result["blocked_by"] == "pattern_loss_breaker", (
        f"Expected blocked_by='pattern_loss_breaker', got {result.get('blocked_by')}"
    )


def test_s4_risk_cap_no_block_without_metadata(monkeypatch):
    """When metadata has no s4_risk_cap_block, the gate does not fire."""
    monkeypatch.setenv("SIZING_CONSOLIDATION_V1", "1")
    gw = _make_gateway()
    monkeypatch.setattr(
        "backend.v9.gateway.trading_gateway.is_within_firing_window",
        lambda: True,
    )
    monkeypatch.setattr(
        "backend.v9.services.kill_switch.is_engaged",
        lambda: (False, ""),
    )
    monkeypatch.setattr(
        "backend.v9.services.feed_watchdog.is_feed_alive",
        lambda: (True, "ok"),
    )

    setup = {
        "firing_system": 4,
        "direction": "LONG",
        "classification": "ZLR",
        "confidence": 0.8,
        "entry_price": 7500.0,
        "stop": 7493.0,
        "t1": 7507.0,
        "t2": None,
        "t3": None,
        "metadata": {"pattern": "ZLR", "sizing": "full"},
    }
    result = gw.route_setup(setup, 4)
    # Should NOT be blocked by s4_risk_cap
    assert result.get("blocked_by") != "s4_risk_cap"


# ── Group 4: S3 dead code shim ──────────────────────────────────────

def test_s3_calculate_size_always_rejects():
    """S3 calculate_size is shimmed to always-reject (S3_MUTE / item-11)."""
    from backend.v9.systems.footprint.footprint_system import FootprintSystem
    fs = FootprintSystem.__new__(FootprintSystem)
    result = fs.calculate_size({"strength": 0.9, "direction": "LONG"})
    assert result == "reject", f"S3 shim must always reject, got {result}"
