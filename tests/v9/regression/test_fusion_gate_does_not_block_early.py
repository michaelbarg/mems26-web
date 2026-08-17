"""The fusion gate must not block an opening trade while it is still "not ready".

Michael, 2026-08-17: "האם יש דגלים שהפעלת ועלולים לפגוע בעסקאות טובות?"

This is the honest answer to that question for T7. On 08-16 I changed the
opening fusion to read its volume from the CANONICAL closed bars instead of from
the partial `current_bar` snapshots. That was the right fix — the old comparison
was partial-bar volume against a full-bar median, so the gate said "auction, too
quiet" on 8 of 8 opening candidates it ever saw.

But it introduced a timing hazard. At the moment the 6th LIVE bar arrives, the
6th row may not be closed in the table yet, so the honest answer is None = "not
ready". And a None fusion is exactly what the gate treats as "low conviction —
drop the trade". If that transient None were latched, or if it were allowed to
gate, the system would drop the opening trade for the wrong reason: not because
the open was quiet, but because a database row had not landed yet.

The design that keeps both properties: the gate is only consulted once
`_oe_fusion_done` is set, and `_oe_fusion_done` is set only on a DEFINITIVE
answer (UP/DOWN) or once the window has moved past it (8 bars ≈ 40 min, well
past the 30-minute measurement). "Not ready" therefore means the gate is not
applied at all — the candidate is judged on its other merits — rather than
meaning "no".
"""
import inspect

from backend.v9.systems.five_min import five_min_system as fms


def _gate_region() -> str:
    src = inspect.getsource(fms)
    i = src.index("OPENING_DIR_FUSION_V1: compute the volume-confirmed")
    return src[i:i + 4000]


class TestNotReadyIsNotNo:
    def test_the_latch_waits_for_a_definitive_answer(self):
        blk = _gate_region()
        assert "if self._oe_fusion is not None or len(self._oe_bars) >= 8:" in blk, (
            "a transient None must not become the answer for the whole day")

    def test_the_latch_is_not_set_before_the_call(self):
        """The original bug: `_oe_fusion_done = True` ran BEFORE
        get_opening_dir_fusion(), so whatever came back was final."""
        blk = _gate_region()
        i_call = blk.index("get_opening_dir_fusion(")
        i_latch = blk.index("self._oe_fusion_done = True")
        assert i_latch > i_call, (
            "the latch must close after the answer, not before it")

    def test_the_gate_is_only_consulted_once_settled(self):
        """This is what makes 'not ready' safe: the gate is skipped entirely,
        so the opening candidate is judged on its other merits."""
        src = inspect.getsource(fms)
        i = src.index("OPENING_DIR_FUSION gate dropped")
        blk = src[i - 600:i]
        assert '_oe_fusion_done' in blk, (
            "without this guard a not-ready None would drop a good opening trade")

    def test_a_settled_none_still_blocks(self):
        """The gate must keep working — a genuinely quiet open is still a skip.
        08-14 measured 89,246 contracts against a 114,590 median: that open
        really was quiet, and the fix corrects the measure, not the verdict."""
        src = inspect.getsource(fms)
        i = src.index("OPENING_DIR_FUSION gate dropped")
        blk = src[i - 400:i + 200]
        assert "_fb is None" in blk


class TestTheWindowStillCloses:
    def test_eight_bars_ends_the_wait(self):
        """Retrying forever would leave the gate permanently un-applied, which
        is its own way of losing money."""
        blk = _gate_region()
        assert "len(self._oe_bars) >= 8" in blk

    def test_it_says_so_in_the_log(self):
        blk = _gate_region()
        assert "not ready yet" in blk, (
            "a silent wait is indistinguishable from a broken gate")
