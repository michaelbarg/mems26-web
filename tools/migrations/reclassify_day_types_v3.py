"""
V3 Day Type Reclassification — OFFLINE migration script.

Reclassifies 4,996 cached MDS setups from V2 day types to V3.
Read-only on original parquet; outputs new V3 parquet.

Version: V8.4.2-RESEARCH-MIGRATION-SELFCONTAINED
Date: 2026-05-05
Phase: 3.2 Day 2 — Pure Observation

Usage:
    python3 -m tools.migrations.reclassify_day_types_v3
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# ═══════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════

INPUT_PATH = Path("tools/multidim_sim/cache/setups_clean_2026-05-05_full.parquet")
OUTPUT_PATH = Path("tools/multidim_sim/cache/setups_clean_2026-05-05_v3.parquet")
MIGRATION_VERSION = "v8.4.2-2026-05-05"

# [APPROVED 2026-05-05] MES realistic ATR in normal markets (VIX 13-15)
ATR_BASELINE_DEFAULT = 40.0

# [V2] Hysteresis: switch only if new_conf >= current + 15
HYSTERESIS_THRESHOLD = 15

# [HANDOFF] GAP_FILL minimum gap size (was 5pt in V2)
GAP_FILL_MIN_PTS = 20.0

# [PATCH 2] MES Rollover Periods 2026
ROLLOVER_PERIODS_2026 = [
    {"start": "2026-03-12", "end": "2026-03-19"},
    {"start": "2026-06-11", "end": "2026-06-18"},
    {"start": "2026-09-10", "end": "2026-09-17"},
    {"start": "2026-12-10", "end": "2026-12-17"},
]

# [APPROVED 2026-05-05] Tie-breaking priority (lower index = higher priority)
TIE_BREAK_ORDER = [
    "GAP_FILL", "REVERSAL_DAY", "TREND_DAY",
    "BROAD_CHANNEL", "RANGE_DAY", "NEUTRAL",
]

# ET timezone offset (UTC-4 during EDT, UTC-5 EST)
# Apr 29 - May 3 2026 is EDT (UTC-4)
ET_OFFSET = timedelta(hours=-4)


# ═══════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════

@dataclass
class DayMetrics:
    """Aggregated metrics for one trading day, derived from setups."""
    date: date
    day_range: float = 0.0           # max - min price observed
    ib_range: float = 0.0            # initial balance range (first 60min)
    atr_baseline: float = ATR_BASELINE_DEFAULT
    vegas_flips_today: int = 0       # count of vegas direction changes
    ib_break_held: bool = False      # did IB breakout hold?
    ib_break_direction: str = "NONE" # LONG/SHORT/NONE
    ib_break_failed_count: int = 0   # how many failed IB breaks
    no_range_extension_held: bool = False
    open_price: float = 0.0          # first setup entry price
    prior_day_close: float = 0.0     # last setup entry of previous day
    moving_to_pdc: bool = False      # price moving toward PDC
    first_90min_direction: str = "NONE"  # majority dir in 09:30-11:00 ET
    current_direction: str = "NONE"      # direction of last setup
    close_to_mid_ratio: float = 0.0      # how close to day midpoint
    volume_burst_at_reversal_ratio: float = 0.0
    n_setups: int = 0
    # For gap detection
    gap_size: float = 0.0


@dataclass
class SetupMetrics:
    """Per-setup classification results."""
    day_type_v3: str = "UNKNOWN"
    day_type_v3_confidence: float = 0.0
    day_type_v3_details: str = ""
    is_developing_v3: bool = False
    is_special_day_v3: bool = False
    special_day_reason_v3: str = ""
    news_tier_v3: int = 0
    time_phase_v3: str = "UNKNOWN"


# ═══════════════════════════════════════════════════════════
# TIME / CALENDAR FUNCTIONS
# ═══════════════════════════════════════════════════════════

def _ts_to_et(ts: int) -> datetime:
    """Convert unix timestamp to ET datetime."""
    utc_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return utc_dt + ET_OFFSET


def get_time_phase(ts: int) -> str:
    """Determine time phase from timestamp. [HANDOFF §A.2]"""
    et = _ts_to_et(ts)
    hour, minute = et.hour, et.minute
    t = hour * 60 + minute

    if t < 9 * 60 + 30:
        return "PREMARKET"
    elif t < 11 * 60:
        return "DEVELOPING"
    elif t < 14 * 60 + 30:
        return "RTH"
    elif t < 16 * 60:
        return "LATE_DAY"
    else:
        return "OFF_HOURS"


def is_developing_period(ts: int) -> bool:
    """[HANDOFF §A.2] Is this timestamp in the DEVELOPING time phase?"""
    return get_time_phase(ts) == "DEVELOPING"


def is_rollover_period(ts: int) -> bool:
    """[PATCH 2] Is this timestamp during a MES rollover period?"""
    dt = datetime.fromtimestamp(ts, tz=timezone.utc).date()
    for period in ROLLOVER_PERIODS_2026:
        start = date.fromisoformat(period["start"])
        end = date.fromisoformat(period["end"])
        if start <= dt <= end:
            return True
    return False


def is_special_day_block(ts: int) -> tuple[bool, str]:
    """[INFERRED + PATCH 2 §A.4] Check if special day restrictions apply."""
    et = _ts_to_et(ts)
    dt = et.date()
    reasons = []

    # Friday after 14:00 ET
    if et.weekday() == 4 and et.hour >= 14:
        reasons.append("friday_late")

    # Year-end window
    if (dt.month == 12 and dt.day >= 22) or (dt.month == 1 and dt.day <= 2):
        reasons.append("year_end_window")

    # Rollover
    if is_rollover_period(ts):
        reasons.append("rollover_period")

    if reasons:
        return True, "|".join(reasons)
    return False, ""


def is_news_blackout(ts: int, news_calendar: dict) -> tuple[bool, int]:
    """[HANDOFF §A.5] News filter — stub with empty calendar."""
    # No calendar available for migration — always returns no blackout
    return False, 0


# ═══════════════════════════════════════════════════════════
# DAY TYPE DETECTORS
# ═══════════════════════════════════════════════════════════

def is_trend_day(m: DayMetrics) -> tuple[bool, float]:
    """[V2 — unchanged, IB relaxed for proxy data per §A.6 limitations]
    TREND_DAY: low vegas flips, directional, range extension.
    When IB data unavailable (no setups in 09:30-10:30 ET), IB constraint
    is relaxed and direction consistency is used instead of ib_break_held.
    """
    has_ib_data = m.ib_range != m.day_range * 0.4  # True if real IB was computed
    range_ratio = m.day_range / m.atr_baseline if m.atr_baseline > 0 else 0

    # Override: extreme range extension (>2x ATR) is TREND regardless of IB
    # (§A.6: IB from setup entry prices is approximate — unreliable for trend detection)
    if range_ratio > 2.0:
        conf = min(1.0, range_ratio / 3.0)
        return True, conf

    if has_ib_data:
        # Full V3 logic
        if (m.vegas_flips_today <= 2
                and m.ib_range < m.atr_baseline * 0.7
                and m.ib_break_held
                and m.day_range > m.atr_baseline * 0.7):
            conf = min(1.0, m.day_range / m.atr_baseline)
            return True, conf
    else:
        # Relaxed: no IB data. Use flips + range + direction consistency.
        range_ratio = m.day_range / m.atr_baseline if m.atr_baseline > 0 else 0
        # Strong trend signal: range > 2x ATR overrides moderate flips
        # (big extension days can have intraday pullbacks creating flips)
        max_flips = 2 if range_ratio < 1.5 else (5 if range_ratio < 2.0 else 15)
        if (m.vegas_flips_today <= max_flips
                and m.day_range > m.atr_baseline * 0.7):
            # Direction consistency provides confidence boost
            dir_consistent = (m.first_90min_direction == m.current_direction
                              and m.first_90min_direction != "NONE")
            base_conf = min(1.0, range_ratio)
            conf = base_conf * (0.9 if dir_consistent else 0.6)
            return True, conf

    return False, 0.0


def is_broad_channel(m: DayMetrics) -> tuple[bool, float]:
    """[HANDOFF rename + APPROVED 2026-05-05, IB relaxed for proxy data]
    BROAD_CHANNEL: moderate movement, low-to-moderate flips, contained range.
    Replaces V2 NORMAL.
    """
    range_ratio = m.day_range / m.atr_baseline if m.atr_baseline > 0 else 0
    has_ib_data = m.ib_range != m.day_range * 0.4

    if has_ib_data:
        ib_low = m.atr_baseline * 0.5
        ib_high = m.atr_baseline * 1.0
        if (ib_low <= m.ib_range <= ib_high
                and m.vegas_flips_today <= 3
                and 0.7 <= range_ratio <= 1.2):
            conf = min(1.0, 0.4 + 0.1 * m.vegas_flips_today)
            return True, conf
    else:
        # Relaxed: moderate range (0.4 to 2.0 ATR), moderate flips (<=8)
        # BROAD_CHANNEL is the "normal" trading day — rotational, some range
        if (0.4 <= range_ratio <= 2.0
                and m.vegas_flips_today <= 8):
            conf = min(1.0, 0.3 + 0.1 * min(m.vegas_flips_today, 3))
            # Higher conf if range is closer to 1.0 ATR
            range_closeness = 1.0 - abs(range_ratio - 1.0) * 0.5
            conf = min(1.0, conf * max(0.3, range_closeness))
            return True, conf

    return False, 0.0


def is_range_day(m: DayMetrics) -> tuple[bool, float]:
    """[V2 — unchanged, IB relaxed]
    RANGE_DAY: high chop (many vegas flips), contained range.
    """
    has_ib_data = m.ib_range != m.day_range * 0.4

    if has_ib_data:
        if (m.vegas_flips_today >= 4
                and m.ib_range > m.atr_baseline * 1.2
                and m.no_range_extension_held):
            conf = min(1.0, m.vegas_flips_today / 6.0)
            return True, conf
    else:
        # Relaxed: high flips (4+) + range not extreme (<=1.5x ATR)
        range_ratio = m.day_range / m.atr_baseline if m.atr_baseline > 0 else 0
        if (m.vegas_flips_today >= 4
                and range_ratio <= 1.5):
            conf = min(1.0, m.vegas_flips_today / 8.0) * 0.8
            return True, conf

    return False, 0.0


def is_gap_fill_day(m: DayMetrics) -> tuple[bool, float]:
    """[HANDOFF — min size patched §A.1] GAP_FILL detection."""
    gap = abs(m.open_price - m.prior_day_close)
    if gap > GAP_FILL_MIN_PTS and m.moving_to_pdc:
        conf = min(1.0, gap / 30.0)
        return True, conf
    return False, 0.0


def is_reversal_day(m: DayMetrics) -> tuple[bool, float]:
    """[HANDOFF NEW — APPROVED 2026-05-05] REVERSAL_DAY V-shape detection."""
    if (m.first_90min_direction != "NONE"
            and m.current_direction != "NONE"
            and m.first_90min_direction != m.current_direction
            and m.day_range > m.atr_baseline * 1.0
            and m.volume_burst_at_reversal_ratio >= 1.5):
        # Confidence = estimated pct reversed (proxy)
        conf = min(1.0, m.day_range / (m.atr_baseline * 1.5))
        return True, conf
    return False, 0.0


def is_neutral_day(m: DayMetrics) -> tuple[bool, float]:
    """[V2 — unchanged] NEUTRAL detection."""
    if (m.ib_break_direction != "NONE"
            and m.ib_break_failed_count >= 2
            and m.vegas_flips_today >= 6
            and abs(m.close_to_mid_ratio) < 0.2):
        conf = min(1.0, m.ib_break_failed_count / 2.0)
        return True, conf
    return False, 0.0


# ═══════════════════════════════════════════════════════════
# ORCHESTRATOR
# ═══════════════════════════════════════════════════════════

def classify_day(m: DayMetrics) -> tuple[str, float, str]:
    """[§A.7] Run all detectors, pick best with tie-breaking."""
    detectors = [
        ("TREND_DAY", is_trend_day),
        ("BROAD_CHANNEL", is_broad_channel),
        ("RANGE_DAY", is_range_day),
        ("GAP_FILL", is_gap_fill_day),
        ("REVERSAL_DAY", is_reversal_day),
        ("NEUTRAL", is_neutral_day),
    ]

    candidates = []
    for name, fn in detectors:
        matched, conf = fn(m)
        if matched:
            candidates.append((name, conf))

    if not candidates:
        # Fallback: BROAD_CHANNEL at low confidence (replaces V2 NORMAL).
        # Most days that don't match strict criteria are rotational/channel days.
        fallback_conf = 0.3 if m.day_range > 0 else 0.1
        return ("BROAD_CHANNEL", fallback_conf * 100, "fallback — no strict detector matched")

    # Sort by confidence descending
    candidates.sort(key=lambda x: -x[1])

    # [APPROVED 2026-05-05] Tie-breaking: if top 2 within 5pp, use priority order
    if len(candidates) >= 2:
        top_conf = candidates[0][1]
        tied = [c for c in candidates if top_conf - c[1] <= 0.05]
        if len(tied) > 1:
            # Sort tied candidates by tie-break priority
            tied.sort(key=lambda x: TIE_BREAK_ORDER.index(x[0])
                      if x[0] in TIE_BREAK_ORDER else 99)
            best = tied[0]
        else:
            best = candidates[0]
    else:
        best = candidates[0]

    details = f"matched {len(candidates)}: {[c[0] for c in candidates]}"
    return (best[0], best[1] * 100, details)


# ═══════════════════════════════════════════════════════════
# METRIC BUILDERS (from setup data — heuristics per §A.6)
# ═══════════════════════════════════════════════════════════

def _parse_vegas_flips(ts_reasons_pairs: list[tuple[int, str]]) -> int:
    """Count unique vegas direction changes per day.

    Strategy: extract actual Vegas trend direction from score_reasons,
    take majority vote per 180s window, then count transitions.
    This avoids inflation from stale re-emission and simultaneous
    LONG+SHORT setup generation.
    """
    from collections import Counter

    # Extract Vegas direction from each score_reasons
    window_votes: dict[int, list[str]] = {}  # window_id → list of directions
    for ts, r in ts_reasons_pairs:
        if not r:
            continue
        r_lower = r.lower()
        # Extract actual Vegas trend direction (not setup direction)
        # "Vegas BULLISH match" → Vegas=BULL
        # "Vegas BEARISH OPPOSES LONG" → Vegas=BEAR
        # "Vegas BEARISH match" → Vegas=BEAR
        # "Vegas BULLISH OPPOSES SHORT" → Vegas=BULL
        direction = None
        if 'vegas bullish' in r_lower:
            direction = 'BULL'
        elif 'vegas bearish' in r_lower:
            direction = 'BEAR'

        if direction is None:
            continue

        window_id = ts // 180
        if window_id not in window_votes:
            window_votes[window_id] = []
        window_votes[window_id].append(direction)

    # Majority vote per window
    window_directions = []  # (window_id, majority_direction)
    for wid in sorted(window_votes.keys()):
        votes = window_votes[wid]
        c = Counter(votes)
        majority = c.most_common(1)[0][0]
        window_directions.append((wid, majority))

    if len(window_directions) < 2:
        return 0

    # Count direction transitions
    flips = sum(1 for i in range(1, len(window_directions))
                if window_directions[i][1] != window_directions[i - 1][1])
    return flips


def _get_majority_direction(directions: list[str]) -> str:
    """Return majority direction from a list."""
    if not directions:
        return "NONE"
    long_count = sum(1 for d in directions if d == "LONG")
    short_count = sum(1 for d in directions if d == "SHORT")
    if long_count > short_count:
        return "LONG"
    elif short_count > long_count:
        return "SHORT"
    return "NONE"


def build_day_metrics(group: pd.DataFrame, prior_day_last_price: float = 0.0) -> DayMetrics:
    """
    Build DayMetrics from all setups for one date.
    Uses heuristics documented in §A.6.
    """
    if group.empty:
        return DayMetrics(date=date.today())

    # Sort by timestamp
    g = group.sort_values("ts")
    the_date = datetime.fromtimestamp(int(g.iloc[0]["ts"]), tz=timezone.utc).date()

    # Prices
    entry_prices = g["entry_price"].dropna().values
    open_price = float(entry_prices[0]) if len(entry_prices) > 0 else 0.0

    # Day range from entry_price + MFE/MAE expansion
    if len(entry_prices) > 0:
        mfe_vals = g["mfe_pts"].fillna(0).values
        mae_vals = g["mae_pts"].fillna(0).values
        # For LONG: high = entry + mfe, low = entry - mae
        # For SHORT: high = entry + mae, low = entry - mfe
        highs = []
        lows = []
        for i, row in g.iterrows():
            ep = row["entry_price"]
            mfe = row.get("mfe_pts", 0) or 0
            mae = row.get("mae_pts", 0) or 0
            if row["direction"] == "LONG":
                highs.append(ep + mfe)
                lows.append(ep - mae)
            else:
                highs.append(ep + mae)
                lows.append(ep - mfe)
        day_high = max(highs) if highs else open_price
        day_low = min(lows) if lows else open_price
        day_range = day_high - day_low
    else:
        day_range = 0.0
        day_high = day_low = open_price

    # IB range: setups in first 60min of RTH (09:30-10:30 ET)
    ib_setups = []
    for _, row in g.iterrows():
        et = _ts_to_et(int(row["ts"]))
        t = et.hour * 60 + et.minute
        if 9 * 60 + 30 <= t <= 10 * 60 + 30:
            ib_setups.append(row)

    if ib_setups:
        # IB range from entry + MFE/MAE expansion (captures actual price range)
        ib_highs = []
        ib_lows = []
        for r in ib_setups:
            ep = r["entry_price"]
            mfe = r.get("mfe_pts", 0) or 0
            mae = r.get("mae_pts", 0) or 0
            if r["direction"] == "LONG":
                ib_highs.append(ep + mfe)
                ib_lows.append(ep - mae)
            else:
                ib_highs.append(ep + mae)
                ib_lows.append(ep - mfe)
        ib_range = max(ib_highs) - min(ib_lows) if ib_highs else 0
        # IB break heuristic: if majority direction consistent → held
        ib_dirs = [r["direction"] for r in ib_setups]
        long_count = sum(1 for d in ib_dirs if d == "LONG")
        short_count = len(ib_dirs) - long_count
        dominant = "LONG" if long_count > short_count else "SHORT"
        last_dir = ib_dirs[-1]
        ib_break_held = (last_dir == dominant)
        ib_break_direction = dominant
        # Failed breaks: unique direction changes (deduplicated by 180s)
        unique_dirs = []
        prev_ts = 0
        for r in sorted(ib_setups, key=lambda x: x["ts"]):
            if int(r["ts"]) - prev_ts >= 180 or not unique_dirs:
                unique_dirs.append(r["direction"])
                prev_ts = int(r["ts"])
        ib_flips = sum(1 for i in range(1, len(unique_dirs)) if unique_dirs[i] != unique_dirs[i - 1])
        ib_break_failed_count = ib_flips
    else:
        ib_range = day_range * 0.4  # fallback: assume IB ~ 40% of day range
        ib_break_held = False
        ib_break_direction = "NONE"
        ib_break_failed_count = 0

    # Vegas flips from score_reasons (deduplicated by 3-min window)
    ts_reasons = list(zip(g["ts"].astype(int).tolist(), g["score_reasons"].fillna("").tolist()))
    vegas_flips = _parse_vegas_flips(ts_reasons)

    # no_range_extension_held: if day_range <= ib_range * 1.1
    no_range_extension_held = (day_range <= ib_range * 1.1) if ib_range > 0 else True

    # Gap detection
    gap_size = abs(open_price - prior_day_last_price) if prior_day_last_price > 0 else 0
    # Is price moving toward PDC?
    last_price = float(entry_prices[-1]) if len(entry_prices) > 0 else open_price
    if prior_day_last_price > 0 and gap_size > 0:
        moved_toward = abs(last_price - prior_day_last_price) < abs(open_price - prior_day_last_price)
    else:
        moved_toward = False

    # First 90min direction (DEVELOPING phase: 09:30-11:00 ET)
    dev_setups_dirs = []
    for _, row in g.iterrows():
        et = _ts_to_et(int(row["ts"]))
        t = et.hour * 60 + et.minute
        if 9 * 60 + 30 <= t <= 11 * 60:
            dev_setups_dirs.append(row["direction"])
    first_90min_dir = _get_majority_direction(dev_setups_dirs)

    # Current (last) direction
    current_dir = g.iloc[-1]["direction"] if len(g) > 0 else "NONE"

    # Close to mid ratio
    mid = (day_high + day_low) / 2 if day_range > 0 else open_price
    if day_range > 0:
        close_to_mid = (last_price - mid) / (day_range / 2) if day_range > 0 else 0
    else:
        close_to_mid = 0

    # Volume burst proxy: setups in last 2 hours vs average
    all_ts = g["ts"].values
    if len(all_ts) > 4:
        session_duration = int(all_ts[-1]) - int(all_ts[0])
        if session_duration > 7200:  # >2 hours of data
            last_2h_start = int(all_ts[-1]) - 7200
            last_2h_count = sum(1 for t in all_ts if t >= last_2h_start)
            avg_per_2h = len(all_ts) * 7200 / session_duration if session_duration > 0 else len(all_ts)
            vol_burst = last_2h_count / avg_per_2h if avg_per_2h > 0 else 1.0
        else:
            vol_burst = 1.0
    else:
        vol_burst = 1.0

    return DayMetrics(
        date=the_date,
        day_range=day_range,
        ib_range=ib_range,
        atr_baseline=ATR_BASELINE_DEFAULT,
        vegas_flips_today=vegas_flips,
        ib_break_held=ib_break_held,
        ib_break_direction=ib_break_direction,
        ib_break_failed_count=ib_break_failed_count,
        no_range_extension_held=no_range_extension_held,
        open_price=open_price,
        prior_day_close=prior_day_last_price,
        moving_to_pdc=moved_toward,
        first_90min_direction=first_90min_dir,
        current_direction=current_dir,
        close_to_mid_ratio=close_to_mid,
        volume_burst_at_reversal_ratio=vol_burst,
        n_setups=len(g),
        gap_size=gap_size,
    )


# ═══════════════════════════════════════════════════════════
# MAIN MIGRATION
# ═══════════════════════════════════════════════════════════

def run_migration():
    start = time.time()
    print("=" * 60)
    print("  V3 Day Type Reclassification — Migration")
    print(f"  Version: {MIGRATION_VERSION}")
    print("=" * 60)

    # Load
    df = pd.read_parquet(INPUT_PATH)
    print(f"\n  Input: {INPUT_PATH}")
    print(f"  Rows: {len(df)}")

    # Add date column from ts
    df["_date"] = df["ts"].apply(lambda t: datetime.fromtimestamp(int(t), tz=timezone.utc).date())
    dates = sorted(df["_date"].unique())
    print(f"  Dates: {dates}")

    # Build per-day metrics
    day_metrics_cache: dict[date, DayMetrics] = {}
    prior_close = 0.0
    for d in dates:
        group = df[df["_date"] == d]
        dm = build_day_metrics(group, prior_close)
        day_metrics_cache[d] = dm
        # Set prior_close for next day
        sorted_group = group.sort_values("ts")
        if len(sorted_group) > 0:
            prior_close = float(sorted_group.iloc[-1]["entry_price"])

    # Print day metrics summary
    print(f"\n  Day Metrics:")
    for d, m in day_metrics_cache.items():
        dt, conf, det = classify_day(m)
        print(f"    {d}: range={m.day_range:.1f} ib={m.ib_range:.1f} "
              f"flips={m.vegas_flips_today} held={m.ib_break_held} "
              f"→ {dt} ({conf:.0f}%)")

    # Classify each setup
    results = []
    for idx, row in df.iterrows():
        ts = int(row["ts"])
        d = row["_date"]
        dm = day_metrics_cache[d]

        # Day type classification
        day_type, conf, details = classify_day(dm)

        # Time phase
        time_phase = get_time_phase(ts)
        is_dev = (time_phase == "DEVELOPING")

        # Special day
        is_special, special_reason = is_special_day_block(ts)

        # News (stub)
        _, news_tier = is_news_blackout(ts, {})

        results.append({
            "day_type_v3": day_type,
            "day_type_v3_confidence": conf,
            "day_type_v3_details": details,
            "day_type_v2": row.get("day_type", "UNKNOWN"),
            "time_phase_v3": time_phase,
            "is_developing_v3": is_dev,
            "is_special_day_v3": is_special,
            "special_day_reason_v3": special_reason,
            "news_tier_v3": news_tier,
            "v3_migration_version": MIGRATION_VERSION,
        })

    # Build output DataFrame
    result_df = pd.DataFrame(results)
    out_df = pd.concat([df.drop(columns=["_date"]).reset_index(drop=True),
                        result_df.reset_index(drop=True)], axis=1)

    # ─── Sanity checks ───
    print(f"\n  Sanity Checks:")
    assert len(out_df) == len(df), f"Row mismatch: {len(out_df)} vs {len(df)}"
    print(f"    ✓ Row count: {len(out_df)}")

    null_count = out_df["day_type_v3"].isna().sum()
    assert null_count == 0, f"NULL day_type_v3: {null_count}"
    print(f"    ✓ No NULL day_type_v3")

    conf_min = out_df["day_type_v3_confidence"].min()
    conf_max = out_df["day_type_v3_confidence"].max()
    assert conf_min >= 0 and conf_max <= 100, f"Confidence out of range: [{conf_min}, {conf_max}]"
    print(f"    ✓ Confidence range: [{conf_min:.1f}, {conf_max:.1f}]")

    v3_sum = out_df["day_type_v3"].value_counts().sum()
    assert v3_sum == len(out_df), f"V3 count sum mismatch"
    print(f"    ✓ V3 type counts sum to total")

    reversal_count = (out_df["day_type_v3"] == "REVERSAL_DAY").sum()
    if reversal_count > 0:
        print(f"    ✓ REVERSAL_DAY detected: {reversal_count} setups")
    else:
        print(f"    ℹ No REVERSAL_DAY detected (V-shape conditions not met in 5-day window)")

    dev_count = out_df["is_developing_v3"].sum()
    dev_pct = dev_count / len(out_df) * 100
    print(f"    ✓ DEVELOPING phase: {dev_count} ({dev_pct:.1f}%) — "
          f"{'reasonable' if 5 < dev_pct < 40 else 'CHECK'}")

    # Save
    out_df.to_parquet(OUTPUT_PATH, index=False)
    print(f"\n  Output saved: {OUTPUT_PATH}")
    print(f"  Size: {OUTPUT_PATH.stat().st_size / 1024:.0f} KB")

    elapsed = time.time() - start

    # ─── Summary Statistics ───
    print(f"\n{'='*60}")
    print(f"  DISTRIBUTION COMPARISON")
    print(f"{'='*60}")

    # V2 distribution
    print(f"\n  V2 Distribution (original):")
    v2_counts = out_df["day_type_v2"].value_counts()
    for dt, cnt in v2_counts.items():
        print(f"    {dt:<15} {cnt:>5} ({cnt/len(out_df)*100:>5.1f}%)")

    # V3 distribution
    print(f"\n  V3 Distribution (reclassified):")
    v3_counts = out_df["day_type_v3"].value_counts()
    for dt, cnt in v3_counts.items():
        print(f"    {dt:<15} {cnt:>5} ({cnt/len(out_df)*100:>5.1f}%)")

    # Time phase distribution
    print(f"\n  Time Phase Distribution:")
    tp_counts = out_df["time_phase_v3"].value_counts()
    for tp, cnt in tp_counts.items():
        print(f"    {tp:<15} {cnt:>5} ({cnt/len(out_df)*100:>5.1f}%)")

    # Special day
    special_count = out_df["is_special_day_v3"].sum()
    print(f"\n  Special day blocks: {special_count}")
    if special_count > 0:
        reason_counts = out_df[out_df["is_special_day_v3"]]["special_day_reason_v3"].value_counts()
        for r, c in reason_counts.items():
            print(f"    {r}: {c}")

    # V2 → V3 migration map
    print(f"\n  V2 → V3 Migration Map:")
    cross = pd.crosstab(out_df["day_type_v2"], out_df["day_type_v3"])
    print(cross.to_string())

    # WR per V3 type (using outcome column)
    print(f"\n  Win Rate per V3 Day Type:")
    print(f"  {'Type':<15} {'N':>5} {'Wins':>5} {'Losses':>6} {'WR%':>6} {'Avg MFE':>8}")
    if "outcome" in out_df.columns:
        for dt in sorted(out_df["day_type_v3"].unique()):
            subset = out_df[out_df["day_type_v3"] == dt]
            wins = (subset["outcome"] == "HIT_C1").sum()
            losses = (subset["outcome"] == "HIT_STOP").sum()
            decisive = wins + losses
            wr = wins / decisive * 100 if decisive > 0 else 0
            # MFE
            risk = np.where(subset["direction"] == "LONG",
                           subset["entry_price"] - subset["stop_price"],
                           subset["stop_price"] - subset["entry_price"])
            risk = np.maximum(risk, 0.01)
            mfe_r = subset["mfe_pts"].values / risk
            avg_mfe = np.nanmean(mfe_r)
            print(f"  {dt:<15} {len(subset):>5} {wins:>5} {losses:>6} {wr:>5.1f}% {avg_mfe:>7.2f}R")

    # WR for DEVELOPING phase
    print(f"\n  DEVELOPING Phase WR:")
    dev_df = out_df[out_df["is_developing_v3"] == True]
    if len(dev_df) > 0 and "outcome" in dev_df.columns:
        dev_wins = (dev_df["outcome"] == "HIT_C1").sum()
        dev_losses = (dev_df["outcome"] == "HIT_STOP").sum()
        dev_decisive = dev_wins + dev_losses
        dev_wr = dev_wins / dev_decisive * 100 if dev_decisive > 0 else 0
        print(f"    N={len(dev_df)}, Wins={dev_wins}, Losses={dev_losses}, WR={dev_wr:.1f}%")
    else:
        print(f"    N={len(dev_df)} (no outcome data)")

    non_dev = out_df[out_df["is_developing_v3"] == False]
    if len(non_dev) > 0 and "outcome" in non_dev.columns:
        nd_wins = (non_dev["outcome"] == "HIT_C1").sum()
        nd_losses = (non_dev["outcome"] == "HIT_STOP").sum()
        nd_decisive = nd_wins + nd_losses
        nd_wr = nd_wins / nd_decisive * 100 if nd_decisive > 0 else 0
        print(f"    Non-DEVELOPING: N={len(non_dev)}, WR={nd_wr:.1f}%")

    print(f"\n  Runtime: {elapsed:.1f}s")
    print(f"{'='*60}")

    return out_df


if __name__ == "__main__":
    run_migration()
