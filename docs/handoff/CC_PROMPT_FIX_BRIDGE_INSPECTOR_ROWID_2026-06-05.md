# CC PROMPT — B-11: bridge_inspector `ORDER BY rowid` שובר על Postgres → Build-Status OFFLINE שקרי · 2026-06-05

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** **bugfix read-path בלבד — אפס שינוי trading/risk/ingest.** אומת ע"י Cowork.

## הבאג
Build-Status מראה כל 8 הזרמים `no_data` + Bridge "run off / OFFLINE" — **למרות שהגשר דוחף מצוין** (`/tmp/bridge.err.log`: push#50, errors≈0, last_push_age=1s). המערכת עובדת — **הדאשבורד משקר.**
שורש: `backend/v9/systems/build_status/bridge_inspector.py` שורות **82** (`_check_stream`) ו-**204** משתמשות ב-
```python
SELECT {ts_col} FROM {table} ORDER BY rowid DESC LIMIT 1
```
`rowid` הוא pseudo-column של **SQLite בלבד**. ב-Postgres זה זורק `column "rowid" does not exist` → `_check_stream` נופל ל-`except` → `status="ERROR"`/DEAD לכל זרם → כל הזרמים `no_data`, Bridge מסומן OFFLINE. רגרסיית PG-migration (SQLite-ism ששרד).

## ⛔ risk surface
read-path/display בלבד. אל תיגע ingest/risk/sc_study/לוגיקת-trading. localhost-PG.

## Phase 1 — diagnose (הדבק raw)
1. הדבק את `bridge_inspector.py` סביב 80–86 ו-202–206 (שתי השאילתות).
2. **הוכח את הכשל על PG:** הרץ מול ה-DB `SELECT ts FROM v9_bars_5min ORDER BY rowid DESC LIMIT 1;` → הדבק את שגיאת ה-`rowid`. ואז `... ORDER BY ts DESC LIMIT 1;` → מחזיר שורה.
3. **סריקת-אחים (Rule 3):** `grep -rn "rowid" backend/v9 --include=*.py` — ודא שאלו 2 המקומות היחידים ב-נתיבי-קריאה. (`safe_writer.lastrowid` שונה — ערך-החזרה של INSERT, **אל תיגע**.)

## Phase 2 — תיקון (smallest correct)
בשני המקומות: `ORDER BY rowid DESC` → **`ORDER BY {ts_col} DESC`** (הכי-עדכני לפי עמודת-הזמן — תקין ב-PG ו-SQLite, וגם נכון סמנטית: ה-freshness רוצה את הבר האחרון לפי ts, לא לפי insert-order).

## Phase 3 — אימות (B1 anti-tautological, raw)
- **טסט:** מול טבלה עם שורות (PG), `_check_stream` מחזיר את ה-ts האחרון ו-status לא-ERROR. *"if reverted (`ORDER BY rowid`) → RED: PG זורק → ERROR/DEAD."*
- **end-to-end:** הרץ `/api/v9/build/pattern-status` (או fixture) כשהגשר דוחף → הזרמים שיש להם דאטה טרייה מציגים `present=true`/FRESH (לא no_data). הדבק raw (לפני/אחרי).

## Acceptance (✓/✗ + raw)
- [ ] Phase-1: 2 השאילתות + הוכחת כשל-rowid על PG + grep-אחים (2 מקומות, lastrowid לא נגוע).
- [ ] תיקון בשני המקומות (diff).
- [ ] טסט + litmus revert→RED (raw).
- [ ] `pattern-status` מראה זרמים present כשיש דאטה (raw).
- [ ] `git log -1` · עדכון `STATUS_BOARD.md` (B-11: root=rowid SQLite-ism · fix=ORDER BY ts · verification) · **NOT-DONE/DEVIATIONS**.

## Invariants
read-path bugfix · smallest-correct · אל תיגע lastrowid/ingest/risk/sc_study · localhost-PG · No silent failures ·
Cowork מאמת בלתי-תלוי (Chrome→`/api/v9/build/pattern-status` מראה present + grep 0 `ORDER BY rowid` נותרו).
