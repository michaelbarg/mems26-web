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
        if d.get("acct_ok") not in (1, True):
            return None
        # ±DBL_MAX sentinel (2026-07-28, 9 minutes before the open): on a SIM
        # account Sierra has no real balances and GetTradeAccountData returns
        # ~1.8e308 for NLV and available funds. The API endpoint already nulls
        # these for display, but THIS module reads the file directly — and a
        # 1.8e308 "available funds" makes the margin cap compute 6.5e290
        # permitted contracts, i.e. no cap at all, in the one place whose whole
        # job is to be a cap. Absurd magnitude = unusable, and unusable means
        # leave the size alone rather than authorise anything (Rule 1).
        for k in ("acct_available_funds", "acct_margin_req", "acct_account_value"):
            v = d.get(k)
            if isinstance(v, (int, float)) and abs(v) > 1e15:
                logger.warning("[MarginSizing] %s is a sentinel (%.3g) — account "
                               "data unusable, size left unchanged", k, v)
                return None
        return d
    except Exception as e:
        logger.warning("[MarginSizing] state unreadable: %s", e)
        return None


#: The size Michael ruled as the margin fallback (2026-08-19): "אם אין מספיק
#: מרגין לסחור על 4 לא לשאול לבצע". Not "max affordable" — FOUR. 18.08 proved
#: why 5 is skipped: a 5-lot needed $1,931.00 against $1,925.xx available and
#: was rejected over ~$6. The fallback must leave headroom, not shave it.
MARGIN_FALLBACK_CONTRACTS = 4


def margin_per_contract(state: dict) -> Optional[float]:
    """Margin for ONE contract — the broker's own arithmetic where possible.

    Two honest sources, combined conservatively with max():
    - live: acct_margin_req / position_qty when a position is held. This is a
      MAINTENANCE figure and under-states what OPENING a new contract costs
      (live 08-19: $275.33/ct held vs $386.20/ct demanded at order entry 18.08).
    - MES_MARGIN_PER_CONTRACT env: the operator-recorded OPENING requirement
      from an actual broker rejection.
    Taking the max means we are never fooled by the cheaper maintenance number
    into sending an order the broker will reject. Neither available → None
    (no guess, Rule 1)."""
    live = None
    try:
        qty = abs(int(state.get("position_qty") or 0))
        req = float(state.get("acct_margin_req") or 0.0)
        if qty > 0 and req > 0:
            live = req / qty
    except (TypeError, ValueError):
        pass
    conf = None
    try:
        v = float(os.getenv("MES_MARGIN_PER_CONTRACT", "0"))
        conf = v if v > 0 else None
    except (TypeError, ValueError):
        pass
    if live is not None and conf is not None:
        return max(live, conf)
    return live if live is not None else conf


def cap_contracts(requested: int) -> Tuple[int, str]:
    """Return (allowed, reason). Never raises, never increases `requested`.

    Semantics per Michael's 2026-08-19 ruling (supersedes the 08-13 "1:1"
    no-cut ruling, which itself anticipated exactly this: 'אם יחזרו דחיות-מרג'ין
    אמיתיות — לחזור למייקל עם הנתון' — they returned on 18.08, the number was
    reported, and he ruled): if the account cannot carry the ruled size, trade
    **4** — not the max affordable, not 5, and never ask mid-session.

    - affordable(requested)          → requested  (6 stays 6)
    - not affordable, requested > 4  → 4          (the ruling; 5 is skipped)
    - requested <= 4                 → unchanged  (08-13 "1:1" still governs
      below the fallback: no silent shrink to 3/2/1/0. If even 4 cannot clear
      margin the broker rejects it — same net outcome as any smaller guess,
      without inventing a size Michael never ruled.)
    - account data missing/stale     → unchanged  (no guess, Rule 1)
    """
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
    if usable >= requested * per:
        return requested, f"margin ok (${usable:.2f} covers {requested}×${per:.2f})"
    if requested > MARGIN_FALLBACK_CONTRACTS:
        return MARGIN_FALLBACK_CONTRACTS, (
            f"MARGIN FALLBACK {requested}→{MARGIN_FALLBACK_CONTRACTS} (Michael "
            f"2026-08-19): ${usable:.2f} usable cannot carry "
            f"{requested}×${per:.2f}")
    return requested, (f"below-fallback size kept 1:1 (Michael 2026-08-13): "
                       f"${usable:.2f} usable vs {requested}×${per:.2f} — "
                       f"broker adjudicates")

# Never send more contracts than the deployed study can PROTECT.
#
# The old premise was "one bracket per contract, four slots, therefore four
# contracts". Michael found the failure shape on 2026-07-28: "העסקה היא על 6
# חוזים והסטופ והמימוש על חוזה 1 … אם אני פותח עסקה הוא צריך להגן על כל החוזים".
#
# That premise is no longer the code (2026-08-18, after the ladder shipped in
# `sc_study/MES_AI_DataExport_merged.cpp` and was compiled into the loaded DLL).
# A group is not limited to one contract: it may carry several behind a shared
# stop and target. Four groups therefore protect up to six contracts in the
# shape Michael ruled on 08-16 — t0=1 · t1=2 · t2=2 · t3=1. The binding limit
# is what the LADDER covers, not how many slots exist, so this cap now reads
# the same table the backend and the DLL both use. One source; if they ever
# disagree, the trade is sized for a protection that is not there.
from backend.v9.services.contract_size import MAX_PROTECTED_CONTRACTS

#: kept as an alias — the number of OCO groups the study builds. It is NOT the
#: contract cap and must not be used as one.
DLL_BRACKET_SLOTS = 4


def cap_to_bracketable(requested: int) -> Tuple[int, str]:
    """Never send more contracts than the DLL can protect."""
    if requested <= MAX_PROTECTED_CONTRACTS:
        return requested, "covered by the ladder"
    return MAX_PROTECTED_CONTRACTS, (
        f"reduced {requested}→{MAX_PROTECTED_CONTRACTS}: the study's ladder "
        f"covers at most {MAX_PROTECTED_CONTRACTS} contracts inside four OCO "
        f"groups — anything above would be naked")
