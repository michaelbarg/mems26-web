# P5-0 — Gateway Audit (D-093.Q1 Recommendation)

**Date:** 2026-05-31  
**Agent:** Claude Code (Opus 4.6)  
**Type:** READ-ONLY audit — zero code changes  
**Context:** Two TradingGateway implementations coexist. This report recommends canonical path.

---

## 1 · File Classification (KEEP / ADAPT / REPLACE / DEFER)

### KEEP — Legacy Gateway (ACTIVE, production-wired)

**File:** `backend/v9/gateway/trading_gateway.py` (368 lines)  
**Wiring:** `main.py:384` → `from backend.v9.gateway import TradingGateway`

**Verbatim — Safety gates (lines 88-134):**
```python
# ζ.A4 Cooldown
if self.cooldown.is_blocked():
    return {"rejected": True, "reason": "cooldown_blocked"}

# ζ.B2 Suffering Side Veto
if self.ssv.check_veto(direction):
    return {"rejected": True, "reason": "ssv_veto", "direction": direction}

# ζ.F2 Chop State
chop_state = self._get_chop_state()
if chop_state == "SEARCHING":
    return {"rejected": True, "reason": "chop_searching"}

# Record for cluster guard
self.cluster_guard.record_attempt()

# ζ.A5 Cluster Guard (DEMO/LIVE only)
if self.cluster_guard.is_blocked():
    # SHADOW still records per D-088
    ...

# ζ.C3 Strict Checks (LIVE only)
if not passes_strict_checks(setup, "live", self):
    return {"rejected": True, "reason": "risk_checks_failed"}
```

**Classification: KEEP + ADAPT**  
**Rationale:** All 5 safety gates are active and battle-tested. DEMO path works. LIVE is a stub.  
The gateway has earned trust through SHADOW operation. Adapt by: (1) parameterize account, (2) implement LIVE execution, (3) integrate RiskValidator for LIVE.

---

### ADAPT — Risk Guards (ACTIVE, part of legacy)

| File | Lines | Gate | Classification |
|------|-------|------|---------------|
| `backend/v9/gateway/cooldown.py` | 93 | ζ.A4 Cooldown + ζ.A5 Cluster | KEEP |
| `backend/v9/gateway/suffering_side_veto.py` | 64 | ζ.B2 SSV (D-049) | KEEP |
| `backend/v9/gateway/risk_checks.py` | 76 | ζ.C3 Strict checks | KEEP |

No changes needed. These are correct and comprehensive.

---

### ADAPT — Sierra Command (ACTIVE, shared utility)

**File:** `backend/v9/services/sierra_command.py` (90 lines)

**Verbatim — Account injection (lines 48, 62-64):**
```python
def write_trade_command(action, trade_id, direction, price, contracts,
                        stop_price, target_price, account, mode, context=None):
    payload = {
        "action": action,
        ...
        "account": account,  # ← caller injects, no hardcoding here
    }
```

**Classification: KEEP**  
**Rationale:** Clean separation. Account is parameterized. Ready for IronBeam migration — just change the caller's constant.

---

### DEFER — New Gateway (DEAD CODE, test-only)

**File:** `backend/v9/services/trading_gateway/gateway.py` (217 lines)

**Verbatim — RiskValidator integration (live.py:54):**
```python
def execute(self, setup) -> Tuple[bool, int, str]:
    result = self._risk_validator.check_setup(setup, AccountState(mode="LIVE"))
    if not result.allowed:
        return (False, 0, result.reason)
    trade_id = self._trade_manager.accept_setup(setup, mode="live")
    return (True, trade_id, "")
```

**Classification: DEFER (do not delete, do not wire)**  
**Rationale:** Clean architecture but **missing cooldown/SSV/cluster/chop gates**. A cutover would regress safety. The RiskValidator W14 logic is worth extracting and integrating into legacy gateway for LIVE mode.

---

### DEFER — Bridge Handler (ACTIVE, account-agnostic)

**File:** `bridge/trade_commands.py` (193 lines)

**Verbatim — Pass-through (lines 90-94):**
```python
# Write full command to SC path (account string flows through untouched)
with open(self.sc_command_path, 'w') as f:
    json.dump(command_payload, f, indent=2)
```

**Classification: KEEP**  
**Rationale:** Bridge is correctly account-agnostic. DLL receives whatever account backend sends. No change needed here — account validation belongs in the backend.

---

## 2 · D-093.Q1 Recommendation

### RECOMMENDATION: **MERGE** (Legacy base + New components)

### RATIONALE:

1. **Safety first:** Legacy gateway has 5 proven pre-trade gates (cooldown, SSV, chop, cluster, strict checks). New gateway has **zero** of these. A cutover to New = immediate safety regression in DEMO and future LIVE.

2. **LIVE readiness:** Legacy LIVE is a stub (`logger.warning("NOT sent")`). New has clean executor + RiskValidator. Merge = extract RiskValidator + LiveExecutor logic and **add to legacy gateway's `_execute_live()` method**, preserving all upstream gates.

3. **Account migration ready:** `sierra_command.py` already parameterizes account. Legacy gateway's hardcoded `PA-APEX-125218-01` is one constant swap away from IronBeam `37138283`.

### RISK IF WRONG:

If we do LEGACY-only (never merge RiskValidator): LIVE mode enabled without W14 risk caps → unlimited daily loss possible.  
If we do NEW-only (replace legacy): lose cooldown/SSV/cluster/chop gates → over-trading in DEMO/LIVE.  
**MERGE has lowest risk:** keep all gates, add LIVE capability.

### MIGRATION PATH:

```
P5-1: Swap DEMO account PA-APEX → IronBeam 37138283 (one constant)
P5-2: Extract RiskValidator.check_setup() → call in legacy _execute_live()
P5-3: Implement _execute_live() to call sierra_command.write_trade_command()
P5-4: Wire heartbeat/ladder if needed (D-093 Re-lock decisions)
P5-5: Enable LIVE for S2/S4 after soak + Michael approval
```

---

## 3 · Dead-Code Map

### Confirmed DEAD (zero production imports):

| File | rg import check | Status |
|------|----------------|--------|
| `backend/v9/services/trading_gateway/gateway.py` | only in tests | DEAD |
| `backend/v9/services/trading_gateway/executors/shadow.py` | only via gateway (dead) | DEAD |
| `backend/v9/services/trading_gateway/executors/demo.py` | only via gateway (dead) | DEAD |
| `backend/v9/services/trading_gateway/executors/live.py` | only via gateway (dead) | DEAD |
| `backend/v9/services/risk_validator/validator.py` | only via LiveExecutor (dead) | DEAD |

**Note:** Do NOT delete yet — RiskValidator logic will be extracted in P5-2.

---

## 4 · Apex Account Map

### `PA-APEX-125218-01` (DEMO — dead account, migrating to IronBeam)

| Location | Line | Context | Action in P5 |
|----------|------|---------|-------------|
| `backend/v9/gateway/trading_gateway.py` | 280 | `account="PA-APEX-125218-01"` in `_execute_demo()` | REPLACE → `37138283` |
| `backend/v9/services/trading_gateway/executors/demo.py` | 16 | `SIERRA_DEMO_ACCOUNT = "PA-APEX-125218-01"` | REPLACE or DELETE (dead code) |
| `backend/v9/services/trading_gateway/gateway.py` | 5 | docstring reference | REPLACE or DELETE |
| Multiple test files | various | test fixtures | UPDATE when account changes |

### `APEX-125218-13` (LIVE — new gateway only, dead path)

| Location | Line | Context | Action in P5 |
|----------|------|---------|-------------|
| `backend/v9/services/trading_gateway/executors/live.py` | 20 | `SIERRA_LIVE_ACCOUNT = "APEX-125218-13"` | EVALUATE — is this the IronBeam LIVE account? |
| `backend/v9/services/trading_gateway/gateway.py` | 6 | docstring | same |

### `37138283` (IronBeam — target, docs only)

| Location | Context |
|----------|---------|
| `docs/plans/PIPELINE5_ACTION_PLAN_2026-05-31.md` | Migration target |
| `docs/plans/STATUS_BOARD.md` | P5 reference |
| `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md` | Decision document |

**Not in code yet.** Will be introduced in P5-1 (one-constant swap in legacy gateway).

---

## 5 · D-093 Ancillary Decisions

### Re-lock 1: BuyEntry + Attached Order (bracket)

**Relevant code:** `sierra_command.py:70-88` — builds command payload with `stop_price` and `target_price`. DLL must create bracket from these.

**Finding:** Current command structure supports bracket (stop + target in same payload). Sierra DLL must honor Attached Order semantics — validated in DLL ops log.

**Status:** No code change needed. DLL responsibility.

### Re-lock 2: ModifyOrder (trail)

**Relevant code:** `bridge/trade_commands.py:72` — VALID_ACTIONS includes `MODIFY`.  
**Finding:** MODIFY action is accepted by bridge but **not emitted by any backend code currently**. Trail engine (`backend/v9/services/trail_engine.py`) exists but its integration with sierra_command is unclear.

**Status:** P5-4 scope. Trail → MODIFY command path needs wiring.

### Heartbeat Ladder

**Finding:** No heartbeat/ladder mechanism in current code. Neither legacy nor new gateway implements periodic order status polling or Sierra DLL heartbeat.

**Status:** P5-4 scope. Decision needed: does DLL provide fill notifications via result file, or do we poll?

---

## Summary

| Decision Point | Recommendation | Confidence |
|---------------|---------------|------------|
| D-093.Q1: Which gateway? | **MERGE** (legacy base + RiskValidator from new) | HIGH |
| Account migration | One-constant swap in P5-1 | HIGH |
| Safety gates | KEEP all 5 in legacy | CRITICAL |
| Dead code | DEFER deletion until P5-2 extracts RiskValidator | MEDIUM |
| LIVE execution | Implement in legacy `_execute_live()` using sierra_command | HIGH |
| Re-lock / heartbeat | P5-4 scope, not blocking P5-1/2/3 | — |

**Gate:** This report is a recommendation. No code changes made. P5-1+ awaits Michael's decision lock.
