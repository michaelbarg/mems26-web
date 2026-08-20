"""DAYTYPE_RECLASS_STABILITY_V1 — T-47 / F6 (Michael 2026-08-19, re-confirmed 08-20).

The label the engine publishes flips 200 times over 54 sessions (3.7/session,
53/54 sessions flip at least once).  49% of the interior runs are pure A->B->A
reverts and 28.5% of every non-final label survives exactly ONE bar.  That noise
is what makes `v9_day_type_history` and `day_type_at_entry` disagree on 46% of
days (-$728.75 on disagreeing days vs +$1,048.75 on agreeing ones,
docs/reports/DAILY_EXTREMES_PLAYBOOK_2026-08-20.md §3).

This flag requires a label CHANGE to repeat on N consecutive bars before it is
published.  N=2 measured (scripts/daytype_stability_study.py) — see the module
docstring of backend/v9/systems/day_type/label_stability.py for the full table.

The fixtures below are REAL published-label timelines, replayed bar-by-bar from
`v9_bars_5min_woodies` through the repo's own `classify_session` with the live
S1_* flag set, then frozen here.  They are not invented sequences.
"""
import os

import pytest

from backend.v9.systems.day_type.label_stability import (
    DEFAULT_CONFIRM_BARS,
    confirm_bars,
    confirm_label,
    is_label,
    pending_view,
)

TODAY = "2026-08-20"


# --------------------------------------------------------------------------
# real frozen timelines: (label, bars_it_survived) runs, in order
# --------------------------------------------------------------------------
# 2026-08-05 — the textbook flip-flop. Live said Variation, post-hoc said
# Trend_DD (a 🔴 row in the playbook table). The tail is Trend_DD for ONE bar,
# back to Variation for 3, then Trend_DD for ONE bar at the close.
RUNS_08_05 = [("Nontrend", 2), ("Normal", 1), ("Variation", 8), ("Trend_DD", 13),
              ("Variation", 38), ("Trend_DD", 1), ("Variation", 3), ("Trend_DD", 1)]

# 2026-08-18 — Normal holds 55 bars, then a single Variation bar on the close.
RUNS_08_18 = [("Nontrend", 11), ("Normal", 55), ("Variation", 1)]

# 2026-08-19 — a REAL regime change: Variation takes over and holds 64 bars.
RUNS_08_19 = [("Nontrend", 2), ("Normal", 1), ("Variation", 64)]

# 2026-06-15 — the worst churn in the sample: 7 flips, including a 1-bar
# Variation head-fake 14 bars before Variation genuinely takes over.
RUNS_06_15 = [("Nontrend", 7), ("Normal", 3), ("Trend_Normal", 3), ("Variation", 1),
              ("Trend_Normal", 12), ("Variation", 14), ("Trend_DD", 1), ("Variation", 26)]


def expand(runs):
    """runs -> the per-bar candidate sequence the live promotion path sees."""
    out = []
    for label, n in runs:
        out.extend([label] * n)
    return out


def replay(seq, n):
    """Feed `seq` through the stabiliser; return the per-bar PUBLISHED sequence."""
    state = {}
    published = None
    out = []
    for cand in seq:
        if confirm_label(state, published, cand, n, TODAY):
            published = cand
        out.append(published)
    return out


def flips(published):
    return sum(1 for a, b in zip(published, published[1:]) if a != b)


# ==========================================================================
# 1. FLAG OFF / N=1  ==  today's behaviour, byte-identical
# ==========================================================================
def test_n1_is_byte_identical_to_today():
    """N<=1 publishes every change immediately — the current live behaviour.

    This is the anti-regression anchor: the flag is default OFF in code, and even
    if someone sets it ON with N=1 the published series must be the raw series.
    """
    for runs in (RUNS_08_05, RUNS_08_18, RUNS_08_19, RUNS_06_15):
        seq = expand(runs)
        assert replay(seq, 1) == seq
        assert replay(seq, 0) == seq          # malformed-low N degrades to immediate


def test_default_n_is_two_and_malformed_env_falls_back(monkeypatch):
    """N comes from DAYTYPE_RECLASS_CONFIRM_BARS; garbage must not silently
    disable the damping (that would be a flag that looks ON and does nothing)."""
    monkeypatch.delenv("DAYTYPE_RECLASS_CONFIRM_BARS", raising=False)
    assert confirm_bars() == DEFAULT_CONFIRM_BARS == 2
    monkeypatch.setenv("DAYTYPE_RECLASS_CONFIRM_BARS", "3")
    assert confirm_bars() == 3
    for junk in ("", "  ", "abc", "0", "-4", "2.7"):
        monkeypatch.setenv("DAYTYPE_RECLASS_CONFIRM_BARS", junk)
        assert confirm_bars() == 2, junk


# ==========================================================================
# 2. the flip-flop is damped
# ==========================================================================
def test_flipflop_1bar_blip_never_publishes():
    """A->B->A where B lasts a single bar: B must never reach the gates."""
    seq = ["Variation"] * 5 + ["Trend_DD"] + ["Variation"] * 5
    pub = replay(seq, 2)
    assert "Trend_DD" not in pub
    assert flips(pub) == 0


def test_real_0805_tail_flipflop_is_damped():
    """2026-08-05, real data: 7 raw flips -> 3, and neither 1-bar Trend_DD
    blip is ever published. The 13-bar Trend_DD earlier in the day IS."""
    seq = expand(RUNS_08_05)
    raw, pub = replay(seq, 1), replay(seq, 2)
    assert flips(raw) == 7
    assert flips(pub) == 3
    assert pub[-1] == "Variation"          # the 1-bar closing blip did not stick
    assert "Trend_DD" in pub                # the genuine 13-bar Trend_DD did


def test_real_0818_single_closing_bar_is_damped():
    """2026-08-18: Normal held 55 bars, then ONE Variation bar on the close."""
    seq = expand(RUNS_08_18)
    assert flips(replay(seq, 1)) == 2
    pub = replay(seq, 2)
    assert flips(pub) == 1
    assert pub[-1] == "Normal"


def test_oscillation_never_accumulates():
    """B and C alternating must not add up to N — the clock restarts on a
    different candidate. Otherwise two unrelated blips would publish one of them."""
    seq = ["Variation"] + ["Trend_DD", "Normal"] * 8
    pub = replay(seq, 2)
    assert set(pub) == {"Variation"}


# ==========================================================================
# 3. a REAL regime change still passes (never block, only damp)
# ==========================================================================
def test_real_0819_regime_change_still_passes():
    """2026-08-19, real data: Variation genuinely takes over for 64 bars.
    It must still be published — exactly ONE bar later than raw."""
    seq = expand(RUNS_08_19)
    raw, pub = replay(seq, 1), replay(seq, 2)
    assert pub[-1] == raw[-1] == "Variation"
    assert raw.index("Variation") + 1 == pub.index("Variation")


def test_real_0615_final_label_survives_the_churn():
    """2026-06-15, the worst churn: 7 flips -> 3, final label unchanged.
    The 1-bar Variation head-fake does NOT publish, so 'Variation' is first
    published at the 14-bar run — the damping working, not a delay."""
    seq = expand(RUNS_06_15)
    raw, pub = replay(seq, 1), replay(seq, 2)
    assert flips(raw) == 7 and flips(pub) == 3
    assert pub[-1] == raw[-1] == "Variation"


def test_change_publishes_on_exactly_the_nth_bar():
    """Boundary: with N=2 the change lands on the 2nd agreeing bar, not the 1st
    or the 3rd. With N=3, on the 3rd."""
    seq = ["Variation"] + ["Trend_Normal"] * 5
    assert replay(seq, 2) == ["Variation", "Variation", "Trend_Normal",
                              "Trend_Normal", "Trend_Normal", "Trend_Normal"]
    assert replay(seq, 3) == ["Variation", "Variation", "Variation",
                              "Trend_Normal", "Trend_Normal", "Trend_Normal"]


# ==========================================================================
# 4. semantics of the pure helper
# ==========================================================================
def test_first_ever_label_is_accepted_immediately():
    """Nothing published yet => nothing to protect. A day must not spend its
    first N bars unlabelled because of a damping rule."""
    st = {}
    assert confirm_label(st, None, "Variation", 2, TODAY) is True


@pytest.mark.parametrize("current", ["", "UNKNOWN", "None", "INDETERMINATE", "FORMING", None])
def test_non_label_current_accepts_immediately(current):
    assert confirm_label({}, current, "Variation", 2, TODAY) is True


@pytest.mark.parametrize("cand", ["", "UNKNOWN", "None", "INDETERMINATE", "FORMING", None])
def test_non_label_candidate_is_ignored(cand):
    st = {"date": TODAY, "candidate": "Trend_DD", "count": 1}
    assert confirm_label(st, "Variation", cand, 2, TODAY) is False
    assert st["candidate"] == "Trend_DD" and st["count"] == 1   # clock untouched


def test_same_label_clears_a_pending_candidate():
    st = {}
    assert confirm_label(st, "Variation", "Trend_DD", 2, TODAY) is False
    assert st["candidate"] == "Trend_DD"
    assert confirm_label(st, "Variation", "Variation", 2, TODAY) is False
    assert "candidate" not in st                                # confirmed current


def test_session_roll_resets_the_pending_clock():
    """A candidate must never carry across the ET day roll — yesterday's pending
    change publishing on today's first bar is exactly the class of bug this
    flag exists to remove."""
    st = {}
    confirm_label(st, "Variation", "Trend_DD", 2, "2026-08-19")
    assert st["count"] == 1
    assert confirm_label(st, "Variation", "Trend_DD", 2, "2026-08-20") is False
    assert st["date"] == "2026-08-20" and st["count"] == 1


def test_is_label_and_pending_view():
    assert is_label("Variation") and not is_label("FORMING") and not is_label(None)
    assert pending_view({}) == "-"
    assert pending_view({"candidate": "Trend_DD", "count": 1}) == "Trend_DD 1"


# ==========================================================================
# 5. the wiring in main.py (the single promotion point)
# ==========================================================================
def test_main_promotion_is_gated_by_the_flag_and_defaults_off():
    """Structural guard: the promotion block must consult the stabiliser and the
    flag must default OFF, so an unset env is byte-identical to today."""
    import re
    src = open(os.path.join(os.path.dirname(__file__), "..", "..", "..",
                            "backend", "main.py")).read()
    assert "DAYTYPE_RECLASS_STABILITY_V1" in src
    m = re.search(r'_stab_on\s*=\s*_os\.environ\.get\(\s*\n?\s*"DAYTYPE_RECLASS_STABILITY_V1",\s*"0"', src)
    assert m, "flag must read with a '0' default (OFF in code)"
    # the legacy test is preserved verbatim as the OFF path
    assert "_publish = (_new_dt != state.day_type)" in src
    assert "confirm_label as _stab_confirm" in src
    # and the one-source re-sync only runs under the flag
    assert "ONE-SOURCE re-sync" in src
