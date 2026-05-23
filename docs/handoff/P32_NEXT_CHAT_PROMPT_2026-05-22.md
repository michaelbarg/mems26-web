# MEMS26 P31 → P32 — Next Chat Handoff (2026-05-22 11:00 IL)

> **קלוט את כל ה-prompt לפני שאתה עונה משהו.**  
> אל תפתח Sierra / bridge / כלום עד שהבנת את כל ה-context.

---

## 0. ברכה + פרוטוקול

- אמור **שלום / בוקר טוב / צהריים טובים / ערב טוב** לפי הזמן.
- קרא לפני כל פעולה:
  1. `CLAUDE.md` (root)
  2. `.cursor/rules/mems26-pre-live-protocol.mdc`
  3. `docs/handoff/P31_TASK_BOARD.md` — single source of truth
  4. `docs/reports/PROMPT_P31_SYSTEMS_FIRING_STRATEGY.md` — מצב 6 המערכות
- **ה-bridge הוא local-only.** `CLOUD_URL=http://localhost:8000`. אל תיגע ב-LaunchAgent / DLL.
- **אל תריץ `scripts/start_all.sh`, `npm run dev` בלי בקשה מפורשת.**
- **commits — רק אם Michael מבקש מפורשות.**

---

## 1. מצב שירותים (snapshot 2026-05-22 11:00 IL)

| רכיב | סטטוס | PID |
|------|--------|-----|
| Backend `:8000` | 🟢 | 10845 (restart ב-11:00 בערך) |
| Frontend `:3000` | 🟢 | 26120 |
| Bridge | 🟢 | כל 12 הזרמים, §9 TZ workaround פעיל |
| S4 Woodies | 🟢 ירה | ~1,230 trades ב-DB |
| S2 5-Min | ⏳ לא ירה עדיין | ממתין ל-RTH + AMT לא 0 |
| S3 Footprint | Observer בלבד | per D-082 LOCKED |

---

## 2. מה הסשן הנוכחי (2026-05-22) עשה

### Commits שנסגרו (2 חדשים)

```text
2bc6796  fix(types): SYSTEM_ROLES — S3=observer per D-082, S1=observer per Matrix
dcae75d  fix(footprint): COT session reset + AMT 90-min rolling [P31-STRAT-S3 #2+#3]
```

### מה בוצע

**Bug #3 — COT לא reset יומי (CC):**
- `backend/v9/systems/footprint/footprint_system.py::hydrate()` — COT עכשיו מאופס בתחילת session Globex (18:00 ET). לפני: נצבר ל-−144K. עכשיו: יומי בלבד.
- `backend/v9/common/session_classifier.py` — נוסף `current_session_open_utc()` helper.
- 4 טסטים חדשים: `tests/v9/systems/test_footprint_cot_session.py`

**Bug #2 — AMT per-bar → 90-min rolling (Cursor):**
- `backend/v9/systems/footprint/footprint_system.py::_update_flow()` — נוסף `_amt_window` list (18 ברים = ~90 דק'). לפני: AMT=0.0 תמיד (per-bar instant). עכשיו: rolling average.
- 8 טסטים חדשים: `tests/v9/systems/test_footprint_amt_rolling.py`
- **12/12 pytest PASS**

**types.ts (Cursor):**
- `frontend/v9/src/v9/types/index.ts::SYSTEM_ROLES` — S1=observer, S3=observer. לפני: S1=firing (שגוי), S3=observer (בכיוון הנכון אבל לא עם comment). עכשיו: נכון לפי D-082 + D-086 + Master Matrix.

**Canvas ויזואלי (Cursor):**
- `~/.cursor/projects/Users-michael-Downloads-mems26-web-git/canvases/firing-systems-decision-trees.canvas.tsx` — עצי החלטה ויזואליים לכל 6 המערכות, מצב בגים, המלצות.

### מה לא עובד עדיין (ממצאים חדשים)

| ממצא | חומרה | מקור |
|---|---|---|
| **S2 לא ירה** (0 trades מאז תמיד) | 🔴 | AMT עדיין 0 לאחר restart — צריך RTH לוודא |
| **S6 direction-aware bug (RCA-1)** | 🔴 pre-LIVE blocker | `_system_agrees(sid=6)` עיוור לכיוון, 154/200 disagree שגוי |
| **9 patterns של Woodies** — targets לא סקרנו | 🟡 | ZLR מאומת (8/12/24 ticks). שאר 8 לא |
| **S2 4-bar pattern conditions** — לא מאומת ב-RTH | 🟡 | תלוי ב-AMT>0 + 4-bar pattern ב-Sierra |

### מה לא לגעת בו (החלטות LOCKED)

| נושא | LOCKED | למה |
|---|---|---|
| `footprint_system.py::_fire()` עם `if mode=="LIVE"` | D-082 + D-086 | זה safety net, לא באג. S3=Observer |
| Stops / T1/T2 של patterns | — | אין בסיס data לשנות. SHADOW soak ראשון |
| Trailing stop / partial exit / time stop | — | DEMO, לא pre-LIVE |
| ZLR/GB100 "כיבוי" (WR נמוך) | — | n<50 RTH, מדגם זעיר |

---

## 3. הצעד הבא — לפי עדיפות

### 🔴 Priority 1 — מייד (pre-LIVE blocker)

**RCA-1: תיקון Killzone S6 direction-aware**

- **קובץ:** `backend/v9/services/trade_context.py:249-256`
- **הבאג:** `_system_agrees(sid=6)` מחזיר `True` לkillzone high ו-`False` לlow **בלי להסתכל על direction**. 154/200 trades מוצגים כ-S6 disagree שגוי.
- **התיקון (4 שורות):**

```python
# לפני:
        if edge == "high":
            return True
        if edge == "low":
            return False

# אחרי:
        if edge == "high":
            return d == "SHORT"
        if edge == "low":
            return d == "LONG"
```

- **regression test:** edge=high + LONG → False, edge=high + SHORT → True, edge=low + LONG → True, edge=low + SHORT → False, blob ריק → None.
- **קובץ RCA מלא:** `docs/reports/PROMPT_P31_CONFLUENCE_FILTER_RCA.md`
- **זמן:** 30-45 דק' כולל test
- **UAT:** אחרי restart, פילטר "All systems agree" ב-`/trades` יחזיר 40-150 trades (לא 3).

### 🟡 Priority 2 — בצ'אט הזה (ממתין ל-RTH)

**UAT: S2 יורה?**

- **מתי:** אחרי 09:30 ET (16:30 IL), עם Sierra + Bridge פעילים.
- **הוראות:** `docs/handoff/agents/CC_UAT_S2_AMT_PROMPT.md`
- **בדיקה מהירה:**

```bash
curl -s http://127.0.0.1:8000/api/v9/footprint/current | python3 -c "
import sys,json; d=json.load(sys.stdin)
print('cot:', d.get('cot'), '| amt:', d.get('amt'))"

grep "FiveMin.*FIRE" /tmp/backend.log | tail -5

sqlite3 data/mems26_local.db \
  "SELECT COUNT(*) FROM v9_trades WHERE firing_system=2 AND date(entry_ts)='2026-05-22';"
```

- **קריטריון:** `amt > 50` ב-RTH, לפחות 1 trade מ-S2.
- **אם S2 לא יורה:** לדווח ב-`docs/reports/PROMPT_P31_S3_S2_UAT_RESULT.md`.

### 🟢 Priority 3 — לאחר RCA-1 וUAT

- סקירת 9 patterns של Woodies (stop/T1/T2 לכל אחד) — `P31-STRAT-4`
- `P31_NEXT_CHAT_CHART_POC_DAYTYPE.md` — CVD alignment, POC lines, Day Type → S2 fire

---

## 4. Compass Artifact — הקשר אסטרטגי

מסמך ש-Michael קיבל (`compass_artifact_wf-09931f85...`) קובע:
- **S2 V3.3 לא יורה בLIVE** — אין נוסחאות מספריות ל-T1/T2/T3 ב-11 patterns (רק "momentum push" / "POC/VWAP" — לא נומרי).
- **4 patterns של Zohar (Reactive/Initiative LONG/SHORT)** לא קיימים ב-S2 V3.3 כלל.
- **המלצת Compass:** ATR-multiple stop (1.5-2.0× ATR-14 על 5-min) + hybrid targets.
- **ההמלצה שלי:** לא לממש עכשיו. SHADOW soak ראשון, אז להחליט.

**עקרון על:** לא לשנות stops/targets/patterns עד שיש SHADOW data. כל שינוי עכשיו מעוות את ה-baseline.

---

## 5. Constraints — אסור / חובה

### אסור
- 🚫 לשנות `CLOUD_URL` / LaunchAgent / Bridge
- 🚫 `git push --force`
- 🚫 לשנות trading logic / risk surface בלי שאלת Michael
- 🚫 לשנות stops/targets/patterns לפני SHADOW data
- 🚫 לתקן Bug #1 (`if mode=="LIVE"` ב-S3) — זה D-082 safety net
- 🚫 לכבות ZLR/GB100 בלי n≥50 RTH trades

### חובה
- ✅ לקרוא `P31_TASK_BOARD.md` לפני כל פעולה
- ✅ לעדכן board אחרי כל שינוי (timestamp + מי + מה + מה נשאר)
- ✅ לעצור ב-phase gate
- ✅ 4 צירי UAT (Quality / Recency / Cardinality / Latency)

---

## 6. Pointers מהירים

| נושא | קובץ |
|---|---|
| RCA-1 fix (S6) | `backend/v9/services/trade_context.py:249-256` |
| RCA-1 דוח + tests | `docs/reports/PROMPT_P31_CONFLUENCE_FILTER_RCA.md` |
| UAT S2 prompt | `docs/handoff/agents/CC_UAT_S2_AMT_PROMPT.md` |
| מצב 6 מערכות | `docs/reports/PROMPT_P31_SYSTEMS_FIRING_STRATEGY.md` |
| Canvas ויזואלי | `~/.cursor/projects/.../canvases/firing-systems-decision-trees.canvas.tsx` |
| Task board | `docs/handoff/P31_TASK_BOARD.md` |
| D-082 (S3 Observer) | `docs/reports/P30_DECISION_D086_S3_FIRING.md` |

---

## 7. שורה אחת

**RCA-1 (S6 direction-aware, 4 שורות + test) הוא ה-pre-LIVE blocker הבא. אחריו UAT ש-S2 יורה ב-RTH. אל תשנה stops/patterns עד SHADOW data. עדכן לוח אחרי כל שינוי.**
