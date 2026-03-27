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
REDIS_KEY         = "mems26:latest"
REDIS_CANDLES_KEY = "mems26:candles"
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

from fastapi import Request as FastAPIRequest
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: FastAPIRequest, exc: Exception):
    log.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={"Access-Control-Allow-Origin": "*"}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: FastAPIRequest, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={"Access-Control-Allow-Origin": "*"}
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


@app.get("/market/candles")
async def get_candles(limit: int = 80):
    raw = await redis_lrange(REDIS_CANDLES_KEY, 0, limit - 1)
    candles = []
    for item in raw:
        try:
            c = json.loads(item) if isinstance(item, str) else item
            candles.append(c)
        except Exception:
            continue
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
    et_offset = timedelta(hours=-4)  # EDT (קיץ) — בחורף -5
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

    prompt = f"""אתה מערכת AI מתקדמת למסחר יומי ב-MES (Micro E-Mini S&P 500 Futures).
אתה מומחה ב-3 סטאפים ספציפיים. החלט האם יש הזדמנות מסחר עכשיו.

נתוני שוק:
מחיר={price} | Session={session.get('phase')} | דקה={session.get('min',-1)}
DayType={day.get('type','?')} | IB_Range={day.get('ib_range',0):.2f} | Gap={day.get('gap_type','FLAT')}
Extensions={day.get('total_ext',0)} | Returned={day.get('returned',False)}

נר 3m: O={bar.get('o')} H={bar.get('h')} L={bar.get('l')} C={bar.get('c')} Delta={bar.get('delta')}
Pattern: {candle_p.get('bar0')} | prev={candle_p.get('bar1')} | BullEngulf={candle_p.get('bull_engulf')} | BearEngulf={candle_p.get('bear_engulf')}

CVD: {cvd.get('trend')} | 60m={cvd.get('d20')} | 15m={cvd.get('d5')} | bar={cvd.get('delta')}
VWAP: {vwap.get('value')} | above={vwap.get('above')} | dist={vwap_dist:.2f} | pullback={vwap.get('pullback')}
CCI: cci14={cci.get('cci14',0):.1f} | cci6={cci.get('cci6',0):.1f} | trend={cci.get('trend')}
     TurboBull={cci.get('turbo_bull')} | TurboBear={cci.get('turbo_bear')} | ZLR_Bull={cci.get('zlr_bull')} | ZLR_Bear={cci.get('zlr_bear')}

Profile: POC={profile.get('poc')} | VAH={profile.get('vah')} | VAL={profile.get('val')} | PrevPOC={profile.get('prev_day_poc')}
         in_VA={profile.get('in_va')} | above_poc={profile.get('above_poc')}
IB: H={session.get('ibh')} L={session.get('ibl')} | locked={session.get('ib_locked')}
    breakout_up={day.get('ib_breakout_up')} | breakout_down={day.get('ib_breakout_down')}
OR: H={day.get('or_high')} L={day.get('or_low')}
Woodi: PP={woodi.get('pp')} R1={woodi.get('r1')} R2={woodi.get('r2')} S1={woodi.get('s1')}
Levels: PDH={levels.get('prev_high')} PDL={levels.get('prev_low')} DO={levels.get('daily_open')} ONH={levels.get('overnight_high')} ONL={levels.get('overnight_low')}
OF: Absorption={of2.get('absorption_bull')} | LiqSweepLong={of2.get('liq_sweep_long')} | LiqSweepShort={of2.get('liq_sweep_short')} | ImbBull={of2.get('imbalance_bull')} | ImbBear={of2.get('imbalance_bear')}
RelVol: {rel_vol:.2f}x ({vol_ctx.get('context','NORMAL')})
MTF: 15m={mtf.get('m15',{}).get('delta')} | 30m={mtf.get('m30',{}).get('delta')} | 60m={mtf.get('m60',{}).get('delta')}
סטאפים:
1. LIQ SWEEP: שבירת רמה+חזרה אגרסיבית+volume. אחוז בסיס: 68-75%
2. VWAP PULLBACK: מגמה+pullback חלש+נר היפוך. אחוז בסיס: 62-70%
3. IB BREAKOUT RETEST: פריצה+חזרה+בלימה. אחוז בסיס: 58-65%

ניהול: C1=R:R 1:1 | C2=R:R 1:2 | C3=Runner Woodi R1/R2

JSON בלבד ללא backticks:
{{"direction":"LONG/SHORT/NO_TRADE","score":0-10,"confidence":"LOW/MEDIUM/HIGH/ULTRA","setup":"שם סטאפ בעברית","win_rate":0-85,"t1_win_rate":0-85,"t2_win_rate":0-65,"t3_win_rate":0-45,"entry":0.0,"stop":0.0,"target1":0.0,"target2":0.0,"target3":0.0,"risk_pts":0.0,"rationale":"2-3 משפטים עברית","wait_reason":"מה להמתין אם NO_TRADE","tl_color":"red/orange/green/green_bright"}}"""

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
                    "model": "claude-sonnet-4-5",
                    "max_tokens": 600,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
        result = resp.json()
        text = result.get("content", [{}])[0].get("text", "").strip()
        signal = json.loads(text)
        signal["ts"] = data.get("ts", 0)
        log.info(f"AI: {signal.get('direction')} score={signal.get('score')} win={signal.get('win_rate')}% t1={signal.get('t1_win_rate')}%")
        return signal
    except json.JSONDecodeError as e:
        log.error(f"AI JSON parse error: {e} | text: {text[:200] if 'text' in dir() else 'N/A'}")
        raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {e}")
    except httpx.TimeoutException:
        log.error("AI timeout")
        raise HTTPException(status_code=504, detail="AI request timed out — try again")
    except Exception as e:
        log.error(f"AI error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")


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
