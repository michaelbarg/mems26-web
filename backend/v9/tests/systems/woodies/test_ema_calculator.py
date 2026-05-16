"""Test EMA Calculator — helper for B13 Vegas trail (EMA-169)."""
import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

from backend.v9.systems.woodies.helpers.ema_calculator import EMACalculator


def test_ema_basic_convergence():
    """EMA converges toward constant input."""
    ema = EMACalculator(10)
    for _ in range(50):
        val = ema.update(100.0)
    assert val is not None
    assert abs(val - 100.0) < 0.01, f"Expected ~100, got {val}"


def test_ema_169_convergence():
    """EMA-169 with 200 bars converges within tolerance."""
    ema = EMACalculator(169)
    # Feed 169 bars at 7400, then 31 more at 7400
    for _ in range(200):
        val = ema.update(7400.0)
    assert val is not None
    assert abs(val - 7400.0) < 0.1, f"Expected ~7400, got {val}"


def test_ema_tracks_trend():
    """EMA responds to price trend (rising prices → rising EMA)."""
    ema = EMACalculator(10)
    # Seed with 10 bars at 100
    for _ in range(10):
        ema.update(100.0)
    # Feed rising prices
    for i in range(20):
        val = ema.update(100.0 + i * 2)
    assert val is not None
    assert val > 100.0, f"EMA should be above seed, got {val}"


def test_ema_not_ready_before_period():
    """Value is None before period values are fed."""
    ema = EMACalculator(10)
    for i in range(9):
        val = ema.update(100.0 + i)
        assert val is None, f"Should be None at count {i+1}"
    assert not ema.ready


def test_ema_ready_after_period():
    """Ready flag set after period values."""
    ema = EMACalculator(10)
    for i in range(10):
        ema.update(100.0)
    assert ema.ready
    assert ema.value is not None


def test_ema_reset_clears_state():
    """Reset clears all accumulated state."""
    ema = EMACalculator(10)
    for _ in range(20):
        ema.update(100.0)
    assert ema.value is not None
    ema.reset()
    assert ema.value is None
    assert not ema.ready
    assert ema._count == 0


def test_ema_sma_seed_correct():
    """SMA seed = average of first N values."""
    ema = EMACalculator(5)
    prices = [10.0, 20.0, 30.0, 40.0, 50.0]
    for p in prices[:4]:
        ema.update(p)
    val = ema.update(prices[4])  # 5th value triggers seed
    expected_sma = sum(prices) / 5  # = 30.0
    assert val == expected_sma, f"Expected SMA seed {expected_sma}, got {val}"


def test_ema_period_1_equals_price():
    """EMA(1) should equal the latest price."""
    ema = EMACalculator(1)
    val = ema.update(42.0)
    assert val == 42.0
    val = ema.update(99.0)
    assert val == 99.0


if __name__ == "__main__":
    test_ema_basic_convergence()
    test_ema_169_convergence()
    test_ema_tracks_trend()
    test_ema_not_ready_before_period()
    test_ema_ready_after_period()
    test_ema_reset_clears_state()
    test_ema_sma_seed_correct()
    test_ema_period_1_equals_price()
    print("✅ All 8 EMA tests passed")
