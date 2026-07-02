# MEMS26 — ניתוח-פערים מול "מסמך משלים: גלאים, חסמים ומבחני הבחנה" (MoM מעבר-שני)
_Cowork 2026-07-02 ~18:2x IL · המסמך של מיכאל נשמר ב-`MOM_SUPPLEMENT_DETECTORS_2026-07-02.md` · ראיות מ-grep+classify_replay חי._

## מה כבר קיים (לא לבנות מחדש — audit-before-build)
| פריט מהמסמך | מצב | ראיה |
|---|---|---|
| VA-מלא של אתמול (VAH/VAL/POC+רוחב) | ✅ קיים כ-input | `classify_replay`: prior_vah/prior_val/pdh/pdl/va_width |
| זיהוי צורת-פרופיל P/b/D | 🟡 מחושב, **לא נצרך ע"י שום gate** | `tpo_history`/`tpo_routes` מחשבים; אף gate/pattern לא קורא — הפילטר-נגד-initiative-מזויף לא מחווט |
| Second distribution (DD) | ✅ detector קיים | `classify_replay.second_distribution` |
| Gap גודל+מיקום-מול-PD | 🟡 קיים כ-input לסיווג (A1 Pre-Open) | `detector.py:334`, `state_machine.py:431-480`; **אין** טיימר-שעה-ראשונה/כלל-מחיקה כטרייד |
| Single-prints / tails | 🟡 נבנים ב-TPO builder | `tpo/profile_builder.py`, `levels.py`; **אין** דירוג-איכות-קיצון (TAIL_STRONG/TIME_WEAK) ואין צריכה ב-stops/targets |
| One-timeframe integrity | 🟡 חלקי (trend_state) | כהגדרת המסמך עצמו — לא בוליאני-רץ שמזין trailing/C3 |
| רוחב-IB פרסנטילי | ✅ | ib_pctile/ib_class (הכימות שלנו — הספר בלי ספים) |

## הפערים — לפי שכבות ערך
### שכבה A · חוסמי-עסקאות-רעות (הכי קרוב לכסף; משלים את שער-R:R)
| ❌ פער | מהות | ווקטור |
|---|---|---|
| **P/b כפילטר-initiative** | הצורה כבר מחושבת! לחווט: 4 תנאי-P ⇒ חסימת INITIATIVE/CONT-long (מראה ל-b) | פריט-13 לחבילת-CC — קטן, data קיים |
| **NONCONVICTION (סוג-יום 8)** | Open-Auction-in-value + אפס-tails + אפס-RE ⇒ override חוסם-הכל | S1-recalibration (עם questionnaire) |
| **Value-Area Rule כחסם-fade** | פתיחה מחוץ-ל-VA + acceptance בפנים ⇒ אסור-fade על הקצה הקרוב + target=קצה-נגדי | פריט-CC בינוני; inputs קיימים |
| **Calendar/news flag** | יום-לפני-נתון ⇒ הטיית-Nonconviction | input חיצוני חדש (feed לוח-שנה) |
| **Auction-failure detector** | חיטוט-רפרנס-בלי-follow-through כטריגר-reactive כל-היום | מרחיב את opening_type לכל-סשן |

### שכבה B · איכות מעברים/ניהול (מזין trailing + reclass)
דאבל-פרינט transition (4 קטגוריות-מעבר — "הגלאי שחסר" גם למקרה של היום: IB-break→acceptance) · Time-at-Extreme warning · דירוג-איכות-קיצון · One-TF בוליאני→יציאת-C3.

### שכבה C · רפרנסים/תגיות (inputs חדשים ל-S1)
TPO-count מעל/מתחת-POC בלי-tails (+נטרול-בטרנד; קיים רק `max_tpo_count` לרוחב ב-zohar_rules) · Spike-memory מאתמול (+אומדן-טווח) · תגיות-EOD (3-1 / 2I-1R / Neutral-Extreme-close) · HVN/LVN-proxy ל-targets · gap-timer.

### חוקי-ביטול (טבלה-9) שאינם ממומשים
מחיקת-gap כסטופ-קשיח · double-prints-בתוך-spike מבטלים רפרנס · DD-singles-שמתמלאים=יציאה · חזרה-לאיזון אחרי breakout=יציאה+דריכה-נגדית ("rock"). קיימים היום: trail ✓, opposite-exit (בנוי, OFF) ✓.

## המלצת-קדימויות (לפסיקת-מיכאל)
1. **P/b-filter** (שכבה A, זול — הנתון קיים) 2. **דאבל-פרינט transition** (משרת גם את reclass של היום) 3. **Value-Area Rule** 4. **NONCONVICTION** בתוך S1-recalibration 5. השאר לפי תור. הסטטיסטיקות (94%/59% וכו') = אג"ח 86-87 — לאמת על MES לפני משקולות (כהערת-המסמך).
