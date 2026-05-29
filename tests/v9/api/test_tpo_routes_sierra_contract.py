import json
import time

import pytest

from backend.v9.api.v9 import tpo_routes


def test_normalize_sierra_tpo_contract():
    data = {
        "type": "tpo",
        "version": "v9.4.0-p30.9",
        "export_ts": 1779134300,
        "session": {
            "poc": 7408.25,
            "vah": 7430.50,
            "val": 7388.50,
            "session_high": 7454.25,
            "session_low": 7372.75,
            "total_volume": 1622751.0,
        },
        "ib": {"found": True, "high": 7454.25, "mid": 7434.75, "low": 7415.25},
        "prior_day": {"found": True, "high": 7435.25, "low": 7375.0, "close": 7385.5},
    }

    normalized = tpo_routes._normalize_sierra_tpo(data, age_s=1.234)

    assert normalized["source"] == "sierra_tpo_json"
    assert normalized["poc"] == 7408.25
    assert normalized["vah"] == 7430.50
    assert normalized["val"] == 7388.50
    assert normalized["ib_high"] == 7454.25
    assert normalized["ib_mid"] == 7434.75
    assert normalized["ib_low"] == 7415.25
    assert normalized["ib_width"] == 39.0
    assert normalized["prior_day"]["high"] == 7435.25
    assert normalized["session_va_ok"] is True
    assert normalized["ib_found"] is True


def test_load_sierra_tpo_serves_stale_file_with_flag(tmp_path):
    export_path = tmp_path / "tpo.json"
    export_path.write_text(
        json.dumps(
            {
                "type": "tpo",
                "session": {"poc": 7411.25, "vah": 7428.5, "val": 7390.75},
                "ib": {"found": True, "high": 7378.75, "mid": 7366.25, "low": 7353.75},
            }
        )
    )
    old_ts = time.time() - 120
    export_path.touch()
    import os

    os.utime(export_path, (old_ts, old_ts))

    loaded = tpo_routes._load_sierra_tpo(export_path, max_age_s=1)
    assert loaded is not None
    assert loaded["stale"] is True
    assert loaded["poc"] == 7411.25
    assert loaded["session_va_ok"] is True


def test_va_spread_rejects_collapsed_session():
    assert tpo_routes._va_spread_ok(7392.5, 7393.5, 7392.5) is False
    assert tpo_routes._va_spread_ok(7411.25, 7428.5, 7390.75) is True


def test_normalize_emits_session_opened_ts_for_rth_anchor():
    """Frontend POC line anchors at RTH open; backend must always provide it.

    Sierra `tpo.json` currently omits `session.opened_ts`, so the backend
    computes 09:30 ET of the current trading day. Without this anchor the
    pink current-day POC starts at the first visible bar instead of RTH
    open — root cause of the "POC not big from RTH start" complaint.
    """
    data = {
        "type": "tpo",
        "session": {"poc": 7408.25, "vah": 7430.50, "val": 7388.50},
        "ib": {"found": True, "high": 7454.25, "mid": 7434.75, "low": 7415.25},
        "prior_day": {"found": True, "high": 7435.25, "low": 7375.0, "close": 7385.5},
    }
    normalized = tpo_routes._normalize_sierra_tpo(data, age_s=1.0)
    assert normalized["session_opened_ts"] is not None
    assert normalized["session_opened_ts"].endswith(" 09:30:00")


def test_normalize_prefers_export_session_opened_ts_when_present():
    """If Sierra DLL ever exports session.opened_ts, honour it verbatim."""
    data = {
        "type": "tpo",
        "session": {
            "poc": 7408.25,
            "vah": 7430.50,
            "val": 7388.50,
            "opened_ts": "2026-05-19T09:30:00-04:00",
        },
        "ib": {"found": True, "high": 7454.25, "mid": 7434.75, "low": 7415.25},
        "prior_day": {"found": False},
    }
    normalized = tpo_routes._normalize_sierra_tpo(data, age_s=1.0)
    assert normalized["session_opened_ts"] == "2026-05-19 09:30:00"


def test_load_tpo_periods_normalizes_unix_ts(monkeypatch):
    import sqlite3

    # Skip history path so sessions fallback runs with our FakeConn
    monkeypatch.setattr(tpo_routes, "_load_periods_from_history", lambda **kw: [])

    import time as _time
    # Use a recent timestamp (within 48h cutoff) so the filter doesn't reject
    recent_epoch = int(_time.time()) - 3600  # 1 hour ago

    class FakeConn:
        row_factory = None

        def execute(self, *args, **kwargs):
            class R:
                def fetchall(self_inner):
                    return [
                        {
                            "opened_ts": recent_epoch,
                            "closed_ts": None,
                            "poc_price": 7415.25,
                            "vah_price": 7420.0,
                            "val_price": 7410.0,
                        }
                    ]

            return R()

        def close(self):
            pass

    monkeypatch.setattr(sqlite3, "connect", lambda *a, **k: FakeConn())
    periods = tpo_routes._load_tpo_periods(limit=1)
    assert periods[0]["poc_price"] == 7415.25
    assert periods[0]["opened_ts"].startswith("2026-")


def test_normalize_rejects_invalid_va_without_synthesis(monkeypatch, caplog):
    """Memorial Day fix #3 · CLAUDE.md compliance.

    When Sierra session VA is invalid, backend MUST return poc=None.
    It must NOT silently substitute stale DB period data.
    """
    import logging

    stale_periods = [
        {"poc_price": 7501.5, "vah_price": 7517.5, "val_price": 7485.5,
         "opened_ts": "2026-05-22 09:30:00", "closed_ts": "2026-05-22 16:00:00"},
    ]
    monkeypatch.setattr(tpo_routes, "_load_tpo_periods", lambda *a, **k: stale_periods)

    data = {
        "type": "tpo",
        "session": {"poc": 0.0, "vah": 0.0, "val": 0.0, "va_ok": False},
        "ib": {"found": False, "high": 0, "mid": 0, "low": 0},
        "prior_day": {"found": False},
    }

    with caplog.at_level(logging.WARNING, logger="backend.v9.api.v9.tpo_routes"):
        normalized = tpo_routes._normalize_sierra_tpo(data, age_s=1.0)

    assert normalized["poc"] is None, "synthesis leaked: poc should be None"
    assert normalized["vah"] is None, "synthesis leaked: vah should be None"
    assert normalized["val"] is None, "synthesis leaked: val should be None"
    assert normalized["session_va_ok"] is False
    assert any(
        "Sierra session VA invalid" in r.message and "rejecting" in r.message
        for r in caplog.records
    ), "expected warning log on rejection"


def test_previous_session_passes_through_y_ib_when_dll_reports_it(monkeypatch):
    """Step 9 (2026-05-28): DLL Input 19 → previous_session.ib_high/ib_low.

    When Sierra DLL emits ``previous_session.ib_found=true`` with valid
    MES-range high/low, the normalized previous_session must surface them
    unchanged. No synthesis, no DB merge for IB.
    """
    monkeypatch.setattr(tpo_routes, "_load_previous_cash_session", lambda: None)
    data = {
        "type": "tpo",
        "session": {"poc": 7559.5, "vah": 7563.5, "val": 7555.75},
        "ib": {"found": True, "high": 7570, "mid": 7562, "low": 7554},
        "prior_day": {"found": True, "high": 7524, "low": 7478.75, "close": 7484.25},
        "previous_session": {
            "found": True,
            "poc": 7535.25,
            "vah": 7549.75,
            "val": 7520.75,
            "ib_found": True,
            "ib_high": 7545.50,
            "ib_low": 7522.25,
        },
    }
    normalized = tpo_routes._normalize_sierra_tpo(data, age_s=1.0)
    prev = normalized["previous_session"]
    assert prev is not None
    assert prev["ib_high"] == 7545.50
    assert prev["ib_low"] == 7522.25
    assert prev["ib_found"] is True


def test_previous_session_y_ib_missing_when_dll_disabled(monkeypatch):
    """Step 9: when Sierra Input 19 is 0 (default), DLL emits ib_found=false
    and ib_high/ib_low=0. Backend must surface NULL, never synthesise."""
    monkeypatch.setattr(tpo_routes, "_load_previous_cash_session", lambda: None)
    data = {
        "type": "tpo",
        "session": {"poc": 7559.5, "vah": 7563.5, "val": 7555.75},
        "ib": {"found": False, "high": 0, "mid": 0, "low": 0},
        "prior_day": {"found": True, "high": 7524, "low": 7478.75, "close": 7484.25},
        "previous_session": {
            "found": True,
            "poc": 7535.25,
            "vah": 7549.75,
            "val": 7520.75,
            "ib_found": False,
            "ib_high": 0,
            "ib_low": 0,
        },
    }
    normalized = tpo_routes._normalize_sierra_tpo(data, age_s=1.0)
    prev = normalized["previous_session"]
    assert prev is not None
    assert prev["ib_high"] is None
    assert prev["ib_low"] is None
    assert prev["ib_found"] is False


def test_previous_session_y_ib_rejects_out_of_range(monkeypatch):
    """Step 9: corrupt Y IB (e.g. -89088 like Memorial Day session VA) must
    be rejected by the same MES range guard, never leaking into the API."""
    monkeypatch.setattr(tpo_routes, "_load_previous_cash_session", lambda: None)
    data = {
        "type": "tpo",
        "session": {"poc": 7559.5, "vah": 7563.5, "val": 7555.75},
        "ib": {"found": False},
        "prior_day": {"found": False},
        "previous_session": {
            "found": True,
            "poc": 7535.25,
            "vah": 7549.75,
            "val": 7520.75,
            "ib_found": True,
            "ib_high": -89088,
            "ib_low": 0,
        },
    }
    normalized = tpo_routes._normalize_sierra_tpo(data, age_s=1.0)
    prev = normalized["previous_session"]
    assert prev is not None
    assert prev["ib_high"] is None
    assert prev["ib_low"] is None


def test_normalize_valid_va_unchanged_by_fix3(monkeypatch):
    """Regression: Fix #3 must NOT affect the happy path."""
    monkeypatch.setattr(tpo_routes, "_load_tpo_periods", lambda *a, **k: [
        {"poc_price": 9999.0, "vah_price": 9999.0, "val_price": 9999.0}
    ])
    data = {
        "type": "tpo",
        "session": {"poc": 7559.5, "vah": 7563.5, "val": 7555.75},
        "ib": {"found": True, "high": 7570, "mid": 7562, "low": 7554},
        "prior_day": {"found": True, "high": 7524, "low": 7478.75, "close": 7484.25},
    }
    normalized = tpo_routes._normalize_sierra_tpo(data, age_s=1.0)
    assert normalized["poc"] == 7559.5
    assert normalized["session_va_ok"] is True
    assert normalized["poc"] != 9999.0


# ──────────────────────────────────────────────────────────────────────
# IB sourcing — Sierra-live preferred, v9_bars_5min fallback approved by
# Michael 2026-05-28 18:31 IDT ("don't touch DLL — use the data we have").
# ──────────────────────────────────────────────────────────────────────

def test_sierra_change_tracks_within_one_cycle():
    """When Sierra emits a NEW IB value, normalize must follow verbatim."""

    def normalize(ib_high, ib_low):
        return tpo_routes._normalize_sierra_tpo({
            "type": "tpo",
            "session": {"poc": 7551.0, "vah": 7574.0, "val": 7541.0},
            "ib": {"found": True, "high": ib_high, "mid": (ib_high + ib_low) / 2,
                   "low": ib_low},
            "prior_day": {"found": False},
        }, age_s=1.0)

    n1 = normalize(7543.75, 7522.0)
    n2 = normalize(7555.0, 7530.0)
    assert n1["ib_high"] == 7543.75 and n1["ib_low"] == 7522.0
    assert n2["ib_high"] == 7555.0 and n2["ib_low"] == 7530.0
    assert n1["ib_source"] == "sierra_live"


def test_sierra_silent_returns_missing():
    """Sierra `ib_found=false` → ib_source='missing', no synthesis.

    _ib_from_bars() deleted per 2026-05-28 evening revocation. IB only
    from Sierra Initial Balance Study. See AMENDMENTS_LOG.md.
    """
    data = {
        "type": "tpo",
        "session": {"poc": 7561.5, "vah": 7574.0, "val": 7544.75},
        "ib": {"found": False, "high": 0.0, "mid": 0.0, "low": 0.0},
        "prior_day": {"found": False},
    }
    n = tpo_routes._normalize_sierra_tpo(data, age_s=2.0)
    assert n["ib_found"] is False
    assert n["ib_high"] is None
    assert n["ib_low"] is None
    assert n["ib_width"] is None
    assert n["ib_source"] == "missing"


def test_sierra_live_ib_source():
    """Sierra-live IB is the only source (no bars fallback)."""
    data = {
        "type": "tpo",
        "session": {"poc": 7551.0, "vah": 7574.0, "val": 7541.0},
        "ib": {"found": True, "high": 7543.75, "mid": 7532.88, "low": 7522.0},
        "prior_day": {"found": False},
    }
    n = tpo_routes._normalize_sierra_tpo(data, age_s=1.0)
    assert n["ib_high"] == 7543.75
    assert n["ib_low"] == 7522.0
    assert n["ib_source"] == "sierra_live"
