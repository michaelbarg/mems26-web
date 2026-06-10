# CC — סוכן ביקורת‑EOD ל‑SHADOW + counterfactual פר S1/S2/S4 (2026‑06‑10)

> פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`. **בנה סוכן רב‑פעמי** (לא ריצה חד‑פעמית) שרץ בסוף כל יום‑מסחר. ריצה ראשונה: **סוף יום‑1 (היום, RTH close ~16:00 ET)**.

## מטרה (בקשת‑Michael)
סוכן‑EOD שמבצע **הכל** בסוף יום‑מסחר:
1. **לסיים את הבדיקות** (suite ירוק, כולל טסט‑I‑3).
2. **סריקת SHADOW** — האם המערכת עבדה **לפי האפיון**, והאם **התבניות קיבלו מידע נכון**.
3. **מחקר‑עומק counterfactual על כל שעות‑המסחר‑הרציף** — אילו תבניות **S1/S2/S4** היו צריכות להיות מזוהות, **האם המערכת נכנסה**, ו**כמה $ היה צריך להרוויח/להפסיד**.

## עיקרון‑על — אל תשכפל, תזמר את הקיים (CLAUDE.md §audit‑before‑build)
תשתית קיימת שהסוכן **חייב להשתמש בה** (KEEP/ADAPT, לא לבנות מאפס):
- `backend/v9/systems/build_status/missed_trade_detector.py` — "should‑have‑fired" (S2/S4, hypothetical_r). **ADAPT:** הרחב ל‑**S1** + ל‑replay של **כל הסשן** (כיום 6‑bar live) + הוסף **$** (לא רק R).
- `backend/v9/services/daily_quality_agent/agent.py` — מדרג עסקאות‑בפועל (quality). **KEEP** — שלב 2.
- `backend/v9/services/historical_replay.py` — מנוע‑replay. **KEEP** — להזין את הסשן הרציף.
- `backend/v9/services/eod_archiver.py` + `eod_archive_scheduler.py` — hook EOD 15:55 ET. **KEEP** — נקודת‑ההפעלה.
- `config/stop_anchors.yaml` + אפיון‑06‑10 (`MEMS26_S4_REVIEW_TABLE_2026-06-10.xlsx`) — מקור entry/stop/T1 ל‑P&L ה‑counterfactual.

## הסוכן — `backend/v9/services/eod_shadow_audit.py` (חדש, מתזמר)
ריצה idempotent ליום נתון. 4 שלבים:

### שלב 1 — לסיים בדיקות
- הרץ `pytest tests/v9/regression -q` + טסטי‑S4 הספציפיים. הדבק ספירת pass/fail. אם אדום → דווח ואל תמשיך לשלב 2 (strategic‑stop).

### שלב 2 — סריקת SHADOW (האם עבד לפי האפיון + מידע נכון)
**🔴 קודם‑כל — S1 staging‑timing (תקלה חוזרת · Michael 06‑10):** ודא שה‑S1 סיווג **בזמן**: `opening_type@15דק'` (≠NA) · **`day_type@30דק'` (≠UNKNOWN)** · `IB‑lock@60דק'`. הצלב `v9_day_type_state`: ה‑ts של הסיווג הראשון שאינו UNKNOWN מול (RTH‑open + 30דק'). **אם day_type לא סוּוַּג עד 30דק' → כשל קריטי** (חוסם auth/sizing של S2/S4 → `fire_setup=None`, בדיוק מה ש‑Cowork ראה בטסט‑I‑3) → דווח בראש‑הדוח + ספק `bar_count` ו‑`_day_type_on_bar` (האם המנוי ירה). זו **התקלה החוזרת** — תעד אם חזרה גם היום.

לכל עסקה שנפלטה היום (`v9_trades` של היום):
- **לפי האפיון?** entry/stop/T1 תואמים את האפיון‑הנעול (לא טיקים‑קבועים) · BE/trail לפי הכלל · sizing לפי auth. סמן ✓/✗ פר‑שדה.
- **מידע נכון?** ה‑4 ציר‑UAT + source‑of‑truth: ה‑CCI/day_type/IB/POC שהתבנית צרכה = ערכי‑Sierra (לא מסונתז). הצלב מול `v9_day_type_state` + exports.
- הרץ `DailyQualityAgent.run_eod_batch(today)` → grades.

### שלב 3 — מחקר‑עומק counterfactual פר S1/S2/S4 (הליבה)
**Replay** את כל הסשן‑הרציף של היום (`historical_replay`) → בכל בר הרץ זיהוי **S1·S2·S4** → לכל תבנית:
- **היתה צריכה להיזהות?** (התנאים המהותיים התקיימו — אותה formula מ‑`woodies_inspector`/detection).
- **האם המערכת נכנסה?** הצלב מול `v9_trades`. אם לא → **למה** (`why_not`: גייט/auth/day_type/R:R — מ‑missed_trade_detector).
- **P&L counterfactual ($):** entry/stop/T1 מהאפיון‑הנעול · MES $5/נק' · תוצאה = הגעה ל‑T1 (+reward×$5×contracts) או לסטופ (−risk×$5×contracts) לפי הברים שאחרי. פיצול 50%T1/30%T2/20%trail אם ניתן למדל; אחרת T1‑בלבד עם הצהרה.
- **טבלת‑פלט פר מערכת:** `pattern · ts · should_fire · system_entered? · why_not · entry/stop/T1 · hypothetical_$ · ΣP&L`.
- **דלתא:** ΣP&L‑counterfactual מול ΣP&L‑בפועל = "כמה השאיר על השולחן / חסך".

### שלב 4 — דוח + verdict
כתוב `docs/reports/EOD_AUDIT_<YYYY-MM-DD>.md`:
- **Verdict:** האם המערכת עבדה לפי האפיון? (כן/לא + נימוק) · האם התבניות קיבלו מידע נכון? · ΣP&L בפועל מול counterfactual פר S1/S2/S4.
- טבלאות שלב 2 + שלב 3. **NOT‑DONE** למה שלא ניתן (למשל מודל‑פיצול חלקי).

## הפעלה
- חבר ל‑`eod_archive_scheduler` (15:55 ET, אחרי הארכוב) **או** CLI `python -m backend.v9.services.eod_shadow_audit --date today`. idempotent.
- ריצה ראשונה: **היום בסוף RTH** (יום‑1).

## ⛔ אסור לגעת / כללים
- **observability/analytical בלבד** — הסוכן **לא** משנה fire‑path, לא מסחר‑לוגיקה, לא דגלים. (כמו daily_quality_agent.)
- source‑of‑truth: P&L מחושב מברים‑אמיתיים + אפיון; **אל תסנתז** ערכי‑CCI/מחיר. אם חסר → "missing" ביושר (Rule 1).
- Standing Decisions · §Polling Floors · אל תיגע ב‑sc_study/bridge.
- **תלות:** טסט‑I‑3 (סבב‑5) ואימות‑חי עדיין פתוחים — שלב 1 יתפוס אם אדום.

## Acceptance + Rule 5
- הדבק: ריצת‑הסוכן ליום‑1 (raw) → דוח `EOD_AUDIT_<date>.md` נוצר · טבלת counterfactual פר S1/S2/S4 עם $ · ΣP&L בפועל‑מול‑counterfactual.
- טסט (B1, anti‑tautological): על נתוני‑יום ידועים, הסוכן מזהה ≥1 missed/captured נכון + מחשב P&L צפוי. RED‑on‑revert.
- **דוח** עם NOT‑DONE. (ענף ahead — Michael ידחוף.)
