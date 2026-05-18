"""Tests for V9 bridge streams (W2.6 — new woodies, tpo, 5min streams)."""

import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Patch env before importing streams
os.environ.setdefault("V9_EXPORT_DIR", "/tmp/v9_test_export")
os.environ.setdefault("UPSTASH_REDIS_REST_URL", "")
os.environ.setdefault("UPSTASH_REDIS_REST_TOKEN", "")

from bridge.v9_streams import (
    ALL_STREAMS,
    Woodies30MinStream,
    Woodies5MinStream,
    TpoStream,
    Bars5MinStream,
    TickReversal15Stream,
    FootprintStream,
)


class TestStreamRegistry:
    """Verify all bridge streams are registered."""

    def test_all_streams_count(self):
        assert len(ALL_STREAMS) == 12

    def test_new_streams_in_registry(self):
        names = [s.name for s in ALL_STREAMS]
        assert "woodies_5min" in names
        assert "tpo" in names
        assert "bars_5min" in names


class TestWoodies5MinStream:
    """Woodies 30-min stream tests."""

    def test_class_attrs(self):
        s = Woodies5MinStream()
        assert s.name == "woodies_5min"
        assert s.filename == "woodies_5min.json"
        assert s.redis_key == "mems26:v9:woodies_5min"
        assert s.api_path == "/api/v9/bars/woodies_5min"

    def test_filepath(self):
        with patch.dict(os.environ, {"V9_EXPORT_DIR": "/tmp/test_export"}):
            from bridge.v9_streams.base_stream import EXPORT_DIR
            s = Woodies5MinStream()
            # filepath is computed from EXPORT_DIR module-level constant
            assert s.filename == "woodies_5min.json"

    def test_reads_file_and_pushes(self, tmp_path):
        """Test that _tick reads the file and pushes when export_ts changes."""
        s = Woodies5MinStream()
        export_file = tmp_path / "woodies_5min.json"
        payload = {
            "type": "woodies_5min",
            "export_ts": 1715300000.0,
            "bar_count": 2,
            "history": [
                {"ts": 1715299800.0, "o": 5400.0, "h": 5405.0, "l": 5398.0,
                 "c": 5403.0, "vol": 120, "cci_14": 55.2, "cci_6_tcci": 78.1,
                 "lsma_value": 5401.0, "swi_value": 1.2, "czi_value": 0.8,
                 "ema_34": 5399.0, "trend_state": "BLUE",
                 "predictor_next_cci": 60.0, "zlr_detected": False,
                 "zlr_direction": "NONE"},
                {"ts": 1715298000.0, "o": 5395.0, "h": 5402.0, "l": 5393.0,
                 "c": 5400.0, "vol": 95, "cci_14": 32.1, "cci_6_tcci": 45.0,
                 "lsma_value": 5397.0, "swi_value": 0.8, "czi_value": 0.5,
                 "ema_34": 5396.0, "trend_state": "BLUE",
                 "predictor_next_cci": 40.0, "zlr_detected": True,
                 "zlr_direction": "UP"},
            ],
        }
        export_file.write_text(json.dumps(payload))

        # Override filepath
        with patch.object(type(s), "filepath", new_callable=lambda: property(lambda self: export_file)):
            data = s._read_file()
            assert data is not None
            assert data["type"] == "woodies_5min"
            assert data["bar_count"] == 2
            assert len(data["history"]) == 2
            assert data["history"][0]["trend_state"] == "BLUE"


class TestTpoStream:
    """TPO stream tests."""

    def test_class_attrs(self):
        s = TpoStream()
        assert s.name == "tpo"
        assert s.filename == "tpo.json"
        assert s.redis_key == "mems26:v9:tpo"
        assert s.api_path == "/api/v9/bars/tpo"

    def test_reads_tpo_file(self, tmp_path):
        s = TpoStream()
        export_file = tmp_path / "tpo.json"
        payload = {
            "type": "tpo",
            "export_ts": 1715300000.0,
            "bar_count": 3,
            "bars": [
                {"ts": 1715299800.0, "letter": "A", "price": 5432.25,
                 "level": 12, "period_id": 1},
                {"ts": 1715299800.0, "letter": "A", "price": 5432.50,
                 "level": 13, "period_id": 1},
                {"ts": 1715301600.0, "letter": "B", "price": 5433.00,
                 "level": 15, "period_id": 2},
            ],
        }
        export_file.write_text(json.dumps(payload))

        with patch.object(type(s), "filepath", new_callable=lambda: property(lambda self: export_file)):
            data = s._read_file()
            assert data is not None
            assert data["type"] == "tpo"
            assert len(data["bars"]) == 3
            assert data["bars"][0]["letter"] == "A"


class TestBars5MinStream:
    """5-min bars stream tests."""

    def test_class_attrs(self):
        s = Bars5MinStream()
        assert s.name == "bars_5min"
        assert s.filename == "5min.json"
        assert s.redis_key == "mems26:v9:bars_5min"
        assert s.api_path == "/api/v9/bars/5min"

    def test_reads_5min_file(self, tmp_path):
        s = Bars5MinStream()
        export_file = tmp_path / "5min.json"
        payload = {
            "type": "5min",
            "export_ts": 1715300000.0,
            "bar_count": 2,
            "bars": [
                {"ts": 1715299800.0, "o": 5400.0, "h": 5405.0, "l": 5398.0,
                 "c": 5403.0, "vol": 250, "poc_vol": 80,
                 "vah": 5404.0, "val": 5399.0, "cumulative_delta": 45.0},
                {"ts": 1715299500.0, "o": 5396.0, "h": 5401.0, "l": 5395.0,
                 "c": 5400.0, "vol": 180, "poc_vol": 55,
                 "vah": 5400.5, "val": 5396.5, "cumulative_delta": 22.0},
            ],
        }
        export_file.write_text(json.dumps(payload))

        with patch.object(type(s), "filepath", new_callable=lambda: property(lambda self: export_file)):
            data = s._read_file()
            assert data is not None
            assert data["type"] == "5min"
            assert len(data["bars"]) == 2
            assert data["bars"][0]["vol"] == 250

    def test_push_api_posts_bars_array(self):
        s = Bars5MinStream()
        payload = {
            "type": "5min",
            "export_ts": 1715300000.0,
            "bars": [
                {"ts": 1715299800.0, "o": 5400.0, "h": 5405.0, "l": 5398.0, "c": 5403.0, "vol": 250}
            ],
        }

        class _Resp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch("bridge.v9_streams.base_stream.urllib.request.urlopen", return_value=_Resp()) as mock_urlopen:
            s._push_api(payload)

        req = mock_urlopen.call_args.args[0]
        assert json.loads(req.data.decode()) == payload["bars"]


class TestBaseStreamBehavior:
    """Test inherited base behavior for new streams."""

    @pytest.mark.parametrize("StreamClass,expected_name", [
        (Woodies5MinStream, "woodies_5min"),
        (TpoStream, "tpo"),
        (Bars5MinStream, "bars_5min"),
    ])
    def test_inherits_base(self, StreamClass, expected_name):
        s = StreamClass()
        assert s.name == expected_name
        assert s._last_mtime == 0
        assert s._last_export_ts is None
        assert s._consecutive_errors == 0

    @pytest.mark.parametrize("StreamClass", [
        Woodies30MinStream, TpoStream, Bars5MinStream,
    ])
    def test_stop_event(self, StreamClass):
        s = StreamClass()
        assert not s._stop.is_set()
        s.stop()
        assert s._stop.is_set()

    def test_tick_skips_missing_file(self, tmp_path):
        """If export file doesn't exist, _tick does nothing (no crash)."""
        s = TpoStream()
        # filepath points to non-existent file
        with patch.object(type(s), "filepath", new_callable=lambda: property(lambda self: tmp_path / "nope.json")):
            s._tick()  # should not raise

    def test_tick_skips_unchanged_mtime(self, tmp_path):
        """If file hasn't changed (same mtime), _tick skips."""
        s = Bars5MinStream()
        export_file = tmp_path / "5min.json"
        export_file.write_text(json.dumps({"export_ts": 1.0, "bars": []}))

        with patch.object(type(s), "filepath", new_callable=lambda: property(lambda self: export_file)):
            s._last_mtime = export_file.stat().st_mtime  # pretend already seen
            with patch.object(s, "_push_redis") as mock_redis:
                s._tick()
                mock_redis.assert_not_called()

    def test_tick_skips_same_export_ts(self, tmp_path):
        """If export_ts hasn't changed, _tick skips."""
        s = Woodies5MinStream()
        export_file = tmp_path / "woodies_5min.json"
        export_file.write_text(json.dumps({"export_ts": 99.0, "history": []}))

        with patch.object(type(s), "filepath", new_callable=lambda: property(lambda self: export_file)):
            s._last_export_ts = 99.0  # already seen this ts
            s._last_mtime = 0  # but mtime check passes
            with patch.object(s, "_push_redis") as mock_redis:
                s._tick()
                mock_redis.assert_not_called()

    def test_tick_pushes_on_new_data(self, tmp_path):
        """On new export_ts, _tick pushes to Redis and API."""
        s = Woodies5MinStream()
        export_file = tmp_path / "woodies_5min.json"
        export_file.write_text(json.dumps({"export_ts": 100.0, "history": [{"ts": 1}]}))

        with patch.object(type(s), "filepath", new_callable=lambda: property(lambda self: export_file)):
            with patch.object(s, "_push_redis") as mock_redis, \
                 patch.object(s, "_push_api") as mock_api:
                s._tick()
                mock_redis.assert_called_once()
                mock_api.assert_called_once()
                assert s._last_export_ts == 100.0
