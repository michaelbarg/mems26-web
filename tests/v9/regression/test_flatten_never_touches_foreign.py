"""FLATTEN_ACCOUNT is account-wide. It must never be fired at Michael's position.

Found by an adversarial review on 2026-08-17, hours before a live session.

`write_flatten_account` maps to the DLL's account flatten — it closes the NET
position on the symbol and cancels EVERY working order
(`MES_AI_DataExport_merged.cpp:3631`: "always acts on the account/symbol
position", deliberately not gated on `order_armed`, because it is the orphan
kill-switch). That is the right tool for "get me out of everything" and the
WRONG tool for "scratch this one trade".

Both System-6 auto-exit paths were live (`S6_MAE_SCRATCH_V1=1`,
`S6_TARGET_APPROACH_REALIZE_V1=1`) while Michael held 5 contracts by hand with a
stop at 7806. The first scratch of the day would have closed HIS position and
cancelled HIS stop — and my T1 fix is what finally made those paths actually
execute, so the danger arrived with the repair.

The guard is arithmetic on purpose. An earlier version asked the order-map
whether the system "owned" the position; it inverted in practice, because the
trade being exited is itself still open and so always answered "yes, ours" — it
failed open in exactly the case it existed for. Counting contracts cannot invert.

Skipping the scratch costs a little edge. The trade still carries its own
attached bracket, so it is never unprotected. Flattening his position costs
money and breaks the 12:20 ownership ruling.
"""
import pytest

from backend.v9.services import sierra_command as sc


def _qty(monkeypatch, value):
    import backend.v9.services.sierra_position_reconciler as spr
    monkeypatch.setattr(spr, "_sierra_state_qty", lambda: value)


class TestTheArithmeticGuard:
    def test_only_our_contracts_is_safe(self, monkeypatch):
        _qty(monkeypatch, 4)
        assert sc.account_has_foreign_contracts(4) is False

    def test_michaels_contracts_on_top_is_not_safe(self, monkeypatch):
        """The live 08-17 shape: his 5 + our 4."""
        _qty(monkeypatch, 9)
        assert sc.account_has_foreign_contracts(4) is True

    def test_short_side_counts_by_magnitude(self, monkeypatch):
        _qty(monkeypatch, -9)
        assert sc.account_has_foreign_contracts(4) is True
        _qty(monkeypatch, -4)
        assert sc.account_has_foreign_contracts(4) is False

    def test_unreadable_sierra_is_unknown_not_safe(self, monkeypatch):
        """Flattening blind is how you close a position you cannot see."""
        _qty(monkeypatch, None)
        assert sc.account_has_foreign_contracts(4) is None

    def test_unknown_trade_size_treats_any_position_as_foreign(self, monkeypatch):
        _qty(monkeypatch, 3)
        assert sc.account_has_foreign_contracts(None) is True
        _qty(monkeypatch, 0)
        assert sc.account_has_foreign_contracts(None) is False

    def test_it_cannot_invert(self, monkeypatch):
        """The failure mode of the previous guard: it consulted the order map,
        the exiting trade was always in it, so it answered 'ours' every time."""
        import inspect
        src = inspect.getsource(sc.account_has_foreign_contracts)
        assert "_order_map" not in src
        assert "get_active_trades" not in src


class TestBothS6PathsAreGuarded:
    """A guard on one path only would still lose the position."""

    def test_neither_path_flattens_past_a_foreign_position(self):
        import inspect
        from backend.v9.services.trade_manager import bar_level_detector as bld
        src = inspect.getsource(bld)
        assert src.count("account_has_foreign_contracts") == 2, (
            "both MAE_SCRATCH and TARGET_APPROACH_REALIZE must ask first")

    def test_the_guard_runs_before_the_write(self):
        import inspect
        from backend.v9.services.trade_manager import bar_level_detector as bld
        src = inspect.getsource(bld)
        for call in ("write_flatten_account(", "_mae_write("):
            i_guard = src.rindex("account_has_foreign_contracts", 0, src.index(call))
            assert i_guard < src.index(call)

    def test_unknown_is_treated_as_foreign(self):
        """`is not False` — so None (Sierra unreadable) also skips."""
        import inspect
        from backend.v9.services.trade_manager import bar_level_detector as bld
        src = inspect.getsource(bld)
        assert src.count("_fc is not False") == 2, (
            "None must skip too, or an unreadable state file becomes permission")
