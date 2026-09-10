# סולם · מיקום · סוג-פתיחה — שלוש שאלות, שלוש תשובות עם מספר

**נכתב:** 2026-09-10 08:12→08:35 IL · **סוכן:** cowork-dev · **מצב:** READ-ONLY (אפס עריכת קוד/‏.env/‏שירותים/‏דגלים)
**בסיס-תמחור:** `pnl_sierra` בלבד · `mode='live'` · `state<>'CANCELLED'` · MES $5/נקודה
**חלון A** = 2026-08-01…08-28 (n=51, +$1,027.50) · **חלון B** = 2026-08-31…09-09 (n=24, −$670.00)
**קודם:** `docs/reports/AUGUST_VS_SEPTEMBER_2026-09-10.md`

---

## 0 · שלוש התשובות בשלוש שורות

1. **M1 — הסולם אינו המנוף.** אין הקצאה של 5 חוזים שמנצחת את `(1,2,1,1)` בחלון B בלי להחזיר
   פי-6 עד פי-140 מזה בחלון A. הטובה-ביותר, `(2,2,1,0)`, משפרת את B ב-**+$7.50** ועולה ב-A
   **−$1,041.25**. **לחוזה**, `(1,2,1,1)` היא כבר הצורה הטובה-ביותר (או שוות-סטטיסטית) ב-B.
2. **M2 — ההשערה של מייקל אינה נתמכת, וההיפוך שלה כן.** מתוך −$672.50 של חלון B,
   כניסות **בתוך** הערך תרמו **+$5.00 על 5 עסקאות**. 65% מההפסד (−$440.00, 11 עסקאות, 27% ניצחון)
   בא מכניסות **מעבר** לאזור-הערך. המכונה לא סחרה ב-POC — היא סחרה **הרחק ממנו**.
3. **M3 — אף שער לא הסיר את עסקאות-הפתיחה; היצרן כמעט לא מייצר.** ב-10 סשנים נוצרו
   **7** מועמדי-פתיחה, **3** הגיעו לברוקר, ואף אחד מארבעת הדגלים החשודים אינו מופיע ב-`blocked_by`
   ולו פעם אחת — כי הם מאפסים `_trig` **בתוך** `five_min_system.py`, במעלה-הזרם של פיד-ההחלטות.

---

## 0.1 · 🔴 שתי הנחות בפקודה שהתבררו כשגויות — לתקן לפני שממשיכים

| הנחה בפקודה | המצב בפועל | ראיה |
|---|---|---|
| «`DAYTYPE_LOCATION_GATE`/`REACTIVE_LOCATION_GATE` שניהם `0` ב-.env» | `REACTIVE_LOCATION_GATE=0` ✅ אבל **`DAYTYPE_LOCATION_GATE=1` — דלוק** | `.env:367` |
| «שום דבר בנתיב-החי לא בודק POC/VAH/VAL» | `backend/v9/systems/location_gate.py` **כן** — הוא מיישם אזורי-VAH/VAL/POC עם דרישת-probe, והוא **חי**. בספירה-המדודדת של דוח-הבוקר לחלון B הוא חסם **9 מועמדים בשווי −$451.38** | `location_gate.py:185` קורא את הדגל · דוח-הבוקר §3.4 |

**מה שכן אושר:** `backend/v9/services/dalton_playbook.py` באמת מכיל **אפס** לוגיקת POC/VAH/VAL.
`grep -n -i -E "poc|vah|val\b|value_area|va_high|va_low"` על הקובץ מחזיר 4 שורות **בלבד** —
כולן משתנה-פייתון מקומי בשם `val` בשורות 107/108/114/115 (`val = cond.split("== ",1)[1]`), לא ערך-שוק.
כלומר: שער-המיקום קיים ודלוק — הוא פשוט **לא** בתוך הפלייבוק של דלתון.

---

## 1 · M1 — הסולם

### 1.1 · המוסכמות (כדי שאפשר יהיה לבקר כל מספר)

| מוסכמה | ערך | למה |
|---|---|---|
| סטופ-בכניסה | `COALESCE(quality->>'initial_stop', stop)` | 🔴 **קריטי.** עמודת `stop` היא הסטופ ה**מוזז** (BE). היא תוחמת נכון את הכניסה רק ב-**38/75** עסקאות; ה-COALESCE תוחם **75/75** |
| רמת T0 | כניסה ± **3.0** נק׳ | `.env:355 T0_TARGET_PTS=3.0`; ב-DB רק 23/75 נושאות `t0_target_pts`, וכולן `'3.0'` |
| מיפוי רגליים | `c1..c4 → T0/T1/T2/T3` | `contract_size.target_index_for_contract` |
| סימן | LONG: `יציאה−כניסה` · **SHORT: `כניסה−יציאה`** | |
| חלון-ההליכה | ברים שלמים **אחרי** בר-הכניסה, עד 23:00 IL | בר-הכניסה החלקי מכיל טווח שקדם לכניסה ⇒ ייצר פגיעות-סטופ מדומות |
| בר שמכיל גם יעד וגם סטופ | **סטופ מנצח** (שמרני, נגדנו) | |
| רגל שלא נפתרה עד הסגירה | סומנה למחיר-הסגירה של הבר האחרון | A: 11 רגליים · B: 3 |
| `t2`/`t3` חסרות | נפילה-לאחור ליעד הזמין הנמוך הבא | A: `T2←T1`×8, `T3←T2`×9 · B: ×2, ×2 |

### 1.2 · 🟢 עמימות-תוך-בר אינה מסבירה את התוצאה

> **A: 1/51 = 2% · B: 2/24 = 8%.** שניהם הרבה מתחת לחמישית.
> התוצאה **אינה** ארטיפקט של עיוורון תוך-בר.

### 1.3 · כיול-המודל מול הברוקר (Rule 2 — לפני שמשווים סולמות)

המודל הוא «יעד-או-סטופ» בלבד: בלי BE-אחרי-T0, בלי סקראץ׳, בלי טריילינג.

| מודל | A: מודל על הסולם ה**אמיתי** | A: ברוקר | B: מודל | B: ברוקר |
|---|---|---|---|---|
| סטופ-מקורי | $810.05 | **$1,027.50** | −$537.50 | **−$670.00** |
| BE-אחרי-T1 | $945.05 | **$1,027.50** | −$290.00 | **−$670.00** |

המודל שמרני ב-A ואופטימי ב-B. הוא **מדרג** סולמות אך אינו מתמחר אותם מדויק. כל מספר להלן — יחסי.

### 1.4 · 🔴 הטבלה — סולם × חלון (מודל BE-אחרי-T1, הריאליסטי)

| סולם | A: Σ$ | A: $/חוזה | B: Σ$ | B: $/חוזה | B: חוזים על T2/T3 | B: מימושי-יעד שם | **Δ ב-B** | **מחיר ב-A** |
|---|---|---|---|---|---|---|---|---|
| **`(1,2,1,1)` היום, 5c** | **3,195.75** | **12.53** | **−615.00** | **−5.12** | 48 | 12 | — | — |
| `(2,2,1,0)` 5c | 2,154.50 | 8.45 | −607.50 | **−5.06** | 24 | 8 | **+7.50** | **−1,041.25** |
| `(2,3,0,0)` 5c | 2,114.50 | 8.29 | −707.50 | −5.90 | 0 | 0 | −92.50 | −1,081.25 |
| `(3,2,0,0)` 5c | 1,579.50 | 6.19 | −755.00 | −6.29 | 0 | 0 | −140.00 | −1,616.25 |
| `(1,1,0,0)` אוגוסט, 2c | 738.80 | 7.24 | −292.50 | **−6.09** | 0 | 0 | +322.50 | −2,456.95 |

ואותה טבלה במודל סטופ-מקורי (חסם-עליון ליעדים-רחוקים), לשלמות:

| סולם | A: Σ$ | B: Σ$ | Δ ב-B | מחיר ב-A |
|---|---|---|---|---|
| `(1,2,1,1)` 5c | 3,845.75 | −862.50 | — | — |
| `(2,2,1,0)` 5c | 2,277.00 | −698.75 | +163.75 | −1,568.75 |
| `(2,3,0,0)` 5c | 2,114.50 | −707.50 | +155.00 | −1,731.25 |
| `(3,2,0,0)` 5c | 1,579.50 | −755.00 | +107.50 | −2,266.25 |
| `(1,1,0,0)` 2c | 738.80 | −292.50 | +570.00 | −3,106.95 |

### 1.5 · 🔴 התשובה בשורה אחת

> **לא. אין הקצאת-5-חוזים שמנצחת את `(1,2,1,1)` ב-B בלי להחזיר את הזנב של A.**
> הטובה-ביותר, **`(2,2,1,0)`: +$7.50 ב-B · −$1,041.25 ב-A** — יחס של 1:139 לרעתנו.
> שתיים מארבע החלופות (`(2,3,0,0)`, `(3,2,0,0)`) **גרועות יותר גם ב-B**.
> **לחוזה** ההפרש בין שתי המובילות ב-B הוא $0.06 על n=24 — **הנתונים אינם מפרידים ביניהן.**

### 1.6 · 🔑 והממצא שמתקן את דוח-הבוקר

דוח-הבוקר ייחס −$250 (37% מההפסד) ל«גודל+סולם». **התמחור-מחדש שלו מדד גודל, לא צורה.**
סולם-2-החוזים «מפסיד פחות» רק מפני שהוא סוחר 60% פחות חוזים. **לחוזה הוא גרוע יותר:**

> **B, לחוזה: `(1,2,1,1)` = −$5.12 · `(1,1,0,0)` 2c = −$6.09.**
> הצורה של היום היא ה**טובה** מבין השתיים. ההפסד של B אינו בעיית-הקצאה.

### 1.7 · פיצול ה-P&L: רגלי T0/T1 מול T2/T3

מהריפליי, תחת `(1,2,1,1)`, מודל BE-אחרי-T1 (מלא ופנימית-עקבי):

| חלון | T0/T1 | T2/T3 | חלק T2/T3 |
|---|---|---|---|
| **A** | $1,375.70 | **$1,820.05** | **57%** |
| **B** | −$415.00 | −$200.00 | 33% מההפסד |

מיומן-המימושים האמיתי (`quality.exit_fills`, רגלי-יעד בלבד — סגירות-סטופ נושאות `kind=STOP`
ואינן מיוחסות לרגל, ולכן זה **רווחי-הרגליים** ולא נטו):

| חלון | כיסוי היומן | T0+T1 | T2+T3 |
|---|---|---|---|
| A | 20/51 | $528.75 | $250.00 |
| B | 23/24 | $518.75 | **$90.00** |

**רגלי T2/T3 הן שם הכסף של אוגוסט (57%). לבטל אותן זו בדיוק התנועה ההפוכה.**

---

## 2 · M2 — מיקום

### 2.1 · מקורות, ומבחן-ה-TZ שלא הונח אלא נבדק

* **POC/VAH/VAL — `v9_tpo_history`**, השורה האחרונה עם `ts <= entry_ts` באותו תאריך-IL.
  **למה:** זו טבלת-הערך היחידה שהיא **סדרת-זמן**; ל-`v9_tpo_sessions` יש שורה מיושבת אחת לסשן,
  ולכן שימוש בה כ«מצב-בכניסה» הוא **הצצה-לעתיד**.
* **אזהרת ה-3 שעות נבדקה ונדחתה:** ה-IB המיושב מ-`v9_tpo_history` תואם את ה-IB שחושב מהברים
  ב-**23/23** תאריכים (`v9_tpo_sessions` — **24/24**). `ts` אינו מוסט.
  הארטיפקט האמיתי היחיד: **שורת ה-16:30 עדיין נושאת את פרופיל טרום-הפתיחה** (A: 12 כניסות, B: 4).
* **IB — חושב כאן** מ-12 הברים הראשונים של RTH ב-`v9_bars_5min_woodies`, ונחתך לברים שנסגרו
  עד רגע-הכניסה (A: 14 כניסות לפני שה-IB הושלם, B: 9). **IB שמור לא נלקח באמון.**

### 2.2 · 🔴 הטבלה — דלי-מיקום × חלון

| דלי | A: n | A: Σ$ | A: ניצחון | B: n | B: Σ$ | B: ניצחון |
|---|---|---|---|---|---|---|
| `AT_VALUE` (‏±25% מרוחב-VA סביב POC) | 18 | **+840.00** | **72%** | 4 | −65.00 | 50% |
| `MID_VA` | 10 | +147.50 | 70% | 1 | +70.00 | 100% |
| `EDGE_VA` (‏±25% מ-VAH/VAL) | 12 | +282.50 | 67% | 7 | −237.50 | 43% |
| **`OUTSIDE_VA`** | 11 | **−242.50** | **36%** | 11 | **−440.00** | **27%** |
| **סה״כ** | **51** | **+1,027.50** | | **23** | **−672.50** | |

**מפסידות בלבד:**

| דלי | A: n / Σ$ | B: n / Σ$ |
|---|---|---|
| `AT_VALUE` | 5 / −187.50 | 2 / −196.25 |
| `MID_VA` | 3 / −195.00 | 0 |
| `EDGE_VA` | 4 / −283.75 | 4 / −422.50 |
| **`OUTSIDE_VA`** | **7 / −501.25** | **8 / −671.25** |

**שכבת IB_EDGE (‏≤2 נק׳ מקצה-ה-IB, בלתי-תלויה בדלי):** A 8 / +220.00 / 62% · B 5 / −117.50 / 40%.
**מרחק מ-POC:** A חציון 0.29 רוחבי-VA (7.50 נק׳) · B חציון 0.46 (8.50 נק׳).

### 2.3 · 🔴 השורה שמייקל ביקש

> **מתוך −$672.50 של חלון B: כניסות בתוך-הערך (`AT_VALUE`+`MID_VA`) = 5 עסקאות, +$5.00.
> הכניסות בקצוות ומעבר להם הן כל ההפסד: `EDGE_VA` −$237.50 (7) · `OUTSIDE_VA` −$440.00 (11, 27% ניצחון).**
>
> **ההשערה «מסחר ב-POC ולא באזורי הקיצון» אינה נתמכת — היא הפוכה.** באוגוסט `AT_VALUE` היה
> ה**דלי הרווחי-ביותר** (+$840, 72%) ו-`OUTSIDE_VA` הגרוע-ביותר. בספטמבר `AT_VALUE` הצטמק
> מ-18 עסקאות ל-**4**, ו-`OUTSIDE_VA` נשאר 11. הכסף האבוד יושב **הרחק מהערך**, לא עליו.

### 2.4 · ⚠️ אזהרה: תוויות-הדליים אינן יציבות

| בדיקה | A | B |
|---|---|---|
| POC-בכניסה שונה מ-POC-המיושב ביותר מ-25% מרוחב-VA | **40/51** | **16/23** |
| רוחב-VA: חציון · מינימום | 26.50 · 8.25 | 19.75 · **1.00** |
| `OUTSIDE_VA` על VA צר (<8 נק׳) | 0 מ-11 | 1 מ-11 (−$125) |

הצלבה מול ה-VA ה**מיושב** (`v9_tpo_sessions` CASH) מסווגת אחרת לגמרי:
A → `OUTSIDE_VA` 34 / **+472.50** · B → `EDGE_VA` 9 / −720.00, `OUTSIDE_VA` 9 / −262.50.
**כלומר: התווית תלויה בקריטית באיזה תצלום-ערך בוחרים.** ה-VA המתפתח הוא הקלט הנכון לשער-חי
(זה מה שהמנוע רואה), אבל הוא זז הרבה במהלך היום. הדליים לבדם אינם בסיס לפסיקה.

### 2.5 · 🟢 החתך שכן יציב בשתי הגדרות-ה-VA — ובשני החלונות

הגדרה: **`CHASE-POC`** = הכניסה בצד ה**רחוק** של ה-POC בכיוון-העסקה
(LONG מעל POC · SHORT מתחת ל-POC) — כלומר רדיפה **הרחק** מהערך.
**`TOWARD-POC`** = ההפך — כניסה שמצביעה **חזרה** אל הערך.
כל הקלטים ידועים ברגע-הכניסה. אפס הצצה-לעתיד.

| | A: n / Σ$ / ניצחון | B: n / Σ$ / ניצחון |
|---|---|---|
| **`TOWARD-POC`** | **24 / +1,261.25 / 75%** | **2 / +36.25 / 50%** |
| **`CHASE-POC`** | 27 / **−233.75** / 52% | 21 / **−708.75** / 38% |

> **`CHASE-POC` הפסיד בשני החלונות. `TOWARD-POC` הרוויח את כל הרווח של אוגוסט.**
> **והקצב קרס: כניסות-לכיוון-הערך היו 24/51 = 47% מאוגוסט, ו-2/23 = 9% מספטמבר.**

הצלבה עם T-295 (נגד-ההרחבה) מראה שאלה **לא** אותו חתך — הצומת הוא שמרכז את ההפסד:

| | A: n / Σ$ | B: n / Σ$ |
|---|---|---|
| TOWARD-POC · עם-ההרחבה | 19 / +901.25 | 1 / +76.25 |
| TOWARD-POC · נגד-ההרחבה | 5 / +360.00 | 1 / −40.00 |
| CHASE-POC · עם-ההרחבה | 21 / −188.75 | 12 / +33.75 |
| **CHASE-POC · נגד-ההרחבה** | **6 / −45.00** | **9 / −742.50** |

### 2.6 · הכלל שזה מרמז — ומה הוא היה עולה בחלון A

כל הכללים להלן **בני-מימוש**: POC מתפתח + הרחבה-עד-כה בלבד.
(הסכמה בין «הרחבה-עד-הכניסה» ל«הרחבת-כל-היום»: A 45/51, B 22/23 — ההצצה-לעתיד אינה נושאת-משקל.)

| כלל = לחסום את אלה | A: n | A: $ שנחסם | A: נטו אחרי | A: נשמרו | B: n | B: $ שנחסם | B: נטו אחרי | B: נשמרו |
|---|---|---|---|---|---|---|---|---|
| *(בסיס)* | | | *+1,027.50* | *51* | | | *−672.50* | *23* |
| **`CHASE-POC` (ללא פרמטר)** | 27 | −233.75 | **+1,261.25** | 24 | 21 | −708.75 | **+36.25** | **2** |
| `CHASE-POC` מעבר ל-3 נק׳ | 22 | −481.25 | **+1,508.75** | 29 | 17 | −662.50 | −10.00 | 6 |
| `CHASE-POC` מעבר ל-0.1 רוחבי-VA | 21 | −450.00 | +1,477.50 | 30 | 19 | −840.00 | **+167.50** | 4 |
| `CHASE-POC` ∧ נגד-הרחבה (עד-הכניסה) | 5 | −20.00 | +1,047.50 | 46 | 8 | −617.50 | −55.00 | 15 |
| נגד-הרחבה בלבד (עד-הכניסה) | 13 | **+342.50** | +685.00 | 38 | 9 | −657.50 | −15.00 | 14 |

> **הכלל המדויק שהנתונים מרמזים עליו:**
> **«אין כניסה שהמחיר בה נמצא בצד הרחוק של ה-POC בכיוון-העסקה — אלא אם סוג-הכניסה הוא המשך-מאושר»**
> (מקבילה ל-`entry_kind` של `dalton_playbook`; היום אין דגל כזה).
> **מחירו בחלון A: הוא לא עולה — הוא מרוויח +$233.75** (חוסם 27, משאיר 24 עסקאות, +$1,261.25).

**⚠️ ומה שאסור להסיק ממנו היום:** בגרסה חסרת-הפרמטר הוא משאיר **2 עסקאות בלבד** ב-B —
זו השבתה, לא סינון, ואין בה ראיה שהניצולים רווחיים. הגרסאות עם סף (3 נק׳ / 0.1 רוחבי-VA)
נבחרו מתוך **~10 וריאנטים שנבדקו על 74 עסקאות** — זו התאמה-בתוך-המדגם.
לפי `LEARNING_DOCTRINE_2026-09-09`: **הוראה חדשה ⇒ קודם ריפליי, אחר-כך דגל.**

---

## 3 · M3 — סוג-הפתיחה

### 3.1 · עסקאות-לייב בחלון-הפתיחה (16:30–17:30 IL)

| חלון | סה״כ | יצרני-פתיחה | כל השאר |
|---|---|---|---|
| **A** | 14 | **1** — `OPENING_ORR` #822, **−$95.00** | 13 · +$553.75 (ZLR 6/+227.50 · REACTIVE_LONG 2/+230.00 · HTLB 1/+83.75 · GB100 1/+73.75 · INITIATIVE_LONG 1/−47.50 · ללא-תווית 2/−13.75) |
| **B** | 9 | **1** — `OPENING_DRIVE` #875, **−$100.00** | 8 · +$111.25 (INITIATIVE_LONG 2/+217.50 · REACTIVE_SHORT 1/+116.25 · ללא-תווית 1/+40.00 · GB100 1/−8.75 · ZLR 1/−125.00 · INITIATIVE_SHORT 2/−128.75) |

**שתי עסקאות-פתיחה בסך-הכל בשני החלונות יחד, שתיהן מפסידות, −$195.00.**

### 3.2 · פיד-ההחלטות, 10 סשנים

**קבצים:** `decisions_archive/gateway_decisions.2026-{08-27,08-28,08-31,09-01,09-02,09-03,09-04,09-07,09-08}.jsonl`
\+ `gateway_decisions.jsonl` (09-09).
**2,571 שורות גולמיות → 747 מועמדים מדודדים** (פקטור-ניפוח **3.44×**).
**מפתח-הדדופ:** `candidate_id` מ-`candidate_ledger.v1` — זהו המפתח הנכון: כפילות T-252/`BLOCKED_TWIN_V1`
היא **אותו** מועמד שנפלט-מחדש על הבר-הנבנה ונושאת את **אותו** `candidate_id`.
**⚠️ `gateway_decisions.jsonl` החי חסום ל-~200 שורות (177 בפועל) ⇒ סשן 09-09 קטוע; ספירתו רצפה, לא מפקד.**

| יצרן-פתיחה (שם מהקוד) | נוצרו (מדודד) | הגיעו לברוקר |
|---|---|---|
| `OPENING_DRIVE` | 5 | 2 (#875 31.08 · #1220 08.09) |
| `OPENING_ORR` | 2 | 1 (#822 27.08) |
| `OPENING_TEST_DRIVE` | **0** | 0 |
| `OPENING_PULLBACK_CONT` | **0** | 0 |
| **סה״כ** | **7** | **3** |

**ארבעת שנחסמו:** `news_blackout` ×2 (01.09) · `direction_context` ×1 (28.08) · `direction_compass` ×1 (07.09).

**🔴 אף אחד מארבעת הדגלים החשודים בפקודה אינו מופיע ב-`blocked_by` ולו פעם אחת — והסיבה מבנית:**
`OPENING_FIRST_TRADE_STRICT_V1`, `OPENING_DRIVE_SKIP_V1` ו-`OPENING_PATTERN_SKIP_V1` כולם עושים
`_trig = None` **בתוך** `backend/v9/systems/five_min/five_min_system.py` (שורות 2206‑2280) ורק
כותבים ללוג. הם **לעולם** לא קוראים ל-`route_setup`, ולכן **לא יכולים** לייצר שורת-חסימה.
זו בדיוק המלכודת «`grep ⇒ 0` מוכיח רק שהמחרוזת שניחשתי לא נמצאה» — כאן ה-0 אמיתי אך משמעותו הפוכה:
לא «הם לא חסמו», אלא «הם חוסמים במקום שהפיד אינו רואה».

### 3.3 · מפקד-הלוג — ומה שהוא חשף

`/tmp/backend.err.log` מכסה **2026-09-06 → 09-10 בלבד** (3 סשני-מסחר), ולכן זהו מדגם ולא מפקד:

| מחרוזת | ספירה | סשנים |
|---|---|---|
| `OPENING_FIRST_TRADE_STRICT held` | 3 | 07.09 ×2, 08.09 ×1 |
| `OPENING_DRIVE_SKIP` | **0** | — (`.env:705 =0`, עקבי) |
| `OPENING_PATTERN_SKIP` | **0** | — (לא-מוגדר, עקבי) |
| `OPENING_ENTRY … live-eligible` | 2 | 07.09 16:50, 08.09 16:40 |
| **`OPENING_ENTRY: first seen bar … is past 09:30 — honest skip today`** | **3** | **08.09 ×2, 09.09 ×1** |

* **`FIRST_TRADE_STRICT` השהה, לא הסיר.** בשני המקרים הסטאפ נפלט דקות ספורות אחר-כך
  (07.09: נעצר 16:40+16:45 → נפלט 16:50 · 08.09: נעצר 16:35 → נפלט 16:40).
* 🔴 **`honest skip today` הוא המסיר האמיתי היחיד שזוהה בשמו.** כשהבר הראשון שהמנוע רואה
  מאוחר מ-16:30, `_oe_disabled = True` ו**מנוע-הפתיחה מת לכל אותו יום**.
  ב-09.09 הבר הראשון היה 13:55 UTC = **16:55 IL** ⇒ אפס פתיחה באותו סשן.

### 3.4 · חלון-הפתיחה כולו (כל היצרנים), 10 סשנים

**117 מועמדים מדודדים · 27 הגיעו לברוקר.** מפקד-חסימות מדודד (חסומים ע"י שער **אחד** בדיוק, 82):

```
awaiting_release            42     lsma_flat                  4
direction_compass           10     fhb                        3
entry_location_quality       7     cold_start_guard           2
dalton_intent:stand_down     5     news_blackout              2
                                   entry_not_confirmed        2
                                   extreme_chase_guard        2
```
לפי-תבנית: ZLR 41 · GB100 14 · FAILED_BREAK_LONG 7 · INITIATIVE_LONG 7 · GHOST 6 · DALTON_EDGE_SHORT 5 · **OPENING_DRIVE 5** · OPENING_ORR 2.

⚠️ **`blocked_by` הוא החוסם הראשון.** להסיר את `awaiting_release` **אינו** אומר ש-42 היו נכנסים.
בנוסף `RELEASE_ENTRY_GATE_V1` כובה כבר ב-08.09 18:02, ודוח-הבוקר מצא שמדודד הוא חסם **−$977.85**
בחלון B — כלומר הוא הסיר **מפסידים**.

### 3.5 · 🔴 השורה של M3

> **ב-10 הסשנים האחרונים נוצרו 7 מועמדי-פתיחה, 3 הגיעו לברוקר, ואף שער אינו המסיר-העיקרי —
> היצרן פשוט כמעט לא מייצר (0.7 מועמדים לסשן).** ארבעת הדגלים החשודים שקופים לפיד לחלוטין;
> המסיר היחיד שזוהה בשמו הוא **`honest skip today`** — מנוע-הפתיחה משבית את עצמו ליום שלם
> כשהבר הראשון שהוא רואה מאוחר מ-16:30 (3 פעמים ב-3 סשנים מכוסי-לוג, כולל 09.09 כולו).

---

## 4 · מה מוכן-להכרעה עם מספר, ומה עדיין לא מוכח

### ✅ מוכן-להכרעה — בטוח לפעול לפניו 16:30 היום

| # | הממצא | המספר | הפעולה הבטוחה |
|---|---|---|---|
| 1 | **הסולם אינו המנוף** | הטובה-ביותר `(2,2,1,0)`: **+$7.50 ב-B · −$1,041.25 ב-A**. לחוזה ב-B: `(1,2,1,1)`=−$5.12 מול `(1,1,0,0)`=−$6.09 | **לא לגעת בסולם.** ולא להסתמך על «−$250 מהגודל» של דוח-הבוקר — הוא מדד גודל, לא צורה |
| 2 | **ההשערה «מסחר ב-POC» מופרכת** | בתוך-הערך ב-B = **+$5.00 על 5 עסקאות**; מעבר ל-VA = **−$440.00 על 11** (27% ניצחון) | **לא לבנות שער «אל תיכנס ליד ה-POC»** — הוא היה מוחק +$778.75 מאוגוסט |
| 3 | **תיקון-הנחה: שער-המיקום דלוק** | `.env:367 DAYTYPE_LOCATION_GATE=1` · `location_gate.py` חי · חסם 9 בשווי −$451.38 ב-B | **לא «להדליק» אותו** — הוא כבר דלוק. כל דיון עליו מתחיל מכאן |
| 4 | **יצרני-הפתיחה לא נחסמים — הם לא מייצרים** | 7 מועמדים / 10 סשנים · 3 לברוקר · 4 הדגלים החשודים = 0 שורות-חסימה | **לא לכבות שער-פתיחה כלשהו** בציפייה ליותר עסקאות-פתיחה. זו אבחנה שגויה |

### ⚠️ לא-מוכח — אסור לפעול לפניו 16:30

| # | הפריט | למה לא-מוכח | הצעד הבא |
|---|---|---|---|
| 5 | **`CHASE-POC` כשער** | החתך יציב וחזק (A: 27/−$233.75 · B: 21/−$708.75; `TOWARD-POC` A: 24/**+$1,261.25**/75%), **אבל** בגרסה חסרת-הפרמטר הוא משאיר **2 עסקאות ב-B** — השבתה, לא סינון. גרסאות-הסף (3 נק׳ · 0.1 רוחבי-VA) נבחרו מ-~10 וריאנטים על 74 עסקאות = התאמה-בתוך-המדגם | **ריפליי לפי `LEARNING_DOCTRINE`** על סט-רגרסיה מלא, ואז דגל עם `measured:` — לא דגל היום |
| 6 | **תוויות `AT_VALUE`/`OUTSIDE_VA`** | POC-בכניסה שונה מהמיושב ב-**40/51** (A) ו-**16/23** (B); ה-VA המיושב מסווג הפוך לגמרי | לקבע הגדרת-ערך אחת ולמדוד אותה לפני שמישהו מתמחר עליה |
| 7 | **`honest skip today`** | זוהה ב-3 סשנים בלבד — כל טווח-הלוג. אין מפקד ל-10 סשנים | להאריך שמירת-לוג ולספור; זהו באג-הזנה/עלייה, לא החלטת-מסחר |
| 8 | **מודל-הריפליי עצמו** | «יעד-או-סטופ» בלבד: A $945 מול ברוקר $1,027.50 · B −$290 מול −$670 | מדרג סולמות, **לא** מתמחר אותם. אין להשתמש במספר בודד ממנו כתחזית |

### 🔴 והפריט שהחקירה הזו פתחה ולא סגרה

**קצב ה-`TOWARD-POC` קרס מ-47% מהעסקאות (24/51) ל-9% (2/23).** זה השינוי ההתנהגותי הגדול-ביותר
בין החלונות שאינו גודל ואינו סולם. **מה גרם לו — לא נבדק כאן.** זהו הפריט הבא בתור, והוא
חשוב יותר משלושת אלה: אם המכונה הפסיקה לקחת את הכניסות שהרוויחו את כל אוגוסט,
אף כיול של סולם או שער לא יחזיר את הכסף.

---

## 5 · נספח — פלט גולמי

כל המספרים הופקו 2026-09-10 08:12–08:35 IL מ-`postgresql://localhost/mems26` דרך `psycopg2`,
מ-`~/SierraChart_Data/v9_export/` ומ-`/tmp/backend.err.log`.
סקריפטים: `m_recon.py`, `m_recon2.py`, `m_recon3.py`, `m1_ladder.py`, `m1_ladder2.py`,
`m2_location.py`, `m2_sens.py`, `m3_opening.py`, `m_verify.py`, `m_final.py`
(בתיקיית-הפלט של הסשן).

### 5.1 · אימות סטופ-הכניסה ומקורות-ה-TPO

```
=== (a) initial_stop availability + does it bracket entry correctly? ===
cols: n, has_initial_stop
[(75, 39)]

-- bracket test with COALESCE(initial_stop, stop) as entry-time stop:
   ('LONG', 38, 38, 0)
   ('SHORT', 37, 0, 37)

-- decompose the failures: which half breaks (t1 side vs stop side)?
  dir,t1_ok,curstop_ok,initstop_ok,n = ('LONG', 38, 21, 38, 38)
  dir,t1_ok,curstop_ok,initstop_ok,n = ('SHORT', 37, 17, 37, 37)

=== (b) DECISIVE TPO TZ TEST: bars-derived IB (first 12 RTH bars) vs stored ===
  v9_tpo_history  IB matches bars-derived IB: 23/23
  v9_tpo_sessions IB matches bars-derived IB: 24/24

=== (b2) tpo_history intraday timeline vs bars, 2026-09-03 ===
   16:30  poc=7677.5 vah=7685.5 val=7670.75   RTH-range-so-far=(7704.25, 7718.0)   <-- carry-in
   17:00  poc=7715.5 vah=7723.25 val=7707.75  RTH-range-so-far=(7704.25, 7726.5)   <-- in range
   ...
   22:30  poc=7752.25 vah=7766.25 val=7718.25 RTH-range-so-far=(7698.25, 7766.25)
```

### 5.2 · M1 — ריפליי, אימות וטבלאות

```
(a) REPLAY VALIDATION — replay target-reached vs stored *_hit_ts
   A T1: replay=36  stored=30  n=51        B T1: replay=10  stored=9   n=24
   A T2: replay=26  stored=19  n=51        B T2: replay=7   stored=1   n=24
   A T3: replay=15  stored=4   n=51        B T3: replay=3   stored=0   n=24
   (replay uses the ORIGINAL stop and holds to 23:00 IL; the DB flag reflects the real
    managed trade, so replay >= stored is EXPECTED)

MODEL: ORIGINAL STOP held to session close
  WINDOW A  n=51  same-bar-decided=1 (2%)
    [calibration] model on each trade's REAL ladder $810.05 vs broker $1,027.50
    ladder                    SUM $  $/contract    T0/T1 $    T2/T3 $  c@T2/T3  fills@T2/T3
    (1,2,1,1) today 5c     3,845.75       15.08   1,375.70   2,470.05      102           48
    (2,2,1,0) 5c           2,277.00        8.93   1,477.60     799.40       51           29
    (2,3,0,0) 5c           2,114.50        8.29   2,114.50       0.00        0            0
    (3,2,0,0) 5c           1,579.50        6.19   1,579.50       0.00        0            0
    (1,1,0,0) Aug 2c         738.80        7.24     738.80       0.00        0            0
    -- A minus big-3 days (38 trades) --
    (1,2,1,1) today 5c     1,868.75        9.84     523.75   1,345.00       76           32
    (2,2,1,0) 5c             931.25        4.90     537.50     393.75       38           19
    (2,3,0,0) 5c             792.50        4.17     792.50       0.00        0            0
    (3,2,0,0) 5c             551.25        2.90     551.25       0.00        0            0
    (1,1,0,0) Aug 2c         268.75        3.54     268.75       0.00        0            0

  WINDOW B  n=24  same-bar-decided=2 (8%)
    [calibration] model on each trade's REAL ladder $-537.50 vs broker $-670.00
    (1,2,1,1) today 5c      -862.50       -7.19    -415.00    -447.50       48           12
    (2,2,1,0) 5c            -698.75       -5.82    -585.00    -113.75       24            8
    (2,3,0,0) 5c            -707.50       -5.90    -707.50       0.00        0            0
    (3,2,0,0) 5c            -755.00       -6.29    -755.00       0.00        0            0
    (1,1,0,0) Aug 2c        -292.50       -6.09    -292.50       0.00        0            0

MODEL: BE-after-T1 (T2/T3 legs go to breakeven once T1 prints)
  WINDOW A  n=51   [calibration] $945.05 vs broker $1,027.50
    (1,2,1,1) today 5c     3,195.75       12.53   1,375.70   1,820.05      102           41
    (2,2,1,0) 5c           2,154.50        8.45   1,477.60     676.90       51           26
    (2,3,0,0) 5c           2,114.50        8.29   2,114.50       0.00        0            0
    (3,2,0,0) 5c           1,579.50        6.19   1,579.50       0.00        0            0
    (1,1,0,0) Aug 2c         738.80        7.24     738.80       0.00        0            0
    -- A minus big-3 days (38 trades) --
    (1,2,1,1) today 5c     1,443.75        7.60     523.75     920.00       76           27
    (2,2,1,0) 5c             806.25        4.24     537.50     268.75       38           17

  WINDOW B  n=24   [calibration] $-290.00 vs broker $-670.00
    (1,2,1,1) today 5c      -615.00       -5.12    -415.00    -200.00       48           12
    (2,2,1,0) 5c            -607.50       -5.06    -585.00     -22.50       24            8
    (2,3,0,0) 5c            -707.50       -5.90    -707.50       0.00        0            0
    (3,2,0,0) 5c            -755.00       -6.29    -755.00       0.00        0            0
    (1,1,0,0) Aug 2c        -292.50       -6.09    -292.50       0.00        0            0

  ladder                   A SUM$     B SUM$        A+B  vs (1,2,1,1) in B  cost in A
  (1,2,1,1) today 5c     3,195.75    -615.00   2,580.75              +0.00        +0.00
  (2,2,1,0) 5c           2,154.50    -607.50   1,547.00              +7.50    -1,041.25
  (2,3,0,0) 5c           2,114.50    -707.50   1,407.00             -92.50    -1,081.25
  (3,2,0,0) 5c           1,579.50    -755.00     824.50            -140.00    -1,616.25
  (1,1,0,0) Aug 2c         738.80    -292.50     446.30            +322.50    -2,456.95

  same-bar (target AND stop in one bar) decided >=1 leg on 1/51 (A, 2%), 2/24 (B, 8%)
  legs marked to session close: A 11, B 3
  level fallbacks (missing t2/t3): A {'T3<-T2': 9, 'T2<-T1': 8}   B {'T2<-T1': 2, 'T3<-T2': 2}
```

### 5.3 · M2 — דליים, רגישות, וחתכים

```
WINDOW A 2026-08-01..2026-08-28   n=51   (no VA row: 0)
  entries judged against the 16:30 carry-in profile: 12
  as-of-entry POC differs from SETTLED POC by >25% of VA width: 40
  entries before the IB completed (<12 bars seen): 14
  ALL TRADES        AT_VALUE 18 +840.00 72% | MID_VA 10 +147.50 70%
                    EDGE_VA  12 +282.50 67% | OUTSIDE_VA 11 -242.50 36%   TOTAL 51 +1,027.50
  LOSERS ONLY       AT_VALUE  5 -187.50     | MID_VA  3 -195.00
                    EDGE_VA   4 -283.75     | OUTSIDE_VA  7 -501.25       TOTAL 19 -1,167.50
  IB overlay        not IB edge 43 +807.50 63% | IB_EDGE 8 +220.00 62%
  |d from POC|      VA-widths median=0.29 max=1.03 | points median=7.50 max=43.75

WINDOW B 2026-08-31..2026-09-09   n=23   (no VA row: 1)
  carry-in: 4 | POC disagreement: 16 | pre-IB: 9
  ALL TRADES        AT_VALUE  4  -65.00 50% | MID_VA  1  +70.00 100%
                    EDGE_VA   7 -237.50 43% | OUTSIDE_VA 11 -440.00 27%   TOTAL 23 -672.50
  LOSERS ONLY       AT_VALUE  2 -196.25     | EDGE_VA 4 -422.50
                    OUTSIDE_VA 8 -671.25                                  TOTAL 14 -1,290.00
  IB overlay        IB_EDGE 5 -117.50 40% | not IB edge 18 -555.00 39%
  |d from POC|      VA-widths median=0.46 max=3.00 | points median=8.50 max=36.25

SENSITIVITY 1 — VA width
  A: median=26.50 min=8.25 max=60.50  | <5pt: 0  <8pt: 0  n=51
  B: median=19.75 min=1.00 max=45.25  | <5pt: 1  <8pt: 1  n=23
  OUTSIDE_VA on a degenerate (<8pt) VA:  A 0 of 11   B 1 of 11 (-125.00)

SENSITIVITY 2 — buckets restricted to VA width >= 8pt
  A (51 of 51) unchanged.
  B (22 of 23): AT_VALUE 4 -65.00 | MID_VA 1 +70.00 | EDGE_VA 7 -237.50 | OUTSIDE_VA 10 -315.00

CROSS-CHECK on the SETTLED VA (v9_tpo_sessions CASH)  <-- reclassifies almost everything
  A: AT_VALUE 2 -73.75 50% | MID_VA 8 +722.50 88% | EDGE_VA 7 -93.75 43% | OUTSIDE_VA 34 +472.50 62%
  B:                       | MID_VA 5 +310.00 80% | EDGE_VA 9 -720.00 22% | OUTSIDE_VA  9 -262.50 33%

DIRECTIONAL CUT (as-of-entry POC, no look-ahead)
  A: CHASE-POC n=27 -233.75 win=52%  || TOWARD-POC n=24 +1,261.25 win=75%
  B: CHASE-POC n=21 -708.75 win=38%  || TOWARD-POC n= 2    +36.25 win=50%

CHASE-POC x COUNTER-EXTENSION
  A: TOWARD/WITH 19 +901.25 | TOWARD/COUNTER 5 +360.00 | CHASE/COUNTER 6 -45.00 | CHASE/WITH 21 -188.75
  B: TOWARD/WITH  1  +76.25 | CHASE/WITH    12  +33.75 | TOWARD/COUNTER 1 -40.00 | CHASE/COUNTER 9 -742.50

IMPLEMENTABLE CUTS (all inputs known at entry)
  rule = BLOCK these                          A n  A $blocked  A wr    A net  A kept | B n  B $blocked  B wr    B net  B kept
  [baseline A: n=51 net=$1,027.50]  [baseline B: n=23 net=$-672.50]
  CHASE-POC                                    27    -233.75   52%  1,261.25    24  |  21    -708.75   38%     36.25     2
  CHASE-POC AND counter-extension(as-of-entry)  5     -20.00   60%  1,047.50    46  |   8    -617.50   25%    -55.00    15
  CHASE-POC AND counter-ext(FULL DAY=lookahead) 6     -45.00   50%  1,072.50    45  |   9    -742.50   22%     70.00    14
  counter-extension only (as-of-entry)         13    +342.50   62%    685.00    38  |   9    -657.50   22%    -15.00    14
  CHASE-POC by more than 0.10 VA-widths        21    -450.00   43%  1,477.50    30  |  19    -840.00   32%    167.50     4
  CHASE-POC by more than 0.25 VA-widths        18    -403.75   39%  1,431.25    33  |  16    -487.50   38%   -185.00     7
  CHASE-POC by more than 0.50 VA-widths         9    -306.25   33%  1,333.75    42  |  11    -317.50   36%   -355.00    12
  CHASE-POC by more than 3 points              22    -481.25   41%  1,508.75    29  |  17    -662.50   35%    -10.00     6
  CHASE-POC by more than 5 points              16    -168.75   50%  1,196.25    35  |  16    -518.75   38%   -153.75     7
  CHASE-POC by more than 8 points              15    -225.00   47%  1,252.50    36  |  11    -280.00   36%   -392.50    12

AGREEMENT as-of-entry vs full-day extension: A 45/51, B 22/23  (the look-ahead is not load-bearing)

CANDIDATE RULE 'no entry WITHIN X of POC' (the hypothesis as stated) — it destroys August:
  X      A blocked   A $ removed   A net after  |  B blocked  B $ removed  B net after
  0.10        12        +576.25        451.25   |      2        +131.25      -803.75
  0.20        19        +795.00        232.50   |      5        -221.25      -451.25
  0.25        20        +778.75        248.75   |      6        -145.00      -527.50
  0.50        38      +1,042.50        -15.00   |     12        -355.00      -317.50
```

#### טבלת כל עסקאות חלון B עם ההקשר-הערכי (פלט גולמי)

```
id    date       hh:mm  dir   pattern                 entry      poc          VAL-VAH  d(pts)  d(VAw) bucket      IBe      pnl
873   2026-08-31 16:35  SHORT GB100                 7688.75  7725.00  7712.75-7753.75  -36.25   -0.88 OUTSIDE_VA  .      -8.75
875   2026-08-31 16:40  SHORT OPENING_DRIVE         7689.50  7725.00  7712.75-7753.75  -35.50   -0.87 OUTSIDE_VA  .    -100.00
877   2026-08-31 17:00  SHORT REACTIVE_SHORT        7689.50  7690.25  7682.50-7697.50   -0.75   -0.05 AT_VALUE    .     116.25
881   2026-08-31 17:10  SHORT None                  7682.50  7690.25  7682.50-7697.50   -7.75   -0.52 EDGE_VA     Y      40.00
885   2026-08-31 17:35  SHORT None                  7676.50  7689.50  7677.50-7696.25  -13.00   -0.69 OUTSIDE_VA  Y     -57.50
936   2026-08-31 21:15  LONG  ZLR                   7695.00  7687.25  7680.25-7691.75    7.75    0.67 OUTSIDE_VA  .     -55.00
942   2026-09-01 17:20  LONG  INITIATIVE_LONG       7660.25  7645.50  7643.25-7651.75   14.75    1.74 OUTSIDE_VA  .      55.00
948   2026-09-01 18:45  LONG  GB100                 7668.75  7660.25  7648.00-7668.25    8.50    0.42 OUTSIDE_VA  Y    -128.75
950   2026-09-01 19:35  SHORT INITIATIVE_SHORT      7643.75  7661.25  7652.00-7671.25  -17.50   -0.91 OUTSIDE_VA  .    -156.25
953   2026-09-02 17:15  LONG  INITIATIVE_LONG       7668.75  7650.00  7645.25-7654.75   18.75    1.97 OUTSIDE_VA  .     162.50
968   2026-09-02 19:40  SHORT ZLR                   7676.25  7677.50  7670.25-7691.25   -1.25   -0.06 AT_VALUE    .      15.00
971   2026-09-02 20:10  LONG  GHOST                 7673.25  7677.50  7672.25-7691.25   -4.25   -0.22 EDGE_VA     .      76.25
987   2026-09-03 20:20  SHORT ZLR                   7749.00  7754.75  7714.50-7759.75   -5.75   -0.13 EDGE_VA     .    -156.25
998   2026-09-04 16:55  LONG  ZLR                   7745.75  7742.75  7742.25-7743.25    3.00    3.00 OUTSIDE_VA  .    -125.00
1008  2026-09-04 18:05  SHORT INITIATIVE_SHORT      7717.00  7733.00  7724.00-7746.50  -16.00   -0.71 OUTSIDE_VA  .      13.75
1069  2026-09-04 19:25  LONG  INITIATIVE_LONG       7730.50  7722.00  7710.25-7735.25    8.50    0.34 EDGE_VA     Y      68.75
1073  2026-09-04 20:10  SHORT GB100                 7725.50  7730.75  7714.50-7735.25   -5.25   -0.25 MID_VA      .      70.00
1141  2026-09-04 22:00  LONG  INITIATIVE_LONG       7724.25  7720.50  7712.75-7731.50    3.75    0.20 AT_VALUE    .    -143.75
1224  2026-09-08 16:55  SHORT INITIATIVE_SHORT      7694.00  7703.25  7693.00-7713.50   -9.25   -0.45 EDGE_VA     .     -42.50
1231  2026-09-08 17:19  SHORT INITIATIVE_SHORT      7684.00  7697.00  7680.75-7704.75  -13.00   -0.54 EDGE_VA     .     -86.25
1262  2026-09-08 20:35  LONG  GHOST                 7697.75  7696.00  7688.25-7701.50    1.75    0.13 AT_VALUE    .     -52.50
1328  2026-09-09 19:05  LONG  VEGAS                 7643.25  7652.25  7643.75-7663.50   -9.00   -0.46 OUTSIDE_VA  Y     -40.00
1343  2026-09-09 20:55  LONG  BULL_FLAG_LONG        7652.50  7647.00  7634.50-7655.25    5.50    0.27 EDGE_VA     .    -137.50
```

### 5.4 · M3 — פתיחה

```
PART 1 — LIVE TRADES entered 16:30-17:30 IL
  WINDOW A   opening-window trades = 14
    OPENING producers : n=1   $=  -95.00   [('OPENING_ORR', 1, -95.0)]
    every other producer: n=13  $= 553.75
        ZLR 6 +227.50 | REACTIVE_LONG 2 +230.00 | HTLB 1 +83.75 | GB100 1 +73.75
        INITIATIVE_LONG 1 -47.50 | (none) 2 -13.75
  WINDOW B   opening-window trades = 9
    OPENING producers : n=1   $= -100.00   [('OPENING_DRIVE', 1, -100.0)]
    every other producer: n=8   $= 111.25
        INITIATIVE_LONG 2 +217.50 | REACTIVE_SHORT 1 +116.25 | (none) 1 +40.00
        GB100 1 -8.75 | ZLR 1 -125.00 | INITIATIVE_SHORT 2 -128.75

PART 2 — decisions feed, last 10 sessions
  raw rows=2571 across 10 files; DEDUPED candidates=747 (inflation 3.44x)
  rows per file: 08-27:280 08-28:209 08-31:639 09-01:180 09-02:142 09-03:349
                 09-04:304 09-07:91 09-08:200 live(09-09):177 [CAPPED ~200 => truncated]
  rows without candidate_id (fell back to pattern+dir+minute): 943

2a — OPENING-PRODUCER candidates
    generated (deduped) = 7 across 6 sessions
    by producer: {'OPENING_ORR': 2, 'OPENING_DRIVE': 5}
    producers that generated ZERO: ['OPENING_TEST_DRIVE', 'OPENING_PULLBACK_CONT']
    reached the broker = 3  [('OPENING_ORR','2026-08-27','822'),
                             ('OPENING_DRIVE','2026-08-31','875'),
                             ('OPENING_DRIVE','2026-09-08','1220')]
    blocked_by histogram (deduped): [('news_blackout', 2), ('direction_context', 1),
                                     ('direction_compass', 1)]
      2026-08-27 16:55 OPENING_ORR    LONG  routed=True  trade=822  blocks=[]
      2026-08-28 17:00 OPENING_DRIVE  LONG  routed=False trade=None blocks=['direction_context']
      2026-08-31 16:40 OPENING_DRIVE  SHORT routed=True  trade=875  blocks=[]
      2026-09-01 16:50 OPENING_DRIVE  LONG  routed=False trade=None blocks=['news_blackout']
      2026-09-01 16:55 OPENING_ORR    SHORT routed=False trade=None blocks=['news_blackout']
      2026-09-07 16:50 OPENING_DRIVE  SHORT routed=False trade=None blocks=['direction_compass']
      2026-09-08 16:40 OPENING_DRIVE  SHORT routed=True  trade=1220 blocks=[]

2b — ALL candidates first seen inside 16:30-17:30 IL
    generated (deduped) = 117 across 10 sessions ; reached the broker = 27
    blocked_by (deduped): awaiting_release 42 | direction_compass 11 | entry_location_quality 7
      duplicate_bar_ts 6 | dalton_intent:stand_down 5 | lsma_flat 4 | fhb 4 | cold_start_guard 2
      news_blackout 2 | entry_not_confirmed 2 | extreme_chase_guard 2 | cont_trend_filter 1
      direction_context 1 | pattern_stop_cooldown 1 | location_gate 1
    by pattern: ZLR 41 | GB100 14 | FAILED_BREAK_LONG 7 | INITIATIVE_LONG 7 | GHOST 6
      DALTON_EDGE_SHORT 5 | OPENING_DRIVE 5 | DALTON_EDGE_LONG 4 | FAILED_BREAK_SHORT 4
      TREND_STEP 4 | VA_FADE_LONG 4 | HTLB 3 | REACTIVE_SHORT 3 | OPENING_ORR 2 | VA_FADE_SHORT 2

2c — blocked by exactly ONE gate (82 candidates)
    awaiting_release 42 | direction_compass 10 | entry_location_quality 7
    dalton_intent:stand_down 5 | lsma_flat 4 | fhb 3 | cold_start_guard 2 | news_blackout 2
    entry_not_confirmed 2 | extreme_chase_guard 2 | cont_trend_filter 1 | direction_context 1
    pattern_stop_cooldown 1
    awaiting_release by session: 08-27:3 08-28:8 08-31:1 09-01:7 09-02:6 09-03:3 09-04:6 09-07:2 09-08:6
    (RELEASE_ENTRY_GATE_V1 was switched 1->0 on 2026-09-08 18:02 IL)

BACKEND LOG CENSUS  /tmp/backend.err.log  span 2026-09-06 .. 2026-09-10  (3 trading sessions only)
    OPENING_FIRST_TRADE_STRICT        3   sessions: ['2026-09-07', '2026-09-08']
    OPENING_DRIVE_SKIP                0   (.env:705 OPENING_DRIVE_SKIP_V1=0 — consistent)
    OPENING_PATTERN_SKIP              0   (unset — consistent)
    OPENING_ENTRY DRIVE               2   sessions: ['2026-09-07', '2026-09-08']
    OPENING_ENTRY ORR / TEST_DRIVE / PULLBACK   0 / 0 / 0
    honest skip today                 3   sessions: ['2026-09-08', '2026-09-09']

  2026-09-07 16:40:05 OPENING_FIRST_TRADE_STRICT held DRIVE SHORT — last bar did not confirm SHORT
  2026-09-07 16:45:02 OPENING_FIRST_TRADE_STRICT held DRIVE SHORT — last bar did not confirm SHORT
  2026-09-07 16:50:03 OPENING_ENTRY DRIVE SHORT entry=7714.00 stop=7716.75 t1=7709.88 (live-eligible)
  2026-09-08 16:35:05 OPENING_FIRST_TRADE_STRICT held DRIVE SHORT — only 2 bars < 3 — confirmation bar required
  2026-09-08 16:40:08 OPENING_ENTRY DRIVE SHORT entry=7701.00 stop=7716.00 t1=7678.50 (live-eligible)
  2026-09-08 16:56:42 OPENING_ENTRY: first seen bar 1788875700 is past 09:30 — honest skip today
  2026-09-08 17:19:46 OPENING_ENTRY: first seen bar 1788876900 is past 09:30 — honest skip today
  2026-09-09 16:58:24 OPENING_ENTRY: first seen bar 2026-09-09 13:55:00+00:00 is past 09:30 — honest skip today

NOTE on #1220: routed on 09-08 but it is NOT one of the 75 broker-priced rows —
  (1220, 'live', 'CLOSED', pnl_sierra=None, pnl_usd=None, 'SIERRA_FLAT', 'OPENING_DRIVE', entry_ts=None)
```
