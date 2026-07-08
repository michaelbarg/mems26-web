"""Anti-tautological tests for the S1 Dalton P0 items (Michael 2026-07-08, flag-OFF by default).

Each P0 is proven two ways:
  1. flag ON  → the new behavior fires;
  2. flag OFF → BYTE-IDENTICAL to the old classifier (the flag is a true no-op when unset);
  3. reverted → remove the defining input with the flag ON → the behavior disappears
     (proves the assertion is NOT tautological — it depends on the real signal, not the flag).

P0-1  S1_ACCEPTANCE_RECLASS_V1   — accepted reference breakout ⇒ prompt reclass (waive rib≥2.5)
P0-2  S1_COMMITTED_PROVISIONAL_V1 — committed provisional from the open at 30 min (no bare FORMING)
P0-3  S1_CONFIDENCE_V2           — one canonical confidence ∈[0,1], rises with aligned evidence
"""
import os
from contextlib import contextmanager

from backend.v9.systems.day_type.daytype_classifier import classify, load_plan

PLAN = load_plan()
LOCKED = 30   # bars well past the 12-bar (60-min) IB lock


@contextmanager
def flag(name, value="1"):
    old = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = old


def c(**kw):
    kw.setdefault("n_bars", LOCKED)
    return classify(kw, PLAN)


# ══════════════════════════════════════════════════════════════════════════════
# P0-1 · acceptance-driven prompt reclassification (S1_ACCEPTANCE_RECLASS_V1)
# ══════════════════════════════════════════════════════════════════════════════
_BREAK_DOWN = dict(sides=1, rib=1.6, one_tf="DOWN", close_pos=0.30,
                   accepted_break="DOWN", accepted_break_ref="IB")


def test_p0_1_flag_off_is_not_trend_baseline():
    # rib 1.6 < 2.5 Trend floor, no acceptance-reclass → the OLD behavior = Normal_Variation.
    r = c(**_BREAK_DOWN)
    assert r["day_type"] == "Normal_Variation", r
    assert "reclass" not in r and "confidence" not in r, r   # both flags off ⇒ no new keys


def test_p0_1_flag_on_accepted_break_reclasses_to_trend():
    # THE FIX: an accepted DOWN break + one_tf DOWN ⇒ Trend_Normal even at rib 1.6 (<2.5 floor waived).
    with flag("S1_ACCEPTANCE_RECLASS_V1"):
        r = c(**_BREAK_DOWN)
    assert r["day_type"] == "Trend_Normal" and r.get("reclass") is True, r
    assert r.get("break_dir") == "DOWN" and r.get("reclass_ref") == "IB", r


def test_p0_1_reverted_no_accepted_break_stays_variation():
    # ANTI-TAUTOLOGY: same flag ON but remove the accepted break → falls back to Normal_Variation.
    kw = dict(_BREAK_DOWN); kw.pop("accepted_break"); kw.pop("accepted_break_ref")
    with flag("S1_ACCEPTANCE_RECLASS_V1"):
        r = c(**kw)
    assert r["day_type"] == "Normal_Variation" and "reclass" not in r, r


def test_p0_1_accepted_break_with_dd_is_trend_dd():
    with flag("S1_ACCEPTANCE_RECLASS_V1"):
        r = c(sides=1, rib=2.1, one_tf="DOWN", accepted_break="DOWN",
              accepted_break_ref="prior_range", dd_second_dist=True)
    assert r["day_type"] == "Trend_DD" and r.get("reclass") is True, r


def test_p0_1_accepted_break_without_one_tf_is_variation_reclass():
    # accepted break but one_tf not yet confirming → promote to Variation in the break dir (not Trend).
    with flag("S1_ACCEPTANCE_RECLASS_V1"):
        r = c(sides=1, rib=1.4, one_tf=None, accepted_break="DOWN", accepted_break_ref="IB")
    assert r["day_type"] == "Normal_Variation" and r.get("reclass") is True and r.get("break_dir") == "DOWN", r


def test_p0_1_failed_break_reverts_and_tags():
    # rejection: a prior accepted break returned inside → NO promotion (revert) + failed_breakout tag.
    with flag("S1_ACCEPTANCE_RECLASS_V1"):
        r = c(**_BREAK_DOWN, failed_break=True)
    assert r["day_type"] == "Normal_Variation", r          # reverted, NOT Trend
    assert r.get("failed_breakout") is True and "reclass" not in r, r


def test_p0_1_invalidated_open_blocks_reclass():
    # returned-through-open (oi) is priority-0 → the reclass overlay must NOT promote to Trend.
    with flag("S1_ACCEPTANCE_RECLASS_V1"):
        r = c(**_BREAK_DOWN, returned_through_open=True)
    assert r["day_type"] != "Trend_Normal" and r["invalidated"] is True, r


# ══════════════════════════════════════════════════════════════════════════════
# P0-2 · committed provisional from the open at 30 min (S1_COMMITTED_PROVISIONAL_V1)
# ══════════════════════════════════════════════════════════════════════════════
def test_p0_2_flag_off_is_forming_at_30min():
    # OLD behavior: bare FORMING for the whole first hour.
    r = classify({"n_bars": 6, "opening_type": "OPEN_DRIVE", "open_location": "out_of_range",
                  "open_dir": "UP"}, PLAN)
    assert r["status"] == "FORMING" and r["day_type"] == "FORMING", r


def test_p0_2_flag_on_drive_out_of_range_is_provisional_trend():
    with flag("S1_COMMITTED_PROVISIONAL_V1"):
        r = classify({"n_bars": 6, "opening_type": "OPEN_DRIVE", "open_location": "out_of_range",
                      "open_dir": "UP"}, PLAN)
    assert r["status"] == "PROVISIONAL" and r["day_type"] == "Trend_Normal", r
    assert r.get("provisional_from_open") is True and r.get("prov_dir") == "UP", r


def test_p0_2_open_type_maps_to_different_provisionals():
    # ANTI-TAUTOLOGY: the provisional is DRIVEN by opening_type, not a constant.
    with flag("S1_COMMITTED_PROVISIONAL_V1"):
        rr = classify({"n_bars": 6, "opening_type": "OPEN_REJECTION_REVERSE", "open_dir": "UP"}, PLAN)
        ai = classify({"n_bars": 6, "opening_type": "OPEN_AUCTION_IN"}, PLAN)
        dr = classify({"n_bars": 6, "opening_type": "OPEN_DRIVE", "open_location": "out_value_in_range",
                       "open_dir": "DOWN"}, PLAN)
    assert rr["day_type"] == "Neutral_Center", rr
    assert ai["day_type"] == "Normal", ai
    assert dr["day_type"] == "Normal_Variation", dr           # drive but in-range → Variation, not Trend
    assert len({rr["day_type"], ai["day_type"], dr["day_type"]}) == 3   # genuinely different


def test_p0_2_no_bare_forming_at_30min_even_unknown_open():
    # ACCEPT criterion: 0% bare-FORMING at 30 min — even an unresolved open commits (Normal-leaning).
    with flag("S1_COMMITTED_PROVISIONAL_V1"):
        r = classify({"n_bars": 6}, PLAN)   # no opening_type at all
    assert r["status"] == "PROVISIONAL" and r["day_type"] != "FORMING", r


def test_p0_2_still_forming_before_30min():
    # provisional only starts at 30 min (6 bars); before that it is still FORMING.
    with flag("S1_COMMITTED_PROVISIONAL_V1"):
        r = classify({"n_bars": 4, "opening_type": "OPEN_DRIVE", "open_location": "out_of_range"}, PLAN)
    assert r["status"] == "FORMING", r


# ══════════════════════════════════════════════════════════════════════════════
# P0-3 · one canonical confidence (S1_CONFIDENCE_V2)
# ══════════════════════════════════════════════════════════════════════════════
def test_p0_3_flag_off_no_confidence_key():
    r = c(sides=1, rib=3.0, one_tf="DOWN", close_pos=0.05)
    assert "confidence" not in r, r


def test_p0_3_flag_on_emits_confidence_in_unit_range():
    with flag("S1_CONFIDENCE_V2"):
        r = c(sides=1, rib=3.0, one_tf="DOWN", close_pos=0.05, cvd_pos=0.1, ext_dn_bars=5)
    assert "confidence" in r and 0.0 <= r["confidence"] <= 1.0, r
    assert r["confidence"] >= 0.8, r      # fully-aligned down-trend ⇒ high conviction


def test_p0_3_confidence_rises_monotonically_through_downtrend():
    # 07-08 shape: a down stair-step accumulating aligned evidence bar by bar.
    seq = [
        dict(sides=1, one_tf="DOWN", close_pos=0.35, cvd_pos=0.45, ext_dn_bars=1, rib=1.5,
             opening_type="OPEN_AUCTION_OUT", dd_second_dist=False),
        dict(sides=1, one_tf="DOWN", close_pos=0.18, cvd_pos=0.28, ext_dn_bars=2, rib=2.0,
             opening_type="OPEN_AUCTION_OUT", dd_second_dist=False),
        dict(sides=1, one_tf="DOWN", close_pos=0.06, cvd_pos=0.10, ext_dn_bars=4, rib=2.8,
             opening_type="OPEN_DRIVE", dd_second_dist=True),
    ]
    with flag("S1_CONFIDENCE_V2"):
        confs = [c(**s)["confidence"] for s in seq]
    assert confs == sorted(confs), confs           # non-decreasing
    assert confs[-1] > confs[0], confs             # and it actually MOVED (not flat)


def test_p0_3_conflicted_day_is_lower_confidence_than_aligned():
    # ANTI-TAUTOLOGY: confidence reflects ALIGNMENT, not a constant. Same type, conflicting evidence.
    with flag("S1_CONFIDENCE_V2"):
        aligned = c(sides=1, one_tf="DOWN", close_pos=0.05, cvd_pos=0.1, ext_dn_bars=5, rib=3.0)
        conflicted = c(sides=1, one_tf="DOWN", close_pos=0.80, cvd_pos=0.9, ext_dn_bars=0, rib=1.3)
    assert conflicted["confidence"] < aligned["confidence"], (conflicted["confidence"], aligned["confidence"])
