# התקנת MEMS26 על מק שני — ראנבוק ל-Claude Code (2026-07-11)

## §0 — מצב-בפועל של ה-iMac (עדכון 07-12, גובר על §1-§2 במקרה של סתירה!)
ה-iMac **כבר מותקן** (installer-bundle מ-2026-07-05, ‏SECOND_MACHINE_FIRST_PROMPT):
- הריפו החי: **`~/mems26/mems26_web_git`** (לא ‎~/Downloads!) על הענף הנכון, ב-7f623c29.
- ‏backend ‏:8000 + ‏bridge + ‏export_promoter רצים כ-LaunchAgents מהנתיב הזה.
- סיירה קיימת (‏~/SierraChart*) אבל **בגרסת 07-05** — הסטאדי/צ'ארטבוק/twconfig מפגרים.
- ‏`.env` קיים מגיל ה-bundle — **חסרים בו דגלי 07-08→07-12** (כולל FIXED_CONTRACTS_2=1!).
לכן: **מיישרים את הקיים, לא משכפלים**: origin → ‏GitHub ‏(https://github.com/michaelbarg/mems26-web.git),
‏git fetch + ‏FF ל-HEAD, יישור `.env` לפי `config/RULED_FLAGS.yaml` עד ‏flag_guard ‏PASS ‏47/47.
העותק הישן `~/Downloads/mems26_web_git` (ענף sim ישן, ‏PAT חשוף ב-remote) — להסגר/למחוק
**אחרי** שמייקל מרוטט את הטוקן ב-GitHub. עד ה-cutover-GO: סיירה ב-iMac לא מתחברת ל-Teton.


**מטרה:** עותק מלא ומתעדכן של המערכת. ברירת-מחדל: מכונת פיתוח/גיבוי (בלי סיירה).
מסחר נשאר על המכונה הראשית אלא אם מייקל אומר אחרת.

## 0. עקרונות (לפני הכל)
- קרא את `CLAUDE.md` בשורש — כל כללי-הזהב (דגלים פסוקים, ‏bridge-localhost-only,
  ‏snapshot לפני out-of-git) חלים גם כאן.
- אל תדליק שום דגל פסוק-OFF; אל תשנה `.env` בלי snapshot; אל תפנה לשום cloud.
- המכונה הזו לא סוחרת עד פסיקת מייקל — אל תפעיל bridge מול סיירה ואל תפרוס DLL.

## 1. תלויות
```bash
xcode-select --install                       # git וכלי-בסיס
# Postgres.app מ-https://postgresapp.com (גרסה 18) — להפעיל פעם אחת
# Node/npm: https://nodejs.org LTS (או brew install node אם יש brew)
python3 --version                            # 3.9+ נדרש
```

## 2. שכפול הריפו
הרימוט פרטי: `https://github.com/michaelbarg/mems26-web.git`
```bash
gh auth login        # או SSH key שמייקל יאשר ב-GitHub
git clone https://github.com/michaelbarg/mems26-web.git ~/Downloads/mems26_web_git
cd ~/Downloads/mems26_web_git
git checkout stabilize/mems26-local-truth-2026-05-16   # הענף החי
```

## 3. קובץ הסודות `.env` — לא בגיט!
מייקל מעביר אותו ידנית (AirDrop/Drive) מהמכונה הראשית:
`~/Downloads/mems26_web_git/.env` (או מה-snapshot האחרון ב-`~/mems26_snapshots/`).
להניח בשורש הריפו. בלעדיו שום דבר לא עולה (BRIDGE_TOKEN, 47 דגלים פסוקים).

## 4. בסיס-נתונים
```bash
/Applications/Postgres.app/Contents/Versions/latest/bin/createdb mems26
```
מתחילים ריק (העבר הוא disposable per CLAUDE.md §DB). אם מייקל רוצה היסטוריה:
במכונה הראשית `pg_dump mems26 > mems26.sql` → כאן `psql mems26 < mems26.sql`.

## 5. התקנה
```bash
bash scripts/install_mems26.sh      # אידמפוטנטי: תלויות-פייתון, LaunchAgents מתובנתים
cd frontend/v9 && npm install && cd ../..
```
**הערה:** ה-LaunchAgent של הפרונט נכשל על TCC/launchd במכונה הראשית (npm/PATH +
הרשאות Downloads) — אם קורה גם כאן, השתמש ב-screen כמו `scripts/start_all.sh`.

## 6. אימות (חובה, Rule 5 — צטט פלטים)
```bash
python3 scripts/flag_guard.py        # PASS — all 47 ruled flags match
python3 scripts/fire_drill.py        # 🟢 (יתלונן על feed — אין סיירה כאן; זה צפוי)
bash scripts/mems26_verify.sh        # יסמן חוסר-DLL/feed — מקובל במכונת-פיתוח
curl -s localhost:8000/api/v9/health # אחרי הרמת backend
```
מה שקשור לסיירה (feed, DLL, exports, bridge) **צפוי אדום** במכונה בלי סיירה — לא באג.

## 7. שגרת עדכון
```bash
bash scripts/mems26_update.sh        # או: git pull origin stabilize/mems26-local-truth-2026-05-16
```
אחרי כל pull: `python3 scripts/flag_guard.py` + אם השתנו דגלים — לקרוא את ה-diff
של `config/RULED_FLAGS.yaml` לפני שממשיכים.

## 8. חלוקת-עבודה — פסיקת מייקל 2026-07-11 (מחליפה את הניסוח הקודם)
**המכונה הזו (השנייה) = מכונת-המסחר-באמת. המכונה הראשונה = פיתוח בלבד.**
- כל תיקון/פיצ'ר נכתב ונבדק במכונת-הפיתוח → push ל-origin → כאן **מושכים ופורסים**
  לפי פרוטוקול-הקידום (§10). **אסור לערוך קוד ישירות על מכונת-המסחר** — גיט הוא
  הצינור היחיד; חריג יחיד: `.env` מקומי, ותמיד עם snapshot לפני.
- דוחות שנוצרים כאן: suffix `_TRADING` כדי שלא להתנגש.

## 9. הקמת מכונת-המסחר (גשר + סיירה) — מאושר (פסיקת מייקל 2026-07-11)
**הגשר כבר בגיט** (`bridge/` + LaunchAgent מההתקנה) — הוא רק כבוי כי אין לו מה לקרוא.
מה שחסר הוא סיירה עצמה. שלושה רכיבים:

### 9א. התקנת-סיירה חד-פעמית (העתקה מהמכונה הראשית — לא בגיט!)
במכונה הראשית, לארוז ולהעביר (דיסק חיצוני/רשת; זה גדול):
```bash
# בראשית: כל התיקיות האלה = סיירה + Wine + צ'ארטבוק + twconfig + הגדרות
~/SierraChart/            # כולל ACS_Source, Data (צ'ארטבוק .cht), התצורות
~/SierraChart2/           # אם בשימוש
# עטיפת ה-Wine/CrossOver שמריצה את סיירה (כפי שמותקנת אצל מייקל)
```
ביעד: לשמור באותם נתיבים בדיוק (`~/SierraChart/...`). ואז:
```bash
mkdir -p ~/SierraChart_Data/v9_export      # תיקיית-הייצוא שהסטאדי כותב אליה
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.mems26.export_promoter.plist
```
כניסת Teton = מייקל מזין סיסמה בסיירה עצמה (לא לשמור בקבצים).

### 9ב. ה-DLL/סטאדי המעודכן — תמיד מהגיט, לא מהעתקות
המקור הקנוני `sc_study/` נמצא בריפו ומתעדכן ב-pull. פריסה במכונה הזו:
```bash
git pull
bash scripts/build_monolithic_cpp.sh --deploy   # auto-snapshot + העתקה ל-ACS_Source
# ואז בסיירה: Analysis → Build Custom Studies DLL → Remote Build → טעינת הסטאדי מחדש
```
לוודא ב-Study Input 4 ‏(V9 Export Directory): ‏`/Users/<user>/SierraChart_Data/v9_export/`.

### 9ג. הפעלת הגשר (אחרי שסיירה חיה ומייצאת)
```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.mems26.bridge.plist
tail -f /tmp/bridge.err.log     # לוודא: push ל-http://localhost:8000 בלבד!
```

### ⚠ אילוצים קשיחים
1. **חיבור-דאטה אחד:** ‏Teton/CME מנתק את החיבור הראשון כשנכנסים מהשני — שתי המכונות
   לא סוחרות במקביל. מכונה 2 = גיבוי-חם/פיתוח; מעבר מסחר = פסיקת מייקל מפורשת.
2. ‏`.env`, סיירה, ו-LaunchAgents הם out-of-git — כל שינוי בהם כאן מחייב
   `scripts/mems26_snapshot.sh` לפני (בדיוק כמו בראשית).
3. אחרי כל pull שנוגע ב-`sc_study/` — לחזור על 9ב (build+Remote Build), אחרת
   ה-DLL הרץ מפגר אחרי הקוד. `scripts/mems26_verify.sh` תופס את הדריפט הזה.


## 10. פרוטוקול-קידום: מפיתוח למסחר (המסלול הקבוע מעכשיו)
**במכונת-הפיתוח (לפני push):** טסטים ירוקים + `flag_guard` PASS + עדכון
`RULED_FLAGS.yaml`/`FLAG_REGISTRY.yaml` אם נגעת בדגל + קומיט עם הסבר-סיכון.

**כאן (מכונת-המסחר), לכל קידום — 8 צעדים, בסדר הזה, רק כשהשוק סגור או flat:**
```bash
bash scripts/mems26_snapshot.sh "pre-promote-$(date +%m%d)"   # 1. גיבוי
git pull origin stabilize/mems26-local-truth-2026-05-16       # 2. משיכה
python3 scripts/flag_guard.py                                 # 3. ‎47/47 PASS (אם דגל חדש — מייקל מעדכן .env לפי ה-diff)
# 4. אם השתנה sc_study/: bash scripts/build_monolithic_cpp.sh --deploy
#    → בסיירה Remote Build + reload + הוכחת-סים (scripts/d1_exit_proof.sh)
launchctl kickstart -k gui/$(id -u)/com.mems26.backend        # 5. ריסטארט
python3 scripts/fire_drill.py                                 # 6. 🟢 GO
bash scripts/mems26_verify.sh                                 # 7. עקביות מלאה (DLL↔repo, feed, DB)
# 8. שורת-לוג ב-docs/plans/STATUS_BOARD.md: מה קודם, ראיות, מי אישר
```

### שער-מעבר (cutover) חד-פעמי — מתי המסחר באמת עובר לכאן
עד שכל אלה ✅, המסחר נשאר במכונה הראשונה:
- [ ] §1-§7 בוצעו (backend+frontend+DB חיים, flag_guard 47/47)
- [ ] §9א סיירה הועתקה + Teton מתחבר + פיד חי (live_price זז)
- [ ] §9ב DLL נפרס מהגיט + Remote Build + **הוכחת-סים מלאה עוברת**
      (BUY→T1→תזוזת-סטופ→EXIT→FLATTEN_ACCOUNT→sierra_state.json מתעדכן)
- [ ] §9ג הגשר חי, localhost בלבד, פידר-activity על חשבון-האמת
- [ ] העברת DB: במכונה הישנה `pg_dump mems26 > cut.sql` → כאן `psql mems26 < cut.sql`
      (ההיסטוריה נחוצה ל-tp_audit/לדג'ר/halt היומי)
- [ ] דריל-קצה-לקצה על סים ביום-שוק שקט + אישור-GO כתוב של מייקל
אחרי ה-GO: במכונה הישנה מכבים את הגשר+פידר (למניעת חיבור-Teton כפול), והיא
נשארת פיתוח בלבד.
## 11. חיבור-מרחוק בין המכונות (SSH) — הצינור להעברות ולפריסות
**במכונת-המסחר (Mac2), פעם אחת — מייקל:**
1. System Settings → General → Sharing → **Remote Login: ON** (וגם **Screen Sharing: ON**
   — בשביל Remote Build של סיירה מרחוק).
2. באותו מסך רואים את הכתובת (למשל `michael-trading.local` או IP).

**ממכונת-הפיתוח (פעם אחת):**
```bash
ssh-copy-id <user>@<mac2>.local        # מזינים סיסמה פעם אחת — מכאן והלאה מפתח
ssh <user>@<mac2>.local hostname       # אימות
```

**מה זה פותח:**
- העתקת-סיירה בלי דיסק: `rsync -avz --progress ~/SierraChart/ <user>@<mac2>.local:~/SierraChart/`
  (וכנ"ל SierraChart2 + ‏.env).
- קידום-מרחוק: `ssh <mac2> 'cd ~/Downloads/mems26_web_git && bash -lc "git pull && python3 scripts/flag_guard.py"'`
- פיקוח-מרחוק: הסוכן במכונת-הפיתוח יכול לוודא ש-flag_guard/fire_drill ירוקים במסחר.
- ‏Sierra UI מרחוק: Finder → ⌘K → `vnc://<mac2>.local` (Screen Sharing) ל-Remote Build.

**אבטחה:** מפתח-SSH בלבד (בלי סיסמאות בקבצים); שתי המכונות באותה רשת ביתית;
לא חושפים את הפורט החוצה.
