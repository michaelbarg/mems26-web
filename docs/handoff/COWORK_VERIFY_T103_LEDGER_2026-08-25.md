# אימות T-103 · Candidate Ledger — cowork

**מאת:** cursor-agent · **אל:** cowork-dev  
**מבצע:** cc-macbook לפי `docs/handoff/CC_WORKORDER_T103_LEDGER_2026-08-25.md`  
**אתה:** קריאה-בלבד + חוק-5. **אל תבנה, אל תדליק דגל, אל תריסטארט.**

תוכנית: `docs/plans/MAXIMIZATION_INFRA_EXECUTION_PLAN_2026-08-24.md`  
חוזה: `docs/spec_authority/CANDIDATE_LEDGER_CONTRACT.md`

---

## מתי להתחיל

אחרי ש-cc דוחף וכותב ב-`LIVE_CHANNEL` שיש דוח:

`docs/reports/CC_T103_LEDGER_BUILD_2026-08-25.md`

עד אז: אל תאשר. "should be fixed" בלי פקודה+פלט = לא אומת.

---

## מה לאמת (✓/✗ פר-פריט, command+raw)

1. **דגל כבוי.** `CANDIDATE_LEDGER_V1` לא ב-`.env`, או `=0`.  
   `python3 -c "from backend.v9.services.candidate_ledger import enabled; print(enabled())"` → `False`.
2. **אין מקור שלישי.** אין טבלה `v9_candidate_events`. אין JSONL שני. רק `gateway_decisions.jsonl` + עמודות nullable על `v9_five_min_setups` / `v9_woodies_signals`.
3. **024.** העמודות קיימות, nullable, היסטוריה `candidate_id IS NULL` לכולן עד שהדגל דלוק. הרצה שנייה skip.
4. **Archive.** `v9_woodies_signals_archive` לא שונה. `session_boundary` עדיין מעתיק רשימת-עמודות מפורשת.
5. **פילטר UI.** `/api/v9/gateway/decisions` לא סופר `DETECTED`/`EMIT_DECISION` כ-block/fire. counts על fixtures ישנים לא זזו.
6. **pytest isolation.** אחרי הסוויטה: אפס שורות חדשות ב-`~/SierraChart_Data/v9_export/gateway_decisions.jsonl` החי, ואפס `candidate_id` חדש ב-DB הפרוד מטסטים.
7. **כשל כתיבה לא נוגע בירי.** טסט/קריאה שמוכיחים ש-`route_setup` מחזיר אותו פסק כשהכותב זורק.
8. **RESOLVED.** סקריפט EOD קיים, idempotent, סשן NOT_JUDGEABLE לא נזרק. לא רץ מתוך `route_setup`.
9. **לא הודלקה התנהגות-ירי.** diff לא נוגע בשערי-גודל/כיוון/op=EXIT.

---

## פסק

- הכל ✓ + raw מודבק → כתוב `GO` ב-LIVE_CHANNEL והחזר ל-cursor לאימות בלתי-תלוי.
- פריט אחד ✗ → `NO-GO` עם file:line. cc מתקן. אל תעבור ל-T-100.

Cursor לא מקבל "עבר" בלי שהדבקת פקודה+פלט (חוק-5 / טעות-9).
