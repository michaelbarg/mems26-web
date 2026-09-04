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


# --------------------------------------------------------------- leg state
#
# T-254 + T-257 (2026-09-04) — one shared root: nothing in the system could
# answer "how many contracts has this leg closed, and how many are still in
# the market". Two consumers each invented their own wrong answer:
#
#   * sierra_position_reconciler.py did `n -= 1` per hit target, so a T1 leg
#     that closed TWO contracts subtracted ONE. It also iterated t1..t4 while
#     the ladder legs are (t0, t1, t2, t3) — the T0 leg has no column at all,
#     so it was never subtracted. On #1073 (5 contracts, T0 1c + T1 2c closed)
#     it reported 4 open against Sierra's 2 and raised
#     `DIVERGENCE: Records != reality!` — 256 times on 2026-09-04 — and armed
#     the T-43 live-entry block for 152 minutes of the session on a condition
#     that was never true. No candidate happened to arrive while it was armed,
#     so it cost nothing that day; it is one candidate away from costing a trade.
#   * mobile_monitor.py hard-coded `_lvl_hit[0] = False`, pricing the already
#     banked T0 contract as if it were still open, and sized the ladder from
#     the ORIGINAL contract count. Michael's phone read 69.2 / 65.6 / 65.6
#     while Sierra said 15.0 / 10.0 / 7.5.
#
# The answer lives in ONE place now, and it prefers the T-62 exit-fill ledger
# (`v9_trades.quality["exit_fills"]`) — the legs Sierra actually reported, with
# the quantity it actually filled, T0 included — over any column flag.

#: Ladder leg index for each exit `kind` the T-62 ledger records. STOP/FLATTEN
#: close whatever is left and belong to no leg, so they are counted as raw
#: quantity and never as a leg hit.
LEG_KIND_INDEX = {"T0": 0, "T1": 1, "T2": 2, "T3": 3}
_CLOSING_KINDS = set(LEG_KIND_INDEX) | {"T4", "STOP", "FLATTEN", "EXIT"}


def _fills(exit_fills) -> list:
    if not isinstance(exit_fills, list):
        return []
    return [f for f in exit_fills
            if isinstance(f, dict)
            and str(f.get("kind", "")).upper() in _CLOSING_KINDS]


def closed_contracts(exit_fills) -> Optional[int]:
    """Contracts already out of the market per the T-62 exit-fill ledger.

    None when the ledger is absent — that is "not knowable from fills", NOT
    zero. Callers must fall back explicitly and say which basis they used
    (Rule 1: honest failure beats a synthesized value).
    """
    fills = _fills(exit_fills)
    if not fills:
        return None
    total = 0
    for f in fills:
        try:
            total += max(0, int(f.get("qty") or 0))
        except (TypeError, ValueError):
            continue
    return total


def leg_hits(contracts: int, exit_fills=None, hit_flags=None) -> list:
    """Per-ladder-leg hit state `[T0, T1, T2, T3]`.

    `hit_flags` is the weaker fallback: an iterable of 4 booleans read from the
    `t1_hit_ts..t4_hit_ts` columns. It is offset by one leg (there is no t0
    column) and therefore can never see a T0 scale-out, so entries it cannot
    speak to come back as `None` rather than `False`.
    """
    fills = _fills(exit_fills)
    if fills:
        hit = [False] * 4
        for f in fills:
            idx = LEG_KIND_INDEX.get(str(f.get("kind", "")).upper())
            if idx is not None:
                hit[idx] = True
        return hit
    flags = list(hit_flags or [])
    # columns are t1..t4; ladder legs are t0..t3 ⇒ T0 is simply unknown here
    return [None] + [bool(v) for v in flags[:3]] + [None] * max(0, 3 - len(flags))


def leg_prices(exit_fills=None) -> list:
    """Per-ladder-leg realised fill price `[T0, T1, T2, T3]`, else None.

    A hit leg must be priced at what Sierra paid, not at the level we aimed
    for — and for T0 there is often no level stored at all (`quality["t0"]` is
    NULL on every 2026-09-04 live row; only `has_t0`/`t0_target_pts` are set).
    Pricing a hit T0 against a missing target yields `(0 - entry) * $5`, which
    is how a display bug becomes an absurd number instead of a wrong one.
    """
    out = [None, None, None, None]
    for f in _fills(exit_fills):
        idx = LEG_KIND_INDEX.get(str(f.get("kind", "")).upper())
        if idx is None or out[idx] is not None:
            continue
        try:
            px = float(f.get("price"))
        except (TypeError, ValueError):
            continue
        if px:
            out[idx] = px
    return out


def open_contracts(contracts: int, exit_fills=None,
                   hit_flags=None) -> "tuple[int, str]":
    """`(contracts still in the market, basis)` for one trade.

    basis is `"exit_fills"` (exact — Sierra's own per-leg quantities),
    `"ladder_hits"` (estimate — column flags weighted by the ruled ladder
    instead of the old flat -1, still blind to T0), or `"assumed_open"`.
    Never raises; never returns more than `contracts` or less than 0.
    """
    try:
        total = max(0, int(contracts or 0))
    except (TypeError, ValueError):
        return 0, "assumed_open"
    done = closed_contracts(exit_fills)
    if done is not None:
        return max(0, total - done), "exit_fills"
    flags = list(hit_flags or [])
    if not any(flags):
        return total, "assumed_open"
    groups = ladder_for(total)
    # t1_hit..t3_hit map to ladder legs 1..3; leg 0 (T0) has no column.
    out = sum(groups[i + 1] for i, v in enumerate(flags[:3]) if v)
    return max(0, total - out), "ladder_hits"
