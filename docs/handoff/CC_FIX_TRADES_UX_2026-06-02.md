# CC Mega-Prompt — תיקון מימוש Trades UX (corrective)

> פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.

**הקשר:** מימוש ה-Trades redesign הראשון (commit-ים של 2026-06-02 ~13:25) בנה חלק
מהרכיבים אבל **חזר על הבאג שהאפיון הזהיר מפניו** ופספס מרכיבים מאושרים. זה פרומפט
**מתקן** — לתקן את הקיים, לא לבנות מאפס. כל באג למטה אומת מול הקוד הנוכחי (file:line).

**אסור לגעת (risk surface):** backend, decision pipeline, polling floors, bridge. Frontend בלבד.
**Source-of-truth (Rule 1):** שדה `null` → `—`, בלי סינתזה.

---

## ✅ מה נכון — לשמור
- `TradesTable.tsx` — toggle `visual/classic` (RowView) + שמירת המסלול הקלאסי. KEEP.
- קיום `EdgeKpiRow`, `EquityCurveStrip`, `TradePathVisual` כרכיבים נפרדים. KEEP (יתוקנו).
- `useBuildStatus`/endpoint לא נגעו. KEEP.

---

## 🔴 P1 — באג קריטי: קומולטיב/equity ממוין לפי `entry_ts` במקום `exit_ts`
**איפה:** `EquityCurveStrip.tsx:30` ו-`EdgeKpiRow.tsx:47` —
`.sort((a,b)=>(a.entry_ts??'').localeCompare(b.entry_ts??''))`.
**למה זה שגוי:** equity ממומש ו-max-drawdown נצברים לפי **סדר הסגירה**. בדיוק כאן נכשל
ה-acceptance שכבר תועד: #382 נסגרה 06:50 *לפני* ש-#371–380 נסגרו 08:35 — אך נכנסו אחריהן.
מיון לפי `entry_ts` מצייר עקומה שגויה ו-max-DD שגוי.
**תיקון:** למיין לפי `exit_ts` (פתוחות בלי `exit_ts` — להוציא מהעקומה הממומשת). בנוסף, להוסיף
**שתי סדרות**: `cumClose` (לפי `exit_ts`) ו-`cumOpen` (לפי `entry_ts`) — שתיהן הוצגו ב-mockup המאושר.
- **Acceptance:** עם fixture [A: entry 09:00/exit 12:00/+100, B: entry 10:00/exit 10:30/−50] →
  `cumClose` הוא B(−50) ואז A(+50); `cumOpen` הוא A(+100) ואז B(+50). max-DD מ-`cumClose`.
- **אימות:** `npx vitest run src/v9/lib/__tests__/tradeMath.test.ts` (ראה P0).
- **anti-tautological:** *if reverted (מיון חזרה ל-`entry_ts`) → RED because cumClose order assertion fails.*

## 🔴 P0 — חילוץ הנגזרות ל-`lib/tradeMath.ts` + unit tests (חסר לגמרי)
היום הנגזרות inline ב-3 קבצים, חלקן באגיות, **בלי שום טסט** — הפרת חוזה B1.
**תיקון:** ליצור `frontend/v9/src/v9/lib/tradeMath.ts` עם פונקציות טהורות, ולקרוא להן מכל
הרכיבים (להסיר את ה-inline):
- `formatUsdAccounting(v)` → רווח `+$5.00`, הפסד `($33.75)`, אפס `$0.00`.
- `rLevels(t)` → `{risk=|entry−stop_initial|, stopR:-1, t1R, t2R, exitR:pnl_r, movedR}` (favorable לפי כיוון).
- `riskReward(t)` → `{t1:t1R, t2:t2R}` או `null` כש-`t1==null`.
- `stopMovement(t)` → `'moved'` כש-`|stop_initial−stop|≥0.01`; `'t1_no_be'` כש-`stop_issue==='T1_NO_BE'`; אחרת `'static'`.
- `durationMinutes(t)`, `cumulativeByClose(list)`, `cumulativeByOpen(list)`.
- **anti-tautological:** הטסט מייבא מ-`../tradeMath` (לא מעתיק); כל בדיקה עם שורת *if reverted → RED because ___*. כיסוי חובה: formatUsdAccounting(-33.75)==='($33.75)'; cumulativeByClose ממיין exit_ts (P1); riskReward(t1=null)===null; stopMovement על stop_initial≠stop → 'moved'.

## 🔴 P2 — `TradePathVisual`: ציר מחיר מוחלט → ציר R יחסי
**איפה:** `TradePathVisual.tsx:96-101` (`pMin/pMax/toX` על מחיר גולמי).
**למה:** האפיון המאושר הוא **ציר R יחסי** — כניסה=0, סטופ התחלתי=−1R, יעדים/יציאה במכפילי R —
כדי שעסקה של 0.25 נק׳ ועסקה של 9 נק׳ ייראו באותו קנה-מידה.
**תיקון:** למפות לפי `rLevels(t)` (P0): ציר מ-`minR` ל-`maxR`; קו 0 (כניסה, לבן מקווקו) וקו −1R
(סטופ, אדום); תוויות **גלויות ומדורגות** (לא רק `<title>` על hover) — סטופ/יעדים מעל, כניסה/יציאה מתחת;
ולהוסיף **חץ תנועת-סטופ** מ-−1R ל-`movedR` כש-`stopMovement==='moved'` עם תג `BE✓`. להשתמש ב-CSS vars
(לא hex קשיח כמו `#ef4444` בשורות 34/39/...).
- **Acceptance:** עסקה עם `stop_initial≠stop` מציגה חץ + `BE✓`; ציר מציג `−1R`/`0`/`+x.xR`; שתי תוויות
  במחיר קרוב אינן חופפות.
- **אימות:** component test על trade שזז ועל trade שלא — נוכחות `BE✓`/`סטטי` ותווית `-1R`.
  *if reverted (ציר חזרה למחיר מוחלט) → RED because no R labels rendered.*

## 🟠 P3 — פורמט חשבונאי (סוגריים) בכל מקום
**איפה:** `EdgeKpiRow.tsx:76` (`fmtUsd` עם מינוס מוביל), `EquityCurveStrip.tsx:81/86/118/121`,
maxDd `-$` (`EdgeKpiRow.tsx:105`).
**למה:** ב-RTL המינוס המוביל נשבר — Michael ביקש סוגריים ללא מינוס.
**תיקון:** להחליף הכל ל-`formatUsdAccounting` מ-P0. הפסד=`($X)`, רווח=`+$X`.
- **Acceptance:** Net שלילי ו-Max DD מוצגים `($82.50)` ולא `-$82.50`.
- **אימות:** component test EdgeKpiRow עם net שלילי. *if reverted → RED.*

## 🟠 P4 — R:R (חסר לגמרי)
**תיקון:** להוסיף צ'יפ `R:R 1:x` בכל שורה (visual+classic), KPI "R:R~ T2" ב-`EdgeKpiRow`,
ואופציית מיון `R:R↓`. מקור: `riskReward(t)` מ-P0.
- **Acceptance:** שורה מציגה `R:R 1:2.2`; מיון R:R↓ ממיין יורד לפי `t2R`.
- **אימות:** component test. *if reverted → RED.*

## 🟠 P5 — `TradeFilters` → סרגל קומפקטי + פילטר סטופ + מיון R:R
**איפה:** `TradeFilters.tsx` (עדיין הגרסה הוורבּוזית; mode/overlap כבר קיימים).
**תיקון:** בוררים קומפקטיים (גובה ~26px) בשורה אחת; להוסיף **סטופ** (All / זז BE / סטטי) דרך
`filters.stopMove` חדש ב-`tradeStore` (משתמש ב-`stopMovement`), ואת מיון `R:R↓`. לשמור mode/overlap הקיימים.
- **Acceptance:** כל הבוררים גלויים ב-1280px בלי חיתוך; "זז BE" מסנן רק `stopMovement==='moved'`.
- **אימות:** component test על הפילטר. *if reverted → RED.*

## 🟠 P6 — פנל פרטים לעסקה נבחרת (חסר)
היום אין פנל-צד; המידע פזור. **תיקון:** פנל קבוע (או הרחבת `TradeRowExpand`) שמראה לעסקה הנבחרת:
מחירים+R, **risk/reward** (נק׳ + R + יחס + מומש), **ניהול סטופ** (verdict מ-`stopMovement`:
"זז ל-BE לפי אפיון / ⚠ T1_NO_BE / סטטי −1R"), ו-**קומ׳ פתיחה + קומ׳ סגירה**.
- **Acceptance:** בחירת שורה ממלאת את הפנל; trade שזז מציג `SMART_BE stop_initial→stop`.
- **אימות:** component test click→panel. *if reverted → RED.*

## 🟡 P7 — להסיר כפילות strips
`TradesView.tsx:52-54` מרנדר `TradesSummaryStrip` **וגם** `EdgeKpiRow` **וגם** `EquityCurveStrip` —
אותם מספרים שלוש פעמים. **תיקון:** להשאיר `EdgeKpiRow`+`EquityCurveStrip`; להסיר את
`TradesSummaryStrip` מה-view (הקובץ נשאר, לא נמחק).
- **Acceptance:** אין הצגה כפולה של Net/Win%; הדף נטען ללא שגיאות.
- **אימות:** `npm run build` (0 errors) + בדיקה ויזואלית/snapshot.

---

## דוח חובה (חלק C) + NOT-DONE + roadmap
טבלת phases (Status+Evidence command+output+Deviation), שורת "if reverted → RED" לכל טסט,
סעיף **NOT DONE / DEVIATIONS**. בסיום עדכן `ROADMAP_TO_LIVE.html` + `STATUS_BOARD.md`
(שורת log: root=entry_ts ordering → fix exit_ts + tradeMath tests → verified).

## עצירה אסטרטגית
הכל frontend. אם משהו דורש backend/endpoint (למשל שדה חסר) — עצור ודווח (B6), אל תרחיב בשקט.
