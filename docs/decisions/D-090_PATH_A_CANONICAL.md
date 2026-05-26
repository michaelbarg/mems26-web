# D-090 — Path A Canonical (S2 5-Min · Delete Path B)

**Status:** 🔒 LOCKED
**Date:** 2026-05-23
**Decided by:** Michael Barg (strategic review · pre-LIVE planning)
**Supersedes:** Open Questions P-2, P-3, P-4, P-5 (closed by this decision)
**Related:** Master Index V2 · Constitution V3 §T1 · D-089 (S3 Firing)
**Registry:** `docs/reports/MEMS26_SYSTEMS_DECISIONS_REGISTRY_2026-05-23.md` §S2

---

## Context

Two parallel implementations of S2 patterns coexisted in code:

| Path | Location | Routes to gateway? | Lines of code |
|------|----------|---------------------|---------------|
| **Path A** | `backend/v9/systems/five_min/` | ✅ YES — `_gateway.route_setup(2)` | Production code |
| **Path B** | `backend/v9/systems/chart_5min/` | ❌ NO — generates `Signal` only | ~2,000 LOC |

Path B contained 19 detectors (4 with same names as Path A but different semantics, 15 unique chart patterns). Path B ran on every bar but never reached the gateway — pure CPU waste.

`P31_S2_V9_PATTERNS.md` §6 documented 6 DRIFT items (2.A through 2.F) caused by the dual-path coexistence — including different banding (4/6/9/12/13 vs 4/6/10), different confidence scales (0.75-0.80 vs 0.5-0.7), and the same pattern names producing different fires.

---

## Decision

### Path A = canonical · Path B = deleted

- **Path A** at `backend/v9/systems/five_min/` is the single source of truth for S2.
- **Path B** at `backend/v9/systems/chart_5min/` will be **deleted in full** (~2,000 LOC).
- All 6 DRIFT items in `P31_S2_V9_PATTERNS.md` §6 are closed by this deletion.

### Closed Open Questions

| ID | Question | Resolution by D-090 |
|----|----------|---------------------|
| P-2 | Path A or Path B canonical? | **Path A canonical** |
| P-3 | Delete 15 Path-B-only patterns or promote to spec? | **Delete all** — chart patterns to be promoted will be re-implemented in Path A per D-091 |
| P-4 | Banding canonical — 4/6/9/12/13 (Path A) or 4/6/10 (Path B)? | **Path A banding (4/6/9/12/13)** |
| P-5 | Confidence scale — Path A (0.75/0.80) or Path B (0.5-0.7)? | **Path A scale (0.75/0.80)** |

### What stays in Path A

- 4 OFA patterns (Reactive LONG/SHORT, Initiative LONG/SHORT)
- 5 supporting layers (Q0 dispatcher, First Hour Buffer, First Hour Matrix, Confluence Score, Quality Tier)
- `pre_fire_validator` integration
- Gateway routing to `system_id=2`
- All existing compliance manifests

### What gets deleted

- Entire `backend/v9/systems/chart_5min/` directory
- 19 pattern detectors in `chart_5min/patterns/__init__.py`
- 4 tier configurations in `chart_5min/models.py`
- `Chart5MinSystem` class in `chart_5min/system.py`
- `Chart5MinDetector` class in `chart_5min/detector.py`
- Any imports of `chart_5min` elsewhere in the codebase

---

## Sync actions required (post-D-090)

| # | File | Action |
|---|------|--------|
| 1 | `backend/v9/systems/chart_5min/` | **DELETE** entire directory |
| 2 | `backend/v9/app.py` | Remove any imports of `Chart5MinSystem` / `chart_5min.api` |
| 3 | `backend/v9/systems/__init__.py` | Remove `chart_5min` from exports if present |
| 4 | `docs/architecture/for_designer/02_SYSTEMS_SPEC.md` §S2 §6 | Update — REQ-UI-004 "active pattern overlay" remains as forward work, not as Path B reference |
| 5 | Search codebase | `grep -r "chart_5min" backend/` — verify zero references remain |
| 6 | Tests | Remove any tests under `tests/v9/systems/test_chart_5min/` if exist |

---

## Implementation order

1. **Search** — `rg "chart_5min" --type py` to inventory all references
2. **Validate** — confirm no production code path imports from `chart_5min`
3. **Delete** — remove directory + all imports
4. **Test** — `pytest tests/v9/` must remain green
5. **Commit** — `git rm -r backend/v9/systems/chart_5min/`

---

## Rationale

1. **CPU waste:** Path B ran 19 detectors on every 5-min bar, never used the results. Pure waste.
2. **Code clarity:** Two implementations of the same pattern names with different semantics is a maintenance hazard — a developer searching for "reactive_buyer" finds two different functions.
3. **Spec drift surface:** 6 DRIFT items in `P31_S2_V9_PATTERNS.md` §6 all originate from the dual-path coexistence.
4. **Forward path:** Per D-091 (Scope), 6 new patterns will be implemented in Path A directly (Bull/Bear Flag, Double Bottom/Top, Inverse H&S, H&S Top). These will use Path A's V9 architecture (Footprint live, COT/AMT, pre_fire_validator) rather than Path B's standalone style.

---

## Risk acknowledgement

- **Loss of CPU benchmark:** Path B was a useful reference for "what 19 detectors at every bar costs". Post-deletion, future performance baselines should be re-measured.
- **No backward path:** Deletion is via `git rm` — recoverable from git history only.
- **Patterns currently in Path B that will not be in scope post-deletion** (per D-091): Pennant, Wyckoff Spring/UTAD, Wedges (Rising/Falling), Triangles (Asc/Desc/Sym), Cup & Handle. These remain available for future promotion via Constitution V3 amendment.

---

*End of D-090. Sign-off: Michael Barg, 2026-05-23.*
