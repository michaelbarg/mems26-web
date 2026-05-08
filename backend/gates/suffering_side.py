"""
Suffering Side Veto Gate.

Source: D-049, D-065
Methodology: Michael's notes (חוזים.docx, "Suffering Side Rule")
Quote: "אנחנו אף פעם לא מצטרפים לצד הסובל"

Logic per D-065:
  NO_TRADE_ZONE_PT = 2.0

  if abs(price - day_poc) <= NO_TRADE_ZONE_PT:
      BLOCK("inside POC no-trade zone")
  elif direction == LONG and price < day_poc - NO_TRADE_ZONE_PT:
      BLOCK("below POC — buyers suffer")
  elif direction == SHORT and price > day_poc + NO_TRADE_ZONE_PT:
      BLOCK("above POC — sellers suffer")
  else:
      PASS("clear of POC zone")

Behavior:
- Accepts day_poc as argument (caller fetches from Redis)
- If day_poc is None/0: FAIL-OPEN (PASS with warning) or FAIL-CLOSED via mode param
- Feature flag via MEMS26_SUFFERING_SIDE_ENABLED env var
"""

import logging
import os
from dataclasses import dataclass, asdict
from typing import Optional, Literal
from datetime import datetime, timezone

log = logging.getLogger("gates.suffering_side")

# Constants from D-065
NO_TRADE_ZONE_PT = 2.0

# Feature flag for emergency disable
GATE_ENABLED = os.getenv("MEMS26_SUFFERING_SIDE_ENABLED", "true").lower() == "true"


@dataclass
class GateResult:
    """Result of a gate check."""
    gate: str
    result: Literal["PASS", "BLOCK", "WARNING"]
    reason: str
    details: dict
    source_decision: str
    source_quote: str
    timestamp: str

    def to_dict(self) -> dict:
        return asdict(self)


def check_suffering_side(
    direction: str,
    price: float,
    day_poc: Optional[float] = None,
    mode: str = "open",
) -> GateResult:
    """
    Check Suffering Side Veto for a trade setup.

    Args:
        direction: "LONG" or "SHORT"
        price: Entry price
        day_poc: Day POC value, or None if unavailable
        mode: "open" (fail-open if no POC) or "closed" (fail-closed)

    Returns:
        GateResult with PASS, BLOCK, or WARNING.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # Feature flag check
    if not GATE_ENABLED:
        log.warning("Suffering Side gate DISABLED via env var")
        return GateResult(
            gate="suffering_side",
            result="WARNING",
            reason="gate_disabled",
            details={"feature_flag": False},
            source_decision="D-049, D-065",
            source_quote="אנחנו אף פעם לא מצטרפים לצד הסובל",
            timestamp=timestamp,
        )

    # Validate direction
    direction = direction.upper()
    if direction not in ("LONG", "SHORT"):
        log.error(f"Invalid direction: {direction}")
        return GateResult(
            gate="suffering_side",
            result="WARNING",
            reason="invalid_direction",
            details={"direction": direction},
            source_decision="D-049, D-065",
            source_quote="אנחנו אף פעם לא מצטרפים לצד הסובל",
            timestamp=timestamp,
        )

    # Handle missing/stale day_poc
    if day_poc is None or day_poc <= 0:
        if mode == "closed":
            log.warning("Suffering Side: day_poc unavailable, BLOCKING (fail-closed)")
            return GateResult(
                gate="suffering_side",
                result="BLOCK",
                reason="day_poc_unavailable_fail_closed",
                details={"direction": direction, "price": price, "day_poc": None, "mode": "closed"},
                source_decision="D-049, D-065",
                source_quote="אנחנו אף פעם לא מצטרפים לצד הסובל",
                timestamp=timestamp,
            )
        else:
            log.warning("Suffering Side: day_poc unavailable, PASSING (fail-open)")
            return GateResult(
                gate="suffering_side",
                result="WARNING",
                reason="day_poc_unavailable_fail_open",
                details={
                    "direction": direction, "price": price, "day_poc": None,
                    "mode": "open",
                    "warning": "Gate cannot enforce until DLL populates day_poc",
                },
                source_decision="D-049, D-065",
                source_quote="אנחנו אף פעם לא מצטרפים לצד הסובל",
                timestamp=timestamp,
            )

    # Compute distance from POC
    distance_pts = abs(price - day_poc)

    # D-065 logic
    if distance_pts <= NO_TRADE_ZONE_PT:
        return GateResult(
            gate="suffering_side",
            result="BLOCK",
            reason="inside_no_trade_zone",
            details={
                "direction": direction, "price": price, "day_poc": day_poc,
                "distance_pts": round(distance_pts, 2),
                "no_trade_zone_pts": NO_TRADE_ZONE_PT,
                "decision_logic": f"Inside ±{NO_TRADE_ZONE_PT}pt zone of POC",
            },
            source_decision="D-049, D-065",
            source_quote="אנחנו אף פעם לא מצטרפים לצד הסובל",
            timestamp=timestamp,
        )

    if direction == "LONG" and price < day_poc - NO_TRADE_ZONE_PT:
        return GateResult(
            gate="suffering_side",
            result="BLOCK",
            reason="below_poc_buyers_suffer",
            details={
                "direction": "LONG", "price": price, "day_poc": day_poc,
                "distance_pts": round(distance_pts, 2),
                "no_trade_zone_pts": NO_TRADE_ZONE_PT,
                "decision_logic": f"price < day_poc - {NO_TRADE_ZONE_PT} → buyers suffer",
            },
            source_decision="D-049, D-065",
            source_quote="לא נעשה לונג שאנחנו מתחת ל POC",
            timestamp=timestamp,
        )

    if direction == "SHORT" and price > day_poc + NO_TRADE_ZONE_PT:
        return GateResult(
            gate="suffering_side",
            result="BLOCK",
            reason="above_poc_sellers_suffer",
            details={
                "direction": "SHORT", "price": price, "day_poc": day_poc,
                "distance_pts": round(distance_pts, 2),
                "no_trade_zone_pts": NO_TRADE_ZONE_PT,
                "decision_logic": f"price > day_poc + {NO_TRADE_ZONE_PT} → sellers suffer",
            },
            source_decision="D-049, D-065",
            source_quote="אנחנו אף פעם לא מצטרפים לצד הסובל",
            timestamp=timestamp,
        )

    # PASS — direction aligns with dominant side
    return GateResult(
        gate="suffering_side",
        result="PASS",
        reason="clear_of_poc_zone",
        details={
            "direction": direction, "price": price, "day_poc": day_poc,
            "distance_pts": round(distance_pts, 2),
            "no_trade_zone_pts": NO_TRADE_ZONE_PT,
            "decision_logic": f"price clear of POC zone, {direction} is on dominant side",
        },
        source_decision="D-049, D-065",
        source_quote="אנחנו אף פעם לא מצטרפים לצד הסובל",
        timestamp=timestamp,
    )
