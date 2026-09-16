# GAP ANALYSIS 2026-09-17 — ⛔ NOT-DONE (חסום על פגם-נתונים ב-`scripts/gap_analysis.py`)

**cowork-dev · 2026-09-16 לילה · תור-הלילה, חלק ב'**

> **הדוח הזה אינו מכיל את הניתוח שהוזמן.** ארבעת החלקים (טבלת-day_type · 20 התנועות
> שהוחמצו · ענפים-מועמדים · תשובה-במספר ל-`TREND_STEP`/`RE_ACCEPTANCE`) **לא חושבו**,
> כי הסקריפט קורס על כל סשן שיש בו עסקאות. לפי כלל-הכנות של הריפו (CLAUDE.md Rule 1)
> — שדה שאי-אפשר לחשב מדווח כ-missing ולא מסונתז. **אין כאן שום מספר משוער.**

**מה כן נעשה:** אבחון מלא עם `file:line` ויעדי-תיקון מאומתים מול ה-DB, כדי ש-cc יוכל
לתקן בבוקר בלי לחזור על האבחון. **לא תיקנתי את קוד cc בעצמי** — לפי הוראת-ההזמנה.

---

## ב1 · smoke — ❌ נכשל

```
$ set -a; . ./.env; set +a
$ python3 scripts/gap_analysis.py --dry --session 2026-09-15 --verbose
rc=1   Traceback=1

[dry run] Analyzing session 2026-09-15...
Traceback (most recent call last):
  File "/Users/michael/Downloads/mems26_web_git/scripts/gap_analysis.py", line 968, in <module>
    main()
  File "/Users/michael/Downloads/mems26_web_git/scripts/gap_analysis.py", line 911, in main
    data = analyze_session(session, verbose=True)
  File "/Users/michael/Downloads/mems26_web_git/scripts/gap_analysis.py", line 609, in analyze_session
    day_type_final = (first_cc.get("day_type_final")
AttributeError: 'list' object has no attribute 'get'
```

**זו אינה תקלת-סביבה ואינה מלכודת-T-399.** `.env` נטען (‏`set -a` + env_loader פנימי).

### הכשל שיטתי — 5 מתוך 5 תאריכים, על פני כל 4 החודשים

```
$ for d in 2026-06-10 2026-07-15 2026-08-12 2026-09-11; do python3 scripts/gap_analysis.py --dry --session $d 2>&1 | tail -2; done
2026-06-10 => AttributeError: 'list' object has no attribute 'get'
2026-07-15 => AttributeError: 'list' object has no attribute 'get'
2026-08-12 => AttributeError: 'list' object has no attribute 'get'
2026-09-11 => AttributeError: 'list' object has no attribute 'get'
```

---

## השורש — `cross_context` הוא **רשימה**, והסקריפט מניח **מילון**

```
$ psql -c "SELECT jsonb_typeof(cross_context) AS cc_type, count(*) FROM v9_trades GROUP BY 1;"
 cc_type | count
---------+-------
 array   |  1627
```

**כל 1,627 העסקאות ב-DB — ללא יוצא מן הכלל — נושאות `cross_context` מסוג `array`.**
המבנה האמיתי:

```
cross_context = [
  { "classification", "confidence", "trigger", "metadata", "systems" },   # elem 0 = תמונת-הכניסה
  { "event", "from", "to", "target", "reason" }                            # elem 1+ = אירועים
]
cross_context[0]["systems"] = { day_type_machine · five_min_system · footprint_system
                              · killzone_system · tpo_system · woodies_system }
```

### היקף-הפגם — לא שורה אחת, אלא שכבת-הגישה-לנתונים כולה

| file:line | הקוד | מה קורה בפועל |
|---|---|---|
| `gap_analysis.py:608-611` | `trades[0].get("cross_context",{})` ואז `.get("day_type_final")` | **קורס** — `AttributeError` |
| `gap_analysis.py:487-499` | `cc.get("blocked_by")` | **תמיד `None`** — המפתח לא קיים ברמה הזו |
| `gap_analysis.py:555-563` | `cc.get("day_type_final"/"day_type_confidence"/"opening_type"/"zone"/"extension"/"bars_since_extreme")` | **כל ששת השדות תמיד `None`** |
| `gap_analysis.py:287-294` | הלואדר ממיר `str`→json ו-`None`→`{}` | **לא מטפל במקרה-הרשימה** — ולכן הטיפוס האמיתי עובר הלאה |

**זה הממצא המסוכן:** גם אילו תיקנתי רק את הקריסה בשורה 609, כל שאר השדות היו חוזרים
`None` **בשקט**, והדוח היה נראה תקין בעוד הוא מדווח `NO_SETUP` על הכול. זו בדיוק
אנטי-התבנית של Rule 1 בכיוון ההפוך — כשל שקט שנראה כמו תוצאה.

---

## שני ממצאים נלווים

### 1 · 24 הטסטים הירוקים אינם רשת-ביטחון לנתיב הזה

```
$ grep -n "cross_context" tests/v9/regression/test_gap_analysis.py
183:            "cross_context": {},
200:            "cross_context": {},
216:            "cross_context": {},
233:            "cross_context": {},
```

הטסטים מזריקים **מילון ריק בלבד** — הצורה שקורסת (רשימה) לא נבדקת באף טסט.
לכן `24/24 passed` אמיתי, ואינו מעיד דבר על נתונים אמיתיים. הטסטים מאמתים צורת-נתונים
**שאינה קיימת ב-DB**. זה גם מסביר איך הפריט נמסר כ"עובר" בלי שהורץ פעם אחת על DB.

### 2 · `classify_replay` לא חובר — והוא מפתח-הקיבוץ הראשי של הדוח

ההזמנה קבעה במפורש: `day_type_final` — **מ-`classify_replay`** (המנוע המאומת לפי
`docs/SOURCE_OF_TRUTH.md`). בפועל:

```
$ grep -n "classify_replay" scripts/gap_analysis.py
(אין תוצאות)
```

cc קרא במקום זה מפתח `cross_context.day_type_final` **שמעולם לא היה קיים**. וזה לא
פרט טכני: `day_type` הוא מפתח-הקיבוץ של חלק (1), של חלק (3), ושל התשובה-במספר בחלק (4).
יתרה מזו — גם הנתיב ה**נכון** ב-`cross_context` לא היה מספיק, כי בכניסות מוקדמות הוא עדיין לא התייצב:

```
cross_context[0].systems.day_type_machine =
  {"stage":"A2","day_type":"UNKNOWN","confidence":0.0,"lock_state":"PENDING","opening_type":"UNKNOWN"}
```

כלומר **דרישת ההזמנה ל-`classify_replay` הייתה נכונה מלכתחילה**, וקיצור-הדרך הוא שנכשל.

---

## יעדי-התיקון — מאומתים מול ה-DB (ל-cc, בוקר 17.09)

**יש כבר אדפטר נכון בריפו** — `scripts/replay_s7_acceptance.py:55,75` משתמש ב-
`_systems_blob_at_entry(cross_ctx)`. לפי CLAUDE.md ("audit existing surfaces before
building") יש לאמץ אותו ולא לכתוב שלישי.

| שדה | הנתיב הנכון | סטטוס-אימות |
|---|---|---|
| `blocked_by` | `cross_context[0]["metadata"]["blocked_by"]` | ✅ מאומת מאוכלס (ראה מפקד למטה) |
| `day_type_final` | **`classify_replay`** — לא מ-`cross_context` | ✅ דרישת-ההזמנה המקורית |
| `opening_type` | `…[0].systems.day_type_machine.opening_type` (או `tpo_system`) | ✅ קיים |
| `zone` | **לחשב** ב-`location_gate.zone_of(price, vah, val, ib_width)` | ✅ vah/val ב-`tpo_system` |
| `extension` | **לחשב** מול `tpo_system.ib_high/ib_low` + `session_high/low` | ✅ כל הקלטים קיימים |
| `shadow_only` / `shadow_blocked` | `…[0]["metadata"]` | ✅ קיים — רלוונטי ישירות לחלק (4) |

⚠️ `woodies_system.decision_tree` הוא **`{}` ריק** — הנתיב ש**ההזמנה עצמה** ניחשה
(`woodies_system.last_route.blocked_by`) **אינו קיים**. הנתיב הנכון הוא `metadata.blocked_by`.

**מפקד שמוכיח שהיעד אמיתי ומאוכלס** (‏635 מתוך 1,585 עם ערך):

```
$ psql -c "SELECT COALESCE(cross_context->0->'metadata'->>'blocked_by','(null)'), count(*)
           FROM v9_trades WHERE entry_ts >= '2026-06-01' AND entry_ts < '2026-09-17'
           GROUP BY 1 ORDER BY 2 DESC LIMIT 15;"
 (null)                   | 950
 dalton_intent:stand_down | 143
 awaiting_release         | 128
 dalton_intent:location   |  72
 dalton_intent:kind       |  64
 dalton_intent:bias       |  49
 rr_entry_gate            |  38
 eod_entry_cutoff         |  37
 variation_mid_value      |  28
 entry_location_quality   |  14
 extreme_chase_guard      |  12
 direction_compass        |  11
 location_gate            |   9
 daytype_playbook         |   9
 cold_start_guard         |   7
```

---

## תיקון-מספר: **75 סשנים, לא 85**

```
$ psql -c "SELECT count(DISTINCT (ts AT TIME ZONE 'Asia/Jerusalem')::date)
           FROM v9_bars_5min_woodies
           WHERE ts >= '2026-06-01' AND ts < '2026-09-17'
             AND (ts AT TIME ZONE 'Asia/Jerusalem')::time >= '16:30'
             AND (ts AT TIME ZONE 'Asia/Jerusalem')::time <  '23:00';"
 rth_sessions = 75

$ psql -c "SELECT count(DISTINCT (entry_ts AT TIME ZONE 'Asia/Jerusalem')::date), count(*)
           FROM v9_trades WHERE entry_ts >= '2026-06-01' AND entry_ts < '2026-09-17';"
 sessions_with_trades = 66   trades = 1585   (2026-06-05 .. 2026-09-16)
```

**66 מתוך 75 הסשנים (88%) נופלים על הקריסה.** ה-9 הנותרים הם סשנים ללא עסקאות —
הם היו "עוברים", אבל בלי `day_type` ובלי מעמד-תנועות, כלומר בלי תוכן. **סשנים שעובדו
בפועל: 0.** מספר-היעד "85" שבהזמנה שגוי; הנכון ל-01.06–16.09 הוא **75**.

---

## ארבעת החלקים שהוזמנו

1. **טבלה לפי `day_type_final`** — ⛔ לא חושבה.
2. **20 התנועות-הגדולות שהוחמצו** — ⛔ לא חושבה.
3. **ענפים-מועמדים (‏N ≥ 15)** — ⛔ לא חושבה.
4. **תשובה-במספר ל-`TREND_STEP` ול-`RE_ACCEPTANCE`** — ⛔ **לא ניתן לחשב.**

> **הסיבה, במפורש:** שתי הרגליים של השאלה חסומות. קיבוץ לפי ימי Trend/Normal דורש
> `day_type_final`, ו-`classify_replay` **לא חובר** (‏`grep` ריק). זיהוי "היה לה
> setup-צל" דורש את `metadata.shadow_only`/`shadow_blocked`, ושכבת-הקריאה
> **קורסת לפני שהיא מגיעה לשם**. כל מספר שהייתי נוקב כאן היה המצאה.
>
> **זו נקודת-ההחלטה של מייקל למחר-בבוקר, ולכן דווקא כאן אסור לנחש.** החלטה על ענף-עץ
> חדש שנשענת על מספר מנתיב-נתונים שנכתב בחיפזון בחצות — היא בדיוק סוג-הטעות
> שהדוקטרינה (`LEARNING_DOCTRINE_2026-09-09`: "התשובה להוראה היא מספר, לא קומיט")
> קיימת כדי למנוע. מספר שגוי כאן לא מבזבז זמן — הוא מזריע כלל-מסחר שגוי.

---

## למה לא תיקנתי בעצמי

1. **הזמנת-הלילה אוסרת זאת במפורש** — *"אל תתקן קוד של cc בעצמך — תעד עם `file:line`."*
2. **זה לא באג-שורה אלא שכבת-הגישה-לנתונים של T-389** — אדפטר + `classify_replay` +
   חישוב `zone` + חישוב `extension` + מיפוי `blocked_by`. זה בנייה-מחדש, לא תיקון.
3. **אין גולדן לאמת מולו** — 24 הטסטים מזריקים `{}` בלבד, ולכן אינם מגלים נסיגה בנתיב הזה.
   שכתוב בחצות בלי רשת = בדיוק "טענת-הצלחה" שהריפו אוסר (Rule 5).
4. **המספר מזין החלטת-מסחר של מייקל.** דוח-כן על עבודה חלקית שווה יותר מדוח מלא ושקרי.

## הצעד-הבא המומלץ (‏T-389, נשאר 🟠)

1. לאמץ את `_systems_blob_at_entry` מ-`scripts/replay_s7_acceptance.py` כאדפטר יחיד.
2. לחבר `classify_replay` ל-`day_type_final` — כפי שההזמנה דרשה מלכתחילה.
3. למפות `blocked_by` ל-`cross_context[0].metadata.blocked_by` (‏**לא** ל-`decision_tree`, שהוא `{}`).
4. לחשב `zone` ב-`location_gate.zone_of` ו-`extension` מול `tpo_system.ib_*` — לא לקרוא אותם.
5. **להוסיף טסט עם `cross_context` בצורת-רשימה אמיתית** (‏fixture מ-`v9_trades` אמיתי) —
   בלעדיו 24/24 יישאר ירוק-ושקרי.
6. להריץ `--dry --session 2026-09-15 --verbose` ורק אז את הריצה המלאה בנתחים חודשיים.
