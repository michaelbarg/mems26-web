"""Woodies Active Phase Engine (PROMPT 2 · 2.3).

Routes through B1 → B14 per priority hierarchy:
  ABSOLUTE_EXIT > STRATEGIC_EXIT > ADVISORY_EXIT > TIME_EXIT >
  TARGET > TIGHTEN > PARTIAL > TRAIL > NO_ACTION

Within same priority class, YAML order determines.
Highest-priority action wins; others skipped that bar.

STATUS (Prompt 23): NOT the active runtime path.
  Active runtime: B1-B14 are DELEGATED to services/trade_manager + services/layer4.
  This module is an ALTERNATIVE YAML-driven orchestrator.
  BarLevelDetector handles hit detection; layer4 rules handle tighten/trail/exit.
Reference: Decision Tree V1 § Section 5.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from backend.v9.systems.woodies.yaml_loader import (
    WoodiesConfig,
    get_active_stages,
    load,
)
from backend.v9.systems.woodies.stages.b1_stop_check import B1StopCheck
from backend.v9.systems.woodies.stages.b2_eod_check import B2EodCheck
from backend.v9.systems.woodies.stages.b3_color_flip import B3ColorFlip
from backend.v9.systems.woodies.stages.b4_poc_migration_query import B4PocMigrationQuery
from backend.v9.systems.woodies.stages.b5_otf_mid_trade_query import B5OtfMidTradeQuery
from backend.v9.systems.woodies.stages.b6_news_window import B6NewsWindow
from backend.v9.systems.woodies.stages.b7_time_stop import B7TimeStop
from backend.v9.systems.woodies.stages.b8_counter_pattern import B8CounterPattern
from backend.v9.systems.woodies.stages.b9_market_state_query import B9MarketStateQuery
from backend.v9.systems.woodies.stages.b10_t1_milestone import B10T1Milestone
from backend.v9.systems.woodies.stages.b11_t2_milestone import B11T2Milestone
from backend.v9.systems.woodies.stages.b12_t3_milestone import B12T3Milestone
from backend.v9.systems.woodies.stages.b13_trail_check import B13TrailCheck
from backend.v9.systems.woodies.stages.b14_hold import B14Hold

logger = logging.getLogger(__name__)


class ActiveAction(str, Enum):
    """Actions the active phase can return."""
    CLOSE_ALL = "CLOSE_ALL"
    CLOSE_C1 = "CLOSE_C1"
    CLOSE_C2 = "CLOSE_C2"
    CLOSE_C3 = "CLOSE_C3"
    TIGHTEN = "TIGHTEN"
    PARTIAL_CLOSE = "PARTIAL_CLOSE"
    REDUCE = "REDUCE"
    HOLD = "HOLD"


@dataclass
class ActiveResult:
    """Result of active phase evaluation."""
    action: ActiveAction
    source_stage: str  # which stage produced the winning action
    reason: str
    stage_outputs: Dict[str, object]  # stage_id → output dataclass


# ── Stage registry ────────────────────────────────────────────────

STAGE_CLASSES = {
    "B1_stop_check": B1StopCheck,
    "B2_eod_check": B2EodCheck,
    "B3_color_flip": B3ColorFlip,
    "B4_poc_migration_query": B4PocMigrationQuery,
    "B5_otf_mid_trade_query": B5OtfMidTradeQuery,
    "B6_news_window": B6NewsWindow,
    "B7_time_stop": B7TimeStop,
    "B8_counter_pattern": B8CounterPattern,
    "B9_market_state_query": B9MarketStateQuery,
    "B10_t1_milestone": B10T1Milestone,
    "B11_t2_milestone": B11T2Milestone,
    "B12_t3_milestone": B12T3Milestone,
    "B13_trail_check": B13TrailCheck,
    "B14_hold": B14Hold,
}


class ActivePhaseEngine:
    """Routes through active phase stages B1-B14 per priority hierarchy.

    Each stage is instantiated from the registry and called in
    the order determined by get_active_stages() (sorted by priority_class
    rank, then YAML order within same class).

    Highest-priority action wins; lower-priority stages still run for
    logging but don't override.

    STUB: Returns HOLD for all evaluations (PROMPT 3 adds real dispatcher).
    """

    def __init__(self, config: Optional[WoodiesConfig] = None):
        self.config = config or load()
        self._stages = {}
        for spec in get_active_stages(self.config):
            cls = STAGE_CLASSES.get(spec.id)
            if cls:
                self._stages[spec.id] = cls()

    @property
    def stage_order(self):
        """Return ordered list of enabled stage IDs (by priority hierarchy)."""
        return list(self._stages.keys())

    def evaluate(
        self,
        position_context: Optional[dict] = None,
        bar_context: Optional[dict] = None,
    ) -> ActiveResult:
        """Route through B1 → B14 per priority hierarchy.

        Highest-priority action wins.
        STUB: returns HOLD (logic in PROMPT 3).
        """
        outputs = {}

        for stage_id, stage in self._stages.items():
            # STUB: call each stage with minimal args for wiring verification
            if stage_id == "B1_stop_check":
                output = stage.evaluate(current_price=0, stop_price=0, direction="NONE")
            elif stage_id == "B2_eod_check":
                output = stage.evaluate(current_time_et="12:00")
            elif stage_id == "B3_color_flip":
                output = stage.evaluate(current_color="BLUE", entry_color="BLUE", direction="LONG")
            elif stage_id == "B4_poc_migration_query":
                output = stage.evaluate()
            elif stage_id == "B5_otf_mid_trade_query":
                output = stage.evaluate()
            elif stage_id == "B6_news_window":
                output = stage.evaluate()
            elif stage_id == "B7_time_stop":
                output = stage.evaluate()
            elif stage_id == "B8_counter_pattern":
                output = stage.evaluate()
            elif stage_id == "B9_market_state_query":
                output = stage.evaluate()
            elif stage_id == "B10_t1_milestone":
                output = stage.evaluate(current_price=0, t1_price=0, direction="NONE")
            elif stage_id == "B11_t2_milestone":
                output = stage.evaluate(current_price=0, t2_price=0, direction="NONE")
            elif stage_id == "B12_t3_milestone":
                output = stage.evaluate(current_price=0, t3_price=0, direction="NONE")
            elif stage_id == "B13_trail_check":
                output = stage.evaluate()
            elif stage_id == "B14_hold":
                output = stage.evaluate()
            else:
                continue

            outputs[stage_id] = output
            logger.debug("[Woodies Active] %s → %s", stage_id, output)

        # STUB: always HOLD (real dispatcher logic in PROMPT 3)
        return ActiveResult(
            action=ActiveAction.HOLD,
            source_stage="B14_hold",
            reason="STUB_NOT_IMPLEMENTED",
            stage_outputs=outputs,
        )
