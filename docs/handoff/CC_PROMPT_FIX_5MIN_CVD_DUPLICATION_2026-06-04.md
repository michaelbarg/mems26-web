# CC PROMPT — נרות 5-דקות + cumulative_delta כפולים / סשן-אתמול שגוי (Sierra=מקור-אמת) · 2026-06-04

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** **diagnose-first מחייב — CC כבר נכשל שעות על באג זה כי תיקן נתיב מת.** Cowork ביצע RCA עצמאי; קרא אותו לפני שתיגע בקוד.
**source-of-truth: Sierra.** הערכים הנכונים (RTH 2026-06-04): TPO VAH=7604 · POC=7578.25 · VAL=7552.50 · IB 7570.50/7556.13/7541.75. ה-chart שלנו חייב להיות זהה לטבלת Sierra.

## ⛔ אל תבזבז זמן על הנתיב המת (אומת ע"י Cowork)
`bar_ingestion.ingest_bar()` הוא **no-op** (`bar_ingestion.py:60` `return True`; כל הקוד שכותב ל-DB אחריו **dead/unreachable**). לכן `bar_aggregator_5min.py:179` **לא כותב כלום ל-DB**. **אל תיגע שם — זה לא הכפילות.** (זה ככל הנראה מה ש-CC ניסה קודם.)

## השורש האמיתי (RCA של Cowork — לאמת מול ה-DB לפני תיקון)
**שתי טבלאות 5-דקות שה-chart ממזג:**
1. `v9_bars_5min` — נכתב ב-`bars.py::post_bars_5min` מ-Sierra 5min.json, **עם RTH gate** (`_is_within_rth`, 09:30–16:00 ET).
2. `v9_bars_5min_woodies` — נכתב ב-`woodies_system.py:539 _persist_bar`, **בלי RTH gate** → כותב גם overnight/globex.
3. ה-chart `bars_5min_history.py:_fetch_bars_5min` (`:59-90`) ממזג את שתיהן ומדדפ לפי **`str(ts)` בלבד**. תחת Postgres `ts` חוזר כ-`datetime`; אם שני הנתיבים כתבו את אותו רגע ב-TZ/פורמט שונה במשהו → `str()` שונה → **דדופ נכשל → נרות כפולים**.
4. מסנן-הסשן (`:94-123`) משווה `datetime` naive (מ-`str(ts)`) מול ET wall-clock — **שביר מול PG/UTC** → זליגת overnight/אתמול + אנומליית ציר ("01:36" מול 09:00).

## Phase 1 — אבחון מול ה-DB (diagnose-first, הדבק raw — אל תתקן עד שזה מודבק)
```sql
-- (a) האם v9_bars_5min עצמה כפולה?
SELECT ts, symbol, COUNT(*) FROM v9_bars_5min GROUP BY ts,symbol HAVING COUNT(*)>1 ORDER BY ts DESC LIMIT 10;
-- (b) חפיפת רגעים בין שתי הטבלאות עם פורמט-ts שונה (השורש החשוד):
SELECT a.ts AS ts_5min, w.ts AS ts_woodies
FROM v9_bars_5min a JOIN v9_bars_5min_woodies w
  ON a.ts::timestamptz = w.ts::timestamptz AND a.ts::text <> w.ts::text
ORDER BY a.ts DESC LIMIT 20;
-- (c) האם woodies מכיל overnight (מחוץ ל-RTH) שזולג ל-chart?
SELECT MIN(ts), MAX(ts), COUNT(*) FROM v9_bars_5min_woodies WHERE ts::timestamptz > NOW()-INTERVAL '1 day';
-- (d) ts dtype בפועל (PG datetime?)
SELECT ts, pg_typeof(ts) FROM v9_bars_5min LIMIT 1;
```
הדבק תוצאות + הכרע: הכפילות היא **בדאטה** (חפיפת-טבלאות עם ts שונה) או **ברינדור** (merge/דדופ). הדבק 2-3 נרות שמופיעים כפול + ה-ts של כל אחד מ-2 הטבלאות.

## Phase 2 — תיקון (smallest correct, Sierra=truth, Rule 1)
לפי מה ש-Phase-1 הוכיח (אל תנחש):
- **נרמול ts בדדופ:** במיזוג `bars_5min_history`, דדופ לפי **instant מנורמל** (`ts::timestamptz` / epoch), לא `str(ts)`. כך חפיפת-פורמטים לא יוצרת כפילות. (smallest fix אם השורש=פורמט.)
- **RTH gate ל-woodies:** אם woodies מזליג overnight ל-chart בזמן RTH — החל את אותו `_is_within_rth` של `bars.py` גם ב-`woodies_system._persist_bar` (single-source: ייבא את אותה פונקציה, לא העתק), או סנן בקריאה. **החלט לפי כוונת ה-fallback** ("better overnight coverage") — אם overnight נחוץ, הפרד אותו ויזואלית, לא למזג כפול.
- **מסנן-סשן TZ-נכון:** השווה ב-UTC מפורש (שני הצדדים tz-aware) או הוסף `session_id` בכתיבה. מתחבר לבאג ה-PG datetime↔str (`CC_PROMPT_FIX_PG_DATETIME_FRESHNESS`).
- **cumulative_delta:** אמת — האם אנחנו **קולטים את ה-CVD של Sierra verbatim** או **מחשבים מחדש** (double-count)? Sierra מביא cumulative מוכן → לפי Rule 1 לקלוט, לא לחשב מחדש. בדוק `post_cumulative_delta` (`bars.py:629`) + `v9_bars_cumulative_delta` (UNIQUE על bar_id/(ts,idx)?). הדבק ממצא; תקן רק אם יש double-count מאומת.

## Acceptance (✓/✗ + raw)
- [ ] Phase-1 SQL מודבק (a-d) + הכרעה data-vs-render עם 2-3 נרות-דוגמה.
- [ ] תיקון מוחל לפי השורש המוכח (diff מצורף); **לא נגעת ב-ingest_bar/aggregator המתים**.
- [ ] **אימות נגד Sierra:** ה-chart ל-RTH 2026-06-04 = רצף נרות יחיד (0 כפילות), VAH/POC/VAL/IB == ערכי Sierra (raw: query + השוואה).
- [ ] regression test: מזין שני רגעים זהים בפורמט-ts שונה לשתי הטבלאות → ה-endpoint מחזיר **נר אחד**. *"if reverted (דדופ לפי str) → RED: 2 נרות."*
- [ ] cumulative_delta: ממצא verbatim-vs-recompute מודבק; תוקן רק אם double-count מאומת.
- [ ] regression מלא ירוק · `git log -1` · עדכון `STATUS_BOARD.md` (root+fix+verification) · **NOT-DONE/DEVIATIONS**.

## Invariants
Sierra=source-of-truth (לא לסנתז/לחשב-מחדש מה ש-Sierra מביא — Rule 1) · אל תיגע בנתיב המת `ingest_bar`/aggregator · single-source ל-RTH-gate · אל תיגע sc_study/DLL/risk · §7a anti-regression (קרא `P30_AGENT_INBOX_PRE_LIVE.md §7a` לפני נגיעה ב-market-data routes) · localhost-PG · Cowork מאמת בלתי-תלוי (diff + השוואה מול Sierra + litmus דדופ).
