"""CEILING_FLOOR_STATE — the double-ceiling / double-floor failure detector.

Michael's ruling (2026-08-28, `CC_WORKORDER_CEILING_FLIP_2026-08-28.md`):
"בעסקה האחרונה הייתה כניסה ללונג — ברגע שנוצרה תקרה כפולה שלא הצליחה
להתקדם, אני רוצה שהמערכת תזהה את זה ותסגור את העסקה ברווח. לאחר מכן,
בהינתן הטריגר, אני רוצה עסקה של שורט."

Companion ruling (same evening, 18:55): **"זה היה צריך להיות יחסי"** — every
threshold in here is measured against ATR, never in fixed points. And the
binary-Dalton ruling: a *structural ratio* is a geometric fact and is allowed;
a subjective confidence score is not. There are no percentages, no scores and
no "confidence" anywhere in this module — only geometry.

Anatomy (CEILING; FLOOR is the exact mirror), evaluated on the LAST bar of the
input list, which is always the CONFIRM candidate:

  1. TOUCH-1  — a bar whose high reached/exceeded an edge (VAH · session high ·
                IB high). Its high is `P1`.
  2. REJECTION — somewhere after P1 and no later than P2, a bar CLOSED back
                below the edge.
  3. TOUCH-2  — a later bar, `min_bars_between..max_bars_between` bars after
                P1, whose high `P2` sits in the same area: `|P2 - P1| <= tol`
                where `tol = tol_atr × ATR` (relative — the ruling), and no
                bar in `(P1, P2]` CLOSED above P1 ("failed to advance").
  4. CONFIRM  — the last bar CLOSES below the neckline, i.e. below the lowest
                low of the span `(P1 .. P2]`, within `confirm_max_bars` of P2
                and without a new high above `P1 + tol` in between
                ⇒ **CEILING_FAILED**.

Purity contract (why unit == replay == shadow, byte for byte):
  * no I/O, no DB, no `os.getenv`, no `datetime.now()`, no module state;
  * every threshold arrives via `cfg` (config/ceiling_floor.yaml) with the
    code defaults below as the fallback;
  * missing input — no ATR, no usable level, too few bars — returns `None`.
    Rule 1 (CLAUDE.md § Source-of-Truth Discipline): honest failure beats a
    synthetic value. This detector never guesses an ATR and never invents a
    level the caller did not supply.

Two deliberate additions to the written spec, both documented so nobody has to
reverse-engineer them later:
  * `confirm_max_bars` — the ruling bounds P1→P2 but says nothing about how
    long after P2 a confirmation may arrive. Unbounded, a neckline break three
    hours later would still read as "the ceiling just failed". The bound is in
    bars (structure), not points, so it stays inside the relative-thresholds
    ruling.
  * the neckline is `min(low)` over `(P1 .. P2]` — the bars after the first
    peak up to and including the second. The written spec says
    "min(שפלי-הפער בין השיאים)"; taken as a strictly-interior range it is
    undefined when the two peaks are adjacent, so the second peak's own low is
    included to keep the value defined for every `P2 > P1`. On the 28.08
    anchor both readings give the identical number (7767.25).

This module DOES NOT TRADE. It reports a state. The three consumers of that
state (bank the long · lock the edge against new longs · flip short) are
separate, separately-flagged builds.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Set

# ── Code defaults — the fallback when config/ceiling_floor.yaml is absent ──
# Every one of these is also a key in that YAML; nothing here is a fixed
# PRICE threshold — `tol_atr` is a multiple of ATR, the rest are bar counts.
DEFAULTS: Dict[str, Any] = {
    "tol_atr": 0.25,           # |P2 - P1| <= tol_atr × ATR  (the ruling's 0.25)
    "max_bars_between": 12,    # P2 no later than 12 bars after P1
    "min_bars_between": 1,     # P2 at least 1 bar after P1
    "confirm_max_bars": 12,    # confirm no later than 12 bars after P2
    "edge_sources": ["VAH", "SESSION_HIGH", "IB_HIGH"],
}

CEILING_FAILED = "CEILING_FAILED"
FLOOR_FAILED = "FLOOR_FAILED"

# edge_source → (ceiling level key, floor level key) in the `levels` dict
_EDGE_KEYS: Dict[str, tuple] = {
    "VAH": ("vah", "val"),
    "SESSION_HIGH": ("session_high", "session_low"),
    "IB_HIGH": ("ib_high", "ib_low"),
}


def _f(bar: Dict[str, Any], *keys: str) -> Optional[float]:
    """First readable float among `keys` (family convention: failed_break.py)."""
    for k in keys:
        v = bar.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


def _ohlc(bars: Sequence[Dict[str, Any]]) -> Optional[tuple]:
    """(highs, lows, closes) as float lists — or None if any bar is unreadable."""
    highs: List[float] = []
    lows: List[float] = []
    closes: List[float] = []
    for b in bars:
        h = _f(b, "h", "high")
        low = _f(b, "l", "low")
        c = _f(b, "c", "close")
        if h is None or low is None or c is None:
            return None
        highs.append(h)
        lows.append(low)
        closes.append(c)
    return highs, lows, closes


def _merged_cfg(cfg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    out = dict(DEFAULTS)
    if isinstance(cfg, dict):
        for k, v in cfg.items():
            if k in DEFAULTS and v is not None:
                out[k] = v
    # bar counts must be sane integers; a broken config falls back per key
    for k in ("max_bars_between", "min_bars_between", "confirm_max_bars"):
        try:
            out[k] = int(out[k])
        except (TypeError, ValueError):
            out[k] = DEFAULTS[k]
    try:
        out["tol_atr"] = float(out["tol_atr"])
    except (TypeError, ValueError):
        out["tol_atr"] = DEFAULTS["tol_atr"]
    if not isinstance(out["edge_sources"], (list, tuple)) or not out["edge_sources"]:
        out["edge_sources"] = DEFAULTS["edge_sources"]
    out["min_bars_between"] = max(1, out["min_bars_between"])
    out["max_bars_between"] = max(out["min_bars_between"], out["max_bars_between"])
    out["confirm_max_bars"] = max(1, out["confirm_max_bars"])
    return out


def _argmax(values: Sequence[float], lo: int, hi: int) -> int:
    """Index of the max in values[lo..hi] inclusive; ties → the EARLIEST index.

    Deterministic tie-breaking is what makes unit == replay == shadow: an
    equal-high double top must resolve to the same pair of indices every run.
    """
    best = lo
    for i in range(lo + 1, hi + 1):
        if values[i] > values[best]:
            best = i
    return best


def _argmin(values: Sequence[float], lo: int, hi: int) -> int:
    best = lo
    for i in range(lo + 1, hi + 1):
        if values[i] < values[best]:
            best = i
    return best


def _scan_ceiling(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    edge: float,
    tol: float,
    cfg: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """The whole detector, in CEILING orientation only.

    FLOOR reuses this function on a sign-flipped series (see `_scan_floor`), so
    the two sides cannot drift apart — there is exactly one implementation of
    the geometry.

    The last bar is the confirm candidate. Returns raw indices/prices or None.
    """
    last = len(highs) - 1
    min_gap = cfg["min_bars_between"]
    max_gap = cfg["max_bars_between"]
    confirm_max = cfg["confirm_max_bars"]

    # P1 lives inside a window that could still confirm on this bar:
    # at most max_gap (P1→P2) + confirm_max (P2→confirm) bars back.
    p1_hi = last - min_gap - 1          # P2 needs min_gap after P1, confirm after P2
    if p1_hi < 0:
        return None
    p1_lo = max(0, last - (max_gap + confirm_max))
    if p1_lo > p1_hi:
        return None

    # TOUCH-1: the highest high in the window — the ceiling itself.
    i1 = _argmax(highs, p1_lo, p1_hi)
    p1 = highs[i1]
    if p1 < edge:                        # never reached the edge → not this source
        return None

    # TOUCH-2: the best second peak inside the allowed bar distance.
    p2_lo = i1 + min_gap
    p2_hi = min(i1 + max_gap, last - 1)  # confirm bar must be strictly after P2
    if p2_lo > p2_hi:
        return None
    i2 = _argmax(highs, p2_lo, p2_hi)
    p2 = highs[i2]
    if abs(p2 - p1) > tol:               # not "the same area" (relative to ATR)
        return None

    # CONFIRM bar must be within reach of P2.
    if not (0 < last - i2 <= confirm_max):
        return None

    # REJECTION: a close back below the edge between the two touches.
    if not any(closes[k] < edge for k in range(i1 + 1, i2 + 1)):
        return None

    # "failed to advance": no close above P1 on the way to / at the second
    # peak. Mostly implied by P1 being the window argmax — the exception, and
    # the reason this stays explicit, is P2 == last-1, which sits OUTSIDE the
    # window P1 was chosen from and so can out-close it (mutation-verified:
    # tests::test_second_peak_closing_above_p1_is_rejected).
    if max(closes[i1 + 1:i2 + 1]) > p1:
        return None

    # ...and no new breakout above the ceiling between P2 and the confirm bar.
    if max(highs[i2 + 1:last + 1]) > p1 + tol:
        return None

    # NECKLINE: lowest low of the span (P1 .. P2] — see module docstring.
    j = _argmin(lows, i1 + 1, i2)
    neckline = lows[j]
    if closes[last] >= neckline:          # not yet broken → no state
        return None

    return {
        "p1": p1,
        "p2": p2,
        "p1_index": i1,
        "p2_index": i2,
        "neckline": neckline,
        "neckline_index": j,
        "confirm_bar_extreme": lows[last],
        "confirm_close": closes[last],
        "bars_between": i2 - i1,
        "bars_to_confirm": last - i2,
    }


def _scan_floor(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    edge: float,
    tol: float,
    cfg: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """FLOOR = CEILING on a sign-flipped chart. Exact mirror, by construction."""
    res = _scan_ceiling(
        [-x for x in lows],       # peaks become troughs
        [-x for x in highs],
        [-x for x in closes],
        -edge,
        tol,
        cfg,
    )
    if res is None:
        return None
    for k in ("p1", "p2", "neckline", "confirm_bar_extreme", "confirm_close"):
        res[k] = -res[k]
    return res


def detect_ceiling_floor(
    bars: Sequence[Dict[str, Any]],
    levels: Optional[Dict[str, Any]],
    atr: Optional[float],
    cfg: Optional[Dict[str, Any]] = None,
    *,
    already_fired: Optional[Set[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Detect a failed double ceiling / double floor on the LAST bar.

    Args:
        bars: 5-min bars, OLDEST first, each with h/l/c (or high/low/close).
              The last element is the confirm candidate — it must be a CLOSED
              bar; feeding a building bar is the caller's bug, not this one's.
        levels: {"vah", "val", "session_high", "session_low", "ib_high",
                 "ib_low"} — any subset. A missing/None/non-numeric level
                simply disables that edge source (Rule 1: no invention).
        atr: ATR(14) on the same 5-min series. **None or <= 0 → None.**
             Every threshold here is relative to it, so without it there is no
             honest answer.
        cfg: config/ceiling_floor.yaml section; DEFAULTS fill the gaps.
        already_fired: keys returned as `result["key"]` that must not re-fire.

    Returns:
        {"state": "CEILING_FAILED"|"FLOOR_FAILED", "p1", "p2",
         "confirm_bar_low" (CEILING) / "confirm_bar_high" (FLOOR),
         "edge_source": "VAH"|"SESSION_HIGH"|"IB_HIGH" for a ceiling,
                        "VAL"|"SESSION_LOW"|"IB_LOW" for the mirror,
         "edge_family": the configured source name, "bars_between",
         "confirm_level" (the neckline), "signal_bar_ts", "key", ...} — or None.

    Pure: same input ⇒ byte-identical output in unit, replay and shadow.
    """
    if atr is None:
        return None
    try:
        atr_f = float(atr)
    except (TypeError, ValueError):
        return None
    if not (atr_f > 0):
        return None
    if not bars or len(bars) < 3:
        return None

    parsed = _ohlc(bars)
    if parsed is None:
        return None
    highs, lows, closes = parsed

    conf = _merged_cfg(cfg)
    tol = conf["tol_atr"] * atr_f
    lv = levels if isinstance(levels, dict) else {}
    fired = already_fired or set()
    last_bar = bars[-1]
    signal_bar_ts = last_bar.get("ts", last_bar.get("ets"))

    for source in conf["edge_sources"]:
        keys = _EDGE_KEYS.get(str(source).upper())
        if not keys:
            continue
        hi_key, lo_key = keys
        for state, level_key, scan in (
            (CEILING_FAILED, hi_key, _scan_ceiling),
            (FLOOR_FAILED, lo_key, _scan_floor),
        ):
            raw = lv.get(level_key)
            if raw is None:
                continue
            try:
                edge = float(raw)
            except (TypeError, ValueError):
                continue
            res = scan(highs, lows, closes, edge, tol, conf)
            if res is None:
                continue
            # Dedup key is the STRUCTURE, not the label: the same double top
            # qualifies under several edges at once (28.08 fired under VAH at
            # 18:35 and, one bar later, identically under SESSION_HIGH), and a
            # source-tagged key let the same event through twice.
            key = "%s|%.2f|%.2f" % (state, res["p1"], res["p2"])
            if key in fired:
                continue
            out: Dict[str, Any] = {
                "state": state,
                "key": key,
                "p1": round(res["p1"], 2),
                "p2": round(res["p2"], 2),
                # concrete level name: VAH/SESSION_HIGH/IB_HIGH for a ceiling
                # (exactly the spec's vocabulary), VAL/SESSION_LOW/IB_LOW for
                # the mirror — labelling a floor "SESSION_HIGH" would be a lie.
                "edge_source": level_key.upper(),
                "edge_family": str(source).upper(),
                "edge_price": round(edge, 2),
                "confirm_level": round(res["neckline"], 2),
                "confirm_close": round(res["confirm_close"], 2),
                "bars_between": int(res["bars_between"]),
                "bars_to_confirm": int(res["bars_to_confirm"]),
                "p1_index": int(res["p1_index"]),
                "p2_index": int(res["p2_index"]),
                "atr": round(atr_f, 4),
                "tol": round(tol, 4),
                "signal_bar_ts": signal_bar_ts,
            }
            extreme = round(res["confirm_bar_extreme"], 2)
            if state == CEILING_FAILED:
                out["confirm_bar_low"] = extreme
            else:
                out["confirm_bar_high"] = extreme
            return out
    return None
