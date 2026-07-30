# CURSOR — ביקורת "מזהה רווחיות וגם יורה" (2026-07-30)

**מאת:** cursor-agent · **ספק:** `docs/handoff/CURSOR_PROFIT_FIRE_AUDIT_2026-07-30.md` · **אפס שינויי-קוד/דגלים**
**חוק-5:** כל טענה עם פקודה+פלט (למטה / מצורף). מייקל פוסק על כל המלצה.

---

## 🔴 ממצא-מיידי (לפני שאר הביקורת) — הפיד חי-אבל-נדחה עכשיו

**שורש:** הברידג' (PID 655) רץ מאז **Sat Jul 25 13:16** בלי `V9_CHART_TZ` ב-env → ברירת-מחדל `America/New_York` (+4h קיץ). הצ'ארט = Chicago (−5h). תוצאה: ברים מגיעים ל-backend עם **שיור ~1h**, ו-`TS_OFFSET_INGEST_GATE` דוחה אותם.

```
BRIDGE V9_CHART_TZ NOT IN ENV
BRIDGE started: Sat Jul 25 13:16:03 2026
[woodies_5min] TS-OFFSET-GATE REJECTED batch: newest bar ts 3730s behind now (> 900s)
  while feed advances (1785388800 -> 1785391800) — live-but-mislabeled TS
DB woodies MAX(ts)=2026-07-30 09:15 IL ; export corrected would be ~10:10 IL
.env has V9_CHART_TZ=America/Chicago + TS_WHOLE_HOUR_NORMALIZE_V1=0 — but bridge never restarted
```

**השפעה על "ירי רווחי":** בלי ברים טריים ב-DB אין זיהוי/ירי אמין היום. זה קודם לכל כיול-שער.
**פעולה (לא אני — cowork/cc):** restart bridge עם `V9_CHART_TZ=America/Chicago` מ-`.env` / LaunchAgent; אמת `export_ts − newest_bar ≈ 0` אחרי תיקון; אל תדליק `TS_WHOLE_HOUR_NORMALIZE` מחדש.

---

## §1 · אימות-נגד אבחנת-TZ — ✓ עם הסתייגות-הפעלה

| בדיקה | תוצאה | ראיה |
|---|---|---|
| (א) ייצוא טרי: raw bar ≈5h מאחורי `export_ts` | ✓ | `woodies_5min.json`: export_ts=07:10 UTC, newest raw=02:10 UTC, offset=5.01h. Reinterpret כ-CT wall → 07:10 UTC = תואם. |
| (א′) ts יחיד נכון עד DB | ✗ **עכשיו** | Bridge בלי Chicago → DB לא מקבל batches (TS-OFFSET reject). לפני היום: תאומי-OHLC +1h על 07-27 (12 תאומים 12:25–13:20 ET). |
| (ב) אפס כתיבות-מוזזות מאז כיבוי normalize | ⚠ חלקי | `.env` `TS_WHOLE_HOUR_NORMALIZE_V1=0`, `WOODIES_TS_HOUR_FIX=0`. Backend (PID 72413, start 09:20) — שני הדגלים **לא ב-env** → code default OFF ✓. אבל **10 תאומי +1h OHLC** נרשמו הבוקר 07:25–08:10↔08:25–09:10 IL (לפני/על סף הריסטארט) — שיור ממצב-קודם או מ-bridge-NY. |
| (ג) תיקוני-ts ששרדו | ✓ לכיבוי, ✗ להפעלה | קוד: `_hour_shift_fix` (`bars.py:430`, kill `WOODIES_TS_HOUR_FIX`) + `_ts_whole_hour_normalize` (`:493`, flag OFF). שניהם OFF ב-`.env`. **הבעיה החיה = bridge TZ default**, לא normalize. |

**המלצה §1:** לא למחוק את פונקציות-הנרמול עדיין (kill-switch שימושי אם chartbook ייסחף) — אבל **חובה** שהברידג' ייטען עם Chicago; לתעד ב-CLAUDE.md שהצ'ארט=CT; אחרי restart — שאילתת-תאומים חייבת =0 על חלון חדש.

---

## §2 · נתיחת עסקאות-07-27 (−$90)

E2E דיווח "3 live". DB בפועל:

| id | מצב | תבנית | כניסה | סטופ | t1 | PnL | הערות |
|---|---|---|---|---|---|---|---|
| **545** | CLOSED live | ZLR SHORT | 7424.5 @13:40 ET | 7430.5 (6pt) | 7416.25 | **−$90** | STOP_HIT 13:52 |
| **548** | CLOSED live | GB100 LONG | 7433.0 @13:55 | 7415.5 | 7459.25 | **$0** | SIERRA_FLAT 16:30 — MFE היה +23.75 |
| **536** | CANCELLED | INITIATIVE_LONG | 7456 | 7418.75 | 7511.9 | — | PHANTOM_FILLED_FLAT |

**#545 — ירי-והפסד (מחלה כפולה):**
- בר-הכניסה 13:40 OHLC **זהה** לבר 12:40 (תאום +1h) — הכניסה על נתונים מזוהמים.
- אחרי כניסה (חלון +60דק'): MAE_low=7422.5 (רק 2pt עם-הכיוון!) · MFE_high=7437.75 → הסטופ נגע מיד; לא היה "פולבק" אמיתי.
- מרחק משפל-סשן 7416.25 = 8.25pt → **עובר** `EXTREME_MIN_DIST=6` — הגארד לא היה חוסם.
- `day_type=Variation`. שערים חדשים: `awaiting_release` / trend_bypass — **לא ביומן על הירי הזה** (עבר ללייב). כיול-השחרור לא היה מציל כאן; **שלמות-ברים** כן.

**#548 — ירי בלי מימוש:**
- LONG GB100: min=7424 · max=7456.75 אחרי כניסה → היה רווח פוטנציאלי ~+$23–$118 לפי יעדים, נסגר SIERRA_FLAT עם `pnl_usd=0` — **פער-חשבון**, לא פער-כניסה.

**#536:** פנטום — לא חלק מה−$90.

**מסקנה §2:** ה−$90 = עסקת-ZLR אחת על בר מזוהם + סטופ צר מול רעש. הכיולים החדשים (release/conf) **לא** היו משנים את 545 לטובה בלי תיקון-TS. GB100 הוכיח זיהוי-כיוון נכון ונכשל במימוש/חשבון.

---

## §3 · רגישות כיולים מול יומן (`gateway_decisions.jsonl`)

יומן: 4927 שורות. חלון 27–29:

| יום | live | shadow | blocked | חוסמים דומיננטיים |
|---|---|---|---|---|
| 07-27 | 9 | 5 | 45 | chase 9 · playbook 9 · cont_trend 9 · rr 7 |
| 07-28 | 12 | 154 | 793 | eod 163 · entry_confirm 148 · rr 127 · cont 86 · zone 81 · **lsma 42** · release 18 |
| 07-29 | **0** | 30 | 269 | **feed_watchdog 100** · **awaiting_release 99** · cont 26 · playbook 17 |

### LSMA flat (סף 0.25)
ייחודיים חסומים עם slope: `[0.02, 0.02, 0.04, 0.04, 0.0533, 0.0533, 0.2133, 0.2133]`

| סף | עדיין חוסם (uniq) | משחרר |
|---|---|---|
| 0.10–0.20 | 6 | **2** (רק ה-0.213) |
| 0.25 (נוכחי) | 8 | 0 |

**מקרה 0.213 (07-29 14:30 ET ZLR LONG @7428.5):** אחרי הכניסה בר 14:30 low=7414.75 (−13.75) — סטופ-ZLR טיפוסי היה נפגע **לפני** העלייה ל-7465. אחר כך seam ~90pt (14:40→14:45) — נתיב לא אמין. **טענת "+29pt שהוחמץ" — לא מאומתת** (יותר סביר LOSS ואז עלייה בלי הפוזיציה).
→ **אין ראיה מספקת** להוריד ל-0.20 רק בגלל המקרה הזה.

### Chase 6pt
21 ייחודיים, כל המרחקים `<6` (0.25–5.75). אין שחרור בלי להוריד סף. ב-6→4 משחרר 12/21 — בלי תוצאות-קדימה מלאות על כולם.
→ **השאר 6** עד שיש phase/מבני (המלצת-סופ"ש); אל תרכך בלי סימולציה.

### Cooldown (`PATTERN_STOP_COOLDOWN_V1=1` ב-.env)
**0 חסימות** ביומן בשם cooldown — או שאין עדיין STOP_HIT-חוזר מאז ההדלקה, או שהטלמטריה לא כותבת את המפתח. לא ניתן לאשר אפקטיביות מהיומן.

### RELEASE_TREND_BYPASS / DAYTYPE_PLAYBOOK_MIN_CONF
פרמטרים חיים בקוד (15 / 0.4), לא ב-.env. 07-29: `awaiting_release=99` עדיין החוסם #2 אחרי watchdog — ה-bypass לא מספיק כשהפיד/סיווג שבריריים.
→ **אין ראיה** לשנות 15/0.4 היום; קודם פיד.

---

## §4 · חוסמי-S2 פנימיים — GO/NO-GO

### (א) R:R-breakout = measured-move במקום מרחק-לשיא-ישן
על חסימות `rr_entry_gate` (ייחודיים): פרוקסי reward=impulse מקיצון-סשן נגדי.

- מדגם כולל (כולל לילה): 35/40 "pass" — **מוטה** (טווח-לילה ענק → SHORT תמיד "יש מקום").
- מדגם RTH 07-27 אחר-צהריים (GHOST/ZLR): רוב ה-WIN_1R בחלון 60–90דק' **אבל** על ברים עם תאומי-TS — אמינות מוגבלת.

**פסק: NO-GO לבנייה עכשיו.** הרעיון דוקטרינרי-סביר, אך בלי (1) פיד נקי, (2) הגדרת measured-move מעוגנת-מבנה (לא session-extreme גולמי), (3) סימולציית-RTH בלבד — יירה יותר ויאבד. תנאי-GO: replay RTH ≥10 ימים אחרי תיקון-bridge.

### (ב) auth-table בביטחון-נמוך → REDUCED-2
`DAYTYPE_PLAYBOOK_MIN_CONF=0.4` כבר מדכא veto בביטחון נמוך. 07-29 היסטוריה סופית: `Neutral_Extreme conf=25` — והיום היה **0 live** בעיקר מ-watchdog+release, לא מ-auth.
**פסק: NO-GO כשינוי נפרד.** אין ראיה ש-REDUCED-2 היה משחרר עסקאות-מנצחות ב-07-29; הסיכון = ירי-חלקי על סיווג שגוי. DEFER אחרי System0 direction-authority.

---

## §5 · פערי-זיהוי — NOT-VERIFIED מלא (אין replay נקי)

| פריט | סטטוס קוד | מה יש בדאטה | המלצת-הדלקה |
|---|---|---|---|
| `NEUTRAL_ROUNDTRIP_V1` | בנוי-OFF (`daytype_classifier.py:324`) | 07-29 סופי ב-history = **Neutral_Extreme** כבר (לא NV) — ייתכן שהמנוע החי כבר הגיע ל-Neutral בדרך אחרת; לא הוכח שהדגל היה משנה. | **השאר OFF** עד replay עם ברים מתוקני-TS |
| `DD_BIMODAL_RELAX_V1` | בנוי-OFF (`dd_features.py:118`) | 07-28 history = Variation conf=0; state LOCKED_LOW_CONF Variation. CC טען bimodal=0.932 בלי held — לא שוחזר כאן ב-replay. | **השאר OFF**; סיכון over-classify Variation→Trend_DD |

**NOT-VERIFIED:** הרצת-replay מלאה עם `DD_BIMODAL_RELAX_V1=1` / `NEUTRAL_ROUNDTRIP_V1=1` על ברים 07-28/29 — נחסמה כי ברים מזוהמים + פיד-נדחה; אחרי תיקון-bridge אפשר לחזור.

---

## טבלת-המלצות (מדורגת לפי $-מושפע)

| # | המלצה | $-מושפע (הערכה) | ראיה | טסט-מוכיח | סיכון |
|---|---|---|---|---|---|
| **1** 🔴 | **Restart bridge עם `V9_CHART_TZ=America/Chicago`** (LaunchAgent/env) | חוסם את כל הירי היום | Bridge env חסר TZ; TS-OFFSET reject ~3730s; DB מאחורי export | אחרי restart: `export_ts−bar_ts < 120s` + 0 תאומי-OHLC+1h בחלון חדש + woodies MAX≈now | נמוך אם רק restart+env |
| **2** 🔴 | **אל תדליק מחדש `TS_WHOLE_HOUR_NORMALIZE`** | מונע כפל-+1h | אבחנת-CC אומתה; תאומים 07-27 | שאילתת-תאומים =0 אחרי #1 | נמוך |
| **3** 🟡 | **נקה/בטל ברים תאומים +1h ב-DB** (חד-פעמי, אחרי #1) | מונע כניסות על בר-רפאים (#545) | 12 תאומים 07-27; 10 הבוקר | ספירת-תאומים לפני/אחרי | בינוני — לגבות לפני מחיקה |
| **4** 🟡 | **חקור SIERRA_FLAT pnl=0 על #548** | הפסד-מימוש על מנצחת | GB100 MFE+23 / pnl_usd=0 | השוואת ledger Sierra ↔ v9_trades | נמוך |
| **5** 🟢 | **השאר chase=6, lsma=0.25, release bypass=15, playbook_min_conf=0.4** | — | אין ראיה חד-משמעית לשינוי; "miss 0.213" לא מאומת כרווח | — | שינוי עיוור = ירי גרוע יותר |
| **6** 🟢 | **NO-GO ל-R:R measured-move ו-auth REDUCED-2 כעת** | מונע ירי-יתר | פרוקסי-לילה מוטה; 07-29 חסום בעיקר ע"י פיד | GO רק אחרי #1+#3 + replay RTH | גבוה אם ייבנה עכשיו |
| **7** 🟢 | **השאר DD_BIMODAL / NEUTRAL_ROUNDTRIP OFF** | — | NOT-VERIFIED על ברים נקיים | replay אחרי #1 | over-classify |

---

## שורה-תחתונה

עם ההמלצות, **ביום כמו 07-29** המערכת קודם כל הייתה **צריכה פיד חי** (בלי זה 0 עסקאות בלתי-נמנע מ-watchdog/offset). אחרי תיקון-bridge בלבד — עדיין היו ~99 `awaiting_release` + cont_trend; הכיולים החדשים לבדם **לא** מוכיחים יום-רווחי.

עם ההמלצות, **ביום כמו 07-27**: בלי תאומי-TS ייתכן ש-#545 (ה−$90) לא הייתה נורה על בר-רפאים; #548 עדיין הייתה דורשת תיקון-מימוש. **לא מגובה-חישוב מדויק ל-"Y$"** בלי replay אחרי ניקוי-ברים — לכן לא ממציאים מספר.

**סדר עדיפויות למייקל:** (1) bridge Chicago restart → (2) אמת continuity → (3) רק אז דנים בכיולי-שער / P5.

---

## NOT-VERIFIED / NOT-DONE

- Replay מלא `DD_BIMODAL_RELAX_V1` / `NEUTRAL_ROUNDTRIP_V1` על 07-28/29 עם ברים נקיים.
- סימולציית-תוצאה פר-סף ל-chase (4 vs 6) עם MFE/MAE על כל 21.
- אימות ש-`PATTERN_STOP_COOLDOWN` באמת נטען בתהליך (0 אירועים ביומן).
- האם LaunchAgent של הברידג' מזין `.env` בכלל (חשד חזק שאין — PID מ-25.07).
- תיקון-כיס ZT מהסופ"ש — **מחוץ לסcope של ספק זה** (הספק הנוכחי = profit-fire); לא נבדק מחדש כאן.

## ראיות-גלם (קיצור)

```
.env: V9_CHART_TZ=America/Chicago · TS_WHOLE_HOUR_NORMALIZE_V1=0 · WOODIES_TS_HOUR_FIX=0
Bridge PID655: V9_CHART_TZ NOT IN ENV · started Sat Jul 25
Backend log: woodies TS-OFFSET-GATE REJECTED ~3730s behind (repeating)
Export offset raw→export ≈5.01h (Chicago proof)
07-27 +1h OHLC twins: 12 · since 07-30 00:00 IL twins: 10
Live 07-27 closed: #545 ZLR −$90 · #548 GB100 $0 (SIERRA_FLAT) · sum −90
Journal 07-29: live=0 shadow=30 blocked=269 (watchdog100 + release99)
LSMA slopes blocked uniq: 0.02×2 0.04×2 0.053×2 0.213×2
Chase dists all <6 (n=21 uniq)
```
