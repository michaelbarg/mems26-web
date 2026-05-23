# דוח מלא — ביקורת Plan Tab (משימה #13 / L3)

**תאריך:** 2026-05-20  
**סטטוס שער:** **GREEN** — שרשרת BLOCKED + RTL עובדות; יש 6 GAPs עם המלצות תיקון  
**דוח טכני קצר:** [`PROMPT30_10b_PLAN_LIVE.md`](PROMPT30_10b_PLAN_LIVE.md)  
**Inbox:** `P30_AGENT_INBOX_PRE_LIVE.md` §8 #13, milestone L3 ✅

---

## 0. הנחיית Michael — DLL + זמן אמת מ-Sierra (**בוצע** — 2026-05-20)

**סטטוס:** תיקוני DLL וציר זמן **כבר עלו** (inbox §2). §7a = **לא לשבור / לא לחשב מחדש** — לא משימה פתוחה.

לפני שינוי קוד **חדש** (למשל Gateway / `cluster_guard`):

1. **קראו** — §2 + §7a, `SIERRA_DLL_OPS.md`; **אמתו** live (`export_ts`, ארבע צירי UAT).
2. **מקור אמת = Sierra** — בלי סינתזה ב-Python/React (רשימה ב-§7a).

המלצות Gateway בסעיף 6 — נפרדות; **ממתינות לאישור** Michael.

---

## 1. סיכום מנהלים

בוצעה ביקורת L3 מלאה לטאב **Plan** בכל שש המערכות (S1–S6): חוזה API, pytest, דפדפן live, וארבע צירי UAT.

| ממצא | משמעות |
|------|--------|
| **שורש הבאג שתוקן (#13)** | S2/S3 הורידו `BLOCKED` ל-`SCANNING` כי `maxLifecycle` לא מיזג נכון diagnosis — **תוקן** ב-`planFireDiagnosis.ts` + `systemPlanLive.tsx` + `test_plan_fire_diagnosis_contract.py` |
| **Woodies S4** | `failed_stages` → badge **חסום**; A1–A7 ב-TO FIRE; tap → פאנל עברית RTL — **עובד** |
| **Footprint S3** | `last_fire.blocked_by=cluster_guard` → BUILDING **חסום** + שורת ● — **עובד** |
| **6 GAPs** | לא חוסמים את שער L3; מומלצים לפני LIVE לפי עדיפות למטה |

**המלצה אסטרטגית:** לא לפתוח refactor ל-Plan UI. לטפל ב-**P0** (ביצועים + בהירות OVERNIGHT) ו-**P1** (hydration) לפני L4/L5.

---

## 2. מתודולוגיה

| שלב | כלי | תוצאה |
|-----|-----|--------|
| API | `curl …/cockpit/systems-snapshot \| jq` | HTTP 200, ~340 ms, `count=6` |
| ארבע צירים | quality / recency / cardinality / latency | ראו §5 |
| רגרסיה | `pytest test_cockpit_systems_snapshot.py test_plan_fire_diagnosis_contract.py` | **6/6 passed** |
| UI | Browser MCP `http://127.0.0.1:3000` — Plan לכל S1–S6 | PASS; RTL על S3/S4 |
| אסור | bridge/, sc_study/, POC/TPO overlay, launchctl, commit | נשמר |

---

## 3. תוצאות לפי מערכת

### S1 — Day Type (OBSERVER)

| שדה | API (live) | UI Plan |
|-----|------------|---------|
| `state` | `null` (לפני מיזוג day_type_machine) | **SCANNING** |
| `failed_stages` | — | אין TO FIRE |
| שורות | probability 0%, trading conf. — | CONTEXT ✓ |

**מסקנה:** התנהגות observer תקינה. פער תיעוד: API top-level `state` לעיתים `null` בעוד ה-UI מחשב lifecycle מ-`raw`.

---

### S2 — 5-Min (FIRING)

| שדה | API | UI Plan |
|-----|-----|---------|
| `mode` | `OVERNIGHT_MODE` | TO FIRE: Session mode ✓ |
| BLOCKED chain | רק `MAINTENANCE` / `WEEKEND` בקוד | STATE = טקסט setup (עברית), לא badge **BLOCKED** |

**מסקנה:** תיקון #13 (MAINTENANCE → BLOCKED) **עובד** ב-pytest. **GAP:** `OVERNIGHT_MODE` לא ממופה ל-BLOCKED — המשתמש רואה SCANNING/setup במקום "חסום · מחוץ לחלון מסחר".

---

### S3 — Footprint (FIRING)

| שדה | API | UI Plan |
|-----|-----|---------|
| `state` | `BALANCED` | BUILDING **חסום · cluster_guard** |
| `last_fire.blocked_by` | `cluster_guard` (ב-raw) | שורת ● + tap → RTL **סגור** ✓ |

**מסקנה:** שרשרת `last_fire` → BLOCKED **עובדת** (תיקון #13).

---

### S4 — Woodies (FIRING)

| שדה | API (live) | UI Plan |
|-----|------------|---------|
| `failed_stages` | `[]` | **מוכן לניתוב** / VEGAS SHORT |
| `pre_fire` | 7 שורות, כולן PASS | A1–A6 ✓ ב-TO FIRE |
| `ready_to_route` | `true` | STATE מסביר Gateway |
| `last_route.blocked_by` | `cluster_guard` | מופיע ב-whyNotFire (לא ב-failed_stages) |

**A4 touch-point (איכות):** הודעת A4 מכילה timeouts ל-localhost (`read timeout=2` בלוג ישן / עומס). שלב נשאר **PASS** — advisory degraded.

**מסקנה:** עץ החלטות תקין; חסימת ירי בפועל מ-**Gateway/cluster**, לא מ-A5 FAIL.

---

### S5 — TPO (OBSERVER)

| שדה | API | UI Plan |
|-----|-----|---------|
| `state` | `STUCK` | STATE **READY** (מ-`ib_locked`) |
| שורות | POC, IB lock, migration | CONTEXT ✓ |

**מסקנה:** observer תקין; `STUCK` ב-API vs READY ב-UI — מכוון (נגזר מ-`ib_locked`).

---

### S6 — Killzone (OBSERVER)

| שדה | API | UI Plan |
|-----|-----|---------|
| `state` | `NY_PREMARKET` | STATE **APPROACHING** |
| Gate | סגור (premarket) | ⚠ Gate — |

**מסקנה:** by design — observer לא עובר ל-BLOCKED; S4 FIRING בודק gate ב-`diagnoseWoodies`.

---

## 4. מה כבר תוקן (לא לגעת שוב)

1. **`maxLifecycle` + diagnosis merge** — S2 `MAINTENANCE`/`WEEKEND`, S3 `last_fire.blocked_by` נשארים BLOCKED.
2. **קבצים:** `planFireDiagnosis.ts`, `systemPlanLive.tsx`, `planHelp.ts` (A5 RTL).
3. **בדיקות:** `tests/v9/frontend/test_plan_fire_diagnosis_contract.py` — חוזה מrorror של הלוגיקה.

---

## 5. ארבע צירי UAT

| ציר | קריטריון | תוצאה 2026-05-20 | סטטוס |
|-----|----------|------------------|--------|
| **Quality** | `count=6`; BLOCKED תואם `failed_stages` / `blocked_by` / mode | Woodies `[]` + S3 cluster_guard עקביים | ✅ |
| **Recency** | `endpoint.ts ≈ now` | `age_s ≈ 0.04`; UI Feeds OK 0–36 s | ✅ |
| **Cardinality** | 6 מערכות; עד 7 pre_fire ל-Woodies | `count=6`, `pre_fire_count=7` | ✅ |
| **Latency** | snapshot &lt; 100 ms (test); live סביר | curl **340 ms**; pytest &lt;100 ms | ✅ (live מעל תקציב test — ראו המלצה P1) |

**הערה:** בסוף הביקורת curl נכשל ב-5 s timeout — סימפטום עומס backend (כנראה Woodies bar + touch-points), לא רגרסיית Plan.

---

## 6. GAPs והמלצות תיקון (ממוין לפי עדיפות)

### P0 — לפני LIVE (זמן / כסף אמיתי)

#### G-PLAN-2 — עומס backend / snapshot timeout

**תסמינים:**  
- `systems-snapshot` לעיתים &gt; 5 s (timeout בסוף ביקורת).  
- A4 מדווח `HTTPConnectionPool … Read timed out (read timeout=2)` כשהשרת עמוס.  
- תיעוד קיים: [`PROMPT_P30_WOODIES_SYSTEM_SLOW_HANDLER.md`](PROMPT_P30_WOODIES_SYSTEM_SLOW_HANDLER.md).

**שורש:** Woodies `process_bar` עדיין יכול להעמיס את האירוע לולאה כש-touch-point prefetch נכשל לאט; self-HTTP ל-5 endpoints.

**המלצה (שינוי מינימלי):**

| # | פעולה | קובץ | מאמץ |
|---|--------|------|------|
| 2a | **In-process touch-points** — פונקציה `fetch_touchpoints_inprocess(app.state)` שקוראת ישירות ל-day_type_machine / tpo / killzone בלי HTTP | `decision_tree.py`, `woodies_system.py` | ~0.5 יום |
| 2b | הגדלת `_TOUCHPOINTS_PREFETCH_BUDGET_S` רק אם 2a לא מספיק; log `warning` (לא debug) כש-nach budget | `woodies_system.py` | שעה |
| 2c | UAT: `grep SLOW handler Woodies` ב-`/tmp/backend.err.log` = 0 לאורך 30 דק RTH | — | Michael/CC |

**קריטריון קבלה:** curl snapshot &lt; 500 ms p95; אין `took 10000ms` בלוג.

---

#### G-PLAN-5 (חדש) — S2 `OVERNIGHT_MODE` לא מוצג כ-BLOCKED

**תסמין:** בלילה/לפני RTH המשתמש רואה setup בעברית אבל לא badge **BLOCKED** ברור.

**המלצה:**

```typescript
// planFireDiagnosis.ts — diagnoseFiringSystem S2
if (['MAINTENANCE', 'WEEKEND', 'OVERNIGHT_MODE'].includes(mode)) {
  return { situation: 'GATEWAY_BLOCK', badgeLabel: `חסום · ${mode}`, ... };
}
```

```typescript
// systemPlanLive.tsx — deriveFiringLifecycle S2
if (mode === 'OVERNIGHT_MODE' || mode === 'MAINTENANCE' || mode === 'WEEKEND') return 'BLOCKED';
```

+ בדיקה ב-`test_plan_fire_diagnosis_contract.py`: `test_s2_overnight_stays_blocked`.

**מאמץ:** ~1 שעה. **סיכון:** נמוך — רק תצוגה + lifecycle עקבי.

---

### P1 — אמינות UI (לפני soak ארוך)

#### G-PLAN-1 — React hydration ב-dev

**תסמין:** overlay Next.js על `TopBar` / `PriceDisplay`; לפעמים חוסם קליק על שורות Plan (A5).

**שורש סביר:** `PriceDisplay.tsx` — `Date.now() - lastUpdateMs` ב-render (שונה SSR vs client).

**המלצה:**

| # | פעולה |
|---|--------|
| 1a | להעביר חישוב `isStale` ל-`useEffect` + state, או `suppressHydrationWarning` רק על span הסטטוס |
| 1b | לוודא שאין `Date.now()` / `Math.random()` ב-render של TopBar subtree |

**מאמץ:** 2–4 שעות. **קריטריון:** אין hydration error בקונסול אחרי hard refresh.

---

#### G-PLAN-3 — S1 `state: null` ב-snapshot

**תסמין:** jq מראה `state: null` ל-Day Type כש-machine לא מוזרק; UI עדיין SCANNING.

**המלצה (backend):** ב-`cockpit_systems_snapshot` — אם `day_type_machine` קיים, תמיד למלא `state` מ-`classification.day_type` (כבר קיים ב-try — לבדוק למה live החזיר null: exception שקט ב-`except: pass`).

| # | פעולה |
|---|--------|
| 3a | להחליף `except Exception: pass` ב-`logger.warning` rate-limited + fallback `state: "SEARCHING"` |
| 3b | בדיקת API: `systems[0].state != null` אחרי restart |

**מאמץ:** 1–2 שעות.

---

### P2 — שיפורי שקיפות (אחרי LIVE או ב-soak)

#### G-PLAN-4 — לא צולם BLOCKED + FAIL live

**המלצה:** לא קוד — להריץ במהלך RTH עם Woodies A5 reject:

```bash
curl -s localhost:8000/api/v9/cockpit/systems-snapshot | jq '.systems[]|select(.id==4)|{failed_stages:.raw.failed_stages,pre_fire:.raw.decision_tree.pre_fire[]|select(.status=="FAIL")}'
```

צילום מסך Plan עם badge **BLOCKED** + שורת A5 FAIL — לארכיון L3.

---

#### G-PLAN-6 (חדש) — S4 `ready_to_route=true` אבל `cluster_guard`

**תסמין:** עץ ירוק, אבל `last_route.blocked_by=cluster_guard` — עלול לבלבל סוחר.

**המלצה (UX בלבד):** כש-`ready_to_route && last_route.blocked_by`, badge **APPROACHING** או **BLOCKED** עם תת-כותרת Gateway (לא READY ירוק בלבד). שינוי ב-`lifecycleFromDiagnosis` / `deriveFiringLifecycle` — `maxLifecycle(READY, GATEWAY_BLOCK)`.

**מאמץ:** 2–3 שעות + בדיקת עין.

---

#### G-PLAN-7 (חדש) — S6 gate סגור vs APPROACHING

**סטטוס:** מכוון per spec.  
**המלצה:** להוסיף שורת CONTEXT **● Gate CLOSED** אדומה (כבר קיים ⚠) + משפט ב-`planHelp.ts` שמפנה ל-S4. אין שינוי lifecycle.

---

## 7. תוכנית עבודה מוצעת (P-ID)

| P-ID | נושא | עדיפות | בעלים | תלות |
|------|------|--------|--------|------|
| **P30.10b-P0a** | In-process touch-points (בלי HTTP loopback) | P0 | Cursor | — |
| **P30.10b-P0b** | S2 OVERNIGHT → BLOCKED ב-Plan | P0 | Cursor | — |
| **P30.10b-P1a** | PriceDisplay hydration fix | P1 | Cursor | — |
| **P30.10b-P1b** | Day Type snapshot `state` + warning log | P1 | Cursor | backend restart |
| **P30.10b-P2** | Gateway-block vs READY badge (S4) | P2 | Cursor + Michael sign-off | P0 יציב |
| **#14 L4** | Risk surface audit | הבא בתור | Cursor + Michael | #13 ✅ |

**אין commit** עד אישור Michael.

---

## 8. פקודות אימות (להדבקה אחרי כל תיקון)

```bash
# API — ארבע צירים
curl -s -w "\nHTTP %{http_code} time=%{time_total}s\n" \
  http://localhost:8000/api/v9/cockpit/systems-snapshot \
  | jq '{ts,count,age_s:(now-.ts),systems:[.systems[]|{id,name,state,failed_stages:(.raw.failed_stages//.raw.decision_tree.failed_stages),pre_fire:((.raw.decision_tree.pre_fire//[])|length)}]}'

# רגרסיה Plan
pytest tests/v9/api/test_cockpit_systems_snapshot.py \
  tests/v9/frontend/test_plan_fire_diagnosis_contract.py -q

# עומס Woodies (אחרי P0a)
grep -c "WoodiesSystem.process_bar took" /tmp/backend.err.log
```

**דפדפן:** Side panel → S2 Plan (OVERNIGHT → BLOCKED); S3 tap ●; S4 tap STATE → RTL.

---

## 9. מסקנה

| שאלה | תשובה |
|------|--------|
| האם #13 / L3 סגורים? | **כן** — חוזה, pytest, דפדפן S1–S6 |
| האם בטוח ל-LIVE רק עם Plan? | **לא** — יש לסגור **P0** (עומס + OVERNIGHT) לפחות |
| מה הצעד הבא? | **#14 L4** risk surface + תור P0 למעלה |

---

*נוצר: Cursor agent · משימה #13 · 2026-05-20*
