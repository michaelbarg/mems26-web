# תובנות-הלילה 07→08.10.2026 — מה היום לימד, מה נמדד, מה ממתין לפסיקה

*נכתב 08.10 00:17 IL ע״י cowork (מייקל 07.10 23:4x: "תעבוד, תתקן ותכין תובנות"). כל מספר כאן נמדד בפקודה שמצוטטת; P&L-צל מצוטט עם ההסתייגות הקבועה (21.4% מסטופי-הצל נקבעים ע״י כלל-הסטופ-ראשון).*

## 0. היום במספרים (07.10, יום-דמו ראשון: `MEMS26_MODE=demo` מ-15:18, Sim1)

- **שוק:** פתיחה 7837.5 → שפל 7815.75 (17:xx, הרחבת-IB כושלת של 4.25 נק׳ מתחת ל-7820) → היפוך → שיא 7859.5 (22:xx) → סגירה 7851.25. IB 7820.0–7842.25 (רוחב 22.25 = 3.6 ATR). תוויות (IL): Normal 17:00 → Variation 17:45 → Neutral_Extreme 18:50 → Neutral_Center 22:30 → … → Neutral_Center 23:25 (סופי, conf 0.67).
- **דמו (Sim1): 4 עסקאות, 0 ניצחונות, −106.25$.** #3164 OPENING_DRIVE SHORT 16:50 @7823.25 (סטופ 7838.25 / T1 7800.75) → השוק נתן 7.5 נק׳ בעד, דרש 22.5, סטופ 17:51 **−75$** · #3191 CEILING_FLIP_LONG 18:00 @7823.5 ו-#3196 CEILING_FLIP_LONG 18:15 @7828.25 — **`ORDER_FAILED:-1`, בוטלו** (סעיף 2) · #3220 CEILING_FLIP_SHORT 19:40 @7843.5 (סטופ 7849.5) → סטופ 20:02 **−31.25$**.
- **צל: 108 עסקאות, 39 ניצחונות, −115.77$** — ובחלוקה לכיוון: **LONG 63 · 31 ניצחונות · +762.98$ · SHORT 45 · 8 ניצחונות · −878.75$.** המפסידים: ZLR SHORT 13× −415$, CEILING_FLIP_TOUCH2 SHORT 20× −164$.
- **החלטות:** 103 · ירו 56 · נחסמו: tree:location 24 · **tree:bias 10** · tree:time_cutoff 8 · tree:stand_down 6 · tree:kind 2.

```
$ psql -Atc "SELECT direction, count(*), sum(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END), sum(coalesce(pnl_usd,0))::numeric(10,2) FROM v9_trades WHERE created_at >= '2026-10-07 15:00+03' AND mode='shadow' GROUP BY 1"
LONG|63|31|762.98
SHORT|45|8|-878.75
```

## 1. התובנה הראשונה — השעה שבה המערכת הייתה עיוורת לכיוון (18:00–18:55)

ההרחבה הראשונה של ה-IB הייתה למטה (4.25 נק׳, 17:xx) ונכשלה תוך דקות. מ-17:45 ההטיה (`dir_hint`) = **SHORT** ("ההרחבה הדומיננטית"), ונשארה SHORT עד שההרחבה למעלה עברה את 4.25 נק׳ (~19:00). בחלון הזה נחסמו **10 מועמדי-LONG** ב-`tree:bias`, כולם ביום "Variation", כולם בזמן שהשוק עלה 7823 → 7846:

```
$ psql -Atc "SELECT created_at::time(0), classification, direction, entry FROM v9_decision_vectors WHERE kind='DECISION' AND blocked_by='tree:bias' AND created_at >= '2026-10-07 16:00+03' ORDER BY 1"
18:00:04|HTLB|LONG|7823.25      18:10:05|FAMIR|LONG|7823.75     18:25:04|ZLR|LONG|7827.0       18:25:08|GHOST|LONG|7827.25
18:30:02|ZLR|LONG|7827.5        18:30:06|ZLR|LONG|7826.75       18:40:03|REACTIVE_LONG|LONG|7837.75   18:40:04|GHOST|LONG|7838.25
18:55:05|INITIATIVE_LONG|LONG|7843.0   18:55:07|GHOST|LONG|7842.5
$ psql -Atc "SELECT date_trunc('hour', created_at AT TIME ZONE 'Asia/Jerusalem')::time(0), vector->>'dir_hint', vector->>'extension', count(*) FROM v9_decision_vectors WHERE kind='DECISION' AND created_at >= '2026-10-07 16:00+03' GROUP BY 1,2,3 ORDER BY 1,2"
17:00|SHORT|down|5 · 18:00|SHORT|down|14 · 18:00|SHORT|both|2 · 19:00|LONG|both|13 · 20:00|LONG|both|11 · 21:00|LONG|both|21
```

**זה לא באג וזה לא "לכבות":** שחרור-ההטיה אחרי הרחבה כושלת (T-517, חי) משחרר רק כל עוד המחיר עדיין מחוץ ל-IB; השחרור גם אחרי סגירה פנימה (T-523) **נמדד ונדחה** (64 סשנים: −203$/−102$). היום הוא אותו יוצא-דופן כמו 01.10 ו-02.10 — והמדידה אומרת שבממוצע הכלל צודק. מה שכן אפשר למדוד, וריאנט אחד: **"דומיננטיות לפי קבלה" במקום "דומיננטיות לפי גודל"** — הרחבה כושלת קטנה (< 1 ATR, חזרה פנימה תוך ≤ 3 ברים) אינה קובעת הטיה; ההטיה נקבעת ע״י ההרחבה הראשונה שמתקבלת (≥ 2 סגירות מעבר ל-IB). ייחוס אותו בוקר, כלל-הקבלה הרגיל. היום היה נותן: הטיה None מ-17:45 עד 18:55 ⇒ 10 ה-LONG-ים נבדקים בשאר השערים במקום להיחסם. **לא מדליקים — מודדים.**

## 2. התובנה השנייה — ההפסד האמיתי של היום היה בביצוע, לא בהחלטה: ≈ +155$ שלא נכנסו

שתי כניסות-LONG של הדמו (#3191 18:00 @7823.5 → T1 7835.5; #3196 18:15 @7828.25 → T1 7847.38) נדחו ע״י סיירה (`error=-1 GENERAL_ERROR_OR_NOT_ENABLED`). על הברים שתיהן היו מגיעות ל-T1 בלי לגעת בסטופ (שפל שעת-18:00 7817.25 > 7815.5; שיא 7846.25 ≥ 7835.5; שיא שעת-19:00 7849.25 ≥ 7847.38): **≈ +60$ ו-+95$**. עם שתיהן היום היה ≈ **+49$** במקום −106$. למה נדחו:

```
17:51:09 [Reconcile] AGREED_FLAT — Sierra reports FLAT (position_qty=0)        ← #3164 נסגר
17:52:01 [Reconciler] T-43: contract mismatch DETECTED (TM=0 Sierra=-1) — BLOCKING new entries until resolved
17:52:21 [FillPoller] FIX-10 ORDER_REJECT seen (Trade Order Error - Insufficient Account Value (NLV) for margin…) but no PENDING demo/live trade to correlate — manual order?
18:00:05 [FillPoller] POSITION_TRUTH: Sierra holds -1c but trade 3191 has NO submit-ack — NOT attributing
18:00:09 [FillPoller] ORDER_FAILED from Sierra: error=-1 (GENERAL_ERROR_OR_NOT_ENABLED) — cancelling pending trade + releasing slot
19:40:06 [Reconcile] AGREED_FLAT — Sierra reports FLAT (position_qty=0)        ← #3220 נכנס ומתמלא
$ trade_activity_events.jsonl (היום, שני אירועים בלבד — שניהם חשבון-האמת 37138283, is_sim=false):
  ORDER_REJECT 12:15:43Z (15:15 IL) · ORDER_REJECT 14:52:21Z (17:52 IL)  "Insufficient Account Value (NLV) … Margin needed 288.53 USD"
```

כלומר: מ-17:52:01 ישבה על Sim1 פוזיציית **−1 שאינה שלנו** (עד לפני 19:40), ובאותה דקה — ובשעה 15:15 — נדחו בחשבון-האמת שתי פקודות על מרג׳ין שאינן של המערכת. שתי השעות האלה הן בדיוק השעות של ההודעות שלך אליי (15:14, 17:52). **שאלה אחת ב-MICHAEL_INBOX: אלה לחיצות שלך/אתי?** המערכתי: סיירה (ACSIL) דוחה כניסה **נגד** פוזיציה קיימת בחשבון — בחשבון משותף זה יחזור. בלייב יש שומר-קדם-שליחה ("פוזיציה זרה", 05.10 19:40) שלא שולח בכלל; בדמו הוא לא פעל — הפקודה נשלחה, נדחתה, והעסקה נרשמה-ובוטלה. שתי התוצאות = אפס עסקה. פריט-מדידה (T-565): כמה פעמים ב-65 הסשנים כניסה שלנו חופפת לפוזיציה זרה בחשבון-המשותף — זה המחיר של "חשבון משותף", והוא נמדד, לא מנוחש.

## 3. התובנה השלישית — מה המערכת כן עשתה נכון היום

- הכיוון בצל: 63 LONG +763$ מול 45 SHORT −879$ (הסתייגות 21.4%) — **הגוף של הפוטנציאל היה בלונגים, והעץ חסם אותם רק בשעה אחת (סעיף 1)**. מ-19:00 ההטיה LONG, ובשלב D 21:05–21:55 ה-ZLR LONG-ים עברו את העץ (TAKE על `…/phase=D/day_type=Neutral_Extreme/rel_bias=with`) ונחסמו אחריו ב-`rr_entry_gate` → תאום-צל (`T-219 shadow_blocked … blocked_by=rr_entry_gate`), לא בעץ.
- `tree:time_cutoff` 8 חסימות אחרי 22:00 — החיתוך (3.4.0, 06.10) עובד.
- אפס עסקאות-אמת (דמו בלבד), אפס נגיעה בעץ/.env/LaunchAgents בכל הלילה.

## 4. מה תוקן הלילה (קריאה: `git log --oneline -6`)

| קומיט | מה | מצב |
|---|---|---|
| e6024964 | **T-563** זרם tick_reversal — השורש: ה-plist של ה-LaunchAgent (15.07) מייצא `TICK_REVERSAL_DISABLED=true` **ו-**`FOOTPRINT_DISABLED=true` **אחרי** `source .env`, ו-`env_loader` אינו דורס ⇒ אין שמירה (`curl ⇒ {"disabled":true}`), **ומערכת 3 כבויה לגמרי** למרות `.env FOOTPRINT_DISABLED=0` — זה החסם של 358a4610. השורות עד 01.10 23:06 = חלונות-ה-screen של T-435. | פסיקה 1 ב-INBOX; `scripts/t563_plist_footprint_fix.sh` מוכן (הרצה-יבשה רצה, אפס שינוי) |
| f6405fbd | **T-561** סלוט-שני בהרנס: שני תיקוני-מכניקה (נתיבי 3.4.0 עם `hour=*(NN)/`; הניתוב-מחדש נחסם `duplicate_fire`) ⇒ עשן 2026-08-03: opened=3, +111.25$→+243.75$ | מדידה מלאה בבוקר (t561s2 מול t564ref) |
| 57d31772 | **T-545** `W2_EXIT_OWNERSHIP_V1` (כבוי): אירוע-ברוקר שנסרק לפני `created_at` אינו של העסקה; עסקה PENDING לא נסגרת מה-fallback. 5 מבחנים + 25 קיימים ירוקים. **T-563b** `flag_guard` "שן שלישית": מדווח את 16 מפתחות-ה-plist מול .env ומול הסביבה של ה-pid החי (היום: `FOOTPRINT_DISABLED plist=true .env=0 live=true`), PASS לא משתנה. **`mems26_preflight.sh`**: קרא PASS מהשורה האחרונה — אדום-שווא מאז 25.08 — עכשיו לפי קוד-יציאה. | פסיקה 2 ב-INBOX |
| 395e5752 | **T-526** (fix-agent 23:40): הכותב של דריסת-ברי-woodies נמצא — ה-backfill ההיסטורי של הגשר בעלייה, `America/New_York` קשיח מול `V9_CHART_TZ=America/Chicago` ⇒ ברים שעה מוקדם; תוקן בשורש, שומר-דגל-כבוי | ממתין לאימות בעליית-הגשר הבאה |

## 5. מה רץ בבוקר (08:20, cowork) ואיך פוסקים

`harness_out/t564/run.sh`: **t564ref** (ייחוס אותו בוקר, קונפיג-הלייב) → **t564a** (ההיתר היחיד שביקשת: INITIATIVE_SHORT · Variation · 18–19 · TAKE, `config/decision_tree_v3.t564_allow.yaml`, 19 וקטורים משתנים, 0 מחוץ להקשר) → `cmp_vs_live.py t564a t564ref` → **t561s2** (סלוט-שני על `OPEN_DRIVE/C/Trend_Normal/with`) → `cmp`. ~2 שעות, השומר עוצר לבד ב-16:00. **כלל-הקבלה שלך:** החזקה-10 ≥ 0 **וגם** Δנטו > 0 **וגם** כל חודש ≥ 0 — אחרת "לא עולה". התוצאות ייכתבו ב-`docs/reports/T564_…_2026-10-08.md`, בשרשור וב-INBOX.

## 6. ממתין לפסיקתך (מחוץ ל-RTH בלבד) — ראה `docs/handoff/MICHAEL_INBOX.md`

1. T-563 — להסיר `export FOOTPRINT_DISABLED=true` מה-plist (S3 בצל, אפס שינוי-מסחר) — כן/לא.
2. T-545 — `W2_EXIT_OWNERSHIP_V1=1` (ספרים בלבד) — כן/לא; אפשר באותו ריסטארט.
3. השאלה על 15:15 / 17:52 (סעיף 2).
4. T-564 / T-561 — אחרי ההרנס.

*מקורות: `v9_trades`, `v9_decision_vectors`, `v9_bars_5min_woodies`, `v9_day_type_state` (ts נאיבי-UTC), `/tmp/backend.err.log`, `~/SierraChart_Data/v9_export/trade_activity_events.jsonl`, `docs/reports/SUPERVISION_LATEST.md` (22:36), שרשור 23:30, TASK_LOG T-545/T-561/T-563/T-564.*
