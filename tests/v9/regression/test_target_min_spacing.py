# -*- coding: utf-8 -*-
"""TARGET_MIN_SPACING_V1 — Michael 2026-08-21 ~11:30 IL.

Reference case: live #756 (2026-08-20 11:55 ET) — SHORT 7696.75, stop 7700.25,
ladder 7691.50 / 7691.00 / 7690.50. Three exits 0.5pt apart, and the raw log
proves it is ONE real level (TP-1's IB edge 7691.50) plus two prices the
gateway's ladder-dedup invented.
"""
import importlib
import os

import pytest

from backend.v9.systems import target_spacing as T


# ── the real #756 numbers, frozen ─────────────────────────────────────────
T756 = dict(direction="SHORT", entry=7696.75, stop=7700.25,
            t1=7691.50, t2=7691.00, t3=7690.50)
T756_RISK = 3.50
T756_ATR14 = 8.0714285714286      # 14 TR over the bars before the entry ts
# The structural objectives TP-1 clamped away (from the 18:55:05 log line)
T756_STRUCT = [("struct_c1", 7686.25), ("struct_c2", 7682.75),
               ("struct_c3", 7679.00)]
T756_TPO = {"ib_high": 7716.25, "ib_low": 7691.50, "poc": 7705.00,
            "vah": 7710.00, "val": 7699.00}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("TARGET_MIN_SPACING_V1", raising=False)
    T.reset_cfg_cache()
    T.reset_atr_cache()
    yield
    T.reset_cfg_cache()
    T.reset_atr_cache()


def _cands_756():
    return T.build_candidates(entry=T756["entry"], risk=T756_RISK,
                              tpo_ctx=T756_TPO, producer_levels=T756_STRUCT)


def _run_756(**over):
    kw = dict(direction=T756["direction"], entry=T756["entry"],
              t1=T756["t1"], t2=T756["t2"], t3=T756["t3"],
              risk=T756_RISK, atr14=T756_ATR14, candidates=_cands_756())
    kw.update(over)
    return T.enforce_spacing(**kw)


# ── 1 · flag semantics: OFF is byte-identical, "1" is NOT apply ────────────
class TestFlagMode:
    def test_unset_is_off(self):
        assert T.flag_mode() == T.MODE_OFF

    @pytest.mark.parametrize("val", ["0", "", "off", "false", "no", "OFF"])
    def test_off_values(self, monkeypatch, val):
        monkeypatch.setenv("TARGET_MIN_SPACING_V1", val)
        assert T.flag_mode() == T.MODE_OFF

    @pytest.mark.parametrize("val", ["shadow", "SHADOW", "observe", "1",
                                     "true", "yes", "on"])
    def test_onish_values_are_shadow_never_apply(self, monkeypatch, val):
        """A careless `=1` must never be able to move a live order."""
        monkeypatch.setenv("TARGET_MIN_SPACING_V1", val)
        assert T.flag_mode() == T.MODE_SHADOW

    @pytest.mark.parametrize("val", ["apply", "APPLY", " apply "])
    def test_only_literal_apply_applies(self, monkeypatch, val):
        monkeypatch.setenv("TARGET_MIN_SPACING_V1", val)
        assert T.flag_mode() == T.MODE_APPLY


class TestFlagOffIsByteIdentical:
    def test_gateway_returns_the_same_ladder_and_writes_nothing(self):
        from backend.v9.gateway.trading_gateway import TradingGateway
        gw = TradingGateway.__new__(TradingGateway)
        setup = {"metadata": {}}
        out = TradingGateway._target_spacing_shadow(
            gw, setup, "SHORT", T756["entry"], T756["stop"],
            T756["t1"], T756["t2"], T756["t3"], {"tpo_system": T756_TPO})
        assert out == (T756["t1"], T756["t2"], T756["t3"])
        assert "target_spacing_shadow" not in setup["metadata"]

    def test_shadow_mode_also_returns_the_same_ladder(self, monkeypatch):
        """SHADOW must record but never change the orders."""
        monkeypatch.setenv("TARGET_MIN_SPACING_V1", "shadow")
        monkeypatch.setattr(T, "current_atr14", lambda: T756_ATR14)
        from backend.v9.gateway.trading_gateway import TradingGateway
        gw = TradingGateway.__new__(TradingGateway)
        setup = {"metadata": {"spacing_levels": list(T756_STRUCT)}}
        out = TradingGateway._target_spacing_shadow(
            gw, setup, "SHORT", T756["entry"], T756["stop"],
            T756["t1"], T756["t2"], T756["t3"], {"tpo_system": T756_TPO})
        assert out == (T756["t1"], T756["t2"], T756["t3"]), "SHADOW changed the ladder"
        rec = setup["metadata"]["target_spacing_shadow"]
        assert rec["mode"] == "shadow"
        assert rec["changed"] is True
        assert rec["after"]["t1"] == 7691.50
        assert rec["after"]["t2"] is None
        assert rec["after"]["t3"] is None

    def test_apply_mode_does_change_the_ladder(self, monkeypatch):
        monkeypatch.setenv("TARGET_MIN_SPACING_V1", "apply")
        monkeypatch.setattr(T, "current_atr14", lambda: T756_ATR14)
        from backend.v9.gateway.trading_gateway import TradingGateway
        gw = TradingGateway.__new__(TradingGateway)
        setup = {"metadata": {"spacing_levels": list(T756_STRUCT)}}
        out = TradingGateway._target_spacing_shadow(
            gw, setup, "SHORT", T756["entry"], T756["stop"],
            T756["t1"], T756["t2"], T756["t3"], {"tpo_system": T756_TPO})
        assert out == (7691.50, 0.0, 0.0)


# ── 2 · #756 itself ───────────────────────────────────────────────────────
class TestCase756:
    def test_min_gap_is_relative_and_atr_driven(self):
        gap, basis = T.min_gap(T756_ATR14, T756_RISK)
        # max(0.25*8.0714, 0.33*3.5) = max(2.018, 1.155)
        assert basis == "k*ATR14"
        assert gap == pytest.approx(2.0179, abs=1e-3)

    def test_all_three_legs_violate(self):
        rec = _run_756()
        gap = rec["min_gap"]
        assert 7691.00 - 7691.50 > -gap   # the 0.5pt steps are far under the gap
        assert rec["changed"] is True

    def test_t1_is_the_anchor_and_never_moves(self):
        rec = _run_756()
        assert rec["after"]["t1"] == 7691.50
        assert rec["branches"][0]["branch"] == "ANCHOR"

    def test_t2_and_t3_are_dropped_not_pushed(self):
        """max_reach forbids re-expanding past what the pipeline already ruled:
        struct_c2=7682.75 is a real level but 14pt out, beyond the 6.25pt reach
        TP-1 left this ladder — so the honest answer is DROP, not PUSH."""
        rec = _run_756()
        by = {b["leg"]: b for b in rec["branches"]}
        assert by["t2"]["branch"] == "DROP"
        assert by["t3"]["branch"] == "DROP"
        assert rec["after"]["t2"] is None
        assert rec["after"]["t3"] is None
        assert rec["max_reach"] == 6.25

    def test_shadow_line_names_the_branch_and_the_numbers(self):
        line = T.format_shadow(_run_756())
        assert "7691.50" in line
        assert "dropped" in line
        assert "min_gap=" in line


# ── 3 · a healthy ladder is untouched ─────────────────────────────────────
class TestHealthyLadderUntouched:
    def test_wellspaced_short_ladder_unchanged(self):
        """The pre-clamp #756 ladder: 3.50 / 3.75pt steps — a real ladder."""
        rec = T.enforce_spacing(
            direction="SHORT", entry=7696.75,
            t1=7686.25, t2=7682.75, t3=7679.00,
            risk=T756_RISK, atr14=T756_ATR14, candidates=_cands_756())
        assert rec["changed"] is False
        assert rec["after"] == {"t1": 7686.25, "t2": 7682.75, "t3": 7679.00}
        assert [b["branch"] for b in rec["branches"]] == ["ANCHOR", "KEEP", "KEEP"]

    def test_wellspaced_long_ladder_unchanged(self):
        rec = T.enforce_spacing(
            direction="LONG", entry=7600.0, t1=7604.0, t2=7610.0, t3=7620.0,
            risk=4.0, atr14=7.0, candidates=[])
        assert rec["changed"] is False
        assert rec["after"] == {"t1": 7604.0, "t2": 7610.0, "t3": 7620.0}

    def test_absent_legs_stay_absent(self):
        rec = T.enforce_spacing(
            direction="LONG", entry=7600.0, t1=7604.0, t2=0.0, t3=None,
            risk=4.0, atr14=7.0, candidates=[])
        assert rec["changed"] is False
        assert rec["after"]["t2"] is None and rec["after"]["t3"] is None


# ── 4 · the PUSH branch, and it may only land on a real level ─────────────
class TestPushBranch:
    def test_push_lands_on_a_named_real_level(self):
        """t2 sits 0.5pt past t1, but POC is a real level inside reach."""
        cands = [("POC", 7610.0), ("VAH", 7614.0)]
        rec = T.enforce_spacing(
            direction="LONG", entry=7600.0, t1=7604.0, t2=7604.5, t3=7620.0,
            risk=4.0, atr14=7.0, candidates=cands)
        by = {b["leg"]: b for b in rec["branches"]}
        assert by["t2"]["branch"] == "PUSH"
        assert by["t2"]["price"] == 7610.0
        assert by["t2"]["level"] == "POC"
        assert rec["after"]["t2"] == 7610.0

    def test_no_synthetic_price_ever_leaves_the_rule(self):
        """Every output price must be either an input leg or a candidate.

        This is the rule CLAUDE.md Rule 1 exists for, and the exact thing the
        live ladder-dedup violates by nudging 2 ticks at a time.
        """
        cands = [("POC", 7610.0), ("VAH", 7614.0), ("IBH", 7631.0)]
        allowed = {p for _n, p in cands}
        cases = [
            dict(direction="LONG", entry=7600.0, t1=7604.0, t2=7604.5, t3=7605.0),
            dict(direction="LONG", entry=7600.0, t1=7604.0, t2=7604.25, t3=7632.0),
            dict(direction="SHORT", entry=7600.0, t1=7596.0, t2=7595.75, t3=7595.5),
            dict(direction="LONG", entry=7600.0, t1=7604.0, t2=7603.0, t3=7602.0),
        ]
        for c in cases:
            rec = T.enforce_spacing(risk=4.0, atr14=7.0, candidates=cands, **c)
            ins = {c["t1"], c["t2"], c["t3"]}
            for leg, val in rec["after"].items():
                if val is None:
                    continue
                assert val in allowed or val in ins, (
                    f"{leg}={val} is neither a real candidate nor an input leg "
                    f"— synthetic price invented for {c}")

    def test_push_never_exceeds_the_original_reach(self):
        cands = [("FAR", 7700.0)]
        rec = T.enforce_spacing(
            direction="LONG", entry=7600.0, t1=7604.0, t2=7604.5, t3=7605.0,
            risk=4.0, atr14=7.0, candidates=cands)
        by = {b["leg"]: b for b in rec["branches"]}
        assert by["t2"]["branch"] == "DROP", "reach was extended past the ruled envelope"
        assert rec["max_reach"] == 5.0

    def test_r_multiple_is_an_allowed_landing_level(self):
        cands = T.build_candidates(entry=7600.0, risk=4.0, tpo_ctx=None)
        names = {n for n, _p in cands}
        assert "R2+" in names and "R1.5+" in names
        # 2R above a 7600 entry with 4pt risk = 7608.00, on the tick grid
        assert ("R2+", 7608.0) in cands


# ── 5 · inverted ladders (the archive's other degeneracy) ─────────────────
class TestInvertedLadder:
    def test_leg_closer_than_its_predecessor_is_caught(self):
        """#610-shape: dists 4.5 / 3.75 / 7.5 — t2 sits INSIDE t1."""
        rec = T.enforce_spacing(
            direction="LONG", entry=7600.0, t1=7604.5, t2=7603.75, t3=7607.5,
            risk=3.75, atr14=3.88, candidates=[])
        by = {b["leg"]: b for b in rec["branches"]}
        assert by["t2"]["branch"] == "DROP"
        assert rec["after"]["t1"] == 7604.5
        assert rec["after"]["t3"] == 7607.5, "a valid outer leg must survive"


# ── 6 · dead ATR ──────────────────────────────────────────────────────────
class TestDeadAtrFloor:
    def test_dead_atr_falls_back_to_the_risk_term_and_says_so(self):
        gap, basis = T.min_gap(0.0, 4.0)
        assert gap == pytest.approx(1.32, abs=1e-6)      # 0.33 * 4.0
        assert "sole basis" in basis, "a partial basis must be self-declaring"

    def test_dead_atr_still_catches_756_shaped_clustering(self):
        rec = _run_756(atr14=0.0)
        assert rec["basis"].startswith("m*risk")
        assert rec["changed"] is True                    # 0.5pt < 0.33*3.5=1.155
        assert rec["after"]["t2"] is None

    def test_no_basis_at_all_leaves_the_ladder_untouched(self):
        """No ATR and no risk = no relative yardstick. Rule 1: do nothing,
        rather than inventing a fixed-point gap."""
        rec = T.enforce_spacing(
            direction="LONG", entry=7600.0, t1=7604.0, t2=7604.5, t3=7605.0,
            risk=0.0, atr14=0.0, candidates=[("POC", 7610.0)])
        assert rec["min_gap"] is None
        assert rec["changed"] is False
        assert rec["after"] == {"t1": 7604.0, "t2": 7604.5, "t3": 7605.0}
        assert rec["branches"][0]["branch"] == "SKIP"

    def test_none_atr_behaves_like_dead_atr(self):
        gap, basis = T.min_gap(None, 4.0)
        assert gap == pytest.approx(1.32, abs=1e-6)
        assert "sole basis" in basis


# ── 7 · config is config, not code ────────────────────────────────────────
class TestConfigDriven:
    def test_k_and_m_come_from_targets_yaml(self):
        import yaml
        with open("config/targets.yaml") as f:
            doc = yaml.safe_load(f)
        block = doc["target_spacing"]
        assert block["k_atr"] == 0.25
        assert block["m_risk"] == 0.33
        cfg = T.load_cfg()
        assert cfg["k_atr"] == block["k_atr"]
        assert cfg["m_risk"] == block["m_risk"]

    def test_no_fixed_point_gap_literal_in_the_module(self):
        """Michael's standing principle: relative, never fixed points."""
        import inspect
        src = inspect.getsource(T.min_gap)
        assert "k_atr" in src and "m_risk" in src
        # the only bare number allowed in the gap maths is 0 (the liveness test)
        assert "+ 1.5" not in src and "= 2.0" not in src

    def test_ruled_flags_carries_the_shadow_expectation(self):
        with open("config/RULED_FLAGS.yaml", encoding="utf-8") as f:
            src = f.read()
        assert "TARGET_MIN_SPACING_V1" in src
        i = src.index("TARGET_MIN_SPACING_V1")
        assert 'expected: "shadow"' in src[i:i + 200]


# ── 8 · the guard it sits next to still only drops exact ties ─────────────
def test_degeneracy_guard_alone_would_still_miss_756():
    """Documents the gap this flag closes — if this ever fails, the two guards
    have merged and the flag's premise needs re-reading."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    t1, t2, t3 = TradingGateway._target_degeneracy_guard(
        T756["t1"], T756["t2"], T756["t3"])
    assert (t1, t2, t3) == (7691.50, 7691.00, 7690.50)
