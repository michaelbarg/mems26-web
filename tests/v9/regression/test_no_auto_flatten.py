"""The system no longer closes a position it could not protect.

Michael's ruling 2026-07-28: "תבטל את הכלי שיוצא מעסקאות פתוחות. אם אי אפשר לשים
סטופ במקום אסטרטגי — לא לסגור עסקה."

The orphan flatten existed only because ACSIL cannot place a resting stop on a
position it did not open — proven in sim that same day across three routes plus a
control test. But an exit fired by a virtual line is, by construction, an exit at
the worst available location: it triggers precisely where the market is moving
against the position, with no regard for structure. Not being able to protect a
trade is not a reason to close it badly.

The watch stays. The decision goes back to Michael.
"""
import inspect

import backend.v9.services.sierra_position_reconciler as rec


def test_auto_flatten_is_off_by_default(monkeypatch):
    monkeypatch.delenv("ORPHAN_AUTO_FLATTEN_V1", raising=False)
    assert rec._auto_flatten_enabled() is False


def test_flag_can_re_enable_but_must_be_explicit(monkeypatch):
    monkeypatch.setenv("ORPHAN_AUTO_FLATTEN_V1", "1")
    assert rec._auto_flatten_enabled() is True


def test_breach_path_alerts_before_it_can_flatten():
    """Source-level: the alert-only branch must be evaluated BEFORE the flatten
    branch, so a future edit cannot reinstate the auto-exit by accident."""
    src = inspect.getsource(rec._place_orphan_stop)
    i_alert = src.index("not _auto_flatten_enabled()")
    i_flat = src.index("_flatten_orphan(rec)")
    assert i_alert < i_flat


def test_the_breach_still_shouts():
    """Removing the action must not remove the information."""
    src = inspect.getsource(rec._place_orphan_stop)
    assert "BREACH_ALERT_ONLY" in src
    assert "logger.critical" in src
    assert "phone_alert" in src
