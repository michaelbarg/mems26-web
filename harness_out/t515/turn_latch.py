#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-515 v2 candidate (29.09, harness-only): the turn with a LATCH. v1 re-derives tol/pull_min from the CURRENT ATR, so a
double bottom confirmed at 18:00 (ATR 9 ⇒ tol 2.25 covers 7726.0/7727.75/7728.0) vanishes at 19:00 when ATR falls to 6
(tol 1.5) — 28.09 reads "down" at 19:00-19:20 inside a 7726-7775 balance and "none" from 21:25. The latch: a side stays
confirmed once it was confirmed at ANY earlier cut, as long as its extreme still stands (a new extreme resets it)."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from backend.v9.services.turn_state import _side, atr_of  # noqa: E402


def _latched(bars, top, min_sep=2):
    if len(bars) < 3:
        return None
    hs = [float(b["h"] if top else b["l"]) for b in bars]
    ext = max(hs) if top else min(hs)
    i_ext = hs.index(ext)
    for k in range(len(bars), i_ext + 1, -1):          # newest cut first; every cut that still contains the extreme
        cut = bars[:k]
        if len(cut) < 3:
            break
        atr = atr_of(cut) or 5.0
        s = _side(cut, top, max(1.0, 0.25 * atr), max(3.0, 0.75 * atr), min_sep)
        if s and s["level"] == ext:
            return s
    return None


def detect_turn_latched(bars):
    bars = [b for b in (bars or []) if b]
    if len(bars) < 3:
        return {"turn": "none"}
    atr = atr_of(bars) or 5.0
    base = {"tol": round(max(1.0, 0.25 * atr), 2)}
    dn, up = _latched(bars, True), _latched(bars, False)
    if dn and up:
        return dict(base, turn="range", top=dn["level"], bottom=up["level"])
    if dn:
        return dict(base, turn="down", level=dn["level"], top=dn["level"])
    if up:
        return dict(base, turn="up", level=up["level"], bottom=up["level"])
    return dict(base, turn="none")
