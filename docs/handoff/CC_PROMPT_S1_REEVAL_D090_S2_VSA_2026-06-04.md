# CC PROMPT — S1 re-eval fallback + D-090 observer + S2 VSA enable (3 סעיפים, אישור Michael) · 2026-06-04

**פעל לפי `CC_HANDOFF_CONTRACT.md`.** **אישור Michael 2026-06-04:** VSA gate חי + אכיפת observer ל-S1.
מבוסס על אבחון-PG שאומת ע"י Cowork (`CC_PROMPT_S1_S2_DIAGNOSIS_RERUN_PG`). **smallest correct change + טסט-רגרסיה לכל סעיף.**
זכור: **wire the full pipeline** — שינוי שמגיע לכל הענפים המושפעים, בלי dead-wiring חלקי (תקרית ה-5-דגלים).

## סעיף 1 — S1 re-eval: fallback ל-ATR (מחייה triggers בלי schema/Sierra/bridge)
**שורש (אומת):** אין עמודת `atr` ב-`v9_bars_5min` → `bar.atr`=None. ה-state-machine **כבר** מחשב `self._last_atr_daily`
(rolling 14-bar ranges, `state_machine.py:257,320-324`), אבל אתרים מסוימים קוראים `bar.atr` ישירות בלי fallback → מתים.
**פעולה — החל fallback בכל אתר שקורא `bar.atr` בלי גיבוי (לא רק אחד — חיווט מלא):**
- `_check_reeval()` `state_machine.py:784`: `atr = bar.atr` → `atr = bar.atr or self._last_atr_daily` (מחייה trigger#1 extreme-move + trigger#3 range-exceeded).
- gap ATR `state_machine.py:427-428` (קורא `bar.atr`) — אותו fallback.
- סרוק שאר השימושים ב-`bar.atr` ב-day_type ואכוף עקביות (היכן שיש כבר fallback ל-range — להשאיר).
**טסט-רגרסיה:** עם `bar.atr=None` ו-`_last_atr_daily` מוגדר → trigger#1/#3 נבדקים ופועלים (לא no-op).

## סעיף 2 — D-090: אכיפת OBSERVER ל-S1 (סגירת signal-leak)
**שורש (אומת):** `backend/v9/systems/wrappers.py:86-102` — S1 (רשום OBSERVER) מחזיר `Signal(system_id=1)` ב-LOCKED/LOCKED_LOW_CONF
→ 22 signals יצאו ב-PG בניגוד לרישום.
**פעולה (החלטת Michael = אכוף observer):** הוסף `return None` לפני בלוק יצירת ה-Signal (S1 לא יורה). השאר את חישוב/עדכון
ה-state כפי שהוא (observer ממשיך לסווג) — רק ה-Signal נחסם.
**טסט-רגרסיה:** wrapper של S1 **לעולם** לא מחזיר Signal (גם ב-LOCKED_LOW_CONF+playbook). day-type classification עדיין מתעדכן.

## סעיף 3 — S2: הדלקת VSA כ-gate חי + רישום כל הווריאציות למעקב
**שורש (אומת):** `S2_VSA_VOLUME` כבוי → gate=legacy (90% drop, 0.5% pass) → S2 de-facto מושתק. הווריאציות קיימות
(`five_min_system.py:504-511`, נמדדו על PG: VSA 22.1% · RVOL 20.9% · STRICT 11% · legacy 0.5%).
**פעולה (החלטת Michael = VSA חי + track all):**
- **הדלק `S2_VSA_VOLUME=1`** — הדגל נקרא מ-env ב-call-time. ייצא אותו ב-`scripts/start_all.sh` (ואם ה-backend עולה דרך LaunchAgent — גם שם). אמת שכל 4 אתרי-הדגל (`five_min_system.py:499,513,537,632`) פועלים עקבי תחת הדגל — **בלי wiring חלקי**.
- **gate חי = VSA (Variant A).** (STRICT/RVOL נשארים מחושבים, לא-חיים.)
- **track all (shadow-compare):** ודא ש-`variants_passed` (A_VSA/B_RVOL/C_STRICT verdicts) **נשמר פר-setup שנורה** — ל-`v9_five_min_setups` (כרגע ריקה — לחווט את כתיבת ה-setup) או ל-quality JSON ב-`v9_trades`. כך נשווה וריאציות על דאטה-SHADOW אמיתי וננעל את הטובה אחרי soak.
**טסט-רגרסיה:** עם הדגל ON, gate=VSA; setup שנורה כולל `variants_passed` נשמר ונגיש בשאילתה.

## Acceptance (✓/✗ + raw)
- [ ] S1: כל אתרי `bar.atr` בלי-fallback קיבלו `or self._last_atr_daily` (grep) + טסט trigger#1/#3 ירוק עם bar.atr=None.
- [ ] D-090: `return None` ב-wrappers.py לפני Signal; טסט "S1 wrapper לא מחזיר Signal" ירוק; classification עדיין מתעדכן.
- [ ] S2: `S2_VSA_VOLUME` מיוצא ב-start_all.sh; gate=VSA בכל האתרים; setup שנורה שומר `variants_passed` (raw מ-PG).
- [ ] regression מלא ירוק · commit פר-סעיף (3 commits) · `git log` · סעיף NOT-DONE.

## Invariants
localhost-PG בלבד · ❌ לא Render/Upstash/prod-PG · SHADOW=paper (אין נתיב ברוקר — בטוח להדליק S2) · No silent failures ·
אל תיגע sc_study/risk-caps/polling · wire-the-full-pipeline · Cowork מאמת בלתי-תלוי (בדגש: חיווט מלא של הדגל + ה-fallback, ושאף Signal לא דולף מ-S1).
