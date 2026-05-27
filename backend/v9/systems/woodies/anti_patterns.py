"""Anti-pattern checks for Woodies CCI patterns (W-7).

Each checker is a pure static method returning an AntiPatternResult.
AP5 is EXCLUDED -- it stays distributed in hfe.py (W-4 owns it).

Anti-patterns owned by this module:
  AP1  ZLR pullback too long (>12 bars)
  AP2  GB100 in YELLOW trend state
  AP3  VEGAS swings too close (<5 bars apart)
  AP4  HTLB insufficient touches (<2)
  AP6  GB100 pullback too deep (>6 bars opposite ZL)
  AP7  TT TCCI divergence gap too small (<5)
  AP8  CCI flat (universal -- applies to all 9 patterns)
  AP9  FAMIR LSMA mismatch
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal

from backend.v9.systems.woodies.schemas import WoodiesBar

AP_IDS = Literal["AP1", "AP2", "AP3", "AP4", "AP6", "AP7", "AP8", "AP9"]


@dataclass(frozen=True)
class AntiPatternResult:
    """Immutable result of an anti-pattern check."""
    ap_id: AP_IDS
    blocked: bool
    reason: str
    pattern_id: str
    metadata: dict = field(default_factory=dict)


class AntiPatternChecker:
    """Pure-function anti-pattern checks for Woodies CCI.

    Every method is a static method with no side effects and no logging.
    """

    @staticmethod
    def check_ap1_zlr_pullback(bars: List[WoodiesBar]) -> AntiPatternResult:
        """AP1: ZLR after >12-bar pullback from CCI extreme.

        Count bars since last CCI extreme (|CCI| >= 100).
        If >12 bars since last extreme, the ZLR pullback is too long -> blocked.
        """
        if len(bars) < 2:
            return AntiPatternResult(
                ap_id="AP1", blocked=False, reason="insufficient bars",
                pattern_id="ZLR",
            )

        bars_since_extreme = 0
        for i in range(len(bars) - 2, -1, -1):
            if abs(bars[i].cci_14) >= 100:
                bars_since_extreme = len(bars) - 1 - i
                break
        else:
            # No extreme found at all -- block
            return AntiPatternResult(
                ap_id="AP1", blocked=True,
                reason="no CCI extreme found in history",
                pattern_id="ZLR",
                metadata={"bars_searched": len(bars)},
            )

        if bars_since_extreme > 12:
            return AntiPatternResult(
                ap_id="AP1", blocked=True,
                reason=f"ZLR pullback too long: {bars_since_extreme} bars since extreme (max 12)",
                pattern_id="ZLR",
                metadata={"bars_since_extreme": bars_since_extreme},
            )

        return AntiPatternResult(
            ap_id="AP1", blocked=False, reason="pullback within range",
            pattern_id="ZLR",
            metadata={"bars_since_extreme": bars_since_extreme},
        )

    @staticmethod
    def check_ap2_gb100_yellow(bars: List[WoodiesBar]) -> AntiPatternResult:
        """AP2: GB100 in YELLOW trend state -> blocked.

        Defense-in-depth with P-W5 trend state gate.
        """
        if not bars:
            return AntiPatternResult(
                ap_id="AP2", blocked=False, reason="no bars",
                pattern_id="GB100",
            )

        trend = bars[-1].trend_state
        if trend == "YELLOW":
            return AntiPatternResult(
                ap_id="AP2", blocked=True,
                reason="GB100 blocked: trend state is YELLOW",
                pattern_id="GB100",
                metadata={"trend_state": trend},
            )

        return AntiPatternResult(
            ap_id="AP2", blocked=False, reason="trend state acceptable",
            pattern_id="GB100",
            metadata={"trend_state": trend},
        )

    @staticmethod
    def check_ap3_vegas_swings(
        bars: List[WoodiesBar],
        swing_low_idx: int,
        swing_high_idx: int,
    ) -> AntiPatternResult:
        """AP3: VEGAS swings <5 bars apart -> blocked."""
        gap = abs(swing_high_idx - swing_low_idx)
        if gap < 5:
            return AntiPatternResult(
                ap_id="AP3", blocked=True,
                reason=f"VEGAS swings too close: {gap} bars apart (min 5)",
                pattern_id="VEGAS",
                metadata={"swing_gap": gap, "swing_low_idx": swing_low_idx,
                           "swing_high_idx": swing_high_idx},
            )

        return AntiPatternResult(
            ap_id="AP3", blocked=False, reason="swing gap acceptable",
            pattern_id="VEGAS",
            metadata={"swing_gap": gap},
        )

    @staticmethod
    def check_ap4_htlb_touches(
        bars: List[WoodiesBar],
        touches: int,
    ) -> AntiPatternResult:
        """AP4: HTLB <2 touches -> blocked."""
        if touches < 2:
            return AntiPatternResult(
                ap_id="AP4", blocked=True,
                reason=f"HTLB insufficient touches: {touches} (min 2)",
                pattern_id="HTLB",
                metadata={"touches": touches},
            )

        return AntiPatternResult(
            ap_id="AP4", blocked=False, reason="sufficient touches",
            pattern_id="HTLB",
            metadata={"touches": touches},
        )

    @staticmethod
    def check_ap6_gb100_pullback_depth(
        bars: List[WoodiesBar],
        pullback_bars_opposite: int,
    ) -> AntiPatternResult:
        """AP6: GB100 >6 bars on opposite side of zero line -> blocked."""
        if pullback_bars_opposite > 6:
            return AntiPatternResult(
                ap_id="AP6", blocked=True,
                reason=f"GB100 pullback too deep: {pullback_bars_opposite} bars opposite ZL (max 6)",
                pattern_id="GB100",
                metadata={"pullback_bars_opposite": pullback_bars_opposite},
            )

        return AntiPatternResult(
            ap_id="AP6", blocked=False, reason="pullback depth acceptable",
            pattern_id="GB100",
            metadata={"pullback_bars_opposite": pullback_bars_opposite},
        )

    @staticmethod
    def check_ap7_tt_divergence_gap(bar: WoodiesBar) -> AntiPatternResult:
        """AP7: TT TCCI gap <5 -> blocked.

        If abs(cci_14 - cci_6_tcci) < 5, the TCCI divergence is too small.
        """
        gap = abs(bar.cci_14 - bar.cci_6_tcci)
        if gap < 5:
            return AntiPatternResult(
                ap_id="AP7", blocked=True,
                reason=f"TT TCCI gap too small: {gap:.1f} (min 5)",
                pattern_id="TT",
                metadata={"cci_14": bar.cci_14, "cci_6_tcci": bar.cci_6_tcci,
                           "gap": round(gap, 2)},
            )

        return AntiPatternResult(
            ap_id="AP7", blocked=False, reason="TCCI gap acceptable",
            pattern_id="TT",
            metadata={"gap": round(gap, 2)},
        )

    @staticmethod
    def check_ap8_cci_flat(
        bars: List[WoodiesBar],
        lookback: int = 3,
        range_threshold: float = 50.0,
    ) -> AntiPatternResult:
        """AP8: CCI flat -- UNIVERSAL, applies to all 9 patterns.

        If max(CCI) - min(CCI) over last `lookback` bars < range_threshold,
        the CCI is considered flat and the pattern is blocked.
        """
        if len(bars) < lookback:
            return AntiPatternResult(
                ap_id="AP8", blocked=False, reason="insufficient bars for AP8",
                pattern_id="UNIVERSAL",
            )

        recent_cci = [b.cci_14 for b in bars[-lookback:]]
        cci_range = max(recent_cci) - min(recent_cci)

        if cci_range < range_threshold:
            return AntiPatternResult(
                ap_id="AP8", blocked=True,
                reason=f"CCI flat: range {cci_range:.1f} over {lookback} bars (min {range_threshold})",
                pattern_id="UNIVERSAL",
                metadata={"cci_range": round(cci_range, 2), "lookback": lookback,
                           "threshold": range_threshold},
            )

        return AntiPatternResult(
            ap_id="AP8", blocked=False, reason="CCI not flat",
            pattern_id="UNIVERSAL",
            metadata={"cci_range": round(cci_range, 2)},
        )

    @staticmethod
    def check_ap9_famir_lsma(
        bars: List[WoodiesBar],
        direction: str,
    ) -> AntiPatternResult:
        """AP9: FAMIR LSMA mismatch -> blocked.

        LONG needs lsma_above_price == False (price above LSMA, reversal up).
        SHORT needs lsma_above_price == True (price below LSMA, reversal down).
        """
        if not bars:
            return AntiPatternResult(
                ap_id="AP9", blocked=False, reason="no bars",
                pattern_id="FAMIR",
            )

        lsma_above = bars[-1].lsma_above_price

        if direction == "LONG" and lsma_above:
            return AntiPatternResult(
                ap_id="AP9", blocked=True,
                reason="FAMIR LONG blocked: LSMA above price (need below)",
                pattern_id="FAMIR",
                metadata={"direction": direction, "lsma_above_price": lsma_above},
            )

        if direction == "SHORT" and not lsma_above:
            return AntiPatternResult(
                ap_id="AP9", blocked=True,
                reason="FAMIR SHORT blocked: LSMA below price (need above)",
                pattern_id="FAMIR",
                metadata={"direction": direction, "lsma_above_price": lsma_above},
            )

        return AntiPatternResult(
            ap_id="AP9", blocked=False, reason="LSMA alignment correct",
            pattern_id="FAMIR",
            metadata={"direction": direction, "lsma_above_price": lsma_above},
        )
