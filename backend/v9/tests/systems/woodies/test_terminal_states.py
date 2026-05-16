"""Tests for Woodies Terminal State Emitter (PROMPT 4 · 4.1).

Acceptance: all 18 terminal states emit + recorded + queryable.
"""

import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

import pytest
from backend.v9.systems.woodies.terminal_states import (
    TerminalState,
    TerminalStateEmitter,
    TradeContext,
    ENTRY_TERMINALS,
    ACTIVE_TERMINALS,
)


@pytest.fixture
def emitter():
    """Emitter with no external deps (in-memory only)."""
    return TerminalStateEmitter()


@pytest.fixture
def context():
    return TradeContext(
        trade_id="test-001",
        stage_id="A1_strategic_gate",
        direction="LONG",
        bar_context={"ts": 1000},
    )


# ── Test: 18 terminal states enum ────────────────────────────────

class TestTerminalStateEnum:
    def test_18_total_states(self):
        assert len(TerminalState) == 18

    def test_5_entry_terminals(self):
        assert len(ENTRY_TERMINALS) == 5

    def test_13_active_terminals(self):
        assert len(ACTIVE_TERMINALS) == 13

    def test_no_overlap(self):
        assert ENTRY_TERMINALS & ACTIVE_TERMINALS == set()

    def test_all_covered(self):
        assert ENTRY_TERMINALS | ACTIVE_TERMINALS == set(TerminalState)


# ── Test: Each of 18 states emits correctly ───────────────────────

class TestAllStatesEmit:
    @pytest.mark.parametrize("state", list(TerminalState))
    def test_state_emits(self, emitter, state):
        ctx = TradeContext(
            trade_id=f"test-{state.value}",
            stage_id="test_stage",
            direction="LONG",
            bar_context={"test": True},
        )
        result = emitter.emit(state, ctx)
        assert result["state"] == state.value
        assert result["phase"] in ("entry", "active")

    @pytest.mark.parametrize("state", list(TerminalState))
    def test_state_logged(self, emitter, state):
        ctx = TradeContext(trade_id=f"log-{state.value}", stage_id="test")
        emitter.emit(state, ctx)
        log = emitter.get_emission_log()
        assert len(log) == 1
        assert log[0]["terminal_state"] == state.value


# ── Test: Phase classification ────────────────────────────────────

class TestPhaseClassification:
    def test_entry_states_phase(self, emitter):
        for state in ENTRY_TERMINALS:
            ctx = TradeContext(trade_id="t", stage_id="s")
            result = emitter.emit(state, ctx)
            assert result["phase"] == "entry"

    def test_active_states_phase(self, emitter):
        for state in ACTIVE_TERMINALS:
            ctx = TradeContext(trade_id="t", stage_id="s")
            result = emitter.emit(state, ctx)
            assert result["phase"] == "active"


# ── Test: Record structure ────────────────────────────────────────

class TestRecordStructure:
    def test_record_has_all_fields(self, emitter, context):
        result = emitter.emit(TerminalState.BUY, context)
        record = result["record"]
        assert "trade_id" in record
        assert "terminal_state" in record
        assert "phase" in record
        assert "triggered_at" in record
        assert "bar_context" in record
        assert "stage_id" in record
        assert "direction" in record

    def test_context_preserved(self, emitter):
        ctx = TradeContext(
            trade_id="ctx-test",
            stage_id="B10_t1_milestone",
            direction="SHORT",
            entry_price=7400.0,
            exit_price=7405.0,
            pnl_points=-5.0,
            classification="INITIATIVE",
            notes="T1 hit test",
            priority_class="TARGET",
        )
        result = emitter.emit(TerminalState.SUCCESS_INITIATIVE, ctx)
        r = result["record"]
        assert r["trade_id"] == "ctx-test"
        assert r["direction"] == "SHORT"
        assert r["entry_price"] == 7400.0
        assert r["classification"] == "INITIATIVE"
        assert r["priority_class"] == "TARGET"


# ── Test: In-memory log ───────────────────────────────────────────

class TestEmissionLog:
    def test_multiple_emissions_logged(self, emitter):
        for i in range(5):
            ctx = TradeContext(trade_id=f"multi-{i}", stage_id="s")
            emitter.emit(TerminalState.HOLD, ctx)
        assert len(emitter.get_emission_log()) == 5

    def test_log_returns_copy(self, emitter):
        ctx = TradeContext(trade_id="t", stage_id="s")
        emitter.emit(TerminalState.BUY, ctx)
        log1 = emitter.get_emission_log()
        log2 = emitter.get_emission_log()
        assert log1 == log2
        assert log1 is not log2  # copy, not reference


# ── Test: Graceful degradation ────────────────────────────────────

class TestGracefulDegradation:
    def test_no_db_still_emits(self, emitter, context):
        """Without DB, emission still works (logs + returns)."""
        result = emitter.emit(TerminalState.STOP_LOSS, context)
        assert result["db"] is False
        assert result["state"] == "STOP_LOSS"

    def test_no_redis_still_emits(self, emitter, context):
        result = emitter.emit(TerminalState.EOD_FORCE, context)
        assert result["redis"] is False

    def test_no_slack_still_emits(self, emitter, context):
        result = emitter.emit(TerminalState.NEWS_EXIT, context)
        assert result["slack"] is False


# ── Test: DB model importable ─────────────────────────────────────

class TestDBModel:
    def test_model_importable(self):
        from backend.v9.db.models.woodies_trade_terminals import WoodiesTradeTerminal
        assert WoodiesTradeTerminal.__tablename__ == "woodies_trade_terminals"

    def test_model_has_required_columns(self):
        from backend.v9.db.models.woodies_trade_terminals import WoodiesTradeTerminal
        cols = {c.name for c in WoodiesTradeTerminal.__table__.columns}
        required = {"id", "trade_id", "terminal_state", "phase", "priority_class",
                     "triggered_at", "bar_context", "stage_id", "direction",
                     "entry_price", "exit_price", "pnl_points", "classification", "notes"}
        assert required.issubset(cols)
