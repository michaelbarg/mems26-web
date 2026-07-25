"""W7 — PATTERN_STOP_COOLDOWN_V1 (cursor doctrine gap-4, 2026-07-25).

After a STOP_HIT on the same pattern-family+direction, an identical re-entry
within the cooldown window is blocked (fighting fresh acceptance, Dalton
p.288-292). Real evidence clusters: 07-21 6x ZLR SHORT in 59min (-$206),
07-20 3x LONG (-$310), 07-22 3x SHORT (-$150) — the first fire passes, the
repeats are the bleed. Far-enough re-entry (new information) passes.
"""
import pytest

import backend.v9.gateway.trading_gateway as gw


def _mk_row(entry=7440.0, ts="2026-07-21 21:00:00"):
    return {"entry_price": entry, "stop_hit_ts": ts}


def _patch_read(monkeypatch, row):
    import backend.v9.db.read as dbread
    monkeypatch.setattr(dbread, "read_one", lambda *a, **k: row)


def test_recent_stop_same_idea_blocked(monkeypatch):
    """A ZLR SHORT stopped minutes ago; re-entry 1.5pt away → blocked."""
    _patch_read(monkeypatch, _mk_row(entry=7440.0))
    blocked, reason = gw._stop_cooldown_check("ZLR", "SHORT", 7441.5)
    assert blocked
    assert "cooldown" in reason


def test_far_reentry_is_new_information(monkeypatch):
    """Same stopped pattern but re-entry 6pt away (>=4 default) → allowed."""
    _patch_read(monkeypatch, _mk_row(entry=7440.0))
    blocked, _ = gw._stop_cooldown_check("ZLR", "SHORT", 7446.0)
    assert not blocked


def test_no_recent_stop_allowed(monkeypatch):
    _patch_read(monkeypatch, None)
    blocked, _ = gw._stop_cooldown_check("ZLR", "SHORT", 7441.5)
    assert not blocked


def test_suffix_normalized(monkeypatch):
    """REACTIVE_SHORT normalizes to REACTIVE% — the row matches → blocked."""
    _patch_read(monkeypatch, _mk_row(entry=7450.0))
    blocked, _ = gw._stop_cooldown_check("REACTIVE_SHORT", "SHORT", 7450.5)
    assert blocked


def test_missing_inputs_fail_open(monkeypatch):
    _patch_read(monkeypatch, _mk_row())
    assert gw._stop_cooldown_check(None, "SHORT", 7441.0) == (False, "")
    assert gw._stop_cooldown_check("ZLR", None, 7441.0) == (False, "")
    assert gw._stop_cooldown_check("ZLR", "SHORT", None) == (False, "")


def test_threshold_env_tunable(monkeypatch):
    """PATTERN_STOP_COOLDOWN_MIN_DIST_PT=8 → a 6pt re-entry now blocks."""
    monkeypatch.setenv("PATTERN_STOP_COOLDOWN_MIN_DIST_PT", "8.0")
    _patch_read(monkeypatch, _mk_row(entry=7440.0))
    blocked, _ = gw._stop_cooldown_check("ZLR", "SHORT", 7446.0)
    assert blocked
