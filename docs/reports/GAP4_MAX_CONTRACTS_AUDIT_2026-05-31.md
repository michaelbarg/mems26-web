# GAP-4: MAX_CONTRACTS Enforcement — Audit Report

**Date:** 2026-05-31  
**Agent:** Claude Code (Opus 4.6)  
**Type:** READ-ONLY audit — zero code changes

---

## B1 · All Uses of MAX_CONTRACTS

```
$ grep -rn "MAX_CONTRACTS\|max_contracts" backend/
backend/v9/gateway/risk_checks.py:20:MAX_CONTRACTS = 2
```

**One definition. Zero uses.** The constant is defined at line 20 of `risk_checks.py` but never referenced in any `if` statement, comparison, or function call anywhere in the codebase.

---

## B2 · `passes_strict_checks` — Full Analysis

**File:** `backend/v9/gateway/risk_checks.py`

The function checks LIVE mode only:

| Check | Line | What it does | Contract-related? |
|-------|------|--------------|-------------------|
| Time cutoff | ~49 | No trades after 14:30 ET | No |
| Daily loss cap | ~54 | Blocks if daily PnL < -$250 | No |
| Max trades/day | ~60 | Blocks if >= 5 trades today | No |
| Consecutive losses | ~65 | Blocks if 2+ consecutive stops | No |

**MAX_CONTRACTS is NOT checked.** No line in `passes_strict_checks` reads `setup["contracts"]` or `setup["metadata"]["sizing"]` or compares against `MAX_CONTRACTS`.

---

## B3 · Three-Way Mismatch

| Source | Value | Context |
|--------|-------|---------|
| `risk_checks.py:20` | **2** | Dead constant (never enforced) |
| Auth Table (max per cell) | **3** | HIGH tier, patterns like REACTIVE on Trend_Normal |
| Michael decision (31/5) | **5** | Stated in STATUS_BOARD |

### Contract flow (no enforcement point):

```
Auth Table cell → (verdict, tier, contracts: 0-3)
  → T1Setup.sizing_contracts
  → gateway metadata.sizing (stored, never validated)
  → _build_trade() → DB quality.sizing
  → API response contracts_pnl
```

**Gap:** No point in this chain validates `contracts <= MAX_CONTRACTS`. A HIGH-tier setup gets 3 contracts from Auth Table, and nothing stops it even if MAX_CONTRACTS is 2.

---

## B4 · Semantics Question

**What should MAX_CONTRACTS control?**

| Interpretation | Current state | Implication |
|---------------|---------------|-------------|
| **Per-trade** (single setup size) | Auth Table caps at 3. No runtime check. | If MAX=5, no setup exceeds it anyway (max is 3 from Auth Table) |
| **Concurrent** (total contracts across open trades) | No check exists. Multiple SHADOW trades can accumulate unlimited contracts. | DEMO/LIVE: only 1 slot, so max = single trade size. SHADOW: unbounded. |
| **Daily aggregate** (total contracts fired today) | No check exists. | Would require tracking cumulative contracts per day |

---

## Questions for Michael

1. **Semantics:** Is MAX_CONTRACTS a per-trade cap, concurrent-position cap, or daily aggregate?
2. **Value:** Which is authoritative — 2 (code), 3 (Auth Table max), or 5 (your statement)?
3. **Auth Table alignment:** If MAX_CONTRACTS = 5, does Auth Table need to change (currently max 3/cell)? Or does 5 mean "up to 5 across multiple concurrent setups"?
4. **Enforcement location:** Should this be in `passes_strict_checks` (LIVE only)? Or in gateway for DEMO too? Should SHADOW be unbounded regardless?
5. **Priority:** Fix now (dead code + enforcement) or defer to P5 LIVE wiring?

---

## Evidence (Rule 5)

```
$ grep -rn "MAX_CONTRACTS" backend/
backend/v9/gateway/risk_checks.py:20:MAX_CONTRACTS = 2

$ grep -n "contracts\|sizing\|size" backend/v9/gateway/risk_checks.py
20:MAX_CONTRACTS = 2
(no other matches)

$ grep -n "metadata.sizing\|contracts" backend/v9/gateway/trading_gateway.py
(no matches in passes_strict_checks call path)
```
