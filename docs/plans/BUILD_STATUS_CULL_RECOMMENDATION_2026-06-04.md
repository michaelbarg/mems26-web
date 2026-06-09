# Build Status — המלצת cull (החלפת המשטח הישן) · 2026-06-04

> **סטטוס: פתוח — ממתין להחלטת Michael. לא לבצע מחיקות/עריכת דאשבורד עד אישור.**
> מסמך זה הוא המלצה בלבד; הביצוע בהמשך כצעד נפרד מאושר.

> העיצוב-מחדש (`/build` · `BuildTreeView.tsx`) הומש והוא הופך לעמוד האמיתי. מסמך זה ממליץ
> אילו קבצים מהמשטח הישן למחוק, מה לשמר, ומה לתקן ב-`V9Dashboard`. **המלצה בלבד** —
> הביצוע (מחיקות + עריכת הדאשבורד) הוא צעד נפרד לאישורך, כי `V9Dashboard` הוא משטח רגיש
> (polling floors ב-CLAUDE.md).

## גרף-תלויות (נבדק 2026-06-04, read-only)

```
V9Dashboard.tsx ──(else-branch, שורה 138)── <BuildStatusTab/>   ← המשטח הישן
   BuildStatusTab → SystemSection → PatternRow → ComponentTable(FreshnessPill) → StatusPill
   BuildStatusTab → ReadinessHeader
                                  └── types.ts  ← משותף

BuildPage (/build) ── <BuildTreeView/>   ← המשטח החדש (V2)
   BuildTreeView → types.ts בלבד (מהתיקייה build_status)
```

`BuildStatusTab` מותקן **רק** ב-`V9Dashboard.tsx` (import שורה 13, mount שורה 138, ב-else של
view-toggle). כל שאר קובצי `build_status/` מגיעים דרכו ואינם בשימוש מחוץ לתיקייה — פרט ל-`types.ts`.

## סיווג KEEP / ADAPT / DELETE

| קובץ | סיווג | נימוק |
|---|---|---|
| `build_status/types.ts` | **KEEP** | משותף — נצרך ע"י `BuildTreeView` + `useBuildStatus` + ה-hook. מקור-אמת לסכמה. |
| `build_status/BuildStatusTab.tsx` | **DELETE** | הוחלף ע"י `/build`. מותקן רק בדאשבורד (else-branch). |
| `build_status/SystemSection.tsx` | **DELETE** | נצרך רק ע"י `BuildStatusTab`. `SystemBranch` החדש מחליף. |
| `build_status/PatternRow.tsx` | **DELETE** | יתום אחרי מחיקת `SystemSection`. `BuildTreeView` מימש גרסה inline. |
| `build_status/ComponentTable.tsx` | **DELETE** | כנ"ל (כולל `FreshnessPill`). מומש inline ב-`BuildTreeView`. |
| `build_status/StatusPill.tsx` | **DELETE** | יתום אחרי מחיקת `PatternRow`/`SystemSection`. |
| `build_status/ReadinessHeader.tsx` | **ADAPT → DELETE** | ראה §"לשמר מ-ReadinessHeader". אחרי הפורט — למחוק. |

## לשמר מ-`ReadinessHeader` (לפני מחיקה)

ל-`ReadinessHeader` יש שני אלמנטים שה-`Blocker` החדש עדיין לא מכסה — כדאי לפורט ל-`BuildTreeView`:

1. **שורת-צ'יפים מלאה של כל בדיקות ה-readiness** (`✓ passing` / `⚠ degraded` / `i info`).
   ה-`Blocker` החדש מציג רק את החסם ה-block + degraded. הצ'יפים נותנים תמונת-checklist מלאה.
2. **deep-link `← ראה עסקאות` ל-`/trades`**. ניווט שימושי שאבד במעבר.

המלצה: להוסיף את שניהם ל-`Blocker`/header של `BuildTreeView`, ואז למחוק את `ReadinessHeader`.
(שינוי קטן, additive — לא חוסם את ה-cull.)

## תיקון ב-`V9Dashboard.tsx`

ה-else-branch מרנדר `<BuildStatusTab/>`. שתי אופציות:

- **אופציה A (מומלצת) — Build חי ב-`/build` בלבד:** להחליף את ה-mount בקישור/הפניה ל-`/build`
  (או להסיר את ה-toggle אם הוא קיים רק בשביל Build). יתרון: מקור-אמת אחד, אין כפילות, אין
  סיכון ל-polling כפול. ה-route `/build` כבר עצמאי.
- **אופציה B — להרכיב בדאשבורד:** לרנדר `<BuildTreeView/>` במקום `<BuildStatusTab/>`.
  חיסרון: `BuildTreeView` הוא עמוד-מלא עם header/sticky משלו — לא תוכנן כ-embed; ידרוש התאמה.

**המלצה: A.** Build יחיה ב-`/build`; הדאשבורד יקשר אליו. כך מסירים את כל תת-העץ הישן בבת-אחת
ונמנעים מ-polling כפול מול ה-backend ה-single-worker.

## רצף ביצוע מוצע (לכשתאשר)

1. פורט שורת-הצ'יפים + deep-link מ-`ReadinessHeader` ל-`BuildTreeView`.
2. עריכת `V9Dashboard.tsx` — להחליף `<BuildStatusTab/>` בקישור ל-`/build` (אופציה A).
3. מחיקת 6 הקבצים: `BuildStatusTab`, `SystemSection`, `PatternRow`, `ComponentTable`,
   `StatusPill`, `ReadinessHeader`. **שמירה:** `types.ts`.
4. `tsc --noEmit` + `npm run build` לאימות שאין import שבור (אישור הפעלת build נדרש).
5. עדכון `ROADMAP_TO_LIVE.html` + `STATUS_BOARD.md` (root + solution + verification).

## סיכון
נמוך — תת-העץ הישן מבודד (reachable רק דרך `BuildStatusTab`). הסיכון היחיד הוא import שבור
ב-`V9Dashboard` אחרי המחיקה; מתפוגג ב-tsc/build בשלב 4. אין נגיעה ב-backend/risk-logic.
