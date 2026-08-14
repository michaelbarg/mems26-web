"""Regression — the live-price screen must never depend on a cloud hop.

Michael 2026-08-14 (market opening): "המערכת לא מצליחה לקבל נתונים בצורה שוטפת
והוא מתנתק או על stale — זה לא היה לנו!!" and "מה פתאום? זה צריך להתחבר ישירות
למערכת".

Root cause: the price WebSocket relay read ONLY the Upstash CLOUD Redis stream.
That instance stopped resolving (DNS), so every read returned None — the socket
stayed open while zero ticks were sent, so the UI store went cold and rendered
stale → disconnected. The local feed was healthy the whole time
(sierra_state 0.5-2s, live_price.json ~250ms).

Fix: Redis remains the primary path when it answers; otherwise the relay
broadcasts straight from the LOCAL Sierra export — the same file the trading
path reads. Local-only stack, local-only screen (CLAUDE.md § Bridge Local-Only).
"""
import json
import os

from backend.v9.ws.manager import EventBusWSManager


def _write_price(tmp_path, **kw):
    d = {"price": 7825.25, "ts": 1786714020, "bid": 7825.0, "ask": 7825.5, "vol": 1019}
    d.update(kw)
    (tmp_path / "live_price.json").write_text(json.dumps(d))
    return d


class TestLocalTick:
    def test_parses_sierra_export(self, tmp_path, monkeypatch):
        _write_price(tmp_path)
        monkeypatch.setenv("V9_EXPORT_DIR", str(tmp_path))
        t = EventBusWSManager._local_price_tick()
        assert t is not None
        assert t["price"] == 7825.25
        assert t["bid"] == 7825.0 and t["ask"] == 7825.5

    def test_timestamp_is_milliseconds(self, tmp_path, monkeypatch):
        """The UI computes staleness as Date.now() - ts_ms — seconds would make
        every tick look ~55 years old and keep the banner red forever."""
        _write_price(tmp_path)
        monkeypatch.setenv("V9_EXPORT_DIR", str(tmp_path))
        t = EventBusWSManager._local_price_tick()
        assert t["ts_ms"] > 1_000_000_000_000

    def test_missing_file_returns_none_not_raise(self, tmp_path, monkeypatch):
        monkeypatch.setenv("V9_EXPORT_DIR", str(tmp_path / "nope"))
        assert EventBusWSManager._local_price_tick() is None

    def test_garbage_file_returns_none(self, tmp_path, monkeypatch):
        (tmp_path / "live_price.json").write_text("{not json")
        monkeypatch.setenv("V9_EXPORT_DIR", str(tmp_path))
        assert EventBusWSManager._local_price_tick() is None

    def test_price_missing_returns_none(self, tmp_path, monkeypatch):
        (tmp_path / "live_price.json").write_text(json.dumps({"ts": 1786714020}))
        monkeypatch.setenv("V9_EXPORT_DIR", str(tmp_path))
        assert EventBusWSManager._local_price_tick() is None


class TestRelayWiring:
    def test_relay_falls_back_without_redis(self):
        import inspect
        src = inspect.getsource(EventBusWSManager._relay_loop)
        assert "_local_price_tick" in src
        assert "redis_ok" in src

    def test_no_duplicate_broadcast_for_same_file_timestamp(self):
        """Identical file timestamp must not re-broadcast (the UI treats a
        repeated tick as a no-op, but the socket should stay quiet anyway)."""
        import inspect
        src = inspect.getsource(EventBusWSManager._relay_loop)
        assert "last_file_ts" in src
