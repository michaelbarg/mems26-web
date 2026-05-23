# Claude Code — פרומפט מלא: דוח מצב לפני Cursor / LIVE

**תאריך:** 2026-05-20  
**מזמין:** Michael (via Cursor)  
**נמען:** Claude Code  
**מטרה:** דוח **אחד מלא** עם evidence — מה בוצע, מה חסר, מה חוסם ירי/SHADOW, מה דחוף ל-LIVE — **לפני** ש-Cursor מפעיל 6 סוכני spec או נוגע בקוד.

**Repo:** `~/Downloads/mems26_web_git`

---

## העתקה ל-Claude Code (התחל כאן)

```text
TASK: P30 Pre-Cursor Full Status Report (read-only audit + live probes)

You prepare ONE master report for the Cursor agent. Michael will review LIVE
priorities separately in P30_SYSTEM_GAP_AUDIT.md — you do NOT guess priorities;
you supply facts + recommended P0/P1/P2 labels for Michael to confirm.

DELIVERABLE (required):
  docs/reports/P30_CC_FULL_STATUS_FOR_CURSOR.md

Also update:
  docs/handoff/CC_STATUS_REQUEST_2026-05-20.md §4 (verdict table)
  docs/reports/P30_CC_FIRE_BLOCKERS_SUMMARY.md (1 page)

GUARDRAILS — MANDATORY:
  1. Read docs/reports/P30_SIERRA_STUDY_PROTOCOL.md — Sierra = single source of truth.
  2. Michael approved DLL + time-axis work (2026-05-20). VERIFY live; do NOT re-deploy
     or change study IDs / subgraph indices / export fields without Michael OK.
  3. NO edits to sc_study/, bridge/, LaunchAgent, frontend design/CSS, gateway logic.
  4. NO commit unless Michael asks.
  5. Read inbox §7a: P30_AGENT_INBOX_PRE_LIVE.md

CONTEXT Cursor already diagnosed (you must confirm with data):
  - Woodies ready_to_route can be true while gateway returns blocked_by=cluster_guard
    BEFORE _execute_shadow (trading_gateway.py)
  - Plan tab L3 audit DONE (pytest + browser) — do not redo UI redesign
  - L4 risk audit NOT DONE; L5 paper WAIT

WORKFLOW:
  Phase 1 — Read all sources listed in §2 below (30 min).
  Phase 2 — Run every live probe in §4 (record raw output snippets).
  Phase 3 — Fill gap checklist from P30_SYSTEM_GAP_AUDIT.md §1–7 with PASS/FAIL/UNKNOWN.
  Phase 4 — Write master report §5 structure.
  Phase 5 — 5-line executive summary + explicit list "what blocks SHADOW fire now".

If sandbox cannot run curl/pgrep: say so per row; give exact commands for Michael.

END TASK.
```

---

## §1 — מה Cursor צריך ממך (פלט חובה)

| # | קובץ | תוכן מינימלי |
|---|------|----------------|
| 1 | `docs/reports/P30_CC_FULL_STATUS_FOR_CURSOR.md` | דוח מאסטר (מבנה §5) |
| 2 | `docs/reports/P30_CC_FIRE_BLOCKERS_SUMMARY.md` | טבלה: S2/S3/S4 + gateway blockers + live `blocked_by` |
| 3 | `docs/handoff/CC_STATUS_REQUEST_2026-05-20.md` §4 | כל שורות ה-ID ממולאות |
| 4 | (אופציונלי) עדכון שורות ב-`P30_SYSTEM_GAP_AUDIT.md` | סימון Has/Missing עם תאריך אימות — **לא** Priority Matrix (זה Michael) |

---

## §2 — מסמכים לקריאה (לפני probes)

| סדר | קובץ | למה |
|-----|------|-----|
| 1 | `docs/reports/P30_SIERRA_STUDY_PROTOCOL.md` | subgraph IDs, אישורים |
| 2 | `docs/reports/P30_SYSTEM_GAP_AUDIT.md` | רשימת פערים per subsystem |
| 3 | `docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md` §2, §3, §7a, §8 |
| 4 | `docs/handoff/CC_STATUS_REQUEST_2026-05-20.md` §1 |
| 5 | `docs/reports/PROMPT30_10b_PLAN_LIVE.md` + `PROMPT30_10b_PLAN_LIVE_FULL_REPORT_HE.md` |
| 6 | `docs/runbooks/SIERRA_DLL_OPS.md` |
| 7 | `backend/v9/gateway/trading_gateway.py` | סדר חסימות gateway |
| 8 | `backend/v9/systems/woodies/decision_tree.py` | ready_to_route |
| 9 | `docs/reports/PROMPT_P30_WOODIES_SYSTEM_SLOW_HANDLER.md` | touch-point SLOW |

---

## §3 — רשימת בדיקות מלאה (מה לבדוק / מה חסר)

### A. Sierra DLL + קבצי export (VERIFY בלבד)

Michael: **בוצע** — אל תפרוס בלי אישור. אמת:

| ID | בדיקה | אימות | קריטריון PASS |
|----|--------|--------|----------------|
| DLL-01 | `woodies_5min.json` fresh | `stat`, `age_s` | mtime < 30s ב-RTH |
| DLL-02 | ProjHigh/ProjLow | jq `current_bar.proj_hi/lo` | non-null floats (Study 9 SG1/SG2 per PROTOCOL) |
| DLL-03 | CCI/TCCI/EMA/LSMA/SWI/CZI | jq studies | match PROTOCOL subgraph map |
| DLL-04 | `sierra_source: true` / no bogus 0 | jq | protocol §4 |
| DLL-05 | `cumulative_delta.json` `t` + `output_interval` | jq last point | `t` ≈ `export_ts` ±2s; interval=300 for 5m |
| DLL-06 | `tpo.json` fresh + session POC/VAH/VAL | curl + stat | age_s<30; values in 3000–10000 |
| DLL-07 | `previous_session` block | curl `.previous_session` | found + POC/VAH/VAL vs Sierra yesterday |
| DLL-08 | IB in tpo | jq `.ib` | found, high/low sane |
| DLL-09 | `woodies_diag.json` | only if diagnostic was run | optional |
| DLL-10 | v9.4.2-p30.11 claims in GAP audit | grep DLL version in export | version string |

**פקודות:**

```bash
EXPORT=~/SierraChart_Data/v9_export
for f in woodies_5min.json cumulative_delta.json tpo.json; do
  echo "=== $f ==="; stat -f '%Sm %z' "$EXPORT/$f" 2>/dev/null || echo MISSING
done
python3 -c "import json;d=json.load(open('$EXPORT/woodies_5min.json'));c=d.get('current_bar',{});print('proj',c.get('proj_hi'),c.get('proj_lo'),'sierra',d.get('sierra_source'))"
jq '{export_ts,output_interval,n:(.points|length),last:.points[-1]}' "$EXPORT/cumulative_delta.json"
curl -s http://localhost:8000/api/v9/tpo/current | jq '{age_s,stale,session,previous_session,ib}'
```

**חסר / לסמן בדוח:** Predictor H/L, ZLR vs ID:13, HFE computed, trend GRAY vs CCI Trend study, session volume=0 (מ-GAP audit §1).

---

### B. Bridge

| ID | בדיקה | PASS |
|----|--------|------|
| BR-01 | Process running | `pgrep -fl json_bridge` |
| BR-02 | `CLOUD_URL=http://localhost:8000` | env in process |
| BR-03 | Heartbeat streams | `curl .../cockpit/heartbeat` → 12/12 or 11/12 |
| BR-04 | `/tmp/bridge.err.log` 4h | no FAILED to https://; push errors count |
| BR-05 | TPO stream errors | grep tpo in bridge log |
| BR-06 | stacked_imbalances errors | grep in log |

---

### C. Backend (ארבע צירי UAT ל-endpoints נתונים)

| ID | Endpoint / נושא | Quality | Recency | Cardinality | Latency |
|----|------------------|---------|---------|-------------|---------|
| BE-01 | `GET /api/v9/cockpit/systems-snapshot` | count=6 | ts≈now | 6 systems | <500ms p95 |
| BE-02 | `GET /api/v9/bars/5min?limit=600` | bad_count=0 | latest_ts=DB MAX | len=600 | <200ms |
| BE-03 | `GET /api/v9/tpo/current` | poc sane | age_s<30 | fields present | |
| BE-04 | `GET /api/v9/cumulative_delta/current` | points have t | age_s | | |
| BE-05 | `GET /api/v9/woodies/chart` | no invented proj | age_s | | |
| BE-06 | Woodies `process_bar` SLOW | grep backend.err | 0 in 30min | | |
| BE-07 | Touchpoints A4 | snapshot S4 A4 message | degraded OK? | | |
| BE-08 | `GET /api/v9/gateway/status` + `/risk` | | | | |
| BE-09 | `GET /api/v9/day_type/v9/current` | | | | |
| BE-10 | `GET /api/v9/killzone/current` | gate_open | | | |

```bash
curl -s -w '\nTIME %{time_total}s\n' http://localhost:8000/api/v9/cockpit/systems-snapshot | jq '{ts,count,age_s:(now-.ts)}'
curl -s http://localhost:8000/api/v9/gateway/risk | jq .
curl -s http://localhost:8000/api/v9/cockpit/heartbeat | jq '{streams,mode}'
grep -c 'WoodiesSystem.process_bar took' /tmp/backend.err.log 2>/dev/null || echo 'no log'
```

---

### D. Gateway — מה קובע ירי vs חסימה (קריטי ל-Cursor)

| ID | בדיקה | קוד | live |
|----|--------|-----|------|
| GW-01 | `cluster_guard` state | `cooldown.py` ClusterGuard | `gateway/risk` |
| GW-02 | `record_attempt` before gates | `trading_gateway.py` L78 | |
| GW-03 | SHADOW only if gates pass | L102+ `_execute_shadow` | `last_route.shadow` |
| GW-04 | S4 `ready_to_route` + `blocked_by` | woodies_system.py | snapshot id=4 |
| GW-05 | S3 `last_fire.blocked_by` | footprint_system.py | snapshot id=3 |
| GW-06 | cooldown / SSV / chop_searching | trading_gateway.py | risk endpoint |

```bash
curl -s http://localhost:8000/api/v9/cockpit/systems-snapshot | jq '{
  s3: (.systems[]|select(.id==3)|{combined:.raw.combined_class,last_fire:.raw.last_fire}),
  s4: (.systems[]|select(.id==4)|{ready:.raw.ready_to_route,failed:.raw.failed_stages,last_route:.raw.last_route})
}'
grep -E '\[Gateway\] BLOCKED|\[Woodies\] SHADOW recorded' /tmp/backend.err.log | tail -30
```

**דוח חובה:** האם `blocked_by=cluster_guard` מונע **כל** SHADOW (כולל S3/S4) עכשיו? כמה שניות נשאר ל-block?

---

### E. Frontend (read-only — ללא שינוי עיצוב)

| ID | בדיקה | הערה |
|----|--------|------|
| FE-01 | Pink TPO lines ב-RTH | GAP audit — Michael reported issue |
| FE-02 | CVD X-align last bar | §2.10 sign-off — verify still |
| FE-03 | Woodies HUD CCIDiff/Predictor | display only |
| FE-04 | Hydration overlay TopBar | known GAP |
| FE-05 | Plan tab S1–S6 | Cursor DONE — spot-check only |

Browser URL: `http://127.0.0.1:3000` — צילום/תיאור, לא CSS edits.

---

### F. מערכות S1–S6 (מול compliance_manifest + fire/block)

| Sys | Type | קובץ manifest | בדוק ירי? | בדוק לא-ירי? |
|-----|------|---------------|-----------|--------------|
| S1 Day Type | OBSERVER | `day_type/compliance_manifest.yaml` | never `route_setup` | lock, 6 types |
| S2 5-Min | FIRING | `five_min/compliance_manifest.yaml` | pattern+mode | MAINTENANCE/OVERNIGHT/WEEKEND |
| S3 Footprint | FIRING | `footprint/compliance_manifest.yaml` | combined≠NO_SETUP | blocked_by |
| S4 Woodies | FIRING | `woodies/compliance_manifest.yaml` | A1–A7 PASS + gateway | A5 fail, cluster_guard |
| S5 TPO | OBSERVER | `tpo/compliance_manifest.yaml` | never fire | POC/IB context |
| S6 Killzone | OBSERVER | `killzone/compliance_manifest.yaml` | never fire | gate → S4 whyNotFire |

```bash
pytest tests/v9/compliance/ -q --tb=no 2>/dev/null | tail -20
pytest tests/v9/api/test_cockpit_systems_snapshot.py tests/v9/frontend/test_plan_fire_diagnosis_contract.py -q
```

---

### G. שערי מסלול Pre-LIVE (סטטוס תהליך)

| Milestone | Expected | Evidence |
|-----------|----------|----------|
| L0 | DONE | Michael sign-off |
| L2 | DONE | SHADOW 22/22 |
| L3 | DONE | PROMPT30_10b |
| L1 | G1–G3 DLL | your DLL section |
| L4 | Risk audit | NOT DONE — firewall, kill switch |
| L5 | Paper | WAIT L4 |

---

## §4 — מטריצת ID ל-§4 ב-CC_STATUS_REQUEST (מלא הכל)

מלא כל שורה: `DLL-G1` … `DLL-L1`, `OPS-BRIDGE`, `P30.10`, `P30.11`, `GW-1`, `GW-2`, `PERF-1`, `UI-1`–`UI-3`, `API-1`, `INV-1`, `DOC-1`, `L4`, `L5`.

---

## §5 — מבנה דוח מאסטר `P30_CC_FULL_STATUS_FOR_CURSOR.md`

```markdown
# P30 — CC Full Status for Cursor (YYYY-MM-DD HH:MM ET)

## 0. Executive summary (5 bullets)
## 1. What blocks SHADOW / Woodies fire RIGHT NOW
## 2. Sierra DLL + exports (table DLL-01..10)
## 3. Bridge (BR-01..06)
## 4. Backend UAT 4-axis (BE-01..10)
## 5. Gateway fire/block (GW-01..06 + log excerpts)
## 6. Per-system S1–S6 (fire spec vs code — 1 table)
## 7. P30_SYSTEM_GAP_AUDIT cross-walk (§1–7 PASS/FAIL/UNKNOWN)
## 8. Gaps NOT done (explicit list for Cursor agents)
## 9. Recommended P0/P1/P2 for Michael (he overrides Priority Matrix)
## 10. Commands log (copy-paste block used)
## 11. Strategic stop / blockers for 6-agent launch (GO / NO-GO)
```

---

## §6 — מה **אסור** לכלול בדוח (רעש)

- הצעות redesign / Woodies panel 1:1 designer
- שינוי קוד בלי רשימת "proposed fix" נפרדת ל-Michael
- סימון Priority Matrix במקום Michael (רק **המלצה** ב-§9)

---

## §7 — אחרי הדוח

1. Michael ממלא **Priority Matrix** ב-`P30_SYSTEM_GAP_AUDIT.md`.
2. Cursor קורא `P30_CC_FULL_STATUS_FOR_CURSOR.md` → מפעיל 6 סוכנים (`docs/handoff/agents/AGENT_S*.md`) רק אם §11 = GO.
3. אין מיזוג קוד Gateway/DLL עד Michael "go" על שורות 🔴.

---

*Michael — העתק את §0 (הבלוק בתוך code fence) ל-Claude Code בשלמות.*
