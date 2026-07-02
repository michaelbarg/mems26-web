# MEMS26 — מסמך משלים: גלאים נוספים, חסמים ומבחני הבחנה
_נמסר ע"י מיכאל 2026-07-02 (מעבר שני מלא על Mind Over Markets) · נשמר verbatim ע"י Cowork · ניתוח-פערים מולו: `MOM_GAP_ANALYSIS_2026-07-02.md`_

## מעבר שני מלא על *Mind Over Markets* — מה שחסר במטריצה הראשונה
**מקורות:** פרק 3 (TPO count, שליטת OTF), פרק 4 — Auction Rotations & Timeframe Transition, Auction Failures, Pattern Recognition (P/b/Ledge), Open/Value acceptance-rejection, HVA/LVA, Special Situations (עמ' 272–298), Markets to Stay Out Of (עמ' 300–304).
---
## טבלה 5 — סוג יום שמיני: Nonconviction Day (החסם שחסר ל-S1)
| מאפיין | פירוט |
|---|---|
| **הבעיה** | דלטון מגדיר במפורש יום שנראה **מבנית זהה** ל-Normal / Normal Variation / Neutral — אבל בלי שום conviction של OTF. "The completed Profile looks like a Normal Variation day, but at no point was there a clear indication of other timeframe presence" |
| **זיהוי מכני** | (1) פתיחה מסוג Open-Auction **בתוך ה-VA של אתמול**; (2) אפס tails אמיתיים (אין single-prints בקצוות); (3) אין RE יזום משמעותי — רוטציות אקראיות קטנות; (4) אין נקודות ייחוס שנוצרות במהלך היום |
| **למה זה קריטי** | S1 הנוכחי יסווג יום כזה כ-Normal_Variation בסוף היום — וה-gate יאשר סטאפים על מבנה ריק. דלטון: "any trading decision would be based on conjecture and random price rotations" |
| **פעולה נדרשת** | flag נפרד ב-S1: `NONCONVICTION` — override שחוסם את כל ה-playbooks גם אם הצורה הסופית עוברת סיווג רגיל. תנאי הדלקה: Open-Auction-in-value AND no-tails AND no-initiative-RE עד שעה X |
| **הרחבה** | אותה קטגוריה כוללת גם ימים לפני נתון מאקרו גדול — "היום-יומיים לפני חדשות נשארים בידי הלוקאלים" — נפח נמוך, רוטציות פראיות. מחייב calendar flag (input חסר נוסף) |
---
## טבלה 6 — גלאים מבניים חדשים לספריית ה-detectors
| גלאי | חוק מכני (מהספר) | שימוש ב-MEMS26 |
|---|---|---|
| **TPO Count** | ספירת TPOs מעל ה-POC מול מתחת ל-POC, **בלי single-print tails**. יחס גדל מתחת ל-POC בלי RE מוכר = קונים OTF שולטים בגוף (הלוקאלים מוכרים להם). איזון פתאומי אחרי הטיה = כיסוי מלאי לוקאלים (רוטציה זמנית, לא היפוך) | pillar נוסף לזיהוי שליטה בימי רוטציה; imbalance בסוף יום = מומנטום ליום הבא. **מגבלה קשיחה מהספר:** עובד רק בשוק דו-timeframe רוטציוני — **לנטרל בימי Trend** ובשוק one-timeframe |
| **One-Timeframe Integrity Check** | קניות: low של כל תקופה ≥ low הקודמת בלי לחצות מעלה את הקודמת נגד. תקף פר-בר כבדיקת המשכיות | כבר קיים חלקית; להפוך לבוליאני רץ שמזין גם trailing (הפרה = טריגר יציאה ל-C3 ב-Trend) |
| **Auction-Test → Double-Print Confirmation** | רוטציה נגדית מעבר לקיצון התקופה הקודמת = "מבחן". **double prints (שתי תקופות) מעבר לקיצון נגד כיוון ה-one-timeframe = אישור מעבר שליטה.** דוגמת הספר: FG double prints מתחת ל-low של E מאשרים סוף שליטת קונים | זהו detector המעבר שחסר לנו: 4 קטגוריות מעבר — ללא / 1TF→2TF / 2TF→1TF / 1TF→1TF הפוך (=Neutral). מכני לחלוטין על ברי 30 דק' (או מקבץ 6×5m) |
| **Time-at-Extreme Warning** | תקופה מלאה ליד הקיצון **בלי הרחבת טווח** = "too much time" — האיתות הראשון לשינוי שליטה, לפני tails ו-RE. "Time provides the signal, structure provides the confirmation" | early-warning ל-trailing: תקופה שלמה בקצה בלי RE חדש → הידוק סטופ על C2/C3 |
| **Extreme Quality (tail מול time)** | קיצון עם tail (single prints) = דחייה אגרסיבית, חזק; קיצון עם **double prints בלי tail** = "high made by time, not aggressive activity" — קיצון חלש. וגם: **היעדר tail בקצה בשוק עולה → לקחת רווחים מוקדם, סיכון היפוך** | דירוג איכות קיצונים: TAIL_STRONG / TIME_WEAK. משפיע על אמון בקצה כרפרנס ל-target/stop |
| **Auction Failure** | חיטוט מעבר לנקודת ייחוס ידועה (PDH/PDL, weekly H/L, קצה balance) **בלי follow-through** → דחייה מהירה לכיוון ההפוך. עוצמת הדחייה פרופורציונית לחשיבות הרפרנס (רפרנס ארוך-טווח > קצר) | טריגר reactive ישיר — משלים את ה-Open-Test-Drive לכל שעה ביום, לא רק לפתיחה |
| **תבנית P (Short Covering)** | ראלי חד על/סמוך לפתיחה **אחרי ימי מכירה חזקים** → הקונה נעלם, כל auction עוקב גרוע מהקודם, לפעמים מעבר ל-one-timeframe selling מהשיא. פרופיל בצורת P. 4 תנאים: (1) כיוון אחרון הפוך לתבנית; (2) open ליד ה-low; (3) אין המשכיות אחרי ה-drive; (4) auctions נסוגים בהדרגה | **פילטר קריטי נגד initiative-long מזויף:** ראלי short-covering נראה כמו קניית OTF אבל הוא old business. חוסם IB-1 כשמתקיימים 4 התנאים. צפי: מילוי החצי התחתון של הפרופיל |
| **תבנית b (Long Liquidation)** | תמונת ראי: שבירה חדה אחרי מגמת עלייה, open ליד ה-high, אין המשכיות מוכרים, מעבר ל-one-timeframe buying | פילטר נגד initiative-short מזויף |
| **הבחנה: P אמיתי מול עצירה בראש bracket** | בעצירת bracket הקונה **מחזיק** את הקרקע (auctions שומרים על השיאים) ואחרי הפריצה הראלי מתחדש; ב-P הקונה **מאבד** קרקע בהדרגה | משווים רצף auction highs: יורדים = P; מחזיקים = pause לפני המשך |
| **Ledge** | חצי-פרופיל — עצירות חוזרות באותו מחיר בדיוק. איזון יומי. פריצה "כמה טיקים מעבר ל-ledge" → כניסה עם הפריצה | detector פשוט: N נגיעות באותו מחיר + flat edge. ה-ledge לרוב תוצר של covering/liquidation |
| **Fat-Profile = פרוקסי נפח** | "בהיעדר נתוני נפח, הפרוקסי השני בטובו לריכוזי נפח הוא מחירי ה-TPO הגבוהים סביב ה-POC" — האזור השמן מאט מחיר | **פותר חלקית את ה-input החסר של real volume:** HVN-proxy = מחירים עם ספירת TPO מקסימלית; LVN-proxy = מחירים דקים. שימוש: targets נעצרים לפני HVN של אתמול; LVN נחצה מהר. זיכרון קצר — ככל שהמחיר רחוק יותר זמן, הרפרנס נחלש |
---
## טבלה 7 — Special Situations: טריגרים מכניים + נתוני המחקר של דלטון
מחקר על Treasury Bonds 1986–87. המספרים = bias סטטיסטי, לא ערובה; דלטון עצמו מסייג ששווקים משתנים.
| מצב | הגדרה מכנית | סטטיסטיקה (מהספר) | חוק מסחר |
|---|---|---|---|
| **3-1 Day** | שלושת מדדי הכיוון מיושרים: initiative tail + initiative TPO count + initiative RE באותו כיוון | 90 דק' ראשונות של היום הבא: **94%** מחיר טוב יותר מ-VA של אתמול, 0% גרוע. סגירת יום הבא: 59% טוב יותר, **97% בתוך-או-טוב** | תגית EOD ב-S1 → bias פתיחה ליום הבא (וסיבה להחזיק C3 אם המערכת תתמוך אי-פעם בהחזקת לילה) |
| **2I-1R Day** | כמו 3-1 אבל ה-tail הוא responsive במקום initiative | 90 דק': 71% טוב יותר, 0% גרוע; סגירה: 82% בתוך-או-טוב | תגית חלשה יותר — bias קיים אך פחות אמין |
| **Neutral-Extreme** | יום Neutral (RE דו-צדדי) שנסגר על קיצון | 90 דק' ראשונות: 64% טוב יותר, **92% בתוך-או-טוב** בכיוון הסגירה | ה-close של Neutral-Extreme = חץ כיוון לפתיחת מחר; מזין את בדיקת ה-open של יום המחרת |
| **Value-Area Rule** | פתיחה מחוץ ל-VA של אתמול → מחיר חוזר לתוכו → **acceptance = double TPO prints בתוך ה-VA** ⇒ הסתברות גבוהה לחציית ה-VA כולו | מותנה ב-3 מסננים: (1) מרחק פתיחה מה-value — קרוב = סביר יותר; (2) **VA צר** נחצה בקלות (נפח מאט מחיר); (3) כיוון ה-auction הארוך תומך. בלי המסננים — "מטבע הוגן" | target ליום rotational: קצה ה-VA הנגדי. וגם חסם: אחרי acceptance בתוך VA — לא לעשות fade על קצה ה-VA הקרוב |
| **Spike** (פריצה מ-value בתקופות האחרונות) | טווח ה-spike = מראש התקופה הפורצת ועד הקיצון. אין זמן לאימות ⇒ השיפוט עובר ל-open של מחר: **בתוך ה-spike** = איזון, אימות הרמה; **מעבר ל-spike בכיוונו** = out-of-balance קיצוני, המשך; **נגד ה-spike (מתחת לבסיס buying spike)** = דחייה | פתיחה בתוך spike → **אומדן הטווח = אורך ה-spike, לא טווח היום המלא** ("the spike is treated like a new day"). קצוות ה-spike תקפים כרפרנס **לחיטוט הראשון בלבד**; מבחנים חוזרים באותה תקופה או double prints בתוך ה-spike מבטלים | detector EOD (spike של אתמול = input חדש למחר) + עדכון מודול אומדן הטווח |
| **Balance-Area Breakout** | ≥ מספר ימים של value חופף (או ledge יומי) → acceptance מחוץ לאזור = "trade you almost have to do" עם הפריצה. סטופ: כמה טיקים בתוך האזור | **תבנית ה-rock:** פריצה לצד אחד שנכשלת (חוזרת פנימה) → יציאה בהפסד מינימלי → **מוכנות לפרוץ בצד השני** בכוח מוגבר ("ידוע שאין עסקים מתחת ל-lows") | ל-IB-1 בהקשר רב-יומי; הכשל-ואז-היפוך הוא סטאפ בפני עצמו |
| **Gap** | פתיחה מחוץ לטווח אתמול = "invisible tail" — excess של OTF. **חוק השעה:** אם ה-gap ימולא, המילוי קורה בדרך כלל בשעה הראשונה; ככל שמחזיק יותר — הסתברות המשך עולה | כניסה עם כיוון ה-gap; סטופ = נקודת מחיקת ה-gap (חצייה מלאה). **gap קיצוני בגודלו** → צפוי responsive שמצר אותו קודם — לחכות לחזרת ה-initiative לפני כניסה (דוגמת ה-Swiss franc) | gap-size input + טיימר שעה ראשונה. סיווג רקע: Breakaway / Acceleration / Exhaustion (לפי מיקום במגמה הארוכה) משנה הסתברות החזקה |
---
## טבלה 8 — מטריצת הבחנה בין זוגות מתבלבלים
| זוג | המבחין שהמערכת יכולה למדוד |
|---|---|
| Normal ↔ Normal Variation | IB רחב שמחזיק (אין RE) ↔ IB בינוני + RE חד-צדדי ש"הופך את הבסיס" ובונה value חדש |
| Normal Variation ↔ Trend | NV: אחרי ה-RE נוצר איזון חדש (double prints ברמה החדשה, רוטציות חוזרות). Trend: RE **במספר תקופות רצוף**, one-timeframe שרוד, פרופיל ≤4–5 TPO רוחב, ה-value לא מפסיק לנדוד |
| Trend ↔ DD-Trend | Trend: ה-open הוא הקיצון, drive רציף מהפתיחה. DD: IB צר + שקט בבוקר → פריצה באמצע היום → התפלגות שנייה מופרדת ב-single prints |
| Nontrend ↔ DD-Trend (מוקדם ביום!) | **שניהם מתחילים ב-IB צר.** מבחינים לפי הקשר: Open-Auction בתוך value של אתמול + לוח נתונים למחר → הטיית Nontrend; פתיחה/Open-Auction מחוץ לטווח אתמול (out-of-balance) → הטיית DD. ההכרעה: הופעת RE או אי-הופעתו |
| Neutral ↔ Nonconviction | Neutral: RE **אמיתי לשני הכיוונים** (שני צידי ה-OTF פעילים — מלחמה אנכית). Nonconviction: רעש בלי RE משמעותי, בלי tails, בלי רפרנסים |
| Trend אמיתי ↔ P/b (covering) | P/b: כיוון הימים האחרונים **הפוך** לתנועה, open בקצה הנגדי, auctions מאבדים קרקע בהדרגה, אין new business. Trend: המשכיות RE רב-תקופתית + נפח (או TPO-proxy) גדל עם התנועה |
| קיצון חזק ↔ קיצון חלש | single-print tail (רצוי ≥2 מחירים) ↔ double prints בקצה ("made by time") או היעדר tail — קיצון חלש, לא לבנות עליו target/stop |
| פריצת value אמיתית ↔ מלכודת | acceptance = double TPO prints / זמן ברמה החדשה בלי חזרה לטווח ↔ rejection = חזרה מהירה דרך נקודת הפריצה (ואז התבנית ההפוכה נדרכת) |
---
## טבלה 9 — ריכוז כל חוקי הביטול (Invalidation) לפי סטאפ
| מה נדרך | מה מבטל | פעולה |
|---|---|---|
| Open-Drive / Open-Test-Drive | חזרה **דרך טווח הפתיחה** / מחיקת ה-tail | יציאה — "conditions have changed" |
| DD-Trend | single prints מפרידים → double prints בשעות מאוחרות | ההתפלגות השנייה נדחתה — יציאה מיידית |
| Trend (one-timeframe) | double prints נגד כיוון ה-1TF (אישור transition) | trailing/יציאה; אזהרה מוקדמת: תקופה מלאה בקיצון בלי RE |
| Gap trade | מילוי מלא של ה-gap (נקודת המחיקה); רוב המילויים — בשעה הראשונה | סטופ קשיח בנקודת המחיקה |
| Spike כרפרנס | double prints בתוך ה-spike / מבחנים חוזרים באותה חצי שעה | הקצה כבר לא support/resistance |
| Balance-area breakout | חזרת המחיר לתוך אזור האיזון | יציאה בהפסד מינימלי + היערכות לפריצה הנגדית |
| Ledge hold | מחיר יורד/עולה "כמה טיקים מעבר ל-ledge" | היפוך: נכנסים עם כיוון הנטישה |
| Fade על קצה VA של אתמול (יום שנפתח מחוץ ל-value) | acceptance (double prints) **בתוך** ה-VA | Value-Area Rule נדרך — צפי חצייה מלאה, אסור fade |
| כל סטאפ המבוסס על קיצון | הקיצון "נעשה בזמן" (double prints, בלי tail) | דירוג האמון יורד; רווחים מוקדם יותר |
| TPO-count pillar | היום מסווג Trend / one-timeframe | הפילר מנוטרל — לא תקף מחוץ לרוטציה |
| כל ה-playbooks | flag של NONCONVICTION או calendar-flag (יום לפני נתון גדול) | stand aside — "bad trades keep you from entering a good trade" |
---
## השלכות על S1 — inputs חסרים חדשים (בנוסף לארבעה שכבר סומנו)
1. **VA מלא של אתמול** — VAH/VAL/POC + **רוחב ה-VA** (מסנן ל-Value-Area Rule) — הרחבה של PDH/PDL שכבר ברשימה.
2. **מנוע TPO count** רץ (מעל/מתחת POC, בלי tails) + מתג נטרול בימי 1TF.
3. **Rotation tracker** של auctions 30-דקתיים: one-timeframe integrity, auction tests, double-print transitions, time-at-extreme.
4. **Spike memory** — spike של אתמול (טווח + כיוון) כ-input לפתיחת היום, כולל וריאנט אומדן הטווח.
5. **Gap size + טיימר שעה ראשונה.**
6. **Calendar/news flag** — נתון מאקרו מחר/היום → הטיית Nontrend/Nonconviction ונטרול playbooks.
7. **EOD tags** ליום הבא: 3-1 / 2I-1R / Neutral-Extreme-direction.
8. **HVN/LVN proxy** מ-TPO (תחליף חלקי ל-real volume החסר).
**גבולות הספר:** אין בו ספי IB מספריים (הכימות פרסנטיילי שלנו נשאר שלנו), אין poor highs/lows (זה מהספרים המאוחרים של דלטון), ונתוני ה-Special Situations נמדדו על אג"ח 86–87 — נכון לאמת אותם על MES לפני שמקדדים כמשקולות.
