# WHY WE LOST — 2026-09-09 · שתי עסקאות-הלייב

**נכתב:** cowork-dev, ריצת-לילה 2026-09-09 23:16-23:22 · כל טענה נושאת פקודה + פלט-גולמי (Rule 5)
**קהל:** מייקל · **המסקנה בשורה אחת נמצאת בסוף §3.**

---

## 0 · המספר האמיתי — הברוקר, לא הספרים

```
$ python3 scripts/sierra_activity_join.py --date 2026-09-09 --write     [23:16:40]
# 33 executions · 25 Closed-Trade-P/L records · broker day total +135.00
 trade dir   books_entry  fill_entry  Δentry  books_pnl broker_pnl      recon  ok       Δ$
  1328 LONG      7643.25     7643.25   +0.00     -40.00     -40.00     -40.00  OK    +0.00
  1343 LONG      7652.50     7652.75   -0.25    -131.25    -137.50    -137.50  OK    +6.25
 TOTAL                                          -171.25    -177.50                   +6.25
```

**הלייב היום = −$177.50, לא −$171.25.** ההפרש `+6.25` הוא החלקה של `0.25` נק' בכניסת `#1343`
(‏`7652.50` בספרים מול `7652.75` בפועל) × 5 חוזים × $5. `pnl_sierra` נכתב על שתי השורות.

> `broker day total +135.00` הוא **החשבון כולו** (‏37138283 משותף עם אתי). שלנו −$177.50;
> השארית `+$312.50` אינה שלנו. אין לצטט `+135` כתוצאה של המערכת.

---

## 1 · למה LONG הותר בכלל ביום Variation שההרחבה שלו הייתה DOWN

### 1.1 · המערכת ידעה שהכיוון DOWN — בצל בלבד

```
$ awk '/^2026-09-09 19:05:04/ && /System0/' /tmp/backend.err.log       [23:18:50]
2026-09-09 19:05:04 [INFO] [bar_level_detector] [System0] SHADOW DIR: context.day_bias=DOWN |
  scattered: expansion=None dir_bias=DOWN seed=None | agree=True |
  opening=UNKNOWN(NEUTRAL,0.00) day_type=Variation balance=UNKNOWN
```

`day_bias=DOWN`, `agree=True`, `day_type=Variation` — נכון, ומסומן **SHADOW**. הצל צדק כל היום.

### 1.2 · שורת-הפלייבוק

`config/dalton_playbook.yaml:129`
```yaml
- condition: "day_type in [Variation, Normal_Variation]"
  bias: extension_direction_once_then_BOTH
  entry_kinds: [BREAK, VALUE_RETURN]
  stop_rule: BEYOND_LEG_EXTREME
  target_rule: POC
```

### 1.3 · 🔑 השורש — ה-bias **מעולם לא התהפך ל-BOTH באירוע. הוא נולד BOTH.**

`backend/v9/services/dalton_playbook.py:97-98`
```python
if rule_bias.startswith("extension_direction"):
    return direction_hint or "BOTH"
```

**אין מכונת-מצבים של "once".** הסיומת `_once_then_BOTH` ב-YAML היא **דקורטיבית** — הפונקציה
מחזירה `direction_hint`, ואם הוא `None` היא נופלת ל-**`BOTH`** (fail-open).

ומאיפה מגיע `direction_hint`? `trading_gateway.py:1134-1149` — **אך ורק** מ-
`_resolve_live_cls()['direction']`, עם נפילה-לאחור שחלה על `OPENING_*` בלבד. `VEGAS`
ו-`BULL_FLAG_LONG` אינם `OPENING_*` ⇒ הנפילה-לאחור לא חלה.

**הראיה החותכת — לא הסקה, ספירה:**
```
$ grep -c "dalton_intent:bias" /tmp/backend.err.log                    [23:20:17]
0
```
**אפס.** זרוע-ה-bias של הפלייבוק לא חסמה עסקה **מעולם**, בכל הלוג. ‏`direction_hint` תמיד `None`
⇒ ה-bias תמיד `BOTH` ⇒ **כל כיוון מותר בכל סוג-יום.**

ואישור עקיף מאותו יום: `v9_day_type_state.direction` הוא `NULL` בכל 39 הסשנים שהמדידה כיסתה
(‏`75 rows / 58 non-null` בטבלה כולה, `0` סשנים עם תווית-כיוון שמישה) — מנוע-סוג-היום כותב
`direction`, אבל לא בערך ש-`_resolve_live_cls` יודע לקרוא.

**האסימטריה בשטח באותו יום:** בזמן ששתי עסקאות-LONG נגד-ההרחבה הותרו בשקט,
```
2026-09-09 22:55:09 [Gateway] BLOCKED system=2 pattern=DOUBLE_TOP_AA_SHORT dir=SHORT
  entry=7644.75 blocked_by=dalton_intent:stand_down
```
‏`SHORT` — הכיוון הנכון ליום — נחסם. פילוח היום: `22 dir=LONG · 18 dir=SHORT` נחסמו,
`26 stand_down · 14 kind`, **`0 bias`**.

### 1.4 · 📊 המדידה — 39 סשנים, שורות מתומחרות-ברוקר בלבד

ההרחבה נגזרה מהברים (‏IB = 12 הברים הראשונים; צד-ההרחבה = החריגה הגדולה מבין
`max(high)−ib_high` ל-`ib_low−min(low)`), כי `v9_day_type_state.direction` ריק.
`66 מ-69 סשנים` קיבלו תווית.

```
=== VARIATION days (Variation+Normal_Variation) ===        [23:21:08]
bucket                  n        sum$    win%      avg$
WITH-extension         32      158.75     59%      4.96
COUNTER-extension      19     -715.00     32%    -37.63
(no extension)          1       30.00

=== ALL broker-priced (110 rows / 39 sessions) ===
WITH-extension         66      473.75     56%      7.18
COUNTER-extension      43     -958.75     37%    -22.30
```

> **‏🔴 זה המספר של הלילה.** בימי-Variation, נגד-ההרחבה = **−$715 על 19 עסקאות, 32% הצלחה**,
> מול **+$158.75 על 32, 59%** עם-ההרחבה. על כל המדגם: נגד-ההרחבה −$958.75 מול +$473.75.
> **הספר כולו (−$455) הוא בדיוק דלי-נגד-ההרחבה.** בלעדיו: **+$473.75.** מרווח של $928.75 על 39 סשנים.
>
> שתי העסקאות של היום היו **שתיהן** נגד-ההרחבה.

**מועמד-לשינוי (מדידה בלבד — לא שונה דבר):** שורת-Variation ב-YAML תישאר כיוונית, או תדרוש
טריגר-מבני לפני היפוך. **פסיקת-מייקל נדרשת.**

---

## 2 · למה הסטופים היו 4.00 ו-5.25 נק' — מי כתב אותם

### 2.1 · `#1328` — הפותר **דחה**, והסולם כתב מתחת לרצפה של הפותר

```
$ awk '/^2026-09-09 19:05:0/' /tmp/backend.err.log                      [23:17:35]
19:05:03 [V2Sizing] SIZE_CAP_CUT: risk 18.5pt > cap 9.2pt → contracts 5→2 (floor=2)
19:05:03 [Woodies] V2 sizing: VEGAS contracts=2 mode=tactical risk=18.5pt
19:05:04 [StopResolver] IB floor 6.82pt (35% of IB 19.50) > ATR floor 5.50pt
19:05:04 [StopResolver] no valid rung in band → rejected
19:05:04 [Gateway] STOP ARBITRATION: STEP_SCALED_LADDER OVERRODE StopResolver
         (7624.75 → 7639.25) median=6.75 t1=7646.75 t2=7650.00 t3=7653.50
19:05:04 [Gateway] §3 STRUCT_TARGETS_WIN: day_type=Variation … → 7652.25/7657.25/7663.25
19:05:04 [SierraCmd] §6 RISK_BUDGET capped by sizer: budget=5, sizer=2 → using 2 (הזהיר גובר)
```

- **העוגן-המבני של היצרן היה `7624.75`** (‏18.5 נק' — תואם `V2 sizing … risk=18.5pt`).
- `StopResolver` חישב רצפת-להקה של **6.82 נק'** ואז **`rejected`** — אין שלב מבני תקף בלהקה.
- **`STEP_SCALED_LADDER` דרס ל-`7639.25` = 4.00 נק' — מתחת לרצפה של הפותר עצמו (6.82).**

**‏🔑 זה fail-open:** כשאין שלב מבני תקף, התשובה הנכונה היא להרחיב למבנה או **לא לקחת את
העסקה**. במקום זאת הסולם המציא סטופ גיאומטרי צר יותר מהמינימום שהפותר בדיוק הכריז עליו.

### 2.2 · `#1343` — הפותר **בחר מבנה במפורש**, והסולם דרס אותו **פנימה**

```
$ awk '/^2026-09-09 20:55:0/' /tmp/backend.err.log                      [23:17:35]
20:55:06 [V2Sizing] SIZE_CAP_CUT: risk 13.0pt > cap 7.5pt → contracts 5→2 (floor=2)
20:55:06 [FiveMin] V2 sizing: Flag contracts=2 mode=tactical risk=13.0pt
20:55:06 [S2] T1Setup emitted: BULL_FLAG_LONG LONG entry=7652.50 stop=7639.50 tier=MEDIUM contracts=5
20:55:06 [StopResolver] rung 4 (r4) dist=7.25 > cap=6.77 → WIDEN-TO-STRUCTURE (structural wins, ATR→size-cut)
20:55:06 [Gateway] STOP ARBITRATION: STEP_SCALED_LADDER OVERRODE StopResolver (7639.50 → 7647.25) median=8.62
20:55:06 [Gateway] RR_NO_SELF_INFLICTED: R:R 0.29 came from OUR cut (t1 7654.00);
         the producer's t1 7657.00 gives 0.86 — restoring it instead of blocking
20:55:06 [SierraCmd] RISK_BUDGET: risk=5.2 pts → raw=8.6 → floor=8 → min(ruled=5)=5
```

- היצרן: `7639.50` (13.0 נק'). הפותר: `rung 4` במרחק `7.25` ⇒ `7645.25`, ורשם במפורש
  **`WIDEN-TO-STRUCTURE (structural wins)`** — כלומר עשה **בדיוק** את פסיקת-10:20.
- **`STEP_SCALED_LADDER` דרס גם את זה, ל-`7647.25` (5.25 נק') — צר ב-2.00 נק' מהבחירה המבנית.**

### 2.3 · התשובה לשאלה "מי קבע את הסטופ הסופי"

> **בשתי העסקאות: `STEP_SCALED_LADDER_V1`, בשלב `STOP ARBITRATION` ב-`trading_gateway`.**
> הוא דרס פעם עוגן-יצרן שנדחה (‏`#1328`) ופעם בחירה-מבנית מפורשת של הפותר (‏`#1343`),
> ובשני המקרים כתב **צר יותר** מהמינימום המבני שהשלב שלפניו חישב.

**ובנוסף — שורת-הפלייבוק עצמה נעקפה:** היא מורה `stop_rule: BEYOND_LEG_EXTREME`, ואף לא
אחת מהעסקאות קיבלה סטופ מהכלל הזה.

**‏⚠️ הערת-מיקום (‏T-291):** הסטופ של `#1343` ב-`7647.25` יושב **0.25 נק' מעל ה-POC של
הסשן (`7647.00`, מ-`cross_context`)** — המחיר בעל נפח-המסחר הגבוה ביותר ביום, שהמחיר מסתובב
בו בהגדרה. גם `target_rule: POC` היה שם **מתחת לכניסה** (‏7647.00 < 7652.50) — יעד-POC ל-LONG
מעל ה-POC אינו קוהרנטי.

---

## 3 · מה `trade_economics` היה עושה — והשאלה היחידה שחשובה

### 3.1 · הפונקציה (ריצה טהורה, בלי דגל)

```
$ python3 -c "from backend.v9.services.trade_economics import economics; …"   [23:21:29]
#1328  BEYOND_LEG_EXTREME → stop=7635.25 risk=8.00  contracts=5  t1=7651.25   reject=None
#1328  BEYOND_IB_EDGE     → stop=None    risk=0     contracts=0  reject=no_anchor
#1343  BEYOND_LEG_EXTREME → stop=7643.25 risk=9.25  contracts=4  t1=7661.75   reject=None
#1343  BEYOND_IB_EDGE     → stop=None    risk=0     contracts=0  reject=no_anchor
```
אף עסקה **לא** נדחתה כבלתי-ניתנת-למימון תחת `BEYOND_LEG_EXTREME`.
(‏`BEYOND_IB_EDGE` מחזיר `no_anchor` בשתיהן — רלוונטי ל-§4.2, ה-IB היה שגוי היום.)

### 3.2 · 🔴 הסימולציה על הברים שאחרי הכניסה

הסימולטור **משחזר את שתי התוצאות בפועל במדויק** (‏−$40.00 ו-−$137.50 מול הברוקר) ⇒ מותר
להאמין לתרחישים-הנגדיים שלו.

```
                                                                              [23:22:02]
### #1328 VEGAS LONG entry 7643.25  (ברוקר −$40.00) ###
  ladder ACTUAL 4.00pt / 2c        stop=7639.25 n=2  STOP hit 19:05     pts= -4.00  P&L=  -40.00
  trade_economics BLE     / 5c     stop=7635.25 n=5  STOP hit 19:05     pts= -8.00  P&L= -200.00
  producer structural 18.5pt / 2c  stop=7624.75 n=2  T1 hit 20:10       pts= +9.00  P&L=  +90.00

### #1343 BULL_FLAG LONG entry 7652.75  (ברוקר −$137.50) ###
  ladder ACTUAL 5.25pt / 5c        stop=7647.25 n=5  STOP hit 21:05     pts= -5.50  P&L= -137.50
  trade_economics BLE     / 4c     stop=7643.25 n=4  STOP hit 21:15     pts= -9.50  P&L= -190.00
  producer structural 13.0pt / 3c  stop=7639.50 n=3  open→EOD 7645.50   pts= -7.25  P&L= -108.75
```

| הצבה | ‏#1328 | ‏#1343 | **סה"כ** |
|---|---|---|---|
| הסולם (בפועל) | −$40.00 | −$137.50 | **−$177.50** |
| `trade_economics` ‏`BEYOND_LEG_EXTREME` | −$200.00 | −$190.00 | **−$390.00** |
| עוגן-היצרן, גודל נגזר-מהסטופ | **+$90.00** | −$108.75 | **−$18.75** |

### 3.3 · 🔑 המשפט שמכריע את `TRADE_ECONOMICS_AUTHORITY_V1`

> **לא — הסטופ המבני לא היה מציל את שתיהן.** הוא מציל את `#1328` (‏−$40 → **+$90**, ה-T1 ב-`7652.25`
> נגע ב-20:10) ומקטין את `#1343` (‏−$137.50 → −$108.75), אבל **`trade_economics` בהצבה שלו-עצמו
> היה מחמיר את שתיהן — −$390 מול −$177.50 בפועל, פי 2.2.**
>
> ⇒ **`TRADE_ECONOMICS_AUTHORITY_V1=1` אינו מוצדק הלילה. `diff` בלבד.**

**והמסקנה החשובה יותר:** רוחב-הסטופ **לא** היה השגיאה העיקרית. `#1343` הפסידה בכל הצבה שנבדקה,
כי המחיר פשוט לא עלה — התזה הייתה שגויה. **השגיאה הייתה לקחת שתי עסקאות-LONG נגד-ההרחבה
בכלל.** שם נמצא ה-−$715 (§1.4), ולא ברוחב-הסטופ.

---

## 4 · הגודל — 2 מול 5 על אותו יום, אותו כיוון

| | `#1328` (S4) | `#1343` (S2) |
|---|---|---|
| הסייזר אמר | `SIZE_CAP_CUT … 5→2` | `SIZE_CAP_CUT … 5→2` |
| מה נכתב ל-metadata | `sizing_contracts=2` (`woodies_system.py:1296-1298`) | `sizing=5` — **דרגת-האיכות** (`five_min_system.py:284`) |
| §6 `min(budget, sizer)` | ראה `2` ⇒ **חסם ל-2** | ראה `5`; `5 < 5` = False ⇒ **לא נגע** |
| נשלחו | **2** | **5** |
| הפסד | −$40 | −$137.50 |

**ההפרש אינו החלטת-סיכון — הוא אי-התאמת-מפתח ב-metadata.** בשתי העסקאות הסייזר אמר `2`;
רק S4 ציית. פלט-ה-V2 של S2 הוא **לוג-בלבד** ואינו מחובר במורד-הזרם
(`grep -n sizing_contracts five_min_system.py` ⇒ שורה 284 בלבד). אומת ע"י המדידה של 21:48:
**§6 הופעל 26 פעם היום — 15 בהקשר `[Woodies]`, `0` בהקשר `[FiveMin]`.**

`FIXED_CONTRACTS_5=1` הוא **תקרה ולא רצפה** (`min(ruled=5)`), ותקרת ה-ACSIL 5-OCO חופפת לה.
לא נגעתי ב-`RISK_BUDGET_USD` / `RISK_MIN_CONTRACTS` / `FIXED_CONTRACTS_5`.

**⚠️ האירוניה, שאינה המלצה:** דווקא העסקה שבה הסייזר **נעקף** (5 חוזים) הפסידה פי 3.4.
‏`n=2` אינו מדגם. **מי בעל-הגודל = פסיקת-מייקל.**

---

## 5 · האם שתי העסקאות היו אמיתיות — כן, שתיהן

| | `#1328` | `#1343` |
|---|---|---|
| `exit_fills` | 2 רגלי `STOP` @7639.25 (הזמנות `11079`,`11082`) | 4 רגלי `STOP` @7647.25 = `1+2+1+1` (‏`11088/11091/11094/11097`) |
| יומן-סיירה | ‏`recon −40.00` **OK** | ‏`recon −137.50` **OK** |
| `entry_ts` | `19:05:06.867930+03` | `20:55:08.309084+03` |
| `is_synthetic` | `0` | `0` |
| מסקנה | ✅ **מימוש אמיתי** | ✅ **מימוש אמיתי** |

שתיהן מופיעות ב-`TradeActivityLog` עם רשומת `Closed-Trade-P/L` ונסגרו `OK` מול הספרים.
**עסקת-הרפאים היא `#1337` בלבד** (‏T-290, `+$30`) — והמפריד הוא **`entry_ts IS NULL`** עליה,
מול `entry_ts` מלא על שתי אלה. אין לסכם את `#1337` לתוך היום.

---

## 6 · מה נדרש ממייקל (מספרים מצורפים)

1. **נגד-ההרחבה — 19 עסקאות, −$715, 32% (מול +$158.75/59% עם-ההרחבה).** לחסום כיוון-נגדי
   בימי-Variation, או לדרוש טריגר-מבני? ⇒ שינוי YAML.
2. **`direction_hint` אף פעם לא מחובר — `0` חסימות-bias בכל הלוג.** לחווט את
   `day_bias` מהצל אל הפלייבוק? ⇒ מפעיל את זרוע-ה-bias לראשונה.
3. **`STEP_SCALED_LADDER` דורס את הפותר גם כשהפותר דחה או בחר מבנה.** לכפוף אותו לרצפה
   המבנית? ⇒ שינוי-סיכון.
4. **בעל-הגודל ב-S2:** לחווט את פלט-ה-V2 של S2 ל-§6 כמו ב-S4 (‏5→2), או להשאיר?
5. **`TRADE_ECONOMICS_AUTHORITY_V1`** — ‏**`diff` בלבד.** המדידה (§3.2) שוללת `=1`.

---

**אפס נגיעה בזמן הניתוח הזה:** לא שונה דגל · לא נערך `.env` · לא נגעתי בפוזיציה/סלוט ·
`trade_economics` הורץ כפונקציה טהורה מחוץ למסלול-החי.
