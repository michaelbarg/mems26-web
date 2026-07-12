"""P1-6 — value-migration feature (Michael 2026-07-12; Dalton pp.49, 55).

Trend = migrating value; overlapping value = balance. Feature always emitted
(measured); the control-path veto acts only under S1_VALUE_MIGRATION_V1.
Anti-tautological: the SAME stair-stepping geometry is promoted with migrating
value and vetoed with fully-overlapping value — only the value profile differs.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from backend.v9.systems.day_type.value_migration import developing_value, value_migration  # noqa: E402
from backend.v9.systems.day_type.daytype_classifier import classify, load_plan  # noqa: E402

CTRL = "S1_TREND_CONTROL_V1"
FLAG = "S1_VALUE_MIGRATION_V1"


def _bar(px, v=100.0, spread=1.0):
    return {"o": px, "h": px + spread, "l": px - spread, "c": px, "v": v}


# ───────────────────────── unit: developing_value ─────────────────────────

def test_poc_at_heaviest_bucket_and_va_covers_70pct():
    bars = [_bar(5000, v=100)] * 6 + [_bar(5010, v=800)] * 4 + [_bar(5020, v=100)] * 2
    dv = developing_value(bars)
    assert dv["poc"] == 5010.0
    assert dv["val"] <= 5010.0 <= dv["vah"]
    # the heavy bucket alone is 3200/4400 = 72% >= 70% → VA stays tight around it
    assert dv["vah"] - dv["val"] <= 4.0


def test_migration_up_when_dev_va_above_prior():
    bars = [_bar(5030, v=500)] * 8
    vm = value_migration(bars, prior_vah=5010.0, prior_val=4990.0)
    assert vm["value_migration"] == "UP"
    assert vm["va_overlap_pct"] == 0.0


def test_overlap_when_value_rebuilds_inside_prior():
    bars = [_bar(5000, v=500)] * 8
    vm = value_migration(bars, prior_vah=5010.0, prior_val=4990.0)
    assert vm["value_migration"] is None
    assert vm["va_overlap_pct"] is not None and vm["va_overlap_pct"] >= 0.8


def test_honest_none_without_prior_va():
    vm = value_migration([_bar(5000)] * 4, prior_vah=None, prior_val=None)
    assert vm["va_overlap_pct"] is None and vm["value_migration"] is None
    assert vm["dev_poc"] is not None


# ─────────────────── classify: control-path veto (integration) ───────────────────

def _ctrl_feat(**over):
    """A day that qualifies for the P1-5 control path (3 down-steps, rib 2.0)."""
    f = {"returned_through_open": False, "n_bars": 30, "sides": 1, "rib": 2.0,
         "one_tf": None, "cvd_pos": 0.2, "close_pos": 0.1, "vol_ratio": 1.0,
         "dd_second_dist": False, "stair_steps_up": 0, "stair_steps_dn": 3,
         "ib_narrow": False}
    f.update(over)
    return f


def test_control_path_promotes_when_value_migrates(monkeypatch):
    monkeypatch.setenv(CTRL, "1")
    monkeypatch.setenv(FLAG, "1")
    r = classify(_ctrl_feat(value_migration="DOWN", va_overlap_pct=0.1), load_plan())
    assert r["day_type"] == "Trend_Normal" and r.get("trend_control_path"), r
    assert "value migrating DOWN" in r["reason"], r


def test_control_path_vetoed_on_full_overlap(monkeypatch):
    """SAME geometry — only the value profile says balance → no Trend promotion."""
    monkeypatch.setenv(CTRL, "1")
    monkeypatch.setenv(FLAG, "1")
    r = classify(_ctrl_feat(value_migration=None, va_overlap_pct=0.92), load_plan())
    assert r["day_type"] != "Trend_Normal", r        # falls to Normal_Variation


def test_flag_off_ignores_overlap(monkeypatch):
    """Anti-tautological: with P1-6 OFF the fully-overlapping day still promotes
    (byte-identical to pre-P1-6 behavior)."""
    monkeypatch.setenv(CTRL, "1")
    monkeypatch.delenv(FLAG, raising=False)
    r = classify(_ctrl_feat(value_migration=None, va_overlap_pct=0.92), load_plan())
    assert r["day_type"] == "Trend_Normal" and r.get("trend_control_path"), r
