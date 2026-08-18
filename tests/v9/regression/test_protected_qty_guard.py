"""Every contract behind a stop — not just the first one.

Michael, 2026-07-28: "העסקה היא על 6 חוזים והסטופ והמימוש על חוזה 1 … אם אני
פותח עסקה הוא צריך להגן על כל החוזים."

The existing guard asks "is there A protective stop?" and returns a boolean.
With a partial bracket the answer is True while the rest of the position is
naked — which is exactly the shape that failure takes. Moving from 4 to 5
contracts makes that gap live: the compiled ladder has never placed a real
5-contract bracket, and if it is wrong the fifth contract enters with no stop.

This counts what the stops actually cover.
"""
import pytest

import backend.v9.services.sierra_position_reconciler as R


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.setenv("PROTECTED_QTY_GUARD_V1", "1")
    monkeypatch.setenv("PROTECTED_QTY_STREAK", "2")
    R._prot_short_streak = 0
    R._prot_last_alert = 0.0
    monkeypatch.setattr(R, "push" if hasattr(R, "push") else "logger", R.logger)


def _orders(monkeypatch, orders):
    monkeypatch.setattr(R, "_sierra_state_orders", lambda: orders)


def _stop(qty, bs=1):
    return {"id": 1, "type": 3, "bs": bs, "price": 7800.0, "qty": qty}


def _target(qty, bs=1):
    return {"id": 2, "type": 1, "bs": bs, "price": 7700.0, "qty": qty}


class TestTheShortfallIsCounted:
    def test_a_full_ladder_is_silent(self, monkeypatch):
        _orders(monkeypatch, [_stop(1), _stop(2), _stop(1), _stop(1)])
        assert R._unprotected_contracts(-5) is None
        assert R._unprotected_contracts(-5) is None

    def test_the_2807_shape_is_caught(self, monkeypatch):
        """6 contracts, a stop on one — the failure Michael found."""
        _orders(monkeypatch, [_stop(1)])
        assert R._unprotected_contracts(-6) is None       # streak 1, still quiet
        msg = R._unprotected_contracts(-6)                 # streak 2 → alarm
        assert msg and "5c with NO stop" in msg

    def test_a_five_contract_ladder_missing_its_last_leg(self, monkeypatch):
        _orders(monkeypatch, [_stop(1), _stop(2), _stop(1)])
        R._unprotected_contracts(-5)
        msg = R._unprotected_contracts(-5)
        assert msg and "1c with NO stop" in msg

    def test_targets_do_not_count_as_protection(self, monkeypatch):
        _orders(monkeypatch, [_stop(1), _target(4)])
        R._unprotected_contracts(-5)
        assert "4c with NO stop" in R._unprotected_contracts(-5)

    def test_the_wrong_side_does_not_count(self, monkeypatch):
        """On a SHORT only a BUY stop closes. A SELL stop would add size."""
        _orders(monkeypatch, [_stop(5, bs=2)])
        R._unprotected_contracts(-5)
        assert "5c with NO stop" in R._unprotected_contracts(-5)


class TestItRefusesToGuess:
    def test_no_orders_is_unknown_not_naked(self, monkeypatch):
        """The held-bracket class makes a real bracket briefly invisible."""
        _orders(monkeypatch, [])
        assert R._unprotected_contracts(-5) is None
        assert R._unprotected_contracts(-5) is None

    def test_a_typeless_feed_is_unknown(self, monkeypatch):
        _orders(monkeypatch, [{"id": 1, "bs": 1, "price": 7800.0, "qty": 1}])
        assert R._unprotected_contracts(-5) is None
        assert R._unprotected_contracts(-5) is None

    def test_flat_is_never_an_alarm(self, monkeypatch):
        _orders(monkeypatch, [_stop(1)])
        assert R._unprotected_contracts(0) is None
        assert R._unprotected_contracts(None) is None

    def test_one_check_is_not_enough(self, monkeypatch):
        """A bracket still being attached must not raise an alarm."""
        _orders(monkeypatch, [_stop(1)])
        assert R._unprotected_contracts(-5) is None

    def test_the_streak_resets_once_the_bracket_lands(self, monkeypatch):
        _orders(monkeypatch, [_stop(1)])
        R._unprotected_contracts(-5)
        _orders(monkeypatch, [_stop(1), _stop(2), _stop(1), _stop(1)])
        assert R._unprotected_contracts(-5) is None
        assert R._prot_short_streak == 0

    def test_the_flag_off_is_byte_identical(self, monkeypatch):
        monkeypatch.setenv("PROTECTED_QTY_GUARD_V1", "0")
        _orders(monkeypatch, [_stop(1)])
        for _ in range(4):
            assert R._unprotected_contracts(-6) is None


class TestItNeverActs:
    def test_the_guard_only_reports(self):
        import inspect
        src = inspect.getsource(R._unprotected_contracts)
        for forbidden in ("write_", "flatten", "SellOrder", "BuyOrder",
                          "_place_orphan_stop", "cancel"):
            assert forbidden not in src, (
                "alert-only: %s has no business in this guard" % forbidden)

    def test_it_is_wired_into_the_match_branch(self):
        """The system-owned case — where the books and Sierra agree."""
        import inspect
        src = inspect.getsource(R.reconcile_position)
        i = src.index("MATCH:")
        assert "_unprotected_contracts" in src[max(0, i - 400):i + 200]
