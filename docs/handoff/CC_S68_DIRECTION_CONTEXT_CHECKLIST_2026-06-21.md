# #68 Direction-Context — אינדקס-לעומק + צ'קליסט (TO-DO + TO-CLARIFY) · 2026-06-21

**מטרה:** שכבה אחת משותפת שקובעת **כיוון** בכל רגע — מ-(1) מיקום במרחב, (2) CVD, (3) נקודות-מפתח, (4) סוג-יום — שהתבניות/השער מתייעצים בה. התבניות הן טריגרים; הכיוון הוא קביעה נפרדת ורציפה.
**מקור-עובדות:** audit קוד+DB חי (Cowork 2026-06-21), אינדקס מרוענן. **לא שונה קוד.**

---

## A. אינדקס-לעומק — כל המשטחים המעורבים

### A1. קלטים / נתונים (זמינות בזמן-ירי — מאומת)
| קלט | מקור | זמין ב-`cross_context` בזמן-ירי? |
|---|---|---|
| **סוג-יום** | S1 `extract_g1_entry_context` (`S1_NEW_CLASSIFIER=1`) | ✅ |
| **מיקום + נקודות** (POC/VAH/VAL/IBH/IBL) | `cross_context.tpo_system` | ✅ (אומת: `poc/vah/val/ib_high/ib_low`) |
| **קצוות-סשן** (לזיהוי פריצה) `session_high/low` | TPO / bars | ❌ **חסר** — לכן breakout-state ב-position-gate נופל fail-open |
| **CVD** | `v9_bars_5min.cumulative_delta` + טבלה `v9_bars_cumulative_delta` (179 שורות/06-18) | ❌ **לא מוזרם ל-fire** (קיים ב-DB, לא ב-cross_context) |
| **אות-קבלת-פריצה** (sides = פריצה+ווליום≥8%, מוחזק≥2) | S1 `relative_features.sides` | ❌ לא נחשף ל-שער/תבניות |

### A2. מי קובע כיוון היום (audit)
- **S4** (9 תבניות: ZLR/TLB/TT/GB100/VEGAS/GHOST/FAMIR/HTLB/HFE): **גיאומטריית CCI בלבד** (+`trend_state` ל-TT/GB100, DLL ל-HFE). פרמטר `context` מושחל ל-detectors אבל **מת** (אף אחד לא קורא). אין location/CVD/keypoints/day_type. CVD **חסר לגמרי** ב-woodies.
- **S2 · REACTIVE**: מבנה-נרות (מוכרים→ירידה→קונים) + `belly` + כיוון `poc_vol`. CVD-proxy (COT/AMT) **מושבת** (S2⟂S3). `_detect_initiative` — counterpart, לא נקרא לעומק (לאמת).

### A3. שערים / ניהול (מצב נוכחי)
| רכיב | מצב | הערה |
|---|---|---|
| `daytype_position_gate` | ✅ ON (SHADOW) | location→כיוון; **breakout-state מנוון** (אין session extremes) |
| `structural_targets` | ✅ ON (SHADOW) | C1/C2/C3; **חוזים שגויים** (Neutral 1/2, צ"ל 3) |
| `daytype_playbook` verdict | ✅ ON | מדכא תבניות (SKIP/REDUCED) — **לנטרל** (כל התבניות יורות) |
| `trend_direction_gate` / `reactive_location_gate` | superseded | מבוטלים-אוטו' כש-position-gate ON |
| `manager` + `RUNNER_TRAIL_V1` | ✅ | trail — שימוש-חוזר |

### A4. דגלים
- **ON:** `S1_NEW_CLASSIFIER` · `DAYTYPE_PLAYBOOK` · `DAYTYPE_POSITION_GATE` · `DAYTYPE_TARGETS_STRUCTURAL` · `TREND_DIRECTION_GATE`(superseded) · `REACTIVE_LOCATION_GATE`(superseded) · `RUNNER_TRAIL_V1` · `STOP_ANCHORS_V2`.
- **OFF-קבוע:** `S2_REQUIRE_COT_AMT` · `LAYER0_CHOP_GATE` · `S2_CHOPPINESS_GATE`.

### A5. קונפיג
`config/daytype_playbook.yaml` (`daytype_style` + `patterns`) · `config/daytype_trading_plan.yaml`.

---

## B. TO-CLARIFY — להכריע לפני בנייה (החלטות פתוחות)
1. **קבלה מול דחייה של פריצה — הכלל המדויק?** מחיר מחזיק מעבר ל-IB בזמן-ירי? `sides` (≥8% ווליום, ≥2 ברים)? שילוב? (זה הלב.)
2. **CVD — איזה מקור** (`cumulative_delta` של הבר מול הטבלה הייעודית), **והאם הוא חי/טרי** בזמן-ירי (לא רק היסטורי)? ואיך משתמשים בו לכיוון — אישור-המהלך / דיברגנס בקצה?
3. **"כל התבניות יורות"** — חל גם על Nontrend, או Nontrend = לעמוד-בצד? להסיר `require_with_trend`?
4. **כשהארבעה סותרים** (מיקום=דהה מול CVD=מהלך-חזק) — מי גובר? סדר-עדיפויות/משקל.
5. **direction-context = וטו** (חוסם תבנית נגד-ההקשר) **או override** (כופה כיוון)? המלצה: וטו.
6. **שעה-ראשונה** (טרם נעילת-IB) — provisional / לא-לסחור?
7. **3 חוזים** — להגדיר C2/C3 ל-Neutral_Center; חריג Nontrend.
8. **רציף (per-bar) מול בזמן-ירי** — אמרת "לתשאל כל הזמן" → per-bar.

---

## C. TO-DO — בנייה (מסודר; כל שלב flag-gated + טסטים אנטי-טאוטולוגיים)
1. **תיקון `structural_targets`:** כל סוגי-המסחר → **3 חוזים** (+ הגדרת C2/C3 ל-Neutral_Center).
2. **נטרול דיכוי-תבניות ב-playbook:** כל התבניות יורות (Nontrend לפי החלטה §B3); השער היחיד = כיוון.
3. **צנרת (plumbing) — לחשוף בזמן-ירי ב-`cross_context`:** `session_high/low` (breakout-state) + **CVD** (`cumulative_delta`) + `sides` של S1.
4. **לבנות `direction_context` resolver:** מאחד מיקום+CVD+נקודות+סוג-יום → `{auction_bias, breakout_state, allowed_directions}`. **per-bar** (רציף). כאן חי "פריצה-שנכשלה→דהה / שהצליחה→לך-עם-בפולבק".
5. **לחווט את ה-resolver:** S4 דרך פרמטר `context` (המת-המוכן) + S2 דרך `cross_context` — כ**וטו-כיוון** לפני ירי.
6. **להחליף** את כללי-ה-per-day-type ב-`daytype_position_gate` ב-resolver (breakout-state + מיקום + CVD).
7. **טסטים + הדלקה ב-SHADOW + אימות גולמי** (Rule 5).

---

## D. אימות / "פועל כראוי למסחר הבא"
- **חי עכשיו** (הודלק 06-21): `daytype_position_gate` + `structural_targets` ב-SHADOW. (אבל breakout-state מנוון עד שמוזרמים session extremes — §C3.)
- **SHADOW לוג** פר-בר + פר-ירי: ה-bias שנקבע · breakout_state · CVD · האם התבנית התיישרה/נחסמה.
- **ניטור יום-המסחר-הבא:** `[Gateway] ... daytype_position_gate` + `day_type_at_entry` + (אחרי §C) לוג ה-`direction_context`.
- **כנות:** זה build רב-שלבי; אימות-אמת דורש ימי-SHADOW חיים. כדי שייכנס ראוי למסחר-הבא צריך לפחות §C1+§C2+§C3 (חוזים, כל-התבניות, צנרת-הקלטים) — ה-resolver המלא (§C4-6) יכול להגיע אחריו בלי לחסום.

---

## E. סדר מומלץ למסחר-הבא (מינימום פועל)
1. §C1 (3 חוזים) + §C2 (כל התבניות) — תיקוני-החלטות-אתמול, מהירים.
2. §C3 (צנרת: session extremes + CVD) — בלי זה ה-breakout-state וה-CVD לא קיימים בכלל.
3. §B1+§B2 (להכריע כלל-קבלה + מקור-CVD) → §C4-6 (resolver מלא).
כל שלב: flag-gated, SHADOW, אימות. ללא commit עד הוראת-Michael.
