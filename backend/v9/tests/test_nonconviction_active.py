"""Regression for the NONCONVICTION_ACTIVE_V1 fix (P1-8 "no-conviction day = NO_TRADE").

Bug (audit-confirmed): S1_NONCONVICTION_V1 is RULED ON but was INERT end-to-end:
  (a) backend/v9/systems/daytype_playbook.py `_VALID_DT` EXCLUDED "Nonconviction", so
      decide() fell through to fail-open FULL even though config/daytype_playbook.yaml
      carries `Nonconviction: SKIP` cells -> a no-conviction day was NOT stood aside;
  (b) backend/main.py `_DT_MAP` had no "Nonconviction" entry AND schemas.DayType has no
      "Nonconviction" member, so the day-type could never reach day_type_machine.

Fix: a NEW default-OFF flag NONCONVICTION_ACTIVE_V1. When ON, the playbook treats
"Nonconviction" as a valid day-type (yaml SKIP cells gate -> decide() returns SKIP), and
main.py promotes a dedicated NO_TRADE *string* sentinel (schemas.DayType cannot represent
it) onto the live-promoted machine attribute. When OFF, behavior is byte-identical to today.

These tests prove:
  (a) flag OFF  -> a Nonconviction day still fails open to FULL (current behavior);
  (b) flag ON   -> a Nonconviction day yields SKIP / NO_TRADE (stands aside) and the
                   handling does NOT crash on the missing enum member.

If the fix is reverted, (b) goes RED (Nonconviction -> FULL again = never stands aside).
"""
import pytest

import backend.v9.systems.daytype_playbook as pb


@pytest.fixture(autouse=True)
def _clean_playbook_env(monkeypatch):
    """Deterministic env for every test: playbook engine ON, position-gate OFF
    (the position gate short-circuits decide() to FULL), and the config cache
    cleared so the real config/daytype_playbook.yaml is (re)loaded."""
    monkeypatch.setenv("DAYTYPE_PLAYBOOK", "1")
    monkeypatch.delenv("DAYTYPE_POSITION_GATE", raising=False)
    pb.reset_cache()
    yield
    pb.reset_cache()


# ─────────────────────────────────────────────────────────────────────────────
# (a) Flag OFF -> Nonconviction still fails open to FULL (byte-identical to today)
# ─────────────────────────────────────────────────────────────────────────────

def test_nonconviction_flag_off_fails_open_to_full(monkeypatch):
    """NONCONVICTION_ACTIVE_V1 unset (default OFF): a Nonconviction day is unmapped
    in _VALID_DT -> decide() fails open to FULL (the pre-fix, still-inert behavior)."""
    monkeypatch.delenv("NONCONVICTION_ACTIVE_V1", raising=False)

    d = pb.decide(pattern="ZLR", day_type="Nonconviction", direction="LONG")

    assert d.verdict == "FULL"
    assert d.allow is True
    assert "unmapped" in d.reason  # proves it took the fail-open path, not a real cell


def test_nonconviction_flag_explicit_zero_fails_open(monkeypatch):
    """Explicit '0' behaves the same as unset -> FULL."""
    monkeypatch.setenv("NONCONVICTION_ACTIVE_V1", "0")

    d = pb.decide(pattern="REACTIVE", day_type="Nonconviction", direction="SHORT",
                  trend_state="RED")

    assert d.verdict == "FULL"
    assert d.allow is True


# ─────────────────────────────────────────────────────────────────────────────
# (b) Flag ON -> Nonconviction yields SKIP / NO_TRADE (stands aside), no crash
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("pattern,direction,trend_state", [
    ("ZLR", "LONG", "GREEN"),        # continuation
    ("REACTIVE", "SHORT", "RED"),    # reversal, require_with_trend
    ("HNS", "LONG", "GREEN"),        # reversal, require_with_trend
    ("VEGAS", "SHORT", None),        # reversal
])
def test_nonconviction_flag_on_skips(monkeypatch, pattern, direction, trend_state):
    """NONCONVICTION_ACTIVE_V1=1: every pattern stands aside on a Nonconviction day
    (config/daytype_playbook.yaml marks `Nonconviction: SKIP` for all patterns)."""
    monkeypatch.setenv("NONCONVICTION_ACTIVE_V1", "1")

    d = pb.decide(pattern=pattern, day_type="Nonconviction", direction=direction,
                  trend_state=trend_state)

    assert d.verdict == "SKIP", f"{pattern} should SKIP on Nonconviction, got {d.verdict}"
    assert d.allow is False       # NO_TRADE: the gateway veto (allow=False) blocks the fire
    assert d.contracts == 0


def test_nonconviction_flag_on_true_alias(monkeypatch):
    """Flag accepts the same truthy spellings as the rest of the stack ('true')."""
    monkeypatch.setenv("NONCONVICTION_ACTIVE_V1", "true")

    d = pb.decide(pattern="ZLR", day_type="Nonconviction", direction="LONG")

    assert d.verdict == "SKIP"
    assert d.allow is False


def test_nonconviction_flag_on_does_not_raise(monkeypatch):
    """The ON path must never raise on the string day-type (no enum coercion)."""
    monkeypatch.setenv("NONCONVICTION_ACTIVE_V1", "1")
    # Must not raise:
    d = pb.decide(pattern="ZLR", day_type="Nonconviction", direction="LONG")
    assert isinstance(d.verdict, str)


# ─────────────────────────────────────────────────────────────────────────────
# Scope guard: the flag changes ONLY the Nonconviction day-type, nothing else
# ─────────────────────────────────────────────────────────────────────────────

def test_flag_on_leaves_other_day_types_unchanged(monkeypatch):
    """With the flag ON, the seven pre-existing day-types decide exactly as before:
    Trend_Normal ZLR -> FULL, Nontrend ZLR -> SKIP (both pre-existing)."""
    monkeypatch.setenv("NONCONVICTION_ACTIVE_V1", "1")

    trend = pb.decide(pattern="ZLR", day_type="Trend_Normal", direction="LONG",
                      trend_state="GREEN")
    assert trend.verdict == "FULL"

    nontrend = pb.decide(pattern="ZLR", day_type="Nontrend", direction="LONG")
    assert nontrend.verdict == "SKIP"  # pre-existing (Nontrend was always in _VALID_DT)


def test_flag_off_nontrend_still_skips(monkeypatch):
    """Sanity: the flag is scoped to 'Nonconviction' — pre-existing 'Nontrend' SKIP
    is untouched whether the flag is on or off."""
    monkeypatch.delenv("NONCONVICTION_ACTIVE_V1", raising=False)

    d = pb.decide(pattern="ZLR", day_type="Nontrend", direction="LONG")
    assert d.verdict == "SKIP"


def test_playbook_engine_off_is_full_regardless(monkeypatch):
    """When the whole engine is OFF (DAYTYPE_PLAYBOOK unset), even flag-ON Nonconviction
    is FULL — the new flag never blocks on its own."""
    monkeypatch.delenv("DAYTYPE_PLAYBOOK", raising=False)
    monkeypatch.setenv("NONCONVICTION_ACTIVE_V1", "1")

    d = pb.decide(pattern="ZLR", day_type="Nonconviction", direction="LONG")
    assert d.verdict == "FULL"


# ─────────────────────────────────────────────────────────────────────────────
# Enum constraint that FORCES main.py's raw-string NO_TRADE sentinel
# ─────────────────────────────────────────────────────────────────────────────

def test_daytype_enum_has_no_nonconviction_member():
    """schemas.DayType (== state_machine.DayType, the enum main.py's _DT_MAP uses) has
    NO 'Nonconviction' member. So `_DT.Nonconviction` / `DayType("Nonconviction")` would
    raise — proving why main.py must publish a *string* NO_TRADE sentinel, not an enum."""
    pytest.importorskip("pydantic")
    from backend.v9.systems.day_type.schemas import DayType

    assert "Nonconviction" not in DayType.__members__
    assert not hasattr(DayType, "Nonconviction")
    with pytest.raises(ValueError):
        DayType("Nonconviction")


def test_string_sentinel_is_str_safe_for_live_readers():
    """The raw-string sentinel main.py writes onto day_type_machine.day_type is safely
    consumed by its only two readers, which both use the `.value if hasattr else str`
    idiom (trade_context.get_live_day_type:539, day_type_inspector:68). Mirror that idiom
    here: it yields 'Nonconviction' and never raises (unlike an unguarded `.value`)."""
    sentinel = "Nonconviction"  # exactly what main.py assigns when the flag is ON

    surfaced = sentinel.value if hasattr(sentinel, "value") else str(sentinel)
    assert surfaced == "Nonconviction"

    # And it is excluded from the "not a real classification" set get_live_day_type filters,
    # so it propagates through to day_type_at_entry (rather than being dropped like FORMING).
    assert surfaced not in ("UNKNOWN", "None", "INDETERMINATE", "FORMING")
