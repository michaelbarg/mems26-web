"""Item-18 halt-proof — counter side opens only after a proven stall.

Michael's doctrine (ledger #24): on a directional day the counter is blocked
UNTIL 2 consecutive closes back through the expansion level prove the trend
halted. CC's v1 blocked forever; this proves the release condition.
"""
from backend.v9.systems.day_direction import halt_proof_met


IBH = 7594.0  # expansion level for an UP day (broke above IB high)
IBL = 7551.0  # expansion level for a DOWN day


def test_up_expansion_still_running_no_proof():
    """Closes still above the broken IB high → trend intact → stay blocked."""
    assert halt_proof_met(expansion_dir="UP", expansion_level=IBH,
                          recent_closes=[7600, 7605, 7602]) is False


def test_up_expansion_two_closes_back_proof():
    """Two closes back below IB high → stall proven → counter SHORT allowed."""
    assert halt_proof_met(expansion_dir="UP", expansion_level=IBH,
                          recent_closes=[7600, 7590, 7588]) is True


def test_up_expansion_only_one_close_back_not_enough():
    """A single close back is not the 2-close proof."""
    assert halt_proof_met(expansion_dir="UP", expansion_level=IBH,
                          recent_closes=[7600, 7605, 7588]) is False


def test_down_expansion_two_closes_back_proof():
    """DOWN day: two closes back above IB low → counter LONG allowed."""
    assert halt_proof_met(expansion_dir="DOWN", expansion_level=IBL,
                          recent_closes=[7540, 7556, 7558]) is True


def test_down_expansion_still_running_no_proof():
    assert halt_proof_met(expansion_dir="DOWN", expansion_level=IBL,
                          recent_closes=[7545, 7540, 7538]) is False


def test_missing_level_fails_safe():
    assert halt_proof_met(expansion_dir="UP", expansion_level=None,
                          recent_closes=[7588, 7585]) is False


def test_too_few_closes_fails_safe():
    assert halt_proof_met(expansion_dir="UP", expansion_level=IBH,
                          recent_closes=[7588]) is False


def test_configurable_min_closes():
    """min_closes=3 needs three closes back, not two."""
    assert halt_proof_met(expansion_dir="UP", expansion_level=IBH,
                          recent_closes=[7600, 7590, 7588], min_closes=3) is False
    assert halt_proof_met(expansion_dir="UP", expansion_level=IBH,
                          recent_closes=[7592, 7590, 7588], min_closes=3) is True


# --- behavioral: gateway integration (fails on the pre-halt-proof code) ---

import pytest
from backend.v9.gateway.trading_gateway import TradingGateway
from backend.v9.gateway.cooldown import CooldownManager, ClusterGuard
import backend.v9.gateway.trading_gateway as tg
import backend.v9.systems.day_direction as dd


class _NoVeto:
    def check_veto(self, direction):
        return False

    def record_outcome(self, *a):
        pass


def _dir_day_gateway(monkeypatch, closes):
    """Bare gateway on an UP-expansion Variation day; `closes` = recent closes
    the halt-proof will see."""
    monkeypatch.setattr(tg, "is_within_firing_window", lambda: True)
    # UP expansion: session_high > ib_high, session_low NOT < ib_low
    monkeypatch.setattr(
        tg, "extract_g1_entry_context",
        lambda ctx: {"day_type_at_entry": "Variation"}, raising=False)
    monkeypatch.setattr(dd, "gather_recent_closes", lambda n=3: closes)
    gw = TradingGateway.__new__(TradingGateway)
    gw._recent_fires = []
    gw.shadow_trades = []
    gw._slot_candidates = []
    gw._rr_selection_enabled = False
    gw.cooldown = CooldownManager()
    gw.cluster_guard = ClusterGuard()
    gw.ssv = _NoVeto()
    gw.demo_slot = None
    gw.live_slot = None
    gw._demo_enabled_systems = set()
    gw._live_enabled_systems = set()
    gw._trade_manager = None
    gw._system_registry = {}
    gw._daily_trades = 0
    gw._daily_pnl = 0.0
    gw._consecutive_losses = 0
    monkeypatch.setattr(
        gw, "_capture_cross_context",
        lambda: {"tpo_system": {"ib_high": 7594.0, "ib_low": 7551.0,
                                "session_high": 7600.0, "session_low": 7560.0}},
        raising=False)
    monkeypatch.setattr(gw, "_execute_shadow",
                        lambda setup, sid, ctx: {"trade_id": 99}, raising=False)
    monkeypatch.setattr(gw, "_selfheal_demo_slot", lambda: None, raising=False)
    return gw


def _short_setup():
    return {"firing_system": 2, "direction": "SHORT", "classification": "REACTIVE_SHORT",
            "confidence": 0.7, "entry_price": 7588.0, "stop": 7596.0,
            "t1": 7580.0, "t2": None, "t3": None, "metadata": {}}


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for f in ("FEED_WATCHDOG", "LAYER0_CHOP_GATE", "OPENING_TYPE_GATE", "DAYTYPE_PLAYBOOK",
              "DAYTYPE_POSITION_GATE", "TREND_DIRECTION_GATE", "REACTIVE_LOCATION_GATE",
              "RR_ENTRY_GATE_V1", "RISK_HALT_V1", "DEDUP_FIRE_GUARD", "DAYTYPE_TARGETS_STRUCTURAL"):
        monkeypatch.delenv(f, raising=False)
    monkeypatch.setenv("DAY_DIRECTION_DOCTRINE_V1", "1")


def test_counter_blocked_without_halt_proof(monkeypatch):
    """SHORT against UP expansion, closes still above IB high → blocked."""
    gw = _dir_day_gateway(monkeypatch, closes=[7600.0, 7605.0, 7602.0])
    r = gw.route_setup(_short_setup(), 2)
    assert r.get("blocked_by") == "day_direction_doctrine"


def test_counter_released_with_halt_proof(monkeypatch):
    """Two closes back below IB high → halt-proof met → counter SHORT routes.
    Pre-item-18-halt-proof code blocks here unconditionally."""
    gw = _dir_day_gateway(monkeypatch, closes=[7590.0, 7588.0])
    r = gw.route_setup(_short_setup(), 2)
    assert r.get("blocked_by") is None, f"blocked_by={r.get('blocked_by')} — halt-proof must release the counter (item-18)"
    assert r.get("shadow") == 99
