"""S2 Pattern Detection Probe — per-pattern geometry sub-conditions.

Provides step-by-step visibility into WHY a pattern has/hasn't triggered.
Pure read-only probers. Stop-at-first-fail for clear root-cause identification.

Source: BUILD_STATUS_ENDPOINT_DESIGN.md §4.1 detection sub-layer
"""

import logging
from typing import List, Optional

from backend.v9.systems.build_status.types import Component

# Flag geometry constants (source: patterns/flags.py lines 32-41)
from backend.v9.systems.five_min.patterns.flags import (
    _find_pole_bull, _find_pole_bear,
    TICK_SIZE as FLAG_TICK,
    MIN_BARS_REQUIRED as FLAG_MIN_BARS_REQ,
    FLAG_MIN_BARS, FLAG_MAX_BARS, FLAG_MAX_RETRACE_PCT,
    POLE_MIN_BARS, POLE_MAX_BARS, POLE_MIN_HEIGHT_TICKS,
    SEARCH_WINDOW as FLAG_SEARCH_WINDOW,
)

# H&S geometry constants (source: patterns/head_shoulders.py lines 26-31)
from backend.v9.systems.five_min.patterns.head_shoulders import (
    _swing_lows as hs_swing_lows,
    _swing_highs as hs_swing_highs,
    _shoulders_symmetric,
    MIN_BARS_REQUIRED as HS_MIN_BARS_REQ,
    SEARCH_WINDOW as HS_SEARCH_WINDOW,
    PIVOT_LOOKBACK as HS_PIVOT_LOOKBACK,
    HEAD_MIN_EXT_TICKS,
    TICK_SIZE as HS_TICK,
)

# Double Bottom/Top constants (source: patterns/double_bt.py lines 30-37)
from backend.v9.systems.five_min.patterns.double_bt import (
    _swing_lows as dbt_swing_lows,
    _swing_highs as dbt_swing_highs,
    MIN_BARS_REQUIRED as DBT_MIN_BARS_REQ,
    PIVOT_LOOKBACK as DBT_PIVOT_LOOKBACK,
    TROUGH_SYM_PCT, TROUGH_MIN_WIDTH_BARS, PEAK_MAX_WIDTH_BARS,
    TICK_SIZE as DBT_TICK,
    _trough_width_bars, _peak_width_bars,
)

# OFA constants (source: five_min_system.py lines 26-33)
from backend.v9.systems.five_min.five_min_system import (
    MIN_BARS_REQUIRED as OFA_MIN_BARS_REQ,
    DROP_THRESHOLD_PCT,
    EXPANSION_MIN_PT, EXPANSION_MAX_PT,
    POC_RETURN_TOLERANCE_PT,
    LOOKBACK_BARS, LOOKBACK_MAX_VOL_RATIO,
)

logger = logging.getLogger(__name__)


def probe_pattern(pattern_id: str, bar_buffer: list, five_min_system=None) -> List[Component]:
    """Probe detection geometry for a given S2 pattern.

    Returns a list of Component objects representing step-by-step probe results.
    Stops at first failing step. Returns [] for unknown patterns or on error.
    """
    try:
        dispatch = {
            "BULL_FLAG_LONG": _probe_bull_flag,
            "BEAR_FLAG_SHORT": _probe_bear_flag,
            "INVERSE_HNS_LONG": _probe_inverse_hns,
            "HNS_TOP_SHORT": _probe_hns_top,
            "DOUBLE_BOTTOM_EE_LONG": _probe_double_bottom,
            "DOUBLE_TOP_AA_SHORT": _probe_double_top,
            "REACTIVE_LONG": _probe_reactive_long,
            "REACTIVE_SHORT": _probe_reactive_short,
            "INITIATIVE_LONG": _probe_initiative_long,
            "INITIATIVE_SHORT": _probe_initiative_short,
        }
        prober = dispatch.get(pattern_id)
        if prober is None:
            return []
        return prober(bar_buffer)
    except Exception as e:
        logger.warning("[BuildStatus/Probe] probe_pattern(%s) raised: %s", pattern_id, e)
        return []


# ── Flag probers ─────────────────────────────────────────────────────────────


def _probe_bull_flag(bars: list) -> List[Component]:
    components = []

    # Step 1: min_bars
    ok = len(bars) >= FLAG_MIN_BARS_REQ
    components.append(Component(
        stage="detection", key="min_bars",
        spec=f"buffer ≥ {FLAG_MIN_BARS_REQ}",
        present=ok,
        value=f"buffer={len(bars)} {'≥' if ok else '<'} {FLAG_MIN_BARS_REQ} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    # Step 2: pole_found
    pole = _find_pole_bull(bars)
    ok = pole is not None
    if ok:
        value = f"pole={pole['pole_bars']} bars · height={pole['pole_height']:.2f}pts ✓"
    else:
        value = "no valid pole (need ≥5 bullish bars, ≥4.00pt height)"
    components.append(Component(
        stage="detection", key="pole_found",
        spec=f"_find_pole_bull: ≥{POLE_MIN_BARS} bars, ≥{POLE_MIN_HEIGHT_TICKS}T height",
        present=ok, value=value,
    ))
    if not ok:
        return components

    # Step 3: flag_length
    w = pole["window"]
    top_idx = pole["top_idx"]
    flag_start = top_idx + 1
    flag_end = len(w) - 2
    flag_len = max(0, flag_end - flag_start + 1) if flag_end >= flag_start else 0
    ok = FLAG_MIN_BARS <= flag_len <= FLAG_MAX_BARS
    components.append(Component(
        stage="detection", key="flag_length",
        spec=f"flag bars in [{FLAG_MIN_BARS}, {FLAG_MAX_BARS}]",
        present=ok,
        value=f"flag={flag_len} bars {'✓' if ok else f'(out of range {FLAG_MIN_BARS}–{FLAG_MAX_BARS}) ✗'}",
    ))
    if not ok:
        return components

    # Step 4: flag_retrace
    flag_bars = w[flag_start:flag_end + 1]
    flag_low = min(b["l"] for b in flag_bars)
    retrace = (pole["top_high"] - flag_low) / pole["pole_height"] if pole["pole_height"] > 0 else 1.0
    ok = retrace <= FLAG_MAX_RETRACE_PCT
    pct = retrace * 100
    components.append(Component(
        stage="detection", key="flag_retrace",
        spec=f"retrace ≤ {int(FLAG_MAX_RETRACE_PCT*100)}%",
        present=ok,
        value=f"retrace={pct:.1f}% {'≤' if ok else '>'} {int(FLAG_MAX_RETRACE_PCT*100)}% {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    # Step 5: breakout
    flag_high = max(b["h"] for b in flag_bars)
    trigger = flag_high + FLAG_TICK
    last_close = w[-1]["c"]
    gap = last_close - trigger
    ok = last_close > trigger
    components.append(Component(
        stage="detection", key="breakout",
        spec=f"last_bar.close > flag_high + {FLAG_TICK}",
        present=ok,
        value=f"close={last_close:.2f} · trigger={trigger:.2f} · gap={gap:+.2f}pts {'✓' if ok else '✗'}",
    ))
    return components


def _probe_bear_flag(bars: list) -> List[Component]:
    components = []

    ok = len(bars) >= FLAG_MIN_BARS_REQ
    components.append(Component(
        stage="detection", key="min_bars",
        spec=f"buffer ≥ {FLAG_MIN_BARS_REQ}",
        present=ok,
        value=f"buffer={len(bars)} {'≥' if ok else '<'} {FLAG_MIN_BARS_REQ} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    pole = _find_pole_bear(bars)
    ok = pole is not None
    if ok:
        value = f"pole={pole['pole_bars']} bars · height={pole['pole_height']:.2f}pts ✓"
    else:
        value = "no valid pole (need ≥5 bearish bars, ≥4.00pt height)"
    components.append(Component(
        stage="detection", key="pole_found",
        spec=f"_find_pole_bear: ≥{POLE_MIN_BARS} bars, ≥{POLE_MIN_HEIGHT_TICKS}T height",
        present=ok, value=value,
    ))
    if not ok:
        return components

    w = pole["window"]
    bot_idx = pole["bottom_idx"]
    flag_start = bot_idx + 1
    flag_end = len(w) - 2
    flag_len = max(0, flag_end - flag_start + 1) if flag_end >= flag_start else 0
    ok = FLAG_MIN_BARS <= flag_len <= FLAG_MAX_BARS
    components.append(Component(
        stage="detection", key="flag_length",
        spec=f"flag bars in [{FLAG_MIN_BARS}, {FLAG_MAX_BARS}]",
        present=ok,
        value=f"flag={flag_len} bars {'✓' if ok else f'(out of range {FLAG_MIN_BARS}–{FLAG_MAX_BARS}) ✗'}",
    ))
    if not ok:
        return components

    flag_bars = w[flag_start:flag_end + 1]
    flag_high = max(b["h"] for b in flag_bars)
    retrace = (flag_high - pole["bottom_low"]) / pole["pole_height"] if pole["pole_height"] > 0 else 1.0
    ok = retrace <= FLAG_MAX_RETRACE_PCT
    pct = retrace * 100
    components.append(Component(
        stage="detection", key="flag_retrace",
        spec=f"retrace ≤ {int(FLAG_MAX_RETRACE_PCT*100)}%",
        present=ok,
        value=f"retrace={pct:.1f}% {'≤' if ok else '>'} {int(FLAG_MAX_RETRACE_PCT*100)}% {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    flag_low = min(b["l"] for b in flag_bars)
    trigger = flag_low - FLAG_TICK
    last_close = w[-1]["c"]
    gap = trigger - last_close
    ok = last_close < trigger
    components.append(Component(
        stage="detection", key="breakout",
        spec=f"last_bar.close < flag_low - {FLAG_TICK}",
        present=ok,
        value=f"close={last_close:.2f} · trigger={trigger:.2f} · gap={gap:+.2f}pts {'✓' if ok else '✗'}",
    ))
    return components


# ── H&S probers ──────────────────────────────────────────────────────────────


def _probe_inverse_hns(bars: list) -> List[Component]:
    components = []

    ok = len(bars) >= HS_MIN_BARS_REQ
    components.append(Component(
        stage="detection", key="min_bars",
        spec=f"buffer ≥ {HS_MIN_BARS_REQ}",
        present=ok,
        value=f"buffer={len(bars)} {'≥' if ok else '<'} {HS_MIN_BARS_REQ} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    window = bars[-min(len(bars), HS_SEARCH_WINDOW):]
    lows = hs_swing_lows(window)
    ok = len(lows) >= 3
    components.append(Component(
        stage="detection", key="swing_lows_found",
        spec="≥3 swing lows in search window",
        present=ok,
        value=f"{len(lows)} swing lows found in last {len(window)} bars {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    # Find valid LS/HEAD/RS triplet
    triplet = None
    for i in range(len(lows) - 2):
        ls_idx, ls_price = lows[i]
        h_idx, h_price = lows[i + 1]
        rs_idx, rs_price = lows[i + 2]
        if h_price < ls_price and h_price < rs_price:
            if _shoulders_symmetric(ls_price, rs_price, h_price, "LONG"):
                triplet = (ls_idx, ls_price, h_idx, h_price, rs_idx, rs_price)
                break

    ok = triplet is not None
    if ok:
        _, ls_p, _, h_p, _, rs_p = triplet
        value = f"LS={ls_p:.2f} · HEAD={h_p:.2f} · RS={rs_p:.2f} · sym=OK ✓"
    else:
        value = "no valid triplet (head must be lowest, shoulders symmetric)"
    components.append(Component(
        stage="detection", key="hns_structure",
        spec="LS/HEAD/RS triplet with head lowest + symmetric shoulders",
        present=ok, value=value,
    ))
    if not ok:
        return components

    # Neckline breakout
    ls_idx, _, h_idx, _, rs_idx, _ = triplet
    highs = hs_swing_highs(window)
    nl_highs = [h for idx, h in highs if ls_idx < idx < rs_idx]
    if not nl_highs:
        nl_highs = [window[j]["h"] for j in range(ls_idx + 1, rs_idx) if j < len(window)]
    neckline = max(nl_highs) if nl_highs else window[-1]["h"]
    trigger = neckline + HS_TICK
    last_close = window[-1]["c"]
    gap = last_close - trigger
    ok = last_close > trigger
    components.append(Component(
        stage="detection", key="neckline_breakout",
        spec=f"last_bar.close > neckline + {HS_TICK}",
        present=ok,
        value=f"close={last_close:.2f} · neckline={neckline:.2f} · gap={gap:+.2f}pts {'✓' if ok else '✗'}",
    ))
    return components


def _probe_hns_top(bars: list) -> List[Component]:
    components = []

    ok = len(bars) >= HS_MIN_BARS_REQ
    components.append(Component(
        stage="detection", key="min_bars",
        spec=f"buffer ≥ {HS_MIN_BARS_REQ}",
        present=ok,
        value=f"buffer={len(bars)} {'≥' if ok else '<'} {HS_MIN_BARS_REQ} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    window = bars[-min(len(bars), HS_SEARCH_WINDOW):]
    highs = hs_swing_highs(window)
    ok = len(highs) >= 3
    components.append(Component(
        stage="detection", key="swing_highs_found",
        spec="≥3 swing highs in search window",
        present=ok,
        value=f"{len(highs)} swing highs found in last {len(window)} bars {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    triplet = None
    for i in range(len(highs) - 2):
        ls_idx, ls_price = highs[i]
        h_idx, h_price = highs[i + 1]
        rs_idx, rs_price = highs[i + 2]
        if h_price > ls_price and h_price > rs_price:
            if _shoulders_symmetric(ls_price, rs_price, h_price, "SHORT"):
                triplet = (ls_idx, ls_price, h_idx, h_price, rs_idx, rs_price)
                break

    ok = triplet is not None
    if ok:
        _, ls_p, _, h_p, _, rs_p = triplet
        value = f"LS={ls_p:.2f} · HEAD={h_p:.2f} · RS={rs_p:.2f} · sym=OK ✓"
    else:
        value = "no valid triplet (head must be highest, shoulders symmetric)"
    components.append(Component(
        stage="detection", key="hns_structure",
        spec="LS/HEAD/RS triplet with head highest + symmetric shoulders",
        present=ok, value=value,
    ))
    if not ok:
        return components

    ls_idx, _, h_idx, _, rs_idx, _ = triplet
    lows = hs_swing_lows(window)
    nl_lows = [lo for idx, lo in lows if ls_idx < idx < rs_idx]
    if not nl_lows:
        nl_lows = [window[j]["l"] for j in range(ls_idx + 1, rs_idx) if j < len(window)]
    neckline = min(nl_lows) if nl_lows else window[-1]["l"]
    trigger = neckline - HS_TICK
    last_close = window[-1]["c"]
    gap = trigger - last_close
    ok = last_close < trigger
    components.append(Component(
        stage="detection", key="neckline_breakout",
        spec=f"last_bar.close < neckline - {HS_TICK}",
        present=ok,
        value=f"close={last_close:.2f} · neckline={neckline:.2f} · gap={gap:+.2f}pts {'✓' if ok else '✗'}",
    ))
    return components


# ── Double Bottom/Top probers ────────────────────────────────────────────────


def _probe_double_bottom(bars: list) -> List[Component]:
    components = []

    ok = len(bars) >= DBT_MIN_BARS_REQ
    components.append(Component(
        stage="detection", key="min_bars",
        spec=f"buffer ≥ {DBT_MIN_BARS_REQ}",
        present=ok,
        value=f"buffer={len(bars)} {'≥' if ok else '<'} {DBT_MIN_BARS_REQ} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    window = bars[-min(len(bars), 30):]
    lows = dbt_swing_lows(window)
    ok = len(lows) >= 2
    components.append(Component(
        stage="detection", key="swing_lows_found",
        spec="≥2 swing lows in search window",
        present=ok,
        value=f"{len(lows)} swing lows found {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    # Find symmetric pair
    pair = None
    for i in range(len(lows) - 1):
        t1_idx, t1_price = lows[i]
        t2_idx, t2_price = lows[i + 1]
        lower = min(t1_price, t2_price)
        if lower > 0 and abs(t1_price - t2_price) / lower <= TROUGH_SYM_PCT:
            pair = (t1_idx, t1_price, t2_idx, t2_price)
            break

    ok = pair is not None
    if ok:
        _, t1_p, _, t2_p = pair
        diff_pct = abs(t1_p - t2_p) / min(t1_p, t2_p) * 100
        value = f"T1={t1_p:.2f} · T2={t2_p:.2f} · diff={diff_pct:.1f}% ≤ {TROUGH_SYM_PCT*100:.0f}% ✓"
    else:
        value = f"no symmetric pair found (need diff ≤ {TROUGH_SYM_PCT*100:.0f}%)"
    components.append(Component(
        stage="detection", key="trough_pair",
        spec=f"2 troughs within {TROUGH_SYM_PCT*100:.0f}% of each other",
        present=ok, value=value,
    ))
    if not ok:
        return components

    # Eve variant check
    t1_idx, t1_p, t2_idx, t2_p = pair
    w1 = _trough_width_bars(window, t1_idx, t1_p)
    w2 = _trough_width_bars(window, t2_idx, t2_p)
    ok = w1 >= TROUGH_MIN_WIDTH_BARS and w2 >= TROUGH_MIN_WIDTH_BARS
    components.append(Component(
        stage="detection", key="eve_variant",
        spec=f"each trough width ≥ {TROUGH_MIN_WIDTH_BARS} bars (Eve rounded)",
        present=ok,
        value=f"T1 width={w1} bars · T2 width={w2} bars {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    # Neckline breakout
    nl_highs = [window[j]["h"] for j in range(t1_idx + 1, t2_idx) if j < len(window)]
    neckline = max(nl_highs) if nl_highs else window[-1]["h"]
    trigger = neckline + DBT_TICK
    last_close = window[-1]["c"]
    gap = last_close - trigger
    ok = last_close > trigger
    components.append(Component(
        stage="detection", key="neckline_breakout",
        spec=f"last_bar.close > neckline + {DBT_TICK}",
        present=ok,
        value=f"close={last_close:.2f} · neckline={neckline:.2f} · gap={gap:+.2f}pts {'✓' if ok else '✗'}",
    ))
    return components


def _probe_double_top(bars: list) -> List[Component]:
    components = []

    ok = len(bars) >= DBT_MIN_BARS_REQ
    components.append(Component(
        stage="detection", key="min_bars",
        spec=f"buffer ≥ {DBT_MIN_BARS_REQ}",
        present=ok,
        value=f"buffer={len(bars)} {'≥' if ok else '<'} {DBT_MIN_BARS_REQ} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    window = bars[-min(len(bars), 30):]
    highs = dbt_swing_highs(window)
    ok = len(highs) >= 2
    components.append(Component(
        stage="detection", key="swing_highs_found",
        spec="≥2 swing highs in search window",
        present=ok,
        value=f"{len(highs)} swing highs found {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    pair = None
    for i in range(len(highs) - 1):
        p1_idx, p1_price = highs[i]
        p2_idx, p2_price = highs[i + 1]
        lower = min(p1_price, p2_price)
        if lower > 0 and abs(p1_price - p2_price) / lower <= TROUGH_SYM_PCT:
            pair = (p1_idx, p1_price, p2_idx, p2_price)
            break

    ok = pair is not None
    if ok:
        _, p1_p, _, p2_p = pair
        diff_pct = abs(p1_p - p2_p) / min(p1_p, p2_p) * 100
        value = f"P1={p1_p:.2f} · P2={p2_p:.2f} · diff={diff_pct:.1f}% ≤ {TROUGH_SYM_PCT*100:.0f}% ✓"
    else:
        value = f"no symmetric pair found (need diff ≤ {TROUGH_SYM_PCT*100:.0f}%)"
    components.append(Component(
        stage="detection", key="peak_pair",
        spec=f"2 peaks within {TROUGH_SYM_PCT*100:.0f}% of each other",
        present=ok, value=value,
    ))
    if not ok:
        return components

    p1_idx, p1_p, p2_idx, p2_p = pair
    w1 = _peak_width_bars(window, p1_idx, p1_p)
    w2 = _peak_width_bars(window, p2_idx, p2_p)
    ok = w1 <= PEAK_MAX_WIDTH_BARS and w2 <= PEAK_MAX_WIDTH_BARS
    components.append(Component(
        stage="detection", key="adam_variant",
        spec=f"each peak width ≤ {PEAK_MAX_WIDTH_BARS} bars (Adam sharp)",
        present=ok,
        value=f"P1 width={w1} bars · P2 width={w2} bars {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    nl_lows = [window[j]["l"] for j in range(p1_idx + 1, p2_idx) if j < len(window)]
    neckline = min(nl_lows) if nl_lows else window[-1]["l"]
    trigger = neckline - DBT_TICK
    last_close = window[-1]["c"]
    gap = trigger - last_close
    ok = last_close < trigger
    components.append(Component(
        stage="detection", key="neckline_breakout",
        spec=f"last_bar.close < neckline - {DBT_TICK}",
        present=ok,
        value=f"close={last_close:.2f} · neckline={neckline:.2f} · gap={gap:+.2f}pts {'✓' if ok else '✗'}",
    ))
    return components


# ── OFA Reactive probers ─────────────────────────────────────────────────────


def _probe_reactive_long(bars: list) -> List[Component]:
    components = []

    ok = len(bars) >= OFA_MIN_BARS_REQ
    components.append(Component(
        stage="detection", key="min_bars",
        spec=f"buffer ≥ {OFA_MIN_BARS_REQ}",
        present=ok,
        value=f"buffer={len(bars)} {'≥' if ok else '<'} {OFA_MIN_BARS_REQ} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    b1, b2, b3, b4 = bars[-4], bars[-3], bars[-2], bars[-1]
    b1_vol = b1.get("v", 0) or 0

    # Step 2: b1_sellers
    ok = b1["c"] < b1["o"] and b1_vol > 0
    components.append(Component(
        stage="detection", key="b1_sellers",
        spec="b1.close < b1.open AND b1.volume > 0",
        present=ok,
        value=f"b1 close={b1['c']:.2f} open={b1['o']:.2f} dir={'bear' if b1['c'] < b1['o'] else 'bull'} vol={b1_vol}",
    ))
    if not ok:
        return components

    # Step 3: b2_volume_drop
    b2_vol = b2.get("v", 0) or 0
    threshold = b1_vol * DROP_THRESHOLD_PCT
    ok = b2_vol <= threshold if b1_vol > 0 else False
    ratio = b2_vol / b1_vol if b1_vol > 0 else 0
    components.append(Component(
        stage="detection", key="b2_volume_drop",
        spec=f"b2.volume ≤ b1.volume × {DROP_THRESHOLD_PCT} (90% drop)",
        present=ok,
        value=f"b2_vol={b2_vol} · b1_vol={b1_vol} · ratio={ratio:.2f} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    # Step 4: b3_buyers
    ok = b3["c"] > b3["o"]
    components.append(Component(
        stage="detection", key="b3_buyers",
        spec="b3.close > b3.open (bullish bar)",
        present=ok,
        value=f"b3 close={b3['c']:.2f} open={b3['o']:.2f} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    # Step 5: b4_confirm
    ok = b4["c"] > b4["o"] and b4["c"] > b3["h"]
    components.append(Component(
        stage="detection", key="b4_confirm",
        spec="b4.close > b4.open AND b4.close > b3.high",
        present=ok,
        value=f"b4 close={b4['c']:.2f} · b3_high={b3['h']:.2f} · above={'T' if b4['c'] > b3['h'] else 'F'}",
    ))
    if not ok:
        return components

    # Step 6: lookback_quiet
    lookback = bars[-OFA_MIN_BARS_REQ:-(OFA_MIN_BARS_REQ - LOOKBACK_BARS)]
    if lookback:
        max_lb_vol = max(b.get("v", 0) for b in lookback)
        thresh = b1_vol * LOOKBACK_MAX_VOL_RATIO
        ok = max_lb_vol < thresh
    else:
        max_lb_vol = 0
        thresh = 0
        ok = False
    components.append(Component(
        stage="detection", key="lookback_quiet",
        spec=f"max(lookback {LOOKBACK_BARS} bars vol) < b1_vol × {LOOKBACK_MAX_VOL_RATIO}",
        present=ok,
        value=f"lookback_max={max_lb_vol} · threshold={thresh:.0f} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    # Footprint-dependent (always pass for display)
    components.append(Component(
        stage="detection", key="belly_cot_amt",
        spec="COT > AMT + belly confirmation (footprint-dependent)",
        present=True,
        value="footprint-dependent · not probed here",
    ))
    return components


def _probe_reactive_short(bars: list) -> List[Component]:
    components = []

    ok = len(bars) >= OFA_MIN_BARS_REQ
    components.append(Component(
        stage="detection", key="min_bars",
        spec=f"buffer ≥ {OFA_MIN_BARS_REQ}",
        present=ok,
        value=f"buffer={len(bars)} {'≥' if ok else '<'} {OFA_MIN_BARS_REQ} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    b1, b2, b3, b4 = bars[-4], bars[-3], bars[-2], bars[-1]
    b1_vol = b1.get("v", 0) or 0

    ok = b1["c"] > b1["o"] and b1_vol > 0
    components.append(Component(
        stage="detection", key="b1_buyers",
        spec="b1.close > b1.open AND b1.volume > 0 (buyers bar)",
        present=ok,
        value=f"b1 close={b1['c']:.2f} open={b1['o']:.2f} dir={'bull' if b1['c'] > b1['o'] else 'bear'} vol={b1_vol}",
    ))
    if not ok:
        return components

    b2_vol = b2.get("v", 0) or 0
    threshold = b1_vol * DROP_THRESHOLD_PCT
    ok = b2_vol <= threshold if b1_vol > 0 else False
    ratio = b2_vol / b1_vol if b1_vol > 0 else 0
    components.append(Component(
        stage="detection", key="b2_volume_drop",
        spec=f"b2.volume ≤ b1.volume × {DROP_THRESHOLD_PCT}",
        present=ok,
        value=f"b2_vol={b2_vol} · b1_vol={b1_vol} · ratio={ratio:.2f} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    ok = b3["c"] < b3["o"]
    components.append(Component(
        stage="detection", key="b3_sellers",
        spec="b3.close < b3.open (bearish bar)",
        present=ok,
        value=f"b3 close={b3['c']:.2f} open={b3['o']:.2f} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    ok = b4["c"] < b4["o"] and b4["c"] < b3["l"]
    components.append(Component(
        stage="detection", key="b4_confirm",
        spec="b4.close < b4.open AND b4.close < b3.low",
        present=ok,
        value=f"b4 close={b4['c']:.2f} · b3_low={b3['l']:.2f} · below={'T' if b4['c'] < b3['l'] else 'F'}",
    ))
    if not ok:
        return components

    lookback = bars[-OFA_MIN_BARS_REQ:-(OFA_MIN_BARS_REQ - LOOKBACK_BARS)]
    if lookback:
        max_lb_vol = max(b.get("v", 0) for b in lookback)
        thresh = b1_vol * LOOKBACK_MAX_VOL_RATIO
        ok = max_lb_vol < thresh
    else:
        max_lb_vol = 0
        thresh = 0
        ok = False
    components.append(Component(
        stage="detection", key="lookback_quiet",
        spec=f"max(lookback {LOOKBACK_BARS} bars vol) < b1_vol × {LOOKBACK_MAX_VOL_RATIO}",
        present=ok,
        value=f"lookback_max={max_lb_vol} · threshold={thresh:.0f} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    components.append(Component(
        stage="detection", key="belly_cot_amt",
        spec="COT < AMT + belly confirmation (footprint-dependent)",
        present=True,
        value="footprint-dependent · not probed here",
    ))
    return components


# ── OFA Initiative probers ───────────────────────────────────────────────────


def _probe_initiative_long(bars: list) -> List[Component]:
    components = []

    ok = len(bars) >= OFA_MIN_BARS_REQ
    components.append(Component(
        stage="detection", key="min_bars",
        spec=f"buffer ≥ {OFA_MIN_BARS_REQ}",
        present=ok,
        value=f"buffer={len(bars)} {'≥' if ok else '<'} {OFA_MIN_BARS_REQ} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    b1, b2, b3, b4 = bars[-4], bars[-3], bars[-2], bars[-1]
    b1_range = b1["h"] - b1["l"]

    # Step 2: b1_expansion
    ok = EXPANSION_MIN_PT <= b1_range <= EXPANSION_MAX_PT
    components.append(Component(
        stage="detection", key="b1_expansion",
        spec=f"b1 range in [{EXPANSION_MIN_PT}, {EXPANSION_MAX_PT}] pts",
        present=ok,
        value=f"b1 range={b1_range:.2f} · need [{EXPANSION_MIN_PT}, {EXPANSION_MAX_PT}] {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    # Step 3: b1_bull
    ok = b1["c"] > b1["o"]
    components.append(Component(
        stage="detection", key="b1_bull",
        spec="b1.close > b1.open (bullish expansion bar)",
        present=ok,
        value=f"b1 close={b1['c']:.2f} open={b1['o']:.2f} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    # Step 4: b2_test
    b2_higher_low = b2["l"] > b1["l"]
    b2_poc = b2.get("poc_vol") or b2.get("poc")
    b2_poc_return = b2_poc is not None and abs(b2["c"] - b2_poc) <= POC_RETURN_TOLERANCE_PT
    ok = b2_higher_low or b2_poc_return
    components.append(Component(
        stage="detection", key="b2_test",
        spec="b2.low > b1.low (higher low) OR b2 POC return",
        present=ok,
        value=f"b2_low={b2['l']:.2f} · b1_low={b1['l']:.2f} · higher_low={'T' if b2_higher_low else 'F'} · poc_return={'T' if b2_poc_return else 'F'}",
    ))
    if not ok:
        return components

    # Step 5: b3_joining
    b3_range = b3["h"] - b3["l"]
    ok = b3_range > b1_range
    components.append(Component(
        stage="detection", key="b3_joining",
        spec="b3 range > b1 range (expansion joining)",
        present=ok,
        value=f"b3_range={b3_range:.2f} · b1_range={b1_range:.2f} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    # Step 6: b4_test
    ok = b4["l"] >= b2["l"] and b4["c"] > b1["h"]
    components.append(Component(
        stage="detection", key="b4_test",
        spec="b4.low ≥ b2.low AND b4.close > b1.high",
        present=ok,
        value=f"b4_close={b4['c']:.2f} · b1_high={b1['h']:.2f} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    # Step 7: lookback_quiet
    b1_vol = b1.get("v", 0) or 0
    lookback = bars[-OFA_MIN_BARS_REQ:-(OFA_MIN_BARS_REQ - LOOKBACK_BARS)]
    if lookback and b1_vol > 0:
        max_lb_vol = max(b.get("v", 0) for b in lookback)
        thresh = b1_vol * LOOKBACK_MAX_VOL_RATIO
        ok = max_lb_vol < thresh
    else:
        max_lb_vol = 0
        thresh = 0
        ok = False
    components.append(Component(
        stage="detection", key="lookback_quiet",
        spec=f"max(lookback {LOOKBACK_BARS} bars vol) < b1_vol × {LOOKBACK_MAX_VOL_RATIO}",
        present=ok,
        value=f"lookback_max={max_lb_vol} · threshold={thresh:.0f} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    # Footprint-dependent
    components.append(Component(
        stage="detection", key="cot_amt",
        spec="COT < AMT (footprint-dependent)",
        present=True,
        value="footprint-dependent · not probed here",
    ))
    return components


def _probe_initiative_short(bars: list) -> List[Component]:
    components = []

    ok = len(bars) >= OFA_MIN_BARS_REQ
    components.append(Component(
        stage="detection", key="min_bars",
        spec=f"buffer ≥ {OFA_MIN_BARS_REQ}",
        present=ok,
        value=f"buffer={len(bars)} {'≥' if ok else '<'} {OFA_MIN_BARS_REQ} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    b1, b2, b3, b4 = bars[-4], bars[-3], bars[-2], bars[-1]
    b1_range = b1["h"] - b1["l"]

    ok = EXPANSION_MIN_PT <= b1_range <= EXPANSION_MAX_PT
    components.append(Component(
        stage="detection", key="b1_expansion",
        spec=f"b1 range in [{EXPANSION_MIN_PT}, {EXPANSION_MAX_PT}] pts",
        present=ok,
        value=f"b1 range={b1_range:.2f} · need [{EXPANSION_MIN_PT}, {EXPANSION_MAX_PT}] {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    ok = b1["c"] < b1["o"]
    components.append(Component(
        stage="detection", key="b1_bear",
        spec="b1.close < b1.open (bearish expansion bar)",
        present=ok,
        value=f"b1 close={b1['c']:.2f} open={b1['o']:.2f} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    b2_lower_high = b2["h"] < b1["h"]
    b2_poc = b2.get("poc_vol") or b2.get("poc")
    b2_poc_return = b2_poc is not None and abs(b2["c"] - b2_poc) <= POC_RETURN_TOLERANCE_PT
    ok = b2_lower_high or b2_poc_return
    components.append(Component(
        stage="detection", key="b2_test",
        spec="b2.high < b1.high (lower high) OR b2 POC return",
        present=ok,
        value=f"b2_high={b2['h']:.2f} · b1_high={b1['h']:.2f} · lower_high={'T' if b2_lower_high else 'F'} · poc_return={'T' if b2_poc_return else 'F'}",
    ))
    if not ok:
        return components

    b3_range = b3["h"] - b3["l"]
    ok = b3_range > b1_range
    components.append(Component(
        stage="detection", key="b3_joining",
        spec="b3 range > b1 range",
        present=ok,
        value=f"b3_range={b3_range:.2f} · b1_range={b1_range:.2f} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    ok = b4["h"] <= b2["h"] and b4["c"] < b1["l"]
    components.append(Component(
        stage="detection", key="b4_test",
        spec="b4.high ≤ b2.high AND b4.close < b1.low",
        present=ok,
        value=f"b4_close={b4['c']:.2f} · b1_low={b1['l']:.2f} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    # Step 7: lookback_quiet
    b1_vol = b1.get("v", 0) or 0
    lookback = bars[-OFA_MIN_BARS_REQ:-(OFA_MIN_BARS_REQ - LOOKBACK_BARS)]
    if lookback and b1_vol > 0:
        max_lb_vol = max(b.get("v", 0) for b in lookback)
        thresh = b1_vol * LOOKBACK_MAX_VOL_RATIO
        ok = max_lb_vol < thresh
    else:
        max_lb_vol = 0
        thresh = 0
        ok = False
    components.append(Component(
        stage="detection", key="lookback_quiet",
        spec=f"max(lookback {LOOKBACK_BARS} bars vol) < b1_vol × {LOOKBACK_MAX_VOL_RATIO}",
        present=ok,
        value=f"lookback_max={max_lb_vol} · threshold={thresh:.0f} {'✓' if ok else '✗'}",
    ))
    if not ok:
        return components

    components.append(Component(
        stage="detection", key="cot_amt",
        spec="COT > AMT (footprint-dependent)",
        present=True,
        value="footprint-dependent · not probed here",
    ))
    return components
