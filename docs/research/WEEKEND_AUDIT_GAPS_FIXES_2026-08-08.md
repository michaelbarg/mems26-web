# ביקורת-סופ"ש עמוקה — פערים + אימות-תיקונים · 2026-08-08 (שבת)

**סוכן:** weekend-audit-agent (cowork) · **קריאה-בלבד על קוד/דגלים** · כל טענה עם פקודה+פלט (Rule-5).
**סביבה בזמן-הביקורת:** backend רץ (עלה 08-08 18:38 אחרי ריסטארט-מכונה), שוק סגור, git נקי מול origin.

---

## 0. ריצות-אימות גלובליות (פלט גולמי, מקוצר)

```
$ python3 scripts/flag_guard.py
FLAG-GUARD: PASS — all 156 ruled flags match.

$ ./scripts/mems26_verify.sh
verdict: OK · 2 warn
  ⚠️ FLAG_INDEX drift → run: python3 scripts/gen_flag_index.py
  ⚠️ woodies_5min.json 69422s old (OK if market closed)   ← סופ"ש, תקין

$ env -i … /Library/Frameworks/Python.framework/Versions/3.9/bin/python3 -m pytest \
    test_command_queue test_fill_on_closed test_balance_edge_exempt test_neutral_hysteresis \
    test_balance_imbalance_toggle test_drive_exhaustion_veto test_daytype_watchdog \
    test_opening_windows test_extremes_quality test_target_approach_realize \
    test_s6_invariant10_target_reconcile test_fix633_target_clamp test_postmortem_v1 \
    test_mobile_emergency test_system7_score test_mae_scratch -q
134 passed in 3.08s

$ python3 scripts/classifier_truth_audit.py --scid ~/SierraChart/Data/MESU26_FUT_CME.scid
Balance/Directional accuracy: 13/13 = 100%   (סט-האמת: 07-15..07-31; 08-06 אומת בנפרד ע"י cc)

$ python3 scripts/gen_flag_index.py --check
UNDOCUMENTED behavior flags: BALANCE_EDGE_EXEMPT_V1, DAYTYPE_MECH_HOLD_BARS,
DAYTYPE_STALE_THRESHOLD_MIN, NEUTRAL_HYSTERESIS_PTS, NTFY_TOPIC, S6_APPROACH_DIST_PTS,
S6_MAX_APPROACH_BARS, S6_SCRATCH_STOP_GAP_PTS      ← מקור ה-warn של verify (חוב-תיעוד מהשבוע)
```

---

## 1. 🔴 הממצא המרכזי: תור-הפקודות (P0-1) שבור בפרודקשן — חוסם-מסחר לפני הסשן הבא

**הקוד נמסר + 6/6 טסטים, אבל ל-`drain_command_queue()` אין אף קורא ב-runtime:**
```
$ grep -rn "drain_command_queue" --include=*.py backend/
sierra_command.py:115: def drain_command_queue(...)     ← ההגדרה
tests/test_command_queue.py:83,96                        ← טסטים בלבד. אפס callers בפרודקשן.
```
**המכניקה:** `_write_command` כותב cmd לתור תמיד, ול-`trade_command.json` רק כשהתור ריק
(`len(pending)<=1`, fast-path). בלי drainer — הקובץ הראשון נשאר בתור לנצח ⇒ **כל פקודה
מהשנייה-והלאה לא מגיעה ל-DLL לעולם.**

**הוכחה חיה מיום שישי 08-07** (`~/SierraChart_Data/v9_export/command_queue/`):
```
cmd_000001.json  18:40  PLACE #650 (LONG ZLR, 3c)   ← בוצע דרך fast-path: ACK 18:40:13,
                                                       ENTRY ביומן-fills (parent 10050) ✓
cmd_000002.json  19:35  PLACE #652 (SHORT GHOST, contracts:0 !!)  ← לא בוצע לעולם
cmd_000003.json  22:59  CANCEL #652                                ← לא בוצע לעולם
trade_command.json  mtime 18:40 (0 bytes) · trade_result.json mtime 18:40 — אין ACK אחרי 18:40
$ grep ENTRY trade_fills_journal.jsonl | tail  → אין ENTRY ל-652. אפס fills ל-652.
```
**משמעות #652:** עסקת ה"לייב" GHOST SHORT מעולם לא הייתה קיימת בסיירה — פוזיציית-פנטום ב-DB
שהרקונסיילר סגר ב-23:00:20 כ-SIERRA_FLAT $0 (exit_price=NULL). התאום-צל #651 הפסיד ‎-$78.75
(הבאג "חסך" במקרה — אבל באותה מידה היה חוסם MODIFY_STOP הגנתי).
**באג נלווה:** cmd_000002 מכיל `"contracts": 0` (sizing=half ⇒ עיגול-לאפס) — גם עם drainer
הפקודה הייתה פסולה. שורש שני לבירור.
**מצב עכשיו:** 3 קבצים עומדים בתור ⇒ pending>1 ⇒ ה-fast-path כבוי ⇒ **ביום המסחר הבא אף
פקודת-לייב (כולל כניסות) לא תגיע לסיירה עד שמנקים את התור וגם מחווטים drainer (או משחזרים
fast-path).** אסור לחמש בלי לסגור את זה. (זה בדיוק סוג-הכשל של Rule-5: "6/6 passed" ≠ עובד.)

---

## 2. מטריצת כל פריטי 05-07.08 — DELIVERED / PARTIAL / NOT-DONE

### CC_WORKORDER_2026-08-05 (M1-M5)
| פריט | סטטוס | ראיות |
|---|---|---|
| M1 ביקורת-S6 03-04.08 | ✅ DELIVERED | `7f0949f7`; דוח `system6/S6_REVIEW_2026-08-03_04.md`; המספרים אומתו מול DB (620:−16.25 · 622:−20 · 625:−36.25 = −$72.50) |
| M2 POST_MORTEM_V1 | ✅ עם 2 חורים | `f27fd337`; 10/10 בטסטים שלי; 15 שורות v9_postmortem; PM נכתבו אוטומטית עד שישי (PM_649/650/651). **חור-1: אין PM_640** — ההפסד-הלייב הגדול של השבוע (הטריגר רק על LOSS בזמן-סגירה; ‎#640 נסגר $0 ותוקן רטרואקטיבית). **חור-2: כל קבצי PM_*.md לא-committed** |
| M3a חירום-בטלפון | ✅ DELIVERED | `05c4818c`; 7/7 בריצה שלי; relay חי היום מול Render ("cmd relay enabled…recovered") |
| M3b S7 replay | ✅ הוחלף במסלול-צל | NO-GO מסיבת-דאטה, דוח `S7_REPLAY_ACCEPTANCE_2026-08-05.md`; פסיקת-מייקל M5 = צל-3-ימים |
| M3c Stop-floor replay | ✅ הוחלף במסלול-צל | NO-GO, דוח `TREND_STOP_FLOOR_REPLAY_2026-08-04.md`; TSF_SHADOW חי |
| M3d בידוד-טסטים + חוב-78 | ⚠️ PARTIAL-נסוג | נמסר אז (912 collected/878 pass); **היום שוב 8 דגלים undocumented** (ר' §0) — החוב חזר עם קומיטי-השבוע |
| M4 פרופיל-TPO חי | ✅ (אימות-קוד) | `9fc28a71` — "אין צורך בשינוי"; קבלה-ויזואלית ב-3 זמנים עדיין פתוחה |
| M5 לוגי-צל S7+TSF | ⚠️ PARTIAL | ר' §3.3 |

### CC_WORKORDER_2026-08-06 (דלתון שלב 1-3)
| פריט | סטטוס | ראיות |
|---|---|---|
| 1a-1d Excess/Poor + realize + replay | ✅ DELIVERED+ENABLED | `cfa40f18/b20f3b58/49d3914a/532e300b`; 14/14+17/17 אצלי; replay GO ‎+$410 (`EXTREMES_AWARE_REALIZE_REPLAY.md`); ‏RULED 08-06 + ‎.env=1; ‏0 טריגרים-לייב עדיין |
| 2a-2c חלונות-פתיחה + drive | ✅ DELIVERED+ENABLED | `c3ec9a7f/c8df8a1a`; 16/16 אצלי; replay GO; ‏EXHAUSTION_VETO מחווט (gateway:835-880), ‎.env=1, ‏RULED; ‏0 הפעלות שישי (פתיחה=REJECTION_REVERSE, לא DRIVE — רדום-נכון) |
| 3 מתג Balance/Imbalance | ✅ DELIVERED | `d94bab77`; 9/9; observability; מודולציית-ירי not_built (כמוצהר) |

### CC_WORKORDER_2026-08-07 (P0-P2, P0.5, P1.5, P1.6)
| פריט | סטטוס | ראיות |
|---|---|---|
| P0-1 תור-פקודות+ACK | 🔴 **שבור-בפרודקשן** | ר' §1 — אין drainer ב-runtime; ‏#652 פנטום; 3 קבצים תקועים בתור עכשיו |
| P0-2 חשבונאות-fills | ✅ לייב, ⚠️ רטרו-חלקי | ‏#640 ‎$0→−131.25 (mgmt log `PNL_CORRECTION retroactive 07:40:52`) ✓; ‏#650 `fill_on_closed` רץ חי 18:41:55 ✓. **אבל "רטרואקטיבית 03-06.08 מול היומן" = בפועל רק #640**; אין סקריפט/artifact של סריקה מלאה |
| P0-3 לוגי-צל תוקנו | ✅ לייב | 2+2 שורות אמת מיום שישי (ר' §3.3) |
| P1-4 שחרור-קצה-BALANCE | ⚠️ PARTIAL | נבנה flag-OFF ‏`c7b7d578`, 7/7 — **ה-replay (06.08+14 ימים) לא הורץ**; אין דוח; הדגל גם undocumented ב-FLAG_REGISTRY |
| P1-5 קונסיומר-כניסה ל-EXCESS | ❌ NOT-DONE | ‏`grep EXCESS backend/v9/gateway/` = 0; אין קומיט; הרוטציה-ללא-עסקה של 06.08 עדיין בלי מענה |
| P1-6 gateway_routes:84 | ✅ DELIVERED | `6b370a01` (cast to int); לוגי-שישי אבדו ברוטציה — אין ראיית-ריצה, הקוד בפנים |
| P2-7 self-heal כותב-סוג-יום | 🔴 לא-עובד-בלייב | ר' §3.5 |
| P2-8 היסטרזיס Neutral | ✅ קוד, ⏳ לייב | `e153bcd6`; 3/3+13/13 אצלי; נטען לפני הסשן (הוכחת-ריסטארט §3.6) אבל שישי היה Variation — אין יום-Neutral מאז; ההוכחה-החיה ממתינה |
| P2-9 scratch↔stop gap | ✅ DELIVERED | `8052e0ef`; ‏`mae_scratch.py:105` ‏S6_SCRATCH_STOP_GAP_PTS=2.0 + אכיפה ב-‎:140-147; אין scratch חי מאז — טריגר-לייב ממתין |
| P2 §9 יעדים-מעוגני-מבנה | ❌ NOT-DONE | ‏0 קומיטים תואמים מאז 08-05 (`git log --since 08-05 | grep -ci "anchor|structure.*target"` = 0) |
| P0.5 תיקון-sides במסווג | ✅ DELIVERED | `510e1b3a` (relative_features.py — ≥2 ברים); הריצה שלי: **13/13=100%**; ‏08-06→Variation ✓. סטייה מוצהרת: "משקל-בטן" (סעיף-3) לא נוסף — התיקון הושג בספירת-ברים; היעד "15/15" בפועל = 13 ימי-אמת + 08-06 |
| P1.5 כרטיס-עסקה בטלפון | ⚠️ PARTIAL | `dc841d9d` נגע **רק** ב-`mobile_monitor.py` (העמוד המקומי — יש ✅/🔴 פר-רמה מול sierra_prices). **דף-Render לא עודכן** (נגיעה אחרונה 08-05) — הפקודה דרשה "בשני דפי-הפלאפון". קבלת-סים (הזזת-פקודה⇒🔴 ≤10ש') לא בוצעה |
| P1.6 ntfy לשעון | ⚠️ PARTIAL | ר' §3.7 |

---

## 3. אימות-לייב לכל תיקון שנטען השבוע

**3.1 תור-פקודות ACK** — 🔴 ר' §1.

**3.2 חשבונאות-fills** — ✅ חי. ‏DB: ‏#640 ‏pnl_usd=−131.25 ✓; ‏#650 −86.25 עם `PNL_CORRECTION
{reason: fill_on_closed}` פעמיים (18:41:55 — אידמפוטנטי, שורת-לוג כפולה = nit). ‏P&L-שבוע לייב
(DB): ‏03: +183.75 · 04: +535.00 · 05: +246.25 · 06: −63.75 · 07: −86.25 = **+$815.00**.
**⚠️ אזהרה: ה-$0 של #652 הוא "אמת-במקרה"** (הפקודה לא נשלחה) — לא הישג של ה-poller.

**3.3 לוגי-צל S7+TSF** — ✅ נכתבים חי, ⚠️ חלקיים מול הספק.
```
v9_s7_shadow_log: 2 שורות שישי — #649 ZLR LONG score=30 blocked=True (loc_pos 0.95=chase)
                                  #651 GHOST SHORT score=55 sizing=1 (location 15 + delta 10)
v9_tsf_shadow_log: 2 שורות — floor 6.0, would_apply=False בשתיהן
```
פערים מול פסיקת-M5: ‏(א) נלוגג רק על fire-שנכנס-לצל, **החלטות-נחסמות לא** ("על כל החלטת-גייטוויי");
‏(ב) ‏`gateway_decisions.jsonl` בלי שדות-s7 (‏`grep -c '"s7'` = 0); ‏(ג) ‏hook מעביר `bar_ts=None`
(‏gateway:2928) ⇒ עונשי-צהריים/ZLR-מאוחר לא מחושבים — הציון של #649 (18:40 IL, חלון-הצהריים)
היה צריך להיות 15, לא 30 (עדיין block; אבל הדאטה לדוח-3-הימים מנופחת כלפי-מעלה). ספירת-3-הימים:
שישי = יום-1 עם n=2; אפקטיבית מתחילים שני.

**3.4 sides-fix במסווג** — ✅ ‏13/13 בריצה שלי (פלט ב-§0), ‏08-06 = Variation ✓.

**3.5 self-heal לכותב-סוג-היום** — 🔴 הקוד נטען ולא ריפא. ‏DB שישי (ts-נאיבי-UTC): פערי
‎60ד' (15:00→16:00) ו-‎55ד' (18:10→19:05) בתוך RTH; ‏OPS_LOG_2026-08-07.md מלא אזהרות:
```
[15:20:04-04:00] [daytype_watchdog] [WARN] day_type_state stale: 15min (threshold 10) …
(42 אזכורי watchdog/staleness ביום אחד)
```
ה-watchdog (08-06) עובד; ה-self-heal (P2-7, reset-signature) לא מחזיק את הכותב חי. השורש
האמיתי של מות-הכותב עדיין לא מטופל. ⇒ נשאר 🔴 פתוח.

**3.6 hysteresis** — קוד-in, לייב-ממתין. הוכחה שהקוד רץ בסשן-שישי: ‏pyc-פורנזיקה —
`ntfy_notify.cpython-39.pyc` mtime **08-07 18:40** = import עצל בזמן-הירי של #650 ⇒ הבקאנד
שרץ בסשן כלל את קומיטי-‏15:53-16:07 (ריסטארט אחרי 16:07 ולפני 18:40). האוסצילציה עצמה:
‏08-06 = **16 היפוכי NE↔NC** נמדדו ב-DB; שישי היה Variation — אין מקרה-מבחן עדיין.

**3.7 ntfy** — ⚠️ ‏hooks של on_fire+on_fill מחווטים ורצו חי (הוכחת-pyc 18:40); ‏NTFY_TOPIC ב-.env ✓.
פערים מול הפקודה: ‏on_close/on_alert קיימים אך **אף-אחד לא קורא להם**; אין PAUSE/RESUME ·
חירום · סיכום-EOD · rate-limit · אימות-סיירה-בכניסה; כשל-שליחה נבלע ב-`logger.debug`
(‏ntfy_notify.py:47 — מפר "No silent failures"). מסירה-בפועל לשעון אין איך לאמת מהמכונה — לשאול
את מייקל אם קפצו התראות על #650 ב-18:40 שישי.

**3.8 invariant-10** — ✅ בקוד (`system6_supervisor.py:262`, ‏5/5 אצלי) · 0 הפעלות-לייב (לא
נוצר פער-יעדים השבוע אחרי fix-633). ‏**3.9 exhaustion-veto** — ✅ מחווט+ON · 0 הערכות שישי
(אין OPEN_DRIVE) — רדום-נכון. ‏**3.10 scratch-gap** — קוד ✓, אין scratch חי מאז התיקון.

---

## 4. פערים שקטים נוספים

1. **עבודה לא-committed:** ‏OPS_LOG_2026-08-0{4,5,6,7}.md · E2E_FIRE_PROOF_2026-08-0{5,7}.md ·
   15× PM_*.md · ‏news_calendar.yaml שונה — הכל untracked/dirty. מפר את חוזה-ה-handoff.
2. **חוב-FLAG_REGISTRY חדש:** 8 דגלים/פרמטרים מהשבוע בלי תיעוד (רשימה ב-§0) — ה-warn של
   verify יישאר עד סגירה. (RULED_FLAGS דווקא מעודכן יפה — כל 5 ההדלקות עם פסיקה+תאריך+ציטוט.)
3. **Mac2:** תוכנית 08-07 ("סים-מקביל היום, השוואת-ערב = חלק משער-ה-GO") — **אין אף שורת-תוצאה
   בערוץ**. מעבר-הלייב מחר לא יכול להסתמך על שער שלא דווח; וממילא חסום ע"י §1.
4. **duplicate ב-.env:** ‏`SYSTEM6_SUPERVISOR=1` מופיע פעמיים (היגיינה, כמו מקרה FIXED_CONTRACTS_3).
5. **postmortem עיוור לרטרו:** תיקון-P&L רטרואקטיבי לא מייצר/מעדכן PM (המקרה של #640).

## 5. סדר-פעולות מומלץ לפני חימוש (לפסיקת-מייקל, לא בוצע דבר)

1. 🔴 P0-1b: לחווט drainer לולאתי (fill_poller tick / thread) **או** להחזיר כתיבה-ישירה-תמיד +
   ניקוי-תור בעליית-backend + טסט-אינטגרציה שמוכיח פקודה-שנייה-מגיעה-ל-DLL; לנקות ידנית את
   3 הקבצים התקועים לפני הסשן. 2. 🔴 שורש כותב-סוג-היום (self-heal לא מספיק). 3. contracts:0
   ב-half-sizing — שורש. 4. השלמת P1-5 (EXCESS consumer) + replay-P1-4. 5. ntfy שלב-2 + Render-card.
6. commit לכל ה-untracked + סגירת חוב-FLAG_REGISTRY.
