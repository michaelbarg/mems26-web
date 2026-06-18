"""Reactive Location Gate — blocks REACTIVE fades on the wrong side of POC.

REACTIVE_LONG = fade from oversold (belongs near VAL/below POC).
Block if entry > POC (buying at the ceiling).
REACTIVE_SHORT = fade from overbought (belongs near VAH/above POC).
Block if entry < POC (selling at the floor).

Fail-open, env-gated (REACTIVE_LOCATION_GATE=1), no config file.
Non-REACTIVE patterns, missing POC → always allow.
"""

import logging
import os
from typing import Tuple

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return os.environ.get("REACTIVE_LOCATION_GATE", "0").lower() in ("1", "true", "yes")


def decide(pattern, direction, entry_price, poc) -> Tuple[bool, str]:
    """Decide whether to allow a REACTIVE fire based on entry vs POC.

    Returns (allow: bool, reason: str).
    """
    if not _enabled():
        return (True, "gate OFF")
    if not pattern:
        return (True, "missing pattern")
    if poc is None:
        return (True, "poc unavailable (fail-open)")

    try:
        entry = float(entry_price)
        poc_f = float(poc)
    except (TypeError, ValueError):
        return (True, "non-numeric entry/poc (fail-open)")

    # Only gate REACTIVE patterns
    pat_upper = str(pattern).upper()
    if "REACTIVE_LONG" in pat_upper or (pat_upper == "REACTIVE" and str(direction).upper() == "LONG"):
        if entry > poc_f:
            return (False, f"REACTIVE_LONG entry={entry:.2f} > POC={poc_f:.2f} (upper half — wrong side)")
        return (True, f"REACTIVE_LONG entry={entry:.2f} <= POC={poc_f:.2f} (lower half — correct)")

    if "REACTIVE_SHORT" in pat_upper or (pat_upper == "REACTIVE" and str(direction).upper() == "SHORT"):
        if entry < poc_f:
            return (False, f"REACTIVE_SHORT entry={entry:.2f} < POC={poc_f:.2f} (lower half — wrong side)")
        return (True, f"REACTIVE_SHORT entry={entry:.2f} >= POC={poc_f:.2f} (upper half — correct)")

    # Non-REACTIVE → not targeted
    return (True, f"{pattern} not targeted (non-REACTIVE)")
