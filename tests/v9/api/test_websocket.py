"""Tests: V9 WebSocket endpoints — connection, auth, snapshot, heartbeat."""

import time
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.v9.db.session import Base, get_db
from backend.v9.db.models import *  # noqa: F401,F403
from backend.v9.app import app

# In-memory SQLite for tests
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(TEST_ENGINE, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSession = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)

TOKEN = "michael-mems26-2026"


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def client():
    def _override():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override

    # Patch SessionLocal in websocket module to use test DB
    with patch(
        "backend.v9.api.v9.websocket.SessionLocal", TestSession
    ):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


# Mock Redis publish to avoid needing Redis in tests
@pytest.fixture(autouse=True)
def mock_redis():
    with patch("backend.v9.api.v9.ws_manager.get_redis_client"):
        with patch("backend.v9.api.v9.ws_manager.publish_event"):
            yield


class TestWSConnection:
    """Test WebSocket connection and auth."""

    def test_ws_bars_5min_connects(self, client):
        with client.websocket_connect(f"/ws/v9/bars/5min?token={TOKEN}") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "snapshot"
            assert msg["channel"] == "v9:bars:5min"
            assert isinstance(msg["data"], list)

    def test_ws_tick_reversal_connects(self, client):
        with client.websocket_connect(
            f"/ws/v9/bars/tick_reversal?token={TOKEN}"
        ) as ws:
            msg = ws.receive_json()
            assert msg["type"] == "snapshot"
            assert msg["channel"] == "v9:bars:tick_reversal"

    def test_ws_woodies_connects(self, client):
        with client.websocket_connect(
            f"/ws/v9/bars/woodies?token={TOKEN}"
        ) as ws:
            msg = ws.receive_json()
            assert msg["type"] == "snapshot"
            assert msg["channel"] == "v9:bars:woodies"

    def test_ws_tpo_connects(self, client):
        with client.websocket_connect(
            f"/ws/v9/bars/tpo?token={TOKEN}"
        ) as ws:
            msg = ws.receive_json()
            assert msg["type"] == "snapshot"
            assert msg["channel"] == "v9:bars:tpo"

    def test_ws_markers_connects(self, client):
        with client.websocket_connect(f"/ws/v9/markers/3?token={TOKEN}") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "snapshot"
            assert msg["channel"] == "v9:markers:3"

    def test_ws_signals_connects(self, client):
        with client.websocket_connect(f"/ws/v9/signals/1?token={TOKEN}") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "snapshot"
            assert msg["channel"] == "v9:signals:1"

    def test_ws_trades_connects(self, client):
        with client.websocket_connect(f"/ws/v9/trades?token={TOKEN}") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "snapshot"
            assert msg["channel"] == "v9:trades"

    def test_ws_account_connects(self, client):
        with client.websocket_connect(f"/ws/v9/account?token={TOKEN}") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "snapshot"
            assert msg["channel"] == "v9:account"

    def test_ws_levels_connects(self, client):
        with client.websocket_connect(f"/ws/v9/levels?token={TOKEN}") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "snapshot"
            assert msg["channel"] == "v9:levels"


class TestWSAuth:
    """Test WebSocket authentication."""

    def test_ws_no_token_rejected(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/v9/bars/5min?token=") as ws:
                ws.receive_json()

    def test_ws_bad_token_rejected(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect(
                "/ws/v9/bars/5min?token=wrong-token"
            ) as ws:
                ws.receive_json()


class TestWSPingPong:
    """Test client can send ping and receive pong."""

    def test_ping_pong(self, client):
        with client.websocket_connect(f"/ws/v9/bars/5min?token={TOKEN}") as ws:
            # Receive snapshot first
            msg = ws.receive_json()
            assert msg["type"] == "snapshot"

            # Send ping
            ws.send_text("ping")
            pong = ws.receive_json()
            assert pong["type"] == "pong"
            assert "ts" in pong


class TestWSSnapshotWithData:
    """Test snapshot returns data when DB has records."""

    def test_snapshot_has_bars(self, client):
        from datetime import datetime, timezone
        from backend.v9.db.models import V9Bar5Min

        # Insert a bar
        session = TestSession()
        bar = V9Bar5Min(
            ts=datetime(2026, 5, 10, 14, 30, tzinfo=timezone.utc),
            symbol="MES", open=5412.50, high=5415.00,
            low=5410.25, close=5411.00, volume=1234,
        )
        session.add(bar)
        session.commit()
        session.close()

        with client.websocket_connect(f"/ws/v9/bars/5min?token={TOKEN}") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "snapshot"
            assert len(msg["data"]) == 1
            assert msg["data"][0]["o"] == 5412.50

    def test_snapshot_trades(self, client):
        from datetime import datetime, timezone
        from backend.v9.db.models import V9Trade

        session = TestSession()
        trade = V9Trade(
            mode="SHADOW", firing_system=1, direction="LONG",
            entry_ts=datetime(2026, 5, 10, 14, 30, tzinfo=timezone.utc),
            entry_price=5412.50,
        )
        session.add(trade)
        session.commit()
        session.close()

        with client.websocket_connect(f"/ws/v9/trades?token={TOKEN}") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "snapshot"
            assert len(msg["data"]) == 1
            assert msg["data"][0]["entry_price"] == 5412.50
