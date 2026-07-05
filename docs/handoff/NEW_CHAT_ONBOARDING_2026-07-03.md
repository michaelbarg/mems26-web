# MEMS26 — Onboarding לצ'אט הבא (2026-07-03 EOD)

_קרא אותי ראשון. אחריי: `CLAUDE.md` · `SYSTEM_INDEX.md` · `docs/SOURCE_OF_TRUTH.md` · `docs/plans/STATUS_BOARD.md` · `docs/plans/MICHAEL_ISSUES_LEDGER.md`. כלל-על: index-first, verify-don't-trust (Rule 2), paste-raw-output (Rule 5), snapshot לפני שינוי מחוץ-ל-git, שום שינוי trading-risk בלי אישור-Michael._

---

## 1 · מי אתה ואיך עובדים
Cowork מתזמר+מאמת מול הרפו והמערכת-החיה; **CC** (Claude Code על המאק) מחזיק את כל המצב הרץ ובונה. Michael דובר-עברית, פוסק על trading-risk. עובדים משימה-משימה, ראיות-לפני-טענות.

## 2 · מצב חי כרגע (אומת 07-03 ~14:2x IL)
- **בקאנד מנוהל תחת launchd** (`com.mems26.backend`, KeepAlive-on-failure). **ריסטארט = `launchctl kickstart -k gui/$UID/com.mems26.backend`**, לא nohup ידני. (זה כנראה שורש "הריסטארטים-הלא-יזומים" — kill→respawn.)
- מאזין-יחיד :8000 + :3000, health ok, DEMO enabled, 0 עסקאות פתוחות.
- **דגלים חיים מרכזיים:** `DAYTYPE_PLAYBOOK=1` · `DAYTYPE_POSITION_GATE=0` · `DAYTYPE_TARGETS_STRUCTURAL=1` · `FIXED_CONTRACTS_3=1` · `S1_NEW_CLASSIFIER=1` · `RR_ENTRY_GATE_V1=1` (**הודלק היום**) · `HFE_DISABLED=1` · `S3_MUTE=1`. מקור-אמת: `docs/FLAG_INDEX.md` (89 דגלים, `--check` PASS).
- **חי בקוד מהיום ואתמול:** resolver-מתוקן (רצפת-C1 0.5×ATR · גריד · מונוטוני · אל-חציית-כניסה) · counter-REACTIVE-SKIP ב-Variation · I-57..I-61 (slot-selfheal/fill-routing/sanitize/dedup-after-gates/target-side-guard) · צינון כבוי (סטנדינג) · לוג נקי מספאם-unknown-stream.

## 3 · פסיקות-Michael מהיום (07-03)
1. **היום = חצי-יום-חג** (4.7 בשבת): NYSE סגורה, חוזי-מדדים נעצרים **12:00 CT = 20:00 IL**, חידוש ראשון-ערב. מסחר היום = **DEMO-מלא בלי-הגבלה**; הגנת-EOD בקוד מכוילת 15:00 CT ⇒ **לא** תגן היום → **flatten ידני עד ~19:30 IL** (תוזמנה התרעה 19:15).
2. `RR_ENTRY_GATE_V1=1` — **הודלק חי** (snapshot `20260703T112315Z_rr-gate-on-michael`).
3. פריט-10 `OPENING_WINDOW_FIRE_V1` — **בנוי, כבוי**; מאושר להדלקה **ידנית** ליום-שני 07-06 (Michael דחה הדלקה-אוטומטית). פקודה ב-§5.
4. פריט-19 מספרים **אושרו:** halt ‎−$450 · מעבר-LIVE אחרי 5 ימי-DEMO ≥+2R מצטבר + 0 תקלות-מכניות → ל-CC לבנייה (RISK_* עדיין NOT-IN-CODE).

## 4 · שאלת-הניוד (חדשה היום) — **נבנתה**
Michael: "אפליקציה שמתקינה-לבד ומתחברת לסיארה על מאק-אחר + עדכון-מכאן."
- מסמך: `docs/plans/PORTABILITY_INSTALLABLE_APP_2026-07-03.md`. חבילה: `install/` (מתקין + תבניות + צ'קליסט-סיארה + update/uninstall). קומיט `30f43b2`.
- **אומת:** all-Postgres (SQLite=ברירות-מחדל-מתות); `bash -n` נקי; dry-run תקין; plists מתרנדרים+plutil-OK על נתיב-משתמש-זר. **לא-הורץ** על המכונה החיה.
- החצי-של-סיארה נשאר ידני-מודרך (צד-שלישי מורשה). עדכון-מכאן = GitHub → `install/mems26_update.sh` (ידני-מגודר לפני-LIVE; auto-deploy אחרי-LIVE).
- **שיפורי-קוד לניוד-מלא (לא-חוסם, ל-CC):** נתיבים→`os.path.expanduser("~/...")`; `db/session.py` fail-loud אם `DATABASE_URL` חסר (סוגר מלכודת-נפילה-שקטה-ל-SQLite).

## 5 · פקודות מוכנות
```bash
# הדלקת פריט-10 ליום שני (כשתחליט):
cd /Users/michael/Downloads/mems26_web_git && ./scripts/mems26_snapshot.sh "enable-item10" \
 && printf '\nOPENING_WINDOW_FIRE_V1=1\n' >> .env \
 && launchctl kickstart -k gui/$(id -u)/com.mems26.backend
# אימות דגל חי: grep env_loader /tmp/backend.err.log | tail -1   (מצפים "applied 52 vars")

# הדלקת EOD-window (אם תרצה): אותו דבר עם EOD_RISK_WINDOW_V1=1
```

## 6 · פתוח לערב-מחר / CC (מהפנקס — `MICHAEL_ISSUES_LEDGER.md` §מצב-בוקר)
יתרת-חבילת-הכלכלה: **פריט-4 STOP_RESOLVER (ה-lever מס' 1 — עלות ≈−5..7R אתמול)** · 5 b4-vol · 6 entry-confirm · 9 DBDT-alias · 11 sizing-consolidation+notify · 12 TT_SPEC_V2 · 13 P/b-filter · 16 vol-regime · 17 decision-journal · 18 doctrine-מלא · 19 build-מספרים · 20 Sierra-reconcile · 22 target-zones. + טסט-Mechanism-C התנהגותי · 21 טסטים-ישנים · עמודות-ts-TEXT · שורש-ריסטארטים (LaunchAgent respawn = חשוד-מרכזי).

## 7 · תזכורות-קבלה
- ראיה-ולא-טענה: כל "תוקן/עובד" → הדבק פקודה+פלט-גולמי.
- אל תדליק דגל trading-risk בלי אישור-Michael מפורש; החלטות-סטנדינג נשארות כבויות.
- אחרי כל משימה: עדכן `STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html` + הפנקס (finding+fix+verification).
