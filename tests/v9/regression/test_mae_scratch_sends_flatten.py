"""H19 — MAE_SCRATCH must SEND the exit before it closes the books.

Michael, live 2026-08-14: "the system reported the trade closed but in reality
the order never reached Sierra."

Trade #682 was marked CLOSED / MAE_SCRATCH / $0.00 at 20:00 IL while Sierra
still held SHORT 4 @7799.25. Consequences, all three observed the same evening:
  1. books ≠ Sierra for 62 minutes (a ghost position with no owner),
  2. the LIVE slot was freed, so the engine could stack another fire on top,
  3. the loss was booked as $0.00, so the daily risk counter under-counted.

TARGET_APPROACH_REALIZE, 34 lines above in the same file, already had the right
order: write FLATTEN_ACCOUNT, then close_trade. MAE_SCRATCH had no write at all.

Fix: same order — and if the command write raises, the books are NOT closed
(an open book on a live position is recoverable; a closed book on a live
position is a ghost), plus a priority-1 phone alert.
"""
import inspect

from backend.v9.services.trade_manager import bar_level_detector as bld


def _scratch_block() -> str:
    """The MAE_SCRATCH region: from the log line to the book close."""
    src = inspect.getsource(bld)
    i = src.index("S6 MAE SCRATCH: trade")
    j = src.index('close_trade(trade.id, reason="MAE_SCRATCH")', i)
    return src[i: j + 60]


class TestFlattenIsSent:
    def test_flatten_command_is_written(self):
        blk = _scratch_block()
        assert "FLATTEN_ACCOUNT" in blk, "MAE_SCRATCH must send an exit to Sierra"
        assert "mae_scratch" in blk

    def test_flatten_precedes_book_close(self):
        blk = _scratch_block()
        i_flat = blk.index("FLATTEN_ACCOUNT")
        i_close = blk.index('close_trade(trade.id, reason="MAE_SCRATCH")')
        assert i_flat < i_close, "the exit must be sent BEFORE the books are closed"

    def test_books_not_closed_when_command_fails(self):
        """The failure branch must `continue` — never fall through to
        close_trade — otherwise we recreate the ghost."""
        blk = _scratch_block()
        i_err = blk.index("FLATTEN command")
        i_close = blk.index('close_trade(trade.id, reason="MAE_SCRATCH")')
        tail = blk[i_err:i_close]
        assert "continue" in tail, "a failed FLATTEN must skip the book close"

    def test_failure_raises_a_phone_alert(self):
        blk = _scratch_block()
        i_err = blk.index("FLATTEN command")
        assert "phone_alert" in blk[i_err:i_err + 700]
        assert "priority=1" in blk[i_err:i_err + 900]


class TestParityWithTargetApproach:
    def test_both_realize_paths_send_flatten(self):
        """The two S6 exit paths must behave identically w.r.t. the broker."""
        src = inspect.getsource(bld)
        assert src.count("FLATTEN_ACCOUNT") >= 2, (
            "both TARGET_APPROACH_REALIZE and MAE_SCRATCH must write FLATTEN")

    def test_neither_path_uses_op_exit(self):
        """op=EXIT is known-broken (CLAUDE.md standing rule) — exits go through
        FLATTEN_ACCOUNT only."""
        src = inspect.getsource(bld)
        assert 'action="EXIT"' not in src
        assert "write_exit(" not in src
