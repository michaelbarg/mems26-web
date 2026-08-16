"""The one place that answers "how many contracts did Michael rule for?".

Before this module the same 5-line ladder was copy-pasted into eight files:
`sierra_command` (twice), `quality_tier`, `stop_anchors/sizing`,
`setup_emitter`, `bar_level_detector` (System 6's expected size),
`system6_routes`, `mobile_monitor` and `fire_drill`. Every one of them stopped
at FIXED_CONTRACTS_4.

That duplication is not a style problem, it is a live trading hazard. The
sizing path is a `min(_fixed, _cut)` — `_fixed` comes from
`sierra_command`, `_cut` comes from `quality_tier`. Teaching only one of them
about a larger size does not make the system trade larger; it makes the system
**trade the old size and report the new one**. Same for System 6, which would
raise a false "contracts != expected" on every scan, and for the phone, which
would display a number the account does not hold.

So: one resolver, one precedence order, one place to change when Michael rules
again.

Precedence is highest-first and deliberate — the newest ruling wins, and a
ruling is standing until Michael revokes it in writing (CLAUDE.md § "Rulings
are one-time and standing").

**The size and the protection are not independent.** Sierra's ACSIL exposes
OCOGroup1..5 on `s_SCNewOrder`, and the deployed study builds four groups whose
quantities must sum to the order quantity, per Michael's 2026-08-16 ladder
ruling (1/2/2/1 at six). Any size this module can return MUST be representable
there, or contracts enter with no stop — see `MAX_PROTECTED_CONTRACTS`.
"""
from __future__ import annotations

import os
from typing import Optional

# Ladder shape ruled by Michael 2026-08-16:
#   "t0 - חוזה אחד · t1 - 2 חוזים · t2 - 2 חוזים · t3 - חוזה 1"
# Mirrored in sc_study/MES_AI_DataExport_merged.cpp (the lq[] table). The two
# MUST agree: this is what the backend believes it is buying, that is what the
# broker is actually told to protect.
LADDER = {
    1: (1, 0, 0, 0),
    2: (1, 1, 0, 0),
    3: (1, 1, 1, 0),
    4: (1, 1, 1, 1),
    5: (1, 2, 1, 1),
    6: (1, 2, 2, 1),   # the ruling
}

#: Above this, the ladder cannot cover every contract inside four OCO groups
#: without leaving one unprotected. Clamp the ORDER, never the protection.
MAX_PROTECTED_CONTRACTS = 6


def _on(name: str) -> bool:
    return os.environ.get(name, "0").strip().lower() in ("1", "true", "yes")


def ruled_contracts() -> Optional[int]:
    """The contract count Michael's standing rulings ask for, or None.

    None means "no fixed-size ruling is active" — the caller keeps whatever the
    risk ladder produced. It does NOT mean zero.
    """
    if _on("FIXED_CONTRACTS_6"):
        return 6
    if _on("FIXED_CONTRACTS_5"):
        return 5
    if _on("FIXED_CONTRACTS_4"):
        return 4          # Michael 2026-07-15
    if _on("FIXED_CONTRACTS_2"):
        return 2
    if _on("FIXED_CONTRACTS_3"):
        return 3
    return None


def ruled_contracts_or(default: int) -> int:
    """`ruled_contracts()` with a caller-supplied fallback."""
    n = ruled_contracts()
    return default if n is None else n


def ladder_for(contracts: int) -> tuple:
    """Per-OCO-group quantities for `contracts` — the backend's mirror of the
    DLL table. Sums exactly to min(contracts, MAX_PROTECTED_CONTRACTS)."""
    n = max(1, min(int(contracts), MAX_PROTECTED_CONTRACTS))
    return LADDER[n]


def target_index_for_contract(i: int, contracts: int) -> int:
    """Which target (0=T0, 1=T1, 2=T2, 3=T3) contract `i` (0-based) exits on.

    At six the ruling puts two contracts on T1 and two on T2, so the naive
    "contract i takes target i" mapping under-books a winner. This spells the
    mapping out once so the P&L, the panel and the DLL cannot drift apart.
    """
    groups = ladder_for(contracts)
    seen = 0
    for g_idx, qty in enumerate(groups):
        seen += qty
        if i < seen:
            return g_idx
    return len(groups) - 1
