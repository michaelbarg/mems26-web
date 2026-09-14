# פריט 3א מתוך 8 — `edge_fade_targets` חייב להיות **סמכות**, לא שורת-לוג (T-354)

**פריט 3 (`37326a55`) לא התקבל.** הקוד נכון ברעיון, אבל בפועל **אף לא אחת מ-4 ההפעלות שינתה את
השרשרת שנשלחת לביצוע** — והוא כן שינה משהו אחד: הוא **הסיר חסימת-rr** משלושה מסלולים והשאיר להם את
השרשרת הישנה. זו בדיוק התבנית שאסורה אצלנו: *הכרזה בלוג אינה אכיפה*.

## הראיות הגולמיות (הרנס ×5 + `--restart-at 18:29`, HEAD `37326a55`, מול בסיס `efaaf833`)

ארבע הפעלות של הבלוק — ובכל אחת השרשרת הסופית ב-JSON **זהה לבסיס**, כלומר נדרסה:

```
2026-09-09 17:34:58 EDGE_FADE_TARGETS: ZLR LONG entry=7655.00 stop=7644.00 T1=7662.25 T2=7663.75 T3=None  zone=near_val
   → route סופי:  BASE stop=7640.25 t1=7677.125 t2=7684.5   |  HEAD stop=7640.25 t1=7677.125 t2=7684.5
2026-09-10 17:50:03 EDGE_FADE_TARGETS: REACTIVE_SHORT entry=7607.50 stop=7620.25 T1=7589.0 T2=7585.5 T3=None
   → route סופי:  BASE stop=7624.0  t1=7585.5   t2=7574.5   |  HEAD stop=7624.0  t1=7585.5   t2=7574.5
2026-09-10 19:15:03 EDGE_FADE_TARGETS: VA_FADE_LONG  entry=7600.25 stop=7585.25 T1=7618.0 T2=7620.0 T3=None
   → route סופי:  BASE stop=7596.0  t1=7604.5   t2=7608.38  |  HEAD stop=7596.0  t1=7604.5   t2=7608.38
2026-09-11 17:25:03 EDGE_FADE_TARGETS: VA_FADE_SHORT entry=7675.50 stop=7682.25 T1=7671.0 T2=7663.25 T3=7659.75
   → route סופי:  BASE stop=7680.25 t1=7670.75 t2=7666.0    |  HEAD stop=7680.25 t1=7670.75 t2=7666.0
```

מי דורס: `[ECON-DIFF] … | authority: {...}` (‏`DAYTYPE_TARGETS_STRUCTURAL`), `TARGET_ZONES_V1`,
`#1191 monotonic guard`. `STRUCT_TARGETS_WIN` אמנם חוסן — אבל הוא לא היה הדורס.

**מה כן השתנה — וזה החמור:** `stop_is_structural=True` פטר את `StopResolver`+`STEP_SCALED_LADDER`,
ולכן שלושה מסלולים עברו מ-`rr_entry_gate` ל-**מאושר**, עם השרשרת הישנה:

```
09-09 17:34:58 ZLR            rr_entry_gate → None
09-10 17:50:03 REACTIVE_SHORT rr_entry_gate → None
09-10 19:15:03 VA_FADE_LONG   rr_entry_gate → None
```

ועל 10.09 17:50 זה הגיע עד שכבת-הפקודה והוליד **שגיאה חדשה** (בסיס 0 → HEAD 1):

```
2026-09-10 17:50:03 ERROR sierra_command [SierraCmd] T-335 LADDER INVALID:
  SHORT targets [7589.0, 7569.25, 7585.5] are not monotonic in trade direction — PLACE blocked for trade FWD-live-6
```

בבסיס אותו מסלול נחסם נקי ב-rr; ב-HEAD הוא ניסה **PLACE חי** ורק T-335 עצר אותו. ‏10.09 הוא יום עם
**אפס כתיבות** — אסור שייצא ממנו ניסיון-כתיבה.

**חריגת-תחום:** 11.09 17:25 הוא `dp_day_type=Trend_Normal` — סעיף 3 בהזמנה המקורית אמר
"שורות Variation/Trend ללא שינוי". הבלוק הופעל שם כי השער הוא בדיקת-zone גולמית ולא
`_dp_location_checked`.

**תיקון-עצמי שלי (cowork), לפרוטוקול:** הגולדן שכתבתי בהזמנה המקורית היה **שגוי** — 11.09 18:55
`REACTIVE_SHORT 7673.25` יושב על שורת **Variation** (`dp_intent.reason = "phase=C cond=day_type in
[Variation, Normal_Variation]"`), ולכן לפי סעיף 3 של אותה הזמנה עצמה הוא **לא אמור** לקבל יעדי
edge-fade. ההסבר שלך על רזולוציית-TPO נכון עובדתית אבל לא זה השורש. הגולדן מוחלף להלן.

---

## מה לבנות (פריט 3א — בדיוק זה)

**0. דגל-כיבוי חדש `EDGE_FADE_TARGETS_V1` — ברירת-מחדל OFF בקוד.**
כל הבלוק (כולל `stop_is_structural` שהוא מדליק) רץ רק כש-`os.getenv("EDGE_FADE_TARGETS_V1","0")`
דלוק. **לא להוסיף אותו ל-`.env`.** להוסיף שורה ל-`config/RULED_FLAGS.yaml` עם
`expected: '0'` + `measured: UNMEASURED (ריפליי 3א ממתין)` ומצביע להזמנה הזו. ככה הפתיחה היום רצה
בלי הפיצ'ר, ואני מדליק אחרי מספרי-הריפליי. זה **לא** שאלה — זה חלק מהפריט.

**1. השער: `_dp_location_checked`, לא בדיקת-zone עצמאית.**
- לאתחל `_dp_location_checked = False` ב**ראש** `_route_setup_inner` (ליד `_dalton_intent = None`,
  ~שורה 1060) כדי שהשם קיים גם כשבלוק-דלתון לא רץ.
- הבלוק ב-3116 מותנה ב-`_dp_location_checked is True` (כלומר: `day_type ∈ Normal/Neutral_*`
  **וגם** כלל-המיקום אישר). בדיקת-ה-zone הפנימית נשארת רק כדי לבחור מאיזה קצה נכנסים.
- אימות: 11.09 17:25 (`Trend_Normal`) **לא** מדפיס `EDGE_FADE_TARGETS`.

**2. הסטופ: עוגן-לפני-קצה.**
- אם ל-setup יש `structural_anchor` (עליון או ב-metadata) — **הוא** הסטופ: `anchor ± 0.25`.
  (זה מה שההזמנה המקורית אמרה; המימוש בדק `stop_is_structural` שהוא שדה אחר לגמרי, ולכן פספס את
  כל setups של S2 שנושאים `structural_anchor` בלי הדגל.)
- אחרת, קצה-הערך: SHORT — `edge = VAH` אם `entry <= VAH + tol`, אחרת `max(VAH, IB_high)`;
  LONG — מראה. `tol = location_gate._tol(ib_width)`. סטופ = `edge ± 0.25`.
- הגודל נגזר (`n<3 ⇒ אין כניסה`), `runner=False`. `RISK_*` לא נגעים.

**3. סמכות: השרשרת של edge-fade היא הסופית.**
לעטוף ב-`(not _edge_fade)` — בדיוק כמו ש-`STRUCT_TARGETS_WIN` כבר עטוף — את:
`DAYTYPE_TARGETS_STRUCTURAL` (~3439, כולל בלוק "#68 structural targets") ·
`load_pattern_t1_points` (~3666) · `TARGET_ZONES_V1` (~3711) ·
`TARGET_STRUCTURE_CLAMP_V1` (~3936) · `TARGET_REALISM_V1` (~3967).
**נשארים פעילים:** רישום `ECON-DIFF` (השוואה בלבד) · שומר-הקריסה של הסולם · T-335 · שער-rr.

**4. אסור למכור פטור-סולם בלי שרשרת.** אם משום-מה השרשרת לא נכתבה (כל T ריק) —
**לא** להדליק `stop_is_structural` ולא לגעת בסטופ. פטור בלי שרשרת = בדיוק הבאג של 10.09 17:50.

---

## golden (שורות גולמיות בדיווח — בלי אלה הפריט לא נבדק)

**ג1 · השרשרת שורדת עד הסוף.** לכל מסלול שמדפיס `EDGE_FADE_TARGETS` — הערכים ב-`routes[]` של
ה-JSON (`stop/t1/t2/t3`) **זהים** לשורת-הלוג. להדביק את שתי השורות זו מול זו לכל הפעלה.
מסלול-הייחוס: 10.09 `17:50:03 REACTIVE_SHORT 7607.5` (Normal, VAH 7609.25, POC 7602.75, IB 7620/7585.5).

**ג2 · אפס שגיאות חדשות.** `grep -c "T-335 LADDER INVALID"` = **0** בכל 6 הריצות (בסיס 0).

**ג3 · אפס שינוי בכתיבות** בכל 5 הסשנים + restart: 08-03 `INITIATIVE_LONG 7587.5` ·
08-04 `REACTIVE_LONG 7690.75` · 09-09 `CEILING_FLIP_LONG 7641.25` · **10.09 אפס** ·
11.09 `REACTIVE_SHORT 7673.25` · restart `CEILING_FLIP_SHORT 7671.25`.

**ג4 · מעברי-חסימה מדווחים במפורש.** לרשום טבלה של כל מסלול ש-`blocked_by` שלו השתנה מול הבסיס
(‏`rr_entry_gate → None` וכיו"ב) עם השרשרת המלאה שלו. **לא לשפוט אותם — רק לדווח.** אני פוסק.

**ג5 · דגל כבוי = אפס דלתא.** ריצה אחת נוספת **בלי** `EDGE_FADE_TARGETS_V1` חייבת להיות
זהה-לחלוטין לבסיס `efaaf833` (אפס שורות `EDGE_FADE_TARGETS`, אפס מעבר-חסימה).

**ג6** · `test_edge_fade_targets.py` מורחב: המבחן הקיים בודק פונקציה משוכפלת בקובץ-המבחן ולכן
יעבור גם אם השער מנותק. להוסיף מבחן-מוטציה שקורא ל-`inspect.getsource(_route_setup_inner)` ומוודא
ש-`_dp_location_checked` מופיע בתנאי-הבלוק, ושכל חמשת הדורסים מסעיף 3 עטופים ב-`_edge_fade`.

## דיווח
קומיט אחד · `TASK_LOG` (T-354) + `STATUS_BOARD` באותו קומיט · LOG חתום עם ג1–ג6 גולמיים ·
ואז **"סיים פריט 3א"** ולעצור. **אין ריסטארט** (המתוזמן 15:45), אין נגיעה ב-`.env`.
