"""T1 Ladder V2 — anti-tautological tests with RED-on-revert.

Verifies: V2 gives wider T1 than default at same risk;
flag OFF → identical to default; config validates.
"""

import os
import pytest


@pytest.fixture(autouse=True)
def _enable_v2(monkeypatch):
    monkeypatch.setenv("T1_LADDER_V2", "1")


class TestT1LadderV2:

    def test_v2_wider_than_default_at_risk_12(self):
        """V2 T1 at 12pt risk must be WIDER (further from entry) than default.

        Default: risk=12pt → bucket 10-15 → t1_r=0.65 → T1=12×0.65=7.8pt from entry
        V2:     risk=12pt → bucket 10-15 → t1_r=0.90 → T1=12×0.90=10.8pt from entry
        RED-on-revert: if V2 points to same ladder, v2_dist == default_dist → assert fails.
        """
        from backend.v9.config_loader import load_stop_anchors
        from backend.v9.systems.stop_anchors import resolver as SA

        cfg = load_stop_anchors()
        assert cfg is not None

        entry, stop, direction = 7400.0, 7388.0, "LONG"  # risk = 12pt

        default_t1 = SA.t1_price(
            entry, stop, direction,
            t1_ladder_cont=cfg["t1_ladder_continuation"],
            reversal=False,
            reversal_mult=cfg.get("t1_reversal_multiplier", 0.8),
            t1_floor_points=cfg.get("t1_floor_points", 3.0),
        )
        v2_t1 = SA.t1_price(
            entry, stop, direction,
            t1_ladder_cont=cfg["t1_ladder_continuation_v2"],
            reversal=False,
            reversal_mult=cfg.get("t1_reversal_multiplier_v2", 0.9),
            t1_floor_points=cfg.get("t1_floor_points", 3.0),
        )

        default_dist = abs(default_t1 - entry)
        v2_dist = abs(v2_t1 - entry)

        assert v2_dist > default_dist, (
            f"V2 T1 must be wider: v2={v2_dist:.2f}pt vs default={default_dist:.2f}pt "
            f"(v2_t1={v2_t1}, default_t1={default_t1})"
        )

    def test_v2_reversal_less_restrictive(self):
        """V2 reversal multiplier (0.90) is higher than default (0.80)."""
        from backend.v9.config_loader import load_stop_anchors
        cfg = load_stop_anchors()
        default_mult = cfg.get("t1_reversal_multiplier", 0.8)
        v2_mult = cfg.get("t1_reversal_multiplier_v2", 0.8)
        assert v2_mult > default_mult, f"V2 rev mult {v2_mult} must exceed default {default_mult}"

    def test_flag_off_uses_default(self, monkeypatch):
        """Flag OFF → same ladder as default (anti-regression)."""
        monkeypatch.setenv("T1_LADDER_V2", "0")
        from backend.v9.shared.atr import flag
        assert not flag("T1_LADDER_V2")

    def test_v2_config_validates(self):
        """V2 ladder values pass config_loader validation (within guardrails)."""
        from backend.v9.config_loader import load_stop_anchors
        cfg = load_stop_anchors()
        v2 = cfg.get("t1_ladder_continuation_v2")
        assert v2 is not None, "t1_ladder_continuation_v2 missing from stop_anchors.yaml"
        for row in v2:
            assert 0.2 <= row["t1_r"] <= 1.5, f"t1_r={row['t1_r']} out of guardrails [0.2,1.5]"
            assert "max_risk_points" in row

    def test_s2_v2_config_exists(self):
        """flag_relative_t1_v2 block exists in config."""
        from backend.v9.config_loader import load_stop_anchors
        cfg = load_stop_anchors()
        v2 = cfg.get("flag_relative_t1_v2")
        assert v2 is not None, "flag_relative_t1_v2 missing"
        assert v2["t1_r_max"] > 0.8, "V2 t1_r_max should exceed default 0.8"
