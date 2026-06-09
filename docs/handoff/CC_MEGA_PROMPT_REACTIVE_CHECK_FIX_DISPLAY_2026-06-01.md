# CC MEGA PROMPT — Reactive: Pipeline Check + 3-Variant Fix + Build-Status & Trader Display · 2026-06-01

**תווית החלטה:** `D-RVX` (ראה `docs/plans/DECISION_LEDGER.md`)
**מאת:** Cowork agent → **אל:** Claude Code
**נקודת החלטה:** `docs/reports/DECISION_BRIEF_REACTIVE_VOLUME_THRESHOLD_2026-06-01.md`
**מחליף/מרחיב:** `CC_PROMPT_REACTIVE_VARIANT_SHADOW_HARNESS_2026-06-01.md` (זה ה-superset — הוסיף Phase 0 pipeline-check + תצוגות).

> **משמעת Pre-LIVE (CLAUDE.md) — חובה בכל phase:** diagnose-first · read-current-code · audit-existing (KEEP/ADAPT/REPLACE/DEFER) · smallest-correct-change · **Rule 5 (command + raw output, לא assertion)** · strategic-stop לפני נגיעה ב-live fire path · **No silent failures** (אל `except: pass`).
>
> **תווית בכל מקום שנוגעים:** כל קובץ/פונקציה/שורה חדשה או משונה תישא הערה `# D-RVX: <מה> — <למה> — ראה DECISION_LEDGER`. זה כדי שתמיד אפשר לחזור לנקודת ההחלטה.
>
> **עיקרון-על:** הוריאציות הן **צופים (observational)**. ה-live Reactive (`DROP_THRESHOLD_PCT=0.10`) **לא משתנה**. אפס מעבר ב-gateway/route_setup, אפס זיהום fires/trades ראשיות, אפס נגיעה ב-risk/sizing/order.

---

## ⛔ קריטי לפני הכל — S2 לא הפיק פלט אי-פעם

ב-`v9_five_min_setups` יש **0 שורות all-time**, `v9_trades firing_system=2` = **0 all-time** (STATUS_BOARD 2026-06-01 §חקירת RTH). **משמעות: גם אם נבנה את 3 הוריאציות בצורה מושלמת — הן לא יפיקו כלום אם S2 לא מקבל/מעבד ברים.** לכן Phase 0 חובה קודם.

---

## Phase 0 · Audit מלא של צינור ה-Reactive (READ-ONLY, diagnose-first)

עקוב אחר ה-bar מקצה לקצה והדבק ראיה גולמית (Rule 5) לכל חוליה:

1. **Bridge → DB:** האם `v9_bars_5min` מתעדכן ב-RTH? (`SELECT max(ts), count(*) FROM v9_bars_5min WHERE date(...)=today`).
2. **ערוץ הפרסום מול המנוי — ההשערה המובילה:** האם יש mismatch?
   - `five_min_system.py:88` מנוי על `mems26:events:bar.5min` (+ class attr ערוצים מלאים).
   - `five_min_system.py:696` `subscribed_bar_types()` מחזיר `["5min"]`.
   - `bar_aggregator_5min.py:~206` מפרסם `publish_threadsafe("5min")`.
   - `bar_router.py:~117` פולט `bars.5min`.
   - **שאלה:** האם `FiveMinSystem.process_bar` בכלל נקרא ב-RTH? הוסף לוג זמני / בדוק לוג קיים, הדבק את ה-trace. סווג: האם זה ערוץ-לא-תואם, מנוי-כפול, או משהו אחר.
3. **process_bar → detector:** אם process_bar רץ — האם `_detect_reactive` מגיע? מה ה-`mode` (`DAY_TYPE_MODE`?), והאם `current_day_type` חוסם (NT skip / None)?
4. **COT/AMT:** האם `_get_cot_from_footprint`/`_get_amt_from_footprint` מחזירים ערך (לא None)? (Reactive מחזיר מיד אם None).

**פלט Phase 0:** מפת חוליות CONNECTED/BROKEN עם raw evidence + VERDICT: מה בדיוק מונע מ-S2 לפעול. **strategic-stop — הצג ל-Michael לפני Phase 1.**

## Phase 1 · תיקון מסירת הברים ל-S2 (אם Phase 0 מצא שבר)

- תיקון **smallest-correct** של ה-wiring (ערוץ/מנוי) כך ש-S2 באמת מקבל ומעבד ברי 5-דק' ב-RTH. **לא** לגעת בלוגיקת הזיהוי או בספים.
- טסט regression שמוכיח: bar נכנס → `process_bar` רץ → `_detect_reactive` נקרא.
- **Rule 5:** הדבק לוג חי של bar שמגיע ל-`_detect_reactive` אחרי התיקון.
- תווית `# D-RVX (Phase1 wiring)`.

## Phase 2 · 3 הוריאציות כצופים (D-RVX core)

- **Refactor בטוח:** הוצא את גייט בר 2 (`b2_drop`, ~`five_min_system.py:499`) ל-callable מוזרק, default **זהה-בייט** ל-`<= b1*0.10`. הרץ טסטים קיימים → חייבים לעבור ללא שינוי. **strategic-stop: הצג diff + פלט טסטים לפני המשך.**
- **Variant evaluator (observer):** מריץ את ה-setup ה-4-ברי המלא (b1/b3/b4 + COT/AMT + belly + lookback) ל-3 הגייטים, נבדל **רק** בבר 2:
  - **A · VSA:** `b2<b1 AND b2<b0 AND b2 ≤ 0.7×rolling_avg_20(vol)`
  - **B · RVOL-TOD:** `b2 ≤ 0.6×baseline_TOD(clock_time)` (ממוצע אותה שעת-שעון, 10–20 sessions מ-`v9_bars_5min`, read-only)
  - **C · Strict:** `b2 ≤ 0.5×rolling_avg_20(vol)`
- **טבלה `v9_reactive_variant_signals`:** `id, ts, variant_id(A/B/C), direction, entry_price, b0_vol,b1_vol,b2_vol, rolling_avg_20, rvol_tod, gate_value, other_conditions_json, atr_5m, session_date, created_at`. כתיבה נפרדת מ-fires.
- **Outcome labeler** (job סוף-session, read-only על bars): מ-entry, בחלון time-stop (~18 ברים): הגיע ל-T1=entry±12t לפני stop=entry∓8t? → `outcome, mfe_ticks, mae_ticks, bars_to_resolution` → `v9_reactive_variant_outcomes`.
- **edge-cases:** החרג/טפל 2 ברים אחרי 09:30, בר 15:55–16:00, roll/half-days.

## Phase 3 · תצוגת 3 הוריאציות ב-Build Status (אור ירוק למי שירה)

- **Audit קודם:** קרא `backend/v9/systems/build_status/types.py` (`SystemStatus`, `BuildStatusResponse`), `aggregator.py`, `s2_inspector.py`, `build_status_routes.py`, ורכיב ה-Build Status בפרונט. סווג KEEP/ADAPT.
- הוסף ל-S2 ב-build_status בלוק `reactive_variants`: לכל A/B/C — `armed` (gate-alone עבר היום), `fired_today` (bool), `fires_count`, `last_fire_ts`.
- **בפרונט:** שלושה אינדיקטורים A/B/C עם **אור ירוק** למי ש-`fired_today=true` (אפור=לא ירה, צהוב=armed-לא-ירה). read-only display.
- **Rule 5:** הדבק JSON של ה-endpoint + צילום/תיאור הרכיב אחרי session.

## Phase 4 · תצוגה בטריידר (איזו וריאציה יצאה)

- **Audit קודם:** מצא את עמוד ה-Trades בפרונט + ה-route שמזין אותו (`trades.py` / `frontend/v9/.../trades`).
- הצג את אותות הוריאציות (מ-`v9_reactive_variant_signals`) בעמוד עם **badge וריאציה (A/B/C)** + outcome (כש-labeler סיים), מסומנים בבירור כ-**SHADOW-VARIANT** (לא עסקאות אמיתיות, לא נספרים ב-WR/PnL — כמו badge ה-synthetic הקיים).
- מטרה: שתראה במבט אחד **איזו מהשלוש ירתה** על כל setup.

## Phase 5 · דוח השוואתי + אימות

- `scripts/reactive_variant_report.py`: פר-וריאציה — `fires_per_day, gate_alone_pass_rate, full_setup_fires, win_rate, avg_mfe/mae, expectancy_proxy` — **זה לצד זה, בלי להכריז מנצח** (Michael בוחר מדד בסוף השדאו).
- **Rule 5 — הדבק:** (a) diff ה-refactor + טסטים ירוקים · (b) trace bar→detector אחרי Phase 1 · (c) 3 שורות variant גולמיות מהטבלה · (d) JSON build_status עם הדגלים · (e) פלט הדוח.
- **4 צירי UAT** לכל endpoint חדש: Quality/Recency/Cardinality/Latency.

## Strategic stops (עצור ושאל Michael)
1. סוף Phase 0 — מפת החוליות + VERDICT לפני תיקון.
2. סוף refactor (Phase 2) — diff + טסטים זהים-בייט לפני בניית observers.
3. אחרי session ראשונה — 3 שורות variant גולמיות לאימות תיוג, לפני שסומכים על הצבירה.

## בסיום
עדכן `docs/plans/ROADMAP_TO_LIVE.html` (סקשן 1c · D-RVX) + `STATUS_BOARD.md` (root→fix→verification, Rule 5) + `DECISION_LEDGER.md` (סטטוס D-RVX → 🟢 IMPLEMENTED-SHADOW). שמור את תווית `D-RVX` בכל קובץ שנגעת.

---

### עיגון קוד
- `backend/v9/systems/five_min/five_min_system.py`: `DROP_THRESHOLD_PCT=0.10` (30), `_detect_reactive` (~469–543, גייט בר2 ~499), מנוי ערוצים (88, 696), `mode`/`current_day_type` gating (~734–786), `_current_atr_5m` (767).
- `backend/v9/services/bar_router.py` + `bar_aggregator_5min.py` — ערוץ הפרסום (Phase 0).
- `backend/v9/systems/build_status/{types,aggregator,s2_inspector,build_status_routes}.py` — תצוגת build_status.
- `v9_bars_5min` — baseline TOD + labeler (read-only).
- frontend: רכיב Build Status + עמוד Trades (CC לאתר מדויק).
