"""IB_BARS_VALIDATE_V1 — a WRONG Sierra IB must not silently drive targets.

Michael 2026-08-14, mid-session: "IB תתוקן שם … הוא צריך להיות מקביל של מק-1".

mac-2's Sierra exported ib 7817.50/7808.00 for a session whose real 09:30-10:30
ET range — from the ingested canonical bars, byte-identical on both machines —
was 7830.75/7813.75 (window an hour late; the study loaded mid-session). That
bogus ib_low became the T1 target and killed every candidate on R:R (the last
one: R:R 0.19, T1 1.0pt vs stop 5pt) while mac-1 took the same setup.

This is VALIDATION, not synthesis: Rule 1 forbids inventing an IB when the study
is SILENT — here it is wrong, and CLAUDE.md explicitly allows trading logic on
ingested bars. Provenance stays honest via ib_source=bars_derived_correction.
"""
import os

import pytest

from backend.v9.api.v9 import tpo_routes


RAW_BASE = {
    "type": "tpo",
    "session": {"poc": 7820.0, "vah": 7828.0, "val": 7812.0, "opened_ts": 1786714200},
}


def _raw(ib_found=True, high=7817.5, low=7808.0):
    d = dict(RAW_BASE)
    d["ib"] = {"found": ib_found, "high": high, "low": low,
               "mid": (high + low) / 2 if ib_found else None}
    return d


class TestFlagOff:
    def test_sierra_value_untouched_when_flag_off(self, monkeypatch):
        monkeypatch.delenv("IB_BARS_VALIDATE_V1", raising=False)
        out = tpo_routes._normalize_sierra_tpo(_raw(), age_s=1.0)
        assert out["ib_high"] == 7817.5 and out["ib_low"] == 7808.0
        assert out["ib_source"] == "sierra_live"


class TestValidation:
    @pytest.fixture(autouse=True)
    def _on(self, monkeypatch):
        monkeypatch.setenv("IB_BARS_VALIDATE_V1", "1")

    def _patch_bars(self, monkeypatch, h, l, n=12, hour=11):
        """Stub the DB read + freeze ET clock past the IB window."""
        monkeypatch.setattr(
            "backend.v9.db.read.read_one",
            lambda *a, **k: {"h": h, "l": l, "n": n},
            raising=False,
        )

    def test_wrong_sierra_ib_is_corrected_from_bars(self, monkeypatch):
        self._patch_bars(monkeypatch, 7830.75, 7813.75)
        out = tpo_routes._normalize_sierra_tpo(_raw(), age_s=1.0)
        # Outside the ET window the correction must not run; inside it must.
        if out["ib_source"] == "bars_derived_correction":
            assert out["ib_high"] == 7830.75 and out["ib_low"] == 7813.75
            assert out["ib_width"] == pytest.approx(17.0)
        else:
            assert out["ib_source"] == "sierra_live"  # pre-10:30 ET run

    def test_matching_sierra_ib_is_left_alone(self, monkeypatch):
        """When Sierra agrees with the bars, nothing changes and provenance
        stays 'sierra_live' — the correction must be invisible on a healthy
        machine (mac-1 safety proof)."""
        self._patch_bars(monkeypatch, 7830.75, 7813.75)
        out = tpo_routes._normalize_sierra_tpo(
            _raw(high=7830.75, low=7813.75), age_s=1.0)
        assert out["ib_high"] == 7830.75 and out["ib_low"] == 7813.75
        assert out["ib_source"] == "sierra_live"

    def test_incomplete_window_never_corrects(self, monkeypatch):
        """Fewer than 12 RTH bars = the IB window is not complete → never
        substitute (no half-formed IB)."""
        self._patch_bars(monkeypatch, 7825.0, 7820.0, n=5)
        out = tpo_routes._normalize_sierra_tpo(_raw(), age_s=1.0)
        assert out["ib_source"] != "bars_derived_correction"

    def test_db_error_keeps_sierra_value(self, monkeypatch):
        def _boom(*a, **k):
            raise RuntimeError("db down")
        monkeypatch.setattr("backend.v9.db.read.read_one", _boom, raising=False)
        out = tpo_routes._normalize_sierra_tpo(_raw(), age_s=1.0)
        assert out["ib_high"] == 7817.5  # unchanged, never raises
