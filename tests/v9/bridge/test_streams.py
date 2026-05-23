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
    CumulativeDeltaStream,
)
from bridge import json_bridge


class TestStreamRegistry:
    """Verify all bridge streams are registered."""

    def test_all_streams_count(self):
        assert len(ALL_STREAMS) == 12

    def test_new_streams_in_registry(self):
        names = [s.name for s in ALL_STREAMS]
        assert "woodies_5min" in names
        assert "tpo" in names
        assert "bars_5min" in names

    def test_default_selects_all_streams(self):
        assert json_bridge.select_streams([]) == ALL_STREAMS

    def test_bars_5min_only_flag_selects_single_stream(self):
        selected = json_bridge.select_streams(["--bars-5min-only"])
        names = {s.name for s in selected}
        assert names == {"bars_5min"}

    def test_cockpit_minimal_streams(self):
        selected = json_bridge.select_streams(["--cockpit-minimal"])
        names = {s.name for s in selected}
        assert names == {"bars_5min", "woodies_5min"}

    def test_streams_arg_selects_named_streams(self):
        selected = json_bridge.select_streams(["--streams=bars_5min,live_price"])
        assert [s.name for s in selected] == ["bars_5min", "live_price"]

    def test_unknown_stream_exits_with_available_names(self):
        with pytest.raises(SystemExit) as exc:
            json_bridge.select_streams(["--streams=does_not_exist"])
        assert "Unknown stream(s): does_not_exist" in str(exc.value)


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

    def test_push_api_posts_latest_bar_array(self):
        s = Bars5MinStream()
        payload = {
            "type": "5min",
            "export_ts": 1715300000.0,
            "bars": [
                {"ts": 1715299500.0, "o": 5396.0, "h": 5401.0, "l": 5395.0, "c": 5400.0, "vol": 180},
                {"ts": 1715299800.0, "o": 5400.0, "h": 5405.0, "l": 5398.0, "c": 5403.0, "vol": 250},
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
        assert json.loads(req.data.decode()) == [payload["bars"][-1]]


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


# ── P31 §A: CVD `points[].t` Chicago→UTC fix ─────────────────────────────

class TestCumulativeDeltaChicagoTsFix:
    """Regression for the P31 §A bug: the §9 bridge workaround rewrites
    `bars[].ts` / `history[].ts` etc. but NOT `points[].t` (different field
    name AND different container). CVD points kept Chicago-wall-clock-as-UTC
    encoding → frontend CVD candles rendered ~5h behind the price bars on the
    shared chart timeScale. Override in CumulativeDeltaStream must also touch
    `points[].t`.
    """

    def test_class_attrs(self):
        s = CumulativeDeltaStream()
        assert s.name == "cumulative_delta"
        assert s.filename == "cumulative_delta.json"

    def test_fix_chicago_bar_ts_rewrites_points_t(self, monkeypatch):
        """Points with `t` field must be converted from Chicago→UTC."""
        # Force the workaround on regardless of env.
        monkeypatch.setattr(
            "bridge.v9_streams.base_stream._DISABLE_CHICAGO_TS_FIX", False
        )
        s = CumulativeDeltaStream()
        # A Chicago-wall-clock unix value (10:00 Chicago encoded as UTC).
        # Real meaning is 10:00 CDT = 15:00 UTC; bug stores it as if it were
        # 10:00 UTC = 1779360000.
        chicago_encoded = 1779360000
        data = {
            "type": "cumulative_delta",
            "export_ts": 1779360000.0,
            "points": [
                {"i": 1, "t": chicago_encoded, "d": 10.0, "cum": 10.0, "p": 7430.0},
                {"i": 2, "t": chicago_encoded + 300, "d": -5.0, "cum": 5.0, "p": 7429.0},
            ],
        }

        fixed = s._fix_chicago_bar_ts(data)

        # Every point's `t` should be shifted forward by the Chicago offset
        # (4h CDT for May or 5h CST), so the new value must be > original.
        for pt in fixed["points"]:
            assert pt["t"] > chicago_encoded, (
                f"point.t={pt['t']} not shifted from Chicago-encoded "
                f"{chicago_encoded}; check _chicago_to_utc()"
            )
        # The two points must still be 300s apart after the shift.
        assert fixed["points"][1]["t"] - fixed["points"][0]["t"] == 300

    def test_fix_chicago_bar_ts_preserves_other_fields(self, monkeypatch):
        """Non-`t` fields on each point must pass through unchanged."""
        monkeypatch.setattr(
            "bridge.v9_streams.base_stream._DISABLE_CHICAGO_TS_FIX", False
        )
        s = CumulativeDeltaStream()
        data = {
            "type": "cumulative_delta",
            "export_ts": 1779360000.0,
            "points": [
                {"i": 7, "t": 1779360000, "d": 12.5, "cum": 99.5, "p": 7430.75},
            ],
        }
        fixed = s._fix_chicago_bar_ts(data)
        pt = fixed["points"][0]
        assert pt["i"] == 7
        assert pt["d"] == 12.5
        assert pt["cum"] == 99.5
        assert pt["p"] == 7430.75

    def test_fix_chicago_bar_ts_no_op_when_disabled(self, monkeypatch):
        """`V9_DISABLE_CHICAGO_TS_FIX=1` must short-circuit the fix so the DLL
        canonical fix (§9 Option A) can ship without bridge churn.
        """
        monkeypatch.setattr(
            "bridge.v9_streams.base_stream._DISABLE_CHICAGO_TS_FIX", True
        )
        s = CumulativeDeltaStream()
        original_t = 1779360000
        data = {
            "type": "cumulative_delta",
            "points": [{"i": 1, "t": original_t, "d": 0.0, "cum": 0.0, "p": 7400.0}],
        }
        fixed = s._fix_chicago_bar_ts(data)
        assert fixed["points"][0]["t"] == original_t

    def test_fix_chicago_bar_ts_tolerates_missing_points(self, monkeypatch):
        """Payload without `points` (or non-list) must not crash."""
        monkeypatch.setattr(
            "bridge.v9_streams.base_stream._DISABLE_CHICAGO_TS_FIX", False
        )
        s = CumulativeDeltaStream()
        # No `points` key
        data1 = {"type": "cumulative_delta", "export_ts": 1.0}
        assert s._fix_chicago_bar_ts(data1) is data1
        # `points` is not a list
        data2 = {"type": "cumulative_delta", "points": "oops"}
        assert s._fix_chicago_bar_ts(data2) is data2
        # `points` is list of non-dicts
        data3 = {"type": "cumulative_delta", "points": [1, 2, 3]}
        assert s._fix_chicago_bar_ts(data3) is data3
        # `points` items missing `t` key
        data4 = {"type": "cumulative_delta", "points": [{"i": 1, "d": 0.0}]}
        result = s._fix_chicago_bar_ts(data4)
        assert result["points"][0] == {"i": 1, "d": 0.0}

    def test_fix_chicago_bar_ts_also_rewrites_bars_ts(self, monkeypatch):
        """Regression — the base class behavior for `bars[].ts` must still
        apply even though we overrode the hook (we call ``super()`` first).
        """
        monkeypatch.setattr(
            "bridge.v9_streams.base_stream._DISABLE_CHICAGO_TS_FIX", False
        )
        s = CumulativeDeltaStream()
        original_ts = 1779360000
        data = {
            "type": "cumulative_delta",
            "bars": [{"ts": original_ts, "o": 7400.0}],
            "points": [{"i": 1, "t": original_ts, "d": 0.0, "cum": 0.0, "p": 7400.0}],
        }
        fixed = s._fix_chicago_bar_ts(data)
        assert fixed["bars"][0]["ts"] > original_ts
        assert fixed["points"][0]["t"] > original_ts
