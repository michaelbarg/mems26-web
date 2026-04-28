import os
import json
import asyncio
import logging
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
REDIS_TRADE_STATUS  = "mems26:trade:status"
REDIS_DAILY_PNL     = "mems26:daily:pnl"
REDIS_DAILY_TRADES  = "mems26:daily:trades"
REDIS_TRADE_COMMAND = "mems26:trade:command"
COMMAND_TTL_SEC = 300  # 5 minutes for command pickup
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")


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


async def redis_set_key_ex(key: str, value, ttl_sec: int):
    """Set a Redis key with TTL (expire after ttl_sec seconds)."""
    if not REDIS_URL or not REDIS_TOKEN:
        return
    try:
        serialized = json.dumps(value) if not isinstance(value, str) else value
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{REDIS_URL}",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}",
                         "Content-Type": "application/json"},
                json=["SET", key, serialized, "EX", str(ttl_sec)],
                timeout=3.0
            )
            if resp.status_code != 200:
                log.warning(f"Redis set_key_ex({key}) HTTP {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        log.warning(f"Redis set_key_ex({key}) failed: {e}")


async def redis_set_key(key: str, value):
    """Set an arbitrary Redis key to a JSON-serializable value."""
    if not REDIS_URL or not REDIS_TOKEN:
        return
    try:
        serialized = json.dumps(value) if not isinstance(value, str) else value
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{REDIS_URL}/set/{key}",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}",
                         "Content-Type": "application/json"},
                content=serialized,
                timeout=3.0
            )
            if resp.status_code != 200:
                log.warning(f"Redis set_key({key}) HTTP {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        log.warning(f"Redis set_key({key}) failed: {e}")


async def redis_get_key(key: str):
    """Get an arbitrary Redis key, returns parsed JSON or None."""
    if not REDIS_URL or not REDIS_TOKEN:
        return None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{REDIS_URL}/get/{key}",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                timeout=3.0
            )
            val = resp.json().get("result")
            if val:
                parsed = json.loads(val) if isinstance(val, str) else val
                # Handle double-encoded JSON strings
                while isinstance(parsed, str):
                    parsed = json.loads(parsed)
                return parsed
    except Exception as e:
        log.warning(f"Redis get_key({key}) failed: {e}")
    return None


async def redis_delete_key(key: str):
    if not REDIS_URL or not REDIS_TOKEN:
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.get(
                f"{REDIS_URL}/del/{key}",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                timeout=3.0
            )
    except Exception as e:
        log.warning(f"Redis del({key}) failed: {e}")


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

    def client_count(self) -> int:
        return len(self._clients)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self._clients:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

manager = ConnectionManager()


async def _build_status_payload() -> dict:
    import time
    trade = await trade_status()
    cb    = await check_circuit_breaker()
    data  = await redis_get()

    # D7: Compute trade health if trade is open
    trade_health = None
    if isinstance(trade, dict) and trade.get("status") == "OPEN":
        try:
            from starlette.testclient import TestClient
        except Exception:
            pass
        # Inline health calc to avoid circular import
        health_score = 70  # baseline
        if data:
            price = data.get("price", 0)
            entry = trade.get("entry_price", 0)
            stop = trade.get("stop", 0)
            direction = trade.get("direction", "LONG")
            is_long = direction == "LONG"
            pnl = (price - entry) if is_long else (entry - price)
            risk = abs(entry - stop)
            dist_stop = (price - stop) if is_long else (stop - price)
            if risk > 0 and pnl > risk: health_score += 10
            elif pnl > 0: health_score += 5
            elif risk > 0 and pnl < -risk * 0.5: health_score -= 20
            elif pnl < 0: health_score -= 10
            if dist_stop < 1.0: health_score -= 25
            elif dist_stop < 2.0: health_score -= 10
            bar_delta = (data.get("bar", {}) or {}).get("delta", 0) or 0
            if is_long and bar_delta < -80: health_score -= 15
            elif not is_long and bar_delta > 80: health_score -= 15
            health_score = max(0, min(100, health_score))
        trade_health = health_score

    return {
        "type":            "status_update",
        "ts":              int(time.time()),
        "trade":           trade,
        "trade_health":    trade_health,
        "circuit_breaker": cb,
        "health": {"status": "ok", "has_data": data is not None},
    }

async def _ws_push_loop():
    while True:
        try:
            if manager.client_count() > 0:
                payload = await _build_status_payload()
                await manager.broadcast(payload)
        except Exception as e:
            log.warning(f"WS push error: {e}")
        await asyncio.sleep(2)

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(f"MEMS26 API Started | REDIS_URL={REDIS_URL} | HAS_TOKEN={bool(REDIS_TOKEN)} | PG={bool(DATABASE_URL)}")
    # Initialize Postgres
    from database import init_db, seed_from_redis, close_pool
    try:
        await init_db()
        # Seed from Redis on first run (idempotent — upsert)
        if DATABASE_URL:
            await seed_from_redis(redis_get_key, REDIS_URL, REDIS_TOKEN)
    except Exception as e:
        log.error(f"Postgres init failed: {e}")
    task = asyncio.create_task(_ws_push_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await close_pool()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://thunderous-sopapillas-7ddb4b.netlify.app", "http://localhost:3000", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
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
        return {"type": "no_data", "status": "waiting_for_bridge", "mode": _MODE}
    data["mode"] = _MODE
    return data


# ---------------------------------------------------------------------------
# V7.10.0: Vegas Tunnel state endpoint + filter
# ---------------------------------------------------------------------------

@app.get("/vegas/state")
async def get_vegas_state():
    """Returns current Vegas Tunnel state from market data."""
    import time as _time
    data = await redis_get()
    if not data:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": "VEGAS_NOT_AVAILABLE",
                     "message": "No market data available"})

    vegas = data.get("vegas")
    if vegas is None:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": "VEGAS_NOT_AVAILABLE",
                     "message": "Vegas state not yet computed (waiting for 50+ bars)"})

    # Check staleness via market data timestamp
    data_ts = data.get("ts", 0)
    age = int(_time.time()) - data_ts if data_ts > 0 else 9999
    if age > 60:
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": "VEGAS_STALE",
                     "message": f"Vegas data is {age}s old",
                     "last_updated": data_ts})

    vegas["received_at"] = data_ts
    return {"ok": True, "vegas": vegas}


def validate_setup_against_vegas(setup: dict, vegas: dict | None) -> bool:
    """
    V7.10.0: Returns True if setup direction aligns with Vegas trend.
    Not wired up yet — will be integrated after E2E test of Vegas data flow.
    """
    if vegas is None:
        log.warning("[VEGAS_FILTER] Setup rejected: no Vegas data")
        return False

    trend = vegas.get("trend")
    if trend == "NEUTRAL":
        log.info("[VEGAS_FILTER] Setup rejected: trend=NEUTRAL")
        return False

    direction = setup.get("direction", "").upper()
    if direction == "LONG" and trend != "BULLISH":
        log.info(f"[VEGAS_FILTER] Setup {setup.get('id')} REJECTED: "
                 f"direction=LONG vegas={trend}")
        return False

    if direction == "SHORT" and trend != "BEARISH":
        log.info(f"[VEGAS_FILTER] Setup {setup.get('id')} REJECTED: "
                 f"direction=SHORT vegas={trend}")
        return False

    log.info(f"[VEGAS_FILTER] Setup {setup.get('id')} ALLOWED: "
             f"direction={direction} vegas={trend}")
    return True


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


def _valid_candle(c: dict) -> bool:
    """Filter candles with null/None OHLC or bad timestamps."""
    if not isinstance(c, dict):
        return False
    ts = c.get("ts", 0)
    if not ts or ts < 1577836800:
        return False
    # Support both o/h/l/c and open/high/low/close formats
    o = c.get("o", c.get("open"))
    h = c.get("h", c.get("high"))
    l = c.get("l", c.get("low"))
    cl = c.get("c", c.get("close"))
    if o is None or h is None or l is None or cl is None:
        return False
    if h == 0 and l == 0:
        return False
    return True


def _aggregate_3m_to_tf(candles_3m: list, interval_sec: int, max_out: int) -> list:
    """Aggregate 3m candles into larger timeframe on-the-fly."""
    buckets = {}
    for c in candles_3m:
        ts = c.get("ts", 0)
        if ts <= 0:
            continue
        bucket = (ts // interval_sec) * interval_sec
        o = c.get("o", c.get("open", 0))
        h = c.get("h", c.get("high", 0))
        l = c.get("l", c.get("low", 999999))
        cl = c.get("c", c.get("close", 0))
        if bucket not in buckets:
            buckets[bucket] = {"ts": bucket, "open": o, "high": h, "low": l, "close": cl,
                               "buy": c.get("buy", 0), "sell": c.get("sell", 0),
                               "vol": c.get("vol", 0), "delta": c.get("delta", 0)}
        else:
            b = buckets[bucket]
            if h > b["high"]: b["high"] = h
            if l < b["low"]: b["low"] = l
            b["close"] = cl
            b["buy"] += c.get("buy", 0)
            b["sell"] += c.get("sell", 0)
            b["vol"] += c.get("vol", 0)
            b["delta"] = b["buy"] - b["sell"]
    result = sorted(buckets.values(), key=lambda x: x["ts"])
    result = [c for c in result if c["high"] > 0 and c["low"] < 999999]
    return result[-max_out:]


async def _get_3m_candles() -> list:
    """Read all 3m candles from Redis list."""
    raw = await redis_lrange(REDIS_CANDLES_KEY, 0, 959)
    candles = []
    for item in raw:
        try:
            c = item
            while isinstance(c, str):
                c = json.loads(c)
            if _valid_candle(c):
                candles.append(c)
        except Exception:
            continue
    candles.sort(key=lambda x: x.get("ts", 0))
    return candles


@app.get("/market/candles")
async def get_candles(limit: int = 960, tf: str = "3m"):
    candles_3m = await _get_3m_candles()
    if tf == "3m":
        return candles_3m[-limit:]
    # Aggregate 3m → requested TF on-the-fly (always up-to-date, no gaps)
    tf_config = {"5m": (300, 288), "15m": (900, 96), "30m": (1800, 48), "1h": (3600, 168)}
    if tf in tf_config:
        interval, max_out = tf_config[tf]
        return _aggregate_3m_to_tf(candles_3m, interval, min(limit, max_out))
    return candles_3m[-limit:]


@app.get("/market/candles/5m")
async def get_candles_5m(limit: int = 288):
    candles = await redis_get_json_array(REDIS_CANDLES_5M)
    candles = [c for c in candles if _valid_candle(c)]
    candles.sort(key=lambda x: x.get("ts", 0))
    return candles[-limit:]


@app.get("/market/candles/15m")
async def get_candles_15m(limit: int = 96):
    candles = await redis_get_json_array(REDIS_CANDLES_15M)
    candles = [c for c in candles if _valid_candle(c)]
    candles.sort(key=lambda x: x.get("ts", 0))
    return candles[-limit:]


@app.get("/market/candles/30m")
async def get_candles_30m(limit: int = 48):
    candles = await redis_get_json_array(REDIS_CANDLES_30M)
    candles = [c for c in candles if _valid_candle(c)]
    candles.sort(key=lambda x: x.get("ts", 0))
    return candles[-limit:]


@app.get("/market/candles/1h")
async def get_candles_1h(limit: int = 64):
    candles = await redis_get_json_array(REDIS_CANDLES_1H)
    candles = [c for c in candles if _valid_candle(c)]
    candles.sort(key=lambda x: x.get("ts", 0))
    return candles[-limit:]


# AI response cache — avoid re-calling Claude when candles haven't changed
_ai_cache: dict = {"key": "", "response": None, "ts": 0}
AI_CACHE_TTL = 45  # seconds


@app.get("/market/analyze")
async def market_analyze():
  try:
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
            "wait_reason": "Bridge לא פעיל", "markers": []
        }

    # Cache check: if last candle ts + price unchanged and cache fresh, return cached
    import time as _time
    cache_key = f"{data.get('ts',0)}:{data.get('price',0)}"
    if _ai_cache["key"] == cache_key and _ai_cache["response"] and (_time.time() - _ai_cache["ts"]) < AI_CACHE_TTL:
        log.info("AI cache hit")
        return _ai_cache["response"]

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
    bar_delta = bar.get("delta", 0) or 0
    cvd_d5    = cvd.get("d5", 0) or 0

    # ── B2: Compute macro bias (same logic as B1 pre-analysis) ──
    bullish_c, bearish_c = 0, 0
    for tf_key in ["m5", "m15", "m30", "m60"]:
        tf_d = mtf.get(tf_key, {})
        if tf_d.get("c", 0) > tf_d.get("o", 0) and tf_d.get("delta", 0) > 0: bullish_c += 1
        elif tf_d.get("c", 0) < tf_d.get("o", 0) and tf_d.get("delta", 0) < 0: bearish_c += 1
    if cvd.get("trend") == "BULLISH": bullish_c += 1
    elif cvd.get("trend") == "BEARISH": bearish_c += 1
    if vwap.get("above"): bullish_c += 1
    else: bearish_c += 1
    if profile.get("above_poc"): bullish_c += 1
    else: bearish_c += 1
    total_bc = bullish_c + bearish_c
    if total_bc == 0: macro_bias, bias_conf = "NEUTRAL", 0
    elif bullish_c > bearish_c: macro_bias, bias_conf = "LONG", round(bullish_c / total_bc * 100)
    elif bearish_c > bullish_c: macro_bias, bias_conf = "SHORT", round(bearish_c / total_bc * 100)
    else: macro_bias, bias_conf = "NEUTRAL", 50

    # Draw on Liquidity — nearest level in bias direction
    draw_on = "N/A"
    level_map = {"PDH": levels.get("prev_high",0), "PDL": levels.get("prev_low",0),
                 "ONH": levels.get("overnight_high",0), "ONL": levels.get("overnight_low",0),
                 "IBH": session.get("ibh",0), "IBL": session.get("ibl",0),
                 "R1": woodi.get("r1",0), "S1": woodi.get("s1",0)}
    if macro_bias == "LONG":
        targets = [(n,v) for n,v in level_map.items() if v > price]
        if targets: targets.sort(key=lambda x: x[1]); draw_on = f"{targets[0][0]}={targets[0][1]}"
    elif macro_bias == "SHORT":
        targets = [(n,v) for n,v in level_map.items() if v < price and v > 0]
        if targets: targets.sort(key=lambda x: -x[1]); draw_on = f"{targets[0][0]}={targets[0][1]}"

    # ── Fetch patterns (MSS/FVG status) from Redis ──
    patterns = await redis_get_json_array(REDIS_PATTERNS_KEY)
    mss_status = "NOT_DETECTED"
    mss_level = 0
    fvg_status = "NOT_DETECTED"
    fvg_entry = 0
    sweep_status = "NOT_DETECTED"
    for p in (patterns if isinstance(patterns, list) else []):
        pn = p.get("pattern", "")
        if pn == "LIQ_SWEEP":
            sweep_status = f"DETECTED {p.get('direction','')} @ {p.get('level_name','')}={p.get('level_price',0)}"
            mss_status = f"CONFIRMED @ {p.get('mss_level',0)} rel_vol={p.get('mss_rel_vol',0)}"
            fvg_status = f"ACTIVE {p.get('fvg_high',0)}-{p.get('fvg_low',0)}"
            fvg_entry = p.get("entry", 0)
        elif pn == "MSS" and mss_status == "NOT_DETECTED":
            mss_status = f"DETECTED {p.get('direction','')} @ {p.get('neckline',0)}"
            mss_level = p.get("neckline", 0)
        elif pn == "FVG" and fvg_status == "NOT_DETECTED":
            fvg_status = f"DETECTED {p.get('direction','')} entry={p.get('entry',0)}"
            fvg_entry = p.get("entry", 0)

    # ── Killzone (compute in ET) ──
    from datetime import datetime, timezone
    try:
        from zoneinfo import ZoneInfo
        et_now = datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        et_now = datetime.now(timezone.utc)
    et_min = et_now.hour * 60 + et_now.minute
    kz_zones = [("London", 180, 300), ("NY_Open", 570, 630), ("NY_Close", 900, 960)]
    kz_name, kz_left = "OUTSIDE", 0
    for name, start, end in kz_zones:
        if start <= et_min <= end:
            kz_name, kz_left = name, end - et_min
            break

    # ── Footprint booleans summary ──
    fp_lines = []
    if fp_bools:
        if fp_bools.get("absorption_detected"): fp_lines.append("ABSORPTION (iceberg at extreme)")
        if fp_bools.get("exhaustion_detected"): fp_lines.append("EXHAUSTION (<5 contracts at extreme)")
        if fp_bools.get("trapped_buyers"): fp_lines.append("TRAPPED BUYERS")
        sc = fp_bools.get("stacked_imbalance_count", 0)
        sd = fp_bools.get("stacked_imbalance_dir", "NONE")
        if sc >= 2: fp_lines.append(f"STACKED IMBALANCE {sc}x250% dir={sd}")
        if fp_bools.get("pullback_delta_declining"): fp_lines.append("PULLBACK DELTA DECLINING")
        if fp_bools.get("pullback_aggressive_buy"): fp_lines.append("AGGRESSIVE BUY on pullback")
        if fp_bools.get("pullback_aggressive_sell"): fp_lines.append("AGGRESSIVE SELL on pullback")
    fp_str = " | ".join(fp_lines) if fp_lines else "No footprint signals"

    # ── Volume exhaustion ──
    exhaustion_signs = []
    if rel_vol < 0.9: exhaustion_signs.append("vol_declining")
    if (bar_delta > 0 and cvd_d5 < -20) or (bar_delta < 0 and cvd_d5 > 20): exhaustion_signs.append("cvd_divergence")
    if (bar_delta > 30 and price < vwap.get("value", price)) or (bar_delta < -30 and price > vwap.get("value", price)): exhaustion_signs.append("inverse_delta")
    vol_exh_str = f"{len(exhaustion_signs)}/3: {', '.join(exhaustion_signs)}" if exhaustion_signs else "0/3 — no exhaustion"

    # ── Footprint raw ──
    fp_raw = data.get("footprint", [])
    footprint_summary = "N/A"
    if fp_raw and isinstance(fp_raw, list):
        fl = [f"Δ={fb.get('delta',0):+.0f} vol={fb.get('buy',0)+fb.get('sell',0):.0f}" for fb in fp_raw[-5:] if isinstance(fb, dict)]
        if fl: footprint_summary = " | ".join(fl)

    # ── Last 5 candles ──
    candles_raw = await redis_lrange(REDIS_CANDLES_KEY, 0, 4)
    last_5 = []
    for item in candles_raw:
        try:
            c = item
            while isinstance(c, str): c = json.loads(c)
            if isinstance(c, dict) and c.get("ts", 0) > 0: last_5.append(c)
        except Exception: continue
    last_5.sort(key=lambda x: x.get("ts", 0))
    last_5_str = " | ".join(f"O={c.get('o',0):.2f} H={c.get('h',0):.2f} L={c.get('l',0):.2f} C={c.get('c',0):.2f} Δ={c.get('delta',0):+.0f}" for c in last_5) if last_5 else "N/A"

    # Safe MTF access — mtf values can be None even when key exists
    _m5  = mtf.get('m5')  or {}
    _m15 = mtf.get('m15') or {}
    _m30 = mtf.get('m30') or {}
    _m60 = mtf.get('m60') or {}
    prompt = f"""אתה אנליסט בכיר למסחר ב-MES Futures. איכות מעל כמות — עדיף לפספס 3 עסקאות מלהיכנס לאחת שגויה.

═══ 1. CONTEXT — Macro Bias + Day Type + Killzone ═══
Macro Bias: {macro_bias} (confidence {bias_conf}%, MTF bull={bullish_c} bear={bearish_c})
Draw on Liquidity: {draw_on}
Day Type: {day.get('type','?')} | IB range={day.get('ib_range',0):.1f} locked={session.get('ib_locked',False)}
Session: {session.get('phase','?')} | minute {session.get('min',-1)}
Killzone: {kz_name} ({kz_left}min left) | Gap: {day.get('gap_type','FLAT')} ({day.get('gap',0):.2f}pt)

═══ 2. KEY LEVELS ═══
מחיר: {price}
  PDH={levels.get('prev_high',0)} | PDL={levels.get('prev_low',0)} | DO={levels.get('daily_open',0)}
  ONH={levels.get('overnight_high',0)} | ONL={levels.get('overnight_low',0)}
  IBH={session.get('ibh',0)} | IBL={session.get('ibl',0)}
  VWAP={vwap.get('value',0)} (dist={vwap_dist:+.2f}, above={vwap.get('above',False)}, pullback={vwap.get('pullback',False)})
  POC={profile.get('poc',0)} (above={profile.get('above_poc',False)}) | VAH={profile.get('vah',0)} | VAL={profile.get('val',0)}
  Woodi: PP={woodi.get('pp',0)} R1={woodi.get('r1',0)} S1={woodi.get('s1',0)} R2={woodi.get('r2',0)} S2={woodi.get('s2',0)}

═══ 3. ORDER FLOW + FOOTPRINT ═══
Delta: {bar_delta:+.0f} | CVD: trend={cvd.get('trend','?')} d5={cvd_d5:+.0f} d20={cvd.get('d20',0):+.0f}
Volume: rel={rel_vol:.2f}x ({vol_ctx.get('context','NORMAL')}) | Exhaustion: {vol_exh_str}
MTF delta: 5m={_m5.get('delta',0):+.0f} 15m={_m15.get('delta',0):+.0f} 30m={_m30.get('delta',0):+.0f} 60m={_m60.get('delta',0):+.0f}
CCI: 14={cci.get('cci14',0):.1f} 6={cci.get('cci6',0):.1f} trend={cci.get('trend','?')} turbo_bull={cci.get('turbo_bull',False)} turbo_bear={cci.get('turbo_bear',False)}
OF: Absorption={of2.get('absorption_bull',False)} LiqSweepLong={of2.get('liq_sweep_long',False)} LiqSweepShort={of2.get('liq_sweep_short',False)}
Candle: {candle_p.get('bar0','?')} prev={candle_p.get('bar1','?')} BullEngulf={candle_p.get('bull_engulf',False)} BearEngulf={candle_p.get('bear_engulf',False)}
Footprint: {fp_str}
Raw bars: {footprint_summary}
Last 5 candles: {last_5_str}

═══ 4. SETUP STATUS (Sweep → MSS → FVG chain) ═══
Sweep: {sweep_status}
MSS: {mss_status}
FVG: {fvg_status} (entry={fvg_entry})

═══ 5. DECISION ═══
כללים:
1. סטופ > 15pt → NO_TRADE
2. T1 < 10pt → NO_TRADE
3. rel_vol < 0.8 → confidence max 50
4. DayType BALANCED/ROTATIONAL/NEUTRAL → confidence max 60
5. Volume supports direction (not exhaustion) = CONTINUATION → NO_TRADE
6. No absorption/exhaustion in footprint → confidence -15
7. Killzone=OUTSIDE → confidence max 40

ניהול: C1=50% R:R 1:1 (stop→BE) | C2=25% R:R 1:2 | C3=25% Runner R1/S1 or 1:3

JSON בלבד ללא backticks:
{{"direction":"LONG/SHORT/NO_TRADE","score":0-10,"confidence":0-100,"setup":"שם הסטאפ בעברית","setup_name":"LIQ_SWEEP/VWAP_PB/IB_RETEST","win_rate":0-85,"t1_win_rate":0-85,"t2_win_rate":0-65,"t3_win_rate":0-45,"entry":0.0,"stop":0.0,"target1":0.0,"target2":0.0,"target3":0.0,"risk_pts":0.0,"rr":"1:X","the_box":"low-high","anchor_line":0.0,"order_block":"low-high","invalidation":0.0,"rationale":"2-3 משפטים בעברית — ציין bias, footprint, volume exhaustion, setup chain status","warning":"אזהרות","time_estimate":"X-Y דקות ל-T1","wait_reason":"מה להמתין אם NO_TRADE","tl_color":"red/orange/green/green_bright","markers":[{{"ts":unix_timestamp,"pos":"aboveBar/belowBar","shape":"arrowUp/arrowDown/circle","color":"#10b981/#ef4444/#f59e0b","text":"Entry/Sweep/MSS/FVG/Stop/T1"}}]}}

markers כללים:
- מקסימום 10 markers
- סמן את: נקודת Entry, Sweep bar, MSS bar, FVG zone, Stop, T1/T2
- ts = Unix timestamp של הנר הרלוונטי (השתמש ב-timestamps מה-5 נרות האחרונים שסופקו)
- LONG: Entry/Sweep → belowBar+arrowUp (#10b981), Stop → belowBar+circle (#ef4444)
- SHORT: Entry/Sweep → aboveBar+arrowDown (#ef4444), Stop → aboveBar+circle (#ef4444)
- MSS → circle (#f59e0b), FVG → circle (#8b5cf6)
- אם NO_TRADE → markers ריק []"""

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
                    "max_tokens": 1200,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
        result = resp.json()
        if result.get("type") == "error" or resp.status_code != 200:
            log.error(f"Claude API error: status={resp.status_code} body={str(result)[:300]}")
            raise ValueError(f"Claude API {resp.status_code}: {result.get('error', {}).get('message', str(result)[:100])}")
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
                "t3_win_rate": 0, "wait_reason": "נסה שוב בעוד דקה", "markers": []
            }
        signal["ts"] = data.get("ts", 0)
        # B3: Validate and cap markers
        markers = signal.get("markers", [])
        if not isinstance(markers, list):
            markers = []
        signal["markers"] = markers[:10]
        log.info(f"AI: {signal.get('direction')} score={signal.get('score')} win={signal.get('win_rate')}% markers={len(signal['markers'])}")
        # Store in cache
        _ai_cache["key"] = cache_key
        _ai_cache["response"] = signal
        _ai_cache["ts"] = _time.time()
        return signal
    except Exception as e:
        log.error(f"AI Claude call error: {e}")
        return {
            "direction": "NO_TRADE", "score": 0, "confidence": 0,
            "setup": "שגיאת AI", "win_rate": 0,
            "entry": 0, "stop": 0, "target1": 0, "target2": 0, "target3": 0,
            "risk_pts": 0, "rationale": f"שגיאת AI: {str(e)[:100]}",
            "tl_color": "red", "t1_win_rate": 0, "t2_win_rate": 0,
            "t3_win_rate": 0, "wait_reason": "נסה שוב בעוד דקה", "markers": [], "ts": 0
        }
  except Exception as e:
    import traceback
    tb = traceback.format_exc()
    log.error(f"market_analyze crashed: {e}\n{tb}")
    return {
        "direction": "NO_TRADE", "score": 0, "confidence": 0,
        "setup": "שגיאה פנימית", "win_rate": 0,
        "entry": 0, "stop": 0, "target1": 0, "target2": 0, "target3": 0,
        "risk_pts": 0, "rationale": f"שגיאה: {str(e)[:100]} | {tb[-200:]}",
        "tl_color": "red", "t1_win_rate": 0, "t2_win_rate": 0,
        "t3_win_rate": 0, "wait_reason": "שגיאה פנימית — בדוק logs", "markers": [], "ts": 0
    }


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


def _ema(values: list[float], period: int) -> list[float]:
    """Compute EMA over a list of floats, oldest-first."""
    if not values:
        return []
    k = 2 / (period + 1)
    ema = [values[0]]
    for v in values[1:]:
        ema.append(v * k + ema[-1] * (1 - k))
    return ema


def _swing_points(candles: list[dict], lookback: int = 5) -> dict:
    """Find recent swing highs/lows for HH/HL/LH/LL detection."""
    highs, lows = [], []
    for i in range(lookback, len(candles) - lookback):
        h = candles[i].get("h", 0)
        l = candles[i].get("l", 0)
        if all(h >= candles[j].get("h", 0) for j in range(i - lookback, i + lookback + 1) if j != i):
            highs.append(h)
        if all(l <= candles[j].get("l", 0) for j in range(i - lookback, i + lookback + 1) if j != i):
            lows.append(l)
    return {"highs": highs[-4:], "lows": lows[-4:]}


def _detect_trend(swings: dict) -> str:
    """HH+HL=BULLISH, LH+LL=BEARISH, else NEUTRAL."""
    highs, lows = swings["highs"], swings["lows"]
    if len(highs) >= 2 and len(lows) >= 2:
        hh = highs[-1] > highs[-2]
        hl = lows[-1] > lows[-2]
        lh = highs[-1] < highs[-2]
        ll = lows[-1] < lows[-2]
        if hh and hl:
            return "BULLISH"
        if lh and ll:
            return "BEARISH"
    return "NEUTRAL"


def _draw_on_liquidity(price: float, levels: dict, bias: str) -> dict:
    """Find the next liquidity target in the bias direction."""
    targets = []
    for name, val in levels.items():
        if not val or val == 0:
            continue
        if bias == "BULLISH" and val > price:
            targets.append({"level": name, "price": val, "dist": val - price})
        elif bias == "BEARISH" and val < price:
            targets.append({"level": name, "price": val, "dist": price - val})
    if not targets:
        return {"level": "none", "price": 0, "dist": 0}
    targets.sort(key=lambda x: x["dist"])
    return targets[0]


@app.get("/market/bias")
async def market_bias():
    """B1: Pre-Analysis Rule-Based Macro Bias from 15m + 1H candles."""
    data = await redis_get()
    price = data.get("price", 0) if data else 0
    session = data.get("session", {}) if data else {}
    vwap_val = data.get("vwap", {}).get("value", 0) if data else 0
    profile = data.get("profile", {}) if data else {}

    # Read 15m and 1H candles
    candles_15m_raw = await redis_get_json_array(REDIS_CANDLES_15M)
    candles_1h_raw = await redis_get_json_array(REDIS_CANDLES_1H)

    def parse_candles(raw: list) -> list[dict]:
        out = []
        for c in raw:
            if isinstance(c, str):
                try:
                    c = json.loads(c)
                except Exception:
                    continue
            if isinstance(c, dict) and c.get("ts", 0) > 0:
                out.append(c)
        out.sort(key=lambda x: x.get("ts", 0))
        return out

    c15 = parse_candles(candles_15m_raw)
    c1h = parse_candles(candles_1h_raw)

    # EMA on 15m closes
    closes_15m = [c.get("c", 0) for c in c15]
    ema20_15m = _ema(closes_15m, 20)
    ema50_15m = _ema(closes_15m, 50)

    # EMA on 1H closes
    closes_1h = [c.get("c", 0) for c in c1h]
    ema20_1h = _ema(closes_1h, 20)
    ema50_1h = _ema(closes_1h, 50)

    # Current EMA values
    e20_15 = ema20_15m[-1] if ema20_15m else 0
    e50_15 = ema50_15m[-1] if ema50_15m else 0
    e20_1h = ema20_1h[-1] if ema20_1h else 0
    e50_1h = ema50_1h[-1] if ema50_1h else 0

    # EMA trend: price above both EMAs = bullish, below both = bearish
    ema_trend_15m = "BULLISH" if price > e20_15 > e50_15 else ("BEARISH" if price < e20_15 < e50_15 else "NEUTRAL")
    ema_trend_1h = "BULLISH" if price > e20_1h > e50_1h else ("BEARISH" if price < e20_1h < e50_1h else "NEUTRAL")

    # Swing structure on 1H
    swings_1h = _swing_points(c1h, lookback=3) if len(c1h) >= 10 else {"highs": [], "lows": []}
    structure_trend = _detect_trend(swings_1h)

    # Combined bias: majority vote of 3 signals
    votes = [ema_trend_15m, ema_trend_1h, structure_trend]
    bull = votes.count("BULLISH")
    bear = votes.count("BEARISH")
    if bull >= 2:
        bias = "BULLISH"
    elif bear >= 2:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    # Confidence: 3/3 agree = 85, 2/3 = 65, mixed = 40
    if bull == 3 or bear == 3:
        confidence = 85
    elif bull == 2 or bear == 2:
        confidence = 65
    else:
        confidence = 40

    # Key levels for Draw on Liquidity
    key_levels = {
        "PDH": data.get("levels", {}).get("prev_high", 0) if data else 0,
        "PDL": data.get("levels", {}).get("prev_low", 0) if data else 0,
        "ONH": data.get("levels", {}).get("overnight_high", 0) if data else 0,
        "ONL": data.get("levels", {}).get("overnight_low", 0) if data else 0,
        "VWAP": vwap_val,
        "POC": profile.get("poc", 0),
        "VAH": profile.get("vah", 0),
        "VAL": profile.get("val", 0),
        "IBH": session.get("ibh", 0),
        "IBL": session.get("ibl", 0),
    }

    dol = _draw_on_liquidity(price, key_levels, bias)

    return {
        "bias": bias,
        "confidence": confidence,
        "ema_trend": {
            "15m": ema_trend_15m,
            "1h": ema_trend_1h,
            "ema20_15m": round(e20_15, 2),
            "ema50_15m": round(e50_15, 2),
            "ema20_1h": round(e20_1h, 2),
            "ema50_1h": round(e50_1h, 2),
        },
        "structure": structure_trend,
        "swing_highs": swings_1h["highs"],
        "swing_lows": swings_1h["lows"],
        "draw_on_liquidity": dol,
        "key_levels": key_levels,
        "price": price,
        "candle_counts": {"15m": len(c15), "1h": len(c1h)},
    }


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
                parsed = json.loads(val)
                # Handle double-encoded JSON strings
                if isinstance(parsed, str):
                    parsed = json.loads(parsed)
                if isinstance(parsed, list):
                    # Defense-in-depth: filter stop validation + price-past-entry
                    data = await redis_get()
                    cur_price = data.get("price", 0) if data else 0
                    filtered = []
                    for p in parsed:
                        risk = abs(p.get("entry", 0) - p.get("stop", 0))
                        if risk < 3.0 or risk > 15.0:
                            continue
                        d = p.get("direction", "")
                        e = p.get("entry", 0)
                        if cur_price > 0 and d == "LONG" and cur_price > e:
                            continue
                        if cur_price > 0 and d == "SHORT" and cur_price < e:
                            continue
                        filtered.append(p)
                    return {"patterns": filtered}
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


@app.get("/trades/log")
async def get_trade_log(
    limit: int = 50,
    is_shadow: Optional[str] = None,
    day_type: Optional[str] = None,
    killzone: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
):
    """Return last N closed trades, newest first. Uses Postgres when available."""
    from database import get_trades_log as pg_get_trades, get_pool

    # Try Postgres first
    pool = await get_pool()
    if pool:
        shadow = None
        if is_shadow == "true":
            shadow = True
        elif is_shadow == "false":
            shadow = False
        trades = await pg_get_trades(
            limit=limit, is_shadow=shadow,
            day_type=day_type, killzone=killzone,
            from_date=from_date, to_date=to_date,
        )
    else:
        # Fallback to Redis
        trades = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{REDIS_URL}/keys/mems26:tradelog:*",
                    headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                    timeout=5.0
                )
                keys = resp.json().get("result", [])
                if keys:
                    keys.sort(reverse=True)
                    for key in keys[:limit]:
                        val = await redis_get_key(key)
                        if val and isinstance(val, dict):
                            trades.append(val)
        except Exception as e:
            log.error(f"/trades/log keys failed: {e}")

    # Also include current trade if CLOSED but not yet in log
    try:
        active = await redis_get_key(REDIS_TRADE_STATUS)
        if active and isinstance(active, dict) and active.get("status") == "CLOSED":
            if not any(t.get("id") == active.get("id") for t in trades):
                trades.insert(0, active)
    except Exception:
        pass

    # Enrich each trade with computed fields
    for t in trades:
        entry_ts = t.get("entry_ts", 0)
        exit_ts = t.get("exit_ts", 0)
        if entry_ts and exit_ts:
            t["duration_min"] = round((exit_ts - entry_ts) / 60, 1)
        risk = t.get("risk_pts", 0)
        pnl = t.get("pnl_pts", 0)
        if risk and risk > 0:
            t["rr_actual"] = round(abs(pnl) / risk, 2)
        t["win"] = pnl > 0

    return trades


@app.post("/trades/log/test")
async def create_test_trade():
    """Create a dummy closed trade in Redis for testing the trade log display."""
    import time
    ts = int(time.time())
    trade = {
        "id": f"TEST_{ts}", "direction": "LONG",
        "entry_price": 7009.75, "exit_price": 7006.50,
        "stop": 7004.75, "t1": 7014.75, "t2": 7019.75, "t3": 0,
        "risk_pts": 5.0, "setup_type": "LIQUIDITY_SWEEP",
        "entry_ts": ts - 480, "exit_ts": ts,
        "status": "CLOSED", "close_reason": "STOP",
        "pnl_pts": -3.25, "pnl_usd": -16.25,
        "killzone": "NY_Open", "day_type": "NORMAL",
    }
    await redis_set_key(f"mems26:tradelog:{ts}", trade)
    try:
        from database import insert_trade
        await insert_trade(trade)
    except Exception as e:
        log.warning(f"Postgres test trade failed: {e}")
    return {"ok": True, "trade": trade}


@app.post("/trades/log/shadow")
async def save_shadow_trade(request: Request, x_bridge_token: Optional[str] = Header(None)):
    """Persist a shadow trade from the bridge shadow engine."""
    if x_bridge_token != BRIDGE_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    trade = await request.json()
    trade["is_shadow"] = True
    try:
        from database import insert_trade
        await insert_trade(trade)
    except Exception as e:
        log.warning(f"Shadow trade persist failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True}


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


@app.post("/trade/health")
async def trade_health(request: Request):
    """B3: Fast deterministic trade health check — no AI call.
    Accepts: {direction, entry_price, stop, t1, t2, t3, entry_ts}
    Returns: health_score 0-100, status HEALTHY/WARNING/DANGER, action HOLD/MOVE_BE/EXIT
    """
    body = await request.json()
    direction  = body.get("direction", "LONG")
    entry      = body.get("entry_price", 0)
    stop       = body.get("stop", 0)
    t1         = body.get("t1", 0)
    t2         = body.get("t2", 0)
    entry_ts   = body.get("entry_ts", 0)

    data = await redis_get()
    if not data:
        return {"health_score": 50, "status": "WARNING", "action": "HOLD", "reason": "No market data"}

    price    = data.get("price", 0)
    cvd      = data.get("cvd", {})
    vwap     = data.get("vwap", {})
    vol_ctx  = data.get("volume_context", {})
    fp_bools = data.get("footprint_bools", {})
    mtf      = data.get("mtf", {})
    day      = data.get("day", {})

    is_long = direction == "LONG"
    pnl_pts = (price - entry) if is_long else (entry - price)
    dist_stop = (price - stop) if is_long else (stop - price)
    risk = abs(entry - stop)

    # Start at 70 (healthy baseline)
    score = 70
    warnings = []

    # ── P&L factor ──
    if pnl_pts > risk:
        score += 10  # past 1R = great
    elif pnl_pts > 0:
        score += 5   # in profit
    elif pnl_pts < -risk * 0.5:
        score -= 20  # losing more than half risk
        warnings.append(f"PnL {pnl_pts:+.2f}pt — over half risk lost")
    elif pnl_pts < 0:
        score -= 10  # small loss

    # ── Distance to stop ──
    if dist_stop < 1.0:
        score -= 25
        warnings.append(f"Only {dist_stop:.2f}pt from stop")
    elif dist_stop < 2.0:
        score -= 10
        warnings.append(f"{dist_stop:.2f}pt from stop")

    # ── Delta alignment ──
    bar_delta = (data.get("bar", {}) or {}).get("delta", 0) or 0
    if is_long and bar_delta < -80:
        score -= 15
        warnings.append(f"Strong negative delta {bar_delta:+.0f}")
    elif not is_long and bar_delta > 80:
        score -= 15
        warnings.append(f"Strong positive delta {bar_delta:+.0f}")

    # ── CVD alignment ──
    cvd_d5 = cvd.get("d5", 0) or 0
    if is_long and cvd_d5 < -50:
        score -= 10
        warnings.append("CVD 5-bar diverging against LONG")
    elif not is_long and cvd_d5 > 50:
        score -= 10
        warnings.append("CVD 5-bar diverging against SHORT")

    # ── VWAP cross ──
    vwap_val = vwap.get("value", 0) or 0
    if vwap_val > 0:
        if is_long and price < vwap_val - 2:
            score -= 10
            warnings.append("Price fell below VWAP")
        elif not is_long and price > vwap_val + 2:
            score -= 10
            warnings.append("Price broke above VWAP")

    # ── Volume dying ──
    rel_vol = vol_ctx.get("rel_vol", 1) or 1
    if rel_vol < 0.5:
        score -= 10
        warnings.append(f"Very low volume ({rel_vol:.2f}x)")

    # ── Footprint adverse signals ──
    if fp_bools:
        if is_long and fp_bools.get("pullback_aggressive_sell"):
            score -= 15
            warnings.append("Aggressive selling detected")
        if not is_long and fp_bools.get("pullback_aggressive_buy"):
            score -= 15
            warnings.append("Aggressive buying detected")
        if fp_bools.get("trapped_buyers") and is_long:
            score -= 10
            warnings.append("Trapped buyers pattern")

    # ── MTF momentum fade ──
    m15_delta = mtf.get("m15", {}).get("delta", 0) or 0
    if is_long and m15_delta < -100:
        score -= 5
    elif not is_long and m15_delta > 100:
        score -= 5

    # ── Time decay (staleness after 45min) ──
    if entry_ts > 0:
        import time
        elapsed_min = (time.time() - entry_ts) / 60
        if elapsed_min > 60 and pnl_pts < risk * 0.5:
            score -= 10
            warnings.append(f"Trade open {int(elapsed_min)}min with small progress")

    # Clamp
    score = max(0, min(100, score))

    # Status + action
    if score >= 70:
        status = "HEALTHY"
        action = "HOLD"
    elif score >= 40:
        status = "WARNING"
        action = "MOVE_BE" if pnl_pts > 0 else "HOLD"
    else:
        status = "DANGER"
        action = "EXIT" if pnl_pts < 0 else "MOVE_BE"

    return {
        "health_score": score,
        "status": status,
        "action": action,
        "pnl_pts": round(pnl_pts, 2),
        "pnl_usd": round(pnl_pts * 5, 2),
        "dist_stop": round(dist_stop, 2),
        "warnings": warnings,
        "day_type": day.get("type", ""),
        "rel_vol": round(rel_vol, 2),
    }


# ── Phase C: Semi-Auto Trading ────────────────────────────────────────────

# Circuit Breaker thresholds — MODE-aware (env MEMS26_MODE=SIM|LIVE)
_MODE = os.getenv("MEMS26_MODE", "SIM").upper()
CB_SOFT_LIMIT    = 150 if _MODE == "SIM" else 100   # $/day → lock 30 min
CB_HARD_LIMIT    = 200                                # $/day → lock until next day
CB_MAX_TRADES    = 3                                    # max trades/day (V6.1 spec)
CB_CONSEC_LOSSES = 2                                   # consecutive losses → lock 30 min
CB_LOCK_MIN      = 30                                  # lock duration in minutes
CONTRACTS        = 3   if _MODE == "SIM" else 1        # MES contracts per trade
STOP_MIN_PT      = 3.0                                 # minimum stop distance
STOP_MAX_PT      = 15.0                                # maximum stop distance → NO_TRADE
T1_RR            = 1.5                                 # T1 = risk × 1.5
T1_MIN_PT        = 10.0                                # T1 minimum 10pt
T2_RR            = 3.0                                 # T2 = risk × 3


async def get_daily_state() -> dict:
    """Get daily P&L and trade count from Redis."""
    state = await redis_get_key(REDIS_DAILY_PNL)
    if not state or not isinstance(state, dict):
        state = {"pnl": 0, "trade_count": 0, "consecutive_losses": 0,
                 "locked_until": 0, "hard_locked": False, "date": ""}
    return state


async def save_daily_state(state: dict):
    await redis_set_key(REDIS_DAILY_PNL, state)


async def check_circuit_breaker() -> dict:
    """Check if trading is allowed. Returns {allowed, reason, lock_minutes}."""
    import time
    state = await get_daily_state()

    # Reset if new day
    today = __import__("datetime").date.today().isoformat()
    if state.get("date") != today:
        state = {"pnl": 0, "trade_count": 0, "consecutive_losses": 0,
                 "locked_until": 0, "hard_locked": False, "date": today}
        await save_daily_state(state)

    now = time.time()

    # Hard lock — until next day
    if state.get("hard_locked"):
        return {"allowed": False, "reason": f"Hard lock: daily loss ${abs(state['pnl']):.0f} >= ${CB_HARD_LIMIT}", "lock_minutes": -1}

    # Soft lock — timed
    locked_until = state.get("locked_until", 0)
    if locked_until > now:
        remaining = int((locked_until - now) / 60)
        return {"allowed": False, "reason": f"Locked for {remaining} more minutes", "lock_minutes": remaining}

    # Max trades
    if state.get("trade_count", 0) >= CB_MAX_TRADES:
        return {"allowed": False, "reason": f"Max {CB_MAX_TRADES} trades/day reached", "lock_minutes": -1}

    return {"allowed": True, "reason": "", "lock_minutes": 0}


def _make_checksum(cmd: str, price: float, qty: int, stop: float,
                   trade_id: str, expires_at: int) -> tuple:
    import hashlib
    # Must match C++ format: std::fixed << std::setprecision(2)
    raw = f"{cmd}:{price:.2f}:{qty}:{stop:.2f}:{trade_id}:{expires_at}:{BRIDGE_TOKEN}"
    return hashlib.sha256(raw.encode()).hexdigest(), raw


@app.get("/trade/circuit-breaker")
async def get_circuit_breaker():
    """Check circuit breaker status."""
    cb = await check_circuit_breaker()
    state = await get_daily_state()
    return {
        **cb,
        "daily_pnl": state.get("pnl", 0),
        "trade_count": state.get("trade_count", 0),
        "consecutive_losses": state.get("consecutive_losses", 0),
        "soft_limit": CB_SOFT_LIMIT,
        "hard_limit": CB_HARD_LIMIT,
        "max_trades": CB_MAX_TRADES,
    }


@app.post("/trade/circuit-breaker/reset")
async def reset_circuit_breaker(x_bridge_token: Optional[str] = Header(None)):
    """Reset circuit breaker: clear trade count, PnL, locks."""
    if x_bridge_token != BRIDGE_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    today = __import__("datetime").date.today().isoformat()
    state = {"pnl": 0, "trade_count": 0, "consecutive_losses": 0,
             "locked_until": 0, "hard_locked": False, "date": today}
    await save_daily_state(state)
    log.info("Circuit breaker RESET by user")
    return {"ok": True, "state": state}


@app.post("/trade/execute")
async def trade_execute(request: Request):
    """C1: Semi-auto trade execution.
    Accepts: {direction, entry_price, stop, t1, t2, t3, setup_type}
    Validates circuit breaker, stores trade status in Redis.
    """
    import time
    try:
        # Parse body first — validate inputs before guards
        body = await request.json()
        direction  = body.get("direction", "")
        entry      = body.get("entry_price", 0)
        stop       = body.get("stop", 0)
        t1         = body.get("t1", 0)
        t2         = body.get("t2", 0)
        t3         = body.get("t3", 0)
        setup_type = body.get("setup_type", "MANUAL")

        if direction not in ("LONG", "SHORT"):
            raise HTTPException(status_code=400, detail="direction must be LONG or SHORT")
        if entry <= 0 or stop <= 0:
            raise HTTPException(status_code=400, detail="entry_price and stop required")
        if not t1 or not t2 or not t3:
            raise HTTPException(status_code=400, detail="V6.7.0 requires t1, t2, t3 from Frontend")

        # W1.5 — Early stop validation (before killzone/news checks)
        raw_risk = abs(entry - stop)
        if raw_risk > STOP_MAX_PT:
            raise HTTPException(status_code=400, detail=f"STOP_TOO_WIDE: {raw_risk:.2f}pt > {STOP_MAX_PT}pt max")

        # V6.5.2: Read entry mode from bridge config in Redis
        _exec_entry_mode = "STRICT"
        try:
            _bridge_cfg = await redis_get_key("mems26:bridge_config")
            if _bridge_cfg and isinstance(_bridge_cfg, dict):
                _exec_entry_mode = _bridge_cfg.get("entry_mode", "STRICT")
        except Exception:
            pass
        # V6.7.2: X-Test-Override header — skip entry gates in DEMO
        _test_override = request.headers.get("x-test-override", "").lower() == "true"
        if _test_override:
            # Allow body entry_mode to override Redis config for curl testing
            _body_mode = body.get("entry_mode", "")
            if _body_mode == "DEMO":
                _exec_entry_mode = "DEMO"
            if _exec_entry_mode != "DEMO":
                raise HTTPException(status_code=403, detail="X-Test-Override only allowed in DEMO")
        _skip_gates = _test_override and _exec_entry_mode == "DEMO"
        log.info(f"[EXECUTE] entry_mode={_exec_entry_mode} test_override={_test_override}")

        # Circuit breaker check (skip in DEMO or test override)
        if _exec_entry_mode not in ("DEMO", "RESEARCH") and not _skip_gates:
            try:
                cb = await check_circuit_breaker()
            except Exception as e:
                log.warning(f"Circuit breaker check failed: {e}")
                cb = {"allowed": True, "reason": "CB check failed -- proceeding"}
            if not cb["allowed"]:
                raise HTTPException(status_code=403, detail=cb["reason"])

        # Killzone enforcement (skip in DEMO — tag only)
        from datetime import datetime as _dt
        from zoneinfo import ZoneInfo as _ZI
        _now_et = _dt.now(_ZI("America/New_York"))
        _t = _now_et.hour * 60 + _now_et.minute
        _KILLZONES = [
            ("London",   3*60,        5*60),
            ("NY_Open",  9*60+30,     10*60+30),
            ("NY_Close", 15*60,       16*60),
        ]
        _in_kz = any(start <= _t < end for _, start, end in _KILLZONES)
        if not _in_kz and _exec_entry_mode not in ("DEMO", "RESEARCH") and not _skip_gates:
            raise HTTPException(status_code=403,
                detail=f"Outside killzone -- {_now_et.strftime('%H:%M')} ET. Windows: London 03-05, NY Open 09:30-10:30, NY Close 15-16")

        # News guard check — block during PRE_NEWS_FREEZE
        try:
            news_state = await redis_get_key("mems26:news:state")
            if news_state and isinstance(news_state, dict):
                if news_state.get("state") == "PRE_NEWS_FREEZE":
                    ev = news_state.get("active_event", {})
                    raise HTTPException(status_code=403,
                        detail=f"PRE_NEWS_FREEZE: {ev.get('title', '?')} @ {ev.get('time_et', '?')} ET")
        except HTTPException:
            raise
        except Exception as e:
            log.warning(f"News guard check failed: {e} — proceeding")

        # V7.10.0: Vegas Tunnel trend filter
        if _skip_gates:
            log.info("[VEGAS_FILTER] BYPASSED (test override)")
        else:
            try:
                _mkt = await redis_get()
                _vegas = _mkt.get("vegas") if _mkt else None
                if _vegas and isinstance(_vegas, dict):
                    _setup_data = {"id": setup_type, "direction": direction}
                    if not validate_setup_against_vegas(_setup_data, _vegas):
                        raise HTTPException(status_code=400, detail=json.dumps({
                            "ok": False,
                            "error": "VEGAS_FILTER_REJECT",
                            "message": "Setup direction conflicts with Vegas trend",
                            "details": {
                                "setup_direction": direction,
                                "vegas_trend": _vegas.get("trend"),
                                "vegas_price_position": _vegas.get("price_position"),
                            }
                        }))
                    log.info(f"[VEGAS_FILTER] Setup {setup_type} APPROVED: "
                             f"direction={direction} aligned with vegas={_vegas.get('trend')}")
                else:
                    log.info("[VEGAS_FILTER] No Vegas data — allowing trade")
            except HTTPException:
                raise
            except Exception as e:
                log.warning(f"Vegas filter check failed: {e} — proceeding")

        # Validate: BUY only if no open position
        cmd_type = body.get("cmd_type", "BUY")  # BUY or CLOSE
        if cmd_type == "CLOSE":
            check_active = await redis_get_key(REDIS_TRADE_STATUS)
            if not check_active or check_active.get("status") != "OPEN":
                raise HTTPException(status_code=400, detail="אין פוזיציה פתוחה לסגירה")

        # Check no active trade — force_clear overrides
        force_clear = body.get("force_clear", False)
        is_replacement = False
        active = await redis_get_key(REDIS_TRADE_STATUS)
        if active and active.get("status") == "OPEN":
            if force_clear:
                await redis_delete_key(REDIS_TRADE_STATUS)
                await redis_delete_key(REDIS_TRADE_COMMAND)
                is_replacement = True  # don't double-count
                log.info(f"Force-cleared active trade {active.get('id')} and pending command")
            else:
                raise HTTPException(status_code=409, detail="Trade already open")

        risk = abs(entry - stop)

        # W1.5 — Stop expansion (too-wide already rejected above)
        if risk < STOP_MIN_PT:
            # Expand stop to minimum distance
            old_stop = stop
            if direction == "LONG":
                stop = entry - STOP_MIN_PT
            else:
                stop = entry + STOP_MIN_PT
            risk = STOP_MIN_PT
            log.info(f"[W1.5] Stop expanded: {old_stop:.2f} → {stop:.2f} (min {STOP_MIN_PT}pt)")

        # V6.5.6: Use frontend's t1/t2/t3 directly — they are already computed
        # from the setup's entry/stop/risk by calcLevels() in Dashboard.tsx.
        # Previous code recalculated targets here using T1_RR/T2_RR/T1_MIN_PT,
        # which overwrote the frontend values and caused the 7147.50 bug.
        # Only recompute if targets are missing/zero (manual trade fallback).
        if not t1 or t1 <= 0:
            t1 = round(entry + risk * T1_RR, 2) if direction == "LONG" else round(entry - risk * T1_RR, 2)
        if not t2 or t2 <= 0:
            t2 = round(entry + risk * T2_RR, 2) if direction == "LONG" else round(entry - risk * T2_RR, 2)

        # POST_NEWS tagging — tag trades within 60m of news event
        news_tag = ""
        try:
            news_state = await redis_get_key("mems26:news:state")
            if news_state and isinstance(news_state, dict):
                ns = news_state.get("state", "")
                if ns in ("POST_NEWS_OPPORTUNITY", "UNFREEZE"):
                    news_tag = "POST_NEWS"
                    ev = news_state.get("active_event", {})
                    log.info(f"[NEWS] Trade tagged POST_NEWS — event: {ev.get('title', '?')}")
        except Exception:
            pass

        trade_id = f"T{int(time.time())}"
        trade = {
            "id": trade_id,
            "direction": direction,
            "entry_price": entry,
            "stop": stop,
            "t1": t1,
            "t2": t2,
            "t3": t3,
            "risk_pts": round(risk, 2),
            "setup_type": setup_type,
            "entry_ts": int(time.time()),
            "status": "OPEN",
            "c1_status": "OPEN",
            "c2_status": "OPEN",
            "c3_status": "OPEN",
            "stop_status": "PENDING",
            "c1_fill_price": None,
            "c2_fill_price": None,
            "c3_fill_price": None,
            "stop_fill_price": None,
            "c1_order_id": None,
            "c2_order_id": None,
            "c3_order_id": None,
            "stop_c1_order_id": None,
            "stop_c2_order_id": None,
            "stop_c3_order_id": None,
            "parent_order_id": None,
            "active_management_state": "NORMAL",
            "pnl_pts": 0,
            "pnl_usd": 0,
            "news_tag": news_tag,
            "contracts": CONTRACTS,
            "is_test": _test_override,
        }

        # Snapshot market context at entry for analytics
        try:
            from analytics import snapshot_market_context
            data_snap = await redis_get()
            ctx = snapshot_market_context(data_snap) if data_snap else {}
            trade.update(ctx)
            trade["post_news"] = bool(news_tag)
            # Pillar count from frontend is not available here; set to 0, updated at close
            trade["pillars_passed"] = 0
            trade["pillar_detail"] = ""
        except Exception as e:
            log.warning(f"Context snapshot failed: {e}")

        log.info(f"[EXECUTE] step 1: writing trade status {trade_id}")
        await redis_set_key(REDIS_TRADE_STATUS, trade)
        log.info(f"[EXECUTE] step 2: trade status written OK")

        import time as _time
        expires_at = int(_time.time()) + COMMAND_TTL_SEC
        cmd_str = "BUY" if direction == "LONG" else "SELL"
        chk_hex, chk_raw = _make_checksum(cmd_str, entry, CONTRACTS, stop, trade_id, expires_at)
        command = {
            "cmd": cmd_str, "price": entry, "qty": CONTRACTS,
            "stop": stop, "t1": t1, "t2": t2, "t3": t3,
            "brackets": [
                {"id": "C1", "qty": 1, "target": t1},
                {"id": "C2", "qty": 1, "target": t2},
                {"id": "C3", "qty": 1, "target": t3},
            ],
            "trade_id": trade_id, "expires_at": expires_at,
            "checksum": chk_hex, "checksum_input": chk_raw,
        }
        log.info(f"[EXECUTE] step 3: writing command to Redis key={REDIS_TRADE_COMMAND}")
        await redis_set_key(REDIS_TRADE_COMMAND, command)
        # Verify it was written
        verify = await redis_get_key(REDIS_TRADE_COMMAND)
        log.info(f"[EXECUTE] step 4: command written, verify={verify is not None}, trade_id={verify.get('trade_id') if verify else 'NONE'}")

        # Increment daily trade count — only for genuinely new trades (not test)
        if not is_replacement and not _test_override:
            try:
                state = await get_daily_state()
                today = __import__("datetime").date.today().isoformat()
                if state.get("date") != today:
                    state = {"pnl": 0, "trade_count": 0, "consecutive_losses": 0,
                             "locked_until": 0, "hard_locked": False, "date": today}
                state["trade_count"] = state.get("trade_count", 0) + 1
                await save_daily_state(state)
            except Exception as e:
                log.warning(f"Daily state update failed (trade still opened): {e}")

        log.info(f"Trade opened: {trade_id} {direction} @ {entry} stop={stop} risk={risk:.2f}")

        # Persist open trade to Postgres
        try:
            from database import insert_trade
            await insert_trade(trade)
        except Exception as e:
            log.warning(f"Postgres trade open persist failed: {e}")

        return {"ok": True, "trade": trade}

    except HTTPException:
        raise  # re-raise 400/403/409 as-is
    except Exception as e:
        log.error(f"/trade/execute failed: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/trade/close")
async def trade_close(request: Request):
    """Close active trade. Updates daily P&L and circuit breaker state."""
    import time

    active = await redis_get_key(REDIS_TRADE_STATUS)
    if not active or active.get("status") != "OPEN":
        raise HTTPException(status_code=404, detail="No active trade")

    body = await request.json()
    exit_price = body.get("exit_price", 0)
    reason = body.get("reason", "manual")

    if exit_price <= 0:
        # Use current market price
        data = await redis_get()
        exit_price = data.get("price", 0) if data else 0
    if exit_price <= 0:
        raise HTTPException(status_code=400, detail="exit_price required")

    direction = active["direction"]
    entry = active["entry_price"]
    pnl_pts = (exit_price - entry) if direction == "LONG" else (entry - exit_price)
    pnl_usd = round(pnl_pts * 5, 2)

    # Update trade record
    active["status"] = "CLOSED"
    active["exit_price"] = exit_price
    active["exit_ts"] = int(time.time())
    active["pnl_pts"] = round(pnl_pts, 2)
    active["pnl_usd"] = pnl_usd
    active["close_reason"] = reason
    active["duration_min"] = round((active["exit_ts"] - active.get("entry_ts", active["exit_ts"])) / 60, 1)
    active["bars_held"] = max(1, int(active["duration_min"] / 3))  # 3min bars

    # Compute MAE/MFE from candle history
    try:
        from analytics import compute_mae_mfe
        candles_3m = await _get_3m_candles()
        mae_mfe = compute_mae_mfe(candles_3m, entry, active.get("entry_ts", 0),
                                  active["exit_ts"], direction)
        active["mae_pts"] = mae_mfe["mae_pts"]
        active["mfe_pts"] = mae_mfe["mfe_pts"]
        mfe = mae_mfe["mfe_pts"]
        active["exit_efficiency"] = round(pnl_pts / mfe * 100, 1) if mfe > 0 else 0
    except Exception as e:
        log.warning(f"MAE/MFE compute failed: {e}")
        active["mae_pts"] = 0
        active["mfe_pts"] = 0
        active["exit_efficiency"] = 0

    await redis_set_key(REDIS_TRADE_STATUS, active)

    # Update daily state + circuit breaker
    state = await get_daily_state()
    state["pnl"] = round(state.get("pnl", 0) + pnl_usd, 2)

    if pnl_pts < 0:
        state["consecutive_losses"] = state.get("consecutive_losses", 0) + 1
    else:
        state["consecutive_losses"] = 0

    # Circuit breaker triggers
    if abs(state["pnl"]) >= CB_HARD_LIMIT and state["pnl"] < 0:
        state["hard_locked"] = True
        log.warning(f"HARD LOCK: daily loss ${abs(state['pnl']):.0f}")
    elif abs(state["pnl"]) >= CB_SOFT_LIMIT and state["pnl"] < 0:
        state["locked_until"] = time.time() + CB_LOCK_MIN * 60
        log.warning(f"SOFT LOCK: daily loss ${abs(state['pnl']):.0f} — locked {CB_LOCK_MIN}min")
    elif state["consecutive_losses"] >= CB_CONSEC_LOSSES:
        state["locked_until"] = time.time() + CB_LOCK_MIN * 60
        log.warning(f"CONSEC LOCK: {state['consecutive_losses']} consecutive losses — locked {CB_LOCK_MIN}min")

    await save_daily_state(state)

    # Persist to trade log (Redis + Postgres)
    try:
        log_key = f"mems26:tradelog:{active['exit_ts']}"
        await redis_set_key(log_key, active)
    except Exception as e:
        log.warning(f"Trade log persist failed: {e}")
    try:
        from database import insert_trade
        await insert_trade(active)
    except Exception as e:
        log.warning(f"Postgres trade persist failed: {e}")

    log.info(f"Trade closed: {active['id']} PnL={pnl_pts:+.2f}pt (${pnl_usd:+.2f}) reason={reason}")

    # V7.2.2: Push CLOSE command — mirrors CANCEL format exactly
    try:
        close_ts = int(time.time())
        close_id = f"{active['id']}_CLOSE"
        close_exp = close_ts + COMMAND_TTL_SEC
        chk_hex, chk_raw = _make_checksum("CLOSE", 0, 0, 0, close_id, close_exp)
        close_cmd = {
            "cmd": "CLOSE", "price": 0, "qty": 0, "stop": 0,
            "t1": 0, "t2": 0, "t3": 0,
            "trade_id": close_id, "expires_at": close_exp,
            "checksum": chk_hex, "checksum_input": chk_raw,
        }
        await redis_set_key(REDIS_TRADE_COMMAND, close_cmd)
        log.info(f"[CLOSE] command pushed to Redis for {close_id}")
    except Exception as e:
        log.warning(f"[CLOSE] Redis push failed: {e}")

    # Broadcast to all WS clients
    ws_msg = {
        "type": "TRADE_CLOSE",
        "trade_id": active["id"],
        "exit_type": reason,
        "pnl_pts": round(pnl_pts, 2),
        "pnl_usd": pnl_usd,
    }
    log.info(f"[X4] broadcasting TRADE_CLOSE to {len(manager._clients)} WS clients: {ws_msg}")
    try:
        await manager.broadcast(ws_msg)
        log.info(f"[X4] broadcast sent OK")
    except Exception as e:
        log.warning(f"[X4] broadcast failed: {e}")

    return {"ok": True, "trade": active, "daily_pnl": state["pnl"], "circuit_breaker": await check_circuit_breaker()}


# ---------------------------------------------------------------------------
# V7.9.1: Bailout endpoint — aggressive exit tagged FP_BAILOUT
# ---------------------------------------------------------------------------

@app.post("/trade/bailout")
async def trade_bailout(request: Request):
    """V7.9.1: FP_BAILOUT exit. Same as /trade/close but enqueues BAILOUT cmd."""
    import time

    active = await redis_get_key(REDIS_TRADE_STATUS)
    if not active or active.get("status") != "OPEN":
        raise HTTPException(status_code=404, detail="No active trade")

    body = await request.json()
    exit_price = body.get("exit_price", 0)

    if exit_price <= 0:
        data = await redis_get()
        exit_price = data.get("price", 0) if data else 0
    if exit_price <= 0:
        raise HTTPException(status_code=400, detail="exit_price required")

    direction = active["direction"]
    entry = active["entry_price"]
    pnl_pts = (exit_price - entry) if direction == "LONG" else (entry - exit_price)
    pnl_usd = round(pnl_pts * 5, 2)

    active["status"] = "CLOSED"
    active["exit_price"] = exit_price
    active["exit_ts"] = int(time.time())
    active["pnl_pts"] = round(pnl_pts, 2)
    active["pnl_usd"] = pnl_usd
    active["close_reason"] = "FP_BAILOUT"
    active["active_management_state"] = "BAILED_OUT"
    active["duration_min"] = round((active["exit_ts"] - active.get("entry_ts", active["exit_ts"])) / 60, 1)
    active["bars_held"] = max(1, int(active["duration_min"] / 3))

    try:
        from analytics import compute_mae_mfe
        candles_3m = await _get_3m_candles()
        mae_mfe = compute_mae_mfe(candles_3m, entry, active.get("entry_ts", 0),
                                  active["exit_ts"], direction)
        active["mae_pts"] = mae_mfe["mae_pts"]
        active["mfe_pts"] = mae_mfe["mfe_pts"]
        mfe = mae_mfe["mfe_pts"]
        active["exit_efficiency"] = round(pnl_pts / mfe * 100, 1) if mfe > 0 else 0
    except Exception as e:
        log.warning(f"MAE/MFE compute failed: {e}")
        active["mae_pts"] = 0
        active["mfe_pts"] = 0
        active["exit_efficiency"] = 0

    await redis_set_key(REDIS_TRADE_STATUS, active)

    # Update daily state + circuit breaker (same as /trade/close)
    state = await get_daily_state()
    state["pnl"] = round(state.get("pnl", 0) + pnl_usd, 2)
    if pnl_pts < 0:
        state["consecutive_losses"] = state.get("consecutive_losses", 0) + 1
    else:
        state["consecutive_losses"] = 0
    if abs(state["pnl"]) >= CB_HARD_LIMIT and state["pnl"] < 0:
        state["hard_locked"] = True
    elif abs(state["pnl"]) >= CB_SOFT_LIMIT and state["pnl"] < 0:
        state["locked_until"] = time.time() + CB_LOCK_MIN * 60
    elif state["consecutive_losses"] >= CB_CONSEC_LOSSES:
        state["locked_until"] = time.time() + CB_LOCK_MIN * 60
    await save_daily_state(state)

    # Persist to trade log
    try:
        log_key = f"mems26:tradelog:{active['exit_ts']}"
        await redis_set_key(log_key, active)
    except Exception as e:
        log.warning(f"Trade log persist failed: {e}")
    try:
        from database import insert_trade
        await insert_trade(active)
    except Exception as e:
        log.warning(f"Postgres trade persist failed: {e}")

    log.info(f"[V7.9.1] BAILOUT: {active['id']} PnL={pnl_pts:+.2f}pt (${pnl_usd:+.2f})")

    # Enqueue BAILOUT cmd for DLL
    try:
        bailout_id = f"{active['id']}_BAILOUT"
        bailout_exp = int(time.time()) + COMMAND_TTL_SEC
        chk_hex, chk_raw = _make_checksum("BAILOUT", 0, 0, 0, bailout_id, bailout_exp)
        bailout_cmd = {
            "cmd": "BAILOUT", "price": 0, "qty": 0, "stop": 0,
            "t1": 0, "t2": 0, "t3": 0,
            "trade_id": bailout_id, "expires_at": bailout_exp,
            "checksum": chk_hex, "checksum_input": chk_raw,
        }
        await redis_set_key(REDIS_TRADE_COMMAND, bailout_cmd)
        log.info(f"[V7.9.1] BAILOUT command pushed for {bailout_id}")
    except Exception as e:
        log.warning(f"[V7.9.1] BAILOUT Redis push failed: {e}")

    # Broadcast
    try:
        await manager.broadcast({
            "type": "TRADE_CLOSE", "trade_id": active["id"],
            "exit_type": "FP_BAILOUT",
            "pnl_pts": round(pnl_pts, 2), "pnl_usd": pnl_usd,
        })
    except Exception as e:
        log.warning(f"[V7.9.1] broadcast failed: {e}")

    return {"ok": True, "trade": active, "daily_pnl": state["pnl"], "circuit_breaker": await check_circuit_breaker()}


# ---------------------------------------------------------------------------
# V7.9.2: Modify stop price for active trade
# ---------------------------------------------------------------------------

class ModifyStopRequest(BaseModel):
    trade_id: str
    new_stop_price: float


@app.post("/trade/modify-stop")
async def trade_modify_stop(
    payload: ModifyStopRequest,
    x_bridge_token: Optional[str] = Header(None, alias="X-Bridge-Token"),
):
    """V7.9.2: Modify all 3 stop prices on active trade."""
    import time as _time

    if x_bridge_token != BRIDGE_TOKEN:
        raise HTTPException(status_code=401, detail="invalid token")

    if payload.new_stop_price <= 0:
        raise HTTPException(status_code=400, detail=f"INVALID_STOP: {payload.new_stop_price} must be > 0")

    trade = await redis_get_key(REDIS_TRADE_STATUS)
    if trade is None or trade.get("id") != payload.trade_id:
        raise HTTPException(status_code=404, detail=f"TRADE_NOT_FOUND: {payload.trade_id}")

    if trade.get("status") != "OPEN":
        raise HTTPException(status_code=400, detail=f"TRADE_NOT_OPEN: status={trade.get('status')}")

    entry_price = trade.get("entry_price", 0)
    if entry_price > 0:
        distance = abs(payload.new_stop_price - entry_price)
        if distance > 50.0:
            raise HTTPException(
                status_code=400,
                detail=f"STOP_OUT_OF_RANGE: distance={distance:.2f}pt from entry={entry_price:.2f} exceeds 50pt limit",
            )

    # Enqueue MODIFY_STOP cmd
    mod_ts = int(_time.time())
    mod_exp = mod_ts + COMMAND_TTL_SEC
    chk_hex, chk_raw = _make_checksum(
        "MODIFY_STOP", payload.new_stop_price, 0, 0, payload.trade_id, mod_exp)
    mod_cmd = {
        "cmd": "MODIFY_STOP", "price": payload.new_stop_price, "qty": 0, "stop": 0,
        "t1": 0, "t2": 0, "t3": 0,
        "trade_id": payload.trade_id, "expires_at": mod_exp,
        "checksum": chk_hex, "checksum_input": chk_raw,
    }
    await redis_set_key(REDIS_TRADE_COMMAND, mod_cmd)

    # Update trade record
    trade["stop"] = payload.new_stop_price
    trade["last_stop_modify_price"] = payload.new_stop_price
    trade["last_stop_modify_ts"] = mod_ts
    await redis_set_key(REDIS_TRADE_STATUS, trade)

    log.info(f"[V7.9.2] MODIFY_STOP: trade={payload.trade_id} new_stop={payload.new_stop_price}")

    return {
        "ok": True,
        "trade_id": payload.trade_id,
        "new_stop_price": payload.new_stop_price,
        "cmd_enqueued": True,
    }


# ---------------------------------------------------------------------------
# V7.9.3: Modify target prices for active trade
# ---------------------------------------------------------------------------

class ModifyTargetRequest(BaseModel):
    trade_id: str
    new_t1: Optional[float] = None
    new_t2: Optional[float] = None
    new_t3: Optional[float] = None


@app.post("/trade/modify-target")
async def trade_modify_target(
    payload: ModifyTargetRequest,
    x_bridge_token: Optional[str] = Header(None, alias="X-Bridge-Token"),
):
    """V7.9.3: Modify 1-3 target prices on active trade."""
    import time as _time

    if x_bridge_token != BRIDGE_TOKEN:
        raise HTTPException(status_code=401, detail="invalid token")

    if payload.new_t1 is None and payload.new_t2 is None and payload.new_t3 is None:
        raise HTTPException(status_code=400, detail="NO_TARGETS_PROVIDED: must provide new_t1, new_t2, or new_t3")

    trade = await redis_get_key(REDIS_TRADE_STATUS)
    if trade is None or trade.get("id") != payload.trade_id:
        raise HTTPException(status_code=404, detail=f"TRADE_NOT_FOUND: {payload.trade_id}")

    if trade.get("status") != "OPEN":
        raise HTTPException(status_code=400, detail=f"TRADE_NOT_OPEN: status={trade.get('status')}")

    # Sanity validation per target (50pt from entry)
    entry_price = trade.get("entry_price", 0)
    for label, val in [("new_t1", payload.new_t1), ("new_t2", payload.new_t2), ("new_t3", payload.new_t3)]:
        if val is None:
            continue
        if val <= 0:
            raise HTTPException(status_code=400, detail=f"INVALID_TARGET: {label}={val} must be > 0")
        if entry_price > 0 and abs(val - entry_price) > 50.0:
            raise HTTPException(
                status_code=400,
                detail=f"TARGET_OUT_OF_RANGE: {label}={val} distance={abs(val - entry_price):.2f}pt from entry={entry_price:.2f} exceeds 50pt limit",
            )

    # Enqueue MODIFY_TARGET cmd (0 means "skip / don't change")
    t1_val = payload.new_t1 or 0.0
    t2_val = payload.new_t2 or 0.0
    t3_val = payload.new_t3 or 0.0
    mod_ts = int(_time.time())
    mod_exp = mod_ts + COMMAND_TTL_SEC
    chk_hex, chk_raw = _make_checksum(
        "MODIFY_TARGET", t1_val, 0, 0, payload.trade_id, mod_exp)
    mod_cmd = {
        "cmd": "MODIFY_TARGET", "price": t1_val, "qty": 0, "stop": 0,
        "t1": t1_val, "t2": t2_val, "t3": t3_val,
        "trade_id": payload.trade_id, "expires_at": mod_exp,
        "checksum": chk_hex, "checksum_input": chk_raw,
    }
    await redis_set_key(REDIS_TRADE_COMMAND, mod_cmd)

    # Update trade record
    trade["last_target_modify_ts"] = mod_ts
    if payload.new_t1 is not None:
        trade["t1"] = payload.new_t1
    if payload.new_t2 is not None:
        trade["t2"] = payload.new_t2
    if payload.new_t3 is not None:
        trade["t3"] = payload.new_t3
    await redis_set_key(REDIS_TRADE_STATUS, trade)

    log.info(f"[V7.9.3] MODIFY_TARGET: trade={payload.trade_id} t1={t1_val} t2={t2_val} t3={t3_val}")

    return {
        "ok": True,
        "trade_id": payload.trade_id,
        "new_t1": payload.new_t1,
        "new_t2": payload.new_t2,
        "new_t3": payload.new_t3,
        "cmd_enqueued": True,
    }


@app.post("/ws/broadcast")
async def ws_broadcast(request: Request, x_bridge_token: Optional[str] = Header(None)):
    """Broadcast arbitrary JSON to all WS clients. Bridge-only."""
    if x_bridge_token != BRIDGE_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    body = await request.json()
    await manager.broadcast(body)
    return {"ok": True, "clients": len(manager._clients)}


@app.get("/trade/status")
async def trade_status():
    """Get active trade status."""
    active = await redis_get_key(REDIS_TRADE_STATUS)
    if not active:
        return {"status": "NO_TRADE"}

    # If trade is open, calculate live P&L
    if active.get("status") == "OPEN":
        data = await redis_get()
        if data:
            price = data.get("price", 0)
            direction = active["direction"]
            entry = active["entry_price"]
            pnl = (price - entry) if direction == "LONG" else (entry - price)
            active["live_pnl_pts"] = round(pnl, 2)
            active["live_pnl_usd"] = round(pnl * 5, 2)
            active["current_price"] = price

    return active


@app.post("/trade/scale")
async def trade_scale(request: Request):
    """Scale out a contract (C1/C2/C3)."""
    active = await redis_get_key(REDIS_TRADE_STATUS)
    if not active or active.get("status") != "OPEN":
        raise HTTPException(status_code=404, detail="No active trade")

    body = await request.json()
    contract = body.get("contract", "")  # "c1", "c2", "c3"
    exit_price = body.get("exit_price", 0)

    if contract not in ("c1", "c2", "c3"):
        raise HTTPException(status_code=400, detail="contract must be c1, c2, or c3")

    key = f"{contract}_status"
    if active.get(key) == "closed":
        raise HTTPException(status_code=409, detail=f"{contract} already closed")

    active[key] = "closed"
    active[f"{contract}_exit_price"] = exit_price
    active[f"{contract}_exit_ts"] = int(__import__("time").time())

    # Move stop to BE after C1
    if contract == "c1" and exit_price > 0:
        active["stop"] = active["entry_price"]
        log.info(f"Stop moved to BE: {active['entry_price']}")

    await redis_set_key(REDIS_TRADE_STATUS, active)
    log.info(f"Scaled out {contract} @ {exit_price}")

    # V7.2.2: Push SCALE_OUT command — mirrors CANCEL format exactly
    try:
        import time as _t
        scale_ts = int(_t.time())
        scale_exp = scale_ts + COMMAND_TTL_SEC
        scale_id = f"{active['id']}_SCALE_{contract.upper()}"
        chk_hex, chk_raw = _make_checksum("SCALE_OUT", 0, 1, 0, scale_id, scale_exp)
        scale_cmd = {
            "cmd": "SCALE_OUT", "price": 0, "qty": 1, "stop": 0,
            "t1": 0, "t2": 0, "t3": 0,
            "trade_id": scale_id, "direction": active["direction"],
            "contract": contract,
            "contract_target": active.get(f"t{contract[1]}", 0),
            "expires_at": scale_exp,
            "checksum": chk_hex, "checksum_input": chk_raw,
        }
        await redis_set_key(REDIS_TRADE_COMMAND, scale_cmd)
        log.info(f"[scale] SCALE_OUT pushed to Redis: {scale_id}")
    except Exception as e:
        log.warning(f"[scale] Redis push failed: {e}")

    return {"ok": True, "trade": active}


@app.post("/trade/event")
async def receive_trade_event(request: Request, x_bridge_token: Optional[str] = Header(None)):
    """V7.7.3: Receives POSITION_CHANGE events from DLL via Bridge."""
    if x_bridge_token != BRIDGE_TOKEN:
        raise HTTPException(status_code=401, detail="invalid token")
    body = await request.json()
    if body.get("event_type") != "POSITION_CHANGE":
        return {"status": "ignored", "reason": "unknown event_type"}

    prev_qty = body.get("prev_qty", 0)
    new_qty = body.get("new_qty", 0)
    last_price = body.get("last_price", 0)
    trade_id = body.get("trade_id", "")
    # Strip suffixes to find parent trade
    for sfx in ("_CLOSE", "_SCALE_C1", "_SCALE_C2", "_SCALE_C3"):
        if trade_id.endswith(sfx):
            trade_id = trade_id[:-len(sfx)]
            break

    active = await redis_get_key(REDIS_TRADE_STATUS)
    if not active or active.get("id") != trade_id:
        log.warning(f"[C3] event for unknown trade {trade_id}, ignoring")
        return {"status": "ignored", "reason": "trade not found"}

    transition = "UNKNOWN"
    if prev_qty == 0 and new_qty > 0:
        transition = "ENTRY"
        active["entry_confirmed_ts"] = body.get("ts", 0)
    elif new_qty == 0 and prev_qty > 0:
        transition = "FULL_CLOSE"
        active["status"] = "CLOSED"
        active["exit_price"] = last_price
        active["exit_ts"] = body.get("ts", 0)
        active["close_reason"] = "sierra_event"
    elif 0 < new_qty < prev_qty:
        transition = "SCALE_OUT"
        active["remaining_qty"] = new_qty
        fills = active.get("fills", [])
        fills.append({"qty": prev_qty - new_qty, "price": last_price, "ts": body.get("ts", 0)})
        active["fills"] = fills

    await redis_set_key(REDIS_TRADE_STATUS, active)
    log.info(f"[C3] trade event {trade_id}: {prev_qty} → {new_qty} ({transition})")

    # Persist to Postgres if full close
    if transition == "FULL_CLOSE":
        try:
            from database import insert_trade
            await insert_trade(active)
        except Exception as e:
            log.warning(f"[C3] Postgres persist failed: {e}")

    return {"status": "processed", "trade_id": trade_id, "transition": transition}


@app.get("/trade/command")
async def get_trade_command(x_bridge_token: Optional[str] = Header(None)):
    if x_bridge_token != BRIDGE_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        cmd = await redis_get_key(REDIS_TRADE_COMMAND)
        if not cmd:
            return {"pending": False}
        import time
        if cmd.get("expires_at", 0) < int(time.time()):
            await redis_delete_key(REDIS_TRADE_COMMAND)
            return {"pending": False, "expired": True}
        return {"pending": True, "command": cmd}
    except Exception as e:
        log.error(f"/trade/command failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/trade/command/ack")
async def ack_trade_command(request: Request, x_bridge_token: Optional[str] = Header(None)):
    if x_bridge_token != BRIDGE_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    body = await request.json()
    trade_id = body.get("trade_id", "")
    cmd = await redis_get_key(REDIS_TRADE_COMMAND)
    if cmd and cmd.get("trade_id") == trade_id:
        await redis_delete_key(REDIS_TRADE_COMMAND)
        log.info(f"Command acked: {trade_id}")
        return {"ok": True}
    return {"ok": False, "detail": "No matching pending command"}

@app.post("/trade/test-dispatch")
async def test_dispatch(request: Request):
    """Diagnostic: write a real bracket command to Redis with caller's values.
    Uses the same field mapping as /trade/execute but skips all guards."""
    import time
    body = await request.json()
    direction = body.get("direction", "LONG")
    entry = body.get("entry_price", 0)
    stop = body.get("stop", 0)
    t1 = body.get("t1", 0)
    t2 = body.get("t2", 0)
    t3 = body.get("t3", 0)
    ts = int(time.time())
    trade_id = f"TEST_{ts}"
    cmd_str = "BUY" if direction == "LONG" else "SELL"
    expires_at = ts + 60
    chk_hex, chk_raw = _make_checksum(cmd_str, entry, CONTRACTS, stop, trade_id, expires_at)
    test_cmd = {
        "cmd": cmd_str, "price": entry, "qty": CONTRACTS,
        "stop": stop, "t1": t1, "t2": t2, "t3": t3,
        "brackets": [
            {"id": "C1", "qty": 1, "target": t1},
            {"id": "C2", "qty": 1, "target": t2},
            {"id": "C3", "qty": 1, "target": t3},
        ],
        "trade_id": trade_id, "expires_at": expires_at,
        "checksum": chk_hex, "checksum_input": chk_raw,
    }
    await redis_set_key(REDIS_TRADE_COMMAND, test_cmd)
    log.info(f"[TEST-DISPATCH] wrote {cmd_str} command: entry={entry} t1={t1} t2={t2} t3={t3}")
    return {
        "ok": True,
        "redis_key": REDIS_TRADE_COMMAND,
        "trade_id": trade_id,
        "command": test_cmd,
        "expires_in_sec": 60,
    }


@app.post("/trade/command/cancel")
async def cancel_trade_command(x_bridge_token: Optional[str] = Header(None)):
    if x_bridge_token != BRIDGE_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    import time
    expires_at = int(time.time()) + COMMAND_TTL_SEC
    cancel_id = f"CANCEL_{int(time.time())}"
    chk_hex, chk_raw = _make_checksum("CANCEL", 0, 0, 0, cancel_id, expires_at)
    cmd = {
        "cmd": "CANCEL", "price": 0, "qty": 0, "stop": 0,
        "t1": 0, "t2": 0, "t3": 0,
        "trade_id": cancel_id, "expires_at": expires_at,
        "checksum": chk_hex, "checksum_input": chk_raw,
    }
    await redis_set_key(REDIS_TRADE_COMMAND, cmd)
    return {"ok": True, "command": cmd}


@app.delete("/trade/command")
async def delete_trade_command():
    """Clear any pending trade command from Redis (for testing)."""
    try:
        await redis_delete_key(REDIS_TRADE_COMMAND)
        await redis_delete_key(REDIS_TRADE_STATUS)
        return {"ok": True, "detail": "Cleared trade command and status"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/news/status")
async def news_status():
    """News Guard status — events, freeze state, API health."""
    try:
        news_state = await redis_get_key("mems26:news:state")
        if not news_state or not isinstance(news_state, dict):
            return {
                "is_freeze": False,
                "current_state": "NORMAL",
                "api_healthy": False,
                "last_fetch_iso": "",
                "next_event": None,
                "todays_events": [],
            }

        state = news_state.get("state", "CLEAR")
        events = news_state.get("events", [])
        available = news_state.get("available", False)
        active = news_state.get("active_event")

        # Find next upcoming event
        import datetime as _dtmod
        from zoneinfo import ZoneInfo as _ZI
        now_et = _dtmod.datetime.now(_ZI("America/New_York"))
        next_event = None
        for ev in events:
            try:
                h, m = map(int, ev.get("time_et", "0:0").split(":"))
                ev_time = now_et.replace(hour=h, minute=m, second=0)
                diff_min = int((ev_time - now_et).total_seconds() / 60)
                if diff_min > -5:  # include events up to 5min ago
                    candidate = {
                        "title": ev.get("title", ""),
                        "time_iso": ev_time.isoformat(),
                        "impact": ev.get("impact", "High"),
                        "currency": "USD",
                        "minutes_until": max(0, diff_min),
                    }
                    if next_event is None or diff_min < next_event["minutes_until"]:
                        next_event = candidate
            except Exception:
                continue

        return {
            "is_freeze": state == "PRE_NEWS_FREEZE",
            "current_state": "FREEZE" if state == "PRE_NEWS_FREEZE" else "POST_NEWS" if state == "POST_NEWS_OPPORTUNITY" else "NORMAL",
            "api_healthy": available,
            "last_fetch_iso": now_et.strftime("%Y-%m-%dT%H:%M:%S"),
            "next_event": next_event,
            "todays_events": events,
        }
    except Exception as e:
        log.warning(f"/news/status error: {e}")
        return {"is_freeze": False, "current_state": "NORMAL", "api_healthy": False,
                "last_fetch_iso": "", "next_event": None, "todays_events": []}


# ── Analytics Endpoints ───────────────────────────────────────────────────

async def _get_all_trade_logs(is_shadow: Optional[bool] = None, include_tests: bool = False) -> list:
    """Read all trade log entries. Uses Postgres when available, else Redis."""
    from database import get_all_trades, get_pool
    pool = await get_pool()
    if pool:
        trades = await get_all_trades(is_shadow=is_shadow)
        if not include_tests:
            trades = [t for t in trades if not t.get("is_test")]
        return trades

    # Fallback to Redis
    trades = []
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{REDIS_URL}/keys/mems26:tradelog:*",
                headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
                timeout=5.0
            )
            keys = resp.json().get("result", [])
            if keys:
                keys.sort(reverse=True)
                for key in keys[:200]:
                    val = await redis_get_key(key)
                    if val and isinstance(val, dict):
                        trades.append(val)
    except Exception as e:
        log.error(f"Trade logs read failed: {e}")
    return trades


@app.get("/analytics/daily")
async def analytics_daily(date: str = ""):
    """Daily trade report — WR, P&L, MAE/MFE, pillar attribution, killzone breakdown."""
    from analytics import compute_daily_report
    if not date:
        from datetime import date as _d
        date = _d.today().isoformat()
    trades = await _get_all_trade_logs()
    return compute_daily_report(trades, date)


@app.get("/analytics/weekly")
async def analytics_weekly(week_start: str = ""):
    """Weekly report — 18-trade window, pillar correlation, threshold recs."""
    from analytics import compute_weekly_report
    if not week_start:
        from datetime import date as _d, timedelta as _td
        today = _d.today()
        week_start = (today - _td(days=today.weekday())).isoformat()
    trades = await _get_all_trade_logs()
    return compute_weekly_report(trades, week_start)


@app.get("/analytics/patterns")
async def analytics_patterns():
    """Setup Quality Matrix, MAE/MFE distributions, Exit Efficiency."""
    from analytics import compute_pattern_analysis
    trades = await _get_all_trade_logs()
    return compute_pattern_analysis(trades)


@app.get("/analytics/by-segment")
async def analytics_by_segment():
    """V6.5.2: Breakdown of shadow trades by day_type, killzone, setup_type, trade_number, entry_mode."""
    from database import get_pool
    pool = await get_pool()
    if not pool:
        return {"by_day_type": [], "by_killzone": [], "by_setup_type": [],
                "by_trade_number": [], "by_entry_mode": [], "cross_tab": []}

    trades = await _get_all_trade_logs(is_shadow=True)
    # Only closed trades with pnl
    closed = [t for t in trades if t.get("status") == "CLOSED" and t.get("pnl_pts") is not None]

    def _bucket(items, key_fn):
        groups = {}
        for t in items:
            k = key_fn(t)
            if not k:
                k = "UNKNOWN"
            if k not in groups:
                groups[k] = []
            groups[k].append(t)
        result = []
        for k, g in sorted(groups.items(), key=lambda x: -len(x[1])):
            wins = sum(1 for t in g if (t.get("pnl_pts") or 0) > 0)
            result.append({
                key_fn.__name__: k,
                "n": len(g),
                "wins": wins,
                "wr": round(wins / len(g) * 100, 1) if g else 0,
                "avg_pnl_pts": round(sum(t.get("pnl_pts", 0) or 0 for t in g) / len(g), 2) if g else 0,
                "avg_mae": round(sum(t.get("mae_pts", 0) or 0 for t in g) / len(g), 1) if g else 0,
                "avg_mfe": round(sum(t.get("mfe_pts", 0) or 0 for t in g) / len(g), 1) if g else 0,
            })
        return result

    def day_type(t): return t.get("day_type") or t.get("day_type_at_entry") or "UNKNOWN"
    def killzone(t): return t.get("killzone") or t.get("killzone_at_entry") or "UNKNOWN"
    def setup_type(t): return t.get("setup_type") or "UNKNOWN"
    def entry_mode(t): return t.get("entry_mode") or "UNKNOWN"

    by_day = _bucket(closed, day_type)
    by_kz = _bucket(closed, killzone)
    by_setup = _bucket(closed, setup_type)
    by_mode = _bucket(closed, entry_mode)

    # Trade number buckets (1-3 vs 4+)
    def trade_num_bucket(t):
        n = t.get("trade_number_of_day") or t.get("setup_number_today") or 0
        return "1-3" if 0 < n <= 3 else "4+" if n > 3 else "UNKNOWN"
    by_num = _bucket(closed, trade_num_bucket)

    # Cross-tab: day_type x killzone x setup_type (only combos with n>=2)
    cross = {}
    for t in closed:
        key = f"{day_type(t)}|{killzone(t)}|{setup_type(t)}"
        if key not in cross:
            cross[key] = []
        cross[key].append(t)
    cross_tab = []
    for key, g in sorted(cross.items(), key=lambda x: -len(x[1])):
        if len(g) < 2:
            continue
        parts = key.split("|")
        wins = sum(1 for t in g if (t.get("pnl_pts") or 0) > 0)
        cross_tab.append({
            "day_type": parts[0], "killzone": parts[1], "setup_type": parts[2],
            "n": len(g), "wr": round(wins / len(g) * 100, 1) if g else 0,
        })

    return {
        "by_day_type": by_day,
        "by_killzone": by_kz,
        "by_setup_type": by_setup,
        "by_trade_number": by_num,
        "by_entry_mode": by_mode,
        "cross_tab": cross_tab[:20],
    }


@app.get("/analytics/attempts")
async def analytics_attempts(
    limit: int = 200,
    is_shadow: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
):
    """Return setup attempts (rejected/taken setups) from Postgres."""
    from database import get_attempts, get_pool
    pool = await get_pool()
    if not pool:
        return []
    shadow = None
    if is_shadow == "true":
        shadow = True
    elif is_shadow == "false":
        shadow = False
    return await get_attempts(limit=limit, is_shadow=shadow,
                              from_date=from_date, to_date=to_date)


@app.post("/analytics/attempts")
async def log_attempt(request: Request):
    """Log a setup attempt (for shadow or live)."""
    from database import insert_attempt
    attempt = await request.json()
    await insert_attempt(attempt)
    return {"ok": True}


def _trades_to_csv(trades: list) -> str:
    """Convert trade dicts to CSV string with all fields flattened."""
    import io, csv
    if not trades:
        return ""
    # Collect all keys from all trades
    all_keys = set()
    for t in trades:
        all_keys.update(t.keys())
    # Sort keys for consistent column order
    priority = [
        "id", "direction", "entry_price", "exit_price", "stop",
        "t1", "t2", "t3", "risk_pts", "pnl_pts", "pnl_usd",
        "entry_ts", "exit_ts", "status", "close_reason",
        "setup_type", "day_type", "killzone", "is_shadow", "cb_respected",
        "mae_pts", "mfe_pts", "duration_min",
    ]
    ordered = [k for k in priority if k in all_keys]
    ordered += sorted(all_keys - set(ordered))

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=ordered, extrasaction="ignore")
    writer.writeheader()
    for t in trades:
        # Convert timestamps to ISO strings
        row = dict(t)
        for ts_key in ("entry_ts", "exit_ts", "ts"):
            if ts_key in row and isinstance(row[ts_key], (int, float)) and row[ts_key] > 0:
                from datetime import datetime
                from zoneinfo import ZoneInfo
                row[ts_key] = datetime.fromtimestamp(row[ts_key], tz=ZoneInfo("America/New_York")).isoformat()
        writer.writerow(row)
    return output.getvalue()


def _attempts_to_csv(attempts: list) -> str:
    import io, csv
    if not attempts:
        return ""
    all_keys = set()
    for a in attempts:
        all_keys.update(a.keys())
    ordered = sorted(all_keys)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=ordered, extrasaction="ignore")
    writer.writeheader()
    for a in attempts:
        row = dict(a)
        if "ts" in row and isinstance(row["ts"], (int, float)) and row["ts"] > 0:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            row["ts"] = datetime.fromtimestamp(row["ts"], tz=ZoneInfo("America/New_York")).isoformat()
        writer.writerow(row)
    return output.getvalue()


@app.get("/analytics/export/trades")
async def export_trades(
    format: str = "csv",
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    is_shadow: Optional[str] = None,
    day_type: Optional[str] = None,
):
    """Export trades as CSV or JSON with optional filters."""
    shadow = None
    if is_shadow == "true":
        shadow = True
    elif is_shadow == "false":
        shadow = False
    trades = await _get_all_trade_logs(is_shadow=shadow)

    # Apply additional filters
    if from_date:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from_ts = int(datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=ZoneInfo("America/New_York")).timestamp())
        trades = [t for t in trades if (t.get("entry_ts") or 0) >= from_ts]
    if to_date:
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        to_ts = int((datetime.strptime(to_date, "%Y-%m-%d").replace(tzinfo=ZoneInfo("America/New_York")) + timedelta(days=1)).timestamp())
        trades = [t for t in trades if (t.get("entry_ts") or 0) < to_ts]
    if day_type and day_type != "all":
        trades = [t for t in trades if t.get("day_type") == day_type]

    if format == "json":
        return JSONResponse(
            content=trades,
            headers={"Content-Disposition": "attachment; filename=trades.json"}
        )

    csv_data = _trades_to_csv(trades)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trades.csv"}
    )


@app.get("/analytics/export/attempts")
async def export_attempts(
    format: str = "csv",
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    is_shadow: Optional[str] = None,
):
    """Export setup attempts as CSV or JSON."""
    from database import get_attempts, get_pool
    pool = await get_pool()
    if not pool:
        return JSONResponse(content=[], status_code=200)
    shadow = None
    if is_shadow == "true":
        shadow = True
    elif is_shadow == "false":
        shadow = False
    attempts = await get_attempts(limit=10000, is_shadow=shadow,
                                  from_date=from_date, to_date=to_date)

    if format == "json":
        return JSONResponse(
            content=attempts,
            headers={"Content-Disposition": "attachment; filename=attempts.json"}
        )

    csv_data = _attempts_to_csv(attempts)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attempts.csv"}
    )


@app.get("/analytics/export/all")
async def export_all():
    """Export all trades + attempts as JSON bundle."""
    trades = await _get_all_trade_logs()
    from database import get_attempts, get_pool
    pool = await get_pool()
    attempts = await get_attempts(limit=10000) if pool else []
    return JSONResponse(
        content={"trades": trades, "attempts": attempts},
        headers={"Content-Disposition": "attachment; filename=mems26_all.json"}
    )


@app.get("/api/versions")
async def get_versions():
    """Unified version info for Web/Bridge/DLL + parsed changelog."""
    import re, time as _t
    web_version = "V6.7.0"
    # Bridge info from Redis
    bcfg = await redis_get_key("mems26:bridge_config") or {}
    bridge_version = bcfg.get("bridge_version", "unknown") if isinstance(bcfg, dict) else "unknown"
    bridge_ts = bcfg.get("updated_at", 0) if isinstance(bcfg, dict) else 0
    bridge_age = int(_t.time() - bridge_ts) if bridge_ts > 0 else -1
    dll_version = bcfg.get("dll_version", "unknown") if isinstance(bcfg, dict) else "unknown"
    dll_built = bcfg.get("dll_built_at", "unknown") if isinstance(bcfg, dict) else "unknown"
    # Changelog
    changelog = []
    try:
        with open("CHANGELOG.md") as f:
            content = f.read()
        for m in re.finditer(r'## \[(V[\d.]+)\] - (\d{4}-\d{2}-\d{2})\s*\n\*\*Scope:\*\* ([^\n]+)\s*\n\n((?:- [^\n]+\n?)+)', content):
            v, d, s, b = m.groups()
            changelog.append({"version": v, "date": d, "scope": s.strip(),
                              "items": [l[2:].strip() for l in b.strip().split("\n") if l.startswith("-")]})
    except Exception:
        pass
    mismatch = web_version != bridge_version and bridge_version != "unknown"
    warnings = []
    if mismatch:
        warnings.append(f"Web ({web_version}) differs from Bridge ({bridge_version})")
    return {
        "web": {"version": web_version},
        "bridge": {"version": bridge_version, "heartbeat_age_sec": bridge_age,
                   "status": "online" if 0 <= bridge_age < 60 else "stale"},
        "dll": {"version": dll_version, "built_at": dll_built},
        "changelog": changelog, "mismatch": mismatch, "warnings": warnings,
    }


@app.get("/health")
async def health():
    import time as _t
    data = await redis_get()
    now = _t.time()

    # Bridge heartbeat age
    bridge_age = -1
    sc_age = -1
    if data:
        data_ts = data.get("ts", 0)
        if data_ts > 0:
            bridge_age = int(now - data_ts)
            sc_age = bridge_age  # SC data comes through the bridge

    # News guard health
    news_healthy = False
    try:
        news_state = await redis_get_key("mems26:news:state")
        if news_state and isinstance(news_state, dict):
            news_healthy = news_state.get("available", False)
    except Exception:
        pass

    # Redis health — if we got here with data, Redis is OK
    redis_ok = data is not None

    # V6.5.2: Entry mode from Bridge Redis config (falls back to env)
    _entry_mode = "STRICT"
    _relvol_min = 1.2
    _fvg_max = 4.0
    _sweep_min = 1.5
    _kz_required = True
    try:
        _bridge_cfg = await redis_get_key("mems26:bridge_config")
        if _bridge_cfg and isinstance(_bridge_cfg, dict):
            _cfg_age = now - _bridge_cfg.get("updated_at", 0)
            if _cfg_age < 120:  # fresh within 2 min
                _entry_mode = _bridge_cfg.get("entry_mode", "STRICT")
                _relvol_min = _bridge_cfg.get("gate_relvol_min", 1.2)
                _fvg_max = _bridge_cfg.get("gate_fvg_max", 4.0)
                _sweep_min = _bridge_cfg.get("gate_sweep_min", 1.5)
                _kz_required = _bridge_cfg.get("killzone_required", True)
            else:
                log.warning(f"Bridge config stale in Redis ({_cfg_age:.0f}s), falling back to env config")
    except Exception:
        pass

    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo as _ZI
    _now_et = _dt.now(_ZI("America/New_York"))
    _pre_close = (_now_et.hour * 60 + _now_et.minute) >= 15 * 60 + 30

    return {
        "status": "ok",
        "has_data": data is not None,
        "mode": _MODE,
        "entry_mode": _entry_mode,
        "pre_close_freeze_active": _pre_close,
        "gate_relvol_min": _relvol_min,
        "gate_fvg_max": _fvg_max,
        "gate_sweep_min": _sweep_min,
        "killzone_required": _kz_required,
        "bridge_heartbeat_age_sec": bridge_age,
        "news_guard_healthy": news_healthy,
        "redis_ok": redis_ok,
        "sc_data_age_sec": sc_age,
    }


# ---------------------------------------------------------------------------
# V7.7.1d-be: Trade state schema for active management
# ---------------------------------------------------------------------------

class TradeStateResponse(BaseModel):
    trade_id: str
    status: str
    c1_status: str = "PENDING"
    c2_status: str = "PENDING"
    c3_status: str = "PENDING"
    stop_status: str = "PENDING"
    c1_fill_price: Optional[float] = None
    c2_fill_price: Optional[float] = None
    c3_fill_price: Optional[float] = None
    stop_fill_price: Optional[float] = None
    c1_order_id: Optional[int] = None
    c2_order_id: Optional[int] = None
    c3_order_id: Optional[int] = None
    stop_c1_order_id: Optional[int] = None
    stop_c2_order_id: Optional[int] = None
    stop_c3_order_id: Optional[int] = None
    parent_order_id: Optional[int] = None
    active_management_state: str = "NORMAL"


class TradeOrderIDsUpdate(BaseModel):
    trade_id: str
    c1_order_id: int
    c2_order_id: int
    c3_order_id: int
    stop_c1_order_id: int
    stop_c2_order_id: int
    stop_c3_order_id: int
    parent_order_id: int


@app.get("/trade/state/{trade_id}", response_model=TradeStateResponse)
async def get_trade_state(
    trade_id: str,
    x_bridge_token: Optional[str] = Header(None, alias="X-Bridge-Token"),
):
    """Returns full trade state including per-contract status."""
    if x_bridge_token != BRIDGE_TOKEN:
        raise HTTPException(status_code=401, detail="invalid token")

    trade = await redis_get_key(REDIS_TRADE_STATUS)
    if trade is None or trade.get("id") != trade_id:
        raise HTTPException(status_code=404, detail="trade not found")

    return TradeStateResponse(
        trade_id=trade_id,
        status=trade.get("status", "UNKNOWN"),
        c1_status=trade.get("c1_status", "PENDING"),
        c2_status=trade.get("c2_status", "PENDING"),
        c3_status=trade.get("c3_status", "PENDING"),
        stop_status=trade.get("stop_status", "PENDING"),
        c1_fill_price=trade.get("c1_fill_price"),
        c2_fill_price=trade.get("c2_fill_price"),
        c3_fill_price=trade.get("c3_fill_price"),
        stop_fill_price=trade.get("stop_fill_price"),
        c1_order_id=trade.get("c1_order_id"),
        c2_order_id=trade.get("c2_order_id"),
        c3_order_id=trade.get("c3_order_id"),
        stop_c1_order_id=trade.get("stop_c1_order_id"),
        stop_c2_order_id=trade.get("stop_c2_order_id"),
        stop_c3_order_id=trade.get("stop_c3_order_id"),
        parent_order_id=trade.get("parent_order_id"),
        active_management_state=trade.get("active_management_state", "NORMAL"),
    )


@app.post("/trade/internal/set-order-ids")
async def set_order_ids(
    update: TradeOrderIDsUpdate,
    x_bridge_token: Optional[str] = Header(None, alias="X-Bridge-Token"),
):
    """
    Internal: store all 7 InternalOrderIDs from DLL/Bridge into the
    trade record. Used by V7.8.x flow once Bridge implements relay.
    For now this enables manual testing of the schema.
    """
    if x_bridge_token != BRIDGE_TOKEN:
        raise HTTPException(status_code=401, detail="invalid token")

    trade = await redis_get_key(REDIS_TRADE_STATUS)
    if trade is None or trade.get("id") != update.trade_id:
        return {"status": "ignored", "reason": "trade not found"}

    trade["c1_order_id"] = update.c1_order_id
    trade["c2_order_id"] = update.c2_order_id
    trade["c3_order_id"] = update.c3_order_id
    trade["stop_c1_order_id"] = update.stop_c1_order_id
    trade["stop_c2_order_id"] = update.stop_c2_order_id
    trade["stop_c3_order_id"] = update.stop_c3_order_id
    trade["parent_order_id"] = update.parent_order_id
    await redis_set_key(REDIS_TRADE_STATUS, trade)

    return {"status": "ok", "trade_id": update.trade_id}


# ---------------------------------------------------------------------------
# V7.8.1: POST /trade/state — receive trade_state.json from Bridge
# ---------------------------------------------------------------------------

class OrderState(BaseModel):
    id: int
    status: str
    fill_price: float = 0.0
    filled_qty: int = 0

class OrdersDict(BaseModel):
    c1: OrderState
    c2: OrderState
    c3: OrderState
    stop_c1: OrderState
    stop_c2: OrderState
    stop_c3: OrderState
    parent: OrderState

class TradeStatePayload(BaseModel):
    event_type: str
    trade_id: str
    counter: int
    ts: int
    orders: OrdersDict
    dll_version: str


@app.post("/trade/state")
async def receive_trade_state(
    payload: TradeStatePayload,
    x_bridge_token: Optional[str] = Header(None, alias="X-Bridge-Token"),
):
    """V7.8.1: Receives trade_state.json from Bridge, updates trade record."""
    if x_bridge_token != BRIDGE_TOKEN:
        raise HTTPException(status_code=401, detail="invalid token")

    trade = await redis_get_key(REDIS_TRADE_STATUS)
    if trade is None or trade.get("id") != payload.trade_id:
        return {
            "status": "ignored",
            "reason": "trade not found",
            "trade_id": payload.trade_id,
            "counter": payload.counter,
        }

    orders = payload.orders

    # Per-contract target status
    trade["c1_status"] = orders.c1.status
    trade["c2_status"] = orders.c2.status
    trade["c3_status"] = orders.c3.status

    # Collective stop status
    stop_statuses = [orders.stop_c1.status, orders.stop_c2.status, orders.stop_c3.status]
    if "FILLED" in stop_statuses:
        trade["stop_status"] = "FILLED"
    elif all(s == "CANCELED" for s in stop_statuses):
        trade["stop_status"] = "CANCELED"
    else:
        trade["stop_status"] = "OPEN"

    # Fill prices (only when FILLED with non-zero price)
    if orders.c1.status == "FILLED" and orders.c1.fill_price > 0:
        trade["c1_fill_price"] = orders.c1.fill_price
    if orders.c2.status == "FILLED" and orders.c2.fill_price > 0:
        trade["c2_fill_price"] = orders.c2.fill_price
    if orders.c3.status == "FILLED" and orders.c3.fill_price > 0:
        trade["c3_fill_price"] = orders.c3.fill_price
    for s in [orders.stop_c1, orders.stop_c2, orders.stop_c3]:
        if s.status == "FILLED" and s.fill_price > 0:
            trade["stop_fill_price"] = s.fill_price
            break

    # Order IDs
    trade["c1_order_id"] = orders.c1.id
    trade["c2_order_id"] = orders.c2.id
    trade["c3_order_id"] = orders.c3.id
    trade["stop_c1_order_id"] = orders.stop_c1.id
    trade["stop_c2_order_id"] = orders.stop_c2.id
    trade["stop_c3_order_id"] = orders.stop_c3.id
    trade["parent_order_id"] = orders.parent.id

    # V7.9.5 Bug #3: Auto-transition OPEN→CLOSED when all orders done
    done_statuses = ("CANCELED", "FILLED", "ERROR")
    all_stops_done = all(
        getattr(orders, f"stop_c{i}").status in done_statuses for i in range(1, 4)
    )
    all_targets_done = all(
        getattr(orders, f"c{i}").status in done_statuses for i in range(1, 4)
    )
    if all_stops_done and all_targets_done and trade.get("status") == "OPEN":
        import time as _time
        trade["status"] = "CLOSED"
        trade["close_reason"] = trade.get("close_reason") or "AUTO_DETECTED_FROM_STATE"
        trade["closed_at"] = int(_time.time())
        log.info(f"[STATE] Auto-transitioned trade {payload.trade_id} OPEN→CLOSED")

    await redis_set_key(REDIS_TRADE_STATUS, trade)

    log.info(f"V7.8.1 trade_state #{payload.counter} applied: "
             f"trade={payload.trade_id} c1={orders.c1.status} "
             f"c2={orders.c2.status} c3={orders.c3.status} "
             f"stop={trade['stop_status']}")

    # V7.9.0: Smart BE auto-trigger on c1 FILLED transition
    arm_be_fired = False
    if (orders.c1.status == "FILLED"
            and trade.get("active_management_state", "NORMAL") == "NORMAL"
            and orders.parent.fill_price > 0):
        trade["active_management_state"] = "BE_ARMED"
        await redis_set_key(REDIS_TRADE_STATUS, trade)

        import time as _time
        arm_ts = int(_time.time())
        arm_exp = arm_ts + COMMAND_TTL_SEC
        entry_price = orders.parent.fill_price
        chk_hex, chk_raw = _make_checksum(
            "ARM_BE", entry_price, 0, 0, payload.trade_id, arm_exp)
        arm_cmd = {
            "cmd": "ARM_BE", "price": entry_price, "qty": 0, "stop": 0,
            "t1": 0, "t2": 0, "t3": 0,
            "trade_id": payload.trade_id, "expires_at": arm_exp,
            "checksum": chk_hex, "checksum_input": chk_raw,
        }
        await redis_set_key(REDIS_TRADE_COMMAND, arm_cmd)
        arm_be_fired = True
        log.info(f"[V7.9.0] ARM_BE enqueued for trade={payload.trade_id} "
                 f"entry={entry_price}")

    return {
        "status": "ok",
        "trade_id": payload.trade_id,
        "counter": payload.counter,
        "c1_status": trade["c1_status"],
        "c2_status": trade["c2_status"],
        "c3_status": trade["c3_status"],
        "stop_status": trade["stop_status"],
        "arm_be_fired": arm_be_fired,
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        try:
            payload = await _build_status_payload()
            await ws.send_json(payload)
        except Exception as e:
            log.warning(f"WS initial push failed: {e}")
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
