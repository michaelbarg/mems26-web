# MEMS26 · Decision Ledger

**מטרה:** תווית קבועה לכל החלטה שנוגעת במערכת — **מה הוחלט, למה, ואיפה נקודת ההחלטה** — כדי שתמיד אפשר לחזור למקור ולהבין את הרציונל. כל קוד/roadmap/status שנוגע בפריט **חייב לשאת את התווית** (למשל `# D-RVX: ...`).

**מוסכמה:** `D-XXX` = Decision tag. סטטוס ∈ {🟡 PENDING-MICHAEL · ✅ APPROVED · 🟢 IMPLEMENTED-SHADOW · 🔵 LIVE-WIRED · ⛔ REJECTED}.

---

## D-CHOP · Choppiness gate = opening-only, advisory on classified days
- **סטטוס:** 🟡 PENDING-MICHAEL 2026-06-08 (כיוון-Michael ב-RTH; דורש אישור-ניסוח סופי + מימוש flag-gated).
- **מה הוחלט (כיוון-Michael):** ה-gate של choppiness **לא יחסום ירי ביום מסווג** (במיוחד Trend). נועד לזהות **פתיחה choppy** בלבד — ברגע ש-day_type מסווג (DAY_TYPE_MODE), choppiness הופך ל-**advisory** (כמו killzone, D-093). אופציות-ניסוח לאישור: (א) gate פעיל רק ב-FIRST_HOUR · (ב) על Trend_Normal/Trend_DD לעקוף · (ג) להרים סף מ-70.
- **למה:** חי 2026-06-08 (RTH, day_type=Trend_Normal): `choppiness_score=67` מול סף 70 — **גבולי, קופץ מעל 70 וחוסם לסירוגין את Reactive/Initiative** — בדיוק עסקאות-הטרנד ש-Michael רואה. האלגוריתם (`choppiness.py`) מודד 6 ברים אחרונים; ב-MIDDAY (ברים חופפים) קורא "choppy" גם ביום-טרנד. יום-טרנד מסווג אינו choppy בהגדרה → מדכא setups לגיטימיים. ה-docstring: "from **opening** bars" — היעוד היה פתיחה, אך `five_min_system.py:865` הפך לרציף.
- **נקודת החלטה:** `five_min_system.py:865-870` · `s2_inspector.py:142-143` (gate `<70`) · `choppiness.py`.
- **מימוש (מוצע):** flag `CHOPPINESS_OPENING_ONLY` — ב-DAY_TYPE_MODE/Trend → `chop_ok=True` (advisory). ⚠️ trading-logic → SHADOW + אישור-Michael. ביטול = הסכמת-Michael בלבד.
- **קשור:** D-093 (killzone observer) · D-S1DYN

## D-093 · Killzone = Observer (no firing block) — אומת בקוד 2026-06-08
- **סטטוס:** ✅ APPROVED + 🟢 IMPLEMENTED — אומת Cowork (קוד חי): killzone **לא חוסם ירי**. `wrappers.py:349-359` `analyze()` תמיד None; gateway/pre_fire לא בודקים killzone; `decision_tree.py:295-302` = advisory; S2 הליבה `⛔ NO killzone inputs`. מה שנראה בלוח (MIDDAY/low-edge) = תצוגה, לא חסימה.
- **OPEN (cosmetic):** דאשבורד מציג "low-edge" באופן שעלול להיראות חוסם — תיקון-תצוגה לא-דחוף.

## D-RVX · Reactive Volume-eXhaustion Threshold
- **סטטוס:** ✅ APPROVED 2026-06-01 (Michael) — Stage 1 shadow: 3 וריאציות A/B/C כצופים + אימות (autocorrelation/RVOL distribution) במקביל. live נשאר 0.10.
- **🔬 אבחון 2026-06-02 (Cowork agent) — השערת Phase 0 הוחלפה:** "channel-mismatch" **הופרך** (`main.py:88` wiring תקין, `process_bar` רץ). שורש אמיתי = **גייט volume בלתי-אפשרי מתמטית** (`five_min_system.py:469-543`: `b2<=b1*0.10` AND `max(prev3)<b1*0.6` → 0/1085 זוגות). פרומפט מעודכן `CC_PROMPT_S2_REACTIVE_CANFIRE_2026-06-02.md` מתקן Phase 0, שומר Phases 2-5 של הפרומפטים הקודמים. evidence: `v9_five_min_setups/state=0`, `firing_system=2`=0 all-time.
- **מה הוחלט (מוצע):** להחליף את גייט ה-volume של Reactive מ-"ירידת 90% בר-מול-בר" (`DROP_THRESHOLD_PCT=0.10`) לסף יחסי מבוסס-ממוצע, ולהריץ 3 וריאציות במקביל כצופים: **A=VSA** (נמוך מ-2 ברים קודמים + ≤0.7× ממוצע-20) · **B=RVOL-TOD** (≤0.6× אותה שעת-שעון) · **C=Strict** (≤0.5× ממוצע-20).
- **למה:** סף 90% בר-מול-בר **בלתי-אפשרי פיזית** ב-5-דק' RTH (0/54 זוגות עברו ב-2026-06-01; הקרוב 88%). אף מתודולוגיה (VSA/Wyckoff/Bulkowski/Order-Flow) לא משתמשת בסף אחוז קבוע בר-מול-בר — כולן יחסיות (ממוצע/climax). ה-90% כנראה הגיע מברים יומיים.
- **נקודת החלטה:** `docs/reports/DECISION_BRIEF_REACTIVE_VOLUME_THRESHOLD_2026-06-01.md`
- **מימוש:** `docs/handoff/CC_MEGA_PROMPT_REACTIVE_*` (מגה-פרומפט בדיקה+תיקון+תצוגה build_status/trader)
- **קשור:** [[D-S1DYN]] (פילוסופיית "צופים" משותפת) · fire-audit §3a

## D-S1DYN · S1 Dynamic Mid-Session Re-Classification
- **סטטוס:** 🟢 IMPLEMENTED-SHADOW 2026-06-01 (CC · Phase 0-2 · commits `caeb984`/`df16d03`/`9d8ff30`) — Stage 1 shadow-log (would-be transitions בלבד, לא נוגע ב-Auth Table) · convention=total-range. **code-level אומת ע"י Cowork** (shadow_reclass.py + flag S1_DYNAMIC_RECLASS + טבלה v9_day_type_shadow_transitions + commits). **runtime:** היום נרשם shadow Normal→Variation (@min387 E↑0.74 · @min397 E↑0.95); **אימות יום-trend מלא (→Trend) ב-RTH הבא**. **Stage 3 (חיווט ל-live gating) עדיין דורש אישור נפרד.**
- **מה הוחלט (מוצע):** להוסיף ל-S1 שרשרת monotonic IB-relative — Normal → Normal Variation → Trend — שמתעדכנת כל בר אחרי נעילת IB, עם gating על value-migration + acceptance + initiative(CVD). שלב 1 = **shadow-log בלבד** (מתעד would-be transitions, לא נוגע ב-Auth Table).
- **למה:** סוג-היום הוא **מצב מתפתח**, לא תווית חד-פעמית (Dalton/Steidlmayer). הקפאה ב-Normal (יום 2026-06-01: E_up=1.77, R=2.77 — היה צריך 2 מעברים) **חסמה את ה-Initiative של S2**. מנגנון ה-reeval הקיים (`_rescore_from_behavior`/`_check_reeval`) הוא **ATR-relative + conf-gated**, לא IB-relative — לכן לא תפס את ה-extension.
- **נקודת החלטה:** `docs/reports/DECISION_BRIEF_S1_DAYTYPE_RECLASSIFICATION_2026-06-01.md`
- **מימוש:** `docs/handoff/CC_MEGA_PROMPT_S1_*` (אבחון מלא + הפיכה לדינמי)
- **⚠️ risk surface הגבוה ביותר** — סיווג-מחדש הופך את ה-Auth Table gating. חיווט ל-live (Stage 3) = strategic-stop + אישור.

## D-RDY · Pre-Fire Readiness Gate
- **סטטוס:** ✅ APPROVED 2026-06-01 (Michael) — צורה: הרחבת build_status (שדה `readiness` ב-BuildStatusResponse + תצוגה בדאשבורד). משתלב בשדרוג ה-Build Status (D-OBS).
- **מה הוחלט (מוצע):** שכבת verdict דקה read-only מעל `BuildStatusAggregator` הקיים שמריצה את שלבי `PRE_TRADE_PROTOCOL.md` ומחזירה READY/DEGRADED/BLOCKED + המלצות.
- **למה:** היום הבדיקה לפני מסחר ידנית (runbook 6 שלבים). אוטומציה = מאשרת שהמערכת מוכנה לירי לפני שסומכים על הנתונים. read-only → אפס סיכון.
- **נקודת החלטה:** `docs/handoff/CC_PROMPT_FIRE_AUDIT_DIAGNOSIS_AND_READINESS_GATE_2026-06-01.md` §B

## D-WDIAG · Woodies Missed-Fire Diagnosis (ZLR / HFE / Gray)
- **סטטוס:** ✅ APPROVED 2026-06-01 (Michael) — ZLR confirmed-bounce גם בנתיב ה-DLL + פילטר מומנטום · HFE נשאר counter-trend/exit low-tier · gray: audit תיוג קודם ואז ניתוק HFE מפילטר ה-gray. מתוזמן **אחרי** D-RVX + D-S1DYN.
- **מה הוחלט (מוצע) — 3 הכרעות:**
  - **ZLR = confirmed-bounce (Impl B).** הקוד שלנו (`zlr.py`, `current>prev`) נאמן לדוקטרינה, אבל `woodies_system.py:307-318` (commit `58d6538`) עוקף ויורה על זיהוי-pullback של ה-DLL (Impl A) ללא bounce. מוצע: הצמד confirmed-bounce גם לנתיב ה-DLL + פילטר מומנטום (15–20 CCI, אל תרדוף >120).
  - **HFE = counter-trend/exit, low-tier.** כבר low-tier בקוד (`PATTERN_TIER` לא כולל HFE). שמור; שקול תפקיד exit; לא peer של ZLR.
  - **Gray/P-W5 = audit תיוג קודם.** HFE אמיתי (±200) כמעט לעולם לא ב-gray; אם 17 HFE נחסמו ב-GRAY (DAY1) → באג תיוג. שמור no-trade ב-gray לתבניות המשך; נתק HFE מפילטר ה-gray אחרי audit.
- **למה:** מחקר Woodies doctrine (ZLR=bounce לא pullback; HFE=counter-trend/exit; gray-no-trade לתבניות המשך בלבד). מתקן את פרשנות ה-fire-audit §4 (חלק מה-"8 ZLR שפוספסו" היו pullback לא-תקפים).
- **נקודת החלטה:** `docs/reports/DECISION_BRIEF_WOODIES_ZLR_HFE_TREND_2026-06-01.md` · fire-audit §4
- **⚠️ פוטנציאל רגרסיה:** commit `58d6538` (DLL-primary ZLR) — **הופרך** ע"י audit (73/73 DLL ZLR עם bounce). תקין.
- **⚠️ override `1c0397a` — partial-wiring (אומת ע"י בקרה בלתי-תלויה, `INDEPENDENT_VERIFICATION_2026-06-02.md`):** משנה `_ts`+`current_state` אבל לא `studies["trend_state"]`; ה-decision_tree A1 קורא `studies` → **ה-override לא מגיע ל-gate של `ready_to_route`**. מצב נוכחי: inert ל-routing (decision_tree עדיין חוסם → אין fires שגויים), אבל לא עקבי. החלטה נדרשת: revert לניקיון, או השלמה מאחורי דגל + shadow-validate (השלמה = הפעלת שינוי gating אמיתי). **✅ הוכרע 2026-06-02 (Michael): דרך נקייה** — revert ל-`1c0397a` → relabel במקור יחיד (`studies["trend_state"]` לפני detection/decision_tree) מאחורי דגל `S4_EXTREME_TREND_RELABEL` (default OFF) + regression + shadow-validate. פרומפט: `docs/handoff/CC_PROMPT_FIX_TREND_RELABEL_SINGLE_SOURCE_2026-06-02.md`. strategic-stop לפני הדלקה live. **✅ מומש+מאומת 2026-06-02:** relabel חולץ ל-`trend_relabel.py` (מקור יחיד), נקרא ב-`woodies_system.py:279`; טסט אינטגרציה דרך `decision_tree.evaluate_bar` (commit `c43acc6`; CC: 6/6 green + litmus 2 RED). **Cowork אימת ישירות את פונקציית הייצור** (flag ON: YELLOW+331→BLUE / YELLOW−257→RED / GRAY+80→GRAY; flag OFF: YELLOW→YELLOW) — לא טאוטולוגי. (לא הורצה חבילת pytest מלאה ב-sandb Cowork — חסר sqlalchemy; הסתמכות על CC ל-6/6.) **נותר:** הוכחת shadow על בר ±200 ב-RTH + אישור Michael להדלקת הדגל קבוע. **✅ flag audit 2026-06-02 (`D_WDIAG_RELABEL_FLAG_AUDIT_2026-06-02.md`):** הדגל מאומת **ON ב-runtime** (plist `com.mems26.backend.plist` + env של PID 23884); HFE נרשם ב-`v9_trades` (mode=shadow, firing_system=4). **פער ל-A/B:** ה-relabel מבצע mutation in-place → ה-trend המקורי אבד → אי-אפשר להבחין "HFE עקב relabel" מ-BLUE טבעי. **CC הציע תיקון שורה אחת:** `studies["trend_original"]=trend` לפני ה-mutation (זורם ל-cross_context JSON → queryable). 🟡 **ממתין לאישור Michael** + בדיקת schema של `WoodiesBar` (שיקבל שדה נוסף). **✅ הוכרע 2026-06-02 (Michael): מאושר.** **הכרעת סתירה (Cowork, מול דוח `D_WDIAG_RELABEL_FLAG_AUDIT_2026-06-02.md`):** דוח CC טען "שורה אחת מספיקה" — **שגוי**; אבחון Cowork טען "4 נגיעות" — **הגזמה**. האמת המאומתת = **2 נגיעות**: (1) `trend_relabel.py` שומר `trend_original`; (2) להוסיף `"trend_original"` למילון ה-update **המפורש** ב-`woodies_system.py:425-432` (זה `update({...})` לא `update(studies)`, ו-get_current→cross_context בנוי ממנו). **לא** נדרש schema של `WoodiesBar` (נתיב נפרד, Pydantic מתעלם מעודף, לא קורס). `trade_context.py:342` sid==4 = אופציונלי לתצוגת-סיכום בלבד. ✅ פרומפט: `CC_PROMPT_D_WDIAG_TREND_ORIGINAL_2026-06-02.md` (טסט: revert P2 → RED). **🟢 מומש בעץ-העבודה (uncommitted) 2026-06-02 — אומת ע"י Cowork:** 3 הנגיעות קיימות (`trend_relabel.py:22` שומר תמיד · `woodies_system.py:433` במילון current_state · `trade_context.py:342` ב-tuple sid==4) + טסט `tests/v9/regression/test_d_wdiag_trend_original.py` (4 מקרים + ליטמוס revert-P2→RED). **P1 אומת בהרצת פונקציית-הייצור הישירה** (YELLOW+250→BLUE/orig=YELLOW · GRAY−260→RED/orig=GRAY · natural BLUE→orig=BLUE · flagOFF→orig=YELLOW); P2/P3 בקריאת-קוד. **נותר:** pytest ירוק במכונה החיה (sandbox חסר sqlalchemy) + commit + בר ±200 חי. ⚠️ דוח CC `D_WDIAG_RELABEL_FLAG_AUDIT` מיושן (טען "שורה אחת/ממתין" — בפועל הוטמע מלא, 3 נגיעות).

## D-S3MUTE · השתקת S3 Footprint עד ייצוב 1/2/4
- **סטטוס:** ✅ APPROVED 2026-06-02 (Michael)
- **מה הוחלט:** להשתיק את S3 Footprint (להפסיק ירי/איסוף) **עד ש-S1/S2/S4 יציבים**.
- **למה:** S3 הוא היחיד שמפיק מלא (142 עסקאות) ומציף את הסטטיסטיקות; Michael רוצה להתמקד בייצוב 1/2/4 בלי "רעש" מ-S3.
- **מנגנון:** דגל `S3_MUTE=1` ב-plist (ראה DAY1 §7 item D). **פעולה ל-CC להחיל.**
- **🔬 2026-06-02 (Cowork):** אומת ש-`S3_MUTE` **לא קיים בקוד** (grep ריק) — env-only לא יספיק. ✅ פרומפט נכתב: `CC_PROMPT_D_S3MUTE_2026-06-02.md` (דגל ב-`atr.py` + שער `if S3_MUTE: return` בנתיב הירי `footprint_system.py:436` `_fire` + טסט אנטי-טאוטולוגי). ממתין מימוש CC.
- **un-mute:** כש-S1(D-S1DYN)+S2(D-RVX)+S4(D-WDIAG) מאומתים יציבים ב-RTH.

---

## רקע — אנליזות בסיס (DONE)
- `docs/reports/AGENT_FIRE_AUDIT_VISIBLE_WINDOW_2026-06-01.md` — ניתוח חזותי (S1/S2/S4), חלון נראה, 7 מועמדים.
- שני מחקרים חיצוניים (Reactive volume / AMT day-type) — שולבו ב-D-RVX / D-S1DYN.
