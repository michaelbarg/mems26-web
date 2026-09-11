"""T-313: IB lock label handoff — DAYTYPE_RECLASS_STABILITY bypass.

At the first post-lock classification (_first_lock_done NOT in state), the
stability check must be bypassed (force_immediate=True) so the initial label
commits immediately regardless of N.

When _first_lock_done IS set, normal N-bar confirmation applies and the label
does NOT publish on bar 1 of 2.
"""
from backend.v9.systems.day_type.label_stability import confirm_label

SESSION = "2026-09-10"


def _fresh_state():
    return {"date": SESSION}


# ── T-313-A: first lock — confirm_label publishes immediately ─────────────────

def test_first_lock_bypasses_stability_n2():
    """When _first_lock_done is NOT set, force_immediate=True → publishes on first call."""
    state = _fresh_state()
    # _first_lock_done absent → caller passes force_immediate=True
    result = confirm_label(
        state,
        current="UNKNOWN",      # nothing published yet
        candidate="Trend_Normal",
        n=2,
        session_date=SESSION,
        force_immediate=True,
    )
    assert result is True, "First-lock should publish immediately (force_immediate=True)"


def test_first_lock_publishes_when_current_is_real_label():
    """force_immediate=True also overrides hold when a real label is already current."""
    state = _fresh_state()
    result = confirm_label(
        state,
        current="Normal",
        candidate="Trend_Normal",
        n=2,
        session_date=SESSION,
        force_immediate=True,
    )
    assert result is True, "force_immediate bypasses N even with a real current label"


# ── T-313-B: normal path — confirm_label holds until N bars ──────────────────

def test_normal_path_holds_on_first_of_two_bars():
    """When _first_lock_done IS set, force_immediate is False → N=2 holds on bar 1."""
    state = _fresh_state()
    # Bar 1 — candidate seen for first time
    result_bar1 = confirm_label(
        state,
        current="Normal",
        candidate="Trend_Normal",
        n=2,
        session_date=SESSION,
        force_immediate=False,
    )
    assert result_bar1 is False, "N=2: should NOT publish on bar 1"
    assert state.get("candidate") == "Trend_Normal"
    assert state.get("count") == 1


def test_normal_path_publishes_on_second_bar():
    """N=2 publishes on the second consecutive bar."""
    state = _fresh_state()
    # Bar 1
    confirm_label(state, current="Normal", candidate="Trend_Normal",
                  n=2, session_date=SESSION, force_immediate=False)
    # Bar 2
    result_bar2 = confirm_label(
        state,
        current="Normal",
        candidate="Trend_Normal",
        n=2,
        session_date=SESSION,
        force_immediate=False,
    )
    assert result_bar2 is True, "N=2: should publish on bar 2"


def test_oscillation_never_accumulates():
    """A→B→A oscillation never satisfies N=2 (each flip resets the counter)."""
    state = _fresh_state()
    # Bar 1: Trend_Normal appears
    confirm_label(state, current="Normal", candidate="Trend_Normal",
                  n=2, session_date=SESSION, force_immediate=False)
    # Bar 2: different candidate resets clock
    result = confirm_label(state, current="Normal", candidate="Variation",
                           n=2, session_date=SESSION, force_immediate=False)
    assert result is False, "Different candidate resets clock — must not publish"
    assert state.get("candidate") == "Variation"
    assert state.get("count") == 1
