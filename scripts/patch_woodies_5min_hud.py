#!/usr/bin/env python3
"""Patch woodies_5min.json with P30.10 HUD fields (interim until DLL Export 8b is live).

Reads Sierra export, adds ccidiff H/mid/L, predictor H/L, prev_ohlc, low_prev_angle.
Safe to re-run; atomic write via temp file.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path
from typing import List, Literal, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.v9.systems.woodies.cci_calc import calc_cci, calc_predictor

Anchor = Literal["C", "H", "L"]
DEFAULT_PATH = Path(
    os.getenv(
        "V9_WOODIES_5MIN_EXPORT_PATH",
        "/Users/michael/SierraChart_Data/v9_export/woodies_5min.json",
    )
)
PATCH_VERSION = "v9.4.0-p30.10"


def _anchored_hlc(
    highs: List[float], lows: List[float], closes: List[float], anchor: Anchor
) -> Tuple[List[float], List[float], List[float]]:
    h, l, c = list(highs), list(lows), list(closes)
    if not c:
        return h, l, c
    if anchor == "H":
        c[-1] = h[-1]
    elif anchor == "L":
        c[-1] = l[-1]
    return h, l, c


def calc_cci_at_anchor(
    highs: List[float], lows: List[float], closes: List[float], period: int, anchor: Anchor
) -> float:
    ah, al, ac = _anchored_hlc(highs, lows, closes, anchor)
    return calc_cci(ah, al, ac, period)


def _bar_hlc(bar: dict) -> Tuple[float, float, float, float]:
    ohlc = bar.get("ohlc") or {}
    return (
        float(ohlc.get("h") or 0),
        float(ohlc.get("l") or 0),
        float(ohlc.get("c") or 0),
        float(ohlc.get("o") or 0),
    )


def patch_bar(bars: List[dict], index: int) -> None:
    highs, lows, closes = [], [], []
    for b in bars[: index + 1]:
        h, l, c, _ = _bar_hlc(b)
        highs.append(h)
        lows.append(l)
        closes.append(c)

    cci14_c = calc_cci_at_anchor(highs, lows, closes, 14, "C")
    cci6_c = calc_cci_at_anchor(highs, lows, closes, 6, "C")
    cci14_h = calc_cci_at_anchor(highs, lows, closes, 14, "H")
    cci6_h = calc_cci_at_anchor(highs, lows, closes, 6, "H")
    cci14_l = calc_cci_at_anchor(highs, lows, closes, 14, "L")
    cci6_l = calc_cci_at_anchor(highs, lows, closes, 6, "L")

    bar = bars[index]
    bar["ccidiff"] = round(cci14_c - cci6_c, 2)
    bar["ccidiff_h"] = round(cci14_h - cci6_h, 2)
    bar["ccidiff_l"] = round(cci14_l - cci6_l, 2)

    if index > 0:
        ph, pl, pc, po = _bar_hlc(bars[index - 1])
        bar["prev_ohlc"] = {"o": po, "h": ph, "l": pl, "c": pc}
        _, l_cur, _, _ = _bar_hlc(bar)
        low_delta = l_cur - pl
        bar["low_prev_angle"] = round(math.degrees(math.atan2(low_delta, 2.0)), 1)
        cci14_prev_h = calc_cci_at_anchor(
            highs[:-1], lows[:-1], closes[:-1], 14, "H"
        )
        cci14_prev_l = calc_cci_at_anchor(
            highs[:-1], lows[:-1], closes[:-1], 14, "L"
        )
    else:
        cci14_prev_h = cci14_prev_l = 0.0

    bar["predictor_cci_high"] = round(calc_predictor(cci14_h, cci14_prev_h), 2)
    bar["predictor_cci_low"] = round(calc_predictor(cci14_l, cci14_prev_l), 2)


def patch_payload(data: dict) -> dict:
    history = data.get("history") or []
    for i in range(len(history)):
        patch_bar(history, i)
    current = data.get("current_bar")
    if current:
        if history and history[-1] is not current:
            patch_bar(history + [current], len(history))
        elif history:
            patch_bar(history, len(history) - 1)
        else:
            patch_bar([current], 0)
    data["version"] = PATCH_VERSION
    data["export_ts"] = int(time.time())
    return data


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        return 1
    data = json.loads(path.read_text())
    patch_payload(data)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, separators=(",", ":")))
    tmp.replace(path)
    cb = data.get("current_bar") or {}
    print(f"OK {path}")
    print(f"  version={data.get('version')} ccidiff_h={cb.get('ccidiff_h')} prev_ohlc={'prev_ohlc' in cb}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
