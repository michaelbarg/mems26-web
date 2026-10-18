# CC_ORDER 2026-10-18 — T-588 · פריטי-הפתיחה: למה הגייטוויי החי רואה סוג-פתיחה ותווית-יום שהריפליי לא רואה

**בעלים:** Cursor (או fix-agent בלילה). **קריאה-בלבד על הלייב; קוד רק flag-off + בדיקות; אין נגיעה ב-.env/עץ/LaunchAgents.**
**מקור:** cowork, ביקורת-המערכת 18.10 (`docs/plans/WORK_PLAN_2026-10-18.md`, `harness_out/t586/PARITY_NOTES.md`).

## הראיה (06.10, לוג `/tmp/backend.err.log`, ריפליי `harness_out/t466/t567ref_2026-10-06.json`)
```
16:30:05 [Gateway] TREE_V3 FAMIR LONG 7863.5 → SKIP [hour=*(16)/opening_type=OPEN_AUCTION_IN/phase=A/day_type=*(Trend_Normal)]
16:30:06 [DayType] FIX-9 RTH-boundary reset: dropping carried pre-RTH state (day_type=UNKNOWN, bars=66)
16:40:07 [Gateway] TREE_V3 CEILING_FLIP_TOUCH2 LONG → SKIP [.../opening_type=OPEN_AUCTION_IN/phase=A/day_type=*(Variation)]
16:50:03 [Gateway] TREE_V3 OPENING_DRIVE LONG 7871.5 → SKIP [.../opening_type=OPEN_AUCTION_IN/phase=B/day_type=*(Variation)/kind=*(WITH_DRIVE)/edge=*(none)]
17:00:06 [DayType] Classification changed: UNKNOWN -> Trend_Normal (conf=0.35)
```
הריפליי באותן שניות: 16:40 `opening_type=UNKNOWN/phase=A/day_type=FORMING` (stand_down — זהה) · **16:50 `opening_type=OPEN_REJECTION_REVERSE/phase=B/day_type=FORMING/rel_bias=with` ⇒ TAKE, +95.60$** (גם עם `--restart-at 15:40`).
כלומר בלייב: (א) ב-16:30:05 `Trend_Normal` = התווית הסופית של **05.10** — תוצאת-הסיווג של אתמול עדיין ב-`app.state.last_cls_result` ונקראת ע״י הגייטוויי (`_resolve_live_cls()`, trading_gateway.py:210; `_dp_ot` 1137–1160) **בלי לבדוק `session_date`**; (ב) 16:40–17:05 `Variation` בגייטוויי בעוד המכונה עצמה UNKNOWN עד 17:00 — שני מקורות-תווית שונים באותו תהליך; (ג) `OPEN_AUCTION_IN` כל הבוקר — אין נעילת-T-314 ב-06.10 (ב-08/09.10 יש: `locked opening=OPEN_REJECTION_REVERSE at bar 4`), ולכן `_dp_ot` נפל למקור 1 = `last_cls_result.opening_type` הישן. ב-08/09.10 (ריסטארט לפני הפתיחה, `bars=1`) הלייב הראה `ot=UNKNOWN` ב-16:3x — נכון.

## המשימה
1. **לאשר או להפריך** בפר-פוש: להריץ `scripts/fwd_harness.py --session 2026-10-06` עם לוג INFO של `s1_on_bar` (`_cls_result` opening_type/day_type/session_date בכל פוש 16:30–17:05) ולהשוות לשורות הלייב `[Gateway] TREE_V3 …` של 06.10. לכתוב טבלה: פוש · ot-לייב · ot-ריפליי · day_type-לייב · day_type-ריפליי · המקור בקוד.
2. **שורש אחד, תיקון אחד, flag-off:** אם `last_cls_result` ישן (session_date ≠ היום-ET) — הגייטוויי חייב להתייחס אליו כ-None (UNKNOWN/FORMING), כמו שהמפרסם ל-`v9_day_type_state` כבר עושה (N1 RC#4). דגל מוצע `CLS_RESULT_SESSION_GUARD_V1` (ברירת-מחדל OFF = byte-identical), + בדיקת-רגרסיה: תוצאה עם session_date של אתמול ⇒ `_dp_ot=UNKNOWN`, `_dp_dt` לפי המכונה בלבד.
3. **מקור-תווית אחד לעץ:** לתעד מאיפה `day_type=Variation` ב-16:40 (`get_live_day_type()` ⇒ `day_type_machine.day_type` שקודם ע״י S1-NEW-CLS/יציבות? או `_dp_hyst`?) ולמה הריפליי נותן FORMING באותו רגע. אם זו תווית-PROVISIONAL (T-47/F6) שהעץ מפרש כמוחלטת — להציע תיקון flag-off (העץ רואה FORMING עד נעילת-IB או עד conf ≥ סף פסוק).
4. **S2 Auth-Table (T-315) מול העץ:** 08.10 17:15 `INITIATIVE_LONG killed by Auth Table` (תווית S2 = Normal) בעוד הריפליי TAKE (+32.50$). לספור על 70 הסשנים כמה מועמדי-TAKE-של-העץ נהרגים ב-Auth-Table לפני שהעץ רואה אותם (`_s2_det_dt` מול תווית-העץ), ולהציע: שכבה אחת (העץ) — flag-off.
5. **דיווח:** `docs/reports/OPEN_PARITY_2026-10-18.md` — הוכחה = פקודה + stdout; TASK_LOG T-588; אפס שינוי-לייב.

## למה זה חשוב
עסקאות-הפתיחה (16:45–17:00) הן 54 מ-205 בריפליי (+546$) והמשקל הגדול ביותר בתנודתיות; 06.10 לבד = +95.60$ שהלייב לא לקח בגלל מצב-ישן. בלי פריטי-פתיחה, הדמו לא יכול לאמת את הריפליי.
