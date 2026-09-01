# -*- coding: utf-8 -*-
"""RISK_BUDGET_SIZING_V1 — the flag that decides how many contracts go out.

Michael 2026-09-01: *"אפשר לעשות חוזים יחסי? כדי שהסטופ יהיה במיקום נכון —
כן נכנס לעסקה ופחות חוזים."*  Budget ruled at $225, minimum 3.

**Why this file exists at all.** The flag was built, hand-verified once in a sim
drill, and enabled in `.env` the same morning — with **zero** regression tests.
Every work order that day carried the line "mutation test mandatory"; nobody
checked that it happened. This is the single highest-risk gap of 01.09: a flag
that sets position size on a live account, running unguarded.

The arithmetic under test (`sierra_command._effective_contracts_raw`):

    raw = RISK_BUDGET_USD / (risk_pts * 5.0)      # $5/point, MES
    n   = floor(raw)                              # never round UP past budget
    if risk_pts > RISK_MAX_PTS_HARD:  n = 0
    if n < RISK_MIN_CONTRACTS:        REJECT (return 0)
    else:                             min(n, ruled_contracts())

Two properties carry the money, and each has a mutation guard below:

  * `floor`, not `round`. `round` would spend more than the ruled budget on
    every setup whose raw size lands above .5 — silently, and only sometimes.
  * `n < min` is a **rejection gate**, not a size floor. Clamping up to the
    minimum instead of refusing turns a quality gate into a risk multiplier:
    the wide-stop setup gets taken anyway, at 3 contracts, for more dollars
    than the budget allows. That inversion is the whole point of the ruling.

At $225 / min 3 the gate is arithmetically identical to "maximum stop 15.0
points". 15.0 is admitted; 15.1 is refused. That boundary is asserted directly,
because it is the number Michael reasons about.

`_effective_contracts_raw` is tested rather than `effective_contracts` so the
margin cap (a separate, unconditional safety layer) cannot mask the sizing math.
"""
from __future__ import annotations

import importlib

import pytest


BUDGET = "225"
MIN_C = "3"
RULED = 5          # what ruled_contracts() returns in these tests


@pytest.fixture
def sizing(monkeypatch):
    """`_effective_contracts_raw` with the ruled ladder pinned to RULED."""
    mod = importlib.import_module("backend.v9.services.sierra_command")
    cs = importlib.import_module("backend.v9.services.contract_size")
    monkeypatch.setattr(cs, "ruled_contracts", lambda *a, **k: RULED)
    monkeypatch.setenv("RISK_BUDGET_SIZING_V1", "1")
    monkeypatch.setenv("RISK_BUDGET_USD", BUDGET)
    monkeypatch.setenv("RISK_MIN_CONTRACTS", MIN_C)
    monkeypatch.setenv("RISK_MAX_PTS_HARD", "30")
    return mod._effective_contracts_raw


def _setup(risk_pts, **extra):
    """A setup carrying an explicit risk width, as the gateway ships it."""
    s = {"risk_pts": risk_pts, "contracts": RULED, "size": RULED}
    s.update(extra)
    return s


# ── the sizing curve ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("risk_pts,expected", [
    (4.0, 5),     # raw 11.25 -> 11, capped by the ruled ladder
    (7.0, 5),     # raw  6.43 ->  6, capped by the ruled ladder
    (9.0, 5),     # raw  5.00 ->  5, exactly the ladder
    (11.25, 4),   # raw  4.00 ->  4, below the ladder: budget binds
    (15.0, 3),    # raw  3.00 ->  3, exactly the minimum — admitted
])
def test_contracts_shrink_as_the_stop_widens(sizing, risk_pts, expected):
    assert sizing(_setup(risk_pts)) == expected


def test_the_ruled_ladder_is_never_exceeded(sizing):
    """A 1-point stop buys 45 contracts on budget alone. The ladder still wins."""
    assert sizing(_setup(1.0)) == RULED


# ── the rejection gate ───────────────────────────────────────────────────────

def test_15_0_points_is_admitted_and_15_1_is_refused(sizing):
    """$225 / 3 contracts / $5 == 15.0 points. The boundary Michael reasons about."""
    assert sizing(_setup(15.0)) == 3
    assert sizing(_setup(15.1)) == 0


@pytest.mark.parametrize("risk_pts", [15.1, 20.0, 29.9])
def test_a_stop_wider_than_the_budget_is_rejected_not_clamped(sizing, risk_pts):
    """MUTATION GUARD. Replacing `return 0` with `_n = _min_c` makes every one
    of these return 3 — the setup taken anyway, above budget. The gate would
    read as working while doing the opposite of the ruling."""
    assert sizing(_setup(risk_pts)) == 0


def test_hard_max_points_still_rejects(sizing):
    """RISK_MAX_PTS_HARD=30 is the second net, behind the budget gate."""
    assert sizing(_setup(30.1)) == 0
    assert sizing(_setup(45.0)) == 0


# ── floor, not round ─────────────────────────────────────────────────────────

def test_floor_never_rounds_up_past_the_budget(sizing):
    """MUTATION GUARD. raw = 225/(6*5) = 7.5 exactly.

    floor -> 7 (capped to 5 by the ladder); round -> 8. To see the difference
    the ladder must not mask it, so the ladder is lifted for this one case.
    7 contracts x 6 pts x $5 = $210, inside budget. 8 would be $240 — over."""
    import backend.v9.services.contract_size as cs
    cs_ruled = cs.ruled_contracts
    try:
        cs.ruled_contracts = lambda *a, **k: 99
        assert sizing(_setup(6.0)) == 7      # round() would give 8
    finally:
        cs.ruled_contracts = cs_ruled


def test_a_setup_worth_2_99_contracts_is_refused_not_rounded_to_3(sizing):
    """raw = 225/(15.05*5) = 2.99. `round` would produce 3 and admit it."""
    assert sizing(_setup(15.05)) == 0


# ── stop derived from prices when risk_pts is absent ─────────────────────────

def test_risk_is_derived_from_entry_and_stop_when_not_given(sizing):
    """The gateway does not always ship risk_pts; entry/stop must serve."""
    s = {"entry_price": 7689.5, "stop": 7704.5, "contracts": RULED}   # 15.0
    assert sizing(s) == 3
    s = {"entry_price": 7689.5, "stop": 7704.75, "contracts": RULED}  # 15.25
    assert sizing(s) == 0


def test_no_risk_information_falls_through_instead_of_rejecting(sizing):
    """Honest failure (Rule 1): unknown risk is not a reason to refuse a trade
    here — it falls through to the legacy sizing path. Silently returning 0
    would look like a risk decision that was never actually made."""
    assert sizing({"contracts": RULED, "size": RULED}) != 0


# ── flag OFF must not change anything ────────────────────────────────────────

def test_flag_off_leaves_the_legacy_path_untouched(monkeypatch):
    mod = importlib.import_module("backend.v9.services.sierra_command")
    cs = importlib.import_module("backend.v9.services.contract_size")
    monkeypatch.setattr(cs, "ruled_contracts", lambda *a, **k: RULED)
    monkeypatch.delenv("RISK_BUDGET_SIZING_V1", raising=False)
    monkeypatch.setenv("RISK_BUDGET_USD", BUDGET)
    monkeypatch.setenv("RISK_MIN_CONTRACTS", MIN_C)
    # 25 points would be rejected outright with the flag on.
    assert mod._effective_contracts_raw(_setup(25.0)) != 0


def test_budget_and_minimum_stay_inside_the_daily_loss_cap():
    """RISK_BUDGET_USD x RISK_MIN_CONTRACTS <= RISK_DAILY_LOSS_CAP.

    Raising the budget alone does not add headroom — it moves the daily halt
    closer, so the two must be checked together. 225 x 3 = 675 <= 800 (the live
    cap; the 450 in code is the default, not what runs). Reading the default
    instead of the live value was a real error on 01.09, which is why this
    assertion names both numbers explicitly.
    """
    import os
    budget = float(os.environ.get("RISK_BUDGET_USD", BUDGET))
    min_c = int(os.environ.get("RISK_MIN_CONTRACTS", MIN_C))
    cap = float(os.environ.get("RISK_DAILY_LOSS_CAP", "800"))
    assert budget * min_c <= cap, (
        f"{budget} x {min_c} = {budget * min_c} exceeds the daily cap {cap} — "
        "the halt would fire on losers that the sizing rule considers normal")
