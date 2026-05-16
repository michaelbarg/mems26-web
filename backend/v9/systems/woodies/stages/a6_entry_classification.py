"""Stage A6 — Entry Classification (PROMPT 3 · 3.2).

Purpose: Final classification of entry as REACTIVE or INITIATIVE.
Reference: Decision Tree V1 § Section 4 · A6
Type: Woodies Core (uses A4 hint but decides independently)
"""

from dataclasses import dataclass
from typing import Optional

# Pattern → classification mapping per Decision Tree V1 § A6
REACTIVE_PATTERNS = {"HFE", "FAMIR", "TT"}
INITIATIVE_PATTERNS = {"VEGAS", "GHOST", "TLB", "HTLB", "ZLR", "GB100"}


@dataclass
class A6Output:
    """A6 stage output."""
    entry_classification: str  # "REACTIVE" | "INITIATIVE"
    position_size: int  # 2 (Reactive) | 3 (Initiative)
    management_profile: str  # "TIGHT" (Reactive) | "WIDE" (Initiative)


class A6EntryClassification:
    """Stage A6 — Entry Classification.

    Classifies entry based on pattern type + A4 hint:
      Pattern-based: HFE/FAMIR/TT_extreme → REACTIVE
                     VEGAS/GHOST/TLB/HTLB/ZLR_mid → INITIATIVE
      A4 hint can confirm but NOT override pattern decision (Woodies wins).

    Position sizing: Reactive=2 contracts, Initiative=3 contracts
    Management: Reactive=TIGHT, Initiative=WIDE

    Terminal states: None (continues to A7)
    """

    def evaluate(
        self,
        pattern_matched: str,
        entry_classification_hint: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> A6Output:
        """Evaluate entry classification per Decision Tree V1 § A6.

        Pattern-based classification takes priority over A4 hint.
        """
        if pattern_matched == "NONE" or not pattern_matched:
            # No pattern → default to INITIATIVE (safe assumption)
            return self._make_output("INITIATIVE")

        # Pattern-based classification (Woodies wins)
        if pattern_matched in REACTIVE_PATTERNS:
            classification = "REACTIVE"
        elif pattern_matched in INITIATIVE_PATTERNS:
            classification = "INITIATIVE"
        else:
            # Unknown pattern → use A4 hint if available, else INITIATIVE
            if entry_classification_hint in ("REACTIVE", "INITIATIVE"):
                classification = entry_classification_hint
            else:
                classification = "INITIATIVE"

        return self._make_output(classification)

    def _make_output(self, classification: str) -> A6Output:
        """Build A6Output from classification."""
        if classification == "REACTIVE":
            return A6Output(
                entry_classification="REACTIVE",
                position_size=2,
                management_profile="TIGHT",
            )
        return A6Output(
            entry_classification="INITIATIVE",
            position_size=3,
            management_profile="WIDE",
        )
