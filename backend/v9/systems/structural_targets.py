"""structural_targets — resolve day-type targets to structural price levels.

When daytype_style[day_type].target == "location" (Normal, Variation,
Neutral_Center, Neutral_Extreme), this resolver computes C1/C2/C3 from
TPO structural levels (IB edges, POC, VAH, VAL) instead of R-multiples.

Michael's spec (S1_TRADE_MANAGEMENT_3CONTRACTS.md, 2026-06-20):
  Normal day SHORT from IBH: C1=IB-center, C2=VAL, C3=IBL (trail)
  Normal day LONG from IBL:  C1=IB-center, C2=VAH, C3=IBH (trail)

Flag: DAYTYPE_TARGETS_STRUCTURAL (default OFF). When OFF, returns None
(caller falls back to R-based targets). Fail-safe: any missing level
→ returns None.

Reads daytype_style from config/daytype_playbook.yaml (same file as
the playbook — no duplicate config).
"""
from __future__ import annotations

import logging
import os
from typing import Dict, Literal, Optional

logger = logging.getLogger(__name__)

# Lazy-load the YAML config (same file as daytype_playbook)
_daytype_style: Optional[Dict] = None


def _load_style() -> Dict:
    global _daytype_style
    if _daytype_style is not None:
        return _daytype_style
    try:
        import yaml
        with open("config/daytype_playbook.yaml", "r") as f:
            cfg = yaml.safe_load(f)
        _daytype_style = cfg.get("daytype_style", {})
    except Exception as e:
        logger.warning("[structural_targets] YAML load failed: %s — disabled", e)
        _daytype_style = {}
    return _daytype_style


def _find_swing_t1(direction: str, entry: float, bars: list, atr_5m: float = 7.0, k: int = 2) -> Optional[float]:
    """Williams fractal swing T1: first confirmed swing in trade direction.

    K=2: high[i] > all high[i-k..i+k] (for LONG swing-high target).
    Close-confirmed: bar close must be in the top/bottom 40% of range.
    Noise floor: skip if leg < 0.5 × ATR.
    Cap: 2 × ATR.
    """
    if not bars or len(bars) < 2 * k + 1:
        return None
    noise_floor = 0.5 * atr_5m
    cap = 2.0 * atr_5m

    for i in range(k, len(bars) - k):
        b = bars[i]
        h = float(b.get("h", b.get("high", 0)))
        l = float(b.get("l", b.get("low", 0)))
        c = float(b.get("c", b.get("close", 0)))
        rng = h - l if h > l else 0.01

        if direction == "LONG":
            # Swing high: h[i] > all neighbors
            neighbors = [float(bars[j].get("h", bars[j].get("high", 0))) for j in range(i - k, i + k + 1) if j != i]
            if h > max(neighbors):
                # Close-confirmed: close in top 40%
                if c >= l + 0.6 * rng:
                    leg = h - entry
                    if leg >= noise_floor:
                        return round(entry + min(leg, cap), 2)
        else:  # SHORT
            neighbors = [float(bars[j].get("l", bars[j].get("low", 0))) for j in range(i - k, i + k + 1) if j != i]
            if l < min(neighbors):
                if c <= h - 0.6 * rng:
                    leg = entry - l
                    if leg >= noise_floor:
                        return round(entry - min(leg, cap), 2)
    # No swing found → fall back to 1R from entry
    return None


def _pick_nearest_structure(entry: float, direction: str, structures: list, cap: float) -> Optional[float]:
    """Pick the nearest structural level beyond entry, within cap, in-direction."""
    candidates = []
    for s in structures:
        if s is None:
            continue
        s = float(s)
        dist = (s - entry) if direction == "LONG" else (entry - s)
        if 0.5 < dist <= cap:  # must be beyond entry and within cap
            candidates.append((dist, s))
    candidates.sort()
    return candidates[0][1] if candidates else None


def resolve_structural_targets(
    *,
    day_type: Optional[str],
    direction: Literal["LONG", "SHORT"],
    entry_price: float,
    stop_price: float,
    tpo_ctx: Optional[Dict],
    bars: Optional[list] = None,
    pattern_family: Optional[str] = None,
) -> Optional[Dict]:
    """Resolve structural targets for location-based day types.

    Returns dict with c1/c2/c3 prices, contracts, time_stop, trail flag.
    Returns None when:
      - flag OFF (default)
      - day_type is not location-based
      - required TPO levels missing (fail-safe)

    The caller should fall back to R-based targets when this returns None.
    """
    if not os.getenv("DAYTYPE_TARGETS_STRUCTURAL", "0").lower() in ("1", "true", "yes"):
        return None

    if day_type is None or tpo_ctx is None:
        return None

    style = _load_style().get(day_type)
    if style is None:
        return None
    target_type = style.get("target")
    if target_type not in ("location", "movement"):
        return None

    # Extract structural levels from TPO context
    ib_high = tpo_ctx.get("ib_high")
    ib_low = tpo_ctx.get("ib_low")
    poc = tpo_ctx.get("poc")
    vah = tpo_ctx.get("vah")
    val = tpo_ctx.get("val")

    # All IB levels required for Normal; fail-safe if missing
    if ib_high is None or ib_low is None or poc is None:
        logger.debug(
            "[structural_targets] missing levels for %s (ibh=%s ibl=%s poc=%s) — fail-safe to R-based",
            day_type, ib_high, ib_low, poc,
        )
        return None

    ib_center = (ib_high + ib_low) / 2.0

    # Resolve per day-type + direction
    if day_type == "Normal":
        return _resolve_normal(direction, entry_price, stop_price,
                               ib_high, ib_low, ib_center, poc, vah, val)
    elif day_type == "Variation":
        return _resolve_variation(direction, entry_price, stop_price,
                                  ib_high, ib_low, ib_center, poc, vah, val,
                                  bars=bars, family=pattern_family)
    elif day_type == "Neutral_Extreme":
        return _resolve_neutral_extreme(direction, entry_price, stop_price,
                                         ib_high, ib_low, ib_center, poc, vah, val)
    elif day_type == "Neutral_Center":
        return _resolve_neutral_center(direction, entry_price, stop_price,
                                        ib_high, ib_low, ib_center, poc, vah, val)
    elif day_type == "Trend_Normal":
        return _resolve_trend_normal(direction, entry_price, stop_price,
                                      ib_high, ib_low, ib_center, poc, vah, val,
                                      tpo_ctx)
    elif day_type == "Trend_DD":
        return _resolve_trend_dd(direction, entry_price, stop_price,
                                  ib_high, ib_low, ib_center, poc, vah, val,
                                  tpo_ctx)
    return None


def _resolve_normal(
    direction: str, entry: float, stop: float,
    ibh: float, ibl: float, ib_center: float,
    poc: float, vah: Optional[float], val: Optional[float],
) -> Dict:
    """Normal day: fade IB edges. 3 contracts.

    SHORT from IBH area: C1=IB-center, C2=VAL, C3=IBL (trail)
    LONG from IBL area:  C1=IB-center, C2=VAH, C3=IBH (trail)
    """
    if direction == "SHORT":
        c1 = ib_center
        c2 = val if val is not None else ibl
        c3 = ibl
    else:  # LONG
        c1 = ib_center
        c2 = vah if vah is not None else ibh
        c3 = ibh

    return _build_result(
        direction=direction, entry=entry, stop=stop,
        c1=c1, c2=c2, c3=c3,
        contracts=3,
        time_stop_minutes=30,
        trail_after_c2=True,
        day_type="Normal",
    )


def _resolve_variation(
    direction: str, entry: float, stop: float,
    ibh: float, ibl: float, ib_center: float,
    poc: float, vah: Optional[float], val: Optional[float],
    bars: Optional[list] = None, family: Optional[str] = None,
) -> Dict:
    """Variation day: WITH IB expansion. Michael's C2/C3 split (2026-07-01).

    C1 = first swing / ½ IB-ext (nearest)
    C2 = nearest structure CLOSER than VA edge (POC, IB-center, ½IBext)
    C3 = VA edge (VAH long / VAL short) as runner, trailed
    REV: C2=POC, C3=opposite VA edge (tight)
    """
    ib_width = ibh - ibl
    if ib_width <= 0:
        return None

    atr = 7.0  # default, overridden by cap logic in _build_result
    swing_t1 = _find_swing_t1(direction, entry, bars, atr) if bars else None

    if direction == "LONG":
        half_ext = ibh + ib_width * 0.5
        c1 = swing_t1 if swing_t1 and swing_t1 < half_ext else half_ext
        if family == "REV":
            c2 = poc
            c3 = vah if vah else ibh + ib_width
        else:
            # C2 = nearest structure closer than VA edge
            va_edge = vah if vah else ibh + ib_width
            c2 = _pick_nearest_structure(entry, "LONG",
                    [poc, ib_center, half_ext, ibh + ib_width * 0.25], abs(va_edge - entry))
            if c2 is None:
                c2 = poc if poc > entry else half_ext
            c3 = va_edge  # runner
    else:  # SHORT
        half_ext = ibl - ib_width * 0.5
        c1 = swing_t1 if swing_t1 and swing_t1 > half_ext else half_ext
        if family == "REV":
            c2 = poc
            c3 = val if val else ibl - ib_width
        else:
            va_edge = val if val else ibl - ib_width
            c2 = _pick_nearest_structure(entry, "SHORT",
                    [poc, ib_center, half_ext, ibl - ib_width * 0.25], abs(entry - va_edge))
            if c2 is None:
                c2 = poc if poc < entry else half_ext
            c3 = va_edge

    return _build_result(
        direction=direction, entry=entry, stop=stop,
        c1=c1, c2=c2, c3=c3,
        contracts=3,
        time_stop_minutes=60,
        trail_after_c2=True,
        day_type="Variation",
    )


def _resolve_neutral_extreme(
    direction: str, entry: float, stop: float,
    ibh: float, ibl: float, ib_center: float,
    poc: float, vah: Optional[float], val: Optional[float],
) -> Dict:
    """Neutral Extreme: fade VA edges to POC, trail toward winner. 3 contracts.

    SHORT from VAH area: C1=POC, C2=opposite edge (VAL/IBL), C3=winning extreme (trail)
    LONG from VAL area:  C1=POC, C2=opposite edge (VAH/IBH), C3=winning extreme (trail)
    """
    if direction == "SHORT":
        c1 = poc
        c2 = val if val is not None else ibl
        c3 = ibl  # trail toward winning extreme
    else:
        c1 = poc
        c2 = vah if vah is not None else ibh
        c3 = ibh

    return _build_result(
        direction=direction, entry=entry, stop=stop,
        c1=c1, c2=c2, c3=c3,
        contracts=3,
        time_stop_minutes=45,
        trail_after_c2=True,
        day_type="Neutral_Extreme",
    )


def _resolve_neutral_center(
    direction: str, entry: float, stop: float,
    ibh: float, ibl: float, ib_center: float,
    poc: float, vah: Optional[float], val: Optional[float],
) -> Dict:
    """Neutral Center: fade edges to center. 3 contracts.

    SHORT: C1=POC, C2=opposite IB edge (IBL), C3=trail
    LONG:  C1=POC, C2=opposite IB edge (IBH), C3=trail
    """
    if direction == "SHORT":
        c2 = ibl
        c3 = ibl  # same as C2 for NeuC (no runner beyond)
    else:
        c2 = ibh
        c3 = ibh

    return _build_result(
        direction=direction, entry=entry, stop=stop,
        c1=poc, c2=c2, c3=c3,
        contracts=3,
        time_stop_minutes=30,
        trail_after_c2=False,
        day_type="Neutral_Center",
    )


def _resolve_trend_normal(
    direction: str, entry: float, stop: float,
    ibh: float, ibl: float, ib_center: float,
    poc: float, vah: Optional[float], val: Optional[float],
    tpo_ctx: Optional[Dict],
) -> Optional[Dict]:
    """Trend Normal: WITH trend from open; structural checkpoints. 3 contracts.

    LONG (uptrend): C1=remote checkpoint (2×IB above IBH), C2=PDH, C3=hold-to-close (trail)
    SHORT (downtrend): C1=remote checkpoint (2×IB below IBL), C2=PDL, C3=hold-to-close (trail)
    Movement-based but uses IB/PD levels as structural anchors.
    """
    ib_width = ibh - ibl
    if ib_width <= 0:
        return None

    pdh = tpo_ctx.get("pd_high") if tpo_ctx else None
    pdl = tpo_ctx.get("pd_low") if tpo_ctx else None

    if direction == "LONG":
        c1 = ibh + ib_width * 2.0  # remote checkpoint
        c2 = pdh if pdh is not None and pdh > c1 else c1 + ib_width
        c3 = c2 + ib_width  # trail target
    else:  # SHORT
        c1 = ibl - ib_width * 2.0
        c2 = pdl if pdl is not None and pdl < c1 else c1 - ib_width
        c3 = c2 - ib_width

    return _build_result(
        direction=direction, entry=entry, stop=stop,
        c1=c1, c2=c2, c3=c3,
        contracts=3,
        time_stop_minutes=None,  # no time stop on Trend_Normal
        trail_after_c2=True,
        day_type="Trend_Normal",
    )


def _resolve_trend_dd(
    direction: str, entry: float, stop: float,
    ibh: float, ibl: float, ib_center: float,
    poc: float, vah: Optional[float], val: Optional[float],
    tpo_ctx: Optional[Dict],
) -> Optional[Dict]:
    """Trend DD: CONT after breakout from structure. 3 contracts.

    LONG: C1=distribution POC (or IBH+IB), C2=measured move, C3=trail behind structure
    SHORT: mirror
    """
    ib_width = ibh - ibl
    if ib_width <= 0:
        return None

    if direction == "LONG":
        c1 = ibh + ib_width  # distribution POC proxy
        c2 = ibh + ib_width * 2.0  # measured move
        c3 = c2 + ib_width  # trail
    else:
        c1 = ibl - ib_width
        c2 = ibl - ib_width * 2.0
        c3 = c2 - ib_width

    return _build_result(
        direction=direction, entry=entry, stop=stop,
        c1=c1, c2=c2, c3=c3,
        contracts=3,
        time_stop_minutes=90,
        trail_after_c2=True,
        day_type="Trend_DD",
    )


def _cap_target(entry: float, target: float, direction: str, cap_pts: float) -> float:
    """Snap a target to the cap if it's farther than cap_pts from entry.

    FIX-16 bug fix (trade 350, 2026-07-10): a WRONG-SIDE target must never be
    capped — abs(dist) capping flipped C1=7591.6 (below LONG entry 7608.5) to
    entry+14=7622.5 (above!), masking the wrong side from _fix_side and letting
    the monotonic sort crown the 2R fallback as T1. Wrong-side targets pass
    through untouched so _fix_side handles them honestly.
    """
    wrong_side = (target <= entry) if direction == "LONG" else (target >= entry)
    if wrong_side:
        return target  # let _fix_side deal with it — never flip sides
    dist = abs(target - entry)
    if dist <= cap_pts:
        return target
    if direction == "LONG":
        return round(entry + cap_pts, 2)
    return round(entry - cap_pts, 2)


TICK = 0.25  # MES tick size


def _snap_grid(price: float) -> float:
    """Snap a price to the nearest MES tick grid (0.25)."""
    return round(round(price / TICK) * TICK, 2)


def realism_ceiling(direction: str, entry: float,
                    bars: Optional[list] = None) -> Optional[float]:
    """FIX-16 (Michael ruling 2026-07-10, trade 350): the farthest REALISTIC
    first-target price given today's session.

    T1 beyond the session extreme is wishful: the market must break new ground
    to fill it. The realistic allowance for new ground is today's own average
    breakout step — the mean increment by which the session extreme advanced
    when it DID advance ("גודל פריצות ממוצע של אותו היום").

    ceiling(LONG)  = max(day_high, entry) + avg_new_high_step
    ceiling(SHORT) = min(day_low,  entry) − avg_new_low_step

    Honest None (Rule 1) when today's bars are unavailable — caller skips the
    realism pass rather than inventing a level. `bars` injectable for tests.
    """
    try:
        if bars is None:
            from backend.v9.db.read import read_all
            bars = read_all(
                "SELECT high, low FROM v9_bars_5min_woodies "
                "WHERE ts >= date_trunc('day', now() AT TIME ZONE 'utc') "
                "  + interval '13 hours 30 minutes' "
                "ORDER BY ts ASC", {})
        if not bars or len(bars) < 3:
            return None
        highs = [float(b["high"]) for b in bars if b.get("high") is not None]
        lows = [float(b["low"]) for b in bars if b.get("low") is not None]
        if len(highs) < 3 or len(lows) < 3:
            return None
        if direction == "LONG":
            steps, run_hi = [], highs[0]
            for h in highs[1:]:
                if h > run_hi:
                    steps.append(h - run_hi)
                    run_hi = h
            day_hi = max(highs)
            # <3 fresh-ground samples → fall back to median bar range (still today's data)
            if len(steps) >= 3:
                step = sum(steps) / len(steps)
            else:
                rngs = sorted(h - l for h, l in zip(highs, lows))
                step = rngs[len(rngs) // 2]
            return _snap_grid(max(day_hi, entry) + step)
        elif direction == "SHORT":
            steps, run_lo = [], lows[0]
            for l in lows[1:]:
                if l < run_lo:
                    steps.append(run_lo - l)
                    run_lo = l
            day_lo = min(lows)
            if len(steps) >= 3:
                step = sum(steps) / len(steps)
            else:
                rngs = sorted(h - l for h, l in zip(highs, lows))
                step = rngs[len(rngs) // 2]
            return _snap_grid(min(day_lo, entry) - step)
        return None
    except Exception as e:
        logger.warning("[structural_targets] realism_ceiling unavailable (%s) — pass skipped", e)
        return None


def _build_result(
    *,
    direction: str,
    entry: float,
    stop: float,
    c1: Optional[float],
    c2: Optional[float],
    c3: Optional[float],
    contracts: int,
    time_stop_minutes: Optional[int],
    trail_after_c2: bool,
    day_type: str,
    atr_5m: float = 7.0,
) -> Optional[Dict]:
    """Build result dict. Validates + caps + floor + grid + monotonic."""
    risk = abs(entry - stop) if stop else atr_5m
    c1_floor = 0.5 * atr_5m  # ~3.5pt — kills tiny T1s (item-2 evidence 277/278)

    # Hard caps per spec: use min (not max) per D-3 ruling
    t1_cap = min(2.0 * atr_5m, 14.0)   # ~14pt
    c2_cap = min(4.0 * atr_5m, 28.0)   # ~28pt
    runner_cap = min(6.0 * atr_5m, 42.0)  # ~42pt

    # Apply caps
    if c1 is not None:
        c1 = _cap_target(entry, c1, direction, t1_cap)
    if c2 is not None:
        c2 = _cap_target(entry, c2, direction, c2_cap)
    if c3 is not None:
        c3 = _cap_target(entry, c3, direction, runner_cap)

    # C1 floor: T1 must be at least 0.5×ATR from entry (item-2, trade 277/278)
    if c1 is not None:
        dist = abs(c1 - entry)
        if dist < c1_floor:
            if direction == "LONG":
                c1 = entry + c1_floor
            else:
                c1 = entry - c1_floor

    # Wrong-side protection: targets must be on the correct side of entry.
    # Replace wrong-side targets with R-based fallbacks rather than None.
    def _fix_side(tgt, tgt_name, r_mult):
        if tgt is None:
            return tgt
        if direction == "LONG" and tgt <= entry:
            logger.warning("[structural_targets] %s=%.2f on wrong side of LONG entry=%.2f → R-fallback",
                           tgt_name, tgt, entry)
            return entry + r_mult * risk
        if direction == "SHORT" and tgt >= entry:
            logger.warning("[structural_targets] %s=%.2f on wrong side of SHORT entry=%.2f → R-fallback",
                           tgt_name, tgt, entry)
            return entry - r_mult * risk
        return tgt
    c1 = _fix_side(c1, "c1", 1.0)
    c2 = _fix_side(c2, "c2", 2.0)
    c3 = _fix_side(c3, "c3", 3.0)

    # Monotonicity: |C1−entry| < |C2−entry| < |C3−entry|
    # If violated, sort by distance from entry
    targets = [(c1, "c1"), (c2, "c2"), (c3, "c3")]
    valid = [(abs(t - entry), t, n) for t, n in targets if t is not None]
    valid.sort()
    if len(valid) >= 2 and any(valid[i][0] >= valid[i + 1][0] for i in range(len(valid) - 1)):
        logger.info("[structural_targets] monotonicity fix: reordering targets by distance from entry")
        # Deduplicate: if two targets have the same distance, nudge the farther one
        for i in range(1, len(valid)):
            if valid[i][0] <= valid[i - 1][0]:
                nudge = TICK * (i + 1)
                if direction == "LONG":
                    valid[i] = (valid[i - 1][0] + nudge, valid[i - 1][1] + nudge, valid[i][2])
                else:
                    valid[i] = (valid[i - 1][0] + nudge, valid[i - 1][1] - nudge, valid[i][2])
    # Reassign
    c1 = valid[0][1] if len(valid) > 0 else None
    c2 = valid[1][1] if len(valid) > 1 else None
    c3 = valid[2][1] if len(valid) > 2 else None

    # Grid alignment: snap all targets to 0.25 tick grid (item-2, trade 277/278)
    if c1 is not None:
        c1 = _snap_grid(c1)
    if c2 is not None:
        c2 = _snap_grid(c2)
    if c3 is not None:
        c3 = _snap_grid(c3)

    return {
        "t1_price": c1,
        "t2_price": c2,
        "t3_price": c3,
        "contracts": contracts,
        "time_stop_minutes": time_stop_minutes,
        "trail_after_t2": trail_after_c2,
        "structural": True,
        "day_type": day_type,
        "no_trade": False,
    }
