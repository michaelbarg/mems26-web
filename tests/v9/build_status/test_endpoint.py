"""Endpoint tests for GET /api/v9/build/pattern-status.

Tests 1-3, 12-16 from the mega-prompt golden test list.
Uses real FiveMinSystem and WoodiesSystem instances (anti-mock constraint).
"""

import ast
import importlib
import pkgutil
import sqlite3
import time
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.v9.api.v9.build_status_routes import router as build_status_router
from backend.v9.systems.build_status import s2_inspector, woodies_inspector, day_type_inspector
from backend.v9.systems.build_status.aggregator import BuildStatusAggregator
from backend.v9.systems.build_status.types import BuildStatusResponse
from backend.v9.systems.five_min.five_min_system import FiveMinSystem
from backend.v9.systems.woodies.woodies_system import WoodiesSystem


def _make_app(five_min_system=None, woodies_system=None, day_type_machine=None):
    """Create a minimal FastAPI app with systems attached to state."""
    app = FastAPI()
    app.include_router(build_status_router)
    app.state.five_min_system = five_min_system
    app.state.woodies_system = woodies_system
    app.state.day_type_machine = day_type_machine
    return app


@pytest.fixture
def minimal_db(tmp_path):
    """Minimal SQLite DB with empty tables for endpoint tests."""
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE v9_bars_5min (
        id INTEGER PRIMARY KEY, ts TEXT, symbol TEXT DEFAULT 'MES',
        open REAL, high REAL, low REAL, close REAL, volume INTEGER
    )""")
    conn.execute("""CREATE TABLE v9_bars_5min_woodies (
        id INTEGER PRIMARY KEY, ts TEXT, open REAL, high REAL, low REAL, close REAL, volume INTEGER
    )""")
    conn.execute("""CREATE TABLE v9_five_min_setups (
        id INTEGER PRIMARY KEY, ts TEXT, pattern TEXT, direction TEXT,
        entry_price REAL DEFAULT 0, stop_price REAL DEFAULT 0, confidence REAL DEFAULT 75.0
    )""")
    conn.execute("""CREATE TABLE v9_day_type_history (
        id INTEGER PRIMARY KEY, date TEXT, day_type TEXT, probability REAL,
        directional_certainty REAL, ib_width_class TEXT, opening_type TEXT,
        last_updated_at TEXT, active_zohar_rules TEXT
    )""")
    conn.commit()
    conn.close()
    return db_path


# ── Test 1 ───────────────────────────────────────────────────────────────────

def test_build_status_endpoint_returns_200_when_all_systems_up(
    real_five_min_system, real_woodies_system, minimal_db, monkeypatch
):
    """Test #1: Happy path — all 3 systems present → 200 with 3 system objects."""
    monkeypatch.setattr(s2_inspector, "DB_PATH", minimal_db)
    monkeypatch.setattr(woodies_inspector, "DB_PATH", minimal_db)
    monkeypatch.setattr(day_type_inspector, "DB_PATH", minimal_db)

    import backend.v9.systems.build_status.aggregator as agg_mod
    monkeypatch.setattr(agg_mod, "DB_PATH", minimal_db)

    app = _make_app(
        five_min_system=real_five_min_system,
        woodies_system=real_woodies_system,
    )
    client = TestClient(app)
    resp = client.get("/api/v9/build/pattern-status")

    assert resp.status_code == 200
    data = resp.json()
    assert "systems" in data
    assert len(data["systems"]) == 5  # bridge + five_min + footprint + woodies + day_type
    system_ids = {s["id"] for s in data["systems"]}
    assert system_ids == {"bridge", "five_min", "footprint", "woodies", "day_type"}


# ── Test 2 ───────────────────────────────────────────────────────────────────

def test_build_status_endpoint_returns_200_when_woodies_uninitialized(
    real_five_min_system, minimal_db, monkeypatch
):
    """Test #2: woodies_system=None → 200 (NOT 500), woodies system running=False.

    Per BUILD_STATUS_ENDPOINT_DESIGN.md §5.5:
    "If app.state.woodies_system is None → running=false, hydrated=false · NOT 500"
    """
    monkeypatch.setattr(s2_inspector, "DB_PATH", minimal_db)
    monkeypatch.setattr(woodies_inspector, "DB_PATH", minimal_db)
    monkeypatch.setattr(day_type_inspector, "DB_PATH", minimal_db)

    import backend.v9.systems.build_status.aggregator as agg_mod
    monkeypatch.setattr(agg_mod, "DB_PATH", minimal_db)

    app = _make_app(
        five_min_system=real_five_min_system,
        woodies_system=None,  # not initialized
    )
    client = TestClient(app)
    resp = client.get("/api/v9/build/pattern-status")

    assert resp.status_code == 200  # NOT 500
    data = resp.json()

    woodies_sys = next(s for s in data["systems"] if s["id"] == "woodies")
    assert woodies_sys["running"] is False
    assert woodies_sys["hydrated"] is False


# ── Test 3 ───────────────────────────────────────────────────────────────────

def test_build_status_endpoint_p95_latency_under_300ms(
    real_five_min_system, real_woodies_system, minimal_db, monkeypatch
):
    """Test #3: 50 runs · p95 < 300ms.

    Per BUILD_STATUS_ENDPOINT_DESIGN.md §5.4: "300ms p95".
    Uses time.perf_counter() for accuracy.
    """
    monkeypatch.setattr(s2_inspector, "DB_PATH", minimal_db)
    monkeypatch.setattr(woodies_inspector, "DB_PATH", minimal_db)
    monkeypatch.setattr(day_type_inspector, "DB_PATH", minimal_db)

    import backend.v9.systems.build_status.aggregator as agg_mod
    monkeypatch.setattr(agg_mod, "DB_PATH", minimal_db)

    app = _make_app(
        five_min_system=real_five_min_system,
        woodies_system=real_woodies_system,
    )
    client = TestClient(app)

    # Warm up
    client.get("/api/v9/build/pattern-status")

    latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        resp = client.get("/api/v9/build/pattern-status")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert resp.status_code == 200
        latencies.append(elapsed_ms)

    latencies.sort()
    p95 = latencies[int(0.95 * len(latencies))]

    print(f"\nLatency p50={latencies[24]:.1f}ms p95={p95:.1f}ms p99={latencies[49]:.1f}ms")
    assert p95 < 300, (
        f"p95 latency {p95:.1f}ms exceeds 300ms budget "
        "(BUILD_STATUS_ENDPOINT_DESIGN.md §5.4)"
    )


# ── Test 12 ──────────────────────────────────────────────────────────────────

def test_response_shape_matches_pydantic_schema(
    real_five_min_system, real_woodies_system, minimal_db, monkeypatch
):
    """Test #12: Pydantic round-trip — dict output round-trips through BuildStatusResponse."""
    monkeypatch.setattr(s2_inspector, "DB_PATH", minimal_db)
    monkeypatch.setattr(woodies_inspector, "DB_PATH", minimal_db)
    monkeypatch.setattr(day_type_inspector, "DB_PATH", minimal_db)
    monkeypatch.setattr(
        __import__(
            "backend.v9.systems.build_status.aggregator",
            fromlist=["DB_PATH"],
        ),
        "DB_PATH",
        minimal_db,
    )

    agg = BuildStatusAggregator(
        five_min_system=real_five_min_system,
        woodies_system=real_woodies_system,
        db_path=minimal_db,
    )
    result = agg.get_status()

    assert isinstance(result, BuildStatusResponse)

    raw_dict = result.model_dump()
    roundtripped = BuildStatusResponse(**raw_dict)

    assert roundtripped.build_version == result.build_version
    assert roundtripped.session_date == result.session_date
    assert len(roundtripped.systems) == len(result.systems)


# ── Test 13 ──────────────────────────────────────────────────────────────────

def test_endpoint_includes_data_freshness_block(
    real_five_min_system, real_woodies_system, minimal_db, monkeypatch
):
    """Test #13: data_freshness block present on all systems with correct fields.

    Verifies: last_bar_ts, lag_seconds, fresh, threshold_seconds.
    """
    monkeypatch.setattr(s2_inspector, "DB_PATH", minimal_db)
    monkeypatch.setattr(woodies_inspector, "DB_PATH", minimal_db)
    monkeypatch.setattr(day_type_inspector, "DB_PATH", minimal_db)

    agg = BuildStatusAggregator(
        five_min_system=real_five_min_system,
        woodies_system=real_woodies_system,
        db_path=minimal_db,
    )
    result = agg.get_status()

    for sys_status in result.systems:
        df = sys_status.data_freshness
        assert df is not None, f"System {sys_status.id} missing data_freshness"
        # Verify all required fields exist (Pydantic will have them even if None)
        assert hasattr(df, "last_bar_ts")
        assert hasattr(df, "lag_seconds")
        assert hasattr(df, "fresh")
        assert hasattr(df, "threshold_seconds")
        # Per-system threshold — bridge uses 90s (tighter live-feed gate),
        # S2/Woodies/DayType inspectors use 360s (one 5-min bar + margin).
        # Source: bridge_inspector.py and the *_inspector.py defaults.
        assert df.threshold_seconds in (90, 360, 660), (
            f"System {sys_status.id} has unexpected threshold "
            f"{df.threshold_seconds}; expected 90 (bridge) or 360/660 (5min/woodies)"
        )


# ── Test 14 ──────────────────────────────────────────────────────────────────

def test_endpoint_handles_inspector_exception_returns_partial_result_with_error(
    real_five_min_system, minimal_db, monkeypatch, caplog
):
    """Test #14: one inspector raises → 200 response, that system='unknown', errors non-empty.

    Per BUILD_STATUS_ENDPOINT_DESIGN.md §5.5:
    "If any inspector raises → wrap in try/except, log logger.warning (rate-limited),
    and emit partial result with status='unknown' and errors=[...]"

    Also verifies logger.warning is called (constraint c).
    """
    import logging
    monkeypatch.setattr(s2_inspector, "DB_PATH", minimal_db)
    monkeypatch.setattr(woodies_inspector, "DB_PATH", minimal_db)
    monkeypatch.setattr(day_type_inspector, "DB_PATH", minimal_db)

    # Make woodies_inspector.inspect() raise
    original_woodies_inspect = woodies_inspector.inspect

    def _raise_woodies(*args, **kwargs):
        raise RuntimeError("Simulated woodies inspector failure")

    monkeypatch.setattr(woodies_inspector, "inspect", _raise_woodies)

    # Reset rate limiter so warning fires immediately
    import backend.v9.systems.build_status.aggregator as agg_mod
    agg_mod._WARN_RATE_ANCHOR.clear()

    agg = BuildStatusAggregator(
        five_min_system=real_five_min_system,
        woodies_system=None,  # doesn't matter — inspector is monkeypatched
        db_path=minimal_db,
    )

    # Track logger.warning calls via a logging handler
    warning_messages = []

    class WarningCapture(logging.Handler):
        def emit(self, record):
            if record.levelno >= logging.WARNING:
                warning_messages.append(record.getMessage())

    handler = WarningCapture()
    agg_mod.logger.addHandler(handler)
    try:
        result = agg.get_status()
    finally:
        agg_mod.logger.removeHandler(handler)

    # Should return 200-equivalent response (no exception raised)
    assert isinstance(result, BuildStatusResponse)

    # errors[] must be non-empty
    assert len(result.errors) > 0, "errors[] should be non-empty when inspector fails"
    assert any("woodies" in e.lower() for e in result.errors)

    # The woodies system entry should still be present with running=False
    woodies_sys = next((s for s in result.systems if s.id == "woodies"), None)
    assert woodies_sys is not None
    assert woodies_sys.running is False

    # logger.warning must have been called (constraint c: no silent excepts)
    assert len(warning_messages) > 0, (
        f"logger.warning must be called on inspector failure (constraint c). "
        f"Got 0 warning calls."
    )

    # Restore
    monkeypatch.setattr(woodies_inspector, "inspect", original_woodies_inspect)


# ── Test 15 ──────────────────────────────────────────────────────────────────

def test_endpoint_no_self_http_calls():
    """Test #15: httpx, requests, aiohttp must NOT be imported in build_status/ modules.

    Per mega-prompt §Constraints: no self-HTTP calls on hot path.
    Per BUILD_STATUS_ENDPOINT_DESIGN.md §5.4: no extra DB transactions.
    """
    import backend.v9.systems.build_status as build_status_pkg
    import backend.v9.api.v9.build_status_routes as route_mod

    forbidden_imports = {"httpx", "requests", "aiohttp"}

    def _get_imports(module_path: str) -> set:
        """Extract import names from a Python source file."""
        try:
            with open(module_path) as f:
                source = f.read()
            tree = ast.parse(source)
        except Exception:
            return set()

        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.add(node.module.split(".")[0])
        return names

    import os
    build_status_dir = os.path.dirname(build_status_pkg.__file__)
    for fname in os.listdir(build_status_dir):
        if fname.endswith(".py"):
            fpath = os.path.join(build_status_dir, fname)
            imports = _get_imports(fpath)
            bad = imports & forbidden_imports
            assert not bad, (
                f"{fname} imports forbidden HTTP client(s): {bad}. "
                "No self-HTTP calls allowed (BUILD_STATUS_ENDPOINT_DESIGN.md §5.4)"
            )

    # Also check routes file
    route_path = route_mod.__file__
    route_imports = _get_imports(route_path)
    bad = route_imports & forbidden_imports
    assert not bad, (
        f"build_status_routes.py imports forbidden HTTP client(s): {bad}"
    )


# ── Test 16 ──────────────────────────────────────────────────────────────────

def test_build_status_live_repro_with_real_five_min_system_instance(
    real_five_min_system, minimal_db, monkeypatch
):
    """Test #16: Real FiveMinSystem with 14+ bars — verify buffer state reflects in result.

    CRITICAL: uses real FiveMinSystem() instance — no mocks.
    Memorial Day lesson #1: fake mocks passed unit tests but real wiring failed.

    Verifies: five_min_bar_recency component reflects actual _bar_buffer state.
    """
    assert isinstance(real_five_min_system, FiveMinSystem), (
        "Must be a real FiveMinSystem — not a mock (anti-dead-code-wiring constraint)"
    )

    # Verify buffer has 14 bars (from conftest fixture)
    assert len(real_five_min_system._bar_buffer) == 14, (
        f"Expected 14 bars in _bar_buffer, got {len(real_five_min_system._bar_buffer)}"
    )

    monkeypatch.setattr(s2_inspector, "DB_PATH", minimal_db)

    result = s2_inspector.inspect(
        five_min_system=real_five_min_system,
        day_type_str="Trend_Normal",
    )

    # cci_14_history component must show present=True (14 >= 14)
    for p in result.patterns:
        cci_comp = next(c for c in p.components if c.key == "cci_14_history")
        assert cci_comp.present is True, (
            f"Pattern {p.id}: cci_14_history.present should be True "
            f"when _bar_buffer has 14 bars. "
            f"Got: {cci_comp.value!r}. "
            "This test catches dead-code wiring: if _bar_buffer is not read, "
            "this would show present=False."
        )

    # System must reflect real object's hydrated state
    assert result.running is True, "real_five_min_system._hydrated=True → running=True"
    assert result.hydrated is True
