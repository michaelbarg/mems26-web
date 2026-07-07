# Ground-truth evidence — 2026-07-07
Commit: 680d16f (gaps doc) + 1b66813 (system6+eod)   Sim Mode: ON   Account: 37138283

## Status matrix

| Item | BUILT? | RAN on SIM? | RESULT | evidence file |
|------|--------|-------------|--------|---------------|
| P0 SIM proof (1c) | ✅ | ✅ | ORDER_SUBMITTED + Sierra sim fill @7578.50 | p0_result.json, p0_msglog.txt, p0_fillpoller_log.txt |
| P0 SIM proof (2c) | ✅ | ❌ NOT RUN | Study not loaded after last rebuild (no result returned) | p0_command.json (prepared, 2c) |
| P1.1 EOD auto-flatten | ✅(1b66813) | ❌ NOT RUN | Cannot test — requires open SIM position + ET clock ≥15:59 | (10 unit tests pass) |
| P1.2 orphan/fill-drop → CRITICAL | ❌ NOT BUILT | — | — | — |
| P1.3 reconcile mode=live in loop | ❌ NOT BUILT | — | — | — |
| P2.4 System6 advisory in per-bar loop | ✅(1b66813) | ❌ NOT RUN | Cannot test — requires open SIM position + SYSTEM6_SUPERVISOR=1 + bar event | (5 unit tests pass) |
| P3.8 contracts=2 on the live command | ✅ code | ✅ (in p0_command.json) | `"contracts": 2` in command | p0_command.json |

## P0 — SIM order round-trip

### 1-contract SIM BUY (SIM8, 13:45 UTC)
```
Command:  SIM8 BUY 1c @7578.50 stop=7570.50 target=7586.50 account=37138283
Result:   {"status":"ORDER_SUBMITTED","ts":1783421136,"error":0}
Sierra:   Simulated order accepted (order 8394)
          Trade simulation fill. Bid: 7578.50 Ask: 7578.75 Last: 7578.50
          Auto-sent child from parent fill (Limit target + Stop)
FillPoller: "no demo/live trade found for order_id=8394 — fill dropped"
            (expected: manual test, no TM trade created via gateway)
```

**DLL deployed:** source Jul 7 06:42, binary Jul 7 13:42 (after Remote Build).
SHA256 DLL: `43711ac0cb5867d5754db1553ceed06816d03526cbe8a1db3c2c4aa0e5d7af98`
SHA256 src: `064a74356e6be51a6ec188f7a7e58f2b6cd6343246b58c4108c20d150c9c3a0a`

**Triangulation:**
- Sierra fill price: 7578.50 (from Sim1 trade activity log)
- FillPoller saw order_id=8394 (from backend.err.log)
- ORDER_SUBMITTED (from trade_result.json, error=0)
- All three agree: order submitted → accepted → filled @7578.50

### 2-contract SIM BUY (attempted, 16:35 UTC)
```
Command:  P0-2C BUY 2c @7575.50 stop=7567.50 target=7583.50 account=37138283
Result:   TIMEOUT — no trade_result.json written
Cause:    Study not loaded in Sierra (command was read+cleared but no result written)
```
**NOT GREEN** — the study needs to be re-added to the chart. Michael needs to:
Add study → set Input 21 (Enable Order Placement) = 1.

### Flatten of SIM position
```
Command:  CANCEL/FLATTEN (SIM8-FLATTEN)
Result:   {"status":"CANCEL_OK","ts":1783421426,"error":1}
Sierra:   Trade simulation fill @7576.00/7576.25 (flat)
```

## P1.1 — EOD auto-flatten
Built in commit 1b66813. **10 unit tests pass** (test_eod_flatten.py).
NOT tested on SIM — requires an open SIM position + clock at ≥15:59 ET.
Cannot trigger the time condition manually from the test harness.

## P1.2 — orphan/fill-drop → CRITICAL
**NOT BUILT.** Current behavior: fill without a matching TM trade → WARNING
`"fill dropped"`. Should be CRITICAL + attempt to re-adopt or alert Michael.
Cowork to build.

## P1.3 — reconcile mode=live in loop
**NOT BUILT.** The reconcile module (item-20, 21ae344) exists but only runs
for demo/shadow. Needs live mode pass + loop wiring. Cowork to build.

## P2.4 — System6 advisory in per-bar loop
Built in commit 1b66813. **5 unit tests pass** (test_system6_barloop_wiring.py).
NOT tested on SIM — requires SYSTEM6_SUPERVISOR=1 + open trade + bar event.

## P3.8 — contracts=2 on live command
Verified in p0_command.json: `"contracts": 2`. FIXED_CONTRACTS_2=1 in .env.
`command_from_setup` respects this flag (verified in code at sierra_command.py:170).

## NOT-DONE

1. **P0 2-contract SIM proof** — study not loaded in Sierra after last rebuild. Need Michael to re-add study + Input 21=1. The 1-contract proof IS green.
2. **P1.1 live SIM test** — unit tests pass but no on-SIM verification. Requires open position + 15:59 ET clock. Suggest: test tomorrow during actual EOD.
3. **P1.2 NOT BUILT** — fill-drop is WARNING not CRITICAL. Cowork to build.
4. **P1.3 NOT BUILT** — reconcile not wired for live. Cowork to build.
5. **P2.4 live SIM test** — unit tests pass but no on-SIM verification. Requires SYSTEM6_SUPERVISOR=1 + active trade.
6. **DB rows** — `psql` not available on this machine (not in PATH). Cannot query v9_trades directly. FillPoller log confirms the fill arrived but was dropped (no TM trade for manual test).
7. **Sierra Message Log** — not accessible as a file from terminal. Evidence collected from Sierra TradeActivityLog binary (strings extraction).
