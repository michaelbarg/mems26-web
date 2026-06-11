"""G1 regression: extract_g1_entry_context extracts columns from cross_context.

if reverted → RED because extract_g1_entry_context won't exist, or
the litmus test (missing killzone → NULL, not synthesized) will fail
if anyone adds a fallback.
"""

import pytest

from backend.v9.services.trade_context import (
    extract_g1_entry_context,
    extract_trade_display,
)


# Realistic cross_context from TradeManager (list with systems blob)
FULL_CROSS_CONTEXT = [
    {
        "trigger": "DOUBLE_TOP_AA_SHORT",
        "classification": "DOUBLE_TOP_AA_SHORT",
        "confidence": 0.75,
        "systems": {
            "day_type_machine": {
                "day_type": "TREND_UP",
                "state": "TREND_UP",
                "probability": 0.82,
            },
            "five_min_system": {
                "mode": "DAY_TYPE_MODE",
                "last_classification": "DOUBLE_TOP_AA_SHORT",
            },
            "woodies_system": {
                "trend_state": "GREEN",
                "active_patterns": [
                    {"pattern_id": "ZLR_LONG", "confidence": 0.9, "direction": "LONG"}
                ],
                "classification": "TACTICAL",
            },
            "killzone_system": {
                "zone": "NY_OPEN",
                "state": "ACTIVE",
                "edge_class": "high",
            },
            "footprint_system": {
                "last_classification": "BUYERS",
            },
            "tpo_system": {
                "day_type": "TREND",
            },
        },
    }
]


class TestExtractG1:
    """G1: extract_g1_entry_context returns correct values from cross_context."""

    def test_full_context_extracts_all(self):
        """All 3 fields populated from a full cross_context snapshot."""
        g1 = extract_g1_entry_context(FULL_CROSS_CONTEXT)
        assert g1["day_type_at_entry"] == "TREND_UP"
        assert g1["pattern_id_at_entry"] == "ZLR_LONG"
        assert g1["session_at_entry"] == "NY_OPEN"

    def test_matches_extract_trade_display(self):
        """G1 day_type matches what extract_trade_display returns."""

        class FakeTrade:
            quality = {}
            cross_context = FULL_CROSS_CONTEXT
            firing_system = 2
            direction = "SHORT"
            pnl_usd = None
            pnl_r = None
            outcome = None
            exit_reason = None
            state = "OPEN"
            stop = 7400.0
            t1 = 7300.0
            t2 = 7250.0
            t3 = None
            t1_hit_ts = None
            t2_hit_ts = None
            t3_hit_ts = None
            exit_price = None
            entry_price = 7350.0

        display = extract_trade_display(FakeTrade())
        g1 = extract_g1_entry_context(FULL_CROSS_CONTEXT)
        assert g1["day_type_at_entry"] == display["day_type"]

    def test_litmus_missing_killzone_is_null(self):
        """LITMUS: without killzone in snapshot → session_at_entry is NULL.

        If anyone adds a fallback/synthesis, this test MUST go RED.
        """
        ctx_no_killzone = [
            {
                "trigger": "ZLR_LONG",
                "systems": {
                    "day_type_machine": {"day_type": "NORMAL"},
                    "woodies_system": {"trend_state": "GREEN"},
                    # NO killzone_system key
                },
            }
        ]
        g1 = extract_g1_entry_context(ctx_no_killzone)
        assert g1["session_at_entry"] is None, (
            "Missing killzone MUST be NULL, not synthesized"
        )

    def test_litmus_missing_day_type_is_null(self):
        """Without day_type_machine → day_type_at_entry is NULL."""
        ctx_no_dt = [
            {
                "systems": {
                    "woodies_system": {"classification": "TACTICAL"},
                }
            }
        ]
        g1 = extract_g1_entry_context(ctx_no_dt)
        assert g1["day_type_at_entry"] is None

    def test_unknown_day_type_is_null(self):
        """day_type='UNKNOWN' → treated as NULL (no useful info)."""
        ctx_unknown = [
            {
                "systems": {
                    "day_type_machine": {"day_type": "UNKNOWN"},
                }
            }
        ]
        g1 = extract_g1_entry_context(ctx_unknown)
        assert g1["day_type_at_entry"] is None

    def test_empty_context_all_null(self):
        """Empty cross_context → all 3 fields NULL."""
        g1 = extract_g1_entry_context({})
        assert g1["day_type_at_entry"] is None
        assert g1["pattern_id_at_entry"] is None
        assert g1["session_at_entry"] is None

    def test_s2_pattern_id_not_from_woodies(self):
        """Bug fix (id 43): resolve_pattern_id prefers setup.classification.

        RED-on-revert: if resolve_pattern_id is removed/broken, this fails
        because the g1 fallback returns VEGAS (from woodies snapshot).
        """
        from backend.v9.gateway.trading_gateway import resolve_pattern_id

        # S2 fires REACTIVE_LONG, but woodies snapshot has VEGAS active
        setup = {"classification": "REACTIVE_LONG", "metadata": {"pattern": "REACTIVE_LONG"}}
        g1 = {"pattern_id_at_entry": "VEGAS"}  # what extract_g1_entry_context returns

        result = resolve_pattern_id(setup, g1)
        assert result == "REACTIVE_LONG", (
            f"Expected REACTIVE_LONG, got {result} — "
            "resolve_pattern_id must prefer setup.classification over g1 woodies fallback"
        )

    def test_s2_pattern_id_fallback_when_no_classification(self):
        """Without classification, resolve_pattern_id falls back to g1."""
        from backend.v9.gateway.trading_gateway import resolve_pattern_id

        setup = {}  # no classification, no metadata
        g1 = {"pattern_id_at_entry": "ZLR_LONG"}
        assert resolve_pattern_id(setup, g1) == "ZLR_LONG"

    def test_s4_pattern_id_uses_own_classification(self):
        """S4 setup has classification=HFE → resolve_pattern_id returns HFE."""
        from backend.v9.gateway.trading_gateway import resolve_pattern_id

        setup = {"classification": "HFE"}
        g1 = {"pattern_id_at_entry": "ZLR"}  # stale woodies state
        assert resolve_pattern_id(setup, g1) == "HFE"

    def test_gateway_flat_dict_format(self):
        """Gateway registry format (flat dict, not list) also works."""
        ctx_flat = {
            "day_type_machine": {"day_type": "NORMAL"},
            "killzone_system": {"zone": "LONDON"},
            "woodies_system": {
                "active_patterns": [{"pattern_id": "HFE_SHORT"}]
            },
        }
        g1 = extract_g1_entry_context(ctx_flat)
        assert g1["day_type_at_entry"] == "NORMAL"
        assert g1["pattern_id_at_entry"] == "HFE_SHORT"
        assert g1["session_at_entry"] == "LONDON"
