# MEMS26 P31 — Next Chat Handoff (2026-05-21 אחר הצהריים)

> **קלוט את ה-prompt הזה במלואו לפני שאתה עונה משהו. אל תפתח Sierra/bridge/כלום עד שהבנת את כל ה-context.**

---

## 0. ברכה + פרוטוקול

- אמור **שלום / בוקר טוב / צהריים טובים / ערב טוב** לפי הזמן.
- קרא לפני כל פעולה אחרת:
  1. `CLAUDE.md` (root)
  2. `.cursor/rules/mems26-pre-live-protocol.mdc`
  3. `docs/handoff/P31_TASK_BOARD.md` — single source of truth, **§0** (location now), **§6.1–§6.5** (S2 thread)
  4. `docs/reports/PROMPT_P31_JOURNAL_PNL_AND_S2.md` — full session report
- **ה-bridge הוא local-only.** `CLOUD_URL=http://localhost:8000`. אל תיגע ב-LaunchAgent / DLL / `CLOUD_URL`.
- **אל תריץ `scripts/start_all.sh`, `npm run dev`, `next dev` או דומיהם בלי בקשה מפורשת מ-Michael.**
- **commits — רק אם Michael מבקש.** push ל-origin — רק אם הוא מבקש מפורשות.

---

## 1. איפה אנחנו (P31, pre-LIVE)

**Snapshot 2026-05-21 ~16:00 IL:**

| רכיב | סטטוס |
|------|-------|
| Backend `:8000` | 🟢 PID **82330** (restart בשעה 15:55) |
| Frontend `:3000` | 🟢 |
| Bridge | 🟢 PID 60596, רץ עם §9 TZ workaround (כל 12 הזרמים) |
| `BarRouter: dispatch ... for 5min` | 🟢 **62-231ms (mean ~106ms)** — מ-8000ms (75× שיפור) |
| `FiveMinSystem.process_bar` SLOW warnings | ✅ **0** מאז restart |
| S2 fire path | 🟢 (אומת לוגית; ירוי בפועל ממתין ל-RTH) |
| S4 fire path | 🟢 ירה live בזמן הבדיקה (trade_id=701, GB100 SHORT) |

**איפה אנחנו על הציר:** `P30 baseline ✅ → P31 P0 (אתה כאן, עם רוב התשתית של 02b ירוקה) → SHADOW soak ⬜ → DEMO ⬜ → LIVE ⬜`.

---

## 2. מה הסשן הקודם השלים (Cursor 2026-05-21 PM)

**5 commits מקומיים על branch `stabilize/mems26-local-truth-2026-05-16` (לא נדחפו ל-origin):**

```text
0f5960d  feat(main): inject FootprintSystem into FiveMinSystem at startup [P31-02b]   +7 lines
12b376f  fix(five_min): in-process footprint reads + Sierra TPO file load [P31-02b]   +224 / -24
04514a6  revert: bar_router publish_threadsafe (regression in S2 fire path) [P31-02]  +5 / -84
43f5399  fix(bar_router): publish_threadsafe uses run_coroutine_threadsafe (REVERTED) +84 / -5
5b75101  feat(day_type): extract prev_day loader to standalone module + tests [P31-09] +248
```

### מה שהושלם בקוד

- **P31-09 prev_day:** `backend/v9/systems/day_type/prev_day.py` (extraction מ-`backend/main.py` שהיה inline). 5 בדיקות PASS.
- **P31-02 root cause דיאגנוזה:** `FiveMinSystem.process_bar` עשה 5–9 קריאות `requests.get('http://localhost:8000/...')` סינכרוניות לעצמו (לוקיישנים: `five_min_system.py:290,299,344,434,480,519`). זה ה-8s.
- **P31-02 fix attempt #1 (`43f5399`):** `bar_router.publish_threadsafe` שונה ל-`run_coroutine_threadsafe`. **נכשל** — הזיז את `process_bar` למתקיים על ה-FastAPI loop, אבל ה-self-calls חסמו את ה-loop → timeout=2s → cot/amt/belly = None → `_detect_reactive` חזר `(None, 0, {})` → S2 שתק. **REVERTED ב-`04514a6`** ביוזמת Cursor אחרי source review.
- **P31-02b root cause fix (`12b376f`):** הוסף `set_footprint_system()` setter ל-`FiveMinSystem` (מקביל ל-`set_gateway`). הקריאות `_get_cot/amt/belly_from_footprint` עכשיו מעדיפות `self._footprint_system.get_current()` ב-process. fallback HTTP נשמר ל-graceful degrade. `_compute_location_vs_poc` עכשיו קורא `_load_sierra_tpo()` ישיר. 9 בדיקות חדשות + 74 קיימות PASS.
- **P31-02b wire-up (`0f5960d`):** ב-`backend/main.py` סביב שורה 380, אחרי ה-`set_gateway` block — 7 שורות שמזריקות `app.state.footprint_system` ל-`app.state.five_min_system`. נעשה ב-Approach K (partial staging non-interactive — backup, reset, edit, commit, restore). commit נקי ב-7 שורות בלבד.

### Verification חי 2026-05-21 15:55 ✅

- backend restart: PID 50472 → 82330 (גרשנו עם `pkill -9 -f "uvicorn backend.main"` כי `kill -15` ו-`kill -9` רגילים נכשלו).
- 7 dispatches של 5min ב-30 שניות ראשונות: 62.8 / 78.1 / 86.9 / 89.0 / 90.6 / 108.4 / 231.3 ms.
- 0 SLOW handler warnings של `FiveMinSystem.process_bar` מאז restart.
- S4 trade_id=701 GB100 SHORT עבר Gateway חי בזמן הבדיקה.

---

## 3. הצעד הבא (סדר מוצע)

| # | משימה | למה | זמן | סיכון |
|---|---|---|---|---|
| **1** | **P31-02d — Woodies parallel fix** | הלוג מראה `BarRouter: SLOW handler WoodiesSystem.process_bar took 18155ms`. ה-pattern: כנראה אותם HTTP self-calls. בלוקר חמור לסיגנלים של S4 ב-RTH. הפתרון: setter injection דומה ל-02b. | 1-1.5 שעה | בינוני |
| **2** | **P31-02c — re-apply commit `43f5399`** | thread leak נשמר; כעת בטוח להחזיר את `run_coroutine_threadsafe` כי `process_bar` < 250ms ולא חוסם loop | 30 דק' (cherry-pick + verify) | נמוך |
| 3 | **P31-15 — datetime JSON serialization fix** | `sqlalchemy.exc.PendingRollbackError: ... Object of type datetime is not JSON serializable` ב-`v9_trades INSERT` עבור TLB trade. Gateway/TradeManager צריך לעשות serialize ל-`quality.metadata` לפני `db.add`. | 1 שעה | נמוך |
| 4 | P31-16 — `[Main]` log prefix לא בלוג | קוסמטי — `_logger` ב-`backend/main.py` לא נראה כלל ב-`/tmp/backend.log`. logging config drift פרה-existing. | 30 דק' | אפס |
| 5 | main.py triage | יש 100+ שורות שינויים מסשנים קודמים שלא commit. צריך לפצל לקבוצות לוגיות (prev_day wire-up, journal_compat_routes import, asyncio import, ...) ו-commit כל אחת בנפרד. | 1-2 שעות | נמוך |

**ההמלצה שלי:** התחל ב-#1 (P31-02d — אותה גישה כמו 02b). זה הצעד היחיד שעדיין משחרר ערך perf חיוני ל-RTH; אחרי שהוא עובר, P31-02c הופך טריוויאלי.

---

## 4. הקשר טכני ל-P31-02d (Woodies)

`backend/v9/systems/woodies/woodies_system.py` — `process_bar` סובל מאותו דפוס. צריך:

1. לזהות אילו `requests.get(...)` עצמיים יש ב-`process_bar` ובמתודות העזר שלו (חיפוש: `requests.get|http://localhost:8000`).
2. להוסיף `set_*_system()` setters תואמים (probably `set_footprint_system` + `set_tpo_system` או מה שצריך).
3. להוסיף helper דומה ל-`_footprint_state()` עם graceful HTTP fallback.
4. להוסיף wire-up ב-`backend/main.py` בלוק זהה ל-P31-02b — אלא אם ה-Woodies system כבר מוזרק לwhere it needs (אין set_gateway equivalent, צריך לבדוק).
5. בדיקות ב-`backend/v9/systems/woodies/tests/test_in_process_*.py` או `tests/v9/systems/test_woodies_process_bar_perf.py` (קובץ קיים, אולי שם).
6. אחרי commit + restart → לוודא `BarRouter: SLOW handler WoodiesSystem.process_bar` לא מופיע (היום: 18155ms; יעד: <500ms).

**אזהרה:** אל תחזור על הטעות של P31-02. אל תיגע ב-`bar_router.publish_threadsafe` (P31-02c) **לפני** ש-Woodies process_bar מהיר. אחרת אותה רגרסיה תחזור (loop blocked, S4 שותק).

---

## 5. constraints — אסור / חובה

### אסור
- 🚫 `git push --force` (אלא אם Michael מבקש מפורשות)
- 🚫 לשנות `CLOUD_URL` או LaunchAgent
- 🚫 להריץ `start_all.sh` או דומה בלי בקשה
- 🚫 commits בלי בקשה
- 🚫 לשנות `bridge/v9_streams/base_stream.py` או `bridge/v9_history.py` (כבר מכילים §9 TZ workaround — לא לגעת בלי לקרוא §9 בלוח קודם)
- 🚫 `git reset --hard` (לעולם — יש 100+ שורות לא-committed שיתוקנו)
- 🚫 `workers=4` ב-uvicorn (יישבור state isolation — `BarRouter`, `TradeManager`, `app.state.*` הם per-worker)

### חובה
- ✅ לקרוא את `P31_TASK_BOARD.md` לפני כל פעולה
- ✅ לעדכן את ה-board אחרי כל שינוי משמעותי (timestamp + מי + מה + מה נשאר)
- ✅ לעצור strategically בכל phase gate או ממצא חדש
- ✅ לדווח על pre-existing failures (לא להתבלבל איתן עם רגרסיות)

---

## 6. Pointers

### Code
- `backend/v9/systems/five_min/five_min_system.py` — המקום של P31-02b (לדוגמה ל-02d)
- `backend/v9/systems/woodies/woodies_system.py` — מטרת P31-02d
- `backend/main.py:380-386` — wire-up block (תוסיף שם wire-up ל-Woodies בצורה דומה אם 02d דורש)
- `backend/v9/services/bar_router.py:42-49` — מקום ה-thread leak (P31-02c)
- `backend/v9/api/v9/footprint/routes.py:8-13` — דפוס ל-`get_current()` עם `app.state`
- `backend/v9/api/v9/tpo_routes.py:267-292` — `_load_sierra_tpo()` (קריאה in-process לקבצי Sierra)

### Tests
- `backend/v9/systems/five_min/tests/test_in_process_footprint.py` — דפוס לבדיקות P31-02b (לחקות ב-02d)
- `tests/v9/services/test_bar_router_threadsafe.py` — יש בו `test_publish_threadsafe_warns_when_unbound` שכשל כי ה-fix של 02 הוחזר; יחזור לעבור ב-02c

### Docs
- `docs/handoff/P31_TASK_BOARD.md` — single source of truth (§6 הוא thread של S2)
- `docs/reports/PROMPT_P31_JOURNAL_PNL_AND_S2.md` — full session report עם verification sequence
- `docs/handoff/P31_PATTERN_STOP_AUTONOMY_MATRIX.md` — pattern recognition (P31-PAT)
- `docs/reports/PROMPT_P30_WOODIES_SYSTEM_SLOW_HANDLER.md` — דוח ישן של Woodies SLOW (אולי רלוונטי ל-02d)

---

## 7. UAT axes לכל endpoint שאתה נוגע

לפי הפרוטוקול, אחרי כל fix של data/perf endpoint, וודא **את כל הארבעה**:

1. **Quality** — הבעיה הספציפית הוסרה (e.g., `bad_count=0`, `0 SLOW warnings`)
2. **Recency** — `endpoint.latest_ts == DB.MAX(ts)` (אם רלוונטי)
3. **Cardinality** — `len(rows) == requested_limit` (אם רלוונטי)
4. **Latency** — תחת ה-threshold המתועד

P27.5a שובר: רק Quality נבדק → איבדנו את 20 הברים החדשים. אל תחזור.

---

## 8. שאלות לשאול את Michael אם לא ברור

- אם דבר חוסם RTH או דורש Sierra פתוח — שאל אם הוא רוצה לחכות לסשן בוקר אחר.
- אם אתה רוצה לשנות trading logic או risk surface (e.g., stop calculation, TradeManager) — שאל לפני.
- אם יש בלוקר שלא ידוע מהפרוטוקול — שאל איזה מסלול (A/B) הוא מעדיף, ואל תציע אופציות בעודף.

---

## 9. סיכום בשורה אחת

**P31-02b ירוק חי. P31-02c (thread leak) ו-P31-02d (Woodies 18s) הם הצעדים הבאים. אל תיגע ב-`bar_router` עד ש-Woodies מהיר. אל תפצל את main.py בלי הסכמה. עדכן את הלוח אחרי כל שינוי. אל תפתח threads חדשים בלי אישור.**

צא לדרך 🚀
