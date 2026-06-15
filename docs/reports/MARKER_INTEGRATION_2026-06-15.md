# MEMS26 · שילוב כלי-הסימון + חידוד-תבניות + מוכנות — 2026-06-15

**מקור:** מבוסס על `TRADE_PLACEMENT_MARKER_2026-06-12.html`, `HANDOFF_NEXT_CHAT_2026-06-15.md`,
`PATTERN_EOD_2026-06-12.md`, `DESIGNS_2026-06-12.md`, אודיט-משטחים בקוד החי, ובדיקת-מערכת חיה (Rule 5 — פלט-גולמי).
**סטטוס:** הצעה (design). תיקוני trading-logic דורשים שער-Michael. שלב-0 (v3 של הכלי) כבר נבנה ואומת.

---

## חלק א — שילוב הכלי למערכת (כל עסקה מצטרפת אוטומטית)

### מצב נוכחי של הכלי
כלי-עצמאי (offline). `const DATA={bars,cvd,trades,levels}` **מוטמע קפוא** בקובץ (snapshot מ-06-11/06-12,
14 עסקאות בלבד ל-06-12 — חסרות 80/81). הסימונים (`marks`) לפי `trade.id` ב-**localStorage** בלבד; ייצוא =
הורדת `mems26_placement_marks.json`. **בעיה:** הנתונים לא חיים, והסימונים לא חוזרים למערכת.

### משטחים קיימים (אומתו בקוד — מנוף ל-reuse, לא לבנות מחדש)
| משטח | קובץ | מצב | שימוש בשילוב |
|---|---|---|---|
| Trades API | `backend/v9/api/v9/trades.py` (`/api/v9/trades`, `/recent`, `/active`, `/{id}`) | חי | מקור-העסקאות במקום `DATA.trades` |
| `v9_trades.quality` (JSON) | `backend/v9/db/models/trades.py:51` | קיים (W12) | **יעד-אחסון לדירוג/סימון פר-עסקה** |
| חתכי-כיול אינדקס | `trades.py:62-64` `day_type_at_entry / pattern_id_at_entry / session_at_entry` | חי | חיתוך per-pattern×day-type |
| Markers | `backend/v9/api/v9/markers.py` POST+GET, `payload` JSON | חי — **אך gated ב-`verify_bridge_token`** | אופציה ב' לאחסון; דורש פתרון-auth ל-UI |
| צ'ארט-דאטה | `bars5min` · `cumulative_delta/current` · `key_levels` | חי — **3 endpoints נפרדים** | צריך **aggregator** אחד |
| TradeMarkerOverlay | `frontend/.../chart/TradeMarkerOverlay.tsx` | מחווט ב-`ChartArea.tsx` (✓/✗ על הצ'ארט) | T7 כבר עובד — לעדכן handoff |
| TradesTable / tradeStore | `frontend/.../components/trades/*`, `stores/tradeStore.ts` | מחווט (מציג pnl+outcome) | נקודת-כניסה "פתח בכלי-הסימון" |

> הערה: `SYSTEM_INDEX.md` (06-05) מסמן חלק מרכיבי-ה-trades כ-orphan — האינדקס **מיושן**; grep-טרי מראה
> ש-`TradesView` מייבא אותם. להריץ `python3 scripts/gen_index.py` לרענון.

### הצעת-שילוב — 4 שלבים
**שלב 0 — ✅ בוצע (`TRADE_PLACEMENT_MARKER_v3_2026-06-15.html`):** הצלחה/כישלון ברורים + רשימה-נבחרת מסוננת.
- כל פריט ב-dropdown: `✓ #66 TLB LONG · +$293` / `✗ #69 ZLR SHORT · -$488` (אייקון+צבע+PnL).
- שורת-סינון: **הכל · ✗ הפסדים · ✓ רווחים · 🚫 לא-להיכנס · ✎ מסומנות** + מונה `נראות/סה"כ`.
- צ'יפ-תוצאה צבעוני ב-meta. אומת: `node --check` עבר; פילטר-הפסדים מבודד נכון 69/70/74/77.
- *מגבלה:* עדיין על ה-snapshot הקפוא (4/6 הפסדי-שישי). שלב-1 פותר.

**שלב 1 — הזנה חיה (כל עסקה מצטרפת):** endpoint-אגרגטור חדש
`GET /api/v9/chart/replay?date=YYYY-MM-DD` → `{bars, cvd, levels, trades, day_type}` (מאחד את 3 ה-endpoints
הקיימים + trades-של-היום). הכלי טוען `DATA` מ-fetch במקום הטמעה. ⇒ אוטומטית **כל** עסקה (כולל 80/81 והבאות) ברשימה.

**שלב 2 — שמירת-סימונים חזרה ל-DB (לא רק localStorage):**
- יעד מומלץ: `v9_trades.quality` JSON פר-עסקה: `{review:{verdict:"would_not_enter"|"ok"|"size_down", corrected:{entry,stop1,stop2,stop3,t1,t2,t3}, note, by:"michael", ts}}`.
- endpoint חדש `POST /api/v9/trades/{id}/review` (auth ל-UI, **לא** bridge-token — זו המגבלה שיש לפתור; `markers.py` כולו gated ל-bridge).
- שלב-2 הופך את הסימונים לנכס-כיול שאילתי (`SELECT ... WHERE quality->'review'->>'verdict'='would_not_enter'`).

**שלב 3 — חיבור לדשבורד החי:** כפתור "פתח בכלי-הסימון" בשורת-TradesTable; הצגת-verdict על TradeMarkerOverlay
(מסגרת מקווקוות = "לא-הייתי-נכנס"). אופציונלי — להגיש כ-`mcp__cowork__create_artifact` (דף חי שמושך מה-API בכל פתיחה).

---

## חלק ב — איך הסימונים הופכים לתיקוני-מערכת (marks → fixes)

הכלי לוכד 7 רמות + דגל + הערה. כל אחד ממופה ליעד-תיקון קיים (D-items מ-`DESIGNS_2026-06-12.md`):

| מה Michael מסמן | הופך ל… | יעד בקוד/קונפיג |
|---|---|---|
| 🚫 **no_entry** + הערת-"למה" | סט-אמת מתויג ל-**וטו** | **D3** trend-veto (REVERSAL) · **D4** REACTIVE position — ה-replay חייב לשחזר את ה-no_entry בלי להרוג רווחים |
| **stop1** (התחלתי) | תא בטבלת-stop | **D8** טבלת stop/target פר-תבנית×day-type + `config/stop_anchors.yaml` + `MEMS_MIN/MAX_RISK_POINTS` |
| **t1 / t2 / t3** | תאי-יעד | **D8**; t2 מזין `expected_t2_r_mult` (`pre_fire_validator.py`) |
| **stop2** (אחרי T1) | לוגיקת-BE/מבני | `STOP_AFTER_T1_STRUCTURAL` (D-002) |
| **stop3** (אחרי T2) | trail | `RUNNER_TARGETS_V1` BE+0.5R (`trade_manager/manager.py`) · T3-trail (Trend) |
| **note** | רציונל-הכלל + פיצ'ר חדש | מקור ל-feature (למשל "רחוק מ-POC", "לתוך בר-טיל") שנכנס ל-detector |

**לולאת-הכיול (החזון "אני הופך לקונפיג פר-תבנית×יום×משטר"):**
1. Michael מסמן N עסקאות (דגש: הפסדים + no_entry).
2. הסימונים → JSON (שלב-0) או DB (שלב-2).
3. **reducer** מצרף ל-(א) טבלת-stop/target מועמדת [pattern×day_type×regime], (ב) סט-וטו מתויג.
4. **replay 06-10..06-12** עם המועמד → מדד: כמה מה-no_entry-הפסדים נחסמו **בלי** לחסום את 5 פגיעות-ה-T2.
5. שער-Michael → דגל default-OFF → SHADOW → אימות → LIVE.

---

## חלק ג — עסקאות-שישי שנכשלו: מה כבר עשינו לחידוד ההבחנה

**שישי 06-12 (shadow):** 23 עסקאות, 17W/6L, נטו **−$329.50** (אומת ב-DB). מול חמישי 06-11: 34 עסקאות / **−$1,764**.
6 ההפסדים מתרכזים ב-2 אשכולות + 2 בודדות:

| id | תבנית | כיוון | $ | שורש | מה כבר עשינו (חי בשישי — עם ראיית-לוג) | תיקון-ממתין (שער-Michael) |
|----|------|------|---|------|----------------------------------------|----------------------------|
| 69 | ZLR | SHORT | −487.5 | נגד V-recovery בן-שעה; stop משותף 7429.75 | **RISK_CAP_SIZE_DOWN** הוריד ל-1 חוזה (32.5pt>15) → הפסד ⅓ מ-3-חוזים · **LOSS_BREAKER** חסם ZLR ×8 מ-19:20 | **D3** trend-veto היה מדלג לגמרי |
| 70 | ZLR | SHORT | −581.25 | נכנס 09:50 ומת על בר-הטיל (+43.5pt, mfe=0) | **RISK_CAP_SIZE_DOWN** (38.8pt>15→1 חוזה) | **D3** + **D5** cluster-guard (stop זהה ל-69) |
| 74 | INITIATIVE_S | SHORT | −60 | stop צר 4pt, רעש | sizing שפוי (S2 4–11pt) הגביל נזק | — (קטן; בתחום-הסיבולת) |
| 77 | REACTIVE_S | SHORT | −326.25 | נגד-מהלך באמצע-רנג' | — | **D4** REACTIVE position-context |
| 80 | REACTIVE_L | LONG | −266.25 | LONG בראש-רנג' (שיא-יום נקבע שעתיים קודם) | — | **D4** (>80% עליון-רנג' → skip/half) |
| 81 | REACTIVE_L | LONG | −213.75 | LONG בראש-רנג', mfe 0.5pt | — | **D4** |

**ראיית-לוג גולמית (`/tmp/backend.err.log`, 06-12, IDT):**
```
16:35 RISK_CAP_SIZE_DOWN: GB100 SHORT risk=48.5pt > cap=15pt (CONT→1 contract)
17:45 RISK_CAP_SIZE_DOWN: ZLR SHORT risk=32.5pt > cap=15pt (CONT→1 contract)   ← id69
17:50 RISK_CAP_SIZE_DOWN: ZLR SHORT risk=38.8pt > cap=15pt (CONT→1 contract)   ← id70
17:30 RISK_CAP_SKIP: HFE LONG risk=48.5pt > cap=20pt (REV→SKIP)
17:55 RISK_CAP_SKIP: HTLB LONG risk=67.5pt > cap=20pt (REV→SKIP)
18:35 GIANT_BAR_STOP: VEGAS LONG anchor=7387.50 (57.2pt) → intra-bar stop=7438.75 (6.0pt)
19:20 PATTERN_LOSS_BREAKER: ZLR blocked for session (2 losses today >= 2)   (×8 עד 22:25)
```

**מסקנה ישרה (Rule 1):** ההפסדים **לא** היו כשל-מנגנון אלא **כשל-תיאום-מגמה**. אותם stops/targets בדיוק
הניבו **5 פגיעות-T2 עם-המגמה** (id65/66/78/85/86, Σ≈+14.65R — האימות-החי הראשון של `RUNNER_TARGETS_V1`).
מה ש**עשינו** (חי, מאומת-לוג) ריכך: caps הורידו את אשכול-ZLR לחוזה-בודד (הפסד −$1,069 במקום ~−$3,200),
ו-LOSS_BREAKER חסם כל ZLR נוסף. מה ש**טרם** עשינו (ממתין-שער): **D3 trend-veto** (היה חוסך ~$1,069, 3 ימי-ראיות),
**D5 cluster-guard**, **D4 REACTIVE-position**, **D8 stop/target table**. המנוף בעל-יחס-העלות/תועלת הגבוה: **D3**.

---

## חלק ד — בדיקת-מוכנות (06-15, ~09:46 IDT = ~01:46 CT, טרום-RTH)

| ציר | ממצא (גולמי) | מצב |
|---|---|---|
| Host/migration | `MacBarg.local` · backend+frontend+bridge חיים כאן · runbook קיים אך **migration לא בוצע** | 🟡 להחליט |
| Mode | `v9_trades` שישי כולן `shadow` | 🟢 בטוח |
| /health | `200`, `5ms`, uptime 2.6d, `v9_mounted:true` | 🟢 |
| טעינת-דגלים | backend עלה Fri 18:58:19 — **שנייה אחרי** כתיבת `.env` (18:58:18) ⇒ דגלי-anchor-trial טעונים בתהליך | 🟢 ללא-restart |
| דגלים | `RUNNER_TARGETS_V1·PATTERN_RISK_CAPS·GIANT_BAR_STOP_V1·S2_VOL_ADAPTIVE·PATTERN_LOSS_BREAKER·STOP_ANCHORS_V2·S1_PROVISIONAL_DAYTYPE = 1` | 🟢 |
| Standing-decisions OFF | `S2_REQUIRE_COT_AMT·LAYER0_CHOP_GATE·S2_CHOPPINESS_GATE` — אף-אחד לא force-enabled | 🟢 |
| Bridge | localhost בלבד, push פעיל, **0 כשלי-push** | 🟢 |
| Bar recency | בר אחרון 09:45 מול now 09:47 (פיגור 2 דק׳) | 🟢 |
| Regression | 6 הקבצים → **27 passed, 0.23s** | 🟢 |
| **day_type** | כעת `UNKNOWN/NA/PENDING` (איפוס טרום-RTH — צפוי 6.7 שעות לפני 08:30 CT) | 🟠 **WATCH** ב-RTH+30 (09:00 CT / 17:00 IDT) — חייב להתהפך ל-day_type אמיתי+`PENDING`, לא להישאר UNKNOWN כמו 06-09 |
| נתונים | gap-ids 64/72/76 חסרים ב-`v9_trades` (I-32) | 🟠 לאימות-CC |

**שורת-תחתית:** המערכת **GO-מותנה** ליום-מסחר ב-shadow. שני דברים לעקוב: (1) day_type ב-RTH+30, (2) I-32.

---

## חלק ה — להכרעת Michael (שערים — לא נוגעים בלי אישור)
1. **85 קומיטים לא-דחופים** (branch `stabilize/...`, `0 behind`) — לדחוף מה-Mac?
2. **Migration למכונת-מסחר ייעודית** — בוצע/להריץ עכשיו? (כרגע ה-Mac הזה הוא ה-host החי).
3. **איזה D-item השבוע** — הנתונים תומכים **D8 (stop/target) → D3 (trend-veto)**.
4. שלב-1/2 של השילוב (הזנה-חיה + שמירת-סימונים ל-DB) — לאשר לבנות?
