# -*- coding: utf-8 -*-
"""OPENING_HALF_RANGE_GATE_V1 — PURE verdict (no IO, no env). T-628 (21.10) + T-636 (22.10).

T-628 (mode "1"): on an OPEN_AUCTION opening in phase A/B an OPENING_* entry may not chase — a LONG only in the
lower half of the running opening range (today's closed RTH bars so far), a SHORT only in the upper half.

T-636 (mode "all", Michael 22.10 "למה שוב הפסדנו כסף בפתיחה… סוג הפתיחה צריך לבדוק"): the same rule on EVERY
canonical opening type, OPENING_ORR exempt (the reversal bar through the open is the template's own test —
20.10 #3544 +496 is an ORR at the range top), plus the agreement check: an OPENING_DRIVE / OPENING_TEST_DRIVE
trigger while the canonical detector reads an auction or a rejection-reverse is a contradiction (22.10 #3749:
the producer's "drive" close was one tick through the open; the canonical type was OPEN_AUCTION_IN).
Checked on the past: 22.10 #3749 −221 · 21.10 #3637 −225 · 20.10 #3540 −225 · 19.10 16:50 DRIVE SHORT −210
all blocked; 20.10 #3544 (ORR) kept.
"""
from typing import Any, Dict, Optional, Sequence, Tuple


def _hl(b):
    if not isinstance(b, dict):
        return None
    try:
        h = float(b.get("h", b.get("high"))); l = float(b.get("l", b.get("low")))
    except (TypeError, ValueError):
        return None
    return (h, l)


def opening_half_range_verdict(classification: str, direction: str, entry: float, opening_type: str, phase: str,
                               bars: Sequence[Dict[str, Any]], mode: str) -> Optional[Tuple[str, str]]:
    """(blocked_by, reason) or None. mode: "0"/unset ⇒ never; "1" ⇒ T-628 as measured; "all" ⇒ T-636."""
    m = str(mode or "0").strip().lower()
    on_all = m == "all"
    on_auction = m in ("1", "true", "yes")
    if not (on_all or on_auction):
        return None
    cls = str(classification or "").upper(); d = str(direction or "").upper(); ot = str(opening_type or "").upper()
    if not cls.startswith("OPENING_") or phase not in ("A", "B"):
        return None
    if on_all and cls in ("OPENING_DRIVE", "OPENING_TEST_DRIVE") and (ot.startswith("OPEN_AUCTION") or ot == "OPEN_REJECTION_REVERSE"):
        return ("opening_type_mismatch",
                "T-636 opening-type mismatch: %s %s entry %s — the producer reads a drive while the canonical opening type "
                "is %s (phase %s); no initiating drive entry on an auction / rejection-reverse open" % (cls, d, entry, ot, phase))
    if on_all and cls == "OPENING_ORR":
        return None
    if not on_all and not ot.startswith("OPEN_AUCTION"):
        return None
    hls = [x for x in (_hl(b) for b in (bars or [])) if x]
    try:
        e = float(entry)
    except (TypeError, ValueError):
        return None
    if not hls or e <= 0:
        return None
    orh, orl = max(h for h, _ in hls), min(l for _, l in hls)
    mid = (orh + orl) / 2.0
    if (d == "LONG" and e > mid) or (d == "SHORT" and e < mid):
        return ("opening_half_range",
                "T-628/T-636 opening half-range: %s %s entry %.2f is in the %s half of the opening range %.2f–%.2f (mid %.2f) "
                "on %s phase %s — no chase; the entry belongs at the test"
                % (cls, d, e, "upper" if d == "LONG" else "lower", orl, orh, mid, ot, phase))
    return None
