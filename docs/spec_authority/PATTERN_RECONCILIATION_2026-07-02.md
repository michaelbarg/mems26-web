# MEMS26 — יישוב מפרט התבניות · Pattern Reconciliation (2026-07-02, Cowork)

**מטרה:** מפרט אחד ללא-סתירות ל-16 התבניות הפעילות — זיהוי · הרשאת-יום · סיזינג · יעדים —
כשה-HTML הנערך של מיכאל (`PATTERN_PLAYBOOK_CANDLES.html` + `RESOLVER_TARGETS_BY_DAYTYPE.html`)
הוא המקור שהקוד מאומת מולו. **Read-only:** לא שונה קוד/קונפיג/דגל. כל ממצא עם file:line.

**מקורות שהוצלבו (עם תאריך):**
קוד חי: `daytype_position_gate.py` (משפחות+גייט) · `daytype_playbook.py` + `config/daytype_playbook.yaml` ·
`auth_table_v1.py` + `quality_tier.py` (V1 נעול 05-25) · `structural_targets.py` (168391c, 07-01) ·
`trading_gateway.py` · `sierra_command.py` · `config/stop_anchors.yaml` · `config/targets.yaml` ·
תבניות `five_min/patterns/*` + `woodies/patterns/*`.
ספק: Playbook-HTML (07-01 20:38) · Resolver-HTML (07-01 20:23) · `S1_TRADE_MANAGEMENT_3CONTRACTS.md` (06-20) ·
`MEMS26_Auth_Table_V2_cells.csv` (05-31) · `S4_WOODIES_TABLE_A/B/C` (05-25) · `PATTERN_ACCESS_MAP.md` (06-28) ·
`PATTERN_DEFINITIONS_INDEX.md` (06-26) · `docs/FLAG_INDEX.md` (07-01 22:09).

---

## שורה תחתונה (5 נקודות)

1. **שלוש שכבות-הרשאה פעילות במקביל** על אותה שאלה (תבנית×יום) — Auth-verdicts בפליטת S2,
   מטריצת playbook.yaml בגייטוויי (**חזרה להיות פעילה בשקט** מאז `DAYTYPE_POSITION_GATE=0`),
   ו-PATTERN_AWARE_V1 (רדום). הן **לא מסכימות** על ~8 תאים חמים. נדרשת טבלת-פסיקה אחת.
2. **הרזולבר בקוד מיישם את ספק 06-20, לא את ספק 07-01.** ה-split החדש של מיכאל (C1=swing ·
   C2=מבנה-קרוב<קצה-ערך · C3=קצה-ערך) קיים **רק ב-Variation**. Normal/Neutral/Trend עדיין בסולם הישן.
3. **כל מספרי-החוזים בטבלאות מתים בפועל:** הקוד מריץ Auth **V1** (מקס' 3), ה-CSV **V2** (מקס' 5) מעולם
   לא חוּוט (44/70 תאים שונים), ו-`FIXED_CONTRACTS_3=1` דורס הכל ל-3. שכבת ה-**verdict** (FULL/REDUCED/SKIP)
   זהה 70/70 בין V1 ל-V2 — היא השכבה החיה היחידה.
4. **REACTIVE×Variation הוא התא החם:** כל שכבה חיה מתירה counter-fade בווריאציה — בניגוד לעקרון
   06-20 ("ימי-כיוון: fade נגד נחסם"). זה בדיוק ה−2R של 269/270 ב-07-01.
5. **התיעוד המפת-גישה מפגר אחרי הקוד** בשלוש נקודות מסוכנות (REACTIVE מסווג CONT · עוגן-ZLR ישן ·
   כרטיסי VEGAS/GHOST מתארים גאומטריה אחרת מהקוד).

---

## §1 · מצב פר-תבנית (16)

מקרא: 🟢 מיושר · 🟡 סתירה נקודתית/תיעוד · 🔴 דרושה פסיקת-מיכאל.
"הרשאת-יום" = auth-code (S2, בפליטה) / playbook.yaml (חי עכשיו בגייטוויי) / TableB (מסמך S4).

| # | תבנית | משפחה (קוד) | זיהוי: HTML↔קוד | הרשאת-יום — סתירות | סטופ (config חי) | פסק |
|---|--------|--------------|------------------|----------------------|-------------------|------|
| 1 | ZLR | CONT ✓ | ✓ (V2 stage-machine; כניסה=close) | NeuC: playbook=SKIP vs TableB=⚠️scalp | `breakout_bar` w1 ·15pt (מיכאל 06-30) — **המסמכים עוד אומרים cluster_low w4** | 🟡 |
| 2 | TLB | CONT ✓ | 🟡 HTML לא מזכיר את שער-V2 (±200 תוך 12 ברים + פרטנר CONT, `tlb.py:134`) | NeuE: playbook=REDUCED vs TableB=❌ | `since_trendline_peak` w8 ·15pt ✓ | 🟡 (+Stage-2 לא בנוי) |
| 3 | TT | CONT ✓ | ✓ | **TN/TDD: playbook=REDUCED vs TableB=✅ "made for TN"** · 0 ירי אי-פעם | `zl_excursion` w9 ·15pt | 🔴 לאפיין או לפרוש |
| 4 | GB100 | CONT ✓ | ✓ | TN/TDD: playbook=REDUCED vs TableB=✅ | `cluster_low` w6 ·15pt ✓ | 🟡 |
| 5 | INITIATIVE | CONT ✓ | ✓ (b1-b4, כניסה=b4) | **Normal: auth=SKIP (חוסם בפליטה) vs playbook=REDUCED vs כרטיס-HTML מציג סולם-Normal** | `breakout_bar` w1 ·12pt הדוק ✓ | 🔴 לפסוק Normal |
| 6 | BULL/BEAR_FLAG | CONT ✓ | ✓ (מוט-דגל-פריצה) | ✓ (auth↔playbook תואמים ברמת-verdict) | `breakout_bar` w1 ·15pt · flag_relative_t1 ✓ | 🟢 |
| 7 | REACTIVE | **REV** ✓ (`daytype_position_gate.py:38`) | ✓ (4-bar VSA) | **Variation: כולם FULL → counter-fade עובר (־2R ב-07-01)** · TN/TDD: auth=REDUCED vs playbook=FULL+with-trend | `support_zone` w4 ·15pt ✓ | 🔴 התא החם |
| 8 | VEGAS | REV ✓ | 🔴 **כרטיס-HTML = hook-מקיצון; הקוד = cup&handle** (`VEGAS_SPEC_V2`, `vegas.py:205`) | TN/TDD=SKIP בכולם ✓ · Variation: playbook=REDUCED vs TableB=⚠️סוף-סשן | `swing_extreme` ·20pt · מקדמי-measure בקונפיג מתים כש-structural=ON | 🔴 לעדכן כרטיס |
| 9 | GHOST | REV ✓ | 🔴 **כרטיס-HTML = failed-high במחיר; הקוד = CCI-H&S** | כמו VEGAS ✓ | `shoulder` ·18pt ✓ | 🔴 לעדכן כרטיס |
| 10 | FAMIR | REV ✓ | 🟡 קרוב (קוד=ZLR-שנכשל ב-±200; כרטיס=פריצה-שנכשלה כללי) | כמו VEGAS ✓ | `failed_bar` ·12pt ✓ | 🟡 |
| 11 | HTLB | REV ✓ | ✓ + תפקיד-כיוון (`HTLB_DIRECTION_GATE` ON) חסר בכרטיס | **TN/TDD: HTML="נחסם ביום-מגמה" vs playbook=FULL vs TableB=⚠️with-trend** | `consolidation_extreme` ·20pt — **מול מקור=בר-הפריצה, פתוח מ-06-26** | 🔴 לפסוק Trend+עוגן |
| 12 | DOUBLE_TOP_AA | REV ✓ | ✓ (M + neckline) | **TDD: auth=SKIP vs playbook(DBDT)=REDUCED** | `second_bottom_top` ·20pt ✓ | 🟡 |
| 13 | DOUBLE_BOTTOM_EE | REV ✓ | ✓ (W + neckline) | כנ"ל | כנ"ל ✓ | 🟡 |
| 14 | INVERSE_HNS | REV ✓ | ✓ (כתף-ראש-כתף, סטופ=כתף-ימין ✓) | **Variation: auth=REDUCED vs playbook(HNS)=FULL** · TN/TDD: auth=SKIP vs playbook=REDUCED+with-trend | `shoulder` ·20pt ✓ | 🟡 |
| 15 | HNS_TOP | REV ✓ | ✓ | כנ"ל | כנ"ל ✓ | 🟡 |
| 16 | HFE | REV · מושבת | ✓ `HFE_DISABLED=1` עקבי בכל השכבות | — | — | 🟢 (סגור) |

---

## §2 · ממצאים מרכזיים (עם ראיות)

### F-1 🔴 שלוש מטריצות-הרשאה חיות במקביל — ואף אחת לא הוכרזה קנונית
- **Auth verdicts** — `auth_table_v1.py` דרך `get_quality_tier_v2` (`quality_tier.py:78`) — חוסם בפליטת S2 (SKIP=אין setup). S2 בלבד; S4 לא מכוסה.
- **playbook.yaml** — `trading_gateway.py:270` קורא ל-`daytype_playbook.decide()`. ה-short-circuit ל-FULL קיים **רק כש-`DAYTYPE_POSITION_GATE=1`** (`daytype_playbook.py:105`). מאז 07-01 הדגל=0 (.env) → **המטריצה פעילה בפועל עכשיו** — שינוי-סלקטיביות שקט שאיש לא הכריז עליו. בנוסף: verdict=REDUCED **אינרטי** — הגייטוויי בודק רק `_pb.allow` (`trading_gateway.py:281`) ומתעלם מ-`Decision.contracts`; רק SKIP עושה משהו.
- **DAYTYPE_PATTERN_AWARE_V1** — ב-.env=1 אבל **רדום**: יושב בתוך `daytype_position_gate.decide()` שחוזר "gate OFF" כשהדגל-המארח=0 (`daytype_position_gate.py:89-90,101`). FLAG_INDEX מציג ✅ON בלי סימון-inert.
- **TableB** (S4_WOODIES_TABLE_B) — מסמך בלבד, לא מחווט, סותר את playbook.yaml (TT/GB100 על TN; ZLR על NeuC; VEGAS על Variation).
**פסיקה נדרשת:** טבלה קנונית אחת (מוצע: playbook.yaml כבסיס) + מה עושים עם המטריצה בזמן חלון-הולידציה.

### F-2 🔴 הרזולבר מיישם את 06-20; ספק 07-01 קיים רק ב-Variation
קוד ↔ `S1_TRADE_MANAGEMENT_3CONTRACTS.md` (06-20) — תואם כמעט אחד-לאחד:
Normal: C1=IB-center · C2=VAL/VAH · C3=IBL/IBH (`structural_targets.py:184-191`) = שורת-Normal של 06-20.
NeuE: C1=POC · C2=קצה-נגדי (`:271-278`) = 06-20. Trend_Normal: C1=checkpoint רחוק 2×IB (`:337`) = "checkpoint מדוד רחוק" של 06-20.
אבל **Resolver-HTML של 07-01** (חוקי-הבסיס: C1=swing-ראשון Williams K=2 · קאפ ≈14 · C2=מבנה-קרוב<קצה · C3=קצה-ערך)
מיושם רק ב-`_resolve_variation` (`:203-258`, swing_t1 + `_pick_nearest_structure` + family-split).
פערים נוספים מול ספק-07-01: (א) **קאפים רופפים** — קוד `max(2×ATR, 2×risk)` ל-C1 (`:417`) יכול להגיע
ל-30-50pt כשסטופ רחב, בעוד הספק קובע קאפ-הדוק ≈14 (min); רנר `max(6×ATR,6×risk)` עד ~90pt מול
`min(1.5×dATR, 3×IBw)`. (ב) ATR קשיח 7.0 (`:411`) — לא נמדד חי. (ג) שדות `contracts`/`time_stop`/`trail`
שהרזולבר מחזיר **לא נצרכים** — הגייטוויי לוקח רק את שלושת המחירים (`trading_gateway.py:420-425`).
(ד) אין בדיקת R:R לפני-כניסה ("מרחק-C1 < מרחק-סטופ → דלג") מ-06-20 — לא קיימת באף שכבה.
**פסיקה:** לאשרר את סולם-07-01 כמחליף את 06-20 פר-סוג-יום → handoff ל-CC ליישור Normal/NeuE/NeuC/TN/TDD + קאפים.

### F-3 🔴 מספרי-חוזים: V1 בקוד ≠ V2 במסמך; שניהם מתים תחת FIXED_CONTRACTS_3
דיף מלא (פקודה+פלט בנספח §5): **verdicts זהים 70/70 · מספרים שונים 44/70** (CSV V2 עד 5 חוזים; קוד V1 עד 3).
`FIXED_CONTRACTS_3=1` (.env:186) מחווט ב-3 נקודות-חנק (`quality_tier.py:87` · `sizing.py:89` · `sierra_command.py:171`,
קומיט 6ec3209) — כל ירי=3. **פסיקה:** להכריז שהמספרים בטבלאות היסטוריים; שכבת-verdict נשארת; לסמן את V2-CSV כלא-מחווט.

### F-4 🔴 REACTIVE×Variation — counter-fade מותר בכל שכבה חיה
auth=FULL (`auth_table_v1.py:37`) · playbook=FULL (require_with_trend לא חל — Variation∉_TREND_DAYS,
`daytype_playbook.py:117`) · REACTIVE∈REV → פטור מ-CONT_TREND_FILTER (`trading_gateway.py:369-372`) ·
position-gate=0. התוצאה בפועל: 269/270 ב-07-01 (־2R). PATTERN_AWARE (רדום) כבר מקודד Variation+REV→SKIP
(`daytype_position_gate.py:108-109`). **פסיקה:** מדיניות fade-נגדי בווריאציה (עקרון-06-20 אומר לחסום).

### F-5 🟡 באגי-תיעוד מסוכנים על משפחת-REACTIVE
`PATTERN_ACCESS_MAP.md` שורה 42 מסווג REACTIVE=CONT, וטקסט CONT_TREND_FILTER ב-`FLAG_INDEX`/רגstry
("+ S2 Reactive/Initiative") — **הקוד קובע REV** (`_REV_PATTERNS`, `daytype_position_gate.py:38-44`) והוא פטור
מהפילטר. לתקן את שני המסמכים + `FLAG_REGISTRY.yaml`.

### F-6 🟡 עוגני-סטופ: config חי ≠ מסמכים
`STOP_ANCHORS_V2=1` (חי) → `config/stop_anchors.yaml` הוא האמת: ZLR=`breakout_bar` w1 (מיכאל 06-30).
ACCESS_MAP (06-28) + DEFINITIONS_INDEX (06-26) עדיין מציגים cluster_low w4 — וגם מציגים את
STOP_ANCHORS_V2 כ-OFF. HTLB נשאר בשאלה פתוחה אמיתית: מקור=בר-הפריצה vs config=`consolidation_extreme`.

### F-7 🟡 סמנטיקת-כניסה S4: קוד=close, מסמכי-המקור=stop-order 1T
כל תבניות-woodies נכנסות ב-`bar.close` (למשל `zlr.py:220`); TableA/ACCESS_MAP מגדירים buy-stop 1T מעל
שיא-בר-האות. כרטיסי-ה-HTML של מיכאל = close ✓קוד. **פסיקה:** לאשרר close ולתקן את TableA (או להפוך).

### F-8 ⚪ שונות שנאספה
(א) fallback יום-לא-מוכר ב-auth → Neutral_Center (`auth_table_v1.py:143-147`) — שמרני אך שונה מ-fail-open;
היה רלוונטי ל-I-44 (פיצול-מקור day_type). (ב) כותרת Playbook-HTML עוד אומרת "19 תבניות" — בפוטר 16 ✓.
(ג) FLAG_INDEX מסמן 3 דגלים לא-מתועדים: `FIXED_CONTRACTS_3`, `DAYTYPE_CONFIRM_BARS`, `OPPOSITE_EXIT_THRESHOLD`
— להוסיף ל-FLAG_REGISTRY.yaml. (ד) targets.yaml (R-פר-יום) חי רק כ-fallback כש-structural נכשל — לתעד.

---

## §3 · מה כן מיושר (אין צורך לגעת)

משפחות CONT/REV זהות בקוד↔resolver-HTML↔onboarding (16=7+9) · HFE כבוי עקבי בכל שכבה ·
Nontrend=SKIP בכל המטריצות + `NONTREND_DISABLE_ALL=1` · verdicts V1↔V2 זהים 70/70 ·
עוגני-הסטופ של REACTIVE/INITIATIVE/FLAGS/GHOST/FAMIR/DOUBLE/HNS תואמים config↔מסמכים ·
FIXED_CONTRACTS_3 מחווט נכון בכל שלוש נקודות-החנק (ממתין לריסטארט) · DOUBLE-targets=structural
(ההחלטה "לא measured-move" מיושמת דרך flag=ON) · סטופ-HNS על כתף-ימין (לא neckline) ✓.

---

## §4 · רשימת-הפסיקות למיכאל (מסודר לפי סיכון)

| # | פסיקה | ברירת-המחדל המוצעת |
|---|--------|----------------------|
| D-1 | טבלת-הרשאה קנונית אחת (תבנית×יום) | playbook.yaml כבסיס; ליישב 8 תאים חמים: REACTIVE×Var · INITIATIVE×Normal · HNS×Var · DBDT×TDD · TT,GB100×TN/TDD · HTLB×TN/TDD · ZLR×NeuC; לגזור ממנה את auth-verdicts ו-TableB |
| D-2 | מה קורה עכשיו בחלון-הולידציה | **✅ נפסק 07-02 (Michael):** playbook נשאר =1, מוכר כגייט-המשפחה הפעיל בזמן הולידציה. נימוק-בטיחות: `NONTREND_DISABLE_ALL` יושב בתוך גייט-המיקום הכבוי (`daytype_position_gate.py:89→116`) ⇒ תאי-ה-SKIP של ה-playbook הם ההגנה היחידה על Nontrend ב-S4 כרגע. בלי שינוי .env |
| D-3 | סולם-היעדים 07-01 מחליף את 06-20 | כן → CC מיישר את הרזולבר לכל סוגי-היום + קאפ-14/רנר-cap min() + ATR חי + בדיקת R:R |
| D-4 | מספרי-חוזים | **✅ נפסק 07-02 (Michael):** קבוע-3 (סטנדינג); שכבת-verdict נשארת חיה; מספרי V1-בקוד + V2-CSV מוכרזים היסטוריים — יסומן במסמכים |
| D-5 | סמנטיקת-כניסה S4 | **✅ נפסק 07-02 (Michael):** close = הקנוני (כמו הקוד והכרטיסים); TableA/ACCESS_MAP יתוקנו בהתאם (docs-only) |
| D-6 | HTLB: עוגן-סטופ + מדיניות-Trend | לפסוק consolidation_extreme או breakout-bar; וליישב HTML("נחסם")↔playbook(FULL) |
| D-7 | TT | לאפיין מחדש (למה 0 ירי) או לפרוש; ליישב TableB=✅TN מול playbook=REDUCED |
| D-8 | כרטיסי VEGAS+GHOST | לעדכן את הכרטיסים לגאומטריה המקודדת (cup&handle / CCI-H&S) או לפסוק ההפך |
| D-9 | רענון-מסמכים | ACCESS_MAP · DEFINITIONS_INDEX · FLAG_REGISTRY (3 דגלים חסרים + תיקון טקסט CONT_TREND_FILTER + inert-marker ל-PATTERN_AWARE) |

---

## §5 · נספח ראיות (Rule 5)

**דיף Auth V1-קוד ↔ V2-CSV** — הפקודה: פרסור regex של `_AUTH_TABLE_V1` מול
`MEMS26_Auth_Table_V2_cells.csv` (סקריפט פייתון, הורץ 2026-07-02). פלט גולמי (מקוצר):
`parsed: 70 · VERDICT mismatches (0) · NUMBER mismatches (44)` — הרשימה המלאה של 44 התאים
נשמרה בהיסטוריית-הסשן; דוגמאות: REACTIVE_LONG×Normal code=(3,2,2) csv=(5,4,3) ·
INITIATIVE_SHORT×TN code=(3,2,1) csv=(5,4,3) · BULL_FLAG×TDD code=(3,2,2) csv=(5,4,3).

**מצבי-דגלים** (FLAG_INDEX נוצר 07-01 22:09; .env עודכן 07-01 20:11): `DAYTYPE_POSITION_GATE=0` 🔴 ·
`DAYTYPE_PLAYBOOK=1` ✅ · `DAYTYPE_PATTERN_AWARE_V1=1` ✅(רדום) · `CONT_TREND_FILTER=1` ✅ ·
`DAYTYPE_TARGETS_STRUCTURAL=1` ✅ · `STOP_ANCHORS_V2=1` ✅ · `FIXED_CONTRACTS_3=1` (.env:186, לא-במרשם) ·
`HFE_DISABLED=1` ✅ · `NONTREND_DISABLE_ALL=1` ✅ · `S2_REQUIRE_COT_AMT` 🔴 standing-off.

**הסתייגות:** הניתוח הוא מול הקוד ב-HEAD (e7cfca0). התהליך הרץ קדם לקומיטים של 07-01 —
ההתנהגות החיה עד הריסטארט הקרוב שונה (I-54 קרה על הקוד הישן). אימות-חי לפי
`CC_FINALIZE_WIP_AND_RESTART_2026-07-02.md` אחרי הריסטארט.
