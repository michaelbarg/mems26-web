"""DAYTYPE_HONEST_PRELOCK_V1 — don't report a day_type before the IB locks.

N1c (2026-07-17, docs/handoff/NIGHT_PROMPT_2026-07-17.md): before the IB locks
(~60min/12 bars) `day_type_machine.day_type` can still hold the OLD base
engine's own low-confidence read (e.g. "Trend_Normal" 0.35, seen live on both
2026-07-15 and 2026-07-16 around 10:00 ET) — get_live_day_type()'s exclusion
list didn't catch this string, so it passed through looking like a canonical
verdict on dashboard/pocket screens. Neither engine has a trustworthy answer
before IB lock (the Market Profile foundation isn't formed yet), so once this
flag is on, get_live_day_type() reports None ("forming/unknown") until the
machine says the IB is locked. Default OFF -> byte-identical when unset.
"""
import os
from unittest.mock import patch, MagicMock

from backend.v9.services.trade_context import get_live_day_type


def _mock_app_state(day_type_value, ib_locked):
    dtm = MagicMock()
    dtm.day_type = day_type_value
    dtm.ib_locked = ib_locked
    app = MagicMock()
    app.state.day_type_machine = dtm
    return app


def _env(**extra):
    base = {"DAYTYPE_GATE_LIVE_V1": "1"}
    base.update(extra)
    return base


def test_flag_off_preserves_prelock_leak_byte_identical():
    """Regression guard: default (flag unset) keeps today's behavior — proves
    this fix is opt-in, not a silent change to an already-live gate."""
    mock_app = _mock_app_state("Trend_Normal", ib_locked=False)
    with patch.dict(os.environ, _env()):
        with patch("importlib.import_module", return_value=MagicMock(app=mock_app)):
            result = get_live_day_type()
    assert result == "Trend_Normal"


def test_flag_on_prelock_returns_none():
    """The actual fix: pre-lock, report None instead of the old engine's leak."""
    mock_app = _mock_app_state("Trend_Normal", ib_locked=False)
    with patch.dict(os.environ, _env(DAYTYPE_HONEST_PRELOCK_V1="1")):
        with patch("importlib.import_module", return_value=MagicMock(app=mock_app)):
            result = get_live_day_type()
    assert result is None


def test_flag_on_postlock_still_returns_value():
    """Post-lock, the value (new-classifier-promoted or not) is trustworthy again."""
    mock_app = _mock_app_state("Trend_Normal", ib_locked=True)
    with patch.dict(os.environ, _env(DAYTYPE_HONEST_PRELOCK_V1="1")):
        with patch("importlib.import_module", return_value=MagicMock(app=mock_app)):
            result = get_live_day_type()
    assert result == "Trend_Normal"


def test_flag_on_already_none_stays_none():
    """No new leak introduced when the raw value was already excluded (UNKNOWN etc)."""
    mock_app = _mock_app_state("UNKNOWN", ib_locked=False)
    with patch.dict(os.environ, _env(DAYTYPE_HONEST_PRELOCK_V1="1")):
        with patch("importlib.import_module", return_value=MagicMock(app=mock_app)):
            result = get_live_day_type()
    assert result is None


def test_manual_override_still_wins_over_prelock_gate(monkeypatch):
    """DAY_TYPE_MANUAL_OVERRIDE (Michael is the S1 authority) takes precedence
    over this gate — checked earlier in the function, must not be shadowed."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    monkeypatch.setenv("DAY_TYPE_MANUAL_OVERRIDE", f"{today}:Neutral_Center")
    monkeypatch.setenv("DAYTYPE_HONEST_PRELOCK_V1", "1")
    monkeypatch.setenv("DAYTYPE_GATE_LIVE_V1", "1")
    mock_app = _mock_app_state("Trend_Normal", ib_locked=False)
    with patch("importlib.import_module", return_value=MagicMock(app=mock_app)):
        result = get_live_day_type()
    assert result == "Neutral_Center"
