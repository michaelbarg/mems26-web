"""Stage A4 — POC + Suffering Side Query · Touch-Point (PROMPT 3 · 3.3).

Purpose: Get POC location + Suffering Side to classify entry type + warn on thesis risk.
Reference: Decision Tree V1 § Section 4 · A4
Type: Touch-Point (advisory only · NEVER vetoes)
Blocking: false
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Within this distance (pts) of IB/VA edge → REACTIVE hint
REACTIVE_EDGE_DISTANCE = 3.0


@dataclass
class A4Output:
    """A4 stage output."""
    entry_classification_hint: str  # "REACTIVE" | "INITIATIVE" | "UNCLEAR"
    suffering_warning: str  # "SUFFERING_SIDE" | "NONE"
    bypass_active: str  # "UFL" | "UFH" | "NONE"


class A4PocSufferingQuery:
    """Stage A4 — POC + Suffering Side Query (Touch-Point).

    Queries /api/v9/tpo/current (POC, UFL/UFH) and /api/v9/veto/state (suffering_side).
    Classifies entry as REACTIVE vs INITIATIVE based on price vs IB/VA.
    Warns if on suffering side (but NEVER blocks — RULE 14).
    UFL/UFH zones bypass suffering check.

    Degraded mode: INITIATIVE default, skip suffering warning
    Terminal states: None (advisory only)
    """

    def evaluate(
        self,
        entry_direction: Optional[str] = None,
        current_price: Optional[float] = None,
        poc_location: Optional[float] = None,
        suffering_side: Optional[str] = None,
        ufl_ufh: Optional[dict] = None,
        ib_high: Optional[float] = None,
        ib_low: Optional[float] = None,
        vah: Optional[float] = None,
        val: Optional[float] = None,
    ) -> A4Output:
        """Evaluate POC + suffering side per Decision Tree V1 § A4.

        Advisory only — returns hints/warnings, NEVER blocks entry.
        """
        # Degraded mode: no data available
        if current_price is None or poc_location is None:
            logger.debug("[A4] POC/price unavailable — degraded mode")
            return A4Output(
                entry_classification_hint="INITIATIVE",
                suffering_warning="NONE",
                bypass_active="NONE",
            )

        # Check UFL/UFH bypass
        bypass = "NONE"
        if ufl_ufh:
            ufl = ufl_ufh.get("ufl")
            ufh = ufl_ufh.get("ufh")
            if ufl is not None and current_price <= ufl:
                bypass = "UFL"
            elif ufh is not None and current_price >= ufh:
                bypass = "UFH"

        # Classification hint based on price location
        hint = "UNCLEAR"
        if ib_high is not None and ib_low is not None:
            near_ib_high = abs(current_price - ib_high) <= REACTIVE_EDGE_DISTANCE
            near_ib_low = abs(current_price - ib_low) <= REACTIVE_EDGE_DISTANCE
            near_vah = vah is not None and abs(current_price - vah) <= REACTIVE_EDGE_DISTANCE
            near_val = val is not None and abs(current_price - val) <= REACTIVE_EDGE_DISTANCE

            if near_ib_high or near_ib_low or near_vah or near_val:
                hint = "REACTIVE"
            elif poc_location and entry_direction:
                # Near middle + POC migrating in entry direction
                if entry_direction == "LONG" and current_price > poc_location:
                    hint = "INITIATIVE"
                elif entry_direction == "SHORT" and current_price < poc_location:
                    hint = "INITIATIVE"
                else:
                    hint = "UNCLEAR"

        # Suffering side warning (advisory only — NEVER blocks)
        warning = "NONE"
        if bypass == "NONE" and suffering_side and entry_direction:
            # suffering_side indicates which side is suffering
            # If we're entering on the suffering side → warning
            if suffering_side == "BUYERS" and entry_direction == "LONG":
                warning = "SUFFERING_SIDE"
            elif suffering_side == "SELLERS" and entry_direction == "SHORT":
                warning = "SUFFERING_SIDE"

        return A4Output(
            entry_classification_hint=hint,
            suffering_warning=warning,
            bypass_active=bypass,
        )
