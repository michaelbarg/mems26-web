# DLL ID-rich ack verification — 2026-07-09

## Bug found + fixed
The DLL had two write paths to `trade_result.json`:
1. **ID-rich** (ORDER_SUBMITTED block): `parent_id`, `target_id`, `stop_id`
2. **Generic** (end of command processing): `status`, `ts`, `error` only

Path 2 **overwrote** path 1 every time. Fix: `result_written` flag (279470d).

## Evidence after Remote Build + reload study (12:49 IDT)

### trade_result.json (Rule 5):
```json
{"status":"ORDER_SUBMITTED","ts":1783590657,"parent_id":8527,"target_id":8522,"stop_id":8523}
```
**Before fix:** `{"status":"ORDER_SUBMITTED","ts":...,"error":0}` (no IDs)

### trade_fills_journal.jsonl (ENTRY with all 6 child IDs):
```json
{"kind":"ENTRY","ts":1783590657,"order_id":8527,
 "c1_target_id":8522,"c1_stop_id":8523,
 "c2_target_id":8525,"c2_stop_id":8526,
 "c3_target_id":8528,"c3_stop_id":8529,
 "price":7515.25,"contracts":3,"direction":"LONG"}
```

### T3 fill detected by Pipeline 5:
```json
{"kind":"T3","ts":1783590669,"order_id":8528,"price":7539.25,"contracts":1}
```

## Conclusion
DLL fix verified. Backend FillPoller can now map order IDs at submit time
(no more I-58 fallback heuristic). NAKED_STOP false-positives should be
eliminated for trades placed after this build.
