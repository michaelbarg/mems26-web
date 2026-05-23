# P30 — Fire Blockers Summary (2026-05-20 17:25 ET)

**Purpose:** 1-page summary of what blocks SHADOW/DEMO/LIVE fire right now.

---

## Gateway Fire Path (from code)

```
route_setup(setup, system_id)
  → cluster_guard.record_attempt()     ← BUG: counts before gates
  → cooldown blocked?                  → return blocked_by=cooldown
  → cluster_guard blocked?             → return blocked_by=cluster_guard
  → SSV blocked?                       → return blocked_by=suffering_side_veto
  → chop_searching?                    → return blocked_by=chop_searching  ← self-HTTP, likely timeout
  → _execute_shadow()                  ← SHADOW fires here
  → DEMO (if enabled + slot free)
  → LIVE (if enabled + slot free + risk checks)
```

## Current State (2026-05-20 17:21 ET, from backend log)

| Gate | Active? | Evidence |
|------|---------|----------|
| cooldown (2-stop) | **No** | No STOP outcomes in session |
| cluster_guard (5/60s) | **No** (but risk of false trigger) | 4 SHADOW trades in 12s — 1 more would trigger 5-min block |
| SSV | **No** | All trades LONG, no veto |
| chop_searching | **Effectively disabled** | Self-HTTP to `localhost:8000` times out → returns UNKNOWN → no block |
| DEMO | Not enabled | `_demo_enabled_systems` empty |
| LIVE | Not enabled | `_live_enabled_systems` empty |

## Trades Fired This Session

| Time ET | System | Direction | Pattern | Size | Trade ID |
|---------|--------|-----------|---------|------|----------|
| 17:20:41 | S4 | LONG | TLB | half | cb0d0581 |
| 17:21:09 | S4 | LONG | TLB | half | a731de4b |
| 17:21:22 | S4 | LONG | TLB | half | 1e4201a3 |
| 17:21:29 | S4 | LONG | TLB | half | db0d9bed |

## Bugs Blocking Correct Fire Behavior

| ID | Bug | Impact | Fix |
|----|-----|--------|-----|
| GW-02 | `record_attempt()` before gates | Blocked routes count toward cluster_guard → false 5-min blocks after 5 rapid patterns | Move `record_attempt()` after L100 (after all gates pass, before `_execute_shadow`) |
| GW-CHOP | `_get_chop_state()` self-HTTP | 2s blocking call to own server in `route_setup` path; returns UNKNOWN on timeout | Replace with in-process lookup of Layer 0 state |
| BE-HTTP | Backend HTTP unresponsive | Cannot query `/gateway/risk` or `/gateway/status` to verify gate states | Fix event-loop saturation |

## S2/S3/S4 Gateway Interaction

| System | `ready_to_route` | Last `blocked_by` | Fire? |
|--------|------------------|-------------------|-------|
| S2 (5-Min) | Unknown (API down) | Unknown | No fires in log (likely OVERNIGHT_MODE) |
| S3 (Footprint) | Unknown (API down) | `cluster_guard` (per last snapshot) | No fires in log |
| S4 (Woodies) | `true` (per last snapshot) | None active | **YES** — 4 SHADOW trades |

---

*Generated: Claude Code · 2026-05-20 · no code changes*
