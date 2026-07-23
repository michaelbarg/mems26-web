# סקירה עצמאית — RESPONSIVE_WITH_DAY_TREND_V1 (2026-07-23)

**אל:** הסוכן המאמת (cursor / cc-macbook) · **מאת:** cowork-dev · **פעל לפי** `docs/handoff/CC_HANDOFF_CONTRACT.md`
**סטטוס:** נבנה + אומת (cowork) + **הודלק חי לפי פסיקת-מייקל** · **HEAD `795f6924`** · flag_guard 119/119
**המטרה שלך:** ביקורת בלתי-תלויה (חוק-5 + מבחן-ליטמוס revert→RED) על שינוי trading-logic שכבר חי על כסף-אמת. זה **לא** פרומפט-בנייה — הקוד קיים; אתה **מאמת/מפריך**.

---

## 1 · מה השתנתה — התמצית

**השורש (מייקל הצביע, אומת בקוד):** מערכת 2 בוחרת כיוון מצורת-המחיר בלבד, **עיוורת ל-S1**. `trend_state`/`day_type` הוזנו רק ל-sizing (`compute_v2_sizing`) ולוטו-מיקום — **אף פעם לא לבחירת-כיוון**. בענף ה-RESPONSIVE של הפלייבוק (`daytype_playbook.decide`, משפחת `_RESPONSIVE_REV={REACTIVE,HNS}`) ההכרעה הייתה **מיקום-בלבד** (שורט@VAH / לונג@VAL). לכן ביום-יורד: שורט-עם-הטרנד mid_value נחסם "not at VAH", ולונג-נגד-הטרנד ב-VAL היה מותר → קנייה-בדיפ ביום-יורד.

**התיקון (`RESPONSIVE_WITH_DAY_TREND_V1`, default OFF):** ביום-כיווני, כשכיוון-יום ידוע, המשפחה-המגיבה מצייתת לטרנד:
- counter-trend (LONG@DOWN / SHORT@UP) → **SKIP** ("never fade the trend")
- with-trend (SHORT@DOWN / LONG@UP) → **ALLOW** המשך מחוץ-לקצה, **פרט** לרדיפת-קיצון (SHORT@below_value / LONG@above_value) → SKIP
- דגל OFF **או** כיוון-לא-ידוע → מיקום-בלבד, **byte-identical**

**כיוון-יום** = `get_live_expansion()` (accepted-break) ואם None → fallback חדש `get_live_dir_bias()` = **LSMA-מוחזק על 6 הברים האחרונים** (RED→DOWN/BLUE→UP, GRAY מנוטרל, רוב ≥60%). שורד את ה-GRAY-הרגעי שקורה בדיוק בבר-התיקון (07-23 16:45).

**3 עריכות + קומיטים:**
| קובץ | שינוי | קומיט |
|---|---|---|
| `backend/v9/services/trade_context.py` | `get_live_dir_bias()` חדש (קורא `v9_bars_5min_woodies` דרך `db/read.py`) | `52eb13ba` |
| `backend/v9/systems/daytype_playbook.py` | ענף RESPONSIVE החדש (עם/נגד-טרנד + chasing-guard) | `52eb13ba` |
| `backend/v9/gateway/trading_gateway.py` (~715) | wiring: dir_bias→day_direction כש-expansion=None, flag-gated | `52eb13ba` |
| `docs/FLAG_REGISTRY.yaml` + `config/RULED_FLAGS.yaml` + `.env` | דגל + פסיקה (`795f6924`) | `795f6924` |
| `tests/v9/regression/test_responsive_with_day_trend.py` | 6 טסטים | `52eb13ba` |

**risk surface — אל תיגע** בלי פסיקה: ה-flag עצמו (חי לפי פסיקה), `REQUIRE_WITH_TREND_DAY_DIRECTION_V1=1`, `DAYTYPE_PLAYBOOK=1`, דגלי-הכיול 16T/1.5R/probe. אל "תשחזר" שום דגל-כבוי (CLAUDE.md §Standing).

---

## 2 · הראיה שלי (שחזר → אשר/הפרך)

**AC-1 · טסטים עוברים ואינם טאוטולוגיים.**
```
BRIDGE_TOKEN=test python3 -m pytest tests/v9/regression/test_responsive_with_day_trend.py -q   → 6 passed
```
מבחן-ליטמוס לכל טסט (עשה זאת בעצמך): `git stash` את `daytype_playbook.py` בלבד → הרץ → **חייבים להיכשל** (`test_with_trend_short_allowed_off_edge_on_down_day`, `test_counter_trend_long_blocked_on_down_day`, `test_with_trend_short_chasing_low_blocked`). אם נשארים ירוקים אחרי revert → הטסט **פסול**, דווח. הטסטים קוראים ל-`decide()` הייצורי (לא מעתיקים לוגיקה).

**AC-2 · אפס רגרסיה.**
```
BRIDGE_TOKEN=test python3 -m pytest tests/v9/regression -k "boot or demotion or daytype or decisions or order_fail or playbook or day_direction or ts_offset" -q   → 187 passed
```

**AC-3 · replay על ה-setups האמיתיים של 07-23** (הראיה המרכזית — לא טסט-סינתטי). 7 ה-setups שהמערכת ייצרה היום, דרך `decide()` עם day_dir=DOWN:

| שעה | pattern | דגל OFF (מה שקרה) | דגל ON (התיקון) |
|---|---|---|---|
| 16:50 | REACTIVE_LONG @7469.75 | SKIP (not at VAL) | **SKIP — counter-trend, never fade** ✓ |
| 16:55 | REACTIVE_SHORT @7456.5 | SKIP (not at VAH) | **ALLOW — with-trend** ✓ ← הפספוס תוקן |
| 17:15 | REACTIVE_SHORT @7455 | SKIP | ALLOW ✓ |
| 17:25 | REACTIVE_LONG @7457.75 | SKIP | SKIP (counter) ✓ |
| 17:30 | REACTIVE_SHORT @7449.75 | SKIP | ALLOW ✓ |
| 17:35 | REACTIVE_LONG @7464.25 | SKIP | SKIP (counter) ✓ |
| 17:40 | REACTIVE_SHORT @7448.75 | SKIP | ALLOW ✓ |

OFF = כל-7-SKIP (שטוחים) → ON = 4 שורטים-עם-הטרנד ALLOW + 3 לונגים-נגד-הטרנד SKIP. **אמת זאת בעצמך** — הלוגיקה ב-`/tmp` אינה בריפו; שחזר עם `decide(pattern=..., day_type="Variation", direction=..., day_direction="DOWN", entry_price=..., levels={"vah":7472,"val":7450,"ib_width":12})`.

**AC-4 · dir_bias חי מ-Postgres (לא SQLite).**
```
DATABASE_URL=postgresql://localhost/mems26 python3 -c "import sys;sys.path.insert(0,'.'); from backend.v9.services.trade_context import get_live_dir_bias; print(get_live_dir_bias())"   → DOWN
```
(6 הברים האחרונים = RED). **בלי** `DATABASE_URL` → `db/read.py` נופל ל-SQLite-פגום ומחזיר None — ודא שהבאקנד-החי מזין DATABASE_URL (env_loader).

**AC-5 · דגל פעיל בתהליך.** `flag_guard.py` → PASS 119/119; `parse_env('.env')['RESPONSIVE_WITH_DAY_TREND_V1']=='1'` (בדיוק, בלי הערת-inline — ראה §NOT-DONE להלן).

---

## 3 · מה **אתה** צריך לבדוק בלתי-תלוי (מעבר לשחזור שלי)

1. **byte-identical כשהדגל OFF** — קרא את הענף ב-`daytype_playbook.py`: כש-`RESPONSIVE_WITH_DAY_TREND_V1` OFF, `_with_trend_allow` נשאר False והזרימה חוזרת ל-בלוק-המיקום המקורי מילה-במילה. ודא שאין נתיב שבו הדגל-OFF משנה תוצאה. (AC: הרץ את סוויטת-הפלייבוק הקיימת `test_dalton_require_day_direction_vah.py` — חייבת להישאר ירוקה.)
2. **wiring בגייטוויי מגיע לענף** — ודא ש-`day_direction` באמת מוזרם ל-`_pb_decide` (trading_gateway ~739) וש-`get_live_dir_bias` נקרא רק כש-expansion=None ורק כשהדגל ON. בדוק שאין כפילות/דריסה עם ה-expansion.
3. **`get_live_dir_bias` עמידות** — האם 60%/6-בר סף מספיק? בדוק קצה: 3 RED + 3 BLUE → None (נכון?); חלון-קצר בבוקר (<3 ברים) → None (fail-closed, נכון). האם קריאת-DB פר-הערכת-setup יקרה מדי? (fires נדירים — לדעתי לא, אבל שקול cache/buffer).
4. **chasing-guard** — כרגע חוסם רק את הקיצון-הרחוק (below_value/above_value). האם שורט-עם-הטרנד ב-mid_value אחרי ירידה-ארוכה עדיין "מנקודה גבוהה" מספקת? זו שאלת-דוקטרינה למייקל, לא באג.
5. **הצלבה מול הלוג-החי** — חפש ב-`/tmp/backend.err.log` מאז 18:20: `"never fade the trend"` / `"with-trend"` / `"chasing extreme"` — כמה הופיעו, ועל אילו setups.

---

## 4 · NOT-DONE / הסתייגויות כנות (חובה — אל תדלג בקריאה)

1. **🔴 #479 נסגר LOSS (~‑9.5pt), ולא הודגם ע"י הדגל.** ירי-הלייב 18:25 (SHORT #479) הוא **INITIATIVE_SHORT — לא REACTIVE**, ולכן **לא עבר בענף שתיקנתי כלל**. הוא מוכיח רק ששרשרת-ה-execution בריאה חי (ORDER_SUBMITTED, אפס r=-1, 4 חוזים, ברקט). **אל תספור אותו כראיה לדגל.** הראיה לדגל היא ה-replay (§AC-3) בלבד. פירוט #479: entry 7423.5 → T1@7419.25 ✓ → T2@7415.75 ✓ → המחיר קפץ מ-7411 ל-7434.75 → **2 ראנרים נעצרו @7434.25**. נטו: +4.25 +7.75 −10.75 −10.75 = **−9.5pt**.
2. **🟡 סטופ לא עבר ל-BE אחרי T1/T2 (ניהול-ראנר) — נפרד מהתיקון שלי.** לו הסטופ היה עובר ל-BE אחרי T1, הראנרים היו נעצרים ~שטוח והעסקה נטו-חיובית. זה פער-ניהול ב-S2-initiative (לא ZLR), **לא** נגרם מהשינוי שלי — אבל שווה בדיקה נפרדת. לא טיפלתי בו.
3. **🟡 יציבות סוג-היום לא תוקנה — עוקפתי אותה.** סוג-היום מקרטע Variation↔Trend כל ~5 דק' (הלוג: 17:05/17:30/17:35/17:40...). התיקון עוקף זאת דרך dir_bias (LSMA-מוחזק, לא day_type), אבל **הקרטוע עצמו לא טופל** — שיפור-המשך נפרד (`[[project_s1_daytype_recalibration]]`).
4. **🟡 חסר sim-execution-verify ייעודי.** "לאמת-סים" מומש כ-unit+replay על נתונים-אמיתיים (לא הרצת-סים-חיה של הדגל), כי המערכת כבר במצב-לייב כשמייקל פסק. הדגל הודלק ישירות ללייב. לא ראיתי עדיין REACTIVE-חי עובר בענף (רק INITIATIVE ירה מאז ההדלקה).
5. **✅ תוקן תוך-כדי:** הערת-inline בשורת-ה-.env שברה את `parse_env` (הערך היה "1  # ..." → נכשל `.lower() in ("1",...)`). **env_loader לא מקלף הערות-inline** — הערך עכשיו בשורה נקייה, ההערה בשורה מעל. אם אתה מוסיף דגל — אותו כלל.

---

## 5 · הכרעה מבוקשת ממך
סמן כל AC ✓/✗ עם command+raw output (חוק-5). אם מבחן-הליטמוס נכשל על טסט כלשהו, או ה-byte-identical-OFF מופר, או ה-wiring לא מגיע לענף — **פתח 🔴 ב-LIVE_CHANNEL §OPEN אל cowork-dev** והצע strategic-stop. אחרת אשר ב-LIVE_CHANNEL LOG. תודה.
