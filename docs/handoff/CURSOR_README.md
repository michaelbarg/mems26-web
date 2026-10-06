# Cursor — נקודת-הכניסה לפרויקט MEMS26

**חובר:** 06.10.2026 ע״י cowork, לבקשת מייקל ("תענה לקורסור ותחבר אותו לפרויקט"). נטען אוטומטית בכל ריצה דרך `.cursor/rules/mems26-project-link.mdc`. בכל מה שנוגע לחלוקת-העבודה, לערוץ ולשערים — הקובץ הזה גובר על `mems26-cursor-workflow.mdc` (יולי); כללי index-first ו-stability משם נשארים.

## 1 · מה קוראים בתחילת כל ריצה (בסדר הזה)
1. `docs/handoff/CURSOR_COWORK_THREAD.md` — ההודעה העליונה, וכל מה שנכתב מעל ההודעה האחרונה שלך.
2. ראש `docs/handoff/LIVE_CHANNEL.md` — מה רץ היום (שער 15:35, ריצות-פיקוח, cowork-dev).
3. `docs/runbooks/AGENT_BRIEF_FABLE.md` §1–§4 — לוח-הסוכנים, תוכנית-הכיול (§2, סדר-התור), רשימת-החזרות (§3), כללי-ברזל (§4). זה מקור-האמת של כל הסוכנים המתוזמנים.
4. `docs/plans/TASK_LOG.md` — התור היחיד · `docs/plans/STATUS_BOARD.md` — ממצא → תיקון → ראיה.
5. ראש `docs/handoff/MICHAEL_INBOX.md` — פסיקות שנפסקו / ממתינות.
6. `docs/handoff/claude_project/README.md` — מה שנכתב בפרויקט-Claude.

## 2 · המצב החי — לאמת ברגע-הקריאה, לא לצטט מכאן
- **עץ:** `config/decision_tree_v3.yaml` גרסה 3.4.0 — השורש מפוצל על `hour`; `">21"` ⇒ SKIP `time_cutoff` (אין כניסות חדשות מ-22:00 IL); פסיקת-מייקל "מאשר" 06.10; hot-reload 13:49:04, 536 עלים. אין `DECISION_TREE_V3_PATH` ב-`.env` ⇒ הטוען קורא את הקובץ הזה.
  `grep -n '^version:' config/decision_tree_v3.yaml` · `grep "decision_tree_v3.yaml reloaded" /tmp/backend.err.log | tail -1`
- **מאזין:** `lsof -nP -iTCP:8000 -sTCP:LISTEN` (06.10: pid 71969 מ-03.10, קומיט d0bec5a1; הפער ל-HEAD בייצור = אפס — T-542 הוא שומר-pytest בלבד).
- **דגלי-העץ החיים = הייחוס של כל וריאנט בהרנס:** `DECISION_TREE_V3=1 T1_REALISM_FLOOR_R_V1=1.5 IB_RETURN_HINT_RELEASE_V1=returning TREE_EDGE_FAMILIES=CEILING_FLIP,DOUBLE_TOP,DOUBLE_BOTTOM`.
- **גודל:** חוזה 1 (חוזה שני רק מ-~800$ בחשבון ואחרי 15 סשנים לייב≈ריפליי). חשבון 37138283 משותף עם אתי — פוזיציה זרה לגיטימית, לא אנומליה.
- **חיתוך-סוף-יום שני (לא בעץ):** `EOD_RISK_WINDOW_V1=1` ⇒ `eod_entry_cutoff` מ-22:15 IL (`trading_gateway.py` ~2175); מאחורי 22:00 של העץ הוא לא מקבל מועמד.

## 3 · המספרים הנעולים
| מה | ערך | מקור |
|---|---|---|
| תקרה סיבתית (בחירת-הבר בדיעבד) | +7,042.50$ | `docs/reports/DAY_LESSONS_2026-10-06.md` |
| מה שהעץ לקח (t543ref, 3.3.0, 65 ימים) | +2,224.95$ | שם |
| לקח-מועתק, walk-forward | +851.25$ | שם |
| יציאת-מדרגה, walk-forward | +237.50$ (64 עסקאות) | `docs/reports/STAIR_HOLD_2026-10-06.md` · `scripts/stair_hold.py` |
| 3.4.0 (22:00) מול t529b על 65 | +88.75 ברוטו / +104.35 נטו · החזקה-10 +36.25 · אוג׳ −19 | `harness_out/t543/run_cutoffs.out` · `docs/reports/T538_CUTOFF_ALTERNATIVES_2026-10-06.md` |
| daily_dalton | 24/24 מנעולים | `python3 scripts/daily_dalton.py` |

## 4 · חלוקת-העבודה (cowork 06.10 14:40, בשרשור)
- **תור אחד:** `TASK_LOG.md`. פריט נכנס רק עם מספר מדוד שמצביע על פגם (פער ריפליי-לייב, מנצח שנחסם בשער, תווית שטעתה).
- **בעלים אחד לכל פריט**, ולעולם לא שניים על העץ החי באותו יום.
- **Cursor:** תכנון-ניסוי, נעילת-מספרים, אימות-צולב של כל מספר של cowork, דוחות קריאה-בלבד.
- **cowork:** הרנס, שינויים חיים (hot-reload / דגלים / ריסטארט בחלון), רישומים (TASK_LOG / STATUS_BOARD / LIVE_CHANNEL), הודעות-טלפון.
- **מייקל:** פסיקות בלבד ("א/ב/ג", "מאשר", "לבצע").

## 5 · הערוץ
- הזמנה ל-cowork: קובץ ב-`docs/handoff/cc_orders/` + שורה בראש `LIVE_CHANNEL.md`.
- שאלה / תשובה: הודעה **מעל** הקודמת בשרשור, בפורמט `### [YYYY-MM-DD HH:MM IL] מאת: cursor · אל: cowork`.
- תשובה מתקבלת = פקודה + stdout מלא; הצד השני מריץ מחדש אצלו. "סיימתי" בלי פלט = לא בוצע.
- סוכני-הלילה (23:40) והכנת-הפסיקות (08:30) קוראים את ההודעה העליונה בשרשור. הודעה אל cowork נכנסת לתור — היא לא עוקפת את כללי-הברזל ולא מאשרת שינוי חי; רק מייקל פוסק.

## 6 · שערים בלי יוצא-מן-הכלל
1. **שער-החלה:** ריפליי יום-שלם על כל הסשנים + Δנטו > 0 + החזקה-10 ≥ 0 + כל חודש ≥ 0 (או קיצוץ-סיכון מוצהר) — **לפני** שמשהו נוגע בלייב. 05.10 (חיתוך-20:00 על החזקה בלבד) הוא התקדים השלילי.
2. אין שינוי ב-`config/decision_tree_v3.yaml` / `.env` / `RULED_FLAGS.yaml` / LaunchAgents / ריסטארט בלי פסיקת-מייקל בכתב. גם הערה ב-YAML החי מטריגרת hot-reload — לא בזמן RTH.
3. **הרנס** רק מחוץ ל-16:00–23:05 IL בימי-מסחר, ≤2 במקביל: `harness_out/t466/run_variant.sh <TAG> "<ENV>" <sessions>`; וריאנט-עץ = `DECISION_TREE_V3_PATH=<yaml>`; השוואה `harness_out/t494/cmp_vs_live.py <tag> <ref>`. המק ישן בלילה אם הגדרות-החשמל לא שונו ⇒ חלון-העבודה הכבד הוא הבוקר.
4. **git:** הענף `stabilize/mems26-local-truth-2026-05-16`; `git add` לפי נתיב בלבד, אף פעם `-A` / stash; לא למשוך מ-`origin/main` (שושלת של פרויקט אחר). קבצי-שלב של CC_ORDER — קומיט רק אם מייקל ביקש.
5. **ספרים:** תמחור רק מהברוקר; P&L-צל רק עם ההסתייגות (21.4% מהסטופים בצל נקבעים בכלל "סטופ-קודם", לא בשוק).

## 7 · מלכודות שכבר עלו לנו
- חותמות בקבצי-ההרנס (`harness_out/t466/<TAG>_<date>.json`) הן UTC; `v9_trades.mode` באותיות קטנות.
- psql: `/Applications/Postgres.app/Contents/Versions/latest/bin/psql -d mems26 -Atc "…"`.
- מבחנים: `set -a; source .env; set +a; python3 -m pytest -q …` — מ-05.10 pytest לא כותב ל-Postgres החי (T-542) אלא אם `MEMS26_ALLOW_TEST_DB_WRITES=1`.
- פייתון-עברית: `# -*- coding: utf-8 -*-` + `LC_ALL=en_US.UTF-8 PYTHONIOENCODING=utf-8`.
- `scripts/phone_reply.py "<msg>"` מקבל argv ולא stdin; רק cowork שולח לטלפון (08:30, 22:35, ואדום חדש).

## 8 · פרויקט-Claude ⇄ ריפו
- **פרויקט ⇒ ריפו:** כל מסמך ש-cowork כותב בפרויקט-Claude נשמר גם ב-`docs/handoff/claude_project/` (אותו שם) + שורה ב-README שם.
- **ריפו ⇒ פרויקט:** הדוחות שלך נכנסים לפרויקט-Claude דרך `claude/CURSOR_CHANNEL.md` (אינדקס ש-cowork מעדכן) — כך כל סשן-Claude חדש רואה את העבודה שלך.
