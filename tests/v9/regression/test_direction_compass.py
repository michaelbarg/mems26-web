"""F1 · DIRECTION_COMPASS_V1 — the fused direction compass (Michael 2026-08-20).

Evidence: `docs/reports/MAX_DAYS_2026-08-20.md` §3 — the direction family is the
most expensive recurring mistake of the live era, ‎+$576.25 over 32 sessions
(OPENING_DRIVE without day-direction ‎+$262.50 · Variation shorts against drift
‎+$200.00 · counter-day on trend days ‎+$113.75).

Michael's two binding rulings are asserted here as executable guardrails:
  (a) "מערכת שמפסידה לנו בתבנית אנחנו מתקנים ולא מבטלים" — no pattern is disabled;
      OPENING_DRIVE still fires WITH the compass (test_opening_drive_with_day_allowed).
  (b) "אתה לא מגביל שעות בשום אופן" — no hour/time gating anywhere
      (test_no_hour_gating_anywhere scans the source).

if reverted -> RED because:
  * dropping the leg clamp makes the 2026-08-19 shape (DLL BEARISH + live UP leg
    + rising LSMA on a +26pt up day) read DOWN again → test_yesterdays_shape_*
  * making NEUTRAL block instead of fall through breaks the fail-open contract →
    test_neutral_passes_through / test_flag_off_is_byte_identical
  * removing the stair exemption re-blocks the G2 ladder → test_stair_exempt
"""
import os

import pytest

from backend.v9.services import direction_compass as DC


@pytest.fixture(autouse=True)
def _clean():
    DC.reset_cache()
    yield
    DC.reset_cache()


# ── 1 · flag OFF ⇒ byte-identical (no new behaviour anywhere) ────────────────
def test_flag_off_is_byte_identical(monkeypatch):
    monkeypatch.delenv("DIRECTION_COMPASS_V1", raising=False)
    assert DC.flag_on() is False
    for legacy in ("UP", "DOWN", "NEUTRAL", None):
        assert DC.compass_or(legacy) == legacy, "flag OFF must return the legacy value"
    allow, why = DC.direction_verdict(pattern="OPENING_DRIVE", direction="SHORT")
    assert allow is True and "off" in why


def test_flag_off_gateway_helper_is_identity(monkeypatch):
    monkeypatch.delenv("DIRECTION_COMPASS_V1", raising=False)
    from backend.v9.gateway.trading_gateway import _compass_or
    for legacy in ("UP", "DOWN", "NEUTRAL", None):
        assert _compass_or(legacy) == legacy


def test_flag_off_zero_db_access(monkeypatch):
    """Flag OFF must not even touch the DB — a dead feed can never change a gate."""
    monkeypatch.delenv("DIRECTION_COMPASS_V1", raising=False)

    def _boom(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("compass touched the DB while the flag was OFF")

    monkeypatch.setattr(DC, "current", _boom)
    assert DC.compass_or("UP") == "UP"
    assert DC.direction_verdict(pattern="ZLR", direction="LONG")[0] is True


# ── 2 · yesterday's failure shape: the compass must FLIP, not lag ────────────
def test_yesterdays_shape_dll_bearish_leg_up_rising_lsma_is_up():
    """2026-08-19: the DLL trend read BEARISH while a live UP leg ran and the
    LSMA rose — on a day that closed +26pt UP. The compass must say UP."""
    c = DC.compute_compass(dll_trend="BEARISH", leg_dir="UP", leg_age=5,
                           lsma_slope=0.42)
    assert c["direction"] == "UP", c["reason"]
    assert c["confidence"] > 0.9
    assert c["components"]["leg"] == 1 and c["components"]["lsma"] == 1
    assert c["context"]["dll_trend"] == "BEARISH"   # recorded, never voted


def test_dll_trend_never_votes():
    """dll_trend is the LAGGING source that caused the failure — context only."""
    a = DC.compute_compass(leg_dir="UP", lsma_slope=0.4, dll_trend="BEARISH")
    b = DC.compute_compass(leg_dir="UP", lsma_slope=0.4, dll_trend="BULLISH")
    assert a["score"] == b["score"] and a["direction"] == b["direction"] == "UP"


def test_fresh_leg_clamps_a_stale_opposite_fusion():
    """Leg is the STRONG component: it can never be out-voted into its opposite.
    Worst case the compass goes NEUTRAL (= legacy behaviour), never DOWN.
    Exercised at a LOWERED threshold (DIRECTION_COMPASS_MIN_CONF is env-tunable)
    — that is exactly the configuration where the clamp is load-bearing."""
    c = DC.compute_compass(leg_dir="UP", lsma_slope=-0.5,
                           value_migration="DOWN", cvd_slope=-1,
                           min_confidence=0.15)
    assert c["direction"] == "NEUTRAL", c["reason"]
    assert "opposes fused" in c["reason"]


def test_default_weights_can_never_out_vote_a_live_leg():
    """Structural invariant behind the leg clamp: with the default weights and
    the default threshold, every possible opposing combination still lands
    inside the NEUTRAL band (|score| <= 0.20 < 0.25)."""
    import itertools
    for lsma, mig, cvd in itertools.product((-0.5, 0.0, 0.5, None),
                                            ("DOWN", "FLAT", "UP", None),
                                            (-1, 0, 1, None)):
        c = DC.compute_compass(leg_dir="UP", lsma_slope=lsma,
                               value_migration=mig, cvd_slope=cvd)
        assert c["direction"] != "DOWN", (lsma, mig, cvd, c["reason"])


def test_leg_agreement_is_reported():
    c = DC.compute_compass(leg_dir="DOWN", leg_age=3, lsma_slope=-0.4,
                           value_migration="DOWN", cvd_slope=-1)
    assert c["direction"] == "DOWN" and c["confidence"] == 1.0
    assert "confirmed by live DOWN leg" in c["reason"]


# ── 3 · NEUTRAL / honest-missing ⇒ pass through unchanged ───────────────────
def test_no_components_is_neutral_rule1():
    c = DC.compute_compass()
    assert c["direction"] == "NEUTRAL" and c["confidence"] == 0.0
    assert all(v is None for v in c["components"].values())
    assert "Rule 1" in c["reason"]


def test_missing_component_is_excluded_not_voted_zero():
    """Rule 1: a missing component must not dilute the denominator."""
    c = DC.compute_compass(lsma_slope=0.5)          # lsma only
    assert c["direction"] == "UP" and c["confidence"] == 1.0
    assert c["components"] == {"lsma": 1, "leg": None,
                               "value_migration": None, "cvd": None}


def test_flat_lsma_abstains():
    c = DC.compute_compass(lsma_slope=0.02, value_migration="UP")
    assert c["components"]["lsma"] == 0          # present, abstaining
    assert c["direction"] == "UP"                # migration carries it


def test_neutral_passes_through(monkeypatch):
    monkeypatch.setenv("DIRECTION_COMPASS_V1", "1")
    monkeypatch.setattr(DC, "current", lambda *a, **k: DC.compute_compass())
    assert DC.compass_or("DOWN") == "DOWN"       # legacy value survives
    assert DC.compass_or(None) is None
    allow, why = DC.direction_verdict(pattern="ZLR", direction="SHORT")
    assert allow is True and "NEUTRAL" in why


def test_low_confidence_is_neutral():
    c = DC.compute_compass(lsma_slope=0.4, value_migration="DOWN", cvd_slope=-1)
    # (0.30 − 0.15 − 0.15) / 0.60 = 0.0 → NEUTRAL
    assert c["direction"] == "NEUTRAL"
    assert DC.agrees(c, "LONG") is None


def test_agrees_contract():
    up = DC.compute_compass(lsma_slope=0.5, leg_dir="UP")
    assert DC.agrees(up, "LONG") is True
    assert DC.agrees(up, "SHORT") is False
    assert DC.agrees(None, "LONG") is None


# ── 3b · the structural anchor: no live leg ⇒ advisory only, never a veto ────
def test_no_leg_anchor_is_advisory_only(monkeypatch):
    """Measured calibration (scripts/f1_compass_replay.py, same 0.25 threshold):
    without the anchor 14 blocks cost 6 winners ‎−$356.25 (net ‎+$157.50); with it
    7 blocks cost 2 winners ‎−$68.75 (net ‎+$325.00). Same doctrine as leg_state:
    the leg is the immediate structural read; the slower sources alone are the
    lagging class F1 exists to fix."""
    monkeypatch.setenv("DIRECTION_COMPASS_V1", "1")
    c = DC.compute_compass(lsma_slope=-0.6, value_migration="DOWN", cvd_slope=-1)
    assert c["direction"] == "DOWN" and c["confidence"] == 1.0   # still computed
    assert DC.has_structural_anchor(c) is False
    monkeypatch.setattr(DC, "current", lambda *a, **k: c)
    assert DC.agrees(c, "LONG") is None                          # not actionable
    assert DC.compass_or("UP") == "UP"                           # legacy survives
    assert DC.direction_verdict(pattern="ZLR", direction="LONG")[0] is True


def test_anchor_present_makes_it_actionable(monkeypatch):
    monkeypatch.setenv("DIRECTION_COMPASS_V1", "1")
    c = DC.compute_compass(lsma_slope=-0.6, leg_dir="DOWN",
                           value_migration="DOWN", cvd_slope=-1)
    assert DC.has_structural_anchor(c) is True
    monkeypatch.setattr(DC, "current", lambda *a, **k: c)
    assert DC.compass_or("UP") == "DOWN"
    assert DC.direction_verdict(pattern="ZLR", direction="LONG")[0] is False


def test_has_structural_anchor_edge_cases():
    assert DC.has_structural_anchor(None) is False
    assert DC.has_structural_anchor({}) is False
    assert DC.has_structural_anchor({"components": {"leg": None}}) is False
    assert DC.has_structural_anchor({"components": {"leg": 1}}) is True


# ── 4 · the money rule: counter-day blocked, with-day allowed ───────────────
def _compass(monkeypatch, direction):
    monkeypatch.setenv("DIRECTION_COMPASS_V1", "1")
    if direction == "UP":
        c = DC.compute_compass(leg_dir="UP", lsma_slope=0.5, value_migration="UP")
    elif direction == "DOWN":
        c = DC.compute_compass(leg_dir="DOWN", lsma_slope=-0.5, value_migration="DOWN")
    else:
        c = DC.compute_compass()
    monkeypatch.setattr(DC, "current", lambda *a, **k: c)
    return c


def test_opening_drive_counter_day_blocked(monkeypatch):
    """+$262.50 — OPENING_DRIVE 0/2 live. #564 (07-30) fired SHORT at 09:35 on a
    day that drifted +58.5pt; #575 (07-31) fired LONG on a −$198.75 stop."""
    _compass(monkeypatch, "UP")
    allow, why = DC.direction_verdict(pattern="OPENING_DRIVE", direction="SHORT")
    assert allow is False and "against compass UP" in why


def test_opening_drive_with_day_allowed(monkeypatch):
    """Michael: תבנית מפסידה מתקנים ולא מבטלים — the pattern is NOT disabled."""
    _compass(monkeypatch, "UP")
    allow, why = DC.direction_verdict(pattern="OPENING_DRIVE", direction="LONG")
    assert allow is True and "with-compass UP" in why


def test_opening_drive_neutral_compass_unchanged(monkeypatch):
    """No opinion ⇒ no new blocking: OD keeps firing exactly as today."""
    _compass(monkeypatch, "NEUTRAL")
    assert DC.direction_verdict(pattern="OPENING_DRIVE", direction="SHORT")[0] is True


@pytest.mark.parametrize("pattern", ["ZLR", "REACTIVE_SHORT", "INITIATIVE_SHORT",
                                     "CONFLUENCE_RI_ZLR", "GB100"])
def test_variation_shorts_against_drift_blocked(monkeypatch, pattern):
    """+$200.00 — the Variation-family shorts taken against the session drift.
    Applies to REV patterns too: the rotation exemption is exactly what let the
    −$1,296 SHORT-on-Variation cell through."""
    _compass(monkeypatch, "UP")
    assert DC.direction_verdict(pattern=pattern, direction="SHORT")[0] is False
    assert DC.direction_verdict(pattern=pattern, direction="LONG")[0] is True


def test_counter_day_on_trend_day_blocked(monkeypatch):
    """+$113.75 — SHORT on Trend_Normal / LONG on Trend_DD. The compass replaces
    the unstable `day_type_at_entry` label (mislabelled on 07-15 and 07-31)."""
    _compass(monkeypatch, "DOWN")
    assert DC.direction_verdict(pattern="REACTIVE_LONG", direction="LONG")[0] is False
    assert DC.direction_verdict(pattern="REACTIVE_SHORT", direction="SHORT")[0] is True


def test_stair_exempt(monkeypatch):
    """G2 coherence: a TREND_STEP rides an established staircase and is judged by
    its own structure, not by the day compass."""
    _compass(monkeypatch, "UP")
    allow, why = DC.direction_verdict(pattern="TREND_STEP", direction="SHORT")
    assert allow is True and "structurally exempt" in why
    assert DC.is_stair_pattern("TREND_STEP_SHORT") is True
    assert DC.is_stair_pattern("ZLR") is False
    assert DC.is_stair_pattern(None) is False


def test_with_leg_entry_is_structurally_unblockable(monkeypatch):
    """A live leg can never be traded against: the clamp inside compute_compass
    means the compass is at worst NEUTRAL for a with-leg setup, so the gate can
    never block it. Same doctrine as LEG_RIDE_V1 / RELEASE_LEG_EXEMPT_V1."""
    monkeypatch.setenv("DIRECTION_COMPASS_V1", "1")
    c = DC.compute_compass(leg_dir="UP", lsma_slope=-0.6,
                           value_migration="DOWN", cvd_slope=-1)
    monkeypatch.setattr(DC, "current", lambda *a, **k: c)
    assert DC.direction_verdict(pattern="ZLR", direction="LONG")[0] is True


def test_gate_fails_open_on_error(monkeypatch):
    monkeypatch.setenv("DIRECTION_COMPASS_V1", "1")

    def _boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(DC, "current", _boom)
    assert DC.direction_verdict(pattern="ZLR", direction="SHORT")[0] is True
    assert DC.compass_or("UP") == "UP"


# ── 5 · Michael's standing rulings, asserted on the source ──────────────────
def test_no_hour_gating_anywhere():
    """"אתה לא מגביל שעות בשום אופן" (2026-08-20). The compass must never look at
    the clock — the afternoon is governed by the direction rule alone. Scans the
    parsed AST (not the prose) so a docstring mentioning "hour" cannot mask a
    real time gate, and a real gate cannot hide behind a comment."""
    import ast
    src = open(DC.__file__, encoding="utf-8").read()
    tree = ast.parse(src)
    banned = {"hour", "minute", "now_et", "datetime", "astimezone",
              "ZoneInfo", "market_clock", "utcnow", "today", "weekday"}
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            used.add(node.attr)
        elif isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Import):
            used.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            used.add((node.module or "").split(".")[0])
            used.update(a.name for a in node.names)
    hit = used & banned
    assert not hit, f"compass must not gate on time — found {sorted(hit)}"


def test_no_pattern_is_disabled(monkeypatch):
    """"מערכת שמפסידה לנו בתבנית אנחנו מתקנים ולא מבטלים" — every losing pattern
    still fires when it agrees with the compass; nothing is switched off."""
    _compass(monkeypatch, "DOWN")
    for pattern in ("OPENING_DRIVE", "ZLR", "GHOST", "BEAR_FLAG_SHORT",
                    "REACTIVE_SHORT", "INITIATIVE_SHORT", "TREND_STEP"):
        assert DC.direction_verdict(pattern=pattern, direction="SHORT")[0] is True, pattern


def test_weights_leg_is_strongest():
    assert DC.W_LEG > DC.W_LSMA > DC.W_VALUE_MIGRATION == DC.W_CVD
    assert round(DC.W_LEG + DC.W_LSMA + DC.W_VALUE_MIGRATION + DC.W_CVD, 6) == 1.0


def test_flag_default_off_in_code():
    """Standing rule: default OFF in code, so a clone/restart keeps it off."""
    env = dict(os.environ)
    try:
        os.environ.pop("DIRECTION_COMPASS_V1", None)
        assert DC.flag_on() is False
    finally:
        os.environ.clear()
        os.environ.update(env)
