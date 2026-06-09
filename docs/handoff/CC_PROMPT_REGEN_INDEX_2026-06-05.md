# CC — רענון האינדקס בכל הספריות · 2026-06-05

לפי CLAUDE.md §Codebase Index Protocol (חדש). האינדקס stale (4/6) למרות שינויי-היום.

## מה לעשות
1. הרץ: `python3 scripts/gen_index.py` — מייצר `_INDEX.md` בכל ספריית-קוד + root `SYSTEM_INDEX.md`.
2. ודא **כל ספריית-קוד** (backend + frontend) קיבלה `_INDEX.md` עדכני; orphans זוהו.
3. ודא ש-`SYSTEM_INDEX.md` משקף את הקבצים הקריטיים — בפרט: `backend/main.py` (entrypoint אמיתי,
   subscribe 5min→day_type) מובחן מ-`backend/v9/main.py`; `wrappers.py` DayTypeSystem מסומן
   dead-path אם עדיין קיים.
4. commit את האינדקס המרוענן בנפרד (`chore(index): regenerate ...`).

## VERIFY (raw output)
- `python3 scripts/gen_index.py` → paste הסיכום (כמה קבצים/ספריות/orphans).
- `git status --short | grep _INDEX | wc -l` → מספר ה-_INDEX שעודכנו.
- `grep -c "backend/main.py\|day_type_machine" SYSTEM_INDEX.md` → מופיע.
- NOT-DONE: כל ספרייה שלא נוסרקה / orphan שלא הוסבר.

קל וזריז — תשתמש באינדקס מכאן והלאה לאיתור-קבצים (לא grep עיוור).
