# CC — אבחון‑חי (DIAGNOSE‑ONLY) · חוסמי‑ניתוב S4/TLB + ZLR שלא זוהה + future‑ts (2026‑06‑10, RTH פתוח)

> פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`. **אבחון בלבד — אל תתקן.** זה נוגע ל‑classification/market‑data/targets (risk‑surface + §7a) → **strategic‑stop: דווח שורש + פתרון‑מוצע, חכה לאישור Michael לפני שינוי.** RTH פתוח — נצל את המצב‑החי.

## ⛔ דרישה (Michael) — דוח‑אבחון כתוב חוסם כל תיקון
אמרת "סיימתי אבחון" — אבל **אין דוח‑אבחון committed** (Cowork בדק: `PATTERN_DIAG_2026-06-10` הוא ריצה‑מדלגת מ‑08:08 CT לפני‑RTH; אין קומיט/דוח חדש מאז `832174e`). לפי **Rule 5 + Contract §C**: "סיימתי" בלי דוח‑כתוב + פלט‑גולמי = **לא נחשב**.

**לפני כל תיקון/קומיט — הגש `docs/reports/DIAGNOSE_S4_ROUTE_BLOCKERS_2026-06-10.md`** עם טבלת‑Rule‑5 לכל 4 הפריטים: `ממצא · שורש (file:line + פלט‑גולמי) · רגרסיה‑מאיזה‑commit · פתרון‑מוצע · סיכון` + סעיף **NOT‑DONE**.

**Cowork כבר אימת 2 שורשים — הדוח חייב לכלול את ה‑raw שלהם (ולאשר/לסתור):**
1. **`day_type_matrix="lookup error"` = key‑mismatch:** `backend/v9/systems/woodies/config/day_type_matrix.yaml` משתמש בקודי‑Table‑B (`NV`...), אבל המכונה פולטת שמות‑מלאים (`Variation`...) → `Variation ≠ NV`. הדבק traceback + המפתחות בקובץ.
2. **`day_type accuracy`:** `decision_matrix.py` → `OPEN_DRIVE × כל IB = Trend_Normal`, אז "Normal" **שגוי** (כנראה סוּוַּג מ‑ORR מוקדם, בלי reclass כשה‑opening_type התייצב). הדבק את הסיווג‑בפועל + opening_type ב‑ts‑הסיווג.

**אין תיקון · אין קומיט · עד שהדוח מוגש → Cowork מצליב → Michael מאשר.**

## ראיה‑חיה (build‑status, TLB · 🟡 Armed · Michael 06‑10)
```
detection pattern_specific = True ✓
stage_a1 day_type_gate = Variation ✓   (db, <1s)
targets_stop stop_price = 7381.75 ✓ · targets = 7400.00 ✓
targets_stop r_t1_gate = null ✕   (required ≥1.0, in_memory 4m)
targets_stop day_type_matrix = "lookup error" ✕   (required: allowed, inspector_eval)
exit_rules ready_to_route = False ✕   → לא יורה
```
ועוד (אומת ע"י Cowork ב‑raw היום): day_type היה **UNKNOWN** רוב הבוקר (רק 1 שורת Variation) ואז סוּוַּג ל‑Variation · woodies_5min בעלי **ts עתידי** (בר אחרון 22:40 IDT=15:40 ET בעוד עכשיו 10:05 ET — I‑18 חי) · **ZLR שראית לא זוהה** (`zlr_detected=0`).

## מה לאבחן (כל אחד: שורש + ראיה גולמית + פתרון‑מוצע — בלי לבצע)

### 1. 🔴 `day_type_matrix = "lookup error"` (חוסם ready_to_route)
- **השערה ראשית — key‑mismatch:** ה‑day_type machine פולט `"Variation"`, אבל `config/day_type_matrix.yaml` / `day_type_gate.py` מצפים ל‑`"NV"` / `"Normal Variation"` (Table B). אמת: מה הערך המדויק שמגיע ללוקאפ, ומהם המפתחות בקובץ. הדבק את ה‑traceback/לוג של ה‑"lookup error".
- **רגרסיה?** האם זה נשבר ב‑FIX‑C (`88aa189`, formula/build_pct ב‑woodies_inspector) או בחיווט‑day_type? `git log -p` על `woodies_inspector.py`/`day_type_gate.py`.

### 2. 🔴 `r_t1_gate = null` (= I‑3 חי, לא סגור!)
- עם stop=7381.75 ו‑target=7400, ה‑R:R אמור להיות מחושב (לא null). **למה r_t1=null?** הזרם: היכן ה‑inspector מחשב `r_t1`, והאם הוא קורא את ה‑T1 מה‑`fire_setup` (שעבר חיווט ב‑Phase‑1 `6c58d05`/`11425c2`). השערה: ה‑T1‑החדש (סולם) לא מגיע לשדה‑r_t1 ב‑inspector → null.
- **חשוב:** ה‑unit‑tests של CC עברו (10 ירוקים) אבל ה‑inspector‑החי מראה r_t1=null → **הטסטים לא תפסו את הרגרסיה**. זה מאשר את ה‑NO‑GO של I‑3.

### 3. 🟡 ZLR שלא זוהה + future‑ts (I‑18)
- ה‑woodies_5min עם ts עתידי (~5.5h). **האם ה‑future‑ts שובר את הזיהוי ו/או את חלון‑day_type@30דק'?** אמת: באיזה ts אמיתי הופיע ה‑ZLR שראית, ולמה `zlr_detected=0` (DLL לא סימן? Python‑fallback? trend GRAY/A1?). מקור ה‑future‑ts: DLL/bridge/TZ/Globex‑leak (כמו FIX‑3B אבל בטבלה).
- האם זה מחובר ל‑day_type=UNKNOWN של הבוקר?

## פלט נדרש (Rule 5)
טבלה: `ממצא · שורש (file:line + raw) · רגרסיה‑מאיזה‑commit? · פתרון‑מוצע · סיכון`. **אל תבצע תיקון** — חכה לאישור Michael (זו לוגיקת‑classification/targets/market‑data).

## מה Cowork יאמת
- ה‑raw של ה‑"lookup error" + הערך‑מול‑מפתחות (Variation vs NV).
- היכן r_t1 הופך null (קוד + ערך‑חי).
- האם החוסמים הם רגרסיה מ‑`6c58d05`/`88aa189`.

---

# ✅ אבחון בוצע (CC) + הצלבת‑Cowork → תוכנית‑תיקון מתועדפת (2026‑06‑10)
**מצב‑חי כרגע:** S4 כל 9 חסום ב‑A1 כי `trend_state=GRAY` (אין מגמה) — **זה תקין, לא באג** (אל "תתקן" את A1). S1 סיווג `Normal`. 0 trades. הבאגים שחסמו ירי **לאורך היום**:

### 0. ✅ A7 `T2=None` TypeError — תוקן (`832174e`) · אומת ע"י Cowork
- `pre_fire_validator.py` עכשיו מדלג monotonicity כש‑T2=None. **זה היה ה‑`r_t1=null`/`lookup error` שראינו.** **זו רגרסיה מאופציה‑1** (ה‑T2=None שהוכנס לא חוּוט דרך ה‑validator) — לקח **"wire the full decision pipeline"**.
- 🔴 **חסר טסט‑רגרסיה:** הוסף טסט anti‑tautological — `req.t2_price=None` → validator **עובר** (לא TypeError) ו‑`ready_to_route` יכול להיות True. *(revert→RED: חוזר ל‑TypeError.)* בלי זה הרגרסיה תחזור.

### 1. 🔴 S4 dedup — דיטקטורים יורים ~200x/בר (CC) — **אמת לפני שתבנה**
- **הצלבת‑Cowork:** dedup **חלקי כבר קיים** ב‑`woodies_system.py` (`_last_bar_ts_for_count` ל‑bar_count + הערה על per‑pattern dedup keyed bar_ts). **אל תשכפל.** קודם הדבק raw שמראה **היכן** ה‑200x קורה בפועל (detection? fire/route?), ואז הוסף `is_new_bar` guard בנקודה הנכונה (כמו S2), single‑source. דחוף — אחרת ירי כפול כשהמערכת תירה.

### 2. 🔴 provisional day_type ל‑S4 (day_type@30דק' במקום IB‑lock@60) — **אומת חסר**
- **הצלבת‑Cowork (grep ריק):** ב‑`woodies_system.py` אין `provisional`/`DECISION_MATRIX`/`day_type_machine`. S2 (`five_min_system`, FIX‑1) כבר מחשב provisional מ‑`opening_type × IB` דרך `DECISION_MATRIX`. **חווט את אותו מקור ל‑S4** (לא להמציא חדש) → S4 מקבל day_type@30דק'. **זה השורש של התקלה‑החוזרת** (day_type=UNKNOWN ב‑30דק').

### 3. 🔴 day_type accuracy — Michael: "Normal" שגוי
- בדוק את ה‑`DECISION_MATRIX`: `opening_type` (היום OPEN_DRIVE) × IB‑width → מה **אמור** לצאת? OPEN_DRIVE בד"כ → **Trend**, לא Normal. אמת את הסיווג מול האפיון (S1 spec). **זו לוגיקת‑classification → strategic‑stop + אישור Michael לפני שינוי.**

## דיסציפלינה לכל תיקון
flag‑gated אם trading‑logic · single‑source‑of‑truth (אל תשכפל dedup/provisional) · טסט‑רגרסיה anti‑tautological + **RED‑on‑revert** לכל תיקון · Rule 5 (raw) · **strategic‑stop + אישור Michael** לפני שינוי classification (פריט 3) ולפני LIVE · דוח עם NOT‑DONE · עדכן בורדים.

## סדר מומלץ
0 (טסט‑רגרסיה ל‑A7) → 1 (dedup, אחרי אימות‑מיקום) → 2 (provisional→S4) → 3 (day_type accuracy, עם אישור).

## אימות‑Cowork חוזר (Rule 5)
- A7: RED‑on‑revert של טסט‑ה‑T2=None.
- dedup: raw של מיקום‑ה‑200x + שאחרי‑התיקון ירי‑בודד‑לבר.
- provisional: day_type≠UNKNOWN ב‑S4 ב‑30דק' (DB/live).
- day_type accuracy: OPEN_DRIVE×IB → הסיווג הנכון לפי DECISION_MATRIX.
