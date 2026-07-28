"""RELEASE_ENTRY_GATE_V1 — enter when price LEAVES the zone, not when it touches it.

Michael 2026-07-28: "אתמול הכניסה של הסים לעסקת לונג הייתה טובה אבל מוקדמת …
אפשר היה לזהות ולבצע כניסה בשלב אחר שהמחיר הפסיק להיות תקוע באותו אזור".

The 07-27 session is the specimen (a day whose bar timestamps are verified clean):

    19:15   low 7416.25                       vol 8235   ← the extreme
    19:20   higher low 7418.75                vol 6439
    19:25   higher low 7419.50                vol 4552   ← volume drying up
    19:35   higher low 7423.25                vol 4666
    19:45   higher low 7423.50                vol 4489   ← driest
    19:50   closes 7433.00, above the zone    vol 6239   ← THE RELEASE
    then    7436.50 … 7455.75

The system entered at 19:24 — inside the sticky zone, 26 minutes early, with a
9pt stop, and was stopped out before the move it had correctly predicted.

Three conditions, all required, all measured on closed 5-min bars:

  1. STRUCTURE  — `min_higher_lows` consecutive higher lows since the extreme
                  (mirrored: lower highs for a short). The market stops probing.
  2. EXHAUSTION — volume contracts: the mean of the last `vol_window` bars is
                  below `vol_ratio` × the volume of the extreme bar. Sellers
                  finish.
  3. RELEASE    — a bar CLOSES beyond the rotation zone, with volume above the
                  contracted mean. Price actually leaves.

A side effect that matters as much as the timing: entering on the release puts
the structural stop under the real extreme. On 07-27 that is 7433 with a stop
below 7416 — a 17pt stop, exactly the GB100 profile that survived, instead of
ZLR's 9pt that did not. Waiting for the release and sizing the stop correctly
are the same act.

This gate can only DELAY or SKIP a signal the system already produced. It never
creates one, never changes direction, never widens risk on its own.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Sequence

logger = logging.getLogger(__name__)


def enabled() -> bool:
    return os.getenv("RELEASE_ENTRY_GATE_V1", "0").strip().lower() in ("1", "true", "yes")


def _f(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _i(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass
class Bar:
    high: float
    low: float
    close: float
    volume: float


@dataclass
class ReleaseVerdict:
    released: bool
    reason: str
    structural_stop: Optional[float] = None   # beyond the extreme, for the caller
    higher_lows: int = 0
    vol_ratio: Optional[float] = None


def check_release(bars: Sequence[Bar], direction: str) -> ReleaseVerdict:
    """Pure. `bars` are closed 5-min bars, oldest → newest, covering the window
    from the extreme to now. Returns whether price has released from the zone.

    Unknown / insufficient data → released=False. A gate that fails open would
    reproduce exactly the early entry it exists to prevent (Rule 1)."""
    min_hl = _i("RELEASE_MIN_HIGHER_LOWS", 2)
    vol_window = _i("RELEASE_VOL_WINDOW", 3)
    vol_ratio_max = _f("RELEASE_VOL_RATIO", 0.75)
    zone_pts = _f("RELEASE_ZONE_POINTS", 8.0)
    max_bars = _i("RELEASE_MAX_BARS", 24)          # give up after ~2h

    if not bars or len(bars) < min_hl + vol_window:
        return ReleaseVerdict(False, f"not enough bars ({len(bars)})")

    is_long = str(direction).upper() == "LONG"
    window = list(bars)[-max_bars:]

    # 1 — the extreme, and the rotation zone above/below it
    if is_long:
        ext = min(b.low for b in window)
        ext_i = max(i for i, b in enumerate(window) if b.low == ext)
        zone_hi, zone_lo = ext + zone_pts, ext
    else:
        ext = max(b.high for b in window)
        ext_i = max(i for i, b in enumerate(window) if b.high == ext)
        zone_hi, zone_lo = ext, ext - zone_pts

    after = window[ext_i + 1:]
    if len(after) < max(min_hl, vol_window):
        return ReleaseVerdict(False, f"only {len(after)} bars since the extreme")

    # 2 — structure: consecutive higher lows (or lower highs)
    hl = 0
    prev = window[ext_i]
    for b in after:
        better = (b.low > prev.low) if is_long else (b.high < prev.high)
        hl = hl + 1 if better else 0
        prev = b
    if hl < min_hl:
        return ReleaseVerdict(False, f"structure not turning ({hl}/{min_hl} higher lows)",
                              higher_lows=hl)

    # 3 — exhaustion: volume contracting versus the extreme bar
    ext_vol = window[ext_i].volume or 0.0
    recent = [b.volume or 0.0 for b in after[-vol_window:]]
    mean_recent = sum(recent) / len(recent) if recent else 0.0
    ratio = (mean_recent / ext_vol) if ext_vol > 0 else None
    if ratio is None:
        return ReleaseVerdict(False, "no volume on the extreme bar — cannot judge exhaustion",
                              higher_lows=hl)
    if ratio > vol_ratio_max:
        return ReleaseVerdict(False,
                              f"still active in the zone (vol {ratio:.2f} > {vol_ratio_max})",
                              higher_lows=hl, vol_ratio=ratio)

    # 4 — release: the last CLOSED bar leaves the zone on returning volume
    last = after[-1]
    left = (last.close > zone_hi) if is_long else (last.close < zone_lo)
    if not left:
        return ReleaseVerdict(False,
                              f"has not left the zone (close {last.close} vs "
                              f"{zone_hi if is_long else zone_lo})",
                              higher_lows=hl, vol_ratio=ratio)
    if (last.volume or 0.0) <= mean_recent:
        return ReleaseVerdict(False, "left the zone without volume — not convincing",
                              higher_lows=hl, vol_ratio=ratio)

    buf = _f("RELEASE_STOP_BUFFER_POINTS", 1.0)
    stop = round((ext - buf) if is_long else (ext + buf), 2)
    return ReleaseVerdict(
        True,
        f"released: {hl} higher lows, vol {ratio:.2f} of the extreme, "
        f"closed {last.close} beyond the zone",
        structural_stop=stop, higher_lows=hl, vol_ratio=ratio)


def bars_from_rows(rows: Sequence[dict]) -> List[Bar]:
    """Adapt DB rows (high/low/close/volume) — skips anything unusable."""
    out: List[Bar] = []
    for r in rows or []:
        try:
            out.append(Bar(float(r["high"]), float(r["low"]),
                           float(r["close"]), float(r.get("volume") or 0.0)))
        except (KeyError, TypeError, ValueError):
            continue
    return out
