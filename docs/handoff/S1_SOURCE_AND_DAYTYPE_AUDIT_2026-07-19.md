# S1 מקור-אמת + תבנית×סוג-יום — ביקורת מלאה

**תאריך:** 2026-07-19 · **מבצע:** cursor-agent (קריאה-בלבד) · **מאמת:** cowork-dev (חוק-5)  
**פסיקת-מייקל:** *"מערכת-1 צריכה מקור-אמת אחד… פערים מול דלתון… תבנית-תבנית… מיקומים… מימוש כל החוזים ברווח."*  
**מפרט:** [`CURSOR_S1_SOURCE_AND_DAYTYPE_MISSION_2026-07-19.md`](CURSOR_S1_SOURCE_AND_DAYTYPE_MISSION_2026-07-19.md)  
**הצלב (לא שכתוב):** [`PATTERN_BIBLE_2026-07-19.md`](PATTERN_BIBLE_2026-07-19.md) · [`DALTON_DOCTRINE.md`](../spec_authority/DALTON_DOCTRINE.md) · [`SOURCE_OF_TRUTH.md`](../SOURCE_OF_TRUTH.md)

**אין שינוי-קוד / .env / RULED / מסחר בסשן זה.**

ראיות-ריצה בסשן:
- `sim_matrix.py` → `PASS: 112 cells, keep=65 skip=47, mismatches=0` → `docs/reports/SIM_MATRIX_2026-07-19.md`
- `audit_pattern_miss.py --date 2026-07-17 --relax all` → **FAILED** (Postgres.app trust dialog) → מספרי B2 = **לא-מוכרע מהקוד**

---

## תשובה ישירה למייקל

| שאלה | תשובה |
|---|---|
| האם ל-S1 יש מקור-אמת אחד? | **לא.** לייב-מסחר אמור לעבור ב-`get_live_day_type()` (`trade_context.py:520-584`), אבל צרכנים עדיין קוראים ממקורות אחרים (UI=`classify_replay`; S2 detection=`current_day_type`; S4 נסיגה ל-`v9_day_type_state`/`"Normal"`). |
| איך מזוהה כל סוג-יום? | First-match ב-`daytype_classifier.classify` (`daytype_classifier.py:271-431`) על `sides`/`rib`/`vol_ratio`/`close_pos` + דגלים אופציונליים — טבלה A3. |
| פערים מול דלתון? | כן — מפורט ב-A4 (מתוך `DALTON_DOCTRINE.md` בלבד). בולטים: rib≥2.5≠שליטת-OTF; escalation-only לא על המנוע החי; Normal כ-catch-all מול "חריג"; פתיחה נזרקת ל-FORMING שעתיים. |
| תבנית נכונה + מיקום → מימוש C1–C3? | פלייבוק+שערי-מיקום קיימים (B1); **מספרי מימוש** מ-`audit_pattern_miss` לא זמינים בסשן → B2 חלקי מקוד+Bible בלבד. |

---

# חלק א' — מערכת-1: מקור-אמת-אחד?

## A1. מפת מנועים וצרכנים

| מנוע | כותב | קורא | סטטוס מול SoT |
|---|---|---|---|
| `classify_session` / `daytype_classifier.classify` | pure | `backend/main.py` `_day_type_on_bar` (~453–513) מקדם ל-machine | ✅ **LIVE canonical** כש-`S1_ENGINE_NEW_CLASSIFIER=1` |
| `classify_replay` | API/DB wrapper | UI TopBar/DayTypeLens · audits · G1 **רק** מחוץ לסשן | ✅ UI/replay · ⛔ mid-session G1 (`trade_context.py:587-603`) |
| `day_type_machine` | promote מ-`classify_session` (`main.py:471-513`, map `Normal_Variation→Variation`) | `get_live_day_type` (`trade_context.py:552-558`) | ✅ LIVE shell ללייבל; SoT עדיין כותב "OLD 3-type" — **דריפט-דוק** |
| `v9_day_type_state` | `main.py` write-on-change | S2 hydrate (`five_min_system.py:261-283`); S4 fallback (`woodies_system.py:672-685`) | 🟡 נכתב · SoT: **לא SoT למסחר** |
| `get_live_day_type` | — | G1 · S2 emit/sizing · S4 (A6) · שערי-מיקום | ✅ SoT-helper למסחר (override→machine→antiflap/prelock) |
| `ShadowReclassifier` / TYPE_ORDER | skipped כש-engine חדש (`main.py:548-553`) | — | 🔴 **מת לנתיב-חי** |
| `/api/v9/day_type/current` · `v9/current` | — | — | 🔴 DEAD (SoT + retired FE 06-22) |

**נתיב-לייב הקנוני:** bar → `_day_type_on_bar` → `classify_session` → map NV→Variation → `day_type_machine` → `get_live_day_type`.

**דריפט SoT↔קוד:** `SOURCE_OF_TRUTH.md:29-30` עדיין מתייג machine כ-"OLD 3-type" — בפועל הלייבל מקודם מ-7-type כש-engine flag ON. `DALTON_DOCTRINE.md:147-151` אומר acceptance-driven (יכול לרדת); `shadow_reclass.py:85-88` TYPE_ORDER לא רץ חי.

## A2. האם כל צרכן-מסחר קורא אותו מקור?

| צרכן | מקור סוג-יום | מול `get_live_day_type` |
|---|---|---|
| `extract_g1_entry_context` / שער-playbook | blob machine → אם `S1_NEW_CLASSIFIER`: **`get_live_day_type()`** (`trade_context.py:614-657`); mid-session חוסם `classify_replay` | ✅ (כש-flags ON) |
| Gateway `daytype_playbook` | `day_type_at_entry` מ-G1; בודק `_pb.allow` בלבד (`trading_gateway.py:633`) — **לא** `_pb.contracts` | ✅ מקור; 🔴 גודל (ראה B3) |
| S2 NT early-skip | `self.current_day_type` (`five_min_system.py:1139`) | 🔴 |
| S2 chart 5a/5c allow | `chart_patterns_allowed(self.current_day_type, …)` (`:1180-1192`) | 🔴 |
| S2 Flag T2 fork | `dt = self.current_day_type` (`:1551`) | 🔴 |
| S2 emit / V2 sizing | `get_live_day_type()` first → `_emit_day_type` (`:1336-1435`) | ✅ |
| S4 sizing/targets (A6) | P1: `get_live_day_type` אם `S4_OVERRIDE_AWARE_V1` (`woodies_system.py:650-657`) | ✅ כש-live מחזיר ערך |
| S4 נסיגה | P2 `current_state` → P3 raw machine → P4 **`v9_day_type_state`** → P5 **`"Normal"`** (`:658-688`) | 🔴 fallback-מת + סינתזה |
| UI TopBar / DayTypeLens | `classify_replay` (הערות ב-`TopBar.tsx` · `DayTypeLensContent.tsx`) | 🔴 תצוגה ≠ שער |

### שרשרת-נסיגת S4 (A6 נותר)

תנאים להגעה למקור-מת / סינתזה (`woodies_system.py:650-688`):

1. `S4_OVERRIDE_AWARE_V1` OFF **או** `get_live_day_type()` → `None`/UNKNOWN  
2. ו-`current_state.day_type` ריק  
3. ו-machine ריק/INDETERMINATE  
4. → SELECT מ-`v9_day_type_state` (SoT: לא למסחר)  
5. אם גם זה ריק → **`_s4_day_type = "Normal"`** (סינתזה — Rule 1)

**כמה פעמים קרה בפועל אחרי A6:** **לא-מוכרע מהקוד/לוגים בסשן** — אין מונה/לוג ייעודי ב-OPS_LOG שסופר P4/P5.

## A3. זיהוי 8 סוגי-היום (קריטריון מהקוד)

ספים מ-`config/daytype_trading_plan.yaml` → `daytype_classifier.py:197-205`:  
`rib_trend_min=2.5` · `rib_nontrend_max=1.15` · `rib_normal_max=1.30` · `vol_low_ratio=0.5` · `close_extreme 0.85/0.15` · `close_center [0.33,0.67]` · IB lock 60min→12 bars.

| סוג | תנאי מדויק (first-match) | file:line |
|---|---|---|
| **FORMING** | `n < 12` ו-לא EOD; אופציונלי provisional מ-open אחרי 6 ברים (`S1_COMMITTED_PROVISIONAL_V1`) | `daytype_classifier.py:271-283` |
| **Nonconviction** | דגל ON + OA + `in_value` + `sides==0` + אפס RE + mid close | `:285-300` |
| **Nontrend** | `sides==0` + `vr≤0.5` + `rib≤1.15` (+ רצפת-טווח אופציונלית) | `:302-313` |
| **Neutral_Extreme** | `sides==2` + close extreme | `:316-318` |
| **Neutral_Center** | `sides==2` + close center / resolving | `:319-322` |
| **Trend_DD** | `sides==1` + `dd_second_dist` (אלא אם invalidation ON + neck refill) | `:325-339` |
| **Trend_Normal** | `sides==1` + לא-oi + one_tf + extreme + `rib≥2.5`; אלטרנטיבות דגל: OPEN_DRIVE / control-path | `:340-407` |
| **Normal_Variation** | `sides==1` catch-all → מקודם ל-`Variation` ב-`main.py:471-476` | `:408-411` |
| **Normal** | `sides==0` contained `rib≤1.30` + vol + IB לא-צר; אחרת provisional | `:413-431` |

Overlays: acceptance-reclass (`:247-269`); Neutral precedence (`:220-228`); INVALIDATED `oi` חוסם Trend (`:207,342`).

## A4. פערים מול דלתון (מ-`DALTON_DOCTRINE.md` בלבד × קוד)

| סוג / נושא | דלתון בריפו | הקוד | 🔴 פער? |
|---|---|---|---|
| **Normal** | IB רחב, נדיר, איזון דו-צדדי (`DALTON_DOCTRINE.md:112`) | rib≤1.30 + catch-all provisional (`:413-431`) | 🔴 under-specified + bias-Normal מול "חריג" |
| **Normal Variation** | הארכה חד-צדדית ~×2 IB ואז איזון חדש (`:113`) | sides==1 catch-all; "rebalance" לא נמדד (`:408-411`) | 🔴 |
| **Trend** | שליטת OTF + one_tf + elongation — לא מכפיל-טווח (`:114`) | דורש `rib≥2.5` + extreme (`:340-346`) | 🔴 זיהוי מאוחר (דוקטרינה עצמה מסמנת) |
| **Trend_DD** | IB צר + צוואר single-prints + invalidation ב-refill (`:115`) | detector קיים; invalidation דגל OFF (`:329-336`) | 🟡 חלקי |
| **Nontrend** | אין RE, השתתפות נמוכה, להישאר בחוץ (`:116`) | sides0+vol+rib (`:302-313`); `vr is None` → לא מגיע | 🔴 חור vol-None |
| **Neutral-Center/Extreme** | RE **בשני** צדדים; close mid/extreme (`:117-118`) | sides==2 + cp (`:316-322`) | ✅ מיושר (לא "בלי כיוון") |
| **Nonconviction** | OA בערך קודם, אפס OTF (`:119`) | דגל OFF → סוג חסר ברירת-מחדל (`:285-300`) | 🔴 OFF |
| **פתיחה foreshadow** | open→סוג-יום מוקדם (`:125-134`) | FORMING עד 12 ברים; opening_type כמעט לא בשימוש בלי דגלים (`:271-283`) | 🔴 |
| **הסלמה** | acceptance שני כיוונים — **לא** never-downgrade (`:147-151`) | TYPE_ORDER רק ב-shadow מת (`shadow_reclass.py:85-88`; skip `main.py:548`) | 🔴 דוק/צל מול מנוע חי חופשי |
| **Honest prelock** | (MEMS) אין תווית קנונית לפני IB lock | `DAYTYPE_HONEST_PRELOCK_V1` OFF → תווית ישנה יכולה לעבור (`trade_context.py:559-573`) | 🔴 |
| **`ib_source=bars`** | IB מ-TPO/Sierra עדיף | replay default bars→upgrade TPO (`daytype_classify_routes.py:101-114`); live sanity → bars_fallback (`classifier_core.py:81-92`) | 🟡 fallback כש-TPO חסר |
| **`S1_IB_SANITY_V1`** | IB סיירה מעופש קדם-פתיחה | דגל OFF (`classifier_core.py:63-92`) | 🟡 |
| **`OPENING_FIRE_CVD_V1`** | CVD מאשר drive | FORMING→`day_type=None` ב-G1 כש-ON (`trade_context.py:656-657`); default בקוד OFF — מצב-.env **לא-מוכרע כאן** (אסור לקרוא `.env`) | לא-מוכרע מצב-חי |

---

# חלק ב' — תבנית × סוג-יום: הנכון + המיקום למימוש מלא

מטרת-מייקל: בכל סוג-יום — תבניות מתאימות במיקומים הנכונים → C1/C2/C3.

הצלב Bible: גאומטריה/🚫/B1-paint/B2-late — **לא נשכתבים**; כאן שאלת דלתון×פלייבוק×מיקום.

## B1. מטריצה לפי סוג-יום

מקרא פלייבוק: F=FULL · R=REDUCED · S=SKIP · מקור `config/daytype_playbook.yaml:127-152`.  
`sim_matrix` אומת 112 תאים / 0 mismatches (שכבת-playbook בלבד — לא צבע/FHB/VSA).

שערי-מיקום (משפחתיים, לא מטריצת-תבנית):
- `DAYTYPE_LOCATION_GATE` — REV על רוטציה ליד VA; CONT×Variation עם כיוון-הרחבה (`location_gate.py:8-21,54-106`; gateway `:699-731`)
- `REACTIVE_LOCATION_GATE` — REACTIVE מול POC (`reactive_location_gate.py`; gateway `:682-697`)
- `DAYTYPE_POSITION_GATE` — Normal/Variation/Neutral/Trend zones (`daytype_position_gate.py:10-17,195-293`)

### Trend_Normal / Trend_DD

| | |
|---|---|
| **דלתון** (`DALTON_DOCTRINE.md:114-115`) | שליטת OTF / DD עם צוואר; כניסות **עם** המגמה; מיקום: המשך אחרי pullback / צוואר-DD — לא fade לקצה |
| **הקוד** | CONT: ZLR/TLB/INIT/FLAGS/CONFLUENCE = F (TT/GB100=R); REV fade VEGAS/GHOST/FAMIR = S; HTLB/REACTIVE = F; DBDT = S על TN / R על DD |
| **מיקום בקוד** | Trend: position_gate WITH breakout; location_gate לא נוגע ב-Trend |
| **🔴 פער** | Bible 🚫² TT/GB100 — paint GRAY על `current_bar` (`bars.py:1087` vs `:1153`) חוסם CONT גם כש-playbook מתיר. S2 מאוחר (Bible B2) דוחף כניסה אחרי תנועה → C2/C3 קשים |

### Variation (Normal_Variation)

| | |
|---|---|
| **דלתון** (`:113`) | הארכה חד-צדדית ואז איזון בערך חדש — CONT עם ההרחבה; fade רק אחרי acceptance בצד החדש |
| **הקוד** | CONT F (TT/GB100 R); fade-REV R; HTLB/REACTIVE/HNS F |
| **מיקום** | CONT×Variation חייב עם כיוון-הרחבה (`location_gate`); Variation position = WITH IB expansion |
| **🔴** | FIXED_4 מבטל R→2; location נכון בסגנון אבל כניסה מאוחרת (S2) עדיין מונעת מימוש מלא |

### Normal

| | |
|---|---|
| **דלתון** (`:112`) | IB רחב + רוטציה VAH↔VAL; כניסות בקצוות ערך (REV) יותר מ-CONT רדיפה |
| **הקוד** | CONT R (CONFLUENCE F); fade-REV F; HTLB R; REACTIVE F |
| **מיקום** | REV: LONG ליד VAL / SHORT ליד VAH; REACTIVE מול POC |
| **🔴** | Bible: INITIATIVE×Normal over-fire (A5) — **תוקן** playbook-single-source 07-19. REDUCED לא ממומש בגודל |

### Neutral_Center / Neutral_Extreme

| | |
|---|---|
| **דלתון** (`:117-118`) | שני צדדים; Center=אין מנצח (mid); Extreme=מנצח מאוחר בקצה — לא "בלי כיוון" |
| **הקוד** | CONT כמעט S (TLB/FLAGS R על NE; HTLB R); fade-REV F |
| **מיקום** | כמו Normal VA-edge ל-REV |
| **🔴** | אם UI/override מציגים Neutral והזיהוי עדיין על `current_day_type` ישן — chart-patterns יכולים לפספס/להתיר לא נכון (A2) |

### Nontrend / Nonconviction

| | |
|---|---|
| **דלתון** (`:116,:119`) | להישאר בחוץ |
| **הקוד** | כל התבניות SKIP בפלייבוק; Nonconviction דגל OFF → סוג עלול לא להתקיים |
| **🔴** | אם detection NT-skip על hydrate מעופש — אפשר לדלג על יום שמייקל דרס ל-Trend (או ההפך) |

## B2. איכות-מיקום למימוש C1/C2/C3

| מקור | ממצא | סטטוס |
|---|---|---|
| `audit_pattern_miss` 15/16/17-07 | DB trust dialog — אין ממוצע נקודות-מהקצה / hit-rate C1–C3 בסשן זה | **לא-מוכרע מהקוד** |
| Bible B1 | `current_bar` בלי `_trend_from_cci` → TT/GB100 עיוורים בראלי | אומת בקוד (`bars.py:1087` vs `:1153`); cowork אימת B1 PASS ב-LIVE_CHANNEL |
| Bible B2 | REACTIVE/INIT ≥7 ברים + FHB + VSA avg20 כולל overnight (`five_min_system.py:34,:658-659`) | אומת בקוד; משמעות: כניסה מאוחרת בתנועה → **C2/C3 לא ריאליים** גם כש-playbook FULL |
| שערי-מיקום | כשיש flag ON — דוחפים כניסה לקצה-ערך / עם-הרחבה | מצב-flags חי: **לא-מוכרע** בלי `flag_guard` (אסור `.env`) |
| FIXED_4 | כל ירי מותר מקבל 4 גם ב-REDUCED | `sizing.py:122-124` · `sierra_command.py:235,277-278` · gateway לא מחיל `_pb.contracts` (`:633`) |

**מסקנת-B2 (בלי מספרים):** גם כשהפלייבוק והמיקום "נכונים על הנייר", שלושה מחסומים חוסמים מימוש-מלא: (1) paint-lag S4, (2) S2 מאוחר, (3) REDUCED לא ממומש — ו-(4) פיצול-מקורות סוג-יום גורם לשערים/יעדים על תווית שגויה.

## B3. המלצות-שיפור (ממוינות · הצעות בלבד)

| דירוג | פער | שינוי-מוצע | סיכון | השפעה על מימוש |
|---|---|---|---|---|
| 1 | Paint `current_bar` | `_trend_from_cci` גם על `last_flat` אחרי override (`bars.py:1153`) | באג-ברור / דגל קיים | משחרר TT/GB100 בראלי → יותר C1+ |
| 2 | S2 detection / Flag T2 על `current_day_type` | אותם gates על `get_live_day_type` (דגל OFF) | שער-סיכון · פסיקה+סים | פחות דילוג/יעד-שגוי |
| 3 | S2 כניסה מאוחרת (B4+FHB+VSA) | גישת-כיול נפרדת (Bible B2) — מחוץ לתיקון-SoT בלבד | שער-סיכון גבוה | ישיר ל-C2/C3 |
| 4 | S4 fallback → DB/`"Normal"` | fail-honest `None` במקום סינתזה | שער-סיכון · פסיקה | מונע תמחור Normal על יום אחר |
| 5 | UI ≠ gates | תצוגה מ-`get_live_day_type` | נמוך (תצוגה) | החלטות ידניות נכונות |
| 6 | Honest prelock OFF | הדלקת `DAYTYPE_HONEST_PRELOCK_V1` + RULED | תצוגה/שערים פרה-IB | פחות תווית-שקרי |
| 7 | FIXED_4 × REDUCED | פסיקה: להשאיר / לכבד REDUCED | **גבוה** — גודל | התאמת-סיכון ליום |
| 8 | Trend rib≥2.5 / open foreshadow | דגלים קיימים (`S1_TREND_CONTROL_V1`, `S1_COMMITTED_PROVISIONAL_V1`) — פסיקת-הדלקה בלבד | דוקטרינה | זיהוי מוקדם יותר |

---

## מה לא הצלחתי להכריע מהקוד

1. **מספרי `audit_pattern_miss`** על 15/16/17-07 (נקודות מהקצה, C1/C2/C3 hit-rate) — Postgres trust dialog בסשן זה.  
2. **תדירות נסיגת S4** ל-`v9_day_type_state`/`"Normal"` אחרי A6 — אין מונה בלוגים.  
3. **מצב-flags חי** (`DAYTYPE_GATE_LIVE_V1`, `DAYTYPE_ANTIFLAP_V1`, `DAYTYPE_LOCATION_GATE`, `OPENING_FIRE_CVD_V1`, וכו') — אסור לקרוא `.env`; נדרש `flag_guard` מ-cowork.  
4. **האם override מגיע ל-`self.current_day_type` של S2** באירוע — GAP_REGISTER G-05 עדיין VERIFYING; הקוד מראה detection לא קורא live ישירות.  
5. **מספרי Dalton textbook** (אחוזי Neutral-Extreme וכו') מעבר למה שצוטט ב-`DALTON_DOCTRINE.md` — לא נפתח ה-PDF בסשן.  
6. **BE/runner wiring מלא** מ-`daytype_style` עד trade_manager בכל נתיב — Bible U4 / GAP G-12.

---

## לאימות-cowork (חוק-5)

אל תסמן "בוצע" בלי פקודה+פלט. מינימום:
1. `bars.py` — ציטוט `:1087` מחיל `_trend_from_cci` · `:1153` raw על `current_bar`.  
2. `woodies_system.py:650-688` — שרשרת P1→P5 כולל `"Normal"`.  
3. `five_min_system.py:1139,:1180-1192,:1551` — detection/T2 על `current_day_type`.  
4. `daytype_classifier.py:271-431` — first-match תואם A3.  
5. `sim_matrix` PASS 112/0 (או ריצה מחדש).  
6. אם אפשר על Mac-המסחר: `audit_pattern_miss` ל-15/16/17 — להשלים B2.

שורת-LOG: `S1_SOURCE_AND_DAYTYPE_AUDIT אימות PASS/FAIL · …`

---

## קשר לתור-סגירה S124 (לא חלק מהמשימה, הפניה)

פערי-הקוד שזוהו כאן ממופים ללוח `LIVE_CHANNEL` §🔴 S124 GAPS / `GAP_REGISTER` (G-01 paint · G-05 detection · G-14 Flag T2 · G-15 prelock · G-16 UI · G-17 fallback · G-03 FIXED_4 · G-18 דוקטרינה). סגירה = פסיקת-מייקל → CC — לא בסמכות מסמך זה.
