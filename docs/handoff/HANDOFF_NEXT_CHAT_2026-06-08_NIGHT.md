# Cowork Handoff — צ'אט הבא (2026-06-08 לילה)

אתה (Cowork הבא): **orchestrator + verifier בלתי-תלוי** של MEMS26. CC מבצע על ה-Mac; אתה כותב פרומפטים,
מצליב (**Rule 5: פקודה+פלט גולמי**), מעדכן בורדים, ומאשר לפני ביצוע fire-path.
**קרא קודם:** `CLAUDE.md` (במיוחד §Standing Decisions · §Chop Gates · §S2⟂S3 · §Index — `backend/main.py`≠`backend/v9/main.py`) + הזיכרון.

## 0 · חוקים מחייבים (קרא לפני שאתה נוגע במשהו)
- **§Standing Decisions (חדש היום):** כל דגל default-OFF הוא **קבוע עד ש-Michael מבטל במפורש**. **אסור** להדליק/לשחזר/להחזיר —
  לא בקוד/config/.env/refactor/merge/migration. זה לא באג. re-enable = risk-surface → strategic-stop + אישור-Michael.
- **fire-path / trading-logic** → אבחן-קודם, הצג ראיות גולמיות, STRATEGIC-STOP, Cowork מבקר, אז תיקון.
- **אינדקס קודם** · אל תאבחן מ-endpoint יחיד · הצלב כל טענת-CC (Rule 5: paste פקודה+פלט, לא "confirmed").
- inspector ≠ engine: לאורך כל היום נמצאו פערים (choppiness, belly_cot_amt, GRAY, b4). **תמיד אמת מול ה-engine/fire-path, לא ה-inspector.**

## 1 · מה נסגר/נעשה היום (כולל commits)
**הסרת גייטים (flag-gated, default = ההתנהגות-החדשה, reversible):**
- S2 `choppiness_ok` OFF (`S2_CHOPPINESS_GATE`) · Layer0 chop veto OFF (`LAYER0_CHOP_GATE`) — committed `a8cb1fb`.
- `tick_reversal_15`+`tpo` הוצאו מ-critical-streams (verdict לא BLOCKED מהם) — `a8cb1fb` + frontend `29cc28b`. (תיקון טענה: הם חסמו תצוגה, לא ירי.)
- **S2 ⟂ S3** — תלות COT/AMT הוסרה (`S2_REQUIRE_COT_AMT`, default off) — ⚠️ **עדיין uncommitted** (CC ב-Phase 0).
- CLAUDE.md §Standing Decisions + §S2⟂S3 + `test_s2_independent_of_s3` — ⚠️ **uncommitted** (Phase 0).

**commits של CC:** `4a073c6` choppiness חלון-מתגלגל · `3b06a5d`/`4b5faf9` expansion יחסי-לממוצע · `b1b4400` D-CHOP decision.

**אבחון-שורש (מאומת ע"י Cowork):** 4 באגים שמנעו ירי — דוח: `docs/reports/STOP_AND_BUGS_INVESTIGATION_2026-06-08.md`.

## 2 · 🔴 4 הבאגים — CC מתקן עכשיו (סדר: #1→#3→#2→#4)
- **#1 [P0] S4 stop=None crash** — `woodies_system.py:320,332` (DLL-fallback ZLR/HFE, `stop=None` קשיח); `schemas.py:78 stop: float`.
  **הוכנס ב-`58d6538` (06-01)** ⇒ S4 קורס על כל DLL-ZLR **שבוע שלם** (לא V2!). תיקון = Option A (stop אמיתי דרך `compute_stop`, **לא 0.0**).
- **#3 [P1] S2 detection על בר-חלקי** — `five_min_system.py:874-886`→`:917`→`:532 b4=bars[-1]` חלקי. גם **מקלקל entry** (22:10 entry=7425.25 מול close 7414.75). תיקון = `buffer[:-1]` + 4 תנאים (engine+inspector אותו חלון · emit עקבי · flag · FHB/ATR לא נגעים · לוג-b4 חי).
- **#2 [P2] S2 DB persist ts** — `five_min_system.py:1132` (`fromtimestamp` על ISO-string). Reactive SHORT 22:10 ירה אך לא נשמר.
- **#4 [P1] Woodies DB write ts** — `bars.py:911` (epoch-int → timestamptz). כל ברי-woodies לא נשמרים (persistence).

## 3 · מה לבדוק כש-CC יחזיר (Rule 5 — אל תאשר בלי raw)
1. **Phase 0:** commit לאצווה ה-uncommitted (S2⟂S3 + CLAUDE + test) + 3 טסטים GREEN + restart.
2. **#1:** STOP_ANCHORS_V2=1 + בר עם `zlr_detected=True` → **אין** `process_bar error` · ZLR ב-`active_patterns` · **stop>0 אמיתי (לא 0.0)** · R:R שפוי · git-blame מצוטט.
3. **#3:** engine+inspector על אותו חלון-מלא · emit לא התפצל · FHB/ATR לא נגעו · **לוג-b4 חי** מוכיח את הפרמיסה · flag+regression RED-on-revert.
4. **#2/#4:** ts-parse עמיד (string+epoch) · `safe_writer` לא נשבר לטבלאות אחרות · regression.
5. **אף דגל default-off לא הודלק** (§Standing Decisions).

## 4 · מה CC עוד צריך להשלים מהמגה-פרומפטים
- **`CC_COMBINED_DETECTION_FIX_AND_SHADOW`:** חלק A (=באג #3, בתור-התיקון) · חלק B (ground-truth/near-miss) **הושלם** בדוח-החקירה · **חלק C (frontend) טרם בוצע** — נדחה כי RTH סגור: (a) פאנל "זיהוי תבניות" בטאב SHADOW מקובץ S2/S4 · (b) תיקון תצוגת-day_type freshness (observer, לא סף-360s/"Sierra תקוע") · (c) זרמים-מושתקים לא אדומים-BLOCKED.
- **`CC_MEGA_BUGFIX_4`:** חקירה הושלמה → תיקון בתהליך (סעיף 2).

## 5 · פתוח / החלטות ממתינות
- **פער-CCI:** ה-CCI שלנו=-98.2 מול DLL שסימן ZLR ב-19:00 ⇒ ה-CCI שלנו ≠ Sierra. לפי CLAUDE.md (Sierra=מקור-אמת) — לכן ה-DLL-fallback קיים (ותיקון #1 הוא ה-linchpin). **לחקור seed/period/smoothing.**
- **דגל GRAY (`S4_GRAY_GATE`, soft, GRAY-בלבד):** Michael אישר — **פארק** עד שבאג #1 מתוקן (S4 קורס לפני הגייט; GRAY כבר *רך* ≥0.55). לאחר #1 — לבדוק אם GRAY בכלל חוסם, ואז ליישם אם צריך.
- **near-miss / K-ים:** מתועד (`near-miss table` בדוח). לא לשנות בלי אישור-Michael.
- ZLR CCI delta · I-1 day_type instance-split (opening_type=UNKNOWN/session_min=0) · I-22 pnl_r ~50× · I-18/I-20 TZ mask — פתוחים.

## 6 · הצעד הראשון בצ'אט הבא
1. הצלב את חבילת-התיקונים של CC (סעיף 3, Rule 5).
2. אחרי שבאג #1+#3 חיים+מאומתים — בקש ריצת-RTH הבאה ובדוק אם ZLR/Reactive **באמת יורים** (active_patterns + v9_trades).
3. אז: דגל-GRAY (אם צריך) · חלק C frontend · פער-CCI · סנכרן בורדים.
