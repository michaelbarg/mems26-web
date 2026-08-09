# Command-Queue Sierra Test — Globex open, 2026-08-10 01:20–01:25 IDT

**Agent:** night-sim-agent (Cowork → Desktop Commander on the MacBook, the trading machine)
**Branch:** `stabilize/mems26-local-truth-2026-05-16` @ `d4892f91`
**Verdict: ✅ PASS — the drainer works end-to-end against the real Sierra DLL,
including the exact 08-07 failure mode. Michael's arming condition is met.**

Context: `drain_command_queue()` was wired to the FillPoller loop on 08-09 (`ef01d040`).
Local sim passed 3/3; this test was the missing real-DLL end-to-end proof.

---

## 1. Preconditions (all green)

```
Mon Aug 10 01:20:21 IDT 2026
woodies_5min.json age = 3.0s          → feed ALIVE (Sierra open, Globex)
sierra_state.json:
  position_qty = 0        orders = []        working_orders = 0
  is_sim = 0              trade_account = '37138283'     symbol = MESU26_FUT_CME
  order_placement_armed = 1   send_orders_to_trade_service = 1
v9_trades: last = #652 CLOSED (no PENDING/FILLED rows)
backend: uptime 33410s, /health 200 in 0.060s, PID 58340 (started Aug 9 16:04)
fill_poller.py mtime Aug 9 08:21 < backend start → running process HAS the drainer code
```

## 2. SAFETY — how a live-account test was made provably inert

`is_sim = 0` → **live account.** Per the task's safety rule, **no order was placed.**

Instead the drainer was exercised with a command that *cannot touch an order*.
Derived from the **deployed** DLL source, not from memory
(`~/SierraChart/ACS_Source/MES_AI_DataExport.cpp:3096-3180`):

- `MODIFY_STOP` prefers the `stop_ids` array from the command JSON; the
  persistent-slot fallback (slots 3/5/7/9) runs **only** when `n_from_cmd == 0`.
- Sending `stop_ids:[999999]` therefore suppresses the fallback entirely.
  `GetOrderByOrderID(999999)` → `SCTRADING_ORDER_ERROR` → `continue` →
  `mod_count = 0` → `MODIFY_STOP_NONE`.
- The target-restore loop only re-sets a target whose price *changed* inside the
  same pass — with 0 working orders it is a no-op.
- `_handle_modify_stop_none()` (`STOP_RETRY_ON_NONE_V1=1` in `.env`) returns early
  when there is no FILLED demo/live trade — no retry, no phone push. Confirmed in log.

Belt-and-braces: probe asserted `position_qty == 0 and orders == []` before writing,
and re-read the state after. **Post-check: `position_qty=0 orders=[]` — unchanged.**

## 3. Probe 1 — single command, full round-trip

```
[SierraCmd] COMMAND QUEUED #6 → .../command_queue/cmd_000006.json (op=MODIFY_STOP, pending_before=0, fast_path=True)
PRECHECK ok: position_qty=0 orders=[] is_sim=0
[BEFORE] pending=0 res_mtime=1786280770.128 result={"status":"UNKNOWN","ts":1786280770,"error":0}
WROTE seq=6 fast_path=True
[T+0]    pending=1
  t+1s pending=1 result={"status":"UNKNOWN","ts":1786280770,"error":0}
  t+2s pending=1 result={"status":"UNKNOWN","ts":1786280770,"error":0}
  t+3s pending=0 result={"status":"MODIFY_STOP_NONE","ts":1786314264,"error":0}
DRAINED in 3.0s
POSTCHECK: position_qty=0 orders=[]
```

Proven: command → `trade_command.json` → **DLL executed and ACKed**
(`MODIFY_STOP_NONE`, the predicted inert result) → drainer saw the ACK and
removed the queue file. Queue emptied. **3.0s.**

## 4. Probe 2 — the actual 08-07 regression case (TWO rapid commands)

This is the one that matters. On 08-07 command #1 took the fast path and
**every later command sat in `command_queue/` forever** (PLACE #652 + CANCEL never
reached the DLL). Only the drainer can move command #2.

```
[SierraCmd] COMMAND QUEUED #6 → cmd_000006.json (op=MODIFY_STOP, pending_before=0, fast_path=True)
[SierraCmd] COMMAND QUEUED #7 → cmd_000007.json (op=MODIFY_STOP, pending_before=1, fast_path=False)
A seq=6 fast_path=True | B seq=7 fast_path=False
pending right after write = 2
  t+1s pending=2 files=['cmd_000006.json','cmd_000007.json'] wire_trade_id=QTEST-A result={"status":"MODIFY_STOP_NONE","ts":1786314264,...}
  t+2s pending=1 files=['cmd_000007.json']                   wire_trade_id=QTEST-B result={"status":"MODIFY_STOP_NONE","ts":1786314291,...}
  t+3s pending=1 files=['cmd_000007.json']                   wire_trade_id=QTEST-B
  t+4s pending=1 files=['cmd_000007.json']                   wire_trade_id=QTEST-B
  t+5s pending=0 files=[]                                    wire_trade_id=None  result={"status":"MODIFY_STOP_NONE","ts":1786314294,...}
BOTH DRAINED in 5.0s
B reached trade_command.json (drainer-moved): True
POSTCHECK: position_qty=0 orders=[]
```

**Command B was moved onto the wire by the drainer alone and separately ACKed by
the DLL** (`ts 1786314291` → `1786314294`). The 08-07 class is closed against the
real DLL, not just in the local sim.

## 5. Backend-side confirmation (independent of the probe)

```
2026-08-10 01:24:24 [INFO] [FillPoller] command queue: 1 command(s) completed
2026-08-10 01:24:53 [INFO] [FillPoller] command queue: 1 command(s) completed
2026-08-10 01:24:54 [INFO] [FillPoller] command queue: 1 command(s) completed
2026-08-10 01:24:24 [WARNING] [FillPoller] W3 MODIFY_STOP_NONE but no FILLED demo/live trade — stale result or manual order
2026-08-10 01:24:53 [WARNING] ... (same)
2026-08-10 01:24:54 [WARNING] ... (same)
```

3 drains = probe 1 + probe 2 (A and B). Zero `command-queue drain error` lines in
the whole log. W3 handler degraded exactly as designed.

Queue left clean:
```
command_queue/   → only archived_stale/ (5 pre-existing files from 08-07/08-08/08-09)
position_qty 0 · orders [] · working 0
```

## 6. System consistency after the test

```
════ MEMS26 consistency verify · 2026-08-10 01:25:11 IDT ════
  ✅ backend :8000 → HTTP 200      ✅ bridge running      ✅ export promoter running
  ✅ com.mems26.backend/bridge/export_promoter LaunchAgents running
  ✅ deployed DLL == committed monolith        ✅ sc_study/ clean in git
  ✅ FLAG_INDEX current                        ✅ SYSTEM_INDEX.md present
  ✅ woodies_5min.json fresh (1s)
  ✅ v9_bars_5min_woodies last bar lag: 00:00:13
════ verdict: OK · 0 warn ════
```

---

## What was proven / NOT proven

**Proven:** queue → drainer → `trade_command.json` → real DLL execution → ACK →
queue file removed, for both the fast path *and* the queued-behind case; drainer is
live in the running backend; no drain errors; system consistent after.

**NOT proven (deliberately, live account):** order PLACE, real bracket attach,
FLATTEN, or a `MODIFY_STOP` that actually moves a working stop. Those need a real
working order and were correctly skipped. The command *transport* is what was under
test and it is green; the op semantics themselves are unchanged by K1.

## Gotcha recorded (near-miss, no action needed)

`sc_study/` holds **two** DLL sources. `MES_AI_DataExport.cpp` (2228 lines) has a
legacy V7.9.2 `MODIFY_STOP` that reads `new_stop_price`; the **deployed** file is
`MES_AI_DataExport_merged.cpp` (3912 lines) and reads `new_stop` — matching the
Python writer. Reading the non-merged file first suggested a phantom key-mismatch
bug and a phantom deploy drift; `mems26_verify.sh` shows **no drift**. *For any DLL
semantics question, read `MES_AI_DataExport_merged.cpp` (or the deployed copy).*

## Observation, not investigated

`sierra_state.daily_pnl = -831.25` while flat at Sunday-night Globex open — most
likely Friday's value not yet rolled. Flagged only; outside this test's scope.
