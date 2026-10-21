# מפת-כניסה ליום — פתיחה → IB → שלב C → שלב D (2026-10-06)

**כותב:** Cursor agent · **נכתב:** 2026-10-06 ~16:05 IL · **קריאה בלבד** (בלי yaml, בלי `.env`, בלי ריסטארט, בלי קומיט).
**למי:** מייקל — מפה אחת של "מה מותר להיכנס ומתי", לפי הדוקטרינה ולפי מה שהעץ החי באמת עושה.

**מקורות (בסדר הזה):**
1. `config/dalton_playbook.yaml` — שלבים A/B/C/D. הכללים שם הם הדוקטרינה.
2. `config/decision_tree_v3.yaml` — **גרסה `3.4.0`** (שורת `version:`; הערת-הגרסה: "06.10 T-538: cutoff 20:00 → 22:00 · 05.10 cutoff layer · 03.10 T-529 edge on the responsive rows"). הטוען (`backend/v9/services/decision_tree.py:29`) קורא את הקובץ הזה אלא אם `DECISION_TREE_V3_PATH` עוקף — לא בדקתי env (קריאה בלבד). הקובץ הלא-מעוקב `decision_tree_v3.t543_prune.yaml` **אינו** הקובץ שהטוען קורא כברירת-מחדל.
3. `backend/v9/services/dalton_playbook.py::intent()` + `_resolve_bias()` — רק כדי לראות איך הטיה נבחרת.

**מילון קצר** (שמות מהקבצים, לא תרגום חופשי):
- **סוגי-כניסה (kind):** `WITH_DRIVE` (עם הדרייב) · `REVERSAL` (היפוך בקצה) · `EDGE_FADE` (דעיכה בקצה-ערך/IB) · `PULLBACK` (תיקון-המשך; כולל `TREND_STEP` = מדרגה) · `BREAK` (פריצה/יוזמה; כולל `INITIATIVE_*`, `GB100`, `TLB`, `DOUBLE_*`, `ZLR`) · `VALUE_RETURN` (`RE_ACCEPTANCE` — חזרה לערך).
- **הטיה (bias):** בפלייבוק `drive_direction` / `trend_direction` / `extension_direction*` = `direction_hint` (ואם אין רמז → `BOTH`); `reversal_direction` = ההפך מהרמז (`_resolve_bias`, שורות 85–98). בעץ אותו דבר נקרא `rel_bias` = כיוון-הסטאפ מול רמז-הסשן (`with` / `against` / `none`).
- **מדיניות `kinds_apply_to: counter_bias_only`** (פלייבוק שורה 20, העץ מקודד אותה): כשיש הטיה כיוונית — **כל** סוג-כניסה **עם** ההטיה מותר; רשימת-הסוגים חוסמת רק כניסות **נגד**. כשההטיה `BOTH`/אין רמז — הרשימה מחליטה.
- **פטור-הכישלון (T-329 / T-529):** כניסה נגד ההטיה או מחוץ למיקום מתקבלת בכל-זאת אם `edge == failed_extension` (דאבל מאושר בקצה-ההרחבה). קיים בעץ בלבד.
- **כלל-המיקום (T-319b, בעץ בלבד):** בשורות "רספונסיביות" (Normal / Neutral, וגם תווית-זמנית כזו בשלבי A/B) — LONG רק `near_val|below_value`, SHORT רק `near_vah|above_value`; כשהמיקום בסדר **רשימת-הסוגים מדולגת**; כשאין עדיין VA (`zone=unknown`) — הרשימה מחליטה.

---

## פתיחה (לפני שהיום נקבע) — שלבים A ו-B, 16:30–17:30 IL

שלב A = 16:30–16:45 (3 הברים הראשונים) · שלב B = 16:45–17:30 (עד נעילת ה-IB). `_resolve_phase` (שורות 66–71).

### OPEN_DRIVE — דרייב-פתיחה
**מה המכרז עושה:** מהבר הראשון כיוון אחד, בלי לחזור לפתיחה — הצד האחר "לא בא לעבוד". זה הפתיח הכי בטוח של דלטון, ולכן היחיד שמותר כבר בשלב A.

| | שלב A (16:30–16:45) | שלב B (16:45–17:30) |
|---|---|---|
| הטיה | `drive_direction` | `drive_direction` |
| סוגי-כניסה (פלייבוק) | `WITH_DRIVE` | `WITH_DRIVE`, `PULLBACK` |
| סטופ | `BEYOND_OPEN` — מעבר למחיר-הפתיחה | `BEYOND_OPEN` |
| יעד | `MEASURED_MOVE` | `MEASURED_MOVE` |
| גודל | `size_frac 0.5` (חצי) | `size_frac 1.0` (מלא) |
| ראנר | כן | כן |

**מה העץ באמת עושה** (`root_full → OPEN_DRIVE → A/B`):
- עם הרמז (`rel_bias=with`) → **TAKE** בכל סוג (`take_with_hint`).
- נגד הרמז → **SKIP** `bias`, אלא אם `failed_extension` → TAKE.
- אין רמז → A: `WITH_DRIVE` בלבד TAKE; B: `WITH_DRIVE|PULLBACK` TAKE; כל סוג אחר → SKIP `kind` (אלא אם failed_extension).
- אם התווית-הזמנית כבר `Normal|Neutral_*` → קודם כלל-המיקום: LONG ב-`near_val|below_value` / SHORT ב-`near_vah|above_value` → `loc_ok_then_bias` (נגד הרמז → SKIP, אחרת TAKE); `zone=unknown` → הענפים לעיל; כל אזור אחר → **SKIP** `location`.
- תואם לפלייבוק (פריטי-המיקום הם תוספת, לא סתירה).

### OPEN_TEST_DRIVE — בדיקה-ואז-דרייב
**מה המכרז עושה:** המחיר בודק קודם צד אחד (לרוב מעבר לרמה), נכשל שם, ואז דורש בכיוון ההפוך. הצד שנכשל הוא הרפרנס לסטופ.

| | שלב A | שלב B |
|---|---|---|
| הטיה | — (ברירת-מחדל `NONE`) | `drive_direction` |
| סוגי-כניסה | **אין** | `WITH_DRIVE`, `PULLBACK` |
| סטופ | — | `BEYOND_FAILED_SIDE` — מעבר לצד שנכשל |
| יעד | — | `MEASURED_MOVE` |
| גודל | 0 | 1.0 |
| ראנר | — | כן |

**העץ:** A → **SKIP** לכל סוג (`stand_down` / `location`; ההערה בעץ: "phase A has no test-drive row: stand-down wins"). B → `drive_B` — אותו היגיון כמו OPEN_DRIVE/B (עם הרמז כל סוג; אין רמז → `WITH_DRIVE|PULLBACK`; כלל-המיקום לתווית-זמנית Normal/Neutral). תואם.

### OPEN_REJECTION_REVERSE — דחייה-והיפוך
**מה המכרז עושה:** המחיר הולך כיוון אחד, נדחה (הקצה "נדחה"), ומתהפך דרך הפתיחה. הכניסה היא **לכיוון ההיפוך**, לא לכיוון המהלך הראשון.

| | שלב A | שלב B |
|---|---|---|
| הטיה | `NONE` | `reversal_direction` (ההפך מרמז-הדרייב, `_resolve_bias` 88–94) |
| סוגי-כניסה | **אין** | `REVERSAL`, `PULLBACK` |
| סטופ | — | `BEYOND_REJECTED_EXTREME` — מעבר לקצה שנדחה |
| יעד | — | `OPPOSITE_EDGE` — הקצה הנגדי |
| גודל | 0 | 1.0 |
| ראנר | — | **לא** |

**העץ:** A → **SKIP**. B → `orr_B`: עם הרמז כל סוג; נגד → SKIP (אלא failed_extension); אין רמז → `REVERSAL|PULLBACK` TAKE, אחר → SKIP `kind`. כלל-המיקום לתווית-זמנית Normal/Neutral. תואם ברשימת-הסוגים. (הערה: העץ מודד `rel_bias` מול "רמז-הסשן" שהגייטוויי מספק; האם הגייטוויי כבר הופך את הרמז לכיוון-ההיפוך — לא נבדק כאן.)

### OPEN_AUCTION_IN — מכרז-פתיחה בתוך הערך
**מה המכרז עושה:** רוטציה דו-כיוונית סביב הפתיחה, בתוך אזור-הערך של אתמול. אין שחקן יוזם; הכניסות הן דעיכות בקצוות בלבד, בגודל מופחת.

### OPEN_AUCTION_OUT — מכרז-פתיחה מחוץ לערך
**מה המכרז עושה:** אותה רוטציה, אבל מחוץ לערך של אתמול (פתיחת-גאפ). בפלייבוק שתי הפתיחות האלו הן **שורה אחת**.

| | שלב A | שלב B (שתיהן) |
|---|---|---|
| הטיה | `NONE` | `BOTH` |
| סוגי-כניסה (פלייבוק) | **אין** | `EDGE_FADE` בלבד |
| סטופ | — | `BEYOND_IB_EDGE` — מעבר לקצה ה-IB |
| יעד | — | `POC` |
| גודל | 0 | **0.5** (חצי) |
| ראנר | — | לא |

**העץ** (`OPEN_AUCTION_IN|OPEN_AUCTION_OUT → B`):
- תווית-זמנית `Normal|Neutral_*` → כלל-המיקום: בקצה הנכון → **TAKE** `take_location` (הטיה BOTH, הסוגים מדולגים); `unknown` → `kinds_auction_B`; אחר → SKIP `location`.
- תווית כבר `Trend_Normal|Trend_DD` בשלב B → `kind == BREAK` → **TAKE** `auction_B_trend_break` (T-484, פסיקת-מייקל 25.09 "כן"); סוג אחר → `kinds_auction_B`.
- כל תווית אחרת → `kinds_auction_B`: `EDGE_FADE` TAKE · **`REVERSAL` TAKE** (`auction_B_reversal`, S5/T-494, פסיקת 27.09) · אחר → SKIP `kind` (אלא failed_extension).
- **לא תואם לפלייבוק** בשני סוגים — ראה §איפה-לא-אותו-דבר.

### פתיחה לא-מסווגת (`UNKNOWN`)
פלייבוק: ברירת-מחדל `NONE` בשני השלבים. העץ: A ו-B → **SKIP** לכל סוג. תואם.

---

## אחרי נעילת IB — שלב C, 17:30–21:00

**בשלב C סוג-הפתיחה כבר לא מחליט** — בעץ כל חמשת ענפי-הפתיחה מצביעים לאותו `*phase_C`, שמפוצל על `day_type` ("Dalton: the IB and the extension do"). בפלייבוק שורות שלב C מותנות ב-`day_type` בלבד.

**משפט מפורש על מדרגות:** **מדרגות (שפלים עולים מעל ה-VAH של אותה שעה) שייכות אך ורק ל-`Trend_Normal` ו-`Trend_DD`.** הן אינן הכניסה של Normal, Variation, Neutral או Nontrend. ב-`entry_kind_map` המדרגה (`TREND_STEP`) ממופה ל-`PULLBACK`, ו-`PULLBACK` מופיע ברשימת שלב C **רק** בשורת-הטרנד. (הערה טכנית, כדי לא להטעות: במדיניות `counter_bias_only` העץ מקבל כל סוג **עם** הרמז גם בשורת Variation/הרחבה — כלומר `PULLBACK` עם ההרחבה לא ייחסם שם ב-`kind`; זו תוצאה של המדיניות, לא תזת-כניסה. התזה של מדרגות היא יום-מגמה.)

### Trend_Normal — יום-מגמה
**מה היום:** ה-IB נפרץ לצד אחד והמחיר ממשיך הרחק ממנו (לרוב ≥ 2× IB), ערך נבנה בכיוון, ואין חזרה ל-IB. סוחרים **עם** המגמה עד הסגירה.

| הטיה | סוגי-כניסה | סטופ | יעד | גודל | ראנר |
|---|---|---|---|---|---|
| `trend_direction` | `PULLBACK`, `BREAK` | `BEYOND_LEG_EXTREME` — מעבר לקצה הרגל | `S1_TABLE` | 1.0 | כן |

**העץ** (`phase_C → Trend_Normal|Trend_DD → trend_row`): עם הרמז → **TAKE** כל סוג; נגד → **SKIP** `bias` (אלא failed_extension → TAKE עם סולם `t1_r 1.5 / t2_r 2.5`); אין רמז → `PULLBACK|BREAK` TAKE (אותו סולם R, S7/T-494); אחר → SKIP `kind`. תואם.

### Trend_DD — מגמה בפיזור-כפול
**מה היום:** שני אזורי-ערך (פיזורים) מופרדים ברצועת single-prints; הפיזור השני נבנה אחרי פריצה. הגבול בין הפיזורים הוא הרפרנס — אין חזרה דרכו.

אותה שורה בדיוק כמו Trend_Normal, בפלייבוק ובעץ (`Trend_Normal|Trend_DD` = ענף אחד). מדרגות שייכות גם כאן.

### Variation — וריאציה (Normal-Variation של דלטון)
**מה היום:** IB בינוני, הרחבה **לצד אחד** בלבד, כ-1–2× IB; ההרחבה מחזיקה אבל אין "מגמה עד הסגירה".

### Normal_Variation
**מה היום:** אותה תבנית בתווית-המערכת השנייה; בפלייבוק ובעץ `Variation|Normal_Variation` הם ענף אחד.

| הטיה | סוגי-כניסה | סטופ | יעד | גודל | ראנר |
|---|---|---|---|---|---|
| `extension_direction_once_then_BOTH` | `BREAK`, `VALUE_RETURN` | `BEYOND_LEG_EXTREME` | `POC` | 1.0 | לא |

**העץ** (`variation_row`): תבנית `VAR_CONT` → נגד הרמז SKIP, אחרת **TAKE** (סוגים/מיקום מדולגים); כל תבנית אחרת → עם הרמז TAKE כל סוג; נגד → SKIP (אלא failed_extension); אין רמז → `BREAK|VALUE_RETURN` TAKE (סולם 1.5R/2.5R), אחר → SKIP `kind`. תואם ברשימה.
**הערת-קוד:** החלק "`once_then_BOTH`" (כניסה אחת עם ההרחבה ואז דו-כיווני) **אינו ממומש** — `_resolve_bias` (שורה 97) מחזיר `direction_hint or "BOTH"` לכל `extension_direction*`. ההטיה נשארת כיוונית כל עוד יש רמז.

### Normal — יום נורמלי
**מה היום:** IB רחב שמכיל את היום; המחיר מתנדנד בין הקצוות וחוזר למרכז. רספונסיבי בלבד: מוכרים VAH, קונים VAL, יעד — האמצע.

| הטיה | סוגי-כניסה | סטופ | יעד | גודל | ראנר |
|---|---|---|---|---|---|
| `BOTH` | `EDGE_FADE`, `VALUE_RETURN` | `BEYOND_IB_EDGE` | `POC` | 1.0 | לא |

**העץ** (`phase_C → Normal → normal_by_structure`) — **שואל קודם מה המחיר עשה ל-IB** (`structure`), פסיקת-מייקל 25.09 19:05:
- `structure=none` → `responsive_normal`: LONG ב-`near_val|below_value` / SHORT ב-`near_vah|above_value` → **TAKE** `take_location` (סוגים מדולגים); `zone=unknown` → `EDGE_FADE|VALUE_RETURN` TAKE, אחר SKIP `kind`; אזור לא-נכון → `failed_extension` → TAKE (`take_failed_ext_responsive`, T-529), אחרת **SKIP** `location`.
- `structure=up|down` (ה-IB הורחב לצד אחד) → `extension_row`: עם ההרחבה → **TAKE** `take_with_extension` בכל סוג (מדלג על גייט `entry_location_quality`); נגד → SKIP (אלא failed_extension); אין רמז → `BREAK|VALUE_RETURN`.
- `structure=two_sided` → `responsive_neutral` (תבנית-Neutral, להלן).
- **לא תואם לפלייבוק** בענף `up|down` — ראה §איפה-לא-אותו-דבר.

### Neutral_Center — ניטרלי, סגירה במרכז
**מה היום:** ה-IB נפרץ **לשני** הצדדים (שתי ההרחבות נכשלו), הסגירה באמצע הטווח. דועכים את שני הקצוות ליעד המרכז.

### Neutral_Extreme — ניטרלי, סגירה בקצה
**מה היום:** אותה פריצה דו-צדדית, אבל בשלב מאוחר צד אחד מנצח והסגירה בקצה. בשלב C עדיין מטופל כניטרלי; בשלב D (להלן) הוא מקבל יחס של מגמה-מאוחרת.

| הטיה | סוגי-כניסה | סטופ | יעד | גודל | ראנר |
|---|---|---|---|---|---|
| `BOTH` | `EDGE_FADE` בלבד | `BEYOND_IB_EDGE` | `CENTER` | 1.0 | לא |

**העץ** (`phase_C → Neutral_Center|Neutral_Extreme → responsive_neutral`): כלל-המיקום קודם — בקצה הנכון **TAKE** `take_location` (סוגים מדולגים); `zone=unknown` → `EDGE_FADE` בלבד TAKE; אזור לא-נכון → failed_extension TAKE, אחרת **SKIP** `location`. תואם ברשימה כשאין VA; כשיש VA ובקצה — העץ מרחיב מעבר ל-`EDGE_FADE` (ראה §איפה-לא-אותו-דבר, פריט 5).

### Nontrend — ללא-מגמה
**מה היום:** IB צר, אין הרחבה, נפח דל — "יום של לפני-אירוע". אין כניסות.

### Nonconviction — ללא-שכנוע
**מה היום:** אין מבנה ברור, המערכת לא מצליחה לסווג. אין כניסות.

| הטיה | סוגי-כניסה | סטופ | יעד | גודל |
|---|---|---|---|---|
| `NONE` | **אין** | — | — | 0 |

**העץ:** `Nontrend|Nonconviction → skip_stand_down` — **SKIP** לכל סוג. תואם. גם `FORMING`/לא-ידוע בשלב C → SKIP `stand_down` (פלייבוק: ברירת-מחדל `NONE`). תואם.

---

## שלב D 21:00–23:00

**`phase_d: manage_only`** (פלייבוק שורה 21) — אבל שורות שלב D בפלייבוק עצמו **כבר פותחות** כניסות חדשות לימי-מגמה (פסיקת-מייקל 17.09 14:05, "לפתוח שלב D לימי-מגמה"). הערת-הכותרת בקובץ ("Phase D: 21:00+ (management only, no new entries)") מיושנת ביחס לשורות.

| סוג-יום | פלייבוק (שורות D) | העץ (`phase_D`) |
|---|---|---|
| `Trend_Normal`, `Trend_DD` | **כניסה חדשה מותרת** — `trend_direction`, `PULLBACK`/`BREAK`, סטופ `BEYOND_LEG_EXTREME`, יעד `S1_TABLE`, 1.0, **בלי ראנר** | `trend_row` — עם הרמז TAKE כל סוג; נגד SKIP; אין רמז → `PULLBACK|BREAK` |
| `Neutral_Extreme` | **כניסה חדשה מותרת** — `extension_direction`, `PULLBACK`/`BREAK`, אותם סטופ/יעד, בלי ראנר | `trend_row` (אותו ענף כמו טרנד; הרמז מגיע מ-dir_hint override בגייטוויי לפי הערת-הקובץ) |
| `Variation`, `Normal_Variation` | **ניהול בלבד** (ברירת-מחדל `NONE`) | **TAKE עם ההרחבה בלבד** (`d_with_extension`, S1/T-494, פסיקת 27.09); נגד/אין רמז → SKIP `stand_down` |
| `Normal` + `structure=up\|down` | **ניהול בלבד** | **TAKE עם ההרחבה** (`d_with_extension`) |
| `Normal` + `structure=none/two_sided` | ניהול בלבד | SKIP `stand_down` |
| `Neutral_Center` | ניהול בלבד | SKIP `stand_down` |
| `Nontrend`, `Nonconviction`, `FORMING` | ניהול בלבד | SKIP `stand_down` |

**קאט-אוף 22:00 — דלוק בגרסה 3.4.0.** שורש העץ (`root`) הוא פיצול `hour`: ענף `">21"` → **SKIP `time_cutoff`** לכל כניסה חדשה, בכל סוג-יום ובכל סוג-פתיחה, משעה 22:00 IL (פסיקת-מייקל 06.10 "מאשר", אופציה א: 20:00 → 22:00). ההערה הבלוקית מעל `root` עדיין אומרת "no NEW entries from 20:00 IL" (05.10) — **הטקסט מיושן, העלה החי הוא 22:00** (`">21"` + שורת-הגרסה). עסקאות פתוחות ממשיכות להתנהל. בנוסף, הערת-העלה `d_with_extension` מזכירה גייט `eod_entry_cutoff` ב-22:15 שמחוץ לעץ — לא אומת כאן.

**בפועל, חלון-הכניסה של שלב D הוא 21:00–22:00** (לא עד 23:00 כפי ש-`end_il` של הפלייבוק אומר), ורק: Trend_Normal · Trend_DD · Neutral_Extreme (עם הרמז) · Variation / Normal_Variation / Normal-מורחב (עם ההרחבה).

---

## איפה העץ והפלייבוק לא אותו דבר

כולן תוספות שנפסקו אחרי 09.09 ונכתבו לעץ בלבד; `dalton_playbook.yaml` לא עודכן בעקבותיהן. ההבדל אמיתי כי בהטיה `BOTH` המדיניות `counter_bias_only` לא עוזרת — הרשימה היא שחוסמת.

1. **פתיחת-מכרז, שלב B, `REVERSAL`.** פלייבוק: `EDGE_FADE` בלבד. עץ: `REVERSAL` → TAKE. נתיב: `root → hour:* → root_full → OPEN_AUCTION_IN|OPEN_AUCTION_OUT → B → day_type:* → kinds_auction_B → REVERSAL` (id `auction_B_reversal`, S5/T-494, פסיקה 27.09).
2. **פתיחת-מכרז, שלב B, תווית כבר Trend, `BREAK`.** פלייבוק: `EDGE_FADE` בלבד. עץ: TAKE. נתיב: `… → OPEN_AUCTION_IN|OPEN_AUCTION_OUT → B → Trend_Normal|Trend_DD → kind:BREAK` (id `auction_B_trend_break`, T-484, פסיקה 25.09).
3. **Normal שה-IB שלו הורחב לצד אחד, שלב C.** פלייבוק: רספונסיבי דו-כיווני (`EDGE_FADE`/`VALUE_RETURN`, יעד POC). עץ: תבנית-וריאציה — **עם ההרחבה כל סוג** (ומדלג על גייט `entry_location_quality`). נתיב: `… → C → phase_C → Normal → normal_by_structure → up|down → extension_row → with → take_with_extension` (פסיקה 25.09 19:05). וגם `two_sided` → תבנית-Neutral (`responsive_neutral`) במקום תבנית-Normal.
4. **שלב D על Variation / Normal_Variation / Normal-מורחב.** פלייבוק: ניהול בלבד. עץ: TAKE עם ההרחבה. נתיב: `… → D → phase_D → Variation|Normal_Variation → d_with_extension → with` ו-`… → phase_D → Normal → structure:up|down → d_with_extension → with` (S1/T-494, פסיקה 27.09).
5. **כלל-המיקום T-319b והפטור failed_extension** — קיימים רק בעץ. השלכה: בשורות Normal/Neutral עם VA ידוע, כניסה **בקצה הנכון** מתקבלת **בכל סוג** (`take_location`: "kinds skipped") — רחב מרשימת הפלייבוק (`EDGE_FADE`[+`VALUE_RETURN`]); וכניסה **מחוץ לקצה** נחסמת ב-`location` גם אם היא `EDGE_FADE` לפי הרשימה. נתיב: `… → phase_C → Normal → normal_by_structure → * → responsive_normal → LONG → zone`.
6. **קאט-אוף 22:00** — בעץ בלבד (`root → hour:">21" → time_cutoff`). הפלייבוק נותן לשלב D `end_il: "23:00"` בלי חיתוך.
7. **קוד מול פלייבוק (לא עץ):** `extension_direction_once_then_BOTH` ממומש כ-`direction_hint or BOTH` — ה"פעם-אחת-ואז-דו-כיווני" לא קיים ב-`_resolve_bias`.

לא נמצאה סתירה בשלב A, בפתיחות OPEN_DRIVE / OPEN_TEST_DRIVE / OPEN_REJECTION_REVERSE בשלב B, בשורות Trend ו-Variation בשלב C, וב-Nontrend/Nonconviction.

---
*בלי דולרים, בלי עסקאות חדשות. מספרי-`measured:` של העץ לא הועתקו בכוונה.*
