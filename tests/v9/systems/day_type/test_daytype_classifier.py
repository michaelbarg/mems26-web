"""Tests for daytype_classifier — the locked S1 state machine (Michael 2026-06-20):
priority-0 INVALIDATED overlay, FORMING before IB lock (60 min), provisional states after
the lock, EOD-resolution (no day ends FORMING), tightened Nontrend (rib<=1.15), and all 7
types reachable. Anti-tautological: the *_not_* cases prove the gates actually gate."""
from backend.v9.systems.day_type.daytype_classifier import classify, load_plan

PLAN = load_plan()
LOCKED = 30   # n_bars well past the 12-bar IB lock


def c(**kw):
    """Classify mid-session (after IB lock, not EOD)."""
    kw.setdefault("n_bars", LOCKED)
    return classify(kw, PLAN)


def ce(**kw):
    """Classify at EOD (forces a terminal type)."""
    kw.setdefault("n_bars", 78)
    return classify(kw, PLAN, is_eod=True)


# ── priority 0: INVALIDATED overlay ──────────────────────────────────────────
def test_returned_through_open_is_invalidated_overlay_and_blocks_trend():
    # Trend-shaped inputs, but the open was retraced → `invalidated` overlay True, NOT Trend_Normal,
    # and NOT a terminal "INVALIDATED" type — the day re-forms (Expanded Typical here).
    r = c(returned_through_open=True, sides=1, rib=3.0, one_tf="UP", cvd_pos=0.9, close_pos=0.95)
    assert r["invalidated"] is True and r["opening_invalidated"] is True, r
    assert r["day_type"] != "Trend_Normal", r
    assert r["status"] != "INVALIDATED" and r["day_type"] != "INVALIDATED", r


# ── priority 1: FORMING before IB lock (60 min / 12 bars) ────────────────────
def test_forming_before_ib_lock_then_not_forming():
    assert classify({"n_bars": 10, "sides": 1, "rib": 3.0}, PLAN)["status"] == "FORMING"   # < 12
    assert classify({"n_bars": 12, "sides": 1, "rib": 1.6}, PLAN)["status"] != "FORMING"   # locked


def test_never_forming_after_ib_lock_and_eod_commits():
    # After the IB lock the status is PROVISIONAL or CLASSIFIED — never FORMING; at EOD it COMMITS.
    cases = [
        dict(sides=0, rib=1.6, vol_ratio=1.0, ib_width=20.0),   # 0-sided gap (rib 1.3-1.5+)
        dict(sides=1, rib=1.0),                                  # 1-sided, small
        dict(sides=2, rib=1.2, close_pos=0.75),                 # 2-sided, close between center/extreme
    ]
    for kw in cases:
        mid = classify({**kw, "n_bars": 30}, PLAN)
        assert mid["status"] in ("CLASSIFIED", "PROVISIONAL") and mid["day_type"] != "FORMING", (kw, mid)
        eod = classify({**kw, "n_bars": 78}, PLAN, is_eod=True)
        assert eod["status"] == "CLASSIFIED" and eod["day_type"] != "FORMING", (kw, eod)


# ── priority 2: Nontrend — tightened to truly-compressed (rib<=1.15) ──────────
def test_nontrend_low_vol_and_compressed():
    r = c(sides=0, vol_ratio=0.3, rib=1.05)
    assert r["day_type"] == "Nontrend" and r["direction"] == "none", r


def test_nontrend_requires_compressed_not_just_low_vol():
    # Michael 2026-06-20: rib 1.49 is NOT truly compressed (overlaps Normal/Neutral) → NOT Nontrend,
    # even with low volume. (rib<=1.5 was the regression.)
    r = c(sides=0, vol_ratio=0.2, rib=1.49)
    assert r["day_type"] != "Nontrend", r


def test_normal_volume_zero_sided_not_nontrend():
    assert c(sides=0, rib=1.10, vol_ratio=1.0, ib_width=20.0)["day_type"] != "Nontrend"


# ── priority 3: Neutral ──────────────────────────────────────────────────────
def test_neutral_extreme():
    assert c(sides=2, close_pos=0.92)["day_type"] == "Neutral_Extreme"


def test_neutral_center():
    r = c(sides=2, close_pos=0.50)
    assert r["day_type"] == "Neutral_Center" and r["direction"] == "fade_both", r


# ── priority 4/5/6: sides==1 family ──────────────────────────────────────────
def test_trend_dd():
    assert c(sides=1, dd_second_dist=True, rib=2.2)["day_type"] == "Trend_DD"


def test_trend_normal_strict_signature():
    # ALL four: open held + one_tf + close opposite extreme + rib>=2.5. (CVD confirms, not a gate.)
    r = c(sides=1, rib=3.0, one_tf="UP", cvd_pos=0.85, close_pos=0.97)
    assert r["day_type"] == "Trend_Normal" and r["direction"] == "with_trend", r


def test_trend_normal_fires_without_cvd_confirm():
    # CVD is a CONFIRM, not a gate: a trend (one_tf + close extreme + rib) fires even when CVD is
    # flat/mid (cvd_confirms=False). This is what lets 06-05 stay Trend despite a CVD that didn't help.
    r = c(sides=1, rib=3.0, one_tf="DOWN", close_pos=0.05, cvd_pos=0.5)
    assert r["day_type"] == "Trend_Normal" and r.get("cvd_confirms") is False, r


def test_big_rib_without_one_timeframe_is_not_trend():
    # 06-17: huge rib closed at the low BUT whipsawed (no one_tf) + returned through open → Variation.
    assert c(sides=1, rib=5.13, one_tf=None, close_pos=0.15, returned_through_open=True)["day_type"] == "Normal_Variation"


def test_normal_variation_catch_all():
    r = c(sides=1, rib=1.6, one_tf=None, cvd_pos=0.5)
    assert r["day_type"] == "Normal_Variation" and r["direction"] == "with_extension", r


# ── priority 7: Normal ───────────────────────────────────────────────────────
def test_normal_contained_not_narrow():
    r = c(sides=0, ib_width=20.0, rib=1.10, vol_ratio=1.0)
    assert r["day_type"] == "Normal" and r["direction"] == "fade_both", r


def test_normal_medium_ib_contained():
    assert c(sides=0, rib=1.0, vol_ratio=1.4, ib_width=46.0)["day_type"] == "Normal"


# ── coverage ─────────────────────────────────────────────────────────────────
def test_all_seven_types_reachable():
    got = set()
    for r in [c(sides=1, rib=3.0, one_tf="UP", cvd_pos=0.85, close_pos=0.97),  # Trend_Normal
              c(sides=1, dd_second_dist=True, rib=2.2),                         # Trend_DD
              c(sides=1, rib=1.6),                                              # Normal_Variation
              c(sides=2, close_pos=0.92),                                       # Neutral_Extreme
              c(sides=2, close_pos=0.50),                                       # Neutral_Center
              c(sides=0, ib_width=20.0, rib=1.10, vol_ratio=1.0),               # Normal
              c(sides=0, vol_ratio=0.3, rib=1.05)]:                             # Nontrend
        got.add(r["day_type"])
    for t in ("Trend_Normal", "Trend_DD", "Normal_Variation", "Neutral_Extreme",
              "Neutral_Center", "Normal", "Nontrend"):
        assert t in got, (t, got)


# ── K6: Trend-elongation path ─────────────────────────────────────────────

def test_elongation_path_off_falls_through_to_nv(monkeypatch):
    """S1_TREND_ELONGATION_V1 OFF → rib≥2.5 + extreme cp stays Normal_Variation."""
    monkeypatch.delenv("S1_TREND_ELONGATION_V1", raising=False)
    r = c(sides=1, rib=2.9, close_pos=0.10)  # extreme cp-low, high rib
    assert r["day_type"] == "Normal_Variation"


def test_elongation_path_on_promotes_to_trend(monkeypatch):
    """S1_TREND_ELONGATION_V1 ON → rib≥2.5 + cp≤0.15 = Trend_Normal (DOWN)."""
    monkeypatch.setenv("S1_TREND_ELONGATION_V1", "1")
    r = c(sides=1, rib=2.9, close_pos=0.10)
    assert r["day_type"] == "Trend_Normal"
    assert "elongation" in r.get("reason", "").lower()


def test_elongation_path_up_direction(monkeypatch):
    """Elongation path UP: rib≥2.5 + cp≥0.85 = Trend_Normal (UP)."""
    monkeypatch.setenv("S1_TREND_ELONGATION_V1", "1")
    r = c(sides=1, rib=3.0, close_pos=0.90)
    assert r["day_type"] == "Trend_Normal"
    assert "elongation" in r.get("reason", "").lower()


def test_elongation_path_needs_extreme_cp(monkeypatch):
    """Elongation: rib≥2.5 but cp=0.50 (not extreme) → stays Normal_Variation."""
    monkeypatch.setenv("S1_TREND_ELONGATION_V1", "1")
    r = c(sides=1, rib=2.9, close_pos=0.50)
    assert r["day_type"] == "Normal_Variation"
