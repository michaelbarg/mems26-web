# PREOPEN NO-BLOCKER SWEEP · 2026-07-20

**זמן סריקה:** ~4ש' לפני פתיחת RTH (13:19 IDT · 06:19 ET · ~191 דק' ל-09:30 ET)  
**מבצע:** cursor-agent · **קריאה-בלבד** · `is_sim=1` · אין PLACE · אין `.env`  
**מאמת:** cowork (Rule 5)

---

## סיכום-מנהלים

**עדכון cowork 07-20 (אימות Rule 5):** **0 מחסומי-ירי קשים** לפני RTH.

| מצב | ספירה |
|-----|-------|
| 🟢 GO | 30 |
| 🟡 WATCH (re-check / אופציונלי) | 10 |
| 🔴 NO-GO (מחסום-ירי) | **0** |

**מסקנה:** הצינורות, המנועים והשערים **מוכנים ל-Globex/pre-RTH**.  
**⛔ לפני 16:30 IL:** החזר Sierra ל-LIVE + אמת `is_sim=0`.

**מוכן ל-cc:**
- ORPHAN: `scripts/verify_orphan_place_stop_sim.py`
- T17 4-contract: `scripts/verify_t17_e2e_4contract_sim.py`
- T15 stage-E: `scripts/fire_readiness_real.py` (`FIRE_DRILL_STAGE_E=0`)

**Re-check 09:35 ET:** A12 — אמת ש-`chart/bars5min` התמלא אחרי RTH (אז 🟢).

---

## A · צינורות-נתונים

| # | בדיקה | פקודה | פלט (RAW) | 🟢/🔴 |
|---|--------|--------|-----------|-------|
| A1 | Sierra export טרי | `ls -la ~/SierraChart_Data/v9_export/*.json \| head -5` | `woodies_5min.json Jul 20 13:17` · `5min.json Jul 20 13:17` · `sierra_state.json Jul 20 13:17` | 🟢 |
| A2 | Sierra state · sim · שטוח | `cat ~/SierraChart_Data/v9_export/sierra_state.json` | `{"is_sim":1,"position_qty":0,"working_orders":0,"order_placement_armed":1,"send_orders_to_trade_service":0,...}` | 🟢 |
| A3 | Bridge localhost בלבד · רץ | `pgrep -fl bridge` + `grep CLOUD_URL ~/Library/LaunchAgents/com.mems26.bridge.plist` | `Python bridge/json_bridge.py` · `CLOUD_URL="http://localhost:8000"` | 🟢 |
| A4 | אין push לענן | `grep -E 'https://' /tmp/bridge.err.log \| tail -3` | רק `Connection refused` ל-`localhost:8000` מ-07-17 (backend down אז) — **אין** `https://` cloud | 🟢 |
| A5 | export_promoter רץ | `pgrep -fl v9_export_promoter` | `Python .../scripts/v9_export_promoter.py` | 🟢 |
| A6 | Backend :8000 | `curl -sf http://127.0.0.1:8000/health` | `{"status":"ok","service":"mems26-unified","version":"9.0.0",...}` | 🟢 |
| A7 | Bridge pushes חיים | `tail -3 /tmp/bridge.err.log` | `[woodies_5min] New data — export_ts=... (push #42846)` · `[bars_5min] New data` | 🟢 |
| A8 | CVD זורם | `python3 -c "import json;d=json.load(open('~/SierraChart_Data/v9_export/cumulative_delta.json'.replace('~','$HOME')))"` … | `points_count=90` · `session_delta=-4067` · `trend=BEARISH` | 🟢 |
| A9 | Stream health (bridge→API) | `curl -sf http://127.0.0.1:8000/api/v9/health/streams` (subset) | `live_price: healthy age=0.5s push=42341 err=0` · `woodies_5min: healthy age=2s push=14606` · `5min: healthy age=1.3s push=14689` · `cumulative_delta: healthy` | 🟢 |
| A10 | live_price API | `curl -sf http://127.0.0.1:8000/api/v9/live_price` | `price=7517.88 age_ms=161 source=cache` | 🟢 |
| A11 | mems26_verify | `bash scripts/mems26_verify.sh` | `verdict: OK · 3 warn` — services ✅ · DLL deployed==repo ✅ · woodies export fresh ✅ · warns: FLAG_INDEX drift · sc_study uncommitted · PG query from script failed | 🟡 |
| A12 | chart/bars5min DB (RTH table) | `curl -sf '.../chart/bars5min?limit=1'` | `[{"ts":"2026-07-17 22:55:00+03:00",...}]` — **Friday = אחרון RTH** | 🟡 **re-check 09:35** |
| A13 | woodies/chart (Sierra export) | `curl -sf 'http://127.0.0.1:8000/api/v9/woodies/chart?limit=1'` | `age_s=2.8 stale=false` · bar `2026-07-20 09:55:00` trend=BLUE | 🟢 |

**הערת A12 (cowork ruling 07-20):** `v9_bars_5min` **מגודר-RTH בלבד** (`bars.py:50` `_is_within_rth` — bars מחוץ ל-09:30–17:00 ET לא נכנסים). Friday 22:55 = **תקין טרום-פתיחה**. woodies/chart טרי (07-20). **S2 יורה מ-buffer-חי**, לא מ-chart-DB. **09:35 ET:** re-run — bar ≥ 09:30 → סמן 🟢.

---

## B · מערכות S1 / S2 / S4 / S6 / Gateway

| # | מערכת | בדיקה | פקודה | פלט (RAW) | 🟢/🔴 |
|---|--------|--------|--------|-----------|-------|
| B1 | **S1** classify_replay (אתמול) | `curl -sf '.../day_type/classify_replay?date=2026-07-17'` | `n_bars=78` · `final.day_type=Normal_Variation` · `status=CLASSIFIED` | 🟢 |
| B2 | **S1** pre-RTH היום | `curl -sf '.../classify_replay?date=2026-07-20'` | `n_bars=0` · `note=no RTH bars` | 🟡 pre-RTH |
| B3 | **S1** get_live_day_type | `curl -sf '.../day_type/live'` | `{"day_type":null,"source":"get_live_day_type"}` | 🟡 FORMING — צפוי pre-IB |
| B4 | **S1** machine state | `curl -sf '.../day_type/state'` | `stage=A2` · `day_type=UNKNOWN` · `lock_state=PENDING` | 🟡 pre-RTH |
| B5 | **S1** build-status | `curl -sf '.../build/pattern-status?systems=day_type'` | `running=true hydrated=true` · `day_type=UNKNOWN` · `behavior=DEVELOPING` | 🟢 |
| B6 | **S2** hydrated + mode | `curl -sf '.../build/pattern-status?systems=five_min'` | `running=true hydrated=true mode=WEEKEND` · `buffer_size=159` · `nt_day_type gate=Normal` | 🟢 |
| B7 | **S2** FHB / VSA לא חוסם-הכל | same · gates | `global_gates nt_day_type present=True value=Normal` · patterns all `blocked` (pre-RTH WEEKEND — לא 07-09 zero-fire signature) | 🟡 |
| B8 | **S2** nt_skip | `curl -sf '.../five_min/nt_skip_stats'` | `nt_skip_count=0` · `current_day_type=UNKNOWN` | 🟢 |
| B9 | **S4** woodies hydrated | `curl -sf '.../woodies/current'` | `running=true hydrated=true buffer_size=50` · `trend_state=GRAY` · `classification=NO_SETUP` | 🟢 |
| B10 | **S4** paint = export current_bar | export `current_bar.trend_state` vs API | export `GRAY cci=-26.57` · API `GRAY cci=42.95` — **אותו paint GRAY** (chart history BLUE = ברים סגורים, לא current_bar) | 🟢 |
| B11 | **S4** build-status bars | `curl -sf '.../build/pattern-status?systems=woodies'` | `last_bar_ts=2026-07-20 13:15:00+03:00 lag=224s fresh=true` | 🟢 |
| B12 | **S6** supervisor | `curl -sf '.../system6/diagnose'` | `{"active":false}` — אין עסקה פתוחה | 🟢 |
| B13 | **S6** flags | `python3 scripts/flag_guard.py` (subset) | `SYSTEM6_SUPERVISOR=1` · `SYSTEM6_AUTOCORRECT=protective` · `STALL_EXIT=unset` · `OPPOSITE_EXIT=unset` | 🟢 |
| B14 | **Gateway** slot + enabled | `curl -sf '.../gateway/status'` | `live_slot=null` · `live_enabled_systems=[2,4]` · `chop_state=EXPANDING` | 🟢 |
| B15 | **Gateway** decisions | `curl -sf '.../gateway/decisions?limit=5'` | `fired=0 blocked=0` · `note=in-memory since backend start` | 🟡 buffer ריק — צפוי pre-RTH |
| B16 | **flag_guard** | `python3 scripts/flag_guard.py` | `FLAG-GUARD: PASS — all 91 ruled flags match.` | 🟢 |
| B17 | **fire_drill** A–C | `python3 scripts/fire_drill.py --no-live` | `🟢 GO — כל שרשרת ההחלטה כשרה לירי.` exit=0 | 🟢 |

---

## C · שערים שחסמו בעבר (שישי)

| # | בדיקה | פקודה | פלט | 🟢/🔴 |
|---|--------|--------|-----|-------|
| C1 | סף כניסות 15:30 ET | `flag_guard` | `RISK_CUTOFF_HOUR_ET=15` · `RISK_CUTOFF_MINUTE_ET=30` | 🟢 |
| C2 | entry_not_confirm פעיל (לא OFF) | `flag_guard` | `S4_ENTRY_CONFIRM_V1=1` · tol `ENTRY_CONFIRM_TOL_MIN_PTS=0.5` | 🟢 |
| C3 | cont_trend ON (לא bypass-accidental) | `flag_guard` | `CONT_TREND_FILTER=1` · `DIRECTION_LSMA_VETO` via direction_now `mode=lsma_cvd_veto` | 🟢 |
| C4 | location gate OFF (פסיקה) | `flag_guard` | `DAYTYPE_POSITION_GATE=0` | 🟢 |
| C5 | S2 ⟂ S3 (COT לא נדרש) | `flag_guard` | `S2_REQUIRE_COT_AMT=unset` | 🟢 |
| C6 | chop gate OFF (פסיקה) | `flag_guard` | `LAYER0_CHOP_GATE=unset` | 🟢 |
| C7 | live_price לא מעופש | `curl live_price` | `7517.88` bid/ask spread 0.25 — לא 996150 | 🟢 |
| C8 | direction pre-RTH כנה | `curl -sf '.../day_type/direction_now'` | `dir=NEUTRAL reason=no RTH bars yet (pre-open / forming)` | 🟢 |

---

## D · תצוגה + פלאפון

| # | בדיקה | פקודה | פלט | 🟢/🔴 |
|---|--------|--------|-----|-------|
| D1 | Frontend local | `curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/` | `200` | 🟢 |
| D2 | /board /build | `curl -sf -o /dev/null -w 'board=%{http_code}\n' ...` | `board=200` · `build=200` | 🟢 |
| D3 | day_type/live (override-aware) | `curl -sf '.../day_type/live'` | `source=get_live_day_type` · `day_type=null` (pre-RTH) | 🟢 |
| D4 | classify_replay UI source (07-17) | `curl classify_replay?date=2026-07-17` | `Normal_Variation CLASSIFIED` — מקור replay עובד | 🟢 |
| D5 | Mobile ZT backend | `curl -sf -o /dev/null -w '%{http_code}' http://10.1.118.147:8000/health` | `200` | 🟢 |
| D6 | Mobile ZT frontend (דשבורד מלא) | `curl -sf -o /dev/null -w '%{http_code}' http://10.1.118.147:3000/` | `000` — localhost bind | 🟡 **לא מחסום-ירי** |
| D7 | Mobile app :8000 | `curl -sf -o /dev/null -w '%{http_code}' http://10.1.118.147:8000/health` | `200` | 🟢 |
| D8 | אופציה: דשבורד מלא בכיס | `frontend/v9/package.json` `"dev": "next dev -H 127.0.0.1"` | bind ZT = `0.0.0.0:3000` — **פסיקת-מייקל**; אחרת מינורי | 🟡 |

---

## E · בטיחות

| # | בדיקה | פקודה | פלט | 🟢/🔴 |
|---|--------|--------|-----|-------|
| E1 | is_sim=1 (סריקה) | `cat sierra_state.json` | `"is_sim":1` | 🟢 (מכוון) · ⛔ flip לפני LIVE |
| E2 | חשבון שטוח | `curl -sf '.../agent/sierra_live_check'` | `verdict=🟢` · `sierra_qty=0` · `tm_net=0` · `is_sim=1 armed=1` | 🟢 |
| E3 | RISK_HALT | flag_guard | `RISK_HALT_V1=1` · `RISK_DAILY_LOSS_CAP=400` | 🟢 |
| E4 | EOD_FLATTEN | flag_guard | `EOD_FLATTEN_V1=1` · `EOD_RISK_WINDOW_V1=1` | 🟢 |
| E5 | FEED_WATCHDOG | flag_guard | `FEED_WATCHDOG=1` | 🟢 |
| E6 | LIVE_EXECUTION | flag_guard | `LIVE_EXECUTION_V1=1` · `LIVE_TRADING_ARMED=1` (.env) | 🟢 |
| E7 | ORPHAN OFF | flag_guard / env | `ORPHAN_AUTO_STOP_V1` לא ב-RULED 91 — default OFF | 🟢 |
| E8 | op=EXIT paths OFF | flag_guard | `STALL_EXIT=unset` · `OPPOSITE_EXIT=unset` | 🟢 |
| E9 | PHANTOM_HEAL ON | flag_guard | `PHANTOM_HEAL_V1=1` | 🟢 |
| E10 | PATTERN_LOSS_BREAKER OFF | flag_guard | `PATTERN_LOSS_BREAKER=0` (07-18 ruling) | 🟢 |

---

## F · כלי-עזר מוכנים (לא חוסם pre-open)

| # | כלי | פקודה | פלט | סטטוס |
|---|-----|--------|-----|--------|
| F1 | ORPHAN harness | `python3 scripts/verify_orphan_place_stop_sim.py --phase auto` | INDETERMINATE (flat) exit=2 | 🟢 מוכן ל-cc |
| F2 | T17 4-contract harness | `python3 scripts/verify_t17_e2e_4contract_sim.py --auto` | INDETERMINATE until cc PLACE 4c | 🟢 מוכן ל-cc |
| F3 | T15 stage-E | `python3 scripts/fire_readiness_real.py --date 2026-07-17 --no-live` | INDETERMINATE exit=2 | 🟢 · OFF |
| F4 | morning_briefing | `python3 scripts/morning_briefing.py` | flag-guard PASS | 🟢 |

---

## 🔴 מחסומי-ירי

**אין (07-20 cowork verify).** שני סעיפים שהיו 🔴 הורדו:

| היה | ruling | סטטוס |
|-----|--------|--------|
| A12 chart-DB Friday | RTH-gated (`bars.py:50`); S2=buffer חי | 🟡 re-check 09:35 |
| D6 :3000 לא ZT | mobile :8000 עובד; דשבורד-מלא=אופציונלי | 🟡 מינורי |

---

## 🟡 WATCH — re-check / אופציונלי

1. **A12 chart/bars5min** — Friday OK pre-RTH; **09:35 ET** bar ≥ 09:30 → 🟢.
2. **S1 UNKNOWN/PENDING** — pre-RTH; IB lock אחרי 10:30 ET.
2. **Gateway decisions buffer=0** — in-memory מאז restart; צפוי fills אחרי 09:30.
3. **S2 mode=WEEKEND** — יעבור FIRST_HOUR בפתיחה; re-check build-status 09:35.
4. **is_sim=1** — מכוון לסריקה; **⛔ לפני 16:30 IL → LIVE + is_sim=0**.
5. **mems26_verify warns** — FLAG_INDEX drift · sc_study uncommitted (deployed==repo OK).
6. **footprint stream no_data** — `FOOTPRINT_DISABLED=true` ב-LaunchAgent — מכוון.
7. **status.bridge.running=false** — pgrep מראה bridge חי + pushes; metric stale (V9_DISABLE_WATCHDOG=1).
8. **T15 stage-E INDETERMINATE** — LSMA history חסר ב-replay; לא GO-כוזב (נכון).
9. **morning_briefing PG trust** — script shell לא מתחבר ל-PG; backend (LaunchAgent) כן — לא runtime blocker.

---

## פקודות-חזרה מהירות (cowork · 09:35 ET)

```bash
# A12 re-check 09:35 ET
curl -sf 'http://127.0.0.1:8000/api/v9/chart/bars5min?limit=1' | python3 -m json.tool

# LIVE flip
cat ~/SierraChart_Data/v9_export/sierra_state.json | python3 -c "import sys,json; d=json.load(sys.stdin); print('is_sim=',d.get('is_sim'),'qty=',d.get('position_qty'))"

# cc sim harnesses (after placement)
python3 scripts/verify_orphan_place_stop_sim.py --phase hold --baseline-qty 2
python3 scripts/verify_t17_e2e_4contract_sim.py --trade-id <id>
```

---

*נוצר: cursor-agent · 2026-07-20 13:19 IDT · commit+push עם LIVE_CHANNEL LOG*
