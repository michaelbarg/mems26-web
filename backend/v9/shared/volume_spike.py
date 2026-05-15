"""Volume Spike Detector — z-score method (LOCKED 16b · 2026-05-15).

Thresholds per user decision:
  z_threshold: 2.0 (option α · balanced)
  lookback: 20 bars
  skip_first_n: 6 (absorb open volatility)
  rth_only: true (09:30-16:00 ET)
  session_reset: true

Sources: TradingSim Volume Analysis 2026, TosIndicators Unusual Volume,
         BOSWaves Volumetric Trend Structure.
"""
from dataclasses import dataclass
from datetime import datetime, time
from collections import deque
from typing import Optional
import statistics


@dataclass(frozen=True)
class VolumeSpikeEvent:
    timestamp: datetime
    bar_volume: int
    rolling_mean: float
    rolling_stddev: float
    z_score: float
    is_spike: bool
    bar_index_in_session: int


class VolumeSpikeDetector:
    # LOCKED 16b constants (2026-05-15 · user decision option α)
    SPIKE_THRESHOLD = 2.0
    LOOKBACK = 20
    SKIP_FIRST_N = 6
    RTH_OPEN = time(9, 30)
    RTH_CLOSE = time(16, 0)

    def __init__(self):
        self._window: deque = deque(maxlen=self.LOOKBACK)
        self._bar_index_in_session: int = 0
        self._session_date = None

    def reset_session(self, session_date=None):
        """Reset rolling window at session start (09:30 ET each day)."""
        self._window.clear()
        self._bar_index_in_session = 0
        self._session_date = session_date

    def detect_spike(self, bar_volume: int, bar_timestamp: datetime) -> Optional[VolumeSpikeEvent]:
        """Check if bar_volume is a spike relative to rolling window.

        Returns VolumeSpikeEvent if z >= 2.0, else None.
        Returns None for non-RTH bars and first 6 bars after open.
        """
        bar_time = bar_timestamp.time() if hasattr(bar_timestamp, 'time') else bar_timestamp
        # 1. RTH check
        if not (self.RTH_OPEN <= bar_time <= self.RTH_CLOSE):
            return None

        # 2. Session bar index
        self._bar_index_in_session += 1

        # 3. Skip-first guard (absorb open volatility)
        if self._bar_index_in_session <= self.SKIP_FIRST_N:
            self._window.append(bar_volume)
            return None

        # 4. Need full window for meaningful z-score
        if len(self._window) < self.LOOKBACK:
            self._window.append(bar_volume)
            return None

        # 5. Compute z-score
        mean = statistics.mean(self._window)
        stddev = statistics.stdev(self._window)
        if stddev == 0:
            self._window.append(bar_volume)
            return None
        z = (bar_volume - mean) / stddev

        # 6. Update window AFTER computation (current bar not in its own baseline)
        self._window.append(bar_volume)

        # 7. Classify
        if z >= self.SPIKE_THRESHOLD:
            return VolumeSpikeEvent(
                timestamp=bar_timestamp,
                bar_volume=bar_volume,
                rolling_mean=round(mean, 2),
                rolling_stddev=round(stddev, 2),
                z_score=round(z, 3),
                is_spike=True,
                bar_index_in_session=self._bar_index_in_session,
            )
        return None
