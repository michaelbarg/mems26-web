# -*- coding: utf-8 -*-
"""T-625 — register the Mac-2 (iMac) takeover in TASK_LOG / STATUS_BOARD / LIVE_CHANNEL (idempotent, in-place)."""
import re, sys, pathlib, datetime
REPO = pathlib.Path("/Users/michael/Downloads/mems26_web_git")
NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

ROW = ("| T-625 | 🟠 **מעבר הפרויקט במלואו ל-iMac (מק-2) — פסיקת-מייקל 21.10 12:10: \"להעביר את הפרויקט במלואו למחשב המק השני… המסחר יהיה שם, הכל יהיה שם — LaunchAgents כולל הפרונט\".** "
       "ה-iMac לוקח את הזהות המלאה (אותו נתיב `~/Downloads/mems26_web_git`, אותו `.env`, 11 ה-plists מילה-במילה, `MACHINE_TAG=מק-1`, רלה `mems26-mobile`); המקבוק = פיתוח בלבד. "
       "ראנבוק `docs/handoff/MAC2_TAKEOVER_2026-10-21.md` + `scripts/mac2/{phaseA_imac_prepare,phaseB_cutover_macbook,phaseB_imac_golive}.sh`. "
       "**Phase A בוצע 21.10 12:04–13:00 (מהמקבוק דרך SSH/LAN):** snapshot `20261021T091708Z_pre-mac2-takeover`; WIP-checkpoint `2618a68f7` (כל העץ הלא-קומוט נדחף); pg_dump מלא `-Fd -j2` (1.2 GB, 53 TABLE DATA, 0 שגיאות); "
       "iMac: 222 GB (`~/Library/ScreenRecordings`, 3 .mov מ-2020) + 46 GB (`SpotlightKnowledgeEvents`) שוחררו באישור ⇒ 270 GB פנויים; 11 הסוכנים הישנים `bootout` + plists ל-`_retired_mems26_2026-10-21`; שני ה-repo הישנים → `~/mems26_trash`; "
       "rsync repo 8,672 קבצים/998 MB (ללא node_modules/harness_out; harness_out+mems26_hist+snapshots+v9_archive ברקע) · pip freeze 105 פינים מותקן · DB שוחזר `pg_restore -j4` 298s ⇒ 7.45 GB · 55 טבלאות · 0 שגיאות · footprint 5,531,689 / tick_reversal 2,681,775 זהים עד השורה · "
       "`.env` זהה למקבוק עם `LIVE_TRADING_ARMED=0` · 11 plists במקום (לא נטענו) · Sierra-config/13 chartbooks/SymbolSettings/ACS_Source (shasum `014481f15d83` == monolith)/DLL הועתקו עם גיבוי · backend עלה לאימות ⇒ `health ok`, `flag_guard` PASS. "
       "ממצאים: (א) ב-iMac אין `/usr/local/bin/node` (רק nvm 20) ⇒ `com.mems26.frontend` ייפול עד התקנת Node 24.10 (admin); (ב) Sierra2 (Y_SierraChart2) נפתחה ב-iMac 12:41 לא ע\"י Cowork ומייצאת ל-v9_export — הפיד במקבוק לא נפגע (Teton לא ניתק); "
       "(ג) ה-DLL הבינארי במקבוק מ-18.08 בעוד מקור ACS_Source מ-20.10 ⇒ ב-iMac Remote Build מהמקור העדכני = שינוי-התנהגות אפשרי שחייב `fire_drill` לפני חימוש; (ד) TCC: הסוכן הראשון ב-iMac נדחה על `~/Downloads` (Operation not permitted) ואושר ⇒ עובד "
       "| 🟠 Phase A ✓ · Phase B הלילה ≥23:35 | cowork-dev (SSH מהמקבוק) · מייקל (Sierra, חימוש, admin) · Claude-iMac | **הצעד הבא:** ≥23:35 IL (אחרי משימת-23:20): במקבוק `bash scripts/mac2/phaseB_cutover_macbook.sh all` → ב-iMac `bash scripts/mac2/phaseB_imac_golive.sh all` → מייקל: Sierra `Y_SierraChart` + Remote Build + reload study + `mems26_verify` + `fire_drill` GO → חימוש; אחר-כך לכוון את משימת-23:20 ל-iMac (Desktop Commander שם), סימניית-ZT לטלפון → `10.1.118.70`, ולסגור ✅ |")

UPDATED = (f"**עודכן:** {NOW} IL cowork-dev (**[[T-625]] מעבר מלא ל-iMac — Phase A הושלם**: snapshot · WIP-checkpoint `2618a68f7` · dump 1.2 GB · iMac נוקה (270 GB פנויים) · repo+חבילה+pip · DB שוחזר 7.45 GB/55 טבלאות/0 שגיאות/ספירות זהות · `.env` disarmed · 11 plists · Sierra-config · backend `health ok`. "
           "Phase B (חיתוך) הלילה ≥23:35 לפי `docs/handoff/MAC2_TAKEOVER_2026-10-21.md`. פתוח ב-iMac: Node 24 (admin). **cc-macbook:** מהלילה המקבוק = פיתוח בלבד — שינויי-קוד מגיעים ל-iMac דרך git בלבד.)\n\n")

LIVE = (f"🟠 **[cowork-dev · [[T-625]] מעבר מלא ל-iMac · {NOW} IL · Phase A הושלם — Phase B (חיתוך) הלילה ≥23:35]** פסיקת-מייקל 21.10 12:10: הפרויקט כולו עובר ל-iMac (זהות מלאה: אותו נתיב, `.env`, 11 plists, מק-1, `mems26-mobile`); המקבוק סוחר היום כרגיל ומהלילה = פיתוח בלבד. "
        "בוצע: snapshot, WIP-checkpoint `2618a68f7`, dump מלא, iMac נוקה (222+46 GB) וסוכניו הישנים הורדו, repo+חבילה+pip ל-iMac, DB שוחזר (7.45 GB, 55 טבלאות, 0 שגיאות, ספירות זהות), `.env` disarmed, 11 plists, Sierra-config, backend-iMac `health ok`. "
        "**ל-cc-macbook:** אל תרסטרט ואל תשנה `.env` במקבוק אחרי 23:00 — ב-23:35 מורידים פה את כל `com.mems26.*` (plists → `_retired_mems26_2026-10-21`). **ל-Claude-iMac:** ראנבוק `docs/handoff/MAC2_TAKEOVER_2026-10-21.md` (גם בפרויקט `claude/MAC2_TAKEOVER_2026-10-21.md`); נדרש admin ל-Node 24 ב-`/usr/local/bin`. "
        "Sierra2 ב-iMac נפתחה 12:41 לא ע\"י Cowork — אינסטנס-המסחר (Y_SierraChart) נפתח רק בחיתוך.\n\n---\n\n")

BOARD = (f"[{NOW} cowork-dev · [[T-625]] · **מעבר מלא ל-iMac — Phase A**] 🔧 **ממצא → פעולה → ראיה.** **הממצא:** מייקל פסק (21.10 12:10) שהמסחר וכל המערכת עוברים ל-iMac; ה-iMac היה 2 חודשים מאחור (repo 19.08, סוכנים על קוד-אוגוסט, 3.5 GB פנויים). "
         "**הפעולה:** זהות מלאה בנתיב זהה ⇒ אפס שינויי-נתיבים; `.env`/plists מילה-במילה; DB בהעתקה מלאה (dump+restore) ולא בבנייה-מחדש; Sierra-config מועתק, Sierra-iMac סגורה עד החיתוך (Teton); `LIVE_TRADING_ARMED=0` נכפה — מייקל מחמש. "
         "**הראיה (Rule 5, גולמי):** iMac `pg_restore rc=0 errors=0 time=298s` · `select count(*) from v9_bars_footprint ⇒ 5531689` (== MacBook `STATIC_COUNTS.txt`) · `v9_bars_tick_reversal ⇒ 2681775` (==) · `information_schema.tables public ⇒ 55` · `curl 127.0.0.1:8000/api/v9/health ⇒ {\"status\":\"ok\"}` · `df /System/Volumes/Data ⇒ 270Gi avail` (היה 8.5Gi→3.5Gi) · `shasum ACS_Source == sc_study monolith ⇒ 014481f15d83`. "
         "**פתוח:** Node 24 (admin) · Phase B הלילה ≥23:35 (`scripts/mac2/phaseB_*.sh`).\n\n")

def edit(path, fn):
    p = REPO / path; s = p.read_text(encoding="utf-8"); n = fn(s)
    if n != s: p.write_text(n, encoding="utf-8"); print("updated", path)
    else: print("unchanged", path)

def task_log(s):
    if "| T-625 |" in s: return s
    s = re.sub(r"(\| T-624 \|[^\n]*\n)", lambda m: m.group(1) + ROW + "\n", s, count=1)
    # the newest **עודכן:** line goes right after the legend line
    s = re.sub(r"(\*\*מקרא:\*\*[^\n]*\n\n)", lambda m: m.group(1) + UPDATED, s, count=1)
    return s

def live(s):
    return s if "[[T-625]]" in s else LIVE + s

def board(s):
    return s if "[[T-625]]" in s else BOARD + s

edit("docs/plans/TASK_LOG.md", task_log)
edit("docs/handoff/LIVE_CHANNEL.md", live)
edit("docs/plans/STATUS_BOARD.md", board)
