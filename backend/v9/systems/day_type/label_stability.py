"""Day-type label stability — T-47 / F6 (Michael ruling 2026-08-19, re-confirmed 2026-08-20).

WHY THIS EXISTS
---------------
`docs/reports/DAILY_EXTREMES_PLAYBOOK_2026-08-20.md` §3 measured the label's
instability over 54 sessions:

  * 44% disagreement between the label the engine recorded LIVE and the honest
    post-hoc classification (23/52 days);
  * **46% disagreement between the TWO live sources on the SAME day** (12/26) —
    `v9_day_type_history` vs the `day_type_at_entry` stamped on that day's trades;
  * days where the two live sources disagreed netted **-$728.75**; days where they
    agreed netted **+$1,048.75**.

Every per-day-type playbook (RUNNER_TRAIL_V2's day-type gate, a day-type-conditional
DAY_ENTRY_BUDGET, per-day-type stop width) is applied to the wrong label on nearly
half the days until this is closed.  T-47 is the prerequisite, not an improvement.

WHAT THIS MODULE IS
-------------------
The pure, side-effect-free half of `DAYTYPE_RECLASS_STABILITY_V1`: an
N-consecutive-agreeing-bars confirmation before a label CHANGE is published.
It never blocks a legitimate regime change — it only makes a change prove itself
for N bars first.  The wiring (which surfaces get written) lives at the single
promotion point in `backend/main.py::_day_type_on_bar`.

WHY N = 2 (measured, not chosen by taste)
-----------------------------------------
`scripts/daytype_stability_study.py` replays the LIVE per-bar promotion sequence
(`classify_session(bars[:i], is_eod=False)` for every bar i >= 12, exactly as
main.py runs it) over all 54 sessions:

    N   flips  removed  final-label changed  median delay
    1   200      0        0                  0 bars      <- today
    2   135     65        4                  1 bar
    3   115     85        7                  2 bars
    4   100    100        8                  3 bars
    5    96    104        8                  4 bars
    6    86    114        9                  5 bars

53 of 54 sessions flip at least once; 200 flips total (3.7/session).  Of every
NON-final label in the timeline, **28.5% survived exactly 1 bar** and 41% survived
<= 2.  Of the 147 interior runs, **72 (49%) are pure A->B->A reverts** — the label
left and came straight back — and 53% of those reverts are <= 2 bars.

N=2 removes 65 flips (32.5%) for a median delay of ONE bar, and all **four**
sessions whose final label changes under N=2 are cases where the raw "final" label
was itself a **1-bar blip on the closing bar** (verified per-session: 06-11
Variation-59-bars -> Neutral_Center-1-bar; 07-16 Trend_Normal-17 -> Variation-1;
08-05 Variation-38 -> Trend_DD-1; 08-18 Normal-55 -> Variation-1).  Damping those
is the intent, not a blocked regime change.  N>=3 starts eating 2-3 bar runs on
days where the previous label had held for 55-64 bars, and buys only 20 more flips
for a second bar of delay on EVERY real transition.

Two existing Michael rulings independently land on the same number:
  * `DAYTYPE_CONFIRM_BARS=2` (ruled 2026-07-01) — the same N-consecutive-bars
    anti-noise rule, but wired ONLY into the OLD base engine's `_stage_b6`
    rescore (`state_machine.py:751-772`).  The NEW classifier promotion — the one
    that actually publishes today under `S1_ENGINE_NEW_CLASSIFIER=1` — has no
    such damping.  That gap is precisely what this flag closes.
  * `DAYTYPE_ANTIFLAP_HOLD_S=600` (ruled 2026-07-09) = 2 bars, but applied only to
    the gate-facing READ (`get_live_day_type`), never to what is PUBLISHED — so
    `v9_day_type_history` never got it.  That asymmetry is one of the mechanical
    reasons the two live sources disagree.

Default OFF in code; `DAYTYPE_RECLASS_CONFIRM_BARS` defaults to 2 when ON.
N <= 1 reproduces today's behaviour exactly.
"""

from typing import Any, Dict, Optional

# Values that are not a published label at all (mirrors the exclusion list in
# trade_context.get_live_day_type:565 — one definition, not two).
NOT_A_LABEL = ("", "UNKNOWN", "None", "INDETERMINATE", "FORMING")

DEFAULT_CONFIRM_BARS = 2


def confirm_bars(env: Optional[Dict[str, str]] = None) -> int:
    """N for the confirmation, from `DAYTYPE_RECLASS_CONFIRM_BARS` (default 2).

    Malformed value -> the default (never crash the hot path, never silently
    disable the damping).
    """
    import os as _os
    if env is None:
        raw = _os.environ.get("DAYTYPE_RECLASS_CONFIRM_BARS", "")
    else:
        raw = env.get("DAYTYPE_RECLASS_CONFIRM_BARS", "")
    try:
        n = int(str(raw).strip() or DEFAULT_CONFIRM_BARS)
    except (TypeError, ValueError):
        return DEFAULT_CONFIRM_BARS
    return n if n >= 1 else DEFAULT_CONFIRM_BARS


def is_label(value: Any) -> bool:
    """True when `value` is a real published label (not FORMING/UNKNOWN/None)."""
    if value is None:
        return False
    return str(value) not in NOT_A_LABEL


def confirm_label(state: Dict[str, Any],
                  current: Any,
                  candidate: Any,
                  n: int,
                  session_date: str,
                  force_immediate: bool = False) -> bool:
    """Should `candidate` be published in place of `current`?

    `state` is a plain dict owned by the caller (app.state), mutated in place:
      {"date": <ET session date>, "candidate": <pending label>, "count": <bars>}

    Rules (deliberately the same shape as the already-ruled `_antiflap_day_type`
    and `DAYTYPE_CONFIRM_BARS`, so there is one mental model, not three):

      * a new ET session resets the pending clock — a candidate never carries
        across the day roll;
      * a candidate that is not a real label is ignored entirely (no state churn);
      * when nothing is published yet, or what IS published is not a real label,
        accept immediately — there is nothing to protect;
      * a candidate equal to the published label clears any pending candidate;
      * N <= 1 publishes immediately == today's behaviour, byte-identical;
      * otherwise the candidate must repeat on N CONSECUTIVE calls before it is
        published.  A different candidate restarts the clock at 1 — an oscillation
        A->B->A->B never accumulates.

    Returns True when the caller should publish `candidate`.
    """
    if state.get("date") != session_date:
        state.clear()
        state["date"] = session_date

    if not is_label(candidate):
        return False                                  # nothing to confirm

    if not is_label(current):
        state.pop("candidate", None)
        state.pop("count", None)
        return True                                   # nothing to protect

    if str(candidate) == str(current):
        state.pop("candidate", None)
        state.pop("count", None)
        return False                                  # already published

    if n <= 1 or force_immediate:
        state.pop("candidate", None)
        state.pop("count", None)
        return True                                   # N=1 == today / Dalton definitive

    if state.get("candidate") == str(candidate):
        state["count"] = int(state.get("count", 0)) + 1
    else:
        state["candidate"] = str(candidate)
        state["count"] = 1

    if int(state["count"]) >= n:
        state.pop("candidate", None)
        state.pop("count", None)
        return True

    return False


def pending_view(state: Dict[str, Any]) -> str:
    """Short 'candidate x/N' string for the WARNING log (observability from day 1)."""
    c = state.get("candidate")
    if not c:
        return "-"
    return "%s %s" % (c, state.get("count", 0))
