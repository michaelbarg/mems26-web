# -*- coding: utf-8 -*-
"""NEXT_FIRE — "מה המחיר שצריך להגיע אליו כדי שהירי הקרוב יבוצע — ורק לייב".

Michael 01.10 (19:5x IL): "אני צריך שגם בפלאפון וגם בפרונט יהיה ברור לגמרי מה המחיר אליו
צריך להגיע כדי שיבוצע הירי הקרוב ביותר — ואני רוצה רק על לייב".

One assembly, consumed by three screens (desktop fire-queue strip, the 🌌 field's panel, the phone):
    GET /api/v9/tree/next_fire   and   mobile/data["next_fire"]

What it is (and is not):
  * LIVE-ONLY: a producer whose setups carry metadata.shadow_only (ZLR_SHADOW_V1, CEILING_FLIP_TOUCH2_V1=
    shadow, TREND_STEP_ENTRY_V1=shadow, S2_DELTA_DBL_V1=shadow, FAILED_BREAK_*, VA_FADE, RE_ACCEPTANCE=shadow,
    S3) is never "the next live fire". `live_capability()` is the registry — the same env flags the
    producers read, in one place, so the screen cannot promise a fire the gateway would route to shadow.
  * THE TREE DECIDES FIRST: a candidate is "allowed" only if DECISION_TREE_V3's plan for the current
    situation says TAKE for its (direction, entry-kind). A refused direction is reported with the
    tree's own Hebrew reason (plan_he) — "לונג: נגד ההטיה" is an answer, not a blank.
  * THE LEVEL IS THE PRODUCER'S OWN TRIGGER GEOMETRY, never a forecast:
      CEILING_FLIP_SHORT/LONG  — the edge a double touch must fail at (VAH · session high · IB high / mirror),
                                 then a close below/above the neckline (ceiling_floor_state.py anatomy)
      DALTON_EDGE_LONG/SHORT   — a new 12-bar extreme (lowest low / highest high of the last N bars) with a
                                 rejection close in the far 40% of the bar on volume >= 2x SMA20 (dalton_edge.py)
      OPENING_EXTREME_REJECT   — the opening extreme (session low / high) while phase A/B
      S2 necklines             — DOUBLE_*/H&S: close beyond the neckline +-1 tick (the inspector's live numbers)
      everything else          — no price level by construction (bar-shape / CCI conditions): the line says
                                 what the market must print, from the pattern inspector's own "Awaiting".
  * NOTHING HERE PREDICTS. Every line is a condition the market has to satisfy; the distance is |level - price|.
    Reaching the level is necessary, not sufficient — the safety gates after the trigger are listed too.

Pure assembly: `assemble()` is a pure function of (context, plan, bars, inspector snapshot, flags) so it is
unit-testable without the app; `build_next_fire(app)` only gathers those inputs.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

TICK = 0.25
DALTON_LOOKBACK_N = 12
ON = ("1", "true", "yes", "live")

KIND_HEB = {"WITH_DRIVE": "עם-הדרייב", "REVERSAL": "היפוך", "EDGE_FADE": "דהיית-קצה", "PULLBACK": "פולבק",
            "BREAK": "פריצה", "VALUE_RETURN": "חזרה-לערך"}
LEVEL_HEB = {"VAH": "VAH", "VAL": "VAL", "POC": "POC", "IB_HIGH": "IB-high", "IB_LOW": "IB-low",
             "SESSION_HIGH": "שיא-הסשן", "SESSION_LOW": "שפל-הסשן", "LOW_12": "שפל-12-ברים", "HIGH_12": "שיא-12-ברים",
             "NECKLINE": "צוואר"}
GATES_AFTER_HE = ["בר-אישור בכיוון", "R:R ≥ 0.65 מול T1 מבני", "לא בחלון-חדשות", "סלוט פנוי", "חשבון ללא פוזיציה-שלא-בספרים"]


def _flag(key: str) -> str:
    return (os.getenv(key, "0") or "0").strip().lower()


def live_capability(pattern_id: str) -> Tuple[bool, str]:
    """(live-capable?, which switch decides). Mirrors the producers' own flags — one registry."""
    p = (pattern_id or "").upper()
    if p == "ZLR":
        return (_flag("ZLR_SHADOW_V1") not in ("1", "true", "yes"), "ZLR_SHADOW_V1")
    if p.startswith("CONFLUENCE"):
        return (_flag("CONFLUENCE_RI_ZLR_LIVE") in ON, "CONFLUENCE_RI_ZLR_LIVE")
    if p.startswith("CEILING_FLIP_TOUCH2") or p.startswith("CEILING_TOUCH2"):
        return (_flag("CEILING_FLIP_TOUCH2_V1") in ON, "CEILING_FLIP_TOUCH2_V1")
    if p.startswith("CEILING_FLIP"):
        return (_flag("CEILING_FLIP_SHORT_V1") in ON, "CEILING_FLIP_SHORT_V1")
    if p.startswith("DALTON_EDGE"):
        return (_flag("DALTON_EDGE_V1") in ON, "DALTON_EDGE_V1")
    if p.startswith("OPENING_"):
        return (_flag("OPENING_ENTRY_V1") in ON, "OPENING_ENTRY_V1")
    if p.startswith("VA_FADE"):
        return (False, "va_fade.py: shadow_only by code")
    if p.startswith("FAILED_BREAK"):
        return (False, "failed_break.py: shadow_only by code")
    if p in ("FAILED_RE_IB", "RE_ACCEPTANCE") or p.startswith("RE_ACCEPT"):
        return (_flag("RE_ACCEPTANCE_V1") in ON, "RE_ACCEPTANCE_V1")
    if "DELTA_DBL" in p:
        return (_flag("S2_DELTA_DBL_V1") in ON, "S2_DELTA_DBL_V1")
    if p.startswith("TREND_STEP"):
        return (_flag("TREND_STEP_ENTRY_V1") in ON, "TREND_STEP_ENTRY_V1")
    if p.startswith("VAR_CONT"):
        return (_flag("VAR_CONT_V1") in ON, "VAR_CONT_V1")
    if p.startswith("FOOTPRINT"):
        return (False, "S3: calculate_size shim (cannot fire)")
    return (True, "live producer")


def kind_of(pattern_id: str) -> str:
    """Entry kind via config/dalton_playbook.yaml entry_kind_map (the gateway's own map); BREAK default."""
    try:
        from backend.v9.services.dalton_playbook import entry_kind_for, load_config
        m = load_config().get("entry_kind_map", {}) or {}
        p = (pattern_id or "").upper()
        if p in m:
            return str(m[p])
        base = re.sub(r"_(LONG|SHORT)$", "", p)
        if base in m:
            return str(m[base])
        # longest prefix (CEILING_FLIP_TOUCH2 before CEILING_FLIP)
        best = ""
        for k in m:
            if p.startswith(str(k).upper()) and len(k) > len(best):
                best = str(k)
        return str(m[best]) if best else entry_kind_for(p)
    except Exception:
        return "BREAK"


def _direction_of(pattern_id: str) -> Optional[str]:
    p = (pattern_id or "").upper()
    if p.endswith("_LONG") or "_LONG_" in p:
        return "LONG"
    if p.endswith("_SHORT") or "_SHORT_" in p:
        return "SHORT"
    return None


def _f(v: Any) -> Optional[float]:
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def _nearest(levels: List[Tuple[str, Optional[float]]], price: float, side: str) -> Optional[Tuple[str, float]]:
    """The nearest usable edge on `side` of the price ("above"/"below"); an edge the price sits on counts."""
    best: Optional[Tuple[str, float]] = None
    for name, lv in levels:
        if lv is None:
            continue
        ok = (lv >= price - 2 * TICK) if side == "above" else (lv <= price + 2 * TICK)
        if not ok:
            continue
        d = abs(lv - price)
        if best is None or d < abs(best[1] - price):
            best = (name, lv)
    return best


def _plan_leaf(plan: Dict[str, Any], direction: str, kind: str) -> Dict[str, Any]:
    return ((plan or {}).get(direction) or {}).get(kind) or {}


def assemble(*, ctx: Dict[str, Any], plan: Dict[str, Any], plan_he: Dict[str, str],
             bars: List[Dict[str, Any]], inspector: Dict[str, Any], flags: Optional[Dict[str, str]] = None,
             ts: str = "") -> Dict[str, Any]:
    """Pure: the next-fire picture from the inputs. `flags` overrides os.environ for tests."""
    if flags is not None:
        for k, v in flags.items():
            os.environ[k] = v
    price = _f(ctx.get("price"))
    va = ctx.get("va") or [None, None]
    ib = ctx.get("ib") or [None, None]
    sess = ctx.get("session") or [None, None]
    levels = {"VAH": _f(va[1]) if len(va) > 1 else None, "VAL": _f(va[0]) if va else None, "POC": _f(ctx.get("poc")),
              "IB_HIGH": _f(ib[1]) if len(ib) > 1 else None, "IB_LOW": _f(ib[0]) if ib else None,
              "SESSION_HIGH": _f(sess[1]) if len(sess) > 1 else None, "SESSION_LOW": _f(sess[0]) if sess else None}
    phase = str(ctx.get("phase") or "?")
    lows = [_f(b.get("l", b.get("low"))) for b in bars[-DALTON_LOOKBACK_N:]]
    highs = [_f(b.get("h", b.get("high"))) for b in bars[-DALTON_LOOKBACK_N:]]
    lo12 = min([x for x in lows if x is not None], default=None)
    hi12 = max([x for x in highs if x is not None], default=None)

    allowed = {d: any((v or {}).get("leaf") == "TAKE" for v in (plan.get(d) or {}).values()) for d in ("LONG", "SHORT")}
    shadow_dir = {d: any((v or {}).get("leaf") == "SHADOW" for v in (plan.get(d) or {}).values()) for d in ("LONG", "SHORT")}

    cands: List[Dict[str, Any]] = []

    def add(pid: str, direction: str, level: Optional[float], level_name: Optional[str], how_he: str,
            source: str, awaiting: Optional[str] = None, kind: Optional[str] = None) -> None:
        live, why = live_capability(pid)
        k = kind or kind_of(pid)
        leaf = _plan_leaf(plan, direction, k)
        take = leaf.get("leaf") == "TAKE"
        dist = round(abs(level - price), 2) if (level is not None and price is not None) else None
        side = None
        if level is not None and price is not None:
            side = "above" if level > price + TICK / 2 else ("below" if level < price - TICK / 2 else "at")
        cands.append({
            "pattern": pid, "direction": direction, "kind": k, "kind_he": KIND_HEB.get(k, k),
            "live": live, "live_switch": why,
            "leaf": leaf.get("leaf"), "leaf_id": leaf.get("id"), "leaf_note": leaf.get("note"), "allowed": bool(take),
            "level": level, "level_name": level_name, "level_he": LEVEL_HEB.get(level_name or "", level_name),
            "dist": dist, "side": side, "how_he": how_he, "awaiting": awaiting, "source": source,
        })

    # ── CEILING_FLIP (live when CEILING_FLIP_SHORT_V1 on) — the edge a double touch must fail at ──
    e_hi = _nearest([("VAH", levels["VAH"]), ("SESSION_HIGH", levels["SESSION_HIGH"]), ("IB_HIGH", levels["IB_HIGH"])],
                    price, "above") if price is not None else None
    e_lo = _nearest([("VAL", levels["VAL"]), ("SESSION_LOW", levels["SESSION_LOW"]), ("IB_LOW", levels["IB_LOW"])],
                    price, "below") if price is not None else None
    if e_hi:
        add("CEILING_FLIP_SHORT", "SHORT", e_hi[1], e_hi[0],
            f"נגיעה כפולה ב-{LEVEL_HEB[e_hi[0]]} {e_hi[1]:.2f} (|P2−P1| ≤ 0.25×ATR, בלי סגירה מעל P1) ואז סגירה מתחת לצוואר (שפל-הפער)", "ceiling_floor_state")
    if e_lo:
        add("CEILING_FLIP_LONG", "LONG", e_lo[1], e_lo[0],
            f"נגיעה כפולה ב-{LEVEL_HEB[e_lo[0]]} {e_lo[1]:.2f} (|P2−P1| ≤ 0.25×ATR, בלי סגירה מתחת P1) ואז סגירה מעל הצוואר (שיא-הפער)", "ceiling_floor_state")

    # ── DALTON_EDGE — a NEW 12-bar extreme with a rejection close on 2x volume ──
    if lo12 is not None and price is not None:
        lv = min(lo12, price)
        add("DALTON_EDGE_LONG", "LONG", lv, "LOW_12",
            f"בר שמדפיס שפל חדש של 12 ברים (≤ {lo12:.2f}) וסוגר ב-40% העליונים שלו, טווח ≥ 2 נק׳, נפח ≥ 2×SMA20", "dalton_edge")
    if hi12 is not None and price is not None:
        lv = max(hi12, price)
        add("DALTON_EDGE_SHORT", "SHORT", lv, "HIGH_12",
            f"בר שמדפיס שיא חדש של 12 ברים (≥ {hi12:.2f}) וסוגר ב-40% התחתונים שלו, טווח ≥ 2 נק׳, נפח ≥ 2×SMA20", "dalton_edge")

    # ── opening engine — phase A/B only ──
    if phase in ("A", "B"):
        if levels["SESSION_LOW"] is not None:
            add("OPENING_EXTREME_REJECT", "LONG", levels["SESSION_LOW"], "SESSION_LOW",
                f"דחייה של שפל-הפתיחה {levels['SESSION_LOW']:.2f} — בר שנוגע ונסגר מעליו", "opening_engine")
        if levels["SESSION_HIGH"] is not None:
            add("OPENING_EXTREME_REJECT", "SHORT", levels["SESSION_HIGH"], "SESSION_HIGH",
                f"דחייה של שיא-הפתיחה {levels['SESSION_HIGH']:.2f} — בר שנוגע ונסגר מתחתיו", "opening_engine")
        for d in ("LONG", "SHORT"):
            add("OPENING_DRIVE", d, None, None, "אין מחיר — דרייב: ברי-פתיחה רצופים בכיוון אחד (מנוע-הפתיחה מאשר)", "opening_engine")

    # ── the pattern inspector (S2 five-min · S4 Woodies) — live numbers of what each pattern awaits ──
    s4_veto: Optional[str] = None
    for sysb in (inspector or {}).get("systems", []) or []:
        sid = sysb.get("id")
        if sid not in ("five_min", "woodies"):
            continue
        # S4 fires WITH the Woodies trend colour (BLUE → LONG, RED → SHORT; GRAY = A1 veto)
        s4_dir: Optional[str] = None
        if sid == "woodies":
            for li in sysb.get("live_inputs") or []:
                if li.get("field") == "trend_state":
                    s4_dir = {"BLUE": "LONG", "RED": "SHORT"}.get(str(li.get("value") or "").upper())
        for p in sysb.get("patterns") or []:
            pid = str(p.get("id") or "")
            st = str(p.get("status") or "")
            reason = str(p.get("reason") or "")
            if sid == "woodies":
                if st == "blocked" and "trend_state=GRAY" in reason:
                    s4_veto = reason[:90]
                    continue
                if st not in ("armed", "forming", "ready") or not s4_dir:
                    continue
                add(pid, s4_dir, None, None, f"אין מחיר — תנאי CCI (עם הטרנד {s4_dir}): {reason[:80]}", "inspector:S4",
                    awaiting=reason[:90])
                continue
            # five_min
            if st not in ("armed", "forming", "ready"):
                continue
            d = _direction_of(pid)
            if not d:
                continue
            aw = re.match(r"^Awaiting:\s*([^—]+?)\s*(?:—\s*(.*))?$", reason)
            key = aw.group(1).strip() if aw else None
            detail = (aw.group(2) or "").strip() if aw else reason
            level, lname, how = None, None, None
            m = re.search(r"neckline=(-?[0-9.]+)", detail)
            if key == "neckline_breakout" and m:
                nl = float(m.group(1))
                level = nl + TICK if d == "LONG" else nl - TICK
                lname = "NECKLINE"
                how = f"סגירת בר-5-דק׳ {'מעל' if d == 'LONG' else 'מתחת'} לצוואר {nl:.2f} ± טיק"
            else:
                how = f"אין מחיר — תנאי-בר: {key or '?'} ({detail[:70]})"
            add(pid, d, level, lname, how, "inspector:S2", awaiting=f"{key or '?'} — {detail[:80]}")

    def rank(c: Dict[str, Any]) -> Tuple[int, int, float]:
        return (0 if (c["live"] and c["allowed"]) else 1, 0 if c["dist"] is not None else 1, c["dist"] if c["dist"] is not None else 9e9)
    cands.sort(key=rank)
    live_allowed = [c for c in cands if c["live"] and c["allowed"]]
    nearest = next((c for c in live_allowed if c["dist"] is not None), None)

    # the Hebrew headline — the one line Michael asked for
    parts: List[str] = []
    for d, heb in (("LONG", "לונג"), ("SHORT", "שורט")):
        best = next((c for c in live_allowed if c["direction"] == d and c["dist"] is not None), None)
        if best:
            arrow = "מעל" if best["side"] == "above" else ("מתחת" if best["side"] == "below" else "על")
            parts.append(f"{heb}: {best['pattern']} ב-{best['level']:.2f} ({best['level_he']}) — {best['dist']:.2f} נק׳ {arrow} למחיר")
        elif allowed[d]:
            nolevel = next((c for c in live_allowed if c["direction"] == d), None)
            parts.append(f"{heb}: אין מחיר-מטרה — {nolevel['pattern'] + ': ' + nolevel['how_he'] if nolevel else 'העץ מרשה, אין מפיק-לייב עם טריגר-מחיר עכשיו'}")
        else:
            why = (plan_he or {}).get(d) or "העץ מסרב"
            parts.append(f"{heb}: העץ מסרב — {why}" + (" (צל בלבד)" if shadow_dir[d] else ""))
    headline = " · ".join(parts)

    return {
        "ts": ts, "price": price, "phase": phase, "levels": levels, "lo12": lo12, "hi12": hi12,
        "allowed": allowed, "why_he": {d: (plan_he or {}).get(d) for d in ("LONG", "SHORT")},
        "nearest": nearest, "candidates": cands[:14], "n_live_allowed": len(live_allowed),
        "s4_veto": s4_veto, "gates_after_he": GATES_AFTER_HE, "headline_he": headline,
        "note_he": "הגעה למחיר היא תנאי הכרחי, לא מספיק: אחרי הטריגר עוברים את השערים (בר-אישור · R:R · חדשות · סלוט · חשבון). אין כאן תחזית — רק מה שהשוק צריך להדפיס.",
    }


def _bars_from_db(n: int = DALTON_LOOKBACK_N + 1) -> List[Dict[str, Any]]:
    try:
        from backend.v9.db.read import read_all
        rows = read_all(
            "select ts, high h, low l, close c from v9_bars_5min_woodies where symbol='MES' order by ts desc limit :n",
            {"n": n})
        return [dict(ts=r["ts"], h=float(r["h"]), l=float(r["l"]), c=float(r["c"])) for r in reversed(list(rows))]
    except Exception as e:  # honest-missing: no bars → no DALTON levels, nothing invented
        logger.debug("[next_fire] bars unavailable: %s", e)
        return []


def build_next_fire(app, state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Gather the inputs from the running app and assemble. Never raises — returns {error} instead.
    `state` = an already-built tree state (mobile/data has one) to avoid walking the tree twice."""
    import time
    try:
        from backend.v9.api.v9.tree_routes import build_state
        st = state if isinstance(state, dict) and state.get("plan") else build_state(app, recent_n=0)
        if st.get("error"):
            return {"error": st["error"], "ts": time.strftime("%H:%M:%S")}
        inspector: Dict[str, Any] = {}
        try:
            from backend.v9.systems.build_status.aggregator import BuildStatusAggregator
            inspector = BuildStatusAggregator(
                five_min_system=getattr(app.state, "five_min_system", None),
                woodies_system=getattr(app.state, "woodies_system", None),
                day_type_machine=getattr(app.state, "day_type_machine", None),
                footprint_system=getattr(app.state, "footprint_system", None),
            ).get_status(systems=["five_min", "woodies"]).model_dump()
        except Exception as e:
            inspector = {"error": str(e)[:80]}
        out = assemble(ctx=st.get("context") or {}, plan=st.get("plan") or {}, plan_he=st.get("plan_he") or {},
                       bars=_bars_from_db(), inspector=inspector, ts=time.strftime("%H:%M:%S"))
        out["mode"] = st.get("mode")
        out["where_he"] = st.get("where_he")
        if inspector.get("error"):
            out["inspector_error"] = inspector["error"]
        return out
    except Exception as e:
        logger.warning("[next_fire] failed: %s", e)
        return {"error": str(e)[:120], "ts": time.strftime("%H:%M:%S")}
