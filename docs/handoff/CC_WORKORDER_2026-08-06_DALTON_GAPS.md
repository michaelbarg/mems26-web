# cc — פערי-דלתון בשלבים (פסיקת-מייקל 06.08 "מאשר"). שינוי-אחד-בכל-פעם, observability-תחילה.

## שלב-1 (עכשיו) — EXCESS + POOR-HIGH/LOW (גילוי-בלבד ⇒ חיבור-לכלל-המימוש)
1. `backend/v9/systems/extremes_quality.py` (חדש, טהור): על ברי-סשן —
   excess_high/low: זנב-דחייה בקיצון (tail ≥ EXCESS_TAIL_PTS=2.0 או ≥1.5×גוף-הבר, סגירה-מתרחקת,
   ללא-ביקור-חוזר K=3 ברים) ⇒ קיצון-מגֻן. poor_high/low: קיצון שטוח (≤0.5נק' tail, ≥2 נגיעות)
   ⇒ קיצון-עני=מגנט. פלט: {high_quality: EXCESS|POOR|NEUTRAL, low_quality, levels}.
2. חשיפה: לרדאר (שדות extremes) + לפאנל-TPO (סימון ▲מגֻן/▽עני על הקיצונים) + tpo.json-נצרך.
3. **חיבור לכלל-המימוש (EXTREMES_AWARE_REALIZE_V1, בנה-OFF):** ב-S6_TARGET_APPROACH_REALIZE —
   דחייה על קיצון-EXCESS ⇒ מימוש-מיידי (אישור-חזק); יעד יושב על POOR-extreme ⇒ להחזיק (מגנט,
   אל-תממש-מוקדם). replay על 186 העסקאות + 14 ימי-אמת: NET מול הכלל-הקיים ⇒ פסיקה.
4. טסטים לכל פונקציה; Rule-1 (אין-דאטה⇒NEUTRAL, לא ניחוש).

## שלב-2 (אחרי קבלת-1) — חלונות-פתיחה פר-סוג + מסנן-מיקום-drive
לפי מחקר-35-הסשנים: Drive=5-15ד' · Test=10-20 · Reject=15-30 · Auction=30+; re-eval פר-בר;
מסנן: drive-רחוק-מערך=אמת, drive-בקצה-מאזן=חשד-תשישות (balance7 כבר חי). flag-OFF⇒replay.

## שלב-3 — איחוד מתג-Balance↔Imbalance מפורש (חיווט: סוג-יום+רגל+חפיפת-7-ימים ⇒ מתג-אחד ל-S2/S4).
## נדחה: Profile-shapes (b/P/D).
