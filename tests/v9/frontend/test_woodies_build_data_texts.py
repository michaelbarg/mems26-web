"""P30.10 — Woodies data column text builders (mirrors woodiesDesignerSpec.ts)."""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

import pytest

# Keep in sync with frontend/v9/.../woodiesDesignerSpec.ts BAR.SLOT
_BAR_SLOT = 9


def _cci_minus_tcci(bar: Dict[str, Any]) -> Optional[float]:
    tcci = bar.get("cci_6_tcci")
    if tcci is None:
        return None
    return float(bar["cci_14"]) - float(tcci)


def _compute_low_line_angle_deg(prev_low: float, cur_low: float) -> float:
    dy = cur_low - prev_low
    return round(math.degrees(math.atan2(dy, _BAR_SLOT)) * 10) / 10


def _format_cci_diff_row(value: Optional[float], variant: str) -> str:
    if value is None or not math.isfinite(value):
        return "—"
    suffix = (
        " CCIDiff"
        if variant == "mid"
        else " CCIDiff H"
        if variant == "H"
        else " CCIDiff L"
    )
    return f"{value:.2f}{suffix}"


def build_data_texts(
    bar: Dict[str, Any], prev_bar: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    mid_diff = _cci_minus_tcci(bar)

    last = f"{float(bar['close']):.2f} Last" if bar.get("close") is not None else "—"

    phi = f"{float(bar['proj_hi']):.2f} ProjHigh" if bar.get("proj_hi") is not None else "—"
    plo = f"{float(bar['proj_lo']):.2f} ProjLow" if bar.get("proj_lo") is not None else "—"

    prev_high = (prev_bar or {}).get("high") if prev_bar else bar.get("prev_high")
    prev_low = (prev_bar or {}).get("low") if prev_bar else bar.get("prev_low")

    hi = "—"
    if prev_high is not None and bar.get("high") is not None:
        hi = f"{float(prev_high):.2f} {float(bar['high']):.2f} Hig"

    lo = "—"
    if prev_low is not None and bar.get("low") is not None:
        lo = f"{float(prev_low):.2f} {float(bar['low']):.2f} Low"

    cci = "—"
    if bar.get("predictor_next_cci") is not None:
        pred_hi = bar.get("predictor_cci_high", bar["predictor_next_cci"])
        pred_lo = bar.get("predictor_cci_low", bar["predictor_next_cci"])
        cci = f"{float(pred_hi):.1f}  {float(pred_lo):.1f} CCI Pre"

    angle = "—"
    if bar.get("low_prev_angle") is not None:
        angle = f"{float(bar['low_prev_angle']):.1f}° Low Prev/Cur"
    elif prev_low is not None and bar.get("low") is not None:
        deg = _compute_low_line_angle_deg(float(prev_low), float(bar["low"]))
        angle = f"{deg:.1f}° Low Prev/Cur"

    diff_w = "—"
    if mid_diff is not None and math.isfinite(mid_diff):
        diff_w = _format_cci_diff_row(mid_diff, "mid")

    return {
        "diff-g": _format_cci_diff_row(bar.get("ccidiff_h"), "H"),
        "diff-w": diff_w,
        "diff-m": _format_cci_diff_row(bar.get("ccidiff_l"), "L"),
        "hi": hi,
        "last": last,
        "lo": lo,
        "phi": phi,
        "plo": plo,
        "cci": cci,
        "angle": angle,
    }


def _bar(**kwargs: Any) -> Dict[str, Any]:
    base = {
        "ts_unix": 1,
        "cci_14": 10.0,
        "cci_6_tcci": 5.0,
        "trend_state": "GRAY",
        "trend_color": "#888888",
    }
    base.update(kwargs)
    return base


def test_ccidiff_white_is_cci14_minus_tcci():
    texts = build_data_texts(_bar(cci_14=12.5, cci_6_tcci=8.0))
    assert texts["diff-w"] == "4.50 CCIDiff"
    assert texts["diff-g"] == "—"
    assert texts["diff-m"] == "—"


def test_ccidiff_h_l_from_export_when_present():
    texts = build_data_texts(
        _bar(ccidiff_h=55.19, ccidiff_l=44.0, cci_14=10, cci_6_tcci=5),
    )
    assert texts["diff-g"] == "55.19 CCIDiff H"
    assert texts["diff-m"] == "44.00 CCIDiff L"
    assert texts["diff-w"] == "5.00 CCIDiff"


def test_high_low_prev_cur_from_ohlc():
    prev = _bar(high=7371.0, low=7356.75, close=7370.0)
    cur = _bar(high=7375.0, low=7366.75, close=7374.0)
    texts = build_data_texts(cur, prev)
    assert texts["hi"] == "7371.00 7375.00 Hig"
    assert texts["lo"] == "7356.75 7366.75 Low"


def test_cci_pred_only_when_predictor_present():
    no_pred = build_data_texts(_bar())
    assert no_pred["cci"] == "—"
    with_pred = build_data_texts(_bar(predictor_next_cci=-14.12))
    assert with_pred["cci"] == "-14.1  -14.1 CCI Pre"


def test_cci_pred_separate_hi_lo_when_exported():
    texts = build_data_texts(
        _bar(
            predictor_next_cci=10.0,
            predictor_cci_high=18.1,
            predictor_cci_low=12.0,
        ),
    )
    assert texts["cci"] == "18.1  12.0 CCI Pre"


def test_high_low_uses_prev_high_low_from_api():
    texts = build_data_texts(
        _bar(high=7375.0, low=7366.75, close=7374.0, prev_high=7371.0, prev_low=7356.75),
    )
    assert texts["hi"] == "7371.00 7375.00 Hig"
    assert texts["lo"] == "7356.75 7366.75 Low"


def test_low_angle_geometric_from_two_bars():
    prev = _bar(low=7378.0)
    cur = _bar(low=7368.75)
    texts = build_data_texts(cur, prev)
    expected = _compute_low_line_angle_deg(7378.0, 7368.75)
    assert texts["angle"] == f"{expected:.1f}° Low Prev/Cur"
    assert expected < 0


def test_build_time_axis_labels_no_overlap_on_few_bars():
    bars = [_bar(ts_unix=1000 + i * 300) for i in range(5)]
    labels = build_time_axis_labels(
        bars,
        lambda ts: "5/19/2026",
        lambda ts: f"{(ts // 60) % 60}:{ts % 60:02d}",
        min_gap_px=48,
    )
    xs = [t["x"] for t in labels]
    for i in range(1, len(xs)):
        assert xs[i] - xs[i - 1] >= 48
    keys = [t["key"] for t in labels]
    assert keys.count("date") == 1
    assert len(keys) == len(set(keys))


def build_time_axis_labels(bars, format_date, format_time, min_gap_px=48):
    """Mirror woodiesDesignerSpec.buildTimeAxisLabels (minimal)."""
    n = len(bars)
    if n == 0:
        return []
    ts_list = [b["ts_unix"] for b in bars]
    first_x, last_x = 28, 289
    xs = [first_x + (i / max(1, n - 1)) * (last_x - first_x) for i in range(n)]
    span = max(1, xs[-1] - xs[0])
    max_ticks = max(2, int(span / min_gap_px) + 1)
    out = [{"key": "date", "label": format_date(ts_list[0]), "x": xs[0], "align": "left"}]
    budget = max(1, max_ticks - 1)
    raw = [round((k / max(1, budget - 1)) * (n - 1)) for k in range(budget)]
    seen, last_x = set(), xs[0]
    for idx in raw:
        if idx in seen or idx == 0:
            continue
        seen.add(idx)
        gap = 60 if idx == 1 else min_gap_px
        if xs[idx] - last_x < gap:
            continue
        label = format_time(ts_list[idx])
        if any(t["label"] == label for t in out):
            continue
        out.append({"key": f"t-{idx}", "label": label, "x": xs[idx], "align": "center"})
        last_x = xs[idx]
    return out


def test_resolve_chart_paint_bars_freezes_when_not_live():
    """Chart window does not tick when historical; new live slice ignored until pan."""
    live_v1 = [{"ts_unix": 1, "cci_14": 10.0}]
    live_v2 = [{"ts_unix": 1, "cci_14": 99.0}]
    r1 = resolve_chart_paint_bars(False, live_v1, None, "0:5", "")
    r2 = resolve_chart_paint_bars(False, live_v2, r1["frozen"], "0:5", r1["frozenKey"])
    assert r1["bars"][0]["cci_14"] == 10.0
    assert r2["bars"][0]["cci_14"] == 10.0
    r3 = resolve_chart_paint_bars(True, live_v2, r2["frozen"], "0:5", r2["frozenKey"])
    assert r3["bars"][0]["cci_14"] == 99.0


def resolve_chart_paint_bars(at_live, live_window, frozen, view_key, frozen_key):
    """Mirror woodiesDesignerSpec.resolveChartPaintBars."""
    if at_live:
        return {"bars": live_window, "frozen": None, "frozenKey": ""}
    if frozen and frozen_key == view_key:
        return {"bars": frozen, "frozen": frozen, "frozenKey": frozen_key}
    snap = [dict(b) for b in live_window]
    return {"bars": snap, "frozen": snap, "frozenKey": view_key}


def test_low_prev_angle_prefers_sierra_export():
    """DLL/Sierra angle (dx=2) wins over frontend geometric fallback (BAR.SLOT)."""
    bar = _bar(
        low=7365.0,
        prev_low=7364.25,
        low_prev_angle=20.56,
    )
    texts = build_data_texts(bar, prev_bar=_bar(low=7364.25))
    assert texts["angle"] == "20.6° Low Prev/Cur"


def test_dll_export_bar_full_hud():
    """Regression: live export shape fills all 10 HUD rows (no em dashes on core fields)."""
    bar = _bar(
        cci_14=-7.99,
        cci_6_tcci=-5.23,
        ccidiff_h=-27.9,
        ccidiff_l=-2.77,
        high=7379.25,
        low=7365.0,
        close=7365.0,
        prev_high=7378.5,
        prev_low=7364.25,
        proj_hi=7395.0,
        proj_lo=7351.75,
        predictor_next_cci=-8.19,
        predictor_cci_high=69.83,
        predictor_cci_low=7.29,
        low_prev_angle=20.56,
    )
    texts = build_data_texts(bar)
    assert texts["diff-g"] == "-27.90 CCIDiff H"
    assert texts["diff-w"] == "-2.76 CCIDiff"
    assert texts["diff-m"] == "-2.77 CCIDiff L"
    assert "7378.50" in texts["hi"]
    assert texts["last"] == "7365.00 Last"
    assert "7395.00 ProjHigh" in texts["phi"]
    assert "69.8" in texts["cci"]
    assert texts["angle"] == "20.6° Low Prev/Cur"


def test_hud_all_rows_from_live_bar():
    """HUD uses live bar for every row (not frozen historical bar)."""
    hist = _bar(cci_14=1.0, cci_6_tcci=1.0, close=7360.0)
    live = _bar(cci_14=12.5, cci_6_tcci=8.0, close=7374.5)
    hist_texts = build_data_texts(hist)
    live_texts = build_data_texts(live)
    assert hist_texts["diff-w"] == "0.00 CCIDiff"
    assert live_texts["diff-w"] == "4.50 CCIDiff"
    assert live_texts["last"] == "7374.50 Last"


def test_previous_bar_for_display_logic():
    """Mirror previousBarForDisplay index rules."""
    bars = [_bar(ts_unix=i, close=7400 + i) for i in range(5)]

    def prev(all_bars, display, window):
        if display is None:
            return None
        in_w = next((i for i, b in enumerate(window) if b["ts_unix"] == display["ts_unix"]), -1)
        if in_w > 0:
            return window[in_w - 1]
        in_a = next((i for i, b in enumerate(all_bars) if b["ts_unix"] == display["ts_unix"]), -1)
        if in_a > 0:
            return all_bars[in_a - 1]
        if len(window) >= 2:
            return window[-2]
        if len(all_bars) >= 2:
            return all_bars[-2]
        return None

    window = bars[2:5]
    assert prev(bars, bars[4], window)["ts_unix"] == 3
    assert prev(bars, window[-1], window)["ts_unix"] == 3


def trend_header_values(bar: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """Mirror woodiesDesignerSpec.ts trendHeaderValues (§5.2 Sierra flags)."""
    s = ((bar or {}).get("trend_state") or "GRAY").upper()
    return {
        "down": 1.0 if s == "RED" else 0.0,
        "neutral": 1.0 if s == "YELLOW" else 0.0,
        "up": 1.0 if s == "BLUE" else 0.0,
    }


def test_trend_header_sierra_flags_not_cci_values():
    assert trend_header_values(_bar(trend_state="BLUE", cci_14=179.3)) == {
        "down": 0.0,
        "neutral": 0.0,
        "up": 1.0,
    }
    assert trend_header_values(_bar(trend_state="RED", cci_14=-50.0))["down"] == 1.0
    assert trend_header_values(_bar(trend_state="YELLOW", cci_14=12.0))["neutral"] == 1.0
    assert trend_header_values(_bar(trend_state="GRAY", cci_14=99.0)) == {
        "down": 0.0,
        "neutral": 0.0,
        "up": 0.0,
    }
