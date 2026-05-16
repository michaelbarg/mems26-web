# WAVE 1 — S4 Woodies Mini-Audit

**Date:** 2026-05-16  
**Scope:** Decision tree stages A1–B14 skeleton + manifest update  
**Authority:** Master Index V2 + Woodies Decision Tree V1  
**Source:** PROJECT_TRUTH_AUDIT §6 item 1

---

## Current State

| Layer | What exists | Lines | Quality |
|-------|-------------|-------|---------|
| 11 CCI Studies | `cci_calc.py` + DLL | 172 | GREEN — all 11 computed |
| 9 Pattern detectors | `patterns/*.py` (9 files) | ~800 | GREEN — ZLR/TLB/TT/GB100/VEGAS/GHOST/FAMIR/HTLB/HFE |
| Pattern engine | `pattern_engine.py` | 59 | GREEN — detect_all_patterns loop |
| System runtime | `woodies_system.py` | 364 | GREEN — process_bar + calculate_size |
| Direction change | `direction_change_detector.py` | 74 | GREEN — TCCI cross CCI14 |
| calculate_size | in woodies_system.py | ~50 | GREEN — per V2 PART 6 tier map |
| Compliance tests | `test_woodies_compliance.py` | — | 20/20 pass |
| **Decision Tree A1–B14** | **DOES NOT EXIST** | 0 | **RED** |
| **Priority Dispatcher** | **DOES NOT EXIST** | 0 | **RED** |
| **18 Terminal States** | **DOES NOT EXIST** | 0 | **RED** |

---

## What "Decision Tree" Means (from GAPS doc + Spec V1)

The Woodies V1 Decision Tree has **21 stages**:

### A-stages (Pre-fire: pattern detection → entry decision)
| Stage | Name | Status |
|-------|------|--------|
| A1 | Trend Gate (SWI/Trend State filter) | GREEN — `trend_state` computed |
| A2 | Study Validity (all 11 studies present) | GREEN — `compute_all_studies` |
| A3 | Pattern Detection (9 patterns) | GREEN — `detect_all_patterns` |
| A4 | Touch-Points query (6 advisory) | **RED** — not consumed |
| A5 | Auxiliary Alignment (SWI/CZI/TCCI/LSMA/EMA34) | GREEN — in `calculate_size` |
| A6 | Entry Classification (REACTIVE vs INITIATIVE) | **YELLOW** — uses TACTICAL/STRATEGIC |
| A7 | Universal Checks (news/cooldown/cap/stop/bridge/EOD) | **RED** — in gateway, not Woodies |

### B-stages (Active trade management within Woodies)
| Stage | Name | Status |
|-------|------|--------|
| B1–B14 | Active trade management rules | **RED** — all in external trade_manager |

---

## Architectural Question (OPEN — from GAPS doc)

> "Is the Woodies V1 Decision Tree meant to be self-contained with all 21 stages internally, or an orchestration spec where stages map to different backend services?"

**Current architecture:** A1/A3/A5 inside Woodies. A4/A6/A7/B1-B14 in separate services.  
**Spec expectation:** All 21 stages inside the Woodies decision tree.

### Options for Wave 1

**Option A — Full spec compliance (big):**  
Move/duplicate all 21 stages into `backend/v9/systems/woodies/decision_tree/`.  
~500 lines, touches trade_manager territory. Risk: dual ownership.

**Option B — Skeleton + orchestration (pragmatic):**  
Create `decision_tree.py` with 21 stage stubs that delegate to existing services.  
Each stage = a function that either runs internally OR calls external service.  
Manifest updated to track all 21 stages.  
~200 lines, no duplication, clear audit trail.

**Option C — Manifest-only + acceptance (minimal):**  
Document the architectural divergence. Update manifest with 21 stages.  
Mark B1–B14 as "IMPLEMENTED_EXTERNALLY (trade_manager)".  
Mark A4/A7 as "IMPLEMENTED_EXTERNALLY (gateway/pre_fire)".  
~50 lines manifest YAML. No code changes.

---

## Recommendation

**Option B** — because:
1. It creates the skeleton Michael's gate requires ("S4 decision tree")
2. It doesn't duplicate trade_manager logic
3. It provides clear extension points for future per-stage refinement
4. The manifest update makes compliance tests aware of all 21 stages

---

## Proposed Deliverables (if approved)

1. `backend/v9/systems/woodies/decision_tree.py` — 21-stage skeleton
2. Update `compliance_manifest.yaml` — add `decision_tree_stages` section
3. Wire skeleton into `woodies_system.py` process_bar flow
4. Test: `tests/atomic/test_woodies_decision_tree.py`

---

## Pre-existing Issues (do NOT fix in Wave 1)

- HFE pattern in code but grep says "0 results" in GAPS doc — file EXISTS now (149 lines)
- `chart_5min/` vs `five_min/` confusion (separate issue, S2)
- Dual JSON dirs (infra, not S4)
- sc_study uncommitted edits (reviewed separately)

---

**APPROVED: Option B — implemented 2026-05-16**

- `backend/v9/systems/woodies/decision_tree.py`
- Wired in `woodies_system.py` → `current_state.decision_tree`
- `compliance_manifest.yaml` → `decision_tree_stages` (21 rows)
- `tests/atomic/test_woodies_decision_tree.py`
- `docs/v9/WOODIES_DECISION_TREE_MAP.md`

**Next Wave 1b:** A4 HTTP touch-points · Priority dispatcher · 18 terminal states
