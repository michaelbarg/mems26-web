# MEMS26 V3 — מסמך התקדמות

תאריך: 10 אפריל 2026

---

## מה בוצע — סיכום לפי משימות

---

### שלב א — בסיס (A1-A6)

#### A1 — Bridge: נרות 5m ✅
**קובץ:** `bridge/json_bridge.py`
**מה נעשה:**
- נוסף `CandleBuilder` ל-5m ב-`MTF_CONFIG`: `("m5", "mems26:candles:5m", 300, 288)`
- Bridge בונה נרות 5m מנתוני 3m ושומר ב-Redis
- Seeding מהיסטוריה (288 נרות) בעליית Bridge
- Dedup: אם נר עם אותו `ts` כבר קיים — מעדכן במקום (לא מוסיף כפול)
- Volume accumulation: `buy += ...`, `sell += ...`, `vol += ...`

**Redis key:** `mems26:candles:5m` (עד 288 נרות = יום שלם)

---

#### A2 — Bridge: נרות 15m ✅
**קובץ:** `bridge/json_bridge.py`
**מה נעשה:**
- `("m15", "mems26:candles:15m", 900, 96)` ב-MTF_CONFIG
- Seeding: 96 נרות מהיסטוריה

**Redis key:** `mems26:candles:15m`

---

#### A3 — Bridge: נרות 1H ✅
**קובץ:** `bridge/json_bridge.py`
**מה נעשה:**
- `("m60", "mems26:candles:1h", 3600, 64)` ב-MTF_CONFIG
- Frontend: שונה limit מ-64 ל-168 (שבוע שלם)

**Redis key:** `mems26:candles:1h`

---

#### A4 — Pattern Scanner: MSS Detection ✅
**קובץ:** `bridge/pattern_scanner.py`
**מה נעשה:**
- פונקציה `detect_mss(candles)` — standalone detector
  - LOOKBACK=5 נרות, סורק מהסוף אחורה
  - שבירת swing low (SHORT) או swing high (LONG)
  - דורש rel_vol > 1.2
  - מחזיר `PatternResult` עם confidence 60-95
- גם כחלק מהשרשרת V3: `_find_mss_after_sweep()` — מחפש MSS תוך 5 נרות אחרי Sweep

---

#### A5 — Pattern Scanner: FVG Detection ✅
**קובץ:** `bridge/pattern_scanner.py`
**מה נעשה:**
- פונקציה `detect_fvg(candles)` — standalone detector
  - Gap בין high של N-2 ל-low של N
  - גודל: 0.5pt-4.0pt
  - Bearish FVG + Bullish FVG
  - מחזיר `PatternResult` עם confidence 75
- גם כחלק מהשרשרת V3: `_find_fvg_after_mss()` — מחפש FVG תוך 10 נרות אחרי MSS

---

#### A6 — Pattern Scanner: Killzones ✅
**קובץ:** `bridge/pattern_scanner.py`
**מה נעשה:**
- קבוע `KILLZONES`:
  - London: 07:00-10:00 UTC
  - NY Open: 13:30-15:00 UTC
  - NY Close: 18:30-21:00 UTC
- פונקציה `is_in_killzone(ts)` — מחזירה:
  - `in_killzone` (bool)
  - `zone` (שם)
  - `minutes_left` (דקות נותרו)
  - `minutes_to_next` + `next_zone` (אם מחוץ)
- מיוצא גם ל-bridge: `from pattern_scanner import scan_patterns, is_in_killzone`

---

### שרשרת V3: Sweep → MSS → FVG ✅
**קובץ:** `bridge/pattern_scanner.py`
**מה נעשה:**
- פונקציה מרכזית: `detect_liquidity_sweep(candles_5m, levels, day_type)`
- **שלב 1 — Sweep:** סורק 5m candles, wick >= 1.5pt מעבר לרמת נזילות, סגירה חזרה
- **שלב 2 — MSS:** `_find_mss_after_sweep()` — שבירת swing (5 נרות לפני) תוך 5 נרות אחרי sweep, rel_vol > 1.2
- **שלב 3 — FVG:** `_find_fvg_after_mss()` — gap 0.5-4pt תוך 10 נרות אחרי MSS, כניסה באמצע
- **פילטרים:** Killzone + DayType (חוסם NON_TREND/ROTATIONAL/NEUTRAL) + risk <= 8pt
- **Levels נבדקים:** PDH, PDL, ONH, ONL, DO, IBH, IBL, VWAP, POC, VAH, VAL
- **Confidence:** 50 בסיס + wick quality + MSS vol + FVG size + Killzone bonus + Delta
- מוחזר כ-`LIQ_SWEEP` pattern בעדיפות ראשונה

**Bridge integration:**
- `json_bridge.py` מביא 5m candles מ-Redis + levels מ-payload
- מעביר ל-`scan_patterns(all_candles, candles_5m=..., levels=..., day_type=...)`

---

### שיפורים נוספים שבוצעו

| שינוי | קובץ | commit |
|-------|-------|--------|
| `calcBarAligned` — MTF מיושר לגבולות זמן אמיתיים | `sc_study/MES_AI_DataExport.cpp` | 7fc8d0f |
| MTF JSON כולל `ts` (bar_ts) | `sc_study/MES_AI_DataExport.cpp` | 7fc8d0f |
| Bridge: Sierra `ts` עדיף על wall_ts floor | `bridge/json_bridge.py` | 7fc8d0f |
| Bridge: קריאה כל 0.2s, שליחה כל 0.5s | `bridge/json_bridge.py` | 01fd33a |
| Bridge: dedup — עדכון נר קיים עם אותו ts | `bridge/json_bridge.py` | 3bba4f5 |
| Bridge: vol accumulate (+=) במקום overwrite | `bridge/json_bridge.py` | 3bba4f5 |
| Frontend: `key={tf}` ב-LightweightChart (remount on TF switch) | `Dashboard.tsx` | 3bba4f5 |
| Frontend: fetchLive 1s (היה 2s) | `Dashboard.tsx` | 598a6df |
| Frontend: keepalive ping כל 30s ל-/health | `Dashboard.tsx` | 598a6df |
| Frontend: 1h limit 168 (היה 64) | `Dashboard.tsx` | 598a6df |
| Frontend: filter phantom candles (ts < 2020) | `LightweightChart.tsx` | c401ffc |
| Frontend: הסרת כל console.log | Dashboard + LightweightChart | 3bba4f5 |

---

## מה נשאר — לפי שלבים

---

### שלב א — בדיקות (צריך לוודא שעובד)

| בדיקה | סטטוס | הערות |
|-------|--------|-------|
| SC Study מקמפל בהצלחה עם `calcBarAligned` | ❓ | DLL ב-18:20, הקובץ הפסיק להתעדכן ב-18:49. צריך לבדוק build log ב-Sierra Chart |
| `mes_ai_data.json` מכיל `ts` ב-MTF bars | ❓ | תלוי בהצלחת הקומפילציה |
| נרות 5m ב-Redis — כמות + עדכניות | ❓ | Bridge צריך לרוץ עם SC פעיל |
| נרות 15m ב-Redis | ❓ | כנ"ל |
| נרות 1h ב-Redis | ❓ | כנ"ל |
| `scan_patterns` רץ עם 5m + levels ולא קורס | ❓ | צריך bridge חי |
| `detect_liquidity_sweep` מזהה sweep על רמה אמיתית | ❓ | צריך שוק בשעות Killzone |
| `is_in_killzone` מחזיר תוצאה נכונה | ✅ | נבדק: `in_killzone=False, next=NY_Close, 104 min` |
| Frontend מציג 5m/15m/1h charts | ❓ | צריך בדיקה ידנית באתר |
| Patterns tab מציג `LIQ_SWEEP` | ❓ | צריך sweep בזמן killzone |

---

### שלב ב — ניתוח ו-AI (שבוע 2)

#### B1 — Backend: Pre-Analysis Rule-Based (Macro Bias) ❌
**קובץ:** `backend/main.py`
**מה לעשות:**
- endpoint חדש: `GET /market/bias`
- קרא נרות 15m ו-1H מ-Redis
- חשב EMA20 ו-EMA50
- זהה Higher High / Lower Low למגמה
- מצא Draw on Liquidity (הרמה הבאה)
- פלט: `{bias, draw_on_liquidity, ema_trend, key_levels, confidence}`

#### B2 — Backend: שדרוג פרומפט AI ❌
**קובץ:** `backend/main.py`
**מה לעשות:**
- הוסף Macro Bias מ-B1 לפרומפט
- הוסף MSS confirmation + FVG location
- הוסף Draw on Liquidity כ-T3
- הוסף Killzone status
- שנה כניסה מ"פריצת high" → "Limit ב-FVG"
- שנה max_tokens: 1500 → 2000

#### B3 — Backend: AI Markers ❌
**קובץ:** `backend/main.py`
**מה לעשות:**
- הוסף `markers[]` לתשובת AI
- כל marker: `{ts, pos, shape, color, text}`
- מקסימום 10, ניקוי בכל refresh

#### B4 — Backend: Trade Health Endpoint ❌
**קובץ:** `backend/main.py`
**מה לעשות:**
- endpoint חדש: `GET /trade/health`
- CVD delta מאז כניסה
- rel_vol נוכחי
- מיקום מחיר ביחס ל-FVG
- Health Score 0-100
- החלטות: >= 70 החזק, 50-69 צמצם, < 30 סגור הכל

---

### שלב ג — Semi-Auto Trading (שבוע 3)

#### C1 — Backend: Trade Execute Endpoint ❌
**קובץ:** `backend/main.py`
- `POST /trade/execute`
- בדיקת Circuit Breaker לפני ביצוע
- כתיבה ל-Redis: `mems26:trade:command`

#### C2 — Backend: Circuit Breaker ❌
**קובץ:** `backend/main.py`
- `GET /trade/daily-stats`
- Soft Limit $150, Hard Limit $200
- מקס 3 עסקאות/יום, 2 הפסדים ברצף = נעילה 30 דקות
- איפוס יומי

#### C3 — Backend: Trade Status Monitoring ❌
**קובץ:** `backend/main.py`
- `GET /trade/status`
- קריאת trade_status.json מ-ACSIL
- עדכון daily_pnl
- Trade Health Monitor כל 10 שניות

#### C4 — Bridge: כתיבת trade_command.json ❌
**קובץ:** `bridge/json_bridge.py`
- כתיבת JSON לנתיב Sierra Chart
- checksum (sha256) + expires_at
- קריאת trade_status.json בחזרה

#### C5 — ACSIL: קריאת פקודות וביצוע ❌
**קובץ:** `sc_study/MES_AI_DataExport.cpp`
- קריאת trade_command.json כל 3 שניות
- אימות checksum + expires_at
- Bracket Order דרך Iron Beam (3 MES)
- כתיבת trade_status.json

---

### שלב ד — Frontend (שבוע 3-4)

#### D1 — Dashboard: Pre-Entry Checklist Component ❌
**קובץ:** `frontend/src/components/Dashboard.tsx`
- 8 תנאים עם ✅/❌ בזמן אמת
- כפתור "⚡ בצע כניסה" רק אם כולם ירוקים
- הסבר מדויק לכל תנאי שנכשל

#### D2 — LightweightChart: FVG Zone ❌
**קובץ:** `frontend/src/components/LightweightChart.tsx`
- מלבן צהוב שקוף (opacity 0.2) בין fvg_low ל-fvg_high
- קו entry מקווקו באמצע
- נעלם כש-FVG נסגר

#### D3 — LightweightChart: MSS Marker ❌
**קובץ:** `frontend/src/components/LightweightChart.tsx`
- סטיקר ◆ כתום על נר MSS
- קו אופקי ב-mss_level

#### D4 — LightweightChart: AI Markers ❌
**קובץ:** `frontend/src/components/LightweightChart.tsx`
- קבלת markers[] מ-AI
- ציור עם candleSeries.setMarkers()
- מקסימום 10, ניקוי בכל refresh

#### D5 — Dashboard: Trade Panel ❌
**קובץ:** `frontend/src/components/Dashboard.tsx`
- סטטוס עסקה פעילה: כניסה + P&L + Health Score
- C1/C2/C3 סטטוס
- כפתור "סגור הכל"

#### D6 — Dashboard: Killzone Badge ❌
**קובץ:** `frontend/src/components/Dashboard.tsx`
- Badge ב-DayTypeBar
- ירוק: "NY Open — 23 דקות נותרו"
- אפור: "מחוץ ל-Killzone — עוד 47 דקות"

#### D7 — LightweightChart: Channel Detection Visual ❌
**קובץ:** `frontend/src/components/LightweightChart.tsx`
- 2 קווים מקבילים לכל תעלה
- ירוק = עולה, אדום = יורדת, כחול = אופקית

---

### שלב ה — Paper Testing (שבועות 4-8)

#### E1 — Trade Journal ❌
- תיעוד כל עסקה: תאריך, Killzone, DayType, Health Score, תוצאה, P&L

#### E2 — Statistics Dashboard ❌
- Win Rate כללי + לפי Killzone/DayType
- ממוצע R:R, Profit Factor

#### E3 — Review שבועי ❌
- עבור על עסקאות, זהה patterns של הפסדים, עדכן פרמטרים

---

### שלב ו — ML Pipeline (חודש 6+)

#### F1 — Data Collection ❌
- איסוף features לכל עסקה

#### F2 — Model Training ❌
- XGBoost classifier, 500+ עסקאות

---

## מצב תשתיות נוכחי

| רכיב | סטטוס | endpoint/key |
|-------|--------|-------------|
| 3m candles | ✅ פעיל | `mems26:candles` (960) |
| 5m candles | ✅ מוגדר | `mems26:candles:5m` (288) |
| 15m candles | ✅ מוגדר | `mems26:candles:15m` (96) |
| 30m candles | ✅ מוגדר | `mems26:candles:30m` (48) |
| 1h candles | ✅ מוגדר | `mems26:candles:1h` (64→168) |
| Latest snapshot | ✅ פעיל | `mems26:latest` |
| Patterns | ✅ מוגדר | `mems26:patterns` |
| `/market/latest` | ✅ קיים | backend |
| `/market/candles/*` | ✅ קיים | backend (3m/5m/15m/30m/1h) |
| `/market/analyze` | ✅ קיים | backend |
| `/market/patterns` | ✅ קיים | backend |
| `/market/bias` | ❌ חסר | צריך B1 |
| `/trade/execute` | ❌ חסר | צריך C1 |
| `/trade/health` | ❌ חסר | צריך B4 |
| `/trade/status` | ❌ חסר | צריך C3 |
| `/trade/daily-stats` | ❌ חסר | צריך C2 |

---

## Commits של הסשן הנוכחי (10.04.2026)

```
d4cc3e9 feat: V3 Liquidity Sweep chain (Sweep→MSS→FVG) on 5m + Killzone filter (A6)
7e60332 feat: A4+A5 MSS and FVG detection in pattern_scanner
01fd33a perf: bridge read 0.2s, send 0.5s interval
c401ffc fix: filter phantom candles with ts before 2020
598a6df fix: fetchLive 1s interval, keepalive ping, 1h limit 168
11a9e7f fix: bar_data not in scope on stale path, revert to wall_ts floor
7fc8d0f fix: calcBarAligned real time boundaries + Sierra ts in bridge
3bba4f5 fix: TF switch key={tf}, MTF dedup, accumulate vol, remove debug logs
```

---

## חסימה עיקרית כרגע

**SC Study לא מקמפל** — הקובץ `mes_ai_data.json` הפסיק להתעדכן ב-18:49.
צריך לפתוח Sierra Chart → Analysis → Build Custom Studies DLL ולבדוק שגיאות.
בלי SC פעיל, ה-bridge רץ עם "Stale" ואף MTF candle לא מתעדכן.
