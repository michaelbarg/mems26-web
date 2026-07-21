# ראנבוק-בוקר 2026-07-21 — הכנת המערכת ללייב (אור-ירוק מייקל 07-20 23:32)

**כסף אמיתי. הכלל: אין ירוק בשלב → לא ממשיכים לשלב הבא. אין חימוש בלי שער-הפתיחה הקשיח (§7).**
בעלים: **מייקל** מכריע · **cc-macbook** מבצע (טרמינל אמיתי) · **cowork** מאמת סימטרית · **cursor** מוביל + מאמת.
כל שלב: פקודה + פלט-גולמי ב-LIVE_CHANNEL (חוק-5). זמנים IL (פתיחה 16:30).

---

## שלב 0 — לילה/שחר: ביקורת-קלוד על תיקון-הדאטה (cc-macbook)
- [ ] `docs/handoff/CC_AUDIT_TS_REPAIR_2026-07-20.md` — כל שאילתות-האימות מול EXPECTED.
- [ ] חריגה כלשהי → **עצור, אל תמשיך לראנבוק** — rollback לפי הנוהל במסמך ולהעיר את cursor.

## שלב 1 — שתי פסיקות-מייקל (בכתב, שורה אחת כל אחת) — לפני ה-restart
| # | דגל | המלצת-cursor | פסיקת-מייקל (מלא!) |
|---|---|---|---|
| 1 | `TS_OFFSET_INGEST_GATE_V1=1` | **כן** — היה עוצר את תקלת-07-20; מצב-הכשל שלו = דחיית-batch+לוג, לא מסחר | ☑ **כן — "מאשר את שניהם" (מייקל 07-21 08:11 IL)** |
| 2 | `IB_BREAK_ANY_EXPANSION_V1=1` | **כן** — מסווג-יום-אוטומטי; בלעדיו אין override (פג בחצות) והתווית תלויה במסווג בלבד | ☑ **כן — "מאשר את שניהם" (מייקל 07-21 08:11 IL)** |

נפסק "כן" (שניהם ✅) → cc-macbook: עדכון `.env` + `config/RULED_FLAGS.yaml` **באותו קומיט**, לפני ה-restart של שלב 3.

### פסיקות נוספות 07-21 בוקר (מהגדרות-מייקל 08:05) — **נפסקו 08:23**
| # | נושא | מצב-קוד | פסיקת-מייקל |
|---|---|---|---|
| 3 | `T0_TARGET_PTS`: 3.5 → **4.0** (מייקל: "T0 הוא 4 נקודות") | `.env:282=3.5` | ☑ **"1 מאושר" (08:23)** |
| 4 | `BE_AFTER_REAL_T1_V1=1` — BE על T1 האמיתי (C2), לא על סקאלפ-T0; משם S6 | קוד מוכן (`manager.py:481`), דגל OFF | ☑ **"הסטופ עובר לכניסה רק אחרי T1" (08:23)** |
| 5 | ביטול time-stop לעסקאות (מייקל: "אין זמן לעסקה, רק מערכת 6") — W-10 90ד' + טבלת 30-90ד'. W-10 סוגר רשומת-backend בלבד (לא Sierra) → מחולל רשומות≠מציאות | פעיל היום | ☑ **"3 מאשר" (08:23)** |

**מפרט-ביצוע 3-5 ל-cc-macbook (אותו קומיט+restart של פסיקות 1-2):**
- (3) `.env`: `T0_TARGET_PTS=4.0`.
- (4) `.env`: `BE_AFTER_REAL_T1_V1=1`.
- (5) time-stop off בשני המקורות: `config/targets.yaml` — כל 7 סוגי-היום `time_stop_minutes: null` ·
  `backend/v9/systems/woodies/config/dispatcher_config.yaml` — `time_stop.time_stop_minutes: null`
  (kill-switch מובנה ב-`TimeStopEnforcer`, `time_stop.py:50-53` — null/0 → disabled, אפס שינוי-קוד).
- כל החמישה + RULED_FLAGS **באותו קומיט** · אימות אחרי restart: probe שהדגלים נטענו + `flag_guard`.

### שלב 1ב — פסיקת-C4 (מייקל 08:56: "מאשר 1" — תיקון-מלא היום)
- [ ] cc-macbook: פערי A+B (BE-wiring + dispatcher W-10) → ואז מפרט C4-RULING6 (LIVE_CHANNEL 09:10):
      DLL-hardening קבוצה-4 · t4 פר-סוג-יום (קצה-נגדי/stop-only/T3+15:45) · טסטים · build+deploy.
- [ ] cc-imac: אימות-סים — 4 קבוצות-OCO, 4 סטופים (צילום + פלט-גולמי).
- [ ] **שער-החימוש 16:15 מותנה בזה.** לא ירוק → אין חימוש (או פסיקת-מייקל מפורשת לסחור בלעדיו).

## שלב 2 — snapshot (cc-macbook, ~15:30 IL)
- [ ] `bash scripts/mems26_snapshot.sh "pre-open-0721"` → ודא תיקייה חדשה ב-`~/mems26_snapshots/`.

## שלב 3 — restart-בוקר אחד נקי (cc-macbook)
- [ ] `launchctl kickstart -k gui/$(id -u)/com.mems26.backend` → PID חדש.
- [ ] **הוכחת-תהליך-חי** (§8 מנוף 2 — לא "קומיט=בוצע"): `curl -s :8000/health` →
      alive:true, ו-boot-line בלוג עם ה-PID החדש. אם נפסקו דגלים בשלב 1 — אמת שהם נטענו:
      `curl -s :8000/api/v9/status | jq` / probe ייעודי, לא הנחה.
- [ ] ⚠ אם PG מסרב אחרי restart (`Postgres.app failed to verify trust`) — restart ל-Postgres.app
      מה-GUI לפני הכל (הסיכון שמופה אמש ב-LIVE_CHANNEL).

## שלב 4 — תיקון תווית-07-20 (cc-macbook, אחרי ה-restart בלבד)
- [ ] ```sql
      UPDATE v9_day_type_history SET day_type='Normal_Variation'
      WHERE date='2026-07-20' AND day_type IN ('Neutral_Extreme','Neutral_Center');
      ```
- [ ] המתן 5 דק' → `SELECT day_type FROM v9_day_type_history WHERE date='2026-07-20'` →
      עדיין `Normal_Variation` (אתמול המנוע-החי דרס תוך 2 דק'; אחרי restart+rollover אמור להחזיק).

## שלב 5 — אימות-מערכת (cc-macbook מריץ, cowork מצליב)
- [ ] `python3 scripts/flag_guard.py` → **PASS** (אם הודלקו דגלים — אחרי עדכון RULED).
- [ ] `bash scripts/mems26_verify.sh` → DLL=repo · אינדקס · פיד · DB-lag — הכל ירוק.
- [ ] `curl -s :8000/api/v9/health/streams` → streams ירוקים, errors=0 (footprint no_data = ידוע).
- [ ] אורפן/חשבון: `cat ~/SierraChart_Data/v9_export/sierra_state.json` → `position_qty:0, working_orders:0`
      **וגם מול מסך-Sierra** (23:32 אמש כבר הראה שטוח — לאמת שלא השתנה בלילה).

## שלב 6 — PRE_TRADE_PROTOCOL מלא (T-30 = 16:00 IL)
- [ ] `docs/runbooks/PRE_TRADE_PROTOCOL.md` Phases 0-3 (שירותים · streams · מחיר-חי · סנכרון-Sierra).
- [ ] iMac = **Sim מאושר** (חוק סוחר-יחיד) לפני שה-MacBook חמוש.

## שלב 7 — שער-פתיחה קשיח (מייקל מאשר, 16:15 IL)
**כל אלה ירוקים, אחרת אין חימוש:**
- [ ] ביקורת-שלב-0 של קלוד עברה נקי (או rollback בוצע והוסבר).
- [ ] flag_guard PASS · verify ירוק · פיד טרי.
- [ ] חשבון שטוח מול Sierra-UI · iMac=Sim.
- [ ] תווית-07-20 מחזיקה (שלב 4).
- [ ] מייקל: "מאשר חימוש" ב-LIVE_CHANNEL.

## שלב 8 — במהלך היום (cursor מוביל מעקב, אפס-שינויים תוך-כדי מסחר)

### הגדרת-ההצלחה של מייקל (07-21 07:54): "לא מספיק שיירה בלייב"
לייב-נכון = **(א)** סוג-יום מזוהה נכון · **(ב)** סטופ מבני נכון (לא כמו #420) · **(ג)** ניהול-סיכון
פעיל (S6 protective + OCO + cap) · **(ד)** התבנית בכיוון רווח מרגע-הכניסה — נמדד, לא מקווים.

**לכל עסקת-לייב היום — 4 בדיקות תוך-דקות מהכניסה (cursor):**
- [ ] **תווית:** `day_type_at_entry` בעסקה == `classify_replay` באותו רגע == מה שמייקל רואה בצ'ארט.
- [ ] **סטופ:** ההוראה ב-Sierra = קצה-המבנה של התבנית +6T (לא בתוך-המבנה). חריגה = ראיה מיידית + FLATTEN אם מייקל פוסק.
- [ ] **יעדים/כמות:** T1/T2/T3 + חוזים לפי טבלת-סוג-היום (`targets_table.py`) — לא ברירת-מחדל גנרית.
- [ ] **איכות-כניסה (ד'):** רישום MAE/MFE — כמה הלך נגדנו לפני שהלך איתנו. עסקה שנפתחת ומיד
      נלחצת לסטופ = כניסה מאוחרת/מיקום-שגוי → ראיה ל-EOD (zone_limit/location עשו את עבודתם?).
- [ ] 16:35: `classify_replay?date=2026-07-21` → FORMING/PROVISIONAL תקין.
- [ ] **17:35 (נעילת-IB): `ib_source=sierra_tpo` ו-IB=מה שבצ'ארט-Sierra (±טיק)** — הבדיקה הקריטית של אתמול.
- [ ] מעקב `gateway/decisions` — כל חסימה עם reason; כל ירי מול עץ-ההחלטות
      (`docs/reference/SYSTEM_DECISION_TREE_VISUAL.html`). **וגם ההיפך:** מנצח שנחסם → לתעד איזה שער ולמה.
- [ ] שינוי-קוד תוך-כדי-מסחר = אסור. תקלה חיה → FLATTEN_ACCOUNT (לא op=EXIT) → עצירה → אבחון.

**גבולות-כנות (לא להבטיח מה שאין):** S6 היום = protective בלבד (השלמת-BE + התרעות; לא ניהול-עסקה
מלא — זה ה-OCO והטבלה). זיהוי-S2 (allow-lists) עדיין קורא תווית-ישנה (G2/G3 בסים, לא היום).
"רווח מובטח" לא קיים — מה שמובטח: תנאי-הכניסה נאכפים, הסטופ מבני, והכל נמדד ומתועד לאותו ערב.

## שלב 9 — אחרי הסגירה: המשך §1 לפי סדר-סיכון
I רקונסיליאציה (Task#6, trade_fills ריק — חוסם-אמון) → H ביצוע→Sierra → C/D סטופים על עסקאות-היום → F/G → K.

---
**מסמכי-עוגן:** עץ-החלטות `SYSTEM_DECISION_TREE_VISUAL.html`+`_LIVE.md` · ביקורת `CC_AUDIT_TS_REPAIR_2026-07-20.md` ·
דגלים `FLAG_RULING_2026-07-20.md` · פרוטוקול `PRE_TRADE_PROTOCOL.md`.
