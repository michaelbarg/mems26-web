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

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("contract_size")

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
    # Michael 2026-09-18 12:05 ("היום לעבוד על חוזה 1"): a one-contract ruling.
    # Checked FIRST so that a smaller-size ruling always wins over a stale larger
    # one — the failure mode of 15-17.09 was a size in .env that the account
    # could no longer carry (avail 476.64 vs 772.40 for two). Ladder (1,0,0,0):
    # the single contract exits on T1 (T0 needs >= 4, see sierra_command).
    if _on("FIXED_CONTRACTS_1"):
        return 1
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


def target_index_for_contract(i: int, contracts: int, groups=None) -> int:
    """Which target (0=T0, 1=T1, 2=T2, 3=T3) contract `i` (0-based) exits on.

    At six the ruling puts two contracts on T1 and two on T2, so the naive
    "contract i takes target i" mapping under-books a winner. This spells the
    mapping out once so the P&L, the panel and the DLL cannot drift apart.

    The return value is the OCO GROUP index (0-based). `groups` (T-610) is the
    trade's own recorded ladder — `contract_ladder_of()` hands it out together
    with the group→leg offset; None = today's `ladder_for(contracts)`.
    """
    groups = tuple(groups) if groups is not None else ladder_for(contracts)
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
                   hit_flags=None, quality=None) -> "tuple[int, str]":
    """`(contracts still in the market, basis)` for one trade.

    basis is `"exit_fills"` (exact — Sierra's own per-leg quantities),
    `"ladder_hits"` (estimate — column flags weighted by the ruled ladder
    instead of the old flat -1, still blind to T0), or `"assumed_open"`.
    Never raises; never returns more than `contracts` or less than 0.

    `quality` (T-610): the trade's quality dict (or the trade). When it carries
    a recorded ladder (`ladder_groups`) the column flags are weighted by THAT
    ladder's legs — a 2/2/1 five-lot's T2 closes two contracts, not one.
    Without it (every historical row) the estimate is exactly today's.
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
    legs = leg_quantities(quality, total) if quality is not None else None
    if legs is not None:
        out = sum(legs[i + 1] for i, v in enumerate(flags[:3]) if v)
        return max(0, total - out), "ladder_hits"
    groups = ladder_for(total)
    # t1_hit..t3_hit map to ladder legs 1..3; leg 0 (T0) has no column.
    out = sum(groups[i + 1] for i, v in enumerate(flags[:3]) if v)
    return max(0, total - out), "ladder_hits"


# ------------------------------------------------------------ T-610 · 2/2/1
#
# LADDER_221_V1 (Michael 2026-10-19): "נעבוד עם 5 חוזים לפי 2 2 1 כאילו זה 3
# חוזים רק שבמימוש נתייחס בשלב הזה ככה" — five contracts split 2/2/1 over
# T1/T2/T3, NO T0 scalp. Until now five always executed as LADDER[5] =
# T0×1 · T1×2 · T2×1 · T3×1, so what he asked for and what the broker held
# differed.
#
# The shape is a contract between TWO programs: this module (what the books
# believe) and the DLL's lq[] table (what the broker is told to protect). A
# 2/2/1 bracket needs a DLL that takes per-group quantities from the command
# ("lq1".."lq4"); only the T-610 build does, and it says so in its 1 s
# heartbeat (sierra_state.json "cap_lq":1). So the 2/2/1 plan is chosen ONLY
# when the flag is on, the size is five AND a fresh state file reports the
# capability. In every other case the plan is exactly today's: sending lq* to
# a DLL that ignores them would book 2/2/1 against a broker bracketed
# 1/2/1/1 — the very disagreement this exists to end.
#
# Decided ONCE per trade (TradeManager.accept_setup), recorded on the row
# (quality.ladder_groups / has_t0 / ladder_reason) and handed to the PLACE
# writer (setup["ladder_plan"] / remember_plan) — the command never re-decides
# on its own. Every consumer reads the TRADE's ladder (ladder_for_trade,
# contract_ladder_of, ladder_leg_count, leg_quantities); a row without
# `ladder_groups` (all history, and every trade while the flag is off)
# computes exactly as before.

LADDER_221 = (2, 2, 1, 0)
LADDER_221_CONTRACTS = 5
#: A capability nobody vouched for in the last two minutes is not one (Rule 1).
DLL_CAP_MAX_AGE_S = 120.0


def ladder_221_enabled() -> bool:
    """LADDER_221_V1 — read at call time, default OFF (byte-identical)."""
    return _on("LADDER_221_V1")


def _t0_target_pts() -> float:
    try:
        return float(os.getenv("T0_TARGET_PTS", "0") or 0)
    except (TypeError, ValueError):
        return 0.0


def sierra_state_path() -> Path:
    """The DLL's 1 s heartbeat file: <V9_EXPORT_DIR or ~/SierraChart_Data/v9_export>/sierra_state.json."""
    raw = (os.getenv("V9_EXPORT_DIR") or "").strip()
    base = Path(os.path.expanduser(raw or "~/SierraChart_Data/v9_export"))
    if base.suffix.lower() == ".json":      # a script that points it at a file
        base = base.parent
    return base / "sierra_state.json"


#: (path) -> ((mtime_ns, size), caps) — the DLL rewrites the file every second,
#: so a hit only ever saves re-parsing the very same bytes.
_CAP_CACHE: dict = {}


def _read_state(p: Path):
    """Parse sierra_state.json (tolerating Sierra's bare inf) — None when unreadable."""
    for attempt in (0, 1):
        try:
            raw = p.read_text(encoding="utf-8", errors="replace").strip()
            if raw:
                data = json.loads(re.sub(r':\s*-?inf\b', ':null', raw))
                if isinstance(data, dict):
                    return data
        except (OSError, ValueError):
            pass
        if attempt == 0:
            time.sleep(0.05)   # the DLL truncates+rewrites in place: one retry
    return None


def dll_capabilities(state_path=None, *, now=None,
                     max_age_s: float = DLL_CAP_MAX_AGE_S) -> dict:
    """What the LOADED DLL says it can do — from its own heartbeat file.

    Returns {"cap_lq": 0|1, "ok": bool, "why": str, "age_s": float|None}.
    Missing, unreadable or stale (> max_age_s) → cap_lq 0. Never raises.
    """
    p = Path(state_path) if state_path is not None else sierra_state_path()
    try:
        st = p.stat()
    except OSError:
        return {"cap_lq": 0, "ok": False, "why": "sierra_state.json missing (%s)" % p,
                "age_s": None}
    _now = time.time() if now is None else float(now)
    age = _now - st.st_mtime
    if age > max_age_s:
        return {"cap_lq": 0, "ok": False,
                "why": "sierra_state.json stale (%.0fs > %.0fs)" % (age, max_age_s),
                "age_s": round(age, 1)}
    key = str(p)
    stamp = (st.st_mtime_ns, st.st_size)
    hit = _CAP_CACHE.get(key)
    if hit is not None and hit[0] == stamp:
        out = dict(hit[1])
        out["age_s"] = round(age, 1)
        return out
    data = _read_state(p)
    if data is None:
        # not cached: the next call must look again
        return {"cap_lq": 0, "ok": False, "why": "sierra_state.json unreadable",
                "age_s": round(age, 1)}
    try:
        cap = int(data.get("cap_lq") or 0)
    except (TypeError, ValueError):
        cap = 0
    caps = {"cap_lq": 1 if cap == 1 else 0, "ok": True,
            "why": ("cap_lq=1" if cap == 1 else
                    "the loaded DLL does not report cap_lq (pre-T-610 build — "
                    "Remote Build pending)")}
    _CAP_CACHE[key] = (stamp, caps)
    while len(_CAP_CACHE) > 16:
        _CAP_CACHE.pop(next(iter(_CAP_CACHE)))
    out = dict(caps)
    out["age_s"] = round(age, 1)
    return out


def _clamped(contracts) -> int:
    try:
        return max(1, min(int(contracts), MAX_PROTECTED_CONTRACTS))
    except (TypeError, ValueError):
        return 1


def legacy_plan(contracts, reason: str) -> dict:
    """Today's plan for `contracts` — LADDER[n], T0 at >= 4 when T0_TARGET_PTS > 0
    (the condition accept_setup has always used), no lq* on the wire."""
    n = _clamped(contracts)
    return {"groups": tuple(LADDER[n]),
            "has_t0": bool(n >= 4 and _t0_target_pts() > 0),
            "lq_cmd": False, "reason": reason}


def ladder_plan(contracts, *, dll_caps=None) -> dict:
    """THE decision: how a trade of `contracts` is bracketed.

    {"groups": (g1, g2, g3, g4), "has_t0": bool, "lq_cmd": bool, "reason": str}

    lq_cmd=True only for: LADDER_221_V1 on AND contracts == 5 AND the loaded
    DLL reports cap_lq == 1 (`dll_caps`, else read from sierra_state.json) →
    groups (2, 2, 1, 0), has_t0 False: T1×2 · T2×2 · T3×1, no T0, no 4th leg.
    Anything else → `legacy_plan` (exactly today), with the reason.
    """
    if not ladder_221_enabled():
        return legacy_plan(contracts, "LADDER_221_V1 off")
    try:
        n_raw = int(contracts)
    except (TypeError, ValueError):
        n_raw = None
    if n_raw != LADDER_221_CONTRACTS:
        return legacy_plan(contracts, "contracts=%s (2/2/1 is ruled for %d only)"
                           % (contracts, LADDER_221_CONTRACTS))
    caps = dll_caps if dll_caps is not None else dll_capabilities()
    try:
        cap = int((caps or {}).get("cap_lq") or 0)
    except (TypeError, ValueError, AttributeError):
        cap = 0
    if cap != 1:
        why = (caps or {}).get("why") if isinstance(caps, dict) else None
        return legacy_plan(contracts, "DLL cap_lq missing — %s"
                           % (why or "no capability reported"))
    return {"groups": LADDER_221, "has_t0": False, "lq_cmd": True,
            "reason": "LADDER_221_V1 · DLL cap_lq=1"}


def plan_fits(plan, contracts) -> bool:
    """A plan can bracket `contracts` iff its groups are 4 non-negative ints,
    the first >= 1, no group after an empty one, summing to the clamped size —
    the same validation the DLL applies to lq1..lq4."""
    if not isinstance(plan, dict):
        return False
    try:
        g = tuple(int(x) for x in plan.get("groups"))
    except (TypeError, ValueError):
        return False
    if len(g) != 4 or g[0] < 1 or any(x < 0 for x in g):
        return False
    if any(g[i] > 0 and g[i - 1] == 0 for i in range(1, 4)):
        return False
    return sum(g) == _clamped(contracts)


def format_plan(plan) -> str:
    """'2/2/1' (lq plan) · '1/2/1/1+T0' (today's five)."""
    try:
        g = [int(x) for x in plan.get("groups")]
    except (TypeError, ValueError, AttributeError):
        return "?"
    if plan.get("lq_cmd"):
        g = [x for x in g if x > 0]
    return "/".join(str(x) for x in g) + ("+T0" if plan.get("has_t0") else "")


#: trade_id (str) -> plan, written by accept_setup the moment the row exists.
#: The gateway hands command_from_setup a COPY of the setup, so the decision
#: travels by trade id. In-memory: a restart between accept and PLACE (which
#: run back-to-back in one call) is not a case that exists.
_PLANS: dict = {}
_PLANS_CAP = 256


def remember_plan(trade_id, plan) -> None:
    if trade_id is None or not isinstance(plan, dict):
        return
    _PLANS[str(trade_id)] = dict(plan)
    while len(_PLANS) > _PLANS_CAP:
        _PLANS.pop(next(iter(_PLANS)))


def recorded_plan(trade_id) -> Optional[dict]:
    p = _PLANS.get(str(trade_id)) if trade_id is not None else None
    return dict(p) if p is not None else None


def plan_for_place(setup, trade_id, contracts) -> dict:
    """The plan a PLACE carries — the trade's own, decided at accept_setup.

    Order: setup["ladder_plan"] (same dict passed through) → the plan
    remembered for `trade_id` (the gateway passes a copy) → decide now (drills
    and scripts that PLACE with no trade row). A recorded plan that cannot
    bracket `contracts` (the size moved between accept and PLACE) is not sent:
    the PLACE goes out with today's ladder and the reason says why.
    Adds "source": setup | recorded | decided | mismatch.
    """
    cands = []
    if isinstance(setup, dict) and isinstance(setup.get("ladder_plan"), dict):
        cands.append(("setup", setup["ladder_plan"]))
    _rec = recorded_plan(trade_id)
    if _rec is not None:
        cands.append(("recorded", _rec))
    for src, cand in cands:
        if plan_fits(cand, contracts):
            out = dict(cand)
            out["groups"] = tuple(int(x) for x in cand.get("groups"))
            out["source"] = src
            return out
        out = legacy_plan(contracts, "recorded plan %s does not fit contracts=%s"
                          % (format_plan(cand), contracts))
        out["source"] = "mismatch"
        return out
    out = ladder_plan(contracts)
    out["source"] = "decided"
    return out


# --- the trade's own ladder, for every consumer --------------------------

def _quality_of(obj) -> dict:
    """A quality dict from a trade, a quality dict, or a DB row dict that
    selected ladder_groups/has_t0/t0_target_pts by those names."""
    if isinstance(obj, dict):
        return obj
    q = getattr(obj, "quality", None) if obj is not None else None
    return q if isinstance(q, dict) else {}


def _truthy(v) -> bool:
    """has_t0 arrives as a bool (ORM) or as 'true'/'false' text (->> in SQL)."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "t")
    return False


def trade_has_t0(trade_or_quality) -> bool:
    """The rule manager.py has always used (`t0_target_pts or has_t0`),
    tolerant of SQL text values."""
    q = _quality_of(trade_or_quality)
    try:
        pts = float(q.get("t0_target_pts") or 0)
    except (TypeError, ValueError):
        pts = 0.0
    return pts > 0 or _truthy(q.get("has_t0"))


def recorded_ladder(trade_or_quality, contracts=None) -> Optional[tuple]:
    """The trade's recorded `ladder_groups`, validated — else None.

    None for every row written without LADDER_221_V1 (all history), and for a
    record that does not bracket `contracts` (callers then use today's
    `ladder_for`, so a damaged record can never invent a shape)."""
    raw = _quality_of(trade_or_quality).get("ladder_groups")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return None
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        return None
    try:
        groups = tuple(int(x) for x in raw)
    except (TypeError, ValueError):
        return None
    if groups[0] < 1 or any(g < 0 for g in groups):
        return None
    if contracts is not None and sum(groups) != _clamped(contracts):
        return None
    return groups


def ladder_for_trade(trade_or_quality, contracts) -> tuple:
    """Per-OCO-group quantities THIS trade was bracketed with: its recorded
    ladder when present and consistent, else today's `ladder_for(contracts)`."""
    rec = recorded_ladder(trade_or_quality, contracts)
    return rec if rec is not None else ladder_for(contracts)


def contract_ladder_of(trade_or_quality, contracts) -> "tuple[Optional[tuple], int]":
    """(groups, leg_offset) for mapping contract i → LEG (0=T0 .. 3=T3):

        leg = min(target_index_for_contract(i, n, groups=groups) + leg_offset, 3)

    A recorded ladder WITHOUT a T0 starts at T1, so group 0 is leg 1 (2/2/1:
    C1,C2→T1 · C3,C4→T2 · C5→T3). No record → (None, 0) = exactly today's map.
    """
    rec = recorded_ladder(trade_or_quality, contracts)
    if rec is None:
        return None, 0
    return rec, (0 if trade_has_t0(trade_or_quality) else 1)


def ladder_leg_count(trade_or_quality, contracts) -> int:
    """How many legs (non-empty groups) the trade's recorded ladder has — the
    2/2/1 five-lot has three ("כאילו זה 3 חוזים"), so its T3 is the last leg.
    No record → `contracts`, the number the close logic has always compared."""
    rec = recorded_ladder(trade_or_quality, contracts)
    if rec is None:
        try:
            return int(contracts)
        except (TypeError, ValueError):
            return 0
    return sum(1 for g in rec if g > 0)


def leg_quantities(trade_or_quality, contracts) -> Optional[list]:
    """Contracts per LEG [T0, T1, T2, T3] from the recorded ladder, else None
    (callers keep today's estimate)."""
    rec = recorded_ladder(trade_or_quality, contracts)
    if rec is None:
        return None
    if trade_has_t0(trade_or_quality):
        return list(rec)
    return [0] + list(rec[:3])
