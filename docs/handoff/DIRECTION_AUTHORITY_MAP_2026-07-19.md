# D0 · מפת רשות-הכיוון — סוג-יום × מיקום × POC-migration → כיוון מותר

**פסיקת-מייקל 2026-07-19.** זו ה**מפה-הקנונית** שרשות-הכיוון (`daytype_position_gate`, שלב D1)
תיישם. **spec בלבד — אין קוד עד שמייקל חותם + קורסור מצליב.** אין סינתזה (Rule 1).

**מקור:** כללי `daytype_position_gate.py` הקיימים (אומתו תואמי-דלתון ע"י cowork) + פסיקת-Normal של
מייקל + חיווט POC-migration (הפער-החדש). דוקטרינה: `DALTON_DOCTRINE.md`.

## הגדרות
- **מיקום (zone):** `below_value`(<VAL) · `near_val` · `mid`(סביב POC) · `near_vah` · `above_value`(>VAH).
- **POC-migration:** האם ה-POC **עצמו** נודד לאורך הסשן — `UP` / `DOWN` / `FLAT` (תקוע). נמדד על
  חלון-מתגלגל (ספֶק-D1). זה ≠ POC-רמה (איפה המחיר). דלתון: *נדידת-ערך = מגמה.*
- **משפחה:** CONT (המשך: ZLR/TLB/TT/GB100/FLAGS/INITIATIVE) · REV (דהייה: VEGAS/GHOST/FAMIR/HTLB/
  HNS/DBDT/REACTIVE).

---

## המפה

| סוג-יום | REV (דהייה) | CONT (המשך) | POC-migration | הערה |
|---|---|---|---|---|
| **Normal** ⭐ | ✅ תמיד בקצוות: LONG@`near_val/below`, SHORT@`near_vah/above` | ✅ **רק** בצד-הנכון של POC **וגם** POC נודד בכיוון-העסקה: LONG(mig=UP, מתחת-POC), SHORT(mig=DOWN, מעל-POC). **חריג מפורש ל-PATTERN_AWARE** (חוק-על 3) | **מבחין**: `FLAT`→REV-בלבד (מאוזן-אמיתי) · `UP/DOWN`→פותח CONT בכיוון | **פסיקת-מייקל 07-19** — ראיה: 07-17 4/4 ZLR CONT +$255; REV-only היה חוסם הכל |
| **Variation** | ✅ אחרי acceptance בצד-החדש | ✅ **עם ההרחבה**: LONG אם IB נפרץ מעלה, SHORT אם מטה | אישור: migration שמסכים עם ההרחבה = איכות-גבוהה; מנוגד = הורדת-איכות | `location_gate` כבר אוכף with-expansion |
| **Trend_Normal** | ❌ (שער-משפחה מחזיק REV) | ✅ **עם המגמה** בלבד | **POC לא-שער** — המגמה קובעת (חוק-על 1) | `position_gate`: WITH trend |
| **Trend_DD** | ❌ | ✅ **עם כיוון-הפריצה** (אחרי refill-צוואר) | **POC לא-שער** — המגמה קובעת | invalidation ב-refill |
| **Neutral_Center** | ✅ **שני** הצדדים (דהיית שני קצוות; אין מנצח, mid) | ❌ (מאוזן) | לרוב FLAT; אם נודד → היום מתפרק לכיוון (שקול Variation) | `position_gate`: both sides |
| **Neutral_Extreme** | ✅ **שני** הצדדים (דהיית קצה, החזק-מנצח מאוחר) | ❌ | migration מראה מי-המנצח | both sides |
| **Nontrend** | ❌ SKIP | ❌ SKIP | — | להישאר בחוץ (playbook) |
| **Nonconviction** | ❌ SKIP | ❌ SKIP | — | OA בערך-קודם, אפס-OTF — בחוץ |

⭐ = התא שנפסק היום. שאר-השורות = כללי-`position_gate` הקיימים (תואמי-דלתון) + שכבת-migration.

---

## חוקי-העל (חוצי-סוג-יום)
1. **חוק-POC חל אך-ורק על ימי-רוטציה** (פסיקת-מייקל 07-19): `Normal · Variation · Neutral_Center ·
   Neutral_Extreme`. גם POC-**רמה** (long-מתחת/short-מעל) וגם POC-**migration** הם שערי-כיוון **רק שם**.
   **בימי-Trend (`Trend_Normal · Trend_DD`) הכיוון נקבע ע"י המגמה בלבד — POC אינו שער-כיוון** (מחיר
   מעל-POC בלונג = עם-המגמה = תקין).
2. **מלכודת-#372 — רק בימי-רוטציה:** לחסום CONT-LONG מעל-POC · CONT-SHORT מתחת-POC. **בימי-Trend
   זה לא חל** (זו בדיוק כניסת-ההמשך הרצויה).
3. **Normal CONT = חריג מפורש ל-`DAYTYPE_PATTERN_AWARE_V1`** (פסיקת-מייקל 07-19): pattern_aware חוסם
   CONT בימים-מאוזנים (`_BALANCED_DAYTYPES`), **אבל המפה מתירה CONT ב-Normal כש-POC נודד בכיוון-העסקה
   ובצד-הנכון של POC.** D1 חייב **לפטור** את חסימת-ה-CONT של pattern_aware ב-Normal כשתנאי-ה-migration
   מתקיים (ורק אז). POC `FLAT` ב-Normal → החסימה נשארת (REV-בלבד).
4. **חסר-דאטה (POC/VA/migration=None) → fail-open** עם סיבה (לא חסימה-מסונתזת; Rule 1).
5. **הרשות מגייטת כיוון+משפחה בלבד** — לא גודל (זה G7) ולא תזמון (זה FHB/paint).
6. **תלוי בתווית-יום נקייה** — לכן D1 **חייב** לרוץ אחרי G2/G6 (לקח I-44: תווית-מעופשת → חסימה שגויה).

## מה D1 מיישם (מהמפה הזו)
- מרחיב את `daytype_position_gate` שיכסה **CONT** לפי המפה (היום CONT נופל ל-POC-strict בלבד).
- **מוסיף POC-migration** כקלט (`UP/DOWN/FLAT`) — הפער-החדש-היחיד; המקור: חלון-מתגלגל על POC
  (ספֶק בפועל ב-D1, לא מ-`poc_drift`-הסיווג).
- מדליק `DAYTYPE_POSITION_GATE` (+ `DAYTYPE_GATE_LIVE_V1` לתיקון I-44) — **רק אחרי G2/G6 + סים**.

## חתימות
- [ ] **מייקל** — המפה משקפת את הכוונה (במיוחד תא Normal + חוק-על-1 + POC-migration-כתנאי).
- [ ] **cursor-agent** — הצלבה מול `DALTON_DOCTRINE.md` + `daytype_position_gate.py` (file:line), אישור/תיקון.
- [ ] **cowork** — אחרי 2 החתימות: זה נעשה הבסיס ל-D1; אין קוד לפני.
