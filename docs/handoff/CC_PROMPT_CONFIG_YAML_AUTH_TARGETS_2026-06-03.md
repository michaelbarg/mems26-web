# CC PROMPT — Externalize Auth-Matrix + Targets/Stop tables to YAML (Option A, calibration flexibility) · 2026-06-03

**פעל לפי `CC_HANDOFF_CONTRACT.md`.** רץ **אחרי** שער ה-audit (`CC_PROMPT_PRE_SHADOW_DASHBOARD_DATA_AUDIT`) שמאמת את הערכים הנוכחיים.
**אישור Michael 2026-06-03: Option A (YAML).** עיצוב מלא: `docs/plans/CONFIG_EXTERNALIZATION_DESIGN_2026-06-03.md`.

## מטרה (הורחב — Michael 2026-06-04: stop+exits+contracts כולם גמישים)
להפוך **שלוש** קבוצות-risk-surface מ-const-dict-בקוד ל-**YAML config** הניתן לכיול בלי redeploy:
- `auth_table_v1.py::_AUTH_TABLE_V1` (70 תאים: pattern × day-type × tier → verdict + **חוזים/sizing**) → דרישה: כמות-חוזים.
- `targets_table.py::_TARGETS` (פר day-type: T1/T2/T3 R-multiples + **time-stop** + sizing/contracts) → דרישה: יציאות.
- **`five_min/adaptive_stop.py` (+ S4 layered-stop) — פרמטרי ה-stop:** structural-anchor offsets, ATR-cap multipliers (`_FLOOR_ATR_K` וכו'), floor ticks → דרישה: ה-stop. **(נוסף 2026-06-04.)**
- **+ `pattern_dispatcher.py:47 min_r_t1_threshold`** (כרגע 0.0 קשיח/no-op) → להוציא ל-config (סוגר residual #3 של P0-2).

## עיקרון-על: מהלך מכני, **התנהגות זהה לחלוטין**
זו הוצאה-לקובץ, **לא** שינוי-ערכים. כל שינוי-ערך הוא risk-logic → strategic-stop + Michael, **לא** כאן.
חובה להוכיח: הערכים שנטענים מ-YAML **זהים byte-for-byte** ל-const-dict הנוכחי.

## פעולות
1. **חלץ ל-YAML:** `config/auth_matrix.yaml` + `config/targets.yaml` + **`config/stop_params.yaml`** (פרמטרי adaptive_stop + S4 layered + `min_r_t1_threshold`), שמשחזרים בדיוק את הקבועים הנוכחיים (כולל aliases, verdict, no_trade, trail flags).
2. **Loader עם fallback (לא-הרסני):** `auth_table_v1.py`/`targets_table.py`/`adaptive_stop.py`+`pattern_dispatcher.py` הופכים ל-loader שקורא YAML; **אם הקובץ חסר/לא-תקין → נופל חזרה לקבוע הנוכחי** + `logger.warning` (לא silent). הקבועים נשארים בקוד כ-fallback.
3. **Schema-validation בטעינה:** מבנה + טיפוסים + שלמות (כל 70 התאים; כל ה-day-types). config לא-תקין → דחייה + fallback + warning.
4. **תקרות-קשיחות (risk guardrails):** `contracts ≤` ה-global max-contracts (אתר את הערך), R-multiples בטווח שפוי (>0, ≤ תקרה). ערך שחורג → נדחה, לא נטען.
5. **ממשל:** ה-spec `docs/spec_authority/S2_AUTH_TABLE_V1.md` נשאר baseline מאושר; הוסף הערה ש-YAML הוא הערך הפעיל, ושינוי-ערך = גרסה חדשה + אישור Michael. git עוקב אחרי ה-YAML.
6. **(אופציונלי, מאחורי דגל)** endpoint reload לטעינה-מחדש בלי restart — אם פשוט; אחרת דחה.

## Acceptance (✓/✗ + raw)
- [ ] **round-trip equality:** טסט שמוכיח `load_from_yaml() == _AUTH_TABLE_V1`, `== _TARGETS`, **ו-stop-params == הקבועים הנוכחיים** (deep-equal, raw).
- [ ] schema-validation דוחה config פגום (טסט) → fallback לקבוע + warning (לא silent).
- [ ] תקרת-חוזים נאכפת (טסט: contracts מעל max → נדחה); stop-params בטווח שפוי.
- [ ] `min_r_t1_threshold` נטען מ-config (לא 0.0 קשיח) — אם config חסר → fallback לערך הנוכחי.
- [ ] 0 שינוי בערכי-מסחר בפועל (deep-equal מוכיח). [ ] regression ירוק · commit · `git log`.

## Invariants
localhost-PG בלבד · ❌ לא Render/Upstash/prod-PG · **אסור לשנות ערך auth/target** (רק להוציא לקובץ) · No silent failures · const-dict נשאר fallback · Cowork מאמת בלתי-תלוי (בדגש: round-trip equality + שאף ערך לא זז).
