# אלגוריתם בדיקה-עצמית לכל המערכות — עיצוב (2026-08-16)

> משימת מייקל: *"תשלח סוכן שיבחן איך מייצרים אלגוריתם בדיקות שיבחן את כל המערכות לבד"* —
> כדי שאף בוקר לא נצטרך לשאול "היא דרוכה?".
>
> **הכלל היחיד שמעצב את כל המסמך:** *טענה שווה משהו רק אם היא הריצה את נתיב-הייצור
> וצפתה באפקט אמיתי* — קובץ שנכתב, שורה שנוספה, מעבר-מצב, פקודה שקיבלה ACK.
> כל השאר הוא נחמה, לא ראיה.

---

## ⓪ למה המסמך הזה קיים — שלוש מחלקות של "ירוק שקרי" שכבר קרו

| # | המחלקה | המקרה הקנוני | העלות |
|---|---|---|---|
| A | **בדיקת טקסט-מקור במקום ריצה** | `tests/v9/regression/test_mae_scratch_sends_flatten.py` — 6 טסטים ירוקים בנויים על `inspect.getsource()` + `str.index`, בזמן ש-`write_trade_command(action=..., context={...})` זרק `TypeError` לפני שנכתב בייט. הניסיון-תיקון הראשון (`ede1d570`) אומת באותה שיטה, ולכן "עבר" בעוד הקוד עדיין זורק | עסקה #682 נסגרה בספרים CLOSED/$0 בזמן שסיירה החזיקה SHORT 4 @7799.25 כ-58 דק' → −$83.75 בפועל. אותו פגם השבית בשקט את `TARGET_APPROACH_REALIZE` (אף פעם לא רץ) ואת כפתור-ה-FLATTEN בפלאפון |
| B | **סקריפט שרץ מסנדבוקס בלי DB ובלי backend** | סוכן מריץ `scripts/*.py` מסביבה מנותקת ומדווח GO על מכונה שמעולם לא היה מחובר אליה | דוחות-שקר; החלטת-מסחר על סמך מכונה אחרת. *(הערה: גם המסמך הזה נכתב מסנדבוקס — ראו §7 "מה לא אומת כאן")* |
| C | **סוויטה שאי-אפשר להשתמש בה כאות** | ~487 כשלים ברובם fixtures ⇒ "הסוויטה ירוקה" לא זמין כסיגנל; טסט שעובר לבד ונופל בסוויטה (זיהום-סדר) ולהפך | אין קו-בסיס. כל תיקון "מאומת" נבדק מול רעש |

**המסקנה התכנונית:** האלגוריתם לא בונה עוד שכבת-דיווח מעל מה שקיים. הוא בונה **שרשרת
ראיות מבצעת** + **חוק-פסילה**: כל בדיקה חייבת להצהיר איזו *מוטציה* מפילה אותה, ואם היא לא
יכולה להיבדק — היא מדווחת `UNKNOWN`, ו-`UNKNOWN` בקבוצה-הקריטית = NO-GO (כלל 1: כישלון
כנה עדיף על ערך מסונתז).

---

## ① ביקורת המשטחים הקיימים — KEEP / ADAPT / REPLACE

לפי CLAUDE.md §*Audit existing surfaces before building*. אין כאן שכפול — כמעט הכל קיים
ופזור; החסר הוא **תזמורת + סמנטיקת-פסק + שכבת-החיווט**.

| קובץ | מה הוא מוכיח באמת | אמון | פסק |
|---|---|---|---|
| `scripts/flag_guard.py` | `.env` == `config/RULED_FLAGS.yaml`. מריץ פרסור אמיתי, פסק בינארי | **גבוה** (על מה שהוא מודד) | **KEEP** — הופך ל-L0.1. הגבלה: משווה קובץ, לא את התהליך החי |
| `scripts/mems26_fingerprint.sh` | זהות-מכונה: git HEAD, sha של ה-DLL בריפו מול ה-deployed, sha של `.env`, staleness של backend מול `FETCH_HEAD`, גיל `sierra_state.json`, `.tmp` תקועים | **גבוה** | **KEEP+ADAPT** — הופך ל-**חותם-הפרובננס** של כל ריצה (§4). כרגע פלט-לאדם; צריך `--json` |
| `scripts/mems26_verify.sh` | שירותים חיים, LaunchAgents, DLL-deployed↔repo, טריות פיד, DB lag | **בינוני** | **ADAPT** — §3 (DLL hash) הוא `wn` (warn) בלבד; בפרופיל pre-open הוא חייב להיות **FAIL**. §5/§6 מסתפקים ב"נשאל" בלי לבדוק את ארבעת צירי-ה-UAT |
| `scripts/mems26_arming_gate.py` | **המצאה הכי חשובה שכבר קיימת:** ההבחנה `internal` (מקולקל) מול `market` (חי וממתין), דרך `/api/v9/build/pattern-status` | **בינוני-גבוה** | **KEEP — מאמצים את הסמנטיקה שלו לכל האלגוריתם** (§4). חולשה: `_classify_block` הוא התאמת-מחרוזת על `reason`; טקסט-סיבה חדש ייפול ל-`market` = ירוק שקרי. תיקון: רשימת-קודים מפורשת + ברירת-מחדל `UNKNOWN` |
| `scripts/fire_drill.py` | שלב B/C **מריצים קוד אמת** — `compute_stop_v2` → `validate_fire`, `effective_contracts`, `entry_confirmed`. שלב D נוגע ב-API החי | **גבוה ללוגיקה** | **KEEP** — הופך ל-L2. **הגבלה קריטית: הוא לא כותב פקודה ולא נוגע בסיירה** — הוא לא היה תופס את באג ה-`TypeError` |
| `scripts/sim_matrix_e2e.py` | **כבר קיים כאן "דריל-ירי סינתטי" מלא:** `debug_gateway_fire` → `_execute_demo` → `op=PLACE` → מילוי סיירה-סים → זוגות-OCO → `MODIFY_STOP` על כל הסטופים → `FLATTEN` → journal → `v9_trades`. עם `_require_sim()` לפני כל ירי | **הכי גבוה בריפו** | **ADAPT → זה הליבה של §2.** חסרונות: משנה `.env` ומריץ `launchctl kickstart` (לא מתאים ל-pre-open), אין ניקוי מובטח ב-`finally`, `--keep-env` מתועד ולא ממומש |
| `backend/v9/api/v9/trade_commands.py::debug_gateway_fire` | ירי דרך ה-gateway האמיתי; שער-בטיחות קשיח `is_sim!=1 → 403` fail-safe | **גבוה** | **KEEP** — נקודת-ההזרקה של §2. לשנות: הנתיב ל-`sierra_state.json` **hardcoded** ל-`/Users/michael/...` (שובר במכונה שנייה); `sizing`/`stop_pts` מגיעים ב-query |
| `scripts/e2e_fire_proof.py` | 11 חוליות בשחזור על DB אמיתי; מריץ דטקטורים אמיתיים | **בינוני-גבוה** | **KEEP** — הופך ל-L6 (שפיות כלכלית). חוליות 8–10 (פקודה/ACK/ניהול) מוצהרות "לא זמינות ברפליי" — בדיוק החור ש-§2 סוגר |
| `scripts/post_restart_verify.sh` | 5 בדיקות חיות; מבדיל RTH/מחוץ-ל-RTH | **בינוני-גבוה** | **KEEP** — נבלע כ-L1 בפרופיל `postrestart` |
| `scripts/mems26_preflight.sh` · `mems26_doctor.sh` · `mems26_startup_check.sh` · `check_status.sh` · `credentials_self_test.sh` | חופפים ב-70% למעלה | נמוך-בינוני | **REPLACE** — לאחד מאחורי `mems26_selftest.py --profile ...`. להשאיר את `doctor.sh` בלבד לתרחיש התקנה-שבורה (הוא מדבר עם מי שאין לו backend) |
| `tests/` — 576 קבצים, **57 מהם משתמשים ב-`inspect.getsource`** | טקסט-מקור | **אפס** לגבי התנהגות | **REPLACE בהדרגה** — §3 + §6.7. הסוויטה **כולה** לא כשירה כשער |
| `tests/conftest.py` — בידוד `MEMS26_SIGNALS_DIR` + `_never_touch_the_live_command_file` | מונע מטסט לירות בחשבון האמיתי; אזעקה על mtime | **גבוה** | **KEEP** — תשתית-החובה של L4. עם `_assert_not_a_test_writing_live` ב-`sierra_command.py:38` זה מנעול-כפול תקין |

---

## ② מודל שכבות — מה כל שכבה מוכיחה, ומה היא **לא** יכולה להוכיח

לכל בדיקה בכל שכבה יש חמישה שדות חובה במרשם (`config/selftest_registry.yaml`):
`id · layer · probe (הפקודה) · evidence (מה נצפה) · mutation (מה מפיל אותה) · criticality`.
**בדיקה בלי `mutation` מוכחת לא נכנסת למרשם.** זו התרופה למחלקה A.

### L0 — זהות ותצורה (drift)
* **פרוב מבצע:** `mems26_fingerprint.sh --json` + `flag_guard.py` + שורת-האתחול של התהליך
  החי: `grep '[env_loader]' /tmp/backend.err.log | tail -1` (**לא** `ps eww` — פסיקת-זיכרון).
* **ראיה:** sha של `.env` (ללא `MACHINE_TAG`/`RENDER_MOBILE_URL`/`SIERRA_LIVE_ACCOUNT`),
  `git rev-parse HEAD`, `shasum` של `sc_study/MES_AI_DataExport_merged.cpp` מול
  `~/SierraChart/ACS_Source/MES_AI_DataExport.cpp`, `backend.staleness` (PID start מול
  `.git/FETCH_HEAD`), `is_sim` + `order_placement_armed` + `send_orders_to_trade_service`
  מ-`sierra_state.json` (ה-DLL מייצא את שלושתם, `merged.cpp:2079-2096`).
* **מה זה לא מוכיח:** ש-**הבינארי הטעון בסיירה** תואם למקור. ה-hash משווה `.cpp`, לא את
  ה-DLL שנטען אחרי Remote Build. **חור אמיתי** — ראו §6.8 (הוספת `study_build_ts`+`src_sha`
  ל-`sierra_state.json`) ו-§7 (עד אז: צעד-אדם).
* **מה זה לא מוכיח (2):** שהדגל *עושה* משהו. `flag_guard` מוכיח מחרוזת, לא התנהגות.

### L1 — טריות ושלמות נתונים (ארבעת צירי-ה-UAT)
* **פרוב מבצע:** לכל מקור ב-`docs/SOURCE_OF_TRUTH.md` — שאילתת psql *ו*-קריאת ה-endpoint
  שמגיש אותו, ואז ההשוואה:
  1. **Quality** — `bad_count=0` (למשל: `high<low`, `ts` בעתיד, תפר >15pt כמו
     `e2e_fire_proof.link2`).
  2. **Recency** — `endpoint.latest_ts == MAX(ts) FROM v9_bars_5min_woodies` (שוויון, לא
     "שניהם טריים" — זה מה שתפס את הקטיעה השקטה של 20 הברים ב-P27.5a).
  3. **Cardinality** — `len(rows) == requested_limit`.
  4. **Latency** — זמן-תגובה מתחת לסף מתועד.
* **ראיה:** JSON עם שני המספרים זה-לצד-זה + ההפרש. אף פעם לא "טרי ✓".
* **גבולות:** `v9_bars_5min` ידוע כנוטה להיתקע/לפעור (SoT); `v9_bars_5min_continuous`
  אסור לשימוש למחיר. שתי הבדיקות האלה חייבות לרוץ **על הטבלה הנכונה לכל צרכן** — לא
  "על הברים".
* **מה זה לא מוכיח:** שהמחירים *נכונים*. טריות + עקביות-פנימית אינן דיוק. אימות מול
  הצ'ארט של סיירה הוא צעד-אדם (§7).

### L2 — לוגיקה טהורה (דטקטורים/שערים בקלט קבוע)
* **פרוב מבצע:** קריאה ישירה לפונקציה עם וקטור-זהב. זה בדיוק שלב B/C של `fire_drill`:
  `compute_stop_v2(...)` → `validate_fire(...)`, `effective_contracts({"size":"full"})`,
  `entry_confirmed(...)`, `daytype_playbook.decide(...)`, `detect_opening_type(...)`,
  `classifier_core.classify_session(...)`.
* **ראיה:** ערך-החזרה מול הצפי, מודפס. `effective_contracts` בפרט חייב לרוץ עם `.env`
  טעון — הרצה בסביבה ריקה החזירה מספר-חוזים שגוי (מתועד ב-`fire_drill.py:33-41`).
* **מה זה לא מוכיח:** **שמישהו קורא לפונקציה בייצור.** זה בדיוק החור של `TARGET_APPROACH_REALIZE`:
  הלוגיקה הייתה נכונה, הקריאה זרקה. L2 היה נשאר ירוק לנצח.

### L3 — חיווט (האם הקורא באמת מגיע לנקרא, ובחתימה נכונה)
* **פרוב מבצע:** שניים, משלימים:
  * **(א) `wire_guard` — כריכת-חתימה סטטית מבצעת** (§3, כולל קוד + הוכחה שהוא תופס את
    הבאג ההיסטורי).
  * **(ב) מוני-הגעה בזמן-ריצה** — כל נתיב-יציאה/התראה קורא `reach.hit("mae_scratch.flatten")`
    (מונה בזיכרון + שורה ל-`ops_log`). דוח-הלילה מדפיס טבלת `last_hit_ts` לכל נתיב.
    נתיב שלא נגע **מעולם** מאז ההתקנה = 🔴 `NEVER_REACHED`; נתיב שלא נגע 30 יום = ⚠️.
* **ראיה:** רשימת call-sites שנכשלו ב-`bind()` + טבלת `NEVER_REACHED`.
* **מה זה לא מוכיח:** שהתנאי אי-פעם *מתקיים* בשוק, ושהסמנטיקה נכונה (אפשר לקרוא נכון
  לפונקציה הלא-נכונה). לכן L3 לבד לא מספיק — §2 סוגר את זה בפועל.

### L4 — הלולאה הפנימית: writer → queue → drainer → `trade_command.json`
* **פרוב מבצע (בלי סיירה בכלל, ולכן מותר גם על מכונת-LIVE):**
  `MEMS26_SIGNALS_DIR=$(mktemp -d)` → `write_flatten_account(...)` → לוודא
  `command_queue/cmd_000001.json` נוצר עם `op="FLATTEN_ACCOUNT"` → `drain_command_queue()`
  → לוודא `trade_command.json` נכתב ו-`_sent_ts` הוטבע → **לזייף ACK**
  (`touch trade_result.json`) → `drain_command_queue()` שוב → לוודא שהקובץ הוסר מהתור.
  ואז שלושת מסלולי-הכשל: TTL (`SIERRA_CMD_TTL_S=0` → archive, **לא** נשלח), grace ללא ACK
  (→ archive, **לא** נשלח שוב), ו-fast-path כשהתור לא ריק (→ **לא** נכתב ישירות).
* **ראיה:** קבצים אמיתיים על דיסק. זה בדיוק הסגנון של
  `tests/v9/regression/test_flatten_account_executes.py` (החלק המבצע שלו) —
  להרחיב אותו לכל שמונת ה-`write_*` × ארבעת מסלולי-הכשל.
* **מה זה לא מוכיח:** ש-ה-DLL מפרסר את ה-JSON, שהחשבון מקבל, שההוראה מגיעה לברוקר.
* **בטיחות:** `_assert_not_a_test_writing_live` (`sierra_command.py:38`) + conftest —
  שני מנעולים; L4 חייב גם הוא לאמת שהוא לא מצביע ל-`~/SierraChart_Data/v9_export`.

### L5 — סבב מלא מול סיירה (SIM בלבד) — **הדריל הסינתטי**, §2
### L6 — שפיות כלכלית (התנהגות-היום מול replay)
* **פרוב מבצע:** `e2e_fire_proof.py --date <today>` + `decision_replay.py` על אותם ברים,
  והשוואה: **קבוצת-הירי בפועל מול קבוצת-הירי בשחזור**.
* **ראיה:** `fires_live \ fires_replay` (ירי שלא היה אמור) ו-`fires_replay \ fires_live`
  (ירי שהוחמץ), עם `blocked_by` לכל אחד.
* **למה זו שכבה נפרדת:** L0–L5 יכולות להיות ירוקות והמערכת עדיין לא-סוחרת. 07-29 —
  **60 החלטות, 0 ירי, 29 מנצחות נחסמו** על ידי release-gate; כל בדיקת-צנרת הייתה ירוקה.
  L6 היא הבדיקה היחידה שמודדת "האם היא באמת עובדת" ולא "האם היא באמת חיה".
* **מה זה לא מוכיח:** שהשחזור עצמו נכון (אותם ברים, אותה גרסת-קוד — לא נבואה).

---

## ③ §2 — הדריל הסינתטי (SYNTHETIC FIRE DRILL) · הליבה

**המטרה:** להזריק setup מפוברק דרך ה-gateway **האמיתי** → sizing אמיתי → `command_from_setup`
אמיתי → `_write_command` → drainer → `trade_command.json` → **ה-DLL** → ACK → bracket →
`MODIFY_STOP` → `FLATTEN_ACCOUNT` → סגירה — ולאסוף ראיה בכל תחנה.
קובץ: **`scripts/selftest/synthetic_fire.py`** (עיבוד של `sim_matrix_e2e.py::_fire_cell`).

### 3.1 שער-הבטיחות — למה זה לא יכול לרוץ על LIVE
ארבע שכבות בלתי-תלויות; כל אחת לבדה מספיקה לעצור:

1. **דלת-הכניסה (backend):** `debug_gateway_fire` קורא `sierra_state.json`, ואם
   `is_sim != 1` — כולל כשלא הצליח לקרוא (`_is_sim = -1`) — מחזיר `403`. fail-safe מובנה.
2. **הצד של הבודק:** `_require_sim(stage)` קורא `is_sim` **מחדש מהדיסק לפני כל ירי**
   (לא פעם אחת בהתחלה) — כי מייקל יכול להעביר את סיירה ל-LIVE באמצע הריצה. `is_sim != 1`
   ⇒ `SystemExit` + `log_event(..., "CRITICAL", ...)`.
3. **טריות ה-`is_sim`:** להוסיף — אם `sierra_state.json` ישן מ-10 שניות, `is_sim` **לא
   קביל** (הקובץ נכתב בפעימת-שנייה של ה-DLL; קובץ ישן = ה-DLL לא רץ = לא יודעים כלום).
   `UNKNOWN` → עצירה. זה תיקון של פער אמיתי: היום `_require_sim` בודק ערך, לא גיל.
4. **נעילת-מכונה:** להוסיף — `MEMS26_SELFTEST_HOT=1` נדרש ב-`.env`, ומוגדר **רק במכונת-הסים**.
   מכונה שסוחרת LIVE לא מריצה L5 בכלל. (נכון ל-08-13 שני המקים רשאים LIVE במקביל, ולכן
   הנעילה חייבת להיות מפורשת ולא "מק-1 = סים" לפי הנחה.)

> ⚠️ **`op=EXIT` אסור בכל הדריל.** היציאות היחידות המותרות: ה-OCO המצורף (T1/T2/T3,
> צד-סיירה), `MODIFY_STOP`, ו-`FLATTEN_ACCOUNT`. שום נתיב חדש לא מתחבר ל-`write_exit`.

### 3.2 הרצף, תחנה-תחנה (כל תחנה = ראיה נצפית)

| # | פעולה | ראיה שנאספת | כשל = |
|---|---|---|---|
| 0 | `_require_sim("preflight")` + גיל `sierra_state.json` ≤10s | `is_sim=1`, `age=Ns` | ABORT (לא FAIL — לא בדקנו כלום) |
| 0b | תמונת-בסיס: `position_qty`, `working_orders`, `pending_command_count()`, mtime של `trade_command.json` | `baseline{}` | ABORT אם `position_qty != 0` (יש פוזיציה — לא נוגעים) |
| 1 | `POST /api/v9/trade/debug_gateway_fire?direction=LONG&stop_pts=8&sizing=full&pattern=SELFTEST` (Bearer `BRIDGE_TOKEN`) | `status ∈ {FIRED, FIRED_DIRECT}` + `trade_id` | FAIL `gateway_refused` (עם `blocked_by` — יכול להיות **תקין**, ראו §4) |
| 2 | ה-gateway בנה עסקה | שורה ב-`v9_trades` עם `mode='demo'`, `contracts == effective_contracts(setup)` | FAIL `no_trade_row` |
| 3 | ה-writer כתב | `command_queue/cmd_*.json` עם `op="PLACE"`, `contracts>0` (הגנת `K1e`) | FAIL `no_command_file` |
| 4 | ה-drainer שלח | `trade_command.json`.mtime > baseline | FAIL `drainer_dead` ← **זה היה תופס את K1a (08-07): התור לא התנקז והפקודות נעלמו** |
| 5 | ה-DLL אישר | `trade_result.json`.mtime > `_sent_ts`, `status != ORDER_FAILED` (אחרת: `error_text` מהמיפוי ב-`merged.cpp:3020`) | FAIL `no_ack` / `order_failed:<code>` |
| 6 | מילוי + סוגריים | `position_qty == contracts` **וגם** `working_orders == 2×qty == len(orders)` | FAIL `bracket_incomplete` ← מכסה את מחלקת האורפן-העירום |
| 7 | `write_modify_stop(stop_ids=[כל הסטופים])` | **כל** מחירי-הסטופ ב-`orders[]` שווים ל-`new_stop` | FAIL `modify_partial` ← מכסה את "הסטופ זז רק לחוזה אחד" |
| 8 | `write_flatten_account(trade_id=..., source="selftest")` | `position_qty == 0` **וגם** `working_orders == 0` תוך ≤20s | FAIL `flatten_failed` ← **בדיוק הבאג של #682** |
| 9 | רישום | שורת `"ENTRY"` ב-`trade_fills_journal.jsonl`, העסקה `CLOSED` ב-`v9_trades`, מופיעה ב-`/api/v9/trades/recent` | FAIL `not_registered` |
| 10 | **ניקוי — ב-`finally`, תמיד** | ראו 3.3 | ריצה שלא ניקתה = 🔴 CRITICAL + phone alert |

### 3.3 ניקוי (ה-`finally`, לא "בסוף אם הכל הלך טוב")
```
finally:
    1. FLATTEN_ACCOUNT (אידמפוטנטי) → polling עד position_qty==0 & working_orders==0,
       עד 30s. לא הגיע לשטוח → CRITICAL + phone_alert.push(priority=1) + exit 3.
    2. סימון העסקה: quality["selftest"]=True + reason="SELFTEST" → כל דוח P&L/סטטיסטיקה
       חייב לסנן WHERE (quality->>'selftest') IS NULL. אחרת הדריל מזהם את הלדג'ר.
    3. ניקוי התור: command_queue/*.json של הריצה → archived_stale/ (בשם selftest_*).
    4. שחרור סלוט: gateway.on_trade_close({...}) — אחרת הסלוט תפוס והמערכת לא תירה בפתיחה.
    5. שחזור .env אם שונה (ראו למטה) + כתיבת EVIDENCE JSON.
```
**שינוי מהמימוש הקיים:** `sim_matrix_e2e.py` כותב `DAY_TYPE_MANUAL_OVERRIDE` ל-`.env`
ומריץ `launchctl kickstart` — יקר מדי ומסוכן מדי לפרופיל pre-open. `synthetic_fire.py`
מקבל `--day-type` **רק** במצב `--nightly`, ואז חייב לעטוף ב-snapshot
(`scripts/mems26_snapshot.sh "selftest-daytype"`) ולשחזר ב-`finally`.
בפרופיל pre-open — **בלי נגיעה ב-`.env`, בלי restart.**

### 3.4 שינויים נדרשים בקוד קיים (קטנים, נקודתיים)
* `trade_commands.py:279` — הנתיב `/Users/michael/SierraChart_Data/v9_export/sierra_state.json`
  **קשיח**. להחליף ב-`signals_dir()` / `V9_EXPORT_DIR`, אחרת שער-הבטיחות מתנהג שונה בין מכונות.
* `debug_gateway_fire` — להוסיף `metadata["selftest"]=True` ל-setup, כדי ש-(3.3.2) יעבוד.
* `sierra_command.py` — לחשוף `last_sent_ts()` כדי שתחנה 5 תדע מול מה להשוות ACK.

---

## ④ §3 — כיסוי-חיווט: המנגנון שהיה תופס את ה-TypeError

### 4.1 `wire_guard` — כריכת-חתימה על כל call-site
**רעיון:** לחלץ ב-AST את חתימות משפחת ה-`write_*` (וכל משפחה מסומנת), לחלץ ב-AST את כל
ה-call-sites בייצור, ולנסות `inspect.Signature.bind(...)` על כל אחד. AST ולא import —
כי הקריאות בייצור הן **imports עצלים בתוך גוף-פונקציה**
(`from backend.v9.services.sierra_command import write_flatten_account` בתוך `if`),
ולכן גרף-import סטטי לא רואה אותן, ו-import אמיתי מושך fastapi/sqlalchemy ותופעות-לוואי.

**קובץ:** `scripts/selftest/wire_guard.py`. גרעין (נבדק — ראו 4.2):

```python
import ast, inspect, pathlib

FAMILIES = {                      # קובץ-מקור → קידומת-שם
    "backend/v9/services/sierra_command.py": "write_",
    "backend/v9/services/phone_alert.py":    "push",
    "backend/v9/services/exit_verifier.py":  "register",
}

def sig_from_ast(fn: ast.FunctionDef) -> inspect.Signature:
    a, P, params = fn.args, inspect.Parameter, []
    npos   = len(a.posonlyargs) + len(a.args)
    d_off  = npos - len(a.defaults)
    for i, arg in enumerate(a.posonlyargs + a.args):
        params.append(P(arg.arg,
                        P.POSITIONAL_ONLY if i < len(a.posonlyargs) else P.POSITIONAL_OR_KEYWORD,
                        default=P.empty if i < d_off else "…"))
    if a.vararg: params.append(P(a.vararg.arg, P.VAR_POSITIONAL))
    for arg, dflt in zip(a.kwonlyargs, a.kw_defaults):
        params.append(P(arg.arg, P.KEYWORD_ONLY, default=P.empty if dflt is None else "…"))
    if a.kwarg: params.append(P(a.kwarg.arg, P.VAR_KEYWORD))
    return inspect.Signature(params)

def check(root: pathlib.Path):
    sigs, bad, unbindable = {}, [], []
    for src, prefix in FAMILIES.items():
        mod = ast.parse((root / src).read_text())
        sigs.update({n.name: sig_from_ast(n) for n in ast.walk(mod)
                     if isinstance(n, ast.FunctionDef) and n.name.startswith(prefix)})
    for py in list((root/"backend").rglob("*.py")) + list((root/"scripts").rglob("*.py")):
        if "/tests/" in str(py):            # tests are allowed to probe bad shapes
            continue
        for node in ast.walk(ast.parse(py.read_text())):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
            if name not in sigs:
                continue
            if any(k.arg is None for k in node.keywords):   # **kwargs
                unbindable.append(f"{py}:{node.lineno} {name}"); continue
            try:
                sigs[name].bind(*["…"]*len(node.args),
                                **{k.arg: "…" for k in node.keywords})
            except TypeError as e:
                bad.append(f"{py}:{node.lineno}  {name}(...) → {e}")
    return bad, unbindable     # bad = 🔴 NO-GO · unbindable = ⚠️ needs an executing smoke test
```

### 4.2 הוכחה שזה תופס את הבאג ההיסטורי (Rule 5 — פלט גולמי, לא הצהרה)
```
# על הריפו כפי שהוא היום (אחרי התיקון של 08-15):
$ python3 scripts/selftest/wire_guard.py .
signatures found: ['write_cancel', 'write_exit', 'write_flatten_account',
 'write_flatten_orphan', 'write_modify_stop', 'write_modify_target',
 'write_place_bracket', 'write_trade_command']
call sites checked: 16
BAD: 0

# על עותק שבו הוחזרה צורת-הקריאה ההיסטורית (בדיוק זו של MAE_SCRATCH לפני 08-15):
#   write_trade_command(action="FLATTEN_ACCOUNT", context={"source":"mae_scratch","trade_id":"682"})
$ python3 scripts/selftest/wire_guard.py /tmp/proto/fake
call sites checked: 2
  MISBOUND: backend/v9/x/old.py:3  write_trade_command(...) → missing a required argument: 'trade_id'
BAD: 1
```
זמן-ריצה: פחות משנייה. אין תלויות מעבר ל-stdlib. **זו הבדיקה עם יחס עלות/תועלת הכי גבוה
במסמך הזה** — היא הייתה חוסכת את #682, את `TARGET_APPROACH_REALIZE`, ואת כפתור-החירום.

### 4.3 שלוש הגבלות שחייבות להיאמר בפה מלא
1. `wire_guard` מוכיח **חתימה**, לא **סמנטיקה**. `write_flatten_account(trade_id=x, source=y)`
   ייכרך יפה גם אם הקריאה במקום הלא-נכון.
2. קריאות עם `**kwargs` לא ניתנות לכריכה סטטית → מדווחות `unbindable` ודורשות
   **smoke מבצע** (L4) פר call-site. אין להן פטור.
3. `wire_guard` לא יודע אם ה-call-site אי-פעם **מגיע**. לכן מוני-ההגעה (L3-ב).

### 4.4 מוני-הגעה — `scripts/selftest/reach.py`
```python
# backend/v9/observability/reach.py
_HITS: dict[str, tuple[int, float]] = {}
def hit(tag: str) -> None:
    n, _ = _HITS.get(tag, (0, 0.0)); _HITS[tag] = (n + 1, time.time())
    try:  from scripts.ops_log import log_event; log_event("reach", "INFO", tag)
    except Exception: pass          # never break the caller
```
מותקן בכל נתיב שהיה יכול למות בשקט: `mae_scratch.flatten`, `target_realize.flatten`,
`mobile.flatten`, `exit_verifier.reemit`, `fill_poller.order_failed_retry`,
`reconciler.orphan_alert`, `phone_alert.push`, `risk_halt.trip`, `eod.flatten`.
דוח-הלילה: `GET /api/v9/selftest/reach` → כל תג עם `count` + `last_hit`.
🔴 `NEVER_REACHED` מאז ההתקנה = בדיוק הסימפטום של `TARGET_APPROACH_REALIZE`.
(הערה כנה: `NEVER_REACHED` אינו הוכחת-שבירה — יכול פשוט להיות שהתנאי לא קרה. לכן הוא
⚠️ DEGRADED ולא 🔴 NO-GO, **חוץ** מנתיבים שהדריל הסינתטי מפעיל בכוונה — שם הוא 🔴.)

---

## ⑤ ניקוד וסמנטיקת-שער — GO / DEGRADED / NO-GO

### 5.1 חמישה ערכים, לא שניים
| ערך | משמעות | דוגמה |
|---|---|---|
| `PASS` | הפרוב רץ, הראיה נצפתה | `trade_command.json` mtime עלה |
| `WAITING_MARKET` | **המערכת בריאה וממתינה** — לא כישלון | `blocked: awaiting b1_sellers` · `day_type=UNKNOWN` ב-09:05 · פיד "ישן" בשבת |
| `DEGRADED` | פגם אמיתי, לא-חוסם, עם הגבלה שמית | `phone_alert` בלי creds · `FLAG_INDEX` drift · `NEVER_REACHED` בנתיב שלא נבדק חם |
| `FAIL` | הפרוב רץ והראיה **לא** נצפתה | `wire_guard BAD>0` · `flatten_failed` · `endpoint.latest_ts != MAX(ts)` |
| `UNKNOWN` | **לא ניתן היה להעריך** | `sierra_state.json` בן 4 דקות · psql לא נענה · endpoint 500 |

**החוק שמונע את מחלקה B:** `UNKNOWN` **אינו** `PASS` ואינו `WAITING_MARKET`.
בקבוצה-הקריטית `UNKNOWN ≡ FAIL`. סוכן שרץ מסנדבוקס יקבל `UNKNOWN` על כל L1/L4/L5 →
NO-GO, ולא "ירוק".

### 5.2 ההבחנה internal-מול-market (הכללה של `mems26_arming_gate`)
הגישה של `arming_gate` נכונה עקרונית אבל שברירית: `_classify_block` מחפש מחרוזות
(`INTERNAL_KEYS`) בטקסט-סיבה חופשי, וכל טקסט חדש נופל ל-`market` = **ירוק שקרי**.
התיקון:
* ה-gateway/build-status יחזירו **`block_code` מפורש** מ-enum סגור, לצד ה-`reason` החופשי.
* `block_code` בקטגוריה `INTERNAL` (`five_min_bar_recency`, `cci_14_history`,
  `mode_context`, `fhb_eligible`, `day_type_known`, `auth_table_cell`, `bar_data`,
  `buffer`) → `FAIL`.
* `block_code` בקטגוריה `MARKET` (`awaiting_b1_sellers`, `swing_highs_found`,
  `session_gate_closed`, `no_setup`, `counter_trend_skip`) → `WAITING_MARKET`.
* **קוד לא-מוכר → `UNKNOWN`, לא `WAITING_MARKET`.** זה ההיפוך הקריטי מול היום.

**מערכת שממתינה ל-09:30 לעולם לא נצבעת אדום:** בפרופיל pre-open, `session_gate_closed`,
`day_type UNKNOWN`, `mode_context` חסר, וסטרימים "idle" — כולם `WAITING_MARKET` מעצם
ההגדרה (זה כבר מיושם ב-`arming_gate --preopen` וב-`post_restart_verify`, ונשמר).

### 5.3 קבוצות-קריטיות ופסק
```
CRITICAL   (כל FAIL/UNKNOWN → NO-GO):
  L0: flag_guard · env.sha match · DLL src==deployed · backend not-stale
  L1: bars_5min_woodies recency (RTH) · endpoint.latest_ts == DB MAX(ts)
  L3: wire_guard BAD == 0
  L4: writer→queue→drainer→command round-trip, כולל TTL ו-grace
  L5: (מכונת-סים בלבד) הדריל הסינתטי — כל 10 התחנות
  ---: position flat + no orphan + לא ננעל סלוט

IMPORTANT  (FAIL → DEGRADED עם הגבלה שמית, מסחר מותר בהיקף מוקטן):
  L2: fire_drill B/C · L6: replay-drift ≤ סף · phone/ntfy transport · reach NEVER_REACHED

INFO       (מדווח, לא משפיע): FLAG_INDEX drift · SYSTEM_INDEX drift · latency בתוך הסף
```
**הפסק:** `NO-GO` אם קיים FAIL/UNKNOWN ב-CRITICAL · `DEGRADED` אם רק ב-IMPORTANT
(ההגבלה מודפסת מילולית: *"מותר לסחור, ללא X"*) · `GO` אחרת.
`WAITING_MARKET` **לעולם** לא מוריד ציון.

### 5.4 חותם-פרובננס — בלי זה, אין דוח
כל ריצה כותבת `docs/reports/selftest/SELFTEST_<date>_<profile>_<host>.json` עם:
`hostname · git HEAD + dirty · env.sha · DLL src sha + deployed sha · backend PID + start_ts ·
is_sim + sierra_state age · DATABASE_URL host · profile · ts`.
**אם `hostname` אינו אחד משני המקים, או `DATABASE_URL` אינו localhost, או
`sierra_state.json` חסר — הדוח נחתם `UNTRUSTED` והפסק נכפה ל-`UNKNOWN`.**
זה החיסון המכני נגד מחלקה B (הדוח-מהסנדבוקס).

---

## ⑥ תקציב-זמן ולוח-זמנים

| פרופיל | מתי | תקציב | מה רץ | איפה |
|---|---|---|---|---|
| `heartbeat` | כל 60s ב-RTH | **≤3s** | L0 מקוצר (`is_sim`, staleness) · L1 recency · פוזיציה-מול-ספרים · `pending_command_count()` · `last_poll_age` · `reach` delta | LaunchAgent `com.mems26.selftest_hb`, תהליך נפרד — **לא** בתוך ה-backend (לולאת-מסחר חד-worker; פסיקת polling-floors) |
| `preopen` | 09:05 ET (יומיים-מסחר) | **≤4 דק'** | L0 מלא · L1 ארבעת הצירים · L2 (`fire_drill --no-live` + שלב D) · **L3 מלא (`wire_guard` <1s)** · **L4 מלא (tmpdir, בטוח גם ב-LIVE)** · L5 **רק אם `MEMS26_SELFTEST_HOT=1`** | על ה-Mac, דרך Desktop Commander — **לעולם לא מסנדבוקס** |
| `postrestart` | אחרי כל `launchctl kickstart` | ≤90s | `post_restart_verify` (a–e) + L0 + boot-line דגלים | Mac |
| `nightly` | 22:00 ET | **≤25 דק'** | הכל, כולל **L5 מלא על מכונת-הסים** (כל 6 סוגי-היום × FULL/REDUCED) · L6 (`e2e_fire_proof --date today` + replay-drift) · תת-סוויטת-הפיתיון (§7.7) · `reach` NEVER_REACHED | מכונת-סים |
| `weekly` | ראשון | ≤60 דק' | ה-nightly + `mems26_fingerprint` **דיפרנציאלי בין שני המקים** + מוטציות (§7.7) | שתיהן |

**מדוע `preopen` ≤4 דק':** מייקל חייב GO/NO-GO עם זמן לתקן לפני 09:30. הדריל הסינתטי המלא
(6 סוגי-יום, restart לכל אחד) חורג בהרבה — ולכן ה-preopen מריץ **תא-הוכחה אחד** (LONG/full,
בלי `.env`, בלי restart), וה-nightly מריץ את המטריצה. פיצול זה הוא ההבדל בין דריל שרץ
כל יום לדריל שאיש לא מריץ.

---

## ⑦ תוכנית-בנייה מתועדפת

| # | פריט | גודל | הכשל **הנמדד** שהוא היה תופס |
|---|---|---|---|
| 1 | **`scripts/selftest/wire_guard.py`** + חיבור כ-CRITICAL ל-`fire_drill` שלב A | **S** (חצי יום; אב-טיפוס כבר עובד, §4.2) | ה-`TypeError` של 08-15: MAE_SCRATCH סגר ספרים ב-$0 על SHORT 4 חי (−$83.75 + 58 דק' פוזיציית-רפאים) · `TARGET_APPROACH_REALIZE` שלא רץ מעולם · כפתור-FLATTEN בפלאפון ששלח כלום |
| 2 | **חותם-פרובננס + `UNKNOWN ≠ PASS`** ב-orchestrator `scripts/mems26_selftest.py` | **S** | דוחות-סנדבוקס ירוקים על מכונה מנותקת (מחלקה B) · `arming_gate` שמסווג סיבה לא-מוכרת כ-`market` |
| 3 | **L4 — round-trip של לולאת-הפקודות ב-tmpdir** (8 writers × 4 מסלולי-כשל) | **M** (יום) | K1a (08-07): התור לא התנקז מעולם → PLACE+CANCEL של #652 לא הגיעו ל-DLL · 110 פקודות שפגו בתור (T2) |
| 4 | **`synthetic_fire.py`** — עיבוד `sim_matrix_e2e` לתא-הוכחה יחיד + `finally` נקי + נעילת `MEMS26_SELFTEST_HOT` + טריות `is_sim` | **M** (יומיים) | מק-2 ישב יום-מסחר שלם בזמן שכל בדיקה הייתה ירוקה (08-13) · יום-הירי-המת של 07-08 (סטופ 1pt נפסל ב-A7 כל היום) · bracket חלקי → מחלקת האורפן-העירום (07-20/23) |
| 5 | **`reach.py` — מוני-הגעה** ב-9 הנתיבים השקטים + `GET /api/v9/selftest/reach` | **M** (יום) | `TARGET_APPROACH_REALIZE` = 0 הרצות אי-פעם · 12 התראות naked-stop קריטיות שמתו בלוג (07-27) · `phone_alert` שמת בשקט (08-12) |
| 6 | **`block_code` enum** ב-gateway/build-status + החלפת `_classify_block` הטקסטואלי | **M** (יום) | ירוק-שקרי ב-`arming_gate` על כל סיבת-חסימה חדשה שלא מכילה מחרוזת מ-`INTERNAL_KEYS` |
| 7 | **מרשם-מוטציות** `config/selftest_registry.yaml` + `--verify-mutations` (הזרקת פגם ← הבדיקה חייבת ליפול) + תת-סוויטה `pytest -m selftest` שחייבת 100% ירוק, שאר 576 הקבצים בהסגר | **L** (3–4 ימים) | 6 הטסטים הירוקים על קוד זורק (מחלקה A) · אי-אפשרות להשתמש בסוויטה כאות (מחלקה C) · 57 קבצי `inspect.getsource` |
| 8 | **חותם-בילד ל-DLL:** `study_build_ts` (`__DATE__ " " __TIME__`) + `src_sha` ב-`sierra_state.json` | **S** בקוד, **M** בפריסה (דורש Remote Build) | היום אין שום דרך לדעת שה-**בינארי הטעון** תואם ל-`.cpp`. `mems26_verify` משווה מקור בלבד ומדווח `wn` — 08-13 "המערכת לא מזהה את סיירה אחרי בילד" |
| 9 | **L6 — replay-drift** (`fires_live` Δ `fires_replay` יומי) | **L** (3 ימים) | 07-29: 60 החלטות / 0 ירי / 29 מנצחות נחסמו — כל בדיקת-צנרת ירוקה · 06-30: 0 עסקאות ביום-מגמה (family-gate over-block) |

---

## ⑧ מה **אי-אפשר** לבדוק אוטומטית — וצעד-האדם המחליף

אין להמציא כיסוי. אלה נשארים בני-אדם, ומופיעים בדוח כשורות `HUMAN` (לא PASS, לא FAIL):

| # | הדבר | למה לא אוטומטי | הצעד האנושי |
|---|---|---|---|
| 1 | **חימוש סיירה** (`EnableOrderPlacement`) ומעבר SIM↔LIVE | פסיקת-מייקל: *cowork לא מחמש — מייקל מחמש* (07-17). מכונה שמחמשת את עצמה היא משטח-סיכון | מייקל מחמש. האלגוריתם **צופה בלבד** ב-`order_placement_armed` + `send_orders_to_trade_service` מ-`sierra_state.json` ומדווח `HUMAN: armed=0` |
| 2 | **שהבינארי שנטען בסיירה הוא הבילד החדש** | Remote Build + reload study הם פעולות UI; אין היום חותם-בילד בייצוא | מייקל/CC מריץ Remote Build ומאשר reload. נסגר חלקית ע"י פריט 8 |
| 3 | **שסיווג-היום *נכון*** מול הצ'ארט | זו שיפוטיות של דלתון. אוטומציה יכולה למדוד יציבות/עקביות, לא אמת (הלקח של 07-31: לאמת תווית מול נרות) | מייקל מסתכל על הצ'ארט בבריפינג. האלגוריתם מדווח `HUMAN` + סטייה מול `classify_replay` |
| 4 | **כשירות ברוקר** (NLV/מרג'ין/loss-limit) | תלוי בצד השני של החוט | נצפה מ-`acct_available_funds`/`acct_under_margin`/`acct_loss_limit_reached`, מדווח כ-`HUMAN`. אירוע 07-28: המרג'ין החסר הוא היחיד שמנע 6 הוראות-אמת מטסט |
| 5 | **שהתבניות רווחיות** | זו שאלת-שוק, לא שאלת-מערכת | L6 נותן ראיה כמותית; ההחלטה של מייקל |
| 6 | **קיפאון פיד בגלל סיירה סגורה/הפסקת-CME** | חיצוני | `WAITING_MARKET` מפורש; התראה רק בתוך RTH |

---

## ⑨ מה **לא אומת** בכתיבת המסמך הזה (Rule 5, עלינו)

* **לא הרצתי psql.** הסנדבוקס הזה הוא לינוקס מבודד בלי Postgres.app ובלי גישה ל-DB של
  מייקל — ולכן **כל טענה על טריות/פערים ב-DB במסמך הזה היא עיצוב, לא מדידה.** זו בדיוק
  מחלקה B, ולכן היא מוצהרת ולא מוסתרת.
* **לא הרצתי את הסוויטה** (אין venv/תלויות בסנדבוקס). מספר ה-~487 כשלים לקוח מהתדריך,
  לא נמדד כאן. `find tests backend/v9/tests -name 'test_*.py' | wc -l` = **576** — זה כן נמדד.
* **`grep -rln "inspect.getsource" tests/ backend/v9/tests/ | wc -l` = 57** — נמדד.
* **`wire_guard`** — נמדד: 16 call-sites, 0 misbound היום; 1 misbound על שחזור הצורה
  ההיסטורית (§4.2). זו הראיה היחידה במסמך שהיא ריצה מלאה של המנגנון המוצע.

---

### נספח — פקודת-ההרצה המיועדת
```bash
# על ה-Mac (Desktop Commander), לעולם לא מסנדבוקס:
python3 scripts/mems26_selftest.py --profile preopen
#  → docs/reports/selftest/SELFTEST_2026-08-16_preopen_<host>.json
#  → שורה ל-docs/reports/OPS_LOG_2026-08-16.md
#  → exit 0=GO · 1=DEGRADED · 2=NO-GO · 3=CRITICAL (ניקוי נכשל / פוזיציה נשארה)
```

---
*נכתב 2026-08-16 · עיצוב בלבד, אפס שינויי-קוד · כל שינוי המוצע כאן שנוגע בזרימת-מסחר
דורש שער-אסטרטגי + אישור מייקל לפני מימוש (Pre-LIVE Discipline).*
