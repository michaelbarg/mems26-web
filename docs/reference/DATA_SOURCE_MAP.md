# MEMS26 Data Source Map

**Canonical rule:** Live trading values come from **Sierra Chart exports** → **Bridge** → **DB** → **API/UI**.  
**DB path:** `/Users/michael/Downloads/mems26_web_git/data/mems26_local.db`  
**Sierra exports:** `/Users/michael/SierraChart_Data/v9_export/`

---

## Sierra Study: `MES AI Data Export v9.4.2`

| Input | Name | Default | Purpose |
|-------|------|---------|---------|
| 4 | V9 Export Directory | `~/SierraChart_Data/v9_export/` | All JSON files |
| 13 | TPO Yesterday Study ID | 1 | TPO VA Lines ref=1 |
| 14 | TPO Today Study ID | 3 | TPO VA Lines ref=0 |
| 15 | Initial Balance Study ID | 6 | IB study |
| 16 | Projected H/L Study ID | 0 | proj_hi/proj_lo for Woodies |
| 17 | TPO Chart Number | 0 | Chart hosting TPO+IB |
| 18 | Woodies Chart Number | 0 | Chart hosting Woodies studies |

---

## Category 1 — Market Bars / Price / Flow

| Field | Sierra | JSON | Bridge → API | DB table | Direct SQL |
|-------|--------|------|--------------|----------|------------|
| Live price | chart | `live_price.json` | POST `/api/v9/live_price` | — (WS) | `cat live_price.json` |
| 5min OHLCV | chart 5m | `5min.json` | POST `/api/v9/bars/5min` | `v9_bars_5min` | `SELECT ts,open,high,low,close,volume FROM v9_bars_5min ORDER BY ts DESC LIMIT 20` |
| Bar POC/VAP | VAP per bar | `5min.json` | ↑ | `poc_vol,vah,val` cols | same table |
| CVD | CVD subgraph | `cumulative_delta.json` | POST `/api/v9/bars/cumulative_delta` | `v9_bars_cumulative_delta` | `SELECT ts,delta,cumulative FROM v9_bars_cumulative_delta ORDER BY ts DESC LIMIT 20` |
| Volume profile | VAP | `volume_profile.json` | POST `/api/v9/bars/volume_profile` | `v9_bars_volume_profile` | `SELECT ts,poc,vah,val FROM v9_bars_volume_profile ORDER BY ts DESC LIMIT 10` |
| Footprint | **SCID ticks** | monitor only | POST `/api/v9/bars/footprint` | `v9_bars_footprint` | `SELECT ts,delta FROM v9_bars_footprint ORDER BY ts DESC LIMIT 5` |
| Tick reversal 12/15 | study | `tick_reversal_*.json` | POST `/api/v9/bars/tick_reversal` | `v9_bars_tick_reversal` | `SELECT ts,bar_id FROM v9_bars_tick_reversal ORDER BY ts DESC LIMIT 5` |
| Imbalance | study | `imbalance_flags.json` | POST `/api/v9/bars/imbalance` | `v9_bars_imbalance` | `SELECT * FROM v9_bars_imbalance ORDER BY ts DESC LIMIT 5` |

**Chart API:** `GET /api/v9/chart/bars5min` ← `v9_bars_5min`

---

## Category 2 — TPO / IB / POC

| Field | Sierra Study | Subgraph | JSON | DB table | Direct SQL |
|-------|-------------|----------|------|----------|------------|
| POC today | ID **3** | idx 0 | `session.poc` | `v9_tpo_sessions` CASH | `SELECT poc_price,vah_price,val_price FROM v9_tpo_sessions WHERE trading_date=date('now') AND session_type='CASH'` |
| VAH/VAL | ID 3 | idx 1/2 | `session.vah/val` | ↑ | ↑ |
| IB high | ID **6** | **idx 6** | `ib.high` | `v9_tpo_sessions` + `v9_day_type_history` | see Category 3 |
| IB low | ID 6 | **idx 8** | `ib.low` | ↑ | ↑ |
| Session H/L | chart loop | — | `session.session_high/low` | — | read `tpo.json` |
| POC prev day | ID **1** ref=1 | idx 0/1/2 | `previous_session` | `v9_tpo_sessions` CASH | `SELECT * FROM v9_tpo_sessions WHERE trading_date=date('now','-1 day') AND session_type='CASH'` |

**Live TPO API (file-first):** `GET /api/v9/tpo/current` reads **`tpo.json` directly** (not DB) for lowest latency.  
**Key Levels API (DB-first):** `GET /api/v9/key_levels` reads **DB tables** + returns `sources` map.

---

## Category 3 — Day Type (S1)

| Field | Source | DB table | Direct SQL |
|-------|--------|----------|------------|
| day_type, opening_type | S1 state machine | `v9_day_type_history` | `SELECT day_type,opening_type,ib_width_class FROM v9_day_type_history WHERE date=date('now')` |
| IB (authoritative S1) | RTH 5min bars only | `v9_day_type_history` | `SELECT ib_high,ib_low,ib_width FROM v9_day_type_history WHERE date=date('now')` |
| globex_h/l, rth_h/l | S1 meta | `v9_day_type_state.meta` | `SELECT meta FROM v9_day_type_state ORDER BY rowid DESC LIMIT 1` |
| stage, confidence | state machine | `v9_day_type_state` | `SELECT ts,stage,confidence FROM v9_day_type_state ORDER BY rowid DESC LIMIT 5` |

**API:** `/api/v9/day_type/v9/current` → `v9_day_type_history`

---

## Category 4 — Woodies (S4)

**Sierra chart (Input 18):**

| JSON field | Study ID | Subgraph | DB column |
|------------|----------|----------|-----------|
| cci_14 | 4 | 0 | `cci_14` |
| cci_6_tcci | 10 | 0 | `cci_6_tcci` |
| ema_34 | 3 | 0 | `ema_34` |
| lsma_value | 2 | 0 | `lsma_value` |
| swi_value | 6 | 5 | `swi_value` |
| czi_value | 7 | 2 | `czi_value` |
| trend_state | 1 | 1/2/3 | `trend_state` |
| predictor_next_cci | 11 | 0/1 | `predictor_next_cci` |
| proj_hi / proj_lo | Input 16 | 1/2 | `proj_hi`, `proj_lo` *(migration 018)* |
| hfe_* | DLL compute | — | `hfe_detected`, `hfe_direction`, `hfe_extreme_bars_ago` |
| lsma_above_price | DLL | — | `lsma_above_price` |
| zlr_* | DLL compute | — | `zlr_detected`, `zlr_direction` |

**Pipeline:** `woodies_5min.json` → POST `/api/v9/bars/woodies_5min` → `v9_bars_5min_woodies`  
**SQL:** `SELECT ts,close,cci_14,trend_state,proj_hi,proj_lo FROM v9_bars_5min_woodies ORDER BY ts DESC LIMIT 10`  
**Signals:** `v9_woodies_signals` · **Patterns:** `v9_woodies_patterns`  
**API state:** `GET /api/v9/woodies/current`

---

## Key Levels Strip — DB table per field

| UI field | Primary table | Fallback |
|----------|---------------|----------|
| IB H/L | `v9_day_type_history` | `v9_tpo_sessions.CASH` → `GLOBEX` |
| POC/VAH/VAL today | `v9_tpo_sessions.CASH` | — |
| Globex range | `v9_bars_5min` (pre-RTH) | — |
| RTH range | `v9_bars_5min` (post-RTH) | — |
| Prev POC/IB | `v9_tpo_sessions.CASH` (yesterday) | — |
| day_type | `v9_day_type_history` | — |

Response includes `"sources": {...}` for UAT.

---

## Gap-fill (startup only)

| JSON | DB |
|------|-----|
| `5min.json` | `v9_bars_5min` |
| `cumulative_delta.json` | `v9_bars_cumulative_delta` |
| `volume_profile.json` | `v9_bars_volume_profile` |

Trigger: backend startup or `POST /api/v9/admin/history/gap_fill`

---

## Quick probe commands

```bash
DB="/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
EXPORT="/Users/michael/SierraChart_Data/v9_export"

sqlite3 $DB "SELECT ib_high,ib_low FROM v9_day_type_history WHERE date=date('now')"
sqlite3 $DB "SELECT session_type,poc_price,ib_high,ib_low FROM v9_tpo_sessions WHERE trading_date=date('now')"
curl -s localhost:8000/api/v9/key_levels | python3 -m json.tool
cat $EXPORT/tpo.json | python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('ib'), d.get('session'))"
```

See also: [DATA_SOURCE_GAPS.md](./DATA_SOURCE_GAPS.md)
