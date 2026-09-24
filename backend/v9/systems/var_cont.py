"""VAR_CONT_V1 — with-extension pullback-continuation, one contract (T-458א, 24.09).

Michael 24.09: "רוב הימים בשנה הם וריאציה … אתה ביום צריך להגיע גם אם זה במספר עסקאות למקסום כדי לנצל
פולבאק" — the second engine of a Variation day: after the range extension (or a confirmed opening
drive), re-enter WITH the day's direction on the first strong bar after a pullback.

This is the model rule ``CONT_1S`` of scripts/variation_playbook_test.py ported 1:1 (same features
as scripts/review_lib.py::features), measured 24.09 on 60 sessions (one contract, first touch on
5-min bars, $1.30/side):
    CONT_1S  N=113  T1 1.5R Σ+$156 42%  ·  Variation n=78 Σ+$459 45%  ·  Normal/Neutral lose
    first CONT of a Variation day n=26 Σ+$642 62% · second +$12 · third+ Σ−$272 · 22:xx entries −$183 21%
    playbook drive→T1 + CONT (≤2/day, <22:00) Σ+$738 vs drive-only +$442 (60 sessions)
⇒ the two limits are part of the rule: at most VAR_CONT_MAX_PER_DAY (2) LIVE entries per session and
no new entry from VAR_CONT_CUTOFF_IL (22:00 Asia/Jerusalem).

Rule, all causal on CLOSED RTH bars (bars[0] = 16:30 IL bar; entry = close of the last closed bar i):
  * i ≥ 12 (IB locked: ib_h/ib_l = extremes of bars[:12])
  * trigger bar: close in the extreme 30% of its range in direction d, range ≥ 0.8×ATR
  * pullback_before: ≥2 of the 3 bars before i closed AGAINST d
  * one_sided: (close beyond the IB edge in d AND the other IB edge was never exceeded) OR
               (the day's opening drive is d AND (close−open)/ATR ≥ 0.5 in d AND the other edge never exceeded)
  * stop = extreme of the 4 bars before i ± 1 tick, capped at 1.5×ATR, risk ≥ 1 pt; t1 = T1_BANK_R × risk
ATR = 14-bar causal ATR (bars 12–13 use the ATR of the bars available so far — the model used a
session ATR there; the only deviation from the model, on two bars).

Flag VAR_CONT_V1: 0 (default, byte-identical) · shadow (setup carries metadata.shadow_only) · 1 (live).
Gateway gates still apply (dalton_intent kind PULLBACK via entry_kind_map, ELQ, R:R, slot).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
IL = ZoneInfo("Asia/Jerusalem")
TICK = 0.25


def enabled() -> bool:
    return os.getenv("VAR_CONT_V1", "0").strip().lower() in ("1", "true", "yes", "shadow")


def is_shadow() -> bool:
    return os.getenv("VAR_CONT_V1", "0").strip().lower() == "shadow"


def max_per_day() -> int:
    try:
        return int(os.getenv("VAR_CONT_MAX_PER_DAY", "2") or 2)
    except (TypeError, ValueError):
        return 2


def cutoff_il() -> str:
    return (os.getenv("VAR_CONT_CUTOFF_IL", "22:00") or "22:00").strip()


def t1_r() -> float:
    try:
        return float(os.getenv("T1_BANK_R", "1.5") or 1.5)
    except (TypeError, ValueError):
        return 1.5


# ── pure helpers (mirror scripts/oracle_engine.compute_atr + review_lib.features) ──
def _f(bar: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        v = bar.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


def _norm(bars: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for b in bars:
        o, h, l, c = _f(b, "o", "open"), _f(b, "h", "high"), _f(b, "l", "low"), _f(b, "c", "close")
        if None in (o, h, l, c):
            continue
        out.append({"ts": b.get("ts"), "o": o, "h": h, "l": l, "c": c, "v": _f(b, "v", "vol", "volume") or 0.0})
    return out


def atr_at(bs: List[Dict[str, Any]], i: int, period: int = 14) -> Optional[float]:
    """Causal ATR at bar i over bars [i-period+1 .. i] (true range uses the previous close).
    With fewer than `period` prior bars, uses what is available (i ≥ 1)."""
    if i < 1:
        return None
    p = min(period, i)
    trs = []
    for k in range(i - p + 1, i + 1):
        trs.append(max(bs[k]["h"] - bs[k]["l"], abs(bs[k]["h"] - bs[k - 1]["c"]), abs(bs[k]["l"] - bs[k - 1]["c"])))
    return (sum(trs) / len(trs)) if trs else None


def drive_dir_of(bs: List[Dict[str, Any]]) -> Optional[str]:
    """The day's opening-drive direction as the model saw it: bar-2 drive, else lite, else late (bars 3..5)."""
    if len(bs) < 3:
        return None
    b0, b1, b2 = bs[0], bs[1], bs[2]
    or_hi, or_lo = max(b0["h"], b1["h"]), min(b0["l"], b1["l"])
    down = b2["c"] < or_lo and b1["c"] <= b0["c"] and b2["c"] < b2["o"]
    up = b2["c"] > or_hi and b1["c"] >= b0["c"] and b2["c"] > b2["o"]
    if down or up:
        stop = (max(b0["h"], b1["h"], b2["h"]) + TICK) if down else (min(b0["l"], b1["l"], b2["l"]) - TICK)
        if abs(stop - b2["c"]) <= 25:
            return "SHORT" if down else "LONG"
    down = b2["c"] < or_lo and b2["c"] < b2["o"]
    up = b2["c"] > or_hi and b2["c"] > b2["o"]
    if down or up:
        stop = (max(b0["h"], b1["h"], b2["h"]) + TICK) if down else (min(b0["l"], b1["l"], b2["l"]) - TICK)
        if abs(stop - b2["c"]) <= 25:
            return "SHORT" if down else "LONG"
    if len(bs) >= 6:
        or_hi3 = max(x["h"] for x in bs[:3]); or_lo3 = min(x["l"] for x in bs[:3]); mid = (or_hi3 + or_lo3) / 2
        for k in range(3, 6):
            b, prev = bs[k], bs[k - 1]
            down = b["c"] < or_lo3 and prev["c"] < mid and b["c"] < b["o"]
            up = b["c"] > or_hi3 and prev["c"] > mid and b["c"] > b["o"]
            if down or up:
                stop = (max(x["h"] for x in bs[:k + 1]) + TICK) if down else (min(x["l"] for x in bs[:k + 1]) - TICK)
                if abs(stop - b["c"]) > 25:
                    return None
                return "SHORT" if down else "LONG"
    return None


def _il_hhmm(ts) -> Optional[str]:
    if ts is None:
        return None
    try:
        if isinstance(ts, str):
            d = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        else:
            d = ts
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(IL).strftime("%H:%M")
    except Exception:
        return None


def detect(bars: List[Dict[str, Any]], *, drive_dir: Optional[str] = None,
           cutoff: Optional[str] = None, t1_mult: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Evaluate the LAST closed RTH bar as a VAR_CONT trigger. Returns the trigger dict or None."""
    bs = _norm(bars)
    i = len(bs) - 1
    if i < 12:
        return None
    b = bs[i]
    hhmm = _il_hhmm(b.get("ts"))
    cut = cutoff or cutoff_il()
    if hhmm is not None and hhmm >= cut:
        return None
    atr = atr_at(bs, i)
    if not atr or atr <= 0:
        return None
    ib_h = max(x["h"] for x in bs[:12]); ib_l = min(x["l"] for x in bs[:12])
    ses_hi = max(x["h"] for x in bs[:i + 1]); ses_lo = min(x["l"] for x in bs[:i + 1])
    rng = b["h"] - b["l"]
    cp = ((b["c"] - b["l"]) / rng) if rng > 0 else 0.5
    if rng < 0.8 * atr:
        return None
    dd = drive_dir if drive_dir is not None else drive_dir_of(bs)
    mo = (b["c"] - bs[0]["o"]) / atr
    day_dir = "SHORT" if mo <= -0.5 else "LONG" if mo >= 0.5 else None
    seq3 = bs[max(0, i - 4):i][-3:]
    seq4 = bs[max(0, i - 4):i]
    mult = t1_mult if t1_mult is not None else t1_r()
    for short in (True, False):
        d = "SHORT" if short else "LONG"
        trigger_ok = (cp <= 0.3) if short else (cp >= 0.7)
        if not trigger_ok:
            continue
        pull = sum(1 for x in seq3 if ((x["c"] > x["o"]) if short else (x["c"] < x["o"])))
        if pull < 2:
            continue
        ext_in_dir = (b["c"] < ib_l) if short else (b["c"] > ib_h)
        other_ext = (ses_hi > ib_h + TICK) if short else (ses_lo < ib_l - TICK)
        via = None
        if ext_in_dir and not other_ext:
            via = "ib_extension"
        elif dd == d and day_dir == d and not other_ext:
            via = "opening_drive"
        if via is None:
            continue
        stop = (max(x["h"] for x in seq4) + TICK) if short else (min(x["l"] for x in seq4) - TICK)
        risk = abs(stop - b["c"])
        if risk > 1.5 * atr:
            stop = b["c"] + 1.5 * atr if short else b["c"] - 1.5 * atr
            risk = 1.5 * atr
        if risk < 1.0:
            continue
        sign = -1.0 if short else 1.0
        t1 = b["c"] + sign * mult * risk
        return {
            "type": "VAR_CONT", "direction": d, "entry": round(b["c"], 2), "stop": round(stop, 2),
            "t1": round(t1, 2), "risk": round(risk, 2), "atr": round(atr, 2), "via": via,
            "ib_h": ib_h, "ib_l": ib_l, "ext": "down" if b["c"] < ib_l else "up" if b["c"] > ib_h else "none",
            "drive_dir": dd, "cp": round(cp, 3), "range_atr": round(rng / atr, 2), "bar_il": hhmm,
            "bar_ts": b.get("ts"), "i": i,
        }
    return None


def build_setup(trigger: Dict[str, Any], shadow: bool) -> Dict[str, Any]:
    """Gateway-routable setup. The stop IS the structural anchor (4-bar extreme + tick, capped) —
    metadata.stop_is_structural keeps StopResolver / STOP_FLOOR_IB / STEP_SCALED_LADDER off it
    (T-328 §4). The ladder is monotonic m×risk (t1 = T1_BANK_R, t2 = 2.5R, t3 = 4R) so T3_REQUIRED
    never rejects it; with one contract only t1 is placed."""
    entry = float(trigger["entry"]); stop = float(trigger["stop"])
    risk = abs(entry - stop); sign = 1.0 if trigger["direction"] == "LONG" else -1.0
    t1 = float(trigger["t1"])
    t2 = round(entry + sign * max(2.5 * risk, abs(t1 - entry) + 0.5 * risk), 2)
    t3 = round(entry + sign * max(4.0 * risk, abs(t2 - entry) + 0.5 * risk), 2)
    return {
        "firing_system": 2,
        "pattern": "VAR_CONT",
        "classification": "VAR_CONT",
        "direction": trigger["direction"],
        "entry_price": round(entry, 2),
        "stop": round(stop, 2),
        "t1": round(t1, 2),
        "t2": t2,
        "t3": t3,
        "confidence": 0.6,
        "structural_anchor": round(stop, 2),
        "metadata": {
            "pattern": "VAR_CONT",
            "source": "var_cont_v1",
            "entry_kind": "PULLBACK",
            "via": trigger.get("via"),
            "ext": trigger.get("ext"),
            "drive_dir": trigger.get("drive_dir"),
            "atr": trigger.get("atr"),
            "risk": round(risk, 2),
            "bar_il": trigger.get("bar_il"),
            "stop_is_structural": True,
            "structural_anchor": round(stop, 2),
            "shadow_only": bool(shadow),
        },
    }
