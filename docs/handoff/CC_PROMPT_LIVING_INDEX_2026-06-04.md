# CC PROMPT — אינדקס חי למערכת (`_INDEX.md` פר-ספרייה + `SYSTEM_INDEX.md` + זיהוי "במה משתמשים") · 2026-06-04

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** אישור Michael 2026-06-04. **read-only על קוד** (רק כותב קובצי-אינדקס + סקריפט). אפס שינוי לוגיקה.

## מטרה
אינדקס **מתעדכן** (להריץ מתי שרוצים, לא נכתב ידנית): בכל ספריית-קוד `_INDEX.md` מסודר עם רשימת הקבצים + שורת-תיאור לכל קובץ + **דגל-שימוש** (מי מייבא אותו → לזהות מה בשימוש ומה חשוד-מת), ו-`SYSTEM_INDEX.md` בשורש עם עץ-על + רשימת ה-orphans.

## נקודת-פתיחה — פרוטוטיפ עובד כבר קיים
Cowork כתב והריץ `scripts/gen_index.py` (פרוטוטיפ). תוצאה: **669 קבצים · 107 ספריות · 137 orphans**. הוא בונה import-graph (Python דרך `from/import`; TS/TSX דרך `import ... from`, כולל `@/` ו-relative), מוציא purpose מ-docstring/הערה-ראשונה, ומסמן `✅N` / `▶ entry/test` / `⚠️ orphan?`. **המשימה: לבקר, להקשיח, ולאמת — לא לכתוב מאפס.**

## ⛔ risk surface
- read-only על קוד-המערכת. לכתוב רק `_INDEX.md`/`SYSTEM_INDEX.md`/`scripts/gen_index.py`.
- היקף: `backend/ · frontend/v9/src · bridge/ · scripts/ · sc_study/`. החרגות: `node_modules,__pycache__,.next,.git,dist,build`.

## Phase 1 — אודיט הפרוטוטיפ (diagnose)
הרץ `python3 scripts/gen_index.py`, הדבק את ה-JSON + דגום 3 `_INDEX.md` + ראש `SYSTEM_INDEX.md`. אתר את חולשות ה-import-graph.

## Phase 2 — הקשחה (העיקר: צמצום false-positive ב-orphans)
137 ה-orphans כוללים כנראה הרבה false-positives. תקן את הזיהוי:
- **טעינה דינמית:** `importlib.import_module("...")`, מחרוזות-route, מודולים שנטענים ע"י flag/env (חפש שמות-מודול גם במחרוזות).
- **Frontend entry:** `frontend/v9/src/app/**/page.tsx|route.ts|layout.tsx` = entrypoints (Next.js — לא מיובאים ישירות) → לא orphan.
- **Python:** `import x as y`, re-exports ב-`__init__.py`, ו-`from pkg import submodule`.
- **Registries/plugins:** מודולים שנרשמים ב-decorator/registry בלי import ישיר → סמן `▶ registry` במקום orphan אם מזוהה.
- הוסף עמודות שימושיות: LOC + תאריך-שינוי אחרון (git).
- שמור idempotent (הרצה חוזרת = אותו פלט; אל תסמן את קובצי `_INDEX.md` עצמם).

## Phase 3 — אימות (B1 — anti-tautological, raw)
- **חיובי:** בחר יחס-import ידוע-אמיתי (למשל `s2_inspector.py` מיובא ע"י `aggregator.py`) → הוכח שה-graph תופס אותו (`✅≥1`, לא orphan).
- **שלילי:** בחר קובץ ידוע-בשימוש (`adaptive_stop.py`) → אסור שיסומן orphan. *"if reverted (graph שבור) → הקובץ הזה היה מסומן orphan בטעות."*
- **דגימת-orphans:** בדוק ידנית 5 מתוך רשימת ה-orphan וסווג כל אחד: באמת-מת / false-positive (טעינה דינמית/route). הדבק את ההכרעה. עדכן את ה-heuristic אם נמצא דפוס false-positive חוזר.
- ספירת orphans **אחרי** ההקשחה (צריכה לרדת מ-137).

## Acceptance (✓/✗ + raw)
- [ ] `scripts/gen_index.py` רץ נקי; JSON-summary מודבק (files/dirs/orphans אחרי הקשחה).
- [ ] `_INDEX.md` קיים בכל ספריית-קוד בהיקף + `SYSTEM_INDEX.md` בשורש (raw: `find . -name _INDEX.md | wc -l`).
- [ ] בדיקת חיובי+שלילי עברו (raw) + litmus.
- [ ] 5 orphans נבדקו ידנית וסווגו (raw).
- [ ] idempotent: הרצה שנייה → 0 diff (`git status` נקי אחרי 2 הרצות).
- [ ] commit (סקריפט + אינדקסים) · `git log -1` · **NOT-DONE/DEVIATIONS** (גם "none"). עדכן `STATUS_BOARD.md` בשורה אחת.

## Invariants
read-only על קוד · idempotent · היקף נעול (5 ספריות) · orphan="חשוד, לאמת" לא "למחוק" · אל תיגע בלוגיקה/risk/sc_study ·
Cowork מאמת בלתי-תלוי (ספירת `_INDEX.md`, יחס-import ידוע נתפס, דגימת-orphans).
