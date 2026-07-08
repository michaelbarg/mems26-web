# SIM Proof — Partial (2026-07-09, outside RTH)

## What was proven

1. **Gateway round-trip works:** `debug_gateway_fire` → session_gate_closed bypass →
   `_execute_demo` → Trade #317 created (mode=demo, sys=4, LONG, 2 contracts)
2. **Sierra command written:** `trade_command.json` op=PLACE, action=BUY, contracts=2,
   stop=7516.25, target=7532.25 — correct format
3. **Slot management:** demo_slot taken at fire, released after CANCEL_OK
4. **EOD flatten gate works:** BarLevelDetector caught the post-close trade within 1 second,
   sent CANCEL → Sierra returned `{"status":"CANCEL_OK","ts":1783540908,"error":1}`

## Log evidence (Rule 5)
```
2026-07-08 23:01:45 [WARNING] [debug_gateway_fire] session_gate_closed — bypassing for SIM proof
2026-07-08 23:01:46 [INFO] Trade 317 created: mode=demo sys=4 dir=LONG
2026-07-08 23:01:46 [INFO] [SierraCmd] wrote trade_command.json (op=PLACE)
2026-07-08 23:01:46 [INFO] [Gateway] DEMO trade TM id=317: LONG SIM_TEST system=4 t1=7532.25 t2=7540.25 t3=7548.25
2026-07-08 23:01:46 [WARNING] [BarLevelDetector] EOD FLATTEN (RTH close, 16:01 ET): CANCEL sent for demo trade 317
```

## What still needs verification (requires market hours)

- [ ] ORDER_SUBMITTED error=0 (Sierra ack)
- [ ] `[FillPoller] registered order` log line (order-id map at submit)
- [ ] Bracket = exactly 2 OCO groups (1 per contract)
- [ ] `/trades/active` shows "0/2"
- [ ] Fill captured at Sierra fill price (not setup price — L4 class)
- [ ] Flatten clean + slot released after fill

**Recommendation:** Fire SIM proof during tomorrow's RTH (after 08:30 CT) when Sierra SIM
account is active. The gateway+command path is verified; the fill round-trip is not.
