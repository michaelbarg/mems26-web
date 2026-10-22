# -*- coding: utf-8 -*-
"""MID_VALUE_EDGE_TEST_V1 (T-635 D2, 22.10.2026) — PURE geometry, no IO.

Michael 22.10 ("זום-אין לפי עסקה"): six demo entries inside the value area on 19–20.10
(#3483 #3501 #3508 #3515 #3574 #3582, −337.5$) all came AFTER the edge had been tested
(VAL / yesterday's VAH) — but the entry was 0.5–2 ATR away from the tested extreme, on the
POC, in the middle of the rotation, with the stop inside the rotation. None of the three
winners entered inside value. Dalton: inside value the trade is responsive — buy the VAL
test, sell the VAH test; the POC is fair price, there is no edge there.

Doctrine condition (consistent with Michael's 17.09 ruling that with-extension entries are
not blocked as such): an entry INSIDE the value area is allowed only as the test of an edge —
one of the last `lookback` closed bars touched the edge (≤ touch_atr × ATR beyond/at it) and
the entry is ≤ near_atr × ATR from that edge. Otherwise: blocked (mid_value_no_edge_test).

Levels for a LONG (edges below the entry): today's VAL, IB low, yesterday's VAL / VAH / low.
For a SHORT: today's VAH, IB high, yesterday's VAH / VAL / high. Missing levels are skipped.
"""
from typing import Dict, Iterable, List, Optional


def _f(v) -> Optional[float]:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x == x and x > 0 else None


def _hl(b) -> Optional[tuple]:
    if not isinstance(b, dict):
        return None
    h = _f(b.get("h", b.get("high"))); l = _f(b.get("l", b.get("low")))
    return (h, l) if (h is not None and l is not None) else None


def bars_atr(bars: Iterable[dict], n: int = 14) -> Optional[float]:
    """Simple ATR proxy from the last n closed bars (mean high−low). None when < 3 bars."""
    rng = [h - l for h, l in (x for x in (_hl(b) for b in (bars or [])) if x) if h >= l]
    rng = rng[-n:]
    if len(rng) < 3:
        return None
    return sum(rng) / len(rng)


def is_mid_value(entry: float, vah: Optional[float], val: Optional[float], poc: Optional[float],
                 atr: float, edge_atr: float = 0.5) -> bool:
    """Inside the value area AND more than edge_atr × ATR away from both VAH and VAL (or on the POC)."""
    e = _f(entry); a = _f(atr)
    if e is None or a is None:
        return False
    vah = _f(vah); val = _f(val); poc = _f(poc)
    if vah is not None and val is not None and val < vah:
        inside = (val + edge_atr * a) < e < (vah - edge_atr * a)
        if inside:
            return True
    if poc is not None and abs(e - poc) <= 1.0 * a and (vah is None or val is None):
        return True
    return False


def mid_value_edge_test(direction: str, entry: float, bars: List[dict], levels: Dict[str, Optional[float]],
                        atr: Optional[float], *, touch_atr: float = 0.25, near_atr: float = 0.5,
                        lookback: int = 2) -> Dict:
    """Decide whether an inside-value entry is a legitimate edge test.

    levels: {"val","vah","ib_low","ib_high","prev_val","prev_vah","prev_low","prev_high"} (any may be None)
    Returns {"ok": bool, "why": str, "edge": float|None, "tested": [edges touched], "lo2": .., "hi2": ..}.
    Fail-open (ok=True) when there are no closed bars or no ATR — the gate must never block blind.
    """
    d = (direction or "").upper()
    e = _f(entry)
    hls = [x for x in (_hl(b) for b in (bars or [])) if x][-max(1, int(lookback)):]
    a = _f(atr) or bars_atr(bars)
    if d not in ("LONG", "SHORT") or e is None or not hls or a is None:
        return {"ok": True, "why": "fail-open: no direction/entry/bars/atr", "edge": None, "tested": [],
                "lo2": None, "hi2": None}
    lo2 = min(l for _, l in hls); hi2 = max(h for h, _ in hls)
    if d == "LONG":
        names = ("val", "ib_low", "prev_val", "prev_vah", "prev_low")
        cands = [(n, lv) for n, lv in ((n, _f(levels.get(n))) for n in names) if lv is not None and lv <= e + touch_atr * a]
        tested = [(n, lv) for n, lv in cands if lo2 <= lv + touch_atr * a]
        near = [(n, lv) for n, lv in tested if (e - lv) <= near_atr * a]
    else:
        names = ("vah", "ib_high", "prev_vah", "prev_val", "prev_high")
        cands = [(n, lv) for n, lv in ((n, _f(levels.get(n))) for n in names) if lv is not None and lv >= e - touch_atr * a]
        tested = [(n, lv) for n, lv in cands if hi2 >= lv - touch_atr * a]
        near = [(n, lv) for n, lv in tested if (lv - e) <= near_atr * a]
    if near:
        n, lv = near[0]
        return {"ok": True, "why": "edge test %s=%.2f (entry %.2f, %.2f pts = %.2f ATR)" % (n, lv, e, abs(e - lv), abs(e - lv) / a),
                "edge": lv, "tested": [lv for _, lv in tested], "lo2": lo2, "hi2": hi2}
    if tested:
        n, lv = tested[0]
        return {"ok": False, "why": "edge %s=%.2f was tested (lo2=%.2f hi2=%.2f) but the entry %.2f is %.2f pts = %.2f ATR from it (> %.2f ATR) — the middle after the test"
                % (n, lv, lo2, hi2, e, abs(e - lv), abs(e - lv) / a, near_atr),
                "edge": lv, "tested": [lv for _, lv in tested], "lo2": lo2, "hi2": hi2}
    return {"ok": False, "why": "no edge tested in the last %d bars (lo2=%.2f hi2=%.2f; edges %s) — inside value without a test"
            % (len(hls), lo2, hi2, ", ".join("%s=%.2f" % (n, lv) for n, lv in cands) or "none"),
            "edge": None, "tested": [], "lo2": lo2, "hi2": hi2}
