# ביקורת סטופ + מימוש — 2026-08-17 (טרום-פתיחה)

**משימת מייקל (מילולית):** "לוודא שאין בעיה עם הצבת סטופ ומימוש ושהן פועלים בהתאם להנחיות."

**מבצע:** cowork-dev · **מכונה:** mac-1 (מכונת-המסחר, backend חי על localhost:8000)
**מצב:** READ-ONLY מלא — לא שונה קובץ-קוד, לא שונה דגל, לא בוצע ריסטארט, לא נכתב ל-`~/SierraChart_Data`.
**נכתב:** 2026-08-17 ~04:40 IL · פתיחת שוק 16:30 IL

---

## פסק-דין

### (A) הסטופ מוצב איפה שהפסיקות אומרות?  **לא — חלקית בלבד.**
הסטופ אכן נבנה ממבנה נר-5-דקות, וכל 4 החוזים מקבלים סטופ ב-DLL. אבל:
1. **StopResolver אינו הבעלים האחרון של הסטופ.** `STEP_SCALED_LADDER_V1` רץ 363 שורות אחריו באותה פונקציה ודורס את התוצאה שלו ללא תיאום וללא לוג-ארביטרז'.
2. **ריווח-העוגן 16T (פסיקת 07-23) לא מגיע לרזולבר של הגייטוויי** — שם רץ ברירת-מחדל 6T. שני ריווחים שונים חיים באותה עסקה.
3. **3 מתוך 42 עסקאות-לייב חרגו מתקרת-25-הנקודות** שנפסקה (#536 37.25 · #575 39.75 · #581 43.00). #581 גם קיבל 2 חוזים במקום 1 שה-`contract_ladder` מחייב מעל 25 נק'.

### (B) המימוש מתבצע כמו שהפסיקות אומרות?  **לא — יש שתי בעיות אמיתיות.**
1. **סולם-היעדים לא-מונוטוני ב-10 מתוך 42 עסקאות (24%)** — 6 הפוכות (T2 קרוב יותר מ-T1 ⇒ חוזה-2 מממש לפני חוזה-1 ובפחות) ו-4 קרוסות (T1==T2 בדיוק ⇒ אין ראנר בכלל).
2. **"BE אחרי T1" לא קרה ב-3 מתוך 22 העסקאות שהגיעו ל-T1** (#566 · #625 · #657) — וזו לא תקלה, זו **סתירת-פסיקות חיה** (ראה §3).

### שתי חסימות שנוצרו ב-24 השעות האחרונות (שתיהן נכנסות לסשן של היום)
- 🔴 **BLOCKER-1:** ה-dedup החדש בולע את ניסיון-החוזר של סטופ-עירום (W3).
- 🔴 **BLOCKER-2:** `exit_verifier` דורש `position_qty == 0` **ברמת-החשבון** — וכרגע יש בחשבון פוזיציה-ידנית של 8 חוזים.

---

## 0. מצב-החשבון בזמן הביקורת (04:33 IL)

`~/SierraChart_Data/v9_export/sierra_state.json`:
```json
{"is_sim":0,"position_qty":8,"avg_price":7813.25,"open_pnl":-40.00,
 "trade_account":"37138283","working_orders":1,
 "orders":[{"id":10232,"type":3,"bs":2,"price":7809.50,"qty":8}],
 "acct_account_value":2875.49,"acct_available_funds":674.61,"acct_margin_req":2200.88}
```
- **פוזיציה-ידנית חיה של 8 חוזים LONG** עם סטופ עובד ב-7809.50. מקור: `TradeActivityLog_2026-08-17_UTC.37138283.data` — `"Trade DOM/User order entry"` + `Username:MichaelBarg` ⇒ כניסה ידנית של מייקל, לא של המערכת.
- `trade_activity_events.jsonl` שורה אחרונה: `CLOSED_TRADE_PNL −150.0 @ 2026-08-17T01:34:45Z` — כבר −$150 הלילה מהמסחר-הידני. ה-`daily_pnl` בספרים = 0.00, כלומר **RISK_HALT לא רואה את ההפסד הזה**.
- `v9_trades`: אפס עסקאות פתוחות (`state not in CLOSED/CANCELLED` → 0 שורות). כלומר המערכת שטוחה בספרים והחשבון מחזיק 8.
- ה-reconciler **שותק** — נכון לפי `RECONCILER_OWNERSHIP_AWARE_V1=1` (פוזיציה בלי order-map = ידנית = INFO). זו התנהגות מאושרת.
- **מרג'ין:** פנוי $674.61 מול $275/חוזה ⇒ **מקום ל-2 חוזים בלבד**. `MARGIN_AWARE_SIZING_V1=0` (פסיקת 08-13 "1:1"), ולכן המערכת תשלח 4 והברוקר עלול לדחות. זה בדיוק תרחיש 6 הדחיות של 07-28.

---

## 1. טבלת-החוקים (STEP 1) — מה ההנחיות באמת אומרות

| # | החוק | מקור |
|---|---|---|
| R1 | סטופ = קיצון-מבנה על חלון ברים-**סגורים**, מאחורי הקיצון (לא בר-בודד) | `STRUCTURAL_STOP_ORIGIN_V1` + `STOP_STRUCTURE_EXTREME_V1` + `STOP_WINDOW_COMPLETED_V1` (פסיקות 07-20/07-21/07-22) |
| R2 | חלון-מבנה = 12 ברים סגורים | `stop_anchors.yaml:17 structure_window_bars: 12` |
| R3 | ריווח מאחורי הקיצון = **16 טיקים** (גובר על 6 שב-yaml) | `STOP_ANCHOR_OFFSET_TICKS_OVERRIDE=16`, פסיקת 07-23 (כיול-32-סשנים P=0.99) |
| R4 | StopResolver = המעצב **היחיד** של הסטופ | `STOP_RESOLVER_V1`, פסיקת 07-05 + memory "StopResolver=מעצב" |
| R5 | רצועה: `[0.5×ATR .. cap×ATR]`, מבנה מנצח בתוך הרצועה, מינימום מוחלט 2 נק' | `TRADING_SPEC.yaml` STOP-1 + `MEMS_MIN_RISK_POINTS=2` |
| R6 | רצפת-סטופ 0.8×ATR בימי Variation/Neutral/**Normal**; מגמה 0.5 | `STOP_FLOOR_ROTATION_ATR=0.8` (החלטה 5/6, 07-15) + `NORMAL_ROTATION_FIX_V1` |
| R7 | תקרת-סיכון גלובלית 25 נק' + סולם-חוזים (≤15→3 · ≤25→2 · >25→1) | `stop_anchors.yaml risk_cap_points: 25` + `contract_ladder` |
| R8 | תקרת-סיכון פר-תבנית (ZLR 15 · VEGAS 20 · FAMIR 12 …); CONT→SIZE_DOWN, REV→SKIP | `PATTERN_RISK_CAPS`, פסיקת 06-12 |
| R9 | סטופ = `max(4, 0.6×מדרגה-חציונית)`, יעדים 0.5/1.0/1.5×מדרגה — **במקום ATR עיוור** | `STEP_SCALED_LADDER_V1`, פסיקת 08-12 |
| R10 | אחרי T1: סטופ ל-**BE+טיק** ונשלח לסיירה בפועל (לא רק DB) | `TRADING_SPEC` STOP-2 + `stop_anchors.yaml:72 be_after_t1: breakeven_plus_1tick` (Table C §6.1) |
| R11 | אחרי T1: סטופ ל**מבנה הקרוב — לא BE מכני**; never-widen; fallback BE+1T | `STOP_STRUCTURE_TRAIL_V1`, פסיקת 07-08 |
| R12 | בכל בר אחרי T1 — בדיקת עוגן-מבנה מתגלגל, **מקרב-בלבד** | `STOP_PERBAR_STRUCT_V1`, פסיקת 07-10 |
| R13 | ראנר: טרייל `hwm − 1.0×risk` / re-anchor על קונסולידציה חדשה | `RUNNER_TRAIL_V1` + `DYNAMIC_STRUCT_TRAIL` |
| R14 | ZLR/S4: T1=2c · T2=1c · אפס-סטופ-לפני-T1 · אחרי-T1→BE | `ZLR_MGMT_V1`, פסיקת 07-14 |
| R15 | `op=EXIT` **שבור ואסור**. יציאות: OCO מוצמד (T1/T2/T3) · MODIFY_STOP · FLATTEN_ACCOUNT בלבד | CLAUDE.md (07-13) + `STALL_EXIT`/`OPPOSITE_EXIT_V1` = OFF |
| R16 | SCALE_IN: child +2 חוזים אחרי T1, **הסטופ של ה-child ב-BE של ההורה**, תקרה 8, פעם-אחת | `SCALE_IN_V1`, פסיקת 08-13 |
| R17 | סולם 6 חוזים = t0:1 · t1:2 · t2:2 · t3:1 | פסיקת 08-16, commit `7bce3afb` |
| R18 | הספרים נסגרים **רק** אחרי שסיירה מוכיחה שהפוזיציה נסגרה | `EXIT_VERIFY_V1`, פסיקת 08-14/15 |
| R19 | T1 בסוף מבנה-הכניסה (חלון 12 ברים); בנק ב-1.5R | `T1_STRUCTURE_END_V1` + `T1_BANK_R=1.5` |
| R20 | אין יעד מעבר ל-IB ביום שאינו נייטרלי/מגמתי | `TARGET_STRUCTURE_CLAMP_V1`, TP-1 |

---

## 2. אימות מול הקוד שרץ בפועל (STEP 2)

מסלול הכניסה שרץ באמת (אומת מ-`backend/main.py`, לא מ-`backend/v9/main.py`):

```
S2 five_min_system.py  |  S4 woodies_system.py
   עוגן 12 ברים, 16T   |     STOP_TICKS + widen-to-structure + pattern caps
              ↓ pre_fire_validator.validate_fire (min 2pt, RR≥1)
   trading_gateway.py:2044  STOP_RESOLVER_V1   → setup["stop"] = דריסה #1
   trading_gateway.py:2407  STEP_SCALED_LADDER → setup["stop"] = דריסה #2  ← הכותב-האחרון מנצח
              ↓ sierra_command.py:844 → DLL merged.cpp:2901 → 4 קבוצות OCO
```

| חוק | ציון | ראיה |
|---|---|---|
| R1 | **PARTIAL** | חלון-סגורים אמיתי ב-S2 (`five_min_system.py:1580` `_det_buf = self._bar_buffer[:-1]`). **ב-S4 אין בדיקת `STOP_WINDOW_COMPLETED_V1` בכלל**, וההערה `woodies_system.py:799` ("buffer holds CLOSED bars") מוכחשת ע"י הכותב עצמו `woodies_system.py:424` `self._bar_buffer[-1] = wb  # update latest with fresh OHLC`. הרזולבר בגייטוויי `trading_gateway.py:2052` שולף `ORDER BY ts DESC LIMIT 12` בלי סינון בר-מתהווה. |
| R2 | **IMPLEMENTED (כניסה) / CONTRADICTED (אחרי T1)** | בכניסה 12 ✓. אחרי T1 `manager.py:855` `_win = int(os.environ.get("STOP_STRUCT_WINDOW_BARS", "8"))` — **8 ברים**, ולא קורא את ה-yaml. |
| R3 | **CONTRADICTED** | ה-override נקרא ומוחל ב-`config_loader.py:352-357` (עוקף במכוון את `anchor_offset_ticks_max: 6`), ומגיע לגלאים בלבד. `trading_gateway.py:2113` קורא ל-`_sr_resolve(...)` **בלי `offset_ticks`** ⇒ נופל ל-`stop_resolver.py:53 offset_ticks: int = 6`. הטרייל-הדינמי מקודד 3T קשיח (`manager.py:1188`). **שלושה ריווחים שונים חיים במקביל: 16 / 6 / 3.** |
| R4 | **CONTRADICTED** | 5 מסלולים כותבים סטופ מחוץ לרזולבר. העיקרי: `trading_gateway.py:2430` `setup["stop"] = _ssl["stop"]`. |
| R5 | **PARTIAL** | הרצועה קיימת ב-`stop_resolver.py:86-88`, אבל הרצפה המוחלטת שם היא **1.0 נק'** (`floor_pts = max(_floor_mult * atr_5m, 1.0)`) ולא 2. חוק ה-2 נק' חי רק ב-`pre_fire_validator.py:75` שרץ **לפני** שהגייטוויי דורס. אין ולידציה חוזרת על הסטופ הסופי. |
| R6 | **IMPLEMENTED** | `stop_resolver.py:79-83` — `NORMAL_ROTATION_FIX_V1` באמת מוסיף `"Normal"`, ברירת-מחדל-בקוד ON. |
| R7 | **CONTRADICTED בשטח** | 3 עסקאות חרגו מ-25 (ראה §4). |
| R8 | **PARTIAL** | נאכף ל-S4 בלבד (`woodies_system.py:847`). **S2 לא קורא את ה-`max_risk_points` של עצמו** (Reactive 15 · OFA 12 · Double_BT/HnS 20 · Flag 15 יושבים ב-yaml ואף אחד לא קורא אותם). |
| R9 | **IMPLEMENTED — ומנצח את כולם** | `step_scaled_ladder.py:196` `stop_dist = max(stop_floor, stop_frac * median)`. פסיקת 08-12 אמרה "במקום ATR עיוור" — אבל בפועל הוא מבטל גם את **המבנה** (R1), את **תקרות-התבנית** (R8), את **רצפת-הרוטציה** (R6) ואת **ריווח-ה-16T** (R3), שאף אחד מהם לא בוטל בפסיקה. |
| R10 vs R11 | **סתירה חיה** | ראה §3 — זהו הממצא המרכזי בצד-המימוש. |
| R12 | **PARTIAL** | לא מחובר ל-`on_bar` בכלל; שורד רק כ-fallback מקונן בתוך הטרייל-הדינמי (`manager.py:898`, נקרא מ-`:1183/1193/1201`). |
| R13 | **NOT IMPLEMENTED (RUNNER_TRAIL)** | `bar_level_detector.py:667-675` — `if DYNAMIC_STRUCT_TRAIL: ... elif RUNNER_TRAIL_V1: ...`. שניהם =1 ⇒ **`hwm − 1.0×risk` לעולם לא רץ.** `docs/FLAG_INDEX.md:210` מציג אותו כמנוף פעיל = הצהרה שגויה. |
| R14 | **IMPLEMENTED** | `manager.py:736 trade.stop = entry` (BE נקי, בלי +1T — עקבי עם הפסיקה). ZLR נועל את כל 4 מסלולי-הטרייל (`manager.py:896/1008/1109/1300`). |
| R15 | **IMPLEMENTED** | `STALL_EXIT` / `OPPOSITE_EXIT_V1` לא ב-`.env` ⇒ OFF. אין קורא חדש ל-`_emit_exit`. ⚠️ מוקש: `trading_gateway.py:2930` (`OPPOSITE_2X`) סוגר ספרים + משחרר slot **בלי שום פקודת-יציאה לסיירה** — לא מסוכן היום רק כי הדגל כבוי. |
| R16 | **PARTIAL** | `scale_in.py:81` `add_stop = e` כאשר `e = entry_price` — **הכניסה של ההורה, לא ה-BE של ההורה** (שהוא `entry ± 0.25`). טיק אחד לרעה. שאר הפסיקה מקוימת: ה-child מקבל בראקט מלא משלו, אין `write_modify_stop`/cancel על ההורה. ⚠️ `n_contracts_open` נספר **פר-עסקה** ולא פר-חשבון — שני הורים של 4 יכולים להגיע ל-12 חוזים ושניהם "עוברים ≤8". |
| R17 | **NOT DEPLOYED** | `merged.cpp:2901-2915` מכיל את הסולם `if (contracts >= 6) { lq = {1,2,2,1}; }` אבל commit `e43cd0eb` עצמו כותב "NOT DEPLOYED — needs Remote Build". בנוסף `margin_sizing.py:141 DLL_BRACKET_SLOTS = 4` + `cap_to_bracketable` נקרא ללא-תנאי ⇒ **גם `FIXED_CONTRACTS_6=1` היה שולח 4 היום.** ל-n=4 הסולם הוא 1/1/1/1 ו**כל 4 החוזים מקבלים סטופ** (`Stop1..Stop4Price`, ללא תנאי) ✓ |
| R18 | **IMPLEMENTED אך לא-מאומת-בשטח** | ראה §5 + BLOCKER-2. `grep -c ExitVerify /tmp/backend.err.log` = **0** — הקוד מעולם לא רץ בייצור. |
| R19/R20 | לא נבדק לעומק בסבב הזה | — |

### מסלולי סטופ-עירום (סטופ None/0 שעדיין יוצא לשוק)
1. `sierra_command.py:844` `stop_price=setup.get("stop") or setup.get("stop_price")` — **אין בדיקת `> 0`**. `command_from_setup` בודק `contracts <= 0` אבל לא סטופ. ה-DLL מקבל `0.0` ושולח את הכניסה (`merged.cpp:2974`). להשוואה: `PLACE_BRACKET` **כן** בודק (`merged.cpp:3388`).
2. `merged.cpp:3197 mod.Price1 = static_cast<float>(new_stop);` בלולאת 4 הקבוצות — **אין בדיקת `new_stop > 0`**, בעוד MODIFY_TARGET (`:3235`) כן בודק. JSON פגום אחד מזיז את כל הסטופים ל-0.
3. `STOP_RETRY_ON_NONE_V1` **לא מכסה** את שני אלה — הוא נדלק רק על תוצאת `MODIFY_STOP_NONE` מה-DLL.

---

## 3. הממצא המרכזי בצד-המימוש: R10 ⟂ R11 — שתי פסיקות סותרות חיות במקביל

`manager.py:790-816` (`_apply_smart_be_after_t1`):
```python
if direction == "LONG":
    _be = entry + tick
    _cur = float(trade.stop) if trade.stop is not None else None
    if _struct_stop is not None and (_cur is None or _struct_stop > _cur):
        target_stop = _struct_stop          # structure that tightens
    else:
        target_stop = _be                   # BE+1T fallback
```
הקוד בוחר את המבנה בכל פעם שהוא **מהדק מול הסטופ הנוכחי** — **ללא רצפה ב-BE**. כלומר אחרי T1 הסטופ יכול להישאר הרחק מתחת לכניסה.

**זה בדיוק מה שקרה בשטח** (`v9_trade_management_log`, action=`SMART_BE`):

| עסקה | כיוון | כניסה | BE נדרש | SMART_BE הזיז מ→אל | תוצאה |
|---|---|---|---|---|---|
| #566 | LONG | 7435.75 | 7436.00 | 7422.00 → **7427.00** | 8.75 נק' **מתחת** לכניסה |
| #625 | LONG | 7744.75 | 7745.00 | 7724.75 → **7729.25** | 15.50 נק' מתחת · אח"כ STOP_HIT |
| #657 | SHORT | 7775.25 | 7775.00 | 7790.25 → **7781.75** | 6.50 נק' **מעל** לכניסה (עדיין הפסד) |

**למה זה חשוב היום ולא אתמול:**
מערכת-6 (`SYSTEM6_AUTOCORRECT=protective`, `.env:294`) מריצה את האינווריאנט `stop_not_at_be` (`system6_supervisor.py:160-162`) שמסווג בדיוק את המצב הזה כתקלה ומנפיק תיקון AUTO `MODIFY_STOP` ל-BE. עד אתמול הוא **הפסיד** — כי `trade.stop` מעולם לא נכתב חזרה, האינווריאנט נדלק לנצח, ונוצר שיטפון (392 פקודות זהות על #657, 110 מהן פגו בתור בלי להישלח).

**התיקון של אתמול (`dc13cc70`) הופך את התוצאה:** עכשיו יש write-back ⇒ מערכת-6 תשלח פקודה **אחת** שתצליח, `trade.stop` ייכתב ל-BE, והאינווריאנט ישתתק. כלומר **מהיום מערכת-6 מנצחת את STOP_STRUCTURE_TRAIL_V1 ומושכת את הסטופ ל-BE** — שינוי-התנהגות אמיתי, לא-מוכרז, שנכנס לסשן של היום. הסטופים אחרי T1 יהיו הדוקים יותר מ-3 השבועות האחרונים.

**זה לא באג — זו פסיקה חסרה.** צריך משפט אחד ממייקל: מי גובר אחרי T1 — המבנה (R11, פסיקת 07-08) או BE (R10, Table C §6.1 + מערכת-6)?

---

## 4. אימות מול עסקאות אמיתיות (STEP 3)

**מדגם:** `v9_trades`, `mode='live'`, 21 יום אחרונים = **43 עסקאות** (07-27 → 08-14). אין עסקאות `demo` כלל (97 `shadow` לא נספרו). אין עסקאות פתוחות.

### 4.1 הסטופ ההתחלתי מול תקרת-הסיכון (R7)

| עסקה | תבנית | סוג-יום | סיכון-התחלתי | חוזים | חריגה |
|---|---|---|---|---|---|
| #581 | INITIATIVE_SHORT | Trend_Normal | **43.00 נק'** | **2** | תקרת-25 ✗ + סולם-חוזים ✗ (מעל 25 ⇒ חוזה 1) |
| #575 | OPENING_DRIVE | — | **39.75 נק'** | 1 | תקרת-25 ✗ (חוזים ✓) |
| #536 | INITIATIVE_LONG | Variation | **37.25 נק'** | **4** | תקרת-25 ✗ + סולם-חוזים ✗ |

**39 מתוך 42** בתוך התקרה. **אפס** מתחת לרצפת-2-נקודות (המינימום בפועל 2.50 ב-#607).
#581 = $430 סיכון על חשבון של $2,875 — יותר מחצי מתקרת-ההפסד-היומית בעסקה אחת.
כל שלוש החריגות הן במסלול INITIATIVE/OPENING — עקבי עם הממצא ש-**S2 לא קורא את תקרות-התבנית שלו** (R8 PARTIAL) ושהמסלול של OPENING_FIRE מייצר סטופ משלו.

### 4.2 BE אחרי T1 (R10/R11)

22 עסקאות הגיעו ל-T1. בכל 22, `quality->>'initial_stop'` מלא ⇒ **הסטופ אכן זז, ופקודת MODIFY_STOP אכן נשלחה** (`SMART_BE` נרשם בדיוק פעם אחת לכל עסקה — לא רק לוג).

| תוצאה | ספירה | עסקאות |
|---|---|---|
| הגיע ל-BE או טוב יותר | **19 / 22** | 573,581,588,593,595,601,604,612,615,620,622,627,633,637,643,660,661,670,673 |
| **לא הגיע ל-BE** | **3 / 22** | **#566 · #625 · #657** |

**ראיה שהספרים ≠ סיירה ב-#657:** `STOP_HIT` נרשם עם `{"stop": 7781.75, "fill_price": 7775.25}` — סיירה מילאה בדיוק במחיר-הכניסה (BE), בעוד הספרים החזיקו 7781.75. כלומר בסיירה הסטופ **כן** היה ב-BE וה-393 הפקודות היו קרב על באג-ספרים בלבד.

### 4.3 סולם-היעדים — האם כל חוזה יוצא ביעד שלו (R14/R19/R20)

**10 מתוך 42 (24%) שיגרו סולם-יעדים פגום:**

| סוג | ספירה | עסקאות | מה קורה בפועל |
|---|---|---|---|
| **הפוך** (T2 קרוב יותר מ-T1) | 6 | #536 · #545 · #548 · #586 · #610 · #670 | חוזה-2 מממש **לפני** חוזה-1 ובפחות רווח. ב-#545 T1=8.25 נק' מול T2=3.75 נק'. |
| **קרוס** (T1 == T2 בדיוק) | 4 | #595 · #604 · #620 · #622 | שני חוזים יוצאים באותו מחיר — **אין ראנר, אין T2, אין "runner exits at LSMA"**. כולן ZLR עם 2 חוזים. |

ה-4 הקרוסות הן תוצאה ישירה של `pattern_t1_points` + clamp שמושך את t2 אל t1 כששניהם נחסמים לאותה רמה מבנית. `T2T3_NO_STOMP_V1=1` נועד למנוע בדיוק את זה ולא מנע.

### 4.4 P&L מול הברוקר

- `pnl_sierra` מאוכלס ב-**עסקה אחת מתוך 42** (#664, 140.00 = 140.00 ✓). כלומר **אין הצלבה שיטתית מול הברוקר** — הפער של 08-14 (ספרים −$135 מול ברוקר +$120) לא נסגר במנגנון, רק בדוח ידני.
- `trade_activity_events.jsonl` מכיל `CLOSED_TRADE_PNL` פר-רגל ולא פר-עסקה, בלי `trade_id` — **אי-אפשר להצליב אוטומטית** במצב הנוכחי. זה השורש של "הספרים טעו בעבר" ועדיין פתוח.
- תיקון T3 (`1f2f2167`, חשבונאות 4 חוזים) לא נבדק על עסקאות חדשות — אין עסקאות מאז 08-14.

---

## 5. שני השינויים מ-24 השעות האחרונות (STEP 4)

### 5.1 `backend/v9/services/exit_verifier.py` (חדש, `EXIT_VERIFY_V1=1`)

| בדיקה | תוצאה |
|---|---|
| נעילה-לנצח? | **תקין ברמת-המודול.** גבולות מפורשים: `EXIT_VERIFY_TIMEOUT_S=45` → ניסיון-FLATTEN שני → כניעה ב-~90ש עם CRITICAL+פוש; `EXIT_VERIFY_UNKNOWN_MAX_S=300` על state לא-טרי. הספרים נשארים פתוחים במכוון (`exit_verifier.py:208-257`). מפתח נכון: `sierra_position_reconciler.py:64 data.get("position_qty")` ✓ |
| סגירה-כפולה? | **תקין.** 3 שכבות: `:110` duplicate-register · `:181-189` `still_open()` לפני בדיקת-המציאות · `:192` `del _pending[tid]` **לפני** `on_confirmed()`. ובנוסף `machine.transition(CLOSED)` זורק על עסקה סגורה. |
| ה-FillPoller מגיע? | **כן.** `backend/main.py:1104-1114` יוצר `FillPoller` + `asyncio.create_task(_fp.run())`; `fill_poller.py:155` → `:186-190` → `verify_pending()` כל ≤2ש. |
| ריסטארט | **RISK.** `_pending` בזיכרון בלבד. ריסטארט באמצע-אימות מאבד את הממתין; `POSITION_TRUTH_SYNC_V1` סוגר `SIERRA_FLAT` אם היציאה הצליחה, אבל יציאה **שנכשלה** נעלמת בשקט. |
| כיסוי | **RISK.** רק 2 מתוך ~8 מסלולי-סגירת-ספרים עוברים דרכו (MAE_SCRATCH `bar_level_detector.py:864` · TARGET_APPROACH_REALIZE `:768`). היתר מוכחי-סיירה מטבעם (מילויים, position-truth, reconciler) או רדומים. |
| הטסטים | **מריצים קוד אמיתי** (17 טסטים, שעון סינתטי, שחזור בר-אחר-בר של #682). רק 2 בדיקות-wiring הן `inspect.getsource` — נבדקו ידנית. |

### 🔴 BLOCKER-2 — `qty == 0` הוא **ברמת-החשבון**, לא ברמת-העסקה

`exit_verifier.py:192` `if qty == 0:` כאשר `qty = _sierra_qty()` = `position_qty` מ-`sierra_state.json` = **נטו החשבון כולו**.

עם 8 החוזים הידניים של מייקל פתוחים כרגע, אם המערכת תוציא היום MAE_SCRATCH או TARGET_APPROACH_REALIZE:
1. `qty` לעולם לא יהיה 0 ⇒ אימות לעולם לא יאושר;
2. אחרי 45 שניות המאמת **משדר FLATTEN_ACCOUNT שני** (`_reemit_flatten` → `write_flatten_account`) — **פקודה ברמת-חשבון שתסגור גם את 8 החוזים הידניים של מייקל**;
3. אחרי ~90ש: CRITICAL, הספרים נשארים פתוחים, ה-slot תפוס, אין עסקה נוספת.

שלב 2 מפר ישירות את פסיקת `ORPHAN_AUTO_FLATTEN_V1=OFF` ("תבטל את הכלי שיוצא מעסקאות פתוחות") ואת `RECONCILER_OWNERSHIP_AWARE_V1` ("פוזיציה ידנית = INFO, לא פעולה").

⚠️ אותה בעיה קיימת גם **בלי** פוזיציה ידנית: FLATTEN_ACCOUNT הוא ברמת-חשבון, ולכן אם שתי עסקאות-מערכת פתוחות במקביל, MAE_SCRATCH על אחת סוגר גם את השנייה, והאימות של הראשונה דורש שהשנייה תיסגר גם.

**המאמת מעולם לא רץ בייצור:** `grep -c "ExitVerify" /tmp/backend.err.log` = **0**.

### 5.2 `manager.py::_emit_modify_stop` — dedup 60 שניות + write-back

| בדיקה | תוצאה |
|---|---|
| מפתח ה-dedup | `manager.py:253` `_dedup_key = (int(trade.id), round(float(new_stop), 2))` — **מזהה + מחיר**, לא מזהה לבד. |
| **האם הוא בולע הזזה-שנייה לגיטימית?** | **לא, כשהמחיר שונה — מוכח.** T1 ב-10:00:05 עם BE=P1, טרייל ב-10:00:40 עם P2≠P1: המפתח `(tid,P2)` ריק ⇒ `_now - 0.0 < 60.0` = False ⇒ נשלח. הטסט `test_a_different_stop_still_goes_through` (`tests/v9/regression/test_modify_stop_idempotent.py:72-77`) מריץ את זה באמת ובודק `len(sent) == 2`. **התשובה לשאלה שנשאלה: השער הזה תקין.** |
| התנגשות בין עסקאות | תקין. `_recent_stop_emits` מילון פר-instance, מפתח על PK מונוטוני, סחיפה ב-300ש. |
| הקוראים | ZLR-BE (פעם) · SMART_BE (פעם) · TARGET_REALISM (פר-בר 5ד') · טרייל (פר-בר) · S6 AUTO (פר-בר ×2 כי `on_bar` רשום גם ל-`5min` וגם ל-`woodies_5min`) — כולם >60ש או שהכפילות היא בדיוק מה שה-dedup נועד לו. **חוץ מאחד.** |

### 🔴 BLOCKER-1 — ה-dedup הורג את ניסיון-החוזר של סטופ-עירום (W3)

`STOP_RETRY_ON_NONE_V1=1` (`.env:379`, פסיקת 07-27 שסגרה חשיפה של 837 שניות). כשה-DLL מחזיר `MODIFY_STOP_NONE` ("לא מצאתי את הסטופ — הפוזיציה אולי חשופה"), ההתאוששות היא לשדר **את אותו** סטופ שוב:

`backend/v9/services/fill_poller.py:893,938`
```python
stop_val = getattr(trade, "stop", None)
...
self._tm._emit_modify_stop(trade, float(stop_val))
logger.warning("[FillPoller] W3 RETRY: re-sent MODIFY_STOP for trade %d stop=%s", ...)
```

ה-write-back של אתמול (`manager.py:280 trade.stop = float(new_stop)`) הוא מה שהופך את זה לקטלני: הוא רץ מיד אחרי ה-emit **שנכשל**, ולכן מחיר-הניסיון-החוזר **זהה-בייט** לזה שנכשל ⇒ אותו מפתח-dedup ⇒ `manager.py:261-264` מחזיר בלי לכתוב בייט.

וזה **חד-כיווני**: `_handle_modify_stop_none` נדלק רק כשמשתנה `trade_result.json` עם הסטטוס הזה (`fill_poller.py:704`), מה שמחייב שפקודה תישלח בפועל. לא נשלחה פקודה ⇒ אין תוצאה חדשה ⇒ ה-throttle של 10ש לא מקבל הזדמנות שנייה. **דיכוי אחד מסיים את לולאת-ההתאוששות לתמיד.**
לפני התיקון של אתמול זה עבד במקרה, כי `trade.stop` עדיין החזיק את הערך הישן.

חמור מזה: שורה 939 רושמת `W3 RETRY: re-sent` ב-WARNING **ללא תנאי** (הפונקציה מחזירה `None` בשני המסלולים) בעוד הדיכוי הוא `logger.debug`. **הלוג יטען שנשלח ניסיון-חוזר שמעולם לא נשלח** — כשל-שקט בדיוק על נתיב-הסטופ-העירום, המחלקה ש-CLAUDE.md §SYS-2 אוסרת.

**התיקון הקטן-הנכון (לא הוחל):**
```diff
--- backend/v9/services/trade_manager/manager.py
-    def _emit_modify_stop(self, trade, new_stop: float) -> None:
+    def _emit_modify_stop(self, trade, new_stop: float, *, force: bool = False) -> bool:
@@
-        if _now - _recent.get(_dedup_key, 0.0) < 60.0:
+        if not force and _now - _recent.get(_dedup_key, 0.0) < 60.0:
             logger.debug(...)
-            return
+            return False
      # ... return True אחרי כתיבה מוצלחת, False ב-except

--- backend/v9/services/fill_poller.py
-            self._tm._emit_modify_stop(trade, float(stop_val))
-            logger.warning("[FillPoller] W3 RETRY: re-sent MODIFY_STOP ...")
+            _ok = self._tm._emit_modify_stop(trade, float(stop_val), force=True)
+            logger.warning("[FillPoller] W3 RETRY: MODIFY_STOP trade %d stop=%s (sent=%s)",
+                           trade.id, stop_val, _ok)
```
`force=True` נכון **רק כאן**: לאתר-הקריאה הזה יש throttle משלו של 10ש (`fill_poller.py:928-935`) והוא שידור-בטיחות, לא מקור-שיטפון.

### 5.3 RISK נוסף ב-write-back (לא BLOCKER, אבל להכיר)
`sierra_command._write_command` **לא זורק** על אי-מסירה — הוא כותב קובץ-תור ומחזיר. המסירה נחתכת מאוחר יותר ע"י ה-drainer שמארכב בלי callback:
```
sierra_command.py:290:  _archive(cmd_file, "sent ... no DLL ACK ... — will not resend")
sierra_command.py:297:  _archive(cmd_file, "queued ... > TTL ...")
```
לכן "נכתב" ≠ "סיירה קיבלה". ה-write-back מספק את האינווריאנט של מערכת-6 ⇒ המנגנון היחיד שהיה משדר-שוב שותק. T2 החליף שיטפון-רועש ב**ירייה-אחת-בלי-אישור-מסירה**. אין בשום מקום השוואה בין `trade.stop` לסטופ-העובד האמיתי של סיירה.

---

## 6. מה חייב להיתקן לפני 16:30

### 🔴 BLOCKER — לא לסחור לפני שזה מטופל

**B1. לסגור את הפוזיציה-הידנית של 8 החוזים לפני 16:30 — או להשבית `EXIT_VERIFY_V1`.**
`exit_verifier.py:192` `if qty == 0` (חשבון-כולו) · `sierra_state.json position_qty=8`.
כל עוד יש פוזיציה ידנית פתוחה: כל מימוש-S6 של המערכת יישאר לא-מאומת, ישדר FLATTEN_ACCOUNT שני שיסגור גם את הפוזיציה של מייקל, ואז יקפיא את ה-slot.
*התיקון הקטן-הנכון (בחר אחד):* (א) מייקל סוגר את 8 החוזים לפני הפתיחה — הכי פשוט, אפס-קוד; (ב) `EXIT_VERIFY_V1=0` להיום (חזרה להתנהגות שלפני 08-15 — מחזיר את סיכון-הרפאים של #682, לא מומלץ); (ג) תיקון-קוד: ללכוד `qty_before` בזמן ה-register ולאשר על `abs(qty) <= abs(qty_before) - trade_contracts` במקום `qty == 0`. (ג) הוא הנכון, אבל הוא שינוי-משטח-סיכון ⇒ דורש פסיקת-מייקל + אימות-סים, לא לפני 16:30.

**B2. ה-dedup בולע את ניסיון-החוזר של הסטופ-העירום (W3).**
`manager.py:253-264` + `fill_poller.py:893,938-940`. הדיף בסעיף 5.2. 6 שורות, אזור מבודד, יש טסטים מריצים באותו קובץ להרחיב. **אם לא מתקנים — להשבית `STOP_RETRY_ON_NONE_V1` לא עוזר** (זה משאיר את החשיפה המקורית); חייבים את ה-`force`.

**B3. פסיקה נדרשת: מי גובר אחרי T1 — מבנה או BE?**
`manager.py:790-816` מול `system6_supervisor.py:160-162`. שאלה אחת למייקל. **בלי הפסיקה, ההתנהגות משתנה היום מעצמה** לטובת BE בגלל ה-write-back של אתמול — שינוי שלא נפסק ולא הוכרז. אם מייקל רוצה שהמבנה יגבר: להוסיף חריגה ב-`stop_not_at_be` כשה-`SMART_BE` בחר מבנה. אם BE גובר: להוסיף רצפת-BE ב-`manager.py:795/808` (`target_stop = max(_struct_stop, _be)` ל-LONG).

### 🟠 FIX-TODAY

**F1. אימות-פיד לפני הפתיחה.** הלוג כרגע דוחה **כל** batch של ברי-5-דקות:
`[bars/5min] TS-OFFSET-GATE REJECTED batch: newest bar ts 189,6xx s behind now` (≈2.2 ימים).
זו התנהגות סופ"ש צפויה, אבל **הסטופ, ה-ATR, חלון-12-הברים וה-step-ladder כולם ניזונים מהברים האלה.** אם ב-16:00 הפיד עדיין תקוע, הסטופ ייגזר מהברים של יום שישי. לבדוק ב-16:00: `select max(ts) from v9_bars_5min_woodies;` חייב להיות בתוך 10 דקות מ-now.

**F2. מרג'ין: $674.61 פנוי = 2 חוזים.** `FIXED_CONTRACTS_4=1` + `MARGIN_AWARE_SIZING_V1=0` ⇒ המערכת תשלח 4 והברוקר ידחה. או שמייקל סוגר את 8 החוזים (משחרר $2,200) — מה שגם פותר את B1 — או שמורידים ל-2 חוזים היום.

**F3. ריווח-העוגן 16T לא מגיע לרזולבר.** `trading_gateway.py:2113` — להעביר `offset_ticks=` מה-config במקום לתת ל-default 6 לרוץ. שורה אחת. הפסיקה של 07-23 (P=0.99 על 32 סשנים) לא נאכפת במקום שקובע.

**F4. `STEP_SCALED_LADDER_V1` דורס בשקט.** `trading_gateway.py:2407-2433`. מינימום להיום: לוג ב-WARNING שאומר "ladder overrode resolver: X → Y" כדי ש-EOD יראה כמה זה קורה. לוג בלבד = אפס-שינוי-התנהגות. ההחלטה אם הוא צריך להיות כפוף ל-25pt cap ולתקרות-התבנית = פסיקה.

**F5. אין בדיקת `stop > 0` ב-PLACE.** `sierra_command.py:844` + `merged.cpp:3197`. השורה ב-Python היא התיקון הזול (`PLACE_BRACKET` כבר עושה את זה ב-`merged.cpp:3388`). צד-ה-DLL דורש Remote Build ⇒ LATER.

### 🟡 LATER

- **L1.** `RUNNER_TRAIL_V1=1` אינרטי בגלל ה-`elif` ב-`bar_level_detector.py:673`. או לתקן את החיווט או לתקן את `docs/FLAG_INDEX.md:210` שמצהיר עליו כפעיל.
- **L2.** סולם-יעדים לא-מונוטוני ב-24% מהעסקאות — להוסיף ולידציה `T1 < T2 < T3` (בכיוון-הרווח) ב-`pre_fire_validator`, ולדחות/לתקן במקום לשגר.
- **L3.** `S2` לא קורא את `max_risk_points` של עצמו (`stop_anchors.yaml anchors:` — Reactive/OFA/Double_BT/HnS/Flag). שלוש חריגות-התקרה בשטח כולן ב-S2/OPENING.
- **L4.** `manager.py:855` `STOP_STRUCT_WINDOW_BARS` default **8** מול `structure_window_bars: 12` שנפסק. ליישר.
- **L5.** `scale_in.py:81` — סטופ ה-child ב-`entry` במקום ב-`entry ± tick` (BE של ההורה). טיק אחד.
- **L6.** `scale_in` סופר `n_contracts_open` פר-עסקה ולא פר-חשבון ⇒ תקרת-8 עקיפה.
- **L7.** `_pending` של המאמת בזיכרון בלבד — אובד בריסטארט.
- **L8.** `pnl_sierra` מאוכלס ב-1/42 עסקאות. אין הצלבה שיטתית מול הברוקר; `trade_activity_events.jsonl` בלי `trade_id` לא ניתן להצליב אוטומטית. זה השורש של פער 08-14 והוא עדיין פתוח.
- **L9.** מוקשים רדומים בנתיב-הכסף: `trading_gateway.py:2930` (OPPOSITE_2X סוגר ספרים בלי פקודת-יציאה) · `execution_bridge.py:152` · `trail_engine.py` (מודול מת, כותב סטופים ל-DB בלי לספר לסיירה).
- **L10.** סולם 6 החוזים (פסיקת 08-16) לא פרוס: `margin_sizing.py:141 DLL_BRACKET_SLOTS = 4` + `cap_to_bracketable` ללא-תנאי ⇒ גם `FIXED_CONTRACTS_6=1` ישלח 4. דורש Remote Build + הוכחת-סים.

---

## 7. מה נבדק ולא נמצא בו פגם

- **`op=EXIT` לא חזר.** `STALL_EXIT` / `OPPOSITE_EXIT_V1` לא ב-`.env` ⇒ OFF. אין קורא חדש ל-`_emit_exit`/`write_exit`. ✓
- **כל 4 החוזים מקבלים סטופ ב-DLL.** `merged.cpp:2928/2936/2949/2965` — `Stop1..Stop4Price` ללא-תנאי; רק היעדים מותנים ב-`tN_price > 0`, כלומר חוזה יכול להיות stop-only אבל לא stop-less. ✓
- **כל מסלולי-הטרייל אחרי T1 הם מהדקים-בלבד.** `manager.py:799, 812, 911-915, 1060, 1069, 1191, 1199` — אין מסלול חי שמרחיב סטופ. ✓
- **ה-dedup לא בולע הזזה-שנייה עם מחיר שונה** (הבדיקה בעלת-הערך-הגבוה שנתבקשה) — מוכח מהקוד ומטסט מריץ. ✓
- **`NORMAL_ROTATION_FIX_V1`** באמת מוסיף `"Normal"` לרשימת-הרוטציה. ✓
- **ה-reconciler לא מזעיק שווא** על הפוזיציה הידנית — `RECONCILER_OWNERSHIP_AWARE_V1` עובד כפי שנפסק. ✓
- **הטסטים של `dc13cc70` ו-`1f2f2167`/T4 מריצים קוד אמיתי**, לא `inspect.getsource` — המחלקה של `aa5b6af9` לא חזרה. ✓

---

## נספח — פקודות האימות (Rule 5)

```
/Applications/Postgres.app/Contents/Versions/latest/bin/psql postgresql://localhost/mems26
  select mode,count(*) from v9_trades where entry_ts>now()-interval '21 days' group by mode;
    -> shadow 97 | live 43   (אין demo)
  select trade_id,action,value from v9_trade_management_log
    where trade_id in (566,625,657) and action='SMART_BE';
    -> 566 {"to":7427.0,"from":7422.0} | 625 {"to":7729.25,"from":7724.75} | 657 {"to":7781.75,"from":7790.25}
  select count(*) from v9_trades where mode='live' and pnl_sierra is not null
    and entry_ts>now()-interval '21 days';   -> 1

cat ~/SierraChart_Data/v9_export/sierra_state.json   -> position_qty:8, is_sim:0, working_orders:1
grep -c "ExitVerify" /tmp/backend.err.log            -> 0   (מעולם לא רץ בייצור)
curl -s http://localhost:8000/api/v9/health          -> {"status":"ok","version":"v9.0.0"}
tail -3 /tmp/backend.err.log                         -> TS-OFFSET-GATE REJECTED batch (189,6xx s behind)
```

*ביקורת קריאה-בלבד. לא שונה קוד, דגל, `.env`, LaunchAgent או קובץ ב-`~/SierraChart_Data`. לא בוצע ריסטארט.*
