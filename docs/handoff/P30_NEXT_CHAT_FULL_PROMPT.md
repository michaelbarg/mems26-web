# P30 — פרומפט מלא לצ'אט הבא (2026-05-20)

**מטרה:** המשך Pre-LIVE בלי לאבד הקשר.  
**מקור אמת:** `docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md` (עדכן §1/§2/§8 בכל פרומפט).

---

## בלוק להדבקה (העתק מהשורה הבאה עד סוף הקופסה)

```text
MEMS26 P30 — המשך Pre-LIVE (2026-05-20)

קרא קודם (בסדר):
1. docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md — §6 roadmap, §8 תור #1–#15
2. docs/handoff/P30_NEXT_CHAT_FULL_PROMPT.md — מסמך זה
3. docs/reports/PROMPT30_10b_PLAN_LIVE.md — מפרט Plan tab (משימה נוכחית)

=== סגור (Michael sign-off 2026-05-20) — אל תפתח מחדש ===
- L0 cockpit parity (#9)
- #7 Visual UAT (§2.1–§2.10 + ChartV5b)
- Chart TASK A: CVD ↔ price candle X-align (alignCvdPointTimesToPriceBars)
- #2 G4 round 2 (TPO subgraphs, CC)
- #12 L2 soak (22/22 ב-PROMPT30_SHADOW_READY.md)
- #1 bridge, #1b backend, #8 verify, #10 snap-to-latest, #10b day-type seed, #11 G6 archiver

=== משימה ראשית (עבוד strict top-down) ===
#13 — L3: Audit Plan tab BLOCKED reason chain לכל S1–S6

Deliverables:
1. לכל מערכת (S1 Day Type … S6 Killzone): Side panel → Plan → תעד:
   - lifecycle badge (SCANNING/APPROACHING/BLOCKED/READY/FIRING)
   - שורות TO FIRE / CONTEXT
   - tap badge + tap שורת FAIL → טקסט עברית RTL נכון
2. API: GET /api/v9/cockpit/systems-snapshot — ארבע צירי UAT (quality/recency/cardinality/latency)
3. עדכן docs/reports/PROMPT30_10b_PLAN_LIVE.md — טבלת S1–S6 + gaps
4. עדכן inbox §8 שורה #13 → DONE או BLOCKED עם סיבה
5. regression tests רק אם מוצא באג אמיתי (לא refactor)

קבצים מרכזיים:
- frontend/.../plan/systemPlanLive.tsx, planFireDiagnosis.ts, planHelp.ts
- backend/v9/app.py (systems-snapshot)
- backend/v9/systems/woodies/decision_tree.py (pre_fire, failed_stages)
- Woodies: failed_stages → BLOCKED (דוגמה A5)

אחרי #13 (רק אם Michael אומר go):
- #14 L4 risk audit (firewall, risk_engine, kill switch)
- #15 L5 paper V9_PAPER_MODE=1

=== אסור / הקפאה ===
- אל תיגע ב-POC/TPO/VAH/VAL בפרונט (tpoLevels, loadLevels, SierraLevelsOverlay TPO) — Michael: "לא לגעת ב poc יותר"
- אל תערוך bridge/, sc_study/, LaunchAgent
- אל תריץ start_all.sh / npm run dev / launchctl / kill -9 בלי בקשה מפורשת
- CLOUD_URL רק http://localhost:8000
- commit/push רק לפי בקשת Michael
- דוחות ארוכים → Claude Code; אתה: קוד + UAT + עדכון inbox קצר

=== פרוטוקול Pre-LIVE (חובה) ===
לפני תיקון: Read קוד → Audit KEEP/ADAPT/REPLACE → אמת עם curl/DB → smallest fix
לנתוני API: 4 צירים — quality, recency, cardinality, latency
אם תקוע 2× באותה פקודה — החלף כלי או עצור ושאל Michael

=== מצב קוד (לא committed) ===
שינויי ChartV5b/CVD/TPO overlay על דיסק — Michael לא ביקש commit עדיין.
אם צריך backend restart ל-day_type seed (#10b) — שאל לפני restart.

=== אופציונלי (לא לקפוץ לפני #13) ===
- #3 Day Type Nontrend investigation (IN PROGRESS) — docs/handoff/INVESTIGATE_DAY_TYPE_NONTREND_2026-05-19.md
- #4 CC consolidated report — docs/handoff/CC_DETAILED_STATUS_REPORT_REQUEST.md → P30_CONSOLIDATED_STATUS.md (CC, לא Cursor)
- L1 DLL G1/G3 — CC + Sierra Remote Build — docs/runbooks/SIERRA_DLL_OPS.md

התחל ב-#13: קרא PROMPT30_10b_PLAN_LIVE.md, הרץ curl ל-systems-snapshot, ואז audit UI S1–S6.
```

---

## 1. הקשר — איפה אנחנו בתוכנית LIVE

```
✅ L0  Cockpit parity (Michael 2026-05-20)
✅ L2  Systems soak (#12)
⏳ L3  Plan tab BLOCKED chain  ← #13 (עכשיו)
⏸ L4  Risk audit               ← #14 (אחרי L3)
⏸ L5  Paper dry run            ← #15
⏸ L6–L8 Broker / LIVE gates    ← Michael go/no-go
```

מפת דרכים מלאה: inbox §6 · מאסטר: `docs/spec_authority/MEMS26_MASTER_INDEX_V2.markdown`

---

## 2. מה נסגר — אל תחזור על זה

| ID | משימה | הערה |
|----|--------|------|
| #7 | Visual UAT | Chart + Woodies + CVD + TPO lines |
| #9 | L0 sign-off | G4 r2 + cockpit accepted |
| #12 | L2 soak | 22/22 SHADOW + Michael |
| Chart TASK A | `cvdMapping.ts` +4h align | §2.10 inbox |
| #2 | G4 TPO DLL round 2 | CC subgraph indices |

**ChartV5b קבצים (reference בלבד — לא לערוך POC):**

| קובץ | תפקיד |
|------|--------|
| `frontend/.../v5b/cvdMapping.ts` | `alignCvdPointTimesToPriceBars` |
| `frontend/.../v5b/CvdChartPane.tsx` | CVD pane + align log |
| `frontend/.../v5b/ChartV5b.tsx` | 2 panes, dedup bars, goToLatest |
| `frontend/.../v5b/tpoLevels.ts` | pickTodayPeriod, buildTpoPlan (frozen) |
| `frontend/.../v5b/SierraLevelsOverlay.tsx` | SVG TPO lines (frozen) |

---

## 3. משימה #13 — Plan tab audit (פירוט לביצוע)

### 3.1 מטרה

לוודא שלכל **S1–S6** ב-Side Panel → **Plan**:

1. **STATE** badge משקף נכון את `raw` מ-`systems-snapshot` (BLOCKED כשיש `failed_stages` / gateway block / וכו').
2. **TO FIRE** (S4 Woodies, S2 5-Min) או **CONTEXT** (S1,S3,S5,S6) — שורות עם PASS/FAIL/SKIP + message.
3. **לחיצה** על badge / שורה → פאנל עברית RTL (`planHelp.ts`, `planFireDiagnosis.ts`) תואם את הסיבה האמיתית.
4. **DATA HEALTH** — poll age + dot (Feeds OK / Degraded / Stale).

### 3.2 API — בדיקת 4 צירים

```bash
# Recency + Quality + Cardinality (מבנה)
curl -s --max-time 5 http://localhost:8000/api/v9/cockpit/systems-snapshot | jq '{
  ts: .timestamp,
  s1: .systems["1"] | {state, health, raw_keys: (.raw|keys)},
  s4: .systems["4"] | {state, health, failed: .raw.failed_stages, pre_n: (.raw.decision_tree.pre_fire|length)}
}'

# Woodies pre_fire detail
curl -s --max-time 5 http://localhost:8000/api/v9/cockpit/systems-snapshot | \
  jq '.systems["4"].raw.decision_tree | {failed_stages, pre_fire: [.pre_fire[]|{stage_id,status,message}]}'
```

| ציר | בדיקה |
|-----|--------|
| Quality | `failed_stages` ב-API = BLOCKED ב-UI; A5 FAIL message מופיע בשורה |
| Recency | `lastUpdate` / poll age < 60s במהלך RTH (אם bridge/up) |
| Cardinality | Woodies: 7 שורות pre_fire (A1–A7); אין שורות ריקות שבורות |
| Latency | curl < 500ms מקומי |

### 3.3 UI — checklist לכל מערכת

| Sys | Plan component | מה לבדוק |
|-----|----------------|----------|
| S1 | `DayTypePlan.tsx` | CONTEXT rows; אין TO FIRE; day_type מ-snapshot |
| S2 | `FiveMinPlan.tsx` | mode/buffer rows; FIRING/OBSERVER לפי spec |
| S3 | `FootprintPlan.tsx` | CONTEXT; COT/AMT אם ב-raw |
| S4 | `WoodiesPlan.tsx` | **BLOCKED** + `failed_stages`; tap A5; 7 pre_fire rows |
| S5 | `TpoPlan.tsx` | CONTEXT; observer only |
| S6 | `KillzonePlan.tsx` | gate OPEN/CLOSED; session zones |

### 3.4 פלטים נדרשים בסוף #13

1. **`docs/reports/PROMPT30_10b_PLAN_LIVE.md`** — סעיף "Per-system audit 2026-05-20" עם טבלה S1–S6 (PASS/GAP/BLOCKED reason).
2. **`P30_AGENT_INBOX_PRE_LIVE.md`** — §8 שורה #13 → DONE + תאריך; אם GAP → §3 שורה חדשה.
3. **באגים בלבד:** test תחת `tests/v9/` + fix מינימלי.
4. **אל** לשכתב `WoodiesCciPanel` או Plan ל-props-only (inbox §8 "should NOT start").

---

## 4. אחרי #13 — תור (אל תקפוץ)

| # | משימה | מסמך |
|---|--------|------|
| #14 | Risk surface audit | inbox L4; `firewall.json`, `risk_engine`, kill switch |
| #15 | Paper `V9_PAPER_MODE=1` | inbox L5; 1 RTH, bridge log clean |

---

## 5. Gaps פתוחים (לא חוסמים #13 אבל לדעת)

| ID | בעלים | הערה |
|----|--------|------|
| G1 | CC | proj_hi/lo ב-DLL |
| G2 | CC | previous_session ב-tpo.json |
| G3 | CC | CVD `t` + output_interval ב-DLL (קוד backend כבר מוכן) |
| G4 | **Closed L0** | monitor `age_s` על tpo |
| G5 | CC+Cursor | Redis cleanup — אחרי bridge יציב |
| #3 | Cursor | Day Type Nontrend — investigation handoff |
| #4 | CC | P30_CONSOLIDATED_STATUS.md |

---

## 6. שירותים — קריאה בלבד אלא אם Michael מבקש

```bash
lsof -i :8000 -i :3000 | head
curl -s --max-time 3 http://localhost:8000/api/v9/status | jq '{mode,session}'
# bridge log (אם רלוונטי):
tail -20 /tmp/bridge.err.log
```

§9 ב-inbox עלול להיות **מיושן** (צילום 2026-05-19) — אל תסתמך עליו לגבי bridge up/down; בדוק live.

---

## 7. קישורים מהירים

| נושא | קובץ |
|------|------|
| Inbox | `docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md` |
| Chart (סגור) | `docs/handoff/P30_CHART_V5B_HANDOFF_NEXT_CHAT.md` |
| Plan spec | `docs/reports/PROMPT30_10b_PLAN_LIVE.md` |
| SHADOW gate | `docs/reports/PROMPT30_SHADOW_READY.md` |
| Pre-LIVE rules | `.cursor/rules/mems26-pre-live-protocol.mdc` |
| Sierra DLL ops | `docs/runbooks/SIERRA_DLL_OPS.md` |
| Day Type | `docs/handoff/INVESTIGATE_DAY_TYPE_NONTREND_2026-05-19.md` |

---

*נוצר 2026-05-20 — עדכן תאריך וסטטוס #13 כשהצ'אט הבא מסיים.*
