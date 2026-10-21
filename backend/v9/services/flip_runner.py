"""FLIP_RUNNER (T-621 fix 4, Michael 21.10 "מאשר את 2 ו 4" — the 20.10 plan): an opposite TAKE closes the runner.

20.10: the 16:50 OPENING_ORR LONG (7729.00) banked T1 17:00 and T2 17:15; its last contract — a runner with the
stop at breakeven or better — held the ONE live slot. At 17:35 DALTON_EDGE_SHORT 7779.25 (tree TAKE, take_location —
above value, at the failed extension) and at 17:50 CEILING_FLIP_TOUCH2 SHORT 7781.00 (tree TAKE) were both refused
`live_slot_occupied`; the market then fell 7787 → 7746.75 (18:10). A runner is the part of a trade that is already
paid for: when the tree TAKES the opposite side, the market has answered the runner's question.

The rule (one decision, pure):
  · the slot holds a trade in the OPPOSITE direction to the candidate,
  · that trade is a RUNNER — its T1 has filled (the stop is at breakeven or beyond),
  · the candidate was admitted by the decision tree (leaf TAKE, tree mode "on") and passed every gate before the
    slot check (the hook sits at the slot check),
then the runner is closed at the market and the candidate takes the slot. A trade before its T1 is never flipped.

Live: the gateway hook only LOGS the flip it would make ("would flip") — closing a Sierra position and then placing
the opposite entry is an order-path change on the shared account (the F1 pre-send guard refuses an entry while the
account carries a position), built only if Michael rules the fix on after the measurement. The harness
(scripts/fwd_harness.py) executes the flip on its own simulated trades — that is what the measurement needs.
Flag FLIP_RUNNER_ON_OPPOSITE_TAKE_V1, default OFF ⇒ the hook returns at once (byte-identical).
"""
from __future__ import annotations

import os
from typing import Optional, Tuple


def enabled() -> bool:
    return os.getenv("FLIP_RUNNER_ON_OPPOSITE_TAKE_V1", "0").strip().lower() in ("1", "true", "yes")


def decide(open_dir: Optional[str], open_is_runner: Optional[bool], new_dir: Optional[str],
           tree_leaf: Optional[str], tree_mode: Optional[str] = "on") -> Tuple[bool, str]:
    """(flip?, reason). Pure — the caller supplies the slot's direction / runner state and the candidate's tree leaf."""
    od, nd = str(open_dir or "").upper(), str(new_dir or "").upper()
    if od not in ("LONG", "SHORT") or nd not in ("LONG", "SHORT"):
        return False, "direction unknown"
    if od == nd:
        return False, "same direction"
    if not open_is_runner:
        return False, "open trade before T1 (not a runner)"
    if str(tree_leaf or "").upper() != "TAKE" or str(tree_mode or "").lower() != "on":
        return False, "candidate not a tree TAKE"
    return True, f"runner {od} closed for the opposite tree TAKE {nd}"
