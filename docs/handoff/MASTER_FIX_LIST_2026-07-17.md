# רשימת-אב: תיקונים שבוצעו + מה שעדיין פתוח (16→17/07)

**מי מבצע (עדכון מייקל 2026-07-17 00:2x — גובר על 23:5x):** **cc-imac (Sonnet) מבצע — עבודה רציפה עכשיו, לא בבוקר**, לפי הסדר N9(סיירה)→N1→N10→N11→N2→N4→N8→N3→N5→N6→N7; **cowork-dev מנהל+מאמת כל N דרך git**. סיבות: העבודה שנותרה דורשת ידיים על ה-iMac (עסקאות-סים אמיתיות על Sierra, פרונט `:3000` נפול שם, צילומי-מסך של הצ'ארט), ולסשן-ה-Cowork הנוכחי אין Desktop Commander / HTTP-ל-iMac / git-remote (ראו פסקת-הגישה). הרשימה הזו היא מקור-האמת היחיד לסטטוס; מתעדכנת עם כל שינוי.

**מציאות-גישה (עדכון 00:2x, סשן-Cowork חדש):** הסנדבוקס הנוכחי מנותק-יותר מקודמו: Desktop Commander לא-זמין · `git pull/push` ל-remote חסום (אין הרשאות) · HTTP ל-iMac חסום-allowlist (403, אומת 00:23). cowork יכול רק לערוך+לקמט מקומית ב-MacBook; **הקומיטים המקומיים (fb3f5ff2 · db764e25 · fa53406b + קומיט-הקיק) מגיעים ל-cc-imac רק אחרי שמייקל מריץ `git pull --no-rebase && git push` מהטרמינל של ה-MacBook.** כל הביצוע בפועל — על ה-iMac בידי cc-imac.

---

## ✅ בוצע (תיקוני-שורש שכבר הוחלו + נדחפו)

| # | תיקון | קובץ/דגל | סטטוס-פריסה | ראיה |
|---|---|---|---|---|
| 1 | **תווית-יום כפויה** (השורש של 10 חסימות location_gate): fallback ל-classify_replay נחסם לאחרי-סגירה בלבד; אמצע-סשן→None כן | `trade_context.py` `extract_g1` + 3 pin-tests | 🟢 חי ב-iMac (ריסטארט cc-imac 21:30) | `test_no_forced_daytype_midsession.py` ירוק |
| 2 | **feed_watchdog טבלה-מתה**: קורא `v9_bars_5min_woodies` החי, לא `v9_bars_5min` הקפוא (חסם כל ירי בפתיחה) | `feed_watchdog.py` `_db_max_bar_age` + 2 pin-tests | 🟢 חי (21:30) | `test_feed_watchdog_live_table.py` ירוק |
| 3 | **S2 חסום מול 4-חוזים**: `le=3`→`le=4` בסכמת-הפלט (כל ירי-S2 מלא=4 נזרק) | `output_schema.py:27` | 🟡 הוחל 20:47, דורש ריסטארט-ערב | S-10 ב-SYNC |
| 4 | **RR רוטציה**: `RR_MIN_ROTATION=0.65` — מעביר את המנצח-החסום 18:15, חוסם את ה-0.28 | `RULED_FLAGS.yaml` + `trading_gateway.py` | 🟢 חי (GO 19:25) | `test_rr_graded_rotation.py` ירוק |
| 5 | **LSMA lag**: `LSMA_SUSTAIN_BARS=2` | RULED | 🟢 חי | flag_guard |
| 6 | **מפסק-הפסדים**: `PATTERN_LOSS_BREAKER=0` (פסיקת-מייקל 21:40, אחרי 2 הפסדי-ZLR) | RULED | 🟢 חי | SYNC 21:40 |
| 7 | **עקיפת-יום ידנית**: מנגנון `DAY_TYPE_MANUAL_OVERRIDE=<תאריך>:<תווית>` + 07-16:Neutral_Center | `trade_context.py` `get_live_day_type` | 🟢 חי (cb1fe6fa) | SYNC 21:50 |
| 8 | **פלאפון**: שער-מפתח + כרטיס-פר-תבנית + כרטיס-דוח-יומי + כפתור-flatten | `mobile_monitor.py` | 🟢 חי | — |
| 9 | **גישת-פלאפון מכל-מקום**: מנהרת-Cloudflare + מפתח | cloudflared (iMac) | 🟢 חי | URL+key נמסרו |
| 10 | **פיד-החלטות + פאנל**: כל ניסיון-ירי מתועד (fired/blocked+שער) | `trading_gateway.py` `/gateway/decisions` | 🟢 חי | endpoint מגיב |
| 11 | **מוניטור-פערי-ברים**: הוכיח ברי-פתיחה שלמים (29/29) | `bar_gap_monitor.py` | 🟢 חי | verdict |
| 12 | **דוח-יומי**: EOD מה-DB → MD+JSON לפלאפון | `gen_daily_report.py` | 🟢 קיים | — |
| 13 | **תוכנית-לילה**: N9-N12 ב-NIGHT_PROMPT + S-12 ב-SYNC | docs/handoff | 🟢 נדחף | a32ae7a4 |
| 14 | **3 ממצאי-אימות-לילה**: גייט-is_sim · פרונט-נפול · עוגן-N1 | AGENT_SYNC | 🟢 נדחף | e3ee1fde·7d5a57c4 |
| 15 | **מחקר CONFLUENCE_RI_ZLR**: מפרט + ורדיקט 40% → SHADOW-first | CONFLUENCE_PATTERN_SPEC | 🟢 מפרט | 30b52ede |
| 16 | **N12-ליבה: לוג-תפעול מרכזי** — `scripts/ops_log.py` (append-only, fcntl-lock, CLI+import, נבדק) → `docs/reports/OPS_LOG_<date>.md` | scripts/ops_log.py | 🟢 מקומי-MacBook (ממתין-push) | fb3f5ff2 · OPS_LOG_2026-07-16.md |
| 17 | **N9-ליבה (אופליין)**: `scripts/sim_matrix.py` — 13 תבניות × 8 סוגי-יום דרך route_setup אמיתי (playbook-gate מבודד), **104 תאים PASS** (keep=61/skip=43), 6/6 שליליים-נגד-מגמה, אינווריאנטות-ניהול; רגרסיה 990-pass / 0-regressions | scripts/sim_matrix.py | 🟢 מקומי-MacBook (ממתין-push) | db764e25 · fa53406b · docs/reports/SIM_MATRIX_2026-07-17.md |

---

## 🔴 פתוח — טרם בוצע (**cc-imac מבצע עכשיו, רציף** — פסיקת-מייקל 00:2x; cowork מאמת פר-N דרך git)

| N | משימה | מה חסר | סטטוס |
|---|---|---|---|
| **N12** | **לוג-תפעול מרכזי** `scripts/ops_log.py` → `OPS_LOG_<date>.md` | ליבה ✅ (fb3f5ff2). נותר: חיווט הוואצ'רים/מתזמנים בצד-ה-iMac (session-watch · post_restart_verify · bar_gap_monitor · feed_watchdog · S6 · ריצות-N9) + commit-כל-שעה | 🟡 ליבה-בוצעה · חיווט → cc-imac |
| **N9** | **מטריצת-הדמיה** 7 סוגי-יום × כל תבנית, עם ניהול-סטופ+עסקה+בדיקת-מחסומים | אופליין ✅ (sim_matrix.py, 104 תאים — db764e25). נותר החלק-החם: **עסקאות-סים אמיתיות E2E על Sierra** (כניסה→סולם→MODIFY_STOP→מילוי-יעד→BE→S6→סגירה) + רישום-ב-5-מקומות (command→fills→v9_trades→ledger→פרונט/פלאפון) + שלילי-פר-סוג-יום; **gate is_sim=1 פר-תא** | 🔴 **הראשון של cc-imac — עכשיו** |
| **N1** | **מערכת-1 חיה**: פרסום המסווג ה-7-סוגי + מעברים acceptance-driven + תווית-מדויקת בכל מסך | חיווט-פרסום + מטריצת-מעברים + איחוד-תצוגה. קריטריון: ריפליי 16/07 = Normal→Neutral_Center→Neutral_Extreme בזמני-מייקל | 🔴 הגדול — לא-התחיל |
| **N10** | **קווי POC/IB בצ'ארט + הטבלה** | שכבת-הקווים לא מציגה ערכים-חיים; תיקון-תצוגה | 🔴 לא-התחיל |
| **N11** | **פרונט חי + פלאפון מלא** (חיות+סגורות+S6+day_type) | פרונט `:3000` **נפול** על ה-iMac; להרים קבוע + תצוגת-עסקאות | 🔴 לא-התחיל |
| **N2** | **ביקורת-דוקטרינה** תבנית×סוג-יום → רולינגים ממוספרים | טבלת-תאים-הפוכים + הצעות | 🔴 לא-התחיל |
| **N4** | **הצלת-S6**: ALERT עכשיו / AUTO אחרי-סים; חיווט `DROP_TARGET` | הפער: DROP_TARGET advisory-בלבד, לא-מחווט | 🔴 לא-התחיל |
| **N8** | **CONFLUENCE_RI_ZLR** בנייה (flag-OFF, SHADOW-first, n≥15) | קוד: חריג-2-חוזים, G-fresh, תחרות-slot | 🔴 מפרט-בלבד |
| **N3** | **ZONE_LIMIT_ENTRY_V1** + סים (כניסה-מאוחרת-מדי) | מפרט+קוד | 🔴 לא-התחיל |
| **N5** | **סריקת Rule-1**: אין-סינתזה-על-מקור-שקט | audit רוחבי | 🔴 לא-התחיל |
| **N6** | **פרוטוקול-בוקר קשיח**: החזרת is_sim→live + flag_guard + fire_drill GO | סקריפט-שער לפני-פתיחה | 🔴 קריטי-לבוקר |
| **N7** | **שגרה**: דוח-יומי · תצוגת-עסקאות-כולל-S6 · fallback-Redis · כיול · אינדקסים | חלקי | 🟡 חלקי |

### פריטי-SYNC פתוחים (לא-N)
- **S-7** — עסקה-חיה לא מוצגת בפרונט/פלאפון + תצוגה-מלאה-כולל-S6 → **מתמזג ל-N11**.
- **S-9** — 🔴 אירוע-לייב: שורט-2 יתום + phantom-heal לא-מרפא (19:37); reconciler מזהה ולא-מרפא. לסגור עם N4/N7.
- **S-11** — דוח-S6-EOD 07-16 (הריצה-המתוזמנת עיוורת בסנדבוקס) → מתמזג ל-N9/N7.

---

## גייטי-בטיחות (לא-משתנים)
- **is_sim=1 מאומת מ-Sierra לפני כל ירי-סים** — ה-backend על `mode=live`.
- op=EXIT שבור-אסור עד EXIT-v2 → יציאות רק OCO/MODIFY_STOP/FLATTEN_ACCOUNT.
- אפס op=PLACE על לייב. החזרה-ללייב רק בפרוטוקול-בוקר (N6) לפני הפתיחה.
- שינוי risk-surface → פסיקת-מייקל.
