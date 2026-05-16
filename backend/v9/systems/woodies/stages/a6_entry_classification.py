"""Stage A6 — Entry Classification (PROMPT 2 · 2.2 stub).

Purpose: Final classification of entry as REACTIVE or INITIATIVE.
Reference: Decision Tree V1 § Section 4 · A6
Type: Woodies Core (uses A4 hint but decides independently)
Logic: PROMPT 3
"""

from dataclasses import dataclass
from typing import Optional


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
        """Evaluate entry classification. STUB: returns INITIATIVE/3/WIDE."""
        # STUB: real logic in PROMPT 3
        return A6Output(
            entry_classification="INITIATIVE",
            position_size=3,
            management_profile="WIDE",
        )
