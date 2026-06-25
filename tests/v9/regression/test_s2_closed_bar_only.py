"""T4: S2 detection runs only on COMPLETED bars (not the partial forming bar).

Bug #3 fix (2026-06-08): the bridge pushes each bar ~20x while building.
Detection on bars[-1] (partial OHLC) produces wrong entries/stops. The fix
trims to buffer[:-1] so detectors see only completed bars.

if reverted → RED because: reverting _det_buf to self._bar_buffer would
remove the [:-1] trim, making the source inspection fail.
"""
def test_s2_detection_uses_completed_bars_only():
    """S2 detection buffer trims the last (partial) bar.

    if reverted → RED because: removing [:-1] trim makes this assertion fail.
    """
    import inspect
    from backend.v9.systems.five_min.five_min_system import FiveMinSystem
    # Find the process_bar / _on_bar method that runs detection
    source = inspect.getsource(FiveMinSystem)
    assert "_det_buf = self._bar_buffer[:-1]" in source, \
        "S2 must detect on buffer[:-1] (completed bars only, not the partial bar)"


def test_s2_partial_bar_comment_documents_fix():
    """The fix is documented in the code (not accidental)."""
    import inspect
    from backend.v9.systems.five_min.five_min_system import FiveMinSystem
    source = inspect.getsource(FiveMinSystem)
    assert "COMPLETED bars" in source
    assert "partial" in source.lower()
