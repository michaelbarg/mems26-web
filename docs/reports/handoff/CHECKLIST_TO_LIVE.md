**Status:** living document — update as the project advances
**Last updated:** 2026-05-18
**Author:** Cursor multitask session

# CHECKLIST_TO_LIVE — actionable checklist from "right now" to LIVE

מסמך companion ל-prompt bodies. כאן רק checkboxes, gate criteria, ונקודות
החלטה. ל-prompt bodies מלאים → [`PROMPT_LIST_TO_LIVE.md`](./PROMPT_LIST_TO_LIVE.md).
ל-Gantt + exit criteria → [`GANTT_TO_LIVE.md`](./GANTT_TO_LIVE.md).
לתוכנית מלאה בעברית → [`../../../../../../.cursor/plans/mems26_to_live_b4d674ce.plan.md`](../../../../../../.cursor/plans/mems26_to_live_b4d674ce.plan.md).

> כללי עבודה: Diagnose first → read current code → smallest correct fix →
> regression test → 4 UAT axes (Quality / Recency / Cardinality / Latency)
> → דוח `docs/reports/PROMPT_<id>.md` לפני מעבר ל-P-ID הבא.
> כל שורה עם `🛑 STOP — ASK MICHAEL` היא נקודת החלטה. **לא ממשיכים בלי אישור.**

---

## מצב נוכחי (2026-05-18)

- Phase 0 backend data integrity: P27.5a/c/d/e/f/z GREEN, P27.5b DEFERRED (RTH).
- Bridge OFF (baseline שקט). Sierra OFF (סופ"ש).

---

## Phase 0 — Backend Data Integrity

- [x] **P27.5a** — bad bars ב-`/api/v9/chart/bars5min` (כולל slice hotfix)
  - GREEN: count=240, bad_count=0, last_ts=MAX(ts), latency<5ms.
- [x] **P27.5c** — `publish_threadsafe` ב-BarRouter
  - GREEN: tpo.bars_processed_today=2 אומת חי. 4 טסטים חדשים עוברים.
- [x] **P27.5d** — Footprint bar dispatch latency <50ms
  - GREEN: connection reuse, 0 dispatches >50ms ב-soak.
- [x] **P27.5e** — `5min.partial` topic ב-1Hz throttle
  - GREEN: throttle test עובר. אין subscribers עדיין (Phase 6).
- [x] **P27.5f** — `/api/v9/five_min/current` instance bug
  - GREEN: route uses `app.state.five_min_system`, 28/28 targeted tests passed, live endpoint HTTP 200, `hydrated=true`, latency<100ms. Report: `PROMPT_27_5F_FIVE_MIN_ROUTE_INSTANCE_FIX.md`.
- [ ] **P27.5b** — `live_price.age_ms < 60000` בזמן RTH ← **DEFERRED**
  - GATE: Sierra running + `bash scripts/uat_prompt_27_5b_live_price.sh` → 10/10 PASS.
  - UAT package ready: script + report template. Route reads DLL file directly (no bridge in path).
  - To run: `bash scripts/uat_prompt_27_5b_live_price.sh` during RTH with Sierra open.
- [x] **P27.5z** — רענון control board + handoff docs אחרי P27.5f
  - GREEN: `CHECKLIST_TO_LIVE.md`, `PROMPT_LIST_TO_LIVE.md`, `NEXT_CHAT_PROMPT_2026-05-17.md`, `SYSTEM_COMPLETION_CONTROL_BOARD.md` מסונכרנים (2026-05-18). P27.5b remains DEFERRED — docs sync does not depend on it.

**🛑 שער יציאה Phase 0 → 1:** Michael מאשר ש-6 ה-P27.5x ירוקים (כולל P27.5b חי).

---

## Phase 1 — Replay Smoke על נתונים נקיים

- [ ] **P28.1** — `scripts/run_stage.sh status_check` על backend חי
- [ ] **P28.2** — replay smoke מלא לפי `PROMPT28_REPLAY_SMOKE_RUN.md`
  - אימות: כל 6 המערכות (S1-S6) מפיקות פלט replay צפוי
  - אימות: אין שגיאות `pre_fire_validator`
- [ ] **P28.3** — עדכון `PROMPT28_REPLAY_SMOKE_RUN.md` עם post-fix evidence
- [ ] **P28.4** — `pytest tests/v9/ -q` ירוק מלא

**🛑 שער יציאה Phase 1 → 2:** Michael מאשר שה-replay נקי. אם כשל — לא ממשיכים ל-P29.

---

## Phase 2 — Scenario Pack (10 תרחישים)

לכל תרחיש: fixture/replay source, expected outcome, reason tree, PASS/FAIL מתועד.

- [ ] **P29.1** — Trending day
- [ ] **P29.2** — Balance / non-trend
- [ ] **P29.3** — Opening drive
- [ ] **P29.4** — S2 Five-Min setup
- [ ] **P29.5** — S3 Footprint setup
- [ ] **P29.6** — S4 Woodies setup
- [ ] **P29.7** — Killzone context change
- [ ] **P29.8** — TPO context / location
- [ ] **P29.9** — Missing / degraded data
- [ ] **P29.10** — Pre-fire / risk block
- [ ] **P29.report** — `docs/reports/PROMPT29_SCENARIO_PACK.md` עם 10/10

**🛑 שער יציאה Phase 2 → 3:** 10/10 עוברים עם reason trees ניתנים לביקורת. אין DEMO/LIVE writes.

---

## Phase 3 — Data Collection Package

הגדרה מדויקת של מה SHADOW יתעד.

- [ ] **P29.5.1** — schemas: bars + stream health
- [ ] **P29.5.2** — schemas: S1-S6 state snapshots
- [ ] **P29.5.3** — schemas: pre-fire decisions
- [ ] **P29.5.4** — schemas: gateway dry-run decisions
- [ ] **P29.5.5** — schemas: reason trees
- [ ] **P29.5.6** — schemas: lifecycle events
- [ ] **P29.5.uat** — UAT script: שעת replay → artifacts קריאים, אין שדות חסרים
- [ ] **P29.5.report** — `docs/reports/PROMPT29_5_DATA_COLLECTION.md`

**🛑 שער יציאה Phase 3 → 4:** Michael מאשר שכל schema מתועד, נכתב, נקרא וניתן לניתוח.

---

## Phase 4 — SHADOW Dashboard / UI (חובה לפני SHADOW)

- [ ] **P30.1** — החלטה: 6 קוביות מערכת — איפה ואיך
  - **🛑 STOP — ASK MICHAEL** (החלטת עיצוב)
- [ ] **P30.2** — אסטרטגיית volume overlay
  - **🛑 STOP — ASK MICHAEL**
- [ ] **P30.3** — Mode badge בולט (SHADOW/DEMO/LIVE)
- [ ] **P30.4** — Stale / degraded indicators בולטים
- [ ] **P30.5** — Fire/block reason tree נגיש ב-UI
- [ ] **P30.6** — Active trade / no active trade — חד
- [ ] **P30.spec** — `docs/design/SHADOW_DASHBOARD_SPEC.md`
- [ ] **P30.uat** — visual sanity + אין chart מקור חיצוני / watermark
- [ ] **P30.build** — build/lint ירוקים

**🛑 שער יציאה Phase 4 → 4.5:** Michael מאשר שהעיצוב לא חוסם פיקוח SHADOW.

---

## Phase 4.5 — שלושה שערי מוכנות SHADOW

### Accuracy Gate
- [ ] S1-S6: state נכון, טרי, עקבי מול source
- [ ] S2/S3/S4: setup/fire/block מדויק ב-replay
- [ ] S1/S5/S6: advisory context נכון, לא מסתיר degraded
- [ ] אין client-side filters לתיקון נתונים שגויים

### Decision Tree Gate
- [ ] עץ ההחלטה הפעיל ל-SHADOW: מלא ובר-ביקורת
- [ ] אין stub/delegated קריטי ב-S2/S3/S4 fire/block path
  - **🛑 STOP — ASK MICHAEL** לכל stub שמתגלה
- [ ] כל fire/block מייצר reason tree ניתן להבנה ב-UI
- [ ] **🛑 STOP — ASK MICHAEL** אם חלק מהעץ עוד לא מחובר

### Design Gate
- [ ] dashboard מראה ב-1 שנייה: mode, health, stale/degraded, reason, active trade, 6 systems
- [ ] לא נדרשת קריאת logs להבין מצב קריטי

- [ ] **P30.5.report** — `docs/reports/SHADOW_READINESS.md` עם GO/FIX

**🛑 שער יציאה Phase 4.5 → 5:** Michael מאשר **בכתב** שכל 3 השערים סגורים.

---

## Phase 5 — SHADOW Activation

- [ ] **🛑 STOP — ASK MICHAEL** לאישור מפורש בכתב
- [ ] להגדיר `MEMS26_MODE=shadow`
- [ ] לוודא gateway = record-only
- [ ] לוודא אין כתיבות ל-`trade_command.json`
- [ ] snapshot של `/api/v9/gateway/status` לפני ואחרי
- [ ] status check לפני/אחרי restart

**🛑 שער יציאה Phase 5 → 6:** יום SHADOW אחד מסתיים בלי קריסות ובלי כתיבות לא בטוחות.

---

## Phase 6 — SHADOW Soak

### 6.0 — Strategic Review מיד אחרי הפעלה
- [ ] לוודא שכל המידע הנדרש נאסף בפועל
- [ ] לוודא פורמט אנליטי, לא רק UI
- [ ] לזהות שאלות אסטרטגיות מהנתונים הראשונים
- [ ] `docs/reports/shadow/SHADOW_INITIAL_STRATEGY_REVIEW.md`
- [ ] רשימת fields שנאספים מול נדרשים
- [ ] דוגמאות fire / block / no-setup / degraded

**🛑 STOP — ASK MICHAEL:** continue / fix data collection / open strategic prompt

### 6.1 — Soak ≥10 ימי RTH
- [ ] EOD daily report
- [ ] מעקב trades / win rate / max DD / reason trees / pre-fire blocks
- [ ] עצירה מיידית על anomaly
- [ ] `docs/reports/shadow/SHADOW_SOAK_FINAL.md` עם GO/EXTEND/FIX

**🛑 שער יציאה Phase 6 → 7:** Michael מחליט: DEMO / extend / fix.

---

## Phase 7 — DEMO Activation

- [ ] **🛑 STOP — ASK MICHAEL** לאישור
- [ ] חיבור `DemoExecutor` ל-`trade_command.json` (Sierra Sim)
- [ ] הפעלת firing system אחת בלבד — מומלץ **S4 ראשון**
- [ ] מדידת latency end-to-end
- [ ] UAT מול Sierra Sim
- [ ] בדיקת `trade_command.json` writes
- [ ] בדיקת fills + risk caps
- [ ] `docs/reports/demo/DEMO_FIRST_ROUNDTRIP.md`

**🛑 שער יציאה Phase 7 → 8:** Round trip ראשון נסגר נכון, אין הפרת risk-cap.

---

## Phase 8 — DEMO Soak

- [ ] ≥7 ימי מסחר DEMO
- [ ] EOD: השוואת SHADOW expected vs DEMO actual fills
- [ ] תקציב slippage מאומת
- [ ] אין executor crashes
- [ ] `docs/reports/demo/DEMO_SOAK_FINAL.md`

**🛑 שער יציאה Phase 8 → 9:** Michael מחליט: LIVE pre-flight / extend DEMO.

---

## Phase 9 — LIVE Pre-Flight (CRITICAL SAFETY)

### Risk Caps
- [ ] Daily loss cap — tests בכיוון PASS + BLOCK
- [ ] Max trades cap — tests בכיוון PASS + BLOCK
- [ ] Max contracts cap — tests בכיוון PASS + BLOCK
- [ ] Time cutoff — tests בכיוון PASS + BLOCK

### Kill-Switch
- [ ] UI kill-switch מול Sierra Sim עם position פתוח
- [ ] API kill-switch
- [ ] Script kill-switch
- [ ] runbook recovery מתועד ומתורגל

### Alerts
- [ ] Slack: health / trades / risk blocks / kill-switch
- [ ] Slack test live

### Redundancy
- [ ] Bridge restart recovery
- [ ] Backend restart recovery
- [ ] DB lock recovery (נבדק ב-P27.5d — לאמת מחדש)

- [ ] **🛑 STOP — ASK MICHAEL** לחתימת UAT ידנית

**🛑 שער יציאה Phase 9 → 10:** UAT חתום + כל בדיקות בטיחות ירוקות.

---

## Phase 10 — LIVE Micro-Trial

- [ ] **🛑 STOP — ASK MICHAEL** לאישור בכתב לפני התחלה
- [ ] מערכת ראשונה: **S4 Woodies** בלבד
- [ ] חוזה מיקרו אחד (MES/MNQ/M2K — לפי החלטת Michael)
  - **🛑 STOP — ASK MICHAEL** לבחירת מכשיר
- [ ] שאר המערכות נשארות SHADOW
- [ ] real-time monitoring חי
- [ ] אישור kill-switch זמין לפני start
- [ ] **עצירה מיידית** בכל anomaly
- [ ] `docs/reports/live/LIVE_MICRO_TRIAL.md`

**🛑 שער יציאה Phase 10 → 11:** trade מיקרו אחד נסגר (או 0 עם הסבר תקין), אין anomaly, אין הפרת risk.

---

## Phase 11 — LIVE Expansion (הדרגתי)

- [ ] **🛑 STOP — ASK MICHAEL** אחרי S4 micro success
- [ ] להפעיל **S2 LIVE** (S4 ממשיך, S3 SHADOW)
- [ ] **🛑 STOP — ASK MICHAEL** אחרי S2 success
- [ ] להפעיל **S3 LIVE** (כל ה-3 LIVE)
- [ ] **🛑 STOP — ASK MICHAEL** להחלטת size scaling ב-S4
- [ ] SHADOW ממשיך לרוץ תמיד כ-oracle להשוואה
- [ ] EOD: השוואת SHADOW vs LIVE לילית
- [ ] `docs/reports/live/LIVE_DAILY_<date>.md`

**שער יציאה:** LIVE יציב עם SHADOW-vs-LIVE check לילי.

---

## Guardrails שחלים בכל הצ'קליסט

- **Bridge local-only:** `CLOUD_URL=http://localhost:8000` תמיד. כל push ל-render = הפסקה מיידית.
- **LaunchAgent:** `KeepAlive` תנאי על `SuccessfulExit=false`, `V9_DISABLE_WATCHDOG=1`.
- **No service bring-up** ללא בקשה מפורשת.
- **4 UAT axes** על כל endpoint שנגעו בו: Quality / Recency / Cardinality / Latency.
- **No silent failures** — `logger.warning`/`error` rate-limited, לא `debug`.
- **One thread at a time** — לסיים + דוח לפני P-ID הבא.
- **Diagnose → read code → smallest fix → regression test** — בלי קיצורי דרך.
- **Reports first** — לפני שעוברים P-ID, CC כותב/מעדכן `docs/reports/PROMPT_<id>.md`.

---

## נקודות החלטה קריטיות למיכאל (סיכום)

| # | מתי | החלטה |
|---|-----|--------|
| 1 | סוף Phase 0 | האם 6 ה-P27.5x מספיק נקיים ל-replay |
| 2 | סוף Phase 4 | אישור עיצוב dashboard |
| 3 | סוף Phase 4.5 | אישור **בכתב** של 3 השערים |
| 4 | סוף Phase 5 | לעבור ל-soak |
| 5 | סוף Phase 6.0 | continue / fix data collection / strategic prompt |
| 6 | סוף Phase 6.1 | DEMO / extend / fix |
| 7 | סוף Phase 8 | LIVE pre-flight / extend DEMO |
| 8 | סוף Phase 9 | חתימת UAT |
| 9 | תחילת Phase 10 | אישור LIVE micro + בחירת מכשיר |
| 10 | כל מערכת חדשה LIVE ב-Phase 11 | אישור הפעלה / scaling |

---

## איך לעדכן את הקובץ הזה

1. כל גמר P-ID → סמן `[x]`, כתוב 1-2 שורות ראיה חיה.
2. כל מעבר Phase → עדכן את "מצב נוכחי" למעלה + ה-`Last updated`.
3. כל החלטה של Michael → כתוב התאריך + ההחלטה בשורת ה-gate הרלוונטית.
4. אל תמחק היסטוריה — קווי `[x]` נשארים גם אחרי שעברנו Phase.
