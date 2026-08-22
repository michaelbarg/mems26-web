"""S1_STRUCTURAL_BINARY_V1 — Event-driven binary day-type classifier.

Ruling: Michael 22.08 ("or day is one of the types or it isn't"), re-confirmed
as map §B spec.  Cancels confidence from the decision path.

WHY: The existing classifier (`classify_session`, per-bar) re-evaluates running
aggregates (sides/close_pos/rib) on every 5-min bar → 200 label flips in 54
sessions, 49% of intermediate runs are A→B→A, and `Trend_Normal` alive for
one minute (08-21 19:00→19:01).

WHAT CHANGES: the criteria stay byte-identical (they're already Dalton-binary).
The **publication semantics** change from "re-evaluate on every bar" to "label
changes only on structural events":
  (a) IB lock (bar 12 = session_min 60)
  (b) first acceptance beyond a reference (2 closes + volume)
  (c) acceptance of SECOND side → immediate Neutral
  (d) failed-break revert (accepted, then closes return inside)
  (e) DD neck formation or refill
  (f) round-trip through the opening price
  (g) EOD

Between events the label is HELD — no churn, no A→B→A.

WHAT THIS MODULE IS: a pure-function shadow wrapper around classify_session.
On each bar, it:
  1. Detects whether a structural event occurred (from feature deltas)
  2. If yes: re-classify and publish the new label
  3. If no: hold the previous label
  4. Log both old and new for shadow comparison

Consumers get `{label, determined: bool, direction}` — no confidence field.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def enabled() -> bool:
    return os.getenv("S1_STRUCTURAL_BINARY_V1", "0").lower() in (
        "1", "true", "yes", "shadow")


def shadow_only() -> bool:
    return os.getenv("S1_STRUCTURAL_BINARY_V1", "0").lower() == "shadow"


class StructuralBinaryClassifier:
    """Event-driven binary classifier (shadow or live).

    Keeps minimal state: the held label, the last structural features,
    and the bar count.  All classification is delegated to classify_session.
    """

    def __init__(self) -> None:
        self._label: Optional[str] = None
        self._determined: bool = False
        self._direction: Optional[str] = None
        self._bar_count: int = 0
        self._ib_locked: bool = False
        self._prev_sides: int = 0
        self._prev_accepted_break: Optional[str] = None
        self._prev_dd: bool = False
        self._prev_returned: bool = False
        self._prev_failed_break: bool = False
        self._transitions: int = 0
        self._session_date: Optional[str] = None

    def reset(self, session_date: str) -> None:
        """Reset for a new session."""
        self.__init__()
        self._session_date = session_date

    def on_bar(self, cls_result: Dict[str, Any], bar_count: int) -> Dict[str, Any]:
        """Process one bar's classify_session result.

        Returns {label, determined, direction, event, transition, held}.
        """
        self._bar_count = bar_count
        candidate = cls_result.get("day_type", "FORMING")
        measured = cls_result.get("measured") or {}
        cur_sides = measured.get("sides", 0) or 0
        cur_accepted = cls_result.get("accepted_break") if "accepted_break" in cls_result else None
        cur_dd = bool(cls_result.get("dd_second_dist") or
                      (measured and measured.get("dd_second_dist")))
        cur_returned = bool(cls_result.get("returned_through_open") or
                           (measured and measured.get("returned_through_open")))
        cur_failed = bool(cls_result.get("failed_break") or
                         (measured and measured.get("failed_break")))

        # Detect structural events
        event = self._detect_event(
            bar_count, cur_sides, cur_accepted, cur_dd,
            cur_returned, cur_failed, candidate)

        # Update previous state
        self._prev_sides = cur_sides
        self._prev_accepted_break = cur_accepted
        self._prev_dd = cur_dd
        self._prev_returned = cur_returned
        self._prev_failed_break = cur_failed

        transition = False
        if event:
            # Structural event → re-classify (use the candidate from classify_session)
            if candidate not in ("FORMING", "UNKNOWN", "INDETERMINATE", ""):
                if candidate != self._label:
                    transition = True
                    self._transitions += 1
                self._label = candidate
                self._determined = self._ib_locked
                self._direction = cls_result.get("direction")
        elif self._label is None and candidate not in (
                "FORMING", "UNKNOWN", "INDETERMINATE", ""):
            # First valid label — always accept
            self._label = candidate
            self._determined = self._ib_locked
            self._direction = cls_result.get("direction")
            transition = True
            self._transitions += 1

        return {
            "label": self._label or "NOT_YET",
            "determined": self._determined,
            "direction": self._direction,
            "event": event,
            "transition": transition,
            "held": not event and self._label is not None,
            "candidate": candidate,
            "transitions_today": self._transitions,
            "bar_count": self._bar_count,
        }

    def _detect_event(self, bar_count: int, sides: int,
                      accepted_break: Optional[str], dd: bool,
                      returned: bool, failed_break: bool,
                      candidate: str) -> Optional[str]:
        """Detect whether a structural event occurred on this bar.

        Returns event name or None (hold).
        """
        # (a) IB lock — bar 12 (session_min ~60)
        if bar_count == 12 and not self._ib_locked:
            self._ib_locked = True
            return "ib_lock"

        # (b) First acceptance beyond reference
        if accepted_break and accepted_break != self._prev_accepted_break:
            return f"acceptance_{accepted_break}"

        # (c) Second side acceptance → Neutral
        if sides == 2 and self._prev_sides < 2:
            return "dual_ib_break"

        # (d) Failed-break revert
        if failed_break and not self._prev_failed_break:
            return "failed_break_revert"

        # (e) DD neck formation
        if dd and not self._prev_dd:
            return "dd_neck_formed"

        # (f) Round-trip through opening
        if returned and not self._prev_returned:
            return "round_trip_open"

        return None

    def get_state(self) -> Dict[str, Any]:
        """Current state for API/status."""
        return {
            "label": self._label,
            "determined": self._determined,
            "direction": self._direction,
            "ib_locked": self._ib_locked,
            "bar_count": self._bar_count,
            "transitions_today": self._transitions,
        }


# Module-level singleton
_instance: Optional[StructuralBinaryClassifier] = None


def get_classifier() -> StructuralBinaryClassifier:
    global _instance
    if _instance is None:
        _instance = StructuralBinaryClassifier()
    return _instance
