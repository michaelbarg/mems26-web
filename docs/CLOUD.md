# MEMS26 — CLOUD.md (אינדקס-מערכת מרוכז)

**מטרה:** נקודת-כניסה **אחת** לסוכן Cloud / Cursor / Cowork — במקום לדפדף 117 קבצי `_INDEX.md`.
**מקור:** נגזר מ-`SYSTEM_INDEX.md` + תתי-אינדקסים (2026-07-17) · מסונכרן עם `docs/SYSTEM_MANIFEST.md` · `docs/SOURCE_OF_TRUTH.md` · `CLAUDE.md`.

> **לפני כל סשן:** `git pull` → קרא `docs/handoff/LIVE_CHANNEL.md` (ערוץ-חי) · `docs/handoff/AGENT_SYNC.md` §🔴 OPEN.

---

## 1. תמונת-על

```
Sierra Chart (CrossOver/Wine)
  └─ DLL  sc_study/MES_AI_DataExport.cpp  →  ~/SierraChart_Data/v9_export/*.json
       └─ promoter  scripts/v9_export_promoter.py  (.tmp → .json)
            └─ Bridge  bridge/json_bridge.py  (+ 14 streams ב-bridge/v9_streams/)
                 └─ CLOUD_URL=http://localhost:8000 ONLY  →  FastAPI backend :8000
                      ├─ Postgres  postgresql://localhost/mems26
                      ├─ Redis/Upstash  (Event Bus)
                      └─ Next.js frontend :3000  (frontend/v9/)
```

| שכבה | תפקיד |
|------|--------|
| **Layer 0** | Chop / session context (`backend/v9/systems/layer0/`) |
| **Layer 1** | 6 מערכות-עצמאיות (S1–S6) — זיהוי + ירי |
| **Layer 2** | Day-type + direction — מסנן הקשר |
| **Layer 3** | Pre-fire validation, risk, confluence |
| **Layer 4** | Targets / stops / structural levels |
| **Gateway** | SHADOW / DEMO / LIVE routing → Sierra DLL |

**Repo:** `/Users/michael/Downloads/mems26_web_git` · **846 קבצים** · **117 תיקיות** עם `_INDEX.md`.

---

## 2. עץ-עליון (SYSTEM_INDEX)

| תיקייה | קבצים | אינדקס | תפקיד |
|--------|-------|--------|--------|
| `backend/` | 526 | `backend/_INDEX.md` | FastAPI · מערכות · gateway · DB · WS |
| `frontend/v9/src/` | 179 | `frontend/v9/src/app/_INDEX.md` + `v9/components/_INDEX.md` | Next.js cockpit |
| `bridge/` | 28 | `bridge/_INDEX.md` | קריאת JSON מ-Sierra → push ל-backend |
| `scripts/` | 108 | `scripts/_INDEX.md` | ops · verify · backtest · gen_index |
| `sc_study/` | 5 | `sc_study/_INDEX.md` | מקור C++ ל-DLL |

**Entry points קריטיים (אל תטעו):**

| מה | קובץ אמיתי | לא |
|----|------------|-----|
| Backend boot | `backend/main.py` | ~~`backend/v9/main.py`~~ |
| Bridge | `bridge/json_bridge.py` | |
| V9 app/router | `backend/v9/app.py` | |
| Frontend root | `frontend/v9/src/app/page.tsx` | |
| DLL deploy | `scripts/build_monolithic_cpp.sh --deploy` | |

---

## 3. שש המערכות (S1–S6)

| # | שם | תיקייה | קובץ-ליבה | תפקיד |
|---|-----|--------|-----------|--------|
| **S1** | Day Type | `backend/v9/systems/day_type/` | `state_machine.py` · `classifier_core.py` · `daytype_classifier.py` | 7 סוגי-יום · IB · direction |
| **S2** | 5-min T1 | `backend/v9/systems/five_min/` | `five_min_system.py` · `setup_emitter.py` | Reactive / Initiative · Auth Table |
| **S3** | Footprint T3 | `backend/v9/systems/footprint/` | (muted/broken — I-11) | COT/AMT · order flow |
| **S4** | Woodies CCI | `backend/v9/systems/woodies/` | `woodies_system.py` · `pattern_engine.py` | 8 תבניות CCI · 30m+5m |
| **S5** | TPO | `backend/v9/systems/tpo/` | | IB/VAH/VAL/POC |
| **S6** | Killzone / Mgmt | `backend/v9/systems/killzone/` + `system6_*.py` | `system6_supervisor.py` | פיקוח עסקה · MODIFY_STOP |

**Wrappers (חיבור ל-bar pipeline):** `backend/v9/systems/wrappers.py`  
**Build Status (מצב-מערכות):** `backend/v9/systems/build_status/` → `GET /api/v9/build/pattern-status`

### S1 — Day Type (מקור-אמת)

| שימוש | מקור | הערה |
|-------|------|------|
| ✅ **canonical 7-type** | `classifier_core.classify_session` · `GET /api/v9/day_type/classify_replay` | **READ FIRST:** `docs/spec_authority/S1_ACTIVE_CANONICAL.md` |
| 🟡 live engine (3-type ישן) | `app.state.day_type_machine` · `v9_day_type_state` | עד `S1_ENGINE_NEW_CLASSIFIER=1` |
| ✅ direction עכשיו | `direction_context_live.py` · `GET /api/v9/day_type/direction_now` | |
| 🔴 DEAD | `/api/v9/day_type/v9/current` · `/api/v9/day_type/current` | אל תחבר מחדש |

### S2 — Five Min

- **Detector:** `five_min_system.py` (1622 LOC) — lifecycle מלא D-077
- **Emit path:** `setup_emitter.py` → pre_fire → gateway
- **Patterns:** `backend/v9/systems/five_min/patterns/`
- **Auth table:** `auth_table_v1.py` · `quality_tier.py`
- **Gate עצמאי מ-S3:** `S2_REQUIRE_COT_AMT` default OFF

### S4 — Woodies

- **Detector:** `woodies_system.py` · `pattern_engine.py` (8 patterns)
- **Stages:** `backend/v9/systems/woodies/stages/`
- **Stream:** `bridge/v9_streams/woodies_5min_stream.py` + `woodies_30min_stream.py`
- **Chart API:** `GET /api/v9/woodies/chart`

---

## 4. צינור-נתונים (Bridge → DB)

### 14 Bridge streams (`bridge/v9_streams/`)

| Stream | קובץ | JSON export | מערכת |
|--------|------|-------------|--------|
| 5min OHLCV | `bars_5min_stream.py` | `5min.json` | S2 |
| 5min continuous | `bars_5min_continuous_stream.py` | `5min_continuous.json` | (CVD delta — יכול לעצור) |
| Woodies 5m | `woodies_5min_stream.py` | `woodies_5min.json` | S4 |
| Woodies 30m | `woodies_30min_stream.py` | `woodies_30min.json` | S4 |
| TPO | `tpo_stream.py` | `tpo.json` | S5 |
| Footprint | `footprint_stream.py` | `footprint.json` | S3 |
| CVD | `cumulative_delta_stream.py` | `cumulative_delta.json` | S2/S1 |
| Live price | `live_price_stream.py` | `live_price.json` | UI |
| Tick reversal 12/15 | `tick_reversal_*_stream.py` | | |
| Volume profile / imbalances | `volume_profile_stream.py` etc. | | |

**Base:** `base_stream.py` — **מסרב להתחיל** אם `CLOUD_URL` ≠ localhost/127.0.0.1.

### טבלאות DB עיקריות (Postgres local)

| סיגנל | טבלה / endpoint | הערה |
|-------|-----------------|------|
| OHLC live + trend | `v9_bars_5min_woodies` | contiguous · **preferred for price geometry** |
| OHLC + bar delta | `v9_bars_5min` | `cumulative_delta` = per-bar delta (misnomer) · **can stall** |
| 🔴 avoid | `v9_bars_5min_continuous` | close garbage — excluded from chart API |
| TPO levels | `v9_tpo_sessions` WHERE `session_type='CASH'` | `trading_date` = VARCHAR ISO string |
| Trades | `v9_trades` + `v9_trade_management_log` | |
| S2 setups | `v9_five_min_setups` | |
| Day-type state | `v9_day_type_state` | live engine persistence |

**TZ:** timestamps stored +03:00 · trading windows in `America/Chicago` · RTH 08:30–15:00 CT.

---

## 5. Backend — מפת API (`backend/v9/api/v9/`)

| קובץ | Endpoint(s) | שימוש |
|------|-------------|--------|
| `status.py` | `GET /api/v9/status` | 5-layer health dashboard |
| `bars.py` | `POST /api/v9/bars/*` | Bridge ingest (push) |
| `bars_5min_history.py` | `GET /api/v9/chart/bars*` | Chart rendering |
| `price_routes.py` | `GET /api/v9/live_price` | ~200ms tick |
| `daytype_classify_routes.py` | `GET /api/v9/day_type/classify_replay` | **S1 authority** |
| `key_levels_routes.py` | `GET /api/v9/key_levels` | IB/VAH/VAL strip |
| `tpo_routes.py` | `GET /api/v9/tpo/*` | TPO panel |
| `build_status_routes.py` | `GET /api/v9/build/pattern-status` | Pattern build tree |
| `gateway_routes.py` | `GET /api/v9/gateway/*` | SHADOW/DEMO/LIVE status |
| `trades.py` | `/api/v9/trades` | Journal + mgmt log |
| `system6_routes.py` | `/api/v9/system6/*` | Active-trade diagnosis |
| `mobile_monitor.py` | `/api/v9/mobile` | iPhone pocket monitor |
| `websocket.py` | WS feeds | Real-time dashboard |
| `kill_switch_routes.py` | kill-switch | Halt all firing |

**Auth:** `backend/v9/api/v9/auth.py` — `BRIDGE_TOKEN` header.

---

## 6. Gateway & Execution

| קובץ | תפקיד |
|------|--------|
| `backend/v9/gateway/trading_gateway.py` | 3-mode router (2209 LOC) — **לב trading logic** |
| `backend/v9/services/trading_gateway/` | Executors · validators |
| `backend/v9/services/pre_fire_validator/` | Pre-fire gates |
| `backend/v9/services/risk_validator/` | Risk caps |
| `bridge/trade_commands.py` | File-based Sierra command/result |
| `backend/v9/services/sierra_command.py` | Write trade commands to DLL path |
| `backend/v9/services/fill_poller.py` | Read `trade_fills.json` → TradeManager |

**מodes:** SHADOW (record only) · DEMO (Sierra sim) · LIVE (real money)

### ⛔ op=EXIT — שבור, אסור

`write_exit` / `op="EXIT"` → DLL `r=-1`. **אל תאפשר** `STALL_EXIT` / `OPPOSITE_EXIT_V1` עד EXIT-v2.
**יציאות עובדות:** T1/T2/T3 OCO (Sierra-side) · `MODIFY_STOP` · `FLATTEN_ACCOUNT`.

---

## 7. Services שכבת-תשתית (`backend/v9/services/`)

| שירות | קובץ | תפקיד |
|-------|------|--------|
| Bar pipeline | `bar_router.py` · `bar_ingestion.py` · `bar_aggregator_5min.py` | 5min distribution |
| Feed health | `feed_watchdog.py` · `frozen_tail_watchdog.py` | block fires when stale |
| Reconcile | `sierra_position_reconciler.py` · `reconcile.py` | Sierra truth vs DB |
| Trade mgmt | `trade_manager/` · `active_trade_manager/` | In-trade lifecycle |
| Market time | `market_clock.py` | ET + holidays D-068 |
| Kill switch | `kill_switch.py` | Emergency halt |
| Ops | `ops_log.py` (via `scripts/ops_log.py`) | Central ops log |
| EOD | `eod_archiver.py` · `eod_archive_scheduler.py` | End-of-day archive |

---

## 8. Frontend (`frontend/v9/src/`)

| אזור | תיקייה | רכיבים עיקריים |
|------|--------|----------------|
| Dashboard | `v9/components/layout/` · `chart/` | `ChartV5b` · `V9Dashboard` |
| Build tree | `build_tree/` · `build_status/` | Pattern readiness |
| Day type | `day-type/` · `strips/` | Pills · KeyLevelsStrip |
| Trades | `trades/` · `app/trades/` | Trade history · marker.html |
| Systems pills | `systems/` | S1–S4 status |
| Health | `health/` · `topbar/` | Stream health · heartbeat |
| Mobile | (served from backend) | `/api/v9/mobile` |
| Agent chat | `agent/` | In-dashboard Claude |
| Board | `app/board/` | Task board from DEV_BACKLOG |

**Polling floors (אל תקטין):** ראה `CLAUDE.md` § Frontend Polling Floors — e.g. system state 5000ms, sound 10000ms.

---

## 9. Scripts & Ops (בחירה)

| Script | תפקיד |
|--------|--------|
| `scripts/gen_index.py` | regenerate `SYSTEM_INDEX.md` + all `_INDEX.md` |
| `scripts/gen_flag_index.py` | regenerate `docs/FLAG_INDEX.md` |
| `scripts/mems26_verify.sh` | one-shot system consistency |
| `scripts/mems26_snapshot.sh` | snapshot out-of-git surfaces before change |
| `scripts/mems26_restore.sh` | rollback snapshot |
| `scripts/flag_guard.py` | verify ruled flags didn't drift |
| `scripts/post_restart_verify.sh` | liveness gate after restart |
| `scripts/start_all.sh` | bridge+backend+frontend (screen) |
| `scripts/build_monolithic_cpp.sh --deploy` | DLL monolith → Sierra |

---

## 10. משטחים מחוץ ל-git (snapshot חובה)

| Surface | מיקום |
|---------|--------|
| DLL source+binary | `~/SierraChart*/ACS_Source/` · `Data/MES_AI_DataExport_64.dll` |
| `.env` (flags live) | `<repo>/.env` |
| LaunchAgents | `~/Library/LaunchAgents/com.mems26.{backend,bridge,export_promoter,frontend}.plist` |
| Sierra exports | `~/SierraChart_Data/v9_export/*.json` |
| Postgres | `postgresql://localhost/mems26` |
| Snapshots | `~/mems26_snapshots/` |

**Sierra Inputs (per chart):** 0=ExportPath · 4=V9 Export Dir · 21=EnableOrderPlacement (**default OFF**).

---

## 11. שירותים & פורטים

| Service | Port | LaunchAgent | Verify |
|---------|------|-------------|--------|
| Backend | `:8000` | `com.mems26.backend` | `curl :8000/health` |
| Frontend | `:3000` | `com.mems26.frontend` | `curl :3000` |
| Bridge | (process) | `com.mems26.bridge` | `pgrep -f json_bridge.py` |
| Export promoter | (process) | `com.mems26.export_promoter` | JSON mtime ≤2s |
| Postgres | `:5432` | (local) | `psql mems26` |

---

## 12. Guardrails — חובה לסוכן Cloud

### Local-only (PERMANENT)
- Bridge **רק** `CLOUD_URL=http://localhost:8000` — **לעולם לא** `mems26-web.onrender.com`
- DB **רק** local Postgres — לא Render/Upstash prod DB
- Render cloud = deployment נפרד/ישן — **לא** מקור-אמת ל-LIVE

### Standing decisions (default OFF — אל תדליק בלי פסיקת מייקל)
- S2 `choppiness_ok` · Layer-0 chop veto · `S2_REQUIRE_COT_AMT`
- כל re-enable = **strategic stop** + חתימת מייקל

### Source-of-truth discipline
1. **Honest failure > synthetic** — `None` / `"missing"`, לא bars fallback עם `found=True`
2. **Verify before trust** — DB query לפני patch
3. **min/max aggregators amplify** — audit downstream after synthesis fix
4. **TZ explicit** — כל `HH:MM:SS` עם timezone
5. **Verification quote** — פקודה + פלט גולמי, לא "תוקן"

### UAT 4 axes (כל endpoint נתונים)
Quality · Recency · Cardinality · Latency — **כולם**, לא רק הבאג שתיקנת.

---

## 13. אינדקסים עמוקים — לא לשכפל, לקרוא

| מסמך | מתי |
|------|-----|
| `SYSTEM_INDEX.md` + `*/_INDEX.md` | locate file/function (auto-gen) |
| `docs/SOURCE_OF_TRUTH.md` | WHICH table is canonical per signal |
| `docs/FLAG_INDEX.md` | flag ON/OFF (auto-gen from code+.env) |
| `docs/SYSTEM_MANIFEST.md` | out-of-git surfaces + snapshot protocol |
| `docs/handoff/LIVE_CHANNEL.md` | משימות פתוחות + LOG חי |
| `docs/handoff/AGENT_SYNC.md` | תיאום cowork ⇄ cc-imac |
| `docs/handoff/INDEX.md` | בית-אחד — איפה כל משטח חי |
| `docs/plans/STATUS_BOARD.md` | יומן החלטות |
| `docs/plans/ROADMAP_TO_LIVE.html` | מפת-דרך ל-LIVE |
| `CLAUDE.md` | guardrails מלאים |
| `.cursor/rules/mems26-pre-live-protocol.mdc` | פרוטוקול pre-LIVE |

---

## 14. רשת & גישה מרחוק (2026-07-18)

| מכונה | ZeroTier IP | תפקיד |
|-------|-------------|--------|
| MacBook (trading) | 10.1.118.147 | **primary** — LIVE |
| iMac | 10.1.118.70 | SIM/backup |
| iPhone | 10.1.118.31 | pocket monitor |

- **ZeroTier בלבד** (לא Tailscale — פסיקת מייקל)
- Dashboard: `http://10.1.118.147:3000` (MacBook) or iMac IP
- Mobile: `/api/v9/mobile?key=` (backend-served)

---

## 15. רענון האינדקס

```bash
# אחרי שינוי מבני (קובץ/תיקייה/מערכת חדשה):
python3 scripts/gen_index.py

# אחרי שינוי flag:
python3 scripts/gen_flag_index.py

# בדיקת drift:
python3 scripts/gen_flag_index.py --check
python3 scripts/mems26_verify.sh
```

---

*נוצר 2026-07-18 · consolidated from SYSTEM_INDEX (846 files, 117 dirs). עדכן כשמוסיפים מערכת/משטח חדש — או הרץ `gen_index.py` וסנכרן סעיפים 2–9.*
