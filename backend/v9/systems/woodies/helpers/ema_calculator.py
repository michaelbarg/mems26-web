"""EMA Calculator — local helper for B13 Vegas trail (EMA-169).

Per D-067 Hybrid boundary: compute helpers live IN Woodies module,
NOT in services/trade_manager/.

Standard EMA formula:
  alpha = 2 / (period + 1)
  Init: SMA of first <period> values, then EMA from there.

Usage:
  ema = EMACalculator(169)
  for bar in bars:
      val = ema.update(bar.close)
  current = ema.value  # cached last value
"""

from typing import Optional


class EMACalculator:
    """Exponential Moving Average calculator with session reset."""

    def __init__(self, period: int):
        if period < 1:
            raise ValueError(f"EMA period must be >= 1, got {period}")
        self.period = period
        self.alpha = 2.0 / (period + 1)
        self._values: list = []
        self._ema: Optional[float] = None
        self._count: int = 0

    @property
    def value(self) -> Optional[float]:
        """Current EMA value (None if not yet initialized)."""
        return self._ema

    @property
    def ready(self) -> bool:
        """True after at least `period` values have been fed."""
        return self._count >= self.period

    def update(self, price: float) -> Optional[float]:
        """Feed a new price and return updated EMA.

        First `period` values: accumulates for SMA seed.
        After seed: standard EMA calculation.
        Returns None until seed is complete.
        """
        self._count += 1

        if self._ema is None:
            # Accumulating for SMA seed
            self._values.append(price)
            if len(self._values) >= self.period:
                # Seed: SMA of first `period` values
                self._ema = sum(self._values) / self.period
                self._values = []  # free memory
                return self._ema
            return None

        # Standard EMA: new = price * alpha + old * (1 - alpha)
        self._ema = price * self.alpha + self._ema * (1.0 - self.alpha)
        return self._ema

    def reset(self) -> None:
        """Reset for new session. Clears all state."""
        self._values = []
        self._ema = None
        self._count = 0

    def __repr__(self) -> str:
        return f"EMACalculator(period={self.period}, value={self._ema}, count={self._count})"
