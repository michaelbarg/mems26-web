# CC — בילד-בוקר חכם לפני פתיחה (מייקל ~04:15 ET, 2026-07-22)

**מחליף-מרחיב את CC_LIVE_PREP_2026-07-22.md** לאור מחקר-בוקר (2 סוכני-קוד + היסטוריה) + 4 פסיקות-מייקל.
**חלון: עד ~09:00 ET (בילד+אימות+RULED) → ריסטארט-אחד → שער-פתיחה → מייקל מחמש. אפס-קוד אחרי 09:30 ET.**

## פסיקות-מייקל הבוקר (מחייבות)
1. **המיקוד = מיקום-מחיר לפי סוג-יום + סוג-פתיחה** — לא נעילת-כיוון. ההפסדים של אתמול (4 שורטים ‎−$139)
   = כניסות **אמצע-value**; התיקון הוא שער-מיקום, לא שער-כיוון.
2. **סוג-הפתיחה = כלי-הכסף-הגדול בפתיחה** ("יכול להיות הכלי שמכניס הכי הרבה כסף") — היפוך-בפתיחה לפי
   סיווג-הפתיחה חייב להיות סחיר (16.07: רכיבה-עם-היום מ-09:30 = 100 נק' = $2,000 ל-4 חוזים).
3. **DAYTYPE_LOCATION_GATE v2 נבנה לפני פתיחה** (לא v1-כמו-שהוא).
4. **מיפוי-דלטון לסוג-פתיחה מאושר:** Open-Drive/Test-Drive → ודאות-כיוונית (רק עם-הדרייב; היפוך-בפתיחה
   שמאושר = כניסה מוקדמת) · Open-Rejection-Reverse → עסקת-היפוך · Open-Auction-In/Out → אין-יתרון, המתן.
5. **אפס-טריילינג.** "טריילינג שורף עסקאות — בשביל זה יש מערכת 6." רוכב-הרחבה = יעדים מבניים קבועים
   עד T4, ניהול ע"י System 6 (protective). שום לוגיקת-טריילינג חדשה.

## ממצאי-מחקר שמעצבים את הבילד (מאומתים file:line ע"י סוכנים)
- `location_gate.py` v1 **קיים** וכבר חוסם mid-value/counter-expansion — כבוי (`DAYTYPE_LOCATION_GATE=0`).
  S4 עובר את אותו gateway כמו S2 (אין bypass) — השערים keyed על pattern-family ומכירים ZLR/TT/GB100/TLB.
- `opening_type_gate.py::decide` (L82-106) **כבר מיישם** את דוקטרינת-הפתיחה (with-drive/reversal/hold).
- פאנל-סוג-פתיחה **קיים** (opening_panel endpoint + OpeningTypePanel.tsx mounted) — אבל קורא `classify_replay`
  בעוד השערים קוראים `get_live_day_type` (הפיצול שמייקל ראה). `/api/v9/day_type/live` כבר קיים לזה.
- **4 מימושי-opening-type מקבילים** (fragmentation): `opening_detector_v2.py` (קנוני) · `detector.py`
  (ה-live state-machine — יכול לחלוק!) · `open_type.py` (טקסונומיה-4 יתומה) · `opening_detector.py` (טסט-בלבד).
- סטופ-S4 כבר מבני אבל מעוגן **לבר-בודד** (`stop_anchors.yaml:80` breakout_bar/window:1), לא לקיצון-המבנה.
- T1 היום = R-multiple/MFE-points/day-level — **לא** סוף-מבנה; `T1_STRUCTURE_END_V1`+`STOP_STRUCTURE_EXTREME_V1`
  לא קיימים בקוד (docs בלבד). `.env` מכיל `STOP_WINDOW_COMPLETED_V1=1` שדווח אינרטי — נקה או בנה.

## סדר-ביצוע (עדיפות ללייב; דלג ל-B1 אם הזמן קצר)

### B1 🔴 — DAYTYPE_LOCATION_GATE **v2** (פסיקה 3: לפני פתיחה)
בסיס = `location_gate.py` v1 (אל תשכתב — הרחב). מוסיף:
- **בדיקת-probe מכנית** (מפרט ב-CC_T1_STRUCTURE_END §B): REV בקצה מותר רק אחרי probe — בר חדר את
  הקצה (VAH/VAL) **ונסגר חזרה** מתחתיו/מעליו; בלי probe = BLOCK.
- **S4 עובר את השער במלואו** (כבר במסלול — ודא אין exemption), **mid-value נגד-הרחבה = BLOCK תמיד**.
- Fixtures חובה: ‎#449/#452/#456 (ZLR SHORT על POC) = BLOCK · 19:55 VAH-test = ALLOW · S4 mid-POC SHORT
  על Variation-UP = BLOCK. טסטים ירוקים **עם ‎.env טעון** (לקח §0 אתמול: טסט בלי env = מערכת פיקטיבית).
- הדלקה: `DAYTYPE_LOCATION_GATE=1` + RULED (פסיקת 22:18+היום מחליפה כיבוי-07-20).

### A 🔴 — מקור-יחיד: סוג-יום + סוג-פתיחה (החיווט המדויק מהאודיט)
1. `opening_panel` (daytype_classify_routes.py L287-368): גזור `live`/`effective_day_type` מ-**`get_live_day_type()`**
   (הסמכות של השערים); `classify_replay` נשאר **audit בלבד** בשדה `cross_check:{match,audit_label,live_label}`;
   None → `"—"/FORMING` בכנות (Rule 1, בלי fallback ל-Normal).
2. **opening_type קנוני = `opening_detector_v2`** בכל מקום: החלף את קריאת `detector.py` ב-state-machine
   או תעד-פער אם מסוכן היום; `open_type.py` (4-type) — סמן legacy, אל תציג ב-UI.
3. TopBar == opening_panel.live == `/day_type/live` — אותה תווית ב-3 (curl-הוכחה).

### O 🟠 — סוג-פתיחה סחיר + פאנל (פסיקות 2+4)
1. **שדה-stance קנוני**: הוסף ל-`daytype_playbook.yaml` בלוק `opening_stance:` לפי המיפוי המאושר
   (DRIVE/TEST_DRIVE→DIRECTIONAL · REJECTION_REVERSE→REVERSAL · AUCTION_IN/OUT→NO_EDGE) והצג אותו
   ב-opening_panel (המקור: `opening_type_gate.decide` — חשוף read-only, אל תשכפל לוגיקה).
2. פאנל: הוסף **"אילו תבניות ירו בפועל"** (join: eligible-patterns × `v9_five_min_setups` +
   `zlr_detected`/`hfe_detected` מ-woodies) — מייקל רואה סיווג-פתיחה + תבניות-מתאימות + מה-ירה.
3. **ודא היפוך-בפתיחה סחיר**: `opening_type_gate` ב-ALLOW-reversal לא נחסם ע"י dead-zone השעה-הראשונה
   (Task#3) — אם נחסם, תעד את החוסם המדויק ועצור לפסיקה (לא לתקן-פרוץ לבד).

### E 🟠 — `LSMA_FLAT_GATE_V1=1` (בנוי — הדלקה+RULED)
סמנטיקת-מייקל ל-RULED: "מחיר תקוע = אנרגיה נצברת; כניסה מוקדמת = הפסד". fixtures ‎#449/452/456=BLOCK, ‎#444=pass.

### F 🟠 — הידרציה מתאפסת ב-09:30 ET
אתמול cap אפקטיבי $675 במקום $800. טסט: restart לפני 09:30 → מונים=0/pre-session; אחרי — עסקאות-היום בלבד.

### C+D 🟡 (אם נשאר זמן; אחרת אחרי-שוק) — T1 סוף-מבנה + סטופ קיצון-מבנה
לפי CC_T1_STRUCTURE_END (אל תשכתב). אותו מזהה-מבנה לשניהם. **בלי טריילינג** (פסיקה 5).
נקה גם את `STOP_WINDOW_COMPLETED_V1` האינרטי (בנה או הסר מ-env — בלי אשליית-דגל).

### R 🟡 — רוכב-הרחבה: **מפרט בלבד היום** (פסיקות 2+5)
זיהוי-הרחבה+ודאות → כניסה-עם-היום, ראנר עד **T4 מבני קבוע**, System-6 מנהל, **אפס-טריילינג**,
קירוב-מימוש = פעולת-System-6 (protective), לא לוגיקה חדשה. דגל-OFF, סים לפני לייב. לא לבנות היום.

## שער-פתיחה (לפני שמייקל מחמש)
```
python3 scripts/flag_guard.py                      # PASS חובה
curl /api/v9/day_type/live · /day_type/opening_panel  # אותה תווית + stance
DAYTYPE_LOCATION_GATE=1 · LSMA_FLAT_GATE_V1=1 · fixtures ירוקים עם env
MEMS26_MODE=live · LIVE_TRADING_ARMED=1 · is_sim=0 · position=0 · פיד טרי
```
חוק-5 לכל שלב → LIVE_CHANNEL. **cursor מאמת כל סעיף** (אף סוכן לא סוגר את-של-עצמו). cowork: RULED + ריסטארט + שער.
