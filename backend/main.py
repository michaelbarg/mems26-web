import os
import json
import asyncio
import logging
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("api")

BRIDGE_TOKEN      = os.getenv("BRIDGE_TOKEN", "michael-mems26-2026")
REDIS_URL         = os.getenv("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN       = os.getenv("UPSTASH_REDIS_REST_TOKEN")
REDIS_KEY          = "mems26:latest"
REDIS_CANDLES_KEY  = "mems26:candles"
REDIS_FOOTPRINT_KEY = "mems26:footprint"
REDIS_PATTERNS_KEY  = "mems26:patterns"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


async def redis_set(data: dict):
    if not REDIS_URL or not REDIS_TOKEN:
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{REDIS_URL}/set/{REDIS_KEY}",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                json=json.dumps(data),
                timeout=3.0
            )
    except Exception as e:
        log.warning(f"Redis set failed: {e}")


async def redis_get() -> Optional[dict]:
    if not REDIS_URL or not REDIS_TOKEN:
        return None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{REDIS_URL}/get/{REDIS_KEY}",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                timeout=3.0
            )
            result = resp.json()
            val = result.get("result")
            if val:
                return json.loads(val)
    except Exception as e:
        log.warning(f"Redis get failed: {e}")
    return None


async def redis_lrange(key: str, start: int, stop: int) -> list:
    if not REDIS_URL or not REDIS_TOKEN:
        return []
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{REDIS_URL}/lrange/{key}/{start}/{stop}",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                timeout=5.0
            )
            result = resp.json()
            return result.get("result", [])
    except Exception as e:
        log.warning(f"Redis lrange failed: {e}")
        return []


class ConnectionManager:
    def __init__(self):
        self._clients: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._clients.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self._clients:
            self._clients.remove(ws)

    async def broadcast(self, data: dict):
        for ws in self._clients:
            try:
                await ws.send_json(data)
            except:
                pass

manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(f"MEMS26 API Started | REDIS_URL={REDIS_URL} | HAS_TOKEN={bool(REDIS_TOKEN)}")
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/ingest")
async def ingest(request: Request, x_bridge_token: Optional[str] = Header(None)):
    if x_bridge_token != BRIDGE_TOKEN:
        log.warning(f"Unauthorized: {x_bridge_token}")
        raise HTTPException(status_code=401, detail="Invalid token")
    raw = await request.json()
    await redis_set(raw)
    log.info(f"Received: {raw.get('bar', {}).get('c')}")
    await manager.broadcast({"type": "market_update", **raw})
    return {"ok": True}


@app.get("/market/latest")
async def market_latest():
    data = await redis_get()
    if not data:
        return {"type": "no_data", "status": "waiting_for_bridge"}
    return data


@app.post("/ingest/history")
async def ingest_history(request: Request, x_bridge_token: Optional[str] = Header(None)):
    if x_bridge_token != BRIDGE_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    raw = await request.json()
    candles = raw.get("candles", [])
    if not candles:
        raise HTTPException(status_code=400, detail="No candles provided")

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{REDIS_URL}/del/{REDIS_CANDLES_KEY}",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                json={},
                timeout=5.0
            )
            items = [json.dumps(c) for c in candles[:960]]
            for chunk in [items[i:i+20] for i in range(0, len(items), 20)]:
                path_values = "/".join(
                    v.replace("/", "%2F").replace(" ", "%20") for v in chunk
                )
                await client.post(
                    f"{REDIS_URL}/lpush/{REDIS_CANDLES_KEY}/{path_values}",
                    headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                    timeout=15.0
                )
        log.info(f"History loaded: {len(candles)} candles")
        return {"ok": True, "loaded": len(candles)}
    except Exception as e:
        log.error(f"History ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/market/candles")
async def get_candles(limit: int = 960):
    raw = await redis_lrange(REDIS_CANDLES_KEY, 0, limit - 1)
    candles = []
    for item in raw:
        try:
            c = item
            while isinstance(c, str):
                c = json.loads(c)
            if isinstance(c, dict) and c.get("ts", 0) > 0:
                candles.append(c)
        except Exception:
            continue
    candles.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return candles


@app.get("/market/analyze")
async def market_analyze():
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")

    data = await redis_get()
    if not data:
        return {
            "direction": "NO_TRADE", "score": 0, "confidence": "LOW",
            "setup": "אין נתונים", "win_rate": 0,
            "entry": 0, "stop": 0, "target1": 0, "target2": 0, "target3": 0,
            "risk_pts": 0, "rationale": "Bridge לא פעיל", "tl_color": "red", "ts": 0,
            "t1_win_rate": 0, "t2_win_rate": 0, "t3_win_rate": 0,
            "wait_reason": "Bridge לא פעיל"
        }

    from datetime import datetime, timezone, timedelta
    et_offset = timedelta(hours=-4)
    now_et = datetime.now(timezone(et_offset))
    h, m = now_et.hour, now_et.minute
    is_rth = (h == 9 and m >= 30) or (10 <= h <= 15) or (h == 16 and m == 0)

    if not is_rth:
        return {
            "direction": "NO_TRADE", "score": 0, "confidence": "LOW",
            "setup": "מחוץ לשעות RTH", "win_rate": 0,
            "entry": 0, "stop": 0, "target1": 0, "target2": 0, "target3": 0,
            "risk_pts": 0, "rationale": "שוק סגור. RTH מתחיל ב-9:30 ET",
            "tl_color": "red", "ts": data.get("ts", 0),
            "t1_win_rate": 0, "t2_win_rate": 0, "t3_win_rate": 0,
            "wait_reason": "RTH מתחיל ב-9:30 ET"
        }

    price   = data.get("price", 0)
    bar     = data.get("bar", {})
    cvd     = data.get("cvd", {})
    vwap    = data.get("vwap", {})
    session = data.get("session", {})
    profile = data.get("profile", {})
    woodi   = data.get("woodi", {})
    levels  = data.get("levels", {})
    of2     = data.get("order_flow", {})
    mtf     = data.get("mtf", {})
    day     = data.get("day", {})
    cci     = data.get("woodies_cci", {})
    vol_ctx = data.get("volume_context", {})
    candle_p= data.get("candle_patterns", {})

    vwap_dist = vwap.get("distance", 0) or 0
    rel_vol   = vol_ctx.get("rel_vol", 1) or 1

    fp_raw = data.get("footprint", [])
    if fp_raw and isinstance(fp_raw, list):
        fp_lines = []
        for fb in fp_raw[-5:]:
            if isinstance(fb, dict):
                fp_lines.append(f"Δ={fb.get('delta',0):+.0f} vol={fb.get('buy',0)+fb.get('sell',0):.0f}")
        footprint_summary = " | ".join(fp_lines) if fp_lines else "N/A"
    else:
        footprint_summary = "N/A"

    candles_raw = await redis_lrange(REDIS_CANDLES_KEY, 0, 4)
    last_5 = []
    for item in candles_raw:
        try:
            c = item
            while isinstance(c, str):
                c = json.loads(c)
            if isinstance(c, dict) and c.get("ts", 0) > 0:
                last_5.append(c)
        except Exception:
            continue
    last_5.sort(key=lambda x: x.get("ts", 0))
    last_5_str = " | ".join(
        f"O={c.get('o',0):.2f} H={c.get('h',0):.2f} L={c.get('l',0):.2f} C={c.get('c',0):.2f} Δ={c.get('delta',0):+.0f}"
        for c in last_5
    ) if last_5 else "N/A"

    prompt = f"""אתה אנליסט בכיר למסחר ב-MES Futures.
נתח את הנתונים הבאים וגבש המלצת כניסה מדויקת.

נתוני שוק נוכחיים:
- מחיר: {price}
- Session: {session.get('phase','?')} | דקה: {session.get('min',-1)}
- DayType: {day.get('type','?')} | IB_Range: {day.get('ib_range',0):.2f} | Gap: {day.get('gap_type','FLAT')}
- Delta נר נוכחי: {bar.get('delta',0)}
- CVD trend: {cvd.get('trend','?')} | CVD d5: {cvd.get('d5',0)} | CVD d20: {cvd.get('d20',0)}
- Volume יחסי: {rel_vol:.2f}x ({vol_ctx.get('context','NORMAL')})
- VWAP: {vwap.get('value',0)} | מעל: {vwap.get('above',False)} | dist: {vwap_dist:.2f} | pullback: {vwap.get('pullback',False)}
- POC: {profile.get('poc',0)} | מעל POC: {profile.get('above_poc',False)} | VAH: {profile.get('vah',0)} | VAL: {profile.get('val',0)}
- PDH: {levels.get('prev_high',0)} | PDL: {levels.get('prev_low',0)} | DO: {levels.get('daily_open',0)}
- ONH: {levels.get('overnight_high',0)} | ONL: {levels.get('overnight_low',0)}
- IBH: {session.get('ibh',0)} | IBL: {session.get('ibl',0)} | IB נעול: {session.get('ib_locked',False)}
- CCI14: {cci.get('cci14',0):.1f} | CCI6: {cci.get('cci6',0):.1f} | trend: {cci.get('trend','?')}
- Turbo Bull: {cci.get('turbo_bull',False)} | Turbo Bear: {cci.get('turbo_bear',False)}
- Woodi: PP={woodi.get('pp',0)} R1={woodi.get('r1',0)} R2={woodi.get('r2',0)} S1={woodi.get('s1',0)} S2={woodi.get('s2',0)}
- Pattern: {candle_p.get('bar0','?')} | prev: {candle_p.get('bar1','?')} | BullEngulf: {candle_p.get('bull_engulf',False)} | BearEngulf: {candle_p.get('bear_engulf',False)}
- OF: Absorption={of2.get('absorption_bull',False)} | LiqSweepLong={of2.get('liq_sweep_long',False)} | LiqSweepShort={of2.get('liq_sweep_short',False)}
- Footprint (5 נרות): {footprint_summary}
- MTF: 15m={mtf.get('m15',{{}}).get('delta',0)} | 30m={mtf.get('m30',{{}}).get('delta',0)} | 60m={mtf.get('m60',{{}}).get('delta',0)}
- 5 נרות אחרונים: {last_5_str}

כללים קשיחים:
1. אם סטופ > 8 נקודות → direction: NO_TRADE
2. אם T1 < 10 נקודות → direction: NO_TRADE
3. אם rel_vol < 0.8 → confidence מקסימום 50
4. אם DayType = BALANCED → confidence מקסימום 60
5. אם אין sweep ברור ב-5 נרות אחרונים → העדף NO_TRADE

סטאפים מועדפים:
1. LIQ SWEEP: שבירת רמה (PDH/PDL/ONH/ONL/IBH/IBL) ב-wick, חזרה אגרסיבית עם volume. הטוב ביותר.
2. VWAP PULLBACK: מגמה ברורה + pullback חלש ל-VWAP + נר היפוך + delta מאשר.
3. IB BREAKOUT RETEST: פריצת IB + חזרה לגבול + בלימה + המשך.

ניהול עסקה: C1=50% R:R 1:1 | C2=25% R:R 1:2 | C3=25% Runner Woodi R1/S1

JSON בלבד ללא backticks:
{{"direction":"LONG/SHORT/NO_TRADE","score":0-10,"confidence":0-100,"setup":"שם הסטאפ","setup_name":"LIQ_SWEEP/VWAP_PB/IB_RETEST","win_rate":0-85,"t1_win_rate":0-85,"t2_win_rate":0-65,"t3_win_rate":0-45,"entry":0.0,"stop":0.0,"target1":0.0,"target2":0.0,"target3":0.0,"risk_pts":0.0,"rr":"1:X","the_box":"low-high","anchor_line":0.0,"order_block":"low-high","invalidation":0.0,"rationale":"2-3 משפטים בעברית — הקשר נפח-מבנה","geometric_notes":"הוראות ציור: rect/line/label","warning":"אזהרות אם יש","time_estimate":"X-Y דקות ל-T1","wait_reason":"מה להמתין אם NO_TRADE","tl_color":"red/orange/green/green_bright"}}"""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 800,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
        result = resp.json()
        text = result.get("content", [{}])[0].get("text", "").strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
            text = text.strip()
        signal = json.loads(text)
        signal["ts"] = data.get("ts", 0)
        log.info(f"AI: {signal.get('direction')} score={signal.get('score')} win={signal.get('win_rate')}% t1={signal.get('t1_win_rate')}%")
        return signal
    except Exception as e:
        log.error(f"AI error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/footprint")
async def ingest_footprint(request: Request, x_bridge_token: Optional[str] = Header(None)):
    if x_bridge_token != BRIDGE_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    raw = await request.json()
    bars = raw.get("footprint", [])
    if not bars:
        return {"ok": True, "msg": "no data"}
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{REDIS_URL}/set/{REDIS_FOOTPRINT_KEY}",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                json=json.dumps(bars),
                timeout=5.0
            )
        log.info(f"Footprint: {len(bars)} bars stored")
        return {"ok": True, "bars": len(bars)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/market/patterns")
async def get_patterns():
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{REDIS_URL}/get/{REDIS_PATTERNS_KEY}",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                timeout=3.0
            )
            result = resp.json()
            val = result.get("result")
            if val:
                return {"patterns": json.loads(val)}
    except Exception as e:
        log.warning(f"Patterns get failed: {e}")
    return {"patterns": []}


@app.get("/market/footprint")
async def get_footprint():
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{REDIS_URL}/get/{REDIS_FOOTPRINT_KEY}",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                timeout=3.0
            )
            result = resp.json()
            val = result.get("result")
            if val:
                return json.loads(val)
    except Exception as e:
        log.warning(f"Footprint get failed: {e}")
    return []


REDIS_TRADES_KEY = "mems26:trades"


async def redis_trades_get() -> list:
    if not REDIS_URL or not REDIS_TOKEN:
        return []
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{REDIS_URL}/lrange/{REDIS_TRADES_KEY}/0/199",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                timeout=5.0
            )
            result = resp.json()
            items = result.get("result", [])
            trades = []
            for item in items:
                try:
                    t = json.loads(item) if isinstance(item, str) else item
                    if isinstance(t, dict):
                        trades.append(t)
                except:
                    pass
            return trades
    except Exception as e:
        log.warning(f"Trades get failed: {e}")
    return []


@app.get("/trades")
async def get_trades():
    return await redis_trades_get()


@app.post("/trades")
async def save_trade(request: Request, x_bridge_token: Optional[str] = Header(None)):
    trade = await request.json()
    if not trade.get("entry_price"):
        raise HTTPException(status_code=400, detail="entry_price required")
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{REDIS_URL}/lpush/{REDIS_TRADES_KEY}",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                json=[json.dumps(trade)],
                timeout=5.0
            )
            await client.post(
                f"{REDIS_URL}/ltrim/{REDIS_TRADES_KEY}/0/199",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                timeout=5.0
            )
        log.info(f"Trade saved: {trade.get('side')} @ {trade.get('entry_price')}")
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/trades/{trade_id}")
async def delete_trade(trade_id: str, x_bridge_token: Optional[str] = Header(None)):
    try:
        trades = await redis_trades_get()
        updated = [t for t in trades if t.get("id") != trade_id]
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{REDIS_URL}/del/{REDIS_TRADES_KEY}",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                timeout=5.0
            )
            for t in updated:
                await client.post(
                    f"{REDIS_URL}/rpush/{REDIS_TRADES_KEY}",
                    headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                    json=[json.dumps(t)], timeout=5.0
                )
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trades/analyze/{trade_id}")
async def analyze_trade(trade_id: str):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="No API key")

    trades = await redis_trades_get()
    trade = next((t for t in trades if t.get("id") == trade_id), None)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    data = await redis_get()
    if not data:
        raise HTTPException(status_code=503, detail="No market data")

    price   = data.get("price", 0)
    cvd     = data.get("cvd", {})
    vwap    = data.get("vwap", {})
    cci     = data.get("woodies_cci", {})
    day     = data.get("day", {})
    session = data.get("session", {})

    entry   = trade.get("entry_price", 0)
    side    = trade.get("side", "LONG")
    stop    = trade.get("stop", 0)
    t1      = trade.get("t1", 0)
    t2      = trade.get("t2", 0)
    pnl_pts = (price - entry) if side == "LONG" else (entry - price)

    prompt = f"""אתה מנהל עסקאות MES Futures. עסקה פתוחה:
צד: {side} | כניסה: {entry} | מחיר נוכחי: {price:.2f}
PnL: {pnl_pts:+.2f} נקודות | סטופ: {stop} | T1: {t1} | T2: {t2}
Session: {session.get('phase')} | DayType: {day.get('type')}
CCI14: {cci.get('cci14',0):.1f} | CVD trend: {cvd.get('trend')} | VWAP above: {vwap.get('above')}

החלט: האם להישאר בעסקה, לצאת, להזיז סטופ ל-BE, או לקחת חלקי רווח?
ענה JSON בלבד:
{{"action":"HOLD/EXIT/MOVE_BE/PARTIAL","confidence":0-100,"reason":"משפט קצר בעברית","urgency":"LOW/MEDIUM/HIGH"}}"""

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-sonnet-4-6", "max_tokens": 200, "messages": [{"role": "user", "content": prompt}]}
            )
        text = resp.json().get("content", [{}])[0].get("text", "").strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            text = text[4:] if text.startswith("json") else text
        result = json.loads(text.strip())
        result["pnl_pts"] = round(pnl_pts, 2)
        result["pnl_usd"] = round(pnl_pts * 5, 2)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    data = await redis_get()
    return {"status": "ok", "has_data": data is not None}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
