# CC Prompt — השלמת ה-NOT-DONE ללילה: RUNNER_TARGETS_V1 + מכשירי-EOD (2026-06-12)

**Contract:** `CC_HANDOFF_CONTRACT.md` — Rule 5, אנטי-טאוטולוגי + RED-on-revert מוכח, NOT-DONE.
**מצב נוכחי (Cowork, 01:35):** commit `e6d214e` [ANCHOR-TRIAL] + tags `pre-anchor-trial-2026-06-12`/`anchor-trial-2026-06-12` בוצעו · backend הופעל-מחדש דרך ה-LaunchAgent
(`com.mems26.backend`, PID 53821, ה-plist עושה `source .env` → PATTERN_RISK_CAPS=1 +
S2_DETECTION_LOG=1 טעונים) · health 200 · 14/14 טסטים ירוקים (RED-on-revert אומת ע"י Cowork).
**הוראת Michael: שהכול יהיה מוכן למחר.** נשארו 4 פריטים מה-NOT-DONE שלך:

## T1 — `RUNNER_TARGETS_V1` (T2/T3 לראנר) — לממש הלילה, flag default-OFF

לפי העיצוב שכבר כתבת (`FIX_2026-06-12_REPORT.md` §2.3) + פלייבוק חלק ו':
1. בעת fire: חישוב T2 = הקרוב-מבין R-multiple (2.0 CONT / 1.5 REV מהכניסה) ↔ רמה
   מבנית לפי סוג-יום (`compute_targets_for_day_type` / קצה-IB / POC) — מקור-אמת בלבד,
   None אם אין (Rule 1). T3 = trail: 2-bar ביום Trend בלבד (chandelier נדחה — משתנה אחד).
2. ניטור: BarLevelDetector קיים מזהה T1 — הרחב ל-T2/T3 (cross-channel dedup קיים);
   mgmt-log `T2_HIT`/`T3_HIT` (אירועים קיימים בסכמה). אחרי T2: סטופ ל-BE+0.5R.
3. UI: `t2`/`t3` כבר בסכמת ה-API — ודא שהם מאוכלסים ושהעמוד מציג.
4. רגרסיות אנטי-טאוטולוגיות: (א) flag=ON + סטאפ-CONT ביום Variation ⇒ t2=min(2R, רמה)
   ולא None; (ב) flag=OFF ⇒ t2=None בדיוק כהיום (אנטי-רגרסיה!); (ג) T2_HIT נרשם כשמחיר
   חוצה; (ד) RED-on-revert מוכח-ומודבק.
5. **לא להדליק ב-.env** — Michael מחליט בבוקר אם יום-התצפית כולל גם את זה או רק תקרות.
   להכין שורה מוכנה: `RUNNER_TARGETS_V1=1`.

## T2 — `scripts/eod_anchor_trial_report.py`

בדוק קודם מה קיים (`eod_shadow_audit.py` #16 / PATTERN_EOD) — להרחיב, לא לשכפל. פלט
לסוף-יום: כל עסקה/דחייה × עוגן, סיכון, האם RISK_CAP_SKIP/SIZE_DOWN, קאונטרפקטואל
"בלי תקרה", פגיעות T1/T2/T3, היסטוגרמת תנאי-S2 מ-`[S2-DL]`. דוח MD ל-`docs/reports/`.

## T3 — `TRADE_CVD_SNAPSHOT` (קל) + `S4_DETECTION_LOG` (קל)

CVD ב-entry/T1/exit מ-`read_cumulative_delta()` ל-quality/metadata (None אם חסר);
S4: שורת-לוג פר-בר של התבניות הפעילות+תנאים עיקריים. שניהם log-only, default-OFF,
מותר ON ב-.env (observability).

## T4 — סגירה

קומיט נוסף על אותו branch (לא לגעת ב-tags — הם נקודת-הביטול), עדכון לוחות, דוח
`docs/reports/NIGHT_COMPLETE_2026-06-12.md` עם פלטים גולמיים. Cowork יאמת לפני הפתיחה.

## מחוץ לתחום
STOP_AFTER_T1_STRUCTURAL (שער Michael) · COUNTER_PATTERN_VETO (שער Michael) · כיול
b2_vsa/b1_expansion (אחרי דאטה מה-DL) · Standing Decisions OFF · §7a.
