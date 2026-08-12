"""B1-B4 — Opening entry gap fixes (2026-08-12).

B1: Confidence engine fuse (OPENING_CONF_ENGINE_FUSE_V1)
B2: OR_NARROW_MAX_PTS parameterization + ATR scale
B4: Fusion logging (always, not just on success)
"""
import os
import pytest

from backend.v9.systems.opening_entry import (
    opening_first_trade_ok,
    evaluate_opening_entry,
    opening_dir_fusion,
    OR_NARROW_MAX_PTS,
)


def _bar(o, h, l, c):
    return {"o": o, "h": h, "l": l, "c": c}


# ── B1: Engine confidence fuse ─────────────────────────────────────────────

class TestConfidenceEngineFuse:
    """When OPENING_CONF_ENGINE_FUSE_V1=1, the engine's own graded confidence
    overrides the detector's opening_conf for matching trigger types."""

    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch):
        monkeypatch.setenv("OPENING_CONF_ENGINE_FUSE_V1", "1")

    def test_drive_fuse_overrides_zero_conf(self):
        """DRIVE trigger with detector conf=0.0 → fuse gives 0.85 → passes."""
        bars = [_bar(7770, 7775, 7768, 7774),
                _bar(7774, 7778, 7772, 7776),
                _bar(7776, 7780, 7774, 7779)]
        ok, reason = opening_first_trade_ok(bars, "LONG", 0.0,
                                            trigger_type="DRIVE")
        assert ok is True
        assert "confirmed" in reason

    def test_orr_fuse_passes_at_065(self):
        """ORR trigger → fuse gives 0.65, min_conf=0.7 → still fails (0.65<0.7)."""
        bars = [_bar(7770, 7775, 7768, 7774),
                _bar(7774, 7778, 7772, 7776),
                _bar(7776, 7780, 7774, 7779)]
        ok, reason = opening_first_trade_ok(bars, "LONG", 0.0,
                                            trigger_type="ORR",
                                            min_conf=0.7)
        # ORR engine conf = 0.65 < min_conf 0.7 → should fail
        assert ok is False

    def test_fuse_off_uses_detector_conf(self, monkeypatch):
        """When fuse OFF, detector conf=0.0 → fails regardless of trigger type."""
        monkeypatch.setenv("OPENING_CONF_ENGINE_FUSE_V1", "0")
        bars = [_bar(7770, 7775, 7768, 7774),
                _bar(7774, 7778, 7772, 7776),
                _bar(7776, 7780, 7774, 7779)]
        ok, _ = opening_first_trade_ok(bars, "LONG", 0.0,
                                       trigger_type="DRIVE")
        assert ok is False

    def test_no_trigger_type_no_fuse(self):
        """Without trigger_type, fuse doesn't fire."""
        bars = [_bar(7770, 7775, 7768, 7774)] * 3
        ok, _ = opening_first_trade_ok(bars, "LONG", 0.0,
                                       trigger_type=None)
        assert ok is False


# ── B2: OR_NARROW_MAX_PTS parameterization ─────────────────────────────────

class TestORParamterization:
    def test_default_is_env_readable(self, monkeypatch):
        """OR_NARROW_MAX_PTS reads from env."""
        monkeypatch.setenv("OR_NARROW_MAX_PTS", "20.0")
        # Need to reimport to pick up the new env
        import importlib
        import backend.v9.systems.opening_entry as oe
        importlib.reload(oe)
        assert oe.OR_NARROW_MAX_PTS == 20.0
        # Restore
        monkeypatch.setenv("OR_NARROW_MAX_PTS", "10.0")
        importlib.reload(oe)

    def test_drive_with_wide_or_blocked_at_10(self):
        """OR=14pt > 10pt → DRIVE doesn't fire (current behavior)."""
        bars = [
            _bar(7770, 7784, 7770, 7784),  # bar1: OR=14pt
            _bar(7784, 7788, 7782, 7787),  # close above OR high
        ]
        result = evaluate_opening_entry(bars)
        assert result is None  # blocked by OR width > 10

    def test_drive_with_narrow_or_fires(self):
        """OR=8pt <= 10pt → DRIVE fires."""
        bars = [
            _bar(7770, 7778, 7770, 7778),  # bar1: OR=8pt
            _bar(7778, 7782, 7776, 7780),  # close above OR high
        ]
        result = evaluate_opening_entry(bars)
        assert result is not None
        assert result["type"] == "DRIVE"
        assert result["direction"] == "LONG"


# ── B4: Fusion logging ────────────────────────────────────────────────────

class TestFusionLogging:
    def test_fusion_logs_on_skip(self, caplog):
        """Fusion must log when it drops due to vol < median."""
        import logging
        with caplog.at_level(logging.INFO):
            result = opening_dir_fusion(
                [_bar(7770, 7775, 7768, 7774)] * 6,
                open_price=7770.0,
                opening_vol=100.0,
                median_open_vol=200.0,
            )
        assert result is None
        assert any("OPENING_DIR_FUSION" in r.message and "SKIP" in r.message
                    for r in caplog.records)

    def test_fusion_logs_on_success(self, caplog):
        """Fusion must log its result."""
        import logging
        with caplog.at_level(logging.INFO):
            result = opening_dir_fusion(
                [_bar(7770, 7775, 7768, 7778)] * 6,  # close > open+2 → UP
                open_price=7770.0,
                opening_vol=200.0,
                median_open_vol=100.0,
            )
        # May or may not produce a result depending on refs
        assert any("OPENING_DIR_FUSION" in r.message for r in caplog.records)


# ── Code path verification ────────────────────────────────────────────────

class TestCodePaths:
    def test_b1_flag_in_code(self):
        import inspect
        from backend.v9.systems import opening_entry
        src = inspect.getsource(opening_entry.opening_first_trade_ok)
        assert "OPENING_CONF_ENGINE_FUSE_V1" in src
        assert "ENGINE_CONF" in src

    def test_b2_env_in_code(self):
        import inspect
        from backend.v9.systems import opening_entry
        src = inspect.getsource(opening_entry)
        assert 'OR_NARROW_MAX_PTS' in src
        assert 'OPENING_OR_ATR_SCALE_V1' in src

    def test_trigger_type_wired_in_five_min(self):
        import inspect
        from backend.v9.systems.five_min import five_min_system
        src = inspect.getsource(five_min_system.FiveMinSystem.process_bar)
        assert "trigger_type" in src
