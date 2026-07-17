# N9 — מטריצת-הדמיה סוג-יום × תבנית (2026-07-17)

שער-הפלייבוק בבידוד (כל שער-סיכון אחר כבוי) דרך ה-`route_setup` האמיתי. כל תא נבדק מקצה-לקצה: SKIP חייב חסימה `daytype_playbook`; KEEP חייב לעבור + לעמוד בבדיקות-ניהול (סטופ-צד-נכון, סולם-מונוטוני, BE-אחרי-T1, גודל FULL=3/REDUCED=2).

**סיכום:** 🟢 PASS · 104 תאים · KEEP=61 · SKIP=43 · כשלי-ניהול=0 · מקרי-קאונטר-טרנד 6/6 · אי-התאמות=0

| תבנית | Trend Normal | Trend DD | Variation | Normal | Neutral Center | Neutral Extreme | Nontrend | Nonconviction |
|---|---|---|---|---|---|---|---|---|
| **ZLR** | ✅ | ✅ | ✅ | ½ | · | · | · | · |
| **TLB** | ✅ | ✅ | ✅ | ½ | · | ½ | · | · |
| **TT** | ½ | ½ | ½ | ½ | · | · | · | · |
| **GB100** | ½ | ½ | ½ | ½ | · | · | · | · |
| **INITIATIVE** | ✅ | ✅ | ✅ | ½ | · | · | · | · |
| **FLAGS** | ✅ | ✅ | ✅ | ½ | · | ½ | · | · |
| **HTLB** | ✅ | ✅ | ✅ | ½ | ½ | ½ | · | · |
| **VEGAS** | · | · | ½ | ✅ | ✅ | ✅ | · | · |
| **GHOST** | · | · | ½ | ✅ | ✅ | ✅ | · | · |
| **FAMIR** | · | · | ½ | ✅ | ✅ | ✅ | · | · |
| **DBDT** | · | ½ | ½ | ✅ | ✅ | ✅ | · | · |
| **REACTIVE** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | · | · |
| **HNS** | ½ | ½ | ✅ | ✅ | ✅ | ✅ | · | · |

מקרא: ✅=KEEP-FULL עבר · ½=REDUCED עבר · ·=SKIP (נחסם כצפוי) · ❌=אי-התאמה

## מגבלה מודעת
זו הדמיית-**לוגיקה** (נתיב-הקוד האמיתי, ביצוע מנוטרל). שכבת-ה-fill על Sierra-סים (op=PLACE אמיתי לחשבון-סים, is_sim=1) היא ההמשך — דורשת stack רץ ולא נכללת כאן.
## N9-hot — שכבת-fill על Sierra-סים (E2E, is_sim=1)

| סוג-יום | תבנית | sizing | ירי | entry | זוגות-OCO | MODIFY×all | FLATTEN | journal | v9_trades | פסק |
|---|---|---|---|---|---|---|---|---|---|---|
| Trend_Normal | ZLR | full | FIRED_DIRECT | 0 | ❌ | ❌ | ✅ | ✅ | False | ❌ |

שאר תאי-ה-KEEP חולקים נתיב-fill זהה (command_from_setup→op=PLACE→OCO) — **✅ נתיב-משותף** מכוח תא-ההוכחה של סוג-היום שלהם. שליליים (SKIP/קאונטר) מכוסים במטריצת-הלוגיקה (43+6).

## N9-hot — שכבת-fill על Sierra-סים (E2E, is_sim=1)

| סוג-יום | תבנית | sizing | ירי | entry | זוגות-OCO | MODIFY×all | FLATTEN | journal | v9_trades | פסק |
|---|---|---|---|---|---|---|---|---|---|---|
| Trend_Normal | ZLR | full | FIRED_DIRECT | 4 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

שאר תאי-ה-KEEP חולקים נתיב-fill זהה (command_from_setup→op=PLACE→OCO) — **✅ נתיב-משותף** מכוח תא-ההוכחה של סוג-היום שלהם. שליליים (SKIP/קאונטר) מכוסים במטריצת-הלוגיקה (43+6).

## N9-hot — שכבת-fill על Sierra-סים (E2E, is_sim=1)

| סוג-יום | תבנית | sizing | ירי | entry | זוגות-OCO | MODIFY×all | FLATTEN | journal | v9_trades | פסק |
|---|---|---|---|---|---|---|---|---|---|---|
| Trend_Normal | ZLR | full | FIRED_DIRECT | 4 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Trend_DD | ZLR | full | FIRED_DIRECT | 4 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Variation | ZLR | full | FIRED_DIRECT | 4 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Normal | ZLR | full | FIRED_DIRECT | 4 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Neutral_Center | HTLB | full | FIRED_DIRECT | 4 | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| Neutral_Extreme | TLB | full | FIRED_DIRECT | 4 | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |

שאר תאי-ה-KEEP חולקים נתיב-fill זהה (command_from_setup→op=PLACE→OCO) — **✅ נתיב-משותף** מכוח תא-ההוכחה של סוג-היום שלהם. שליליים (SKIP/קאונטר) מכוסים במטריצת-הלוגיקה (43+6).

### ממצא-N9 ❗ (S-13): צירוף-ברקטים לסירוגין נכשל
בחלק מהמחזורים ה-entry מתמלא אך **אפס הוראות-OCO מצורפות** (qty=2/4, working=0) — פוזיציה-עירומה עד FLATTEN.
נצפה: Neutral_Center/HTLB · Neutral_Extreme/TLB · הוכחת-REDUCED (2c). ‏ZLR-full×5 צירף תקין (8/8).
חשד: מיצוי/זיהום-סלוטים ב-DLL במחזורי-ירי-מהירים-עוקבים (state cap 10, ניקוי-איטי?) — **לחקירת-DLL (cc/dev)**.
בלייב זה = כניסה-בלי-סטופ ⇒ ה-S6 naked-ALERT הוא הרשת. REDUCED sizing עצמו הוכח (commanded=2, filled=2 ✓).
+ ‏EOD_FLATTEN_V1=0 זמנית לחלון-הסים (מבטל-מיידית ברקטים מחוץ-RTH) — שחזור ב-N6 (נוסף לפרוטוקול).
