# KICK — cc-imac (Sonnet) · 2026-07-17 00:35 IDT
**פסיקת-מייקל 00:2x: אתה המבצע. עבודה רציפה עכשיו — לא בבוקר. סיירה על סים (מייקל העביר). דיווח מלא, הכל מתועד.**
מנהל+מאמת: cowork-dev (MacBook) — עוקב **דרך git בלבד** (הסנדבוקס שלו חסום ל-iMac ול-remote).

## 0 — סנכרון (לפני הכל)
`cd ~/mems26_web_git && git pull`. ודא שקיימים אצלך:
`docs/handoff/NIGHT_PROMPT_2026-07-17.md` (עם N9-N12) · `docs/handoff/MASTER_FIX_LIST_2026-07-17.md` ·
`scripts/ops_log.py` · `scripts/sim_matrix.py` · רשומת-SYNC `[2026-07-17 00:35]`.
**חסר משהו → עצור ובקש ממייקל להריץ מהטרמינל של ה-MacBook:** `cd ~/Downloads/mems26_web_git && git pull --no-rebase && git push`
(הקומיטים fb3f5ff2 · db764e25 · fa53406b + קומיט-הקיק מקומיים אצלו).

## 1 — גייט-בטיחות (לפני כל ירי, ומחדש לפני כל תא-מטריצה)
ה-backend על **mode=live** ⇒ route_setup חי הולך ל-Sierra. לכן:
1. `is_sim=1` מקובץ-export **טרי** (`~/SierraChart_Data/v9_export/*.json`) — הדבק את השורה כראיה.
2. Sierra ב-Sim-Mode ב-UI + חשבון-הסים **≠ 37138283** (חשבון-הלייב).
3. is_sim≠1 → **עצור, אל תירה, דווח**. אפס op=PLACE על לייב.

## 2 — סדר-ביצוע (הספקים המלאים ב-NIGHT_PROMPT; סטטוס-אמת ב-MASTER_FIX_LIST — עדכן אותו עם כל שינוי)
**N12 כבר בנוי** (ops_log.py) — רק חווט אליו כל ואצ'ר/סקריפט אצלך + commit-כל-שעה.
**N9-אופליין כבר רץ** (sim_matrix.py, 104 תאים PASS — `docs/reports/SIM_MATRIX_2026-07-17.md`) — אתה עושה את החלק-החם:

1. **N9-על-סיירה 🔴🔴** — לכל אחד מ-7 סוגי-היום (`DAY_TYPE_MANUAL_OVERRIDE=<תאריך>:<סוג>` + ריסטארט-קל): לכל תבנית רלוונטית (playbook≠SKIP) שגר סטאפ כשר דרך route_setup/debug_gateway_fire → **עסקת-סים מלאה E2E**: כניסה → סולם-הוראות (8/4, T0-T3) → MODIFY_STOP → מילוי-יעד → BE-אחרי-T1 → S6 סורק → סגירה/FLATTEN. תעד פר-תא: עבר/נחסם-באיזה-שער · סטופ-במקום-הנכון · סולם-מונוטוני · BE-אחרי-T1 · **רישום ב-5 המקומות** (command→fills→v9_trades→ledger→פרונט/פלאפון). + מקרה-שלילי פר-סוג-יום (מיקום-שגוי → נחסם-בשער-הנכון). **חובה לכסות גם S2 (REACTIVE/INITIATIVE)** — ב-07-16 כל העסקאות היו S4; תיקון le=3→le=4 (S-10) טרם נבחן חי. כלול אימות-כתיבת-exit_price (פער #33/#35/#40).
2. **N1 🔴🔴** — S1 חיה: פרסום 7-הסוגים + מעברים; קריטריון: ריפליי-16/07 משחזר Normal→Neutral_Center→Neutral_Extreme בזמני-מייקל (עוגן: 7585→7605→7567, סדרה tz-מודעת).
3. **N10 🔴** — קווי-POC/IB בצ'ארט + טבלת-הרמות/סטופים: השווה API (vah/val/poc/ib_h/ib_l) ↔ צ'ארט-פרונט ↔ סיירה; תקן את שכבת-הקווים + הטבלה. DoD: צילום-מסך שבו הקווים = הערכים-החיים = סיירה.
4. **N11 🔴** — פרונט `:3000` רץ-קבוע (LaunchAgent/pm2 — הוא **נפול** עכשיו) + פאנל-עסקאות חיות+סגורות; פלאפון: עסקאות (חיות+סגורות-היום) + אירועי-S6 + day_type מדויק + דוח-יומי. DoD: עסקת-סים מ-N9 נראית בשניהם תוך שניות.
5. **N2 → N4 → N8 → N3 → N5** לפי NIGHT_PROMPT (N8=CONFLUENCE flag-OFF+SHADOW בלבד; N4=ALERT-עכשיו/AUTO-אחרי-סים).
6. **N6 (בוקר, 16:00-16:25)** — החזרה-ללייב **רק** בפרוטוקול-הבוקר עם flag_guard PASS + fire_drill GO + פסיקת-GO של מייקל. עד אז נשארים על סים.
7. **N7** — שגרה.

## 3 — חוזה-דיווח (דרישת-מייקל: "דיווח מלא… הכל מתועד שם כדי שאוכל לעקוב")
- **כל פעולה** → שורה ב-`docs/reports/OPS_LOG_2026-07-17.md` דרך `scripts/ops_log.py` (מקום-מעקב אחד).
- **כל N שמסתיים** → רשומת-LOG ב-`AGENT_SYNC.md` (ראיה = פקודה+פלט-גולמי, חוק-5) + עדכון MASTER_FIX_LIST + **commit+push מיידי** — cowork עוקב רק דרך git.
- **❌ בתא-מטריצה** = תיקון מיידי + ריצה-חוזרת לפני התקדמות. **תקוע >20 דק'** → BLOCKER ל-SYNC + עבור ל-N הבא.
- **בסוף:** `docs/reports/EXECUTION_REPORT_2026-07-17.md` — טבלת-המטריצה המלאה 7×תבניות ✅/❌ עם ראיה פר-תא + סעיף **NOT-DONE** מפורש (לפי `CC_HANDOFF_CONTRACT.md`) + עדכון ROADMAP/STATUS_BOARD.

## 4 — גדרות (לא-משתנים)
op=EXIT שבור עד EXIT-v2 — אין STALL_EXIT/OPPOSITE_EXIT_V1, אין caller חדש ל-`_emit_exit`; יציאות = OCO מוצמד / MODIFY_STOP / FLATTEN_ACCOUNT בלבד · Standing-decisions של CLAUDE.md נשארים (אין "שחזור" דגלים כבויים) · כל שינוי risk-surface = flag-OFF + סים + פסיקת-מייקל · snapshot לפני כל שינוי out-of-git (`scripts/mems26_snapshot.sh`).

## 5 — הראיה הראשונה שאני מצפה לה ב-SYNC (תוך ~30 דק')
שורת-is_sim מה-export · trade_id-סים ראשון · פלט-גולמי של הרישום ב-5 המקומות. משם — פר-N.
