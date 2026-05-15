"""CVD Context Classifier — 8-state system-wide context layer (LOCKED 16c · 2026-05-15).

Classifies CVD vs Price behavior into 8 states consumed by:
  System 1 (Day Type) · System 2 (5-min) · System 3 (Footprint)

Update frequency: every 5-min bar close.

Sources: Bookmap CVD, XS CVD, ZitaPlus CVD Divergence, LuxAlgo CVD Explained.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class CVDState(str, Enum):
    CONFIRMATION_BULL = "confirmation_bull"
    CONFIRMATION_BEAR = "confirmation_bear"
    DIVERGENCE_BULL = "divergence_bull"
    DIVERGENCE_BEAR = "divergence_bear"
    ABSORPTION_BULL = "absorption_bull"
    ABSORPTION_BEAR = "absorption_bear"
    MECHANICAL = "mechanical"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class CVDContextEvent:
    timestamp: datetime
    state: CVDState
    price_delta_bar: float
    cvd_value: float
    cvd_slope: float
    has_volume_spike: bool
    reasoning: str


class CVDContextClassifier:
    """Classifies CVD context into one of 8 states.

    Thresholds LOCKED 16c (2026-05-15):
      FLAT_PRICE_THRESHOLD: 0.25 pt (MES tick)
      FLAT_CVD_SLOPE_THRESHOLD: 50 (delta units per bar)
      ABSORPTION_CVD_SLOPE_MIN: 200 (aggressive flow)
    """
    # LOCKED 16c constants
    FLAT_PRICE_THRESHOLD = 0.25   # MES tick size
    FLAT_CVD_SLOPE_THRESHOLD = 50  # delta units per bar
    ABSORPTION_CVD_SLOPE_MIN = 200  # aggressive directional flow

    def classify(
        self,
        timestamp: datetime,
        price_delta_bar: float,
        cvd_value: float,
        cvd_slope: float,
        has_volume_spike: bool = False,
    ) -> CVDContextEvent:
        """Classify current bar's CVD context.

        Args:
            timestamp: bar close time
            price_delta_bar: close - open of current bar (signed)
            cvd_value: current cumulative delta value
            cvd_slope: CVD change over last bar (signed)
            has_volume_spike: True if VolumeSpikeDetector fired on this bar
        """
        price_up = price_delta_bar > self.FLAT_PRICE_THRESHOLD
        price_down = price_delta_bar < -self.FLAT_PRICE_THRESHOLD
        price_flat = not price_up and not price_down

        cvd_up = cvd_slope > self.FLAT_CVD_SLOPE_THRESHOLD
        cvd_down = cvd_slope < -self.FLAT_CVD_SLOPE_THRESHOLD
        cvd_flat = not cvd_up and not cvd_down

        cvd_aggressive_up = cvd_slope > self.ABSORPTION_CVD_SLOPE_MIN
        cvd_aggressive_down = cvd_slope < -self.ABSORPTION_CVD_SLOPE_MIN

        state = CVDState.NEUTRAL
        reasoning = "no clear pattern"

        # Priority order per spec
        if has_volume_spike and cvd_flat:
            state = CVDState.MECHANICAL
            reasoning = "spike with flat CVD · mechanical"
        elif price_flat and cvd_aggressive_down and has_volume_spike:
            state = CVDState.ABSORPTION_BULL
            reasoning = "CVD down aggressively but price flat · sellers absorbed"
        elif price_flat and cvd_aggressive_up and has_volume_spike:
            state = CVDState.ABSORPTION_BEAR
            reasoning = "CVD up aggressively but price flat · buyers absorbed"
        elif price_up and cvd_up:
            state = CVDState.CONFIRMATION_BULL
            reasoning = "price up · CVD confirms"
        elif price_down and cvd_down:
            state = CVDState.CONFIRMATION_BEAR
            reasoning = "price down · CVD confirms"
        elif price_up and cvd_down:
            state = CVDState.DIVERGENCE_BEAR
            reasoning = "price up but CVD down · buying weakness"
        elif price_down and cvd_up:
            state = CVDState.DIVERGENCE_BULL
            reasoning = "price down but CVD up · hidden buying"

        return CVDContextEvent(
            timestamp=timestamp,
            state=state,
            price_delta_bar=price_delta_bar,
            cvd_value=cvd_value,
            cvd_slope=cvd_slope,
            has_volume_spike=has_volume_spike,
            reasoning=reasoning,
        )
