# אימות בלתי-תלוי לעבודת `cc-macbook` — שבת 29.08.2026

**המאמת:** cowork-dev · **מצב:** קריאה-בלבד על הייצור (אפס שינוי קוד/דגלים/.env/DB, אפס ריסטארט;
worktree זמני נמחק בסוף) · **HEAD בזמן הבדיקה:** `2411b696` · **בסיס להשוואה:** `7d1552f8`

## 0 · פסק כולל

| החוסם | ההצהרה | הפסק |
|---|---|---|
| **T-43** מודל-פוזיציה (`a7fbc934`) | "סטופים מ-avg_price + אימות-כמות + תיקון-סלוט" | 🔴 **לא עבר** — (א) מתקן את הפונקציה היחידה שלא יצרה את הבאג · (ב)+(ג) חיים-כברירת-מחדל בלי דגל · (ג) נבנה נגד השערה שכבר הופרכה |
| **T-41** הזנת-CVD (`205fbd1a`) | "נרמול-חותמת + חסינות-חלון" | ⚠️ **עבר חלקית** — הנרמול נכון ומאומת על נתוני-אמת (26 חורים → 1), אבל **בלי backfill**, מסלול-הייצור לא-מכוסה-בטסט, ותג-הכיסוי הוא חיווט-מת |
| **T-37** מקור-הכיוון (`585168f8`) | "apply ל-S1DayDir + הורדת-LSMA" | 🔴 **לא עבר** — טסט-הקבלה של 28.08 **אדום בתצורת-הייצור**; שובר 2 טסטי-רגרסיה קיימים; קריאת-DB בלי סינון-תאריך. **הדגל עצמו מגודר נכון** ✅ |
| **"25 טסטים ירוקים · 0 רגרסיות ב-34"** | — | 🔴 **שקר מדיד** — עם `.env` של הייצור: 24/1. מול בסיס: **+11 כשלים חדשים, 0 תוקנו** |

---

## 1 · הטבלה המלאה

### T-43 · `a7fbc934`

| # | הטענה | מה נמצא | פסק | הראיה הגולמית | הסיכון | התיקון הנדרש |
|---|---|---|---|---|---|---|
| 43-1 | "(א) מחיר-הייחוס לסטופים = `sierra.avg_price` … מונע את באג-28.08: סטופים ב-7745.50 מעל הממוצע 7740.83" | `_position_reference_price` נקראת מ**אתר אחד בלבד** — `_apply_smart_be_after_t1` (`manager.py:791`). לוג-הניהול מוכיח ש-**7745.50 נכתב ע"י `SWING_TRAIL`** ולא ע"י `SMART_BE`. חמישה מסלולי-סטופ נוספים ממשיכים לקרוא `trade.entry_price` גולמי | 🔴 | `v9_trade_management_log` #851: `18:57:11 SMART_BE {from:7764.5, to:7749.75}` → `19:13:18 SWING_TRAIL {from:7749.75, to:7745.5, source:'runner_trail_v2', be_floor:7749.75}`. אתרים לא-מתוקנים: `apply_structural_swing_trail` (1195) · `apply_trail_after_t1` (1246) · `apply_dynamic_struct_trail` (1347) · `_apply_stop_after_t2` (1542) · `apply_target_realism_perbar` (1055) | הבאג שמייקל ראה **נשאר**. גרוע מכך: `apply_structural_swing_trail:1197` מחשב `be_floor = entry ± tick` מ-`trade.entry_price` — כלומר גם כשההצבה-לפי-ממוצע כן קורית, הטרייל הלא-מתוקן דורס אותה בחזרה לרצפת-הפר-עסקה | להעביר את **כל חמשת** האתרים דרך `_position_reference_price`, או (עדיף, לפי פסיקת-T-90 "סטופ מבני אחד לפוזיציה הממוצעת") לרכז את חישוב-הסטופ לפונקציה אחת ברמת-פוזיציה |
| 43-2 | (א) היה מונע את 28.08 | **לא.** ב-11:57 ET (רגע ה-SMART_BE של #851) הייתה עסקה-חיה **אחת** — #853 נכנסה ב-12:01 ET. ⇒ `len(same_dir_trades) <= 1` ⇒ מחזיר `entry_price` ⇒ **פלט זהה-בייט למה שקרה בפועל** | 🔴 | `v9_trades`: #851 `entry_ts` 11:55 ET · #853 `entry_ts` 12:01 ET; `SMART_BE` #851 ב-18:57:11 IL = 11:57 ET | "התיקון" אינרטי על התרחיש שהוא נבנה בשבילו | ראו 43-1 |
| 43-3 | "(ב) אימות-רציף … עם חסימת-כניסות" | **לא מגודר-דגל, חי כברירת-מחדל, בלי רשומת-RULED_FLAGS.** נקבע ב-`sierra_position_reconciler.py:~933` — **לפני** בדיקת-הבעלות ב-`:967` | 🔴 | `grep -n RECONCILER_OWNERSHIP_AWARE_V1 .env` ⇒ `387:RECONCILER_OWNERSHIP_AWARE_V1=1`; `grep 'POSITION_MISMATCH\|CVD_WINDOW_MIN_PCT' config/RULED_FLAGS.yaml` ⇒ 0 שורות | **רגרסיה למחלקת 07-24.** פוזיציה-ידנית של מייקל (‏tm_qty=0, sierra≠0) מדליקה את החסם ⇒ **כל כניסות-הלייב של המערכת נחסמות**, בעוד ההיגיון-מודע-הבעלות — שנפסק בדיוק בשביל זה — מוריד את אותו מקרה ל-INFO ענף אחד אחר-כך. ב-27.08 מייקל החזיק 2 חוזים ידניים בזמן מסחר | להעביר את קביעת-`_position_mismatch_block` ל**אחרי** בדיקת-הבעלות ולא להדליק כשהמסקנה "לא-שלנו"; לגדר בדגל + רשומת-RULED_FLAGS |
| 43-4 | "(ב) … עד שההפרש נפתר" | הניקוי נמצא **רק** בתוך `if tm_qty == sierra_qty`. שלושה `return` מוקדמים עוקפים אותו: `"no Sierra position data"` (state ישן >10ש' **וגם** events ריק), `"TM query error"`, ו-`return True, hmsg` של phantom-heal | 🔴 | `sierra_position_reconciler.py:793` `return True, "no Sierra position data…"` · `:822` `return True, f"TM query error: {e}"` · `STATE_MAX_AGE_S = 10.0` (`:30`) | **נעילה שקטה:** אחרי הפרש בודד, קיפאון-פיד/‏DLL של >10 שניות משאיר את החסם דלוק ⇒ **יום ללא מסחר** בלי שאיש יידע. קיפאון-פיד הוא מחלקה מתועדת (I-40, 25.06, 07-17) | לנקות את החסם גם במסלולי-היציאה-המוקדמת, או להוסיף TTL (למשל ניקוי-אוטומטי אחרי N דקות ללא נתון) |
| 43-5 | "(ג) `live_slot` משתחרר רק ב-`position_qty==0`" | נבנה נגד השערה ש**כבר הופרכה בלוג-המשימות עצמו** ששימש כמקור-העבודה | 🔴 | `TASK_LOG.md:424`: "~~+חור-סלוט (PARTIAL שחרר)~~ **חור-הסלוט הופרך**"; DB: `v9_trades.quality` #851 = `{'scaled_in': True, 'scale_in_added': 2, 'scale_in_child_id': 853}` ⇒ #853 היא ילד-SCALE_IN, לא כניסה-שנייה | פתרון לבעיה שלא קיימת | לבטל את (ג), או לצמצם ל-latch עם timeout + בדיקת-בעלות |
| 43-6 | (ג) בטוח | ה-`return` המוקדם **סופי** — אין לולאת-בדיקה-חוזרת. אחרי שהסלוט לא-שוחרר, שום מסלול לא חוזר לבדוק | 🔴 | `trading_gateway.py:3811-3860` — שני ענפי ה-hold מסתיימים ב-`return` בלי תזמון-חוזר | פוזיציה-ידנית של מייקל, או רגל-OCO שנשארת רגע אחרי סגירה (`_sw > 0`), נועלת את הסלוט **עד ריסטארט** | להוסיף שחרור-מאוחר (בדיקה מחזורית ב-reconciler) + התניה על בעלות |
| 43-7 | "9 טסטים" | מחלקת `TestSlotRelease` (3 טסטים) **אינה בודקת קוד-ייצור**: מייבאת `TradingGateway` ולא קוראת ל-`on_trade_close`, ומשכפלת את התנאי בגוף-הטסט | 🔴 | `test_t43_position_model.py:230-243` — `assert sq == -3` ואז `assert gw.live_slot is not None` (טריוויאלי: שום דבר לא שינה אותו). `:265-268` — `force_free = outcome in ("CANCELLED",…)` מחושב **בטסט** | שלושת הטסטים עוברים גם אם קוד-הייצור נמחק לגמרי. **מבחן-מוטציה: לא** | לכתוב טסט שקורא ל-`on_trade_close` האמיתי |
| 43-8 | — | `_position_reference_price` מסנן `mode.in_(("live","demo"))` בלי `symbol` ובלי טווח-זמן | ⚠️ | `v9_trades` 10 ימים: `shadow 104 · live 30` — אין `demo` ⇒ הצל **לא** מזוהם. אבל עסקה-לייב תקועה ב-ACTIVE מיום קודם תדליק את מסלול-הממוצע שלא-בצדק | זיהום-הצל נשלל; שארית: עסקה-יתומה מיום קודם | להוסיף סינון סשן/סימבול |
| 43-9 | — | `position_mismatch_blocks_entry()` נבדק ב**אחד** משני אתרי-`_execute_live` | 🟡 | `grep -n '_execute_live(' trading_gateway.py` ⇒ `3630` (מכוסה) · `3697` (מסלול `on_bar_close`/RR — **לא מכוסה**). `RR_FIRE_SELECTION` לא ב-`.env` ⇒ רדום | רדום היום; יתעורר אם הדגל יידלק | להוסיף את הבדיקה גם ב-3697 |
| 43-10 | — | **חיובי:** החסימה **כן** נרשמת בפיד-ההחלטות, והצל **כן** ממשיך לרוץ | ✅ | `trading_gateway.py:809` `"live_blocked_by": result.get("live_blocked_by")`; `result["shadow"] = True` ב-`:3580` — **לפני** בלוק-החסימה ב-`:3616` | — | — |

### T-41 · `205fbd1a`

| # | הטענה | מה נמצא | פסק | הראיה הגולמית | הסיכון | התיקון הנדרש |
|---|---|---|---|---|---|---|
| 41-1 | "(א) נרמול … 28 שורות מול 38 ברים" | **הנרמול נכון וכיוון-העיגול מאומת מול הנתונים הגולמיים.** שורות-ה-`:59` הן שנייה **מוקדם**, לא "סוף-בר" — לכן עיגול-מעלה מדויק | ✅ | רצף גולמי 28.08: `06:29:59 → 06:35:00 → 06:39:59 → 06:45:00 → 07:00:00 → 07:04:59 → 07:10:00` (מרווחים 5m01s/4m59s לסירוגין) ⇒ `06:29:59 ≡ 06:30`. פילוח: `sec=0,min%5=0 → 1027` · `sec=59,min%5=4 → 304` · ווּדיס: `sec=0,min%5=0` בלבד | — | — |
| 41-2 | "החורים ייסגרו" | **מאומת מספרית על נתוני-אמת** | ✅ | 28.08 RTH 09:30-16:00 ET: ווּדיס 78 ברים · CVD 77 שורות · התאמה-גולמית **52 ⇒ 26 חורים** · אחרי-נרמול **77 ⇒ 1 חור** (בר-הפתיחה 09:30). 27.08: **26 ⇒ 0**. 25.08: 154 שורות → 77 סלוטים (77 התנגשויות — יום-הכפילויות T-112) | — | — |
| 41-3 | "התיקון חי" | **אין backfill.** 5,498 השורות הקיימות שומרות `:59` | 🔴 | `select min(ts),max(ts),count(*) from v9_bars_cumulative_delta` ⇒ `2026-04-21 … 2026-08-28 … 5498` | כל רפליי / מדידת-צל / **§D** על 25–28.08 עדיין רואה 26 חורים ליום. כל החלטה שתישען על מדידה-היסטורית של CVD תהיה שגויה | מיגרציית-נרמול חד-פעמית על הטבלה (עם snapshot לפני), ואז אימות-מחדש |
| 41-4 | "9 טסטים" | הנרמול **משוכפל** בשני קבצים; רק העותק הלא-נכון-לייצור נבדק | 🔴 | הטסטים קוראים ל-`history_loader._normalize_cvd_ts` בלבד. **מסלול-הייצור החי הוא `bars.py:1069-1080`** (ה-DLL דוחף דרך ה-API) — **אפס טסטים** | הטסטים ירוקים בזמן שהמסלול שבאמת רץ אינו מכוסה; שינוי באחד לא ייתפס | לחלץ את הנרמול לפונקציה אחת ולקרוא לה משני המקומות; טסט על `post_cumulative_delta` |
| 41-5 | "(ב) חסינות-חלון 90% עם תיוג-כיסוי" | לא מגודר-דגל: `CVD_WINDOW_MIN_PCT` **אינו ב-`.env`** ⇒ ברירת-המחדל 0.9 משנה התנהגות ללא env ובלי רשומת-RULED_FLAGS. מרפה את שומר-כלל-1 שנוסף במכוון ב-23.08 (A1) | ⚠️ | `grep CVD_WINDOW_MIN_PCT .env config/RULED_FLAGS.yaml` ⇒ 0 שורות. אחרי 41-2 הכיסוי ≈99-100% ⇒ הסף כמעט לא נוגע | מרפה שומר בתמורה לאפס-רווח (הכיסוי כבר מלא אחרי (א)) | להשאיר את (א) ולהחזיר את (ב) ל-100% — או לגדר בדגל + רשומת-פסיקה |
| 41-6 | "תיוג-coverage במקום None" | **חיווט-מת.** `coverage` נכתב ל-dict ואף אחד לא קורא אותו | 🔴 | `grep -rn '"coverage"' backend/v9/systems backend/v9/gateway` ⇒ שורה אחת: `five_min_system.py:815` (הכתיבה עצמה) | "כיסוי-חלקי בכנות" הוא תג שאיש לא רואה — ההחלטה יורדת בדיוק כמו על כיסוי-מלא | לחווט לצרכן (פיד-החלטות / איכות-סטאפ) או להסיר |
| 41-7 | — | עם חורים, `perbar_deltas` מערבב מרווחי 5 ו-10 דקות בלי סימון | ⚠️ | `perbar = [cums[i]-cums[i-1] …]` — שורות לא-סמוכות אחרי חור | צרכן שסופר "N מ-M ברים חיוביים" מקבל תשובה על סקאלה מעורבת | למלא חורים ב-`None` במקום לדחוס, או לחשוף את רשימת-ה-ts |
| 41-8 | "9 טסטים" | `test_28_08_scenario_with_fix` הוא **טאוטולוגיה** | 🔴 | `coverage = 28 / 38` ואז `assert coverage < 0.9` — אריתמטיקה על שני ליטרלים, אפס קוד-ייצור | טסט-הקבלה של התרחיש בודק כלום | להחליף בטסט על נתוני-28.08 האמיתיים |
| 41-9 | — | `test_cvd_point_parser` — שאותו CC בדיוק ערך (`parse_cvd_points`) — **נשאר אדום** | 🔴 | `FAILED tests/v9/services/test_history_loader.py::TestParsers::test_cvd_point_parser` | נגע בפונקציה והשאיר את הטסט שלה שבור | לתקן למפתח-הזמן החדש |

### T-37 · `585168f8`

| # | הטענה | מה נמצא | פסק | הראיה הגולמית | הסיכון | התיקון הנדרש |
|---|---|---|---|---|---|---|
| 37-1 | "מגודר — הדגל בשדואו" | **נכון ומאומת.** `_flag_on` לא כולל `shadow` ⇒ הבלוק החדש מדולג ⇒ המסלול-הכבוי זהה-בייט | ✅ | `.env:581 S1_DAY_DIRECTION_V1=shadow`; `trade_context.py:869` `_flag_on = _mode in ("1","true","yes","on","apply")`; `RULED_FLAGS.yaml:184 expected:"shadow"` ⇒ flag_guard ייכשל על הפעלה לא-מאושרת | — | — |
| 37-2 | "טסט: רפליי-28.08 — ה-ZLR של 17:21 עובר" | 🔴 **הטסט אדום בתצורת-הייצור.** ירוק **רק** כשהפלייבוק כבוי | 🔴 | `set -a; source .env; pytest …` ⇒ `AssertionError: ZLR LONG 17:21 should pass with UNDETERMINED, got SKIP` · `1 failed, 24 passed`. בלי `.env` ⇒ `25 passed`. בידוד: `DAYTYPE_PLAYBOOK=1` ⇒ נכשל · `=0` ⇒ עובר. `.env:79 DAYTYPE_PLAYBOOK=1`. `config/daytype_playbook.yaml:164` — `ZLR … Neutral_Extreme: SKIP` | **החוסם האמיתי של 17:21 היה ה-playbook, לא מקור-הכיוון.** T-37 לא פותח אותו. זה גם מתועד ב-TASK_LOG 28.08 21:07: "חסימות אחרונות = daytype_playbook (ZLR-שורט על Neutral_Extreme)" | להחליט: או לשנות את תא-הפלייבוק (פסיקה נפרדת), או לתקן את הטסט שיבטא את מה שהתיקון באמת עושה. **לא להצהיר שהחוסם נסגר** |
| 37-3 | "0 רגרסיות" | שובר **2 טסטי-רגרסיה קיימים** של אותו דגל | 🔴 | `FAILED tests/v9/regression/test_s1_day_direction_v1.py::test_flag_on_is_honest_when_no_break` · `::test_flag_on_ignores_garbage_direction` — שניהם `assert get_live_expansion() is None` ⇒ `AssertionError: assert {'dir':'UNDETERMINED','ref':'v9_day_type_state:fade_both(DOWN)'} is None` | הטסטים מקבעים את **כלל-1** (כישלון-כן > ערך-מסונתז). לשבור אותם בשקט = לבטל את הכלל | לעדכן את שני הטסטים במפורש עם ציטוט-הפסיקה החדשה, או לשנות את המימוש |
| 37-4 | "קורא את הוראת-הדלתון מ-`v9_day_type_state`" | השאילתה **`ORDER BY id DESC LIMIT 1` — בלי סינון תאריך ובלי בדיקת-טריות** | 🔴 | `trade_context.py:950-952` `"SELECT direction FROM v9_day_type_state ORDER BY id DESC LIMIT 1"` | ביום-ב' בבוקר, לפני הסיווג הראשון, זה מחזיר את **השורה של שישי**. אם היא `with_extension(DOWN)` — כיוון-יום שגוי נכפה על הפתיחה. זו בדיוק מחלקת "‏`CURRENT_DATE` שקרי אחרי חצות" מ-`COWORK_DAILY_READ` וכלל-2 | להוסיף `WHERE ts::date = today(ET)` + סף-טריות; None ⇒ `UNDETERMINED` |
| 37-5 | "הורדת-LSMA" | **אין שינוי-LSMA בדיף.** שום קוד-LSMA לא נגוע. ההשפעה מסתכמת ב"לא ליפול ל-LSMA בתוך הפונקציה הזו" | ⚠️ | `git show 585168f8 --stat` ⇒ `trade_context.py` + קובץ-טסט בלבד. `get_live_dir_bias` (מקור-ה-LSMA) לא נגוע, ועדיין נקרא ב-`trading_gateway.py:1256` תחת `RESPONSIVE_WITH_DAY_TREND_V1` | הכותרת "הורדת-LSMA" מבטיחה יותר ממה שנעשה | לנסח מחדש, או לבצע את ההורדה בפועל |
| 37-6 | "UNDETERMINED = בלי וטו" | **נכון — אבל לכן גם כמעט-אינרטי.** כל ארבעת הצרכנים מסננים `.get("dir") in ("UP","DOWN")` ⇒ `UNDETERMINED` מתנהג **זהה ל-`None`** | ⚠️ | `market_context.py:135` · `trading_gateway.py:1238` · `:1566` (`location_gate`) · `bar_level_detector.py:501` — כולם `in ("UP","DOWN")` | אין סכנת "וטו-על-הכל" ✅, אבל גם אין שינוי-התנהגות בשלושה מארבעת האתרים | לוודא שהערך אכן משנה משהו לפני §D |
| 37-7 | "7 טסטים (רפליי + תרחיש-נגד)" | **תרחיש-הנגד טאוטולוגי** | 🔴 | `test_counter_scenario_down_blocks_long` — הקביעה היחידה היא `assert result is not None  # Doesn't crash` | "LONG נחסם" לא נבדק בכלל | לכתוב קביעה על `verdict` |

---

## 2 · "25 טסטים ירוקים · 0 רגרסיות ב-34" — הבדיקה

**שיטה:** `git worktree add --detach /tmp/mems_base_7d1552f8 7d1552f8`, אותו `.env` בשני העצים,
`python3 -m pytest tests/ backend/v9/tests -q`, השוואת **שמות** הכשלים ב-`comm`.

```
בסיס 7d1552f8 : 460 failed, 5703 passed, 7 skipped, 2 xfailed  (161.44s)
HEAD  2411b696 : 471 failed, 5717 passed, 7 skipped, 2 xfailed  (166.06s)
comm -23 head_f.txt base_f.txt  ⇒  11 כשלים חדשים
comm -13 head_f.txt base_f.txt  ⇒  0 כשלים שתוקנו
```

**11 הכשלים החדשים:**

```
backend/v9/tests/test_fix12_smart_be_fallback.py::test_long_structure_wider_falls_back_to_be
backend/v9/tests/test_fix12_smart_be_fallback.py::test_never_widen_still_holds
backend/v9/tests/test_fix12_smart_be_fallback.py::test_short_structure_wider_falls_back_to_be
backend/v9/tests/test_fix12_smart_be_fallback.py::test_structure_that_tightens_still_wins
backend/v9/tests/test_t37_direction_source.py::TestScenario28Aug::test_zlr_long_1721_passes_with_undetermined
backend/v9/tests/test_zlr_mgmt_v1.py::test_b_non_zlr_unchanged_when_on
backend/v9/tests/test_zlr_mgmt_v1.py::test_d_non_zlr_post_t1_unchanged_when_on
backend/v9/tests/test_zlr_mgmt_v1.py::test_d_zlr_post_t1_flag_off_is_be_plus_1t
backend/v9/tests/test_zlr_mgmt_v1.py::test_d_zlr_post_t1_short_mirror_when_on
backend/v9/tests/test_zlr_mgmt_v1.py::test_d_zlr_post_t1_stop_to_entry_be_when_on
tests/v9/regression/test_s1_day_direction_v1.py::test_flag_on_ignores_garbage_direction
tests/v9/regression/test_s1_day_direction_v1.py::test_flag_on_is_honest_when_no_break
```

**השורש של 8 מהם:**

```
E  AttributeError: 'TradeManager' object has no attribute '_db'
   backend/v9/services/trade_manager/manager.py:791: AttributeError
```

**הערכת-חומרה מדויקת:** זו **לא** תקלת-ייצור — `TradeManager.__init__` מציב `self._db = db`
(`manager.py:196`). הכשל הוא בכפילי-הטסט (`_mk_manager` בונה stub בלי `_db`). **אבל** התוצאה
המעשית: **8 טסטים קיימים ששומרים על מסלול ה-BE/הסטופ כבר לא רצים בכלל** — רשת-הרגרסיה מעל
הצבת-הסטופ נקרעה, יומיים לפני יום-מסחר חי. בנוסף `self._apply_smart_be_after_t1(trade)`
(`manager.py:685`) **אינו** עטוף ב-`try/except`, ו-T-43 הכניס לתוכו שאילתת-DB חדשה במסלול-החם
של T1 — מצב-כשל שלא היה שם קודם.

**"25 ירוקים":** נכון רק **בלי** `.env` של הייצור.

```
בלי .env                       :  25 passed in 1.07s
set -a; source .env; set +a    :  1 failed, 24 passed in 1.13s
```

**שלושת האדומים הידועים — כולם עדיין אדומים:**

```
FAILED tests/v9/systems/test_daytype_playbook.py::test_zlr_skip_on_normal_ruling_2026_08_12
FAILED tests/v9/regression/test_playbook_inversion_2026_08_12.py::test_zlr_skip_on_normal_and_neutral
FAILED tests/v9/services/test_history_loader.py::TestParsers::test_cvd_point_parser
3 failed, 2 warnings in 0.28s
```

---

## 3 · ארבעת ממצאי-הביקורת-העצמית

| ממצא | מצב | הראיה |
|---|---|---|
| **SA-3 / F3** — `DIRECTION_CONTEXT=0` סוגר בלוק בן ~196 שורות שמכיל את אתר-החסימה היחיד של `cont_trend_filter` ואת שני אתרי-`_compass_or` | 🔴 **לא טופל** | `trading_gateway.py:1668` עדיין `if os.getenv("DIRECTION_CONTEXT","0")…`; `cont_trend_filter` נאכף רק ב-`:1781`; `_compass_or` נקרא רק ב-`:1708` ו-`:1792` — כולם בפנים. `.env`: `CONT_TREND_FILTER=1` · `DIRECTION_COMPASS_V1=1` · `NEUTRAL_RESPONSIVE_V1=1` · `NORMAL_ROTATION_FIX_V1=1` — **4 דגלים פסוקים-ON בלתי-נגישים**. `flag_guard` עדיין מדפיס "all ON flags have ≥1 production read-site" |
| **SA-7 / F4** — הווטו הבינארי של הפתיחה משווה למחרוזות שהייצור לא מייצר | 🔴 **לא טופל** | `opening_entry.py:425-426` ללא שינוי. `grep -rn "OPEN_DRIVE_DOWN\|OPEN_DRIVE_UP\|TEST_DRIVE_DOWN\|TEST_DRIVE_UP" --include=*.py --include=*.yaml .` ⇒ **אפס אתרי-ייצור** — רק התנאי עצמו + `test_binary_gates_sites.py`. המפיק: `market_context.py:31` מתעד `OPEN_DRIVE / TEST_DRIVE / ORR / AUCTION_IN / AUCTION_OUT / UNKNOWN`, וה**כיוון בשדה נפרד** `opening_dir` (`:116-118`), שנזרק. `.env:447 OPENING_FIRST_TRADE_STRICT_V1=1` ⇒ **הווטו חוסם אפס מקרים** |
| **SA-8** — ריצוד-תווית | 🔴 **לא טופל** | `.env:256 DAYTYPE_RECLASS_STABILITY_V1=0`. `git diff 7d1552f8..2411b696 --stat` ⇒ 12 קבצים, אף אחד לא נוגע ביציבות-תווית |
| **F7** — רשומות-כפולות סותרות ב-`RULED_FLAGS.yaml` | ✅ **נסגר** — אבל ע"י cowork (`8d8681bc`), לא ע"י cc | פרסור עם ה-regex של flag_guard: `total 218 · unique 214 · dups {STRUCTURAL_TARGETS_WRONG_SIDE_VETO_V1:2, FIXED_CONTRACTS_3:2, RISK_DAILY_LOSS_CAP:2, TARGET_MIN_SPACING_V1:2}` — שלוש הסותרות (`DIRECTION_CONTEXT` / `LSMA_FLAT_GATE_V1` / `DAYTYPE_RECLASS_STABILITY_V1`) נעלמו; ארבע הנותרות אינן סותרות |

---

## 4 · בטיחות-אינטגרציה

| בדיקה | תוצאה |
|---|---|
| `python3 scripts/flag_guard.py` | ✅ `FLAG-GUARD: PASS — all 214 ruled flags match` (exit 0) |
| `python3 scripts/fire_drill.py` | 🔴 `NO-GO — 2 כשלים` — (1) `task_log_guard`: *"T-126 is marked ✅ but has no line in STATUS_BOARD.md"* (2) `feed טרי (<30s): age=64519485ms` (סופ"ש — צפוי). שלב B/C ירוקים · `effective_contracts == 3` · `wire_guard 53 call sites` ✅ · `live_slot פנוי` · `live_enabled == [2,4]` |
| `git status` | נקי מקוד. 4 קבצי-דוקומנטציה/קונפיג משתנים (`config/news_calendar.yaml`, `docs/handoff/PHONE_THREAD.jsonl`, `docs/reports/postmortem/PM_1.md`, `PM_2.md`) — **לא** מהקומיטים של cc |
| `.env` שונה? | **לא.** cc לא נגע. `S1_DAY_DIRECTION_V1=shadow` תקין. אפס דגלים חדשים |
| `TODO`/`FIXME` חדשים | **אפס** — `git diff 7d1552f8..2411b696 -- '*.py' \| grep '^+.*\(TODO\|FIXME\|XXX\|HACK\)'` ⇒ ריק |
| חיווט-מת | **כן** — `coverage` ב-`five_min_system.py:815`, אפס צרכנים |
| שורה ב-`STATUS_BOARD.md` | 🔴 **חסרה.** הרשומה האחרונה היא של cowork מ-28.08 23:55. CLAUDE.md: *"סגרת? ל-✅ **וגם** שורה מאומתת ב-STATUS_BOARD.md"*. כותרת ה-TASK_LOG מכריזה ✅ בעוד שורת-הפריט (`:424`) עדיין `🔴 פתוח` |
| רשומות `RULED_FLAGS` להתנהגות החדשה | 🔴 **אפס.** T-43 (א)(ב)(ג) לא-מגודרים; `CVD_WINDOW_MIN_PCT` לא רשום |

---

## 5 · רשימת-התיקונים לפני פתיחת יום-ב', לפי סדר

| # | מה | למה עכשיו | מי |
|---|---|---|---|
| 1 | **לבטל או לגדר-בדגל את T-43(ב) ו-T-43(ג)** — שניהם חיים-כברירת-מחדל, שניהם יכולים לעצור מסחר ליום שלם בשקט (חסם-נעול / סלוט-נעול), ו-(ג) נבנה נגד השערה מופרכת | סיכון-אי-מסחר חדש שלא היה שם ביום שישי | cc בונה · cowork מאמת |
| 2 | **T-43(ב): להעביר את הדלקת-החסם ל-אחרי בדיקת-הבעלות** + ניקוי במסלולי-היציאה-המוקדמת (או TTL) | פוזיציה-ידנית של מייקל תחסום את המערכת; רגרסיה לפסיקת 07-24 | cc בונה · cowork מאמת |
| 3 | **לתקן את 8 טסטי-ה-`_db`** (`test_fix12_smart_be_fallback` + `test_zlr_mgmt_v1`) | רשת-הרגרסיה מעל הצבת-הסטופ קרועה; בלעדיה אין דרך לדעת אם שינוי-סטופ הבא שובר משהו | cc בונה · cowork מאמת |
| 4 | **T-37: לתקן את 2 טסטי-הרגרסיה של `S1_DAY_DIRECTION_V1`** (או לשנות את המימוש) + להוסיף סינון-תאריך/טריות לשאילתת `v9_day_type_state` | טסטי-כלל-1 אדומים בשקט; קריאת-שישי-ביום-ב' היא באג-כיוון בפתיחה | cc בונה · cowork מאמת |
| 5 | **לתקן את הצהרת-הסטטוס:** T-43 ו-T-37 **אינם סגורים**. לעדכן TASK_LOG + להוסיף שורת-STATUS_BOARD מאומתת (ממצא→תיקון→ראיה); `fire_drill` NO-GO גם על `task_log_guard` | ההצהרה הנוכחית תגרום למייקל לפתוח את יום-ב' בהנחה ששלושת החוסמים נסגרו | cowork |
| 6 | **SA-3:** להוציא את `CONT_TREND_FILTER` ואת `_compass_or` מהבלוק המת של `DIRECTION_CONTEXT` | 4 דגלים פסוקים-ON מתים; כניסות-המשך של INITIATIVE יורות בלי מסנן-מגמה | cc בונה · cowork מאמת |
| 7 | **SA-7:** להעביר `direction` ל-`opening_first_trade_ok` ולהשוות `(opening_type, direction)` | אין היום שום הגנת-כיוון בפתיחה | cc בונה · cowork מאמת |
| 8 | **T-41: מיגרציית-נרמול על 5,498 השורות ההיסטוריות** (עם snapshot) | בלעדיה §D וכל רפליי-CVD ימשיכו להימדד על 26 חורים ליום | cowork |
| 9 | **T-43(א): להעביר את חמשת מסלולי-הסטופ הנותרים** דרך `_position_reference_price` (ובראשם `apply_structural_swing_trail`, שהוא זה שכתב את 7745.50) | הבאג שמייקל דיווח עליו עדיין שם | cc בונה · cowork מאמת |
| 10 | לאחד את שני מימושי-נרמול-ה-CVD לפונקציה אחת + טסט על `bars.py` · לחווט או להסיר את תג-`coverage` · לתקן `test_cvd_point_parser` · להחזיר את `CVD_WINDOW_MIN_PCT` ל-1.0 או לרשום פסיקה | חוב-איכות; לא חוסם פתיחה | cc |

---

*כל הפקודות הורצו על ה-Mac דרך Desktop Commander. ה-worktree הזמני (`/tmp/mems_base_7d1552f8`)
נמחק ב-`git worktree remove --force` + `prune`; `git status` וה-`HEAD` (`2411b696`) זהים לפני ואחרי.*
