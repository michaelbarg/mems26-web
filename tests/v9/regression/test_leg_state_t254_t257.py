"""T-254 + T-257 regression — one shared root: leg -> contracts was never mapped.

Both bugs come from the same missing fact: nothing could answer "how many
contracts has this leg closed". Each consumer invented its own wrong answer.

T-254 `sierra_position_reconciler`: `n -= 1` per hit target, iterating the
t1..t4 columns while the ruled ladder legs are (t0, t1, t2, t3). So a T1 leg
that closed TWO contracts subtracted ONE, and the T0 scale-out — which has no
column, only an `exit_fills` entry — was never subtracted at all. Live #1073
on 2026-09-04 (5 contracts; T0 1c @7722.50 + T1 2c @7720.25 banked, 2 left)
was reported as 4 open against Sierra's 2 and printed
`DIVERGENCE: Records != reality!` 256 times, arming the T-43 live-entry block
for 152 minutes of the session on a condition that was never true.

T-257 `mobile_monitor`: `_lvl_hit[0] = False`, hard-coded, so the banked T0
contract was priced as open at `mid` forever. Phone showed 69.2 / 65.6 / 65.6
against Sierra's own 15.0 / 10.0 / 7.5 in the same second.

The fixture below is the REAL `quality["exit_fills"]` of #1073.
"""
import pytest

from backend.v9.services.contract_size import (
    LADDER, closed_contracts, leg_hits, leg_prices, open_contracts,
    target_index_for_contract,
)

# v9_trades.quality->'exit_fills' for live #1073 (S4/GB100 SHORT, 5 contracts),
# read from Postgres 2026-09-04 23:4x. Entry filled 7725.50.
T1073_FILLS = [
    {"ts": "2026-09-04T17:24:58+00:00", "qty": 1, "kind": "T0",
     "price": 7722.5, "column": None, "order_id": 10999},
    {"ts": "2026-09-04T17:29:38+00:00", "qty": 2, "kind": "T1",
     "price": 7720.25, "column": 0, "order_id": 11002},
    {"ts": "2026-09-04T18:58:01+00:00", "qty": 1, "kind": "STOP",
     "price": 7725.25, "column": None, "order_id": 11006},
    {"ts": "2026-09-04T18:58:01+00:00", "qty": 1, "kind": "STOP",
     "price": 7725.25, "column": None, "order_id": 11008},
]
# state mid-trade: T0 and T1 banked, the two runners still live
T1073_MID = T1073_FILLS[:2]


def _old_open(contracts, hit_flags4):
    """The pre-fix reconciler arithmetic, kept so the mutation is explicit."""
    n = contracts
    for v in hit_flags4:
        if v:
            n -= 1
    return max(0, n)


# ----------------------------------------------------------------- T-254

def test_t1_leg_of_two_contracts_subtracts_two_not_one():
    n, basis = open_contracts(5, T1073_MID, [True, False, False])
    assert (n, basis) == (2, "exit_fills")
    # the exact number Sierra reported for that trade
    assert closed_contracts(T1073_MID) == 3


def test_mutation_restoring_the_flat_minus_one_reproduces_the_false_divergence():
    """Put the old `n -= 1` back and #1073's ghost divergence returns."""
    assert _old_open(5, [True, False, False, False]) == 4     # the bug
    assert open_contracts(5, T1073_MID, [True, False, False])[0] == 2
    # 4 vs Sierra's 2 is exactly the logged `TM says -4 ... Sierra says -2`
    assert _old_open(5, [True, False, False, False]) != 2


def test_t0_scaleout_has_no_column_and_was_invisible_to_the_old_counter():
    """Only T0 has fired: no t*_hit_ts column can see it, exit_fills can."""
    t0_only = [T1073_FILLS[0]]
    assert _old_open(5, [False, False, False, False]) == 5      # blind
    assert open_contracts(5, t0_only, [False, False, False]) == (4, "exit_fills")
    assert leg_hits(5, t0_only)[0] is True


def test_fallback_is_ladder_weighted_not_flat_one_and_says_so():
    """No ledger (shadow twin / legacy row): still never subtract a flat 1.

    At five the ruled ladder is 1/2/1/1, so a hit T1 is TWO contracts.
    """
    n, basis = open_contracts(5, None, [True, False, False])
    assert basis == "ladder_hits"
    assert n == 5 - LADDER[5][1] == 3
    assert open_contracts(5, None, [False, False, False]) == (5, "assumed_open")


def test_fallback_marks_t0_unknown_never_false():
    """Rule 1: the column set cannot speak to T0, so it must not claim False."""
    assert leg_hits(5, None, [True, False, False]) == [None, True, False, False]


def test_open_contracts_is_clamped_and_never_raises():
    assert open_contracts(0, None, None) == (0, "assumed_open")
    assert open_contracts(None, None, None) == (0, "assumed_open")
    assert open_contracts(5, "not-a-list", None) == (5, "assumed_open")
    # a ledger claiming more than the position closed cannot go negative
    over = [{"kind": "STOP", "qty": 99, "price": 1.0}]
    assert open_contracts(5, over, None) == (0, "exit_fills")


# ----------------------------------------------------------------- T-257

def test_panel_leg_hits_see_the_banked_t0():
    """The hard-coded False is gone: C1 (the T0 leg) reads as HIT."""
    hits = leg_hits(5, T1073_MID, [True, False, False])
    assert hits == [True, True, False, False]
    assert target_index_for_contract(0, 5) == 0     # C1 exits on T0
    assert target_index_for_contract(1, 5) == 1     # C2/C3 on T1 (2 contracts)
    assert target_index_for_contract(2, 5) == 1


def test_banked_leg_is_priced_at_the_fill_not_at_a_missing_target():
    """`quality["t0"]` is NULL on every live row of 2026-09-04 — only
    `has_t0`/`t0_target_pts` are stored. Marking T0 hit without a price source
    would have priced it against 0 and turned a wrong number into an absurd one.
    """
    assert leg_prices(T1073_MID)[0] == 7722.5
    assert leg_prices(T1073_MID)[1] == 7720.25
    assert leg_prices(None) == [None, None, None, None]


def test_phone_total_pnl_shape_for_1073_matches_the_broker():
    """End-to-end arithmetic of the panel's `total_pnl` for #1073 mid-trade.

    SHORT 5 @ 7725.50 fill. Banked: T0 1c @7722.50 = +15.00,
    T1 2c @7720.25 = +52.50. Two runners open at mid 7723.00 = +25.00.
    Before the fix the T0 contract was counted as open at mid (+12.50 instead
    of +15.00) — small here, unbounded as price runs.
    """
    entry, mid, mul, n = 7725.50, 7723.00, -1.0, 5
    hits, fills = leg_hits(n, T1073_MID), leg_prices(T1073_MID)
    total = 0.0
    for i in range(n):
        leg = target_index_for_contract(i, n)
        if hits[leg]:
            total += (fills[leg] - entry) * mul * 5.0
        else:
            total += (mid - entry) * mul * 5.0
    assert round(total, 2) == 15.00 + 52.50 + 25.00 == 92.50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
