# סבב-בדיקה לפני-פתיחה — 11.09.2026

**מטרה:** לוודא שהשער בשעה 15:45 (ריסטארט מתוזמן, פתיחת-שוק 16:30 IL) יהיה GREEN.
**סוכן:** cowork-dev (סבב-אימות, read-only-על-קוד). **HEAD בתחילת הסבב:** `0c62af06` (13:25).
כל פקודה רצה על ה-Mac דרך `mcp__Desktop_Commander__start_process`/`interact_with_process`.

---

## מסקנה: 🟢 GO ל-15:45

`fire_drill.py` (המנגנון שאוכף את השער, לפי `CLAUDE.md`) רץ על HEAD הנוכחי והחזיר
**`🟢 GO — כל שרשרת ההחלטה כשרה לירי.`** — ראו סעיף 2. כל ארבעת השומרים שנבדקו
בנפרד (flag_guard / task_log_guard / wire_guard / guard_tests.sh) ירוקים. הדגל
החדש היחיד שנכנס היום (T-317) כבוי כברירת-מחדל ואינו ב-`.env`. הממצא האדום היחיד
(`config_consumer_guard.py`) **אינו** חלק משרשרת `fire_drill` ואינו חוסם — ראו סעיף 2.1.

---

## 1. Git — משיכה + מצב

```
$ git pull --rebase --autostash
Current branch stabilize/mems26-local-truth-2026-05-16 is up to date.

$ git log -1 --format='%h %ad %s' --date=format:'%H:%M'
0c62af06 13:25 docs: T-308 + T-310 LIVE_CHANNEL log entries

$ git status --short
?? docs/reports/postmortem/PM_1400.md ... (46 קבצי postmortem לא-מעקבים, קיימים מראש)
?? harness_out/
```
אין שינויים לא-מקומטים ב-HEAD בתחילת הסבב; קבצי ה-postmortem וה-`harness_out/`
הם תוצרים לא-מעקבים שקדמו לסבב הזה ולא נגעתי בהם.

## 2. שומרים (Guards) — rc לכל אחד

```
$ python3 scripts/flag_guard.py; echo rc=$?
...
FLAG-GUARD: PASS — all 252 ruled flags match.
  ── LIVENESS REPORT: all ON flags have ≥1 production read-site ──
rc=0

$ python3 scripts/task_log_guard.py; echo rc=$?
task_log_guard — 317 items, last committed 0.0 days ago
✅ the task log is current, structured, and the only one
rc=0

$ python3 scripts/wire_guard.py; echo rc=$?
wire_guard — 56 call sites bound against 11 guarded signatures
✅ every guarded call site can actually be called
rc=0

$ bash scripts/guard_tests.sh   (רץ ברקע, נבדק עם wait על ה-PID האמיתי — לא הורץ פעמיים)
...
160 passed, 42 warnings in 7.47s
✅ GUARDS GREEN — sizing, entry_stop, VA sanity, entry location, slot, patterns
$ wait 20447; echo rc=$?
rc=0
$ grep -c "FAILED\|ERROR" /tmp/gt.log
0
```

### 2.1 ממצא אדום — `config_consumer_guard.py` (לא בשרשרת השער)

```
$ python3 scripts/config_consumer_guard.py; echo rc=$?
🔴 CONFIG_CONSUMER_GUARD: 13 fields with NO consumer:
  daytype_playbook.yaml: fade_edges, ref_points, stop_be_early
  stop_anchors.yaml: applies_over_risk_points, atr_cap_role, be_after_t1,
    be_move_points, enabled_flag, first_spike_only, giant_candle,
    short_time_stop, structural_stop_always_wins, target_mode
  Total fields checked: 127
rc=1
```
**זה נמצא, אך אינו נכנס לחישוב ה-GO/NO-GO**: `fire_drill.py` (שלבים A/B/C/Y/G/D — ראו
סעיף 3) **אינו קורא** ל-`config_consumer_guard.py` בכלל — אין לו הזכרה בפלט השלם של
fire_drill (34 שורות, ראו סעיף 3). זהו שדה-config יתום (13/127), לא אכיפת-שער. מדווח
לשקיפות, לא כחוסם. לא תיקנתי — מחוץ לתחום הסבב (read-only-על-קוד).

## 3. `fire_drill.py` — הרצה מלאה (34 שורות, אפס סמנים-אדומים)

```
$ python3 scripts/fire_drill.py   (רץ ברקע עקב חסימת-timeout על הרצה בקדמה; פלט מלא נקרא מהקובץ)
$ wc -l /tmp/fd.log
34
$ grep -nE '🔴|✗|FAIL|NO-GO|Traceback|Error' /tmp/fd.log
(אין תוצאות — rc=1 של grep, כלומר אפס התאמות)

🔫 FIRE DRILL — ירי-יבש של שרשרת ההחלטה
— שלב A · דגלים שנפסקו — ✓ flag_guard
— שלב B · שרשרת הסטופ (הבאג של 07-08) — ✓ 4/4 (LONG/SHORT × עוגן-צמוד/מבני)
— שלב C · חוזים + בר-אישור — ✓ effective_contracts == 5 · ✓ בר-אישור
— שלב Y · RULED_FLAGS YAML תקין — ✓ 252 ruled flags
— שלב G · שומרי-התנהגות — ✓ guard_tests (160 passed) · ✓ wire_guard · ✓ task_log_guard
— שלב D · מצב חי — ✓ backend health · ✓ T-61 INFO-לוג · ✓ feed טרי (82ms)
  · ✓ live_slot פנוי · ✓ live_enabled==[2,4] · ✓ day_type קיים (UNKNOWN conf=0.0 — צפוי טרם-פתיחה)

🟢 GO — כל שרשרת ההחלטה כשרה לירי.
```
לא הצלחתי לתפוס rc מספרי ישיר של fire_drill.py (מעטפת ה-shell שהריצה אותו קרסה על
timeout-לקוח לפני שהספקתי `wait`) — אך פלט מלא + אפס סמן-כישלון + השורה המסכמת
"🟢 GO" הם ראיה ישירה וחד-משמעית לתוצאה, לא הסקה.

## 4. עקביות תיעוד — TASK_LOG.md מול STATUS_BOARD.md (T-311…T-319)

**ממצא מרכזי: ההנחיה שקיבלתי הניחה שארבעה פריטים (T-311/313/314/315) מסומנים ✅
וזקוקים לשורת-לוח. בפועל, בקריאה ישירה מה-HEAD הנוכחי, רק שניים מהם ✅ — ושניהם
כבר עם שורת-לוח. לא הוספתי כלום, כדי לא לכתוב "אומת/סגור" על פריט שהקובץ עצמו
מכריז שהוא פתוח.**

| T# | סטטוס בפועל (עמודה 3, TASK_LOG.md) | שורת-STATUS_BOARD קיימת? |
|---|---|---|
| T-311 | ✅ סגור (11.09) | **כן** — `[2026-09-11 10:12] cowork-dev` + פירוט ב-שורה 55 |
| T-313 | ✅ סגור (11.09) | **כן** — אותה שורה 10:12 + פירוט ב-שורה 74 |
| T-314 | 🔴 פתוח (נפתח-מחדש) | **כן** — `[2026-09-11 11:52] cowork-dev`, מסביר בפירוש למה **לא** ✅ (חסר קובץ-מבחן) |
| T-315 | 🟠 פתוח (נפתח-מחדש — חלקי) | **כן** — אותה שורה 11:52, אותה סיבה |
| T-316 | 🟠 פתוח | אין (לא ✅ — לא נדרש) |
| T-319a | 🔴 פתוח | אין (לא ✅ — לא נדרש) |
| T-317 / T-318 / T-319 / T-319b | **אין שורה כזו בכלל ב-TASK_LOG.md** | אין |

ראיה גולמית (grep על TASK_LOG.md, השדה השלישי בכל שורה = סטטוס):
```
T-315: STATUS = 🟠 פתוח (נפתח-מחדש — חלקי)   WHO = cc-macbook
T-314: STATUS = 🔴 פתוח (נפתח-מחדש)           WHO = cc-macbook
T-313: STATUS = ✅ סגור (11.09)               WHO = cc-macbook
T-311: STATUS = ✅ סגור (11.09)               WHO = cc-macbook
T-316: STATUS = 🟠 פתוח (מאומת בטקסט המלא)     WHO = cc-macbook (חיווט) → cowork (מדידה חוזרת)
T-319a: STATUS = 🔴 פתוח                       WHO = cc-macbook (תיקון) → מייקל (פסיקה)
```
```
$ for t in T-311 T-313 T-314 T-315 T-316 T-317 T-319 T-319a T-319b; do
    grep -c "$t" docs/plans/STATUS_BOARD.md; done
T-311: יש (10:12, +פירוט 55)   T-313: יש (10:12, +פירוט 74)
T-314: יש (11:52)               T-315: יש (11:52)
T-316/T-317/T-319/T-319a/T-319b: 0 שורות — אף אחד מהם לא מוזכר ב-STATUS_BOARD, ובוודאי לא כ-✅.
```
**T-314/T-315 אינן סתם "פתוחות ולא-מדווחות" — שורת ה-11:52 עצמה מסבירה את הפער בין
הגולדן-שאומת (מצדיק את החלטת-ה-HEAD לריסטארט) לבין הסגירה הפורמלית (חסרה קובץ-מבחן
רגרסיה, לפי משמעת-הרגרסיה של CLAUDE.md). זו בדיוק ההבחנה בין "תנאי-התפעולי-לשער
מתקיים" לבין "הפריט סגור" — ושתיהן נכונות בו-זמנית.**

לכן: **לא הוספתי שורות STATUS_BOARD חדשות, ולא שיניתי סמלי-סטטוס** — כל המצב כבר
עקבי ומתועד נכון על HEAD `0c62af06`. הרצתי `task_log_guard.py` שוב ליתר ביטחון:
```
$ python3 scripts/task_log_guard.py; echo rc=$?
✅ the task log is current, structured, and the only one
rc=0
```

## 5. תחום-ההתנהגות של קומיטי-היום + הדגל החדש

```
$ git show --stat 0c62af06   → docs בלבד (LIVE_CHANNEL.md, 10 שורות)
$ git show --stat f867bb5c   → backend/.../sierra_position_reconciler.py (T-308a+b: קבוע דולר 12.50→5.0 + ניסוח)
$ git show --stat 6baed7c8   → backend/v9/services/entry_guard.py, 30 שורות (T-310: ניסוח stray-vs-foreign)
$ git show --stat 0c6fb74f   → bar_level_detector.py +101, config/RULED_FLAGS.yaml +1,
                                 scripts/t317_pre_t1_realize_replay.py +339 (T-317)
```

**דגל חדש יחיד שנכנס היום:** `STRUCTURE_EXIT_REALIZE_PRE_T1_V1` (קומיט `0c6fb74f`, 13:19, T-317).
```
$ git show 0c6fb74f | grep -nE "getenv\(|environ"
38:  _pre_t1_on = _se_os.getenv("STRUCTURE_EXIT_REALIZE_PRE_T1_V1", "0").lower() in ("1","true","live")
```
ברירת-המחדל בקוד היא `"0"` (כבוי) — פעיל רק אם משתנה-הסביבה מוגדר ל-`1`/`true`/`live`.
```
$ grep -nE "STRUCTURE_EXIT_REALIZE_PRE_T1_V1" .env; echo rc=$?
rc=1   ← אין התאמה, הדגל לא קיים ב-.env בכלל
$ stat -f "%Sm" .env
Sep 10 11:27:41 2026   ← זהה לבסיס הצפוי, .env לא נגע בו איש
```
`flag_guard.py` (סעיף 2) מאשר: `✓ STRUCTURE_EXIT_REALIZE_PRE_T1_V1: expected=unset_or_0 actual=unset`.
⇒ **הענף של T-317 אינרטי**, לא משנה התנהגות-חיה. שני הקומיטים האחרים (f867bb5c,
6baed7c8) בדקתי גם אותם ל-getenv/environ: f867bb5c מכיל שורת `getenv("ORPHAN_MAX_LOSS_USD"...)`
אך זו שורת-הקשר קיימת-מראש (לא `+` בדיף) — השינוי בפועל הוא קבוע מוקשח
`_MES_DOLLAR_PER_POINT = 12.50 → 5.0` (תיקון-דיוק ללוגים CRITICAL/ORPHAN, לא לגודל-פוזיציה
או ניתוב-הזמנות). 6baed7c8: אפס תוצאות ל-getenv/environ — ניסוח בלבד.

**הערה נוספת שעלתה תוך-כדי (לא נדרשה במפורש אך רלוונטית ל-GO):** קומיט `1fb91968`
(cowork 13:26) **מבטל** בפירוש קביעה קודמת שלו-עצמו (`d6331922`, 11:52) ש"HEAD לריסטארט
הוא `e706831c`" — כי מאז נחתו `0c6fb74f`/`f867bb5c`/`6baed7c8` כקוד-ייצור:
> "the 15:30 gate must re-derive HEAD and green guard_tests on it before restarting"

זה בדיוק מה שסבב זה עשה: הרצתי guards+fire_drill מחדש על ה-HEAD **הנוכחי** (`0c62af06`,
כולל T-308/T-310/T-317) ולא הסתמכתי על פסיקת-HEAD ישנה — והתוצאה GO (סעיף 3).

## 6. מצב-חי (read-only)

```
$ KEY=$(grep -E '^MOBILE_ACCESS_KEY=' .env | cut -d= -f2)
$ curl -s "localhost:8000/api/v9/mobile/data?key=$KEY" | python3 -c "..."
pos 0  is_sim 0  armed 1  sendorders 1  avail 3649.69

$ curl -s localhost:8000/api/v9/gateway/status | python3 -c "..."
{'live_slot': None, 'demo_slot': None, 'live_enabled_systems': [2, 4]}

$ pgrep -f 'backend.main|uvicorn' | head -1 | xargs -I{} ps -o lstart= -p {}
Fri Sep 11 09:21:46 2026
```
**לתשומת-לב:** הבקאנד-הרץ עלה ב-09:21:46 — **מקדים** את כל קומיטי-היום (13:19-13:25:49,
כולל T-317/T-308/T-310). זה תקין וצפוי לנוכח הריסטארט המתוזמן ל-15:45 (המנגנון שמטרתו
בדיוק לטעון את הקוד העדכני לפני הפתיחה ב-16:30) — לא סימן-אזהרה, אך מציין שהבדיקות
ב-שלב D של fire_drill (health/feed/slot) בדקו את התהליך **הישן**, כצפוי בבדיקת-טרום-ריסטארט.

## 7. מה נערך בקבצים

| קובץ | פעולה | שורה אחת |
|---|---|---|
| `docs/plans/TASK_LOG.md` | **לא נערך** | כל הסטטוסים כבר נכונים ועקביים (סעיף 4) |
| `docs/plans/STATUS_BOARD.md` | **לא נערך** | T-311/313/314/315 כבר עם שורות-לוח; T-316/317/319* לא ✅ בשום מקום |
| `docs/plans/ROADMAP_TO_LIVE.html` | **נערך** | "עודכן" רוענן ל-11.09 13:50 עם הסטטוס האמיתי (2✅+2🟠+1🆕, לא "4 מאומתים"); "אתה כאן" רוענן עם נתוני-חי אמיתיים (סעיף 6), הגרסה הישנה (04.09) נשמרה כ-"היסטוריה" — לא נמחקה |
| `docs/reports/PREOPEN_SWEEP_2026-09-11.md` | **נוצר** | הדוח הזה |

```
$ git diff --stat docs/plans/ROADMAP_TO_LIVE.html
 docs/plans/ROADMAP_TO_LIVE.html | 4 ++--
 1 file changed, 2 insertions(+), 2 deletions(-)
```

## 8. סיכום GO/NO-GO

| בדיקה | תוצאה |
|---|---|
| `flag_guard.py` | rc=0, PASS 252/252 |
| `task_log_guard.py` | rc=0, PASS (317 items), גם לפני וגם אחרי (לא נערך) |
| `wire_guard.py` | rc=0, PASS 56/11 |
| `guard_tests.sh` | rc=0, 160 passed, 0 failed |
| `fire_drill.py` | פלט מלא = 🟢 GO, אפס סמני-כישלון (rc מספרי לא נתפס — ראו סעיף 3) |
| `config_consumer_guard.py` | rc=1 — **אדום אך לא בשרשרת השער**, 13/127 שדות-config יתומים |
| דגל חדש היום | `STRUCTURE_EXIT_REALIZE_PRE_T1_V1` — כבוי, לא ב-`.env`, אינרטי |
| `.env` mtime | `Sep 10 11:27:41 2026` — ללא שינוי |
| מצב-חי | pos=0 · is_sim=0 · armed=1 · sendorders=1 · slots פנויים · live_enabled=[2,4] |

**מסקנה: 🟢 GO לריסטארט 15:45**, בכפוף לכך שאיש לא ישנה קוד/`.env`/דגלים בין רגע
כתיבת הדוח (13:5x) לריסטארט עצמו. הפריט האדום היחיד (`config_consumer_guard`) אינו
חלק ממנגנון-השער ואינו עילה ל-NO-GO — מדווח לשקיפות בלבד.
