"""MARGIN_AWARE_SIZING_V1 — never send an order the account cannot carry.

Michael 2026-07-28, after the Account Monitor went live: available funds $97.68
against $276.21 of margin per MES contract. The system is configured for four
contracts — $1,104.84 — so every fire would have been rejected by the broker.
Sierra's log already holds six "Insufficient Account Value (NLV) for margin"
rejections from that morning.

A rejected order is worse than a smaller one: the signal is consumed, the slot
churns, `ORDER_FAILED` pollutes the books, and nothing is protected. Sizing to
what the account can actually carry turns a guaranteed rejection into a real,
smaller trade.

This can only REDUCE size. It never increases it, and it never overrides a lower
cap set elsewhere (SIZE_CAP_CUT and friends stay authoritative downward).

Source: sierra_state.json acct_available_funds + acct_margin_req from
sc.GetTradeAccountData — the same numbers Sierra's Trade Accounts window shows.
When they are missing or stale the function returns the requested size unchanged
and says so: guessing a margin figure would be the exact class of synthetic value
that caused today's other failures (Rule 1).
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

STATE = Path(os.path.expanduser("~/SierraChart_Data/v9_export/sierra_state.json"))
STATE_MAX_AGE_S = 30.0


def enabled() -> bool:
    return os.getenv("MARGIN_AWARE_SIZING_V1", "0").strip().lower() in ("1", "true", "yes")


def _read_state() -> Optional[dict]:
    try:
        if not STATE.exists():
            return None
        if (time.time() - STATE.stat().st_mtime) > STATE_MAX_AGE_S:
            return None
        import re
        raw = re.sub(r':\s*-?inf\b', ':null', STATE.read_text().strip() or "{}")
        d = json.loads(raw)
        return d if d.get("acct_ok") in (1, True) else None
    except Exception as e:
        logger.warning("[MarginSizing] state unreadable: %s", e)
        return None


def margin_per_contract(state: dict) -> Optional[float]:
    """Margin for ONE contract, derived from what the account currently holds.

    Uses the live requirement divided by the live position — the broker's own
    arithmetic — rather than a hard-coded number that drifts with volatility.
    With no open position there is nothing to divide, so fall back to
    MES_MARGIN_PER_CONTRACT if the operator has set one, else None."""
    try:
        qty = abs(int(state.get("position_qty") or 0))
        req = float(state.get("acct_margin_req") or 0.0)
        if qty > 0 and req > 0:
            return req / qty
    except (TypeError, ValueError):
        pass
    try:
        v = float(os.getenv("MES_MARGIN_PER_CONTRACT", "0"))
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def cap_contracts(requested: int) -> Tuple[int, str]:
    """Return (allowed, reason). Never raises, never increases `requested`."""
    if requested <= 0:
        return requested, "no size requested"
    if not enabled():
        return requested, "MARGIN_AWARE_SIZING_V1 off"

    state = _read_state()
    if state is None:
        return requested, "account data unavailable — size unchanged (no guess)"

    per = margin_per_contract(state)
    if per is None or per <= 0:
        return requested, "margin per contract unknown — size unchanged (no guess)"

    try:
        avail = float(state.get("acct_available_funds"))
    except (TypeError, ValueError):
        return requested, "available funds unknown — size unchanged (no guess)"

    # Keep a buffer so a tick against us at entry does not breach margin.
    try:
        buf = float(os.getenv("MARGIN_BUFFER_USD", "50"))
    except (TypeError, ValueError):
        buf = 50.0

    usable = avail - buf
    if usable <= 0:
        return 0, (f"no margin: available ${avail:.2f} minus ${buf:.0f} buffer "
                   f"cannot carry one contract (${per:.2f})")

    allowed = int(usable // per)
    if allowed >= requested:
        return requested, f"margin ok (${usable:.2f} covers {requested}×${per:.2f})"
    if allowed <= 0:
        return 0, (f"no margin: ${usable:.2f} usable, ${per:.2f} needed per contract")
    return allowed, (f"reduced {requested}→{allowed}: ${usable:.2f} usable "
                     f"at ${per:.2f} per contract")

# The DLL attaches a bracket PER CONTRACT, but only has slots 1..4
# (Stop1Price..Stop4Price / OCOGroup1..4Quantity). A 5th contract would be sent
# with NO stop and NO target — a naked contract inside a position that looks
# protected. Michael found this shape on 2026-07-28: "העסקה היא על 6 חוזים והסטופ
# והמימוש על חוזה 1 … אם אני פותח עסקה הוא צריך להגן על כל החוזים".
# Today FIXED_CONTRACTS_4 caps at 4 so the slots are never exceeded, but the
# account can now carry 7 — so the cap must live in code, not in a flag that
# might change.
DLL_BRACKET_SLOTS = 4


def cap_to_bracketable(requested: int) -> Tuple[int, str]:
    """Never send more contracts than the DLL can protect."""
    if requested <= DLL_BRACKET_SLOTS:
        return requested, "within bracket slots"
    return DLL_BRACKET_SLOTS, (
        f"reduced {requested}→{DLL_BRACKET_SLOTS}: the DLL attaches one bracket "
        f"per contract and has {DLL_BRACKET_SLOTS} slots — extra contracts would "
        f"be naked")
