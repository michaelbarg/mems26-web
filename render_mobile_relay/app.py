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
from fastapi.responses import HTMLResponse, JSONResponse, Response

app = FastAPI(title="mems26-mobile-relay")

_SNAP = {"data": None, "recv_ts": 0.0}

# ── Command relay state (in-memory, queue of 1, TTL 60s) ──
_CMD = {"pending": None, "ts": 0.0, "counter": 0}
_CMD_TTL = 60

# ── Session series for the pocket chart (Michael 31.08: "גרף קטן פה") ──
# Built HERE, from the snapshots the Mac already pushes every ~5s. No Mac-side
# change, no backend restart, no new data path. In-memory only: it resets on a
# Render cold start, and the page says so rather than pretending otherwise.
# P&L is today.pnl (the system's own closed trades from v9_trades) — NOT
# sierra.daily_pnl, which is mixed on the shared account 37138283.
_SERIES = {"day": None, "pts": []}   # pts: [epoch_s, price, pnl, n_trades]
_SERIES_MAX = 500       # ~4h at one point per 30s
_SERIES_GAP_S = 30      # normal sampling gap; a P&L change samples immediately


def _series_add(body: dict) -> None:
    """Append one sample. Never raises — a bad snapshot must not break /snapshot."""
    try:
        day = time.strftime("%Y-%m-%d", time.gmtime())
        if _SERIES["day"] != day:
            _SERIES["day"] = day
            _SERIES["pts"] = []
        price = (body.get("sierra") or {}).get("last_price")
        today = body.get("today") or {}
        pnl = today.get("pnl")
        n = today.get("n") or 0
        if price is None:
            return
        price = round(float(price), 2)
        pnl = round(float(pnl), 2) if pnl is not None else 0.0
        now = time.time()
        pts = _SERIES["pts"]
        if pts:
            last = pts[-1]
            pnl_changed = (last[2] != pnl) or (last[3] != n)
            if not pnl_changed and (now - last[0]) < _SERIES_GAP_S:
                return
        pts.append([int(now), price, pnl, int(n)])
        if len(pts) > _SERIES_MAX:
            del pts[:len(pts) - _SERIES_MAX]
    except Exception:
        pass


def _series_out(limit: int = 110) -> list:
    """Downsample to <= limit points so the mobile payload stays small."""
    pts = _SERIES["pts"]
    if len(pts) <= limit:
        return pts
    step = len(pts) / float(limit)
    out = [pts[int(i * step)] for i in range(limit)]
    out[-1] = pts[-1]   # always keep the freshest point
    return out


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
    _series_add(body)
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
    import uuid
    item = {
        "id": str(uuid.uuid4())[:8],  # stable across deploy restarts
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


# Durable thread pushed by the Mac every cycle (survives Render deploys —
# the source of truth is docs/handoff/PHONE_THREAD.jsonl on the Mac).
_PUSHED_THREAD = {"items": []}


@app.post("/chat_push")
async def chat_push(request: Request):
    want = (os.getenv("MOBILE_PUSH_KEY") or "").strip()
    got = (request.headers.get("X-Push-Key") or "").strip()
    if not want or got != want:
        raise HTTPException(status_code=401, detail="push key required")
    try:
        body = await request.json()
        items = body.get("items") or []
        assert isinstance(items, list)
    except Exception:
        raise HTTPException(status_code=400, detail="json items required")
    _PUSHED_THREAD["items"] = items[-30:]
    return {"ok": True, "n": len(_PUSHED_THREAD["items"])}


@app.get("/chat")
async def get_chat(request: Request):
    """The page polls this: merged thread of Michael's messages + agent replies."""
    if not _page_key_ok(request):
        raise HTTPException(status_code=401, detail="auth required")
    thread = (
        list(_PUSHED_THREAD["items"])  # durable, pushed by the Mac — survives deploys
        + [{"sender": "מייקל", "text": i["text"], "ts": i["ts"],
            "status": i.get("status", "")} for i in _INBOX["items"]]
        + [{"sender": r["sender"], "text": r["text"], "ts": r["ts"], "status": ""}
           for r in _REPLIES["items"]]
        # uploads not yet echoed back by the Mac push (text must equal the
        # relay-written line so the dedup below collapses them once pulled)
        + [{"sender": "מייקל",
            "text": "📎 " + u["name"] + ((" — " + u["note"]) if u["note"] else ""),
            "ts": u["ts"],
            "status": "התקבל ✓" if u["status"] == "done" else "ממתין למשיכה למק...",
            "att": {"id": u["id"], "name": u["name"], "mime": u["mime"],
                    "size": u["size"]}}
           for u in _UPLOADS["items"]]
    )
    seen, dedup = set(), []
    for m in thread:
        k = (m.get("sender"), m.get("text"), (m.get("ts") or "")[:16])
        if k not in seen:
            seen.add(k)
            dedup.append(m)
    dedup.sort(key=lambda x: x.get("ts") or "")
    return {"items": dedup[-30:]}


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


# ── File/image upload from the phone (Michael 28.08, id 45f1231e:
# "תוסיף אפשרות להעלות קבצים ותמונות לצ'אט כאן") ──
# Pull-based like instructions: the page POSTs raw bytes (no multipart — keeps
# requirements.txt unchanged) → kept in memory → the Mac relay polls
# /upload/pending, downloads /upload/file/<id>, stores durably under
# docs/handoff/phone_uploads/ + appends a thread line (agents open the file
# locally), then ACKs /upload/status=done. Bytes stay here (size-capped LRU)
# only so the page can render the image; a deploy wipes them — the durable
# copy is on the Mac.
_UPLOADS = {"items": [], "max_items": 10,
            "max_bytes": 8 * 1024 * 1024, "max_total": 24 * 1024 * 1024}


def _safe_name(name: str) -> str:
    name = os.path.basename((name or "file").strip())[:80]
    return "".join(c for c in name if c.isalnum() or c in "._- ") or "file"


@app.post("/upload")
async def post_upload(request: Request):
    """Michael uploads a file/photo from the phone (raw body, name in query)."""
    if not _page_key_ok(request):
        raise HTTPException(status_code=401, detail="auth required")
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="empty body")
    if len(data) > _UPLOADS["max_bytes"]:
        raise HTTPException(status_code=413, detail="file too large (max 8MB)")
    import uuid
    item = {
        "id": str(uuid.uuid4())[:8],
        "name": _safe_name(request.query_params.get("name") or "file"),
        "mime": (request.headers.get("Content-Type")
                 or "application/octet-stream").split(";")[0].strip(),
        "size": len(data), "data": data,
        "note": (request.query_params.get("note") or "").strip()[:500],
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "received",  # received → done (pulled to the Mac)
    }
    _UPLOADS["items"].append(item)
    while (len(_UPLOADS["items"]) > _UPLOADS["max_items"]
           or sum(len(i["data"]) for i in _UPLOADS["items"]) > _UPLOADS["max_total"]):
        _UPLOADS["items"].pop(0)
    return {"ok": True, "id": item["id"], "name": item["name"], "size": item["size"]}


@app.get("/upload/pending")
async def upload_pending(request: Request):
    """Local relay polls: metadata of items not yet pulled to the Mac."""
    if not _page_key_ok(request):
        raise HTTPException(status_code=401, detail="auth required")
    return {"items": [{"id": i["id"], "name": i["name"], "mime": i["mime"],
                       "size": i["size"], "ts": i["ts"], "note": i["note"]}
                      for i in _UPLOADS["items"] if i["status"] != "done"]}


@app.get("/upload/file/{uid}")
async def upload_file(uid: str, request: Request):
    """Bytes — used by the relay to download AND by the page to render."""
    if not _page_key_ok(request):
        raise HTTPException(status_code=401, detail="auth required")
    for i in _UPLOADS["items"]:
        if i["id"] == uid:
            # headers are latin-1 — Hebrew names need RFC 5987 (filename*=)
            from urllib.parse import quote
            ascii_name = (i["name"].encode("ascii", "ignore").decode()
                          .strip() or "file")
            return Response(
                content=i["data"],
                media_type=i["mime"] or "application/octet-stream",
                headers={"Content-Disposition":
                         'inline; filename="%s"; filename*=UTF-8\'\'%s'
                         % (ascii_name, quote(i["name"]))})
    raise HTTPException(status_code=404,
                        detail="not on Render (deploy wiped memory); durable copy is on the Mac")


@app.post("/upload/status")
async def upload_status(request: Request):
    """Local relay marks an upload done after storing it durably."""
    if not _page_key_ok(request):
        raise HTTPException(status_code=401, detail="auth required")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON body required")
    for i in _UPLOADS["items"]:
        if i["id"] == body.get("id"):
            i["status"] = "done"
            return {"ok": True}
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
    out["_series"] = _series_out()
    return JSONResponse(out)


_PAGE = """<!DOCTYPE html><html lang="he" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>MEMS26 · מוניטור</title><style>
html{height:auto;overflow-y:auto}
body{margin:0;background:#0b0e14;color:#e6edf3;font-family:-apple-system,'Segoe UI',sans-serif;padding:14px 12px 90px;height:auto;min-height:100%;overflow-y:auto;-webkit-overflow-scrolling:touch}
h1{font-size:16px;margin:0 0 10px;color:#79c0ff}.card{background:#151a23;border:1px solid #2a3140;border-radius:12px;padding:12px;margin-bottom:10px}
.big{font-size:28px;font-weight:800}.green{color:#3fb950}.red{color:#f85149}.dim{color:#8b949e;font-size:12px}
.row{display:flex;justify-content:space-between;align-items:baseline;margin:3px 0}.tag{font-size:11px;padding:1px 7px;border-radius:6px;background:#21262d}
.alert{color:#f0883e;font-size:12px;line-height:1.5}.pulse{animation:p 2s infinite}@keyframes p{50%{opacity:.4}}
/* 29.08: ב-RTL הסימן המוביל של מספר שלילי נזרק לצד השני ("-62.50$" נראה
   "62.50$-"), כך שרווח והפסד נבדלו בצבע בלבד. .num מבודד את המספר ל-LTR. */
.num{direction:ltr;unicode-bidi:isolate;display:inline-block}
.stale{background:#2d1214;border:1px solid #f85149;color:#f85149;border-radius:10px;padding:8px 12px;margin-bottom:10px;font-size:13px;display:none}
</style></head><body>
<h1>⚡ MEMS26 · מוניטור-כיס <span id="machine" class="tag" style="background:#1f6feb;color:#fff"></span> <span id="clock" class="dim"></span>
 <a id="readyLink" href="/readiness" class="tag" style="color:#79c0ff;text-decoration:none;font-weight:600;white-space:nowrap">📋 תיק-מוכנות</a></h1>
<div id="stale" class="stale">⚠ הנתונים מעופשים — המק לא דוחף עדכונים</div>
<div class="card" style="border:1px solid #1f6feb">
 <div class="row"><span class="dim">✉️ הנחיה לקלוד (cowork + cc)</span><span id="insStatus" class="dim"></span></div>
 <textarea id="insText" rows="2" placeholder="כתוב הנחיה או פסיקה... (למשל: מאשר 12)"
  style="width:100%;box-sizing:border-box;background:#0d1117;color:#e6edf3;border:1px solid #30363d;border-radius:6px;padding:8px;font-size:14px;margin-top:6px"></textarea>
 <button onclick="sendIns()" style="margin-top:6px;width:100%;min-height:44px;padding:12px;background:#1f6feb;color:#fff;border:0;border-radius:6px;font-size:14px;font-weight:700">שלח הנחיה</button>
 <input type="file" id="insFile" style="display:none" onchange="if(this.files[0])sendFile(this.files[0]);this.value='';">
 <button onclick="document.getElementById('insFile').click()" style="margin-top:6px;width:100%;min-height:44px;padding:11px 8px;background:#21262d;color:#79c0ff;border:1px solid #30363d;border-radius:6px;font-size:13px">📎 צרף קובץ / תמונה (עד 8MB; טקסט בתיבה = כיתוב)</button>
 <details open style="margin-top:8px">
 <summary style="font-size:11px;color:#8b949e;cursor:pointer">💬 צ'אט עם הסוכנים (הקש לקיפול) — כל הודעה מגיעה לשניהם: cowork (מתכנן) ו-cc (מבצע). "התקבל ✓" = על ה-Mac.</summary>
 <div id="chatThread" style="margin-top:8px;max-height:240px;overflow-y:auto;overscroll-behavior:contain;font-size:13px;line-height:1.5"></div>
 </details>
 <script>
 function attErr(el){
  var d=document.createElement('div');
  d.style.cssText='font-size:11px;color:#8b949e';
  d.textContent='📎 הקובץ נשמר על ה-Mac (תצוגת-הענן פגה)';
  var box=el.parentNode.parentNode; box.replaceChild(d,el.parentNode);
 }
 function copyMsg(i,btn){
  const txt=(window._chatTexts||[])[i]||'';
  const ok=function(){btn.textContent='✓';setTimeout(function(){btn.textContent='📋';},1200);};
  if(navigator.clipboard&&navigator.clipboard.writeText){
   navigator.clipboard.writeText(txt).then(ok).catch(function(){legacyCopy(txt);ok();});
  }else{legacyCopy(txt);ok();}
 }
 function legacyCopy(txt){
  var ta=document.createElement('textarea');ta.value=txt;
  ta.style.cssText='position:fixed;opacity:0';document.body.appendChild(ta);
  ta.focus();ta.select();try{document.execCommand('copy');}catch(e){}
  document.body.removeChild(ta);
 }
 async function loadChat(){
  try{
   const r=await fetch('/chat'+location.search); const d=await r.json();
   const el=document.getElementById('chatThread');
   if(!d.items||!d.items.length){el.innerHTML='<span style="color:#8b949e">אין הודעות עדיין</span>';return;}
   window._chatTexts=d.items.map(m=>m.text||'');
   el.innerHTML=d.items.map((m,i)=>{
    const me=m.sender==='מייקל';
    let t=(m.ts||'').slice(11,16);
    try{t=new Date(m.ts).toLocaleTimeString('he-IL',{timeZone:'Asia/Jerusalem',hour:'2-digit',minute:'2-digit'});}catch(e){}
    let att='';
    if(m.att&&m.att.id){
     const u='/upload/file/'+m.att.id+location.search;
     if((m.att.mime||'').indexOf('image/')===0){
      att='<div style="margin-top:4px"><a href="'+u+'" target="_blank">'
       +'<img src="'+u+'" loading="lazy" onerror="attErr(this)" '
       +'style="max-width:100%;max-height:180px;border-radius:8px"></a></div>';
     }else{
      att='<div style="margin-top:4px"><a href="'+u+'" target="_blank" style="color:#79c0ff">📄 '
       +String(m.att.name||'קובץ').replace(/</g,'&lt;')+'</a>'
       +'<span style="font-size:10px;color:#8b949e"> ('+Math.max(1,Math.round((m.att.size||0)/1024))+'KB)</span></div>';
     }
    }
    return '<div style="margin:4px 0;text-align:'+(me?'right':'left')+'">'
     +'<div style="display:inline-block;max-width:85%;padding:6px 10px;border-radius:10px;background:'
     +(me?'#1f6feb':'#21262d')+';color:#e6edf3;text-align:right">'
     +'<div style="font-size:11px;color:'+(me?'#c9d9f7':'#8b949e')+'">'+m.sender+' · '+t
     +(m.status?' · '+m.status:'')
     +' <span onclick="copyMsg('+i+',this)" title="העתק הודעה" '
     +'style="cursor:pointer;padding:0 4px;font-size:12px">📋</span></div>'
     +m.text.replace(/</g,'&lt;')+att+'</div></div>';
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
 async function sendFile(f){
  const st=document.getElementById('insStatus');
  if(f.size>8*1024*1024){st.textContent='✗ גדול מ-8MB';st.style.color='#f85149';return;}
  st.textContent='מעלה '+f.name+'...';st.style.color='';
  try{
   const note=(document.getElementById('insText').value||'').trim();
   const u='/upload'+location.search+'&name='+encodeURIComponent(f.name)
    +(note?'&note='+encodeURIComponent(note):'');
   const r=await fetch(u,{method:'POST',
    headers:{'Content-Type':f.type||'application/octet-stream'},body:f});
   const d=await r.json();
   if(d.ok){st.textContent='✓ הועלה — המק ימשוך תוך ~חצי דקה';st.style.color='#3fb950';
    if(note)document.getElementById('insText').value='';loadChat();}
   else{st.textContent='✗ '+(d.detail||d.error||'נכשל');st.style.color='#f85149';}
  }catch(e){st.textContent='✗ '+e;st.style.color='#f85149';}
  setTimeout(()=>{st.textContent='';st.style.color='';},12000);
 }
 </script>
</div>
<div class="card"><div class="row"><span class="dim">פוזיציה בסיירה</span><span id="mode" class="tag"></span></div>
<div class="big" id="pos">—</div><div class="dim" id="posdet"></div>
<div id="sierraAge" style="font-size:11px;margin-top:3px"></div></div>
<div class="card"><div class="dim">עסקאות פעילות</div><div id="active">—</div></div>
<div class="card"><div class="row"><span class="dim">יומי (סגורות)</span><span class="dim" id="daymeta"></span></div>
<div class="big num" id="daypnl">—</div><div class="dim">תקרת-הפסד לעצירת-יום: <span class="num" id="cap">—</span></div></div>
<div class="card"><div class="row"><span class="dim">גרף הסשן</span><span class="dim" id="chmeta"></span></div>
<div id="chart" style="margin-top:6px"></div>
<div class="dim" style="font-size:10.5px;margin-top:4px">מחיר <span style="color:#58a6ff">━</span> · רווח-סגורות <span style="color:#3fb950">━</span> · נמדד מרגע שהעמוד קם</div></div>
<div class="card"><div class="row"><span class="dim">חשבון</span><span id="acctmeta" class="dim"></span></div>
<div class="row"><span class="dim">שווי חשבון</span><span id="acct_val" class="num" style="font-weight:800;font-size:18px">—</span></div>
<div class="row"><span class="dim">רווח/הפסד יומי</span><span id="acct_day" class="num">—</span></div>
<div class="row"><span class="dim">P&L פוזיציה פתוחה</span><span id="acct_open" class="num">—</span></div>
<div class="row"><span class="dim">זמין למרג'ין</span><span id="acct_avail" class="num dim">—</span></div></div>
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
/* תיק-המוכנות מאומת באותו MOBILE_ACCESS_KEY, ולכן הקישור נושא את המפתח
   שכבר בכתובת — בלעדיו הדף היה מחזיר 401 בקליק. */
try{document.getElementById('readyLink').href='/readiness'+Q;}catch(e){}
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
// גרף-כיס (מייקל 31.08). מצויר מסדרה שהממסר צובר מה-snapshots — ולכן הוא
// מתחיל כשהעמוד ברנדר קם, לא בפתיחת-הסשן. אומרים את זה בכותרת ולא מעמידים
// פנים. הרווח הוא today.pnl (הסגורות של המערכת), לא daily_pnl של החשבון
// המשותף. אין נתון ⇒ כתוב "אוסף נתונים", בלי להמציא קו.
function drawChart(d){
 const el=document.getElementById('chart'); const mt=document.getElementById('chmeta');
 if(!el) return;
 const S=d._series||[];
 if(S.length<2){ el.innerHTML='<span class="dim" style="font-size:12px">אוסף נתונים…</span>';
  if(mt) mt.textContent=S.length?'1 דגימה':''; return; }
 const W=320,H=88,PL=4,PR=4,PT=8,PB=12;
 const t0=S[0][0], t1=S[S.length-1][0], dt=Math.max(t1-t0,1);
 const X=t=>PL+((t-t0)/dt)*(W-PL-PR);
 const px=S.map(p=>p[1]), pmin=Math.min(...px), pmax=Math.max(...px);
 const pr=Math.max(pmax-pmin,0.5);
 const YP=v=>PT+(1-(v-pmin)/pr)*(H-PT-PB);
 const priceLine=S.map(p=>X(p[0]).toFixed(1)+','+YP(p[1]).toFixed(1)).join(' ');
 let svg='<svg viewBox="0 0 '+W+' '+H+'" style="width:100%;height:88px;display:block">';
 // קו-כניסה ממוצע כשיש פוזיציה — רק אם הוא בתוך טווח-הגרף, אחרת הוא משקר על הסקאלה
 const ap=(d.sierra&&d.sierra.avg_price)||0;
 if(ap>0&&ap>=pmin&&ap<=pmax){ const y=YP(ap).toFixed(1);
  svg+='<line x1="'+PL+'" y1="'+y+'" x2="'+(W-PR)+'" y2="'+y+'" stroke="#f0883e" stroke-width="1" stroke-dasharray="3,3" opacity="0.8"/>'; }
 svg+='<polyline points="'+priceLine+'" fill="none" stroke="#58a6ff" stroke-width="1.6" stroke-linejoin="round"/>';
 const lastX=X(t1).toFixed(1), lastY=YP(S[S.length-1][1]).toFixed(1);
 svg+='<circle cx="'+lastX+'" cy="'+lastY+'" r="2.6" fill="#58a6ff"/>';
 // רווח-הסגורות — סקאלה משלו, נמתח רק אם באמת היה רווח/הפסד
 const pl=S.map(p=>p[2]); const lmin=Math.min(...pl,0), lmax=Math.max(...pl,0);
 if(lmax-lmin>0.01){ const lr=lmax-lmin;
  const YL=v=>PT+(1-(v-lmin)/lr)*(H-PT-PB);
  const z=YL(0).toFixed(1);
  svg+='<line x1="'+PL+'" y1="'+z+'" x2="'+(W-PR)+'" y2="'+z+'" stroke="#8b949e" stroke-width="0.7" stroke-dasharray="2,4" opacity="0.6"/>';
  const cur=pl[pl.length-1], col=cur>=0?'#3fb950':'#f85149';
  svg+='<polyline points="'+S.map(p=>X(p[0]).toFixed(1)+','+YL(p[2]).toFixed(1)).join(' ')+'" fill="none" stroke="'+col+'" stroke-width="1.6" stroke-linejoin="round"/>'; }
 svg+='<text x="'+(W-PR)+'" y="7" text-anchor="end" fill="#8b949e" font-size="8">'+pmax.toFixed(2)+'</text>';
 svg+='<text x="'+(W-PR)+'" y="'+(H-2)+'" text-anchor="end" fill="#8b949e" font-size="8">'+pmin.toFixed(2)+'</text>';
 svg+='</svg>';
 el.innerHTML=svg;
 const mins=Math.round((t1-t0)/60);
 if(mt) mt.textContent=(mins<60? mins+' דק׳': (mins/60).toFixed(1)+' שע׳')+' · '+S.length+' דגימות';
}

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
  } else if (d._relay === 'empty') {
    // 29.08: זה המצב שמייקל רואה בפועל בשבת/אחרי-deploy — Render בתוכנית-חינם
    // נרדם ומאבד את הזיכרון, ואז העמוד צעק "המק לא דוחף עדכונים" (האשמה
    // לא-מאומתת שנראית כמו תקלה). עכשיו: הסבר ישר, וציון שבת אם רלוונטי.
    const _il = new Date().toLocaleString('en-US',{timeZone:'Asia/Jerusalem',weekday:'short'});
    el.style.background = '#2d2614'; el.style.borderColor = '#d29922'; el.style.color = '#d29922';
    el.textContent = '⏸ אין נתונים בענן — שירות-הענן התעורר מחדש והזיכרון נמחק.'
      + (_il.startsWith('Sat')? ' שבת — השוק סגור והממסר במנוחה.' : '')
      + ' הנתונים יחזרו תוך שניות אם המק דוחף; אם לא — המק כבוי או הממסר לא רץ.';
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
  // ts במצב-ריק מגיע משעון-UTC של Render (3 שעות אחורה) — הוצג כאילו הוא זמן
  // הנתונים. במצב-ריק לא מציגים שעון בכלל.
  document.getElementById('clock').textContent = d._relay==='empty' ? '☁ ממתין למק'
    : ((d.ts||'') + ' · ☁ Render' + (age!=null? ' · עדכון לפני '+Math.round(age)+'ש':''));
  if(d._relay==='empty'){ _lastOk = Date.now();
    document.getElementById('health').textContent='ממתין ל-snapshot ראשון מהמק...'; return; }
  const s = d.sierra||{}; const q = s.position_qty;
  // 29.08 ביקורת-UX: "לא ידוע" חייב להיראות שונה מ-"אפס"/"תקין". שדה חסר
  // (sierra_state לא נקרא) הציג בעבר "אמת · לא-חמוש" ו-FLAT בביטחון מלא —
  // בדיוק המקרה שבו מייקל ראה "לא חמושה" בזמן שהמנוע עבד. שלושה מצבים.
  const modeEl = document.getElementById('mode');
  const _sim = s.is_sim==null? '⚠ מצב?' : (s.is_sim? 'סים':'אמת');
  const _arm = s.order_placement_armed==null? ' · ⚠ חימוש?'
             : (s.order_placement_armed? ' · חמוש':' · לא-חמוש');
  modeEl.textContent = _sim + _arm;
  modeEl.style.background = (s.is_sim==null||s.order_placement_armed==null)? '#5a3d0a' : '';
  modeEl.style.color = (s.is_sim==null||s.order_placement_armed==null)? '#ffd479' : '';
  // גיל עין-המצב: נקרא בשניות גולמיות ("41209.6ש") — בלתי-קריא. מוצג כמשך
  // אנושי, ומעל 2 דק' מסמן את כל הכרטיס כלא-עדכני.
  const _ageS = s._age_s;
  const _dur = v => v==null? null : v<90? Math.round(v)+' שנ׳'
             : v<5400? Math.round(v/60)+' דק׳' : (v/3600).toFixed(1)+' שע׳';
  const _sierraStale = (_ageS==null || _ageS>120);
  document.getElementById('sierraAge').innerHTML = _sierraStale
    ? '<span style="color:#f0883e">⚠ '+(_ageS==null? 'עין-מצב: גיל-הנתונים לא ידוע'
        : 'עין-מצב לפני '+_dur(_ageS))+' — לא עדכני</span>'
    : '<span class="dim">עין-מצב לפני '+_dur(_ageS)+'</span>';
  if (d.machine) document.getElementById('machine').textContent = d.machine;
  // ── חשבון (Account Monitor, מה-snapshot) ──
  const $$ = (v,pfx)=> v==null? '—' : (pfx&&v>=0?'+':'')+Number(v).toFixed(2)+'$';
  const cls = v => 'num '+(v==null?'dim':(v>=0?'green':'red'));
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
   // 29.08: אזור-הנגיעה היה 170×24px על פקד שמשבית שער-בטיחות — הוגדל ל-44px.
   if(L.blocked_by && (d.gate_overridable||[]).includes(L.blocked_by)) ge.innerHTML += '<div style="margin-top:6px"><button onclick="gateOv(\\''+L.blocked_by+'\\',false)" style="min-height:44px;padding:10px 14px;border-radius:8px;border:1px solid #d29922;background:#2d2614;color:#d29922;font-size:12px;font-family:inherit">🔓 בטל חוסם זה (עד-ריסטארט)</button></div>';
   document.getElementById('gmeta').textContent = g.attempts+' ניסיונות · '+g.fired+' ירו · '+g.blocked+' נחסמו';
  } else { ge.innerHTML = '<span class="dim">אף מועמד לא הגיע לשער מאז-הריסטארט</span>'; document.getElementById('gmeta').textContent=''; }
  const ov = d.gate_overrides||[];
  if(ov.length) ge.innerHTML += '<div style="margin-top:5px;padding:4px 6px;border:1px solid #d29922;border-radius:8px;color:#d29922;font-size:11px">🔓 חוסמים מבוטלים (עד-ריסטארט): '+ov.map(o=>(o.label||o.gate)+' <span class="dim">'+o.ts+'</span> <button onclick="gateOv(\\''+o.gate+'\\',true)" style="padding:1px 8px;border-radius:6px;border:1px solid #3fb950;background:#0d2818;color:#3fb950;font-size:10.5px;font-family:inherit">החזר</button>').join(' · ')+'</div>';
  const ST_HE = {ready:['מוכן לירי','#3fb950'],armed:['חמוש','#3fb950'],fired:['ירה היום','#58a6ff'],
   building:['בהתהוות','#d29922'],blocked:['ממתין','#8b949e'],vetoed:['וטו','#f85149'],skip:['SKIP לסוג-היום','#f85149'],
   not_applicable:['לא-רלוונטי','#8b949e'],unknown:['?','#8b949e']};
  const P = d.patterns||[];
  // 27.08 (מייקל: "לשים בפאנל את התבנית הכי קרובה לירי כדי שאדע"):
  // מדרג לפי פער-מספרי בהודעת-ההמתנה (gap=Xpts) — הקטן ביותר = הקרוב-לירי;
  // תבנית בלי פער מדיד מדורגת אחרי המדידות. מוצג כשורה בולטת מעל הרשימה.
  let _near = null;
  P.forEach(p=>{
   if(p.status!=='armed' && p.status!=='forming' && p.status!=='ready') return;
   const m = /gap=(-?[0-9.]+)\s*pts/.exec(String(p.reason||''));
   const g = m? Math.abs(parseFloat(m[1])) : null;
   if(!_near) { _near = {p, g}; return; }
   if(g!==null && (_near.g===null || g<_near.g)) _near = {p, g};
  });
  const _nearHtml = _near? '<div style="background:#132a1a;border:1px solid #2ea04366;border-radius:8px;padding:6px 9px;margin-bottom:6px"><span style="color:#3fb950;font-weight:600">🎯 הכי קרוב לירי: '+_near.p.name+'</span>'+(_near.g!==null? ' <span style="color:#e6edf3">· '+_near.g.toFixed(2)+' נק׳ מהטריגר</span>':'')+'<div class="dim" style="font-size:10.5px">'+String(_near.p.reason||'').replace(/</g,'&lt;').slice(0,90)+'</div></div>' : '';
  document.getElementById('pats').innerHTML = _nearHtml + (P.length? P.map(p=>{
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
  }).join('') : '<span class="dim">אין נתוני-תבניות</span>');
  const posEl = document.getElementById('pos');
  // 29.08: פוזיציה לא-ידועה הוצגה כ-"FLAT" מודגש — השקר המסוכן ביותר בעמוד
  // (מייקל קורא FLAT, לא עושה כלום, ופוזיציה עירומה נשארת בשוק).
  if (q==null) {
   posEl.textContent = '⚠ לא ידוע';
   posEl.className = 'big'; posEl.style.color = '#f0883e';
   document.getElementById('posdet').innerHTML =
    '<span style="color:#f0883e">אין קריאת-פוזיציה מסיירה — בדוק בסיירה לפני כל החלטה</span>';
  } else {
   posEl.textContent = q===0? 'FLAT' : (q>0? 'LONG ':'SHORT ') + Math.abs(q);
   posEl.className = 'big ' + (q===0?'':'pulse');
   posEl.style.color = _sierraStale? '#f0883e' : '';
   document.getElementById('posdet').textContent = q!==0
    ? ('ממוצע '+(s.avg_price??'—')+' · '+(s.working_orders??'—')+' הוראות-הגנה') : '';
  }
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
     `<span class="num ${c.pnl>=0?'green':'red'}" style="font-family:monospace;font-size:11px">${c.pnl>=0?'+':''}${c.pnl}$</span>`+
     `<span style="font-size:10.5px" class="num ${(c.pct||0)>=0?'green':'red'}">${c.pct!=null?(c.pct>0?'+':'')+c.pct+'%':''}</span></div>${bar}</div>`;
   }).join('');
   const mv=t.move_pts!=null?`<div class="row" style="font-size:11.5px"><span class="dim">תזוזה</span><span class="num ${t.move_pts>=0?'green':'red'}">${t.move_pts>0?'+':''}${t.move_pts} נק׳${t.mae_pts!=null?' · הכי-נגד '+t.mae_pts:''}${t.mfe_pts!=null?' · הכי-בעד '+t.mfe_pts:''}</span></div>`:'';
   const sp=t.stop_pct!=null?`<div class="row" style="font-size:11.5px"><span class="dim">מהדרך לסטופ</span><span class="num ${t.stop_pct>=50?'red':'dim'}" style="font-weight:700">${Math.max(t.stop_pct,0)}%</span></div>`:'';
   const nt=t.next_target_pct!=null?`<div class="row" style="font-size:11.5px"><span class="dim">ליעד הבא ${t.next_target??''}</span><span class="num ${t.next_target_pct>=0?'green':'red'}" style="font-weight:700">${t.next_target_pct>0?'+':''}${t.next_target_pct}%</span></div>`:'';
   const tp=t.total_pnl??t.upnl_usd;
   return `<div class="row"><span>#${t.id} ${t.direction} ×${legs.length||t.contracts} ${t.pattern||''} @${t.entry_price} <span class="dim">${t.t_in}</span></span>`+
    `<span class="num ${(tp||0)>=0?'green':'red'}" style="font-weight:800">${tp!=null?(tp>=0?'+':'')+tp+'$':''}</span></div>`+
    `<div class="dim" style="font-size:11px">סטופ ${t.stop??'—'} · ${t.summary||''}</div>`+mv+sp+nt+
    (rows?`<div style="margin-top:4px">${rows}</div>`:`<div class="dim">T0 ${t.t0??'—'} · T1 ${t.t1??'—'} · T2 ${t.t2??'—'} · T3 ${t.t3??'—'}</div>`);
  }).join('<div style="height:8px"></div>')
   : '<span class="dim">אין עסקה פעילה</span>';
  const td = d.today||{}; const pnl = td.pnl??0;
  const de = document.getElementById('daypnl');
  de.textContent = (pnl>=0?'+':'')+Number(pnl).toFixed(0)+'$';
  de.className = 'big num '+(pnl>=0?'green':'red');
  document.getElementById('daymeta').textContent = (td.n||0)+' עסקאות · '+(td.w||0)+' מנצחות';
  try{ drawChart(d); }catch(e){ const _ce=document.getElementById('chart'); if(_ce) _ce.innerHTML='<span class="dim" style="font-size:11px">גרף לא-זמין</span>'; }
  document.getElementById('cap').textContent = d.halt_cap==null? '—' : '−'+d.halt_cap+'$';
  // 29.08: כרטיס "סוג-יום" הציג "—" בזמן שהרדאר שני כרטיסים מעליו הציג
  // Neutral_Center 67% — שני פאנלים באותו מסך סותרים זה את זה. אותה snapshot,
  // מקור מסומן במפורש (בלי להמציא ערך).
  const _dt = d.day_type ?? (d.radar&&d.radar.day_type) ?? null;
  const _dtFromRadar = (d.day_type==null && _dt!=null);
  document.getElementById('daytype').innerHTML = _dt
    ? (_dt + (_dtFromRadar? ' <span class="dim" style="font-size:11px">(מהרדאר)</span>':'')) : '—';
  const _dc = d.day_conf ?? (d.radar&&d.radar.confidence!=null? Math.round(d.radar.confidence*100)+'%':null);
  document.getElementById('dayconf').textContent = _dc!=null? 'ביטחון '+_dc : '';
  const dr = d.daily; const drEl = document.getElementById('daily');
  if(dr){
   const p = dr.pnl_usd||0;
   drEl.innerHTML = '<span class="num '+(p>=0?'green':'red')+'" style="font-size:16px;font-weight:800">'+(p>=0?'+':'')+p+'$</span> · '+
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
  // 29.08: התראות הוצגו כ-markdown גולמי ("**"), נחתכו ב-110 תווים בלי "…",
  // ובלי גיל — כך שהתראה בת 36 יום נראתה בדיוק כמו התראה מלפני דקה.
  document.getElementById('alerts').innerHTML = (d.alerts&&d.alerts.length)? d.alerts.map(x=>{
   const raw = String(x);
   const m = /([0-9]{4})-([0-9]{2})-([0-9]{2})[ T]([0-9]{2}):([0-9]{2})/.exec(raw);
   let badge = '';
   if(m){
    const days = Math.floor((Date.now()-new Date(+m[1],+m[2]-1,+m[3],+m[4],+m[5]).getTime())/864e5);
    if(days>=1) badge = '<span class="tag" style="color:#8b949e">לפני '+days+' ימים</span> ';
   }
   const body = raw.replace(/[*]{2}/g,'').replace(/^[-•][ ]*/,'').replace(/</g,'&lt;');
   const cut = body.length>130? body.slice(0,130)+'…' : body;
   return '<div style="margin-bottom:4px">'+badge+cut+'</div>';
  }).join(''):'<span class="dim">שקט ✓</span>';
  // 29.08: updatePause הוגדרה מעולם-לא-נקראה — הבאנר האדום "PAUSED" לא הופיע
  // אף פעם, והכפתור תמיד שלח PAUSE. כלומר: אי-אפשר היה לחדש מסחר מהטלפון.
  // d.trading_paused כבר קיים ב-snapshot; שורה אחת סוגרת את הפער.
  if (d.trading_paused!=null) updatePause(!!d.trading_paused);
  document.getElementById('health').textContent = 'מחיר '+(d.mid??'—')+' · חוזים מוגדרים: '+(d.contracts_cfg??'—')+' · רענון-5ש · ☁';
  _lastOk = Date.now();
 }catch(e){ _offline(e); }
}
// 29.08: נפילת-רשת הותירה את העמוד מציג "SHORT 3 · אמת · חמוש · עדכון לפני 4ש"
// לנצח, עם שורת-שגיאה אפורה בתחתית העמוד בלבד. עכשיו: באנר אדום למעלה + גיל
// אמיתי של הנתונים המוצגים.
let _lastOk = 0;
function _offline(e){
 const el = document.getElementById('stale');
 const secs = _lastOk? Math.round((Date.now()-_lastOk)/1000) : null;
 el.style.background='#2d1214'; el.style.borderColor='#f85149'; el.style.color='#f85149';
 el.textContent = '⚠ אין קשר לענן — הנתונים למטה ' +
  (secs==null? 'לא נטענו כלל' : 'מלפני '+(secs<90? secs+' שנ׳' : Math.round(secs/60)+' דק׳')) +
  ' · אל תסתמך עליהם';
 el.style.display='block';
 document.getElementById('clock').textContent = '⚠ מנותק · ☁';
 document.getElementById('health').textContent = 'שגיאת-רשת: '+String(e).slice(0,60);
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
// 29.08: פקודת-חירום הציגה "✓ נשלחה" ונמחקה אחרי 8ש — בלי שום סימן אם המק
// אכן קיבל וביצע. אם הממסר לא רץ (מצב שקרה בפועל), FLATTEN פג בשקט אחרי 60ש
// ומייקל נשאר עם פוזיציה פתוחה ובטוח שסגר. עכשיו עוקבים אחרי /cmd/pending עד
// שהתור מתנקה (=המק משך וביצע) או פג (=לא הגיע לאף אחד).
async function _watchCmd(id, action){
 const st=document.getElementById('cmdStatus');
 const t0=Date.now();
 while(Date.now()-t0 < 70000){
  await new Promise(r=>setTimeout(r,2000));
  let d;
  try{ d = await (await fetch('/cmd/pending'+Q,{cache:'no-store'})).json(); }
  catch(e){ st.textContent='⚠ '+action+' נשלחה — אבד הקשר, לא ידוע אם בוצעה';
            st.style.color='#f0883e'; return; }
  if(d && d.expired){
   st.textContent='🔴 '+action+' לא בוצעה — המק לא משך את הפקודה (הממסר לא רץ?). בדוק בסיירה!';
   st.style.color='#f85149'; return;
  }
  if(!d || d.cmd==null || d.cmd.id!==id){
   st.textContent='✓ '+action+' — המק משך וביצע. ודא את התוצאה בסיירה/בפאנל.';
   st.style.color='#3fb950'; return;
  }
  st.textContent='⏳ '+action+' ממתינה למק... ('+Math.round((Date.now()-t0)/1000)+'ש)';
  st.style.color='#d29922';
 }
 st.textContent='🔴 '+action+' פגה אחרי 60ש בלי שהמק משך אותה. בדוק בסיירה!';
 st.style.color='#f85149';
}
async function sendCmd(action){
 const msg={FLATTEN:'לסגור עכשיו את כל הפוזיציות בחשבון (FLATTEN מלא)?',
            PAUSE:'להשהות מסחר? כניסות חדשות → צל-בלבד. פוזיציות פתוחות נשארות.',
            RESUME:'לחדש מסחר רגיל? כניסות חדשות ישוגרו שוב.'}[action];
 if(!confirm(msg)) return;
 const msg2={FLATTEN:'אישור סופי — לסגור את כל הפוזיציות בשוק עכשיו?',
             PAUSE:'אישור סופי — להשהות מסחר?',
             RESUME:'אישור סופי — לחדש מסחר?'}[action];
 if(!confirm(msg2)) return;
 const st=document.getElementById('cmdStatus'); st.textContent='שולח...'; st.style.color='';
 try{
  const r=await fetch('/cmd'+Q,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:action})});
  const d=await r.json();
  if(d.ok && d.cmd){
   st.textContent='⏳ '+action+' נשלחה — ממתינה למק...'; st.style.color='#d29922';
   _watchCmd(d.cmd.id, action);   // לא מנקה לבד — נשאר עד תוצאה סופית
  } else {
   st.textContent='✗ '+(d.error||d.detail||'נכשל'); st.style.color='#f85149';
   setTimeout(()=>{st.textContent='';st.style.color='';},8000);
  }
 }catch(e){st.textContent='✗ '+e;st.style.color='#f85149';
  setTimeout(()=>{st.textContent='';st.style.color='';},8000);}
}
document.getElementById('pauseBtn').onclick=()=>sendCmd(_paused?'RESUME':'PAUSE');
document.getElementById('flatBtn').onclick=()=>sendCmd('FLATTEN');
</script></body></html>"""


# ── תיק-המוכנות (מייקל 29.08: "שיהיה לינק באפליקציה ובמערכת פרונטאנד") ──
# דף סטטי בלבד. נוצר מ-docs/plans/TASK_LOG.md ע"י scripts/gen_readiness_page.py
# ונכתב ל-render_mobile_relay/static/readiness.html — כלומר בתוך rootDir של
# השירות ברנדר, ולכן הוא נפרס יחד עם הקוד. אין DB, אין backend, אין מסחר.
_READINESS_PATHS = (
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "readiness.html"),
    # גיבוי: כשהריפו כולו זמין (ריצה מקומית), המקור הקנוני.
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "docs", "plans", "MONDAY_READINESS.html"),
)


@app.get("/readiness", response_class=HTMLResponse)
@app.get("/readiness/", response_class=HTMLResponse)
async def readiness_page(request: Request):
    if not _page_key_ok(request):
        return HTMLResponse(
            "<html dir=rtl><body style='background:#0b0e14;color:#e6edf3;"
            "font-family:-apple-system;padding:40px;text-align:center'>"
            "<h2>🔒 נדרש מפתח-גישה</h2><p>הוסף <code>?key=…</code> לכתובת.</p>"
            "</body></html>", status_code=401)
    for p in _READINESS_PATHS:
        try:
            with open(p, "r", encoding="utf-8") as fh:
                return HTMLResponse(fh.read())
        except OSError:
            continue
    # כנות במקום 500: אם הקובץ לא נפרס — אומרים את זה, ואומרים איך מתקנים.
    return HTMLResponse(
        "<html dir=rtl><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "</head><body style='background:#0b0e14;color:#e6edf3;"
        "font-family:-apple-system;padding:32px 20px;line-height:1.7'>"
        "<h2>📋 תיק-המוכנות לא נפרס</h2>"
        "<p>הקובץ <code>static/readiness.html</code> אינו קיים בשירות הזה.</p>"
        "<p class=dim style='color:#8b949e;font-size:13px'>התיקון: להריץ על המק "
        "<code>python3 scripts/gen_readiness_page.py</code>, ואז commit+push — "
        "רנדר פורס אוטומטית תוך ~90 שניות.</p>"
        "<p><a href='/' style='color:#79c0ff'>← חזרה למוניטור</a></p>"
        "</body></html>", status_code=404)


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
