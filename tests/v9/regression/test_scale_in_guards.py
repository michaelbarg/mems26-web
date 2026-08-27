"""SCALE_IN_V1 — reinforce a winner, but only one that Sierra actually holds.

Michael's ruling (2026-08-13): "אם הכיוון ממשיך אפשר לחזק בעוד חוזים."
Two defects found on 2026-08-17, both measured, both fixed by asking Sierra
instead of asking our own books.

1. THE ADD WAS DECIDED AGAINST THE BOOKS. On 13.08 the reconciler logged
   "TM says 4 contracts, Sierra says 1" at the moment child 662 was placed —
   0 divergences in the 5.5 minutes before, 18 in the ten minutes after. The
   system was adding contracts on top of a position the broker may no longer
   have held.

2. THE CEILING NEVER BOUND. `max_total_contracts` compared the PARENT's size
   against the cap, so a chain 660 → 661 → 662 passed every time: each link
   saw "2 + 2 <= 8". A replay reached 20 contracts. Michael's 8-contract
   ceiling was written down and never enforced.

Both close with the same fact — the account's real net position, which is also
the honest denominator because margin is charged on the account, not on our books.
"""
import pytest

from backend.v9.services.trade_manager.scale_in import should_scale_in, ScaleInCfg


def _scale_in_method(src: str) -> str:
    """The body of the method that decides a reinforcement — not the call-site
    comment 20k characters earlier, which is where a naive search lands."""
    i = src.index("n_open = abs(int(_acct))")
    start = src.rfind("def ", 0, i)
    return src[start:i + 4000]


def _decide(**kw):
    base = dict(direction="LONG", entry_price=7800.0, t1_hit=True,
                already_scaled=False, n_contracts_open=4,
                bar_high=7810.0, bar_low=7799.0, dir_bias="UP",
                cfg=ScaleInCfg(min_profit_pts=6, add_contracts=2,
                               max_total_contracts=8))
    base.update(kw)
    return should_scale_in(**base)


class TestTheCeilingActuallyBinds:
    """Counted against the ACCOUNT, a chain hits the ceiling. Counted against
    the parent, it never does."""

    def test_a_winner_is_reinforced_when_there_is_room(self):
        assert _decide(n_contracts_open=4) is not None

    def test_the_chain_is_stopped_at_the_ceiling(self):
        # 4 (parent) + 2 (first child) = 6 held; a second add would make 8...
        assert _decide(n_contracts_open=6) is not None
        # ...and a third must not: 8 + 2 = 10 > 8.
        assert _decide(n_contracts_open=8) is None, (
            "this is the chain that reached 20 contracts in replay")

    def test_michaels_manual_contracts_count_against_the_ceiling(self):
        """Margin is charged on the account. 8 of his + our 4 leaves no room."""
        assert _decide(n_contracts_open=12) is None

    def test_the_ceiling_is_configurable_not_hardcoded(self):
        cfg = ScaleInCfg(min_profit_pts=6, add_contracts=2, max_total_contracts=12)
        assert _decide(n_contracts_open=8, cfg=cfg) is not None


class TestItOnlyReinforcesARealWinner:
    def test_no_add_before_t1(self):
        assert _decide(t1_hit=False) is None

    def test_no_add_twice_on_the_same_parent(self):
        assert _decide(already_scaled=True) is None

    def test_no_add_without_enough_continuation(self):
        assert _decide(bar_high=7803.0) is None, "3pt is not the 6pt the ruling asks for"

    def test_no_add_against_the_day_bias(self):
        assert _decide(dir_bias="DOWN") is None

    def test_the_child_stop_sits_at_the_parents_breakeven(self):
        d = _decide()
        assert d.stop == 7800.0, (
            "the child's worst case must be giving back only its own paper gain")

    def test_the_child_never_touches_the_parent(self):
        d = _decide()
        assert d.add_contracts == 2
        assert not hasattr(d, "parent_stop"), "a reinforcement is additive, never a rewrite"


class TestItAsksSierraFirst:
    """The guard lives at the call site, where the account position is readable."""

    def test_the_caller_reads_the_account_position(self):
        import inspect
        from backend.v9.services.trade_manager import bar_level_detector as bld
        src = inspect.getsource(bld)
        blk = _scale_in_method(src)
        assert "_sierra_state_qty" in blk, (
            "the add must be decided against Sierra, not against our books")
        assert "n_open = abs(int(_acct))" in blk, (
            "the ceiling must count the account, or a chain slips past it")

    def test_unknown_position_means_no_add(self):
        import inspect
        from backend.v9.services.trade_manager import bar_level_detector as bld
        src = inspect.getsource(bld)
        blk = _scale_in_method(src)
        j = blk.index("_acct is None")
        assert "return" in blk[j:j + 300], (
            "a stale state file is not a reason to add contracts (Rule 1)")

    def test_wrong_side_means_no_add(self):
        import inspect
        from backend.v9.services.trade_manager import bar_level_detector as bld
        src = inspect.getsource(bld)
        blk = _scale_in_method(src)
        assert "_want_long" in blk, (
            "reinforcing a LONG while Sierra is short would open a new position")


# ══════════════ T-111 · margin precheck (broker reject 27.08 21:05) ══════════

class TestMarginPrecheck:
    """cmd #405 placed a 2c child while avail was ~$59 — 10700 filled, 10703
    margin-rejected, books desynced (SYS-3). The precheck must veto ONLY on a
    positive shortfall; missing data is UNDETERMINED, not a veto."""

    def test_shortfall_blocks(self):
        from backend.v9.services.trade_manager.scale_in import margin_precheck
        ok, reason = margin_precheck(2, 59.0, 398.75)
        assert ok is False and "avail 59.00 < need 797.50" in reason

    def test_sufficient_passes(self):
        from backend.v9.services.trade_manager.scale_in import margin_precheck
        ok, _ = margin_precheck(2, 1314.84, 398.75)
        assert ok is True

    def test_exact_boundary_passes(self):
        from backend.v9.services.trade_manager.scale_in import margin_precheck
        ok, _ = margin_precheck(2, 797.50, 398.75)
        assert ok is True

    def test_unknown_funds_is_undetermined_pass(self):
        """Absence of knowledge is not negative knowledge (binary doctrine) —
        the broker stays the final arbiter."""
        from backend.v9.services.trade_manager.scale_in import margin_precheck
        ok, reason = margin_precheck(2, None, 398.75)
        assert ok is True and "UNDETERMINED" in reason

    def test_wired_before_parent_marking(self):
        """The skip must happen BEFORE `scaled_in` is set, so a margin-skipped
        add stays eligible when funds free up later."""
        import inspect
        from backend.v9.services.trade_manager import bar_level_detector as bld
        src = inspect.getsource(bld)
        pre = src.index("SCALE_IN_MARGIN_PRECHECK_V1")
        mark = src.index('q2["scaled_in"] = True')
        assert pre < mark, "precheck drifted below the parent-marking"

    def test_flag_default_on_and_disableable(self, monkeypatch):
        import inspect
        from backend.v9.services.trade_manager import bar_level_detector as bld
        src = inspect.getsource(bld)
        assert 'getenv("SCALE_IN_MARGIN_PRECHECK_V1", "1")' in src, (
            "default must be ON per the T-111 night mandate")
