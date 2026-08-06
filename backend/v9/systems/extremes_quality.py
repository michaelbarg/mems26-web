"""Excess / Poor-High / Poor-Low detection (Dalton gap analysis, Step 1).

Pure detection engine — no behavior change. Classifies session extremes as:
  EXCESS  — rejection tail at the extreme (protected, auction complete)
  POOR    — flat extreme (magnet, unfinished business)
  NEUTRAL — insufficient data or ambiguous

Rule-1: no bars / missing data → NEUTRAL (never guess).

Dalton definitions:
  Excess high: session high has a rejection tail (long upper wick, close
    retreating from the high, no revisit within K bars). The market tested
    and REJECTED this price — it's a protected extreme.
  Poor high: session high is flat (tiny/no tail, price sat at the extreme
    with multiple touches). Unfinished business — future sessions will
    likely revisit and resolve it.
  Mirror for lows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

# ── Configurable thresholds ──
EXCESS_TAIL_PTS = 2.0        # minimum tail length for excess (points)
EXCESS_TAIL_BODY_RATIO = 1.5 # alternative: tail ≥ 1.5× body
EXCESS_NO_REVISIT_BARS = 3   # bars without revisiting the extreme
POOR_TAIL_PTS = 0.5          # maximum tail for "flat" extreme
POOR_MIN_TOUCHES = 2         # minimum touches at the extreme level


@dataclass
class ExtremeQuality:
    """Classification of a session extreme."""
    quality: str              # "EXCESS" | "POOR" | "NEUTRAL"
    level: float              # the extreme price level
    tail_pts: float           # measured tail length
    touches: int              # number of bars touching the extreme band
    detail: str               # human-readable explanation


@dataclass
class SessionExtremes:
    """Both extremes for a session."""
    high: ExtremeQuality
    low: ExtremeQuality
    session_high: float
    session_low: float
    n_bars: int


def classify_session_extremes(
    bars: Sequence[Dict[str, Any]],
    *,
    excess_tail_pts: float = EXCESS_TAIL_PTS,
    excess_tail_body_ratio: float = EXCESS_TAIL_BODY_RATIO,
    no_revisit_bars: int = EXCESS_NO_REVISIT_BARS,
    poor_tail_pts: float = POOR_TAIL_PTS,
    poor_min_touches: int = POOR_MIN_TOUCHES,
) -> Optional[SessionExtremes]:
    """Classify the high and low extremes of a bar sequence.

    Args:
        bars: list of dicts with keys: high, low, open, close (floats).
              Must be in chronological order.

    Returns:
        SessionExtremes or None if insufficient data (Rule-1).
    """
    if not bars or len(bars) < 3:
        return None

    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]
    session_high = max(highs)
    session_low = min(lows)

    high_q = _classify_high(
        bars, session_high,
        excess_tail_pts, excess_tail_body_ratio,
        no_revisit_bars, poor_tail_pts, poor_min_touches,
    )
    low_q = _classify_low(
        bars, session_low,
        excess_tail_pts, excess_tail_body_ratio,
        no_revisit_bars, poor_tail_pts, poor_min_touches,
    )

    return SessionExtremes(
        high=high_q, low=low_q,
        session_high=session_high, session_low=session_low,
        n_bars=len(bars),
    )


def classify_extremes_live(
    bars: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Convenience wrapper returning a dict for radar/API consumption.

    Returns {high_quality, low_quality, session_high, session_low,
             high_detail, low_detail, high_tail, low_tail} or empty dict.
    """
    result = classify_session_extremes(bars)
    if result is None:
        return {}
    return {
        "high_quality": result.high.quality,
        "low_quality": result.low.quality,
        "session_high": result.session_high,
        "session_low": result.session_low,
        "high_tail_pts": round(result.high.tail_pts, 2),
        "low_tail_pts": round(result.low.tail_pts, 2),
        "high_touches": result.high.touches,
        "low_touches": result.low.touches,
        "high_detail": result.high.detail,
        "low_detail": result.low.detail,
    }


# ── Internal helpers ──

def _classify_high(
    bars, session_high,
    excess_tail_pts, excess_tail_body_ratio,
    no_revisit_bars, poor_tail_pts, poor_min_touches,
) -> ExtremeQuality:
    """Classify the session high extreme."""
    # Find the bar that made the session high
    high_bar_idx = None
    for i, b in enumerate(bars):
        if float(b["high"]) == session_high:
            high_bar_idx = i
            break  # first occurrence

    if high_bar_idx is None:
        return ExtremeQuality("NEUTRAL", session_high, 0.0, 0, "high bar not found")

    hb = bars[high_bar_idx]
    h = float(hb["high"])
    o = float(hb["open"])
    c = float(hb["close"])
    l = float(hb["low"])
    body = abs(c - o)

    # Upper tail: distance from high to max(open, close)
    upper_tail = h - max(o, c)

    # Check EXCESS: tail ≥ threshold AND close retreats from high
    close_retreats = c < h - 0.25  # close is below the high
    tail_meets_pts = upper_tail >= excess_tail_pts
    tail_meets_ratio = body > 0 and upper_tail >= excess_tail_body_ratio * body

    # No revisit: subsequent bars don't touch the extreme band
    extreme_band = session_high - 0.5  # within 0.5pt of the high
    revisited = False
    bars_checked = 0
    for j in range(high_bar_idx + 1, min(high_bar_idx + 1 + no_revisit_bars, len(bars))):
        bars_checked += 1
        if float(bars[j]["high"]) >= extreme_band:
            revisited = True
            break

    if (tail_meets_pts or tail_meets_ratio) and close_retreats and not revisited and bars_checked > 0:
        return ExtremeQuality(
            "EXCESS", session_high, round(upper_tail, 2), 1,
            f"rejection tail {upper_tail:.2f}pt, close retreats, no revisit {bars_checked} bars",
        )

    # Check POOR: flat top (tiny tail, multiple touches)
    touches = sum(1 for b in bars if abs(float(b["high"]) - session_high) <= 0.25)
    if upper_tail <= poor_tail_pts and touches >= poor_min_touches:
        return ExtremeQuality(
            "POOR", session_high, round(upper_tail, 2), touches,
            f"flat top: tail {upper_tail:.2f}pt, {touches} touches",
        )

    return ExtremeQuality(
        "NEUTRAL", session_high, round(upper_tail, 2),
        sum(1 for b in bars if abs(float(b["high"]) - session_high) <= 0.25),
        f"ambiguous: tail {upper_tail:.2f}pt",
    )


def _classify_low(
    bars, session_low,
    excess_tail_pts, excess_tail_body_ratio,
    no_revisit_bars, poor_tail_pts, poor_min_touches,
) -> ExtremeQuality:
    """Classify the session low extreme."""
    low_bar_idx = None
    for i, b in enumerate(bars):
        if float(b["low"]) == session_low:
            low_bar_idx = i
            break

    if low_bar_idx is None:
        return ExtremeQuality("NEUTRAL", session_low, 0.0, 0, "low bar not found")

    lb = bars[low_bar_idx]
    h = float(lb["high"])
    o = float(lb["open"])
    c = float(lb["close"])
    l = float(lb["low"])
    body = abs(c - o)

    # Lower tail: distance from min(open, close) to low
    lower_tail = min(o, c) - l

    close_retreats = c > l + 0.25
    tail_meets_pts = lower_tail >= excess_tail_pts
    tail_meets_ratio = body > 0 and lower_tail >= excess_tail_body_ratio * body

    extreme_band = session_low + 0.5
    revisited = False
    bars_checked = 0
    for j in range(low_bar_idx + 1, min(low_bar_idx + 1 + no_revisit_bars, len(bars))):
        bars_checked += 1
        if float(bars[j]["low"]) <= extreme_band:
            revisited = True
            break

    if (tail_meets_pts or tail_meets_ratio) and close_retreats and not revisited and bars_checked > 0:
        return ExtremeQuality(
            "EXCESS", session_low, round(lower_tail, 2), 1,
            f"rejection tail {lower_tail:.2f}pt, close retreats, no revisit {bars_checked} bars",
        )

    touches = sum(1 for b in bars if abs(float(b["low"]) - session_low) <= 0.25)
    if lower_tail <= poor_tail_pts and touches >= poor_min_touches:
        return ExtremeQuality(
            "POOR", session_low, round(lower_tail, 2), touches,
            f"flat bottom: tail {lower_tail:.2f}pt, {touches} touches",
        )

    return ExtremeQuality(
        "NEUTRAL", session_low, round(lower_tail, 2),
        sum(1 for b in bars if abs(float(b["low"]) - session_low) <= 0.25),
        f"ambiguous: tail {lower_tail:.2f}pt",
    )
