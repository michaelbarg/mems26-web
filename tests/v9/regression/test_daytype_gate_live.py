"""DAYTYPE_GATE_LIVE_V1 — live in-memory day_type source for position gate + auth.

Fixes I-44/I-50: position gate read stale "Normal" from classify_replay cache
while the live engine had already promoted to "Trend_Normal". This blocked CONT
patterns on a trend day (06-30: 0 trades on a Trend_Normal / OPEN_DRIVE day).

Anti-tautological: calls REAL extract_g1_entry_context + daytype_position_gate.decide.
Contract: docs/handoff/CC_HANDOFF_CONTRACT.md
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from backend.v9.services.trade_context import extract_g1_entry_context, _NC_CACHE


@pytest.fixture(autouse=True)
def enable_flags():
    with patch.dict(os.environ, {
        "S1_NEW_CLASSIFIER": "1",
        "DAYTYPE_GATE_LIVE_V1": "1",
        "DAYTYPE_POSITION_GATE": "1",
        "DAYTYPE_PATTERN_AWARE_V1": "1",
    }):
        yield


def _mock_app_state(day_type_value):
    """Create a mock app.state.day_type_machine with the given day_type."""
    dtm = MagicMock()
    dtm.day_type = day_type_value
    app = MagicMock()
    app.state.day_type_machine = dtm
    return app


def _cross_ctx(old_engine_dt="Normal"):
    """Cross-context with old engine reporting the given day_type."""
    return {"systems": {"day_type_machine": {"day_type": old_engine_dt}}}


# ---------------------------------------------------------------------------
# Test 1: 06-30 golden fixture — live Trend_Normal, cross_context stale "Normal"
# if reverted → RED because removing the live read lets stale Normal through
# ---------------------------------------------------------------------------
class TestLiveSourceFix:
    def test_gate_reads_live_trend_normal_not_stale_normal(self):
        """Live engine = Trend_Normal, cross_context = Normal (stale).
        With flag ON: gate sees Trend_Normal → ZLR (CONT) ALLOWED on trend day.
        Without fix: gate sees Normal → ZLR blocked as 'balanced day CONT'."""
        mock_app = _mock_app_state("Trend_Normal")
        with patch("importlib.import_module", return_value=MagicMock(app=mock_app)):
            with patch.dict(_NC_CACHE, {}, clear=True):
                result = extract_g1_entry_context(_cross_ctx("Normal"))
        assert result["day_type_at_entry"] == "Trend_Normal", (
            f"Expected Trend_Normal from live, got {result['day_type_at_entry']}"
        )

    def test_zlr_long_allowed_on_live_trend_normal(self):
        """Full path: live=Trend_Normal → position gate ALLOWS ZLR (CONT)."""
        from backend.v9.systems.daytype_position_gate import decide
        tpo = {"ib_high": 7450, "ib_low": 7400, "poc": 7420,
               "vah": 7440, "val": 7407,
               "session_high": 7480, "session_low": 7405}
        allow, reason = decide(
            pattern="ZLR", direction="LONG", day_type="Trend_Normal",
            entry_price=7470.0, tpo_ctx=tpo,
        )
        assert allow is True, f"ZLR LONG should be allowed on Trend_Normal: {reason}"

    def test_initiative_long_allowed_on_live_trend_normal(self):
        """Full path: live=Trend_Normal → position gate ALLOWS INITIATIVE_LONG (CONT)."""
        from backend.v9.systems.daytype_position_gate import decide
        tpo = {"ib_high": 7450, "ib_low": 7400, "poc": 7420,
               "vah": 7440, "val": 7407,
               "session_high": 7480, "session_low": 7405}
        allow, reason = decide(
            pattern="INITIATIVE_LONG", direction="LONG", day_type="Trend_Normal",
            entry_price=7470.0, tpo_ctx=tpo,
        )
        assert allow is True, f"INIT_LONG should be allowed on Trend_Normal: {reason}"


# ---------------------------------------------------------------------------
# Test 2: Source equality — live attribute matches what gate receives
# if reverted → RED because the stale classify_replay != live attribute
# ---------------------------------------------------------------------------
class TestSourceEquality:
    def test_live_source_matches_app_state(self):
        """extract_g1_entry_context returns the same value as app.state.day_type_machine.day_type."""
        for live_dt in ("Trend_Normal", "Trend_DD", "Variation", "Normal", "Neutral_Center"):
            mock_app = _mock_app_state(live_dt)
            with patch("importlib.import_module", return_value=MagicMock(app=mock_app)):
                with patch.dict(_NC_CACHE, {}, clear=True):
                    result = extract_g1_entry_context(_cross_ctx("Normal"))
            expected = {"Normal_Variation": "Variation"}.get(live_dt, live_dt)
            assert result["day_type_at_entry"] == expected, (
                f"Live={live_dt}, expected gate to see {expected}, got {result['day_type_at_entry']}"
            )


# ---------------------------------------------------------------------------
# Test 3: No Stage-1 regression — balanced day still blocks CONT
# if reverted → RED because balanced-day safety must hold
# ---------------------------------------------------------------------------
class TestBalancedDayStillBlocksCont:
    def test_normal_day_blocks_initiative(self):
        """Live engine = Normal (genuinely balanced) → INITIATIVE still blocked."""
        from backend.v9.systems.daytype_position_gate import decide
        tpo = {"ib_high": 7450, "ib_low": 7400, "poc": 7420,
               "vah": 7440, "val": 7407}
        allow, reason = decide(
            pattern="INITIATIVE_LONG", direction="LONG", day_type="Normal",
            entry_price=7405.0, tpo_ctx=tpo,
        )
        assert allow is False
        assert "continuation" in reason.lower()


# ---------------------------------------------------------------------------
# Test 4: Auth table — Trend_Normal + INITIATIVE_LONG → FULL (not SKIP)
# if reverted → RED because stale UNKNOWN/Normal → Neutral_Center → SKIP
# ---------------------------------------------------------------------------
class TestAuthTableLiveSource:
    def test_initiative_long_trend_normal_full(self):
        """Auth table: INITIATIVE_LONG × Trend_Normal = FULL, 3 contracts (HIGH)."""
        from backend.v9.systems.five_min.auth_table_v1 import get_auth_cell
        verdict, h, m, l = get_auth_cell("INITIATIVE_LONG", "Trend_Normal")
        assert verdict == "FULL", f"Expected FULL, got {verdict}"
        assert h == 3

    def test_initiative_long_neutral_center_skip(self):
        """Auth table: INITIATIVE_LONG × Neutral_Center = SKIP (the stale fallback)."""
        from backend.v9.systems.five_min.auth_table_v1 import get_auth_cell
        verdict, h, m, l = get_auth_cell("INITIATIVE_LONG", "Neutral_Center")
        assert verdict == "SKIP"


# ---------------------------------------------------------------------------
# Test 5: Flag OFF → byte-identical (falls back to classify_replay path)
# if reverted → RED because flag-off backward compat must hold
# ---------------------------------------------------------------------------
class TestFlagOffFallback:
    def test_flag_off_uses_classify_replay(self):
        """Flag OFF: extract_g1_entry_context uses the old classify_replay path."""
        import time
        today_iso = __import__("datetime").datetime.now(
            __import__("zoneinfo").ZoneInfo("America/New_York")
        ).date().isoformat()
        # Pre-seed cache with "Normal" (simulating stale classify_replay)
        _NC_CACHE.update({"date": today_iso, "ts": time.time(), "day_type": "Normal"})

        with patch.dict(os.environ, {"DAYTYPE_GATE_LIVE_V1": "0"}):
            result = extract_g1_entry_context(_cross_ctx("Normal"))
        # Flag off → uses cached classify_replay "Normal" (even if live is different)
        assert result["day_type_at_entry"] == "Normal"

    def test_flag_off_live_attr_not_read(self):
        """Flag OFF: the live importlib path is never called."""
        mock_app = _mock_app_state("Trend_Normal")
        with patch.dict(os.environ, {"DAYTYPE_GATE_LIVE_V1": "0"}):
            import time
            today_iso = __import__("datetime").datetime.now(
                __import__("zoneinfo").ZoneInfo("America/New_York")
            ).date().isoformat()
            _NC_CACHE.update({"date": today_iso, "ts": time.time(), "day_type": "Variation"})
            result = extract_g1_entry_context(_cross_ctx("Normal"))
        # Should get Variation from cache, NOT Trend_Normal from live
        assert result["day_type_at_entry"] == "Variation"


# ---------------------------------------------------------------------------
# Test 6: Live UNKNOWN/FORMING falls through to classify_replay
# if reverted → RED because live UNKNOWN must not short-circuit to None
# ---------------------------------------------------------------------------
class TestLiveUnknownFallthrough:
    def test_live_unknown_falls_to_classify_replay(self):
        """Live = UNKNOWN → skip live path, use classify_replay."""
        import time
        mock_app = _mock_app_state("UNKNOWN")
        today_iso = __import__("datetime").datetime.now(
            __import__("zoneinfo").ZoneInfo("America/New_York")
        ).date().isoformat()
        _NC_CACHE.update({"date": today_iso, "ts": time.time(), "day_type": "Trend_Normal"})
        with patch("importlib.import_module", return_value=MagicMock(app=mock_app)):
            result = extract_g1_entry_context(_cross_ctx("Normal"))
        # Live is UNKNOWN → falls through to classify_replay cache → Trend_Normal
        assert result["day_type_at_entry"] == "Trend_Normal"
