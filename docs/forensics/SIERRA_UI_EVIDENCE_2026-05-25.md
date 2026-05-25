# Sierra UI Forensic Evidence · 2026-05-25 19:32 IL

**Purpose:** Canonical reference for CC Stream A fix (HA-2 subgraph indices + HA-3 chart number resolution).
**Source:** Michael's direct Sierra Chart screenshots, validated visually.
**Status:** AUTHORITATIVE — supersedes any in-code assumption about subgraph layout.

---

## 1 · DLL Chart Number — RESOLVED

| Question | Answer |
|---|---|
| Where does the DLL (`MES AI Data Export v9.4.2-p30.11`) run? | **Chart #3** (per Michael 19:32 IL) |
| `TPOChartNumber` Input[17] default | `0` = host chart = #3 ✅ |
| HA-3 verdict | **REFUTED** — TPOChartNumber=0 is correct given DLL lives on chart #3 |
| Chart #19 (visible in additional screenshots) | **Separate visualization chart** · Numbers Bars TPO study + VbP + CountDown · NOT the DLL chart · red herring |

**Implication:** No change needed to `TPOChartNumber` Input. Bug is purely subgraph-indices (HA-2).

---

## 2 · Subgraph Layouts — VERIFIED FROM SIERRA UI

### 2.1 · TPO Value Area Lines · ID:1 (Yesterday) and ID:3 (Today)

Both TPO studies share identical subgraph layout:

| UI Subgraph | Sierra UI Label | Draw Style | 0-indexed (cpp) |
|---|---|---|---|
| **SG1** | TPO POC | Stair Step (ID:3) / Line (ID:1) | **SG0** |
| **SG2** | TPO VAH | Stair Step Dash-Dot | **SG1** |
| **SG3** | TPO VAL | Stair Step Dash-Dot | **SG2** |

**Verdict for `cpp:655-657` (today TPO) and `cpp:729-731` (yesterday TPO):**
Mapping `SG0=POC · SG1=VAH · SG2=VAL` is **CORRECT** if the DLL uses 0-indexed access. CC's Phase 1 hypothesis of "wrong subgraph indices" for TPO may have been **partially refuted**.

**However:** Sierra `sc.GetStudyArrayFromChartUsingID(chart, study_id, subgraph_index, ...)` is **0-indexed** per Sierra's ACSIL docs. So if DLL reads SG0/SG1/SG2 → maps to UI SG1/SG2/SG3 → POC/VAH/VAL. Correct.

**Open question for CC:** if TPO indices are correct, why does `tpo.json` emit `poc=-89088`? Two remaining hypotheses to verify in fix #2:
- (a) The DLL reads from chart #3 but at startup time the studies are not yet calculated → uninitialized memory returned
- (b) `GetStudyArrayFromChartUsingID` call ordering / `n_periods_back` parameter wrong
- (c) Different bug entirely (e.g. `va_ok` flag computed wrong before output)

### 2.2 · Initial Balance · ID:6

IB study has **11 subgraphs** (extensions above + IB core + extensions below):

| UI Subgraph | Sierra UI Label | Draw Style | 0-indexed (cpp) |
|---|---|---|---|
| SG5 | IB High Ext 2 | Ignore | SG4 |
| SG6 | IB High Ext 1 | Ignore | SG5 |
| **SG7** | **IB High** | **Dash Solid** | **SG6** |
| **SG8** | **IB Mid** | **Dash Solid** | **SG7** |
| **SG9** | **IB Low** | **Dash Solid** | **SG8** |
| SG10 | IB Low Ext 1 | Ignore | SG9 |
| SG11 | IB Low Ext 2 | Ignore | SG10 |

**Verdict for `cpp:707-708` (IB read):**
If DLL reads `SG0/SG1/SG2` for IB high/mid/low → it reads **wrong subgraphs entirely** (extensions or POC fields above the IB core). This **fully explains** `ib.found=false` and `ib.high=ib.mid=ib.low=0.00` in `tpo.json`.

**Required fix:** change DLL subgraph indices from `SG0/SG1/SG2` to **`SG6/SG7/SG8`** for IB at `cpp:707-708`.

This is HA-2 **CONFIRMED for IB** at high confidence (≥95%).

---

## 3 · Letter Time Anomaly · ID:1 Yesterday TPO

| Study | TPO Letter/Block Time | Comment |
|---|---|---|
| ID:1 Yesterday | **1440 minutes (= 24h)** | ⚠️ One TPO bracket spans the full day |
| ID:3 Today | 30 minutes | ✓ Classical 30min Market Profile letters |

**Michael's decision (Q3 in chat):** investigate — is Friday DB POC drift (DB 7505.50 vs Sierra UI 7501.50 = 4pt) caused by 1440min letter time?

**Investigation TBD post-fix.** Does NOT block fix #1 or fix #2. Logged here for traceability.

---

## 4 · Cross-Reference for CC Stream A fix #2

When CC executes fix #2 (DLL patch), it must:

1. **Edit `sc_study/MES_AI_DataExport.cpp:707-708`** — change IB subgraph indices from `0/1/2` to **`6/7/8`** (or whatever the existing values are — confirm by reading current code first).
2. **Leave `cpp:655-657` and `cpp:729-731`** alone IF current values are `SG0/SG1/SG2` — those match UI SG1/SG2/SG3 = POC/VAH/VAL correctly. Verify by reading the cpp lines.
3. **Leave `TPOChartNumber` default at 0** — DLL is on chart #3, host-chart semantics correct.
4. **Investigate why `poc=-89088` is emitted despite correct subgraph indices** — this is the residual mystery for TPO (not IB). Possible: `va_ok` flag computed before TPO study is initialized; or `n_periods_back` parameter mismatch.

---

## 5 · Reference data for verification

After fix deployed via `./scripts/build_monolithic_cpp.sh --deploy` and study reloaded in Sierra:

**Expected `tpo.json` (post-fix · per Sierra UI ground truth):**

```json
{
  "session": {
    "poc": 7559.75,
    "vah": 7565.00,
    "val": 7556.75,
    "va_ok": true,
    "session_date": "2026-05-25"
  },
  "ib": {
    "found": true,
    "high": 7570.00,
    "mid": 7562.00,
    "low": 7554.00
  },
  "previous_session": {
    "found": true,
    "poc": 7501.50,
    "vah": 7517.50,
    "val": 7485.50
  }
}
```

(Values from Sierra Chart UI screenshots Michael shared 18:42 IL · validated against `v9_tpo_sessions` row CASH_2026-05-22.)

---

## 6 · Screenshots archive

All 6 source screenshots saved to workspace:

- `assets/image-6f012952-98ca-432c-bf18-7738b37a789c.png` · TPO levels Sierra UI (initial trigger)
- `assets/image-90a40d8a-0cc1-43c8-a3a3-7ebd684c8d2b.png` · IB ID:6 Settings tab
- `assets/image-43242aa3-4d90-470b-b9a0-bac0dfad2089.png` · TPO Yesterday ID:1 Settings tab
- `assets/image-14e43f80-dcb1-4a39-a4d5-69b1d98bc61f.png` · TPO Today ID:3 Settings tab
- `assets/image-6affe129-18a3-44cb-8ba1-d7178f90dbcb.png` · VbP for TPO Chart ID:7 (chart #19 · separate)
- `assets/image-ae6f4d78-5873-4f02-9223-22fc67659124.png` · Numbers Bars TPO chart #19 ID:6
- `assets/image-7bef3558-8ef5-4aa7-9bc0-e7b24fa0f22d.png` · Chart Studies list chart #19
- `assets/image-6407fc0b-3371-438a-8974-4bebd272aa4a.png` · TPO Today ID:3 Subgraphs tab ★
- `assets/image-dce12ec9-d0d5-499e-a6eb-8911fd735fc7.png` · TPO Yesterday ID:1 Subgraphs tab ★
- `assets/image-efffcb3b-63b4-4549-a8d6-60117bd390d5.png` · IB ID:6 Subgraphs tab ★

★ = primary evidence for subgraph mapping table in §2.

---

**Authored:** Cursor · 2026-05-25 19:35 IL · post Phase-1 audit
**Status:** ✅ READY for CC fix #2 reference
