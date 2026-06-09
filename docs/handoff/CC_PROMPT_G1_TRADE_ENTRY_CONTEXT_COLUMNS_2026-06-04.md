# CC PROMPT — G1: קיבוע חתכי‑כיול כעמודות queryable (Trades redesign)

**חוזה:** קרא `docs/handoff/CC_HANDOFF_CONTRACT.md` לפני שתתחיל. כל טענת "DONE" =
paste של פקודה + raw output (Pre‑LIVE Rule 5). מבנה הדוח חייב לכלול סעיף **NOT‑DONE**.
מקור‑עיצוב מלא: `docs/handoff/HANDOFF_TRADES_PAGE_REDESIGN_NEXT_2026-06-04.md` §5/§5a/§5b.

**Scope (הוכרע Michael 2026‑06‑04):** G1 בלבד. **אל תיגע ב‑G2–G7** (DEFERRED). אל תיגע
ב‑risk‑logic / polling‑floors / frontend. localhost‑PG בלבד.

---

## 0. הקשר מאומת (כבר נקרא ע"י Cowork — אל תסרוק מחדש, רק אמת בריצה)
- מודל: `backend/v9/db/models/trades.py` `V9Trade` — `cross_context = Column(JsonColumn)`
  מתועד "Cross-system context **at entry time**" (`:53‑54`). **אין** עמודות
  day_type/pattern/killzone נפרדות.
- כתיבה‑בכניסה: `backend/v9/gateway/trading_gateway.py`
  - `_capture_cross_context()` (`:399‑410`) — מצלם את **כל 6 המערכות** מתוך `_system_registry`
    דרך `get_current()`/`current_state`, כולל `killzone_system` (system 6).
  - `_persist_trade()` (`:412‑426`) — `INSERT INTO v9_trades (... cross_context ...)`,
    `json.dumps(cross_context)`.
- נגזרים ב‑runtime: `backend/v9/services/trade_context.py` — `_SYSTEM_REGISTRY_KEYS`
  (`:38‑45`) ממפה killzone→`killzone_system`, day_type→`day_type_machine`,
  pattern→`woodies_system.active_patterns`. `extract_trade_display()` (`:482`) חולץ אותם
  **מ‑ה‑JSON** → לכן אי‑אפשר GROUP_BY ב‑SQL.

---

## 1. ⚠️ VERIFY‑FIRST (חובה לפני כל שינוי קוד — Rule 2)
לפני שמוסיפים עמודה אחת, ענה על השאלה: **מה באמת מאוכלס ב‑`cross_context` בכניסה?**
זה קובע אם G1 הוא "promote JSON→column" (backfillable) או "capture חדש" (write‑at‑entry,
לא‑backfillable). paste raw output של:

```sql
-- כמה מהעסקאות בכלל יש להן snapshot של כל מערכת בכניסה?
SELECT
  count(*)                                                   AS total,
  count(*) FILTER (WHERE cross_context::text LIKE '%killzone_system%')   AS has_killzone,
  count(*) FILTER (WHERE cross_context::text LIKE '%day_type_machine%')  AS has_daytype,
  count(*) FILTER (WHERE cross_context::text LIKE '%woodies_system%')    AS has_woodies
FROM v9_trades;
```
+ הדפס `cross_context` של 2 עסקאות אחרונות (`ORDER BY id DESC LIMIT 2`) כדי לראות את
המבנה בפועל (top‑level dict? רשימת snapshots? מפתחות numeric?).

**שער החלטה (דווח ל‑Michael, אל תכריע לבד):**
- אם `has_killzone`/`has_daytype` ≈ total → הנתון **קיים ב‑JSON** → G1 = promote + **backfill**
  מ‑JSON (היסטוריה ניתנת לשחזור).
- אם ≈ 0 → המערכת **לא רשומה** ב‑`_system_registry` בזמן‑כניסה → זה write‑at‑entry אמיתי:
  קודם לחווט את הרישום (`set_system_reference`), ואז אין backfill להיסטוריה הקיימת. **strategic‑stop ל‑Michael.**

---

## 2. מימוש G1 (רק אחרי שער §1)
מטרה: 3 חתכי‑הכיול ניתנים ל‑`GROUP BY` ב‑SQL, בלי לשבור את ה‑JSON הקיים, בלי סינתזה.

### 2a. עמודות (חוזה‑ממשק §5b — שמות מחייבים)
`backend/v9/db/models/trades.py` — הוסף ל‑`V9Trade`:
```python
day_type_at_entry   = Column(String(20), nullable=True, index=True)   # מקור שותק → NULL
pattern_id_at_entry = Column(String(40), nullable=True, index=True)
session_at_entry    = Column(String(20), nullable=True, index=True)   # killzone/session zone
```
migration אלמביק נפרד (`alembic/versions/`), `nullable=True`, `CREATE INDEX`. אל תשנה עמודות קיימות.

### 2b. אכלוס בכניסה (מקור‑אמת יחיד — מאותו snapshot)
ב‑`trading_gateway.py` בין `_capture_cross_context()` ל‑`_persist_trade()`: חלץ את 3 השדות
**מתוך אותו `cross_context`** שכבר נלכד (אל תקרא מקור שני), בעזרת אותם helpers של
`trade_context.py` (`_systems_blob_at_entry` / `_snapshot_hint`) כדי שהערך **יהיה זהה**
למה שה‑UI מציג היום. מקור שותק/`error` → `None` (לא ""). הוסף את 3 העמודות ל‑INSERT של `_persist_trade`.

### 2c. backfill (רק אם §1 = "קיים ב‑JSON")
סקריפט one‑shot שקורא `cross_context` הקיים וממלא את 3 העמודות לעסקאות ישנות, באותם
helpers. מקור שותק → נשאר NULL. **אל תסנתז.** paste: count לפני/אחרי + 3 דוגמאות.

---

## 3. מפת‑התפרים (SEAM MAP) — "איפה המערכת מתלבשת על מה שחסר"
זהו הסימון שמונע עבודה כפולה: כל שדה חסר ↔ נקודות‑החיבור המדויקות. כל סוכן יודע בדיוק
איפה הקצה שלו מתחבר.

| שדה חסר | יצרן (write‑at‑entry) | אחסון | צרכן |
|---------|----------------------|-------|------|
| `session_at_entry` (killzone) | `trading_gateway.py:~410` (מ‑`killzone_system` snapshot) | עמודה חדשה §2a | G2 `/trades/stats?group_by=killzone` (DEFERRED) · frontend Edge Matrix ציר killzone (היום אפור "pending G1") |
| `day_type_at_entry` | אותו snapshot (`day_type_machine`) | עמודה חדשה | G2 group_by=day_type · Edge Matrix |
| `pattern_id_at_entry` | אותו snapshot (`woodies_system.active_patterns`) | עמודה חדשה | G2 group_by=pattern · Edge Matrix |

**צד‑frontend (סוכן אחר, לא בפרומפט הזה):** עד שהעמודות מאוכלסות, מרנדר "missing — pending G1"
ב‑runtime (Rule 1) + ציר killzone אפור מנוטרל. כשהעמודות נוחתות → מסיר את ה‑gating, אפס UI חדש.

---

## 4. בדיקות (anti‑tautological — חובה)
- טסט: עסקה עם `killzone_system` ב‑cross_context → `session_at_entry` מאוכלס **זהה** ל‑`extract_trade_display` zone.
- טסט litmus: עסקה **בלי** killzone ב‑snapshot → `session_at_entry IS NULL` (לא "", לא ערך מסונתז).
  אם מישהו ירכיב fallback ממקור אחר → הטסט חייב להפוך RED.
- טסט: `GROUP BY day_type_at_entry` מחזיר את אותה התפלגות כמו ספירה ידנית מ‑JSON על אותן שורות.
- אל תשנה טסטים קיימים ל"ירוק". paste מספרי pass/fail גולמיים.

## 5. NOT‑DONE (חובה בדוח)
מה לא נעשה ולמה: G2–G7 (DEFERRED), frontend (סוכן אחר), כל שדה שמקורו שותק ונשאר NULL,
וכל הסתייגות backfill (עסקאות שאין להן snapshot).
