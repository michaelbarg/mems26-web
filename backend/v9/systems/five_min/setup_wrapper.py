"""setup_wrapper — converts pattern detection output to T1Setup.

GRACEFUL DEGRADATION:
- If Layer 3 cluster + empty_zone provided -> exact entry/stop
- Else -> approximations from bar data with provisional=True

WAVE 1: approximation only (Layer 3 wiring deferred to Wave 2+).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, TypedDict, Literal

from .output_schema import T1Setup, PatternName


DEFAULT_TIME_STOP_MIN = 60  # placeholder · S1 Day Type provides exact in Wave 2


class ClusterInfo(TypedDict, total=False):
    top: float
    bottom: float
    yellow_poc: float


class EmptyZone(TypedDict, total=False):
    top: float
    bottom: float


class Bar(TypedDict, total=False):
    high: float
    low: float
    close: float
    open: float
    volume: int


def build_t1setup(
    pattern_name: PatternName,
    direction: Literal['LONG', 'SHORT'],
    bars: list,  # last 4 closed bars
    bar_index: int,
    *,
    cluster: Optional[ClusterInfo] = None,
    empty_zone: Optional[EmptyZone] = None,
    day_type: Optional[str] = None,
) -> T1Setup:
    """Build T1Setup from pattern + bars (+ optional Layer 3 cluster).

    If cluster/empty_zone provided -> use them.
    Else -> approximate from bar data and mark provisional.
    """
    bar_0 = bars[-1]
    bar_n3 = bars[-4] if len(bars) >= 4 else bars[0]
    provisional = cluster is None or empty_zone is None or day_type is None
    reason_parts = []
    if cluster is None:
        reason_parts.append("no Layer 3 cluster")
    if empty_zone is None:
        reason_parts.append("no empty zone")
    if day_type is None:
        reason_parts.append("no Day Type (S1)")
    provisional_reason = " · ".join(reason_parts) if reason_parts else None

    # Entry: cluster.yellow_poc if available, else bar_0.close
    if cluster and 'yellow_poc' in cluster:
        entry = cluster['yellow_poc']
    else:
        entry = bar_0.get('close', 0.0) or bar_0.get('c', 0.0)

    # Stop: empty_zone.bottom (LONG) / top (SHORT), else bar_n3 extreme
    if empty_zone:
        stop = empty_zone['bottom'] if direction == 'LONG' else empty_zone['top']
    else:
        if direction == 'LONG':
            stop = bar_n3.get('low', bar_n3.get('l', entry - 1.0))
        else:
            stop = bar_n3.get('high', bar_n3.get('h', entry + 1.0))

    risk = abs(entry - stop)
    if risk < 0.25:
        risk = 0.25  # minimum 1 tick MES

    # T1 = 1R, T2 = 2R (Wave 2 will use Day Type matrix)
    if direction == 'LONG':
        t1 = entry + risk
        t2 = entry + 2 * risk
    else:
        t1 = entry - risk
        t2 = entry - 2 * risk

    return T1Setup(
        pattern_name=pattern_name,
        direction=direction,
        entry_price=round(entry, 2),
        stop_price=round(stop, 2),
        t1_price=round(t1, 2),
        t2_price=round(t2, 2),
        time_stop_minutes=DEFAULT_TIME_STOP_MIN,
        confidence=70,  # placeholder · Wave 2 wires real scoring
        bar_index=bar_index,
        fired_at=datetime.now(timezone.utc),
        provisional=provisional,
        provisional_reason=provisional_reason,
    )
