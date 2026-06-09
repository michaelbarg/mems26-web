# CC Prompt — Fire-Audit Diagnosis + Pre-Fire Readiness Gate · 2026-06-01

**מאת:** Cowork agent (תפקיד: סוכן בקרת מערכת) → **אל:** Claude Code
**הקשר מקור:** `docs/reports/AGENT_FIRE_AUDIT_VISIBLE_WINDOW_2026-06-01.md` (ניתוח חזותי, חלון נראה)
**רקע משלים:** `docs/reports/DAY1_DEEP_ANALYSIS_2026-06-01.md` · `docs/reports/PATTERN_AUDIT_DAY1_2026-06-01.md`

> **משמעת Pre-LIVE (CLAUDE.md) — חובה בכל סעיף כאן:**
> 1. **Diagnose first, fix second.** אמת כל היפותזה עם נתון (DB query / log read) **לפני** נגיעה בקוד.
> 2. **קרא את הקוד הנוכחי** לפני כל הצעה. אפס עריכות מהזיכרון.
> 3. **Audit existing surfaces** — לכל רכיב שתיגע: סווג KEEP / ADAPT / REPLACE / DEFER.
> 4. **Rule 5 — verification quote, not assertion.** כל "תוקן/עובד/אמור" = **הדבק command + raw output**. אל תכתוב "אומת, ממשיך".
> 5. **Strategic stop** בכל phase gate ולפני כל שינוי שנוגע ל-firing logic / risk surface — עצור ושאל את Michael.
>
> **חלק A = אבחון בלבד (אפס שינוי קוד). חלק B = design + אישור Michael לפני מימוש.**

---

## חלק A · "למה זה לא ירה בפועל?" — אבחון פר-פריט

הניתוח החזותי (חלון נראה, 2026-06-01) זיהה 7 מועמדים שהמערכת **הייתה צריכה** לשקול. עבור **כל פריט**, החזר אבחון מעוגן-נתונים: **למה הוא לא ירה בפועל** — באג, gating לפי spec, סף, תנאי שלא התקיים, או "אין נתון". **הדבק את ה-query והפלט הגולמי** לכל קביעה.

### טבלת המועמדים (מהדוח החזותי)

| # | מערכת | תבנית | כיוון | מיקום נראה | conviction | היפותזה ראשונית למה לא ירה |
|---|-------|-------|-------|------------|-----------|------------------------------|
| 1 | S4 | ZLR UP | LONG | חץ ירוק ~12:15 | גבוה | DLL סימן אך לא תורגם ל-fire? dispatcher/decision_tree חסם? |
| 2 | S4 | ZLR UP | LONG | בר "עכשיו" ~13:15 | גבוה | bounce טרי — נחסם? dedup? trend≠BLUE? |
| 3 | S2 | INITIATIVE | LONG | פריצת VAH ~12:25–12:45 | בינוני-גבוה | Auth Table `SKIP` כי S1=Normal? |
| 4 | S2 | REACTIVE | LONG | חזרה ל-POC/IB_H | בינוני | `DROP_THRESHOLD_PCT=0.10` בלתי-אפשרי |
| 5 | S4 | ZLR DOWN | SHORT | ~09:30 ו-~10:00 | בינוני | trend GRAY → P-W5 חוסם? |
| 6 | S4 | HFE DOWN | SHORT | פסגות CCI>+200 | נמוך | AP5 bars_ago? trend GRAY? counter-trend? |
| 7 | S2 | BULL_FLAG | LONG | דשדוש 7620–7628 | מותנה | run<5 ברים? day_type לא TN/NV? |

### מה להריץ לכל פריט (אבחון, read-only)

**S4 (פריטים 1,2,5,6):**
- `v9_bars_5min_woodies`: שלוף ts, cci_14, cci_6_tcci, trend_state, zlr_detected, zlr_direction, hfe_detected, hfe_direction, hfe_extreme_bars_ago — לחלון 2026-06-01 RTH. אמת מול `zlr.py` / `hfe.py`:
  - ZLR UP: היה CCI≥+100 ב-12 ברים? היה pullback (−100<CCI≤100)? בבר ה-fire `current>prev` ו-`0<current<200`?
  - ZLR DOWN: מראה — היה CCI≤−100, pullback, `current<prev`, `−200<current<0`?
  - HFE: `hfe_detected` מה-DLL? `2≤hfe_extreme_bars_ago≤12` (AP5)? hook≥50?
  - **P-W5 gate:** מה היה `trend_state` באותם ברים? GRAY/YELLOW → נחסם (לפי spec). הדבק את ה-trend_state פר-בר.
- `v9_woodies_signals`: האם נרשם signal כלשהו באותם ts? אם כן — מה ה-classification ומדוע לא הפך ל-route?
- לוגים: חפש `[Woodies]` סביב אותם ts — `not_ready_to_route` / `duplicate_bar_ts` / `YELLOW state blocked` / `Gateway blocked`. הדבק את השורות.

**S2 (פריטים 3,4,7):**
- `v9_day_type_history` / `v9_day_type_state` ל-2026-06-01: מה ה-`day_type`, `ib_width_class`, opening_type, ותזמון? האם סווג מחדש אחרי IB lock? (היפותזה: תקוע Normal).
- **Initiative (#3):** אמת מול Auth Table — `INITIATIVE_LONG × Normal = SKIP`? הצג את שורת ה-Auth Table הרלוונטית. בנוסף: האם המבנה ה-4-ברי בכלל התקיים (`_detect_initiative`)? COT<AMT? expansion gate (ATR-relative)?
- **Reactive (#4):** הדבק `DROP_THRESHOLD_PCT` הנוכחי (`five_min_system.py`). חשב את מינימום יחס `b2_vol/b1_vol` בחלון — כמה זוגות עברו 0.10? (היפותזה: 0).
- **Bull Flag (#7):** מה אורך ה-bull run המקסימלי בחלון (`detect_bull_flag`)? סף=5. ומה day_type בזמן — מורשה (TN/Variation/NeuE/Normal)?

**S1 (חוצה — פריטים 3,7):**
- האם קיים מנגנון re-evaluation שבודק IB extension / VA breakout אחרי הסיווג הראשוני? (חפש `_rescore_from_behavior` / `_check_ib_extension` ב-state machine). אם לא רץ / לא קיים — זה השורש ל-#3 ואולי #7.

### פלט נדרש לחלק A
לכל פריט: **VERDICT** ∈ {באג / spec-gating / סף / תנאי-לא-התקיים / אין-נתון}, עם **command + raw output** שמוכיח. ללא הצעות תיקון בשלב זה — רק האבחון. אם פריט הוא **באג מאומת** (למשל ZLR שסומן ב-DLL ולא נורה ללא סיבת-spec), סמן `BUG-CONFIRMED` והשאר ל-Michael להחליט על תיקון.

---

## חלק B · מנגנון Pre-Fire Readiness Gate (design → אישור → מימוש)

**מטרה (מ-Michael):** מנגנון אוטומטי שלפני/במהלך מסחר **בודק שהכל תקין, מאשר שהמערכת מוכנה לירי, ונותן המלצות** — אוטומציה של `docs/runbooks/PRE_TRADE_PROTOCOL.md`.

### אל תבנה מאפס — Audit קודם
קיים כבר:
- `backend/v9/systems/build_status/aggregator.py` — `BuildStatusAggregator` מאחד S1/S2/S3/S4/bridge/footprint, read-only (sqlite `mode=ro`), לא זורק 500.
- `s2_inspector.py` / `woodies_inspector.py` / `day_type_inspector.py` / `bridge_inspector.py` / `footprint_inspector.py` — כל אחד מחזיר `SystemStatus` (running/hydrated/armed-blocked patterns).
- `build_status_routes.py` — endpoint קיים.
- `scripts/sot_health.py --strict` — בדיקת streams/exports.
- `PRE_TRADE_PROTOCOL.md` — ה-checklist הידני (Phase 0–6).

**משימה ראשונה:** מפה כל Phase/בדיקה ב-`PRE_TRADE_PROTOCOL.md` לשדה קיים ב-`BuildStatusResponse` / `sot_health`, וסמן: כבר-מכוסה (KEEP) · קיים-וצריך-הרחבה (ADAPT) · חסר (חדש). **אל תכפיל** בדיקה שכבר קיימת.

### עקרון התכנון
שכבת **verdict** דקה **מעל** ה-aggregator הקיים — לא מנוע חדש. היא **read-only**, לא נוגעת ב-firing logic, ולכן risk-surface נמוך (אבל עדיין דורשת אישור Michael כי היא הופכת ל-gate לפני מסחר).

מבנה הפלט המוצע (לכל מערכת + overall):
```
verdict: READY | DEGRADED | BLOCKED
checks:  [ {phase, name, status: PASS|FAIL|UNKNOWN, evidence, recommendation} ]
overall: { ready_to_trade: bool, blocking: [...], recommendations: [...] }
```
כללי verdict (priors — לאישור Michael):
- **BLOCKED** אם כשל Phase 0–3 (שירות מת / stream stale / ערך≠Sierra / DISCONNECTED).
- **DEGRADED** אם Phase 4–6 חלקי (תבנית לא ARMED שעות לתוך RTH / day-type "—" / דגל ON ללא אפקט).
- **READY** רק אם אין FAIL ב-0–3 ולפחות מערכת אחת ARMED ב-session פעיל.
- כל FAIL נושא **המלצה** ממופה לטבלת "כשלים ידועים" ב-runbook (עמודת תיקון).

### החלטת-עיצוב ל-CC להמליץ + Michael לאשר
באיזו צורה לחשוף את ה-gate (המלץ אחת, נמק):
1. **הרחבת build_status** — שדה `readiness` ב-`BuildStatusResponse` + תצוגה בדאשבורד (משתלב בקיים, מתעדכן עם ה-polling).
2. **סקריפט CLI** בסגנון `scripts/sot_health.py` (למשל `scripts/pre_fire_readiness.py`) — מתאים ל-T-30 ולהרצה מתוזמנת, פלט PASS/FAIL לטרמינל.
3. **שניהם** — לוגיקת verdict משותפת במודול אחד, נחשפת גם ב-endpoint וגם ב-CLI.

### דרישות מימוש (אחרי אישור בלבד)
- read-only מוחלט (אפס DB writes; sqlite `mode=ro` כמו ה-aggregator).
- אפס self-HTTP בתוך ה-aggregator (כמו §5.4 הקיים).
- כל check עוטף try/except + `logger.warning` rate-limited; אף פעם לא 500.
- **טסט regression** לכל verdict-rule (READY/DEGRADED/BLOCKED) עם fixtures.
- עדכון `PRE_TRADE_PROTOCOL.md` להצביע על ה-gate האוטומטי ליד ה-checklist הידני.
- **Rule 5:** הדבק פלט גולמי של ה-gate בשני מצבים — יום תקין (READY) ויום עם כשל מוזרק (BLOCKED).

### Strategic stop
עצור ושאל את Michael ב-2 נקודות: (א) אחרי מיפוי ה-KEEP/ADAPT/חדש + המלצת הצורה (1/2/3) — **לפני** כתיבת קוד. (ב) לפני שה-gate הופך ל-gate חוסם-מסחר בפועל (ולא רק אינפורמטיבי).

### Roadmap auto-update
בסיום: עדכן `docs/plans/ROADMAP_TO_LIVE.html` + `docs/plans/STATUS_BOARD.md` (root → fix → verification per Rule 5), כמתחייב ב-CLAUDE.md.

---

## סדר עבודה מוצע ל-CC
1. **חלק A** — אבחון 7 הפריטים, raw evidence, VERDICT פר-פריט. דווח ל-Michael.
2. **חלק B שלב 1** — audit KEEP/ADAPT/חדש מול ה-runbook + המלצת צורה. **עצור לאישור.**
3. **חלק B שלב 2** — מימוש read-only + טסטים + raw verification. **עצור לאישור** לפני הפיכה ל-gate חוסם.
4. עדכון roadmap/status.
