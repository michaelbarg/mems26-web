"""N1 RC#4 — v9_day_type_state additive observability columns (migration 022).

docs/handoff/N1B_TRANSITIONS_DIAGNOSIS_2026-07-17.md §4/§5.5: the table had NO
direction/reason/sides columns — "Variation-DOWN" was not representable, so the
07-15/07-16 missed-transition diagnosis needed memory + replay. This pins:

1. `classify()` emits an always-on `dir_bias` (UP/DOWN/None) so the leg
   direction exists in the canonical result (additive key, no gate reads it).
2. `state_row_extras()` maps the canonical result onto the new columns with a
   session_date freshness stamp — a stale cross-session result yields honest
   NULLs (Rule 1), never yesterday's read dressed as today's.
3. The SQLAlchemy model and migration 022 agree on the 4 columns (drift pin).

No flag: observability-only columns, written unconditionally by the single
writer in backend/main.py (with a legacy-INSERT fallback until 022 is applied).
"""
import importlib.util
import os

from backend.v9.systems.day_type.daytype_classifier import classify, load_plan
from backend.v9.systems.day_type.classifier_core import state_row_extras

PLAN = load_plan()
TODAY = "2026-07-17"


def c(**kw):
    kw.setdefault("n_bars", 30)
    return classify(kw, PLAN)


# ── 1. dir_bias emission (always on, additive) ───────────────────────────────

def test_dir_bias_from_one_tf():
    r = c(sides=1, rib=1.5, one_tf="DOWN", close_pos=0.4)
    assert r["dir_bias"] == "DOWN", r


def test_dir_bias_from_accepted_break_when_no_one_tf():
    r = c(sides=1, rib=1.5, accepted_break="UP", close_pos=0.5)
    assert r["dir_bias"] == "UP", r


def test_dir_bias_from_close_extreme():
    r = c(sides=1, rib=1.5, close_pos=0.92)
    assert r["dir_bias"] == "UP", r
    r = c(sides=1, rib=1.5, close_pos=0.08)
    assert r["dir_bias"] == "DOWN", r


def test_dir_bias_none_when_balanced():
    r = c(sides=0, rib=1.1, close_pos=0.5, vol_ratio=1.0)
    assert r["dir_bias"] is None, r


def test_dir_bias_present_with_all_flags_unset(monkeypatch):
    for k in list(os.environ):
        if k.startswith(("S1_", "DAYTYPE_", "NONTREND")):
            monkeypatch.delenv(k, raising=False)
    r = c(sides=1, rib=1.5, one_tf="UP", close_pos=0.9)
    assert "dir_bias" in r and r["dir_bias"] == "UP", r


# ── 2. state_row_extras honesty + mapping ────────────────────────────────────

def _fresh_result(**over):
    r = {
        "day_type": "Normal_Variation", "status": "PROVISIONAL",
        "direction": "with_extension", "dir_bias": "DOWN",
        "reason": "1-sided extension = Expanded Typical (rib 1.38)",
        "session_date": TODAY,
        "measured": {"sides": 1, "rib": 1.38},
    }
    r.update(over)
    return r


def test_extras_all_none_when_result_absent():
    assert state_row_extras(None, TODAY) == {
        "direction": None, "reason": None, "sides": None, "rib": None}
    assert state_row_extras({}, TODAY) == {
        "direction": None, "reason": None, "sides": None, "rib": None}


def test_extras_all_none_when_result_is_stale_cross_session():
    """Rule 1: yesterday's canonical result must NOT populate today's row."""
    stale = _fresh_result(session_date="2026-07-16")
    assert state_row_extras(stale, TODAY) == {
        "direction": None, "reason": None, "sides": None, "rib": None}


def test_extras_all_none_when_no_session_stamp():
    unstamped = _fresh_result()
    unstamped.pop("session_date")
    assert state_row_extras(unstamped, TODAY)["direction"] is None


def test_extras_maps_fresh_result_variation_down():
    x = state_row_extras(_fresh_result(), TODAY)
    assert x["direction"] == "with_extension(DOWN)"     # "Variation-DOWN" representable
    assert x["reason"].startswith("1-sided extension")
    assert x["sides"] == 1 and x["rib"] == 1.38


def test_extras_strategy_without_leg_stays_bare():
    x = state_row_extras(_fresh_result(direction="fade_both", dir_bias=None), TODAY)
    assert x["direction"] == "fade_both"


def test_extras_missing_measured_gives_null_sides_rib():
    x = state_row_extras(_fresh_result(measured=None), TODAY)
    assert x["sides"] is None and x["rib"] is None


# ── 3. model ↔ migration drift pin ──────────────────────────────────────────

def test_model_has_the_four_columns():
    from backend.v9.systems.day_type.models import V9DayTypeState
    cols = set(V9DayTypeState.__table__.columns.keys())
    assert {"direction", "reason", "sides", "rib"} <= cols, cols


def test_migration_022_declares_the_same_columns():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    path = os.path.join(root, "backend", "v9", "db", "migrations", "versions",
                        "022_day_type_state_n1_columns.py")
    spec = importlib.util.spec_from_file_location("migration_022", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert [c[0] for c in mod.COLUMNS] == ["direction", "reason", "sides", "rib"]
