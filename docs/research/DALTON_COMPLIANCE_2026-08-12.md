# DALTON COMPLIANCE — האם אנחנו סוחרים לפי דלתון היום? (בוקר 2026-08-12, לפני CPI)

**סוכן:** `dalton-compliance-agent` (Cowork) · **נכתב:** 2026-08-12 ~08:00 IDT (פתיחה 16:30 IL; CPI 15:30 IL, אדום)
**סטטוס:** READ-ONLY — אפס שינויי קוד/דגל/קונפיג, אפס ריסטארטים. הכתיבות היחידות: הדוח הזה + רשומת LIVE_CHANNEL.
**בסיס (לא שוחזר, רק הוצלב):** `DALTON_DAY_TYPE_2026-08-10.md` (מיפוי-הדוקטרינה) · `WEEKEND_TRADING_RESEARCH_2026-08-08.md` §3 ·
`SYSTEM2/SYSTEM4_FULL_AUDIT_2026-08-11.md` · `QUALITY_BLOCKS_2026-08-10_11.md` · `WORK_PLAN_2026-08-12.md`.
**מצב-הריצה שנבדק (Rule 5, §D):** backend PID 88223 עלה **07:37:51 IDT היום**, שורת-בוט `[env_loader] applied 221 vars`
(ה-221 = `RELEASE_TREND_BYPASS_PTS=12` — פסיקת-הבוקר טעונה), `flag_guard → PASS — all 165 ruled flags match`.
F1+F2+F4+F6 + A1+A2 + chase-fixes של אתמול — **כולם בתהליך הרץ**.

> **🔴 עובדת-שטח לפני הכל (07:52 IDT):** בחשבון-האמת 37138283 פתוח עכשיו **לונג ידני 6 חוזים @7758.0**
> (sierra_state טרי-לשנייה; radar מאשר qty=6; אין עסקת-TM פתוחה ⇒ ownership=מייקל, לא אורפן, per פסיקת 07-24).
> ה-reconciler שם סטופ-וירטואלי @7748 (00:51 ET). **כל עוד הפוזיציה פתוחה — `PRE_SEND_ENTRY_GUARD_V1` (F1) חוסם
> כל כניסת-LIVE של המערכת** (position_qty≠0), וגם המרג'ין קוצץ (available $852.68 ⇒ contracts_allowed=2).
> זו נקודת-החיכוך #1 של היום — לפני כל דיון בשערים.

---

## A. מטריצת-תאימות-דלתון — 7 עקרונות

מוסכמות: **LIVE** = מחווט ופעיל בתהליך הרץ, עם ראיה מהשבוע · **OFF** = קיים בקוד, דגל כבוי · **חסר** = אין קוד.
עמודת-הראיה = היכן זה רץ בפועל השבוע (decisions/לוג/DB), לא "אמור לרוץ".

| # | עקרון דלתון | פסק | מנגנונים (דגל→קובץ) | ראיה שרץ השבוע / הסתייגות |
|---|---|---|---|---|
| 1 | **מסחר עם ה-OTF ביום-מגמה** (with-trend only) | **LIVE** | `CONT_TREND_FILTER=1` + `LSMA_SUSTAIN_BARS=2` · `DIRECTION_CONTEXT=1` + `DIRECTION_LSMA_VETO=1` · playbook `require_with_trend` + `RESPONSIVE_WITH_DAY_TREND_V1=1` + `NEVERFADE_TREND_ONLY_V1=1` · `LEG_RIDE_V1=1` (פטור-שערים לרגל-חיה, `trading_gateway._live_leg`) · chase leg-bypass `:1651` | cont_trend חסם 6/3 שורות ב-08-10/08-11 (decisions); ההיפוך המסוכן (revocation שביטל 14/14 פטורי-רגל ב-08-11) **כובה-בקוד אתמול**. הסתייגות-ביצוע: על האיתותים שעברו, מודל +$1,127 מול חשבון +$23.75 (S4 §9) — העיקרון נאכף בכניסה אך לא ממומש ברווח (סולם-סטופ, F3 נבנה היום flag-OFF, קומיט 967f3675) |
| 2 | **רספונסיבי בקצות-ואליו ביום-איזון** | **LIVE (בחלקו)** | `DAYTYPE_PLAYBOOK=1` (Normal/Neutral: fade_edges, VAL→LONG·VAH→SHORT) · `DAYTYPE_LOCATION_GATE=1` + probe + `REV_EDGE_DAY_STRUCTURE_V1=1` · `NEUTRAL_RESPONSIVE_V1=1` | 08-10 11:10 REACTIVE_SHORT נחסם "not at VAH (near_val)" — נכון; playbook = השער הרווחי במערכת (−$670/48 סשנים). פערים: scope הלוקיישן = REACTIVE/HNS בלבד (DBDT לא נבדק-מיקום); `EDGE_FADE_V1` **OFF בכוונה** (ממתין scid-replay); `REACTIVE_LOCATION_GATE=0` (standing) |
| 3 | **סוג-הפתיחה קובע קונביקציה** (drive=go-with, auction=wait) | **LIVE בזיהוי, לא-יורה בכניסה** | detector v2 + `OPENING_TYPE_GATE=1` (חוסם counter-drive עד IB-lock; AUCTION⇒HOLD) · `OPENING_DIR_FUSION_V1=1` · `OPENING_FIRST_TRADE_STRICT_V1=1` (conf≥`OPENING_MIN_CONF=0.6`) · `OPENING_TYPE_SEEDS_S1_V1=1` · `OPENING_WINDOW_FIRE_V1=1` (override חיובי ב-30 הדק' הראשונות) | הזיהוי רץ כל יום (v9_day_type_history: 5 זיהויים כיווניים ב-7 סשנים). **אפס עסקאות-פתיחה מאז 07-31** — הפירוק המלא ב-§B. חסר: מיפוי opening-type→sizing/טווח-צפוי (המלצת-08-10 #8, דורש פסיקה) |
| 4 | **רוחב-IB מכייל ציפיות** | **🐛 שבור-LIVE; תיקון בנוי וכבוי** | הבאג המאומת מ-08-10 (`_last_atr_daily`=ממוצע-נר-5-דק' ⇒ IB/ATR מנופח ×13) עדיין הנתיב החי: `state_machine.py:370-371` fallback. תיקון C1 קיים מאחורי **`ATR_DAILY_FIX_V1` — לא ב-.env = OFF** | **v9_day_type_history: `ib_width_class=EXTREME` בכל 9 הסשנים 08-03→08-12** — בדיוק "EXTREME כמעט-קבוע" שהדוח חזה. משמעות: מטריצת (Opening×IB) מקבלת קלט מורעל; Nontrend דרך NARROW כמעט-בלתי-נגיש. **זה הפריט היחיד במטריצה שנשאר שבור אחרי אתמול** |
| 5 | **כניסה על פולבק/ריטסט, לא רדיפת-קצה** | **חצי-LIVE: הבלימה כן, הכניסה לא** | בלימת-רדיפה LIVE: `EXTREME_CHASE_GUARD_V1=1` (סף `max(6.0, 0.30×IB)`, בגרות `CHASE_MIN_SESSION_BARS=8`, דרישת-פולבק ≥3pt, scope=CONT פסיקת-מייקל) + A1 `STRUCTURAL_TARGETS_WRONG_SIDE_VETO_V1=1` (fail-closed, סוגר את מחלקת-#655) + `TARGET_REALISM_V1=1` + `ZONE_LIMIT_ENTRY_V1=1` | כניסת-הפולבק החיובית של דלתון (broken-IB-edge/POC/singles) — **עדיין חסרה**: `RE_PULLBACK_ENTRY_V1` לא קיים ב-.env (OFF), הפרוזה ב-playbook Variation ("enter on pullback to broken edge") ללא מבצע; PULLBACK_CONT קיים רק בשעת-הפתיחה; `TREND_STEP_ENTRY_V1` מתוכנן-צל; F3 ladder בנוי flag-OFF |
| 6 | **Excess = קצה-מוגן · Poor = מגנט** | **LIVE ביציאות; ספק-מת בכניסות** | `extremes_quality` מחושב (דייק ב-08-10) · יציאות: `EXTREMES_AWARE_REALIZE_V1=1` · כניסות: `EXCESS_COUNTER_ENTRY_V1=1` (11.08) | ⚠️ ממצא-K5 של exec-agent (08-12): פטור-ה-EXCESS ב-`daytype_playbook.py:259-297` נראה **בלתי-נגיש** (ענף `_variation_wt` אחרי RESPONSIVE_WITH_DAY_TREND); `test_expansion_counter_fade_blocked/exempt` נכשלים גם על HEAD נקי ⇒ ייתכן רגרסיה-חיה מאז 07-23. פריט-cc פתוח (WORK_PLAN 7d). Excess כעוגן-סטופ: חסר. Single prints: מחושבים, **אפס צרכנים** — חסר |
| 7 | **הטיית-כיוון מנדידת-ואליו רב-יומית** | **מחושב-LIVE, שער-OFF** | `multiday_profile` (migration/overlap/open_location) חי ב-radar; `MULTIDAY_VETO_V1` **לא ב-.env = OFF**; `S1_VALUE_MIGRATION_V1=1` (וטו-קידום-Trend בלבד, מקור יום-אחורה) | ה-1%-overlap/+33pt-migration מ-08-10 הגיע לתצוגה ולמסווג — לא לשום החלטת-ירי. סטטוס ללא-שינוי מהביקורת |

**שכבת-הבטיחות שנוספה מאז הביקורות (הכל LIVE מהבוקר):** A2 `COLD_START_GUARD_V1=1` (אין ירי עד ≥3 ברים-מעובדים; סוגר את "ירה 8 שניות אחרי ריסטארט") · F1 `PRE_SEND_ENTRY_GUARD_V1` (אין כניסת-LIVE על פוזיציה-עומדת/הזמנות-עובדות/sierra_state ישן) · F2 פיד-יחיד (הרעלת-החוצץ של S2 נסגרה) · F4 פלייבוק-הפוך (GB100=FULL·ZLR=REDUCED/SKIP-Normal·FAMIR+VEGAS=SKIP-הכל·GHOST=REDUCED) · F6 רוטציית-decisions + zlr-דביק.

**שורה תחתונה ל-A:** מן הדוקטרינה — עקרונות 1-2-3(זיהוי)-5(בלימה)-6(יציאות) אכופים-LIVE; **4 שבור-חי (התיקון כבוי)**; 3(כניסה), 5(כניסת-פולבק), 6(כניסת-excess, ספק-K5), 7(שער) — לא מגיעים להחלטת-ירי. אנחנו **דלתוניאנים בסינון, עדיין לא דלתוניאנים בכניסה וביישום-הרווח**.

---

## B. פער-הכניסה של סוגי-הפתיחה — למה 0 עסקאות-פתיחה מאז 08-03

### B.1 מה ממופה למה (המצב בקוד היום)

| זיהוי-detector (radar/history) | טריגר-כניסה ב-`opening_entry.py` | תנאי-הפעלה קשיח | stance ב-playbook |
|---|---|---|---|
| OPEN_DRIVE | `DRIVE` (close מעבר לקצה-OR) | **רק כש-OR bar-1 ≤ 10pt** (`OR_NARROW_MAX_PTS`) | DIRECTIONAL |
| OPEN_TEST_DRIVE | `TEST_DRIVE` (excursion ≥0.5×OR + reclaim) | ברים 3..12 | DIRECTIONAL |
| OPEN_REJECTION_REVERSE | `ORR` (drive-close קודם + close חזרה דרך ה-open) | מבר 3, אחד לסשן | REVERSAL |
| (ללא זיהוי מקביל) | `EXTREME_REJECT` (כלל-מייקל 07-22) · `PULLBACK_CONT` (excursion≥6pt + retrace≥33% + bias-seed) | בר 3+ / חלון-60-דק' | — |
| OPEN_AUCTION_IN/OUT | **אין כניסה (honest)** | — | NO_EDGE |

כל טריגר → `build_opening_setup` (סטופ מבני, cap 15/25pt, T1=1.5R בנק) → gateway ככל setup, עם פטור מוצהר
מ-`awaiting_release`+`lsma_flat` בלבד (`_opening_gate_exempt`, `OPENING_PLAYBOOK_V1=1`).

### B.2 העובדות (Rule 5)

- `v9_trades`: **6 עסקאות-OPENING בכל ההיסטוריה, האחרונה 07-31** (ORR-shadow WIN +$80 · #575 DRIVE-live −$198.75 · 07-30 DRIVE-live −$63.75). מאז 08-03: **0**.
- decisions מאז 08-03 (706 שורות אחרי ניקוי-fixtures): **רק 5 שורות OPENING_DRIVE — כולן שידור-חוזר-ישן** (entry 7535 ב-10:34Z/05:52Z, מחוץ-ל-RTH, נחסמו `session_gate_closed`). **אפס setup-פתיחה טרי הגיע ל-gateway בכלל.**
- הלוג השורד (מ-08-11 14:36 בלבד): **4×** `OPENING_FIRST_TRADE_STRICT held DRIVE SHORT — opening confidence 0.0 < 0.6`; **0** `honest skip` · **0** `OPENING_DIR_FUSION` · **0** emission.

### B.3 הליכה יום-יום: זיהוי מול חלון-כניסה (זיהוי מ-`v9_day_type_history`; טריגרים = רפליי-טהור של `evaluate_opening_entry` על 12 ברים קנוניים, window=12+pullback)

| יום | זיהוי (conf-strict) | OR bar-1 | טריגרים שהיו קיימים על ברים נקיים | מה קרה בפועל |
|---|---|---|---|---|
| 08-03 | OPEN_DRIVE (.85 ✓) | **22.50** | **NONE** — DRIVE דורש OR≤10; שום TD/ORR/PB לא התקיים | זיהוי-drive בלי כניסה ממופה — פער-מיפוי, לא שער |
| 08-04 (Trend!) | OPEN_DRIVE (.85 ✓) | **14.25** | **NONE** (אותו פער) | יום-המגמה של השבוע נפתח ב-drive מזוהה ואפס טריגר |
| 08-05 | OPEN_DRIVE (.85 ✓) | 15.50 | EXTREME_REJECT LONG 09:40 · PULLBACK_CONT SHORT 09:45 · TEST_DRIVE LONG 09:55 | לא נותב דבר; הלוגים לא שרדו — החשודים: fusion=None (נפח<חציון⇒drop אחרי בר-6) / bias-seed / חוצץ-מורעל (F2) |
| 08-06 | ORR (.65 ✓) | 17.00 | PULLBACK_CONT LONG 09:40 · EXTREME_REJECT SHORT 10:25 | כנ"ל — לא נותב, לא ניתן-לשחזור-לוג |
| 08-07 | ORR (.65 ✓) | **10.00** | **DRIVE LONG 09:40** · PULLBACK_CONT SHORT 09:45 · **ORR SHORT 10:00** | היום היחיד עם DRIVE+ORR חוקיים — ואפס ניתוב. אותם חשודים |
| 08-10 | OPEN_AUCTION_IN (0 ✗) | 11.25 | PULLBACK_CONT SHORT 09:40 · **EXTREME_REJECT LONG 09:45 @7777.75** — בדיוק "עסקת-היום" שה-chase חסם ל-S4! | strict הורג הכל על auction (conf 0<0.6) — by-design; הכניסה הנכונה של היום הייתה קיימת במנוע-הפתיחה ומתה על ודאות-הזיהוי |
| 08-11 | OPEN_AUCTION_IN (0 ✗) | 14.00 | PULLBACK_CONT LONG 09:55 (על ברים נקיים) | **מוכח מהלוג:** המנוע החי פלט DRIVE SHORT ×4 — **בלתי-אפשרי על OR=14** ⇒ ה-OR שלו נבנה מהפיד-הכפול המורעל (F2, תוקן היום); strict עצר נכון (conf 0.0). ריסטארט 18:11 IL סגר את המנוע להמשך-היום (mode עזב FIRST_HOUR) |

### B.4 תשובות ישירות

**האם וטו-מיצוי-drive + first-trade-strict + cold-start ביחד הופכים כניסות-פתיחה לכמעט-בלתי-אפשריות?**
כימות 7 הסשנים: `drive_exhaustion_veto` — **0 חסימות מאז שהודלק (06.08)**; הוא בכלל לא הגורם (אף setup לא הגיע אליו).
`cold_start_guard` — חי רק מ-08-11 22:25, **0 חסימות**, ובבוקר רגיל (backend עלה 07:37, ברים-לילה נטחנים) הוא חם מזמן עד 16:30 — מסוכן רק אחרי ריסטארט תוך-סשן. **החוסמים בפועל הם אחרים:** (א) **first-trade-strict על ימי-AUCTION הוא מוות-מובנה** (conf≤0.5<0.6 תמיד — by-design, וזה "נכון-דלתוניאנית" אבל הרג גם את EXTREME_REJECT@7777.75 של 08-10); (ב) **מיפוי-DRIVE צר מדי** — `OR_NARROW_MAX_PTS=10` מול OR חציוני ~14-17 בשבועיים ⇒ ביום-drive אמיתי אין טריגר (08-03/08-04); (ג) **fusion שקט** — מפיל הכל אחרי בר-6 כשנפח<חציון, בלי שורת-לוג ניתנת-לביקורת ברוב הימים; (ד) עד-אתמול — **המנוע רץ על חוצץ מורעל** (F2). הצירוף (א)+(ב)+(ג) לבדו מסביר 0-מתוך-5 זיהויים-כיווניים ⇒ **כן, בקונפיג הנוכחי כניסת-פתיחה היא כמעט-בלתי-אפשרית, אבל לא בגלל הווטו והקולד-סטארט.**

**מה חייב להשתנות כדי שזיהוי OPEN_DRIVE / REJECTION_REVERSE מחר יפיק כניסה** (פריטי-בנייה; כולם flag-OFF⇒replay⇒פסיקה):

| # | פריט | בעלים | מסלול |
|---|---|---|---|
| B1 | **איחוד מקור-הוודאות**: strict-gate ידרג לפי הטריגר של מנוע-הכניסה (DRIVE/.85, TEST/.75, ORR/.65) כשה-detector עצמו זיהה טיפוס-כיווני באותו כיוון — היום conf נלקח רק מה-detector, וה-0.0-מול-DRIVE הורג גם טריגרים לגיטימיים | cc | flag חדש (למשל `OPENING_CONF_ENGINE_FUSE_V1`) → רפליי 31-סשנים → פסיקה |
| B2 | **פרמטריזציית `OR_NARROW_MAX_PTS`** (10 קשיח בקוד) ל-YAML + כיול-רפליי (למשל סקלה ל-ATR/median-OR) — בלעדיו "drive=go-with" לא קיים ברוב ימי-drive | cc | YAML+replay; שינוי-ערך = פסיקה |
| B3 | **חיווט `opening_windows` (`OPENING_WINDOWS_V1=1`) לנתיב-הירי** — היום zero-consumers פרט לווטו-המיצוי: phase=CONFIRMED של ORR-window יתיר ORR-entry גם כש-strict-conf גבולי | cc | flag-OFF ⇒ replay |
| B4 | **תצפיתיות-fusion**: לוג קבוע של inputs (נפח-פתיחה מול חציון) + אימות מקור-הנפח על הפיד הנקי של F2 — היום ה-drop שקט | cowork (אימות בסשן הראשון) | לוג בלבד |
| B5 | **כבר-בנוי, לאמת היום**: F2 נותן למנוע OR נקי לראשונה — הסשן של היום הוא מבחן-הקבלה; לוודא ש-`OPENING_DIR_FUSION =` מופיע בלוג אחרי בר-6 | cowork | אימות-Rule-5 |
| B6 | **opening-type→sizing/expected-range** (המלצת-08-10 #8; ‎26pt מול ATR-84 = לא 4 חוזים) | מייקל-פסיקה → cc | מחקר-אמפירי → פסיקה |

---

## C. צילום-פתיחות-שערים להיום (הסדר = `trading_gateway.route_setup`)

**פעילים היום (ערכים חיים מהבוט של 07:37):**

| # | שער (blocked_by) | פרמטרים חיים | חוסם היום כאשר… | שינוי מאתמול/הבוקר |
|---|---|---|---|---|
| 1 | `kill_switch` | לא-מופעל | מייקל/מובייל לוחץ | — |
| 2 | `session_gate_closed` | 08:30–15:00 CT | מחוץ-לחלון (כולל שידורי-חוזר של boot) | — |
| 3 | `cold_start_guard` | A2, `COLD_START_MIN_BARS=3`, fail-closed | <3 ברים-מעובדים אחרי ריסטארט (ריסטארט-צהריים!) | **חדש-חי** (11.08) |
| 4 | `eod_entry_cutoff` | 45 דק' לפני 15:00 CT | אחרי 15:15 ET | — |
| 5 | `feed_watchdog` | stale>90s + `FEED_CONTENT_STALE_SECONDS=600` | פיד קפוא (CPI-spike?) | — |
| 6 | `cooldown` | 2-stop cooldown | אחרי 2 סטופים | — |
| 7 | `duplicate_fire` | חלון 30s, ±0.5pt | איתות זהה פעמיים | — |
| 8 | `opening_type_gate` | עד IB-lock; AUCTION⇒HOLD, counter-drive⇒BLOCK | פתיחת-auction ⇒ הקפאת-הכל בשעה הראשונה (fail-open על EARLY_BIAS ניטרלי) | — |
| 9 | `drive_exhaustion_veto` | b7-edge בזמן drive | רק כש-detector=DRIVE והכניסה בקצה-balance-7 | 0 הפעלות מאז שהודלק |
| 10 | `daytype_playbook` | **מטריצה הפוכה (F4)**: GB100 FULL/4 סוגי-יום · ZLR REDUCED+SKIP-Normal · FAMIR/VEGAS SKIP-הכל · GHOST REDUCED · REACTIVE with-day-trend · `NONTREND_DISABLE_ALL=1` | תא-SKIP; יום-Neutral ⇒ S4 מושבת כמעט-כולו; counter-trend רספונסיבי | **F4 חי מהבוקר** — ההוכחה הראשונה = ההחלטה הראשונה היום |
| 11 | `location_gate` | REV בקצה-הנכון + probe (`PROBE_REJECT_MIN_PTS=0.0`) + פטור-רגל (`LEG_RIDE_V1`) | REV-fade לא-בקצה, בלי רגל-מסכימה | פטור-רגל מאומת 2/2 |
| 12 | `cont_trend_filter` | LSMA-3-ברים, `LSMA_SUSTAIN_BARS=2`; פטור-רגל | CONT נגד-מגמה-מקומית; מתהפך בהפוגות-מדרגה (שארית #2, n=1) | — |
| 13 | `direction_context` | CVD+breakout ("רק עם התנועה") | ירי נגד הכיוון החי | — |
| 14 | `lsma_flat` | slope<0.25 ⇒ block; `LEG_EXEMPT_LSMA_FLAT_V1=1` (כמעט-אינרטי 0/18) + פטור-opening | שיפוע שטוח בהפוגות (שארית #3, n=1) | פטור-רגל נשאר; פתרון-שורש = step-entry |
| 15 | `extreme_chase_guard` | `max(6.0, 0.30×IB)` · בגרות **8 ברים** · פולבק≥3pt · **scope=CONT** (REV פטור) · בייפס: רגל-חיה `:1651` / displacement≥12 · **tip-revocation OFF-בקוד** (`EXTREME_CHASE_TIP_REVOKE_V1` default-0) + `TREND_LEG_CHASE_EXEMPT_V1=1` | CONT קרוב-לקצה בלי רגל/displacement; או בלי-פולבק-3pt | **אשכול-08-11 (+$300 חד-משבצת) עובר היום** — 0 כיסוי-חי עד-כה, ההחלטה הראשונה = ההוכחה |
| 16 | `pattern_stop_cooldown` | re-entry זהה אחרי STOP | ריפוי-יתר של אותה תבנית | — |
| 17 | `awaiting_release` | `RELEASE_ENTRY_GATE_V1=1`: higher-lows≥2 · vol-ratio 0.75/3 · zone 8pt/24 ברים · **TREND-bypass @12pt (היה-15)** · fail-closed · פטור-opening | תקוע-בזון בלי release; ענף-הנפח חסם עם-מגמה אתמול (+$540 per-sig) | **סף-12 חי מהבוקר (פסיקת-מייקל, var #221)** |
| 18 | `news_blackout` | **אדום בלבד: −10m..+5m** (פסיקת 07-13) | היום: CPI 08:30 ET ⇒ חסימה 08:20–08:35 ET בלבד — הפתיחה 09:30 לא מושפעת | לוח-אירועים עודכן הלילה |
| 19 | A1 `structural_targets_wrong_side` | fail-closed כשכל c1/c2/c3 בצד-הלא-נכון | קנייה-מעל-הכל/מכירה-מתחת-להכל (מחלקת-#655) | **חדש-חי** (11.08) |
| 20 | `entry_not_confirmed` (S4) | `S4_ENTRY_CONFIRM_V1=1`, tol 0.5pt | בר-אישור חסר | — |
| 21 | `rr_hard_floor`/`rr_entry_gate` | `RR_MIN_ROTATION=0.65` · `RR_BREAKOUT_MM_V1=1` (חילוץ-MM) · T1 קדם-realism | R:R-חתום שלילי; **נשאר הצוואר כשסטופ-Resolver רחב מול מדרגה-11pt — הפתרון F3 (בנוי, OFF)** | — |
| 22 | `zone_limit_late_entry` | `ZONE_LIMIT_ENTRY_V1=1` | כניסה מאוחרת מחוץ-לזון | — |
| 23 | `daily_loss_halt` | `RISK_HALT_V1=1`, cap **$800** | הפסד-יומי ≥$800 | — |
| 24 | F1 `PRE_SEND_ENTRY_GUARD_V1` (ב-`_execute_live`) | position_qty≠0 / working>0 / sierra_state>30s ⇒ block + retry-once | **חוסם עכשיו בגלל 6-הלונג-הידני** | **חדש-חי מהבוקר** |
| 25 | sizing | `FIXED_CONTRACTS_4=1` → 4c · REDUCED≈2 · `MARGIN_AWARE_SIZING_V1=1` (עכשיו: allowed=2) · S7 score = צל-בלבד | מרג'ין נמוך כל-עוד ה-6-לוט פתוח | — |

**כבויים (לא יחסמו היום):** `TREND_DIRECTION_GATE=0` · `REACTIVE_LOCATION_GATE=0` · `DAYTYPE_POSITION_GATE=0` · `MULTIDAY_VETO_V1` off · chop-gates off (standing) · `SSV_GATE_V1=0` · `DAY_DIRECTION_DOCTRINE_V1` off · `SYSTEM7_SCORE_V1` off · `RISK_CONSECUTIVE_LOSS_LIMIT=0` · `PATTERN_LOSS_BREAKER=0` · `HLST`/`RE_PULLBACK`/`EDGE_FADE`/`TREND_STEP` off · F3 `STEP_SCALED_LADDER_V1` בנוי-OFF (ממתין רפליי⇒פסיקה).

### C.9 התשובה הכנה: איתות with-trend נקי במיקום טוב היום — מה עומד בינו לבין הזמנה חיה?

1. **הלונג-הידני-6** — עד שהוא סגור, F1 חוסם כל כניסת-LIVE (והסיירה עצמה תדחה -1: AllowOpposite=0). *זה המחסום היחיד שהוא ודאי.*
2. **מרג'ין** — גם אחרי סגירתו, לוודא available מתאושש (עכשיו allowed=2; flat ≈ $2,503 ⇒ 4c חוקיים).
3. **תווית-היום** — אם היום יסווג שוב Neutral_* (פתיחת-auction שלישית ברצף, וה-IB-class עדיין EXTREME-קבוע מהבאג #4), הפלייבוק מכבה S4 כמעט-כולו וגם GB100-FULL לא קיים ב-Neutral. יום-CPI צפוי Variation/Trend — אבל התווית תלויה במסווג המורעל-חלקית.
4. **שעה ראשונה על פתיחת-auction** — `opening_type_gate` מחזיק הכל עד IB-lock (fail-open רק על bias ניטרלי).
5. **R:R מול סולם-מדרגה** — כשהסטופ 10-15pt מול מדרגת-11pt, `rr_entry_gate` ימשיך לתפוס כניסות-אמת; F3 בנוי אך OFF עד רפליי+פסיקה ⇒ היום עדיין חשוף למחלקת "4 כניסות פתוחות, 0 נבנקו".
6. **ביצוע** — retry-once של F1 עדיין ללא כיסוי-חי (32% מהניתובים מתו היסטורית); המשמרת של היום היא ההוכחה.
7. **שאריות-שער בהסתברות-נמוכה** — chase על CONT בלי-רגל בפתיחת-סשן צעירה (בגרות-8 טרם מולאה) · cont_trend/lsma_flat בהפוגות (n=1 כ"א אתמול) · דדליין-EOD.
8. **מה שכבר לא עומד בדרך (בניגוד לאתמול):** tip-revocation (מת-בקוד) · פלייבוק-הפוך (ZLR-FULL הישן) · הזנה-כפולה · ORDER_FAILED-שקט · סף-release-15.

---

## D. אימות-גולמי (Rule 5 — פקודה + פלט)

```
ps -axo pid,lstart,command | grep uvicorn
  88223 Wed Aug 12 07:37:51 2026  … -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
grep -a 'env_loader' /tmp/backend.err.log | tail -1
  [env_loader] applied 221 vars from …/.env | HFE_DISABLED=1 …
tail -1 .env  →  RELEASE_TREND_BYPASS_PTS=12   (פסיקת-מייקל 12.08, "מאשר ברור")
python3 scripts/flag_guard.py → FLAG-GUARD: PASS — all 165 ruled flags match.

SELECT … FROM v9_trades WHERE pattern_id_at_entry ILIKE '%OPENING%'
  → n=6, אחרונה 2026-07-31 16:40 (OPENING_ORR shadow WIN +80) · #575/#574/#564/#563 DRIVE
decisions 08-03..: 706 שורות; OPENING_*=5 (כולן entry=7535, session_gate_closed, שידור-ישן)
blocked histogram: awaiting_release 214 · session_gate 85 · daytype_playbook 68 · cont_trend 38 ·
  lsma_flat 32 · eod 29 · chase 23 · location 20 · rr 19 · direction_context 17 · feed_watchdog 10 ·
  stop_cooldown 9 · opening_type_gate 5 · chop 2 · news 1 · dup 1   (שורות-גולמיות, לא דדופ)
grep -c /tmp/backend.err.log (מכסה 08-11 14:36→עכשיו):
  'OPENING_FIRST_TRADE_STRICT' = 4 (כולן "DRIVE SHORT … 0.0 < 0.6") · 'OPENING_DIR_FUSION' = 0 ·
  'honest skip' = 0 · 'BYPASS REVOKED' = 14 (אשכול-08-11, before the kill)
v9_day_type_history 08-03..08-12: opening_type = DRIVE,DRIVE,DRIVE,ORR,ORR,AUCTION_IN×3;
  ib_width_class = EXTREME בכל 9 השורות
רפליי-טהור evaluate_opening_entry (window=12, pullback):
  08-03 OR=22.50 NONE · 08-04 OR=14.25 NONE · 08-05 [ER-L 09:40, PB-S 09:45, TD-L 09:55] ·
  08-06 [PB-L 09:40, ER-S 10:25] · 08-07 OR=10.00 [DRIVE-L 09:40, PB-S 09:45, ORR-S 10:00] ·
  08-10 [PB-S 09:40, ER-L 09:45 @7777.75] · 08-11 OR=14.00 [PB-L 09:55]
sierra_state.json (ts=07:52:41, טרי): position_qty=6 LONG @7758.0, is_sim=0, acct 37138283,
  open_pnl −15, daily_pnl +490, available 852.68, margin_req 1650.66; radar: qty=6, allowed=2
v9_trades open: NONE · trade_state.json: absent  ⇒ ownership=manual (07-24 doctrine)
OPS_LOG 00:51:58 ET: reconciler "ORPHAN VIRTUAL STOP SET: LONG stop @ 7748.0 for 6c @ 7758.0"
state_machine.py:348-371: ATR_DAILY_FIX_V1 (C1) קיים; לא ב-.env ⇒ fallback 5-min-avg פעיל
news_calendar 08-12: CPI 08:30 ET red; news_blackout: red = −10m..+5m בלבד
```

**חתום: dalton-compliance-agent · 2026-08-12 · READ-ONLY (0 שינויי קוד/דגל/ריסטארט)**
