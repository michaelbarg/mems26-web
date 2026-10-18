# -*- coding: utf-8 -*-
"""T-598 / BRIEF §2.3 variant 1 — stop → break-even once the MFE since the fill reaches R × the initial risk.

The rule is a pure function (be_after_mfe.py); its only caller is the harness mirror BE_AFTER_MFE_R_V1 in
scripts/fwd_harness.py (default 0 ⇒ byte-identical replay — the T-567c / T-566 precedent for a measured exit
rule). No live path imports the module: the live protective BE stays "after T1" until a ruling."""
import os
import re

from backend.v9.services.trade_manager.be_after_mfe import be_stop_after_mfe, mfe_pts

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _src(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as f:
        return f.read()


# ── the pure rule ──────────────────────────────────────────────────────────────────────────────────────────────
def test_flag_off_r_zero_never_moves():
    assert be_stop_after_mfe("LONG", 100.0, 96.0, 96.0, [110.0], [99.0], 0) is None
    assert be_stop_after_mfe("LONG", 100.0, 96.0, 96.0, [110.0], [99.0], None) is None
    assert be_stop_after_mfe("LONG", 100.0, 96.0, 96.0, [110.0], [99.0], "") is None


def test_long_moves_to_fill_exactly_at_one_r_not_before():
    # fill 100, initial stop 96 ⇒ risk 4 ⇒ +1R at 104
    assert be_stop_after_mfe("LONG", 100.0, 96.0, 96.0, [101.0, 103.75], [99.0, 100.0], 1.0) is None
    assert be_stop_after_mfe("LONG", 100.0, 96.0, 96.0, [101.0, 104.0], [99.0, 100.0], 1.0) == 100.0


def test_short_is_symmetric():
    # fill 7762.5, initial stop 7770.25 ⇒ risk 7.75 ⇒ +1R at 7754.75 (the 24.09 DOUBLE_TOP of the smoke run)
    assert be_stop_after_mfe("SHORT", 7762.5, 7770.25, 7770.25, [7763.0], [7755.0], 1.0) is None
    assert be_stop_after_mfe("SHORT", 7762.5, 7770.25, 7770.25, [7763.0, 7760.0], [7755.0, 7754.75], 1.0) == 7762.5


def test_never_widens_an_already_tighter_stop():
    assert be_stop_after_mfe("LONG", 100.0, 101.0, 96.0, [110.0], [99.0], 1.0) is None     # stop already past BE
    assert be_stop_after_mfe("SHORT", 100.0, 99.0, 104.0, [101.0], [90.0], 1.0) is None


def test_r_scales_with_the_initial_risk_not_the_current_stop():
    # current stop tightened to 98 by something else: the R is still |fill − initial stop| = 4
    assert be_stop_after_mfe("LONG", 100.0, 98.0, 96.0, [103.0], [99.0], 1.0) is None
    assert be_stop_after_mfe("LONG", 100.0, 98.0, 96.0, [104.0], [99.0], 1.0) == 100.0


def test_zero_distance_initial_stop_counts_as_one_tick():
    assert be_stop_after_mfe("LONG", 100.0, 100.0, 100.0, [100.25], [100.0], 1.0) is None   # stop_now == fill ⇒ no tighten
    assert be_stop_after_mfe("LONG", 100.0, 99.0, 100.0, [100.25], [100.0], 1.0) == 100.0


def test_mfe_uses_the_fill_bar_through_the_current_bar():
    assert mfe_pts("LONG", 100.0, [100.5, 102.0, 101.0], [99.0, 100.0, 100.5]) == 2.0
    assert mfe_pts("SHORT", 100.0, [100.5, 102.0, 101.0], [99.0, 100.0, 97.5]) == 2.5


# ── the harness mirror: default off, wired only under the flag, reports that it ran ───────────────────────────
def test_harness_reads_the_flag_with_a_zero_default():
    s = _src("scripts/fwd_harness.py")
    assert re.search(r'_BE_MFE_R = float\(os\.getenv\("BE_AFTER_MFE_R_V1", "0"\) or 0\)', s)


def test_harness_calls_the_rule_only_under_the_flag_pre_t1():
    s = _src("scripts/fwd_harness.py")
    i = s.index('if _BE_MFE_R > 0 and tr.get("filled") and not tr["be_moved"]:')
    block = s[i:i + 900]
    assert "be_stop_after_mfe(d, e, tr[\"stop\"], tr[\"stop_initial\"]" in block
    assert 'tr["stop"] = float(_ns); tr["be_moved"] = True' in block
    # the rule runs at the bar's close, AFTER the stop/target settlement of that bar (effective from the next bar)
    assert s.index("stop_hit = (lo <= stop)") < i < s.index("if _SE_TIGHTEN and tr.get(\"filled\")")


def test_harness_output_carries_the_proof_the_mechanism_ran():
    s = _src("scripts/fwd_harness.py")
    assert '"be_after_mfe": dict(_BE_MFE_STATS, r=_BE_MFE_R)' in s


def test_no_live_module_imports_the_rule():
    """The live counterpart is not wired: a ruling + a flag of its own come first."""
    for root, _dirs, files in os.walk(os.path.join(REPO, "backend", "v9")):
        for fn in files:
            if not fn.endswith(".py") or fn == "be_after_mfe.py" or "/tests" in root.replace("\\", "/"):
                continue
            with open(os.path.join(root, fn), encoding="utf-8", errors="replace") as f:
                assert "be_after_mfe" not in f.read(), os.path.join(root, fn)
