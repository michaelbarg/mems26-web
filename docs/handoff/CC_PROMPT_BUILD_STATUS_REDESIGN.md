# CC Prompt — Build Status Redesign (decision-tree-to-fire)

> פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.

**מטרה אחת:** לבנות עמוד **Build Status** מסודר שבמרכזו **עץ החלטות per-system עד רגע
הירי** — "מה הולך לירות ואיפה זה נתקע ולמה" — בנוי מ-5 אזורים + לולאת קישור ל-Trades.
מקור עיצוב: ה-mockup שאושר מול Michael + `docs/reports/UX_AUDIT_TRADES_BUILD_2026-06-02.md`.

הנתונים כבר קיימים ב-`GET /api/v9/build/pattern-status` (אומת:
`frontend/v9/src/v9/hooks/useBuildStatus.ts:29`, schema `…/components/build_status/types.ts`).
**רענון ידני בלבד — אסור להוסיף auto-poll** (CLAUDE.md §Frontend Polling Floors).

---

## 0 · גבולות — מה אסור לגעת (risk surface)

- **אסור** לשנות לוגיקת מסחר / decision pipeline / dispatcher / DLL / bridge.
- **אסור** לערוך את ערכי `AUTH_TABLE` ב-`backend/v9/systems/build_status/auth_table_lookup.py`
  — זו ספציפיקציה **נעולה** (`S2_AUTH_TABLE_V1.md` 🔒). מותר אך ורק **לקרוא ולשרשר** אותה.
- **אסור** auto-poll. שומרים על מודל הרענון-הידני הקיים.
- **אסור** למחוק את `BuildStatusTab.tsx` הקיים — להשאיר כ-fallback.
- **Source-of-truth (CLAUDE.md Rule 1):** מצב שער שלא ידוע / freshness חסר → להציג
  "stale"/"—". **אסור** להמציא `present:true` או ערך live שלא הגיע מה-payload.
- טקסט "כניסה/יציאה" ב-Auth Table הוא **תיאור UI בלבד** — לא חוקי-מסחר חדשים, לא מחווט
  לשום ביצוע. אם נראה שהוא דורש wiring → לעצור ולדווח (B6).

---

## 1 · Audit לפני בנייה (KEEP / ADAPT / REPLACE)

| רכיב | קובץ | סיווג |
|---|---|---|
| `BuildStatusTab` | `…/build_status/BuildStatusTab.tsx` | KEEP (fallback) |
| `SystemSection` / `ComponentTable` / `PatternRow` / `StatusPill` | `…/build_status/*` | ADAPT — נשען עליהם לרנדר שערים |
| `useBuildStatus` | `…/hooks/useBuildStatus.ts` | KEEP — אותו endpoint, אותו refresh ידני |
| `types.ts` | `…/build_status/types.ts` | KEEP — מכסה `SystemBlock/Pattern/Component/Readiness` |
| `auth_table_lookup.py` | `backend/v9/systems/build_status/` | KEEP (לקרוא בלבד) |

חובה לקרוא כל קובץ לפני שינוי. `SystemBlock` כבר כולל את כל מה שצריך לעץ:
`global_gates`, `patterns[].components[]` (עם `stage`,`present`,`live`,`required`,`freshness`),
`live_inputs`, `interpretations`, `fired_today_count`, `last_fire_ts`, `data_freshness`,
`mode`, `running`, `hydrated`. ה-`readiness` כבר נושא `verdict`+`checks`.

---

## 2 · 5 האזורים (היררכיה מלמעלה למטה)

1. **Readiness bar** — `readiness.verdict` + `rtb_session` (RTH/IB) + **סוג יום מזוהה**
   (מ-`interpretations` של S1 / `day_type`) + סיכום "יורה עכשיו / הקרוב לירי" (נגזר).
2. **System rail S1–S6** — כרטיס לכל מערכת עם **מד התקדמות-לירי** (#שערים שעברו / סה״כ),
   סטטוס (ARMED / חסום ב-X / observe-only), `fired_today_count` + סה״כ. לחיצה בוחרת מערכת.
3. **עץ החלטות (מערכת נבחרת) — המרכז** — pipeline של `global_gates`+`components` לפי `stage`,
   ירוק=present, **צהוב="אתה כאן"** על השער הראשון שאינו present (live מול required + מה חסר),
   תג **`← S1`** על שער שתלוי בפלט S1, וצומת **🔥 FIRE** (ARMED אם כל השערים present).
4. **Auth Table** — מטריצה pattern×day_type, מתעדכנת לפי סוג היום מאזור 1, confluence→חוזים,
   תבניות מומלצות + טקסט כניסה/יציאה (תיאורי).
5. **Fire ledger** — יריות אחרונות (מ-`/api/v9/trades`), לכל ירייה סיבה (`pattern_id/trigger`)
   + P&L + **קישור ל-Trades עם מספר הירייה**.

---

## 3 · Phases אטומיים (Acceptance בינארי + פקודת אימות)

### P0 — backend read-only: חשיפת AUTH_TABLE  ⚠ דורש אישור Michael (B5/B6)
מימוש: route חדש `GET /api/v9/build/auth-table` שמחזיר את
`auth_table_lookup.AUTH_TABLE` **verbatim** (+`DAY_TYPE_SHORT_TO_ENUM`). אפס לוגיקה, אפס
שינוי בערכים. אם לא מאושר — חלופה: embed קריאה-בלבד ב-frontend מסומן `// synced to
S2_AUTH_TABLE_V1.md 🔒` (סיכון drift — לציין ב-NOT-DONE).
- **Acceptance:** `curl -s localhost:8000/api/v9/build/auth-table` מחזיר תא
  `BULL_FLAG_LONG.Trend_Normal == ["FULL",3,2,2]` (תואם ל-`auth_table_lookup.py`).
- **anti-tautological:** הטסט מייבא את ה-route ומשווה את הפלט ל-`auth_table_lookup.AUTH_TABLE`
  האמיתי (לא מעתיק ערכים לטסט). *if reverted (route מחזיר {}) → RED.*

### P1 — `lib/buildDerive.ts` + unit tests
`progressToFire(sysBlock)` (סופר present עד השער החסר הראשון), `isArmed(sysBlock)`,
`firstBlocker(sysBlock)`, `dependsOnS1(gate)` (סורק `interpretations.from_input ~ /S1/`),
`readinessSummary(systems)` (armed[] + closest).
- **Acceptance:** מערכת עם 4 present + 1 missing → `progress={passed:4,armed:false}`;
  מערכת עם הכל present → `armed:true`. `dependsOnS1` מזהה `from_input:"S1_day_type"`.
- **אימות:** `cd frontend/v9 && npx vitest run src/v9/lib/__tests__/buildDerive.test.ts`.
  *if reverted (progress תמיד total) → RED.*

### P2 — `SystemRail`
6 כרטיסים, מד התקדמות, סטטוס, `fired_today_count`, בחירה.
- **Acceptance:** מערכת observe-only (אין pattern עם fire-path) מציגה "observe", לא progress
  מטעה; מערכת armed מציגה "🔥".
- **אימות:** component test — render עם fixture של 6 מערכות, assert על badge/progress.
  *if reverted → RED.*

### P3 — `DecisionTree` (מרכזי)
רנדר `global_gates`+`components` לפי `stage`; present=ירוק, missing-ראשון="אתה כאן"
(מציג `component.live` / `component.required` / freshness + "חסר"), `← S1` כש-`dependsOnS1`,
פס התקדמות, צומת FIRE.
- **Acceptance:** השער ה-"here" הוא בדיוק ה-missing הראשון; ARMED ⇔ אין missing; תג `← S1`
  מופיע על `day_type_gate` של S2/S4.
- **אימות:** component test על fixture חסום (S4, day_type_gate missing) — assert שה-"אתה כאן"
  על `day_type_gate` ויש `← S1`. *if reverted (here על שער שגוי) → RED.*

### P4 — `ReadinessBar`
`verdict` + `rtb_session` + day_type מזוהה + summary armed/closest (מ-`readinessSummary`).
- **Acceptance:** כש-מערכת אחת armed והשאר חסומות → verdict מ-payload מוצג; summary מציין
  את ה-armed ואת ה-closest הנכון.
- **אימות:** component test. *if reverted → RED.*

### P5 — `AuthTableView`
fetch `/api/v9/build/auth-table` (P0); מטריצה 10×7; בורר day_type (ברירת מחדל = day_type
מזוהה); toggle confluence (HIGH/MED/LOW → אינדקס חוזים); תבניות מומלצות (FULL) עם הסבר +
טקסט כניסה/יציאה (תיאורי, מסומן non-executable); resolver למועמד.
- **Acceptance:** בחירת `Nontrend` → כל התאים SKIP + באנר "עומדים בצד"; toggle confluence
  משנה את מספר החוזים בכל תא בהתאם ל-tuple.
- **אימות:** component test עם ה-AUTH_TABLE האמיתי — בחר `Nontrend`, assert שאין תא != SKIP.
  *if reverted → RED.*

### P6 — `FireLedger`
מ-`/api/v9/trades` (recent): לכל ירייה system + reason (`pattern_id`→`trigger`→`classification`)
+ P&L (פורמט חשבונאי) + deep-link ל-`/trades` עם ה-id.
- **Acceptance:** לחיצה על שורת ירייה מנווטת ל-`/trades` ומדגישה/פותחת את ה-trade עם אותו id.
- **אימות:** component/e2e — click ⇒ navigation ל-`/trades` עם param ה-id. *if reverted → RED.*

### P7 — `BuildStatusView` + route `/build` + לולאה ל-Trades
`app/build/page.tsx` עוטף `BuildStatusView` שמרכיב אזורים 1–5. Nav ל-`/build`.
`BuildStatusTab` הישן נשאר כ-fallback. לולאה: fire→`/trades#id`; תא Auth→`/trades?pattern=…&dayType=…`
(אם פילטר ה-day_type בעמוד Trades לא קיים — לעצור ולדווח, לא לאלתר backend).
- **Acceptance:** `/build` עולה ללא שגיאות console; refresh ידני עובד; שני ה-deep-links עובדים.
- **אימות:** `cd frontend/v9 && npm run build` (0 errors) + `npx playwright test
  tests/components/build-view.spec.ts` (ליצור spec מינימלי שטוען `/build`).

---

## 4 · ארבעת צירי UAT
1. **Quality:** אין שער עם מצב מסונתז — `present` רק מה-payload; freshness חסר → "stale".
2. **Recency:** `fired_today_count` בכרטיס == `COUNT(*) v9_trades WHERE date=today AND firing_system=N`.
3. **Cardinality:** מספר השערים בעץ == `global_gates.length + components.length` לאותה מערכת.
4. **Latency:** רנדר העמוד עם 6 מערכות < 200ms; אין auto-poll (רענון ידני בלבד).

## 5 · דוח חובה (חלק C) + NOT-DONE + עדכון roadmap
טבלת phases (Status+Evidence+Deviation), "if reverted → RED" לכל טסט, סעיף
**NOT DONE / DEVIATIONS** (גם "none"). בסיום: עדכן `docs/plans/ROADMAP_TO_LIVE.html`
(פריט "Build Status redesign") + `docs/plans/STATUS_BOARD.md` (שורת log: finding+fix+verification).

## 6 · עצירה אסטרטגית
P0 הוא התוספת היחידה ל-backend (read-only) — **אישור Michael לפני** (B5). כל צורך נוסף
ב-backend/endpoint/לוגיקה שמתגלה תוך כדי → **עצור ודווח** (B6), אל תרחיב בשקט.

## 7 · נדחה לפאזה נפרדת (לא בהיקף הזה)
שכבת **edge היסטורי** (win%/expectancy per pattern×day_type מ-374 היריות) על תאי ה-Auth
Table — תוכנן, אך דורש שאילתת DB ואג׳רגציה; אפיון נפרד. לא לממש כאן.
