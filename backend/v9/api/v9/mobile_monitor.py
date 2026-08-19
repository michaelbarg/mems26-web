"""mobile_monitor — מוניטור-אייפון (Michael 2026-07-15, מוגש מהבקאנד).

GET /api/v9/mobile        → עמוד HTML קל (RTL, כהה, רענון-5ש', בלי גרפים)
GET /api/v9/mobile/data   → JSON מרוכז: פוזיציית-סיירה, עסקאות-פעילות + P&L,
                            יומי, סוג-יום, בריאות-פיד, ‏halt, התראות אחרונות.

קריאה-בלבד במתכוון: אין כאן שום פעולה (אין flatten/כיבוי) — צפייה מהנייד בלבד.
ללא-טוקן (כמו health): נתוני-תצוגה על רשת-בית/hotspot בלבד.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/api/v9/mobile", tags=["v9-mobile"])

_EXP = os.path.expanduser("~/SierraChart_Data/v9_export")


def _key_ok(request: Request) -> bool:
    """07-16 (Michael: "לינק מכל-מקום"): access gate for public exposure via a
    Cloudflare tunnel. When MOBILE_ACCESS_KEY is UNSET → open (LAN/ZeroTier mode,
    unchanged). When set → require ?key= / X-Mobile-Key header / mkey cookie ==
    the secret, so the tunnel URL is safe to share (the flatten button must NOT
    be reachable unauthenticated on the public internet)."""
    want = (os.getenv("MOBILE_ACCESS_KEY") or "").strip()
    if not want:
        return True
    got = (request.query_params.get("key")
           or request.headers.get("X-Mobile-Key")
           or request.cookies.get("mkey") or "")
    return got == want


def _sierra():
    try:
        p = f"{_EXP}/sierra_state.json"
        d = json.loads(open(p).read().strip() or "{}")
        d["_age_s"] = round(time.time() - os.path.getmtime(p), 1)
        return d
    except Exception:
        return {}


def _price():
    try:
        lp = json.loads(open(f"{_EXP}/live_price.json").read())
        return round((float(lp["bid"]) + float(lp["ask"])) / 2, 2)
    except Exception:
        return None


def _remote_data() -> dict | None:
    """07-15 (Michael: "הלינק = הנתונים של מכונת-המסחר"): when MOBILE_REMOTE_URL
    is set (e.g. http://<imac-ip>:8000), serve the TRADING machine's data through
    this link. Unreachable → fall back to local data with a clear badge."""
    base = (os.getenv("MOBILE_REMOTE_URL") or "").strip().rstrip("/")
    if not base:
        return None
    try:
        import urllib.request
        with urllib.request.urlopen(f"{base}/api/v9/mobile/data", timeout=3) as r:
            d = json.loads(r.read().decode("utf-8"))
        d["_src"] = "trading"
        d["_src_url"] = base
        return d
    except Exception as e:
        return {"_remote_err": str(e)[:60]}


@router.get("/data")
async def mobile_data(request: Request):
    if not _key_ok(request):
        raise HTTPException(status_code=401, detail="mobile access key required")
    import asyncio
    rem = await asyncio.to_thread(_remote_data)
    if rem is not None and "_remote_err" not in rem:
        return rem  # מכונת-המסחר עונה — הלינק מציג אותה
    # B3 (11.08): ts was a display string ("10:17:40") — the phone/Render page
    # could not tell fresh data from a frozen snapshot. Keep the human field,
    # add an epoch so any client can compute staleness.
    out = {"ts": time.strftime("%H:%M:%S"), "ts_epoch": time.time(),
           "sierra": _sierra(), "mid": _price(),
           # 13.08 (two machines, separate Render per machine): the page must
           # SAY which Mac it is showing. Same tag as the notification prefix.
           "machine": os.getenv("MACHINE_TAG", "").strip() or None}
    # רדאר בנייד (מייקל 2026-07-30: "תוסיף לאפליקציה של הפלאפון את הרדאר") —
    # אותו מקור-אמת בדיוק כמו הרצועה במסך: /api/v9/context/radar, קריאה ישירה
    # לפונקציה (לא self-HTTP — uvicorn עובד-יחיד, קריאה-עצמית = חסימה).
    try:
        from backend.v9.api.v9.context_radar import radar as _radar_fn
        out["radar"] = _radar_fn(request)
    except Exception as _rd_err:
        out["radar"] = None
        out["radar_err"] = str(_rd_err)[:80]
    out["_src"] = "local"
    if rem is not None:
        out["_remote_err"] = rem["_remote_err"]
    # עסקאות פעילות + P&L צף + Sierra order verification + B2 per-contract
    try:
        from backend.v9.db.read import read_all
        rows = read_all("""
            SELECT id, direction, entry_price, stop, t1, t2, t3,
                   COALESCE((quality->>'t0')::float, NULL) AS t0,
                   COALESCE((quality->>'contracts')::int, 0) AS contracts,
                   quality->>'pattern' AS pattern, state, mode,
                   pattern_id_at_entry,
                   firing_system,
                   quality->>'c1_target_id' AS c1_tgt_id,
                   quality->>'c2_target_id' AS c2_tgt_id,
                   quality->>'c3_target_id' AS c3_tgt_id,
                   quality->>'c1_stop_id' AS c1_stop_id,
                   to_char(entry_ts AT TIME ZONE 'Asia/Jerusalem','HH24:MI') AS t_in,
                   t1_hit_ts IS NOT NULL AS t1_hit,
                   t2_hit_ts IS NOT NULL AS t2_hit,
                   t3_hit_ts IS NOT NULL AS t3_hit,
                   stop_hit_ts IS NOT NULL AS stop_hit
            FROM v9_trades WHERE mode != 'shadow'
              AND state NOT IN ('CLOSED','CANCELLED') ORDER BY id DESC LIMIT 4""", {})
        mid = out["mid"]
        sierra = out.get("sierra") or {}
        acts = []
        for r in rows:
            r = dict(r)
            if mid and r.get("entry_price"):
                sign = 1 if (r.get("direction") or "").upper() == "LONG" else -1
                r["upnl_usd"] = round(sign * (mid - float(r["entry_price"])) * 5 * (r.get("contracts") or 1), 1)

            # P1.5: per-level Sierra verification (✅/🔴)
            r["sierra_verify"] = _verify_sierra_levels(r, sierra)

            # B2: per-contract breakdown (C1/C2/C3 — same logic as trades.py /active)
            _entry = float(r.get("entry_price") or 0)
            _stop = float(r.get("stop") or 0)
            _is_long = (r.get("direction") or "").upper() == "LONG"
            _mul = 1.0 if _is_long else -1.0
            _risk = abs(_entry - _stop) if _entry and _stop else 1.0
            _risk_usd = _risk * 5.0
            # 2026-08-18: three specs sliced to _n could never describe more than
            # three contracts, and the t0 this very query already SELECTs (line
            # ~109) was never used — so on a 5-contract position the phone showed
            # three legs, and the first one was measured against T1 while that
            # contract really exits at T0. Built from the same ladder the DLL
            # brackets with, so the phone, the desktop and the broker agree.
            from backend.v9.services.contract_size import target_index_for_contract
            _n = max(r.get("contracts") or 0, 1)
            _lvl = [r.get("t0"), r.get("t1"), r.get("t2"), r.get("t3")]
            _lvl_hit = [False, r.get("t1_hit"), r.get("t2_hit"), r.get("t3_hit")]
            _contract_specs = []
            for _i in range(_n):
                _leg = target_index_for_contract(_i, _n)
                _contract_specs.append(
                    ("C%d" % (_i + 1), _lvl[_leg], _lvl_hit[_leg]))
            _contracts = []
            for _cid, _tgt, _hit in _contract_specs:
                _tv = float(_tgt) if _tgt else 0
                if _hit:
                    _status = "HIT_TARGET"
                    _cpnl = round((_tv - _entry) * _mul * 5.0, 1)
                elif r.get("stop_hit"):
                    _status = "HIT_STOP"
                    _cpnl = round((_stop - _entry) * _mul * 5.0, 1)
                else:
                    _status = "OPEN"
                    _cpnl = round((_mul * (mid - _entry) * 5.0), 1) if mid else 0
                _cr = round(_cpnl / _risk_usd, 2) if _risk_usd > 0 else 0
                _cdist = None
                _cpct = None
                if _status == "OPEN" and _tv > 0 and mid:
                    _cdist = round((_tv - mid) if _is_long else (mid - _tv), 2)
                    _total = abs(_tv - _entry)
                    if _total > 0:
                        # SIGNED (2026-08-18). This was abs(mid - entry), which
                        # is positive no matter which way price went — a LONG
                        # five points UNDERWATER displayed as "+40% toward the
                        # target". The number has to tell Michael which side of
                        # entry he is on, so it is the progress in the trade's
                        # own direction and it goes negative when he is losing.
                        _prog = _mul * (mid - _entry) / _total * 100.0
                        _cpct = max(min(round(_prog, 0), 100), -100)
                _contracts.append({
                    "id": _cid, "target": _tv, "status": _status,
                    "pnl": _cpnl, "r": _cr,
                    "dist_pts": _cdist, "pct": _cpct,
                    "be": _cid == "C2" and r.get("t1_hit") and not r.get("t2_hit"),
                })
            r["legs"] = _contracts
            r["total_pnl"] = round(sum(c["pnl"] for c in _contracts), 1)
            r["total_r"] = round(sum(c["r"] for c in _contracts), 2)
            r["hits"] = sum(1 for c in _contracts if c["status"] == "HIT_TARGET")
            r["summary"] = f"{r['hits']}/{len(_contracts)} hit"

            # P1.5: per-target progress bars (kept for backwards compat).
            # t0 included and the percentage SIGNED — same fix as the per-leg
            # number above: abs() made a losing trade look like it was making
            # progress toward its target.
            if mid and r.get("entry_price"):
                entry = float(r["entry_price"])
                r["progress"] = {}
                for tgt in ("t0", "t1", "t2", "t3"):
                    tv = r.get(tgt)
                    if tv and float(tv) != 0:
                        total = abs(float(tv) - entry)
                        if total <= 0:
                            continue
                        pct = max(min(round(_mul * (mid - entry) / total * 100, 0),
                                      100), -100)
                        r["progress"][tgt] = {"target": float(tv), "pct": pct}

            # 2026-08-19 (Michael: "אחוז של כל הגעה ליעד או סטופ ותזוזה של
            # עסקה"): one glance-block per trade — signed movement in points,
            # % of the risk consumed toward the STOP, % of the way to the NEXT
            # unhit target, and Sierra's own worst/best excursion.
            if mid and _entry:
                r["move_pts"] = round(_mul * (mid - _entry), 2)
                if _stop and abs(_entry - _stop) > 0:
                    _tw = _mul * (_entry - mid) / abs(_entry - _stop) * 100.0
                    r["stop_pct"] = max(min(round(_tw, 0), 100), -100)
                _next = next((float(_lvl[_g]) for _g in range(4)
                              if _lvl[_g] and not _lvl_hit[_g]), None)
                if _next and abs(_next - _entry) > 0:
                    r["next_target"] = _next
                    r["next_target_pct"] = max(min(round(
                        _mul * (mid - _entry) / abs(_next - _entry) * 100, 0),
                        100), -100)
                _hi = sierra.get("high_during_pos")
                _lo = sierra.get("low_during_pos")
                if (isinstance(_hi, (int, float)) and isinstance(_lo, (int, float))
                        and abs(_hi) < 1e15 and abs(_lo) < 1e15
                        and (sierra.get("position_qty") or 0) != 0):
                    r["mfe_pts"] = round((_hi - _entry) if _is_long else (_entry - _lo), 2)
                    r["mae_pts"] = round((_entry - _lo) if _is_long else (_hi - _entry), 2)

            acts.append(r)
        out["active"] = acts
        day = read_all("""
            SELECT COALESCE(SUM(pnl_usd),0) pnl, COUNT(*) n,
                   COUNT(*) FILTER (WHERE pnl_usd > 0) w
            FROM v9_trades WHERE mode != 'shadow' AND state='CLOSED'
              AND (entry_ts AT TIME ZONE 'Asia/Jerusalem')::date =
                  (now() AT TIME ZONE 'Asia/Jerusalem')::date""", {})
        out["today"] = dict(day[0]) if day else {}
    except Exception as e:
        out["db_err"] = str(e)[:80]
    # 2026-08-19: ביטולי-חוסמים פעילים + הרשימה הניתנת-לביטול (לכפתורי-הדף)
    try:
        from backend.v9.services.gate_overrides import active_overrides, overridable_gates
        out["gate_overrides"] = active_overrides()
        out["gate_overridable"] = overridable_gates()
    except Exception:
        pass
    # סוג-יום חי
    try:
        from backend.v9.services.trade_context import get_live_day_type
        out["day_type"] = get_live_day_type()
    except Exception:
        out["day_type"] = None
    try:
        # request.app = ה-app הרץ בפועל (backend/main.py הוא ה-entrypoint —
        # לא backend.v9.app; ייבוא-מודול נותן instance אחר וריק)
        _app = request.app
        _cls = getattr(_app.state, "last_cls_result", None) or {}
        out["day_conf"] = _cls.get("confidence")
        # 07-15: "למה לא ירה" גם בנייד — ההחלטה האחרונה + ספירות-שער מאז-הריסטארט
        _gw = getattr(_app.state, "trading_gateway", None)
        _decs = list(getattr(_gw, "decisions", []) or [])
        if _decs:
            _n_fired = sum(1 for d in _decs if d.get("outcome") in ("live", "demo"))
            _n_blocked = sum(1 for d in _decs if d.get("blocked_by"))
            out["gate"] = {"attempts": len(_decs), "fired": _n_fired,
                           "blocked": _n_blocked, "last": _decs[-1]}
        # 07-15 (מייקל): פר-תבנית בנייד — יורה / למה-לא / מה-חוסם.
        # מיזוג: התהוות (build-status inspectors) + החלטת-השער האחרונה.
        try:
            from backend.v9.systems.build_status.aggregator import BuildStatusAggregator
            _bs = BuildStatusAggregator(
                five_min_system=getattr(_app.state, "five_min_system", None),
                woodies_system=getattr(_app.state, "woodies_system", None),
                day_type_machine=getattr(_app.state, "day_type_machine", None),
                footprint_system=getattr(_app.state, "footprint_system", None),
            ).get_status(systems=["five_min", "woodies"]).model_dump()

            def _norm(x):
                return "".join(ch for ch in str(x or "").upper() if ch.isalnum())

            _pats = []
            for _sysb in _bs.get("systems", []):
                for _p in (_sysb.get("patterns") or []):
                    _pn, _pi = _norm(_p.get("name")), _norm(_p.get("id"))
                    _last = None
                    for _d in reversed(_decs):  # newest first
                        _g = _norm(_d.get("pattern"))
                        if _g and (_g in (_pn, _pi) or _pn in _g or _pi in _g
                                   or (_pi and _pi in _g)):
                            _last = {"ts": _d.get("ts"), "blocked_by": _d.get("blocked_by"),
                                     "outcome": _d.get("outcome"),
                                     "trade_id": _d.get("trade_id"),
                                     "direction": _d.get("direction")}
                            break
                    _pats.append({
                        "sys": _sysb.get("id"), "name": _p.get("name") or _p.get("id"),
                        "status": _p.get("status"),
                        "reason": (str(_p.get("reason"))[:90] if _p.get("reason") else None),
                        "last": _last,
                    })
            out["patterns"] = _pats[:14]
        except Exception as _pe:
            out["patterns_err"] = str(_pe)[:60]
    except Exception:
        pass
    # דוח-יומי (Michael 07-16: "דוח יומי שגם יופיע בכיס") — נכתב ע"י
    # scripts/gen_daily_report.py בסגירת-RTH; הכרטיס בנייד קורא אותו.
    try:
        _dr = json.loads(open(f"{_EXP}/daily_report.json").read())
        out["daily"] = {"date": _dr.get("date"), "pnl_usd": _dr.get("pnl_usd"),
                        "n_trades": _dr.get("n_trades"), "wins": _dr.get("wins"),
                        "losses": _dr.get("losses"),
                        "day_type": (_dr.get("day_type") or {}).get("day_type")}
    except Exception:
        out["daily"] = None
    # דגלי-קריטיים + halt
    out["trading_paused"] = _is_paused()
    out["halt_cap"] = os.getenv("RISK_DAILY_LOSS_CAP", "400")
    from backend.v9.services.contract_size import ruled_contracts as _ruled
    out["contracts_cfg"] = _ruled() or 3   # the phone must not show a size the account does not hold
    # התראות אחרונות (לא-פתורות בלבד, 3 שורות)
    try:
        al = Path(os.path.expanduser("~/Downloads/mems26_web_git/docs/reports/ALERTS_LIVE.md"))
        lines = [l for l in al.read_text(encoding="utf-8", errors="ignore").splitlines()[-25:]
                 if l.strip().startswith(("- ", "🔴", "[")) and "RESOLVED" not in l]
        out["alerts"] = lines[-3:]
    except Exception:
        out["alerts"] = []
    return out


# NOTE: this function sits ABOVE the /flatten pair on purpose, with its own
# decorator immediately adjacent — never insert anything between a decorator
# and its function (T-36, the 422 class).
@router.post("/gate_override")
async def mobile_gate_override(request: Request):
    """2026-08-19 (מייקל: "מנגנון שיאפשר לי דרך האפליקציה לבטל חוסם").

    body {"gate": <blocked_by name>, "restore": bool}. רק שערי-דעה מהרשימה
    הלבנה; session-scoped (restart מחזיר הכל). מפתח-גישה חובה."""
    if not _key_ok(request):
        raise HTTPException(status_code=401, detail="mobile access key required")
    try:
        body = await request.json()
    except Exception:
        return {"ok": False, "error": "JSON body required"}
    gate = str(body.get("gate") or "").strip()
    from backend.v9.services.gate_overrides import (
        set_override, clear_override, active_overrides)
    if body.get("restore"):
        ok = clear_override(gate)
        return {"ok": ok, "overrides": active_overrides()}
    res = set_override(gate)
    if res is None:
        return {"ok": False,
                "error": f"'{gate}' אינו ניתן-לביטול (שער-בטיחות או לא-מוכר)",
                "overrides": active_overrides()}
    return {"ok": True, "disabled": res, "overrides": active_overrides()}


@router.post("/flatten")
async def mobile_flatten(request: Request):
    """07-15 (מייקל: "שיהיה ניתן לסגור עסקאות אמת באופן ידני") — כפתור-החירום
    של הכיס. שולח FLATTEN_ACCOUNT (protective-only: סוגר פוזיציות + מבטל
    הוראות; מאומת ב-DLL). מוגן: דגל MANUAL_FLATTEN_V1 (opt-in פר-מכונה,
    RULED) + body {"confirm":"FLATTEN"} מאישור-כפול בדף. כש-MOBILE_REMOTE_URL
    מוגדר — מועבר למכונת-המסחר, כך שהכפתור סוגר תמיד את מה שהמסך מציג."""
    import asyncio
    if not _key_ok(request):
        raise HTTPException(status_code=401, detail="mobile access key required")
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    if body.get("confirm") != "FLATTEN":
        return {"ok": False, "error": "confirm חסר — לא בוצע"}

    base = (os.getenv("MOBILE_REMOTE_URL") or "").strip().rstrip("/")
    if base:
        def _fwd():
            import urllib.request
            req = urllib.request.Request(
                f"{base}/api/v9/mobile/flatten",
                data=json.dumps({"confirm": "FLATTEN"}).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=5) as r:
                return json.loads(r.read().decode())
        try:
            out = await asyncio.to_thread(_fwd)
            out["_via"] = "trading-machine"
            return out
        except Exception as e:
            return {"ok": False, "error": f"מכונת-המסחר לא זמינה: {str(e)[:60]}"}

    if os.getenv("MANUAL_FLATTEN_V1", "0").lower() not in ("1", "true", "yes"):
        return {"ok": False, "error": "MANUAL_FLATTEN_V1 כבוי במכונה זו"}
    try:
        # ROOT-FIX 2026-08-15: this called write_trade_command WITHOUT the
        # required `trade_id` keyword → TypeError → the phone emergency
        # FLATTEN button never sent anything. It reported {"ok": true} only
        # because the exception message was returned by the caller's except.
        from backend.v9.services.sierra_command import write_flatten_account
        write_flatten_account(source="mobile_manual", reason="michael pressed FLATTEN")
        return {"ok": True, "msg": "FLATTEN_ACCOUNT נשלח לסיירה"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:80]}


def _verify_sierra_levels(trade: dict, sierra: dict) -> dict:
    """P1.5: Compare DB target/stop levels vs Sierra working orders.

    Returns per-level verification: ✅ match / 🔴 gap with both prices.
    """
    result = {}
    orders = sierra.get("orders") or []
    if not orders or not trade.get("entry_price"):
        return result

    # Build order price lookup from Sierra
    sierra_prices = {}
    for o in orders:
        oid = o.get("order_id") or o.get("id")
        price = o.get("price") or o.get("limit_price")
        if oid and price:
            sierra_prices[str(oid)] = float(price)

    # Check each level
    for level, order_key in [("stop", "c1_stop_id"), ("t1", "c1_tgt_id"),
                              ("t2", "c2_tgt_id"), ("t3", "c3_tgt_id")]:
        db_val = trade.get(level)
        oid = trade.get(order_key)
        if db_val is None or oid is None:
            continue
        db_val = float(db_val)
        sierra_val = sierra_prices.get(str(oid))
        if sierra_val is None:
            result[level] = {"db": db_val, "sierra": None, "match": None, "status": "unknown"}
        elif abs(db_val - sierra_val) <= 0.25:
            result[level] = {"db": db_val, "sierra": sierra_val, "match": True, "status": "ok"}
        else:
            result[level] = {"db": db_val, "sierra": sierra_val, "match": False,
                              "status": "gap", "gap": round(abs(db_val - sierra_val), 2)}
    return result


_PAUSE_FILE = os.path.expanduser("~/SierraChart_Data/v9_export/trading_paused.json")


def _is_paused() -> bool:
    return os.path.exists(_PAUSE_FILE)


@router.post("/pause")
async def mobile_pause(request: Request):
    """PAUSE: route all fires to shadow-only (no new live/demo entries).
    Existing positions untouched — defenses/BE/MAE continue. Double-confirm required."""
    if not _key_ok(request):
        raise HTTPException(status_code=401, detail="mobile access key required")
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    if body.get("confirm") != "PAUSE":
        return {"ok": False, "error": "confirm=PAUSE required"}

    base = (os.getenv("MOBILE_REMOTE_URL") or "").strip().rstrip("/")
    if base:
        import asyncio
        def _fwd():
            import urllib.request
            req = urllib.request.Request(
                f"{base}/api/v9/mobile/pause",
                data=json.dumps({"confirm": "PAUSE"}).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=5) as r:
                return json.loads(r.read().decode())
        try:
            out = await asyncio.to_thread(_fwd)
            out["_via"] = "trading-machine"
            return out
        except Exception as e:
            return {"ok": False, "error": f"trading machine unreachable: {str(e)[:60]}"}

    try:
        import time as _t
        Path(_PAUSE_FILE).write_text(
            json.dumps({"paused": True, "ts": _t.strftime("%Y-%m-%dT%H:%M:%S"),
                         "source": "mobile"}),
            encoding="utf-8")
        try:
            from scripts.ops_log import log_event
            log_event("mobile", "WARN", "TRADING PAUSED via mobile emergency")
        except Exception:
            pass
        # B5: push notification on PAUSE
        try:
            from backend.v9.services.ntfy_notify import on_pause
            on_pause("PAUSED via mobile — fires routed to shadow only")
        except Exception:
            pass
        return {"ok": True, "msg": "PAUSED — fires routed to shadow only"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:80]}


@router.post("/resume")
async def mobile_resume(request: Request):
    """RESUME: restore normal trading (fires go to demo/live again)."""
    if not _key_ok(request):
        raise HTTPException(status_code=401, detail="mobile access key required")
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    if body.get("confirm") != "RESUME":
        return {"ok": False, "error": "confirm=RESUME required"}

    base = (os.getenv("MOBILE_REMOTE_URL") or "").strip().rstrip("/")
    if base:
        import asyncio
        def _fwd():
            import urllib.request
            req = urllib.request.Request(
                f"{base}/api/v9/mobile/resume",
                data=json.dumps({"confirm": "RESUME"}).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=5) as r:
                return json.loads(r.read().decode())
        try:
            out = await asyncio.to_thread(_fwd)
            out["_via"] = "trading-machine"
            return out
        except Exception as e:
            return {"ok": False, "error": f"trading machine unreachable: {str(e)[:60]}"}

    try:
        p = Path(_PAUSE_FILE)
        if p.exists():
            p.unlink()
        try:
            from scripts.ops_log import log_event
            log_event("mobile", "WARN", "TRADING RESUMED via mobile")
        except Exception:
            pass
        # B5: push notification on RESUME
        try:
            from backend.v9.services.ntfy_notify import on_resume
            on_resume("RESUMED via mobile — normal trading restored")
        except Exception:
            pass
        return {"ok": True, "msg": "RESUMED — normal trading restored"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:80]}


_PAGE = """<!DOCTYPE html><html lang="he" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>MEMS26 · מוניטור</title><style>
body{margin:0;background:#0b0e14;color:#e6edf3;font-family:-apple-system,'Segoe UI',sans-serif;padding:14px 12px 40px}
h1{font-size:16px;margin:0 0 10px;color:#79c0ff}.card{background:#151a23;border:1px solid #2a3140;border-radius:12px;padding:12px;margin-bottom:10px}
.big{font-size:28px;font-weight:800}.green{color:#3fb950}.red{color:#f85149}.dim{color:#8b949e;font-size:12px}
.row{display:flex;justify-content:space-between;align-items:baseline;margin:3px 0}.tag{font-size:11px;padding:1px 7px;border-radius:6px;background:#21262d}
.alert{color:#f0883e;font-size:12px;line-height:1.5}.pulse{animation:p 2s infinite}@keyframes p{50%{opacity:.4}}
</style></head><body>
<h1>⚡ MEMS26 · מוניטור-כיס <span id="clock" class="dim"></span></h1>
<div class="card"><div class="row"><span class="dim">פוזיציה בסיירה</span><span id="mode" class="tag"></span></div>
<div class="big" id="pos">—</div><div class="dim" id="posdet"></div></div>
<div class="card"><div class="dim">עסקאות פעילות</div><div id="active">—</div></div>
<div class="card"><div class="row"><span class="dim">יומי (סגורות)</span><span class="dim" id="daymeta"></span></div>
<div class="big" id="daypnl">—</div><div class="dim">עצירה ב-−$<span id="cap"></span></div></div>
<div class="card"><div class="row"><span class="dim">חשבון</span><span id="acctmeta" class="dim"></span></div>
<div class="row"><span class="dim">שווי חשבון</span><span id="acct_val" style="font-weight:800;font-size:18px">—</span></div>
<div class="row"><span class="dim">רווח/הפסד יומי</span><span id="acct_day">—</span></div>
<div class="row"><span class="dim">P&L פוזיציה פתוחה</span><span id="acct_open">—</span></div>
<div class="row"><span class="dim">זמין למרג'ין</span><span id="acct_avail" class="dim">—</span></div></div>
<div class="card"><div class="row"><span class="dim">📡 רדאר</span><span id="rmeta" class="dim"></span></div>
<div id="radar" style="font-size:12.5px;line-height:1.8">—</div></div>
<div class="card"><div class="row"><span class="dim">סוג-יום</span><span id="dayconf" class="dim"></span></div>
<div style="font-size:20px;font-weight:700" id="daytype">—</div></div>
<div class="card"><div class="row"><span class="dim">למה לא יורה? (שער-הירי)</span><span id="gmeta" class="dim"></span></div>
<div id="gate" style="font-size:12px;line-height:1.6">—</div></div>
<div class="card"><div class="dim">תבניות — מי יורה, למה לא, ומה חוסם</div>
<div id="pats" style="font-size:11.5px;line-height:1.7">—</div></div>
<div class="card"><div class="row"><span class="dim">דוח-יומי (סגירת-RTH)</span><span id="drmeta" class="dim"></span></div>
<div id="daily" style="font-size:13px;line-height:1.6">—</div></div>
<div class="card"><div class="dim">התראות</div><div id="alerts" class="alert">—</div></div>
<div id="staleBanner" style="display:none;background:#d29922;color:#000;text-align:center;padding:8px;border-radius:12px;margin-bottom:10px;font-size:14px;font-weight:700">⚠ נתונים ישנים</div>
<div id="pauseBanner" style="display:none;background:#f85149;color:#fff;text-align:center;padding:10px;border-radius:12px;margin-bottom:10px;font-size:16px;font-weight:800">PAUSED — fires routed to shadow only</div>
<button id="pauseBtn" style="width:100%;padding:12px;margin:4px 0;border-radius:12px;border:1px solid #d29922;
background:#2d2614;color:#d29922;font-size:14px;font-weight:700;font-family:inherit">⏸ השהה מסחר (צל-בלבד)</button>
<button id="flat" style="width:100%;padding:12px;margin:4px 0 8px;border-radius:12px;border:1px solid #f85149;
background:#2d1214;color:#f85149;font-size:14px;font-weight:700;font-family:inherit">⏻ סגור עסקאות-אמת (השטח הכל)</button>
<div class="dim" id="health" style="text-align:center"></div>
<script>
const GATE_HE = {kill_switch:'מתג-חירום',session_gate_closed:'מחוץ לחלון-מסחר',eod_entry_cutoff:'סוף-יום',
feed_watchdog:'פיד תקוע',cooldown:'צינון',suffering_side_veto:'וטו צד-סובל',duplicate_fire:'ירי-כפול',
chop_searching:'שוק-קופצני',opening_type_gate:'שער סוג-פתיחה',daytype_playbook:'פלייבוק סוג-יום',
trend_direction_gate:'כיוון-מגמה',reactive_location:'מיקום ריאקטיבי',location_gate:'שער-מיקום (דלתון)',
daytype_position_gate:'משפחה×סוג-יום',cont_trend_filter:'המשך-עם-מגמה',direction_context:'הקשר-כיוון',
lsma_flat:'LSMA שטוח',news_blackout:'חלון-חדשות',day_direction_doctrine:'דוקטרינת-כיוון',
entry_not_confirmed:'אין אישור-כניסה',t1_wrong_side:'T1 בצד שגוי',rr_entry_gate:'שער R:R',
daily_loss_halt:'עצירת הפסד-יומי',consecutive_loss_halt:'עצירת רצף-הפסדים',s4_risk_cap:'תקרת-סיכון S4',pattern_loss_breaker:'מפסק-הפסדים (תבנית)',cluster_guard:'שומר-צבירה',cold_start_guard:'אתחול-קר',structural_targets_wrong_side:'יעדים בצד-שגוי',rr_hard_floor:'רצפת R:R',
awaiting_release:'ממתין לשחרור-אזור',extreme_chase_guard:'רדיפת-קיצון',drive_exhaustion_veto:'תשישות-דרייב',pattern_stop_cooldown:'צינון אחרי-סטופ',zone_limit_late_entry:'איחור לאזור',
strict_risk:'בדיקת-סיכון-לייב',pre_send_entry_guard:'שומר קדם-שיגור (פוזיציה-עומדת)',margin_zero_size:'אין מרג׳ין',live_slot_occupied:'עסקה-חיה פתוחה',place_refused:'PLACE נדחה'};
async function load(){
 try{
  const r = await fetch('/api/v9/mobile/data'+Q,{cache:'no-store'}); const d = await r.json();
  document.getElementById('clock').textContent = d.ts + (d._src==='trading'? ' · 📡 מכונת-המסחר' : d._remote_err? ' · ⚠ מקומי (מכונת-המסחר לא-זמינה)' : '');
  const s = d.sierra||{}; const q = s.position_qty||0;
  document.getElementById('mode').textContent = (s.is_sim? 'סים':'אמת') + (s.order_placement_armed? ' · חמוש':' · לא-חמוש');
  // ── חשבון (Account Monitor דרך הסיארה, כמו במסך) ──
  const $$ = (v,pfx)=> v==null? '—' : (pfx&&v>=0?'+':'')+Number(v).toFixed(2)+'$';
  const cls = v => v==null?'dim':(v>=0?'green':'red');
  document.getElementById('acct_val').textContent = $$(s.acct_account_value);
  const ad=document.getElementById('acct_day'); ad.textContent=$$(s.acct_daily_pl,1); ad.className=cls(s.acct_daily_pl);
  const ao=document.getElementById('acct_open'); ao.textContent=$$(s.acct_open_positions_pl,1); ao.className=cls(s.acct_open_positions_pl);
  document.getElementById('acct_avail').textContent = $$(s.acct_available_funds);
  document.getElementById('acctmeta').textContent = s.acct_trading_disabled? '🔴 מסחר-מושבת' : s.acct_loss_limit_reached? '🔴 תקרת-הפסד' : '';
  // ── רדאר (אותו מקור כמו הרצועה במסך) ──
  const R = d.radar; const rEl = document.getElementById('radar');
  if(R){
   const gl=R.gates_last_hour||{}, tr=R.trading||{}, rg=R.release_gate||{};
   const leg = R.leg==='UP'?'<span class="green">▲ UP</span>':R.leg==='DOWN'?'<span class="red">▼ DOWN</span>':'—';
   const integ = R.bar_integrity==='clean'?'<span class="green">✓ נקי</span>':R.bar_integrity==='suspect'?'<span class="red">🔴 חשוד</span>':(R.bar_integrity||'—');
   const canTrade = tr.armed===1 && (tr.contracts_allowed||0)>0 && !tr.stale;
   let lb='';
   if(gl.last_block) lb='<div class="row"><span class="dim">חסימה אחרונה</span><span>'+gl.last_block.ts+' '+(GATE_HE[gl.last_block.gate]||gl.last_block.gate)+'</span></div>';
   rEl.innerHTML =
    '<div class="row"><span class="dim">סוג-יום</span><span>'+(R.day_type||'—')+(R.confidence!=null?' <span class=dim>'+Math.round(R.confidence*100)+'%</span>':'')+'</span></div>'+
    '<div class="row"><span class="dim">רגל</span><span>'+leg+'</span></div>'+
    '<div class="row"><span class="dim">פתיחה</span><span>'+(R.opening_type||'—')+(R.opening_dir?' '+R.opening_dir:'')+'</span></div>'+
    '<div class="row"><span class="dim">שער-שחרור</span><span>'+(rg.state==='holding'?'<span style="color:#f0883e">מחזיק '+(rg.age_min??'?')+' דק\\'</span>':'פנוי')+'</span></div>'+
    '<div class="row"><span class="dim">שערים/שעה</span><span><span class="'+((gl.passed||0)>0?'green':'dim')+'">'+(gl.passed||0)+' עברו</span> / <span style="color:#d29922">'+(gl.blocked||0)+' נחסמו</span></span></div>'+lb+
    '<div class="row"><span class="dim">שלמות-ברים</span><span>'+integ+'</span></div>'+
    '<div class="row"><span class="dim">מסחר</span><span>'+(canTrade?'<span class="green">✓ מוכן · עד '+tr.contracts_allowed+' חוזים</span>':'<span class="red">'+(tr.stale?'נתונים לא-טריים':tr.armed!==1?'לא-חמוש':'אין מרג\\'ין')+'</span>')+'</span></div>';
   document.getElementById('rmeta').textContent = (tr.is_sim===0?'לייב':'סים');
  } else { rEl.innerHTML='<span class="dim">'+(d.radar_err?'רדאר-שגיאה: '+d.radar_err:'רדאר לא-זמין (מכונה מרוחקת ישנה?)')+'</span>'; }
  const g = d.gate; const ge = document.getElementById('gate');
  if(g && g.last){
   const L = g.last; const t = L.ts? new Date(L.ts).toTimeString().slice(0,5) : '';
   ge.innerHTML = L.blocked_by? '⛔ '+t+' '+(L.pattern||'?')+' '+(L.direction||'')+' נחסם — <b>'+(GATE_HE[L.blocked_by]||L.blocked_by)+'</b>'
    : (L.outcome==='live'||L.outcome==='demo')? '<span class="green">🔫 '+t+' '+(L.pattern||'?')+' ירה ('+(L.outcome==='live'?'לייב':'דמו')+(L.trade_id?' #'+L.trade_id:'')+')</span>'
    : '👁 '+t+' '+(L.pattern||'?')+' עבר-שערים · צל-בלבד';
   if(!L.blocked_by && L.live_blocked_by) ge.innerHTML += '<div style="color:#f0883e;font-size:11px">⛔ הלייב לא-שוגר: <b>'+(GATE_HE[L.live_blocked_by]||L.live_blocked_by)+'</b>'+(L.live_block_reason?' — '+String(L.live_block_reason).replace(/</g,'&lt;').slice(0,70):'')+'</div>';
   if(L.blocked_by && (d.gate_overridable||[]).includes(L.blocked_by)) ge.innerHTML += ' <button onclick="gateOv(\\''+L.blocked_by+'\\',false)" style="padding:3px 10px;border-radius:8px;border:1px solid #d29922;background:#2d2614;color:#d29922;font-size:11px;font-family:inherit">🔓 בטל חוסם זה (עד-ריסטארט)</button>';
   document.getElementById('gmeta').textContent = g.attempts+' ניסיונות · '+g.fired+' ירו · '+g.blocked+' נחסמו';
  } else { ge.innerHTML = '<span class="dim">אף מועמד לא הגיע לשער מאז-הריסטארט — ראה פאנל-תבניות</span>'; document.getElementById('gmeta').textContent=''; }
  const ov = d.gate_overrides||[];
  if(ov.length) ge.innerHTML += '<div style="margin-top:5px;padding:4px 6px;border:1px solid #d29922;border-radius:8px;color:#d29922;font-size:11px">🔓 חוסמים מבוטלים (עד-ריסטארט): '+ov.map(o=>(o.label||o.gate)+' <span class="dim">'+o.ts+'</span> <button onclick="gateOv(\\''+o.gate+'\\',true)" style="padding:1px 8px;border-radius:6px;border:1px solid #3fb950;background:#0d2818;color:#3fb950;font-size:10.5px;font-family:inherit">החזר</button>').join(' · ')+'</div>';
  const ST_HE = {ready:['מוכן לירי','#3fb950'],armed:['חמוש','#3fb950'],fired:['ירה היום','#58a6ff'],
   building:['בהתהוות','#d29922'],blocked:['ממתין','#8b949e'],vetoed:['וטו','#f85149'],skip:['SKIP לסוג-היום','#f85149'],
   not_applicable:['לא-רלוונטי','#8b949e'],unknown:['?','#8b949e']};
  const P = d.patterns||[];
  document.getElementById('pats').innerHTML = P.length? P.map(p=>{
   const st = ST_HE[p.status]||ST_HE.unknown;
   let line = '';
   if(p.last){
    const t = p.last.ts? new Date(p.last.ts).toTimeString().slice(0,5) : '';
    const _ob = p.last.blocked_by && (d.gate_overridable||[]).includes(p.last.blocked_by)? ' <a href="#" onclick="gateOv(\\''+p.last.blocked_by+'\\',false);return false" style="color:#d29922">🔓 בטל</a>':'';
    line = p.last.blocked_by? '<div style="color:#f0883e;font-size:10.5px">⛔ '+t+' נחסם — '+(GATE_HE[p.last.blocked_by]||p.last.blocked_by)+_ob+'</div>'
     : (p.last.outcome==='live'||p.last.outcome==='demo')? '<div class="green" style="font-size:10.5px">🔫 '+t+' ירה'+(p.last.trade_id?' #'+p.last.trade_id:'')+'</div>'
     : '<div class="dim" style="font-size:10.5px">👁 '+t+' עבר-שערים · צל</div>';
   } else if(p.reason && p.status!=='ready' && p.status!=='fired'){
    line = '<div class="dim" style="font-size:10.5px">מה חסר: '+String(p.reason).replace(/</g,'&lt;').slice(0,80)+'</div>';
   }
   return '<div style="border-bottom:1px solid #1c2330;padding:3px 0"><div class="row"><span>'+p.name+'</span><span style="color:'+st[1]+';font-size:10.5px">'+st[0]+'</span></div>'+line+'</div>';
  }).join('') : '<span class="dim">אין נתוני-תבניות</span>';
  const posEl = document.getElementById('pos');
  posEl.textContent = q===0? 'FLAT' : (q>0? 'LONG ':'SHORT ') + Math.abs(q);
  posEl.className = 'big ' + (q===0?'':'pulse');
  document.getElementById('posdet').textContent = q!==0? ('ממוצע '+s.avg_price+' · '+s.working_orders+' הוראות-הגנה') : ('עין-מצב '+(s._age_s??'?')+'ש');
  const a = d.active||[];
  document.getElementById('active').innerHTML = a.length? a.map(t=>{
   // P1.5: Sierra verification icons
   const sv = t.sierra_verify||{};
   function vIcon(level){
    const v=sv[level]; if(!v) return '';
    if(v.match===true) return '<span class="green">✅</span>';
    if(v.match===false) return '<span class="red">🔴 '+v.db+'≠'+v.sierra+'</span>';
    return '<span class="dim">❓</span>';
   }
   // B2: per-contract rows (C1/C2/C3)
   const legs = t.legs||[];
   const SC={'OPEN':'#d29922','HIT_TARGET':'#3fb950','HIT_STOP':'#f85149'};
   const SL={'OPEN':'פתוח','HIT_TARGET':'✓ מילוי','HIT_STOP':'✗ סטופ'};
   function legRow(c){
    const col=SC[c.status]||'#8b949e';
    const pnlCol=c.pnl>=0?'green':'red';
    let bar='';
    if(c.status==='OPEN'&&c.pct!=null){
     const bc=c.pct>=90?'#3fb950':c.pct>=50?'#d29922':'#8b949e';
     bar=`<div style="background:#21262d;border-radius:3px;height:5px;margin:2px 0"><div style="background:${bc};width:${c.pct}%;height:100%;border-radius:3px"></div></div>`;
    }
    const dist=c.dist_pts!=null?(c.dist_pts>=0?c.dist_pts.toFixed(1)+'pt ליעד':Math.abs(c.dist_pts).toFixed(1)+'pt מעבר'):'';
    return `<div style="border-bottom:1px solid #1c2330;padding:3px 0">`+
     `<div class="row"><span style="font-weight:600;width:24px;color:#8b949e">${c.id}</span>`+
     `<span style="font-family:monospace;font-size:11px;width:55px">${c.target?c.target.toFixed(2):'—'}</span>`+
     `<span style="font-size:10px;color:${col};padding:0 4px">${SL[c.status]||c.status}${c.be?' ⇄':''}</span>`+
     `<span style="font-family:monospace;font-size:11px;width:40px;text-align:left" class="${pnlCol}">${c.pnl>=0?'+':''}${c.pnl}$</span>`+
     `<span class="dim" style="font-family:monospace;font-size:10px;width:30px;text-align:left">${c.r.toFixed(1)}R</span></div>`+
     (dist?`<div class="dim" style="font-size:10px;padding-right:24px">${dist} · ${c.pct??0}%</div>`:'')+
     bar+`</div>`;
   }
   // Total P&L from per-contract
   const tPnl=t.total_pnl??t.upnl_usd??0;
   const tR=t.total_r??0;
   return `<div style="border:1px solid #2a3140;border-radius:10px;padding:8px;margin-bottom:8px">`+
   `<div class="row"><span style="font-weight:700">#${t.id} ${t.direction} ×${legs.length||t.contracts} ${t.pattern_id_at_entry||t.pattern||''}</span>`+
   `<span class="${tPnl>=0?'green':'red'}" style="font-size:18px;font-weight:800">${tPnl>=0?'+':''}${tPnl.toFixed(0)}$ <span class="dim" style="font-size:11px">${tR.toFixed(1)}R</span></span></div>`+
   `<div class="dim">כניסה ${t.entry_price} · סטופ ${t.stop??'—'} ${vIcon('stop')} · ${t.t_in} · S${t.firing_system||'?'}</div>`+
   (t.move_pts!=null?`<div class="row" style="font-size:11.5px;margin-top:3px"><span class="dim">תזוזה</span><span class="${t.move_pts>=0?'green':'red'}">${t.move_pts>0?'+':''}${t.move_pts} נק׳${t.mae_pts!=null?' · הכי-נגד '+t.mae_pts:''}${t.mfe_pts!=null?' · הכי-בעד '+t.mfe_pts:''}</span></div>`:'')+
   (t.stop_pct!=null?`<div class="row" style="font-size:11.5px"><span class="dim">מהדרך לסטופ</span><span class="${t.stop_pct>=50?'red':'dim'}" style="font-weight:700">${Math.max(t.stop_pct,0)}%</span></div>`:'')+
   (t.next_target_pct!=null?`<div class="row" style="font-size:11.5px"><span class="dim">ליעד הבא ${t.next_target??''}</span><span class="${t.next_target_pct>=0?'green':'red'}" style="font-weight:700">${t.next_target_pct>0?'+':''}${t.next_target_pct}%</span></div>`:'')+
   (legs.length?`<div style="margin-top:6px">${legs.map(legRow).join('')}</div>`:
   `<div style="font-size:11px;margin-top:4px">`+
   `<div class="row"><span>T1 ${t.t1??'—'} ${vIcon('t1')}</span><span>T2 ${t.t2??'—'} ${vIcon('t2')}</span><span>T3 ${t.t3??'—'} ${vIcon('t3')}</span></div></div>`)+
   `<div class="row dim" style="margin-top:4px;font-size:10px"><span>${t.summary||''}</span></div>`+
   `</div>`;
  }).join('')
   : '<span class="dim">אין עסקה פעילה</span>';
  const td = d.today||{}; const pnl = td.pnl??0;
  const de = document.getElementById('daypnl');
  de.textContent = (pnl>=0?'+':'')+Number(pnl).toFixed(0)+'$';
  de.className = 'big '+(pnl>=0?'green':'red');
  document.getElementById('daymeta').textContent = (td.n||0)+' עסקאות · '+(td.w||0)+' מנצחות';
  document.getElementById('cap').textContent = d.halt_cap;
  document.getElementById('daytype').textContent = d.day_type||'—';
  document.getElementById('dayconf').textContent = d.day_conf!=null? 'ביטחון '+d.day_conf : '';
  const dr = d.daily; const drEl = document.getElementById('daily');
  if(dr){
   const p = dr.pnl_usd||0;
   drEl.innerHTML = '<span class="'+(p>=0?'green':'red')+'" style="font-size:16px;font-weight:800">'+(p>=0?'+':'')+p+'$</span> · '+
    (dr.n_trades||0)+' עסקאות ('+(dr.wins||0)+'W/'+(dr.losses||0)+'L) · '+(dr.day_type||'—');
   document.getElementById('drmeta').textContent = dr.date||'';
  } else { drEl.innerHTML = '<span class="dim">יופק בסגירת-RTH</span>'; }
  document.getElementById('alerts').innerHTML = (d.alerts&&d.alerts.length)? d.alerts.map(x=>'<div>'+x.replace(/</g,'&lt;').slice(0,110)+'</div>').join(''):'<span class="dim">שקט ✓</span>';
  updatePause(!!d.trading_paused);
  // B3: stale-data indicator — compare ts_epoch to client clock
  const staleEl = document.getElementById('staleBanner');
  if(d.ts_epoch){
   const age = Math.round(Date.now()/1000 - d.ts_epoch);
   if(age > 30){
    staleEl.style.display='block';
    staleEl.textContent='⚠ נתונים ישנים — '+age+'ש מאז עדכון אחרון';
   } else { staleEl.style.display='none'; }
  }
  document.getElementById('health').textContent = 'מחיר '+(d.mid??'—')+' · חוזים מוגדרים: '+d.contracts_cfg+' · רענון-5ש';
 }catch(e){ document.getElementById('health').textContent = '⚠ אין קשר למערכת — '+e; }
}
load(); setInterval(load, 5000);
async function gateOv(g,restore){
 if(!confirm((restore?'להחזיר את החוסם ':'לבטל את החוסם ')+g+'?')) return;
 if(!restore && !confirm('אישור סופי — ביטול עד-ריסטארט של '+g+'? עסקאות שהשער הזה היה עוצר יעברו.')) return;
 try{const r=await fetch('/api/v9/mobile/gate_override'+Q,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({gate:g,restore:restore})});
  const d=await r.json(); if(!d.ok) alert('✗ '+(d.error||'נכשל')); load();
 }catch(e){alert('✗ '+e);}
}
// Pause banner update
function updatePause(paused){
 const b=document.getElementById('pauseBanner'); b.style.display=paused?'block':'none';
 const pb=document.getElementById('pauseBtn');
 if(paused){pb.textContent='▶ חדש מסחר (RESUME)';pb.style.borderColor='#3fb950';pb.style.color='#3fb950';pb.style.background='#0d2818';}
 else{pb.textContent='⏸ השהה מסחר (צל-בלבד)';pb.style.borderColor='#d29922';pb.style.color='#d29922';pb.style.background='#2d2614';}
 window._paused=paused;
}
document.getElementById('pauseBtn').onclick = async () => {
 const action = window._paused? 'RESUME':'PAUSE';
 const msg = action==='PAUSE'? 'להשהות את המסחר? כניסות חדשות ינותבו לצל-בלבד.':'לחדש מסחר רגיל?';
 if(!confirm(msg)) return;
 if(!confirm('אישור סופי — '+action+' עכשיו?')) return;
 const b=document.getElementById('pauseBtn'); b.disabled=true; b.textContent='שולח...';
 try{
  const ep=action==='PAUSE'?'pause':'resume';
  const r=await fetch('/api/v9/mobile/'+ep+Q,{method:'POST',headers:{'Content-Type':'application/json','X-Mobile-Key':KEY},body:JSON.stringify({confirm:action})});
  const d=await r.json();
  b.textContent=d.ok? '✓ '+d.msg : '✗ '+(d.error||'failed');
  if(d.ok) updatePause(action==='PAUSE');
 }catch(e){ b.textContent='✗ no connection'; }
 setTimeout(()=>{ updatePause(window._paused); b.disabled=false; }, 4000);
};
document.getElementById('flat').onclick = async () => {
 if(!confirm('לסגור את כל עסקאות-האמת ולבטל את כל ההוראות?')) return;
 if(!confirm('אישור סופי — FLATTEN עכשיו?')) return;
 const b = document.getElementById('flat'); b.disabled = true; b.textContent = 'שולח...';
 try{
  const r = await fetch('/api/v9/mobile/flatten'+Q,{method:'POST',headers:{'Content-Type':'application/json','X-Mobile-Key':KEY},body:JSON.stringify({confirm:'FLATTEN'})});
  const d = await r.json();
  b.textContent = d.ok? '✓ נשלח — בדוק פוזיציה' : '✗ '+(d.error||'נכשל');
 }catch(e){ b.textContent = '✗ אין קשר'; }
 setTimeout(()=>{ b.disabled=false; b.textContent='⏻ סגור עסקאות-אמת (השטח הכל)'; }, 6000);
};
</script></body></html>"""


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def mobile_page(request: Request):
    if not _key_ok(request):
        return HTMLResponse(
            "<html dir=rtl><body style='background:#0b0e14;color:#e6edf3;"
            "font-family:-apple-system;padding:40px;text-align:center'>"
            "<h2>🔒 נדרש מפתח-גישה</h2><p>הוסף <code>?key=…</code> לכתובת.</p>"
            "</body></html>", status_code=401)
    resp = HTMLResponse(_PAGE)
    # FIX 07-25 (Michael: "מערכת הכיס לא עובדת"): _key_ok() has always accepted an
    # `mkey` cookie, but nothing ever SET it — so a home-screen bookmark without
    # ?key= (and every in-page /data fetch after a cookie-less load) returned 401
    # and the app looked dead. Persist the key as a cookie on the first keyed
    # visit so the bare URL works from then on. Only when a key was supplied
    # explicitly (never invent one), 30 days, httponly, lax.
    _want = (os.getenv("MOBILE_ACCESS_KEY") or "").strip()
    _given = (request.query_params.get("key") or request.headers.get("X-Mobile-Key") or "")
    if _want and _given == _want and request.cookies.get("mkey") != _want:
        resp.set_cookie("mkey", _want, max_age=30 * 24 * 3600,
                        httponly=True, samesite="lax", path="/")
    return resp
