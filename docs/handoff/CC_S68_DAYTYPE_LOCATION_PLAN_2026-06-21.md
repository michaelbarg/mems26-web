# CC Handoff — #68: סינרגיית S1→S2/S4 לפי סוג-יום + מיקום · תוכנית-עבודה מלאה · 2026-06-21

**מחבר:** Cowork (תכנון + audit מול אינדקס מרוענן, ללא קוד). **סמכות:** Michael + `docs/spec_authority/S1_TRADE_MANAGEMENT_3CONTRACTS.md`.
**מחליף** את המסגרת הצרה של `CC_S68_REACTIVE_NORMAL_2026-06-20.md` (REACTIVE-בלבד) — זה המסמך הקנוני ל-#68. **לא בוצע commit. לא שונה קוד.**

---

## 0. המודל (אושר ע"י Michael)
S1 מאבחן את סוג-היום. S2/S4 (מערכות-הירי, לכל אחת תבניות לונג+שורט) יורות **בהתאם לסוג-היום + מיקום-המחיר ביחס לנקודות-החשובות**. שלוש שכבות:

1. **S1 מאבחן** סוג-יום (חי). ✅ קיים ומקודם (`S1_NEW_CLASSIFIER=1`).
2. **שער מיקום+כיוון:** לכל ירי — סוג-היום + איפה המחיר ביחס לנקודות → האם הכיוון מותר.
3. **ניהול C1/C2/C3** מבני לפי סוג-היום.

**🔴 עיקרון-מפתח:** הכיוון נקבע מ**סוג-יום+מיקום**, לא ממדד CCI. (לכן `TREND_DIRECTION_GATE` מבוסס-CCI = מודל-שגוי → לבטל.)

---

## 1. טבלת סוגי-היום (ליבת-המסחר)

| סוג-יום | נקודות-מפתח | הטיה לפי מיקום | C1 / C2 / C3 |
|---|---|---|---|
| **Nontrend** | IBH/IBL/POC | דלג (לכל היותר סקאלף-קצה→POC, חוזה-1) | POC / — / — |
| **Normal** | VAH/POC/VAL/IB | VAL→**לונג** · VAH→**שורט** (דהה לערך) | IB-center / VA-נגדי / IB-נגדי (trail) |
| **Variation** | קצה-IB-שנפרץ · measured-move · PDH/PDL | **עם-ההרחבה** בלבד; כניסה בפולבק לקצה-שנפרץ | measured / PDH-PDL / trail |
| **Neutral-Center** | 2 קצוות-IB · POC | דהה כל קצה→מרכז (2 צדדים) | POC / קצה-נגדי / יציאה (בלי runner) |
| **Neutral-Extreme** | קצוות · POC · קצה-מנצח | דהה קצוות, אך החזק לכיוון-המנצח | POC / קצה-נגדי / trail-למנצח |
| **Trend_DD** | single-print/neck · POC-התפלגות-2 · PDH/PDL | **עם-הפריצה** מה-single-print | dist-2 POC / measured / trail-מאחורי-המבנה |
| **Trend_Normal** | קצה-כל-פרק (one-TF) · open · PDH/PDL | **עם-המגמה** מהפתיחה; הוסף בפולבקים רדודים | checkpoint-רחוק / measured-נוסף / hold-to-close |

**חיבור התבניות:** תבנית-לונג מותרת רק היכן שהמודל אומר "לונג"; תבנית-שורט רק היכן ש"שורט". ה-`daytype_playbook` כבר קובע *איזו תבנית בכלל* יורה ביום; השכבה החדשה מוסיפה את אילוץ ה-**מיקום+כיוון**.

---

## 2. מפת שימוש-חוזר (אינדקס מרוענן 2026-06-21 — לא לבנות מחדש)

| רכיב | מצב | היכן | פעולה |
|---|---|---|---|
| סוג-יום חי בכניסה | ✅ | `extract_g1_entry_context` | שימוש-חוזר |
| verdict תבנית×יום | ✅ | `daytype_playbook.decide()` (gateway:150) | שימוש-חוזר |
| נקודות VAH/VAL/POC/IB בכניסה | ✅ זמין | `cross_context.tpo_system` | לקרוא משם |
| מסווג 7-סוגים | ✅1 | `daytype_classifier`+`relative_features` | שימוש-חוזר |
| שער-מיקום | ⚠️ חלקי | `reactive_location_gate.py` ✅1 (POC, REACTIVE) | **להכליל** לכל התבניות, מותנה-יום |
| ניהול C1/C2/C3 | ⚠️ R-based; מבני=stub | `targets_table` ✅7 / `day_type_targets` ✅2 | **להתאים** ליעדים מבניים |
| trail/runner | ✅ | `manager` + `RUNNER_TRAIL_V1` | שימוש-חוזר |
| שרשרת-שערים | ✅ | `trading_gateway.route_setup` | שימוש-חוזר |
| נקודות+הטיה פר-יום | ⚠️ מת | `daytype_playbook.yaml::daytype_style` (0 קוראים) | **להחיות** (§1) |

**3 החסרים האמיתיים לבנייה:** (א) קונפיג §1 (להחיות `daytype_style`); (ב) resolver מיקום→כיוון-מותר; (ג) resolver יעדים-מבניים.

---

## 3. רשימת ביטול/פרישה (usage מאינדקס 2026-06-21)

| רכיב | usage | פעולה | מתי |
|---|---|---|---|
| `TREND_DIRECTION_GATE` (CCI) | ✅1, חי ב-SHADOW | **לבטל** (מודל-שגוי) → כיוון מסוג-יום+מיקום | עכשיו · **דורש אישור-Michael (trading-surface)** |
| `reactive_location_gate.py` | ✅1 | לאחד לשער-המוכלל | כשהמאוחד נכנס |
| `decision_matrix.py` | ✅**5** | לפרוש (הוחלף במסווג) | אחרי #68a (עדיין load-bearing) |
| `state_machine.py` | ✅**5** | לפרוש | אחרי #68a |
| `open_type.py`✅1 · `shadow_reclass.py`✅1 · `opening_detector.py`(v1)✅1 · `detector.detect_opening_type` · `api._classify_v1_from_tpo` | low | לפרוש (הוחלפו ב-v2/החדש) | אחרי #68a |
| `neutral_classifier`✅2 · `extensions`✅4 · `zohar_rules`✅4 · `triggers`✅3 | feed הישן | לאמת — המסווג-החדש עושה אותם בעצמו | לפרוש עם state_machine |
| `services/trail_engine.py` · `gateway/trade_management.py` | יתומים | ניקוי אופציונלי (הוחלפו ב-RUNNER_TRAIL_V1) | נפרד |
| chop/Layer0/COT-AMT gates | OFF-קבוע | **לא נוגעים** | — |

---

## 4. תוכנית-עבודה (שלבים)

- **שלב 0 — רענון אינדקס. ✅ בוצע 2026-06-21** (714 קבצים; המסווג+השערים מאונדקסים; usage-counts מעודכנים). אין מחיקות.
- **שלב 1 — קונפיג סוג-יום:** להחיות `daytype_style` לטבלה המלאה §1 (נקודות+הטיה+C1/C2/C3). config-only, אפס נתיב-ריצה ⇒ אפס סיכון.
- **שלב 2 — בניית 2 ה-resolvers (flag default-OFF):** (א) מיקום→כיוון-מותר (מכליל את reactive_location_gate, מחליף CCI); (ב) יעדים-מבניים (מתקן את ה-stub, קורא `cross_context.tpo_system`). טסטים אנטי-טאוטולוגיים.
- **שלב 3 — חיווט בגייטוויי (flag default-OFF):** שער מאוחד ב-`route_setup` (sibling לקיימים) + ניהול דרך resolver-היעדים. **לבטל `TREND_DIRECTION_GATE`** (אישור-Michael).
- **שלב 4 — אימות SHADOW חי:** flag ON ב-SHADOW בלבד; לוג פר-ירי (day_type · מיקום מול נקודות · החלטת-כיוון · C1/C2/C3 · תוצאה מול בפועל). לצבור ≥N ימים לכל סוג לפני DEMO/LIVE. (אין offline — §4א ב-spec הקודם.)
- **שלב 5 — פרישה:** לחבר את האירוע-per-bar (`main.py`) למסווג-החדש (#68a) → ואז לפרוש decision_matrix+state_machine+המודולים §3 → לרענן אינדקס שוב.

---

## 5. שערי-אישור (Michael) + בטיחות
- אישור נדרש: (א) טבלת §1 כקונפיג · (ב) **ביטול `TREND_DIRECTION_GATE`** · (ג) כל flag ON ב-SHADOW.
- כל שלב flag-gated default-OFF, fail-open/fail-safe; אנטי-טאוטולוגי; 4 צירי-UAT; עדכון STATUS_BOARD/ROADMAP + רענון-אינדקס אחרי שינוי מבני; CC בונה, Cowork מאמת (Rule 5); **ללא commit עד הוראת-Michael**.

## 6. NOT-DONE
- לא מוחקים את המנוע-הישן בשלבים 1–4 (load-bearing עד #68a בשלב 5).
- לא נוגעים ב-opening_type, ב-S3/footprint, ובשערי-ה-Standing-OFF.
- CCI לכל היותר אישור-משני — לא קובע-כיוון.
