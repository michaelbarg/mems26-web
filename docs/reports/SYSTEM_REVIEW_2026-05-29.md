# MEMS26 — סקירת מערכת כוללת

**תאריך:** 2026-05-29
**Branch:** `stabilize/mems26-local-truth-2026-05-16`
**מטרת הסקירה:** היכרות מקיפה עם המערכת לקראת מסחר חי (Pre-LIVE), עם איתור נושאים פתוחים וסיכונים.
**אופי:** קריאה בלבד (read-only). לא בוצעו שינויי קוד.

---

## 1. תמונה כללית — מה המערכת עושה

MEMS26 היא מערכת מסחר אוטונומית מקומית לחוזים עתידיים (MES). זרימת הנתונים:

```
Sierra Chart (C++ study)  →  קבצי JSON ב-~/SierraChart_Data/v9_export/
        ↓ (bridge — Python, מאזין לקבצים)
   POST ל-localhost:8000  +  Redis (Upstash)
        ↓
   Backend (FastAPI, single-worker uvicorn, SQLite: data/mems26_local.db)
        ↓  מערכות זיהוי setup → Gateway → executor
   Frontend (Next.js 16 / React 19) — דשבורד עם polling + WebSocket
```

**עקרון העל ("Source of Truth"):** ערכי שוק (OHLC, TPO, CVD, Woodies) מגיעים *רק* מ-Sierra. הקוד אסור לו להמציא ערכים — כשהמקור שותק, מעבירים `None`/"missing" עד ל-UI. עיקרון זה נשמר היטב ברוב הקוד.

**מצב ביצוע מסחר היום:** המערכת היא **SHADOW/paper בלבד**. אין שום נתיב שמגיע להזמנה אמיתית בברוקר — ה-executors הם stubs, וה-DLL מאשר קבלת פקודה אך לא קורא ל-`sc.SubmitOrder`. זו שכבת בטיחות חשובה כרגע, אך משמעותה גם שנתיב ה-LIVE לא נבדק מקצה לקצה.

---

## 2. ארכיטקטורה — הרכיבים

### Backend (`backend/v9/`)
- **Entrypoint** `backend/main.py` — אפליקציית FastAPI אחת; ב-`startup` מחווט ידנית את כל המערכות, ה-`BarRouter`, ה-`TradingGateway`, ה-schedulers ומכונת המצבים של day_type.
- **Routing** `backend/v9/app.py` מאחד ~35 routers (bars, tpo, woodies, day_type, footprint, killzone, key_levels, cumulative_delta, gateway, shadow, pre_fire, trades…).
- **DB** SQLite ב-`data/mems26_local.db` (WAL). יש מודלים ב-SQLAlchemy אך גם כתיבות sqlite3 גולמיות.
- **זרימת אירועים** bridge → ingestion/aggregator → `BarRouter` (pub/sub) → מערכות נרשמות לפי סוג bar → `event_dispatcher` מעביר signal ל-`TradingGateway.route_setup()`.

### Systems (`backend/v9/systems/`)
- **נוגעות במסחר/סיכון:** `five_min` (S2), `footprint` (S3), `woodies` (S4) — מייצרות setups. `layer0` — `chop_score` שמשמש כ-**gate קשיח** (חוסם DEMO/LIVE כשהמצב "SEARCHING").
- **הקשר (context):** `day_type` (סיווג סוג היום ממכונת מצבים), `tpo` (Market Profile / value area), `tick_reversal`, `reversal`, `killzone`, `behavior_phase`.

### Bridge (`bridge/`)
- `json_bridge.py` נקודת כניסה; thread לכל stream (12 streams ב-`v9_streams/__init__.py`). `base_stream.py` מאזין לקובץ, dedup לפי mtime/export_ts, תיקון TZ, push ל-Redis + API.
- `vap_recompute.py` קורא קובץ SCID גולמי כדי לחשב footprint bid/ask אמיתי (במקום הפיזור המנוון של ה-DLL).

### sc_study (`sc_study/`)
- `MES_AI_DataExport.cpp` הוא ה-study הפעיל (split-headers). `MES_AI_DataExport_merged.cpp` הוא עותק monolith ישן/ארכיוני (mtime מ-05-25).
- Headers: `v9_types.h`, `v9_exports.h`, `v9_woodies_export.h`. ערכי Woodies מגיעים מ-Sierra Study subgraphs אמיתיים; `proj_hi/proj_lo` מ-Study ID:9 (לא מומצאים).

### Frontend (`frontend/v9/`)
- Next.js 16.2 + React 19 + TS. `page.tsx` → `V9Dashboard` → `ChartV5b` ופאנלים (TopBar, Layer0Strip, KeyLevelsStrip, TradeHistoryStrip, WoodiesCciPanel…).
- תקשורת: REST (`localhost:8000`) + WebSocket (`ws://localhost:8000`, ערוצים `/ws/v9/signals/{1..6}` וכו'). ה-defaults מצביעים נכון ל-localhost.

---

## 3. עמידה בכללי הבטיחות (Guardrails) — מה תקין

| כלל | מצב | הערה |
|-----|-----|------|
| Bridge local-only | ✅ תקין | `base_stream.py:39-44` — ברירת מחדל localhost, `raise RuntimeError` אם CLOUD_URL לא מקומי. |
| Source-of-truth (אין סינתזה) | ✅ נשמר ברובו | `tpo_routes`, `key_levels_routes` מחזירים `None` במפורש לפי Rule 1. |
| day_type consumer write-gate | ✅ קיים | `systems/day_type/consumer.py:40-74` — מסרב UPSERT של `UNKNOWN`+`PENDING`. |
| None-propagation ל-UI | ✅ ברובו | Frontend משתמש ב-`?? null` ו-`EmptyState`, ללא `Math.random` ברכיבים החיים. |
| LIVE execution חסום | ✅ stub | אין `sc.SubmitOrder`; `enable_live` לא נקרא ב-main.py (רק `enable_demo`). |

> **הערה ב-.env:** המשתנה `CLOUD_URL` מכיל TODO "Revert to onrender before production". כל עוד הערך מקומי המגן עובד — אבל יש לוודא שזה לא מוחזר ל-remote בטעות (מנוגד לכלל ה-bridge).

---

## 4. נושאים פתוחים וסיכונים — מסודר לפי חומרה

### 🔴 חוסמי LIVE (מתוך `docs/handoff/OPEN_ITEMS_PRE_LIVE_2026-05-28.md`)

1. **DLL frozen-tail bug** — `GetContainingIndexForDateTimeIndex` תופס/מקפיא את ~13 ה-bars האחרונים של Woodies (CCI/SWI/TCCI קפואים). זהו ה-root cause המרכזי; דורש תיקון DLL + rebuild או reconfig של ה-chart.
2. **שני Gateways מקבילים — הלא-בטוח הוא המחובר.** המאומת: `main.py:365` מייבא `from backend.v9.gateway import TradingGateway`. ה-gateway הזה משתמש ב-`risk_checks.passes_strict_checks` — שאין בו בדיקת חלון חדשות (placeholder מוערה) ואין אכיפת position-size. הנתיב המלא יותר עם `RiskValidator` (W14, כולל news + position size + manual override) יושב ב-`services/trading_gateway/` ו**אינו מחווט**. זו דיברגנציה משמעותית לפני LIVE.
3. **`pre_fire_validator` לא נקרא בנתיב הירי בפועל** — קיים רק כ-route עצמאי (`pre_fire_routes.py`), למרות docstrings שטוענים שהוא רץ ב-`route_setup`.

### 🟠 באגים בעדיפות גבוהה

4. **TZ פצצת-זמן ב-bridge** — `base_stream.py:74` משתמש ב-`America/New_York` לתיקון TZ, ואילו `v9_history.py:43` משתמש ב-`America/Chicago` לאותו תיקון מתועד. ticks חיים מול backfill היסטורי יומרו ל-UTC שונה. (זהו ה-root של P32 Task I — ~540K שורות tick_reversal עם ts עתידי.)
5. **`woodies_chart_routes.py:43`** — hardcoded `+5*3600` שאינו מודע ל-DST (יישבר בשעון חורף).
6. **`key_levels_routes._day_type_row()`** משתמש ב-SQLite `date('now')` (UTC) — שובר את pill סוג-היום ~4 שעות כל ערב. חייב להיתקן אטומית עם P31 Task C.
7. **S2 `current_day_type=None`** גורם ל-skip שקט בעת restart באמצע סשן.
8. **Status enum sync** — `/api/v9/status.day_type` מדווח PENDING/UNKNOWN בעוד שורת ה-DB כבר מסווגת.
9. **11 כשלי pytest קיימים** מעבודת day_type/IB — חוסמים את שער ה-"all green".

### 🟡 חוב/דיברגנציות שאיתרתי בסקירה זו

10. **W-10 Time-Stop בנוי אך מושבת** (`dispatcher_config.yaml::time_stop_minutes=null`, החלטת Michael 2026-05-28). הסיבה: `_bar_count` עלה לפי push כל ~3s ולא לפי bar 5-דקות סגור, כך ש-TIME_STOP ירה אחרי ~52 שניות. ה-authority עכשיו הוא Constitution V3 Layer 4. תקין כהחלטה — שווה לוודא שזה מתועד כמכוון.
11. **WoodiesCciPanel polling = 15000ms** (`WoodiesCciPanel.tsx:1107`) — בעוד ש-CLAUDE.md מנדט **5000ms**. הכיוון בטוח (פחות עומס), אך סותר את ה-floor המתועד. או לתקן את הקוד ל-5000 או לעדכן את הטבלה ב-CLAUDE.md.
12. **SoundProvider מנוטרל** (`return null`, "Sound removed per Michael 2026-05-22"). אין יותר "fire ding". CLAUDE.md עדיין מתעד 10000ms ו-"ding תוך <10s". כרגע fire מופיע ויזואלית בלבד — לאשר שזה מכוון בהקשר מסחר חי.
13. **קוד מת שמסנתז OHLC** — `bridge/candle_builder.py` בונה candles מ-ticks (min/max/close), ו-`frontend .../ChartArea.tsx` נופל ל-`generateMockBars` כשה-API ריק. שניהם **לא בנתיב החי** (אין importers / לא נרנדר), אך נשארים ככשל פוטנציאלי אם יופעלו — מנוגדים לכלל ה-source-of-truth.
14. **`except Exception` רחב ב-startup** של `main.py` יכול לבלוע כשל רישום מערכת בשקט (האפליקציה תעלה גם אם מערכת לא נרשמה).
15. **נתיבי DB אבסולוטיים hardcoded** (`/Users/michael/Downloads/...`) ב-main.py וב-gateway עוקפים את `DATABASE_URL` — שכבת SQLAlchemy וכתיבות sqlite3 גולמיות עלולות להתפצל.

### עבודה בתהליך (uncommitted, 2026-05-29)
- **P31 — Daily Reset / Archive** (8 משימות A–H): write-gate, `SessionBoundaryManager` ל-18:00 ET, החלפת 13× `date.today()` ב-`et_today()`, חיווט `RiskValidator.daily_reset()`, Migration 019 (טבלאות ארכיון, `is_synthetic`). **כרגע מומש בפועל רק** `backend/v9/common/trading_date.py` + הטסט שלו (Task C). השאר staged אך לא ממומש.
- **P32 — Bridge TZ + sot_health cleanup** (I–L): תיקון ה-`+5h` future-ts, repoint של sot_health מ-`v9_tpo_sessions`→`v9_tpo_history`, הוספת S3 ל-map, ניקוי טבלאות יתומות.
- **מסקנת ה-consult:** commit `570f10d` תיקן רק חלקית את באג התאריך (השאיר חלון לילה פתוח אחרי חצות ET). הוחלט לשמור סמנטיקת `et_calendar_date`.

### Registry
`MEMS26_REGISTRY.yaml`: 135 דרישות — **73 IMPLEMENTED, 57 SPECIFIED (לא נבנו), 2 IN_PROGRESS, 2 VERIFIED**. 52 CRITICAL, 50 HIGH. בולטים: 8 שורות "SHADOW BLOCKER" (S2/S3 schemas ריקים), ו-Pipeline 5 (Sierra Order Routing, P5-1..P5-8) מסומן כחוסם LIVE.

---

## 5. כיסוי בדיקות

- `backend/v9/tests/`: 38 קבצים, ~454 פונקציות בדיקה — חזק מאוד ב-day_type, woodies (שלבים A1–A7), tpo, footprint, killzone, state_machine, consumer.
- **פער מהותי:** הכיסוי החזק הוא על המערכות והסיווג, אבל **ה-gateway המחובר בפועל** (`gateway/trading_gateway.py` + `risk_checks`) אינו מכוסה end-to-end; דווקא ל-`RiskValidator` ה-dormant יש בדיקות סיכון מפורשות. כלומר הבדיקות מכסות נתיב סיכון שאינו בשימוש.

---

## 6. המלצות מתועדפות

1. **להכריע על ה-Gateway הכפול** (סיכון #2) — או לחווט את `RiskValidator` (news + position-size) לנתיב הירי, או למזג את בדיקותיו ל-`risk_checks`. אסור להגיע ל-LIVE עם נתיב סיכון לא-מכוסה ופחות-בטוח.
2. **לוודא ש-`pre_fire_validator` באמת נקרא ב-`route_setup`** (סיכון #3) — או להסיר את ה-docstrings המטעים.
3. **לתקן את שלוש פצצות ה-TZ אטומית** (#4, #5, #6) — מקור אחד אמיתי ל"היום" (`et_today()`) ו-DST-aware, לפני כל מעבר LIVE.
4. **לסגור את 11 כשלי ה-pytest** (#9) ולהוסיף בדיקת end-to-end ל-gateway המחובר.
5. **ליישר את CLAUDE.md מול הקוד** — לעדכן את ערך ה-Woodies polling (#11) ואת מצב ה-SoundProvider (#12), כדי שהמסמך לא ישקר על מצב המערכת.
6. **לטפל בקוד המת שמסנתז OHLC** (#13) — למחוק `candle_builder.py` ואת fallback ה-mock ב-`ChartArea.tsx`, כדי שכלל ה-source-of-truth לא ייפרץ בטעות עתידית.
7. **להמשיך P31/P32 לפי הסדר שתועד** ולוודא restart של ה-backend לבאגים שסומנו "RESOLVED — awaiting restart".

---

**שורה תחתונה:** הליבה (source-of-truth של Sierra IB/key-levels) הושלמה והמערכת שמורה היטב כ-SHADOW. חוסמי ה-LIVE המרכזיים: באג frozen-tail ב-DLL, ה-Gateway הכפול עם נתיב הסיכון הלא-מחובר, שלוש פצצות TZ/DST, כשלי בדיקות פתוחים, ו-executors שעדיין stubs. העבודה הפעילה (P31/P32) מטפלת בחלק מהתאריך/reset אך עדיין staged ולא ממומשת ברובה.
