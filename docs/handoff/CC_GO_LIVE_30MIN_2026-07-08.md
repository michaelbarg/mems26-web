# 🔴 CC — GO-LIVE in 30 min (Michael approved: restart + minimal gate → LIVE)

RTH opens 16:30 IL. Execute top-to-bottom NOW. Paste raw output for each step into
`docs/reports/evidence_2026-07-08/`. ANY red → STOP → DEMO today (Michael's standing rule).
Full context: `CC_CONTINUATION_2026-07-08.md`. Do NOT rebuild anything — all code is committed
(`6bb25ce`·`9f0a64a`·`d999698`·`b275165`·`d933751`).

## GATE A — flat + snapshot (target: 5 min)
```bash
# 1. FLAT check — all three must agree (DB open rows may include stale 40x orphans — gateway slot is authoritative)
curl -s localhost:8000/api/v9/trades/active
psql postgresql://localhost/mems26 -c "SELECT id,mode,state FROM v9_trades WHERE state IN ('PENDING','FILLED','PARTIAL','OPEN') AND mode IN ('demo','live');"
# + Sierra: Trade >> Positions = FLAT
# 2. Snapshot (out-of-git surfaces)
scripts/mems26_snapshot.sh "pre-0708-golive"
```
**GO =** no open live/demo position anywhere. Orphan DB rows (401-405 class) noted but slot flat → proceed.

## GATE B — deploy (one restart ships L8 + N3 + L7) (target: 5 min)
```bash
# 1. .env: add/set  LIVE_LEDGER_V1=1   (snapshot already taken)
# 2. Restart:
launchctl kickstart -k gui/$UID/com.mems26.backend
# 3. Verify via [env_loader] boot-line (NOT ps eww):
tail -50 /tmp/backend.out.log | grep env_loader
```
**GO =** boot-line shows: `LIVE_EXECUTION_V1=1 · FIXED_CONTRACTS_2=1 · RISK_HALT_V1=1 ·
RISK_DAILY_LOSS_CAP=400 · EOD_FLATTEN_V1=1 · RECONCILE_LIVE_V1=1 · SYSTEM6_SUPERVISOR=1 ·
CONT_TREND_FILTER=1 · LIVE_LEDGER_V1=1`. Any safety flag missing → NO-GO.

## GATE C — one SIM 2c proof order (outside RTH — Michael's 07-07 ruling) (target: 10 min)
Place a small 2-contract SIM order through the normal command path, then flatten. Must see ALL:
1. `trade_result.json` → `ORDER_SUBMITTED` + `error:0` + `parent_id/target_id/stop_id` (**arming holds**).
2. Backend log → `[FillPoller] registered order <parent_id> → trade <id>` (**N3 map live**).
3. Sierra bracket = exactly **2** OCO groups, no group 3 (**L7**); `/api/v9/trades/active` →
   2 contract rows, `"summary": "0/2 hit"` (**L7 display**).
4. NO `"SKIPPED"` warnings in the log during the round-trip.
5. Flatten → position 0.
**GO =** all five. Any miss → NO-GO → DEMO.

## GATE D — ledger + health (target: 5 min)
```bash
curl -s localhost:8000/api/v9/live_ledger | python3 -m json.tool | head -40   # → the 2 real 07-07 trades
curl -s localhost:8000/api/v9/health                                          # feed fresh, DB lag ok
# :3000 up (start if down) → /board renders the ledger
```
**GO =** 2 real trades visible with fills+P&L; feed fresh.

## ARM (Michael does this himself in Sierra)
All gates GO → tell Michael: **"GATES GREEN — arm 2-contract live."** Michael arms. Keep during session:
- First real T1 → paste the `sc.ModifyOrder` line (L2 live proof) — System 6 + reconcile watching;
  a `"MODIFY_STOP SKIPPED"` warning = the old silent bug surfacing LOUDLY → alert Michael immediately.
- First live ZLR/GHOST → confirm no `failed_stages=['A7']`.
- V1–V5 ledger verification during quiet minutes (not blocking).
- Hard stops stay: −$400 halt · EOD flatten · 22:15 no-entry · System 6.

## NOT covered by this gate (accepted by Michael for today)
L2 live MODIFY unproven until first real T1 (mitigated: loud warnings + System6) · A7 unproven on live
fire · V1–V5 deferred to in-session. Update `task_board.json` + journal as each proves out.
