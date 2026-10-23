"""Opening type v2 — Dalton's four openings read on CLOSED RTH 5-min bars, in ATR units.

Michael 23.10 09:5x–10:2x ("האם פתרת את סיווג סוג הפתיחה?" · "תקרא שוב דלתון איך צריך לסווג ותבחן פערים ותקרא
בעצמך גם את הימים ב-30 ימים … עד הפתיחה אתה כבר צריך לדעת להגדיר בצורה מצוינת סוג פתיחה ושלא יהיה בקלות מדי
שיהיה נכון").

Why a second classifier: the T-314 label matched the bars on 7/24 days of 08.09–16.10 (AUCTION_IN was its
default on 12 days, 7 of them 15–22 pt drives) and the opening engine's TEST_DRIVE trigger fired on a ONE-TICK
close through the open (22.10 #3749). This module is a pure function of the bars, scaled by the prior session's
5-min ATR, with Dalton pp.63–74 written as numbers (our words):

  OPEN_DRIVE             conviction from the first bars: the price drives one way, never closes back through the
                         open, the open is not re-traded once the drive is under way, and the gain holds.
  OPEN_TEST_DRIVE        the first leg goes to a KNOWN reference (yesterday's high/low, value-area edge, overnight
                         extreme), fails there, and the price reverses through the open into a drive that holds.
  OPEN_REJECTION_REVERSE the first leg is a real move that is rejected with NO reference behind it; the price
                         reverses through the open and the other side holds. Low conviction (the initial
                         extreme holds < 50%).
  OPEN_AUCTION_IN/OUT    no conviction: rotation around the open. IN = the open is inside yesterday's RTH range,
                         OUT = outside it (out of balance ⇒ a large move later is possible either way).

The difference between TEST_DRIVE and REJECTION_REVERSE is the REFERENCE, not the size of the first leg
(Dalton p.65 vs p.68); the difference between both and an AUCTION is the reversal CLOSE ≥ 0.5 ATR beyond the
open and the other side holding.

Strictness ("שלא יהיה בקלות מדי"): read on CLOSED bars only; a drive needs ≥ DRIVE_U ATR inside the first 6 bars
and locks only after 4 bars (20 min); a reversal needs a CLOSE ≥ 0.5 ATR beyond the open; an auction locks only
after 8 bars (40 min) so a slow test-drive still has room; and a locked directional reading is REVOKED when a
later bar (inside the first 8) closes back through the open — Dalton: a return through the drive's origin means
the conditions have changed. Calibrated by hand on 33 sessions 08.09–22.10 (docs/reports/OPENING_V2_STUDY_2026-10-23.md).

Pure: no I/O, no clock. `OpeningLock` keeps the lock/revocation state for a caller that feeds bars as they close.
Unit-tested in tests/v9/regression/test_opening_classifier_v2.py.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

TYPES = ("OPEN_DRIVE", "OPEN_TEST_DRIVE", "OPEN_REJECTION_REVERSE", "OPEN_AUCTION_IN", "OPEN_AUCTION_OUT")
TICK = 0.25

# --- thresholds in ATR units (the prior RTH session's mean 5-min range; floored at MIN_UNIT_PTS) ---
MIN_UNIT_PTS = 3.0
DRIVE_U = 1.75           # a drive: ≥ 1.75 ATR from the open inside the drive window …
DRIVE_ONESIDED_U = 1.5   # … or ≥ 1.5 ATR when the other side was never explored (≤ ONESIDED_ADV_U)
ONESIDED_ADV_U = 0.3
DRIVE_ADV_U = 0.5        # a drive tolerates against it: max(0.5 ATR, 20% of its reach) …
DRIVE_ADV_FRAC = 0.2
DRIVE_BAR1_ADV_U = 1.2   # … and the opening bar itself up to 1.2 ATR
RETRADE_PRE_U = 0.6      # the open may be re-traded ≤ 0.6 ATR before the drive has 1 ATR, ≤ 2 ticks after
HOLD_U = 1.0             # the last close must still be ≥ 1 ATR on the drive side
LEG_MIN_U = 0.4          # a first leg smaller than this is noise
LEG_DOMINANCE = 0.7      # before the first leg's extreme, the other side may have at most 70% of it
REF_TOL_U = 0.5          # the leg "reached" a reference when it got within 0.5 ATR of it (or beyond)
REV_CLOSE_U = 0.5        # the reversal must CLOSE ≥ 0.5 ATR beyond the open on the other side
ORR_FIRST_U = 1.25       # rejection-reverse (no reference): the first leg must be ≥ 1.25 ATR AND have closed ≥ 0.5 ATR out …
ORR_SECOND_U = 1.0       # … and the reversal side must reach ≥ 1 ATR
DRIVE_WINDOW = 6         # bars in which a drive must reach DRIVE_U (30 min)
REV_WINDOW = 8           # bars in which a reversal close must happen (40 min)
DRIVE_LOCK_BARS = 4
REV_LOCK_BARS = 3
AUCTION_LOCK_BARS = 8
REVOKE_WINDOW = 8        # a locked directional reading can be revoked by a close through the open up to bar 8
MAX_BARS = 12            # the opening is judged on the first hour at most


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def _ohlc(b: dict) -> Optional[Tuple[float, float, float, float]]:
    o = _f(b.get("o", b.get("open"))); h = _f(b.get("h", b.get("high")))
    l = _f(b.get("l", b.get("low"))); c = _f(b.get("c", b.get("close")))
    if None in (o, h, l, c) or h < l:
        return None
    return o, h, l, c


def unit_from_atr(atr: Optional[float]) -> float:
    a = _f(atr)
    return max(a if a else 0.0, MIN_UNIT_PTS)


REF_KEYS = ("high", "low", "vah", "val", "on_high", "on_low")


def _refs(prev: Optional[dict], side: str, o: float) -> List[Tuple[str, float]]:
    """known references on one side of the open: yesterday's high/low, VAH/VAL and the overnight high/low —
    whichever of them lies on that side (after a gap, yesterday's LOW is a reference ABOVE the open)."""
    out = []
    for k in REF_KEYS:
        v = _f((prev or {}).get(k))
        if v is None:
            continue
        if (side == "down" and v < o) or (side == "up" and v > o):
            out.append((k, v))
    return out


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def classify_opening_v2(bars: Iterable[dict], prev: Optional[dict] = None, atr: Optional[float] = None) -> Dict:
    """Read the opening from today's CLOSED RTH 5-min bars (oldest first; only the first MAX_BARS are used).

    prev: {"high","low","vah","val","poc","on_high","on_low"} of the prior session (any subset).
    atr:  the prior session's mean 5-min range in points (None ⇒ MIN_UNIT_PTS).

    Returns {"type","direction" ("up"/"down"/""),"locked","confidence","bars","unit","why","metrics"}.
    Never raises on bad input: returns type "UNKNOWN". Stateless — see OpeningLock for lock persistence.
    """
    rows = [x for x in (_ohlc(b) for b in (bars or []) if isinstance(b, dict)) if x][:MAX_BARS]
    n = len(rows)
    u = unit_from_atr(atr)
    base = {"type": "UNKNOWN", "direction": "", "locked": False, "confidence": 0.0, "bars": n, "unit": round(u, 2),
            "why": "", "metrics": {}}
    if n == 0:
        base["why"] = "no closed RTH bars yet"
        return base
    o = rows[0][0]
    highs = [r[1] for r in rows]; lows = [r[2] for r in rows]; closes = [r[3] for r in rows]
    up = [h - o for h in highs]; dn = [o - l for l in lows]
    max_up = max(up); max_dn = max(dn)
    last = closes[-1]
    retrades = sum(1 for i in range(1, n) if lows[i] <= o <= highs[i])
    metrics = {"open": o, "max_up": round(max_up, 2), "bar_up": up.index(max_up) + 1, "max_dn": round(max_dn, 2),
               "bar_dn": dn.index(max_dn) + 1, "last_close_vs_open": round(last - o, 2), "retrades_of_open": retrades,
               "max_up_u": round(max_up / u, 2), "max_dn_u": round(max_dn / u, 2)}
    base["metrics"] = metrics

    def done(t: str, d: str, locked: bool, conf: float, why: str) -> Dict:
        base.update({"type": t, "direction": d, "locked": bool(locked), "confidence": round(_clamp(conf), 2), "why": why})
        return base

    # ------------------------------------------------------------------ 1. OPEN_DRIVE
    def drive(sign: int) -> Optional[Dict]:
        fav = up if sign > 0 else dn
        adv = dn if sign > 0 else up
        win = fav[:DRIVE_WINDOW]
        reach = max(win)
        adv_all = max(adv); adv_after1 = max(adv[1:]) if n > 1 else 0.0
        one_sided = adv_all <= ONESIDED_ADV_U * u
        if not (reach >= DRIVE_U * u or (one_sided and reach >= DRIVE_ONESIDED_U * u)):
            return None
        if adv[0] > DRIVE_BAR1_ADV_U * u or adv_after1 > max(DRIVE_ADV_U * u, DRIVE_ADV_FRAC * reach):
            return None
        # every close after the first bar on the drive side
        if any((closes[i] - o) * sign <= 0 for i in range(1, n)):
            return None
        # the open is not re-traded once the drive is under way (≤ 2 ticks), and only lightly before
        running = 0.0
        for i in range(1, n):
            running = max(running, (closes[i - 1] - o) * sign)   # under way = a CLOSE ≥ 1 ATR on the drive side
            through = adv[i]
            if through > (2 * TICK if running >= 1.0 * u else RETRADE_PRE_U * u):
                return None
        if (last - o) * sign < HOLD_U * u:
            return None
        locked = n >= DRIVE_LOCK_BARS
        d = "up" if sign > 0 else "down"
        conf = 0.55 + 0.12 * (reach / u - DRIVE_U) - 0.3 * (adv_all / u)
        return done("OPEN_DRIVE", d, locked, conf,
                    "drive %s %.2f pts (%.1f ATR) by bar %d, against ≤ %.2f, open never closed-through, holds %+.2f"
                    % (d, reach, reach / u, win.index(reach) + 1, adv_all, last - o))

    r = drive(+1) or drive(-1)
    if r:
        return r

    # ------------------------------------------------------------------ 2./3. two-sided with a reversal through the open
    def reversal(sign: int) -> Optional[Dict]:
        """first leg against `sign`, then a close ≥ REV_CLOSE_U beyond the open with `sign`, and that side holds."""
        first = dn if sign > 0 else up        # the first (rejected) leg
        second = up if sign > 0 else dn       # the reversal side
        for k_rev in range(2, min(n, REV_WINDOW)):
            if (closes[k_rev] - o) * sign < REV_CLOSE_U * u:
                continue
            e1 = max(first[:k_rev]); k1 = first.index(e1)
            if e1 < LEG_MIN_U * u:
                continue
            opp = list(second[:k1 + 1])
            if opp and (closes[0] - o) * sign < 0:                 # bar 1 closed on the first leg's side ⇒ its opposite wick is noise
                opp[0] = 0.0
            if max(opp) > LEG_DOMINANCE * e1:                      # the first leg was not the dominant move
                continue
            if any((closes[i] - o) * sign <= 0 for i in range(k_rev, n)):  # the reversal side must hold
                return None
            e2 = max(second[k_rev:])
            ext_price = (o - e1) if sign > 0 else (o + e1)
            refs = _refs(prev, "down" if sign > 0 else "up", o)
            hit = [k for k, v in refs if ((ext_price <= v + REF_TOL_U * u) if sign > 0 else (ext_price >= v - REF_TOL_U * u))]
            d = "up" if sign > 0 else "down"
            lead = "down" if sign > 0 else "up"
            if hit and e2 >= DRIVE_U * u:
                conf = 0.55 + 0.1 * (e2 / u - DRIVE_U) + 0.05 * min(len(hit), 2)
                return done("OPEN_TEST_DRIVE", d, n >= REV_LOCK_BARS, conf,
                            "test %s %.2f pts (%.1f ATR) to %s at bar %d failed, reversal closed through the open at bar %d, drive %s %.2f pts (%.1f ATR), holds %+.2f"
                            % (lead, e1, e1 / u, "/".join(hit), k1 + 1, k_rev + 1, d, e2, e2 / u, last - o))
            leg_closed = any((o - closes[i]) * sign >= REV_CLOSE_U * u for i in range(0, k1 + 1))   # the leg was a drive, not a wick
            if e1 >= ORR_FIRST_U * u and e2 >= ORR_SECOND_U * u and leg_closed:
                conf = 0.45 + 0.08 * (e1 / u - ORR_FIRST_U) + 0.08 * (e2 / u - ORR_SECOND_U) + (0.05 if hit else 0.0)
                return done("OPEN_REJECTION_REVERSE", d, n >= REV_LOCK_BARS, conf,
                            "first leg %s %.2f pts (%.1f ATR, %s) to bar %d rejected, reversal closed through the open at bar %d, %s side %.2f pts holds %+.2f"
                            % (lead, e1, e1 / u, ("at " + "/".join(hit)) if hit else "no reference", k1 + 1, k_rev + 1, d, e2, last - o))
            return None   # a reversal close happened but neither pattern is big enough ⇒ auction
        return None

    r = reversal(+1) or reversal(-1)
    if r:
        return r

    # ------------------------------------------------------------------ 4. OPEN_AUCTION (in / out of yesterday's range)
    ph = _f((prev or {}).get("high")); pl = _f((prev or {}).get("low"))
    vah = _f((prev or {}).get("vah")); val = _f((prev or {}).get("val"))
    if ph is not None and pl is not None:
        inside = pl <= o <= ph
        t = "OPEN_AUCTION_IN" if inside else "OPEN_AUCTION_OUT"
        loc = ("inside yesterday's range %.2f–%.2f" % (pl, ph)) if inside else \
              ("%s yesterday's range %.2f–%.2f" % ("above" if o > ph else "below", pl, ph))
        if vah is not None and val is not None:
            loc += " · %s value %.2f–%.2f" % ("inside" if val <= o <= vah else "outside", val, vah)
    else:
        t = "OPEN_AUCTION"; loc = "no prior range"
    locked = n >= AUCTION_LOCK_BARS
    conf = 0.35 + 0.05 * min(n, AUCTION_LOCK_BARS) - 0.1 * max(0.0, max(max_up, max_dn) / u - 1.5)
    return done(t, "", locked, conf,
                "rotation around the open (up %.2f / down %.2f pts = %.1f/%.1f ATR, open re-traded %d×), %s%s"
                % (max_up, max_dn, max_up / u, max_dn / u, retrades, loc, "" if locked else " — provisional until bar %d" % AUCTION_LOCK_BARS))


class OpeningLock:
    """Lock persistence for a caller that feeds the closed bars as they arrive.

    update(bars, prev, atr) → the reading to USE: once a reading is locked it is kept bar after bar, unless a
    later bar (inside REVOKE_WINDOW) closes back through the open against a directional reading — then the lock
    is revoked and the fresh reading (re-read from scratch) is taken. An auction lock is final.
    """

    def __init__(self):
        self.locked: Optional[Dict] = None
        self.locked_bar: Optional[int] = None
        self.revoked: List[Tuple[int, str]] = []   # (bar, type) history

    def update(self, bars: Iterable[dict], prev: Optional[dict] = None, atr: Optional[float] = None) -> Dict:
        bars = list(bars or [])
        fresh = classify_opening_v2(bars, prev, atr)
        n = fresh.get("bars", 0)
        if self.locked is not None:
            lt = self.locked.get("type", ""); ld = self.locked.get("direction", "")
            if lt.startswith("OPEN_AUCTION") or n > REVOKE_WINDOW or n == 0:
                out = dict(self.locked); out["bars"] = n; out["kept"] = True
                return out
            # a rejection-reverse that develops into a drive on the same side is upgraded to a test-drive
            if (lt == "OPEN_REJECTION_REVERSE" and fresh.get("type") == "OPEN_TEST_DRIVE"
                    and fresh.get("direction") == ld and fresh.get("locked")):
                fresh["upgraded_from"] = lt
                self.locked = dict(fresh); self.locked_bar = n
                return fresh
            o = _f(bars[0].get("o", bars[0].get("open")))
            c = _f(bars[-1].get("c", bars[-1].get("close")))
            sign = 1 if ld == "up" else -1
            if o is not None and c is not None and (c - o) * sign <= 0:
                self.revoked.append((n, lt))
                self.locked, self.locked_bar = None, None
                fresh["revoked_from"] = lt
                fresh["why"] = "REVOKED %s at bar %d (close %+.2f back through the open) ⇒ " % (lt, n, c - o) + fresh.get("why", "")
            else:
                out = dict(self.locked); out["bars"] = n; out["kept"] = True
                return out
        if fresh.get("locked"):
            self.locked = dict(fresh); self.locked_bar = n
        return fresh


def describe(res: Dict) -> str:
    """One log line."""
    if not isinstance(res, dict):
        return "UNKNOWN"
    return "%s%s dir=%s conf=%.2f bars=%d unit=%.2f — %s" % (
        res.get("type"), " LOCKED" if res.get("locked") else " provisional", res.get("direction") or "-",
        float(res.get("confidence") or 0), int(res.get("bars") or 0), float(res.get("unit") or 0), res.get("why") or "")
