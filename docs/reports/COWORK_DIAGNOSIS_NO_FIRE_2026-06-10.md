# אבחון Cowork — למה המערכת לא ירתה היום (2026‑06‑10)

**מסקנה: 0 trades. הסיבה אינה באג בודד אלא שרשרת‑חוסמים** לאורך ה‑pipeline. כל שורש אומת ע"י Cowork (raw — קוד/DB/build‑status), לא הסתמכות על CC.

---

## שרשרת‑הכשל (לפי סדר ה‑pipeline)

### 1. פיד — woodies_5min עם ts עתידי (I‑18) · אומת
ברי‑woodies מתויגים ~5.5 שעות **בעתיד** (בר אחרון 22:40 IDT=15:40 ET בעוד 10:05 ET). פוגע בחלונות‑זמן (recency, חלון‑RTH של day_type) ובזיהוי. **חשד מרכזי לשורש‑משותף** של גם ה‑day_type וגם ה‑ZLR‑שלא‑זוהה.

### 2. S1 — סיווג יום: שתי תקלות
- **2א · תזמון (התקלה החוזרת):** day_type=UNKNOWN רוב הבוקר, סוּוַּג רק מאוחר (לכיוון IB‑lock@60דק'), **לא ב‑30דק'**. שורש: ה‑provisional day_type (מ‑`DECISION_MATRIX`, opening_type×IB) מחווט ל‑S2 (`five_min_system`) אבל **לא ל‑S4** (אומת: grep ב‑`woodies_system.py` ל‑provisional/DECISION_MATRIX = ריק). → S4 חסום auth שעה ראשונה.
- **2ב · דיוק:** סוּוַּג "Normal", אבל `decision_matrix.py`: **OPEN_DRIVE × כל IB = Trend_Normal**. אז הסיווג שגוי (כנראה סוּוַּג מ‑opening_type לא‑יציב בפתיחה — ORR×WIDE→Normal — ואין **intraday‑reclass** כשה‑opening_type התייצב ל‑OPEN_DRIVE).

### 3. A7 / `pre_fire_validator` — `T2=None` TypeError · אומת · **החוסם הדומיננטי**
ה‑T2=None שהוכנס באופציה‑1 (יעדי‑CCI‑cross נדחים) **לא חוּוט דרך ה‑validator** → monotonicity check `entry<t1<t2` עם t2=None → **TypeError** → `r_t1_gate=null` → `ready_to_route=False` → **לא יורה**. זה מה שראינו ב‑build‑status (TLB Armed, r_t1=null). **רוב היום עבר לפני התיקון** (`832174e`). **רגרסיה ישירה מאופציה‑1** — לקח "wire the full decision pipeline". 🔴 עדיין **חסר טסט‑רגרסיה**.

### 4. `day_type_matrix="lookup error"` — key‑mismatch · אומת בקוד
`backend/v9/systems/woodies/day_type_gate.py:92` עושה `self._matrix[(pattern_id, day_type)]` — **גישה‑ישירה ללא alias/`.get`** (למרות docstring "Never raises"). המטריצה (`config/day_type_matrix.yaml`) ממופתחת בקודי‑Table‑B (`NV`...) בעוד המכונה פולטת שמות‑מלאים (`Variation`...) → `KeyError`. חוסם את `day_type_matrix` gate → `ready_to_route=False`. (חוסם **גם אחרי** תיקון A7.)

### 5. S4 dedup — ~200x ירי/בר · אומת חלקית
dedup חלקי קיים (`_last_bar_ts_for_count` ל‑bar_count) אך לא על נתיב‑הירי → כשהמערכת *כן* תירה, תירה עשרות‑מאות פעמים. **לא סיבה ל"לא ירה"**, אלא סיכון‑מימוש כשייפתח.

### 6. עכשיו (חי) — `trend_state=GRAY` · תקין, **לא באג**
כרגע כל S4 חסום ב‑A1 כי אין מגמה (CCI איבד כיוון). זו התנהגות **נכונה** — לא לתקן.

---

## פר מערכת
| מערכת | מצב היום | חוסם עיקרי |
|---|---|---|
| **S1** | סיווג מאוחר (UNKNOWN→מאוחר) + שגוי ("Normal" במקום Trend_Normal) | provisional לא‑מחווט ל‑S4 · אין reclass · (future‑ts?) |
| **S2** | — (פר‑5דק', day_type provisional מחווט) | day_type accuracy · A7 TypeError (משותף) |
| **S4** | Armed אך 0 routable | **A7 T2=None TypeError** (רוב היום) + **matrix lookup error** + day_type מאוחר/שגוי |

## שורה תחתונה
המערכת לא ירתה בגלל **שרשרת**: future‑ts → day_type מאוחר+שגוי → **A7 T2=None TypeError (הדומיננטי, רוב היום)** → matrix lookup‑error. ה‑A7 (רגרסיה מאופציה‑1) חסם גם setups תקפים (ה‑ZLR/TLB שראית **כן זוהו** — אך נחסמו ב‑routing). חלק מ‑0‑trades לגיטימי (GRAY עכשיו, מעט setups נקיים), אבל **הבאגים מנעו ניתוב גם של מה שכן נמצא**.

## מצב‑תיקונים
- ✅ A7 (`832174e`) — תוקן (מאוחר), 🔴 חסר טסט‑רגרסיה.
- 🔴 פתוחים (מאומתי‑שורש, ממתינים לדוח‑CC + אישור Michael): matrix alias (NV↔Variation) · provisional→S4 · accuracy/reclass · dedup · future‑ts (I‑18).

*(אבחון Cowork חי. מקור: woodies_system / day_type_gate:92 / decision_matrix / v9_day_type_state / build‑status. הזרימה: דוח‑CC → הצלבה → אישור → תיקון.)*
