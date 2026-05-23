# D-089 — S3 Footprint = FIRING (locked)

**Status:** 🔒 LOCKED
**Date:** 2026-05-23
**Decided by:** Michael Barg (strategic review · pre-LIVE)
**Supersedes:** D-082 (S3 = Observer-only per V3 spec), D-086 (S3 SHADOW firing path tolerated, defer to post-SHADOW)
**Related:** Master Matrix V1.0 (`backend/v9/systems/wrappers.py:8-14`), Footprint Spec V3 (`1iPndwDKwYn70pXCwkHNJVyAwLeU8WislDGAQX3HXvT4`)
**Registry doc:** `docs/reports/MEMS26_SYSTEMS_DECISIONS_REGISTRY_2026-05-23.md`

---

## Context

Conflict between two locked sources:

| Source | Position | Date |
|---|---|---|
| **Master Matrix V1.0** (`wrappers.py:9`) | S3 = Firing (one of 3: S2, S3, S4) | older |
| **Footprint Spec V3** (Drive `1iPn...XvT4`) | S3 = Observer only | newer at the time |
| **D-082** | S3 = Observer only per V3 spec | LOCKED |
| **D-086** (`P30_DECISION_D086_S3_FIRING.md`) | S3 SHADOW firing path tolerated, "revisit before LIVE" | LOCKED 2026-05-20 |
| **Code state today** | `footprint_system.py::_fire()` calls `route_setup(3)` with `if mode == "LIVE":` safety net | active |
| **types.ts (22/5 commit `2bc6796`)** | S3 → 'observer' per D-082 | 22/5 |

D-086 §"Conditions" explicitly states: "Must be revisited **before LIVE**". The revisit has happened (this decision).

---

## Decision (Michael · 2026-05-23)

### S3 = **FIRING system** (one of three: S2, S3, S4)

- **Restores** Master Matrix V1.0 designation (already reflected in `wrappers.py:8-14`)
- **Supersedes** D-082 (Observer-only spec)
- **Supersedes** D-086 (deferred fix to post-SHADOW)
- **No spec V4 doc required** — Master Matrix V1.0 is the authority for system roles; Footprint Spec V3 §detector behavior remains in effect (4 detectors: Absorption, Stacked Imbalance, Sweep+Return, Exhaustion).

### `if mode == "LIVE":` safety net = **KEEP**

- Location: `backend/v9/systems/footprint/footprint_system.py::_fire()`
- Status: **Do not remove** until Michael explicitly says otherwise.
- Rationale: even though S3 is now an authorized firing system, the safety net was designed by D-082 for a defensive purpose. Removal requires data-backed decision (post-SHADOW).
- This means **S3 fires in SHADOW today** via the same gated path as before D-089.

---

## Scope — what D-089 does and does NOT change

### Does change

| Item | Before | After |
|------|--------|-------|
| S3 role label | Observer (per D-082) | **Firing** |
| `types.ts` `SYSTEM_ROLES[3]` | `'observer'` | **`'firing'`** |
| Registry, audits, plans referring to "3 firing systems" | S2, S4, and S3-tolerated-firing | **S2, S3, S4** (canonical) |
| D-086 disposition | "tolerated, revisit before LIVE" | **closed by D-089** |

### Does NOT change

| Item | Status |
|------|--------|
| S3 firing code path (`footprint_system.py::_fire()`) | UNCHANGED (already exists with safety net) |
| `if mode == "LIVE":` safety net | **KEEP** (Michael 23/5) |
| 4 footprint detectors (Absorption, Stacked Imbalance, Sweep+Return, Exhaustion) | UNCHANGED |
| `pre_fire_validator` integration | UNCHANGED |
| Gateway gates (cooldown, cluster_guard, SSV, chop) | UNCHANGED |
| `wrappers.py:8-14` header text | Already says "Firing: S2, S3, S4" — Master Matrix V1.0 was correct; the spec drift was D-082+D-086, not the code |
| DEMO slot | NOT enabled for S3 — post-SHADOW decision |
| LIVE slot | NOT enabled for S3 — post-LIVE-pilot decision |

---

## Pre-LIVE obligations (still required)

D-089 unlocks S3 as a firing system **conceptually**, but does NOT bypass:

1. **S3 entry/stop/T1/T2 spec audit** — detectors only return `{signal, direction, level, strength}`. The actual entry/stop/T1/T2 are computed in `backend/v9/shared/pre_fire_validator.py` or `footprint_system.py::calculate_size` (must be documented before LIVE).
2. **SHADOW soak** with S3 firing (≥20 trades, 4h green)
3. **DEMO soak** with Sierra Sim
4. **P-L0 Preflight** (kill-switch, Registry §18 per D-087)
5. **P-L1 LIVE micro** (1 contract, 1 day)

---

## Sync actions required (post-D-089)

These are not behavioral changes — they are documentation/role-label syncs:

| # | File | Change | Owner |
|---|------|--------|-------|
| 1 | `frontend/v9/src/v9/types/index.ts:222-236` | `SYSTEM_ROLES[3]: 'observer'` → `'firing'`. Comment block to cite D-089 (replaces D-082+D-086 citation). | Cursor agent |
| 2 | `backend/v9/systems/wrappers.py:8-14` | Header text already correct (says Firing: 2,3,4). Add reference to D-089 in note. | Cursor agent |
| 3 | `docs/reports/MEMS26_SYSTEMS_DECISIONS_REGISTRY_2026-05-23.md` §6.1 | Update D-089 status from "pending doc" to "LOCKED · doc at `docs/decisions/D-089_S3_FIRING_LOCKED.md`" | Cursor agent |
| 4 | `docs/handoff/P31_TASK_BOARD.md` §0 | Add D-089 lock entry + flip blocker from "S3 spec ambiguity" to "S3 entry/stop spec audit (pre-LIVE)" | Cursor agent |

---

## Comparison to D-086 (clarity)

| Capability | D-086 (2026-05-20) | D-089 (2026-05-23) |
|------------|--------------------|--------------------|
| S3 role | Observer (with tolerated firing path) | **Firing** (canonical) |
| Observer journal (`v9_footprint_journal`) | Yes | Yes (unchanged) |
| Signal detection + sizing | Yes | Yes (unchanged) |
| `pre_fire_validator` | Yes | Yes (unchanged) |
| SHADOW row in `v9_trades` | Yes (as tolerated violation) | Yes (as authorized fire) |
| `last_fire` / Plan tab reasoning | Yes | Yes (unchanged) |
| Sierra order / broker execution | No | No (DEMO/LIVE slots remain disabled) |
| DEMO slot | No | No |
| LIVE slot | No | No |
| Full active-trade lifecycle (BE, scale, time stop, EOD) via B-stages | No (S2/S4 only) | No — **pending post-SHADOW spec** |
| `if mode == "LIVE":` safety net | n/a (S3 was Observer) | **KEEP** until explicit removal |
| Disposition | "revisit before LIVE" | **CLOSED by D-089** |

---

## Plain language (for handoff)

- S3 (Footprint) הוא מערכת **יורה** (firing) רשמית מ-23/5.
- שום שינוי בקוד הירייה הקיים — `_fire()` עם safety net נשארים כפי שהם.
- ההבדל היחיד היום: התיוג ב-`types.ts` עובר ל-'firing', ה-Registry מתעדכן, ו-D-082+D-086 נסגרים.
- כל הdiscussions בעתיד שמדברים על "3 firing systems" → S2, S3, S4 (סופי).
- לא דורש שינויי trading logic, לא דורש שינוי בdetectors, לא דורש שינוי בstops/targets.
- Pre-LIVE blocker חדש שנחשף: spec audit של S3 entry/stop/T1/T2 (איפה מחושב בקוד) — לפני LIVE micro.

---

## Linked documents

| ID | Relationship |
|----|--------------|
| D-082 | **SUPERSEDED** (S3 Observer-only spec V3) |
| D-086 (`docs/reports/P30_DECISION_D086_S3_FIRING.md`) | **SUPERSEDED** (tolerated firing path · "revisit before LIVE") |
| D-087 (`docs/decisions/D-087_REGISTRY_WAIVER.md`) | Independent — Registry §18 waiver remains |
| D-088 (`docs/decisions/D-088_CLUSTER_GUARD_SHADOW.md`) | Independent — cluster_guard policy unchanged |
| Master Matrix V1.0 | **AUTHORITY RESTORED** for system roles |
| Footprint Spec V3 | Detector behavior unchanged; role label deprecated |
| Registry V1 (`docs/reports/MEMS26_SYSTEMS_DECISIONS_REGISTRY_2026-05-23.md`) | Updates §6.1 |

---

*End of D-089. Sign-off: Michael Barg, 2026-05-23.*
