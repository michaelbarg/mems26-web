"""
json_bridge.py — v5
- שומר נתוני זמן אמת ב-Redis (mems26:latest)
- צובר היסטוריית נרות 3m ב-Redis (mems26:candles) עד 960 נרות (48h)
- מעביר ישירות שדות חדשים מ-Study v5: woodies_cci, day_context, candle_patterns, volume_context
"""
import json, asyncio, aiohttp, os, logging, time
from datetime import datetime
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bridge")

SC_JSON_PATH    = os.getenv("SC_JSON_PATH", "/Users/michael/SierraChart2/Data/mes_ai_data.json")
SC_HISTORY_PATH = os.getenv("SC_HISTORY_PATH", "/Users/michael/SierraChart2/Data/mes_ai_history.json")
REDIS_URL       = os.getenv("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN     = os.getenv("UPSTASH_REDIS_REST_TOKEN")
REDIS_KEY       = "mems26:latest"
REDIS_CANDLES   = "mems26:candles"
MAX_CANDLES     = 960
POST_INTERVAL   = 1.0
CANDLE_INTERVAL = 180

@dataclass
class SessionState:
    date: str = ""
    daily_open: float = 0.0
    daily_open_set: bool = False
    overnight_high: float = 0.0
    overnight_low: float = 999999.0
    overnight_done: bool = False
    rev15_type: str = "NONE"
    rev22_type: str = "NONE"
    rev15_price: float = 0.0
    rev22_price: float = 0.0

@dataclass
class CandleBuilder:
    start_ts: int = 0
    o: float = 0.0
    h: float = 0.0
    l: float = 999999.0
    c: float = 0.0
    buy: float = 0.0
    sell: float = 0.0
    vol: float = 0.0
    cci14: float = 0.0
    cci6: float = 0.0
    vwap: float = 0.0
    phase: str = ""
    above_vwap: bool = False
    liq_sweep_long: bool = False
    liq_sweep_short: bool = False

    def update(self, price, buy, sell, vol):
        if self.o == 0: self.o = price
        if price > self.h: self.h = price
        if price < self.l: self.l = price
        self.c = price
        self.buy += buy
        self.sell += sell
        self.vol += vol

    def to_dict(self):
        return {
            "ts": self.start_ts,
            "o": self.o, "h": self.h, "l": self.l, "c": self.c,
            "buy": self.buy, "sell": self.sell,
            "vol": self.vol,
            "delta": self.buy - self.sell,
            "cci14": round(self.cci14, 2),
            "cci6": round(self.cci6, 2),
            "vwap": round(self.vwap, 2),
            "phase": self.phase,
            "above_vwap": self.above_vwap,
            "liq_sweep_long": self.liq_sweep_long,
            "liq_sweep_short": self.liq_sweep_short,
        }

state  = SessionState()
candle = CandleBuilder()

def enrich(raw):
    global state

    today   = datetime.fromtimestamp(raw["timestamp"]).strftime("%Y-%m-%d")
    ses     = raw.get("session_phase", "OVERNIGHT")
    price   = raw.get("current_price", 0)
    ses_min = raw.get("session_min", -1)

    # ── Session state ─────────────────────────────────────────
    if today != state.date:
        log.info(f"New session: {today}")
        state = SessionState(date=today)

    if ses == "OVERNIGHT" and not state.overnight_done:
        if price > state.overnight_high: state.overnight_high = price
        if price < state.overnight_low:  state.overnight_low  = price

    if ses == "OPEN" and not state.daily_open_set:
        state.daily_open = price
        state.daily_open_set = True
        state.overnight_done = True
        log.info(f"Daily open: {price:.2f}")

    # ── Reversal detection (15m / 22m) ───────────────────────
    dc_study = raw.get("day_context", {})
    ibh = dc_study.get("ib_high", 0)
    ibl = dc_study.get("ib_low", 0)
    for mark, at, ap in [(15,"rev15_type","rev15_price"),(22,"rev22_type","rev22_price")]:
        if ses_min >= mark and getattr(state,at) == "NONE" and ibh and ibl:
            if price > ibh + 0.25:
                setattr(state,at,"FAILED_BREAK_SHORT"); setattr(state,ap,price)
                log.info(f"Rev{mark}: FAILED_BREAK_SHORT @ {price:.2f}")
            elif price < ibl - 0.25:
                setattr(state,at,"FAILED_BREAK_LONG"); setattr(state,ap,price)
                log.info(f"Rev{mark}: FAILED_BREAK_LONG @ {price:.2f}")

    # ── Pull directly from Study ──────────────────────────────
    mtf     = raw.get("mtf", {})
    m3      = mtf.get("m3", {})
    m15     = mtf.get("m15", {})
    m30     = mtf.get("m30", {})
    m60     = mtf.get("m60", {})
    cvd     = raw.get("cvd", {})
    vwap_d  = raw.get("vwap", {})
    mp      = raw.get("market_profile", {})
    wp      = raw.get("woodi_pivots", {})
    tl      = raw.get("time_levels", {})
    of_data = raw.get("order_flow", {})
    cci     = raw.get("woodies_cci", {})       # ← חדש
    vol_ctx = raw.get("volume_context", {})    # ← חדש
    candle_p= raw.get("candle_patterns", {})  # ← חדש

    # Day context — מה-Study ישירות
    day_type    = dc_study.get("day_type", "DEVELOPING")
    ib_locked   = dc_study.get("ib_locked", False)
    ib_range    = dc_study.get("ib_range", 0)
    gap_type    = dc_study.get("gap_type", "FLAT")
    gap         = dc_study.get("gap", 0)
    total_ext   = dc_study.get("total_ext", 0)
    or_high     = dc_study.get("or_high", 0)
    or_low      = dc_study.get("or_low", 0)
    returned    = dc_study.get("returned_after_break", False)

    d20 = cvd.get("change_20bar", 0)
    cvd_trend = "BULLISH" if d20 > 100 else "BEARISH" if d20 < -100 else "NEUTRAL"

    ovl = state.overnight_low if state.overnight_low < 999999 else 0
    above_open = (price > state.daily_open) if state.daily_open_set else None

    return {
        "ts":    raw["timestamp"],
        "sym":   "MEMS26",
        "price": price,

        # נר 3m נוכחי
        "bar": {
            "o": m3.get("o", price), "h": m3.get("h", price),
            "l": m3.get("l", price), "c": price,
            "vol": m3.get("vol", 0), "buy": m3.get("buy", 0),
            "sell": m3.get("sell", 0), "delta": m3.get("delta", 0),
        },

        # MTF
        "mtf": {"m3": m3, "m15": m15, "m30": m30, "m60": m60},

        # CVD
        "cvd": {
            "total":    cvd.get("current", 0),
            "d20":      d20,
            "d5":       cvd.get("change_5bar", 0),
            "bull":     cvd.get("trend", "") == "BULLISH",
            "trend":    cvd_trend,
            "buy_vol":  cvd.get("buy_vol", 0),
            "sell_vol": cvd.get("sell_vol", 0),
            "delta":    cvd.get("delta", 0),
            "m15_delta":m15.get("delta", 0),
            "m60_delta":m60.get("delta", 0),
        },

        # VWAP
        "vwap": vwap_d,

        # Woodies CCI — ישירות מה-Study ← חדש
        "woodies_cci": cci,

        # Session
        "session": {
            "phase":     ses,
            "min":       ses_min,
            "sh":        mp.get("session_high", price),
            "sl":        mp.get("session_low", price),
            "ibh":       ibh,
            "ibl":       ibl,
            "ib_locked": ib_locked,
        },

        # Market Profile + Prev Day POC ← חדש
        "profile": {
            "poc":          mp.get("poc", 0),
            "vah":          mp.get("vah", 0),
            "val":          mp.get("val", 0),
            "tpo_poc":      mp.get("tpo_poc", 0),
            "prev_day_poc": mp.get("prev_day_poc", 0),  # ← חדש
            "in_va":        mp.get("in_value_area", False),
            "above_poc":    mp.get("above_poc", False),
        },

        # Woodi Pivots
        "woodi": {
            "pp": wp.get("pp", 0), "r1": wp.get("r1", 0), "r2": wp.get("r2", 0),
            "s1": wp.get("s1", 0), "s2": wp.get("s2", 0),
            "above_pp": wp.get("above_pp", False),
        },

        # Levels
        "levels": {
            "h72": tl.get("h72_high", 0),       "l72": tl.get("h72_low", 0),
            "hwk": tl.get("weekly_high", 0),    "lwk": tl.get("weekly_low", 0),
            "prev_high":  tl.get("prev_high", 0),
            "prev_low":   tl.get("prev_low", 0),
            "prev_close": tl.get("prev_close", 0),
            "daily_open": tl.get("daily_open", state.daily_open),
            "overnight_high": tl.get("overnight_high", state.overnight_high),
            "overnight_low":  tl.get("overnight_low", ovl),
            "above_open": above_open,
        },

        # Order Flow
        "order_flow": {
            "absorption_bull":  of_data.get("absorption_bull", False),
            "liq_sweep":        of_data.get("liq_sweep_long", False),   # backward compat
            "liq_sweep_long":   of_data.get("liq_sweep_long", False),
            "liq_sweep_short":  of_data.get("liq_sweep_short", False),  # ← חדש
            "imbalance_bull":   sum(1 for i in of_data.get("imbalances",[]) if i.get("ratio",0)>0),
            "imbalance_bear":   sum(1 for i in of_data.get("imbalances",[]) if i.get("ratio",0)<0),
            "imbalances":       of_data.get("imbalances", []),
        },

        # Day Context — מה-Study ← מורחב
        "day": {
            "type":           day_type,
            "ib_range":       ib_range,
            "ib_locked":      ib_locked,
            "gap":            gap,
            "gap_type":       gap_type,
            "total_ext":      total_ext,
            "returned":       returned,
            "or_high":        or_high,
            "or_low":         or_low,
            "range":          round(mp.get("session_high", 0) - mp.get("session_low", 0), 2),
        },

        # Volume Context ← חדש
        "volume_context": vol_ctx,

        # Candle Patterns ← חדש
        "candle_patterns": candle_p,

        # Order Fills — פקודות שבוצעו
        "order_fills": raw.get("order_fills", []),

        # Footprint — 10 נרות אחרונים
        "footprint": raw.get("footprint", []),

        # Reversal
        "reversal": {
            "ib_high":    ibh,
            "ib_low":     ibl,
            "locked":     ib_locked,
            "rev15_type": state.rev15_type,
            "rev15_price":state.rev15_price,
            "rev22_type": state.rev22_type,
            "rev22_price":state.rev22_price,
        },
    }


async def redis_post(http, path, data):
    try:
        async with http.post(
            f"{REDIS_URL}/{path}",
            headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
            json=data,
            timeout=aiohttp.ClientTimeout(total=4.0)
        ) as resp:
            if resp.status != 200:
                log.warning(f"Redis {path} {resp.status}")
    except Exception as e:
        log.warning(f"Redis failed ({path}): {e}")


async def save_candle(http, c: CandleBuilder, raw: dict = None):
    # העשר נר עם נתוני indicators לפני שמירה
    if raw:
        cci  = raw.get("woodies_cci", {})
        vwap = raw.get("vwap", {})
        of2  = raw.get("order_flow", {})
        sess = raw.get("session", {})
        c.cci14           = float(cci.get("cci14", 0) or 0)
        c.cci6            = float(cci.get("cci6", 0) or 0)
        c.vwap            = float(vwap.get("value", 0) or 0)
        c.phase           = str(sess.get("phase", ""))
        c.above_vwap      = bool(vwap.get("above", False))
        c.liq_sweep_long  = bool(of2.get("liq_sweep_long", False))
        c.liq_sweep_short = bool(of2.get("liq_sweep_short", False))
    candle_json = json.dumps(c.to_dict())
    await redis_post(http, f"lpush/{REDIS_CANDLES}", candle_json)
    await redis_post(http, f"ltrim/{REDIS_CANDLES}/0/{MAX_CANDLES-1}", "")
    log.info(f"Candle saved: {c.c:.2f} Δ={c.buy-c.sell:.0f} CCI14={c.cci14:.1f} VWAP={c.vwap:.2f}")


async def main():
    if not REDIS_URL or not REDIS_TOKEN:
        log.error("Missing UPSTASH credentials"); return

    log.info("="*50)
    log.info("  MEMS26 Bridge v6 — Full Data + History 960")
    log.info(f"  SC JSON    : {SC_JSON_PATH}")
    log.info(f"  SC HISTORY : {SC_HISTORY_PATH}")
    log.info(f"  Redis      : {REDIS_URL}")
    log.info("="*50)

    # ── טעינת היסטוריה מקובץ Sierra Chart ─────────────────────
    async with aiohttp.ClientSession() as http:
        try:
            if os.path.exists(SC_HISTORY_PATH):
                age_h = time.time() - os.path.getmtime(SC_HISTORY_PATH)
                if age_h < 3600:  # קובץ עד שעה ישן
                    with open(SC_HISTORY_PATH) as hf:
                        hist = json.load(hf)
                    candles = hist.get("candles", [])
                    if candles:
                        log.info(f"Loading {len(candles)} historical candles from Sierra...")
                        API_URL = os.getenv("API_URL", "http://localhost:8000")
                        BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "michael-mems26-2026")
                        async with http.post(
                            f"{API_URL}/ingest/history",
                            json={"candles": candles},
                            headers={"x-bridge-token": BRIDGE_TOKEN},
                            timeout=aiohttp.ClientTimeout(total=30.0)
                        ) as resp:
                            if resp.status == 200:
                                log.info(f"History loaded: {len(candles)} candles → API OK")
                            else:
                                log.warning(f"History API returned {resp.status}")
                else:
                    log.info(f"History file too old ({age_h:.0f}s), skipping")
            else:
                log.info("No history file found — will accumulate live")
        except Exception as e:
            log.warning(f"History load failed: {e}")

    last_send = 0.0

    async with aiohttp.ClientSession() as http:
        while True:
            try:
                with open(SC_JSON_PATH) as f:
                    raw = json.load(f)

                age = time.time() - os.path.getmtime(SC_JSON_PATH)
                if age > 30:
                    log.warning(f"Stale ({age:.0f}s)")
                    await asyncio.sleep(1); continue

                price = raw.get("current_price", 0)
                m3    = raw.get("mtf", {}).get("m3", {})
                buy   = m3.get("buy", 0)
                sell  = m3.get("sell", 0)
                vol   = m3.get("vol", 0)
                ts    = raw.get("timestamp", 0)

                # ── Candle Building ───────────────────────────
                candle_ts = (ts // CANDLE_INTERVAL) * CANDLE_INTERVAL

                if candle.start_ts == 0:
                    candle.start_ts = candle_ts
                    candle.update(price, buy, sell, vol)
                elif candle_ts > candle.start_ts:
                    await save_candle(http, candle, raw)
                    candle.__init__()
                    candle.start_ts = candle_ts
                    candle.update(price, buy, sell, vol)
                else:
                    candle.update(price, buy, sell, vol)

                # ── Send to Redis ─────────────────────────────
                now = time.time()
                if now - last_send >= POST_INTERVAL:
                    payload = enrich(raw)
                    payload["current_candle"] = candle.to_dict()
                    await redis_post(http, f"set/{REDIS_KEY}", payload)
                    last_send = now
                    day_type = payload["day"]["type"]
                    log.info(f"-> {raw.get('session_phase','?')} | {price:.2f} | {day_type} | buy={buy:.0f} sell={sell:.0f}")

            except FileNotFoundError:
                log.warning("JSON not found")
            except json.JSONDecodeError:
                pass
            except Exception as e:
                log.error(f"Error: {e}")
            await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())
