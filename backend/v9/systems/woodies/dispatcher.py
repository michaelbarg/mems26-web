"""Woodies Priority Hierarchy Dispatcher (PROMPT 3 · 3.1).

Single routing function that resolves which action to take when
multiple stages trigger on the same bar.

Priority hierarchy (per Decision Tree V1 § Core Principles):
  ABSOLUTE_EXIT > STRATEGIC_EXIT > ADVISORY_EXIT > TIME_EXIT >
  TARGET > TIGHTEN > PARTIAL > TRAIL > NO_ACTION

Within same priority class, YAML order determines (earlier wins).
"""

import logging
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional

logger = logging.getLogger(__name__)


class PriorityClass(IntEnum):
    """Priority classes ordered highest (1) to lowest (9)."""
    ABSOLUTE_EXIT = 1
    STRATEGIC_EXIT = 2
    ADVISORY_EXIT = 3
    TIME_EXIT = 4
    TARGET = 5
    TIGHTEN = 6
    PARTIAL = 7
    TRAIL = 8
    NO_ACTION = 9


@dataclass
class StageOutput:
    """Output from a single stage evaluation."""
    stage_id: str
    priority_class: PriorityClass
    action: str  # "CLOSE_ALL", "CLOSE_C1", "TIGHTEN", "HOLD", etc.
    triggered: bool  # True if this stage wants to act (not HOLD/NoOp)
    yaml_order: int = 0  # position in YAML config (for tie-breaking)
    reason: str = ""
    details: Optional[dict] = None


@dataclass
class DispatchResult:
    """Result of dispatcher resolution."""
    winning_stage: str  # stage_id of the winner
    winning_action: str  # action to take
    winning_priority: PriorityClass
    reason: str
    all_triggered: List[str]  # all stage_ids that triggered (for logging)


class Dispatcher:
    """Resolves priority conflicts between stage outputs.

    Accepts a list of StageOutput from all evaluated stages,
    filters to those that triggered, sorts by (priority_class, yaml_order),
    and returns the highest-priority action.
    """

    def resolve(self, stage_outputs: List[StageOutput]) -> DispatchResult:
        """Resolve which action wins from a list of stage outputs.

        Sort by (priority_class, yaml_order). Return highest-priority.
        Tie-breaking: earlier in YAML (lower yaml_order) wins.

        If no stage triggered, returns B14_hold / HOLD / NO_ACTION.
        """
        triggered = [s for s in stage_outputs if s.triggered]

        if not triggered:
            return DispatchResult(
                winning_stage="B14_hold",
                winning_action="HOLD",
                winning_priority=PriorityClass.NO_ACTION,
                reason="No stage triggered — default HOLD",
                all_triggered=[],
            )

        # Sort: lowest priority_class number wins, then lowest yaml_order
        triggered.sort(key=lambda s: (s.priority_class, s.yaml_order))

        winner = triggered[0]
        all_ids = [s.stage_id for s in triggered]

        if len(triggered) > 1:
            logger.info(
                "[Woodies Dispatcher] %d stages triggered: %s → winner: %s (%s)",
                len(triggered),
                all_ids,
                winner.stage_id,
                winner.priority_class.name,
            )

        return DispatchResult(
            winning_stage=winner.stage_id,
            winning_action=winner.action,
            winning_priority=winner.priority_class,
            reason=winner.reason,
            all_triggered=all_ids,
        )
