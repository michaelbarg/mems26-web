# CC Desktop Worklist — תיקונים למסחר 2026-06-03
**מאת:** CC CLI Session 2026-06-02 → **אל:** Claude Desktop (מנהל תיקונים)
**חוזה:** `docs/handoff/CC_HANDOFF_CONTRACT.md`

---

## מצב נוכחי (סוף יום 2/6)

**מה עובד:** S4 ירה 24 trades היום. S1 live reclass (Normal→Variation) עובד. S2 armed עם VSA gate.
COT/AMT מגיע מ-Sierra. Build Status readiness=READY during RTH. DB safe_writer מסרל כתיבות.

**מה לא עובד:** DB corruption חוזר (tick_reversal). S2 = 0 fires (gates חוסמים). Chart לא מציג
נרות נכון + CVD לא מיושר. CCI ערך שטותי אחרי crash.

---

## שינויים שבוצעו ב-Woodies (S4) — חשוב לדעת

### 1. `S4_EXTREME_TREND_RELABEL=true` (דגל ON ב-plist)
**מה זה עושה:** כש-CCI >= ±200 ו-trend הוא GRAY/YELLOW, ה-trend **מוחלף** ל-BLUE (CCI>0) או RED (CCI<0).
**למה:** Sierra מדווח GRAY/YELLOW בדיליי מעבר — אבל CCI ±200 = trend מבוסס. בלי זה, A1 gate חוסם 9 patterns.
**קובץ:** `backend/v9/systems/woodies/trend_relabel.py` → נקרא ב-`woodies_system.py:279`.
**שדה A/B:** `trend_original` נשמר ב-`studies` → `current_state` → `cross_context` → `v9_trades` JSON.

### 2. Dispatcher single-source fix
**מה תוקן:** dispatcher (YELLOW pre-drop + pattern selection) קרא `current_state["trend_state"]` (בר **קודם**).
עכשיו קורא מ-`studies["trend_state"]` (בר **נוכחי**, אחרי relabel). **commit `401d526`**.

### 3. `trend_original` field
שדה חדש ב-`studies` → `current_state` → `cross_context` שמתעד את ה-trend המקורי לפני relabel.
**commit `1e077fa`**.

**⚠️ אלה לא "הקלות" — אלה תיקוני עקביות.** ה-relabel מתקן את הדיליי של Sierra. ה-dispatcher fix
מתקן single-source violation. שניהם flag-gated ו-revertable.

---

## A · חוסמים קריטיים — חייב לפני מחר בוקר

### A1. DB tick_reversal corruption (חוזר!)
**בעיה:** `v9_bars_tick_reversal` משחיתה את ה-DB כל כמה שעות. tick_reversal כותב כל שנייה
דרך ORM (SQLAlchemy) — WAL+busy_timeout לא מספיק בקצב הזה.
**תיקון:** הוסף `TICK_REVERSAL_DISABLED=true` flag (כמו FOOTPRINT_DISABLED):
- `footprint_system.py` pattern — early return ב-`process_bar` אם flag ON
- S1/S2/S4 **לא תלויים** ב-tick_reversal (אומת)
- שמור את הקוד, רק עצור כתיבה
**אחרי:** rebuild DB clean (DROP corrupt table + VACUUM), verify integrity_check=ok.
**קבצים:** `backend/v9/shared/atr.py` (flag), API route שכותב tick_reversal (`backend/v9/api/v9/bars.py` ~line 355-384).
**plist:** הוסף `export TICK_REVERSAL_DISABLED=true`.

### A2. CCI=32628 שטותי (SIGBUS crash aftermath)
**בעיה:** SIGBUS crash ב-18:32 השחית את CCI buffer → trend חזר ל-GRAY → S4 patterns blocked.
**תיקון:** restart נקי של backend (יתוקן אוטומטית ע"י hydration מ-DB). ייעשה כחלק מ-A1 reload.

### A3. `S4_EXTREME_TREND_RELABEL` import-time caching
**בעיה:** `trend_relabel.py:12` עושה `from backend.v9.shared.atr import S4_EXTREME_TREND_RELABEL` —
module-level import. **אותו באג** כמו S2_VSA_VOLUME/S1_DYNAMIC_RECLASS שתוקנו.
**תיקון:** שנה ל-`os.environ.get("S4_EXTREME_TREND_RELABEL", ...)` at call-time.
**קובץ:** `backend/v9/systems/woodies/trend_relabel.py:12,20`.

---

## B · תיקוני S2 — שהמערכת תירה מחר

### B1. lookback_quiet gate — חוסם 98.4%
**בעיה:** `LOOKBACK_MAX_VOL_RATIO=0.6` דורש ש-b1 יהיה spike (פי 1.67+ מ-lookback).
בקטסט 29 ימים: בלי lookback = 34 trades, 67% WR, +$220. עם lookback = 1 trade.
**תיקון:** כש-`S2_VSA_VOLUME=true`, **דלג** על lookback_quiet (VSA כבר מוודא volume drop).
**קובץ:** `backend/v9/systems/five_min/five_min_system.py` ~line 520-523. הוסף:
```python
if S2_VSA_VOLUME:
    lookback_quiet = True  # VSA gate sufficient
```
**טסט:** golden: flag OFF → lookback עדיין פעיל. flag ON → bypassed.

### B2. b4_confirm gate — `close > b3.high` קשה מדי (אופציונלי)
**בעיה:** 2 near-misses היום (14:10, 14:35) — כל הגייטים עברו חוץ מ-b4.
b4 close היה מעל b3 close אבל **לא** מעל b3 high.
**אופציות:** (א) שנה ל-`b4.close > b3.close` (קל יותר). (ב) השאר כמו שזה (conservative).
**בקטסט:** לבדוק WR עם כל אופציה לפני שינוי. **strategic-stop — אישור Michael**.

### B3. Initiative expansion multiplier
**בעיה:** `_EXPANSION_MIN_ATR_K=1.5` = 5.2pts בATR=3.5. היום 0 trades גם ב-1.3×.
**בקטסט 29 ימים:** 1.5× = 2 trades (100% WR). 1.2× = 12 trades (58% WR, +$114).
**תיקון:** שנה ל-1.2× או 1.3×. **strategic-stop — אישור Michael**.
**קובץ:** `backend/v9/systems/five_min/five_min_system.py:44`.

### B4. Volume artifacts (15:15-16:15)
**בעיה:** ברי close עם volume 540K-980K (all-time max!) — `is_synthetic=0`. מעוותים rolling_avg של VSA.
**אבחון:** הצלב מול `~/SierraChart_Data/v9_export/5min.json` — DLL values או ingestion artifact?
**תיקון (אם artifact):** סנן volumes > threshold (100K?) מחישוב rolling_avg. או סמן is_synthetic.
**קובץ:** `backend/v9/api/v9/bars.py` (ingest) + `five_min_system.py` (detection).

### B5. S2 inspector spec texts (build status display)
**בעיה:** `s2_pattern_probe.py` עדיין מציג `90% drop` ו-`[1.5, 1.75] pts` בחלק מהמקומות.
**סטטוס:** תוקן חלקית (commit `957c509`). לוודא שכל ה-specs מעודכנים.

---

## C · Frontend

### C1. Chart session filter
**בעיה:** `bars5min` endpoint מערבב ברים מסשן קודם (15:xx אתמול) עם היום (09:30+).
**תיקון:** סנן ברים ב-ChartV5b.tsx — הצג רק מתחילת הסשן הנוכחי (18:00 ET אתמול או 09:30 ET RTH).
**קבצים:** `frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx`.

### C2. CVD alignment
**בעיה:** CVD bars לא מיושרים מתחת לנרות המחיר (timeScale שונה).
**תיקון:** וודא שה-CVD pane משתמש באותו timeScale כמו price series.
**קבצים:** `ChartV5b.tsx` (CVD rendering section).

### C3. Build Status global_gates display
**סטטוס:** תוקן — `global_gates` מרונדרים, readiness banner פעיל.
**נותר:** `woodies_5min` ו-`tpo_bars` מראים "dead" (by design). הוצאו מ-BLOCKED verdict.

### C4. TradeDetailsModal
**בעיה:** Cowork wired ל-`selectedTradeId` — alias נוסף ל-store. TypeScript casts תוקנו.
**נותר:** modal wiring לrow click (option A from UX spec) — TradeRowExpand → TradeDetailsModal.

### C5. Next.js "Object is disposed"
**סיבה:** Turbopack HMR stale module. Hard refresh (Cmd+Shift+R) מתקן.
**תיקון קבוע:** restart Next.js dev server.

---

## D · Infrastructure / Ops

### D1. Module-level flag imports → os.environ
**בעיה מערכתית:** כל הדגלים ב-`atr.py` נקראים ב-import time ונשמרים cached.
הplist עושה `export FLAG=true` לפני python, אז הערך **כן** בprocess — אבל
אם module אחר ייבא את `atr.py` לפני שה-export הגיע, הערך ישן.
**תוקנו:** `S2_VSA_VOLUME`, `S1_LIVE_RECLASS`, `S1_DYNAMIC_RECLASS` — שונו ל-`os.environ.get()` at call-time.
**עדיין cached:** `S4_EXTREME_TREND_RELABEL`, `S2_ATR_RELATIVE`, `S3_RELATIVE`, `S1_CVD_OPENING`,
`S1_DAYTYPE_STAGING`, `S1_IB_WIDTH_ATR`, `S3_MUTE`, `FOOTPRINT_DISABLED`.
**תיקון:** שנה **כולם** לקרוא מ-`os.environ` at call-time, או הוסף lazy property ב-`atr.py`.

### D2. Backfill lost tables
**טבלאות ריקות:** `v9_bars_30min_woodies`, `v9_bars_footprint`, `v9_bars_tick_reversal` (+ `v9_bars_cumulative_delta` חלקי).
**מקור:** `~/SierraChart_Data/v9_export/` → history_loader gap-fill.
**תיקון:** אחרי DB clean, הרץ `history_loader.run_gap_fill("startup")`.

### D3. SIGBUS crash (memory pressure)
**סיבה:** macOS APFS pagein failure — 16GB RAM עם Chrome+Sierra+Python+Node.
**המלצה:** סגור Chrome tabs מיותרים בזמן RTH. אם חוזר — שקול להעלות ל-32GB או להריץ dev server בנפרד.

### D4. DB safe_writer
**סטטוס:** `safe_writer.py` עם RLock serializes raw sqlite3 writes. ORM relies on WAL+busy_timeout.
**בעיה שנותרה:** ORM writes (tick_reversal) עדיין משחיתים → פתרון: disable tick_reversal (A1).

---

## E · Regression Tests
**87/87 pass.** כל שינוי חדש חייב regression green לפני commit.

---

## סדר עדיפות מומלץ

**ערב 2/6 (עכשיו):**
1. A1 — disable tick_reversal + rebuild clean DB
2. A3 — fix S4_EXTREME_TREND_RELABEL import caching
3. B1 — remove lookback_quiet when VSA ON
4. D1 — fix all remaining cached flag imports

**בוקר 3/6 (לפני 16:30 IL):**
5. Reload backend → verify: integrity=ok, readiness=READY, S4 trend=BLUE, S2 armed
6. B3 — strategic-stop: Initiative multiplier (1.2× or 1.3×?)

**אחרי RTH 3/6:**
7. B2 — b4_confirm backtest
8. B4 — volume artifact investigation
9. C1+C2 — chart fixes (dev server)
10. D2 — backfill tables

---

## דגלים פעילים ב-plist (נוכחי)

```
S2_ATR_RELATIVE=true
S3_RELATIVE=true
S1_IB_WIDTH_ATR=true
S1_CVD_OPENING=true
S1_DAYTYPE_STAGING=true
S1_DYNAMIC_RECLASS=true
S4_EXTREME_TREND_RELABEL=true
FOOTPRINT_DISABLED=true
S2_VSA_VOLUME=true
S1_LIVE_RECLASS=true
```

**להוסיף:** `TICK_REVERSAL_DISABLED=true`

---

## F · פריטים מה-ROADMAP שלא נכנסו ל-worklist (חשוב!)

### מהסעיף "חוסמים פתוחים" (section 1):
| # | פריט | סטטוס | רלוונטיות למחר |
|---|------|--------|---------------|
| F1 | **GAP-4 MAX_CONTRACTS** — sizing per-trade max 5 + Auth Table V2 | פרומפט מוכן | 🟡 לא חוסם SHADOW אבל צריך לפני LIVE |
| F2 | **D-094 R:R Fire Selection** — committed, flag OFF | מוכן להפעלה | 🟡 אחרי S2 יציב |
| F3 | **DLL frozen-tail** — אימות חי ב-RTH | code done, needs RTH verify | 🔴 **לאמת מחר** — לוודא שCCI לא קופא |
| F4 | **T1 hit detection** — committed, uncommitted fix | code ready | 🔴 **לאמת מחר** — Smart BE / T1/T2 targets |
| F5 | **TIME_STOP dedup** — ts%300 fix | committed but needs verify | 🟡 לוודא שlא מספר ברים מנופח |

### מסעיף SHADOW soak (section 2):
| # | פריט | סטטוס | רלוונטיות |
|---|------|--------|-----------|
| F6 | **UAT 4 צירים** — Quality/Recency/Cardinality/Latency | לא בוצע | 🟡 צריך אחרי RTH מחר |
| F7 | **EOD review יומי** — WR, drawdown, reason trees | לא מוגדר | 🟡 להגדיר process |
| F8 | **סקירת תבניות חלשות** — GB100/ZLR/VEGAS | לא בוצע | אחרי 10 ימי soak |
| F9 | **SHADOW soak ≥10 ימי RTH** | יום 2 מחר | 🟢 ממשיך אוטומטית |

### מסעיף Pipeline 5 (section 3):
| # | פריט | סטטוס | רלוונטיות |
|---|------|--------|-----------|
| F10 | **Sierra order routing** — stubs, לא אמיתי | לא התחיל | ⬜ לא למחר, Pipeline 5 |
| F11 | **P5-7 TradeCommandHandler** | לא התחיל | ⬜ מקביל |
| F12 | **P5-6 DLL heartbeat** | לא התחיל | ⬜ מקביל |

### uncommitted code (מ-30/5, Cowork flagged):
| # | פריט | קובץ | סטטוס |
|---|------|------|--------|
| F13 | TIME_STOP woodies dedup (ts%300) | `woodies_system.py:206` | ⚠️ uncommitted |
| F14 | T1 hit + bar_level_detector | `bar_level_detector.py:38` | ⚠️ uncommitted |
| F15 | Footprint dedup (level+direction+bar_ts) | `footprint_system.py:430,489` | ⚠️ uncommitted (irrelevant while disabled) |

### נפלו בין הכיסאות:
| # | פריט | מקור | רלוונטיות |
|---|------|------|-----------|
| F16 | **Woodies panel ≠ Sierra overnight** — badge "Last RTH" | roadmap 1b | 🟡 UX, לא חוסם |
| F17 | **pytest full green** — 87 pass, but need full suite | roadmap 1 | 🟡 לאמת כל tests |
| F18 | **publish day_type with except:pass** — silent swallow | roadmap 1 wiring | 🟡 לתקן (no-silent-failures) |
| F19 | **כיול ספים** — ATR k-values, VSA thresholds | after soak | ⬜ אחרי 10+ ימים |
