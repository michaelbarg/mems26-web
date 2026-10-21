# מעבר MEMS26 במלואו ל-iMac (מק-2) — ראנבוק 21.10.2026

**פסיקת-מייקל 21.10 (12:10 IL):** הפרויקט כולו עובר ל-iMac — המסחר, ה-DB, ה-LaunchAgents, הפרונט, הטלפון. ה-iMac
לוקח את **הזהות המלאה** של המקבוק (`MACHINE_TAG=מק-1`, רלה `mems26-mobile`, אותו נתיב-repo). המקבוק סוחר היום
כרגיל (DEMO, `is_sim=1`); **החיתוך הלילה אחרי 23:00**; ה-iMac סוחר ממחר (22.10) בפתיחה. המקבוק נשאר מכונת-פיתוח.

| | MacBook (MacBarg) — היום | iMac — ממחר |
|---|---|---|
| repo | `~/Downloads/mems26_web_git` | **אותו נתיב** `~/Downloads/mems26_web_git` (אפס שינויי-נתיבים) |
| רשת | ZT `10.1.118.147` · LAN `192.168.1.127` | ZT `10.1.118.70` · LAN `192.168.1.14` (SSH מהמקבוק עובד, מפתח מיולי) |
| Postgres | Postgres.app 18 · `mems26` 7.6 GB · 55 טבלאות | Postgres.app 18 (זהה) |
| Python | framework 3.9.7 (`/Library/Frameworks/Python.framework/Versions/3.9`) | אותו framework 3.9 קיים; חבילות = `pip freeze` של המקבוק (105 פינים) |
| Node | 24.10.0 ב-`/usr/local/bin` (pkg רשמי) | **חסר** — nvm 20 בלבד. צריך 24.10 ב-`/usr/local/bin` (פעולת-admin חד-פעמית) |
| Sierra | CrossOver bottle `Sierra Chart-3` → `~/SierraChart` (launcher `Y_SierraChart`) | bottle `Sierra Chart` → `~/SierraChart` (launcher `Y_SierraChart`) — **סגורה עד החיתוך** |
| LaunchAgents | 11 `com.mems26.*` | אותם 11 plists מילה-במילה (נתיבים זהים) |
| טלפון | Render `mems26-mobile` + ZT ישיר | Render `mems26-mobile` (ללא שינוי בטלפון) · ZT ישיר → `10.1.118.70:8000` |

## מה כבר בוצע (21.10, 12:04–13:00 IL, מהמקבוק דרך SSH)

1. **snapshot** על המקבוק: `~/mems26_snapshots/20261021T091708Z_pre-mac2-takeover-2026-10-21` (DLL+.env+plists+HEAD).
2. **קומיט+push** של כל העבודה הלא-קומוטית במקבוק (9 קבצי-קוד שונו + 14 חדשים: tree_routes, trading_gateway, five_min,
   effort_result, decision_tree_v3 variants, daily_dalton/tree_learner/walk_forward, 3 טסטי-רגרסיה, FLAG_REGISTRY, 1026 דוחות-postmortem) —
   `2618a68f7` → GitHub. (אחריו המשיכו קומיטים של cowork-dev run 387 `15adace6c`; cc-macbook ממשיך לעבוד על העץ — הרסינק הסופי הלילה מיישר.)
3. **pg_dump מלא** (format=directory, -j2, Z3): `~/mems26_migration_2026-10-21/db/mems26_full` = 1.2 GB, 53 TABLE DATA, 0 שגיאות.
   ספירות-ייחוס: `db/ROWCOUNTS_at_dump.txt`, `db/STATIC_COUNTS.txt` (footprint 5,531,689 · tick_reversal 2,681,775 — שתי הטבלאות הגדולות **סטטיות**: `FOOTPRINT_DISABLED=true`, `TICK_REVERSAL_DISABLED=true` ב-plist של ה-backend).
4. **iMac — ניקוי מאושר:** `~/Library/ScreenRecordings` (3 קבצי .mov מ-2020, 222 GB) נמחק · `~/Library/Metadata/SpotlightKnowledgeEvents` (46 GB) נמחק ·
   שני ה-repo הישנים (אוג׳) הועברו ל-`~/mems26_trash/` · 11 ה-plists הישנים של ה-iMac הורדו (`bootout`) והועברו ל-`~/Library/LaunchAgents/_retired_mems26_2026-10-21/`.
   **דיסק: 3.5 GB → 270 GB פנויים.** (ה-DB הישן של ה-iMac `mems26` מ-19.08 — יוחלף: Phase A משנה לו שם, Phase B מוחק.)
5. **rsync repo → iMac** (pass 1): 8,672 קבצים / 998 MB כולל `.git`, `.env`, `frontend/v9/.env.local`, `data/`; ללא `node_modules`, `.next`, `__pycache__`, `harness_out` (4.8 GB — מגיע הלילה). `git fsck` נקי על ה-iMac.
6. **חבילת-המעבר → iMac**: `~/mems26_migration_2026-10-21/` (dump, env copies, 11 plists, `pip_freeze_macbook.txt`, `sierra/` = Sierra4/Accounts4/KeyboardShortcuts4.config + 13 chartbooks + SymbolSettings + ACS_Source cpp (20.10) + DLL, `SHA256SUMS*.txt`).
7. **pip install** של ה-freeze לתוך framework-python-3.9 של ה-iMac — הורץ ברקע.

## Phase A — הכנת ה-iMac (היום, בטוח בזמן שהמקבוק סוחר)

סקריפט: **`scripts/mac2/phaseA_imac_prepare.sh`** (רץ **על ה-iMac**; אידמפוטנטי; צעד-צעד או `all`).
לעולם לא: פותח Sierra ב-iMac (Teton = לוגין יחיד — יעיף את הפיד של המקבוק) · מחמש (`LIVE_TRADING_ARMED` נכפה 0) · מעלה `mobile_relay` (כותב יחיד ל-PHONE_THREAD).

| צעד | מה | מי |
|---|---|---|
| `check` | repo, dump+checksums, Postgres, python, Sierra-סגורה | cowork/Claude-iMac |
| `pydeps` | `pip install -r pip_freeze_macbook.txt` + בדיקת-imports | אוטומטי |
| `node` | **node 24.10 ל-`/usr/local/bin`** — pkg רשמי (`sudo installer -pkg node-v24.10.0.pkg -target /`) או nvm+symlinks עם sudo | **מייקל / Claude-iMac עם סיסמה** |
| `npm` | `npm ci` ב-`frontend/v9` | אוטומטי (אחרי node) |
| `db` | `mems26`-הישן → `mems26_imac_old_aug2026`; `CREATE DATABASE mems26`; `pg_restore -j4`; אימות 55 טבלאות + ספירות מדויקות ל-2 הסטטיות | אוטומטי — **דיאלוג Postgres.app על מסך ה-iMac → Allow** (psql, pg_restore, Python — חד-פעמי לכל קובץ-הרצה) |
| `env` | `.env` = של המקבוק; `LIVE_TRADING_ARMED=0` | אוטומטי |
| `plists` | 11 plists → `~/Library/LaunchAgents` (לא נטענים) | אוטומטי |
| `sierra` | גיבוי קבצי-Sierra של ה-iMac → `$MIG/sierra_imac_backup_*`; העתקת configs/chartbooks/ACS_Source/DLL/SymbolSettings; ייצוא ישן של אוג׳ מוזז הצידה | אוטומטי (Sierra סגורה) |
| `services` | טעינת **backend (+frontend)** בלבד לאימות | אוטומטי (דיאלוג-Postgres ל-Python) |
| `verify` | `flag_guard` · health · `mems26_verify` (DLL/feed אדומים עד הלילה — מתוכנן) | אוטומטי |

הפעלה מהמקבוק: `ssh michael@192.168.1.14 'bash ~/Downloads/mems26_web_git/scripts/mac2/phaseA_imac_prepare.sh all'`.

## Phase B — החיתוך (הלילה ≥ 23:05 IL, מייקל נוכח ליד ה-iMac)

**עיקרון-על: בדיוק מכונה-אחת-חיה. קודם מורידים את המקבוק, רק אז מעלים את ה-iMac. Sierra של ה-iMac נפתחת רק אחרי ש-Sierra של המקבוק נסגרה.**

### B-1 על המקבוק — `scripts/mac2/phaseB_cutover_macbook.sh all`
1. `preflight` — שעה ≥23:00 · `position_qty=0` + אין פקודות-עובדות · אין עסקה פעילה · git נקי+pushed · ה-iMac נגיש · Sierra-iMac סגורה.
2. `snapshot` — `mems26_snapshot.sh "cutover-to-imac-…"`.
3. `stop` — **מייקל: Sierra-מקבוק → File ▸ Disconnect → Quit** (הסקריפט מחכה עד 15 דק׳) → `bootout` ל-11 הסוכנים → plists ל-`_retired_mems26_<date>/` → pkill → :8000/:3000 פנויים.
4. `dump` — pg_dump מלא טרי (שום דבר לא כותב ⇒ מדויק) + `ROWCOUNTS_cutover.txt` (count(*) לכל 55 הטבלאות).
5. `ship` — rsync סופי של ה-repo (הפעם **כולל `harness_out`**) + חבילת-המעבר; ה-iMac מאמת checksums.
6. `handoff` — מדפיס את פקודת ה-iMac.

### B-2 על ה-iMac — `scripts/mac2/phaseB_imac_golive.sh all`
1. `preflight` — dump+checksums · **המקבוק לא עונה ב-:8000** (אחרת מסרב) · Sierra סגורה.
2. `snapshot` · 3. `db` — restore ל-`mems26_new` → **אימות ספירות מדויק לכל 55 הטבלאות מול המקבוק** → החלפה אטומית בשם (`mems26`→`mems26_phaseA_<date>`, `mems26_new`→`mems26`) → DROP ל-`mems26_imac_old_aug2026` (מאושר).
4. `env` — `LIVE_TRADING_ARMED=0` נכפה (מייקל מחמש, לא Claude).
5. `services` — bootstrap ל-**כל 11** הסוכנים (כולל `mobile_relay` — מעתה ה-iMac הוא הכותב לטלפון, הרלה `mems26-mobile` ממשיך לעבוד ללא שינוי בטלפון).
6. `verify` — health · status.mode · `flag_guard` PASS · `/healthz` של Render · `mems26_verify`.
7. `sierra` — **ידני, מייקל (Claude-iMac יכול להקליק):** פתיחת `SierraChart_64 (Y_SierraChart).app` → חיבור לחשבון 37138283 → chartbook `AAMichael_lap25.Cht` →
   **Analysis ▸ Build Custom Studies DLL ▸ Remote Build** (מקור 20.10) → הסרה+הוספה של הסטאדי → Input 4 = `Y:\SierraChart_Data\v9_export`, Inputs 21/22 כמו במקבוק (נשמרים בצ׳ארטבוק) →
   Trade Simulation Mode לפי פסיקת-מייקל למחר → `sierra_state.json`/`5min.json` מתרעננים → `mems26_verify.sh` ירוק → `fire_drill.py` 🟢 GO.
8. `arm` — **מייקל בלבד:** `sed -i '' 's/^LIVE_TRADING_ARMED=.*/LIVE_TRADING_ARMED=1/' .env && launchctl kickstart -k gui/$UID/com.mems26.backend`.

### אחרי החיתוך
- טלפון: עמוד-Render ללא שינוי; סימניית-ZT הישירה → `http://10.1.118.70:8000/api/v9/mobile?key=<MOBILE_ACCESS_KEY>`.
- משימת-הסוף-יום המתוזמנת (23:20 IL, "יומן EOD") — כבולה היום למקבוק; **להכוון ל-iMac** (Claude desktop על ה-iMac / המשימה המתוזמנת עם "Require this computer" = iMac).
- 24/7 על ה-iMac (מייקל, sudo): `pmset -a sleep 0 disksleep 0 displaysleep 10 autorestart 1`; Postgres.app ב-Login Items; **Sierra ל-Login Items** (מחלקת T-43/T-259: אחרי ריבוט Sierra לא חוזרת לבד; `agents_bootstrap` מכסה את הסוכנים).
- המקבוק: מכונת-פיתוח. שינויי-קוד מגיעים ל-iMac **דרך git בלבד** (`git pull` + `flag_guard` + restart מכוון שם; DLL → `build_monolithic_cpp.sh --deploy` + Remote Build ב-iMac). `.env` פר-מכונה — שינוי-דגל במקבוק אינו עובר לבד.
- `TASK_LOG.md` / `STATUS_BOARD.md` / `LIVE_CHANNEL.md`: שורת-חיתוך חתומה.

## נקודות-כשל ידועות (מה שיתפוס אותך, ומה עושים)
- **דיאלוג Postgres.app ב-iMac** לכל קובץ-הרצה חדש (psql, pg_restore, Python, python3 של הסקריפטים) — חד-פעמי; "Allow" על המסך. (תועד כבר כ-"PG חסום-דיאלוג במק-2".) אם רוצים לבטל לגמרי: Postgres.app ▸ Settings ▸ הרשאות-לקוחות.
- **Teton = לוגין יחיד**: שתי Sierra על אותו חשבון מנתקות זו את זו (תקרית 07-11). לכן Sierra-iMac סגורה עד שהמקבוק ניתק.
- **ה-DLL הבינארי במקבוק מ-18.08 בעוד המקור ב-ACS_Source מ-20.10** — כלומר ייתכן שהסטאדי החי במקבוק אינו הבילד האחרון. ב-iMac נבנה **Remote Build מהמקור העדכני** — זה שינוי-התנהגות אפשרי לטובה שחייב אימות ב-`mems26_verify.sh` + `fire_drill` לפני חימוש. (ממצא — לא תוקן, לפסיקת-מייקל.)
- **`/usr/local/bin/npm` חסר ב-iMac** → `com.mems26.frontend` ייפול עד להתקנת node 24 (admin). ה-backend לא תלוי בזה.
- **node_modules לא מועתקים** — `npm ci` טרי ב-iMac (כלל CLAUDE.md).
- **rsync בזמן שכ-cc-macbook/cowork-dev מקמטים** — pass-1 תפס מצב-ביניים (HEAD `15adace6c`); הרסינק הסופי הלילה, אחרי `stop`, הוא המדויק. לפני `ship`: `git status` נקי + pushed במקבוק.
- **`.env` של המקבוק מגיע עם `LIVE_TRADING_ARMED=1`** — שני הסקריפטים כופים 0 לפני כל העלאת-שירות; רק מייקל מעלה ל-1.
- **ייצוא ישן של אוג׳ ב-`~/SierraChart_Data/v9_export` של ה-iMac** — הוזז הצידה ב-Phase A כדי שלא ייקרא כפיד.
- Rollback: במקבוק `for p in ~/Library/LaunchAgents/_retired_mems26_<date>/*.plist; do launchctl bootstrap gui/$UID "$p"; done` + פתיחת Sierra שם; ב-iMac `mems26_restore.sh` על ה-snapshot.

## קבצים
`scripts/mac2/phaseA_imac_prepare.sh` · `scripts/mac2/phaseB_cutover_macbook.sh` · `scripts/mac2/phaseB_imac_golive.sh` · חבילה: `~/mems26_migration_2026-10-21/` (בשתי המכונות) ·
רקע: `docs/runbooks/SECOND_MAC_SETUP.md`, `docs/runbooks/MAC2_CLONE_24_7.md`, `docs/handoff/CUTOVER_MAC2_2026-08-03.md`, `docs/SYSTEM_MANIFEST.md`.
