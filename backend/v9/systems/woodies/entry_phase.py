"""Woodies Entry Phase Engine (PROMPT 2 · 2.2).

Routes through A1 → A7 per YAML config order.
Each stage runs, output feeds next stage.
Returns a TerminalState: SKIP, BUY, or SELL.

STATUS (Prompt 23): NOT the active runtime path.
  Active runtime: WoodiesSystem.process_bar() → decision_tree.evaluate_bar() → gateway.
  This module is an ALTERNATIVE YAML-driven orchestrator.
  Kept for future migration to full 21-stage internal architecture.
Reference: Decision Tree V1 § Section 4.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from backend.v9.systems.woodies.yaml_loader import (
    WoodiesConfig,
    get_entry_stages,
    load,
)
from backend.v9.systems.woodies.stages.a1_strategic_gate import A1StrategicGate
from backend.v9.systems.woodies.stages.a2_day_type_query import A2DayTypeQuery
from backend.v9.systems.woodies.stages.a3_pattern_detection import A3PatternDetection
from backend.v9.systems.woodies.stages.a4_poc_suffering_query import A4PocSufferingQuery
from backend.v9.systems.woodies.stages.a5_otf_clarity_query import A5OtfClarityQuery
from backend.v9.systems.woodies.stages.a6_entry_classification import A6EntryClassification
from backend.v9.systems.woodies.stages.a7_universal_checks import A7UniversalChecks

logger = logging.getLogger(__name__)


class EntryTerminal(str, Enum):
    """Terminal states for the entry phase."""
    SKIP = "SKIP"
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class EntryResult:
    """Result of entry phase evaluation."""
    terminal: EntryTerminal
    reason: str
    stage_outputs: Dict[str, object]  # stage_id → output dataclass


# ── Stage registry ────────────────────────────────────────────────

STAGE_CLASSES = {
    "A1_strategic_gate": A1StrategicGate,
    "A2_day_type_query": A2DayTypeQuery,
    "A3_pattern_detection": A3PatternDetection,
    "A4_poc_suffering_query": A4PocSufferingQuery,
    "A5_otf_clarity_query": A5OtfClarityQuery,
    "A6_entry_classification": A6EntryClassification,
    "A7_universal_checks": A7UniversalChecks,
}


class EntryPhaseEngine:
    """Routes through entry phase stages A1-A7 per config order.

    Each stage is instantiated from the registry and called in
    the order determined by get_entry_stages() (sorted by reorder_priority,
    filtered by enabled).

    STUB: Returns SKIP for all evaluations (PROMPT 3 adds real routing).
    """

    def __init__(self, config: Optional[WoodiesConfig] = None):
        self.config = config or load()
        self._stages = {}
        for spec in get_entry_stages(self.config):
            cls = STAGE_CLASSES.get(spec.id)
            if cls:
                self._stages[spec.id] = cls()

    @property
    def stage_order(self):
        """Return ordered list of enabled stage IDs."""
        return list(self._stages.keys())

    def evaluate(self, bar_context: Optional[dict] = None) -> EntryResult:
        """Route through A1 → A7 per YAML order.

        Each stage runs, output feeds next.
        Returns one of: SKIP, BUY, SELL.
        STUB: returns SKIP for now (logic in PROMPT 3).
        """
        outputs = {}

        for stage_id, stage in self._stages.items():
            # STUB: call each stage with minimal args for wiring verification
            if stage_id == "A1_strategic_gate":
                output = stage.evaluate(cci_14_value=0.0, cci_14_history=[])
            elif stage_id == "A2_day_type_query":
                output = stage.evaluate()
            elif stage_id == "A3_pattern_detection":
                output = stage.evaluate(cci_14_history=[], cci_zero_line_distance=0.0)
            elif stage_id == "A4_poc_suffering_query":
                output = stage.evaluate()
            elif stage_id == "A5_otf_clarity_query":
                output = stage.evaluate()
            elif stage_id == "A6_entry_classification":
                output = stage.evaluate(pattern_matched="NONE")
            elif stage_id == "A7_universal_checks":
                output = stage.evaluate(direction="NONE")
            else:
                continue

            outputs[stage_id] = output
            logger.debug("[Woodies Entry] %s → %s", stage_id, output)

        # STUB: always SKIP (real routing logic in PROMPT 3)
        return EntryResult(
            terminal=EntryTerminal.SKIP,
            reason="STUB_NOT_IMPLEMENTED",
            stage_outputs=outputs,
        )
