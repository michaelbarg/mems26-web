# P30 L4 — Risk Surface Audit (#14)

**Date:** 2026-05-21  
**Owner:** Cursor (read-only code audit)  
**Scope:** `firewall.json`, `system_5/risk_engine`, daily-loss kill switch, max-position lock, gateway risk path  
**Out of scope:** `sc_study/`, `bridge/`, service restarts (per Michael 2026-05-21)  
**Live HTTP:** Backend not listening on `:8000` at audit time — curl probes deferred.

---

## Verdict

| Gate | Result |
|------|--------|
| **L4 audit complete** | ✅ YES — findings documented below |
| **GO for SHADOW soak (P-S0)** | ✅ YES — SHADOW bypasses LIVE strict checks; D-088 cluster_guard behavior locked |
| **GO for LIVE trading** | 🔴 **NO-GO** — dual gateway stack, unwired W14 validator, missing caps, no PANIC kill-switch |

Michael sign-off requested on: accept SHADOW with listed gaps vs block P-S0 until P0 fixes land.

---

## 1. Inbox targets — existence check

| Inbox reference | Repo reality | Classification |
|-----------------|--------------|----------------|
| `firewall.json` | **NOT FOUND** (repo-wide grep; not in `docs/spec_authority` either) | **DEFER / SPEC GAP** — planned in `PROMPT_LIST_TO_LIVE.md` (PANIC + `POST /api/v9/admin/kill` + `scripts/kill_live.sh`), not implemented |
| `system_5/risk_engine` | **NOT FOUND** — S5 in registry/compliance = **TPO observer**, not risk | **MISLABEL** — actual risk lives under `backend/v9/gateway/` + `backend/v9/services/risk_validator/` |
| Daily-loss kill switch | **PARTIAL** — see §2 | **ADAPT** before LIVE |
| Max-position lock | **PARTIAL / BROKEN** — constant exists, not enforced on active path | **FIX** before LIVE |

---

## 2. Active production path (what actually runs)

`backend/main.py` wires **`backend.v9.gateway.TradingGateway`** (`backend/v9/gateway/trading_gateway.py`), not `backend/v9/services/trading_gateway/gateway.py`.

```
Firing systems (S2/S3/S4) → route_setup()
  → cooldown (2-stop / 30 min)
  → SSV (suffering-side veto)
  → chop_state == SEARCHING → block
  → cluster_guard (D-088: SHADOW still records)
  → SHADOW (always if past gates)
  → DEMO if enable_demo(system_id)  [never called in repo]
  → LIVE if enable_live(system_id) + passes_strict_checks()  [never called in repo]
```

**API:** `GET /api/v9/gateway/status` (daily_pnl, trades_today, slots), `GET /api/v9/gateway/risk` (cooldown, cluster_guard, ssv, chop only).

---

## 3. LIVE risk caps — active `risk_checks.py`

File: `backend/v9/gateway/risk_checks.py`  
Used only when `enable_live()` has been called and `passes_strict_checks(setup, "live", gateway)` runs.

| Cap (3-Mode Spec §5) | Implemented? | Notes |
|----------------------|--------------|-------|
| Time cutoff 14:30 ET | ✅ | |
| Daily loss $250 | ✅ | Uses `gateway._daily_pnl <= -250` |
| Max trades/day 5 | ✅ | Uses `gateway._daily_trades` |
| Consecutive losses 2 → stop day | ✅ | |
| News ±10 min | ❌ | Commented placeholder; no calendar |
| **Max position 2 contracts** | ❌ | `MAX_CONTRACTS = 2` defined but **never checked** |
| Manual override for size > 1 | ❌ | Not in `passes_strict_checks` |

**State reset:** `TradingGateway.reset_daily()` exists but **no caller** in `main.py` or schedulers — counters persist until process restart.

**Updates on close:** `on_trade_close` increments `_daily_trades` / `_daily_pnl` only for **LIVE slot** trades. SHADOW PnL via TradeManager does not feed gateway LIVE caps today.

---

## 4. Parallel stack — NOT wired (W14)

| Component | Path | Wired in `main.py`? |
|-----------|------|---------------------|
| W14 `RiskValidator` | `backend/v9/services/risk_validator/validator.py` | ❌ |
| Alt `TradingGateway` + LiveExecutor | `backend/v9/services/trading_gateway/` | ❌ |
| Tests | `tests/v9/services/test_risk_validator.py`, `tests/v9/services/test_trading_gateway.py` | Cover **alt** stack only |

W14 implements full §5 order including news calendar (`news_calendar.py`), position size, manual override, and `daily_reset()`. **None of this runs in production.**

---

## 5. Additional gates (gateway pre-LIVE path)

| Gate | File | SHADOW | DEMO/LIVE |
|------|------|--------|-----------|
| 2-stop cooldown 30 min | `gateway/cooldown.py` | Blocks all modes | Same |
| Cluster guard D-037 | `gateway/cooldown.py` ClusterGuard | SHADOW records; DEMO/LIVE blocked (D-088) | ✅ tested `test_d088_shadow_cluster_guard.py` |
| SSV D-049 | `gateway/suffering_side_veto.py` | Blocks | Blocks |
| Layer0 chop SEARCHING | `trading_gateway._get_chop_state()` | Blocks | Blocks |

---

## 6. Woodies A7 — second daily-loss number

`backend/v9/systems/woodies/stages/a7_universal_checks.py`:

- `DAILY_LOSS_CAP_USD = **200**` (Woodies entry phase)
- Gateway LIVE cap = **250**

If A7 is evaluated with live `daily_pnl`, limits disagree. **Unify to one spec value before LIVE.**

Woodies `position_size` can be **3** (Initiative) in A6 while gateway LIVE path does not enforce max contracts at all.

---

## 7. Mode / activation surface

| Control | Location | Current behavior |
|---------|----------|------------------|
| `MEMS26_MODE` | `.env` / `backend/v9/api/v9/status.py` | Default `shadow`; exposed in status |
| `enable_demo` / `enable_live` | `trading_gateway.py` | **No production caller** — DEMO/LIVE slots never arm unless future API/admin adds it |
| `_execute_live` | `trading_gateway.py` | **Stub** — logs warning, does not send Sierra command |
| PANIC / admin kill | — | **Not implemented** (spec only in `PROMPT_LIST_TO_LIVE.md`) |

---

## 8. Findings ranked for LIVE

| ID | Severity | Finding | Recommended action |
|----|----------|---------|-------------------|
| R1 | 🔴 BLOCKER | Two gateway implementations; production uses thinner `risk_checks`, not W14 | **REPLACE or ADAPT:** wire `RiskValidator` into active gateway **or** delete/deprecate alt stack to one path |
| R2 | 🔴 BLOCKER | `MAX_CONTRACTS` not enforced | Add size check in `passes_strict_checks` + regression test |
| R3 | 🔴 BLOCKER | No operational kill-switch (`firewall.json` / admin kill / PANIC) | Implement per `PROMPT_LIST_TO_LIVE.md` before L7 |
| R4 | 🟠 HIGH | News window missing on active path | Port W14 `is_in_news_window` into `risk_checks` or delegate to W14 |
| R5 | 🟠 HIGH | `reset_daily()` never scheduled | Midnight ET hook or session-open in `main.py` |
| R6 | 🟠 HIGH | SHADOW PnL not tied to LIVE daily caps | Define whether LIVE caps read DB aggregate or gateway-only |
| R7 | 🟡 MEDIUM | A7 $200 vs gateway $250 | Single constant + doc |
| R8 | 🟡 MEDIUM | `/gateway/risk` omits daily_pnl / trades_today | Extend API for cockpit risk panel (optional) |
| R9 | 🟡 MEDIUM | No tests for `risk_checks.py` | Add `tests/v9/gateway/test_risk_checks.py` |
| R10 | 🟢 INFO | `firewall.json` / `system_5/risk_engine` are inbox naming drift | Update inbox L4 wording in next edit |

---

## 9. SHADOW soak (P-S0) — risk posture

**Acceptable for soak** with eyes open:

- SHADOW/DEMO bypass `passes_strict_checks` (by design).
- `enable_live` not called → no accidental LIVE slot in code path today.
- Cluster guard + cooldown + SSV + chop still shape **attempt** behavior; D-088 preserves SHADOW rows for analysis.
- Gaps R1–R3 are **LIVE blockers**, not SHADOW soak blockers.

**Michael decision:** Proceed P-S0 while scheduling R1–R3 in POST-SHADOW row (`P30_PRIORITY_TASK_TABLE.md`).

---

## 10. Verification checklist (when backend is up)

```bash
curl -s --max-time 5 http://127.0.0.1:8000/api/v9/gateway/status | jq '{daily_pnl,trades_today,consecutive_losses,live_slot,demo_slot,shadow_active_count}'
curl -s --max-time 5 http://127.0.0.1:8000/api/v9/gateway/risk | jq .
curl -s --max-time 5 http://127.0.0.1:8000/api/v9/status | jq '{mode: .trading_mode // .mode}'
```

Expect: `live_slot=null`, `demo_slot=null`, `mode=shadow` during soak.

---

## 11. Sign-off

| Role | Item | Status |
|------|------|--------|
| Cursor | L4 read-only audit | ✅ Complete |
| Michael | SHADOW soak despite R1–R3 | ⬜ Pending |
| Michael | LIVE NO-GO acknowledged | ⬜ Pending |
| Cursor/CC | Implement R1–R3 before L5/L7 | ⬜ Not started |

---

*Next inbox row: #15 L5 paper dry run — **WAIT** on Michael L4 sign-off + backend up for HTTP UAT.*
