import json
import time

from backend.v9.api.v9 import woodies_chart_routes


def _sample_export():
    return {
        "type": "woodies_5min",
        "version": "v9.4.0-p30.10",
        "export_ts": int(time.time()),
        "history": [
            {
                "ts": 1779180000 + i * 300,
                "ohlc": {"o": 7400, "h": 7401, "l": 7399, "c": 7400, "vol": 100},
                "cci_14": -50.0 + i,
                "cci_6_tcci": -40.0 + i,
                "trend_state": "YELLOW",
                "zlr_detected": False,
                "zlr_direction": "NONE",
            }
            for i in range(40)
        ],
        "current_bar": {
            "ts": 1779180000 + 40 * 300,
            "ohlc": {"o": 7410, "h": 7411, "l": 7409, "c": 7410, "vol": 200},
            "cci_14": 12.5,
            "cci_6_tcci": 8.0,
            "trend_state": "BLUE",
            "zlr_detected": True,
            "zlr_direction": "UP",
        },
    }


def test_normalize_bar_requires_cci():
    assert woodies_chart_routes._normalize_bar({"ts": 1}) is None
    bar = woodies_chart_routes._normalize_bar(
        {"ts": 1779180000, "cci_14": 100.0, "trend_state": "RED"}
    )
    assert bar["cci_14"] == 100.0
    assert bar["trend_color"] == "#E03030"


def test_normalize_bar_ohlc_and_predictor():
    bar = woodies_chart_routes._normalize_bar(
        {
            "ts": 1779180000,
            "cci_14": 12.5,
            "cci_6_tcci": 8.0,
            "ccidiff_h": 55.0,
            "ccidiff_l": 44.0,
            "trend_state": "BLUE",
            "ohlc": {"o": 7410, "h": 7411, "l": 7409, "c": 7410},
            "predictor_next_cci": -14.12,
            "predictor_cci_high": 18.1,
            "predictor_cci_low": 12.0,
        }
    )
    assert bar["high"] == 7411.0
    assert bar["low"] == 7409.0
    assert bar["close"] == 7410.0
    assert bar["predictor_next_cci"] == -14.12
    assert bar["ccidiff_h"] == 55.0
    assert bar["predictor_cci_high"] == 18.1
    assert bar["ccidiff"] == 4.5


def test_normalize_bar_hud_fields_and_prev_ohlc():
    bar = woodies_chart_routes._normalize_bar(
        {
            "ts": 1779180000,
            "cci_14": 55.0,
            "cci_6_tcci": 12.0,
            "ccidiff": 43.0,
            "ccidiff_h": 50.0,
            "ccidiff_l": 40.0,
            "predictor_cci_high": 18.1,
            "predictor_cci_low": 17.5,
            "proj_hi": 7667.0,
            "proj_lo": 7074.75,
            "low_prev_angle": -67.7,
            "ohlc": {"o": 7400, "h": 7411, "l": 7399, "c": 7410},
            "prev_ohlc": {"o": 7390, "h": 7405, "l": 7388, "c": 7402},
            "trend_state": "BLUE",
        }
    )
    assert bar["ccidiff"] == 43.0
    assert bar["ccidiff_h"] == 50.0
    assert bar["ccidiff_l"] == 40.0
    assert bar["predictor_cci_high"] == 18.1
    assert bar["predictor_cci_low"] == 17.5
    assert bar["proj_hi"] == 7667.0
    assert bar["proj_lo"] == 7074.75
    assert bar["low_prev_angle"] == -67.7
    assert bar["prev_high"] == 7405.0
    assert bar["prev_low"] == 7388.0


def test_normalize_bar_ccidiff_from_cci_minus_tcci():
    bar = woodies_chart_routes._normalize_bar(
        {"ts": 1, "cci_14": 55.19, "cci_6_tcci": 0.0, "trend_state": "GRAY"}
    )
    assert bar["ccidiff"] == 55.19


def test_enrich_keeps_export_proj_values():
    """Sierra export's proj_hi/proj_lo must pass through untouched."""
    bars = [
        {"high": 100.0, "low": 90.0},
        {"high": 101.0, "low": 91.0, "proj_hi": 5000.0, "proj_lo": 4000.0},
    ]
    woodies_chart_routes._enrich_bar_projections(bars[1], bars)
    assert bars[1]["proj_hi"] == 5000.0
    assert bars[1]["proj_lo"] == 4000.0


def test_enrich_never_invents_proj_when_missing():
    """Regression: backend must NEVER synthesise proj_hi/proj_lo from rolling
    High/Low — that produced shifting values like 7702.75 vs 7408.25 every
    request. ProjHi/Lo come only from Sierra DLL Pivot Points subgraphs.
    """
    bars = [
        {"high": 100.0, "low": 90.0},
        {"high": 105.0, "low": 88.0},
    ]
    woodies_chart_routes._enrich_bar_projections(bars[1], bars)
    assert "proj_hi" not in bars[1]
    assert "proj_lo" not in bars[1]


def test_enrich_preserves_export_low_prev_angle():
    bars = [
        {"low": 7366.75},
        {"low": 7356.75, "low_prev_angle": 20.56},
    ]
    woodies_chart_routes._enrich_bar_projections(bars[1], bars)
    assert bars[1]["low_prev_angle"] == 20.56


def test_enrich_low_prev_angle_from_price_lows():
    bars = [
        {"low": 7366.75},
        {"low": 7356.75},
    ]
    woodies_chart_routes._enrich_bar_projections(bars[1], bars)
    assert bars[1]["low_prev_angle"] == -78.7


def test_attach_prev_ohlc_from_window():
    cur = {"high": 7411.0, "low": 7409.0}
    prev = {"high": 7405.0, "low": 7388.0, "open": 7390.0, "close": 7402.0}
    woodies_chart_routes._attach_prev_ohlc_from_window(cur, prev)
    assert cur["prev_high"] == 7405.0
    assert cur["prev_low"] == 7388.0


def test_parse_replaces_tail_when_current_bar_same_ts():
    """Building bar: current_bar OHLC/CCI must win over stale history tail."""
    export = {
        "history": [
            {
                "ts": 1779200000,
                "cci_14": 10.0,
                "cci_6_tcci": 5.0,
                "trend_state": "GRAY",
                "ohlc": {"o": 7400, "h": 7401, "l": 7399, "c": 7400},
            }
        ],
        "current_bar": {
            "ts": 1779200000,
            "cci_14": 99.0,
            "cci_6_tcci": 50.0,
            "trend_state": "BLUE",
            "ohlc": {"o": 7400, "h": 7410, "l": 7398, "c": 7409.5},
            "ccidiff_h": 1.0,
            "ccidiff_l": 2.0,
        },
    }
    parsed = woodies_chart_routes._parse_sierra_payload(export, age_s=1.0)
    assert len(parsed["bars"]) == 1
    tail = parsed["bars"][0]
    assert tail["cci_14"] == 99.0
    assert tail["close"] == 7409.5
    assert tail["ccidiff_h"] == 1.0
    assert parsed["current_bar"] is tail


def test_parse_ts_bug_replaces_tail_not_append():
    """When DLL stamps every row with export ts, live current replaces history tail."""
    ts = 1779466862
    export = {
        "history": [
            {
                "ts": ts,
                "cci_14": float(30 + i),
                "cci_6_tcci": 0.0,
                "trend_state": "GRAY",
                "ohlc": {"o": 7500, "h": 7501, "l": 7499, "c": 7500},
            }
            for i in range(5)
        ],
        "current_bar": {
            "ts": ts,
            "cci_14": 162.3,
            "cci_6_tcci": 82.0,
            "trend_state": "BLUE",
            "ohlc": {"o": 7500, "h": 7510, "l": 7498, "c": 7509},
        },
    }
    parsed = woodies_chart_routes._parse_sierra_payload(export, age_s=1.0)
    assert len(parsed["bars"]) == 5
    tail = parsed["bars"][-1]
    assert tail["cci_14"] == 162.3
    assert tail["close"] == 7509.0
    assert parsed["current_bar"] is tail


def test_current_bar_is_enriched_tail_not_raw_normalize():
    export = _sample_export()
    parsed = woodies_chart_routes._parse_sierra_payload(export, age_s=1.0)
    tail = parsed["bars"][-1]
    cur = parsed["current_bar"]
    assert cur is tail
    assert cur.get("ccidiff") is not None
    assert cur.get("prev_high") is not None


def test_load_sierra_woodies_applies_hud_from_export(tmp_path):
    path = tmp_path / "woodies_5min.json"
    export = _sample_export()
    export["current_bar"].update(
        {
            "ccidiff": 43.0,
            "ccidiff_h": 50.0,
            "ccidiff_l": 40.0,
            "proj_hi": 7667.0,
            "proj_lo": 7074.75,
            "predictor_cci_high": 18.1,
            "predictor_cci_low": 17.5,
            "low_prev_angle": -67.7,
            "prev_ohlc": {"o": 7390, "h": 7405, "l": 7388, "c": 7402},
        }
    )
    path.write_text(json.dumps(export))
    loaded = woodies_chart_routes._load_sierra_woodies(path, max_age_s=60)
    cur = loaded["current_bar"]
    assert cur["proj_hi"] == 7667.0
    assert cur["ccidiff_h"] == 50.0
    assert cur["prev_high"] == 7405.0
    assert cur["low_prev_angle"] == -67.7


def test_parse_sierra_payload_study_caption_default():
    export = _sample_export()
    export["bar_period_minutes"] = 5
    parsed = woodies_chart_routes._parse_sierra_payload(export, age_s=1.0)
    assert "study_caption" in parsed
    assert "6, 5, 14, 100" in parsed["study_caption"]
    assert "5m" in parsed["study_caption"]


def test_load_sierra_woodies_tail_limit(tmp_path):
    path = tmp_path / "woodies_5min.json"
    path.write_text(json.dumps(_sample_export()))
    loaded = woodies_chart_routes._load_sierra_woodies(path, max_age_s=60)
    assert loaded is not None
    assert loaded["source"] == "sierra_woodies_5min_json"
    assert len(loaded["bars"]) == 41
    assert loaded["current_bar"]["cci_14"] == 12.5


def test_four_uat_axes_on_parsed_export(tmp_path):
    """Quality / recency / cardinality / latency proxy on normalized payload."""
    path = tmp_path / "woodies_5min.json"
    export = _sample_export()
    export["current_bar"].update(
        {
            "ccidiff_h": 50.0,
            "ccidiff_l": 40.0,
            "proj_hi": 7667.0,
            "proj_lo": 7074.75,
            "predictor_cci_high": 18.1,
            "predictor_cci_low": 17.5,
            "low_prev_angle": -67.7,
            "prev_ohlc": {"o": 7390, "h": 7405, "l": 7388, "c": 7402},
        }
    )
    path.write_text(json.dumps(export))
    t0 = time.time()
    loaded = woodies_chart_routes._load_sierra_woodies(path, max_age_s=60)
    latency_ms = (time.time() - t0) * 1000
    limit = 30
    tail = (loaded["bars"] or [])[-limit:]
    cur = loaded["current_bar"]
    assert cur["ccidiff_h"] == 50.0
    assert cur["prev_high"] == 7405.0
    assert tail[-1]["ts_unix"] == cur["ts_unix"]
    assert len(tail) == min(limit, len(loaded["bars"]))
    assert latency_ms < 500


def test_load_sierra_woodies_rejects_stale(tmp_path):
    path = tmp_path / "woodies_5min.json"
    path.write_text(json.dumps(_sample_export()))
    old = time.time() - 120
    import os

    os.utime(path, (old, old))
    assert woodies_chart_routes._load_sierra_woodies(path, max_age_s=1) is not None
    assert woodies_chart_routes._load_sierra_woodies(path, max_age_s=1)["stale"] is True
