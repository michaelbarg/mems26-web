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

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/api/v9/mobile", tags=["v9-mobile"])

_EXP = os.path.expanduser("~/SierraChart_Data/v9_export")


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
    import asyncio
    rem = await asyncio.to_thread(_remote_data)
    if rem is not None and "_remote_err" not in rem:
        return rem  # מכונת-המסחר עונה — הלינק מציג אותה
    out = {"ts": time.strftime("%H:%M:%S"), "sierra": _sierra(), "mid": _price()}
    out["_src"] = "local"
    if rem is not None:
        out["_remote_err"] = rem["_remote_err"]
    # עסקאות פעילות + P&L צף
    try:
        from backend.v9.db.read import read_all
        rows = read_all("""
            SELECT id, direction, entry_price, stop, t1, t2, t3,
                   COALESCE((quality->>'t0')::float, NULL) AS t0,
                   COALESCE((quality->>'contracts')::int, 0) AS contracts,
                   quality->>'pattern' AS pattern, state, mode,
                   to_char(entry_ts AT TIME ZONE 'Asia/Jerusalem','HH24:MI') AS t_in
            FROM v9_trades WHERE mode != 'shadow'
              AND state NOT IN ('CLOSED','CANCELLED') ORDER BY id DESC LIMIT 4""", {})
        mid = out["mid"]
        acts = []
        for r in rows:
            r = dict(r)
            if mid and r.get("entry_price"):
                sign = 1 if (r.get("direction") or "").upper() == "LONG" else -1
                r["upnl_usd"] = round(sign * (mid - float(r["entry_price"])) * 5 * (r.get("contracts") or 1), 1)
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
    # דגלי-קריטיים + halt
    out["halt_cap"] = os.getenv("RISK_DAILY_LOSS_CAP", "400")
    out["contracts_cfg"] = 4 if os.getenv("FIXED_CONTRACTS_4", "0") == "1" else 3
    # התראות אחרונות (לא-פתורות בלבד, 3 שורות)
    try:
        al = Path(os.path.expanduser("~/Downloads/mems26_web_git/docs/reports/ALERTS_LIVE.md"))
        lines = [l for l in al.read_text(encoding="utf-8", errors="ignore").splitlines()[-25:]
                 if l.strip().startswith(("- ", "🔴", "[")) and "RESOLVED" not in l]
        out["alerts"] = lines[-3:]
    except Exception:
        out["alerts"] = []
    return out


@router.post("/flatten")
async def mobile_flatten(request: Request):
    """07-15 (מייקל: "שיהיה ניתן לסגור עסקאות אמת באופן ידני") — כפתור-החירום
    של הכיס. שולח FLATTEN_ACCOUNT (protective-only: סוגר פוזיציות + מבטל
    הוראות; מאומת ב-DLL). מוגן: דגל MANUAL_FLATTEN_V1 (opt-in פר-מכונה,
    RULED) + body {"confirm":"FLATTEN"} מאישור-כפול בדף. כש-MOBILE_REMOTE_URL
    מוגדר — מועבר למכונת-המסחר, כך שהכפתור סוגר תמיד את מה שהמסך מציג."""
    import asyncio
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
        from backend.v9.services.sierra_command import write_trade_command
        write_trade_command(action="FLATTEN_ACCOUNT",
                            context={"source": "mobile_manual", "by": "michael"})
        return {"ok": True, "msg": "FLATTEN_ACCOUNT נשלח לסיירה"}
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
<div class="card"><div class="row"><span class="dim">סוג-יום</span><span id="dayconf" class="dim"></span></div>
<div style="font-size:20px;font-weight:700" id="daytype">—</div></div>
<div class="card"><div class="row"><span class="dim">למה לא יורה? (שער-הירי)</span><span id="gmeta" class="dim"></span></div>
<div id="gate" style="font-size:12px;line-height:1.6">—</div></div>
<div class="card"><div class="dim">תבניות — מי יורה, למה לא, ומה חוסם</div>
<div id="pats" style="font-size:11.5px;line-height:1.7">—</div></div>
<div class="card"><div class="dim">התראות</div><div id="alerts" class="alert">—</div></div>
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
daily_loss_halt:'עצירת הפסד-יומי',consecutive_loss_halt:'עצירת רצף-הפסדים',s4_risk_cap:'תקרת-סיכון S4',cluster_guard:'שומר-צבירה'};
async function load(){
 try{
  const r = await fetch('/api/v9/mobile/data',{cache:'no-store'}); const d = await r.json();
  document.getElementById('clock').textContent = d.ts + (d._src==='trading'? ' · 📡 מכונת-המסחר' : d._remote_err? ' · ⚠ מקומי (מכונת-המסחר לא-זמינה)' : '');
  const s = d.sierra||{}; const q = s.position_qty||0;
  document.getElementById('mode').textContent = (s.is_sim? 'סים':'אמת') + (s.order_placement_armed? ' · חמוש':' · לא-חמוש');
  const g = d.gate; const ge = document.getElementById('gate');
  if(g && g.last){
   const L = g.last; const t = L.ts? new Date(L.ts).toTimeString().slice(0,5) : '';
   ge.innerHTML = L.blocked_by? '⛔ '+t+' '+(L.pattern||'?')+' '+(L.direction||'')+' נחסם — <b>'+(GATE_HE[L.blocked_by]||L.blocked_by)+'</b>'
    : (L.outcome==='live'||L.outcome==='demo')? '<span class="green">🔫 '+t+' '+(L.pattern||'?')+' ירה ('+(L.outcome==='live'?'לייב':'דמו')+(L.trade_id?' #'+L.trade_id:'')+')</span>'
    : '👁 '+t+' '+(L.pattern||'?')+' עבר-שערים · צל-בלבד';
   document.getElementById('gmeta').textContent = g.attempts+' ניסיונות · '+g.fired+' ירו · '+g.blocked+' נחסמו';
  } else { ge.innerHTML = '<span class="dim">אף מועמד לא הגיע לשער מאז-הריסטארט — ראה פאנל-תבניות</span>'; document.getElementById('gmeta').textContent=''; }
  const ST_HE = {ready:['מוכן לירי','#3fb950'],armed:['חמוש','#3fb950'],fired:['ירה היום','#58a6ff'],
   building:['בהתהוות','#d29922'],blocked:['ממתין','#8b949e'],vetoed:['וטו','#f85149'],skip:['SKIP לסוג-היום','#f85149'],
   not_applicable:['לא-רלוונטי','#8b949e'],unknown:['?','#8b949e']};
  const P = d.patterns||[];
  document.getElementById('pats').innerHTML = P.length? P.map(p=>{
   const st = ST_HE[p.status]||ST_HE.unknown;
   let line = '';
   if(p.last){
    const t = p.last.ts? new Date(p.last.ts).toTimeString().slice(0,5) : '';
    line = p.last.blocked_by? '<div style="color:#f0883e;font-size:10.5px">⛔ '+t+' נחסם — '+(GATE_HE[p.last.blocked_by]||p.last.blocked_by)+'</div>'
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
  document.getElementById('active').innerHTML = a.length? a.map(t=>
   `<div class="row"><span>#${t.id} ${t.direction} ×${t.contracts} ${t.pattern||''} @${t.entry_price} <span class="dim">${t.t_in}</span></span>`+
   `<span class="${(t.upnl_usd||0)>=0?'green':'red'}">${t.upnl_usd!=null? (t.upnl_usd>=0?'+':'')+t.upnl_usd+'$':''}</span></div>`+
   `<div class="dim">סטופ ${t.stop??'—'} · T0 ${t.t0??'—'} · T1 ${t.t1??'—'} · T2 ${t.t2??'—'} · T3 ${t.t3??'—'}</div>`).join('')
   : '<span class="dim">אין עסקה פעילה</span>';
  const td = d.today||{}; const pnl = td.pnl??0;
  const de = document.getElementById('daypnl');
  de.textContent = (pnl>=0?'+':'')+Number(pnl).toFixed(0)+'$';
  de.className = 'big '+(pnl>=0?'green':'red');
  document.getElementById('daymeta').textContent = (td.n||0)+' עסקאות · '+(td.w||0)+' מנצחות';
  document.getElementById('cap').textContent = d.halt_cap;
  document.getElementById('daytype').textContent = d.day_type||'—';
  document.getElementById('dayconf').textContent = d.day_conf!=null? 'ביטחון '+d.day_conf : '';
  document.getElementById('alerts').innerHTML = (d.alerts&&d.alerts.length)? d.alerts.map(x=>'<div>'+x.replace(/</g,'&lt;').slice(0,110)+'</div>').join(''):'<span class="dim">שקט ✓</span>';
  document.getElementById('health').textContent = 'מחיר '+(d.mid??'—')+' · חוזים מוגדרים: '+d.contracts_cfg+' · רענון-5ש';
 }catch(e){ document.getElementById('health').textContent = '⚠ אין קשר למערכת — '+e; }
}
load(); setInterval(load, 5000);
document.getElementById('flat').onclick = async () => {
 if(!confirm('לסגור את כל עסקאות-האמת ולבטל את כל ההוראות?')) return;
 if(!confirm('אישור סופי — FLATTEN עכשיו?')) return;
 const b = document.getElementById('flat'); b.disabled = true; b.textContent = 'שולח...';
 try{
  const r = await fetch('/api/v9/mobile/flatten',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirm:'FLATTEN'})});
  const d = await r.json();
  b.textContent = d.ok? '✓ נשלח — בדוק פוזיציה' : '✗ '+(d.error||'נכשל');
 }catch(e){ b.textContent = '✗ אין קשר'; }
 setTimeout(()=>{ b.disabled=false; b.textContent='⏻ סגור עסקאות-אמת (השטח הכל)'; }, 6000);
};
</script></body></html>"""


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def mobile_page():
    return HTMLResponse(_PAGE)
