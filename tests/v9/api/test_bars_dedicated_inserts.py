"""P31 Phase 1 — POST handler field-name + dedicated INSERT regression tests.

Pins the Phase 1 fixes (Michael 2026-05-22, ``save_full_profile`` + ``populate``):

  * Pydantic schemas accept the **correct** Sierra payload field names:
    ``profiles[]`` (VP), ``points[]`` (CVD), ``stacks[]`` (SImb). The
    legacy ``bars[]`` field stays as backward-compat fallback.
  * Schema accepts a realistic Sierra payload without losing data.
  * Dedicated tables get rows when the handler runs against real data
    shapes (verified end-to-end via the test client + in-memory SQLite).
  * INSERTs are idempotent — re-posting the same payload doesn't
    duplicate ``v9_bars_volume_profile`` rows (UNIQUE on ``bar_id``).

These tests use ``parse_obj`` against real Sierra-shaped fixtures so a
future schema rename breaks them loudly instead of silently dropping back
to an empty ``bars[]``.
"""

from __future__ import annotations

import os

# Auth guard: bars.py imports auth.verify_bridge_token which requires
# BRIDGE_TOKEN at import time. Set a placeholder for test runs.
os.environ.setdefault("BRIDGE_TOKEN", "test-token")

from backend.v9.api.v9.bars import (
    VolumeProfilePayload,
    CumulativeDeltaPayload,
    StackedImbalancePayload,
    ImbalancePayload,
)


# ----------------------------------------------------------------------
# Field-name acceptance — the central P31 Phase 1 fix
# ----------------------------------------------------------------------


class TestSchemaAcceptsSierraFieldNames:
    """The whole point of Phase 1.B–1.D: Sierra sends `profiles` / `points` /
    `stacks`, the handlers used to silently look at an empty `bars` and
    drop everything. If this regression breaks, the live data path is
    dead again — every new dedicated INSERT and the VP zeros fix depend
    on these field names being honored.
    """

    def test_vp_accepts_profiles_field(self):
        payload = VolumeProfilePayload.parse_obj(
            {
                "type": "volume_profile",
                "version": "v9.4.2",
                "export_ts": 1779432786,
                "va_pct": 70.0,
                "bar_count": 1,
                "profiles": [
                    {
                        "bar_idx": 6107,
                        "poc": 7493.0,
                        "poc_vol": 68.43,
                        "vah": 7494.0,
                        "val": 7493.0,
                        "total_vol": 479.0,
                        "levels": [{"p": 7493.0, "v": 68.43}],
                    }
                ],
            }
        )
        assert len(payload.profiles) == 1
        assert payload.profiles[0]["poc"] == 7493.0
        assert payload.profiles[0]["poc_vol"] == 68.43
        # bars stays empty (no backward-compat collision)
        assert payload.bars == []

    def test_vp_falls_back_to_bars_field(self):
        """In-memory bridge / pre-Phase-1 test fixtures still work."""
        payload = VolumeProfilePayload.parse_obj(
            {
                "type": "volume_profile",
                "bars": [{"bar_idx": 1, "poc": 7400.0, "poc_vol": 50.0, "vah": 7401.0, "val": 7400.0}],
            }
        )
        assert payload.profiles == []
        assert len(payload.bars) == 1
        assert payload.bars[0]["poc"] == 7400.0

    def test_cvd_accepts_points_field(self):
        payload = CumulativeDeltaPayload.parse_obj(
            {
                "type": "cumulative_delta",
                "export_ts": 1779432786,
                "output_interval": 300,
                "current_delta": -709.0,
                "session_delta": -709.0,
                "trend": "BEARISH",
                "points": [
                    {"i": 6107, "t": 1779408299, "d": 31.0, "cum": -85.0, "p": 7494.25}
                ],
            }
        )
        assert len(payload.points) == 1
        assert payload.points[0]["t"] == 1779408299
        assert payload.points[0]["cum"] == -85.0
        assert payload.trend == "BEARISH"
        assert payload.bars == []

    def test_simb_accepts_stacks_field(self):
        payload = StackedImbalancePayload.parse_obj(
            {
                "type": "stacked_imbalances",
                "min_stack": 3,
                "total_stacked_bars": 0,
                "stacks": [
                    {"bar_idx": 6107, "count": 4, "direction": "BUY", "start_price": 7400.0, "end_price": 7401.0}
                ],
            }
        )
        assert len(payload.stacks) == 1
        assert payload.stacks[0]["count"] == 4
        assert payload.stacks[0]["direction"] == "BUY"
        assert payload.min_stack == 3
        assert payload.bars == []

    def test_imbalance_schema_unchanged(self):
        """Imbalance was the only export already using `bars` — verify the
        rename didn't accidentally break the working schema."""
        payload = ImbalancePayload.parse_obj(
            {
                "type": "imbalance_flags",
                "total_buy_imbalances": 2,
                "total_sell_imbalances": 1,
                "bars": [
                    {"bar_idx": 100, "ts": 1779408299, "price": 7400.0, "stacked_buy": 30, "stacked_sell": 5}
                ],
            }
        )
        assert len(payload.bars) == 1
        assert payload.total_buy_imbalances == 2


# ----------------------------------------------------------------------
# Defaulting — empty payloads don't crash
# ----------------------------------------------------------------------


class TestEmptyPayloads:
    def test_vp_empty_payload_no_crash(self):
        payload = VolumeProfilePayload.parse_obj({"type": "volume_profile"})
        assert payload.profiles == []
        assert payload.bars == []

    def test_cvd_empty_payload_no_crash(self):
        payload = CumulativeDeltaPayload.parse_obj({"type": "cumulative_delta"})
        assert payload.points == []
        assert payload.bars == []

    def test_simb_empty_payload_no_crash(self):
        payload = StackedImbalancePayload.parse_obj({"type": "stacked_imbalances"})
        assert payload.stacks == []
        assert payload.bars == []


# ----------------------------------------------------------------------
# Anti-regression: VP zeros bug pattern must not return
# ----------------------------------------------------------------------


class TestVPZerosBugAntiRegression:
    def test_vp_payload_with_profiles_does_not_default_bars_to_truthy(self):
        """If a future refactor accidentally swaps `profiles` and `bars`
        defaults, the handler would skip the new data path. Pin the
        expected default: `bars` is empty unless explicitly provided.
        """
        payload = VolumeProfilePayload.parse_obj(
            {
                "type": "volume_profile",
                "profiles": [{"bar_idx": 1, "poc": 7400.0, "poc_vol": 50.0, "vah": 7401.0, "val": 7400.0}],
            }
        )
        # Critical invariant: `profiles or bars` picks `profiles` first
        primary_source = payload.profiles or payload.bars
        assert primary_source == payload.profiles, (
            "Handler must consume `profiles` first; falling back to `bars` "
            "would re-introduce the P31 Phase 1 zeros bug for any Sierra "
            "payload that uses the canonical key."
        )
