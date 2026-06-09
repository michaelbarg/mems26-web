# CC AUTONOMOUS PROMPT — Shadow-Day Operations · 2026-06-03

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** אוטונומי, ללא עצירה לאישור. **אל תעשה `git add -A`.** הפק דוח בכל phase.
**אישור Michael 2026-06-03:** הרץ יום SHADOW מלא — **אבל רק אחרי ששער ה-DB עובר.** "data מושחת גרוע מאין."

## 🚦 שער-על (GO/NO-GO מוחלט)
**אסור לאסוף יום SHADOW עד ש-`PRAGMA integrity_check` עם backend כבוי על ה-Mac = `ok`.** אם לא ניתן להגיע ל-`ok` — **לא אוספים**, להשאיר backend כבוי/קריאה, ולדווח. בדיקה חיה/מעל-mount = false-positive (לא קבילה).

## 🚫 Invariants
אל תיגע: `sc_study/` (החלטת Michael תלויה — **אל תקמט, אל תבנה**) · `get_db()` lock (בוטל, deadlock) · `safe_writer.py` · B2/B3 · polling · LaunchAgent · bridge routes. קמט אטומי, רק קבצים מפורשים.

---

## PHASE A — סגירת round-3 + מצב נקי
1. אם נותרו שינויי round-3 לא-מקומטים שקשורים ל-fixes (B1/session-filter/D1) — קמט אותם אטומית. **אל תקמט `sc_study/`, `CLAUDE.md`, או docs לא-קשורים.**
2. דווח `git status --short` נקי לקבצי ה-fix + `git log --oneline -5`.
- Acceptance: B1 committed (`grep -c "lookback_quiet = True"`=2), טסטים ירוקים, `sc_study` עדיין לא-מקומט (לא נגעת). ✓/✗

## PHASE B — שער DB אוטוריטטיבי (קריטי)
**אבחון:** מהבדיקה הלא-אוטוריטטיבית של Cowork (mount, 2026-06-03 ~03:00 ET): `Rowid out of order` עדיין מופיע **למרות** tick_reversal מושבת. חשד מרכזי: **כותב-ORM בתדר-גבוה שנותר לא-מסורל** — `cumulative_delta` (CVD, 51,803 שורות, כותב עד 06:55) ו/או `imbalance` (שני אלה תועדו ב-NOT-DONE של CC כלא-מסורלים).
1. **עצור backend.** הרץ `PRAGMA integrity_check;` מלא (לא quick). הדבק פלט גולמי.
2. אם **לא ok:** זהה איזו טבלה מושחתת (`PRAGMA integrity_check` + per-table rowid-order: `SELECT count(*) FROM (SELECT rowid,LAG(rowid) OVER(ORDER BY rowid) p FROM <t>) WHERE rowid<p`). דווח.
3. **טפל ב-root הנותר:** לכל כותב-ORM בתדר-גבוה שנותר לא-מסורל (cumulative_delta/imbalance/אחר) — או נתב את כתיבתו דרך `safe_writer`, או השבת אותו זמנית מאחורי דגל (תבנית `TICK_REVERSAL_DISABLED`/`FOOTPRINT_DISABLED`) **call-time**. **אל תחזיר lock ל-get_db.**
4. rebuild נקי לטבלה/DB המושחת (DROP/recover + VACUUM). **לא** מ-`.corrupt.bak`.
5. חזור ל-(1) עד `integrity_check = ok` (backend כבוי).
- **שער:** `integrity_check = ok` backend-כבוי (פלט גולמי). אם לא מושג → **STOP, לא אוספים**, דווח. ✓/✗

## PHASE C — Pre-Trade (לפני 09:30 ET / 16:30 IL)
הפעל backend נקי (port-check :8000/:3000 קודם). הרץ את `docs/runbooks/PRE_TRADE_PROTOCOL.md`. אמת עם פלט גולמי:
- `readiness = READY` (לא BLOCKED) ב-RTH · bridge fresh (לא stale) · Sierra connected · health <100ms.
- כל 6 הדגלים ON כצפוי (כולל `TICK_REVERSAL_DISABLED` + מה שהושבת ב-B).
- בארים זורמים · future-ts=0 · S4 trend לא תקוע GRAY · S2 armed.
- **בדוק את `v9_bars_5min_woodies`** (היה תקוע על 06-02 08:34) — האם S4 מקבל woodies טריים ב-RTH? אם לא → דווח (לא לחסום, אבל לסמן את איכות S4).
- **caveat לתעד (לא לתקן):** (i) `sc_study` v9.4.5 לא-מקומט → ייתכן source≠running-DLL → איכות SWI/Woodies/S4 לא ודאית. (ii) B4: נפח מקס' 5-דק'=1,000,000 artifact → נתוני VSA/S2 מזוהמים חלקית.
- Acceptance: snapshot pre-trade מלא (פלט גולמי) או רשימת blockers. ✓/✗

## PHASE D — איסוף יום SHADOW (09:30–16:00 ET)
- אסוף נורמלי. **ניטור כל ~30-60 דק'** (לוג snapshot): health, fires/setups, future-ts=0, frozen-tail (cci משתנה על ברים שונים), שגיאות כתיבה ב-warning (לא נבלעות).
- אם מופיע `database disk image is malformed`/`malformed`/write-error בלוגים → **עצור איסוף מיידית, השבת את הכותב האשם, דווח** (אל תמשיך לתוך DB מושחת).
- Acceptance: לוג ניטור תקופתי + ספירת fires/trades בסוף.

## PHASE E — EOD (אחרי 16:00 ET)
1. **עצור backend → `integrity_check` אוטוריטטיבי** (פלט גולמי). זה הקובע אם היום נאסף נקי.
2. EOD review: # trades, WR, setups per system (S1/S2/S4), התפלגויות, frozen-tail, slippage, כל corruption. דוח: `docs/reports/SHADOW_DAY_<date>_EOD.md`.
3. עדכן `STATUS_BOARD`/`ROADMAP` עם תוצאת היום (finding+fix+verification).

---

## דוח (חלק C) — פר phase
טבלת phase · Status · Evidence(command+output) · NOT-DONE (כולל sc_study provenance + residual writers שלא טופלו + screenshot/visual שנדחה) · Open.
**החלטות ל-Michael שנשארות פתוחות:** sc_study v9.4.5 (קמט/בנה/זרוק?) · CLAUDE.md §DB Write-Safety doc-drift (get_db לא נועל) · B4 ingestion fix · cumulative_delta serialization קבועה.
