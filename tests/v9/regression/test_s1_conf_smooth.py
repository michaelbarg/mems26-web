"""S1_CONF_SMOOTH_V1 — slew-cap smoothing for the published day-type confidence.

N1 RC#3 (2026-07-17, docs/handoff/N1B_TRANSITIONS_DIAGNOSIS_2026-07-17.md):
`_confidence()` switches between the 8-item directional evidence list and the
3-item balance list whenever its direction-basis flips — adjacent bars flip the
denominator, so the persisted confidence flapped 0.12↔0.67↔1.00 with no market
change (proven live 07-16 + in both 07-15/07-16 replays: max adjacent delta 0.88).

`smooth_confidence(prev, raw, day_type)` is applied at the SEQUENCE layer (live
promoter in backend/main.py + the classify_replay timeline loop): the published
confidence moves at most S1_CONF_SMOOTH_MAX_DELTA (default 0.25) per bar toward
the raw score. Guarantees the N1B T2 acceptance bound (adjacent-bar delta <=0.35)
by construction. Type decisions untouched. Flag default OFF -> returns raw.
"""
from backend.v9.systems.day_type.daytype_classifier import smooth_confidence


# ── flag OFF (default) = inert, byte-identical ──────────────────────────────

def test_flag_unset_returns_raw_unchanged(monkeypatch):
    monkeypatch.delenv("S1_CONF_SMOOTH_V1", raising=False)
    assert smooth_confidence(0.12, 1.0, "Normal") == 1.0
    assert smooth_confidence(1.0, 0.12, "Normal_Variation") == 0.12
    assert smooth_confidence(None, 0.67, "Neutral_Center") == 0.67


def test_flag_zero_returns_raw_unchanged(monkeypatch):
    monkeypatch.setenv("S1_CONF_SMOOTH_V1", "0")
    assert smooth_confidence(0.12, 1.0, "Normal") == 1.0


def test_none_raw_passthrough_regardless_of_flag(monkeypatch):
    monkeypatch.delenv("S1_CONF_SMOOTH_V1", raising=False)
    assert smooth_confidence(0.5, None, "Normal") is None
    monkeypatch.setenv("S1_CONF_SMOOTH_V1", "1")
    assert smooth_confidence(0.5, None, "Normal") is None


# ── flag ON = per-bar slew cap ───────────────────────────────────────────────

def test_flag_on_caps_upward_jump(monkeypatch):
    monkeypatch.setenv("S1_CONF_SMOOTH_V1", "1")
    # the exact live flap: 0.12 -> 1.00 raw becomes a 0.25 step
    assert smooth_confidence(0.12, 1.0, "Normal") == 0.37


def test_flag_on_caps_downward_jump(monkeypatch):
    monkeypatch.setenv("S1_CONF_SMOOTH_V1", "1")
    assert smooth_confidence(1.0, 0.12, "Normal") == 0.75


def test_flag_on_small_moves_pass_through(monkeypatch):
    monkeypatch.setenv("S1_CONF_SMOOTH_V1", "1")
    assert smooth_confidence(0.5, 0.6, "Normal") == 0.6
    assert smooth_confidence(0.5, 0.5, "Normal") == 0.5


def test_flag_on_first_classified_bar_takes_raw(monkeypatch):
    """No smoothing state yet (prev None) -> raw, so the IB-lock read isn't lagged."""
    monkeypatch.setenv("S1_CONF_SMOOTH_V1", "1")
    assert smooth_confidence(None, 0.62, "Normal") == 0.62


def test_flag_on_forming_is_exempt(monkeypatch):
    """FORMING is honest-zero and carries no smoothing state."""
    monkeypatch.setenv("S1_CONF_SMOOTH_V1", "1")
    assert smooth_confidence(0.75, 0.0, "FORMING") == 0.0


def test_flag_on_converges_to_raw_within_four_bars(monkeypatch):
    monkeypatch.setenv("S1_CONF_SMOOTH_V1", "1")
    seq, prev = [], 0.12
    for _ in range(4):
        prev = smooth_confidence(prev, 1.0, "Normal")
        seq.append(prev)
    assert seq == [0.37, 0.62, 0.87, 1.0]


def test_flag_on_flapping_sequence_meets_t2_bound(monkeypatch):
    """N1B T2 acceptance bound: adjacent-bar confidence delta <= 0.35 even when the
    raw score flaps full-scale every bar (the exact 07-16 symptom)."""
    monkeypatch.setenv("S1_CONF_SMOOTH_V1", "1")
    raws = [0.12, 1.0, 0.12, 1.0, 0.67, 0.0, 1.0, 0.25, 1.0]
    prev = None
    smoothed = []
    for r in raws:
        prev = smooth_confidence(prev, r, "Normal")
        smoothed.append(prev)
    deltas = [abs(b - a) for a, b in zip(smoothed, smoothed[1:])]
    assert max(deltas) <= 0.35, (smoothed, deltas)


def test_flag_on_custom_max_delta_env(monkeypatch):
    monkeypatch.setenv("S1_CONF_SMOOTH_V1", "1")
    monkeypatch.setenv("S1_CONF_SMOOTH_MAX_DELTA", "0.5")
    assert smooth_confidence(0.12, 1.0, "Normal") == 0.62


def test_flag_on_bad_max_delta_falls_back(monkeypatch):
    monkeypatch.setenv("S1_CONF_SMOOTH_V1", "1")
    monkeypatch.setenv("S1_CONF_SMOOTH_MAX_DELTA", "junk")
    assert smooth_confidence(0.12, 1.0, "Normal") == 0.37
