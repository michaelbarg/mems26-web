# CC MEGA PROMPT — S1 Day-Type: Full Diagnosis + Make It Dynamic · 2026-06-01

**תווית החלטה:** `D-S1DYN` (ראה `docs/plans/DECISION_LEDGER.md`)
**מאת:** Cowork agent → **אל:** Claude Code
**נקודת החלטה:** `docs/reports/DECISION_BRIEF_S1_DAYTYPE_RECLASSIFICATION_2026-06-01.md`

> **משמעת Pre-LIVE:** diagnose-first · read-current-code · audit-existing · smallest-correct-change · **Rule 5 (command + raw output)** · **No silent failures** · **strategic-stop לפני כל נגיעה ב-Auth Table gating / risk surface**.
>
> **תווית בכל מקום שנוגעים:** `# D-S1DYN: <מה> — <למה> — ראה DECISION_LEDGER`.
>
> **⚠️ היקף הפרומפט הזה:** Phase 0 (אבחון) + Phase 1–2 (**shadow-log בלבד** — מתעד would-be transitions, **לא** משנה את ה-day_type שמוזן ל-Auth Table). **Stage 3 (חיווט ל-gating החי) מחוץ להיקף** — שלב נפרד שדורש אישור Michael מפורש, כי הוא משנה אילו תבניות יורות.

---

## Phase 0 · אבחון מלא — איך סוג-היום מתבצע ולמה הוא קופא (READ-ONLY, Rule 5)

מטרה: מפה מדויקת של מכונת-המצב + הוכחה חיה למה היום סווג Normal ולא השתדרג. אמת/הפרך את הממצאים הבאים (כבר נקראו ע"י Cowork ב-`state_machine.py`) עם פלט גולמי:

1. **מבנה 13 השלבים A1→C3** — מתי נכנסים ל-`_stage_c1` lock. אמת: `_stage_c1` (~711) נועל ב-conf≥threshold / 2 votes זהים / `session_min≥min_session_min_for_lock`. הדבק את ה-config values.
2. **שני טריגרי ה-reeval המתים אחרי lock** (`_check_reeval` ~781):
   - (א) `move_30 = None` **קבוע** (~783, הערה "Would need bar history") → טריגר תנועה-כיוונית לעולם לא יורה.
   - (ב) טריגר ה-range דורש `bar.atr>0` ו-`range/atr>2.0`, אבל `v9_bars_5min` **אין בו עמודת atr** → `bar.atr=None` → ratio=1.0 → מת.
   - **אמת:** `SELECT * FROM pragma_table_info('v9_bars_5min')` (אין atr?) + הדבק את ה-state החי של היום (stage/day_type/lock_state/conf).
3. **ה-rescore הוא ATR-relative, לא IB-relative:** `_rescore_from_behavior` (~660) נשען על `detect_behavior` (extensions + `range_ratio=range/ATR`), ו-`_stage_b6` (~620) מחליף type רק אם `new_conf−old_conf>0.15` (סף דביק). **אין מדידת IB-extension כיחס מרוחב ה-IB, אין VA-breakout acceptance, אין value-migration.**
4. **trace יום הדוגמה / יום RTH חי:** IB=7576/7596.5 (w=20.5), שיא 7632.75 → `E_up=1.77`, `R=2.77`. הראה שה-state נשאר Normal דרך כל ה-extension.

**פלט Phase 0:** מנגנון מדויק של ההקפאה + אישור/הפרכה של 4 הנקודות, raw evidence. **strategic-stop — הצג ל-Michael לפני Phase 1.**

## Phase 1 · מימוש שרשרת IB-relative דינמית — SHADOW-LOG בלבד (D-S1DYN)

מאחורי דגל (למשל `S1_DYNAMIC_RECLASS`, default OFF). **לא** משנה את ה-day_type החי שמוזן ל-Auth Table — רק **מתעד** would-be transitions.

לכל בר אחרי נעילת IB, חשב: `IB_w=IBH−IBL` · `E_up=max(0,hi−IBH)/IB_w` · `E_dn=max(0,IBL−lo)/IB_w` · `R=range/IB_w` · developing VAH/VAL/POC (מ-tpo) · CVD. **convention=total-range** (מומלץ ב-brief).

שרשרת monotonic (defaults tunable — תווית `# D-S1DYN`):
- **Normal → Variation:** `E_dom ≥ 0.10–0.15` accepted (≥2 TPO/sustained, לא wick) · `E_opp < ~0.10` · POC/value נע בכיוון · (אישור) CVD בכיוון.
- **Variation → Trend:** `E_dom ≥ ~1.0` (R≥~2.0) · one-timeframing שלם · VAH/VAL בצד הדומיננטי שבור ומקובל · אין acceptance חזרה ל-value הפותח · CVD חזק כיווני.
- **Neutral guard:** שני צדדים האריכו (`E_up≥~0.10` ו-`E_dn≥~0.10`) → Neutral. override.
- **false-breakout hold:** שבירה שנכשלת ב-acceptance (חזרה ל-IB תוך ~2 TPO / value לא נע / CVD מתהפך) → אל תשדרג.
- **late-session discount:** דכא שדרוג מ-spike ב-bracket אחרון.
- monotonic: רק שדרוגים תוך-יום; המצב הגבוה מחזיק ≥bracket; ירידה רק ל-Neutral.

**טבלה `v9_day_type_shadow_transitions`:** `ts, from_type, to_type, trigger(E_dom/R/value_mig/accept/cvd), E_up,E_dn,R, ib_w, vah,val,poc, cvd, session_date, session_min`.

**טסט regression:** דגל OFF → day_type החי **זהה-בייט** למצב הנוכחי. דגל ON → would-be transitions נרשמים, ה-day_type החי **עדיין לא משתנה**.

## Phase 2 · תצוגת ה-shadow chain ב-Build Status (להשוואה)

- הצג ב-S1 ב-build_status: ה-day_type **החי** (כמו היום) **לצד** ה-shadow chain (would-be: Normal→NV→Trend עם הטריגר שהפעיל כל מעבר + E/R). read-only.
- מטרה: שתראה במבט אחד "המערכת אומרת Normal, אבל הדינמי היה אומר Trend מ-12:30".

## Phase 3 · ולידציה (לפני שמדברים על Stage 3)
- השווה את ה-shadow labels מול קריאה ויזואלית של sessions היסטוריים (תואם?).
- כייל `X∈[0.10,0.15]`, `Y∈[0.8,1.2]` על **MES** (`v9_bars_5min`); כייל IB_w narrow/medium/wide לפי percentile (חלקית קיים ב-`classify_ib_width_atr`).
- מדוד תדירות day-type על הנתונים שלנו (אל תקבע priors ממקור יחיד).
- **Rule 5** לכל מספר.

## ⛔ Stage 3 (מחוץ להיקף — לאחר אישור Michael)
חיווט ה-shadow chain ל-day_type החי שמוזן ל-Auth Table — **זה** מה שישחרר את ה-Initiative של S2 (fire-audit §3). **לא בפרומפט הזה.** דורש: shadow labels אומתו מול קריאה ויזואלית + אישור מפורש (strategic-stop · risk surface).

## בסיום
עדכן ROADMAP (1c · D-S1DYN) + STATUS_BOARD (root→fix→verification) + DECISION_LEDGER (D-S1DYN → 🟢 IMPLEMENTED-SHADOW). תווית `D-S1DYN` בכל קובץ.

---

### עיגון קוד
- `backend/v9/systems/day_type/state_machine.py`: `_stage_c1` lock (~711), `_check_reeval` (~781, `move_30=None` ~783), `_rescore_from_behavior` (~660), `_stage_b6` conf-gate (~620,643), `classify_ib_width_atr`/`_last_atr_daily` (~324,535), `ib_class` (IBH/IBL/range).
- `backend/v9/systems/day_type/detector.py`: `detect_behavior`, `classify_range`, `check_reeval_triggers`.
- `v9_bars_5min` (אין atr — לגזור), tpo source (VAH/VAL/POC), CVD source.
- `backend/v9/systems/build_status/{day_type_inspector,types,aggregator}.py` — תצוגה.
- דגלים קיימים רלוונטיים: `S1_DAYTYPE_STAGING`, `S1_IB_WIDTH_ATR`, `S1_CVD_OPENING`.
