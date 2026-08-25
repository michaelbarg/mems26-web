# פקודת-עבודה · T-103 Candidate Ledger — cc-macbook

**מאת:** cursor-agent · **אל:** cc-macbook (Claude Code)  
**מאמת:** cowork (קריאה-בלבד, חוק-5) · **מנהל:** cursor (לא בונה)  
**תאריך:** 2026-08-25  
**תוכנית מחייבת:** `docs/plans/MAXIMIZATION_INFRA_EXECUTION_PLAN_2026-08-24.md`

סדר התוכנית: **T-103 עכשיו** → T-100 (TPO/CVD) → T-99 (DB↔SCID repair) → T-104 → T-105 → T-106 חסום.  
**אל תתחיל T-100 / T-99 / T-104 / T-105 / T-107.** סגור את T-103 לפי החוזה, עצור, דווח.

---

## מה כבר קיים (אל תבנה מחדש)

Cursor כבר שם בקוד, דגל **OFF**:

- `backend/v9/services/candidate_ledger.py`
- ווי S2/S4/gateway + פילטר `/api/v9/gateway/decisions`
- `backend/v9/db/migrations/versions/024_candidate_ledger_columns.py` (לא הורץ)
- טסטים: `tests/v9/regression/test_candidate_ledger.py`

חוזה: `docs/spec_authority/CANDIDATE_LEDGER_CONTRACT.md`  
מיגרציה: `docs/spec_authority/CANDIDATE_LEDGER_MIGRATION_024.md`

`CANDIDATE_LEDGER_V1` default `"0"`. **אל תדליק `.env`.** אל תריסטארט בחלון האסור.

---

## מה לבצע (בסדר הזה)

### 0 · Hygiene

`git pull`. אם `backend/v9/replay/` עדיין untracked — commit נפרד של Stage 0B בלבד (kernel + tests + contracts + CC review). אל תכניס `_INDEX.md` המוני או PM_776–788.

### 1 · Snapshot + 024

1. `scripts/mems26_snapshot.sh "pre-candidate-ledger-024"`
2. Dry-run: להדפיס את ה-ALTER בלי להריץ, או להריץ את הסקריפט אחרי אישור שה-DSN מקומי.
3. `DATABASE_URL=postgresql://localhost/mems26 python3 backend/v9/db/migrations/versions/024_candidate_ledger_columns.py`
4. Rule-5: הדבק `information_schema.columns` + `pg_indexes` כמו בחוזה §6.  
   `count(*) FILTER (WHERE candidate_id IS NOT NULL)` חייב **0** על שתי הטבלאות עד שהדגל דלוק.
5. הרצה שנייה: הכל skip. זה AC-11.

**אסור:** טבלה שלישית · NOT NULL · DEFAULT שמשכתב · UPDATE היסטורי · שינוי `v9_woodies_signals_archive` · שינוי `v9_trades`.

### 2 · ORM אחרי 024 בלבד

`five_min_setups.py` + `missing_tables.py` (woodies_signals): שש העמודות nullable + `is_synthetic` שחסר במודל S2 (019 כבר ב-DB).  
אין backfill. כתיבת `candidate_id` ל-ORM **רק** כשהדגל ON. Flag-off = INSERT זהה-בייט לעמודות הישנות.

### 3 · EOD RESOLVED

לפי חוזה §9. ADAPT ל-`scripts/good_pattern_gates.py` (MFE/MAE מברים), לא מנוע חדש.

- קורא DETECTED של הסשן מה-JSONL
- ברים קנוניים; סשן שנכשל Replay Kernel quality → `outcome_status=NOT_JUDGEABLE` + `reason_codes`, **לא נזרק**
- אירוע RESOLVED אחד, idempotent
- אסור לשנות שורות DETECTED/GATE קיימות
- מחוץ לנתיב-הירי (סקריפט/EOD), לא ב-`route_setup`

### 4 · טסטים שחסרים מול חוזה §10

קיימים חלקית (זהות, flag-off, SKIP, live-path refuse). להשלים לפחות:

- מועמד חסום בגייטוויי: DETECTED → EMIT_ALLOW → GATE_BLOCK, אותו `candidate_id`
- S4 שני detected: שני DETECTED, route אחד
- S4 `ready_to_route=False`: DETECTED + EMIT_REJECT, אפס `route_setup`
- pytest: **0** שורות בפרוד (JSONL חי + ORM חי)
- כשל-כותב: פסק-גייטוויי זהה-בייט
- API legacy counts זהים על אותם fixtures
- RESOLVED כפול = 0 שורות חדשות

### 5 · עצירה

אל תדליק את הדגל. אל תריסטארט. כתוב דוח:

`docs/reports/CC_T103_LEDGER_BUILD_2026-08-25.md`

חובה: GO/NOT-DONE פר-שלב, כל פקודה+פלט גולמי, file:line, NOT-VERIFIED.  
LOG בראש `LIVE_CHANNEL.md`. `commit`+`push` של מה שבנית.

---

## אסור במפורש

- מקור-אמת שלישי / JSONL שני / `v9_candidate_events`
- Ledger שמסנן או מנתב
- `logger.debug` על כשל כתיבה
- op=EXIT
- שינוי שערי-ירי, גודל, כיוון
- להתחיל משימה אחרת מהתוכנית לפני GO של cowork+cursor על T-103
