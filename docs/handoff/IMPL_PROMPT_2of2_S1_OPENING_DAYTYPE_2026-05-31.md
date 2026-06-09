> ⚠️ **הוחלף ע"י `MEGA_E2E_2of2_S1_S2_S3_IMPL`** (גרסת e2e מתוקנת 31/5).
> השתמש בגרסת ה‑E2E.

# מגה‑פרומפט מימוש 2/2 — S1: סיווג פתיחה (CVD/PE) + day_type מדורג

> פרומפט **מימוש** (משנה קוד) — להדבקה בסוכן קוד עם גישה ל‑repo `mems26_web_git`.
> מאושר עקרונית ע"י Michael 31/5 (פתיחה ✅; מודל day_type מדורג ✅ עם C‑period
> כשלב ולידציה). **קרא קודם `CLAUDE.md` ו‑`.cursor/rules/...mdc`.**
>
> ⚠️ כללי ברזל: SHADOW בלבד · אסור לגעת ב‑order/risk · **flags default OFF**
> (day_type מזין playbook/sizing → שער אישור Michael לפני הפעלה) · **בסיס רגרסיה
> לפני כל שינוי** · CVD/ATR ממקור‑אמת, `None` כשחסר · אסור להפעיל דגל בלי אישור.

---

## 0 · מה אנחנו מתקנים (MANIFEST)

מוסיפים CVD/PE לסיווג הפתיחה, ממירים gap ו‑IB‑width ליחסי‑ATR, והופכים את day_type
ל**מדורג עם ולידציה מתמשכת**. הכל מאחורי flags, priors בקונפיג.

### A · סיווג הרצת הפתיחה — `day_type/detector.py::detect_opening_type`
- **קלט נוכחי:** מחיר בלבד, `directional_ratio = net_move/total_range ≥ 0.7`, 3 ברים.
- **משתנה ל:** הוסף מדדי CVD על חלון הפתיחה (מתוך `v9_bars_footprint.delta` /
  `v9_bars_5min.cumulative_delta`, **בתוך חלון session — reset‑aware**):
  - `delta_i = ask_vol−bid_vol` (כבר ב‑DB); `net_CVD`, `abs_delta_sum=Σ|delta_i|`.
  - **`PE = net_CVD / abs_delta_sum`** (מדד חד‑כיווניות ראשי), `DE = net_CVD/total_vol`.
  - `divergence_flag` (מחיר extreme חדש מול CVD לא מאשר).
- **מודל דו‑שלבי:** `label_15` (09:45, provisional, bias בלבד) → `label_30`
  (10:00, מחייב). priors: DRIVE אם `PE_30>0.65 & range_exp>1.0 & ¬divergence`;
  AUCTION אם `|net_CVD|/total_vol<0.15 & PE_30<0.25`; REJECTION_REVERSE אם
  `CVD_sign_flip & divergence בקצה`. divergence guard מדכא DRIVE.
- **חתימה:** tick‑rule/aggressor מה‑footprint (לא BVC).

### B · gap — `state_machine.py::_stage_a1` (~408)
- **נוכחי:** `if abs(gap) > 2.0` (מוחלט).
- **משתנה ל:** `gap_ratio = (open−prev_close)/ATR14_daily` + 4 קטגוריות
  (Tiny<0.3 · Small 0.3–0.7 · Medium 0.7–1.2 · Large>1.2) כ**ממד נפרד**, לא סף בינארי.

### C · רוחב IB — `detector.py::classify_ib_width` + `schemas.py`
- **נוכחי:** NARROW<15 · MEDIUM 15–25 · WIDE>25 נק' מוחלט.
- **משתנה ל:** `IB_range / ATR14_**daily**` ב‑4 tiers: צר<0.5 · נורמלי 0.5–1.0 ·
  רחב 1.0–1.5 · **קיצוני>1.5** (R03, 5,519 ימים). הוסף ערך `EXTREME` ל‑`IBWidth`
  enum ומפה אותו ב‑`DECISION_MATRIX` (קיצוני→נטייה contained/Neutral). **שים לב:
  IB=מבנה session → ATR יומי** (בניגוד ל‑S2 שמשתמש ב‑ATR 5‑דק').

### D · day_type מדורג + re‑diagnosis — `state_machine.py`
- **נוכחי:** נעילה ב‑13:00 / conf≥0.85 / 2 votes.
- **משתנה ל‑4 שלבים:** 30דק'=סיווג ראשוני (≤60%, provisional) · 60דק' (10:30)=
  ה‑IB נסגר → רוחב IB÷ATR → חיזוק/סיווג מחייב · **ולידציה מתמשכת** מ‑10:30 (הרחב
  את `_check_reeval` עם טריגרי C‑period 10:30–11:00 + עומק נסיגה: רדודה<25%→החזק,
  עמוקה≥50%→re‑diagnose). **אין צ'קפוינט 90 דק' נפרד** — נבלע בולידציה המתמשכת.

**להשאיר:** `directional_ratio` (יחסי), delta/width rules, הצבעות מבניות.

---

## 1 · מנגנון הבקרה (חובה)

1. **Feature flags default OFF:** `S1_CVD_OPENING=False`, `S1_DAYTYPE_STAGING=False`,
   `S1_IB_WIDTH_ATR=False`. כבוי = הקוד הקיים בדיוק.
2. **Shadow‑scoring:** כשהדגל דולק במצב shadow — חשב את הסיווג החדש ו**רשום
   אותו לצד הישן** (לוג/עמודה), **בלי לנתב אותו ל‑playbook/החלטה**. השוואה ל‑EOD truth.
3. **בסיס רגרסיה לפני כל שינוי (גיבוי):**
   - `tests/v9/regression/test_s1_baseline_golden.py` — מריץ את ה‑state machine על
     רצף ברים ידוע ושומר golden snapshot (opening_type, ib_width, day_type, lock).
   - אחרי שינוי: flag OFF ⇒ זהה ל‑golden; flag ON ⇒ הבדל צפוי בלבד.
   - commit golden+טסט **לפני** שינוי לוגיקה.
4. **CVD/ATR ממקור‑אמת:** מ‑`v9_bars_footprint`/`v9_bars_5min`; reset‑aware (CVD
   מתאפס בגבול session — חשב בתוך חלון RTH). חסר נתון → `None`/fallback, לא לסנתז.
5. **שינוי אחד בכל פעם:** A(opening CVD) → B(gap) → C(IB width) → D(staging).
   רגרסיה ירוקה + report בין שלב לשלב.

## 2 · תוצרים + שערים
- קומיט נפרד לכל חלק + רגרסיה ב‑diff.
- דוח `docs/reports/S1_OPENING_DAYTYPE_IMPL_<date>.md`: manifest שבוצע, golden
  coverage, פלט רגרסיה גולמי, דוגמת shadow (old vs new vs EOD).
- **שער:** דגלים כבויים. day_type מזין playbook → **הפעלה רק אחרי אישור Michael**
  + soak ~60 ימי SHADOW לנעילת priors.

## 3 · אסור
- להפעיל flags · לנתב סיווג חדש ל‑playbook/sizing/order לפני אישור · לסנתז CVD/ATR ·
  לחשב CVD חוצה‑session reset · לשנות directional_ratio/ספירות מבניות · refactor רחב.

> STATUS: מימוש מאחורי flags בלבד + shadow‑scoring. priors. נעילה+הפעלה אחרי
> soak ואישור Michael.
