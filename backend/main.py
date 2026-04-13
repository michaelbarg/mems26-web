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
REDIS_CANDLES_5M   = "mems26:candles:5m"
REDIS_CANDLES_15M  = "mems26:candles:15m"
REDIS_CANDLES_30M  = "mems26:candles:30m"
REDIS_CANDLES_1H   = "mems26:candles:1h"
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


async def redis_get_json_array(key: str) -> list:
    """Read a SET-based key that stores a JSON array string."""
    if not REDIS_URL or not REDIS_TOKEN:
        return []
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{REDIS_URL}/get/{key}",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                timeout=5.0
            )
            result = resp.json()
            val = result.get("result")
            if val and isinstance(val, str):
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return parsed
    except Exception as e:
        log.warning(f"Redis get_json_array failed ({key}): {e}")
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


@app.get("/market/candles/5m")
async def get_candles_5m(limit: int = 288):
    candles = await redis_get_json_array(REDIS_CANDLES_5M)
    candles = [c for c in candles if isinstance(c, dict) and c.get("ts", 0) > 0]
    candles.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return candles[:limit]


@app.get("/market/candles/15m")
async def get_candles_15m(limit: int = 96):
    candles = await redis_get_json_array(REDIS_CANDLES_15M)
    candles = [c for c in candles if isinstance(c, dict) and c.get("ts", 0) > 0]
    candles.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return candles[:limit]


@app.get("/market/candles/30m")
async def get_candles_30m(limit: int = 48):
    candles = await redis_get_json_array(REDIS_CANDLES_30M)
    candles = [c for c in candles if isinstance(c, dict) and c.get("ts", 0) > 0]
    candles.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return candles[:limit]


@app.get("/market/candles/1h")
async def get_candles_1h(limit: int = 64):
    candles = await redis_get_json_array(REDIS_CANDLES_1H)
    candles = [c for c in candles if isinstance(c, dict) and c.get("ts", 0) > 0]
    candles.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return candles[:limit]


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
    fp_bools  = data.get("footprint_bools", {})

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

    # B2: Footprint booleans summary
    fp_bool_lines = []
    if fp_bools:
        if fp_bools.get("absorption_detected"): fp_bool_lines.append("ABSORPTION detected (iceberg at extreme)")
        if fp_bools.get("exhaustion_detected"): fp_bool_lines.append("EXHAUSTION detected (<5 contracts at extreme)")
        if fp_bools.get("trapped_buyers"): fp_bool_lines.append("TRAPPED BUYERS (broke high, reversed below open)")
        sc = fp_bools.get("stacked_imbalance_count", 0)
        sd = fp_bools.get("stacked_imbalance_dir", "NONE")
        if sc >= 2: fp_bool_lines.append(f"STACKED IMBALANCE: {sc} levels x250% direction={sd}")
        if fp_bools.get("pullback_delta_declining"): fp_bool_lines.append("PULLBACK DELTA DECLINING (momentum fading)")
        if fp_bools.get("pullback_aggressive_buy"): fp_bool_lines.append("AGGRESSIVE BUY on pullback (+delta during dip)")
        if fp_bools.get("pullback_aggressive_sell"): fp_bool_lines.append("AGGRESSIVE SELL on pullback (-delta during rise)")
    fp_bool_str = " | ".join(fp_bool_lines) if fp_bool_lines else "No footprint signals"

    # B2: Volume exhaustion check
    vol_declining = rel_vol < 0.9
    cvd_d5 = cvd.get("d5", 0) or 0
    bar_delta = bar.get("delta", 0) or 0
    exhaustion_signs = []
    if vol_declining: exhaustion_signs.append("vol_declining")
    if (bar_delta > 0 and cvd_d5 < -20) or (bar_delta < 0 and cvd_d5 > 20): exhaustion_signs.append("cvd_divergence")
    if (bar_delta > 30 and price < vwap.get("value", price)) or (bar_delta < -30 and price > vwap.get("value", price)): exhaustion_signs.append("inverse_delta")
    vol_exh_str = f"{len(exhaustion_signs)}/3 signs: {', '.join(exhaustion_signs)}" if exhaustion_signs else "0/3 — no exhaustion"

    prompt = f"""אתה אנליסט בכיר למסחר ב-MES Futures. עקרון מנחה: איכות מעל כמות — עדיף לפספס 3 עסקאות מלהיכנס לאחת שגויה.

נתח לפי הסדר: 1.רמות → 2.Order Flow → 3.Footprint → 4.החלטה

═══ שלב 1: רמות ומבנה ═══
מחיר: {price} | Session: {session.get('phase','?')} דקה {session.get('min',-1)}
DayType: {day.get('type','?')} | IB: {session.get('ibh',0)}-{session.get('ibl',0)} (range={day.get('ib_range',0):.1f}) locked={session.get('ib_locked',False)}
Gap: {day.get('gap_type','FLAT')} ({day.get('gap',0):.2f}pt)

רמות מפתח:
  PDH={levels.get('prev_high',0)} | PDL={levels.get('prev_low',0)} | DO={levels.get('daily_open',0)}
  ONH={levels.get('overnight_high',0)} | ONL={levels.get('overnight_low',0)}
  VWAP={vwap.get('value',0)} (dist={vwap_dist:+.2f}, above={vwap.get('above',False)}, pullback={vwap.get('pullback',False)})
  POC={profile.get('poc',0)} (above={profile.get('above_poc',False)}) | VAH={profile.get('vah',0)} | VAL={profile.get('val',0)}
  Woodi: PP={woodi.get('pp',0)} R1={woodi.get('r1',0)} S1={woodi.get('s1',0)} R2={woodi.get('r2',0)} S2={woodi.get('s2',0)}

═══ שלב 2: Order Flow ═══
Delta נוכחי: {bar_delta:+.0f} | CVD: trend={cvd.get('trend','?')} d5={cvd_d5:+.0f} d20={cvd.get('d20',0):+.0f}
Volume: rel={rel_vol:.2f}x ({vol_ctx.get('context','NORMAL')})
Volume Exhaustion: {vol_exh_str}
MTF delta: 5m={mtf.get('m5',{{}}).get('delta',0):+.0f} | 15m={mtf.get('m15',{{}}).get('delta',0):+.0f} | 30m={mtf.get('m30',{{}}).get('delta',0):+.0f} | 60m={mtf.get('m60',{{}}).get('delta',0):+.0f}
CCI: 14={cci.get('cci14',0):.1f} 6={cci.get('cci6',0):.1f} trend={cci.get('trend','?')} | turbo_bull={cci.get('turbo_bull',False)} turbo_bear={cci.get('turbo_bear',False)}
OF: Absorption={of2.get('absorption_bull',False)} | LiqSweepLong={of2.get('liq_sweep_long',False)} | LiqSweepShort={of2.get('liq_sweep_short',False)}
Pattern: {candle_p.get('bar0','?')} | prev: {candle_p.get('bar1','?')} | Engulf: bull={candle_p.get('bull_engulf',False)} bear={candle_p.get('bear_engulf',False)}
5 נרות אחרונים: {last_5_str}

═══ שלב 3: Footprint (price-level analysis) ═══
{fp_bool_str}
Raw footprint (5 bars): {footprint_summary}

═══ שלב 4: החלטה ═══
Reversal vs Continuation table:
  Reversal (enter): long wick + close back | vol declining | CVD divergence | inverse delta | absorption/zero-print
  Continuation (don't enter): body closes beyond | vol increasing in direction | CVD matches | delta matches | imbalances support direction

סטאפ עדיף: LIQUIDITY SWEEP (Sweep → MSS → FVG)
  - Sweep: wick >= 1.5pt past level, close back
  - MSS: swing break + rel_vol > 1.2 + stacked imbalance 2+ levels x250%
  - FVG: gap 0.5-4pt within 10 bars, not cancelled (body beyond distal edge)
  - Volume exhaustion required: 2 of 3 signs (vol declining, CVD divergence, inverse delta)

כללים קשיחים:
1. סטופ > 8pt → NO_TRADE
2. T1 < 10pt → NO_TRADE
3. rel_vol < 0.8 → confidence max 50
4. DayType BALANCED/ROTATIONAL/NEUTRAL → confidence max 60
5. Volume supports direction (not exhaustion) → this is CONTINUATION not reversal → NO_TRADE
6. No absorption or exhaustion in footprint → lower confidence by 15

ניהול: C1=50% R:R 1:1 (move stop to BE) | C2=25% R:R 1:2 | C3=25% Runner to R1/S1 or R:R 1:3

JSON בלבד ללא backticks:
{{"direction":"LONG/SHORT/NO_TRADE","score":0-10,"confidence":0-100,"setup":"שם הסטאפ","setup_name":"LIQ_SWEEP/VWAP_PB/IB_RETEST","win_rate":0-85,"t1_win_rate":0-85,"t2_win_rate":0-65,"t3_win_rate":0-45,"entry":0.0,"stop":0.0,"target1":0.0,"target2":0.0,"target3":0.0,"risk_pts":0.0,"rr":"1:X","the_box":"low-high","anchor_line":0.0,"order_block":"low-high","invalidation":0.0,"rationale":"2-3 משפטים בעברית — ציין ממצא footprint + volume exhaustion + מבנה","geometric_notes":"הוראות ציור","warning":"אזהרות","time_estimate":"X-Y דקות ל-T1","wait_reason":"מה להמתין אם NO_TRADE","tl_color":"red/orange/green/green_bright"}}"""

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
                    "max_tokens": 1500,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
        result = resp.json()
        text = result.get("content", [{}])[0].get("text", "").strip()
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    text = part
                    break
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]
        if not text:
            raise ValueError("Empty AI response")
        log.info(f"AI raw response: {text[:300]}")
        # נסה לתקן JSON חתוך
        if text.count('{') > text.count('}'):
            text = text + '}'
        try:
            signal = json.loads(text)
        except json.JSONDecodeError:
            # החזר NO_TRADE במקום לזרוק שגיאה
            signal = {
                "direction": "NO_TRADE", "score": 0, "confidence": 0,
                "setup": "שגיאת פרסור", "win_rate": 0,
                "entry": 0, "stop": 0, "target1": 0, "target2": 0, "target3": 0,
                "risk_pts": 0, "rationale": "תגובת AI לא תקינה — נסה שוב",
                "tl_color": "red", "t1_win_rate": 0, "t2_win_rate": 0,
                "t3_win_rate": 0, "wait_reason": "נסה שוב בעוד דקה"
            }
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


@app.get("/market/pre-analysis")
async def pre_analysis():
    """B1: Fast deterministic pre-analysis — no AI call.
    Returns bias, confidence, levels, day_type, killzone, footprint, volume exhaustion.
    """
    data = await redis_get()
    if not data:
        return {"bias": "NEUTRAL", "confidence": 0, "reason": "No data from bridge"}

    price   = data.get("price", 0)
    cvd     = data.get("cvd", {})
    vwap    = data.get("vwap", {})
    session = data.get("session", {})
    profile = data.get("profile", {})
    levels  = data.get("levels", {})
    day     = data.get("day", {})
    vol_ctx = data.get("volume_context", {})
    fp_bools = data.get("footprint_bools", {})
    mtf     = data.get("mtf", {})

    # ── Bias from MTF alignment ──
    bullish_count = 0
    bearish_count = 0
    for tf_key in ["m5", "m15", "m30", "m60"]:
        tf_data = mtf.get(tf_key, {})
        if not tf_data:
            continue
        tf_c = tf_data.get("c", 0)
        tf_o = tf_data.get("o", 0)
        tf_delta = tf_data.get("delta", 0)
        if tf_c > tf_o and tf_delta > 0:
            bullish_count += 1
        elif tf_c < tf_o and tf_delta < 0:
            bearish_count += 1

    # CVD trend
    cvd_trend = cvd.get("trend", "NEUTRAL")
    if cvd_trend == "BULLISH":
        bullish_count += 1
    elif cvd_trend == "BEARISH":
        bearish_count += 1

    # VWAP position
    if vwap.get("above", False):
        bullish_count += 1
    else:
        bearish_count += 1

    # Profile position
    if profile.get("above_poc", False):
        bullish_count += 1
    else:
        bearish_count += 1

    total = bullish_count + bearish_count
    if total == 0:
        bias = "NEUTRAL"
        confidence = 0
    elif bullish_count > bearish_count:
        bias = "LONG"
        confidence = round(bullish_count / total * 100)
    elif bearish_count > bullish_count:
        bias = "SHORT"
        confidence = round(bearish_count / total * 100)
    else:
        bias = "NEUTRAL"
        confidence = 50

    # ── Volume exhaustion (2 of 3 signs) ──
    rel_vol = vol_ctx.get("rel_vol", 1) or 1
    vol_declining = rel_vol < 0.9
    cvd_divergence = False
    cvd_d5 = cvd.get("d5", 0) or 0
    if bias == "LONG" and cvd_d5 < -20:
        cvd_divergence = True
    elif bias == "SHORT" and cvd_d5 > 20:
        cvd_divergence = True
    inverse_delta = False
    bar_delta = (data.get("bar", {}) or {}).get("delta", 0)
    if bias == "LONG" and bar_delta < -30:
        inverse_delta = True
    elif bias == "SHORT" and bar_delta > 30:
        inverse_delta = True
    exhaustion_signs = sum([vol_declining, cvd_divergence, inverse_delta])
    volume_exhaustion = exhaustion_signs >= 2

    # ── Key levels with distance ──
    key_levels = []
    level_sources = {
        "PDH": levels.get("prev_high", 0),
        "PDL": levels.get("prev_low", 0),
        "ONH": levels.get("overnight_high", 0),
        "ONL": levels.get("overnight_low", 0),
        "DO":  levels.get("daily_open", 0),
        "IBH": session.get("ibh", 0),
        "IBL": session.get("ibl", 0),
        "VWAP": vwap.get("value", 0),
        "POC": profile.get("poc", 0),
        "VAH": profile.get("vah", 0),
        "VAL": profile.get("val", 0),
    }
    for name, lvl in level_sources.items():
        if lvl and lvl > 0:
            dist = round(price - lvl, 2)
            key_levels.append({"name": name, "price": lvl, "distance": dist})
    key_levels.sort(key=lambda x: abs(x["distance"]))

    return {
        "bias": bias,
        "confidence": confidence,
        "price": price,
        "day_type": day.get("type", "DEVELOPING"),
        "ib_locked": session.get("ib_locked", False),
        "volume_exhaustion": volume_exhaustion,
        "exhaustion_detail": {
            "vol_declining": vol_declining,
            "cvd_divergence": cvd_divergence,
            "inverse_delta": inverse_delta,
            "signs": exhaustion_signs,
        },
        "footprint_bools": fp_bools or {},
        "key_levels": key_levels[:10],
        "mtf_alignment": {
            "bullish": bullish_count,
            "bearish": bearish_count,
        },
        "vwap_above": vwap.get("above", False),
        "in_value_area": profile.get("in_va", False),
        "rel_vol": round(rel_vol, 2),
    }


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
