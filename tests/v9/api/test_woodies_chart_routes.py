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


def test_load_sierra_woodies_tail_limit(tmp_path):
    path = tmp_path / "woodies_5min.json"
    path.write_text(json.dumps(_sample_export()))
    loaded = woodies_chart_routes._load_sierra_woodies(path, max_age_s=60)
    assert loaded is not None
    assert loaded["source"] == "sierra_woodies_5min_json"
    assert len(loaded["bars"]) == 41
    assert loaded["current_bar"]["cci_14"] == 12.5


def test_load_sierra_woodies_rejects_stale(tmp_path):
    path = tmp_path / "woodies_5min.json"
    path.write_text(json.dumps(_sample_export()))
    old = time.time() - 120
    import os

    os.utime(path, (old, old))
    assert woodies_chart_routes._load_sierra_woodies(path, max_age_s=1) is not None
    assert woodies_chart_routes._load_sierra_woodies(path, max_age_s=1)["stale"] is True
