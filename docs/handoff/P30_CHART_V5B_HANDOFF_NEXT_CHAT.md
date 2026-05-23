# P30 ChartV5b — Handoff לצ'אט הבא (2026-05-20)

**מטרה:** המשך עבודה בלי לאבד הקשר.  
**בעלים:** Cursor agent · **סטטוס:** קוד לא committed (Michael מאשר לפני commit).  
**מקור אמת נוסף:** `docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md` (inbox כללי P30).

---

## 0. איפה כל התכנון עד LIVE (מאסטר אינדקס)

| שכבה | קובץ | מה יש שם |
|------|------|----------|
| **תור עבודה יומי (P30)** | [`P30_AGENT_INBOX_PRE_LIVE.md`](P30_AGENT_INBOX_PRE_LIVE.md) | §1 uploads · §2 מה תוקן · §3 G1–G8 · §4 mega-prompt ל-CC · **§6 Roadmap L0→L8** · **§8 תור משימות ממוספר (#1–#15)** |
| **מאסטר אינדקס (מוצר + ארכיטקטורה)** | [`docs/spec_authority/MEMS26_MASTER_INDEX_V2.markdown`](../spec_authority/MEMS26_MASTER_INDEX_V2.markdown) | S1–S6 specs · L0–L4 ארכיטקטורת מסחר · M-protections · D-decisions · **PROMPT sequence → SHADOW → LIVE** |
| **מפת יישום P30 (UI)** | [`docs/reports/PROMPT30_0_DESIGN_INGESTION.md`](../reports/PROMPT30_0_DESIGN_INGESTION.md) | מה לבנות / ADAPT / DEFER בקוקפיט |
| **דוחות שלב P30 (כרונולוגי)** | `docs/reports/PROMPT30_*.md` (21 קבצים) | 0=ingestion … 9b=CVD … 10=Woodies … 10b=plan live |
| **אחרי משימות הגרף (ChartV5b)** | §8 למטה + inbox §8 פריטים 12–15 | L2 soak → L3 Plan → L4 risk → L5 paper → L6–L8 LIVE |

### מפת דרכים L0 → L8 (מקוצר מ-inbox §6)

```
L0  Cockpit parity מול Sierra (גרף + Woodies + CVD — TPO ב-DLL/CC)
      ↓
L1  DLL parity (G1 proj, G2 prev session, G3 CVD t+interval, G4 tpo.json) — CC
      ↓
L2  6 מערכות ירוקות 4h soak (systems-snapshot)
L2.5 Bridge + Redis cleanup
L2.6 EOD archive (G6 — קוד קיים)
      ↓
L3  Plan tab + pre-fire / BLOCKED chain (PROMPT30_10b_PLAN_LIVE)
      ↓
L4  Risk audit (firewall, risk_engine, kill switch) — Michael sign-off
      ↓
L5  Paper dry run (V9_PAPER_MODE=1)
      ↓
L6  Broker dry run (Sierra simulator)
      ↓
L7  LIVE 1 contract, half-RTH — Michael go/no-go
      ↓
L8  Full LIVE
```

**איפה ChartV5b יושב:** חלק מ-**L0** — **L0 סגור 2026-05-20** (Michael sign-off: #7, #9, TASK A, G4 r2, #12).

### אחרי משימות הגרף — מה הלאה (בלי POC)

| סדר | משימה | מסמך |
|-----|--------|------|
| ~~1~~ | ~~פריט #1 UAT TASK A~~ | **DONE 2026-05-20** |
| ~~2~~ | ~~#12 L2 soak~~ | **DONE 2026-05-20** |
| **3** | inbox §8 **#13** — Plan tab BLOCKED → L3 | `PROMPT30_10b_PLAN_LIVE.md` |
| 4 | inbox §8 #14–#15 — risk → paper | inbox §6 L4–L5 |
| 5 | Day Type / Woodies | handoffs ב-`docs/handoff/INVESTIGATE_*`, `P30_WOODIES_*` |
| 6 | Michael: Sierra Remote Build (CVD 5m) | `docs/runbooks/SIERRA_DLL_OPS.md` |
| 7 | CC: G1/G4 DLL (לא Cursor) | inbox §4, `CC_FOLLOWUP_TPO_SUBGRAPH_INDICES.md` |

---

## הודעה להדבקה בתחילת הצ'אט הבא

**פרומפט מלא (מומלץ):** [`P30_NEXT_CHAT_FULL_PROMPT.md`](P30_NEXT_CHAT_FULL_PROMPT.md) — העתק את הבלוק מתוך §"בלוק להדבקה".

```text
(קצר) ראה P30_NEXT_CHAT_FULL_PROMPT.md — #13 Plan tab audit; L0/L2 סגורים; לא POC.
```

---

## 1. מה זה "פריט #1"?

**פריט #1** = **אימות ויזואלי (UAT)** שהתיקון ל-**TASK A** באמת עובד אצל Michael בדפדפן.

| שאלה | תשובה נדרשת |
|------|-------------|
| הנר האחרון למעלה — באיזה זמן? | למשל `07:10 ET` |
| הבר האחרון ב-CVD למטה — אותו זמן? | **חייב להיות זהה** |
| אותו מיקום X (פיקסל)? | כן → TASK A ✅ |
| Console | `[ChartV5b] CVD align check` → `aligned: true`, `deltaSec` ≤ 60 |

**זה לא תיקון קוד חדש** — זה בדיקה + אם `aligned: false` → לתקן רק `alignCvdPointTimesToPriceBars` / `cumOhlcSeries` (לא TPO).

---

## 2. סטטוס משימות (ChartV5b)

| ID | נושא | קוד | UAT ויזואלי | הערה |
|----|------|-----|-------------|------|
| **A** | יישור X: נרות ↔ CVD, `timeScale` משותף | ✅ | **DONE 2026-05-20** — Michael sign-off (#7) | §4 |
| **B** | Ghost / stale bars | ✅ | **DONE** — Michael PASS | — |
| **C** | 6 קווי TPO + pills | ✅ L0 | **DONE 2026-05-20** — G4 r2 + L0 sign-off; **אל תיגע ב-POC** | §5 |

---

## 3. שורש הבעיה שמצאנו (TASK A)

**נרות 5m:** `tsToUnix()` מפרש `YYYY-MM-DD HH:MM:SS` כ-**ET** עם סיומת `-04:00`.

**CVD מ-Sierra:** שדה `t` בנקודות הוא לעתים **שעון קיר ET שנשמר כ-UTC epoch** (לא UTC אמיתי).

**דוגמה מוכחת (API, 2026-05-20):**

| מקור | ערך | משמעות |
|------|-----|--------|
| `bars5min` אחרון | `2026-05-20 07:10:00` | ET נכון |
| `cumulative_delta` `t` אחרון (לפני shift) | `1779260999` | ≈ 07:10 **UTC** = 03:10 ET → **פער ~4h** |
| אחרי `alignCvdPointTimesToPriceBars` | `t + 14400` | מתיישר עם הנר |

**הערה:** כשה-DLL מעודכן (`period_s: 300`, נקודות כל 5 דקות), הפרונט עדיין צריך את ה-shift אם `t` נשאר בפורמט הישן.

---

## 4. מה תוקן בקוד (TASK A + תשתית, לא POC)

### 4.1 קבצים שנגעו

| קובץ | שינוי עיקרי |
|------|-------------|
| `frontend/v9/src/v9/components/chart/v5b/cvdMapping.ts` | **`alignCvdPointTimesToPriceBars()`** — shift +4h (EDT) או +5h (EST) לפי הפרש אחרון נר↔CVD |
| `frontend/v9/src/v9/components/chart/v5b/CvdChartPane.tsx` | קורא `align` לפני `normalizePoints`; לוג **`[ChartV5b] CVD align check`** עם `lastBarEt`, `lastCvdEt`, `aligned` |
| `frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx` | גרף אחד + 2 panes; `barsForCvdRef` מסנכרן עם נרות; `applyTpoToChart` (לא לפתח — Michael) |
| `tests/v9/frontend/test_cvd_time_align.py` | חוזה: פונקציית align קיימת ונקראת מ-CvdChartPane |

### 4.2 ארכיטקטורה (TASK A — נשארת)

```
createChart(container)
  ├─ pane 0: CandlestickSeries (מחיר)
  └─ pane 1: CandlestickSeries (CVD, cumOhlcSeries)
shared timeScale — zoom/pan על העליון מזיז את התחתון
```

- `cumOhlcSeries(barList, points)` — **בר אחד לכל timestamp של הנר** (1:1).
- `rightOffset: 0` על שני ה-scales (בקוד ChartV5b init).

### 4.3 באגים שתוקנו בדרך

| באג | תיקון |
|-----|--------|
| `Cannot access 'activeTf' before initialization` | `applyTpoToChart` / `tpoTimeSpan` **אחרי** `useState('5m')` |
| `buildTpoPlan is not defined` | import מ-`./tpoLevels` (רלוונטי ל-TPO — לא לפתח) |

---

## 5. TASK C / TPO — קרא בלבד, אל תערוך

Michael: **"לא לגעת ב poc יותר"**.

קיים (לא לשנות אלא אם מפורש):

- `frontend/v9/src/v9/components/chart/v5b/tpoLevels.ts` — `pickTodayPeriod`, `buildTpoPlan`, `syncTpoPriceLines`
- `SierraLevelsOverlay.tsx` — קווי SVG `<line>` + pills VAH/POC/VAL
- `ChartV5b.tsx` — `loadLevels`, `tpoOverlayRef`, `applyTpoToChart`

**בעיה עסקית נפרדת (DLL):** `MES_AI_DataExport.cpp` לא כותב `tpo.json` טרי — G4 ב-inbox. זה **CC / Sierra**, לא פרונט.

---

## 6. פרוטוקול UAT לפריט #1 (חובה לפני סגירת TASK A)

### 6.1 לפני

```bash
# Backend + frontend רצים (Michael)
lsof -i :8000 -i :3000
curl -s --max-time 5 http://localhost:8000/api/v9/status | head -c 200
```

### 6.2 בדפדפן

1. `http://localhost:3000` → **Cmd+Shift+R**
2. TF **5m**, המתן 5–10 שניות לטעינת bars + CVD
3. F12 → Console → חפש:

```text
[ChartV5b] CVD align check
```

**PASS:**

```json
{ "lastBarEt": "07:10", "lastCvdEt": "07:10", "deltaSec": 0, "aligned": true }
```

(השעות דוגמה — העיקר `aligned: true`, `deltaSec` < 60.)

4. **ויזואלי:** הנר האחרון למעלה והבר האחרון למטה — **אותו X** (גלול לימין / כפתור **▶|** `goToLatest`).

5. צילום מסך לפני/אחרי אם עדיין יש תלונה.

### 6.3 curl מהיר (מחוץ לדפדפן)

```bash
curl -s "http://localhost:8000/api/v9/chart/bars5min?limit=1" | python3 -c "
import sys,json; b=json.load(sys.stdin); print('bar', b[-1]['ts'])"
curl -s "http://localhost:8000/api/v9/cumulative_delta/current" | python3 -c "
import sys,json; d=json.load(sys.stdin); p=d['points'][-1]; print('period_s', d.get('period_s'), 'last_t', p.get('t'))"
```

- `period_s` צריך להיות **300** אחרי Sierra Remote Build חדש; אם עדיין **1500** — CVD עדיין 25 דקות ב-DLL (לא באג פרונט).

---

## 7. בדיקות אוטומטיות

```bash
cd /Users/michael/Downloads/mems26_web_git
python3 -m pytest \
  tests/v9/frontend/test_cvd_time_align.py \
  tests/v9/frontend/test_cvd_histogram_mode.py \
  -q
```

**לא להריץ** `test_tpo_overlay_six_lines.py` אם לא נדרש — קשור ל-TPO.

צפוי: **3 passed** (cvd tests) ללא שינויי TPO.

---

## 8. מה הצ'אט הבא צריך לעשות (סדר מומלץ)

| # | משימה | סטטוס |
|---|--------|--------|
| ~~1~~ | ~~UAT TASK A + #7~~ | **DONE 2026-05-20** |
| ~~2~~ | ~~G4 round 2 + #9 L0~~ | **DONE 2026-05-20** |
| ~~3~~ | ~~#12 L2 soak~~ | **DONE 2026-05-20** |
| **4** | **#13** Plan tab BLOCKED chain (S1–S6) | **READY** |
| **5** | **#14** Risk surface (L4) | WAIT #13 |
| **6** | **#15** Paper dry run (L5) | WAIT #14 |

---

## 9. מה לא לעשות

- ❌ שינוי ב-POC / TPO / `tpoLevels.ts` / `loadLevels` / צבעי קווי TPO
- ❌ `sc_study/`, `bridge/LaunchAgent`, `start_all.sh`, `npm run dev` בלי בקשה
- ❌ commit / push בלי בקשת Michael
- ❌ לסמן GREEN בלי `aligned: true` + צילום (ציר ויזואלי חמישי — ראה `P30_HANDOFF_NEXT_CHAT_2026-05-20.md`)

---

## 10. מצב שירותים (לעדכן בתחילת צ'אט)

| רכיב | בדיקה |
|------|--------|
| Backend `:8000` | `curl -s http://localhost:8000/api/v9/status` |
| Frontend `:3000` | `curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/` |
| Bridge | `tail -5 /tmp/bridge.err.log` — אין push ל-https |
| CVD `period_s` | `curl -s .../cumulative_delta/current \| jq .period_s` → 300 = DLL חדש |

---

## 11. דוחות קשורים

| מסמך | תוכן |
|------|------|
| `docs/reports/PROMPT_P30_CHART_SYNC_AND_BRIDGE_CLEANUP.md` | סנכרון panes + ציר זמן |
| `docs/reports/PROMPT30_9b_CVD_PANE.md` | CVD pane מקורי |
| `docs/handoff/P30_HANDOFF_NEXT_CHAT_2026-05-20.md` | אסטרטגיה: UAT לפני דוחות |
| `docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md` | תור G1–G8, L0–L8 |

---

## 12. היסטוריית שיחה (תמצית)

- Michael: אין קווי TPO, CVD לא מיושר → תוקן (SVG overlay, `alignCvdPointTimesToPriceBars`, `tpoLevels.ts`).
- Michael: "לא לגעת ב poc יותר" — **freeze** על TPO/POC בפרונט.
- **2026-05-20 — Michael sign-off:** #7 UAT ויזואלי · TASK A (פריט #1) · #12 L2 soak · #2 G4 round 2 · #9 L0 מלא.
- **הבא:** inbox #13 Plan tab (לא POC).

---

*עודכן 2026-05-20 — פריט #1 + L0/L2 סגורים.*
