# CC → prove a GATEWAY fire captures the fill (the last gate to real money, 2026-07-07)

## What Cowork verified (from your evidence + the code)
✅ HUGE: the order path WORKS now — the 2c SIM command `ORDER_SUBMITTED` (result 1s after command)
+ 2 sim fills @7580.25 + flatten. No `GENERAL_ERROR`. The study is armed. That was THE blocker.
✅ P1.2 works on real data — order_id 8411/8418 flagged as CRITICAL ORPHAN (not silently dropped).

⚠️ BUT the fills ORPHANED — because you fired **manually via trade_command.json, bypassing the
gateway**, so no TM trade existed to capture into. Code check (`_execute_live` gateway:1244-1259):
a gateway fire DOES `accept_setup(...)` → an **active live/demo trade** exists → the I-58 fallback
(fill_poller:248) adopts the fill → captured. There is NO `register_order` call, so capture relies
ENTIRELY on that single-active-trade fallback. **Unproven live.** For real money we must SEE one
gateway fire captured into a tracked trade with Sierra P&L — an orphaned real fire = a naked
untracked live position.

## GOAL — one gateway SIM fire, captured (paste the artifacts)
### Preflight (both paths — required)
1. **No stale active trade** (else the fallback adopts the WRONG trade):
   `PSQL=/Applications/Postgres.app/Contents/Versions/latest/bin/psql`
   `$PSQL postgresql://localhost/mems26 -c "SELECT id,mode,state FROM v9_trades WHERE state NOT IN ('CLOSED','closed') AND mode IN ('demo','live');"` → must be **empty**. If not, close them first.
2. **Account:** confirm the `[env_loader]` boot line shows `SIERRA_LIVE_ACCOUNT=37138283` (NOT the
   `APEX-125218-13` default at gateway:1257). Paste it.
3. Flags live: `SYSTEM6_SUPERVISOR=1 · EOD_FLATTEN_V1=1 · RECONCILE_LIVE_V1=1 · CONT_TREND_FILTER=1 ·
   RISK_HALT_V1=1/CAP=400 · FIXED_CONTRACTS_2=1` — paste the boot line.

### Fire through the gateway on SIM (creates a real TM trade → tests capture)
Sim Mode ON. Drive a demo fire through the running gateway (NOT a hand-written command). Use the
running app's gateway so the running FillPoller sees the trade. Simplest: a tiny debug call into
`app.state.trading_gateway._execute_demo(setup, system_id, cross_context)` with a minimal setup
(direction, entry_price=live price, stop=±8, t1/t2/t3), OR inject a synthetic setup through
`route_setup`. This must go through `accept_setup` so a `mode=demo` active trade is created.

### CAPTURE proof — paste ALL of it
- `fill_poller` log: `[FillPoller] ENTRY fill: trade <id> @ <price>` — **NOT** `ORPHAN FILL`.
- `$PSQL ... -c "SELECT id,mode,direction,contracts,entry_price,stop,state,exit_price FROM v9_trades ORDER BY id DESC LIMIT 3;"` → the trade row with `entry_price == the Sierra fill price`.
- On exit (T1/stop): P&L computed from the **Sierra fill price** (manager.py:799), not the intended level.
Save as `docs/reports/evidence_2026-07-07/p1_capture_*.{txt,json}` + commit.

## If it ORPHANS anyway (real bug) — the fix
Then the fallback failed (trade not visible when the fill arrived — a commit/timing race). Fix:
in `_execute_demo/_execute_live`, after `accept_setup` + `_db.commit()`, ensure the trade is
queryable BEFORE the command is written (it is committed at gateway:1246 — verify no second
uncommitted session). If needed, add a fill_poller retry: on an unmapped fill, re-query active
trades once after a short delay before declaring orphan. Report the exact orphan line + the
`get_active_trades()` result at that moment so we pinpoint it.

## Verdict loop
Paste the capture artifacts → Cowork verifies `entry_price==fill` + P&L==Sierra → that box goes
GREEN → then real money is defensible (supervised first fire). Until then: not green.
