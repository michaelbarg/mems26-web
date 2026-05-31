"""S3 Golden Regression — flag OFF must reproduce original absolute thresholds."""

import json
from pathlib import Path

GOLDEN = Path(__file__).parent / "golden" / "s3_constants.json"


def _load_golden():
    with GOLDEN.open() as f:
        return json.load(f)


def test_stacked_imbalance_constants():
    from backend.v9.systems.footprint.signals.stacked_imbalance import (
        STACK_N, IMB_THRESHOLD, MIN_LEVEL_VOL,
    )
    g = _load_golden()["stacked_imbalance"]
    assert STACK_N == g["STACK_N"]
    assert IMB_THRESHOLD == g["IMB_THRESHOLD"]
    assert MIN_LEVEL_VOL == g["MIN_LEVEL_VOL"]


def test_detectors_context_defaults():
    """analyze_context default params match golden."""
    import inspect
    from backend.v9.systems.footprint.detectors import analyze_context
    sig = inspect.signature(analyze_context)
    g = _load_golden()["detectors"]
    assert sig.parameters["range_ticks"].default == g["range_ticks"]
    assert sig.parameters["min_acc_bars"].default == g["min_acc_bars"]


def test_stacked_imbalance_functional():
    """Known input → deterministic output (flag OFF baseline)."""
    from backend.v9.systems.footprint.signals.stacked_imbalance import detect_stacked_imbalance
    levels = [
        {"price": 5200.0 + i * 0.25, "ask_vol": 30, "bid_vol": 10}
        for i in range(5)
    ]
    bar = {"c": 5201.0}
    result = detect_stacked_imbalance(levels, bar)
    assert result is not None
    assert result["direction"] == "LONG"
    assert result["evidence"]["stack_count"] >= 3


def test_analyze_context_functional():
    """Known accumulation range → deterministic output."""
    from backend.v9.systems.footprint.detectors import analyze_context
    bars = [{"high": 5201.0, "low": 5200.0, "close": 5200.5, "open": 5200.3}] * 6
    result = analyze_context(bars, min_acc_bars=5, range_ticks=15.0)
    assert result.accumulation is True
    assert result.bars_in_range >= 5
