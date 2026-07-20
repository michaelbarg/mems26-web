# G8 · דוקטרינת Neutral / escalation — **נפסק מייקל 2026-07-20: A**

**חתימה:** מייקל בחר **A — Acceptance דו-כיווני.**  
Neutral-rules (REV בקצוות · CONT=SKIP · לא "אין מסחר"): **מאושרים כברירת-מחדל** עם A (לא בוטלו).

**טקסט מחייב:**
> לאחר IB-lock, סוג-היום מתעדכן על acceptance מחוץ/בחזרה לרהפרנס. מותר upgrade ו-downgrade. antiflap קיים נשאר. Shadow-reclass לא הופך למנוע.

**מה עכשיו:** cowork מעדכן ROADMAP אם צריך. אם נדרש קוד שמממש A מעבר למצב החי — cc-macbook, דגל OFF, סים לפני הדלקה. אין שינוי-מנוע בקומיט הזה.

---

**מקורות:** `docs/spec_authority/DALTON_DOCTRINE.md` §2–3 · `daytype_classifier.py` · `shadow_reclass.py` · GAP **G-18** · S124 G8

## 1. מה הקוד החי עושה היום (לא shadow)

| נושא | התנהגות חיה | file |
|---|---|---|
| Neutral = ? | `sides==2` (שני OTF) · **לא** "אין כיוון" | `daytype_classifier.py` Priority 3 |
| Neutral_Center | close mid | אותו |
| Neutral_Extreme | close בקצה · victor מאוחר | אותו |
| Playbook / position | Neutral → REV בקצוות · CONT חסום (כש-pattern-aware/position ON) | `daytype_position_gate.py` · D0 |
| Escalation-only / never-downgrade | **לא** על מנוע-7 החי | — |
| Shadow escalation | `shadow_reclass.py` · **לוג בלבד** | `shadow_reclass.py` |

## 2. האפשרויות (נפסק: A)

| אפשרות | משמעות | סטטוס |
|---|---|---|
| **A · Acceptance דו-כיווני** | שדרוג **וגם** הורדה על acceptance | ✅ **נבחר 2026-07-20** |
| **B · Escalation-only** | רק כלפי מעלה | נדחה |
| **C · סטטוס-קוו** | תיעוד בלבד | נדחה |

## 3. כללי-Neutral (מאושרים עם A)

1. **Neutral_Center:** רק REV בקצוות VA · CONT=SKIP · יעדים קצרים.  
2. **Neutral_Extreme:** REV בקצה · bias ליום-הבא (EOD tag עדיין חסר) · CONT=SKIP באותו יום.  
3. **לא** לפרש Neutral כ-"אין כיוון / אל תסחור".  
4. POC-mig חזק ב-Neutral → לשקול reclass ל-Variation, לא CONT תחת Neutral.

## 4. מה לא לעשות בלי פסיקה+סים נוספת
- להדליק `shadow_reclass` כמקור-שער  
- never-downgrade על `classify_replay`  
- לשנות ספי Neutral ב-classifier בלי דגל+סים  
