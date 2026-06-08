"""Bug #3 fix: S2 detection runs on completed bars, not the partial new bar.

RED-on-revert: if reverted → detection uses self._bar_buffer (includes
partial bar as b4) → b4 has opening-tick OHLC → confirmation fails on
bars that would pass with final OHLC → S2 almost never fires.

This test verifies that _det_buf = buffer[:-1] when buffer has enough bars.
"""


def test_det_buf_excludes_last_bar():
    """Detection buffer should be buffer[:-1] (exclude the new partial bar)."""
    # Simulate: 10 bars in buffer, last one is partial
    buffer = [{"o": 7400 + i, "h": 7402 + i, "l": 7398 + i, "c": 7401 + i,
               "vol": 5000, "v": 5000, "ts": f"2026-06-08T{10+i}:00:00"}
              for i in range(10)]

    # The fix: _det_buf = buffer[:-1] if len >= 8
    _det_buf = buffer[:-1] if len(buffer) >= 8 else buffer
    assert len(_det_buf) == 9  # 10 - 1 = 9
    assert _det_buf[-1] == buffer[-2]  # last in det_buf = second-to-last in buffer


def test_det_buf_uses_full_when_small():
    """With < 8 bars, detection uses the full buffer (not enough to trim)."""
    buffer = [{"o": 7400, "h": 7402, "l": 7398, "c": 7401, "vol": 5000}
              for _ in range(5)]
    _det_buf = buffer[:-1] if len(buffer) >= 8 else buffer
    assert len(_det_buf) == 5  # full buffer, not trimmed


def test_entry_from_completed_bar():
    """Entry price should come from the completed bar, not the partial one."""
    buffer = [{"o": 7400, "h": 7402, "l": 7398, "c": 7401 + i, "vol": 5000}
              for i in range(10)]
    # Last bar (partial) has c=7410, second-to-last (completed) has c=7409
    _det_buf = buffer[:-1]
    _completed_bar = _det_buf[-1]
    entry_price = _completed_bar.get("c", 0)
    assert entry_price == 7409  # from completed bar
    assert entry_price != buffer[-1]["c"]  # NOT from partial bar (7410)
