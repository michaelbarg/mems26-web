# CC PROMPT — צ'ארט 5-דקות רציף: הפעלת מקור chart#5 (5min_continuous) → טבלה ייעודית → רינדור רציף כמו Sierra · 2026-06-04

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** **קרא `docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md §7a` לפני נגיעה ב-market-data routes (anti-regression).** Sierra=source-of-truth.
**diagnose-first.** Cowork ביצע RCA; אל תיגע בנתיב המת `ingest_bar`/aggregator (no-op מאומת).

## הבעיה (אומת ע"י Cowork, code-level)
הצ'ארט שלנו **לא רציף** (פערים מ-8:30 CT, גם אתמול וגם היום) בעוד **Sierra chart#5 רציף**. השורש:
- Sierra **chart#5** מייצא בארים רציפים 24h → `5min_continuous.json` → `bridge/v9_streams/bars_5min_continuous_stream.py` → `POST /api/v9/bars/5min_continuous`.
- **ה-endpoint הזה מושבת** (`bars.py:899-912`): `return {"inserted":0,"disabled":True}`. ה-docstring: *"writes to v9_bars_5min DISABLED... Re-enable when dedicated continuous table is built."* → **הדאטה הרציפה מתקבלת ונזרקת.**
- הצ'ארט (`bars_5min_history.py`) קורא `v9_bars_5min` (chart#3, **RTH-only**, עם RTH-gate `_is_within_rth` + volume-guard `vol>100_000` ב-`post_bars_5min`) → נרות נופלים (נר ה-RTH-open הגבוה-נפח נזרק) → **פערים בלתי-נמנעים**.
- הושבת בעידן corruption של SQLite (להפחית כותבים). **על Postgres זה כעת בטוח (MVCC)** — CLAUDE.md §DB: הפעלה-מחדש של כותבים מושבתים = החלטת-מוצר, לא בטיחות.

## ⛔ risk surface
- כתוב לטבלה **ייעודית חדשה** `v9_bars_5min_continuous` — **אל תכתוב ל-`v9_bars_5min`** (זו הסיבה המקורית להשבתה: הרציף דרס per-bar volume ב-cumulative בזמן settlement). שמור את `v9_bars_5min` (RTH) כפי שהוא — S2/VSA תלויים בו RTH-only.
- אל תיגע sc_study/DLL/risk · §7a anti-regression · localhost-PG.

## Phase 1 — אבחון (diagnose-first, הדבק)
1. אשר `bars.py:899` מושבת + `bars_5min_continuous_stream.py` (filename `5min_continuous.json`, api_path `/api/v9/bars/5min_continuous`).
2. אשר שהאקספורט קיים ויש בו דאטה רציפה: `ls -la ~/SierraChart_Data/v9_export/5min_continuous.json` + `jq '.bars|length, .bars[0], .bars[-1]'` (או המבנה בפועל). הדבק — אם הקובץ ריק/לא קיים → **עצור ודווח** (ייתכן ש-chart#5 לא מייצא; אז זו בעיית sc_study, לא backend).
3. אשר שהצ'ארט קורא `v9_bars_5min`(+woodies) ולא את הרציף (`bars_5min_history.py`).

## Phase 2 — טבלה ייעודית + הפעלת writer
- צור `v9_bars_5min_continuous` (ts, symbol, open, high, low, close, volume, +poc_vol/vah/val/cumulative_delta אם באקספורט), **UNIQUE(ts,symbol)** (ל-`ON CONFLICT`/upsert בטוח על PG).
- הפעל `post_5min_continuous`: upsert ל-`v9_bars_5min_continuous` (epoch-normalized ts כמו ב-355a54b). **בלי RTH-gate** (זו הנקודה — רציף). volume: אל תפיל נרות-אמת; אם צריך guard ל-cumulative — זהה cumulative ע"י **monotonic-increasing** ולא סף-קשיח 100K.

## Phase 3 — הצ'ארט קורא מהרציף
- `bars_5min_history.py`: קרא **primary = `v9_bars_5min_continuous`** (רציף, כמו Sierra chart#5). dedup-by-epoch (כבר קיים מ-355a54b). הסר/רכך את מסנן-ה-RTH כך שהצ'ארט מציג רצף (גבול-סשן ויזואלי מותר, אבל **בלי פערים בתוך סשן**).
- אם `v9_bars_5min_continuous` ריק (טרם נצבר) → fallback ל-`v9_bars_5min`+woodies (התנהגות נוכחית), עם warning. Rule 1.

## Acceptance (✓/✗ + raw)
- [ ] Phase-1: סטטוס disabled + קיום+תוכן `5min_continuous.json` מודבק.
- [ ] טבלה `v9_bars_5min_continuous` + UNIQUE; `post_5min_continuous` כותב (raw: `\d`, ספירת rows אחרי push).
- [ ] **אימות רציפות מול Sierra chart#5:** ל-RTH 2026-06-04 — רצף נרות **ללא פערים** מ-08:30 CT, ערכים (OHLC + VAH 7604/POC 7578.25/VAL 7552.50/IB 7570.50) == Sierra. raw: query שמראה אין gap > 5min בין בארים עוקבים בתוך הסשן.
- [ ] `v9_bars_5min` (RTH) **לא נגעה**; S2 regression ירוק.
- [ ] regression test: ingest רצף-בארים-רציף → endpoint מחזיר רצף ללא פערים. *"if reverted (chart קורא RTH-only) → RED: פערים."*
- [ ] `git log -1` · עדכון `STATUS_BOARD.md` (root=continuous-endpoint disabled · fix · verification) · **NOT-DONE/DEVIATIONS**.

## Invariants
Sierra=source-of-truth (לקלוט את הרציף verbatim, לא לסנתז) · טבלה נפרדת (אל תזהם `v9_bars_5min` RTH) · §7a · אל תיגע sc_study/risk/ingest_bar-המת ·
localhost-PG · No silent failures · Cowork מאמת בלתי-תלוי (אין-gap-בתוך-סשן + השוואת-ערכים מול Sierra chart#5 + `v9_bars_5min` לא נגעה).
