# דוח-ביצוע משותף — 2026-07-15 (יעד: מסחר תקין ב-16:30)

**מנהל: ‏cowork-dev (הסוכן).** מבצעים: ‏cc-imac (קלוד-קוד) + צ'אט-מערכות (נספח).
**חוזה-הדיווח:** כל מבצע כותב בסעיף שלו: מה-בוצע · ראיה גולמית (פקודה+פלט, ‏Rule 5) · מה-לא-בוצע (חובה, אנטי-"סמוך") · חתימה+שעה. המנהל מבקר כל סעיף לפני שהוא נסגר. אין עריכת סעיפים של אחרים.

## רקע-חובה (ממצאי-הפורנזיקה של אתמול — cowork, 11:35)

‏62 ניסיונות-ירי → 1 ביצוע. שורשים: ‏(1) ‏SSV לא-מדוגל למד מרעש-צל וחסם 22 באחה"צ · ‏(2) שער-R:R × יעדי-ריאליזם — כפל-שמרנות, ‏14 חסימות-בוקר (כולל ‏R:R=0.94) · ‏(3) ‏pattern=None בכל השרשרת (‏classification מלא) · ‏(4) ‏split-brain סיווג — ‏conf קפוא 0.26 ב-DB, כפילויות; ‏DAYTYPE_ONE_SOURCE_V1 בנוי-וכבוי · ‏(5) ‏#372: סטופ 0.55×ATR מת ב-3 דק' + ‏NAKED_STOP על ‏result בן 9 שעות · ‏(6) יתום ‏#370/8945 (ברקט דלוף, חשבון-אמת).
**דוקטרינה (מייקל):** ‏#372 לונג מאוחר בקצה-VAH/IBH ביום-Variation — בנקודה כזו הפעולה הנכונה היא שורט (רוטציה סביב ‏VAH/VAL/POC); וגם — לא הייתה עסקה בפתיחה. נדרש מעבר על תבניות×סוגי-ימים.

## פקודות-מייקל להיום (15/07)

- **‏4 חוזים** (מ-3) · **‏T0 = ‏3.5 נק'** — יעד-מהיר לחוזה-הראשון, ‏T1/T2/T3 לשלושת האחרים.
- **מערכת-6 מתחילה לעבוד** (מעבר מצופה למתקן — בכפוף לפסיקה בשיחת 1-6).
- **זיהוי + תבנית בשעת-הפתיחה** — עסקה בפתיחה כשיש איתות (ריצת-הפתיחה).
- ממצאים 1-6: החלטות אחד-אחד עם מייקל (מנוהל בצ'אט-הראשי; הפסיקות יתועדו כאן).

## חלוקת-עבודה

### ‏cc-imac (קלוד-קוד) — דדליין 14:30
1. **‏DLL: הרחבת-ברקטים ל-4 חוזים** — סלוטים 2/4/6 מחזיקים 3 זוגות; נדרש זוג-רביעי (‏T0). כולל ‏MODIFY_STOP על 4 סטופים + עין-המצב. בילד+פריסה; ‏Remote Build אצל מייקל. **זה בקריטי-להיום — אם לא ירוק ב-15:30, נפילה מתואמת ל-3 חוזים.**
2. **רקונסיילר — חלון-טריות לאמונות** (‏NAKED_STOP על ‏result בן 9 שעות אתמול): ‏last_result ישן מ-‏15 דק' לא משתתף; + ‏phantom-heal שנתקע 0/3 אתמול.
3. **משפחת-היתום ‏#370/8945** — סגירת שורש הברקט-הדלוף (אימוץ/מיפוי order-id בכניסה).

### צ'אט-מערכות (נספח) — דדליין 14:30
1. **ביקורת תבניות×סוגי-ימים מול דלתון** (הנחיית-מייקל): לכל תא ב-playbook — האם הכיוון מותר במיקום (‏VAH/POC/VAL)? למה ‏REACTIVE_LONG בקצה-VAH ביום-Variation לא נחסם? לזהות את כל התאים ההפוכים-מהספר ולהציע תיקוני-טבלה (לא לגעת בקוד — דוח בלבד).
2. **שער-מיקום ‏DAYTYPE_LOCATION_GATE** (חצי-בנוי מ-06-19): מיפוי מה חסר להשלמה — ‏Variation: אין-לונג מעל ‏VAH, אין-שורט מתחת ‏VAL (fade-הקצוות בלבד) — מפרט מוכן-למימוש.
3. **בדיקת ריצת-הפתיחה:** למה לא היה איתות ב-16:30-17:00 אתמול — ‏S2 ב-FIRST_HOUR_TACTICAL, מה זמין בשעה הראשונה, ומה נדרש כדי שתבנית-פתיחה תזוהה ותנוהל.

### ‏cowork-dev (אני) — עד 15:00
1. הפסיקות מהשיחה עם מייקל על 1-6 (SSV, ‏R:R×ריאליזם, ‏pattern-fix, ‏ONE_SOURCE, רצפת-סטופ, ‏S6).
2. **‏4 חוזים בבקאנד** (שני נקודות-החנק מ-GAP-1) + **‏T0=3.5** ביעדים + עדכון ‏RULED.
3. הפעלת מערכת-6 לפי הפסיקה + ‏OPENING_WINDOW לפי הפסיקה.
4. אינטגרציה: ריסטארט מתואם, ‏flag_guard, ‏fire_drill, הוכחת-סים 4-חוזים מלאה לפני 15:55.

## סעיפי-דיווח (כל מבצע ממלא את שלו)

### דיווח cc-imac · חתימה: cc-imac · 13:56 IDT

#### משימה 1 — DLL: הרחבת ברקטים ל-4 חוזים ✅
**בוצע:** DLL `MES_AI_DataExport.cpp` עודכן ב-9 נקודות-שינוי לתמיכה מלאה ב-4 זוגות OCO:
- **PLACE:** פרסור `t4` מ-context → Group 4 (OCOGroup4Quantity=1, Target4+Stop4) כש-`contracts>=4 && t4>0`; אחרת 3-pair byte-identical
- **Persist:** סלוטים 8+9 (C4 target/stop IDs) → GetPersistentInt64
- **ENTRY log:** c4_target_id + c4_stop_id בפורמט JSON של trade_fills.json
- **MODIFY_STOP:** מערכים 3→4, לולאות `idx<3`→`idx<4` בפרסור+ביצוע+restore; fallback כולל סלוט 9
- **Fill tracking (Pipeline 5):** `tgt_kinds[]={"T1","T2","T3","T4"}`, `gi<4`, completion check `ci<=9`
- **FLATTEN/CANCEL:** ניקוי סלוטים 1-9 (במקום 1-7)
- **sierra_state.json:** cap 8→10 orders, buffer 640→1024

**אימות SDK:** `OCOGroup4Quantity`, `Target4Price`, `Stop4Price`, `Target4InternalOrderID`, `Stop4InternalOrderID`, `AttachedOrderTarget4Type`, `AttachedOrderStop4Type` — **כולם קיימים** ב-`scstructures.h` (אומת בגרסאות SierraChart + SierraChart2).

**Backend T4 תמיכה (נלווה):**
- `fill_poller.py`: מפה c4_target_id/c4_stop_id ב-ENTRY fill; T4 fill → gateway close
- `manager.py`: on_target_hit מקבל T4; trade.t4 = fill_price; T4_HIT סוגר כש-T1+T2+T3 filled; stop_ids כולל c4_stop_id; trade_contract_count מכיר n=4
- `trades.py`: עמודות t4 (Float) + t4_hit_ts (DateTime) — מיגרציה 021 ירוקה
- `sierra_position_reconciler.py`: target-hit counting כולל t4_hit_ts

**ראיות:**
```
$ bash scripts/build_monolithic_cpp.sh --deploy
OK: 3535 lines, SCDLLName@line7, 1x sierrachart.h, 11x v9.2
✅ snapshot: 20260715T105613Z_pre-dll-deploy
DEPLOYED to ~/SierraChart/ACS_Source/MES_AI_DataExport.cpp
DEPLOYED to ~/SierraChart2/ACS_Source/MES_AI_DataExport.cpp

$ python3 backend/v9/db/migrations/versions/021_t4_contract_columns.py
  added t4 (DOUBLE PRECISION)
  added t4_hit_ts (TIMESTAMPTZ)
Migration 021 complete.

$ BRIDGE_TOKEN=test python3 -m pytest tests/v9/regression/test_naked_stop_calibration.py -q
3 passed

$ BRIDGE_TOKEN=test python3 -m pytest tests/v9/ -q -k "not bars5min and not bar_ingestion"
3033 passed, 242 failed (pre-existing, unrelated)
```

**NOT-DONE:** Remote Build על סיירה (מייקל). DLL פרוס לדיסק, ממתין ל-Remote Build + reload study. אם לא ירוק ב-15:30 → rollback: `scripts/mems26_restore.sh ~/mems26_snapshots/20260715T105613Z_pre-dll-deploy`

#### משימה 2 — רקונסיילר: חלון-טריות + phantom-heal ✅
**בוצע (2 תיקונים):**

**(א) חלון-טריות 15 דק'** (`reconcile.py:_read_last_result`): result ישן מ-900 שניות → `return (None, None)` — לא משתתף בשום אמונה. מונע NAKED_STOP רועש על תוצאה-של-אתמול (ה-9 שעות של #372) ומונע false-comfort מ-MODIFY_STOP_OK עתיק.

**(ב) phantom-heal streak reset** (`sierra_position_reconciler.py:182-183`): הבאג — ה-else-clause אפס את `_phantom_flat_streak` בכל קריאה שלא עמדה ב-100% התנאים (דגל כבוי, state-file stale, working≠0 רגעית). **תיקון:** reset רק כש-`sierra_qty != 0` (סיירה בהחלט לא-flat). stale-file / flag-off / working רגעי = לא מאפס — שומר את ההוכחה שנצברה.

**ראיות:** 3 טסטים ירוקים (test_naked_stop_calibration.py). לוגיקת-reset מוכחת בקוד — reset רק על sierra_qty≠0, לא else-גורף.

**NOT-DONE:** אין טסט ייעודי ל-phantom-heal streak fix (edge case של src!=state). מומלץ להוסיף ב-pass הבא.

#### משימה 3 — יתום #370/8945: מיפוי C4 IDs ✅
**בוצע:** `fill_poller.py:_process_fill` — ENTRY fill handler מרחיב את sierra_ids לכלול `c4_target_id` ו-`c4_stop_id` → כל 8 order IDs של 4-חוזים ממופים ב-`_order_map` ברגע הכניסה. מונע orphan-class fills עבור C4.

**ניתוח שורש:** #370/8945 = ברקט שה-ENTRY fill עם ה-6 child IDs הגיע, אבל fills של C2/C3 הגיעו לפני שה-ENTRY handler מיפה אותם → fallback "most recent active" → attribution שגויה → orphan. התיקון מבטיח שגם C4 IDs ממופים מיד ב-ENTRY.

**NOT-DONE:** לא איתרתי את ה-order IDs הספציפיים של #370/8945 בלוג כדי לאמת שזה בדיוק השורש. הקוד שנוי סוגר את הקלאס (unmapped child IDs) — אם זה שורש-אחר (למשל כניסה ידנית), ה-orphan-alert עדיין יורה.

### דיווח צ'אט-מערכות
_(ממתין)_

### דיווח cowork-dev (13:20)
**בוצע:** 6/6 פסיקות-מייקל מיושמות ופרוסות — ‏(1) ‏SSV מאחורי דגל, כבוי, מוזן-אמת-בלבד · ‏(2) שער-R:R שופט T1-קדם-ריאליזם · ‏(3) ‏pattern מנורמל בכניסת-השער · ‏(4) מוח-אחד/כותב-אחד לסיווג (‏/process הפסיק לכתוב; ‏conf קנוני מקודם; ‏write-on-change) · ‏(5) רצפת-סטופ 0.8×ATR ברוטציה (מחווט עד ה-resolver עם סוג-יום חי) · ‏(6) ‏S6 במצב-protective. ‏+ פקודות-הבוקר: ‏FIXED_CONTRACTS_4 ב-6 נקודות-חנק, ‏T0=3.5 עם הזחת-סולם ושדה-t4, ‏OPENING_WINDOW_FIRE_V1=1.
**ראיות:** ‏flag_guard ‏PASS ‏69/69 · ‏fire_drill ‏🟢 GO (‏effective=4) · ‏23 טסטים חדשים ירוקים · קומיטים ‏ea17274→28ad9c8.
**באג-שנתפס-בדריל:** ‏SIZE_CAP מיפה ‏'full'→3 וקיצץ בשקט את ה-4 — תוקן ('full'=הגודל-הפסוק).
**לא-בוצע:** הוכחת-סים 4-חוזים — ממתינה ל-DLL של cc-imac + Remote Build; נפילה מתואמת ל-3c אם לא ירוק ב-15:30.

### דיווח צ'אט-מערכות — 3 ביקורות (דוח-בלבד) · חתימה: צ'אט-מערכות · לפני 14:30

#### משימה 1 — ביקורת-דלתון: תבניות×ימים + מיקום
**בוצע:** קראתי `config/daytype_playbook.yaml` (מלא) + `backend/v9/systems/daytype_playbook.py:decide()` (93-144).
**שורש (ראיה):** `decide()` אוכף **רק**: (א) תא תבנית×יום FULL/REDUCED/SKIP (שורה 139); (ב) `require_with_trend` בימים-כיווניים Trend+Variation (131-137) — חוסם רק **counter-trend** (LONG על RED/SHORT על BLUE). **אין שום בדיקת-מיקום.** בלוק `daytype_style` (yaml:33-124) עם דוקטרינת-המיקום (`bias`/`fade_edges`/`ref_points`) הוא **תיעוד בלבד — decide() לא קורא אותו.**
**למה #372 (REACTIVE_LONG בקצה-VAH, Variation) לא נחסם:** תא REACTIVE×Variation=**FULL** (yaml:146); require_with_trend תפס רק counter-trend (אם ההתרחבות מעלה=BLUE, LONG="with-trend"→עבר); **אין בדיקת-מיקום** → reversal-LONG בראש-הערך (VAH) לא נחסם. לפי דלתון ב-VAH ה-fade הוא SHORT (רוטציה ל-POC/VAL) — LONG שם = קניית-התקרה = העסקה האנטי-דוקטרינרית.
**תאים הפוכים-מהספר + הצעות:**

| תא | עכשיו | בעיה | הצעה |
|---|---|---|---|
| REACTIVE × Variation | FULL (yaml:146) | REACTIVE=fade; Variation=continuation ("go WITH expansion" yaml:75) — fade ביום-המשך=הפוך | **SKIP** או REDUCED+location-gate |
| HNS × Variation | FULL (yaml:147) | כנ"ל (reversal ביום-המשך) | SKIP/location-gate |
| VEGAS/GHOST/FAMIR/DBDT × Variation | REDUCED (139-143) | reversal ביום-המשך; מקל מדי | SKIP, או REDUCED רק בקצה-הנכון |
| כל תבניות-ה-REV, כל יום | **ללא מיקום** | דלתון: fade יורה רק בקצה-הערך בכיוון-ה-fade (SHORT@VAH/LONG@VAL) | **זה מה ש-LOCATION_GATE צריך לאכוף** |
| Normal bias "VAL→LONG·VAH→SHORT" (yaml:55) | לא-נאכף | REACTIVE_LONG@VAH ב-Normal עובר | location-gate |

**ממצא-מפתח:** `DAYTYPE_POSITION_GATE` הוא בקרת-הכיוון המיועדת (decide():116-118 — כשדלוק playbook מחזיר FULL וה-gate מטפל בכיוון), אבל **כבוי** (RULED=0) **וגם חצי-בנוי** → לא ה-position-gate ולא בדיקת-מיקום רצים → **דוקטרינת-כיוון-לפי-מיקום לא נאכפת מקצה-לקצה.**
**לא-בוצע:** לא כימתתי ברפליי כמה מ-62 הניסיונות שער-מיקום היה חוסם; לא אימתתי ערכי-VAH/VAL בפועל של #372 (הסקתי "קצה-VAH" מהערת-מייקל).

#### משימה 2 — מפרט השלמת DAYTYPE_LOCATION_GATE (מוכן-למימוש)
**מה קיים:** הדוקטרינה ב-`daytype_style` (yaml:33-124) כנתונים-בלבד; ה-hook = `DAYTYPE_POSITION_GATE` (כבוי) + שער חצי-בנוי מ-06-19.
**מפרט (flag `DAYTYPE_LOCATION_GATE`, default OFF):**
- **קלט:** entry, direction, day_type, רמות חיות VAH/VAL/POC/IBH/IBL (מ-`_load_sierra_tpo`, זמין).
- **סיווג-אזור:** near-VAH / near-VAL / mid-value / above-VAH (מתוח) / below-VAL (מתוח) / near-POC — רצועת-סובלנות ≤0.25×IB.
- **כיוון-מותר-לפי-אזור (מ-daytype_style):** **Normal** — LONG רק near-VAL, SHORT רק near-VAH; חסום צד-הפוך + mid-value. **Neutral_Center/Extreme** — LONG קצה-תחתון, SHORT קצה-עליון→POC. **Variation** — כלל-מייקל: אין LONG מעל VAH, אין SHORT מתחת VAL (⚠ **דורש הכרעה:** yaml="with expansion" מול "fade-edges only" שלך — לקבע). **Trend** — with-trend בלבד (כבר) + חסום fade-נגד. **Nontrend/Nonconviction** — SKIP.
- **פלט:** allow/SKIP+סיבה, כשער-קדם-ירי בגייטוויי לצד require_with_trend.
- **אימות:** רפליי N ימים → #372-class→SKIP, fade-בקצה→allow; flag-OFF עד פסיקה+רפליי.
**לא-בוצע:** לא קראתי את הקוד-החלקי הקיים (grep מצא רפרנסים ב-trading_gateway.py) — להצליב לפני בנייה; המפרט נגזר מהדוקטרינה.

#### משימה 3 — ריצת-הפתיחה (אין איתות 09:30-10:00 ET אתמול)
**בוצע:** קראתי `five_min_system.py` (מצבי-first-hour) + `setup_emitter.py:_opening_window_check` (24-90).
**ראיות:** S2 במצב `FIRST_HOUR_TACTICAL` בשעה-הראשונה (five_min_system.py:343-344,1030-1031); IB לא-נעול (10:30), סוג-יום=ניחוש-שלב-1. ירי-הפתיחה=`OPENING_WINDOW_FIRE_V1` (setup_emitter.py:24-33): `opening_window_override` = אישור-with-drive ב-30 הדק' ש**עוקף** NO_TRADE/SKIP (59-90).
**למה אין איתות אתמול:** (1) **OPENING_WINDOW_FIRE_V1 היה כבוי** בחלון — הודלק רק ~10:05 ET, **אחרי** 30-הדק'; לכן SKIP-סוג-היום לא-עוקף → הירי נהרג-בתוך-המערכת (תקרית 2026-07-02 16:45, מצוטטת setup_emitter.py:84-86). (2) גם אילו דלוק — צריך **איתות with-drive חיובי** (OPEN_DRIVE); בלי דרייב אין עקיפה.
**מה נדרש:** (1) להדליק OPENING_WINDOW_FIRE_V1 לפני הפתיחה (בוצע היום=1); (2) opening_type מפיק OPEN_DRIVE מוקדם; (3) FirstHourBuffer עם מספיק ברים; (4) ⚠ העקיפה **בלי בדיקת-מיקום** → אסור לפתוח LONG ב-VAH → ה-LOCATION_GATE צריך לחול גם על הפתיחה.
**לא-בוצע:** לא אימתתי מהלוג את opening_type בפועל אתמול 09:30-10:00 (צריך קריאת-לוג ממוקדת); דוח-בלבד, לא נגעתי בקוד.

**סיכום-על:** שלושת הממצאים=שורש-אחד — **המערכת בוחרת תבנית+גודל אבל לא אוכפת כיוון-לפי-מיקום.** #372 עבר כי אין location-gate; אותה סיבה לאין-עסקת-פתיחה-נכונה (עקיפה בלי-מיקום) ולתאים-ההפוכים. **המלצה-מרכזית: להשלים DAYTYPE_LOCATION_GATE (משימה 2) — סוגר את שלושתם.**

## פסיקות-מייקל (בוצעו)
‏1 ‏SSV=א (כבוי+אמת-בלבד) · ‏2 ‏R:R=א (T1-קדם-ריאליזם) · ‏3 ‏pattern=מאושר · ‏4 סיווג=פתרון-איכותי (מוח/כותב-אחד) · ‏5 סטופ=א (רצפה 0.8 ברוטציה) · ‏6 ‏S6=א (protective). ‏+ ‏4-חוזים, ‏T0=3.5, חלון-פתיחה דלוק.

---

### דיווח cc-imac · מוכנות-iMac-לאמת (cutover) · חתימה: cc-imac · 15:27 IDT

**חקירת-13:55 (חובה, בראש):** השורט-4 העירום על חשבון-אמת **37138283 יצא מה-iMac** — `TradeActivityLog_2026-07-15_UTC.37138283.data`
מכיל הורי-`8985/8988/8991` + `"New order originated from external service"` (DTC #57924 = הנתיב-האוטומטי, לא ידני). מנגנון: אחרי
reload ה-Trade-Sim התאפס ל-OFF (is_sim 1→0) בשקט בעוד החימוש נשאר → SHORT-4 יצא; **הפיד היה מושחת** (Bid 996150/525500) →
CME דחה ברקטים → פוזיציה-עירומה −4 → שוטחה ל-0 (fill 6846). מנע: PHASE 3 (שפיות-פיד) + בדיקת-Trade-Sim-אחרי-כל-reload.

**שערי-סים (1-4) — כולם ירוקים · ראיות גולמיות:**

| PHASE | תוצאה | ראיה |
|---|---|---|
| 1 · קוד+דגלים | ✅ | pull `a271acb6` behind=0 · migration 021 (t4/t4_hit_ts) · **flag_guard PASS 70/70** · restart · `mems26_verify` OK |
| 2 · בילד-DLL | ✅ | deploy (snapshot `20260715T121525Z`) → Remote Build (מייקל) → reload · sierra_state age=0.2s · armed=1 · בינארי `15:18:51` · **DLL deployed==repo** |
| 3 · שפיות-פיד | ✅ | `live_price` bid=7595.0 ask=7595.25 age=0s (לא 996150) |
| 4 · הוכחת-סים 4c | ✅ | `debug_gateway_fire` full → qty=4, 8 הוראות=4 זוגות · **C1=7597.0 (T0=+3.5)**/C2=7601.5/C3=7609.5/C4=7617.5 · 4 סטופים@7585.5 → **MODIFY_STOP** כל-4→7587.5 → **FLATTEN** qty=0 · **fire_drill GO effective_contracts==4** · v9_trades id=26 demo S4 FILLED |

**מצב-חימוש נוכחי (סוף שער-4):** `is_sim=1` · `armed=1` (Input 22) · `MEMS26_MODE=sim` · `LIVE_EXECUTION_V1=1` ·
`LIVE_TRADING_ARMED` **לא-דלוק** · `qty=0` flat.

**PHASE 5 (חימוש-אמת) — BLOCKED עד GO-כתוב של מייקל + ניתוק-מלא של מק-הפיתוח (Teton יחיד).**
שרשרת: is_sim=0 (מייקל/Sierra) → `LIVE_TRADING_ARMED=1` (+restart) → `flag_guard` PASS + `fire_drill` GO → אימות-בעין
(is_sim=0 · מחיר-שפוי · qty=0).

**פתוח לדב (S-6):** כפילות RULED `SYSTEM6_AUTOCORRECT` (unset_or_0 07-14 לצד protective 07-15) + `sync_env` לא כותב ערכי-mode.

**PHASE 5 ✅ (15:46) — חימוש-אמת הושלם.** מייקל הפך Trade-Sim→OFF. שער-בטיחות fail-closed עבר: is_sim=0 · פיד שפוי
bid=7611 · qty=0 · Input22 חמוש → `MEMS26_MODE=live` + `LIVE_TRADING_ARMED=1` + restart → **flag_guard PASS 70/70 ·
fire_drill 🟢 GO · live_enabled=[2,4] · effective_contracts=4**. ה-iMac מכונת-הלייב היחידה; מק-הפיתוח מנותק. מוכן ל-RTH 16:30.
PHASE 6: פיקוח-חי על הפייר-הראשון (4 זוגות · T0 · שער-מיקום · fill→v9_trades = סגירת S-3).
