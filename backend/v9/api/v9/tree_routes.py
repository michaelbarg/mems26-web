"""tree_routes.py — GET /api/v9/tree/state: where the decision tree (DECISION_TREE_V3) is RIGHT NOW and
what it would admit next (Michael 25.09 13:40: "שאראה אותו בחי בפלאפון ובדסקטופ — הרכיב שבאותו הרגע
המערכת נמצאת בו, ומה הוא מתכנן").

Read-only, display-only, never on the trading path. The context is assembled from the SAME live sources
the gateway reads (the running app's day-type machine, get_live_day_type, the gateway's own cross-context
snapshot / the Sierra TPO export, the IL clock) and the tree is walked once per direction × entry kind with
the last price as the location — that is "the plan": what the tree takes, shadows or refuses in this
circumstance. Recent walks come from the gateway's decision feed (each decision carries `tree_v3`).
"""
from __future__ import annotations

import collections
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v9/tree", tags=["v9-tree"])
_EXP = os.path.expanduser("~/SierraChart_Data/v9_export")
KINDS = ("WITH_DRIVE", "REVERSAL", "EDGE_FADE", "PULLBACK", "BREAK", "VALUE_RETURN")
KIND_HEB = {"WITH_DRIVE": "עם-הדרייב", "REVERSAL": "היפוך", "EDGE_FADE": "דהיית-קצה", "PULLBACK": "פולבק",
            "BREAK": "פריצה", "VALUE_RETURN": "חזרה-לערך"}
ZONE_HEB = {"above_value": "מעל הערך", "near_vah": "על ה-VAH", "mid_value": "בתוך הערך", "near_val": "על ה-VAL",
            "below_value": "מתחת לערך", "unknown": "אין ערך עדיין"}
DT_HEB = {"Trend_Normal": "מגמה", "Trend_DD": "מגמה-כפולה", "Variation": "וריאציה", "Normal_Variation": "וריאציה",
          "Normal": "נורמלי", "Neutral_Center": "נייטרלי-מרכז", "Neutral_Extreme": "נייטרלי-קיצון", "Nontrend": "ללא-מגמה",
          "Nonconviction": "ללא-שכנוע", "FORMING": "מתגבש", "": "מתגבש"}
OT_HEB = {"OPEN_DRIVE": "דרייב", "OPEN_TEST_DRIVE": "טסט-דרייב", "OPEN_REJECTION_REVERSE": "דחייה-היפוך",
          "OPEN_AUCTION_IN": "אוקציה בטווח", "OPEN_AUCTION_OUT": "אוקציה מחוץ לטווח", "UNKNOWN": "טרם סווגה"}
STRUCT_HEB = {"forming": "IB מתגבש", "none": "בלי הרחבה", "up": "הרחבה למעלה", "down": "הרחבה למטה", "two_sided": "הרחבה לשני הצדדים", "unknown": "?"}


def _price() -> Optional[float]:
    try:
        lp = json.loads(open(f"{_EXP}/live_price.json").read())
        return round((float(lp["bid"]) + float(lp["ask"])) / 2, 2)
    except Exception:
        return None


def _context(request) -> Dict[str, Any]:
    """The situation as the gateway would see it for a candidate routed right now."""
    from backend.v9.services import decision_tree as dt3
    from backend.v9.services.dalton_playbook import _resolve_phase, load_config as _pb_cfg
    from backend.v9.services.market_clock import now_et
    from zoneinfo import ZoneInfo
    il = now_et().astimezone(ZoneInfo("Asia/Jerusalem"))
    hhmm = f"{il.hour:02d}:{il.minute:02d}"
    phase = _resolve_phase(hhmm, _pb_cfg())
    app = request.app
    gw = getattr(app.state, "trading_gateway", None)
    dtm = getattr(app.state, "day_type_machine", None)
    # day type — the gateway's hysteresis-held label when it has one, else the live label
    day_type = ""
    try:
        from backend.v9.services.trade_context import get_live_day_type
        day_type = get_live_day_type() or ""
        hyst = getattr(gw, "_dp_hyst", None) if gw is not None else None
        if isinstance(hyst, dict) and hyst.get("label") and str(hyst["label"]).startswith("Trend") and not day_type.startswith("Trend"):
            day_type = hyst["label"]           # Trend→other needs 2 bars (Michael 09.09)
    except Exception:
        pass
    # opening type + direction: the locked value (T-314) else live classification
    ot, hint, ot_src = "UNKNOWN", None, "unknown"
    try:
        if dtm is not None and getattr(dtm, "_opening_type_locked", False):
            ot = str(getattr(dtm, "_opening_locked_val", "UNKNOWN") or "UNKNOWN"); ot_src = "locked"
            d = getattr(dtm, "_opening_locked_dir", None)
            hint = "LONG" if d in ("UP", "LONG") else "SHORT" if d in ("DOWN", "SHORT") else None
        else:
            from backend.v9.gateway.trading_gateway import _resolve_live_cls
            cls = _resolve_live_cls() or {}
            if isinstance(cls, dict) and cls.get("opening_type") and str(cls.get("opening_type")) not in ("UNKNOWN", "NA", "None", ""):
                ot = str(cls.get("opening_type") or "UNKNOWN"); ot_src = "live"
                d = cls.get("open_dir") or cls.get("dir_bias")
                hint = "LONG" if d in ("UP", "LONG") else "SHORT" if d in ("DOWN", "SHORT") else None
            else:
                # the gateway's Source 2: the v2 detector on the machine's opening-gate bars (bar 3+)
                ogb = list(getattr(dtm, "_opening_gate_bars", None) or []) if dtm is not None else []
                if len(ogb) >= 3:
                    from backend.v9.systems.day_type.opening_detector_v2 import detect_opening_type
                    r = detect_opening_type([{"o": b.get("o", 0), "h": b.get("h", 0), "l": b.get("l", 0), "c": b.get("c", 0), "v": b.get("v", 0)} for b in ogb[:6]], ogb[0].get("o", 0)) or {}
                    if r.get("opening_type"):
                        ot = str(r.get("opening_type") or "UNKNOWN"); ot_src = "v2"
                        d = r.get("direction")
                        hint = "LONG" if d in ("UP", "LONG") else "SHORT" if d in ("DOWN", "SHORT") else None
        if ot == "OPEN_REJECTION_REVERSE" and hint:
            hint = "SHORT" if hint == "LONG" else "LONG"      # the gateway's ORR sign fix (drive direction)
    except Exception:
        pass
    # TPO: the gateway's own snapshot first, the Sierra export as fallback
    tpo: Dict[str, Any] = {}
    try:
        if gw is not None:
            tpo = (gw._capture_cross_context() or {}).get("tpo_system") or {}
        if not tpo or not float(tpo.get("vah") or 0):
            from backend.v9.api.v9.tpo_routes import _load_sierra_tpo
            tpo = _load_sierra_tpo() or tpo
    except Exception:
        pass
    f = lambda k, alt=None: float(tpo.get(k) or (tpo.get(alt) if alt else 0) or 0)
    ibh, ibl, sh, sl, vah, val, poc = f("ib_high"), f("ib_low"), f("session_high", "rth_high"), f("session_low", "rth_low"), f("vah"), f("val"), f("poc")
    # IB-extension override of the hint — phase C+ only (T-451)
    ext_up = ext_dn = 0.0
    if hhmm >= "17:30" and ibh > 0 and ibl > 0:
        ext_up, ext_dn = max(0.0, sh - ibh), max(0.0, ibl - sl)
        if ext_up > ext_dn and ext_up > 0:
            hint = "LONG"
        elif ext_dn > ext_up and ext_dn > 0:
            hint = "SHORT"
    structure = dt3.structure_of(ibh, ibl, sh, sl, phase)
    price = _price()
    zone = "unknown"
    try:
        if price and vah > 0 and val > 0:
            from backend.v9.systems.location_gate import zone_of
            zone = zone_of(price, vah, val, (ibh - ibl) if (ibh > 0 and ibl > 0) else None)
    except Exception:
        pass
    # the day profile: yesterday's value (the location reference before today's VA forms), POC side, migration
    prior_zone, migr, pside, prev = "unknown", "unknown", "unknown", {}
    try:
        from backend.v9.api.v9.tpo_routes import _load_previous_cash_session
        prev = _load_previous_cash_session() or {}
        pvah, pval = float(prev.get("vah") or 0), float(prev.get("val") or 0)
        from backend.v9.systems.location_gate import zone_of as _zo, _tol as _tl
        ibw = (ibh - ibl) if (ibh > 0 and ibl > 0) else None
        if price and pvah > 0 and pval > 0:
            prior_zone = _zo(price, pvah, pval, ibw)
            migr = dt3.value_migration(vah, val, pvah, pval)
        if price and poc > 0:
            pside = dt3.poc_side(price, poc, 0.5 * _tl(ibw))
    except Exception:
        pass
    # the tree's own ORR convention: rel_bias vs the REVERSAL direction in phases A/B
    tree_hint = hint
    if ot == "OPEN_REJECTION_REVERSE" and phase in ("A", "B") and hint in ("LONG", "SHORT"):
        tree_hint = "SHORT" if hint == "LONG" else "LONG"
    return {
        "il": hhmm, "phase": phase, "opening_type": ot, "opening_source": ot_src, "day_type": day_type or "FORMING",
        "hint": hint, "tree_hint": tree_hint, "structure": structure, "price": price, "zone": zone,
        "ib": [ibl or None, ibh or None], "session": [sl or None, sh or None], "va": [val or None, vah or None], "poc": poc or None,
        "ext_up": round(ext_up, 2), "ext_dn": round(ext_dn, 2),
        "prior_zone": prior_zone, "value_migration": migr, "poc_side": pside,
        "prev_va": [float(prev.get("val") or 0) or None, float(prev.get("vah") or 0) or None, float(prev.get("poc") or 0) or None],
    }


def _mode() -> str:
    v = (os.getenv("DECISION_TREE_V3", "0") or "0").strip().lower()
    return "on" if v in ("1", "true", "yes") else "shadow" if v == "shadow" else "off"


class _AppRequest:
    """Minimal stand-in so build_state(app) can reuse the request-based helpers."""
    def __init__(self, app):
        self.app = app


def build_state(app, *, recent_n: int = 20) -> Dict[str, Any]:
    """The live tree state for any caller (the /state route, the phone snapshot payload)."""
    from backend.v9.services import decision_tree as dt3
    request = _AppRequest(app)
    t0 = time.time()
    out: Dict[str, Any] = {"mode": _mode(), "ts": time.strftime("%H:%M:%S")}
    try:
        ctx = _context(request)  # type: ignore[arg-type]
    except Exception as e:
        return {"error": f"context failed: {e}"[:160], **out}
    out["context"] = ctx
    # the plan: walk the tree for every direction × kind at the current price
    tree = dt3.load_tree()
    plan: Dict[str, Dict[str, Any]] = {"LONG": {}, "SHORT": {}}
    for direction in ("LONG", "SHORT"):
        rel = "with" if ctx["tree_hint"] == direction else ("against" if ctx["tree_hint"] in ("LONG", "SHORT") else "none")
        for kind in KINDS:
            vec = {"opening_type": ctx["opening_type"], "phase": ctx["phase"], "day_type": ctx["day_type"],
                   "structure": ctx["structure"], "pattern": "?", "kind": kind, "direction": direction, "rel_bias": rel,
                   "zone": ctx["zone"], "prior_zone": ctx.get("prior_zone"), "poc_side": ctx.get("poc_side"),
                   "value_migration": ctx.get("value_migration"), "edge": "none"}
            leaf, path = dt3.walk(tree, vec)
            plan[direction][kind] = {"leaf": leaf.get("leaf"), "id": leaf.get("id"), "note": leaf.get("note"),
                                     "path": "/".join(f"{f}={v}" for f, v in path)}
    out["plan"] = plan
    # one Hebrew sentence per direction
    def _sent(direction: str) -> str:
        rows = plan[direction]
        take = [KIND_HEB[k] for k in KINDS if rows[k]["leaf"] == "TAKE"]
        shadow = [KIND_HEB[k] for k in KINDS if rows[k]["leaf"] == "SHADOW"]
        if not take and not shadow:
            why = collections.Counter(rows[k]["id"] for k in KINDS).most_common(1)[0][0]
            return {"stand_down": "אין שורה לנסיבה הזו — stand-down", "bias": "נגד ההטיה של הסשן", "kind": "אף סוג-כניסה לא מותר בשורה", "location": "המחיר לא בקצה הערך (T-319b)"}.get(str(why), str(why))
        s = ("ייקח: " + " · ".join(take)) if take else ""
        if shadow:
            s += (" · " if s else "") + "צל: " + " · ".join(shadow)
        return s
    out["plan_he"] = {"LONG": _sent("LONG"), "SHORT": _sent("SHORT")}
    c = ctx
    out["where_he"] = (f"{OT_HEB.get(c['opening_type'], c['opening_type'])} · שלב {c['phase']} · {DT_HEB.get(c['day_type'], c['day_type'])}"
                       + (f" · {STRUCT_HEB.get(c['structure'], c['structure'])}" if c["phase"] in ("C", "D") else "")
                       + (f" · הטיה {('לונג' if c['hint'] == 'LONG' else 'שורט')}" if c["hint"] else " · בלי הטיה")
                       + (f" · המחיר {ZONE_HEB.get(c['zone'], c['zone'])}" if c["zone"] != "unknown" else (f" · מול הערך של אתמול: {ZONE_HEB.get(c.get('prior_zone'), c.get('prior_zone'))}" if c.get("prior_zone") not in (None, "unknown") else ""))
                       + ({"higher": " · ערך נודד למעלה", "lower": " · ערך נודד למטה", "overlap_high": " · ערך חופף-גבוה", "overlap_low": " · ערך חופף-נמוך", "inside": " · ערך בתוך של אתמול", "outside": " · ערך רחב מאתמול"}.get(c.get("value_migration"), "")))
    # recent walks from the gateway's decision feed
    recent: List[Dict[str, Any]] = []
    try:
        gw = getattr(app.state, "trading_gateway", None)
        from datetime import datetime
        from zoneinfo import ZoneInfo
        for d in reversed(list(getattr(gw, "decisions", []) or [])):
            tv = d.get("tree_v3")
            if not isinstance(tv, dict):
                continue
            try:
                il = datetime.fromisoformat(str(d.get("ts")).replace("Z", "+00:00")).astimezone(ZoneInfo("Asia/Jerusalem")).strftime("%H:%M:%S")
            except Exception:
                il = str(d.get("ts"))[11:19]
            recent.append({"il": il, "pattern": d.get("pattern"), "direction": d.get("direction"), "entry": d.get("entry"),
                           "leaf": tv.get("leaf"), "id": tv.get("id"), "path": tv.get("path"), "legacy": tv.get("legacy"),
                           "outcome": d.get("outcome"), "blocked_by": d.get("blocked_by") or d.get("live_blocked_by")})
            if len(recent) >= recent_n:
                break
    except Exception:
        pass
    out["recent"] = recent
    out["shadow_branches"] = [{"id": lf.get("id"), "note": lf.get("note"), "measured": lf.get("measured")}
                              for lf in dt3.leaves(tree) if lf.get("leaf") == "SHADOW"]
    out["latency_ms"] = round((time.time() - t0) * 1000, 1)
    return out


@router.get("/state")
async def tree_state(request: Request):
    return build_state(request.app)
