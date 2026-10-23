"""T-640 F1 — an entry that moves INTO yesterday's value after a rejected gap is not "beyond value".

Michael 23.10 18:0x ("תסביר לי איך לדעתך מנוהל היום … איך היה צריך לסחור מהפתיחה בהתייחס למיקום הפתיחה
לדוקטרינה לפריצה … איך מתקנים") · "האם ניתן לתקן הכל עכשיו?" · "תמשיך".

23.10: the open (7661) sat 16 pt BELOW yesterday's RTH range (low 7677, value 7685.5–7714). The market rotated
under the gap for an hour, broke the IB high at 17:40 and closed back inside yesterday's range — Dalton
(Mind Over Markets, the open relative to the previous day): an open outside the range that is REJECTED back into
the range is a strong move in the opposite direction, and once inside yesterday's value it tends to traverse it
(the 80% rule). At 18:05 the with-move TREND_STEP LONG @7686 (on yesterday's VAL, three bars of pause) was
blocked by ELQ "beyond_value ex=0.33" — measured against TODAY's value (the 7650–7685 gap rotation), i.e. the
gate called the move TOWARD value a chase PAST value. Same bar, the counter-extension CEILING_FLIP_TOUCH2 SHORT
was taken (#3876, −175$).

The rule (pure): admitted as "toward yesterday's value" — so the ELQ beyond-value arm does not apply — when
  • today's RTH open was OUTSIDE yesterday's value area (below VAL or above VAH);
  • the gap has been REJECTED: the last closed bar closed back inside yesterday's range beyond the gap-side edge
    (open below ⇒ close > yesterday's low; open above ⇒ close < yesterday's high) — when yesterday's high/low
    are unknown, yesterday's VAL/VAH stand in for them;
  • the entry points INTO yesterday's value (open below ⇒ LONG, open above ⇒ SHORT);
  • and the entry is still on the near side of yesterday's POC (no chasing the far half of the value area).
Anything else ⇒ (False, why) and ELQ judges as before. Fail-closed to "not admitted" on missing data.
Unit-tested in tests/v9/regression/test_prior_value_target.py.
"""
from __future__ import annotations

from typing import Optional, Tuple


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def toward_prior_value(direction: str, entry, open_price, last_close, prev_vah, prev_val, prev_poc,
                       prev_high=None, prev_low=None) -> Tuple[bool, str]:
    """(admitted, why) — see the module docstring."""
    d = str(direction or "").upper()
    e, o, c = _f(entry), _f(open_price), _f(last_close)
    vah, val, poc = _f(prev_vah), _f(prev_val), _f(prev_poc)
    ph, pl = _f(prev_high), _f(prev_low)
    if None in (e, o, c, vah, val) or vah <= val or d not in ("LONG", "SHORT"):
        return False, "missing data"
    if poc is None or not (val <= poc <= vah):
        poc = (vah + val) / 2.0
    lo_edge = pl if pl is not None else val
    hi_edge = ph if ph is not None else vah
    if o < val:
        if d != "LONG":
            return False, "open below yesterday's value — only a LONG points into it"
        if c <= lo_edge:
            return False, "gap not rejected: last close %.2f ≤ yesterday's low/edge %.2f" % (c, lo_edge)
        if e > poc:
            return False, "entry %.2f already past yesterday's POC %.2f" % (e, poc)
        return True, ("open %.2f below yesterday's value %.2f–%.2f, rejected back inside the range (close %.2f > %.2f) — "
                      "LONG %.2f toward value (POC %.2f)" % (o, val, vah, c, lo_edge, e, poc))
    if o > vah:
        if d != "SHORT":
            return False, "open above yesterday's value — only a SHORT points into it"
        if c >= hi_edge:
            return False, "gap not rejected: last close %.2f ≥ yesterday's high/edge %.2f" % (c, hi_edge)
        if e < poc:
            return False, "entry %.2f already past yesterday's POC %.2f" % (e, poc)
        return True, ("open %.2f above yesterday's value %.2f–%.2f, rejected back inside the range (close %.2f < %.2f) — "
                      "SHORT %.2f toward value (POC %.2f)" % (o, val, vah, c, hi_edge, e, poc))
    return False, "open %.2f inside yesterday's value %.2f–%.2f" % (o, val, vah)
