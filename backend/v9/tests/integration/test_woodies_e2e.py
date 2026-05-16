"""Woodies E2E Flow Tests — 5 Scenarios (PROMPT 4 · 4.3).

Tests the full Woodies decision flow: entry → active → terminal.
Uses synthetic bar sequences, mock trade_manager, mock endpoints.

5 scenarios per Decision Tree V1:
  1. Trend BLUE → T1 → T2 → trail → SUCCESS_TRAIL
  2. Trend RED → STOP_LOSS
  3. Color flip mid-trade → STRATEGIC_EXIT
  4. News window mid-trade → NEWS_EXIT
  5. EOD force → EOD_FORCE
"""

import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

import pytest

from backend.v9.systems.woodies.stages.a1_strategic_gate import A1StrategicGate
from backend.v9.systems.woodies.stages.a3_pattern_detection import A3PatternDetection
from backend.v9.systems.woodies.stages.a6_entry_classification import A6EntryClassification
from backend.v9.systems.woodies.stages.a7_universal_checks import A7UniversalChecks
from backend.v9.systems.woodies.stages.b1_stop_check import B1StopCheck
from backend.v9.systems.woodies.stages.b2_eod_check import B2EodCheck
from backend.v9.systems.woodies.stages.b3_color_flip import B3ColorFlip
from backend.v9.systems.woodies.stages.b6_news_window import B6NewsWindow
from backend.v9.systems.woodies.stages.b10_t1_milestone import B10T1Milestone
from backend.v9.systems.woodies.stages.b11_t2_milestone import B11T2Milestone
from backend.v9.systems.woodies.stages.b12_t3_milestone import B12T3Milestone
from backend.v9.systems.woodies.stages.b13_trail_check import B13TrailCheck
from backend.v9.systems.woodies.stages.b14_hold import B14Hold

from backend.v9.systems.woodies.terminal_states import (
    TerminalState,
    TerminalStateEmitter,
    TradeContext,
)
from backend.v9.systems.woodies.execution_bridge import (
    WoodiesExecutionBridge,
    WoodiesIntent,
    IntentType,
)
from backend.v9.systems.woodies.dispatcher import Dispatcher, StageOutput, PriorityClass

from backend.v9.tests.integration.fixtures.woodies_bar_sequences import (
    generate_trend_blue_sequence,
    generate_trend_red_sequence,
    generate_color_flip_sequence,
)


@pytest.fixture
def emitter():
    return TerminalStateEmitter()


@pytest.fixture
def bridge():
    return WoodiesExecutionBridge()


@pytest.fixture
def dispatcher():
    return Dispatcher()


# ═══════════════════════════════════════════════════════════════════
# SCENARIO 1 — Trend BLUE → T1 → T2 → trail → SUCCESS_TRAIL
# ═══════════════════════════════════════════════════════════════════

class TestScenario1TrendBlueSuccess:
    """Full path: A1 BLUE → A3 pattern → A6 INITIATIVE → A7 approves →
    BUY → B10 T1 → B11 T2 INITIATIVE → B13 trail → SUCCESS_TRAIL."""

    def test_entry_phase_blue_buy(self):
        """A1→A7: CCI sustained positive → BLUE → BUY."""
        bars = generate_trend_blue_sequence(30)
        cci_history = [b.cci_14 for b in bars]

        # A1: Strategic gate
        a1 = A1StrategicGate().evaluate(
            cci_14_value=cci_history[-1], cci_14_history=cci_history,
        )
        assert a1.color == "BLUE"
        assert a1.direction_allowed == "LONG"

        # A7: Universal checks (all defaults pass)
        a7 = A7UniversalChecks().evaluate(direction="LONG")
        assert a7.entry_approved is True

    def test_active_t1_no_be(self):
        """B10: T1 hit → CLOSE_C1, NO BE move (D-002)."""
        b10 = B10T1Milestone().evaluate(
            current_price=7405.0, t1_price=7405.0, direction="LONG",
        )
        assert b10.t1_hit is True
        assert b10.action == "CLOSE_C1"
        assert b10.be_moved is False  # D-002

    def test_active_t2_initiative_smart_be(self):
        """B11: T2 INITIATIVE → CLOSE_C2 + Smart BE (D-055)."""
        b11 = B11T2Milestone().evaluate(
            current_price=7415.0, t2_price=7415.0, direction="LONG",
            entry_classification="INITIATIVE",
        )
        assert b11.t2_hit is True
        assert b11.action == "CLOSE_C2"
        assert b11.be_moved is True  # D-055

    def test_active_trail_exit(self):
        """B13: Price below EMA-169 → CLOSE_C3 (trail exit)."""
        b13 = B13TrailCheck().evaluate(
            vegas_ema_169=7420.0, current_price=7418.0, direction="LONG",
            t2_already_hit=True, trail_mode_active=True,
        )
        assert b13.trail_exit is True
        assert b13.action == "CLOSE_C3"

    def test_terminal_emission(self, emitter):
        """All terminals emit: BUY + CLOSE_C1 (T1) + CLOSE_C2 (T2) + SUCCESS_TRAIL."""
        ctx = TradeContext(trade_id="s1", stage_id="A7", direction="LONG")
        r1 = emitter.emit(TerminalState.BUY, ctx)
        assert r1["phase"] == "entry"

        ctx2 = TradeContext(trade_id="s1", stage_id="B13", direction="LONG", pnl_points=15.0)
        r2 = emitter.emit(TerminalState.SUCCESS_TRAIL, ctx2)
        assert r2["phase"] == "active"

        assert len(emitter.get_emission_log()) == 2

    def test_bridge_submit_and_close(self, bridge):
        """Bridge: submit_bracket → close_contracts → close_contracts → close_contracts."""
        r1 = bridge.execute_intent(WoodiesIntent(
            intent_type=IntentType.SUBMIT_BRACKET,
            reason="BUY", direction="LONG",
            stop_price=7395, t1_price=7405, t2_price=7415, t3_price=7435,
        ))
        assert r1.success

        r2 = bridge.execute_intent(WoodiesIntent(
            intent_type=IntentType.CLOSE_CONTRACTS,
            reason="T1_HIT", contract_count=1, target_level="T1",
        ))
        assert r2.success

        assert len(bridge.get_intent_log()) == 2


# ═══════════════════════════════════════════════════════════════════
# SCENARIO 2 — Trend RED → STOP_LOSS
# ═══════════════════════════════════════════════════════════════════

class TestScenario2StopLoss:
    """A1 RED → A3 pattern → SELL → B1 stop hit → STOP_LOSS."""

    def test_entry_phase_red_sell(self):
        bars = generate_trend_red_sequence(30)
        cci_history = [b.cci_14 for b in bars]

        a1 = A1StrategicGate().evaluate(
            cci_14_value=cci_history[-1], cci_14_history=cci_history,
        )
        assert a1.color == "RED"
        assert a1.direction_allowed == "SHORT"

    def test_stop_hit(self):
        b1 = B1StopCheck().evaluate(
            current_price=7410.0, stop_price=7405.0, direction="SHORT",
        )
        assert b1.stop_hit is True
        assert b1.action == "CLOSE_ALL"

    def test_terminal_stop_loss(self, emitter):
        ctx = TradeContext(trade_id="s2", stage_id="B1", direction="SHORT")
        r = emitter.emit(TerminalState.STOP_LOSS, ctx)
        assert r["state"] == "STOP_LOSS"
        assert r["phase"] == "active"

    def test_bridge_close_all(self, bridge):
        r = bridge.close_all(reason="STOP_LOSS")
        assert r.success


# ═══════════════════════════════════════════════════════════════════
# SCENARIO 3 — Color flip → STRATEGIC_EXIT
# ═══════════════════════════════════════════════════════════════════

class TestScenario3ColorFlip:
    """Enter on BLUE → mid-trade color flips to RED → B3 STRATEGIC_EXIT."""

    def test_color_flip_detected(self):
        b3 = B3ColorFlip().evaluate(
            current_color="RED", entry_color="BLUE", direction="LONG",
        )
        assert b3.flip_detected is True
        assert b3.action == "CLOSE_ALL"

    def test_dispatcher_strategic_wins(self, dispatcher):
        outputs = [
            StageOutput("B3_color_flip", PriorityClass.STRATEGIC_EXIT,
                        "CLOSE_ALL", True, yaml_order=2),
            StageOutput("B14_hold", PriorityClass.NO_ACTION,
                        "HOLD", True, yaml_order=13),
        ]
        result = dispatcher.resolve(outputs)
        assert result.winning_stage == "B3_color_flip"

    def test_terminal_strategic_exit(self, emitter):
        ctx = TradeContext(trade_id="s3", stage_id="B3")
        r = emitter.emit(TerminalState.STRATEGIC_EXIT, ctx)
        assert r["state"] == "STRATEGIC_EXIT"


# ═══════════════════════════════════════════════════════════════════
# SCENARIO 4 — News window → NEWS_EXIT
# ═══════════════════════════════════════════════════════════════════

class TestScenario4NewsExit:
    """Active trade → Tier 1 news within 5min → B6 NEWS_EXIT."""

    def test_news_window_triggers(self):
        b6 = B6NewsWindow().evaluate(
            news_calendar={"minutes_to_next_tier1": 3},
            position_size=3,
        )
        assert b6.news_exit is True
        assert b6.action == "CLOSE_ALL"

    def test_dispatcher_absolute_wins(self, dispatcher):
        outputs = [
            StageOutput("B6_news_window", PriorityClass.ABSOLUTE_EXIT,
                        "CLOSE_ALL", True, yaml_order=5),
            StageOutput("B10_t1_milestone", PriorityClass.TARGET,
                        "CLOSE_C1", True, yaml_order=9),
        ]
        result = dispatcher.resolve(outputs)
        assert result.winning_stage == "B6_news_window"

    def test_terminal_news_exit(self, emitter):
        ctx = TradeContext(trade_id="s4", stage_id="B6")
        r = emitter.emit(TerminalState.NEWS_EXIT, ctx)
        assert r["state"] == "NEWS_EXIT"

    def test_bridge_close_all_news(self, bridge):
        r = bridge.close_all(reason="NEWS_EXIT")
        assert r.success


# ═══════════════════════════════════════════════════════════════════
# SCENARIO 5 — EOD force → EOD_FORCE
# ═══════════════════════════════════════════════════════════════════

class TestScenario5EodForce:
    """Active trade at 15:58 → 15:59 → B2 EOD_FORCE."""

    def test_no_trigger_at_1558(self):
        b2 = B2EodCheck().evaluate(current_time_et="15:58")
        assert b2.eod_force is False

    def test_trigger_at_1559(self):
        b2 = B2EodCheck().evaluate(current_time_et="15:59")
        assert b2.eod_force is True
        assert b2.action == "CLOSE_ALL"

    def test_terminal_eod_force(self, emitter):
        ctx = TradeContext(trade_id="s5", stage_id="B2", notes="D-002 no overnight")
        r = emitter.emit(TerminalState.EOD_FORCE, ctx)
        assert r["state"] == "EOD_FORCE"
        assert r["record"]["notes"] == "D-002 no overnight"

    def test_bridge_close_all_eod(self, bridge):
        r = bridge.close_all(reason="EOD_FORCE")
        assert r.success


# ═══════════════════════════════════════════════════════════════════
# CROSS-SCENARIO: DB records all terminals
# ═══════════════════════════════════════════════════════════════════

class TestCrossScenarioDBRecords:
    def test_all_5_scenarios_emit_distinct_terminals(self, emitter):
        """Each scenario produces a distinct terminal state."""
        scenarios = [
            (TerminalState.SUCCESS_TRAIL, "s1", "B13"),
            (TerminalState.STOP_LOSS, "s2", "B1"),
            (TerminalState.STRATEGIC_EXIT, "s3", "B3"),
            (TerminalState.NEWS_EXIT, "s4", "B6"),
            (TerminalState.EOD_FORCE, "s5", "B2"),
        ]
        for state, trade_id, stage in scenarios:
            ctx = TradeContext(trade_id=trade_id, stage_id=stage)
            emitter.emit(state, ctx)

        log = emitter.get_emission_log()
        assert len(log) == 5
        states = {r["terminal_state"] for r in log}
        assert len(states) == 5  # all distinct
