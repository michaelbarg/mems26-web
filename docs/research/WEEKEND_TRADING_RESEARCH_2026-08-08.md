# מחקר-סופ"ש 2026-08-08 — שישי-בדיעבד · דיוק-S1 שבועי · דלתון-שעה-ראשונה · Pullback · קונפלואנס S2×S4 · Counter-Extreme

**סוכן:** weekend-research-agent (cowork) · **מצב:** read-only (אפס שינויי-קוד/דגלים) · **Rule-5:** כל מספר מגובה בשאילתה/פלט.
**מקורות:** `v9_bars_5min_woodies` (ts=שעון-ישראל, אומת מול IB של מייקל 7743.25/7780.5) · `gateway_decisions.jsonl` ·
`v9_trades` · `v9_day_type_state/history/archive` · קוד HEAD `09e98799` · `.env` חי (נטען עם `flag_guard.parse_env`).

---

## §1 · שישי 08-07 — ביקורת-סשן מלאה

### 1.1 מה קרה בשוק (ברים, שעון-IL)
- פתיחה 16:30 @7757.25 → דחף-מטה ל-**IB-low 7743.25 @17:10** → V-reversal חד (17:15 בר 7744→7765.75) → **IB-high 7780.5 @17:25**.
  IB רחב 37.25pt (יום-NFP — ספייק 15:30 IL). Opening=OPEN_REJECTION_REVERSE (נשמר ב-archive).
- **הרגל-UP:** פולבק 17:35–17:50 ל-7764.5 (מעל IB-mid 7761.9) → עליות-מדורגות עד **שיא-יום 7786.75 @18:25–18:30**
  (הרחבה חד-צדדית +6.25 מעל IB-high; אין הרחבה מטה — Variation-up קלאסי).
- אחה"צ: דחייה מהשיא → 19:20–19:30 ירידה ל-7757.75 → רוטציה 7756–7772 → ראלי-סגירה 22:00–22:55 עד 7785.5 → סגירה 7776 (close_pos 0.75).

### 1.2 מה המערכת עשתה — 51 החלטות-gateway, **2 עסקאות-live (לא 0!)**
ספירת-חוסמים (08-07, מ-`gateway_decisions.jsonl`): `awaiting_release`×23 · `rr_entry_gate`×7 · `daytype_playbook`×5 ·
`cont_trend_filter`×4 · `pattern_stop_cooldown`×3 · `direction_context`×2 · `eod/session`×5 · **routed×2**.

```
#650 live S4 ZLR LONG  18:40:13 @7783.75 stop=7778 T1=7788.5 → STOP_FILL 18:41:52 = −$86.25 (−1R, 99 שניות)
#652 live S4 GHOST SHORT 19:35:04 ep=7783.00(!) stop=7772.25 → SIERRA_FLAT 23:00:20, pnl=0.0, exit_price=None
```
🔴 **#652 = אנומליית-רישום:** שורט ב-19:35 כשהשוק ב-7764–7771 לא יכול להתמלא ב-7783.00 (התאום-shadow #651: e=7767, STOP −$78.75).
pnl=$0 עם exit_price=None ו-pnl_sierra=None — אותה משפחת-חשבונאות כמו #640. **לפיוס מול fills-journal ביום ראשון.**

### 1.3 האנטומיה של הפספוס — הצירוף הפוך את לוגיקת-הכניסה
1. **17:45+17:55 IL — כניסות-הפולבק האמיתיות** (ZLR LONG @7771.25/@7770.25) נחסמו `awaiting_release`:
   *"structure not turning (1/2 higher lows)"*. בהגדרה — בזמן פולבק המבנה עוד לא התהפך; השער משחרר רק אחרי שהמהלך ברח.
   כניסה שם: סטופ מבני ~7763.5 (מתחת ללואו-הפולבק 7764.5) ≈ 7–8pt, T1=IB-high 7780.5 ≈ +9.5pt → **R:R≈1.2–1.4, עובר את שער-ה-0.65**. T1 היה נפגע ב-18:10 (H7781.75). שווי מוערך: **+$45–95** (3 חוזים, T1+2×BE).
2. **18:00–18:20 — אשכול ה-rr_entry_gate (6 חסימות ZLR LONG @7776–7778):** `T1_dist=2.5–4.5 < stop~8×0.65`.
   **המתמטיקה של השער נכונה** — אבל הסיבה ש-T1 קרוב היא שהכניסה מאחרת: המחיר כבר עמד 2–4pt מתחת ל-IB-high.
   (בדיעבד כולן היו נוגעות ב-T1 לפני הסטופ — אבל זו לא הצדקה לכניסת-R:R-רע; זו הוכחה שהכניסה הנכונה הייתה מוקדם יותר.)
3. **18:40 — היחידה שעברה = הגרועה ביותר:** #650 LONG @7783.75, **3pt משיא-היום**, T1=7788.5 **מעל השיא הסופי (7786.75)** — סטופ תוך 99ש'. `EXTREME_CHASE_GUARD_V1=1` חי אבל ה-"with-pullback→ALLOW" שלו אישר, כי פולבק *כבר קרה* — הכניסה הייתה על ההחזרה-לשיא, לא בתוך-הפולבק. חסימות-ה-chase של ה-playbook (dist<9.3pt) תפסו את S2 REACTIVE (15:15/15:30 UTC) — **אבל לא את מסלול ה-S4 ZLR**. אסימטריה מסוכנת.
4. **18:40 — הפייד שנחסם קטגורית:** REACTIVE_SHORT @7781.5 (`daytype_playbook`: *"fade only after rebalance"* ב-EXPANSION).
   הקצה 7786.75 עונה על ספי-EXCESS של המנוע (זנב 2.5–5pt בברים 18:25/18:30, אין-revisit ≥3 ברים — חישוב מהברים).
   סטופ מעל השיא ~6.5pt, MFE 23.75pt (→7757.75 תוך 50 דק') → שווי מוערך **+$150–250**. אין שום מסלול במערכת שמסוגל לקחת אותו היום (ר' §6).
5. **קרדיט לשערים:** `direction_context` חסם 2 לונגים @7780.25/7780.5 ב-19:05/19:10 — שניהם היו נסטפים (ירידה ל-7757.75) → **חסך ≈$240**. `cont_trend` חסם 2 לונגים @7768 ב-16:45 בזמן דחף-הפתיחה-מטה (→7743.25) → **חסך ≈$240**. (חסימת GB100 @7766 ב-17:20 דווקא עלתה ~+$50 — מעורב.)

### 1.4 פסק-דין כן
- **לדלג על רוב היום — נכון.** אחרי 18:00 המבנה באמת לא נתן with-trend R:R תקין, והשערים חסכו ≈$480 ריאלי.
- **אבל הצירוף awaiting_release→rr_entry→chase הפוך את העסקה:** חיכה בזמן-הפולבק (הזמן הנכון להיכנס), פסל את האמצע, ואישר את הקצה. ההפסד היחיד של היום (−$86) הוא בדיוק ה-anti-pattern.
- **שווי ריאלי שנשאר על השולחן:** ≈**$200–350** נטו (פולבק-לונג +$45–95, פייד-קצה +$150–250, מניעת-הצ'ייס +$86 — בניכוי אי-ודאויות מילוי/ניהול). לא יום-זהב שפוספס — אבל יום-חיובי-קטן שהפך ל-−$86.

---

## §2 · דיוק-S1 בשבוע 08-03…08-07

### 2.1 מה המערכת אמרה בזמן-אמת (DB: archive/history/state) מול מייקל
| יום | Live final (archive) | קריאת-מייקל (EOD) | Live נכון? | קוד-נוכחי על ברי-woodies (בדגלי-.env) |
|---|---|---|---|---|
| 08-03 | Variation 62% | **Trend_Normal** ✓שלו | ✗ (סוג) / ✓ (משפחה-כיוונית) | Normal_Variation up, rib 1.67, cp 0.90 |
| 08-04 | Trend_Normal 75% | **Trend up** | ✓✓ | Trend_Normal (control-path: 6 מדרגות) — **על 41 ברים בלבד (פיד נקטע 19:50)** |
| 08-05 | Variation **conf 0.0** (כותב-תקוע) | **?** | — | NV **down**, rib 2.92, cp 0.10 → לפי היריסטיקת-דלתון של האודיט (rib≥2.5+cp≤0.15) זה **Trend-down**. ממתין לקריאת-מייקל |
| 08-06 | Neutral_Center 67% | **Variation-down** | ✗ EOD (נעילת-17:30 הראשונה דווקא אמרה Variation-down ✓, התהפכה 18:20 מדקירת-1-בר) | **Normal_Variation down ✓** (תיקון-P0.5 עובד גם על ברי-DB) |
| 08-07 | Variation 62% (ננעל 17:30, החזיק עד 23:00, 47 שורות, 0 היפוכים) | **Variation-up** | ✓✓ | **Normal_Variation up ✓** |

**ציון השבוע (זמן-אמת):** EOD מדויק **2/4** ידועים (04,07) · משפחה-כיוונית **4/4** · נעילה-ראשונה-נכונה 3/4 (גם 06!).
תקלות-תפעול שפגעו: 08-04 פיד-מת 19:50 (41 ברים) · 08-05 כותב-סוג-יום conf-0 (התקיעה של 2h15m) · 08-06 באג-הדקירה (תוקן P0.5).

### 2.2 איפה עומד המסווג-המתוקן ("13/13")
```
פקודה: classify_session על ברי-woodies RTH, .env נטען (DAYTYPE_SIDES_MECHANICAL_V1=1, IB_BREAK_ANY_EXPANSION_V1=1)
08-03 NV up · 08-04 Trend up · 08-05 NV down · 08-06 NV down ✓ · 08-07 NV up ✓
```
- ⚠️ **אזהרת-סביבה (נלמד היום בעצמי):** בלי טעינת .env המסווג נותן 08-07=**Normal** (sides=0) — נפילה למסלול-volume-acceptance הישן. כל replay/אודיט חייב `parse_env` קודם, אחרת מסקנות-שקר.
- **ה-13/13 אמיתי אבל צר:** הקריטריון של `classifier_truth_audit` הוא **balance-מול-directional (משפחה)**, לא סוג-מדויק, וההשוואה היא מול היריסטיקה-מבנית — לא מול קריאות-מייקל ישירות. 08-07 עוד לא היה בחלון-האודיט כשנטען 13/13.
- **הפער האמיתי שנשאר: Trend-recognition.** 03 (rib 1.67 < רצפת-1.8 של מסלול-ה-control) ו-05 (אין 3-מדרגות; rib 2.92 אבל בלי elongation-path) מסווגים NV בעוד מייקל/דלתון רואים Trend. זה בדיוק ה-NO-GO שנרשם ל-TREND_STOP_FLOOR ("the classifier does not produce Trend labels on truth bars"). המשפחה נכונה — האגרסיביות (playbook, סטופים, יעדים) לא.

---

## §3 · דלתון והשעה הראשונה — 10 שורות, ממופה למערכת

1. **ה-IB הוא "בסיס-היום"** (p.11,19): בסיס-צר → צפוי-שבירה (trend-watch); בסיס-רחב → הקצוות כנראה יחזיקו. ✅ מיושם (IB-60min, `ib_narrow`≤0.7×median, rib) · ❌ צר-כ-prior-מוקדם ל-trend לא ממומש (P0-2 בבקלוג).
2. **סטטיסטיקת-על:** H/L-של-היום נקבע בשעה-הראשונה ב-**~75%** מהימים (30 דק' ≈ 50%) — קצה-ה-IB הוא מיקום-העסקה הכי חשוב ביום. ❌ לא מקודד כ-prior לשום שער (rr, playbook, edge-fade).
3. **"The open foreshadows the day"** (p.63): conviction נקרא **בדקות הראשונות**, לא אחרי 12 ברים. ✅ `opening_detector_v2` חי עם 5 הסוגים + `OPENING_TYPE_GATE=1` · ❌ המסווג-הקנוני FORMING עד 12 ברים — התחזית-מהפתיחה נזרקת (סתירה מתועדת ב-DALTON_DOCTRINE.md §3.1).
4. **Open-Drive** (pp.63-65) = הכרעה-קדם-פתיחה; דלתון נכנס **מוקדם, עם-הכיוון, "one step ahead of structure"**, סטופ=מקור-הדרייב; חזרה-דרך-המקור=יציאה. ✅ יש OPENING_DRIVE pattern (2 עסקאות-live, −$262 — כניסות מאוחרות-בדרייב) + exhaustion-veto נבנה (flag-OFF, replay GO $401) · ❌ אין "כניסה-מוקדמת-בדרייב" אמיתית עם סטופ-מקור.
5. **Open-Test-Drive** (pp.65-67): טסט-כושל של רפרנס → דרייב הפוך; הקצה השני-הכי-אמין. דלתון נכנס על ההיפוך-דרך-הפתיחה. שישי היה בדיוק כזה (טסט 7743→דרייב-אפ) — ❌ אין לנו pattern כזה; ה-ORR שלנו קרוב אבל נסחר רק בחלון-הפתיחה.
6. **Open-Rejection-Reverse / Open-Auction** = דו-צדדי/חוסר-שכנוע → דלתון סוחר **responsive בקצוות, בסייז קטן**, או עומד בצד (OA-in-range: "big day unlikely"). ✅ הזיהוי חי · ❌ ההתאמה היחידה היא חסימות (playbook) — אין מסלול-responsive-בקצה (ר' §6).
7. **גאפ שלא נסגר בשעה הראשונה → המשך** (p.293); סטופ=מחיקת-הגאפ. ❌ לא מחווט (מתועד כ-gap ב-doctrine-doc).
8. **סייזינג לפי conviction-הפתיחה:** דרייב=גדול-ומוקדם; test-drive=בינוני; ORR/OA=קטן-responsive. ❌ אצלנו הסייז קבוע (FIXED_CONTRACTS); conviction לא משנה דבר.
9. **מסקנת-החיבור לשישי:** דלתון היה קונה את ה-pullback הראשון אחרי פריצת-IB-high (17:35-17:50) — כי ביום-Variation ההרחבה נוטה להחזיק — ומפייד את קצה-ה-EXCESS ב-18:40. המערכת עשתה את ההפך המדויק.
10. **מקורות:** `docs/spec_authority/DALTON_DOCTRINE.md` (מיפוי-עמודים מלא) + [ThreadReader — MOM open types](https://threadreaderapp.com/thread/1266594167347646465.html) · [Reading the Markets review](http://readingthemarkets.blogspot.com/2013/07/dalton-jones-dalton-mind-over-markets.html) · [Nature of Markets — opening types course](https://www.thenatureofmarkets.com/market-profile-course-3-opening-types-open-range-strategy-and-practical-applications/).

---

## §4 · תבנית-Pullback — יש לנו או אין לנו?

**התשובה: יש *מודול* — אין *מסלול*.**
- **`higher_low_second_test.py` (HLST, W6, 25.07)** — בדיוק המנדט של מייקל ("ירידה בפעם השנייה → רכישה בחלק הגבוה"):
  push→L1→recovery≥33%→L2>L1→בר-דחייה. **אפס callers בכל ה-backend** (grep: הקובץ היחיד שמזכיר את עצמו), הדגל
  `HIGHER_LOW_SECOND_TEST_V1` לא ב-.env, ברגיסטרי: *"OFF, definition awaiting Michael approval"*. **מודול-מת מחווט-לא.**
- **ZLR (S4)** הוא "pullback-לפי-CCI" רעיונית, אבל בפועל יורה על *ההתהפכות אחרי* הפולבק, ואז `awaiting_release`
  (RELEASE_MIN_HIGHER_LOWS=2) דוחה עוד — הכניסה יוצאת על ההחזרה-לקצה. **סטטיסטיקת-live מ-07-15: ZLR n=19 → 6W/13L, −$396.25** (shadow: 75 → 27W/41L, −$566). זה מחיר-הצ'ייס במצטבר.
- קרובים-אבל-לא: `BULL/BEAR_FLAG` (S2, live 3 שורטים −$51) · `OPENING_PULLBACK_CONT` (חלון-פתיחה בלבד, 1 shadow −$216) · `EXTREME_CHASE_GUARD` (חוסם-chase אבל "with-pullback→ALLOW" מאשר החזרה-לשיא, ר' §1.3-3).
- **מה חסר ל-"pullback-to-LSMA/IB-edge ביום trend/variation" נקי:**
  1. **טריגר-מיקום, לא טריגר-מומנטום:** זרוע-כניסה כשמחיר *בתוך* אזור-הפולבק (מגע-LSMA ±1pt / קצה-IB-שנפרץ ±2pt / 38-50% מהרגל) בכיוון-הרגל — לא אחרי higher-lows.
  2. **סטופ-מבני מתחת-לפולבק** (לא 8pt גנרי) — ואז ה-rr_entry_gate עובר מעצמו (T1=קצה קודם רחוק).
  3. **חיווט HLST** ל-five_min_system (flag-OFF→shadow→replay) — המודול כבר כתוב וסימטרי.
  4. **תיקון-האסימטריה:** ה-chase-block של ה-playbook חייב לכסות גם S4-CONT (ZLR@3pt-מהשיא לא יכול לעבור כשREACTIVE@6pt נחסם).
  5. קליברציה על שישי כ-fixture: 17:45/17:55 חייבות-לעבור, 18:40 חייבת-להיחסם.

---

## §5 · קונפלואנס S2×S4 — האם הסכמה מעלה הצלחה? **כן.**

**מתודולוגיה:** כל `v9_trades` (S2/S4, כל mode, 06-05→08-07, n=526 שורות) → דדופ תאומי-live/shadow (אותה מערכת+כיוון+90ש'+1.5pt)
→ **435 אירועי-ירי** (166 S2, 269 S4) → "קונפלואנטי" = אירוע-מערכת-שנייה באותו כיוון בטווח ±10 דק'. outcome לפי live>demo>shadow.
```
CONFLUENT: n=69  W=42 L=23  wr=65%  avg$=+6.4   sum=+$440
SOLO     : n=366 W=167 L=170 wr=50% avg$=−20.2  sum=−$7,187
conf-S4: n=37 wr=72% avg=+$17.7 · conf-S2: n=32 wr=55% avg=−$6.7 (סולו-S2: 46%, −$35.9)
ROUTED-בלבד (live+demo): conf n=10 → 7W/1L (88%), avg +$44 · solo n=83 → 52%, avg +$8.5
מ-07-15 (עידן-השערים הנוכחי): conf n=10 → 8W/2L (80%), avg +$68.2 · solo n=134 → 40%, avg −$19.2
```
דוגמאות טריות: 08-04 17:35 REACTIVE_LONG(live +$200)+ZLR(+$205) · 08-05 18:15-25 ZLR-SHORT(+$284)+INITIATIVE_SHORT(live +$75) · 08-06 18:55 REACTIVE_SHORT(live +$49)+ZLR(+$15).
**כנות (n=):** תאי-ה-routed וה-recent הם n=10 — מגמה עקבית בכל חתך אבל לא הוכחה סטטיסטית חזקה (הפול המלא 65W+L: z≈2.4, p≈0.02, עם ערבוב-מודים ושערים-שהשתנו). שני הצדדים של זוג נספרים (אותו רגע-שוק). **מסקנה זהירה:** confluence-tag שווה לפחות כ-quality-boost (סייז/priority), לא כשער-קשיח.

---

## §6 · יכולת Counter-Extreme — האם המערכת יכולה לפייד קצה-EXCESS היום? **לא.**

**מה חי:** מנוע-הקצוות (`extremes_quality.py`) מזהה EXCESS/POOR ✅ (אומת 08-06: low=EXCESS 5.25pt) · צריכת-**יציאה**
`EXTREMES_AWARE_REALIZE_V1=1` **דלוקה** (replay GO +$410) · radar מציג.
**מה חסום/כבוי/לא-קיים בצד-הכניסה:**
1. **אין קונסיומר-כניסה ל-EXCESS** — פריט-5 בפקודת-07.08, לא נבנה (grep gateway: אפס אזכורי-extremes). הרוטציה 7724→7745 (06.08) והפייד 7781.5 (07.08) עברו בלי-עסקה.
2. **EDGE_FADE_V1 כבוי** אחרי replays NO-GO (N1 −12.8pt/11 כניסות; contained-NV −20pt/7) — **השורש המתועד: זיהוי-ימי-balance במסווג**, לא לוגיקת-הפייד. נשאר OFF עד scid-replay ירוק (פסיקת-02.08).
3. **P1-4 `BALANCE_EDGE_EXEMPT_V1` נבנה 08-07, flag-OFF** (7/7 טסטים, ממתין-replay) — אבל הוא רק *פוטר מ-direction_context*, רק ב-regime=BALANCE/TRANSITIONAL, בקצה-סשן ≤2pt. הוא **לא היה עוזר בשישי**: החסימה שם הייתה `daytype_playbook` ("fade only after rebalance" ב-EXPANSION, `daytype_playbook.py:255`) — שער אחר, יום-Variation.
4. אין דרישת-EXCESS-quality בשום שער-כניסה (ה-playbook חוסם לפי phase בלבד; חתימת-הדחייה לא נבדקת).

**מה נדרש כדי לעשות את זה בטוח (צעדים קונקרטיים, לפי הסדר):**
א. לחווט קונסיומר-EXCESS ל-S2-REACTIVE: תנאי-שחרור = extremes.quality=EXCESS בקצה-הרלוונטי + מרחק-קצה ≤2pt + בר-דחייה — flag-OFF.
ב. להוסיף ל-`daytype_playbook` חריג-EXPANSION: פייד מותר **רק** עם EXCESS מאושר + סטופ מעבר-לזנב (שישי 18:40: סטופ 7788 = זנב+1).
ג. ניהול ייעודי: T1=IB-mid/VA-edge (לא ladder-מגמה), scratch מהיר אם הקצה נפרץ.
ד. Replay על 06-08+07-08 (שני ימי-הראיה) + 14 ימי-scid → פסיקת-מייקל אחת → enable. (EDGE_FADE עצמו ממתין ממילא לתיקון-ה-Trend/balance-labels מ-§2.2.)

---

## §7 · מה לבנות/לתקן ליום שני — מדורג

1. **P0 חשבונאות: פיוס #652** (ep=7783 בלתי-אפשרי, pnl=$0 לא-מאומת) מול fills-journal + guard על entry_price≠מחיר-שוק (>5pt) בזמן-מילוי. אמת-הכסף קודמת לכל.
2. **מסלול-Pullback (הפער-של-שישי):** חיווט HLST flag-OFF + טריגר-מיקום-בפולבק (LSMA/IB-edge) + סטופ-מבני — קליברציה: 17:45✓/18:40✗. זה מקור ה-−$396 של ZLR-live ושל ה-−$86 של שישי.
3. **סגירת אסימטריית-ה-chase:** playbook/chase-guard חלים גם על S4-CONT; "with-pullback→ALLOW" מותנה במחיר-בתוך-הזון (לא החזרה-לקצה).
4. **קונסיומר-EXCESS לכניסה (§6-א,ב)** — flag-OFF + replay. משלים את P1-4 שכבר בנוי.
5. **Trend-recognition (הפער שנשאר ב-S1):** מסלול-elongation ל-03/05 (rib≥2.5+cp-קיצון בלי דרישת-מדרגות, או הורדת רצפת-1.8) — זה מה שחוסם גם את TREND_STOP_FLOOR וגם את EDGE_FADE.
6. **Confluence-boost:** תיוג-קונפלואנס במטא של ה-fire (כבר יש CONFLUENCE_RI_ZLR ראשוני) + priority/size-hint. לא שער-קשיח (n=10).
7. **דלתון-פתיחה:** Open-Test-Drive pattern (שישי היה כזה) + prior "75% H/L בשעה-הראשונה" כקלט ל-rr/playbook.
8. תפעול: retention ל-`v9_day_type_state` (03-05 נמחקו — אי-אפשר לבקר intraday רטרואקטיבית) + תזכורת: כל replay עם `parse_env`.

*נכתב ע"י weekend-research-agent · 2026-08-08 · read-only, שינויים: הדוח הזה + שורת-LIVE_CHANNEL בלבד.*
