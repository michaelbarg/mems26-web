"""MEMS26 — Mobile Monitor + Emergency Command Relay (Render).

07-21 (Michael): "שהלינק לפלאפון יעבוד דרך Render — רק הוא, לא כל המערכת."
08-04 (Michael): "למקרי חירום שאני לא מול מסך" — FLATTEN + PAUSE from phone.

Standalone FastAPI service. NO database, NO trading, NO backend imports.
The Mac pushes a display snapshot (the output of the local /api/v9/mobile/data)
every ~5s via scripts/mobile_relay.py; this service keeps the LAST snapshot
in memory and serves the pocket page.

COMMAND RELAY (pull-based, Mac never exposes ports):
  POST /cmd {action: FLATTEN|PAUSE|RESUME} → stores in memory (queue=1, TTL 60s)
  GET  /cmd/pending → local relay polls this every 5s, executes locally, ACKs
  POST /cmd/ack → clears the queue after execution

Env (set in Render dashboard): MOBILE_ACCESS_KEY (page+cmd auth),
MOBILE_PUSH_KEY (snapshot push auth).
"""
import json
import os
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="mems26-mobile-relay")

_SNAP = {"data": None, "recv_ts": 0.0}

# ── Command relay state (in-memory, queue of 1, TTL 60s) ──
_CMD = {"pending": None, "ts": 0.0, "counter": 0}
_CMD_TTL = 60


def _page_key_ok(request: Request) -> bool:
    want = (os.getenv("MOBILE_ACCESS_KEY") or "").strip()
    if not want:
        return False
    got = (request.query_params.get("key")
           or request.headers.get("X-Mobile-Key") or "").strip()
    return got == want


@app.get("/healthz")
async def healthz():
    return {"ok": True, "has_snapshot": _SNAP["data"] is not None,
            "age_s": round(time.time() - _SNAP["recv_ts"], 1) if _SNAP["recv_ts"] else None}


@app.post("/api/v9/mobile/snapshot")
async def snapshot(request: Request):
    want = (os.getenv("MOBILE_PUSH_KEY") or "").strip()
    got = (request.headers.get("X-Push-Key") or "").strip()
    if not want or got != want:
        raise HTTPException(status_code=401, detail="push key required")
    try:
        body = await request.json()
        assert isinstance(body, dict)
    except Exception:
        raise HTTPException(status_code=400, detail="json body required")
    _SNAP["data"] = body
    _SNAP["recv_ts"] = time.time()
    return {"ok": True}


# ── Command relay endpoints ──

@app.post("/cmd")
async def post_cmd(request: Request):
    """Submit emergency command (FLATTEN/PAUSE/RESUME). Queue of 1, TTL 60s.
    Double-confirm in UI; auth required."""
    if not _page_key_ok(request):
        raise HTTPException(status_code=401, detail="auth required")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON body required")

    action = (body.get("action") or "").upper()
    _ok = action in ("FLATTEN", "PAUSE", "RESUME")
    # 2026-08-19 (Michael): phone gate-override — GATE_OFF:<gate> / GATE_ON:<gate>.
    # The relay forwards to the backend, which enforces the whitelist; here we
    # only sanity-check the shape.
    if not _ok and (action.startswith("GATE_OFF:") or action.startswith("GATE_ON:")):
        _g = action.split(":", 1)[1]
        _ok = 0 < len(_g) <= 40 and _g.replace("_", "").isalnum()
    if not _ok:
        raise HTTPException(status_code=400, detail=f"unknown action: {action}")

    _CMD["counter"] += 1
    _CMD["pending"] = {
        "action": action,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "id": _CMD["counter"],
    }
    _CMD["ts"] = time.monotonic()
    return {"ok": True, "cmd": _CMD["pending"]}


@app.get("/cmd/pending")
async def get_cmd_pending(request: Request):
    """Local relay polls this every 5s. Returns null if no pending command."""
    if not _page_key_ok(request):
        raise HTTPException(status_code=401, detail="auth required")

    if _CMD["pending"] is None:
        return {"cmd": None}

    # TTL check
    if time.monotonic() - _CMD["ts"] > _CMD_TTL:
        _CMD["pending"] = None
        return {"cmd": None, "expired": True}

    return {"cmd": _CMD["pending"]}


@app.post("/cmd/ack")
async def ack_cmd(request: Request):
    """Local relay ACKs after executing the command (clears queue)."""
    if not _page_key_ok(request):
        raise HTTPException(status_code=401, detail="auth required")
    try:
        body = await request.json()
    except Exception:
        body = {}

    cmd_id = body.get("id")
    if _CMD["pending"] and (cmd_id is None or cmd_id == _CMD["pending"].get("id")):
        _CMD["pending"] = None
        return {"ok": True, "cleared": True}
    return {"ok": True, "cleared": False}


# ── Instruction / Inbox relay (Phase 2 INBOX, 2026-08-26) ──
# Pull-based: Michael posts a text instruction from the phone app.
# The local relay polls /instruction/pending and writes to MICHAEL_INBOX.md.
# NOT a trading command — text for tracking only. No market operations.
_INBOX = {"items": [], "max_items": 50}


@app.post("/instruction")
async def post_instruction(request: Request):
    """Michael sends a text instruction from the phone. Stored for relay pickup."""
    if not _page_key_ok(request):
        raise HTTPException(status_code=401, detail="auth required")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON body required")
    text = (body.get("text") or "").strip()
    if not text or len(text) > 2000:
        raise HTTPException(status_code=400, detail="text required (max 2000 chars)")
    item = {
        "id": len(_INBOX["items"]) + 1,
        "text": text,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "received",  # received → in_progress → done
    }
    _INBOX["items"].append(item)
    if len(_INBOX["items"]) > _INBOX["max_items"]:
        _INBOX["items"] = _INBOX["items"][-_INBOX["max_items"]:]
    return {"ok": True, "item": item}


@app.get("/instruction/pending")
async def get_instructions_pending(request: Request):
    """Local relay polls: returns items with status != 'done'."""
    if not _page_key_ok(request):
        raise HTTPException(status_code=401, detail="auth required")
    pending = [i for i in _INBOX["items"] if i["status"] != "done"]
    return {"items": pending}


# Agent replies shown as a chat thread on the page (cowork/cc → Michael).
# In-memory like the inbox; the durable record is MICHAEL_INBOX.md in git.
_REPLIES = {"items": [], "max_items": 50}


@app.post("/reply")
async def post_reply(request: Request):
    """cowork/cc post a reply; the page shows it in the chat thread."""
    if not _page_key_ok(request):
        raise HTTPException(status_code=401, detail="auth required")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON body required")
    text = (body.get("text") or "").strip()
    sender = (body.get("sender") or "cowork").strip()[:20]
    if not text or len(text) > 2000:
        raise HTTPException(status_code=400, detail="text required (max 2000 chars)")
    item = {"sender": sender, "text": text,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
    _REPLIES["items"].append(item)
    if len(_REPLIES["items"]) > _REPLIES["max_items"]:
        _REPLIES["items"] = _REPLIES["items"][-_REPLIES["max_items"]:]
    return {"ok": True}


@app.get("/chat")
async def get_chat(request: Request):
    """The page polls this: merged thread of Michael's messages + agent replies."""
    if not _page_key_ok(request):
        raise HTTPException(status_code=401, detail="auth required")
    thread = (
        [{"sender": "מייקל", "text": i["text"], "ts": i["ts"],
          "status": i.get("status", "")} for i in _INBOX["items"]]
        + [{"sender": r["sender"], "text": r["text"], "ts": r["ts"], "status": ""}
           for r in _REPLIES["items"]]
    )
    thread.sort(key=lambda x: x["ts"])
    return {"items": thread[-30:]}


@app.post("/instruction/status")
async def update_instruction_status(request: Request):
    """Local relay updates an item's status (received→in_progress→done)."""
    if not _page_key_ok(request):
        raise HTTPException(status_code=401, detail="auth required")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON body required")
    item_id = body.get("id")
    new_status = body.get("status", "").lower()
    if new_status not in ("received", "in_progress", "done"):
        raise HTTPException(status_code=400, detail="status must be received/in_progress/done")
    for item in _INBOX["items"]:
        if item["id"] == item_id:
            item["status"] = new_status
            return {"ok": True, "item": item}
    raise HTTPException(status_code=404, detail="item not found")


@app.get("/api/v9/mobile/data")
async def mobile_data(request: Request):
    if not _page_key_ok(request):
        raise HTTPException(status_code=401, detail="mobile access key required")
    if _SNAP["data"] is None:
        return JSONResponse({"_relay": "empty",
                             "_relay_age_s": None,
                             "ts": time.strftime("%H:%M:%S")})
    out = dict(_SNAP["data"])
    out["_relay"] = "render"
    out["_relay_age_s"] = round(time.time() - _SNAP["recv_ts"], 1)
    return JSONResponse(out)


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
.stale{background:#2d1214;border:1px solid #f85149;color:#f85149;border-radius:10px;padding:8px 12px;margin-bottom:10px;font-size:13px;display:none}
</style></head><body>
<h1>⚡ MEMS26 · מוניטור-כיס <span id="machine" class="tag" style="background:#1f6feb;color:#fff"></span> <span id="clock" class="dim"></span></h1>
<div id="stale" class="stale">⚠ הנתונים מעופשים — המק לא דוחף עדכונים</div>
<div class="card" style="border:1px solid #1f6feb">
 <div class="row"><span class="dim">✉️ הנחיה לקלוד (cowork + cc)</span><span id="insStatus" class="dim"></span></div>
 <textarea id="insText" rows="2" placeholder="כתוב הנחיה או פסיקה... (למשל: מאשר 12)"
  style="width:100%;box-sizing:border-box;background:#0d1117;color:#e6edf3;border:1px solid #30363d;border-radius:6px;padding:8px;font-size:14px;margin-top:6px"></textarea>
 <button onclick="sendIns()" style="margin-top:6px;width:100%;padding:9px;background:#1f6feb;color:#fff;border:0;border-radius:6px;font-size:14px;font-weight:700">שלח הנחיה</button>
 <div id="chatThread" style="margin-top:8px;max-height:220px;overflow-y:auto;font-size:13px;line-height:1.5"></div>
 <script>
 async function loadChat(){
  try{
   const r=await fetch('/chat'+location.search); const d=await r.json();
   const el=document.getElementById('chatThread');
   if(!d.items||!d.items.length){el.innerHTML='<span style="color:#8b949e">אין הודעות עדיין</span>';return;}
   el.innerHTML=d.items.map(m=>{
    const me=m.sender==='מייקל';
    const t=(m.ts||'').slice(11,16);
    return '<div style="margin:4px 0;text-align:'+(me?'right':'left')+'">'
     +'<div style="display:inline-block;max-width:85%;padding:6px 10px;border-radius:10px;background:'
     +(me?'#1f6feb':'#21262d')+';color:#e6edf3;text-align:right">'
     +'<div style="font-size:11px;color:'+(me?'#c9d9f7':'#8b949e')+'">'+m.sender+' · '+t
     +(m.status==='done'?' · ✔':'')+'</div>'
     +m.text.replace(/</g,'&lt;')+'</div></div>';
   }).join('');
   el.scrollTop=el.scrollHeight;
  }catch(e){}
 }
 loadChat(); setInterval(loadChat, 10000);
 </script>
 <script>
 async function sendIns(){
  const t=document.getElementById('insText'), st=document.getElementById('insStatus');
  const txt=(t.value||'').trim(); if(!txt){st.textContent='✗ ריק';return;}
  st.textContent='שולח...';
  try{
   const r=await fetch('/instruction'+location.search,{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({text:txt})});
   const d=await r.json();
   if(d.ok||d.id!=null){st.textContent='✓ נשלח — המק ימשוך תוך ~דקה';st.style.color='#3fb950';t.value='';}
   else{st.textContent='✗ '+(d.error||d.detail||'נכשל');st.style.color='#f85149';}
  }catch(e){st.textContent='✗ '+e;st.style.color='#f85149';}
  setTimeout(()=>{st.textContent='';st.style.color='';},10000);
 }
 </script>
</div>
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
<div class="card"><div class="dim">מערכת 6 — פעילות אחרונה</div><div id="s6act" style="font-size:12px;line-height:1.6">—</div></div>
<div class="card"><div class="dim">התראות</div><div id="alerts" class="alert">—</div></div>
<div id="pausedBanner" style="display:none;background:#f85149;color:#fff;text-align:center;padding:10px;border-radius:12px;margin-bottom:10px;font-size:16px;font-weight:800">PAUSED — shadow only</div>
<button id="pauseBtn" style="width:100%;padding:14px;margin:4px 0;border-radius:12px;border:2px solid #d29922;background:#2d2614;color:#d29922;font-size:16px;font-weight:700;font-family:inherit;cursor:pointer">⏸ השהה מסחר (צל-בלבד)</button>
<button id="flatBtn" style="width:100%;padding:14px;margin:4px 0;border-radius:12px;border:2px solid #f85149;background:#2d1214;color:#f85149;font-size:16px;font-weight:700;font-family:inherit;cursor:pointer">⏻ סגור עסקאות-אמת (FLATTEN)</button>
<div id="cmdStatus" class="dim" style="text-align:center;min-height:18px;margin:4px 0 8px"></div>
<div class="dim" id="health" style="text-align:center"></div>
<script>
const Q = location.search || '';
const GATE_HE = {kill_switch:'מתג-חירום',session_gate_closed:'מחוץ לחלון-מסחר',eod_entry_cutoff:'סוף-יום',
feed_watchdog:'פיד תקוע',cooldown:'צינון',suffering_side_veto:'וטו צד-סובל',duplicate_fire:'ירי-כפול',
chop_searching:'שוק-קופצני',opening_type_gate:'שער סוג-פתיחה',daytype_playbook:'פלייבוק סוג-יום',
trend_direction_gate:'כיוון-מגמה',reactive_location:'מיקום ריאקטיבי',location_gate:'שער-מיקום (דלתון)',
daytype_position_gate:'משפחה×סוג-יום',cont_trend_filter:'המשך-עם-מגמה',direction_context:'הקשר-כיוון',
lsma_flat:'LSMA שטוח',news_blackout:'חלון-חדשות',day_direction_doctrine:'דוקטרינת-כיוון',
entry_not_confirmed:'אין אישור-כניסה',t1_wrong_side:'T1 בצד שגוי',rr_entry_gate:'שער R:R',
daily_loss_halt:'עצירת הפסד-יומי',consecutive_loss_halt:'עצירת רצף-הפסדים',s4_risk_cap:'תקרת-סיכון S4',pattern_loss_breaker:'מפסק-הפסדים (תבנית)',cluster_guard:'שומר-צבירה',
cold_start_guard:'אתחול-קר',structural_targets_wrong_side:'יעדים בצד-שגוי',rr_hard_floor:'רצפת R:R',awaiting_release:'ממתין לשחרור-אזור',extreme_chase_guard:'רדיפת-קיצון',
drive_exhaustion_veto:'תשישות-דרייב',pattern_stop_cooldown:'צינון אחרי-סטופ',zone_limit_late_entry:'איחור לאזור',strict_risk:'בדיקת-סיכון-לייב',
pre_send_entry_guard:'שומר קדם-שיגור (פוזיציה-עומדת)',margin_zero_size:'אין מרג׳ין',live_slot_occupied:'עסקה-חיה פתוחה',place_refused:'PLACE נדחה'};
const GATE_WHY={lsma_flat:'אין שיפוע-מגמה (LSMA שטוח) — כניסות-המשך חלשות; רגל-חיה עוקפת',extreme_chase_guard:'הכניסה רודפת קיצון-סשן טרי — סיכון-היפוך; רגל-חיה עוקפת',awaiting_release:'המחיר עוד באזור-הקיצון — מחכים לשחרור מבני (שפלים-עולים + נפח מתייבש)',daytype_playbook:'סוג-היום לא מרשה את משפחת-התבנית הזו',cont_trend_filter:'כניסת-המשך בלי מגמה מבוססת דיה',direction_context:'הכיוון מנוגד ל-bias של היום',rr_entry_gate:'סיכוי/סיכון לרוטציה מתחת 0.65',rr_hard_floor:'R:R מתחת לרצפה 0.3',pattern_stop_cooldown:'אותה תבנית נעצרה בסטופ ב-30 הדק׳ האחרונות',location_gate:'מיקום-הכניסה לא מתאים לסוג-היום (דלתון)',entry_not_confirmed:'אין בר-אישור בכיוון אחרי האיתות',cold_start_guard:'המערכת עלתה הרגע — ממתינה ל-3 ברים',eod_entry_cutoff:'45 דק׳ אחרונות — אין כניסות חדשות',daily_loss_halt:'הפסד-יומי ממומש מעל התקרה — נעצר יום',pre_send_entry_guard:'החשבון מחזיק פוזיציה שלא-בספרים — לא יורים מעליה',margin_zero_size:'אין מרג׳ין פנוי אפילו לחוזה אחד',live_slot_occupied:'עסקה חיה פתוחה — אחת בכל רגע',strict_risk:'בדיקת-סיכון-לייב (שעת-חיתוך/תקרות) עצרה'};
async function load(){
 try{
  const r = await fetch('/api/v9/mobile/data'+Q,{cache:'no-store'}); const d = await r.json();
  const age = d._relay_age_s;
  // 14.08 (Michael): distinguish "idle by design" from "something is broken",
  // and always say WHEN live data resumes.
  const el = document.getElementById('stale');
  if (d.relay_idle) {
    el.style.background = '#2d2614'; el.style.borderColor = '#d29922'; el.style.color = '#d29922';
    el.textContent = '⏸ ' + (d.relay_note || ('ממסר במנוחה — נתונים חיים בחלון ' + (d.relay_window_il || '')));
    el.style.display = 'block';
  } else if (age == null || age > 30) {
    el.style.background = '#2d1214'; el.style.borderColor = '#f85149'; el.style.color = '#f85149';
    el.textContent = '⚠ הנתונים מעופשים (' + (age==null? 'אין נתונים' : Math.round(age)+'ש') +
                     ') — המק לא דוחף עדכונים' + (d.relay_window_il? ' · חלון-דחיפה '+d.relay_window_il : '');
    el.style.display = 'block';
  } else {
    el.style.display = 'none';
  }
  if (d.relay_idle) return;  // no trading data in an idle notice
  document.getElementById('clock').textContent = (d.ts||'') + ' · ☁ Render' + (age!=null? ' · עדכון לפני '+Math.round(age)+'ש':'');
  if(d._relay==='empty'){ document.getElementById('health').textContent='ממתין ל-snapshot ראשון מהמק...'; return; }
  const s = d.sierra||{}; const q = s.position_qty||0;
  document.getElementById('mode').textContent = (s.is_sim? 'סים':'אמת') + (s.order_placement_armed? ' · חמוש':' · לא-חמוש');
  if (d.machine) document.getElementById('machine').textContent = d.machine;
  // ── חשבון (Account Monitor, מה-snapshot) ──
  const $$ = (v,pfx)=> v==null? '—' : (pfx&&v>=0?'+':'')+Number(v).toFixed(2)+'$';
  const cls = v => v==null?'dim':(v>=0?'green':'red');
  document.getElementById('acct_val').textContent = $$(s.acct_account_value);
  const ad=document.getElementById('acct_day'); ad.textContent=$$(s.acct_daily_pl,1); ad.className=cls(s.acct_daily_pl);
  const ao=document.getElementById('acct_open'); ao.textContent=$$(s.acct_open_positions_pl,1); ao.className=cls(s.acct_open_positions_pl);
  document.getElementById('acct_avail').textContent = $$(s.acct_available_funds);
  document.getElementById('acctmeta').textContent = s.acct_trading_disabled? '🔴 מסחר-מושבת' : s.acct_loss_limit_reached? '🔴 תקרת-הפסד' : '';
  // ── רדאר (מה-snapshot — אותו מקור כמו המסך) ──
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
  } else { rEl.innerHTML='<span class="dim">רדאר לא-זמין ב-snapshot</span>'; }
  const g = d.gate; const ge = document.getElementById('gate');
  if(g && g.last){
   const L = g.last; const t = L.ts? new Date(L.ts).toTimeString().slice(0,5) : '';
   ge.innerHTML = L.blocked_by? '⛔ '+t+' '+(L.pattern||'?')+' '+(L.direction||'')+' נחסם — <b>'+(GATE_HE[L.blocked_by]||L.blocked_by)+'</b>'
    : (L.outcome==='live'||L.outcome==='demo')? '<span class="green">🔫 '+t+' '+(L.pattern||'?')+' ירה ('+(L.outcome==='live'?'לייב':'דמו')+(L.trade_id?' #'+L.trade_id:'')+')</span>'
    : '👁 '+t+' '+(L.pattern||'?')+' עבר-שערים · צל-בלבד';
   if(!L.blocked_by && L.live_blocked_by) ge.innerHTML += '<div style="color:#f0883e;font-size:11px">⛔ הלייב לא-שוגר: <b>'+(GATE_HE[L.live_blocked_by]||L.live_blocked_by)+'</b>'+(L.live_block_reason?' — '+String(L.live_block_reason).replace(/</g,'&lt;').slice(0,70):'')+'</div>';
   if(L.blocked_by && (d.gate_overridable||[]).includes(L.blocked_by)) ge.innerHTML += ' <button onclick="gateOv(\\''+L.blocked_by+'\\',false)" style="padding:3px 10px;border-radius:8px;border:1px solid #d29922;background:#2d2614;color:#d29922;font-size:11px;font-family:inherit">🔓 בטל חוסם זה (עד-ריסטארט)</button>';
   document.getElementById('gmeta').textContent = g.attempts+' ניסיונות · '+g.fired+' ירו · '+g.blocked+' נחסמו';
  } else { ge.innerHTML = '<span class="dim">אף מועמד לא הגיע לשער מאז-הריסטארט</span>'; document.getElementById('gmeta').textContent=''; }
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
    const _why = p.last.blocked_by && GATE_WHY[p.last.blocked_by]? '<div class="dim" style="font-size:10px;padding-right:12px">↳ '+GATE_WHY[p.last.blocked_by]+'</div>':'';
    line = p.last.blocked_by? '<div style="color:#f0883e;font-size:10.5px">⛔ '+t+' נחסם — '+(GATE_HE[p.last.blocked_by]||p.last.blocked_by)+_ob+'</div>'+_why
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
  // 2026-08-19 (Michael): the cloud page showed levels only — now the same
  // per-contract bars + movement block the local page has.
  const a = d.active||[];
  document.getElementById('active').innerHTML = a.length? a.map(t=>{
   const legs=t.legs||[]; const SC={'OPEN':'#d29922','HIT_TARGET':'#3fb950','HIT_STOP':'#f85149'};
   const SL={'OPEN':'פתוח','HIT_TARGET':'✓ מילוי','HIT_STOP':'✗ סטופ'};
   const rows=legs.map(c=>{
    let bar='';
    if(c.status==='OPEN'&&c.pct!=null){const w=Math.min(Math.abs(c.pct),100);
     bar=`<div style="background:#21262d;border-radius:3px;height:5px;margin:2px 0"><div style="background:${c.pct>=0?'#3fb950':'#f85149'};width:${w}%;height:100%;border-radius:3px"></div></div>`;}
    return `<div style="border-bottom:1px solid #1c2330;padding:2px 0"><div class="row">`+
     `<span class="dim" style="width:22px">${c.id}</span><span style="font-family:monospace;font-size:11px">${c.target?c.target.toFixed(2):'—'}</span>`+
     `<span style="font-size:10px;color:${SC[c.status]||'#8b949e'}">${SL[c.status]||c.status}${c.be?' ⇄BE':''}</span>`+
     `<span class="${c.pnl>=0?'green':'red'}" style="font-family:monospace;font-size:11px">${c.pnl>=0?'+':''}${c.pnl}$</span>`+
     `<span style="font-size:10.5px" class="${(c.pct||0)>=0?'green':'red'}">${c.pct!=null?(c.pct>0?'+':'')+c.pct+'%':''}</span></div>${bar}</div>`;
   }).join('');
   const mv=t.move_pts!=null?`<div class="row" style="font-size:11.5px"><span class="dim">תזוזה</span><span class="${t.move_pts>=0?'green':'red'}">${t.move_pts>0?'+':''}${t.move_pts} נק׳${t.mae_pts!=null?' · הכי-נגד '+t.mae_pts:''}${t.mfe_pts!=null?' · הכי-בעד '+t.mfe_pts:''}</span></div>`:'';
   const sp=t.stop_pct!=null?`<div class="row" style="font-size:11.5px"><span class="dim">מהדרך לסטופ</span><span class="${t.stop_pct>=50?'red':'dim'}" style="font-weight:700">${Math.max(t.stop_pct,0)}%</span></div>`:'';
   const nt=t.next_target_pct!=null?`<div class="row" style="font-size:11.5px"><span class="dim">ליעד הבא ${t.next_target??''}</span><span class="${t.next_target_pct>=0?'green':'red'}" style="font-weight:700">${t.next_target_pct>0?'+':''}${t.next_target_pct}%</span></div>`:'';
   const tp=t.total_pnl??t.upnl_usd;
   return `<div class="row"><span>#${t.id} ${t.direction} ×${legs.length||t.contracts} ${t.pattern||''} @${t.entry_price} <span class="dim">${t.t_in}</span></span>`+
    `<span class="${(tp||0)>=0?'green':'red'}" style="font-weight:800">${tp!=null?(tp>=0?'+':'')+tp+'$':''}</span></div>`+
    `<div class="dim" style="font-size:11px">סטופ ${t.stop??'—'} · ${t.summary||''}</div>`+mv+sp+nt+
    (rows?`<div style="margin-top:4px">${rows}</div>`:`<div class="dim">T0 ${t.t0??'—'} · T1 ${t.t1??'—'} · T2 ${t.t2??'—'} · T3 ${t.t3??'—'}</div>`);
  }).join('<div style="height:8px"></div>')
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
  // S6 activity panel
  const S6_HE = {SMART_BE:'סטופ→BE',DROP_TARGET:'יעד הוסר',TARGET_REALISM:'יעד תוקן',TRAIL:'טרייל',STRUCT_TRAIL:'טרייל-מבני',STOP_MOVE:'סטופ הוזז',STOP_AFTER_T2:'סטופ-T2'};
  const s6 = d.s6_activity||[];
  document.getElementById('s6act').innerHTML = s6.length? s6.map(e=>{
   const act = S6_HE[e.action]||e.action;
   const v = e.value||{};
   let det = '';
   if(v.from!=null&&v.to!=null) det = ' '+v.from+'→'+v.to;
   return '<div class="row"><span>'+e.t+' #'+e.trade_id+' '+e.direction+'</span><span style="color:#58a6ff">'+act+det+'</span></div>';
  }).join('') : '<span class="dim">אין פעילות S6 ב-24ש האחרונות</span>';
  document.getElementById('alerts').innerHTML = (d.alerts&&d.alerts.length)? d.alerts.map(x=>'<div>'+x.replace(/</g,'&lt;').slice(0,110)+'</div>').join(''):'<span class="dim">שקט ✓</span>';
  document.getElementById('health').textContent = 'מחיר '+(d.mid??'—')+' · חוזים מוגדרים: '+d.contracts_cfg+' · רענון-5ש · ☁';
 }catch(e){ document.getElementById('health').textContent = '⚠ אין קשר לענן — '+e; }
}
load(); setInterval(load, 5000);
async function gateOv(g,restore){
 if(!confirm((restore?'להחזיר את החוסם ':'לבטל את החוסם ')+g+'?')) return;
 if(!restore && !confirm('אישור סופי — ביטול עד-ריסטארט של '+g+'? עסקאות שהשער הזה היה עוצר יעברו.')) return;
 const st=document.getElementById('cmdStatus'); st.textContent='שולח...';
 try{const r=await fetch('/cmd'+Q,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:(restore?'GATE_ON:':'GATE_OFF:')+g})});
  const d=await r.json(); st.textContent=d.ok?'✓ נשלח — המק יבצע תוך ~5ש':'✗ '+(d.error||'נכשל'); st.style.color=d.ok?'#3fb950':'#f85149';
 }catch(e){st.textContent='✗ '+e;st.style.color='#f85149';}
 setTimeout(()=>{st.textContent='';st.style.color='';},8000);
}
let _paused=false;
function updatePause(p){
 _paused=p; document.getElementById('pausedBanner').style.display=p?'block':'none';
 const b=document.getElementById('pauseBtn');
 if(p){b.textContent='▶ חדש מסחר (RESUME)';b.style.borderColor='#3fb950';b.style.color='#3fb950';b.style.background='#0d2818';}
 else{b.textContent='⏸ השהה מסחר (צל-בלבד)';b.style.borderColor='#d29922';b.style.color='#d29922';b.style.background='#2d2614';}
}
async function sendCmd(action){
 const msg={FLATTEN:'לסגור את כל הפוזיציות?',PAUSE:'להשהות מסחר? כניסות חדשות → צל-בלבד.',RESUME:'לחדש מסחר רגיל?'}[action];
 if(!confirm(msg)) return;
 if(!confirm('אישור סופי — '+action+'?')) return;
 const st=document.getElementById('cmdStatus'); st.textContent='שולח...';
 try{
  const r=await fetch('/cmd'+Q,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:action})});
  const d=await r.json();
  st.textContent=d.ok?'✓ פקודה נשלחה — ממתין לביצוע (עד 10s)':'✗ '+(d.error||'failed');
  st.style.color=d.ok?'#3fb950':'#f85149';
 }catch(e){st.textContent='✗ '+e;st.style.color='#f85149';}
 setTimeout(()=>{st.textContent='';st.style.color='';},8000);
}
document.getElementById('pauseBtn').onclick=()=>sendCmd(_paused?'RESUME':'PAUSE');
document.getElementById('flatBtn').onclick=()=>sendCmd('FLATTEN');
</script></body></html>"""


@app.get("/api/v9/mobile", response_class=HTMLResponse)
@app.get("/api/v9/mobile/", response_class=HTMLResponse)
@app.get("/", response_class=HTMLResponse)
async def mobile_page(request: Request):
    if not _page_key_ok(request):
        return HTMLResponse(
            "<html dir=rtl><body style='background:#0b0e14;color:#e6edf3;"
            "font-family:-apple-system;padding:40px;text-align:center'>"
            "<h2>🔒 נדרש מפתח-גישה</h2><p>הוסף <code>?key=…</code> לכתובת.</p>"
            "</body></html>", status_code=401)
    return HTMLResponse(_PAGE)
