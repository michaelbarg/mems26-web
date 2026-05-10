"""Tests for W13 Trading Gateway — 3-mode routing layer.

Coverage targets:
- SHADOW always parallel (no blocking, no caps)
- DEMO first-wins slot management
- LIVE W14 risk validation before entry
- Dual-layer operation (SHADOW + DEMO concurrent)
- Slot release lifecycle
- Full routing per spec Section 4
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Any, Dict

from backend.v9.services.trading_gateway.gateway import TradingGateway
from backend.v9.services.trading_gateway.executors.shadow import ShadowExecutor
from backend.v9.services.trading_gateway.executors.demo import DemoExecutor, SIERRA_DEMO_ACCOUNT
from backend.v9.services.trading_gateway.executors.live import LiveExecutor, SIERRA_LIVE_ACCOUNT
from backend.v9.services.risk_validator.validator import AccountState, RiskValidator


# ── fixtures ─────────────────────────────────────────────────────────

def _make_setup(system_id: int = 1, direction: str = "LONG") -> Dict[str, Any]:
    """Create a minimal valid setup dict."""
    return {
        "firing_system": system_id,
        "direction": direction,
        "stop": 5240.0,
        "t1": 5250.0,
        "t2": 5255.0,
        "t3": 5260.0,
        "entry_price": 5245.0,
    }


def _make_gateway(
    demo_enabled: bool = True,
    live_enabled: bool = False,
) -> TradingGateway:
    """Create a TradingGateway with mocked W11 and W14."""
    trade_manager = MagicMock()
    # accept_setup returns incrementing trade IDs
    trade_manager.accept_setup.side_effect = _id_counter()

    risk_validator = MagicMock(spec=RiskValidator)
    risk_validator.check_setup.return_value = (True, None)

    gw = TradingGateway(
        trade_manager=trade_manager,
        risk_validator=risk_validator,
        demo_enabled=demo_enabled,
        live_enabled=live_enabled,
    )
    return gw


_counter = 0


def _id_counter():
    """Generate incrementing trade IDs for mock."""
    global _counter
    while True:
        _counter += 1
        yield _counter


@pytest.fixture(autouse=True)
def _reset_counter():
    """Reset global counter before each test."""
    global _counter
    _counter = 0
    yield


# ── SHADOW tests ─────────────────────────────────────────────────────

class TestShadowAlwaysParallel:
    """SHADOW: no caps, no slot limit, runs ALL setups."""

    def test_shadow_always_parallel(self):
        """Multiple setups from different systems all get shadow trades."""
        gw = _make_gateway(demo_enabled=False, live_enabled=False)

        results = []
        for sys_id in [1, 2, 4, 1, 2]:
            r = gw.route_setup(_make_setup(system_id=sys_id), system_id=sys_id)
            results.append(r)

        # All 5 setups got shadow trades
        shadow_ids = [r["shadow_trade_id"] for r in results]
        assert len(shadow_ids) == 5
        assert all(sid > 0 for sid in shadow_ids)
        # All unique IDs
        assert len(set(shadow_ids)) == 5

    def test_shadow_no_rejections(self):
        """SHADOW never rejects — no caps, no slot limit."""
        gw = _make_gateway(demo_enabled=False, live_enabled=False)

        for _ in range(10):
            r = gw.route_setup(_make_setup(), system_id=1)
            assert r["shadow_trade_id"] > 0
            assert r["rejections"] == []

    def test_shadow_runs_both_directions(self):
        """SHADOW accepts LONG and SHORT simultaneously."""
        gw = _make_gateway(demo_enabled=False, live_enabled=False)

        r1 = gw.route_setup(_make_setup(direction="LONG"), system_id=1)
        r2 = gw.route_setup(_make_setup(direction="SHORT"), system_id=4)

        assert r1["shadow_trade_id"] > 0
        assert r2["shadow_trade_id"] > 0


# ── DEMO tests ───────────────────────────────────────────────────────

class TestDemoFirstWins:
    """DEMO: ONE slot, first-wins, locked until close."""

    def test_demo_first_wins(self):
        """First setup gets demo slot, second is rejected."""
        gw = _make_gateway(demo_enabled=True, live_enabled=False)

        r1 = gw.route_setup(_make_setup(system_id=1), system_id=1)
        r2 = gw.route_setup(_make_setup(system_id=2), system_id=2)

        # First gets demo
        assert r1["demo_trade_id"] is not None
        assert r1["demo_trade_id"] > 0

        # Second rejected from demo
        assert r2["demo_trade_id"] is None
        demo_rejections = [r for r in r2["rejections"] if r["mode"] == "demo"]
        assert len(demo_rejections) == 1
        assert "occupied" in demo_rejections[0]["reason"]

    def test_demo_locked_until_close(self):
        """Slot stays occupied until release_slot called."""
        gw = _make_gateway(demo_enabled=True, live_enabled=False)

        r1 = gw.route_setup(_make_setup(system_id=1), system_id=1)
        demo_id = r1["demo_trade_id"]

        # Slot is occupied
        status = gw.get_slot_status()
        assert status["demo"]["occupied"] is True
        assert status["demo"]["trade_id"] == demo_id

        # Second setup rejected
        r2 = gw.route_setup(_make_setup(system_id=2), system_id=2)
        assert r2["demo_trade_id"] is None

        # Release the slot
        released = gw.release_slot("demo", demo_id)
        assert released is True

        # Slot now empty
        status = gw.get_slot_status()
        assert status["demo"]["occupied"] is False
        assert status["demo"]["trade_id"] is None

        # Third setup gets demo
        r3 = gw.route_setup(_make_setup(system_id=4), system_id=4)
        assert r3["demo_trade_id"] is not None

    def test_demo_slot_release_mismatch(self):
        """Releasing with wrong trade_id returns False."""
        gw = _make_gateway(demo_enabled=True, live_enabled=False)

        r1 = gw.route_setup(_make_setup(system_id=1), system_id=1)
        demo_id = r1["demo_trade_id"]

        released = gw.release_slot("demo", demo_id + 999)
        assert released is False

        # Slot still occupied
        status = gw.get_slot_status()
        assert status["demo"]["occupied"] is True


# ── LIVE tests ───────────────────────────────────────────────────────

class TestLiveRiskGated:
    """LIVE: ONE slot, first-wins + W14 risk validation."""

    def test_live_uses_risk_validator(self):
        """W14 check_setup is called before LIVE trade creation."""
        gw = _make_gateway(demo_enabled=False, live_enabled=True)

        r = gw.route_setup(_make_setup(system_id=1), system_id=1)

        assert r["live_trade_id"] is not None
        gw._risk_validator.check_setup.assert_called_once()

    def test_live_blocked_by_caps(self):
        """W14 rejection prevents LIVE trade."""
        gw = _make_gateway(demo_enabled=False, live_enabled=True)
        gw._risk_validator.check_setup.return_value = (
            False, "Daily loss cap reached: $250.00 >= $250.00"
        )

        r = gw.route_setup(_make_setup(system_id=1), system_id=1)

        # Shadow still created
        assert r["shadow_trade_id"] > 0
        # Live rejected
        assert r["live_trade_id"] is None
        live_rejections = [r for r in r["rejections"] if r["mode"] == "live"]
        assert len(live_rejections) == 1
        assert "Daily loss cap" in live_rejections[0]["reason"]

    def test_live_first_wins(self):
        """First setup gets live slot, second rejected."""
        gw = _make_gateway(demo_enabled=False, live_enabled=True)

        r1 = gw.route_setup(_make_setup(system_id=1), system_id=1)
        r2 = gw.route_setup(_make_setup(system_id=2), system_id=2)

        assert r1["live_trade_id"] is not None
        assert r2["live_trade_id"] is None
        live_rejections = [r for r in r2["rejections"] if r["mode"] == "live"]
        assert len(live_rejections) == 1
        assert "occupied" in live_rejections[0]["reason"]

    def test_live_slot_release_allows_next(self):
        """Releasing live slot allows next setup through."""
        gw = _make_gateway(demo_enabled=False, live_enabled=True)

        r1 = gw.route_setup(_make_setup(system_id=1), system_id=1)
        live_id = r1["live_trade_id"]

        gw.release_slot("live", live_id)

        r2 = gw.route_setup(_make_setup(system_id=4), system_id=4)
        assert r2["live_trade_id"] is not None


# ── Dual-layer tests ─────────────────────────────────────────────────

class TestDualLayer:
    """SHADOW + DEMO concurrent operation per spec Section 4."""

    def test_dual_layer_shadow_plus_demo(self):
        """Single setup creates both shadow + demo trades."""
        gw = _make_gateway(demo_enabled=True, live_enabled=False)

        r = gw.route_setup(_make_setup(system_id=2), system_id=2)

        assert r["shadow_trade_id"] > 0
        assert r["demo_trade_id"] is not None
        assert r["demo_trade_id"] > 0
        # Different trade objects
        assert r["shadow_trade_id"] != r["demo_trade_id"]

    def test_routing_per_section_4(self):
        """Full routing flow matching spec Section 4 pseudo-code.

        11:00 -- System 1 LONG -> SHADOW + DEMO (slot locked)
        11:05 -- System 2 LONG -> SHADOW + DEMO rejected
        11:30 -- System 1 DEMO closes -> slot unlocked
        11:32 -- System 4 SHORT -> SHADOW + DEMO (slot acquired)
        """
        gw = _make_gateway(demo_enabled=True, live_enabled=False)

        # 11:00 — System 1 fires LONG
        r1 = gw.route_setup(
            _make_setup(system_id=1, direction="LONG"), system_id=1
        )
        assert r1["shadow_trade_id"] > 0
        assert r1["demo_trade_id"] is not None
        demo_1_id = r1["demo_trade_id"]

        # 11:05 — System 2 fires LONG, demo rejected
        r2 = gw.route_setup(
            _make_setup(system_id=2, direction="LONG"), system_id=2
        )
        assert r2["shadow_trade_id"] > 0
        assert r2["demo_trade_id"] is None
        assert any(r["mode"] == "demo" for r in r2["rejections"])

        # 11:30 — System 1 demo trade closes
        gw.release_slot("demo", demo_1_id)

        # 11:32 — System 4 fires SHORT, gets demo slot
        r3 = gw.route_setup(
            _make_setup(system_id=4, direction="SHORT"), system_id=4
        )
        assert r3["shadow_trade_id"] > 0
        assert r3["demo_trade_id"] is not None

        # All 3 setups created shadow trades
        shadow_ids = [r1["shadow_trade_id"], r2["shadow_trade_id"], r3["shadow_trade_id"]]
        assert len(set(shadow_ids)) == 3


# ── Slot status + release tests ──────────────────────────────────────

class TestSlotManagement:
    """Slot status and release lifecycle."""

    def test_slot_release(self):
        """Releasing slot allows next setup through."""
        gw = _make_gateway(demo_enabled=True, live_enabled=True)

        r1 = gw.route_setup(_make_setup(system_id=1), system_id=1)
        demo_id = r1["demo_trade_id"]
        live_id = r1["live_trade_id"]

        status = gw.get_slot_status()
        assert status["demo"]["occupied"] is True
        assert status["live"]["occupied"] is True

        gw.release_slot("demo", demo_id)
        gw.release_slot("live", live_id)

        status = gw.get_slot_status()
        assert status["demo"]["occupied"] is False
        assert status["live"]["occupied"] is False

    def test_initial_slots_empty(self):
        """Slots start empty."""
        gw = _make_gateway()
        status = gw.get_slot_status()
        assert status["demo"]["occupied"] is False
        assert status["demo"]["trade_id"] is None
        assert status["live"]["occupied"] is False
        assert status["live"]["trade_id"] is None

    def test_invalid_mode_release_raises(self):
        """Releasing with invalid mode raises ValueError."""
        gw = _make_gateway()
        with pytest.raises(ValueError, match="Invalid mode"):
            gw.release_slot("shadow", 1)

    def test_invalid_system_id_raises(self):
        """Routing with invalid system_id raises ValueError."""
        gw = _make_gateway()
        with pytest.raises(ValueError, match="Invalid system_id"):
            gw.route_setup(_make_setup(), system_id=3)

    def test_triple_layer(self):
        """All three layers active: SHADOW + DEMO + LIVE."""
        gw = _make_gateway(demo_enabled=True, live_enabled=True)

        r = gw.route_setup(_make_setup(system_id=1), system_id=1)

        assert r["shadow_trade_id"] > 0
        assert r["demo_trade_id"] is not None
        assert r["live_trade_id"] is not None
        # All different trade IDs
        ids = {r["shadow_trade_id"], r["demo_trade_id"], r["live_trade_id"]}
        assert len(ids) == 3


# ── Executor unit tests ──────────────────────────────────────────────

class TestExecutors:
    """Unit tests for individual executors."""

    def test_shadow_executor(self):
        """ShadowExecutor creates trade with mode='shadow'."""
        tm = MagicMock()
        tm.accept_setup.return_value = 42
        executor = ShadowExecutor(tm)

        trade_id = executor.execute(_make_setup(system_id=1))

        assert trade_id == 42
        tm.accept_setup.assert_called_once_with(
            _make_setup(system_id=1), mode="shadow"
        )

    def test_demo_executor(self):
        """DemoExecutor creates trade with mode='demo'."""
        tm = MagicMock()
        tm.accept_setup.return_value = 43
        executor = DemoExecutor(tm)

        trade_id = executor.execute(_make_setup(system_id=2))

        assert trade_id == 43
        tm.accept_setup.assert_called_once_with(
            _make_setup(system_id=2), mode="demo"
        )

    def test_live_executor_allowed(self):
        """LiveExecutor: W14 allows -> trade created."""
        tm = MagicMock()
        tm.accept_setup.return_value = 44
        rv = MagicMock(spec=RiskValidator)
        rv.check_setup.return_value = (True, None)
        executor = LiveExecutor(tm, rv)

        allowed, trade_id, reason = executor.execute(_make_setup(system_id=4))

        assert allowed is True
        assert trade_id == 44
        assert reason == ""

    def test_live_executor_rejected(self):
        """LiveExecutor: W14 rejects -> no trade, reason returned."""
        tm = MagicMock()
        rv = MagicMock(spec=RiskValidator)
        rv.check_setup.return_value = (False, "Max trades/day reached: 5 >= 5")
        executor = LiveExecutor(tm, rv)

        allowed, trade_id, reason = executor.execute(_make_setup(system_id=1))

        assert allowed is False
        assert trade_id == 0
        assert "Max trades/day" in reason
        tm.accept_setup.assert_not_called()

    def test_sierra_accounts(self):
        """Verify Sierra account constants."""
        assert SIERRA_DEMO_ACCOUNT == "PA-APEX-125218-01"
        assert SIERRA_LIVE_ACCOUNT == "APEX-125218-13"
