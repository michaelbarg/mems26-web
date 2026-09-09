# פקודה · 09.09 08:45 — הבנייה-מחדש. היום, בסדר הזה, ובצל לפני לייב

**מאת:** cowork-dev · **אל:** cc-macbook · **פסיקת-מייקל 09.09 08:40:** *"5 חוזים, פשוט שיסחור נכון… שהכל יהיה מוכן בשעות הקרובות."*
**הבסיס:** `docs/reports/DAY_AUDIT_*` (‏4 קבצים, 39 סשנים) · `S1_S2_SPEC_CONFORMANCE_2026-09-08.md` · `MEASUREMENTS.md`.

| שעה | מי | מה |
|---|---|---|
| עכשיו → **14:00** | cc | ‏§1 → §5 **בסדר הזה**. אם נגמר הזמן — מה שלמטה לא נכנס, מה שלמעלה כן |
| ‏14:00–15:00 | cowork | אימות מול פלט גולמי · מוטציות · `guard_tests` · `flag_guard` |
| **‏15:00** | — | **הקפאה.** ריסטארט אחד (cowork) ‏15:45 · שער 16:10 |

## ‏🔴 החוק של היום — כל מה שנוגע בכלכלת-העסקה נכנס במצב **`diff`**

**‏5 חוזים לייב על קוד שנכתב היום = הסיכון שכבר שילמנו עליו שלוש פעמים.** ולכן: כל רכיב ב-§2/§3 רץ היום **לצד** השרשרת הקיימת, מחשב מה **הוא** היה קובע, **רושם את ההפרש** על כל setup — **ואינו משנה את מה שנשלח.** מחר, עם ‏diff של יום שלם, מייקל פוסק. ‏§1/§4/§5 הם מדידה/צל/שער-קטן — נכנסים חיים.

---

## ‏§1 · פוסטמורטם עם סיבה בשם — **חי, אפס סיכון** (‏~1 שעה)

**המצב:** ‏54 עסקאות-לייב מפסידות, ‏24 עם PM (‏44%), ‏**‏61% מה-PM אומרים `NORMAL_NOISE`**. ‏`TIGHT_STOP` ירה **5 מ-307** בזמן שהסטופ החציוני הוא בר אחד. ‏#1224 (סטופ 2 נק' **בתוך** בר-הכניסה, נעצר ב-52 שנ') סווג `NORMAL_NOISE`.
**המקום:** `backend/v9/services/postmortem/analyzer.py` — הקטגוריות הקיימות: `NORMAL_NOISE · WRONG_CLASS · LATE_ENTRY · TIGHT_STOP · MANAGEMENT`.

**להוסיף שש סיבות מכניות, כל אחת = בדיקה מספרית על נתונים שכבר נשמרים, ולרוץ על 100% מעסקאות-הלייב המפסידות (לא 44%):**

| קוד | התנאי | המקור |
|---|---|---|
| `STOP_INSIDE_ENTRY_BAR` | ‏SHORT: `stop_initial <= high(entry bar)` · LONG: `stop_initial >= low(entry bar)` | `quality.metadata.stop_initial` מול `v9_bars_5min_woodies` בבר של `entry_ts` |
| `STOP_UNDER_ONE_BAR` | `abs(entry − stop_initial) < 1.0 × median(high−low)` של ברי-RTH של אותו יום | אותו |
| `TARGET_CUT_THEN_REJECTED` | `t1_pre_struct` קיים ∧ `abs(t1 − entry) < 0.5 × abs(t1_pre_struct − entry)` | `setup.t1_pre_struct` (נוסף אתמול, `trading_gateway.py:3427`) |
| `LATE_VS_SIGNAL` | `entry_ts − signal_bar_ts > 2 ברים` | `quality.metadata.signal_bar_ts` אם קיים; אחרת `_s2_ledger` |
| `NO_DAYTYPE_LABEL` | `day_type_at_entry IS NULL` ∧ `entry_ts > IB-lock` | `v9_trades` |
| `LABEL_DISAGREES` | `day_type_at_entry ≠ classify_replay(EOD)` | `classifier_core.classify_session` |

**סדר-עדיפות בסיווג:** מכני קודם, `NORMAL_NOISE` **רק אם אף אחד מהשישה לא תפס.** **קבלה:** `python3 -m backend.v9.services.postmortem.analyzer --backfill --live-losers` ⇒ ‏54/54 עם PM; ‏`NORMAL_NOISE` יורד מתחת ל-30%; ‏**‏#1224 ⇒ `STOP_INSIDE_ENTRY_BAR`**, ‏#1231 ⇒ `STOP_UNDER_ONE_BAR` (‏12.75 מול 8.75? — אם לא, `LATE_VS_SIGNAL`). **טסט** על #1224 עם הברים האמיתיים.

## ‏§2 · חוק 1 — רשות כלכלית אחת, במצב `diff` (‏~2 שעות)

**המצב:** ‏18:20 אתמול — S2 נתן `stop 7676 / t1 7711`; ‏`STOP ARBITRATION` ‏7676→7693.75; ‏`#68 structural` ‏7711→7703.25; ‏`STRUCT_TARGETS_WIN` דרס שוב; ‏`rr_hard_floor` פסל על 0.27. **חמישה כותבים:** `T1_STRUCTURE_END_V1` · `DAYTYPE_TARGETS_STRUCTURAL` (`:2972`) · `TARGET_ZONES_V1` (`:3244`) · `STEP_SCALED_LADDER_V1` (`:3306`) · `STRUCT_TARGETS_WIN_V1` (`:3377`) + `STOP_RESOLVER_V1` (`:2786`) + `TARGET_REALISM_V1` (`:3493`).

**לבנות `backend/v9/services/trade_economics.py`:** פונקציה טהורה אחת —
```
economics(setup, day_type, structure, bars) → {entry, stop, t1, t2, t3, source}
```
- **סטופ = העוגן שהיצרן חישב** (S2 מחשב `min/max(b1..b3)` ב-`five_min_system.py:1044/1114/1243/1275` **ואינו קורא אותו** — הנה הקורא) + `2T`; **אין דחיסת-ATR.** אם `risk > RISK_MAX_PTS_HARD` ⇒ `reject_reason="risk_exceeds_budget"` — **לא לדחוס.**
- **יעדים = טבלת S1** (`day_type/targets_table.py:32-131`, לפי `day_type`) על הסיכון **האמיתי**; ‏`t1` חייב להיות רמה מבנית אם יש (‏IB/VA/POC) ואחרת ‏R-multiple — **ותמיד על טיק 0.25**.
- **`TRADE_ECONOMICS_AUTHORITY_V1=diff`**: ב-`_route_setup_inner` **אחרי** כל הכותבים הקיימים ולפני `rr_hard_floor` — לחשב, ולרשום שורה אחת: `[ECON-DIFF] trade=… chain: stop/t1/t2/t3 = … | authority: … | Δ = …`. **לא לשנות את ה-setup.** ‏`=1` (לא היום) ⇒ הרשות **מחליפה** את השרשרת.
- **קבלה:** על ה-18:20 של אתמול (ריפליי מהברים) הרשות נותנת `stop 7676 / t1 ≥ 7711` ו-R:R ≥ 0.39. **טסט** עם ה-setup ההוא כפיקסטורה.

## ‏§3 · ‏S1 מתמחר, לא רק פוסל — `diff` (‏~45 דק', חלק מ-§2)

**המצב:** `S1_S2_SPEC_CONFORMANCE` — יעד `7721.875` (לא על טיק, 1.5R אריתמטי), `t2=2.00R` גנרי במקום 2.5R של Variation, **בזמן שהגייטוויי דחה את אותו setup "on Variation"**. ‏ו-`sierra_command.py:747-775` חותך 5 חוזים ל-`auth_table ≤ 3`.
**בתוך `economics()`:** ‏`day_type` נכנס כפרמטר; ‏`targets_table` היא המקור ל-R-multiples ולסטופ-זמן; ‏`contracts = min(ruled_contracts(), table.contracts(day_type))` — **ורושם** כשהטבלה חותכת את 5. **קבלה:** ה-diff מראה על Variation ‏`t2 = 2.5R`, לא 2.0.

## ‏§4 · שני היצרנים — צל (‏~1.5 שעות)

**המצב:** `AUDIT_VALUE_RETURN_REQUEST_2026-09-08.md` — מייקל ביקש 7 פעמים, כל פעם זה הפך לשער; ‏`accepted_break` מחושב ומשמש **רק** להרפות שערים.

| | טריגר (על בר **סגור**) | סטופ | יעד | מטא |
|---|---|---|---|---|
| **`VALUE_RETURN_V1`** | `day_type ∈ {Variation, Normal_Variation, Trend_*}` ∧ אחרי הרחבה ≥ `IB×0.5` ∧ **הבר הראשון שסוגר בחזרה לכיוון ה-POC המתפתח** (מ-`_load_sierra_tpo()`; `poc` חי) ∧ ווליום-הבר ≥ 0.8× ממוצע-5 | מעבר לקיצון-הרגל +2T | ‏POC, ואז הקצה הנגדי | `metadata.doctrine="VALUE_RETURN"`, `shadow_only=True` |
| **`BALANCE_DEPART_V1`** | `day_type ∈ {Normal, Neutral_*}` ∧ `accepted_break` (מ-`_resolve_live_cls()`) מאשר יציאה ∧ **בר-הקבלה** (סגירה מעבר לקצה, ווליום ≥ 1.2× ממוצע-הפאוזה) **או** הפולבק הראשון שמחזיק מחוץ למאזן | חזרה לתוך המאזן −2T | מהלך-מדוד = רוחב-המאזן | `doctrine="BALANCE_DEPART"`, `shadow_only=True` |

**מיקום:** מתודות `_maybe_value_return` / `_maybe_balance_depart` **ליד `_maybe_dalton_edge`** — **לא** בקן `FIRST_HOUR_TACTICAL`. **להוסיף לשניהם ל-`ALL_SESSION_DETECTORS` ב-`test_detector_placement.py` באותו קומיט.** **טסט דרך המתודה האמיתית** (הדגם: `test_re_acceptance_production_path.py`), מוטציה לכל תנאי. ‏`RULED_FLAGS`: `expected: "shadow"`, `ruled_by: מייקל`, `date: 2026-09-09`, note עם הציטוט. **‏`metadata.doctrine` הוא מה שיאפשר מחר פטור-לפי-סיבה במקום לפי-גיאומטריה.**

## ‏§5 · התווית — שני פריטים קטנים, חיים (‏~45 דק')

**‏5א · `NO_LABEL_NO_FIRE_V1=1`:** אחרי נעילת-IB (‏`tpo_sys.ib_locked`), setup לייב-כשיר עם `get_live_day_type() is None` ⇒ **מנותב לצל** עם `blocked_by="no_daytype_label"`. ‏20 מ-46 עסקאות ירו בלי תווית — הן נסחרו על שערים שרצו על `None`. לפני נעילה: ללא שינוי (התווית ארעית בהגדרה). **טסט + מוטציה.** ‏`RULED_FLAGS`: פסיקת 09.09 *"S1 צריכה לזהות… S2/S4 בתיאום"*.
**‏5ב · ה-IB = השעה הראשונה של RTH:** `DAY_AUDIT_07-07_to_07-24` — ב-5 מ-13 סשנים ה-IB של המנוע = טווח-הלילה (‏07-17: "IB" 66 נק' מול 29 אמיתי, ביטחון 100). **היום: מדידה בלבד** — סקריפט שמשווה `ib_high/low` של המנוע (‏`v9_day_type_history`) מול 12 ברי-RTH הראשונים, לכל סשן מ-07.07; לדווח כמה ימים סוטים ובכמה. **התיקון — מחר, אחרי המספר.**

---

## אימות-cowork 14:00 (מה שאני מריץ, לא מה שאתה מדווח)

`git status ⇒ ריק` · **‏§1:** `--backfill` ⇒ 54/54, ‏#1224 בשם · **‏§2/§3:** שורת `[ECON-DIFF]` על ריפליי-18:20 עם המספרים · **‏§4:** `test_detector_placement` ירוק **עם** שני החדשים ברשימה, טסט-ייצור + מוטציה · **‏§5א:** setup עם `None` אחרי נעילה ⇒ צל · `guard_tests` · `flag_guard` · `git log -1` ב-HEAD.

## אסור

להפוך `TRADE_ECONOMICS_AUTHORITY_V1` ל-`1` היום · לגעת ב-`RISK_BUDGET_USD`/`RISK_MIN_CONTRACTS`/`FIXED_CONTRACTS_5` · לכבות `SCALE_IN` (שתי מדידות סותרות — סוכן מודד עכשיו) · ריסטארט · קוד אחרי 15:00 · `op=EXIT` · טסט שמזין את הקלט ידנית כהוכחת-צינור.
