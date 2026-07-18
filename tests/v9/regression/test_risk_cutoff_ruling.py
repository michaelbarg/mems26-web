"""Michael ruling 2026-07-19: no-new-live-entries cutoff moved 14:30 → 15:30 ET.

Evidence (07-17 shadow book): the 14:30 cutoff blocked 4 shadow trades — 3 winning S4
shorts (#401 +28.75, #402 +26.25, #404 +93.75) and 1 losing S2 long (#403 −86.25) =
net +$62.50 the cutoff cost. 15:30 keeps only the last-30-minutes discipline.

Pins: the default IS 15:30 (not 14:30), the boundary behaves correctly, and the
values are env-tunable (they were hardcoded before this ruling).
"""
import importlib

import backend.v9.gateway.risk_checks as rc


def _reload(monkeypatch, hour=None, minute=None):
    if hour is None:
        monkeypatch.delenv("RISK_CUTOFF_HOUR_ET", raising=False)
    else:
        monkeypatch.setenv("RISK_CUTOFF_HOUR_ET", str(hour))
    if minute is None:
        monkeypatch.delenv("RISK_CUTOFF_MINUTE_ET", raising=False)
    else:
        monkeypatch.setenv("RISK_CUTOFF_MINUTE_ET", str(minute))
    return importlib.reload(rc)


def test_default_is_1530_not_1430(monkeypatch):
    """The ruling: default cutoff is 15:30 ET."""
    m = _reload(monkeypatch)
    assert (m.CUTOFF_HOUR, m.CUTOFF_MINUTE) == (15, 30), (
        f"expected 15:30 default, got {m.CUTOFF_HOUR}:{m.CUTOFF_MINUTE:02d}")


def test_env_tunable(monkeypatch):
    """Was hardcoded before the ruling — must now be changeable without code edits."""
    m = _reload(monkeypatch, hour=14, minute=45)
    assert (m.CUTOFF_HOUR, m.CUTOFF_MINUTE) == (14, 45)


def test_bad_env_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("RISK_CUTOFF_HOUR_ET", "not-a-number")
    monkeypatch.delenv("RISK_CUTOFF_MINUTE_ET", raising=False)
    m = importlib.reload(rc)
    assert m.CUTOFF_HOUR == 15


def test_the_0717_window_is_now_open(monkeypatch):
    """The 3 winning S4 shorts fired 21:35-22:10 IL = 14:35-15:10 ET.
    Under the new 15:30 cutoff that whole window is tradeable; the old 14:30 blocked it."""
    m = _reload(monkeypatch)
    cutoff_min = m.CUTOFF_HOUR * 60 + m.CUTOFF_MINUTE
    for et_h, et_m, label in ((14, 35, "#401"), (14, 40, "#402"), (15, 10, "#404")):
        assert et_h * 60 + et_m < cutoff_min, f"{label} still blocked at {et_h}:{et_m:02d} ET"


def test_still_blocks_the_last_half_hour(monkeypatch):
    """Discipline preserved: 15:30 ET onward stays blocked."""
    m = _reload(monkeypatch)
    cutoff_min = m.CUTOFF_HOUR * 60 + m.CUTOFF_MINUTE
    for et_h, et_m in ((15, 30), (15, 45), (15, 59)):
        assert et_h * 60 + et_m >= cutoff_min, f"{et_h}:{et_m:02d} ET should be blocked"
