# CC — השלמת הפערים הפתוחים · 2026-06-05 eve

חוזה `CC_HANDOFF_CONTRACT.md` + `CC_VERIFICATION_PROTOCOL.md` + `CLAUDE.md §Index Protocol`
(אינדקס קודם). בסיום: `VERIFY_GAPS_2026-06-05.md` עם raw output. מקובץ מ-`MEMS26_ISSUES_REGISTER.md`.

═══════════════════════════════════════
## A · DO — housekeeping (בטוח, בצע)
═══════════════════════════════════════
1. **commit מסודר של עבודת-הסשן** (הכל uncommitted → סיכון-אובדן ברסטארט). commits נפרדים:
   B-13 cutover (staleness+session-CT+G1+S3mute) · day_type endpoint+wrapper · B-11 bridge_inspector ·
   choppiness continuous · A5 advisory · frontend (Build Status P0 + Trades Phase 1). **paste `git log --oneline`** אחרי.
2. **regen index** — `python3 scripts/gen_index.py` → commit (`chore(index)`). ודא `backend/main.py` מובחן מ-`v9/main.py`.

═══════════════════════════════════════
## B · DO — סגירת residuals בטיחות/תצפיתיות (עם regression)
═══════════════════════════════════════
3. **I-7 · B-13 write-guard** — החזר את בדיקת ה-**price-band על נתיב-הכתיבה** ב-`bars.py` POST `/5min`
   (בר off-market לא נכתב), אבל **שמור ברים-ישנים-תקינים** להיסטוריית-צ'ארט. regression: בר-glitch off-market
   עם ts עדכני → לא נכתב; בר-ישן-תקין → נכתב. (לפני LIVE.)
4. **I-15 · trend_state מקור-יחיד** — `woodies/current`=RED מול `build/pattern-status`=GRAY (A1 veto שגוי על כל
   9 התבניות). אחֵד מקור-אחד ל-trend_state; הצלב מול Sierra CCI-14. הלוח מציג סיבת-חסימה **שגויה** — תקן.

═══════════════════════════════════════
## C · DIAGNOSE-ONLY — דורש אישור Michael (אל תשנה trading-logic)
═══════════════════════════════════════
5. **I-13 · sizing=reject מפספס תבניות** — חשוף את קלט-ה-sizing ב-`details{}` (`woodies_system.py:721`,
   `aux_count>=2`). דווח: כמה תבניות נחסמו היום על reject, והאם הסף שמרני-מדי (מול counterfactual). **הצע**, אל תשנה.
6. **I-14 · opening→entry chain** — opening_type סווג (`OPEN_REJECTION_REVERSE`) אך אין כניסת-פתיחה. עקוב את
   הנתיב opening→day_type→entry; דווח איפה נקטע (Auth-Table SKIP×Normal? נתיב לא-מחווט?). **דווח, אל תתקן.**
7. **I-10 · עץ-החלטות ל-S2/S3** — לפי `DECISION_TREE_MAP_2026-06-05.md`: **הצע** עיצוב לעץ A1–A7-שקול
   ל-S2/S3 + חשיפה ב-build_status. **עיצוב בלבד** (trading-surface → אישור).

═══════════════════════════════════════
## נפרד / parked (אל תאגד)
═══════════════════════════════════════
- **B-14** (כפילות-צ'ארט) — `CC_PROMPT_B14_CHART_5MIN_DUP` (thread נפרד).
- **I-11 S3 footprint 0-ברים** — **parked** (S3 muted פר-Michael). לבדוק רק כשמבטלים-השתקה.
- **I-3 ZLR** — counterfactual ב-EOD-agent (לכשתידרך).
- **I-9 EOD-cron** — תוקן ע"י Cowork (שער CT≥15:00).

## VERIFY (raw output, Rule 5)
A: `git log --oneline -10` + index regen summary. B: regression RED→GREEN לכל תיקון + צילום-לוח (trend_state
אחיד). C: דוחות-אבחון (לא קוד). NOT-DONE: כל מה שנשאר + פערי Sierra↔backend.
