# CC PROMPT — Build-Status cull (אופציה A, מאושר Michael 2026-06-04) · port→swap→delete · 2026-06-04

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** **Frontend-only.** מקור: `docs/plans/BUILD_STATUS_CULL_RECOMMENDATION_2026-06-04.md` (גרף-תלויות אומת ע"י Cowork).
**אישור Michael: אופציה A** — Build חי ב-`/build` בלבד; הדאשבורד מקשר אליו. מסיר את המשטח הישן ומונע polling כפול מול ה-backend ה-single-worker.

## מצב מאומת (Cowork, raw)
- `BuildStatusTab` מותקן **רק** ב-`V9Dashboard.tsx` (import `:13`, mount `:138` ב-else של ה-view-toggle, בתוך `<div className="flex-1 min-h-0">`).
- `/build` = `app/build/page.tsx` → `<BuildTreeView/>` — עצמאי, לא תלוי ב-`build_status/` פרט ל-`types.ts`.
- 6 קבצים reachable **רק** דרך `BuildStatusTab`: `BuildStatusTab` · `SystemSection` · `PatternRow` · `ComponentTable` · `StatusPill` · `ReadinessHeader`. `types.ts` = **KEEP** (משותף ל-BuildTreeView+hook).

## ⛔ risk surface — מה אסור
- **אל תיגע ב-polling-floors** (CLAUDE.md) — אף interval/hook ב-`V9Dashboard.tsx` לא משתנה. השינוי היחיד בדאשבורד = תוכן ה-else-branch (`:138`).
- אל תיגע ב-`types.ts`, ב-`useBuildStatus`, ב-`BuildTreeView` (פרט לתוספת ה-port §1), ב-backend.
- **אל תריץ** `npm run dev`/`next dev`/`start_all` (CLAUDE.md Service Bring-Up). אימות = `tsc --noEmit` (+ `npm run build` רק אם Michael מאשר).

## Phase 1 — port מ-ReadinessHeader ל-BuildTreeView (additive, לפני מחיקה)
ל-`ReadinessHeader` שני אלמנטים שה-`Blocker` החדש לא מכסה — לפורט ל-`BuildTreeView`:
1. **שורת-צ'יפים מלאה** של בדיקות ה-readiness: `passing` (✓), `degraded` (⚠), `info` (i) — מקור `readiness.checks` (`ReadinessHeader.tsx:65-69`, רינדור `:133-174`). ה-`Blocker` היום מציג רק את החסם ה-block + degraded; הצ'יפים נותנים checklist מלא.
2. **deep-link `← ראה עסקאות` ל-`/trades`** (`ReadinessHeader.tsx:185-198`).
- שניהם additive ל-header/Blocker של `BuildTreeView`, קוראים מאותו `readiness` schema (`types.ts`) — **0 שינוי backend, Rule 1** (חסר→לא להציג, לא לסנתז).

## Phase 2 — swap ב-V9Dashboard (smallest change)
- ב-else-branch (`:137-139`) החלף את `<BuildStatusTab/>` בקישור/הפניה ל-`/build` (Next `<Link href="/build">` או redirect). אם ה-view-toggle קיים **רק** בשביל Build — מותר לפשט אותו לקישור; אם יש לו שימוש אחר — **השאר את ה-toggle, רק החלף את התוכן** (B6: אם לא ברור — לעצור ולדווח).
- הסר את ה-import `:13`. **אל תיגע בשום שורת polling/hook אחרת.**

## Phase 3 — delete (אחרי ש-tsc ירוק על 1+2)
מחק 6 קבצים: `BuildStatusTab.tsx` · `SystemSection.tsx` · `PatternRow.tsx` · `ComponentTable.tsx` · `StatusPill.tsx` · `ReadinessHeader.tsx`. **שמור** `types.ts`.

## Acceptance (✓/✗ + raw)
- [ ] Phase-1 port מודבק (diff) — צ'יפים + deep-link מופיעים ב-BuildTreeView; קוראים מ-`readiness.checks` (0 סינתזה).
- [ ] Phase-2 — `V9Dashboard.tsx` else-branch מקשר ל-`/build`; import `:13` הוסר. **raw: `git diff` של V9Dashboard מראה 0 שינוי בכל שורת polling/interval/hook.**
- [ ] Phase-3 — 6 הקבצים נמחקו, `types.ts` קיים. raw: `ls build_status/`.
- [ ] **litmus מבני:** `grep -rn "BuildStatusTab\|SystemSection\|StatusPill\|ReadinessHeader" frontend/v9/src` = **0** imports (פרט להערות). `grep -rn "build_status/PatternRow\|build_status/ComponentTable"` = 0 (BuildTreeView מממש inline). *"if a broken import remains → tsc RED."*
- [ ] **`tsc --noEmit`** — 0 שגיאות **חדשות** (2 pre-existing מותרות: `PriceDebugConsole.tsx:90`, `api.ts:47`). raw.
- [ ] עדכון `ROADMAP_TO_LIVE.html` + `STATUS_BOARD.md` (root+solution+verification). · `git log -1` · **NOT-DONE/DEVIATIONS** (גם "none").

## Invariants
Frontend-only · **0 שינוי polling-floors / backend / risk** · types.ts=KEEP · port-then-delete (אל תמחק לפני שה-port + tsc ירוקים) ·
אל תריץ dev/start_all · Cowork מאמת בלתי-תלוי (grep 0-imports + tsc + diff שאין נגיעת-polling ב-V9Dashboard).
