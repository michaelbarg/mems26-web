# ✅ צ'קליסט — חיתוך "SHADOW מ-0 היום" · 2026-06-05

מקרא: ✅ בוצע ואומת · 🔄 בביצוע (CC) · ⬜ טרם · ⏳ ממתין להחלטת/אישור Michael.
מקור-אמת: `STATUS_BOARD.md`. צ'קליסט זה = מעקב-על לכל נושאי הסשן.

---

## חלק 0 · בוצע בסשן הזה (Cowork — אבחון, אימות, הכנה)
- [x] ✅ **B-13 אובחן** — המחירים הפנטומיים (7341/7365.75) = ברים אמיתיים ישנים מ-6/5 ששרדו
  את המיגרציה; הגיעו ל-S2 כי אין שומר-staleness בכניסה + S2 נשאר חמוש אחרי הסגירה. (API חי + קוד)
- [x] ✅ **B-13 הוצלב מול CC** — exact-tick match (psql של CC) + `bars.py` future-guard-only + `_route_bar` last_valid_bar.
- [x] ✅ **B-11 אומת חי** — הגשר **משדר** (live_price 321ms, CVD 2.6s); ה-OFFLINE שקרי; `rowid` ב-L82/L204 אושר.
- [x] ✅ **B-14 אומת חי** — CVD pane מכוון (נשאר); כפילות-5דק' = נתיב history-backfill ב-render; הדאטה נקייה.
- [x] ✅ **G1 §0 VERIFY-FIRST** — 7/7 עסקאות עם killzone+daytype+woodies; `cross_context`=מערך[0].systems → **promote-able**.
- [x] ✅ **Session TZ אומת** — 08:30–15:00 שיקגו = 09:30–16:00 ET; `entry_ts` ב-+03:00 (באג); `bars.py:33` סוגר שעה מאוחר.
- [x] ✅ **S3 mute** — מנגנון קיים `S3_MUTE` (env flag, כרגע לא-מוגדר → S3 יורה).
- [x] ✅ **פרומפטים הוכנו** — B-11 · B-13 diagnose · B-13 remediation · G1 work-plan · cutover · **mega closure**.
- [x] ✅ **מגה-פרומפט נשלח ל-CC** (Michael).

---

## חלק 1 · STREAM A — קריטי · חוסם את ה-start (CC, gated)
- [ ] 🔄 **A1 · שומר-staleness בכניסה** (B-13 D2) — `bars.py` POST `/5min` + שאר POST שמריצים `_route_bar`; regression בר-6/5→נדחה.
- [ ] 🔄 **A2 · session 08:30–15:00 שיקגו** (B-13 D3) — ירי חסום מחוץ-לחלון בכל המערכות/modes · מעבר→OVERNIGHT ב-15:00 · `entry_ts` UTC · אמת S3/S4.
- [ ] 🔄 **A3 · G1 עמודות + אכלוס** — `day_type_at_entry`/`pattern_id_at_entry`/`session_at_entry` + migration + populate-at-entry (בלי backfill) · litmus NULL.
- [ ] ⏳ **A4 · gate** — `alembic upgrade` + כל ה-regressions ירוקים (RED→GREEN, raw) → **STRATEGIC-STOP לאישור Michael.**
- [ ] ⏳ **A5 · (אחרי אישור)** — reset ל-0 (`v9_trades`+בארים+`v9_five_min_state`) → restart עם `S3_MUTE=1` → אימות → start ריצה.

### החלטות Michael ב-Stream A
- [ ] ⏳ אישור ערכי **`STALE_PRICE_BAND`** + סבילות-staleness (CC יציע, אתה מאשר).
- [ ] ⏳ אישור **STRATEGIC-STOP** ב-A4 לפני ה-reset.

### אימות נקי לפני "ריצה מאומתת" (A5)
- [ ] soak מקבילי ≥10ד' · 0 errors / 0 deadlocks
- [ ] אין `firing_system=3` (S3 muted)
- [ ] אין ירי מחוץ ל-08:30–15:00 CT
- [ ] עסקה חדשה עם 3 עמודות-G1 מאוכלסות
- [ ] ספירות-בארים נקיות (`COUNT/MIN/MAX` לכל טבלה) · S2 mode=OVERNIGHT אחרי 15:00

---

## חלק 2 · STREAM B — תצפיתיות (כדי לבטוח בלוח, low-risk)
- [ ] 🔄 **B1 · B-11** — `bridge_inspector` `rowid`→`{ts_col}` (L82+L204) + regression revert→RED; הלוח יפסיק להראות OFFLINE שקרי.
- [ ] ⬜ **B2 · day_type=UNKNOWN** — לאמת אם לגיטימי (RTH סגור, +229 דק') או רגרסיית B-8; דווח root לפני תיקון ב-classifier.

---

## חלק 3 · STREAM C — עיצוב/UX · מקבילי, **לא חוסם** (סוכן-frontend נפרד)
- [ ] ⬜ **C1 · B-14** — תיקון כפילות-5דק' (history-backfill ב-`ChartV5b`); CVD נשאר; regression RED→GREEN.
- [ ] ⬜ **C2 · Build Status — השלמת P0** — רינדור `pre_fire_validator` + `risk_checks` + Day-Type Matrix S4 + חיווט S5/S6 (הבסיס BuildTreeView כבר committed).
- [ ] ⬜ **C3 · Trades Frontend Phase 1** — 8 פריטים (ET-date · Edge Matrix · target-dist · equity · price/time-axis · stop-behavior · scratch/BE); killzone/day_type ינוקה-gating כש-G1 ינחת.

---

## חלק 4 · Cowork — הצלבה אחרי ש-CC מחזיר
- [ ] ⬜ הצלבת כל פלט-CC מול קוד/git/API (Rule 5 — לא לקבל "confirmed" בלי raw output).
- [ ] ⬜ עדכון `STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html` פר-שלב עם finding+fix+verification.

---

## הקשר — בוצע בסשנים קודמים (✅, לתמונה מלאה)
- [x] ✅ Postgres migration + constraints + soak (corruption נסגר מהשורש)
- [x] ✅ B-8 day_type inspector (`3820f3b`) · B-9 5min dup-merge (`355a54b`) · B-10 צ'ארט רציף (`1896a97`)
- [x] ✅ S4 YAML wiring (`e41ac5d`) · targets_stop render + de-trust (`66bd45c`)
- [ ] ⬜ residual לפני LIVE: סריקת SQLite-isms · shim ON CONFLICT · main.py SQLite fallback · Pipeline 5 (חוסם-LIVE)
