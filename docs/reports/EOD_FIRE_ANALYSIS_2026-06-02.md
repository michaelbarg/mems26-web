# EOD Fire Analysis — 2026-06-02 (Agent B, SHADOW)

**מצב:** קריאה-בלבד. לא שונה קוד/DB/שירות/דגל. כל מספר מגובה בשאילתת `file:data/mems26_local.db?mode=ro`.
**חלון:** היום UTC = 2026-06-02. RTH נסגר 20:00 UTC; הניתוח רץ ~20:15 UTC.

## ⚠️ הערות מצב מקדימות (לקרוא קודם)

1. **`PRAGMA quick_check` החזיר `database disk image is malformed`** בקריאה הראשונה דרך
   ה-mount הממופה. **זוהי כנראה false-positive מוכרת** של קריאה חיה מעל mount מסונכרן
   (CLAUDE.md §DB Write-Safety). הוכחה שה-DB קריא בפועל: קריאות חוזרות הצליחו מיד —
   `SELECT count(*) FROM v9_trades = 398`, וכל השאילתות בדוח רצו נקי. **המבחן היחיד
   האמין הוא `integrity_check` כשה-backend מושבת** — לא בוצע (read-only, backend חי).
   **המלצה:** הרצת `integrity_check` backend-down בסוף היום לפני הצהרת GO.
2. **ה-backend חי על המק** (לא נגיש ב-curl מתוך ה-sandbox): `data/mems26_local.db-wal`
   פעיל 4.3MB + `-shm`, וזרמים ממשיכים להיכתב עד 20:15. לכן snapshot מ-pattern-status
   לא נשלף — הניתוח כולו מבוסס DB.
3. נוכחות `*.bad2 / *.corrupt / *.corrupt.bak` בתיקיית `data/` (חתימת קרב ה-corruption
   של 2026-06-02 שמתועד ב-CLAUDE.md). לא נגעתי בהם.

---

## 1. סיכום ירי היום

| מערכת (firing_system) | #fires היום | shadow | demo | תוצאות | #setups | סטטוס |
|---|---|---|---|---|---|---|
| **S4 Woodies** (`fs=4`) | **17** | 9 | 8 | 2 WIN / 15 LOSS | n/a | ירה הרבה, הפסיד כמעט הכל |
| **S3 Footprint-lineage** (`fs=3`) | 1 | 1 | 0 | 1 PARTIAL (פתוח) | — | טרייד יחיד 04:32 (Globex) |
| **S2 Five-Min** | **0** | 0 | 0 | — | **0** | רדום — אפס setups, state ריק |
| **S1 day_type** | n/a (מסווג, לא סוחר) | — | — | — | — | סיווג Normal, ראה §3 |

> סה"כ 18 טריידים היום (`SELECT count(*) FROM v9_trades WHERE substr(entry_ts,1,10)='2026-06-02'`).
> מיפוי `firing_system→מערכת` הוא **הסקה** (לא מאומת מטבלת-מקור): `fs=4` תואם בזמנים
> לאותות Woodies, `fs=3` היא המערכת הדומיננטית היסטורית (374/398 טריידים אי-פעם) ותואמת
> לשושלת Footprint שכעת `FOOTPRINT_DISABLED`. **strategic-stop:** לאמת מיפוי לפני הסתמכות.

**כל 17 טריידי Woodies יצאו ב-`STOP_HIT`.** 15 ב-`pnl_r=-1.0`, ו-2 ה"WIN" (`pnl_r=0.81`,
17:20) הם stop-out אחרי partial. אין ולו exit אחד דרך T1/T2 ביעד.

טבלת טריידים גולמית (entry UTC):
```
04:32 fs3 LONG  PARTIAL  (פתוח)
06:46 fs4 LONG  LOSS -1.0   07:46 fs4 SHORT LOSS -1.0
15:06 fs4 SHORT LOSS -1.0   16:09 fs4 SHORT LOSS -1.0
16:10 fs4 SHORT LOSS -1.0   16:12 fs4 SHORT LOSS -1.0
17:09 fs4 LONG  LOSS -1.0   17:09 fs4 LONG  LOSS -1.0
17:20 fs4 SHORT WIN  +0.81  (×demo+shadow לכל שורה)
```

---

## 2. לכל תבנית — נדרך / ירה / סיבה חוסמת

### S4 Woodies — 130 אותות היום → 17 טריידים (~13% המרה)

`SELECT signal_type,count(*) ... WHERE substr(ts,1,10)='2026-06-02'`:

| תבנית | #אותות היום | conf ממוצע | ירה לטרייד? | הערה |
|---|---|---|---|---|
| TLB  | **61** | 0.85 | חלקית | הדומיננטי המוחלט; 59 מתוכם SHORT |
| ZLR  | 23 | 0.66 | חלקית | conf 0.53–0.82 (היחיד עם פיזור) |
| HTLB | 13 | 0.65 | — | conf קבוע 0.65 |
| VEGAS| 11 | 0.75 | — | כולם LONG |
| HFE  | 7  | 0.70 | — | SHORT, CCI חיובי גבוה (97–168) |
| GB100| 7  | 0.74 | — | — |
| GHOST| 6  | 0.70 | — | LONG |
| TT   | 1  | 0.70 | — | בקושי נדרך |
| FAMIR| 1  | 0.75 | — | בקושי נדרך |

**כל 9 התבניות נדרכו לפחות פעם אחת** (ZLR,TLB,TT,GB100,VEGAS,GHOST,FAMIR,HTLB,HFE).
הטיה כיוונית חדה: **97 SHORT מול 33 LONG**.

**הסיבה החוסמת הדומיננטית (להמרה לטרייד) אינה ניתנת לספירה מדויקת מה-DB:** אין עמודת
"blocked_reason" פר-אות, ו-`pattern-status` (שמחזיק reason/blockers סופיים) לא נגיש מה-sandbox.
מה שכן נגזר מהנתונים: 130 אותות נוצרים ברצף (TLB לבדו 61), אך רק 17 הפכו לטרייד — כלומר
gate ההמרה דוחה ~87% מהאותות. **המלצה אופרטיבית בלבד:** להוסיף לוג מתמשך של reason
פר-אות (armed→blocked) כדי שניתן יהיה לכמת זאת ב-EOD. (ראה §5.)

### S2 Five-Min — 3 וריאציות (A_VSA / B_RVOL / C_STRICT)

- `v9_five_min_setups` = **0 שורות (אי-פעם)**.
- `v9_five_min_state` = **0 שורות (אי-פעם)**.
- 0 טריידים מ-`fs=2` אי-פעם.

**אף וריאציה לא נדרכה ולא ירתה** — לא בגלל gate, אלא כי **המנוע לא מייצר setups ולא כותב
state כלל.** זו לא "תבנית שלא ירתה" אלא **מערכת רדומה / לא-מחווטת.** הממצא הכי משמעותי היום.

### S3 Footprint — מושתק

`FOOTPRINT_DISABLED` פעיל. בכל זאת קיים טרייד `fs=3` בודד (id 381, 04:32 LONG PARTIAL פתוח).
`v9_system_signals` רשם היום רק `system_id=3 / IMBALANCE` (169 רשומות) — כלומר נתיב ה-imbalance
עדיין מסווג ורושם. **strategic-stop:** לוודא שטרייד fs=3 הוא שריד ישן/Globex ולא נתיב footprint
שירה אחרי ה-disable.

---

## 3. ציר זמן day_type (S1)

**Live** (`v9_day_type_history`):
```
2026-06-02  Normal  LOCKED_LOW_CONF  conf=68  open=OPEN_AUCTION_IN  IB=WIDE  (stage C3)
2026-06-01  Normal  LOCKED_LOW_CONF  conf=68  open=OPEN_AUCTION_IN  IB=MEDIUM
```

**Shadow** (`v9_day_type_shadow_transitions`, 28 מעברים היום): מ-14:50 UTC (session_min 80)
ואילך, **Normal → Variation** שוב ושוב, עם `E_up` שמטפס **0.18 → 1.15** ו-`E_dn=0.00`
לכל אורך הדרך. דעיכה לקראת הסגירה (16:40: E_up=0.49).

**אי-התאמה משמעותית:** ה-shadow זיהה יום **Variation חד-כיווני כלפי מעלה** (E_dn=0 לחלוטין),
בעוד ה-live נשאר נעול **Normal / low-conf**. זה ההקשר שמסביר את §1: **Woodies שרת SHORT
(97/130) לתוך התרחבות-מעלה חד-כיוונית → 15/17 stop-outs.** ה-WIN היחיד (17:20) הגיע בדיוק
כשה-E_up דעך (16:40 → 0.49). המערכת נלחמה במגמה שה-shadow כבר סימן.

---

## 4. איכות נתונים / זרמים

| זרם | latest ts (UTC) | שורות היום | מצב |
|---|---|---|---|
| `v9_bars_5min` | 20:10:00 | 243 (12/שעה רציף) | ✅ טרי ובריא |
| `v9_bars_imbalance` | 20:15:33 | 33 | ✅ טרי (event-driven, ספירה נמוכה תקינה) |
| `v9_woodies_signals` | 20:15:27 | 130 | ✅ טרי |
| `v9_bars_cumulative_delta` | **19:14:59** | 4161 | ⚠️ **תקוע ~1ש'** (שעה 19: 196 שורות מול ~600/שעה) |
| `v9_bars_5min_woodies` | **08:34:05** | **5** | 🔴 **מת מ-08:34 (~11.6ש' stale)** — כל היום רק 5 שורות, כולן 08:32–08:34 |

**🔴 ממצא קריטי — `v9_bars_5min_woodies` קפא ב-08:34 UTC** בעוד `v9_woodies_signals` טרי
(20:15). כלומר ייצור האותות רץ מנתיב חי (CCI בזמן-אמת מעל `v9_bars_5min`), אבל **טבלת
ה-bars המועשרת של Woodies לא נכתבת** — העמודות `cci_14, proj_hi, proj_lo, zlr_detected,
hfe_detected, trend_state, lsma_value` כולן stale מ-08:34. זה משבית את מקור הנתונים של
`WoodiesCciPanel` (UI/observability), ומסכן כל לוגיקה שקוראת מהטבלה המועשרת ולא מהזרם החי.

**אנומליה נוספת:** באחת מ-5 שורות Woodies של 08:34, `trend_state` מכיל מחרוזת timestamp
(`'2026-06-02 20:15:31'`) במקום ערך-מגמה — חשד ל-column-misalignment בכתיבה. שווה בדיקה.

**CVD תקוע ב-19:14** (~45 דק' לפני הסגירה) — קל, אבל לפי CLAUDE.md Rule 3 (`min/max`
amplifiers) ערך CVD תקוע שזולג ל-aggregators במורד הזרם הוא סיכון regression.

---

## 5. המלצות (data-grounded — המלצה בלבד, לא מימוש)

1. **🔴 S2 Five-Min — לבדוק חיווט/הפעלה.** `v9_five_min_setups` ו-`v9_five_min_state`
   ריקים אי-פעם, 0 טריידים. זה לא סף — המנוע לא רץ או לא כותב. **לאמת שה-stream/scheduler
   של Five-Min בכלל פעיל לפני שמכווננים ספים.** *(strategic-stop — וריאציה/חיווט S2: אישור Michael.)*

2. **🔴 `v9_bars_5min_woodies` — לתקן את הכותב המועשר.** קפא 08:34 בעוד האותות חיים. לבדוק
   מדוע הכתיבה לטבלה המועשרת נעצרה (writer נפרד? נחסם ב-`safe_writer` lock? כשל שקט?).
   זה גם מסביר UI ריק ב-WoodiesCciPanel. + לחקור את ה-`trend_state`=timestamp anomaly.

3. **🟡 Woodies — gate מודעות-יום.** Woodies ירה 97 SHORT לתוך יום שה-shadow סימן
   Variation-up (E_up→1.15, E_dn=0) ונמחק (15/17 stop). **לשקול gate שמכבד את ה-shadow
   day_type:** דיכוי/הקטנת SHORT כאשר `E_up` עולה מונוטונית ו-`E_dn≈0`. *(strategic-stop —
   נוגע ב-trading logic: אישור Michael.)* קודם לכך — לסגור את הפער live↔shadow day_type
   (live תקוע Normal low-conf בעוד shadow זיהה Variation 28 פעמים).

4. **🟡 Observability — לוג reason פר-אות.** אי-אפשר לכמת "הסיבה החוסמת הדומיננטית" כי אין
   עמודת `blocked_reason` ב-`v9_woodies_signals` וה-`pattern-status` לא נשמר ל-DB. **לשקול
   persist של reason/blockers פר-אות (armed→blocked→fired)** כדי שדוח ה-EOD יוכל לספור
   חוסמים במקום להסיק. (תמיכה: 130 אותות → 17 טריידים, ~87% נדחים ללא עקבה ב-DB.)

5. **🟡 CVD freshness alert.** CVD קפא 19:14 (~45דק' לפני סגירה). לשקול warning (לא debug)
   על stall של CVD כדי לזהות drift מוקדם (CLAUDE.md §No silent failures + Rule 3).

6. **🟢 integrity_check backend-down** בסוף היום לפני GO (ראה הערה מקדימה #1) — לאור היסטוריית
   ה-corruption של 2026-06-02.

---
*נוצר ע"י Agent B (EOD scheduled). קריאה-בלבד; לא בוצע שינוי. כל מספר מ-DB read-only לפי Rule 5.*
