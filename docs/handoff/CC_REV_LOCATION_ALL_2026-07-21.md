# CC — פסיקת-מייקל: שער-מיקום לכל תבניות-ה-REV (שורטים של S4 במיקום שגוי) — 2026-07-21

**מייקל (~19:35):** "בשעתיים האחרונות היו עסקאות-שורט של מערכת-4 שלא היו נכונות מבחינת **מיקום** — ארצה פתרון."

## המקרה (אומת בדאטה, live)
**#439 GHOST SHORT live 18:05 @ 7523.25** (בר אמיתי — לפני הזיהום) → STOP_HIT תוך 4 דק' → **‎−$77.50**
(+תאום-צל #438 ‎−$80). מיקום: **אמצע-value** (VAH 7535.25 · POC 7508.5 · VAL 7496.75) ביום-עולה.
שורט-fade באמצע-הטווח ביום-עולה = בדיוק מה שהדוקטרינה אוסרת (fade רק בקצה).

## למה השערים לא עצרו (הפער המדויק)
1. **playbook:** `GHOST: group REV, Variation: REDUCED` — מותר (ו-REDUCED ממילא נדרס ל-4 ע"י FIXED_4 = G7).
2. **בדיקת-המיקום-הרספונסיבית של ה-playbook חלה רק על REACTIVE/HNS** (בעלי `require_with_trend`) — ראינו
   אותה עובדת ב-17:37 ("REACTIVE responsive SHORT not at VAH (mid_value)"). **GHOST/FAMIR/VEGAS/DBDT/HTLB —
   קבוצת-REV שלמה בלי בדיקת-מיקום.**
3. `reactive_location` gate (gateway:744) — S2-בלבד. `DAYTYPE_LOCATION_GATE` — כובה 07-20 (היה שבור על דאטה-רעה).
→ שורט-REV באמצע-value עבר את כולם וירה לייב.

## הפתרון (smallest correct change)
**להרחיב את בדיקת-המיקום-הרספונסיבית הקיימת ב-`daytype_playbook.decide()` מ-REACTIVE/HNS אל כל `group: REV`**
(GHOST · FAMIR · VEGAS · DBDT · HTLB — לפי ה-group שכבר מתויג ב-yaml):
- REV **SHORT** מותר רק כשהמחיר בתקרה: ≥VAH−tolerance (או day-high proximity לפי אותה לוגיקה קיימת).
- REV **LONG** מותר רק ברצפה: ≤VAL+tolerance.
- אחרת → SKIP עם reason מדויק: `"<PAT> responsive SHORT not at VAH (<location>)"` — אותו פורמט שכבר עובד.
- אותה לוגיקה/רמות שכבר משמשות את REACTIVE (מקור: sierra_tpo, מאומת) — **לא** להחיות את DAYTYPE_LOCATION_GATE הישן.
- `require_with_trend` נשאר כפי-שהוא (REACTIVE/HNS בלבד, פסיקה קיימת) — לא מרחיבים אותו; מיקום-בקצה הוא התנאי ל-REV.

**דגל:** `REV_LOCATION_ALL_V1` (OFF עד ריסטארט-הבוקר) + RULED (ציטוט-הפסיקה הזו).
**טסטים (fixtures מהיום):** (א) #439 GHOST SHORT 18:05 @7523.25 mid-value → **SKIP** · (ב) GHOST SHORT ב-VAH
(≥7535.25−tol) → עובר · (ג) רגרסיה: REACTIVE 17:37 עדיין נחסם, REACTIVE-ב-VAH עובר · (ד) REV LONG ב-VAL עובר,
ב-mid נחסם. חוק-5 על הכל.

**שער-ביקורת:** cursor מאשר את המפרט (יחד עם T1-SPEC) לפני ש-cc בונה. הדלקה בריסטארט-הבוקר לפי נוהל-הקבע.
**נקודה ל-cursor:** ודא אינטראקציה נכונה עם T1-structure-end על REV (סטופ מעבר-לקצה, T1=הקצה-הנגדי-של-value
per targets_table — עקבי).
