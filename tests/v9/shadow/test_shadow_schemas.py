"""P29.5 — Offline validation of SHADOW data collection schemas.

Tests that all 6 schema categories:
  1. Accept valid data matching real system outputs.
  2. Reject invalid data (wrong types, missing required fields, bad enums).
  3. Cover the full SHADOW data contract without runtime dependencies.

No SHADOW activation, no Redis, no bridge, no services.
"""

import pytest
from pydantic import ValidationError

from backend.v9.shadow.schemas import (
    BarRecord,
    GatewayDecision,
    GatewayRejection,
    LifecycleEvent,
    PreFireDecision,
    ReasonTree,
    ReasonTreeStage,
    S1DayTypeState,
    S2FiveMinState,
    S3FootprintState,
    S4WoodiesState,
    S5TPOState,
    S6KillzoneState,
    StageStatus,
    StreamHealthEntry,
    StreamHealthSnapshot,
    StreamStatus,
    SystemStateSnapshot,
    TradeState,
    SYSTEM_STATE_MODELS,
    RETENTION_POLICY,
)


# ── 1. Bars + Stream Health ──────────────────────────────────────

class TestBarRecord:
    def test_valid_bar(self):
        bar = BarRecord(
            ts="2026-05-18T10:00:00", open=7400.0, high=7410.0,
            low=7395.0, close=7405.0, volume=120, session="RTH",
        )
        assert bar.high >= bar.low

    def test_high_less_than_low_rejected(self):
        with pytest.raises(ValidationError, match="high.*low"):
            BarRecord(
                ts="2026-05-18T10:00:00", open=7400.0, high=7390.0,
                low=7395.0, close=7405.0, volume=120,
            )

    def test_partial_bar(self):
        bar = BarRecord(
            ts="2026-05-18T10:02:30", open=7400.0, high=7402.0,
            low=7399.0, close=7401.0, volume=30, is_partial=True,
        )
        assert bar.is_partial is True


class TestStreamHealth:
    def test_valid_snapshot(self):
        entry = StreamHealthEntry(
            name="tick_reversal_15", status=StreamStatus.GREEN,
            age_sec=0.5, push_count=1000, subscribed_systems=[3],
        )
        snap = StreamHealthSnapshot(
            ts="2026-05-18T10:00:00",
            streams=[entry],
            summary={"green": 1, "yellow": 0, "red": 0, "grey": 0},
        )
        assert len(snap.streams) == 1

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            StreamHealthEntry(
                name="bad", status="purple", age_sec=1.0, push_count=0,
            )


# ── 2. System State Snapshots ────────────────────────────────────

class TestSystemStates:
    def test_s1_day_type(self):
        s = S1DayTypeState(day_type="TREND", confidence=85, classified=True, stage="C3")
        assert s.day_type == "TREND"

    def test_s2_five_min(self):
        s = S2FiveMinState(running=True, hydrated=True, mode="FIRST_HOUR", buffer_size=42)
        assert s.buffer_size == 42

    def test_s3_footprint(self):
        s = S3FootprintState(running=True, hydrated=True, buffer_size=10, bars_processed_today=5)
        assert s.bars_processed_today == 5

    def test_s4_woodies(self):
        s = S4WoodiesState(
            running=True, hydrated=True, trend_state="BLUE",
            cci_14=55.3, classification="GHOST_ZERO_LINE",
            ready_to_route=True, decision_tree={"A1": "PASS"},
        )
        assert s.ready_to_route is True

    def test_s5_tpo(self):
        s = S5TPOState(running=True, poc=7450.0, vah=7460.0, val=7440.0)
        assert s.poc == 7450.0

    def test_s6_killzone(self):
        s = S6KillzoneState(
            running=True, hydrated=True,
            current_zone={"name": "NY_AM", "edge_class": "prime"},
            clock_mode="REALTIME",
        )
        assert s.current_zone["name"] == "NY_AM"

    def test_all_6_systems_have_models(self):
        assert set(SYSTEM_STATE_MODELS.keys()) == {1, 2, 3, 4, 5, 6}

    def test_cross_system_snapshot(self):
        snap = SystemStateSnapshot(
            captured_ts="2026-05-18T10:00:00",
            trigger="entry",
            firing_system_id=4,
            systems={"1": {"day_type": "TREND"}, "4": {"trend_state": "BLUE"}},
        )
        assert snap.trigger == "entry"

    def test_invalid_trigger_rejected(self):
        with pytest.raises(ValidationError, match="trigger"):
            SystemStateSnapshot(
                captured_ts="2026-05-18T10:00:00",
                trigger="bad_trigger",
                systems={},
            )


# ── 3. Pre-Fire Decisions ────────────────────────────────────────

class TestPreFireDecision:
    def test_valid_pass(self):
        d = PreFireDecision(
            ts="2026-05-18T10:00:00", system_id="T2_WOODIES",
            direction="LONG", entry_price=7400.0, stop_price=7390.0,
            t1_price=7410.0, t2_price=7420.0, confidence=80,
            time_stop_minutes=60, valid=True,
        )
        assert d.valid is True

    def test_valid_rejection(self):
        d = PreFireDecision(
            ts="2026-05-18T10:00:00", system_id="T1_NUMBER_BAR",
            direction="SHORT", entry_price=7400.0, stop_price=7410.0,
            t1_price=7390.0, t2_price=7380.0, confidence=30,
            time_stop_minutes=60, valid=False, fail_reason="R:R < 1.0",
        )
        assert d.fail_reason == "R:R < 1.0"

    def test_invalid_direction_rejected(self):
        with pytest.raises(ValidationError, match="direction"):
            PreFireDecision(
                ts="x", system_id="T2_WOODIES", direction="UP",
                entry_price=1, stop_price=1, t1_price=1, t2_price=1,
                confidence=50, time_stop_minutes=60, valid=True,
            )


# ── 4. Gateway Decisions ─────────────────────────────────────────

class TestGatewayDecision:
    def test_shadow_only(self):
        d = GatewayDecision(
            ts="2026-05-18T10:00:00", system_id=2,
            shadow_trade_id=1,
            rejections=[
                GatewayRejection(mode="demo", reason="not enabled"),
                GatewayRejection(mode="live", reason="not enabled"),
            ],
        )
        assert d.demo_trade_id is None
        assert len(d.rejections) == 2

    def test_s3_footprint_accepted(self):
        """S3 is a valid firing system after P29 gateway fix."""
        d = GatewayDecision(
            ts="2026-05-18T10:00:00", system_id=3,
            shadow_trade_id=42,
        )
        assert d.system_id == 3

    def test_s1_rejected(self):
        """S1 is OBSERVING — not a valid firing system."""
        with pytest.raises(ValidationError, match="system_id"):
            GatewayDecision(
                ts="x", system_id=1, shadow_trade_id=1,
            )

    def test_s5_rejected(self):
        with pytest.raises(ValidationError, match="system_id"):
            GatewayDecision(ts="x", system_id=5, shadow_trade_id=1)


# ── 5. Reason Trees ─────────────────────────────────────────────

class TestReasonTree:
    def test_fire_tree(self):
        tree = ReasonTree(
            ts="2026-05-18T10:00:00", system_id=4,
            stages=[
                ReasonTreeStage(stage_id="A1", status=StageStatus.PASS, message="CCI setup found"),
                ReasonTreeStage(stage_id="A2", status=StageStatus.PASS, message="Trend confirmed"),
                ReasonTreeStage(stage_id="A3", status=StageStatus.PASS, message="Pattern valid"),
                ReasonTreeStage(stage_id="A4", status=StageStatus.PASS, message="Touchpoints OK"),
                ReasonTreeStage(stage_id="A5", status=StageStatus.PASS, message="Pre-fire pass"),
                ReasonTreeStage(stage_id="A6", status=StageStatus.PASS, message="Sizing: full"),
                ReasonTreeStage(stage_id="A7", status=StageStatus.PASS, message="Routed"),
            ],
            outcome="fire", classification="GHOST_ZERO_LINE", direction="LONG",
        )
        assert tree.outcome == "fire"
        assert len(tree.stages) == 7

    def test_block_tree(self):
        tree = ReasonTree(
            ts="2026-05-18T10:00:00", system_id=4,
            stages=[
                ReasonTreeStage(stage_id="A1", status=StageStatus.PASS, message="CCI found"),
                ReasonTreeStage(stage_id="A4", status=StageStatus.FAIL,
                                message="Killzone=WEEKEND", owner="touchpoint_api"),
            ],
            outcome="block",
        )
        assert tree.outcome == "block"

    def test_invalid_outcome_rejected(self):
        with pytest.raises(ValidationError, match="outcome"):
            ReasonTree(ts="x", system_id=2, stages=[], outcome="maybe")

    def test_delegated_stages(self):
        stage = ReasonTreeStage(
            stage_id="B1", status=StageStatus.DELEGATED,
            message="Managed by trade_manager", owner="trade_manager",
        )
        assert stage.status == StageStatus.DELEGATED


# ── 6. Lifecycle Events ─────────────────────────────────────────

class TestLifecycleEvent:
    def test_trade_opened(self):
        ev = LifecycleEvent(
            ts="2026-05-18T10:00:00", trade_id=1,
            event_type="trade.opened", to_state=TradeState.PENDING,
            mode="shadow",
        )
        assert ev.from_state is None

    def test_trade_filled(self):
        ev = LifecycleEvent(
            ts="2026-05-18T10:00:05", trade_id=1,
            event_type="trade.filled",
            from_state=TradeState.PENDING, to_state=TradeState.FILLED,
            mode="shadow", data={"fill_price": 7400.0},
        )
        assert ev.data["fill_price"] == 7400.0

    def test_trade_closed(self):
        ev = LifecycleEvent(
            ts="2026-05-18T10:30:00", trade_id=1,
            event_type="trade.closed",
            from_state=TradeState.FILLED, to_state=TradeState.CLOSED,
            mode="shadow", data={"exit_reason": "t1_hit", "pnl_usd": 25.0},
        )
        assert ev.to_state == TradeState.CLOSED

    def test_invalid_mode_rejected(self):
        with pytest.raises(ValidationError, match="mode"):
            LifecycleEvent(
                ts="x", trade_id=1, event_type="trade.opened",
                to_state=TradeState.PENDING, mode="real_money",
            )


# ── Retention Policy ─────────────────────────────────────────────

class TestRetentionPolicy:
    def test_all_categories_covered(self):
        expected = {"bars", "stream_health", "system_snapshots",
                    "pre_fire", "gateway", "reason_trees", "lifecycle"}
        assert set(RETENTION_POLICY.keys()) == expected

    def test_all_have_sink_and_ttl(self):
        for cat, policy in RETENTION_POLICY.items():
            assert "sink" in policy, f"{cat} missing sink"
            assert "ttl_days" in policy, f"{cat} missing ttl_days"
            assert policy["ttl_days"] > 0, f"{cat} ttl_days must be > 0"
