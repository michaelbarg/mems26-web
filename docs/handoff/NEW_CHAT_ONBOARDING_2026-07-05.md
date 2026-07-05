# MEMS26 — הנדאוף לצ'אט הבא (2026-07-05, ~21:50 IL / Cowork)

מסמך עצמאי. קרא אותו + `CLAUDE.md` + `docs/plans/MICHAEL_ISSUES_LEDGER.md` +
`docs/plans/GAP_ANALYSIS_2026-07-05.md`. כלל-על: **אינדקס-קודם, לאמת-לא-לסמוך
(Rule 2), לצטט-פלט-גולמי (Rule 5), שינוי-סיכון = עצירה + אישור-מיכאל.**

---

## 0 · איפה אנחנו עכשיו (מצב חי, אומת)

- **תאריך:** 2026-07-05 ראשון-ערב. שוק-החוזים נפתח מחדש ~01:00 IL (17:00 CT ראשון)
  ל-trade-date של יום שני 07-06. יום שישי 07-03 היה חצי-יום-חג (נעצר 12:00 CT).
- **שירותים:** בקאנד :8000 ✓ רץ מנוהל תחת LaunchAgent (`com.mems26.backend`).
  **פרונטאנד :3000 ✗ כבוי** — להעלות לפני המסחר (`npm run dev` בתיקיית frontend,
  או דרך `scripts/start_all.sh`; ר' §שירותים ב-CLAUDE.md — לא להריץ באודיט).
- **DB:** local Postgres `postgresql://localhost/mems26`
  (psql: `/Applications/Postgres.app/Contents/Versions/18/bin/psql`).
- **עסקאות פתוחות:** 0. **feed אחרון:** 2026-07-03 19:55 IL (טרם-פתיחה, תקין).
- **HEAD:** `d2bb80f` (רענון-אינדקס). הכל דחוף ל-origin עד `bb157f2`; ודא push.

---

## 1 · ✅ חי במסחר (דגלים ON ב-.env)

`FIXED_CONTRACTS_3=1` (3 חוזים כל ירי) · `DAYTYPE_TARGETS_STRUCTURAL=1`
(רזולבר-מתוקן item-2: רצפת-T1 0.5×ATR · גריד · מונוטוניות · אל-חציית-כניסה) ·
`DAYTYPE_PLAYBOOK=1` (item-1: counter-REACTIVE ב-Variation = SKIP) ·
`RR_ENTRY_GATE_V1=1` (item-3 "לא מממנים סטופים" — הודלק 07-03 באישורך) ·
`OPENING_FIRE_CVD_V1` (I-53 תוקן) · RUNNER_TRAIL_V1 · תיקוני I-57..I-62.

## 2 · 🟡 בנוי + מחווט, דגל-OFF — מוכן להדלקה (פסיקתך)

| פריט | דגל | מה זה עושה |
|---|---|---|
| 10 | `OPENING_WINDOW_FIRE_V1` | ירי-חלון-פתיחה (override חיובי בחצי-שעה); **משימה מתזמנת מדליקה יום-שני** (`enable-item10-opening-window-monday`) |
| 4 | `STOP_RESOLVER_V1` | **מחווט 02a2bf5** — סטופ מבני מרצועת-ATR (מדרגות בר-אמיתי) בנקודת-החנק בגייטוויי. ה-lever מס' 1 |
| 22 | `TARGET_ZONES_V1` | **מחווט 7897ebd** — מזקק t2/t3 למדפי-קונפלואנס |
| 6 | `S4_ENTRY_CONFIRM_V1` | **מחווט 7897ebd** — בר-אישור בכיוון לפני ירי-S4 |
| 21 | `EOD_RISK_WINDOW_V1` | אין כניסות 45 דק' לפני סגירה (מכויל 15:00 CT) |
| 18 | `DAY_DIRECTION_DOCTRINE_V1` | דוקטרינת-יום-כיווני + halt-proof |
| 19 | `RISK_HALT_V1` | עצירת-יום; המספר `RISK_DAILY_LOSS_CAP=450` כבר ב-.env (אישרת) אבל **הגייט OFF** עד חלון-ולידציה |
| 5 | `S2_B4_VOL_V1` | בדיקת-ווליום b4 |
| 9 | (playbook) | תיקון-alias DBDT |
| — | System 6 | supervisor + exit-signals + journal; endpoint `/api/v9/system6/diagnose` חי (אבחון-בלבד) |

## 3 · ❌ לא-נבנה (חוב — רובו CC)

- **item-11** איחוד-sizing — `calculate_size` הישן עוד ב-5 קבצים (שתי מערכות במקביל).
- **item-12** TT_SPEC_V2 — 0 קבצים; TT עוד רדוד (0 יריות אי-פעם).
- **item-13** PB_SHAPE_FILTER_V1 — 0 קבצים.
- **item-16** VOL_REGIME_V1 — 0 קבצים (חלק-החוזים מיותר כי contracts=3; אבל
  סטופים-רחבים/אישור-בכניסה ביום-אלים לא-נבנו).
- **item-17** יומן-כניסה "למה לא נכנס" — לא-נבנה (System 6 מכסה רק צד-יציאה).
- **item-7/8** phase-detector / pullback-retest — מחקר, לא-נבנה.
- **item-20** reconcile — מחווט לendpoint של System 6, **לא** ללולאה/התרעה מחזורית.

## 4 · התמונה בשורה אחת

הרבה בנוי, אבל **כמעט שום דבר שמשפר רווחיות לא חי בפועל** — item-4/22/6 בנויים-ואינרטיים,
item-10/18/19/System-6 דגל-OFF. לכן ה-DEMO של היום ≈ המערכת הישנה + תיקוני-בטיחות.
הערך אמיתי אבל **סמוי**. סגירת-הפער = לחווט-כבר-חיווט + להדליק-את-המוכח + חלון-ולידציה
נקי. **LIVE לא-מוכן** (demo net ≈ −0.67R). ר' `GAP_ANALYSIS_2026-07-05.md`.

---

## 5 · פסיקות פתוחות למיכאל

1. **להדליק את item-4 STOP_RESOLVER_V1?** (ה-lever הכי-משמעותי; שינוי-סיכון → אישורך).
2. להדליק item-22 / item-6 / item-21 / item-18? (כולם בנויים flag-OFF).
3. **S3 tick-reversal-16** — 3 שאלות פתוחות (רעיון-המסחר במשפט? מחליף footprint או
   מערכת-חדשה? עדיפות מול מסלול-LIVE?).
4. חלון-הולידציה של item-19 (מתי מתחילים לספור 5-ימי-DEMO ל-LIVE).

## 6 · תפעול (חובה)

- **ריסטארט בקאנד:** `launchctl kickstart -k gui/$UID/com.mems26.backend`
  (**לא** nohup ידני — יתנגש עם ה-LaunchAgent). ודא 0 עסקאות-פתוחות + מאזין-יחיד לפני.
- **snapshot לפני שינוי out-of-git** (.env/DLL/LaunchAgent): `scripts/mems26_snapshot.sh "label"`.
- **הדלקת-דגל** = ערוך .env → snapshot → kickstart → אמת boot-line (`[env_loader] applied`).
- **אינדקס** רוענן היום (d2bb80f); הרץ `gen_index.py` שוב אחרי שינוי-מבני (איטי על-mount,
  ~80ש' — הרץ ברקע). `gen_flag_index.py --check` = PASS (79 דגלים מתועדים).
- **משימות מתוזמנות רלוונטיות:** `enable-item10-opening-window-monday`,
  `preopen-readiness-daily` (16:05), `rth-trade-supervisor`, `mems26-eod-*`.

## 7 · לצ'אט-הבא — הצעד-הראשון המומלץ

אמת מצב (services/DB/feed/flags), ואז **קבל מ-מיכאל פסיקת הדלקה** על item-4 (+22/6):
הם הדבר-היחיד שמזיז את הרווחיות ובנויים-ומחווטים-ומחכים. אם מדליקים — snapshot,
kickstart, ואמת ב-SHADOW/DEMO על הירי-הראשון (לפני/אחרי גולמי, Rule 5).
