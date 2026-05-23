# P30 Wave 0 CC Verify — Errata (Cursor · post-Michael D-087)

**Date:** 2026-05-20  
**Original:** `P30_WAVE_0_CC_VERIFY.md` — verdict **GO-WITH-NOTES** stands  
**Purpose:** Correct two CC findings and separate D-087 from `cluster_guard`

---

## 1. FAIL #7 (S2 pre_fire) — **overturned → PASS**

| CC claim | Fact in repo |
|----------|----------------|
| `five_min_system.py:556` calls `route_setup` with no `validate_fire` | Line 556 runs **only after** `emit_t1_setup()` returns non-None |
| | `setup_emitter.py:70-85` calls `validate_fire()`; rejects return `None` → no `route_setup` |

**Path (unchanged from P0.5):**

```
FIRE → emit_t1_setup() → validate_fire (setup_emitter:81) → route_setup (:556)
```

**Evidence:** `docs/reports/P30_S2_PF_VERIFY.md`  
**Action:** No S2 code for Wave 1 on this item. CC checklist should grep `emit_t1_setup` before `route_setup`, not line 556 alone.

---

## 2. D-087 vs cluster_guard — **do not conflate**

| Topic | What it is | Michael decision |
|-------|------------|------------------|
| **D-087** | Registry §18 (20 CRITICAL / 23 HIGH SPECIFIED) | **LOCKED** — waived for SHADOW soak only; enforced before LIVE |
| **cluster_guard** | D-037 runtime: 5 attempts / 60s → 5 min block | **Not** part of D-087. Policy table: GW-02 only (P0.5 ✅); **not** “skip in SHADOW” (locked 20/5) |

CC note #37–38 suggested “sign D-087 to accept cluster_guard blocking” — **incorrect linkage**.  
Signing D-087 lets you start soak **on Registry paperwork**; it does **not** restore Woodies SHADOW rows.

### What cluster_guard does today

```83:86:backend/v9/gateway/trading_gateway.py
        if self.cluster_guard.is_blocked():
            result["blocked_by"] = "cluster_guard"
            logger.info("[Gateway] BLOCKED by cluster guard D-037")
            return result
```

Early `return` → **no** `_execute_shadow()` → zero SHADOW DB rows during block window.

Constants: `CLUSTER_MAX_TRADES = 5`, `CLUSTER_WINDOW_SEC = 60` (`cooldown.py`).

Woodies can emit many `route_setup` calls per RTH window → guard trips → WARN #5.

### Timeline note (CC reports)

| Time (ET) | Report | cluster_guard |
|-----------|--------|----------------|
| ~16:06 | Wave 0 verify | WARN — all Woodies SHADOW blocked |
| ~17:20–17:21 | CC_STATUS §4b | 4 TLB LONG SHADOW fires — guard not active |

Guard is **stateful** (5-min block cycles), not permanently broken.

### GW-02 (P0.5) vs CC_STATUS GW-2 row

- **P0.5 fix:** `record_attempt()` **after** gates (`trading_gateway.py:98-99`) — commit `8dd1ffb`
- CC_STATUS **GW-2 CONFIRMED BUG** (17:22) cites old line 78 — **stale**; do not reopen GW-02

---

## 3. Revised Wave 0 scorecard

| # | Check | Original | After errata |
|---|--------|----------|--------------|
| 7 | S2 pre_fire | FAIL | **PASS** (path verified) |
| 5 | Woodies SHADOW | WARN | **WARN** (unchanged — operational) |
| — | D-087 | pending | **LOCKED** — Registry §18 waived for SHADOW |

**Counts:** 7 PASS, 1 FAIL (latency cold-start), 2 WARN, 1 N/A  
**Verdict:** **GO-WITH-NOTES** for Registry + infrastructure; **SHADOW data gap** needs separate decision

---

## 4. Options for cluster_guard (Michael pick — **not** D-087)

| Option | ID | Effect | Conflicts with 20/5 lock? |
|--------|-----|--------|---------------------------|
| A | **D-088** | SHADOW always `_execute_shadow`; cluster blocks DEMO/LIVE only | Yes — needs explicit new decision |
| B | Code | Raise `CLUSTER_MAX_TRADES` (e.g. 20) in SHADOW via env | Yes — “לא MAX_TRADES” unless D-088 |
| C | Ops | Soak during quiet windows; accept sparse SHADOW | No code |
| D | Wait | 5-min block expires; retry | No code — poor soak density |

**Recommendation:** **D-088 Option A** — smallest correct fix for “SHADOW unlimited record-only” (3-Mode Spec §8). One strategic stop before Cursor implements.

---

## 5. Still valid from CC report

- **FAIL #2 latency** — cold start / loaded event loop; re-test warm calls
- **WARN #4** — FP SQLite thread errors (P0.5 journal fix partial; chronic count)
- **PASS** — backend, 4 axes sample, GW-CHOP, Sierra 29/29, pytest
- **N/A #6** — no S3 SHADOW in that log window (D-086 still applies if fires later)

---

*Errata only · no gateway code change in this file*
