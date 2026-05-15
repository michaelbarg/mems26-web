"""ExtensionTracker tests — 4 scenarios per IB extension tracking."""

from backend.v9.systems.day_type.extensions import (
    ExtensionTracker, Direction,
)


def test_extension_up_detected():
    """Bar closing above IB high triggers UP extension event."""
    t = ExtensionTracker()
    t.lock_ib(ib_high=7510.0, ib_low=7490.0)

    ext, fail = t.on_bar_close(7515.0, ts=1000.0)
    assert ext is not None
    assert ext.direction == Direction.UP
    assert ext.price == 7515.0
    assert ext.ib_boundary == 7510.0
    assert fail is None
    assert t.extensions_up == 1


def test_extension_down_detected():
    """Bar closing below IB low triggers DOWN extension event."""
    t = ExtensionTracker()
    t.lock_ib(ib_high=7510.0, ib_low=7490.0)

    ext, fail = t.on_bar_close(7485.0, ts=2000.0)
    assert ext is not None
    assert ext.direction == Direction.DOWN
    assert ext.price == 7485.0
    assert ext.ib_boundary == 7490.0
    assert fail is None
    assert t.extensions_down == 1


def test_failed_extension_returns_to_ib():
    """Extension that returns inside IB produces FailedExtensionEvent."""
    t = ExtensionTracker()
    t.lock_ib(ib_high=7510.0, ib_low=7490.0)

    # First bar extends up
    ext, fail = t.on_bar_close(7520.0, ts=1000.0)
    assert ext is not None
    assert fail is None

    # Second bar returns inside IB
    ext2, fail2 = t.on_bar_close(7505.0, ts=2000.0)
    assert ext2 is None
    assert fail2 is not None
    assert fail2.direction == Direction.UP
    assert fail2.peak_price == 7520.0
    assert fail2.return_price == 7505.0
    assert t.failed_extensions_up == 1


def test_no_event_before_lock():
    """Before lock_ib() is called, on_bar_close returns (None, None)."""
    t = ExtensionTracker()
    ext, fail = t.on_bar_close(9999.0, ts=500.0)
    assert ext is None
    assert fail is None
    assert t.is_locked is False
