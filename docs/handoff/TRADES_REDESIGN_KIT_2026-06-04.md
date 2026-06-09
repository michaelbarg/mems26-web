# 🧰 ערכת Trades Redesign — START HERE · 2026‑06‑04

מסמך‑אב יחיד שמארגן את הכל. כל סוכן (Cowork / CC / Cursor) קורא **את זה ראשון**, ואז את
הקובץ הרלוונטי לקצה שלו. נועד למנוע סריקה‑מחדש ועבודה כפולה.

---

## 1. ההחלטה (Michael, 2026‑06‑04)
**Frontend שלב‑1 עכשיו + G1 במקביל.** Backend‑first מלא ותכנון‑בלבד נדחו.
- שלב‑1 frontend = כל הערך הנראה בלי לגעת ב‑DB/risk/polling.
- G1 = הוצאת חתכי‑הכיול מ‑`cross_context` JSON לעמודות queryable (ברובו backfillable).
- G2–G7 = follow‑up, **לא בונים עכשיו**.

## 2. סדר ביצוע
| # | מנה | בעלים | קובץ‑עבודה | מצב |
|---|-----|-------|------------|-----|
| 0 | **VERIFY‑FIRST**: לאמת מול PG מה מאוכלס ב‑`cross_context` | CC | פרומפט G1 §1 | ⛔ שער לפני קוד |
| 1 | **G1**: עמודות `*_at_entry` + אכלוס + backfill | CC | `CC_PROMPT_G1_TRADE_ENTRY_CONTEXT_COLUMNS_2026-06-04.md` | מוכן לשליחה |
| 2 | **Frontend שלב‑1** (במקביל ל‑1) | סוכן‑Frontend | `CC_PROMPT_FRONTEND_PHASE1_TRADES_REDESIGN_2026-06-04.md` | מוכן לשליחה |
| 3 | **G2–G7** | — | DEFERRED | ⛔ אחרי 1+2 |

G1 ו‑Frontend רצים **במקביל** כי הם מתחברים דרך חוזה‑ממשק קבוע מראש (§4) — אף צד לא ממתין לשני.

## 3. בעלות (אנטי‑כפילות)
- Frontend‑1 = ADAPT מ‑`PatternPerformanceStrip.tsx`, **לא רכיב אגרגציה חדש**.
- G1 = אכלוס מ‑אותו `cross_context` snapshot, **לא מקור שני**.
- G2–G7 = ⛔ אסור להתחיל עד ש‑G1+Frontend‑1 ינחתו.

## 4. חוזה‑ממשק G1 ↔ Frontend (נקודת‑החיבור)
שמות‑שדות מוסכמים **מראש** → כשהעמודות נוחתות, ה‑frontend רק מחליף "missing" בשדה אמיתי, אפס rework:
- עמודות DB: `day_type_at_entry`, `pattern_id_at_entry`, `session_at_entry` (killzone).
- מקור שותק → **NULL**, אפס סינתזה (Rule 1).
- **סימון חי ב‑runtime:** עד G1, ה‑frontend מרנדר חיתוך killzone/day_type כ‑**"missing — pending G1"**
  + ציר Edge Matrix אפור מנוטרל. זה הסיגנל שאומר לכל מערכת שהדאטה חסרה — לא מזויף.

## 5. ממצא‑מפתח מאומת (Rule 2 — מתקן הנחה קודמת)
"killzone‑at‑entry לא נשמר" **הופרך בקוד.** `trading_gateway._capture_cross_context()` (`:399‑410`)
מצלם את כל 6 המערכות (כולל `killzone_system`) ל‑`cross_context` JSON בכניסה ושומר ב‑INSERT (`:414`);
`trade_context.py` חולץ משם ב‑runtime. ⇒ הנתון **קבור ב‑JSON, לא queryable** — ולכן ברובו **backfillable**.
לכן שער §0 (VERIFY‑FIRST) קודם לכל הוספת עמודה.

## 6. Invariants (קשיחים)
- localhost‑PG בלבד · לא נוגעים ב‑risk‑logic / polling‑floors / DB מעבר ל‑G1.
- כל "חסר" = NULL + "pending Gx" ב‑UI, **לא** סינתזה.
- smallest correct change · regression test לכל תיקון · כל "DONE" = raw output (Rule 5).
- אל תריץ dev‑server / start_all.sh בלי בקשת Michael.

## 7. כל הקבצים בערכה
**מסמכי‑עבודה (פרומפטים):**
- `CC_PROMPT_G1_TRADE_ENTRY_CONTEXT_COLUMNS_2026-06-04.md` — G1 (verify‑first + seam‑map + tests).
- `CC_PROMPT_FRONTEND_PHASE1_TRADES_REDESIGN_2026-06-04.md` — Frontend שלב‑1 (8 פריטים מסודרים).

**עיצוב + הקשר:**
- `HANDOFF_TRADES_PAGE_REDESIGN_NEXT_2026-06-04.md` — הנדאוף מלא (§5 החלטה · §5a בעלות · §5b חוזה).
- `docs/plans/TRADES_PAGE_REDESIGN_2026-06-03.md` — מסמך‑עיצוב + gap‑list G1–G7 מלא.
- `docs/plans/TRADES_PAGE_REDESIGN_MOCKUP_2026-06-03.html` — mockup סטטי.
- `docs/plans/TRADES_PAGE_PROTOTYPE_2026-06-03.html` — prototype אינטראקטיבי (tokens אמיתיים).

**מעקב (source of record):**
- `docs/plans/STATUS_BOARD.md` — לוג 2026‑06‑04 (החלטה + ממצא G1 + פרומפט).
- `docs/plans/ROADMAP_TO_LIVE.html` — item Trades redesign (scope הוכרע).

## 8. הצעד הבא של Michael
לשלוח את שני הפרומפטים (G1 + Frontend) — הם רצים במקביל. G1 עוצר ב‑שער §0 לדיווח לפניך
על מה שמאוכלס ב‑`cross_context` (כי זה קובע אם יש backfill או strategic‑stop).

## 9. פסקת‑פתיחה לסוכן (העתק‑הדבק)
> אתה ממשיך את עיצוב‑המחדש של עמוד Trades. **קרא קודם** את מסמך‑האב
> `docs/handoff/TRADES_REDESIGN_KIT_2026-06-04.md` — הוא מכיל את ההחלטה, סדר‑הביצוע, חלוקת‑הבעלות,
> חוזה‑הממשק וה‑Invariants. אחר כך עבוד **רק** לפי הפרומפט של הקצה שלך:
> `CC_PROMPT_G1_TRADE_ENTRY_CONTEXT_COLUMNS_2026-06-04.md` (backend/G1) **או**
> `CC_PROMPT_FRONTEND_PHASE1_TRADES_REDESIGN_2026-06-04.md` (frontend שלב‑1). כללי‑עבודה: חוזה
> `CC_HANDOFF_CONTRACT.md` · diagnose‑first ו‑verify‑first (G1 §0 הוא שער חוסם — דווח ל‑Michael לפני
> הוספת עמודה) · smallest correct change · regression test לכל תיקון · **אל תיגע ב‑G2–G7** (DEFERRED),
> ב‑risk/polling/DB מעבר ל‑scope שלך · כל "חסר" → NULL + "pending Gx" ב‑UI, **לא** סינתזה · אל תריץ
> dev‑server/start_all.sh בלי בקשה · כל "DONE" = paste של פקודה + raw output (Rule 5), והדוח כולל
> סעיף **NOT‑DONE**. כשתסיים — עדכן `STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html` (פריט Trades redesign)
> עם finding+fix+verification, כדי שניתן יהיה להצליב מול התוכנית כאן.

## 10. צ'ק‑ליסט קבלה — מה Cowork יצליב בסוף (acceptance)
הצלבה בלתי‑תלויה מול raw output, לא מול הצהרות:
- [ ] **G1 §0 verify** — paste של 2 השאילתות + ספירות `has_killzone/has_daytype/has_woodies`, ודיווח‑שער ל‑Michael לפני קוד.
- [ ] **G1 עמודות** — `day_type_at_entry`/`pattern_id_at_entry`/`session_at_entry` קיימות (`\d v9_trades`), `nullable`, מאונדקסות; migration קיים.
- [ ] **G1 אכלוס=מקור‑אמת** — הערך זהה ל‑`extract_trade_display` (אותו snapshot); טסט litmus: אין killzone → `NULL` (לא "" ולא מסונתז → RED אם fallback).
- [ ] **G1 backfill** — count לפני/אחרי + 3 דוגמאות (רק אם §0=קיים‑ב‑JSON).
- [ ] **Frontend ET‑date** — עסקה גבולית UTC↔ET נופלת ביום ET; revert→RED.
- [ ] **Edge Matrix** — group_by=system/pattern/direction = ספירה ידנית; day_type/killzone מרונדרים **gated "pending G1"** (לא ערך מזויף).
- [ ] **exec‑mode** — צורך את `auxStatus.liveEligible` הקיים, אפס לוגיקת‑gating חדשה.
- [ ] **Scratch/BE** — דלי מפורש, לא 0.
- [ ] **גבולות נשמרו** — diff לא נוגע ב‑risk/polling/DB‑מעבר‑ל‑G1; G2–G7 לא נבנו.
- [ ] **תיעוד** — STATUS_BOARD + ROADMAP עודכנו עם finding+fix+verification.
