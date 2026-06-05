"""Should-Have-Fired detector — observability only, no trading logic changes.

Rolling 6-bar lookback from RTH open (08:30 CT). On each bar, checks whether
a quality setup was detected but blocked by a gate, or a clean directional move
occurred that no pattern captured.

Persists candidates to v9_missed_trades for daily learning/calibration.
Exposes via get_missed_trades() for build_status API.

Michael spec (2026-06-05): lookback of 6 bars from open, every bar.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Thresholds — proposed defaults, pending Michael's approval
MOVE_THRESHOLD_PTS = 15.0   # Minimum directional move in 6-bar window to flag
MIN_BARS_FOR_ANALYSIS = 3   # Need at least 3 bars before analyzing


class MissedTradeCandidate:
    """A setup that should have fired but didn't."""

    def __init__(
        self,
        ts_ct: str,
        candidate_type: str,      # "blocked_signal" or "uncaptured_move"
        pattern: Optional[str],    # Pattern name if detected
        system: str,               # "S2" / "S4" / "move"
        direction: str,            # "LONG" / "SHORT"
        entry_price: float,
        why_not: str,              # Gate that blocked or "not_detected"
        hypothetical_r: Optional[float] = None,
    ):
        self.ts_ct = ts_ct
        self.candidate_type = candidate_type
        self.pattern = pattern
        self.system = system
        self.direction = direction
        self.entry_price = entry_price
        self.why_not = why_not
        self.hypothetical_r = hypothetical_r

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts_ct": self.ts_ct,
            "type": self.candidate_type,
            "pattern": self.pattern,
            "system": self.system,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "why_not": self.why_not,
            "hypothetical_r": self.hypothetical_r,
        }


class MissedTradeDetector:
    """Rolling 6-bar lookback detector for missed trades."""

    def __init__(self, lookback: int = 6, move_threshold: float = MOVE_THRESHOLD_PTS):
        self._lookback = lookback
        self._move_threshold = move_threshold
        self._bar_history: List[Dict] = []
        self._candidates: List[MissedTradeCandidate] = []
        self._last_reasoning: Dict[str, str] = {}  # Last S2/S4 reasoning notes

    def on_bar(self, bar: Dict, s2_state: Dict, s4_state: Dict) -> None:
        """Process a new 5-min bar. Called from main loop on each RTH bar.

        Args:
            bar: {ts_ct, open, high, low, close, volume}
            s2_state: FiveMinSystem.get_state() snapshot
            s4_state: WoodiesSystem current_state snapshot
        """
        self._bar_history.append(bar)
        if len(self._bar_history) > 100:
            self._bar_history = self._bar_history[-100:]

        if len(self._bar_history) < MIN_BARS_FOR_ANALYSIS:
            return

        window = self._bar_history[-self._lookback:]

        # Check 1: S2 detected pattern but blocked
        s2_pattern = s2_state.get("last_pattern")
        s2_reasoning = s2_state.get("last_reasoning_notes", "")
        if s2_pattern and "reject" in str(s2_reasoning).lower():
            # Extract the gate from reasoning
            gate = "unknown"
            if "location=far" in s2_reasoning:
                gate = "size=reject (location=far from POC)"
            elif "size=reject" in s2_reasoning:
                gate = "size=reject"
            elif "choppiness" in s2_reasoning.lower():
                gate = "choppiness_gate"

            # Only add if this is a new pattern (not duplicate from last bar)
            if s2_reasoning != self._last_reasoning.get("s2"):
                self._candidates.append(MissedTradeCandidate(
                    ts_ct=bar.get("ts_ct", "?"),
                    candidate_type="blocked_signal",
                    pattern=s2_pattern,
                    system="S2",
                    direction="SHORT" if "SHORT" in s2_pattern else "LONG",
                    entry_price=bar.get("close", 0),
                    why_not=gate,
                ))
                self._last_reasoning["s2"] = s2_reasoning

        # Check 2: S4 detected pattern but not routed
        s4_patterns = s4_state.get("active_patterns", [])
        s4_ready = s4_state.get("ready_to_route", False)
        if s4_patterns and not s4_ready:
            for p in s4_patterns:
                if isinstance(p, dict):
                    pid = p.get("pattern_id", "?")
                    self._candidates.append(MissedTradeCandidate(
                        ts_ct=bar.get("ts_ct", "?"),
                        candidate_type="blocked_signal",
                        pattern=pid,
                        system="S4",
                        direction=p.get("direction", "?"),
                        entry_price=bar.get("close", 0),
                        why_not="ready_to_route=False",
                    ))

        # Check 3: Clean directional move with no signal
        if len(window) >= self._lookback:
            first_close = window[0].get("close", 0)
            last_close = window[-1].get("close", 0)
            move = last_close - first_close
            abs_move = abs(move)

            if abs_move >= self._move_threshold:
                direction = "LONG" if move > 0 else "SHORT"
                # Check if any pattern was detected in this window
                if not s2_pattern and not s4_patterns:
                    self._candidates.append(MissedTradeCandidate(
                        ts_ct=bar.get("ts_ct", "?"),
                        candidate_type="uncaptured_move",
                        pattern=None,
                        system="move",
                        direction=direction,
                        entry_price=first_close,
                        why_not=f"no_pattern_detected (move={abs_move:.1f}pts in {self._lookback} bars)",
                    ))

        # Cap candidates
        if len(self._candidates) > 50:
            self._candidates = self._candidates[-50:]

    def get_candidates(self) -> List[Dict]:
        """Return all candidates for API/build_status."""
        return [c.to_dict() for c in self._candidates]

    def persist_daily(self) -> int:
        """Persist today's candidates to DB. Returns count persisted."""
        if not self._candidates:
            return 0
        try:
            from backend.v9.db.safe_writer import safe_execute
            import json
            count = 0
            for c in self._candidates:
                result = safe_execute(
                    "INSERT INTO v9_system_signals (ts, system_id, classification, direction, payload) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        datetime.now(timezone.utc).isoformat(),
                        0,  # system_id 0 = missed-trade detector
                        f"MISSED_{c.candidate_type.upper()}",
                        c.direction,
                        json.dumps(c.to_dict()),
                    ),
                )
                if result is not None:
                    count += 1
            logger.info("[MissedTrades] Persisted %d candidates to v9_system_signals", count)
            return count
        except Exception as e:
            logger.warning("[MissedTrades] Persist failed: %s", e)
            return 0


# Singleton
missed_trade_detector = MissedTradeDetector()
