"""Tests for First Hour Buffer state machine (Tree V3.3 §Stage B)."""
from backend.v9.systems.five_min.first_hour_buffer import FirstHourBuffer, BufferState


def test_accumulating_first_3_bars():
    buf = FirstHourBuffer()
    for _ in range(3):
        buf.on_bar()
    assert buf.state == BufferState.ACCUMULATING
    assert buf.eligible_patterns == set()


def test_early_bars_4_to_6():
    buf = FirstHourBuffer()
    for _ in range(5):
        buf.on_bar()
    assert buf.state == BufferState.EARLY
    assert "REACTIVE_LONG" in buf.eligible_patterns
    assert "INITIATIVE_LONG" not in buf.eligible_patterns


def test_developing_bars_7_to_9():
    buf = FirstHourBuffer()
    for _ in range(8):
        buf.on_bar()
    assert buf.state == BufferState.DEVELOPING
    assert "INITIATIVE_LONG" in buf.eligible_patterns


def test_mature_bars_10_to_12():
    buf = FirstHourBuffer()
    for _ in range(11):
        buf.on_bar()
    assert buf.state == BufferState.MATURE


def test_complete_after_12():
    buf = FirstHourBuffer()
    for _ in range(13):
        buf.on_bar()
    assert buf.state == BufferState.COMPLETE
    assert buf.bar_count == 13
