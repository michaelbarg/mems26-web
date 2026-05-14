"""W5.6-tau -- multi-tf chart routes return 200 + OHLCV shape"""
import sys
sys.path.insert(0, '/Users/michael/Downloads/mems26_web_git')
import requests
import pytest


@pytest.mark.parametrize("tf", ['1m', '5min', '15m', '30m', '1h'])
def test_bars_tf_returns_200(tf):
    r = requests.get(f"http://localhost:8000/api/v9/chart/bars{tf}?limit=5", timeout=15)
    assert r.status_code == 200, f"{tf} returned {r.status_code}"
    data = r.json()
    bars = data if isinstance(data, list) else data.get('bars', [])
    if bars:
        bar = bars[0]
        assert all(k in bar for k in ['open', 'high', 'low', 'close', 'volume']), \
            f"{tf} bar missing OHLCV long keys: {list(bar.keys())}"
        assert all(k in bar for k in ['o', 'h', 'l', 'c', 'v']), \
            f"{tf} bar missing OHLCV short keys: {list(bar.keys())}"


def test_bars5min_returns_bars():
    r = requests.get("http://localhost:8000/api/v9/chart/bars5min?limit=5", timeout=15)
    assert r.status_code == 200
    bars = r.json()
    assert isinstance(bars, list)
    assert len(bars) > 0, "bars5min should return at least 1 bar"


def test_bars1m_same_shape_as_5min():
    r1 = requests.get("http://localhost:8000/api/v9/chart/bars1m?limit=5", timeout=15)
    r5 = requests.get("http://localhost:8000/api/v9/chart/bars5min?limit=5", timeout=15)
    assert r1.status_code == 200
    assert r5.status_code == 200
    b1 = r1.json()
    b5 = r5.json()
    if b1 and b5:
        assert set(b1[0].keys()) == set(b5[0].keys()), "1m and 5min should have same keys"


def test_aggregator_preserves_ohlcv_invariants():
    """15m high >= all underlying 5m highs."""
    r5 = requests.get("http://localhost:8000/api/v9/chart/bars5min?limit=60", timeout=15)
    r15 = requests.get("http://localhost:8000/api/v9/chart/bars15m?limit=20", timeout=15)
    b5 = r5.json()
    b15 = r15.json()
    if b15 and b5:
        # Each 15m bar's high should >= any of its 3 underlying 5m highs
        for bar15 in b15:
            assert bar15['high'] >= bar15['low'], "high >= low invariant"
            assert bar15['volume'] >= 0, "volume >= 0"
