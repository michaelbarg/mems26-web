# NIGHT REPAIR — 2026-09-09

**מבצע:** `cowork-dev` (MacBook, מכונת-המסחר) · **חלון:** 23:15:23 → 23:38:50 IL
**כל שעה בדוח הוזרקה ע"י `date`, לא הוקלדה.** כל טענה נושאת פקודה + פלט (Rule 5).
**הפוסט-מורטם המלא של שתי העסקאות:** `docs/reports/WHY_WE_LOST_2026-09-09.md`.

---

## 0 · TL;DR

| | |
|---|---|
| **למה הפסדנו** | שתי עסקאות-LONG **נגד-ההרחבה** ביום Variation-DOWN. נגד-ההרחבה = **−$715 על 19 עסקאות (32%)** מול **+$158.75 על 32 (59%)** עם-ההרחבה. הסטופ לא היה השורש. |
| **הסטופ המבני היה מציל?** | **לא את שתיהן.** מציל את `#1328` (−$40→**+$90**), מקטין את `#1343` (−$137.50→−$108.75). ‏`trade_economics` בהצבה שלו-עצמו היה **מחמיר את שתיהן**: −$390 מול −$177.50. |
| **הלייב האמיתי היום** | **−$177.50** (ברוקר), לא −$171.25. |
| **מה נשלח הלילה** | 2 קומיטים · 13 טסטים חדשים · guards 146→**159** · fire_drill **🟢 GO** |
| **מוכן ל-16:30?** | **כן.** אין חוסם טכני פתוח. |

---

## 1 · אימות עבודת cc (פלט גולמי, לא "✅ סומך")

```
$ python3 scripts/flag_guard.py                                        [23:25:04]
FLAG-GUARD: PASS — all 250 ruled flags match.
$ python3 scripts/task_log_guard.py
task_log_guard — 293 items, last committed 0.0 days ago
✅ the task log is current, structured, and the only one
$ bash scripts/guard_tests.sh                                          [23:26:25]
146 passed, 2 warnings in 4.34s
✅ GUARDS GREEN
$ git status --short   → 28, all untracked reports + cc's unlanded test
```

| הודעת-cc | נבדק בקוד | מסקנה |
|---|---|---|
| `18dbc554` P1.5 opening_type מהיצרן | `trading_gateway.py:1109-1125`, `_P15_MAP` קיים | ✅ |
| `46156890` P2 economics + 15 טסטים | `pytest test_trade_economics.py` ⇒ **15 passed**; הרצתי `economics()` וקיבלתי עוגנים אמיתיים (7635.25/7643.25), לא stub | ✅ |
| `493adced` T-285 VA_FADE מת | הקריאות הכל-סשן ב-`five_min_system.py:2410-2413` הן 3 בלבד; `VA_FADE` **אינו** ביניהן | ✅ מנגנון נכון |
| `493adced` "VA_FADE 0 fires" | 🔴 **מופרך** — ראה §4.3 | ⚠️ |
| טסט-הרפרודוקציה T-284 | הקובץ קיים אך **לא-committed** | הונחת הלילה |

### 1.1 · 🔴 מספר-הייחוס של הריפליי זז — ולא קומיט הזיז אותו

```
$ python3 scripts/replay_dalton_playbook.py                            [23:25:29]
Sessions: 40 | broker-priced trades: 108 | excluded: 29
Approved: 58 | Rejected: 50
Approved Σ$ (broker): $+430.00    Actual Σ$ (broker): $-491.25
Winners approved : 33/52 = 63%   (gate ≥75%)
Losers rejected  : 31/56 = 55%   (gate ≥60%)
n approved       : 58   (gate ≥40)
GATE: FAIL  [X/X/ok/ok]
```

הייחוס הצפוי היה `56A / +607.50 / 63% / 57% / n=56` על 106.

**מה הזיז — נבדק, לא הונח:**
```
$ git log --oneline 274a8013..HEAD -- scripts/replay_dalton_playbook.py \
    backend/v9/services/dalton_playbook.py config/dalton_playbook.yaml
(אין שורות)
$ grep -n "^import\|^from" scripts/replay_dalton_playbook.py
→ אינו מייבא trade_economics ⇒ 3259716e לא יכול להיות הגורם
```
⇒ **אף קומיט לא הזיז. הנתונים זזו:** שתי עסקאות-הלייב של היום נסגרו **אחרי** שה-cc קבע
את הייחוס (19:07 ו-21:08), שתיהן אושרו ע"י הפלייבוק, שתיהן הפסידו.

חמש סטטיסטיקות מתיישבות עם ההשערה הזו, בלי פרמטר חופשי אחד:
`106→108` (+2) · `56→58` (+2) · `+607.50→+430.00` (**Δ=−177.50 = בדיוק הפסד-הברוקר של היום**) ·
מפסידים-שנדחו `31/54=57%→31/56=55%` (2 מפסידים חדשים, 0 נדחו) · מנצחים `33/52` **ללא שינוי**
(היום לא הוסיף מנצחים).

> **‏🔴 ל-לוח-הבוקר: הפלייבוק חי (`DALTON_PLAYBOOK_V1=1` מ-16:55) והוא נכשל בשער-הקבלה של
> עצמו** — מנצחים 63% מול סף 75%, מפסידים 55% מול סף 60%.

---

## 2 · מה נשלח הלילה

### 2.1 · `98d94024` — T-284 sibling + T-285 placement guard

**ממצא א'.** ‏`post_volume_profile` נשא את **אותה** תבנית שהפילה את הבקאנד פעמיים היום
(12:14, 16:31): `Depends(get_db)` + `db.query(V9Bar5Min)`, שה-SELECT הראשון שלו פותח
טרנזקציה ומקבע את חיבור-המאגר `idle in transaction` לכל אורך הבקשה, בעוד `safe_execute`
בשתי הלולאות שואל חיבור **שני** מאותו מאגר 5+10.

סריקת-המחלקה מצאה גם ש-`post_woodies_5min` מחזיק סשן **מת** — 280 שורות, אפס שימושים ב-`db` —
על **נתיב-הקליטה החם ביותר במערכת** (`v9_bars_5min_woodies` הוא מקור-האמת החי).

**תיקון.** ‏`read_all` על מנוע-הקריאה ה-AUTOCOMMIT, ממומש מראש; התלות המתה הוסרה.
‏`post_footprint`/`post_tick_reversal` ב-allowlist **עם נימוק** — הם `db.add`+`db.commit`
ולעולם לא `safe_execute`, כלומר משחררים במקום לקבע. תבנית אחרת, בטוחה.

**ראיה — הטסט הורץ נגד הקוד הישן קודם:**
```
$ git worktree add /tmp/t284_old HEAD   (‏c2f9342e, לפני התיקון)         [23:28:06]
AttributeError: 'Depends' object has no attribute 'query'   bars.py:871
FAILED test_volume_profile_handler_signature_takes_no_orm_session
FAILED test_no_bridge_ingest_handler_depends_on_an_orm_session
FAILED test_fixed_volume_profile_handler_holds_no_pool_connection
3 failed, 3 passed
$ (קוד חדש)                                                             [23:28:17]
6 passed   —   pool.checkedout()==0 אחרי 20 קריאות רצופות
```
נוסף **שומר-מחלקה** שמונה כל `post_` ב-`bars.py`, כדי שה-sibling הבא לא יוכל להתחבא.

**ממצא ב'.** ‏`test_detector_placement.py` אוסר לקנן גלאי תחת `FIRST_HOUR_TACTICAL`, אבל
`ALL_SESSION_DETECTORS` הכיל **שניים בלבד** — ולכן היה ירוק בזמן ש-`VA_FADE` ישב בתוך
בלוק-השעה-הראשונה. שומר שמכסה מופע אחד אינו שומר מפני המחלקה.

**תיקון.** ‏`VA_FADE` חולץ ל-`_maybe_va_fade()` כל-סשן ליד `_maybe_dalton_edge`, תוך שימור
מגן-הבר-הנבנה (`buffer[:-1]`, T-252) ופתרון-סוג-היום-החי. המפה הורחבה + נוסף טסט-שלמות:
‏`_maybe_*()` חדש בבלוק שאין לו שורה במפה — נכשל.

> **אפס שינוי-התנהגות-מסחר.** ‏`VA_FADE_V1=shadow`, ו-`build_va_fade_setup`
> (`va_fade.py:170`) כופה `shadow_only=True` עם נעילת-רגרסיה — הזזת **אתר-הקריאה** אינה
> יכולה לנתב הזמנה חיה. היא רק מאפשרת למדוד אותו לראשונה. לייב = פסיקה נפרדת.

### 2.2 · `1bb6879b` — שפיות-IB בשכבת ה-TPO (מחלקת G-71)

```
2026-09-09 16:54:52 [TPO] Hydrated IB from DB: H=7717.75 L=7680.00 locked=True W=37.75
```
זה ה-IB של **אתמול** — נמדד ולא הונח: הקיצונים האמיתיים של 12 ברי-ה-RTH הראשונים ב-08.09 הם
בדיוק `7680.00/7717.75`, ושל 09.09 הם `7644.25/7663.75`. הריסטארט נחת בזמן שהשורה של היום
עוד נשאה את ערכי-אתמול עם `ib_locked=1`, ו-`locked` מקצר כל חישוב-מחדש.

**‏⚠️ תיקון-היקף שאני רושם נגד עצמי:** ההנחיה טענה ש"כל החלטה תלוית-IB היום רצה מול טווח
שהשוק לא נסחר בו". **הלוג אינו תומך בזה** — `StopResolver` מדווח `35% of IB 19.50`, הרוחב
**הנכון**, כבר מ-17:35:55, ושתי עסקאות-הלייב השתמשו ב-19.50. חלון-השיבוש היה
`16:54:52 → ~17:35`, לא הסשן.

**תיקון.** ‏`hydrate()` משווה כעת מול 12 ברי-ה-RTH של היום בשני הגלאים של הקלסיפייר
(בר-חורג מעבר ל-IB הנטען = בלתי-אפשרי; IB רחב ב->2 נק' = תסמין-ההיסחפות), ומחליף + מתעד
`ib_source`. ‏**Rule 1:** ‏`_first12_rth_extremes()` מחזיר `None` — לא ניחוש — כשאין 12 ברים
או כשיש שדה-OHLC ריק. חלון-הזמן מוצמד ל-`America/New_York` במפורש (Rule 4).

```
5 passed                                                               [23:34:13]
$ _first12_rth_extremes() על ה-DB החי → (7644.25, 7663.75)  = ה-IB האמיתי של היום
```

---

## 3 · מדידות

### 3.1 · 🔴 המספר של הלילה — עם-ההרחבה מול נגד-ההרחבה (39 סשנים, ברוקר בלבד)

```
=== VARIATION days ===                                                 [23:21:08]
WITH-extension      n=32   Σ +158.75   59% win   avg +4.96
COUNTER-extension   n=19   Σ -715.00   32% win   avg -37.63
=== ALL broker-priced (110 rows / 39 sessions) ===
WITH-extension      n=66   Σ +473.75   56% win
COUNTER-extension   n=43   Σ -958.75   37% win
```
**כל הספר (−$455) הוא דלי-נגד-ההרחבה.** בלעדיו: **+$473.75**. מרווח $928.75.

**והשורש למה זה הותר** (`dalton_playbook.py:97`):
```python
if rule_bias.startswith("extension_direction"):
    return direction_hint or "BOTH"
```
אין מכונת-מצבים של "once" — הסיומת `_once_then_BOTH` דקורטיבית. ‏`direction_hint` מגיע רק
מ-`_resolve_live_cls()['direction']`, ו:
```
$ grep -c "dalton_intent:bias" /tmp/backend.err.log   →   0
```
**אפס.** זרוע-ה-bias לא חסמה עסקה מעולם ⇒ ה-bias תמיד `BOTH`.

### 3.2 · שלושת יצרני-הצל — המדידה המבוקשת אינה קיימת

```
=== broker-priced rows only ===                                        [23:35:10]
n=0 for ALL THREE — they have never traded live.
```
שלושתם **צל** ⇒ `pnl_sierra` הוא `NULL` בכל שורה. אין מספר-ברוקר להביא.
מה שקיים הוא שורות-צל מתומחרות-ספרים, ו**אסור לצטט אותן כאילו הן ברוקר** (Rule 1):

| יצרן | n (צל) | Σ ספרים | wins |
|---|---|---|---|
| `FAILED_RE_IB` | 4 | −$496.25 | 1 (25%) |
| `VA_FADE_LONG` | 3 | +$155.00 | 2 (67%) |
| `RE_ACCEPTANCE` | **0** | — | — |

⚠️ ואלה גם חשודים מבנית לפי T-252 (הגלאי רץ מחדש על הבר-הנבנה ⇒ כל מדד-צל היסטורי חשוד).
**לא הודלק אף יצרן.**

### 3.3 · 🔴 תיקון ל-T-285 של cc: ‏VA_FADE לא ירה 0 — הוא ירה 3, וכולן בשעה הראשונה

```
$ select … where pattern_id_at_entry ilike '%VA_FADE%'                  [23:35:45]
#1001 VA_FADE_LONG 2026-09-04 17:15:02  first_hour=YES
#1227 VA_FADE_LONG 2026-09-08 17:15:03  first_hour=YES
#1232 VA_FADE_LONG 2026-09-08 17:20:06  first_hour=YES
```
**המנגנון של cc נכון, הספירה לא.** והתוצאה גרועה יותר מ"מת": שלוש הפעימות נפלו ב-17:15-17:20,
כלומר ב-15 הדקות האחרונות של חלון-ה-IB — בדיוק כשאזור-הערך **הכי פחות** מבוסס — והן קראו
`_load_sierra_tpo()`, שבתוך חלון-ה-IB מחזיר קרוב לוודאי את אזור-הערך של **הסשן הקודם**.
כלומר: אותה מחלקת-היסחפות בדיוק שתיקנתי ב-§2.2. **פריט ל-cc.**

### 3.4 · לא בוצע הלילה — ונרשם ככזה

| פריט | למה לא |
|---|---|
| §4.1 פיגור-סוג-יום (T-286) — עלות ב-39 סשנים | דורש ריפליי-פר-בר של `get_live_day_type`; לא נבנה. ‏⚠️ ויש חשד-TZ פתוח מ-23:15 (`v9_day_type_state.ts` נאיבי) שעלול להפוך את הפריט לארטיפקט — **לאמת לפני שמודדים** |
| §4.4 שער-VSA של REACTIVE | דורש ריפליי-גלאי על 39 סשנים; אין ארכיוני-החלטות בדיסק (`0` תיקיות) |
| §3.3 היגיינת-דגלים (112 stubs) | לא בוצע. ‏`gen_flag_index --check` לא חובר ל-fire_drill |
| §3.5 באנרי-SUPERSEDED + `sot_map_guard --strict` | לא בוצע |
| §3.6 חנק-לוג ל-5 התבניות | לא בוצע |
| §3.4 שדה `measured:` על **כל** דגל פסוק | בוצע חלקית — הוזן על הדגל היחיד שנגעתי בו |

---

## 4 · דגלי-המחר

| דגל | ערך | נימוק |
|---|---|---|
| `DALTON_PLAYBOOK_V1` | **1** (ללא שינוי) | פסיקת-מייקל 11:15, חי מ-16:55. ⚠️ אך נכשל בשער-הקבלה של עצמו (§1.1) — פריט-בוקר |
| `NO_LABEL_NO_FIRE_V1` | **1** (ללא שינוי) | פסיקה עומדת |
| `TRADE_ECONOMICS_AUTHORITY_V1` | **`diff`** (חדש) | **לא `=1`.** §3.2 בפוסט-מורטם: ההצבה שלו הייתה מפסידה יותר בשתי העסקאות (−$390 מול −$177.50). ‏`diff` מאומת **לוג-בלבד** (`trading_gateway.py:2936-2963` לא כותב ל-`setup` ולא מחזיר) ⇒ מדידה, לא שינוי-סיכון |
| `VA_FADE_V1` | **shadow** (ללא שינוי) | החילוץ מאפשר מדידה; לייב = פסיקה |

> ⚠️ **מלכודת שנמצאה:** ל-`=1` **אין מימוש**. ‏`is_diff()` מיובא ב-`:2939` ואף פעם לא
> מסתעף עליו — כלומר `=1` היה מתנהג בדיוק כמו `diff` בעודו **נראה** כמו הדלקה.
> נרשם ב-`RULED_FLAGS.yaml`.

---

## 5 · ריסטארט + אימות

```
                                                                       [23:37:34-23:38:09]
BEFORE: pid=16477 · pg{active 1, idle 7, idle-in-tx 1} · QueuePool total 4123
$ launchctl kickstart -k gui/501/com.mems26.backend
AFTER : pid=13274  ps -o lstart= → Wed Sep  9 23:37:35 2026
[boot] logging OK pid=13274 commit=0151d586      ·  HEAD = 0151d586   ✓ תואם
[TPO] Hydrated IB from DB: H=7663.75 L=7644.25 locked=True W=19.5      ✓ ה-IB הנכון
health http=200 t=0.0095s
pg_stat_activity AFTER: active 1 · idle 7 · idle in transaction 1      ✓ הרבה מתחת לסף 12
QueuePool since restart: 0    ·    ERRORs since restart: 0
```

```
$ python3 scripts/fire_drill.py                                        [23:38:50]
  ✓ effective_contracts == 5    ✓ yaml_valid — 251 ruled flags
  ✓ guard_tests — 159 passed, GUARDS GREEN
  ✓ wire_guard — 56 call sites / 11 signatures
  ✓ task_log_guard — 293 items
  ✓ backend health   ✓ feed age=688ms   ✓ live_slot פנוי
  ✓ live_enabled == [2,4]   ✓ day_type Variation conf=0.33
🟢 GO — כל שרשרת ההחלטה כשרה לירי.
```

---

## 6 · לוח-הבוקר של מייקל — כל שורה עם מספר

1. **נגד-ההרחבה: 19 עסקאות, −$715, 32%** (מול +$158.75/59%). לחסום כיוון-נגדי בימי-Variation?
2. **‏`direction_hint` לא מחובר — 0 חסימות-bias בכל הלוג.** לחווט את `day_bias` מהצל לפלייבוק?
3. **‏`STEP_SCALED_LADDER` דרס את הפותר בשתי העסקאות** — פעם אחרי `rejected`, פעם אחרי
   `WIDEN-TO-STRUCTURE`, ובשתיהן **צר יותר** מהמינימום המבני. לכפוף אותו לרצפה?
4. **בעל-הגודל ב-S2:** הסייזר אמר `2` ויצאו `5` (מפתח-metadata שונה מ-S4). לחווט או להשאיר?
5. **הפלייבוק חי ונכשל בשער שלו:** מנצחים 63%/75%, מפסידים 55%/60%. להשאיר חי או להחזיר לצל?

**אפס נגיעה:** לא נגעתי ב-`RISK_BUDGET_USD` / `RISK_MIN_CONTRACTS` / `FIXED_CONTRACTS_5` ·
לא הודלק יצרן · לא הוחזר שער כבוי-בפסיקה · אין `git stash` · הריסטארט בוצע פעם אחת, אחרי
23:00, בסוף העבודה.
