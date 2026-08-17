# SCALE_IN_V1 — מוכנות לירי + הגדלת-עסקה, 2026-08-17

**נכתב:** 2026-08-17 (לפני פתיחת RTH 16:30 IL) · **מכונה:** mac-1 (LIVE, localhost:8000)
**מצב-עבודה:** READ-ONLY מלא — לא שונה אף דגל, לא בוצע restart, לא נכתב דבר ל-`~/SierraChart_Data`.
כל הבדיקות המריצות עשו monkeypatch ל-writer של סיירה ולכן לא נוצר אף קובץ-פקודה.

**פסיקת-המקור** (`config/RULED_FLAGS.yaml:144`):

> `SCALE_IN_V1: {expected: "1", ruled_by: "מייקל", date: "2026-08-13", note: "פסיקת 08-13 'אם המערכת
> מזהה שהכניסה נכונה והכיוון ממשיך אפשר גם לחזק בעוד חוזים'. תוסף-ניהול additive — לא נוגע בכניסה
> (אזהרת-מייקל 'אל תשבור כניסות'). child +2 חוזים אחרי T1+המשך-כיוון+עם-הטרנד, סטופ ב-BE-של-ההורה,
> תקרה 8, פעם-אחת. אומת: 9/9 טסטים + Sierra-sim child-PLACE drill (BUY 2 @7774.5 stop=BE 7767.5
> t1=7785, ACK 1s אפס-r=-1, FLATTEN→שטוח). params: SCALE_IN_MIN_PROFIT_PTS=6/ADD_CONTRACTS=2/MAX_TOTAL=8"}`

---

## פסק-דין

> ## ❌ **NO** — הגדלת-עסקה לא תעבוד היום.
>
> **הסיבה החוסמת אינה בקוד של SCALE_IN אלא במרג'ין:** עם 8 החוזים הידניים הפתוחים נשארו
> **$554.61 פנויים** מול **$275.11 מרג'ין לחוזה** — כלומר מקום ל-**2.0 חוזים בלבד**.
> ההורה עצמו (4 חוזים = $1,100.44) ייפסל ע"י הברוקר, ולכן אין בכלל עסקה שאפשר לחזק.
> קיצוץ-המרג'ין האוטומטי **כבוי בפסיקה** (`MARGIN_AWARE_SIZING_V1=0`, פסיקת 08-13 "1:1"),
> ולכן ההזמנה תישלח במלוא הגודל ותידחה — הסיגנל נצרך, ה-slot מתגלגל, הספרים מתמלאים ORDER_FAILED.
>
> **ONLY IF** מייקל סוגר את 8 החוזים הידניים לפני הפתיחה → אז 4+2=6 חוזים נכנסים בנוחות
> ($1,650.66 מתוך ~$2,755) — **אבל** רק אחרי שנסגרים 🔴 BLOCKER-1 ו-🔴 BLOCKER-2 להלן,
> שניהם הוכחו בקוד רץ ובלוג-אמת ולא נבדקו מעולם בשוק חי.

---

## 1. מה ההנחיה אומרת — בעברית של סוחר

הקוד: `backend/v9/services/trade_manager/scale_in.py:37-90` (`should_scale_in`).
**המקור הוא הקוד, לא ה-docstring** — כאן הם דווקא תואמים, למעט נקודה אחת (ראה §1.3).

### 1.1 התנאים שחייבים להתקיים — כולם יחד

| # | תנאי | קוד | פירוש לסוחר |
|---|------|-----|-------------|
| 1 | כיוון תקין | `scale_in.py:62-64` | LONG או SHORT בלבד |
| 2 | **T1 נבנק** | `scale_in.py:65` + `bar_level_detector.py:963` (`t1_hit_ts is not None`) | לא מחזקים לפני שהעסקה הוכיחה את עצמה |
| 3 | **פעם אחת להורה** | `bar_level_detector.py:961` (`q.get("scaled_in")`) | חיזוק יחיד לכל עסקת-אם |
| 4 | יש פוזיציה חיה | `scale_in.py:67` (`n_contracts_open > 0`) | ⚠️ נמדד **מהספרים**, לא מסיירה — ראה BLOCKER-1 |
| 5 | תקרת-חוזים | `scale_in.py:69` (`n_open + add > max_total` → עצור) | ⚠️ 2+2 מול 8 — אף פעם לא חוסם, ראה BLOCKER-2 |
| 6 | **עם הטרנד** | `scale_in.py:71-74` | `dir_bias`=UP ללונג / DOWN לשורט. `dir_bias=None` → **התנאי מדולג** |
| 7 | **המשך של ≥6 נק'** | `scale_in.py:75-79` | תנועה חיובית של הבר הנוכחי מעבר למחיר-הכניסה של ההורה |

### 1.2 מה הוא עושה כשהתנאים מתקיימים

- **כמה מוסיף:** `+2` חוזים (`SCALE_IN_ADD_CONTRACTS`, `scale_in.py:22`).
  אומת בקוד רץ שהילד באמת יוצא ב-2 ולא ב-4 — ראה §4.2.
- **מחיר-כניסה של הילד:** קצה-הבר לטובתנו (`bar_high` בלונג / `bar_low` בשורט) — `scale_in.py:80`.
- **הסטופ שלו:** **מחיר-הכניסה של ההורה** = BE של ההורה (`scale_in.py:81`, `add_stop_at_entry=True`).
- **היעדים שלו:** `t1` יחיד ב-**1.5R** של סיכון-הילד; `t2=t3=None` (`bar_level_detector.py:998-1003`).
  זו עסקה קצרה בכוונה — לא ראנר.
- **סוג-רישום:** עסקה-ילד עצמאית ב-`v9_trades` עם `classification="SCALE_IN"` ו-
  `metadata.scale_in_parent=<id ההורה>` (`bar_level_detector.py:1004-1005`).

### 1.3 מה הוא **לא** עושה — וזה מאומת

- **לא נוגע בכניסה של ההורה, בסטופ שלו, או ביעדים שלו.** ההורה נכתב פעם אחת בלבד ורק כדי
  לסמן `scaled_in=True` (`bar_level_detector.py:991-992`). אין שום `trade.stop=` או
  `trade.entry_price=` על ההורה במסלול הזה. ✅ תואם לאזהרת-מייקל "אל תשבור כניסות".
- **לא משתמש ב-op=EXIT** (השבור) — הילד יוצא דרך בראקט-OCO משלו מסיירה.
- **לא חוסם ולא מסנן אף ירי** — זהו תוסף post-entry בלבד; דגל כבוי = no-op מוחלט.
- ⚠️ **נקודת-אי-דיוק בתיעוד:** ה-docstring (`scale_in.py:7`) כותב *"Once per parent, capped size"*.
  "Once per parent" נכון מילולית, אבל **הילד עצמו הוא הורה חוקי לדור הבא** — ראה BLOCKER-2.

---

## 2. האם זה מחובר לקורא חי? ✅ **כן — מוכח בריצה, לא רק בקוד**

שרשרת-הקריאה מ-`backend/main.py`:

```
backend/main.py:1078   bar_level_detector = BarLevelDetector(trade_manager=trade_manager)
backend/main.py:1084   bar_level_detector.subscribe(bar_router)      ← נרשם לכל בר 5-דקות
        │
        └─► bar_level_detector.py:609   for trade in active:
            bar_level_detector.py:647       if _is_demo_live:
            bar_level_detector.py:649           self._maybe_scale_in(trade, bar_high, bar_low)
                    │
                    └─► bar_level_detector.py:958   דגל SCALE_IN_V1
                        bar_level_detector.py:982   should_scale_in(...)
                        bar_level_detector.py:1008  self._tm.accept_setup(child, mode)
                        bar_level_detector.py:1010  command_from_setup(...)   ← PLACE אמיתי לסיירה
```

**הוכחת-ריצה בפרודקשן** (לא נוכחות-קוד):

```
$ grep -c "BarLevelDetector" /tmp/backend.err.log
24517
$ grep "BarLevelDetector" /tmp/backend.err.log | tail -1
2026-08-17 04:20:04 [WARNING] BarRouter: SLOW handler BarLevelDetector.on_bar took 236.2ms
```

הלולאה שמכילה את ה-hook רצה גם היום (04:20). התהליך הנוכחי חי 1:27 שעות, טען
`[env_loader] applied 233 vars` ו-`SCALE_IN_V1=1` יושב ב-`.env:492`.
`flag_guard.py` → **PASS — all 175 ruled flags match** (אין דריפט).

---

## 3. האם זה ירה אי-פעם? ✅ **כן — 3 פעמים בלייב אמיתי**

```
$ grep -n "ScaleIn" /tmp/backend.err.log
76736:2026-08-13 17:00:33 [WARNING] [ScaleIn] +2c LONG parent=660 child=661 @7822.50 stop@7816.00 (BE) — reinforce LONG: T1 banked + 6.5pt past entry + with-trend (UP) → +2c, stop@parent-entry 7816.00
82635:2026-08-13 17:45:56 [WARNING] [ScaleIn] +2c LONG parent=661 child=662 @7830.25 stop@7822.50 (BE) — reinforce LONG: T1 banked + 7.8pt past entry + with-trend (UP) → +2c, stop@parent-entry 7822.50
180870:2026-08-14 18:14:39 [WARNING] [ScaleIn] +2c SHORT parent=670 child=673 @7806.50 stop@7812.50 (BE) — reinforce SHORT: T1 banked + 6.0pt past entry + with-trend (DOWN) → +2c, stop@parent-entry 7812.50
```

**ספירה: 3 ירי · אחרון: 2026-08-14 18:14:39 · כולם `mode=live`.**

מה-DB:

```sql
SELECT id,mode,direction,state,entry_price,stop,exit_price,exit_reason,pnl_usd,outcome,
       quality->>'scaled_in', quality->>'contracts', quality->>'classification'
FROM v9_trades WHERE id IN (660,661,662,670,673) ORDER BY id;
```

```
 id  | mode | dir   | state  | entry   | stop    | exit    | exit_reason       | pnl_usd | outcome | scaled_in | c | cls
-----+------+-------+--------+---------+---------+---------+-------------------+---------+---------+-----------+---+-----------------
 660 | live | LONG  | CLOSED | 7816    | 7820.5  |         | phantom_reconcile |   12.5  | WIN     | true      | 2 | INITIATIVE_LONG
 661 | live | LONG  | CLOSED | 7822.5  | 7822.75 |         | phantom_reconcile |   46.25 | WIN     | true      | 2 | SCALE_IN
 662 | live | LONG  | CLOSED | 7830.25 | 7822.5  | 7817.25 | STOP_FILL         | -130    | LOSS    |           | 2 | SCALE_IN
 670 | live | SHORT | CLOSED | 7812.5  | 7812.5  |         | manual            |   45    | WIN     | true      | 4 | ZLR
 673 | live | SHORT | CLOSED | 7806.5  | 7806.25 | 7806.25 | STOP_HIT          |   11.25 | WIN     |           | 2 | SCALE_IN
```

**מאזן הילדים: 661 +$46.25 · 662 −$130.00 · 673 +$11.25 = −$72.50 נטו.** מדגם n=3 — לא מסקנה סטטיסטית.

שלוש עובדות שצריך לשים לב אליהן:

1. **660 → 661 → 662 היא שרשרת.** `661` הוא ילד-SCALE_IN שבעצמו קיבל `scaled_in=true` וילד את `662`.
   זה לא תקלה חד-פעמית — זו התנהגות מובנית (BLOCKER-2).
2. **662 יצא ב-7817.25 מול סטופ מוצהר 7822.50** — 5.25 נק' מתחת לסטופ, $52.50 החלקה עודפת
   מתוך ה-−$130.
3. **660 ו-661 נסגרו `phantom_reconcile` ללא `exit_price`** — הספרים לא ידעו איך הם יצאו.

---

## 4. האם זה שורד את שינויי ה-36 שעות האחרונות?

### 4.1 🔴 מאמת-היציאה (`exit_verifier.py`) — **לא. יש כאן פגם אמיתי.**

`_exit_happened` (`exit_verifier.py:149-167`) מודד **תנועה**, לא שטיחות:

```python
moved = abs(int(before)) - abs(int(qty))
return moved >= int(n)
```

`n` = מספר החוזים של העסקה **הזאת**, אבל `moved` = תנועת **החשבון כולו**. כשהורה וילד
פתוחים יחד (בדיוק מה ש-SCALE_IN יוצר), יציאה של האחד יכולה לאשר את ספרי האחר.

**בדיקה מריצה** (`/tmp/scale_in_verifier_check.py`, על הפונקציה האמיתית, חשבון = 8 ידני + 4 הורה + 2 ילד = 14):

```
A) ההורה(4c) ממתין, ואז 2 החוזים של הילד יוצאים  -> qty 12
   ספרי ההורה נסגרים?  False   (נכון: False)  ✅
B) הילד(2c) ממתין, ואז 4 החוזים של ההורה יוצאים  -> qty 10
   ספרי הילד נסגרים?   True    (נכון: False)  🔴 באג
C) הילד(2c) ממתין, והילד באמת יוצא               -> qty 12
   ספרי הילד נסגרים?   True    (נכון: True)   ✅
D) הילד(2c) ממתין, חוזה ידני אחד יוצא            -> qty 13
   ספרי הילד נסגרים?   False   (נכון: False)  ✅
E) הילד(2c) ממתין, מייקל מפלטן את 8 הידניים שלו  -> qty 6
   ספרי הילד נסגרים?   True    (נכון: False)  🔴 באג
```

**המסקנה:** האסימטריה היא הבעיה. עסקה **קטנה** שממתינה לאימות מאושרת בטעות ע"י יציאה
**גדולה** ממנה — של ההורה (B) או של מייקל עצמו (E). זה בדיוק הרפאים ש-T4 נבנה למנוע:
ספר-סגור מעל פוזיציה-חיה. SCALE_IN הוא **הדרך היחידה** ששתי עסקאות-מערכת באותו כיוון
פתוחות בו-זמנית, ולכן הוא זה שהופך את (B) לנגיש.

**מתי זה מתממש:** רק אם הילד רושם `register()`. שני הקוראים היחידים פעילים היום —
`target_approach_realize` (`bar_level_detector.py:771`, `S6_TARGET_APPROACH_REALIZE_V1=1`)
ו-`mae_scratch` (`bar_level_detector.py:870`, `S6_MAE_SCRATCH_V1=1`).

**החמרה נוספת:** שני המסלולים משדרים `write_flatten_account` (`bar_level_detector.py:743`),
שהיא **פקודה כלל-חשבונית**. FLATTEN שנשלח עבור ההורה יסגור גם את הילד וגם את
8 החוזים הידניים של מייקל. ההגנה `_account_holds_foreign_position` (`exit_verifier.py:294`)
שומרת רק על ה-**retry**, לא על השידור הראשון.

### 4.2 ✅ פותר-גודל-החוזים (`contract_size.py`) — **תקין, אבל תלוי בדגל לא-קשור**

הגודל של הילד בא מ-`SCALE_IN_ADD_CONTRACTS` (=2), **לא** מההורה ולא מ-`ruled_contracts()`.
אבל בדרך ל-PLACE הוא עובר דרך `effective_contracts()` שבו `FIXED_CONTRACTS_4` יכול לדרוס אותו.

**בדיקה מריצה** (`/tmp/scale_in_size_check.py`, על `effective_contracts` האמיתי תחת ה-.env החי):

```
live env: FIXED_CONTRACTS_4=1  SIZE_CAP_OVER_FIXED_V1=1  MARGIN_AWARE_SIZING_V1=0
ruled_contracts() (גודל ההורה)          : 4
הילד מבקש                                : 2
effective_contracts(child) -> נשלח       : 2      ✅

תרחיש-נגד, SIZE_CAP_OVER_FIXED_V1=0 (ברירת-המחדל בקוד):
effective_contracts(child) -> נשלח       : 4      🟠
```

**מסקנה:** היום הילד יוצא ב-2 כמו שנפסק — אבל רק מפני ש-`SIZE_CAP_OVER_FIXED_V1=1`
(`sierra_command.py:642-664`, `min(fixed=4, cut=2)`). ברירת-המחדל **בקוד** של אותו דגל היא
OFF, ואז `sierra_command.py:666-668` היה כופה 4. הדגל מוגן בפסיקה
(`RULED_FLAGS.yaml:201`, 07-14) ו-flag_guard עובר — אז אין דריפט היום, אבל הקישור
עקיף ולא מתועד בשום מקום ליד SCALE_IN.

### 4.3 ✅ dedup של 60 שניות ב-`_emit_modify_stop` — **לא בולע את סטופ הילד**

זו הייתה שאלת-הסיכון הגבוהה ביותר במשימה. התשובה נקבעה **בהרצה**, לא בקריאה.

מפתח ה-dedup הוא **(מזהה-עסקה, מחיר)** ולא מחיר בלבד (`manager.py:253`):

```python
_dedup_key = (int(trade.id), round(float(new_stop), 2))
```

**בדיקה מריצה** (`/tmp/scale_in_dedup_check.py`, על `TradeManager._emit_modify_stop` האמיתי,
עם `write_modify_stop` מוחלף ב-stub כך שלא נכתבה שום פקודה):

```
--- 1) ההורה מבקש BE, והילד מבקש את אותו BE בדיוק 0.2 שניות אחריו ---
commands emitted : ['660', '661']
child stop sent  : True
child DB stop    : 7816.0

--- 2) בקרה: אותה עסקה חוזרת על אותו מחיר (אמור להיחסם) ---
commands emitted : ['660'] (expect one)

--- 3) צורת מפתח ה-dedup ---
[(660, 7816.0), (660, 7818.0), (661, 7816.0)]
```

שתי הפקודות יצאו. הבקרה מוכיחה שה-dedup באמת עובד כשצריך (חזרה של אותה עסקה נחסמה),
כך שהתוצאה אינה "הבדיקה לא נגעה במנגנון".

**חיזוק מלוג-אמת:** בעת ה-PLACE של ילד 662 נרשמו מזהי-סטופ לשני החוזים:

```
2026-08-13 17:46:00 [INFO] [TradeManager] Sierra IDs stored on trade 662:
    {'sierra_order_id': 10136, 'c1_target_id': 10134, 'c1_stop_id': 10135, 'c2_stop_id': 10137}
```

בנוסף, הסטופ הראשוני של הילד כלל אינו עובר דרך `MODIFY_STOP` — הוא חלק מה-**PLACE**
עצמו (`bar_level_detector.py:1002`, `"stop": dec.stop`). הילד יוצא מוגן מלידתו.
✅ **אין חוזה-חיזוק חשוף. הסיכון שנחשד בו — לא קיים.**

---

## 5. 🔴 BLOCKER-1 — החיזוק מתבצע מול הספרים, לא מול סיירה

`n_contracts_open` (התנאי "יש פוזיציה חיה לחזק") מגיע מ-
`trade_contract_count(trade)` (`bar_level_detector.py:978-979`), שקורא
`quality["contracts"]` (`manager.py:66-88`) — **מספר בספרים**. הוא לעולם לא קורא
`sierra_state.position_qty`.

**ראיית-שטח, אותה שנייה של ה-PLACE של ילד 662:**

```
2026-08-13 17:46:00 [INFO] [TradeManager] Sierra IDs stored on trade 662: {...}
2026-08-13 17:46:00 [WARNING] [Reconciler] SYS-3 DIVERGENCE: TM says 4 contracts
    ['#662(live,LONG,2c)', '#661(live,LONG,1c)', '#660(live,LONG,1c)'],
    Sierra says 1 (src=state). Records ≠ reality! [phantom-heal streak 0/3]
```

הספרים אמרו 4 חוזים, סיירה החזיקה **1**. המערכת חיזקה פוזיציה שכבר כמעט לא הייתה קיימת.

**וההצטברות סיבתית, לא רקע:**

```
$ awk '/^2026-08-13 16:55:/,/^2026-08-13 17:00:33/' /tmp/backend.err.log | grep -c 'SYS-3 DIVERGENCE'
0
$ awk '/^2026-08-13 17:00:33/,/^2026-08-13 17:10:/' /tmp/backend.err.log | grep -c 'SYS-3 DIVERGENCE'
18
```

**אפס** דיברגנציות ב-5.5 הדקות שלפני החיזוק הראשון; **18** בעשר הדקות שאחריו.
זה גם מסביר את `phantom_reconcile` על 660/661 ואת ההחלקה של 5.25 נק' על 662.

---

## 6. 🔴 BLOCKER-2 — "פעם אחת להורה" אינו חוסם שרשרת

התקרה נבדקת ב-`scale_in.py:69`:

```python
if n_contracts_open + cfg.add_contracts > cfg.max_total_contracts:
    return None
```

`n_contracts_open` הוא של **העסקה הבודדת** (ילד = 2), לא של החשבון. לכן החישוב הוא תמיד
`2 + 2 = 4 ≤ 8` → **אף פעם לא חוסם**.

**בדיקה מריצה** (`/tmp/scale_in_chain_check.py`, על `should_scale_in` האמיתי):

```
cfg: min_profit=6pt add=2c max_total=8c   dir_bias=UP, T1 banked each time
gen 1: +2c @7823.00 stop@7816.00  (סה"כ חוזי-מערכת: 6)
gen 2: +2c @7830.00 stop@7823.00  (סה"כ חוזי-מערכת: 8)
gen 3: +2c @7837.00 stop@7830.00  (סה"כ חוזי-מערכת: 10)
...
gen 8: +2c @7872.00 stop@7865.00  (סה"כ חוזי-מערכת: 20)
... never blocks: the max_total_contracts=8 cap compares 2+2 each
    generation, NOT the account total -> chain is UNBOUNDED
```

בשטח זה מוגבל בקצב (כל דור דורש T1 משלו + עוד 6 נק'; ב-08-13 לקח ~45 דקות לדור),
אבל **ב-08-13 השרשרת אכן הגיעה לדור 2 בלייב**. בטרנד חזק זה מצטבר.
התקרה "8" שמייקל פסק עליה **אינה נאכפת בפועל**.

---

## 7. מרג'ין — החישוב המלא

מקור-אמת, `~/SierraChart_Data/v9_export/sierra_state.json` (טרי, 06:29:13):

```json
{"is_sim":0,"position_qty":8,"avg_price":7807.25,"open_pnl":110.00,
 "trade_account":"37138283","acct_cash_balance":2645.49,"acct_account_value":2755.49,
 "acct_available_funds":554.61,"acct_margin_req":2200.88,"acct_under_margin":0,
 "acct_daily_pl":-270.00,"acct_loss_limit_reached":0}
```

מרג'ין לחוזה, לפי החשבון עצמו: `2200.88 / 8 = **$275.11**`
(תואם ל-`MES_MARGIN_PER_CONTRACT=276.21` ב-.env — לא מספר מומצא).

| תרחיש | חוזים | מרג'ין דרוש | מול $554.61 פנוי | תוצאה |
|-------|-------|-------------|-------------------|--------|
| הורה בלבד | 4 | $1,100.44 | **חסר $545.83** | ❌ נדחה |
| ילד-חיזוק בלבד | +2 | $550.22 | עודף **$4.39** (0.8%) | ⚠️ על הקצה |
| הורה + חיזוק | 6 | $1,650.66 | **חסר $1,096.05** | ❌ נדחה |
| שרשרת דור-3 | 8 | $2,200.88 | **חסר $1,646.27** | ❌ נדחה |
| **אחרי סגירת 8 הידניים** | 4+2 | $1,650.66 | מתוך ~$2,755 | ✅ עובר |

**האם הברוקר יקבל את זה היום? לא.** ההורה נדחה לפני שבכלל מגיעים לשאלת החיזוק.

**ואין רשת-ביטחון:** `MARGIN_AWARE_SIZING_V1=0` (`.env:404`), ולכן
`cap_contracts()` מחזיר מיד `"MARGIN_AWARE_SIZING_V1 off"` (`margin_sizing.py:98-99`)
וההזמנה נשלחת במלוא 4 החוזים אל תוך דחייה ודאית.

**זו אינה רגרסיה — זו פסיקה** (`RULED_FLAGS.yaml:253`, 08-13 19:40):

> "'קבעתי 4 חוזים — אני מבקש שזה יהיה 1:1' … **אם יחזרו דחיות-מרג'ין אמיתיות
> (ORDER_FAILED NLV) — לחזור למייקל עם הנתון, לא להדליק לבד.**"

הדוח הזה הוא בדיוק "הנתון" שהפסיקה ביקשה שיובא. **לא נגעתי בדגל.**
`flag_guard.py` → PASS 175/175.

---

## 8. רשימת-פעולות מדורגת

| # | חומרה | ממצא | מיקום | תיקון מוצע |
|---|--------|------|--------|-------------|
| 1 | 🔴 **BLOCKER** | אין מרג'ין ל-4 חוזים; $554.61 מול $1,100.44 | `sierra_state.json` (out-of-git) | **החלטת-מייקל:** לסגור את 8 הידניים, או להוריד גודל להיום, או לוותר על מסחר-מערכת. אין תיקון-קוד — זו החלטת-הון |
| 2 | 🔴 **BLOCKER** | חיזוק מול ספרים ולא מול סיירה (0→18 דיברגנציות) | `bar_level_detector.py:978-979` | לקרוא `_sierra_state_qty()` ולדרוש `abs(qty) >= n_open` לפני PLACE; פער → לדלג ולהתריע |
| 3 | 🔴 **BLOCKER** | שרשרת חיזוקים ללא-חסם; תקרת-8 לא נאכפת | `scale_in.py:69` + `bar_level_detector.py:961` | לחסום `classification=="SCALE_IN"` מלהיות הורה, **ו**/או להשוות את התקרה לסך-החשבון |
| 4 | 🟠 **FIX-TODAY** | `_exit_happened` מאשר ילד קטן ע"י יציאה גדולה (מקרים B ו-E) | `exit_verifier.py:149-167` | לדרוש `moved == n` בטווח-סבילות, או לקשור לפי `sierra_order_id`/מזהי-מילוי במקום דלתא-כמות |
| 5 | 🟠 **FIX-TODAY** | `FLATTEN_ACCOUNT` של ההורה סוגר גם את הילד וגם את הפוזיציה הידנית של מייקל | `bar_level_detector.py:743` | להחיל את `_account_holds_foreign_position` גם על השידור הראשון, לא רק על ה-retry |
| 6 | 🟡 **LATER** | גודל-הילד תלוי ב-`SIZE_CAP_OVER_FIXED_V1` שברירת-מחדלו בקוד OFF (אחרת 2→4) | `sierra_command.py:642-668` | לפטור SCALE_IN מ-`FIXED_CONTRACTS_*` במפורש, כמו `fixed_contracts_exempt` של CONFLUENCE |
| 7 | 🟡 **LATER** | `scale_in_child_pending=true` נשאר תקוע לנצח על 660/661/670 | `bar_level_detector.py:991` | לנקות אחרי אישור ה-PLACE |
| 8 | 🟡 **LATER** | ההחלקה של 5.25 נק' על 662 (סטופ 7822.50 → מילוי 7817.25) לא הוסברה | — | לא ניתן לקבוע ממה שבידי; נדרש יומן-המילויים של סיירה מ-08-13 17:47 |

---

## 9. מה **לא** ניתן לקבוע מהראיות שבידי

- **האם הילדים רווחיים.** n=3, נטו −$72.50. מדגם קטן מדי. יסגור את זה: replay של
  SCALE_IN על ארכיון-הימים בסגנון `gate_profit_audit.py`.
- **מקור ההחלקה על 662.** צריך את fills-journal של סיירה מ-08-13 17:47:25.
- **התנהגות ה-4 באגים בשוק חי.** מאמת-היציאה, ה-dedup ו-`contract_size` נחתו לפני
  פחות מ-36 שעות; אין להם ולו יום-מסחר אחד. הבדיקות כאן הן על קוד-רץ אך לא בשוק פתוח.
- **האם `dir_bias` יהיה זמין בפתיחה.** אם `None` — תנאי "עם-הטרנד" מדולג בשקט
  (`scale_in.py:71`), והחיזוק יכול לצאת נגד הטרנד. לא נבדק על בר-פתיחה של היום.

---

## נספח — כל הפקודות שהורצו (Rule 5)

כל הבדיקות רצו **על ה-Mac** דרך Desktop Commander (לא מהסנדבוקס — הסנדבוקס מנותק
מה-DB/backend ומייצר דוחות-שקר).

```bash
# ראיות-חיות
grep -n "ScaleIn" /tmp/backend.err.log
grep -c "BarLevelDetector" /tmp/backend.err.log
awk '/^2026-08-13 16:55:/,/^2026-08-13 17:00:33/' /tmp/backend.err.log | grep -c 'SYS-3 DIVERGENCE'
awk '/^2026-08-13 17:00:33/,/^2026-08-13 17:10:/'  /tmp/backend.err.log | grep -c 'SYS-3 DIVERGENCE'
cat ~/SierraChart_Data/v9_export/sierra_state.json
python3 scripts/flag_guard.py            # → PASS 175/175

# DB
/Applications/Postgres.app/Contents/Versions/latest/bin/psql postgresql://localhost/mems26 \
  -c "SELECT ... FROM v9_trades WHERE id IN (660,661,662,670,673) ORDER BY id;"

# בדיקות מריצות (writer של סיירה הוחלף ב-stub — לא נכתבה שום פקודה)
python3 /tmp/scale_in_dedup_check.py      # dedup לא בולע את סטופ הילד
python3 /tmp/scale_in_verifier_check.py   # _exit_happened מקרים A-E
python3 /tmp/scale_in_chain_check.py      # השרשרת אינה חסומה
python3 /tmp/scale_in_size_check.py       # הילד נשלח ב-2, לא ב-4
```

**READ-ONLY מאומת:** לא שונה `.env`, לא בוצע restart, לא נכתב ל-`~/SierraChart_Data`,
לא שונה אף קוד. הקובץ היחיד שנוצר הוא הדוח הזה.
