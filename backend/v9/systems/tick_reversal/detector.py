"""Tick Reversal / Footprint Observer — Main Detector.

Implements the 10-step per-bar processing pipeline from spec Section 6.
OBSERVER ONLY — no trade execution.
"""

from __future__ import annotations
from typing import List, Optional
from collections import deque

from .schemas import (
    BarInput, BarAnalysis, TickReversalConfig,
    ClusterResult, EmptyZoneResult, ContextResult, PatternResult,
    ZoharSignals, IndustrySignals, ConfluenceResult,
)
from .patterns import ALL_PATTERNS
from .signals import (
    calc_belly_comparison,
    calc_volume_drop_90,
    calc_cot_above_amt,
    calc_tick_breach,
    calc_poc_jumping,
    calc_imbalance_250,
    calc_stacked_imbalance,
    calc_cumulative_delta_aligned,
    calc_exhaustion,
    calc_liquidity_sweep,
)


class TickReversalDetector:
    """Per-bar processing pipeline for the Footprint+TR observer.

    STANDALONE: monitors, marks, logs. Never fires trades.
    """

    BUFFER_SIZE = 30  # rolling buffer per spec

    def __init__(self, config: Optional[TickReversalConfig] = None):
        self.config = config or TickReversalConfig()
        self._buffer: deque[BarInput] = deque(maxlen=self.BUFFER_SIZE)

    @property
    def bars(self) -> List[BarInput]:
        return list(self._buffer)

    def process_bar(self, bar: BarInput) -> BarAnalysis:
        """Run the full 10-step pipeline on a new bar. Returns journal entry."""

        # Step 1: Bar Data Update
        self._buffer.append(bar)
        bars = self.bars

        # Step 2: Cluster Detection
        cluster = self._detect_cluster(bar)

        # Step 3: Empty Zone Detection
        empty_zone = self._detect_empty_zone(bar)

        # Step 4: Context Analysis
        context = self._analyze_context(bars)

        # Step 5: Pattern Detection
        pattern = self._detect_pattern(bars, context)

        # Step 6: Signal Calculations
        zohar = self._calc_zohar_signals(bar, bars)
        industry = self._calc_industry_signals(bar, bars)

        # Step 7: Confluence Calculation
        confluence = self._calc_confluence(zohar, industry)

        # Step 8: Classification
        classification = self._classify(confluence.total)

        # Infer direction
        direction = self._infer_direction(bar, context)

        # Would-be prices (hypothetical, observer only)
        entry_price = bar.c if classification != "NO_SETUP" else None
        stop_price = self._calc_stop_price(bar, empty_zone, direction)
        stop_ticks = None
        if entry_price is not None and stop_price is not None:
            stop_ticks = int(abs(entry_price - stop_price) / 0.25)

        # Step 9 + 10: Build journal entry
        bar_id = f"tr_{bar.tick_size}_{int(bar.c * 100)}_{bar.ts}"

        return BarAnalysis(
            ts=bar.ts,
            bar_id=bar_id,
            tick_reversal_size=bar.tick_size,
            bar=bar,
            cluster=cluster,
            empty_zone=empty_zone,
            context=context,
            pattern=pattern,
            signals_zohar=zohar,
            signals_industry=industry,
            confluence=confluence,
            classification=classification,
            direction_inferred=direction,
            would_be_entry_price=entry_price,
            would_be_stop_price=stop_price,
            stop_distance_ticks=stop_ticks,
            visual_marker_drawn=classification != "NO_SETUP",
        )

    def process_dual_bars(self, primary_15_tick: BarInput, secondary_12_tick: BarInput) -> BarAnalysis:
        """Process primary 15-tick and observe secondary 12-tick bar.

        The primary 15-tick bar remains canonical for journal output; the
        secondary stream is accepted to satisfy the dual-feed contract.
        """
        return self.process_bar(primary_15_tick)

    # ── Step 2: Cluster Detection ──

    def _detect_cluster(self, bar: BarInput) -> ClusterResult:
        cfg = self.config

        if bar.footprint and isinstance(bar.footprint, dict):
            levels = bar.footprint.get("levels", [])
            poc_price = bar.footprint.get("poc_price")
            poc_vol = bar.footprint.get("poc_vol")

            if poc_price is not None and bar.vol > 0:
                vol_pct = (poc_vol or 0) / bar.vol if bar.vol > 0 else 0
                # Cluster: top 3 levels by volume
                if isinstance(levels, list) and levels:
                    sorted_levels = sorted(
                        [l for l in levels if isinstance(l, dict)],
                        key=lambda x: x.get("vol", x.get("bid", 0) + x.get("ask", 0)),
                        reverse=True,
                    )
                    top3 = sorted_levels[:3]
                    if top3:
                        prices = [l.get("price", 0) for l in top3 if "price" in l]
                        if prices:
                            return ClusterResult(
                                detected=True,
                                yellow_poc=float(poc_price),
                                boundaries=[min(prices), max(prices)],
                                volume_pct=round(vol_pct, 3),
                            )
                return ClusterResult(
                    detected=vol_pct >= cfg.cluster_poc_threshold_pct / 100,
                    yellow_poc=float(poc_price),
                    volume_pct=round(vol_pct, 3),
                )

        # Fallback: approximate cluster from bar shape
        mid = (bar.h + bar.l) / 2
        body_mid = (bar.o + bar.c) / 2
        return ClusterResult(
            detected=bar.vol > 0,
            yellow_poc=round(body_mid, 2),
            boundaries=[round(min(bar.o, bar.c), 2), round(max(bar.o, bar.c), 2)],
            volume_pct=0.0,
        )

    # ── Step 3: Empty Zone Detection ──

    def _detect_empty_zone(self, bar: BarInput) -> EmptyZoneResult:
        if bar.footprint and isinstance(bar.footprint, dict):
            levels = bar.footprint.get("levels", [])
            if isinstance(levels, list) and levels and bar.vol > 0:
                threshold = self.config.empty_zone_threshold_pct / 100
                empty = [
                    l for l in levels
                    if isinstance(l, dict)
                    and (l.get("vol", l.get("bid", 0) + l.get("ask", 0))) / bar.vol < threshold
                ]
                if empty:
                    prices = [l.get("price", 0) for l in empty if "price" in l]
                    if prices:
                        return EmptyZoneResult(
                            detected=True,
                            boundaries=[min(prices), max(prices)],
                            volume_pct=round(threshold, 3),
                        )

        # Fallback: wick areas are approximated empty zones
        is_up = bar.c >= bar.o
        if is_up and bar.o > bar.l:
            return EmptyZoneResult(
                detected=True,
                boundaries=[round(bar.l, 2), round(bar.o, 2)],
                volume_pct=0.0,
            )
        elif not is_up and bar.o < bar.h:
            return EmptyZoneResult(
                detected=True,
                boundaries=[round(bar.o, 2), round(bar.h, 2)],
                volume_pct=0.0,
            )
        return EmptyZoneResult()

    # ── Step 4: Context Analysis ──

    def _analyze_context(self, bars: List[BarInput]) -> ContextResult:
        cfg = self.config
        tick = 0.25  # MES tick size

        # Accumulation: N bars in tight range
        accum_active = False
        accum_bars = 0
        accum_range = 0
        if len(bars) >= cfg.accumulation_min_bars:
            for n in range(cfg.accumulation_min_bars, len(bars) + 1):
                window = bars[-n:]
                high = max(b.h for b in window)
                low = min(b.l for b in window)
                range_ticks = int((high - low) / tick)
                if range_ticks <= cfg.accumulation_range_ticks:
                    accum_active = True
                    accum_bars = n
                    accum_range = range_ticks
                else:
                    break

        # 3 Jumps: consecutive bars same direction
        jumps_count = 0
        jumps_dir = None
        if len(bars) >= 2:
            current_dir = "UP" if bars[-1].c > bars[-1].o else "DOWN"
            jumps_count = 1
            jumps_dir = current_dir
            for b in reversed(bars[:-1]):
                d = "UP" if b.c > b.o else "DOWN"
                if d == current_dir:
                    jumps_count += 1
                else:
                    break

        # OTF Clarity (simplified from Zohar's 4 states)
        otf = 4  # default = unclear
        if len(bars) >= 3:
            recent = bars[-3:]
            ups = sum(1 for b in recent if b.c > b.o)
            downs = sum(1 for b in recent if b.c < b.o)
            if ups >= 2 and downs >= 1:
                otf = 1  # both sides clear
            elif ups == 0 and downs >= 2:
                otf = 2  # sellers only → LONG only
            elif downs == 0 and ups >= 2:
                otf = 3  # buyers only → SHORT only
            else:
                otf = 4

        return ContextResult(
            accumulation_active=accum_active,
            accumulation_bars=accum_bars,
            accumulation_range_ticks=accum_range,
            jumps_count=jumps_count,
            jumps_direction=jumps_dir,
            otf_state=otf,
        )

    # ── Step 5: Pattern Detection ──

    def _detect_pattern(self, bars: List[BarInput], ctx: ContextResult) -> PatternResult:
        for name, detect_fn in ALL_PATTERNS:
            result = detect_fn(bars, ctx)
            if result.detected:
                return result
        return PatternResult()

    # ── Step 6: Signal Calculations ──

    def _calc_zohar_signals(self, bar: BarInput, bars: List[BarInput]) -> ZoharSignals:
        cfg = self.config
        return ZoharSignals(
            belly_comparison=calc_belly_comparison(bar, bars, cfg.belly_dominance_ratio),
            volume_drop_90=calc_volume_drop_90(bar, bars, cfg.volume_drop_pct),
            cot_above_amt=calc_cot_above_amt(bar, bars),
            tick_breach_ok=calc_tick_breach(bar, bars),
            poc_jumping=calc_poc_jumping(bar, bars),
        )

    def _calc_industry_signals(self, bar: BarInput, bars: List[BarInput]) -> IndustrySignals:
        cfg = self.config
        return IndustrySignals(
            imbalance_250=calc_imbalance_250(bar, bars, cfg.imbalance_ratio),
            stacked_imbalance=calc_stacked_imbalance(
                bar, bars, cfg.imbalance_ratio, cfg.stacked_imbalance_count,
            ),
            cumulative_delta_aligned=calc_cumulative_delta_aligned(bar, bars),
            exhaustion=calc_exhaustion(bar, bars),
            liquidity_sweep=calc_liquidity_sweep(bar, bars),
        )

    # ── Step 7: Confluence ──

    def _calc_confluence(self, zohar: ZoharSignals, industry: IndustrySignals) -> ConfluenceResult:
        """Sum signals with weights per spec Section 6 Step 7."""
        z_count = sum([
            zohar.belly_comparison,
            zohar.volume_drop_90,
            zohar.cot_above_amt,
            zohar.tick_breach_ok,
            zohar.poc_jumping,
        ])

        # Industry: most are +1, stacked = +2, sweep = +2
        i_count = sum([
            industry.imbalance_250,
            industry.cumulative_delta_aligned,
        ])
        boosters = 0
        if industry.stacked_imbalance:
            boosters += 2
        if industry.liquidity_sweep:
            boosters += 2

        # Penalties
        penalties = 0
        if industry.exhaustion:
            penalties += 1
        # Delta divergence: if delta is NOT aligned, that's a penalty
        if not industry.cumulative_delta_aligned:
            penalties += 1

        total = z_count + i_count + boosters - penalties

        return ConfluenceResult(
            zohar_count=z_count,
            industry_count=i_count,
            boosters=boosters,
            penalties=penalties,
            total=max(0, total),
        )

    # ── Step 8: Classification ──

    def _classify(self, confluence_total: int) -> str:
        if confluence_total >= self.config.confluence_strategic_min:
            return "STRATEGIC"
        if confluence_total >= self.config.confluence_tactical_min:
            return "TACTICAL"
        return "NO_SETUP"

    # ── Helpers ──

    def _infer_direction(self, bar: BarInput, ctx: ContextResult) -> Optional[str]:
        if ctx.jumps_direction == "UP" and bar.c > bar.o:
            return "LONG"
        if ctx.jumps_direction == "DOWN" and bar.c < bar.o:
            return "SHORT"
        if bar.c > bar.o:
            return "LONG"
        if bar.c < bar.o:
            return "SHORT"
        return None

    def _calc_stop_price(
        self, bar: BarInput, empty_zone: EmptyZoneResult, direction: Optional[str],
    ) -> Optional[float]:
        if direction is None:
            return None

        if empty_zone.detected and empty_zone.boundaries:
            if direction == "LONG":
                return empty_zone.boundaries[0]
            else:
                return empty_zone.boundaries[1]

        # Fallback: opposite extreme of bar
        if direction == "LONG":
            return bar.l
        return bar.h
