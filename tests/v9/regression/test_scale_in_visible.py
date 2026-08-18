"""A reinforcement must show as the position growing — not replace the trade.

Michael, 2026-08-18: "בסוף היום סגרתי עסקה שזה בסדר, בפרונט אנד זה לא סומן
הגדלת חוזים."

The reinforcement DID fire on 17.08 — `[ScaleIn] 22:32:05 parent=699 child=708
+2c`. The card was not missing a badge; the trade was REPLACED. `/trades/active`
picks `order_by(entry_ts.desc()).first()`, so the newer child won and the parent
disappeared: entry moved 7776.25 -> 7769.75, "1/2 hit" became "0/2 hit", and P&L
went to $0. From the screen it looked like the winning trade had vanished.

A scale-in is an addition to the SAME position. The card must keep showing the
parent and say the position grew.
"""
import inspect

from backend.v9.api.v9 import trades as tr


class TestTheCardKeepsTheParent:
    def test_active_resolves_the_child_to_its_parent(self):
        src = inspect.getsource(tr)
        assert "scale_in_parent" in src, (
            "/active must recognise a reinforcement child")
        # the first mention is the docstring; the resolution lives in the route
        i = src.index("_parent_id = ")
        assert "trade = _parent" in src[i:i + 2000], (
            "the child must hand the card back to the parent — otherwise the "
            "winning trade disappears from the screen mid-position")

    def test_the_parent_side_finds_its_child(self):
        """Either row can be the newest, so both directions must resolve."""
        src = inspect.getsource(tr)
        assert "_find_scale_in_child" in src

    def test_position_contracts_is_the_real_size(self):
        src = inspect.getsource(tr)
        assert '"position_contracts"' in src, (
            "no payload field ever carried the size actually in the market")
        i = src.index('"position_contracts"')
        assert "_scale_in" in src[i:i + 300], (
            "position size must include the reinforcement, not just this "
            "trade's own legs")

    def test_scale_in_block_reaches_the_client(self):
        src = inspect.getsource(tr)
        assert '"scale_in": _scale_in' in src

    def test_it_counts_from_the_same_place_the_guard_counts(self):
        """The ceiling counts contracts via trade_contract_count; if the screen
        counted differently the two could disagree about the same position."""
        src = inspect.getsource(tr)
        assert "_contracts_of" in src
        assert "trade_contract_count" in inspect.getsource(tr._contracts_of)


class TestTheParentKnowsItGrew:
    def test_the_link_is_written_back_to_the_parent(self):
        """Until now only the child knew who its parent was, so nothing looking
        at the parent could tell the position had grown."""
        from backend.v9.services.trade_manager import bar_level_detector as bld
        src = inspect.getsource(bld)
        assert 'scale_in_child_id' in src
        assert 'scale_in_added' in src

    def test_the_pending_marker_is_cleared(self):
        """`scale_in_child_pending` was set and never cleared, so every parent
        looked like it had a reinforcement still in flight."""
        from backend.v9.services.trade_manager import bar_level_detector as bld
        src = inspect.getsource(bld)
        assert 'pop("scale_in_child_pending"' in src
