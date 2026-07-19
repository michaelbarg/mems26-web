# G8 · דוקטרינת Neutral / escalation — מוכן לחתימת-מייקל

**תאריך:** 2026-07-19 · cursor-agent · **spec בלבד — אין שינוי-מסווג**  
**מקורות:** `docs/spec_authority/DALTON_DOCTRINE.md` §2–3 · `daytype_classifier.py` · `shadow_reclass.py` · GAP **G-18** · S124 G8

## 1. מה הקוד החי עושה היום (לא shadow)

| נושא | התנהגות חיה | file |
|---|---|---|
| Neutral = ? | `sides==2` (שני OTF) · **לא** "אין כיוון" | `daytype_classifier.py` Priority 3 |
| Neutral_Center | close mid | אותו |
| Neutral_Extreme | close בקצה · victor מאוחר | אותו |
| Playbook / position | Neutral → REV בקצוות · CONT חסום (כש-pattern-aware/position ON) | `daytype_position_gate.py` · D0 |
| Escalation-only / never-downgrade | **לא** על מנוע-7 החי | — |
| Shadow escalation | `shadow_reclass.py` שרשרת Normal→Variation→Trend + Neutral guard · **לוג בלבד** | `shadow_reclass.py:9-15,74-86` |

Dalton (pp.27–29, 55, 288–292): Neutral = שני צדדים פעילים; מעבר-מצב לפי **acceptance** (כולל downgrade כשמגמה נשברת) — **לא** "רק כלפי מעלה".

## 2. הסתירה ש-G8 צריך לפסוק

| אפשרות | משמעות | סיכון |
|---|---|---|
| **A · Acceptance דו-כיווני (מומלץ דלתון)** | אחרי IB-lock: שדרוג **וגם** הורדה כש-acceptance מפר את הישן (חזרה ל-IB = rejection) | יותר flips; דורש antiflap |
| **B · Escalation-only** | רק Normal→Variation→Trend; אין הורדה תוך-יום | תקוע על Trend_DD נמוך-ביטחון (כמו 07-08) |
| **C · סטטוס-קוו** | מסווג-7 חי ללא shadow; shadow נשאר מת | אין שינוי; G-18 נשאר "דוקטרינה פתוחה" |

הקוד החי כבר **לא** escalation-only. Shadow כן מונוטוני חלקי — **לא** לחבר ללייב בלי פסיקה.

## 3. כללי-Neutral מוצעים לחתימה (מסחר)

1. **Neutral_Center:** רק REV בקצוות VA (fade שני הצדדים) · CONT=SKIP · יעדים קצרים (טבלת-targets: NO T3 / 30min).  
2. **Neutral_Extreme:** REV בקצה · אחרי victor מאוחר — bias ליום-הבא (EOD tag; P2-12 עדיין חסר) · CONT=SKIP באותו יום.  
3. **לא** לפרש Neutral כ-"אין כיוון / אל תסחור" — דלתון סוחר את הקצוות.  
4. אם POC-mig מתחיל לנדוד חזק ב-Neutral → לשקול reclass ל-Variation (קבלת-acceptance), לא CONT בתוך תווית Neutral.

## 4. Escalation — טקסט לחתימה (בחר אחד)

**□ A — Acceptance דו-כיווני (ברירת-מחדל מומלצת)**  
"לאחר IB-lock, סוג-היום מתעדכן על acceptance מחוץ/בחזרה לרהפרנס. מותר upgrade ו-downgrade. antiflap קיים נשאר. Shadow-reclass לא הופך למנוע."

**□ B — Escalation-only**  
"תוך-יום רק העלאת-סוג; הורדה רק ב-EOD או ידני. סותר דלתון p.55/288 — דורש נימוק מפורש."

**□ C — אין שינוי מנוע**  
"G8 = תיעוד בלבד; המסווג החי נשאר; לא מחברים shadow."

## 5. מה לא לעשות בלי פסיקה+סים
- להדליק `shadow_reclass` כמקור-שער  
- never-downgrade על `classify_replay`  
- לשנות ספי Neutral ב-`daytype_classifier`  

**אחרי חתימה:** cowork מעדכן GAP G-18 + ROADMAP; קוד (אם A) = cc-macbook דגל OFF.
