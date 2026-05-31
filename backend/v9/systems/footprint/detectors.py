"""Footprint detection algorithms."""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

# S3 ATR-relative range (E2E 2/2 · shadow only)
from backend.v9.shared.atr import S3_RELATIVE  # noqa: E402
_RANGE_ATR_K = 1.0  # prior: 1.0 × ATR5m


def get_range_ticks(atr_5m: Optional[float] = None) -> float:
    """Accumulation range threshold — ATR-relative when flag ON."""
    if S3_RELATIVE and atr_5m is not None:
        return _RANGE_ATR_K * atr_5m
    return 15.0  # original absolute default


@dataclass
class ClusterResult:
    has_cluster: bool
    yellow_poc_price: Optional[float] = None
    yellow_poc_pct: float = 0.0
    three_level_pct: float = 0.0
    cluster_high: Optional[float] = None
    cluster_low: Optional[float] = None


@dataclass
class EmptyZoneResult:
    has_empty: bool
    zones: Optional[List[Dict[str, Any]]] = None

    def __post_init__(self):
        if self.zones is None:
            self.zones = []


@dataclass
class ContextResult:
    accumulation: bool = False
    bars_in_range: int = 0
    jumps_count: int = 0
    jumps_direction: Optional[str] = None
    otf_state: int = 1


def detect_cluster(footprint: Dict[Any, Dict[str, int]], poc_threshold_pct: float = 30.0) -> ClusterResult:
    if not footprint:
        return ClusterResult(has_cluster=False)
    total_vol = sum((v.get("bid_vol", 0) + v.get("ask_vol", 0)) for v in footprint.values())
    if total_vol == 0:
        return ClusterResult(has_cluster=False)
    sorted_prices = sorted(
        footprint.items(),
        key=lambda x: x[1].get("bid_vol", 0) + x[1].get("ask_vol", 0),
        reverse=True,
    )
    yellow_poc_price = float(sorted_prices[0][0])
    yellow_poc_vol = sorted_prices[0][1].get("bid_vol", 0) + sorted_prices[0][1].get("ask_vol", 0)
    yellow_poc_pct = (yellow_poc_vol / total_vol) * 100
    has_cluster = yellow_poc_pct >= poc_threshold_pct
    three_level_pct = 0.0
    cluster_high = None
    cluster_low = None
    if has_cluster:
        prices_sorted = sorted([float(p) for p in footprint.keys()])
        try:
            idx = prices_sorted.index(yellow_poc_price)
            s = max(0, idx - 1)
            e = min(len(prices_sorted), idx + 2)
            three = prices_sorted[s:e]
            three_vol = sum(
                footprint[p].get("bid_vol", 0) + footprint[p].get("ask_vol", 0)
                for p in three
            )
            three_level_pct = (three_vol / total_vol) * 100
            cluster_high = three[-1]
            cluster_low = three[0]
        except (ValueError, IndexError, KeyError):
            pass
    return ClusterResult(
        has_cluster=has_cluster,
        yellow_poc_price=yellow_poc_price,
        yellow_poc_pct=yellow_poc_pct,
        three_level_pct=three_level_pct,
        cluster_high=cluster_high,
        cluster_low=cluster_low,
    )


def detect_empty_zones(footprint: Dict[Any, Dict[str, int]], threshold_pct: float = 5.0) -> EmptyZoneResult:
    if not footprint:
        return EmptyZoneResult(has_empty=False)
    total_vol = sum((v.get("bid_vol", 0) + v.get("ask_vol", 0)) for v in footprint.values())
    if total_vol == 0:
        return EmptyZoneResult(has_empty=False)
    zones = []
    sorted_prices = sorted([float(p) for p in footprint.keys()])
    current_zone = []
    for price in sorted_prices:
        vol = footprint[price].get("bid_vol", 0) + footprint[price].get("ask_vol", 0)
        pct = (vol / total_vol) * 100
        if pct < threshold_pct:
            current_zone.append({"price": price, "pct": pct})
        else:
            if len(current_zone) >= 2:
                zones.append({"low": current_zone[0]["price"], "high": current_zone[-1]["price"], "count": len(current_zone)})
            current_zone = []
    if len(current_zone) >= 2:
        zones.append({"low": current_zone[0]["price"], "high": current_zone[-1]["price"], "count": len(current_zone)})
    return EmptyZoneResult(has_empty=len(zones) > 0, zones=zones)


def analyze_context(recent_bars: List[Dict[str, Any]], min_acc_bars: int = 5, range_ticks: float = 15.0) -> ContextResult:
    if len(recent_bars) < 3:
        return ContextResult()
    last_n = recent_bars[-min_acc_bars:] if len(recent_bars) >= min_acc_bars else recent_bars
    highs = [b.get("high", b.get("close", 0)) for b in last_n]
    lows = [b.get("low", b.get("close", 0)) for b in last_n]
    if highs and lows:
        rng = max(highs) - min(lows)
        accumulation = (rng <= range_ticks) and (len(last_n) >= min_acc_bars)
        bars_in_range = len(last_n) if accumulation else 0
    else:
        accumulation = False
        bars_in_range = 0
    jumps_count = 0
    jumps_direction = None
    if len(recent_bars) >= 3:
        last_3 = recent_bars[-3:]
        deltas = [b.get("close", 0) - b.get("open", 0) for b in last_3]
        if all(d > 0 for d in deltas):
            jumps_count = 3
            jumps_direction = "UP"
        elif all(d < 0 for d in deltas):
            jumps_count = 3
            jumps_direction = "DOWN"
    otf_state = 2 if accumulation else (3 if jumps_count >= 3 else 1)
    return ContextResult(
        accumulation=accumulation,
        bars_in_range=bars_in_range,
        jumps_count=jumps_count,
        jumps_direction=jumps_direction,
        otf_state=otf_state,
    )


def compute_signals(bar: Dict[str, Any], recent_bars: List[Dict[str, Any]]) -> Dict[str, bool]:
    signals = {
        "belly_ratio_dominant": False,
        "vol_drop_90pct": False,
        "cot_vs_amt_clear": False,
        "tick_breach": False,
        "poc_migration": False,
        "imbalance_250": False,
        "stacked_imbalance_3plus": False,
        "cumulative_delta_aligned": False,
        "exhaustion_zone": False,
        "liquidity_sweep": False,
    }
    if len(recent_bars) >= 2:
        prev_vol = recent_bars[-2].get("volume", 0)
        curr_vol = bar.get("volume", 0)
        if prev_vol > 0 and curr_vol < prev_vol * 0.1:
            signals["vol_drop_90pct"] = True
    if bar.get("imbalance_pct", 0) >= 250:
        signals["imbalance_250"] = True
    if bar.get("stacked_count", 0) >= 3:
        signals["stacked_imbalance_3plus"] = True
    return signals
