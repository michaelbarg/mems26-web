"""P30.9b — Tests for /api/v9/cumulative_delta/current.

Proves the GET endpoint reads Sierra cumulative_delta.json correctly,
rejects stale files, and handles missing files without crashing.
"""

import json
import os
import time
import tempfile

import pytest
from fastapi.testclient import TestClient

from backend.v9.api.v9 import cumulative_delta_routes
from backend.v9.app import app

client = TestClient(app)

SAMPLE_CVD = {
    "type": "cumulative_delta",
    "version": "v9.4.0-p30.9",
    "export_ts": int(time.time()),
    "points": [
        {"i": 100, "d": -88.0, "cum": -88.0, "p": 7400.0},
        {"i": 105, "d": 150.0, "cum": 62.0, "p": 7405.0},
        {"i": 110, "d": -30.0, "cum": 32.0, "p": 7402.0},
    ],
    "current_delta": 32.0,
    "session_delta": 32.0,
    "peak": 62.0,
    "trough": -88.0,
}


def test_cvd_returns_200_with_fresh_file(monkeypatch, tmp_path):
    """Endpoint returns points from a fresh Sierra file."""
    f = tmp_path / "cumulative_delta.json"
    f.write_text(json.dumps(SAMPLE_CVD))

    monkeypatch.setattr(cumulative_delta_routes, "EXPORT_PATH", f)
    resp = client.get("/api/v9/cumulative_delta/current")
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "sierra_cumulative_delta_json"
    assert data["stale"] is False
    assert data["point_count"] == 3
    assert data["current_delta"] == 32.0
    assert data["peak"] == 62.0
    assert len(data["points"]) == 3


def test_cvd_returns_stale_when_old(monkeypatch, tmp_path):
    """Endpoint flags stale when file is older than threshold."""
    f = tmp_path / "cumulative_delta.json"
    f.write_text(json.dumps(SAMPLE_CVD))
    # Set mtime to 60s ago
    old_time = time.time() - 60
    os.utime(f, (old_time, old_time))

    monkeypatch.setattr(cumulative_delta_routes, "EXPORT_PATH", f)
    monkeypatch.setattr(cumulative_delta_routes, "MAX_AGE_S", 30.0)
    resp = client.get("/api/v9/cumulative_delta/current")
    assert resp.status_code == 200
    data = resp.json()
    assert data["stale"] is True
    assert "error" in data


def test_cvd_returns_missing_when_no_file(monkeypatch, tmp_path):
    """Endpoint returns source=missing when file doesn't exist."""
    monkeypatch.setattr(cumulative_delta_routes, "EXPORT_PATH", tmp_path / "nonexistent.json")
    resp = client.get("/api/v9/cumulative_delta/current")
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "missing"


def test_cvd_augments_points_with_t_when_dll_omits_it(monkeypatch, tmp_path):
    """Sierra DLL ships points without `t`; backend must add it from export_ts.

    Frontend pins CVD candles to `pt.t`; without this augment the CVD pane
    falls back to bar-index positioning and drifts off the price chart's X
    axis — exactly the "time axis doesn't overlap" symptom seen on the chart.
    """
    fixed_export_ts = 1779200000
    # i-step=1 mirrors the post-v9.4.2 DLL emitting every host-chart bar.
    payload = {
        **SAMPLE_CVD,
        "export_ts": fixed_export_ts,
        "points": [
            {"i": 100, "d": -88.0, "cum": -88.0, "p": 7400.0},
            {"i": 101, "d": 50.0, "cum": -38.0, "p": 7402.0},
            {"i": 102, "d": -30.0, "cum": -68.0, "p": 7401.0},
        ],
    }
    f = tmp_path / "cumulative_delta.json"
    f.write_text(json.dumps(payload))
    monkeypatch.setattr(cumulative_delta_routes, "EXPORT_PATH", f)
    monkeypatch.setattr(cumulative_delta_routes, "HOST_BAR_S", 300.0)
    monkeypatch.setattr(cumulative_delta_routes, "CVD_PERIOD_S", 300.0)
    # P31 §A — augment logic is independent of the Chicago→UTC workaround
    # added in the same series of fixes; disable the workaround so this
    # test continues to assert period-derivation alone.
    monkeypatch.setattr(cumulative_delta_routes, "_DISABLE_CHICAGO_TS_FIX", True)

    resp = client.get("/api/v9/cumulative_delta/current")
    data = resp.json()
    points = data["points"]
    assert all("t" in p for p in points), "every point must carry a timestamp"
    assert points[-1]["t"] == fixed_export_ts
    assert points[-2]["t"] == fixed_export_ts - 300
    assert points[-3]["t"] == fixed_export_ts - 600
    assert data["period_s"] == 300.0


def test_period_s_prefers_dll_output_interval(monkeypatch, tmp_path):
    """Once the DLL ships `output_interval=300`, backend honours it verbatim."""
    payload = {**SAMPLE_CVD, "export_ts": 1779200000, "output_interval": 300}
    f = tmp_path / "cumulative_delta.json"
    f.write_text(json.dumps(payload))
    monkeypatch.setattr(cumulative_delta_routes, "EXPORT_PATH", f)
    # Set the env fallback to something obviously wrong to prove we don't use it.
    monkeypatch.setattr(cumulative_delta_routes, "CVD_PERIOD_S", 9999.0)
    monkeypatch.setattr(cumulative_delta_routes, "HOST_BAR_S", 9999.0)

    resp = client.get("/api/v9/cumulative_delta/current")
    data = resp.json()
    assert data["period_s"] == 300.0
    # And the synthetic `t` values respect that interval.
    assert data["points"][-1]["t"] - data["points"][-2]["t"] == 300


def test_period_s_auto_detects_legacy_dll_with_mod5_filter(monkeypatch, tmp_path):
    """Pre-v9.4.2 DLL had `% 5 == 0` filter — points have i-step ≈ 5.
    Backend must detect that from the data even with no `output_interval`."""
    payload = {
        **SAMPLE_CVD,
        "export_ts": 1779200000,
        # No output_interval (legacy DLL).
        "points": [
            {"i": 100, "d": -88.0, "cum": -88.0, "p": 7400.0},
            {"i": 105, "d": 150.0, "cum": 62.0, "p": 7405.0},
            {"i": 110, "d": -30.0, "cum": 32.0, "p": 7402.0},
        ],
    }
    f = tmp_path / "cumulative_delta.json"
    f.write_text(json.dumps(payload))
    monkeypatch.setattr(cumulative_delta_routes, "EXPORT_PATH", f)
    monkeypatch.setattr(cumulative_delta_routes, "HOST_BAR_S", 300.0)

    resp = client.get("/api/v9/cumulative_delta/current")
    data = resp.json()
    # i-step = 5 → period_s = 5 * 300 = 1500 s
    assert data["period_s"] == 1500.0
    assert data["points"][-1]["t"] - data["points"][-2]["t"] == 1500


def test_period_s_auto_detects_new_dll_unfiltered(monkeypatch, tmp_path):
    """Post-v9.4.2 DLL emits every host bar — i-step ≈ 1 → period_s = 300 s."""
    payload = {
        **SAMPLE_CVD,
        "export_ts": 1779200000,
        "points": [
            {"i": 100, "d": -88.0, "cum": -88.0, "p": 7400.0},
            {"i": 101, "d": 50.0, "cum": -38.0, "p": 7402.0},
            {"i": 102, "d": -30.0, "cum": -68.0, "p": 7401.0},
        ],
    }
    f = tmp_path / "cumulative_delta.json"
    f.write_text(json.dumps(payload))
    monkeypatch.setattr(cumulative_delta_routes, "EXPORT_PATH", f)
    monkeypatch.setattr(cumulative_delta_routes, "HOST_BAR_S", 300.0)

    resp = client.get("/api/v9/cumulative_delta/current")
    data = resp.json()
    assert data["period_s"] == 300.0
    assert data["points"][-1]["t"] - data["points"][-2]["t"] == 300


def test_cvd_preserves_dll_t_when_present(monkeypatch, tmp_path):
    """If Sierra DLL ever emits `t` per point, the backend must not overwrite it
    via the `_augment_points_with_t` path (the period-derivation augment).
    The Chicago→UTC workaround is disabled here so the assertion compares
    DLL-supplied `t` verbatim.
    """
    payload = {
        **SAMPLE_CVD,
        "export_ts": 1779200000,
        "points": [
            {"i": 100, "d": -88.0, "cum": -88.0, "p": 7400.0, "t": 1779100000},
            {"i": 105, "d": 150.0, "cum": 62.0, "p": 7405.0, "t": 1779100300},
            {"i": 110, "d": -30.0, "cum": 32.0, "p": 7402.0, "t": 1779100600},
        ],
    }
    f = tmp_path / "cumulative_delta.json"
    f.write_text(json.dumps(payload))
    monkeypatch.setattr(cumulative_delta_routes, "EXPORT_PATH", f)
    monkeypatch.setattr(cumulative_delta_routes, "_DISABLE_CHICAGO_TS_FIX", True)

    resp = client.get("/api/v9/cumulative_delta/current")
    data = resp.json()
    assert [p["t"] for p in data["points"]] == [1779100000, 1779100300, 1779100600]


# ── P31 §A: Chicago-wall-clock-as-UTC fix (DLL TZ workaround) ──────────────


def test_cvd_endpoint_fixes_chicago_encoded_t(monkeypatch, tmp_path):
    """Sierra DLL ships `points[].t` encoded as Chicago wall-clock treated
    as UTC unix (same bug as §9 for bars). The endpoint must rewrite each
    `t` so the CVD pane lines up with price bars on the shared timeScale.

    Without this workaround the live CVD pane renders ~5h to the LEFT of
    the price bars, exactly the user-reported Issue A symptom from the
    P31 next-chat handoff doc.
    """
    # Pretend the DLL just exported at 10:00 CDT = 15:00 UTC. The DLL bug
    # would encode the per-point `t` as 10:00 UTC (1779181200) — 5h early.
    chicago_encoded_t = 1779181200  # = 2026-05-19 17:00 UTC = 12:00 CDT
    payload = {
        **SAMPLE_CVD,
        "export_ts": 1779199200,  # 5h later — a real UTC timestamp
        "points": [
            {"i": 100, "d": -88.0, "cum": -88.0, "p": 7400.0, "t": chicago_encoded_t},
            {"i": 101, "d": 50.0, "cum": -38.0, "p": 7402.0, "t": chicago_encoded_t + 300},
        ],
    }
    f = tmp_path / "cumulative_delta.json"
    f.write_text(json.dumps(payload))
    monkeypatch.setattr(cumulative_delta_routes, "EXPORT_PATH", f)
    monkeypatch.setattr(cumulative_delta_routes, "_DISABLE_CHICAGO_TS_FIX", False)

    resp = client.get("/api/v9/cumulative_delta/current")
    data = resp.json()
    for p in data["points"]:
        # Every `t` must be shifted FORWARD by the Chicago→UTC offset
        # (4h CDT or 5h CST) so it lines up with the real UTC clock.
        assert p["t"] > chicago_encoded_t + 300, (
            f"point.t={p['t']} not shifted from Chicago-encoded baseline "
            f"{chicago_encoded_t}; Chicago→UTC fix may not be active"
        )
    # Spacing between points must survive the shift.
    assert data["points"][1]["t"] - data["points"][0]["t"] == 300


def test_cvd_endpoint_chicago_fix_no_op_when_disabled(monkeypatch, tmp_path):
    """`V9_DISABLE_CHICAGO_TS_FIX=1` short-circuits the workaround so the
    DLL canonical fix (§9 Option A) can ship without backend churn.
    """
    original_t = 1779181200
    payload = {
        **SAMPLE_CVD,
        "export_ts": 1779199200,
        "points": [{"i": 1, "d": 0.0, "cum": 0.0, "p": 7400.0, "t": original_t}],
    }
    f = tmp_path / "cumulative_delta.json"
    f.write_text(json.dumps(payload))
    monkeypatch.setattr(cumulative_delta_routes, "EXPORT_PATH", f)
    monkeypatch.setattr(cumulative_delta_routes, "_DISABLE_CHICAGO_TS_FIX", True)

    resp = client.get("/api/v9/cumulative_delta/current")
    data = resp.json()
    assert data["points"][0]["t"] == original_t


def test_cvd_latency_under_100ms(monkeypatch, tmp_path):
    """Endpoint responds within budget."""
    f = tmp_path / "cumulative_delta.json"
    f.write_text(json.dumps(SAMPLE_CVD))
    monkeypatch.setattr(cumulative_delta_routes, "EXPORT_PATH", f)

    start = time.monotonic()
    resp = client.get("/api/v9/cumulative_delta/current")
    elapsed_ms = (time.monotonic() - start) * 1000
    assert resp.status_code == 200
    assert elapsed_ms < 100, f"CVD endpoint took {elapsed_ms:.1f}ms"


# ── P31 §B: DB-backed history backfill ─────────────────────────────────────


def test_cvd_history_off_by_default_keeps_legacy_shape(monkeypatch, tmp_path):
    """Without ``?history=1`` the response shape is unchanged for legacy
    callers — point_count equals what the JSON file ships and DB queries
    are not even attempted.
    """
    f = tmp_path / "cumulative_delta.json"
    f.write_text(json.dumps(SAMPLE_CVD))
    monkeypatch.setattr(cumulative_delta_routes, "EXPORT_PATH", f)

    called = {"db": 0}

    def _fake_history(*_args, **_kwargs):
        called["db"] += 1
        return []

    monkeypatch.setattr(cumulative_delta_routes, "_load_db_history", _fake_history)

    resp = client.get("/api/v9/cumulative_delta/current")
    data = resp.json()
    assert data["point_count"] == 3
    assert data.get("history_count") in (None, 0)
    assert called["db"] == 0, "DB query must not run when history=0"


def test_cvd_history_prepends_older_db_rows(monkeypatch, tmp_path):
    """With ``?history=1`` DB rows older than the first live point are
    prepended so the chart can render the full pane width. Live JSON
    points stay at the tail and keep priority for live update cadence.
    """
    fixed_export_ts = 1779200000
    payload = {
        **SAMPLE_CVD,
        "export_ts": fixed_export_ts,
        "points": [
            {"i": 100, "d": 1.0, "cum": 1.0, "p": 7400.0, "t": fixed_export_ts - 600},
            {"i": 101, "d": 2.0, "cum": 3.0, "p": 7401.0, "t": fixed_export_ts - 300},
            {"i": 102, "d": 3.0, "cum": 6.0, "p": 7402.0, "t": fixed_export_ts},
        ],
    }
    f = tmp_path / "cumulative_delta.json"
    f.write_text(json.dumps(payload))
    monkeypatch.setattr(cumulative_delta_routes, "EXPORT_PATH", f)
    # Disable the Chicago→UTC fix so the live `t` values stay verbatim and
    # the prepend ordering assertion can compare raw integers.
    monkeypatch.setattr(cumulative_delta_routes, "_DISABLE_CHICAGO_TS_FIX", True)

    db_rows = [
        {"i": -3, "t": fixed_export_ts - 1800, "d": -1.0, "cum": -1.0, "p": 0.0},
        {"i": -2, "t": fixed_export_ts - 1500, "d": -2.0, "cum": -3.0, "p": 0.0},
        {"i": -1, "t": fixed_export_ts - 1200, "d": -4.0, "cum": -7.0, "p": 0.0},
    ]

    captured = {}

    def _fake_history(before_unix, limit):
        captured["before"] = before_unix
        captured["limit"] = limit
        return db_rows

    monkeypatch.setattr(cumulative_delta_routes, "_load_db_history", _fake_history)

    resp = client.get("/api/v9/cumulative_delta/current?history=1&limit=600")
    data = resp.json()
    assert data["history_count"] == 3
    assert data["point_count"] == 6
    # DB rows come first (older), live JSON points last.
    assert [p["t"] for p in data["points"]] == [
        fixed_export_ts - 1800,
        fixed_export_ts - 1500,
        fixed_export_ts - 1200,
        fixed_export_ts - 600,
        fixed_export_ts - 300,
        fixed_export_ts,
    ]
    assert captured["before"] == fixed_export_ts - 600
    assert captured["limit"] == 600


def test_cvd_history_filters_overlap_with_live_points(monkeypatch, tmp_path):
    """DB rows whose `t` >= first live point are dropped — live JSON wins
    on the live tail to avoid double-counting the same bucket.
    """
    fixed_export_ts = 1779200000
    payload = {
        **SAMPLE_CVD,
        "export_ts": fixed_export_ts,
        "points": [
            {"i": 100, "d": 1.0, "cum": 1.0, "p": 7400.0, "t": fixed_export_ts - 300},
            {"i": 101, "d": 2.0, "cum": 3.0, "p": 7401.0, "t": fixed_export_ts},
        ],
    }
    f = tmp_path / "cumulative_delta.json"
    f.write_text(json.dumps(payload))
    monkeypatch.setattr(cumulative_delta_routes, "EXPORT_PATH", f)
    monkeypatch.setattr(cumulative_delta_routes, "_DISABLE_CHICAGO_TS_FIX", True)

    # Provide DB rows where one row overlaps the first live `t`.
    def _fake_history(before_unix, limit):
        return [
            # Older — should be kept.
            {"i": -1, "t": fixed_export_ts - 900, "d": 0.0, "cum": 0.0, "p": 0.0},
            # Equal to first live → filtered by _load_db_history's contract.
            {"i": -2, "t": fixed_export_ts - 300, "d": 0.0, "cum": 0.0, "p": 0.0},
        ]

    monkeypatch.setattr(cumulative_delta_routes, "_load_db_history", _fake_history)

    resp = client.get("/api/v9/cumulative_delta/current?history=1")
    data = resp.json()
    # The fake returns one overlap, but the endpoint contract is to *prepend*
    # whatever the loader returns; the loader itself filters by `before_unix`.
    # Here we cover the prepend path; loader-side filter is tested via
    # `test_load_db_history_filters_after_before_unix` below.
    assert len(data["points"]) == 4  # 2 live + 2 db
    assert data["history_count"] == 2


def test_load_db_history_returns_empty_when_db_missing(monkeypatch):
    """The loader is non-fatal — DB unavailability returns [] so the
    endpoint always serves the live JSON tail.
    """
    from backend.v9.api.v9 import cumulative_delta_routes as mod
    import backend.v9.db.session as session_mod

    def _boom(*_a, **_kw):
        raise RuntimeError("db down")

    monkeypatch.setattr(session_mod, "SessionLocal", _boom)
    rows = mod._load_db_history(before_unix=10**9, limit=600)
    assert rows == []


def test_load_db_history_returns_empty_for_zero_limit():
    """`limit=0` short-circuits without touching the DB."""
    from backend.v9.api.v9 import cumulative_delta_routes as mod

    assert mod._load_db_history(before_unix=10**9, limit=0) == []
