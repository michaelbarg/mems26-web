# MEMS26 V9 — Project SKILL

## PROJECT
MEMS26 = MES Futures auto-trading system.
Working dir: /Users/michael/Downloads/mems26_web_git
Branch: feature/v9_architecture_rebuild
Remote: github-mems26 (SSH)
V8 fallback: tag v8-final-20260509

## 6 SYSTEMS (independent, no cross-gating)

Firing (execute trades):
- System 1: day_type        — #58a6ff
- System 2: chart_5min      — #56d364
- System 4: woodies         — #fb950b

Observers (no execution):
- System 3: tick_reversal   — #d2a8ff (label: "Footprint")
- System 5: tpo             — #79c0ff
- System 6: killzone        — #8b949e

## 3 MODES
- SHADOW: parallel, no caps, no orders
- DEMO/SIM: ONE slot first-wins, no caps, Sierra demo
- LIVE: ONE slot, strict caps, Sierra live

Sierra accounts: DEMO=PA-APEX-125218-01, LIVE=APEX-125218-13
LIVE caps: $250/day, 5 trades, 2 contracts, no after 14:30 ET

## STATE
DONE: W1, W1.5, W2, W2.5, W3, W4
OPEN BUGS:
- CRITICAL: DLL memory leak (Sierra hit 123GB!), WebSocket missing,
  3 Bridge streams missing (woodies/tpo/5min), Frontend types wrong
- HIGH: BRIDGE_TOKEN hardcoded, LTRIM silent fail, wrong tables, markers as icons

NOT BUILT: Phase 2 (W5-W10), Phase 3 (W11-W15), R3 validator

## CRITICAL RULES — NEVER VIOLATE

1. SCOPE — Only ALLOWED FILES. Outside? STOP and ask user.
2. REAL-TIME — V8 was real-time. V9 must be. NEVER add "if last bar" guards.
3. ROOT CAUSE — Find the cause. Don't disable features to silence errors.
4. V8 IS REFERENCE — Regressions = critical bugs.
5. SPEC IS LAW — Specs in Drive are LOCKED. Ambiguity? Ask user.
6. NEVER DECLARE DONE WITH BUGS — W*_DONE means works per spec.
7. NAMING CONSISTENCY — Use exact names below.

## ACSIL GOTCHAS (Sierra Chart C++ DLL)

- std::max/min are macros → use ternary (a > b ? a : b)
- SCT_OSC_REJECTED doesn't exist → SCT_OSC_ERROR
- sc.GetPersistentString doesn't exist → sc.GetPersistentSCString
- GetVAPArrayAtBarIndex doesn't exist (W4 used this!) → GetVAPElementAtIndex
- TPO Value Area subgraphs 1-indexed: SG1=POC, SG2=VAH, SG3=VAL
- Y:\ paths = ~/SierraChart/... (Mac on CrossOver)
- std::endl in hot path → use "\n" (forces flush)
- String += in loop → use std::ostringstream pre-sized
- std::vector inside hot path → use static buffers
- history arrays → ring buffer, fixed size
- sc.AddMessageToLog → only on errors

## MEMORY LEAK PATTERNS

User's Sierra hit 123 GB! NEVER let it happen again.

LEAK patterns (avoid):
1. std::map/unordered_map growing unbounded
2. footprint maps keyed by price*timestamp
3. JSON string concat in loop
4. history vectors appended without truncation
5. sc.AddMessageToLog every export
6. Persistent vars re-allocating per call

SAFE patterns (use):
1. Pre-allocated static buffers (function-scope static)
2. reserve() then clear() (not destroy)
3. sc.GetPersistentInt/Float for primitives
4. Ring buffers for history
5. Pre-sized stringstream
6. Cached path strings

## NAMING CONVENTIONS

System namespaces:
day_type, chart_5min, tick_reversal, woodies, tpo, killzone

Bridge streams = DLL filenames:
tick_reversal_15.json, tick_reversal_12.json, footprint.json,
volume_profile.json, imbalance_flags.json, stacked_imbalances.json,
cumulative_delta.json, woodies_30min.json, tpo.json, 5min.json

Redis keys: mems26:v9:{stream_name}
- imbalance_flags → mems26:v9:imbalance (RENAMED)
- stacked_imbalances → mems26:v9:stacked_imbalance (singular!)

DB tables (v9_ prefix):
v9_bars_5min, v9_bars_tick_reversal, v9_bars_30min_woodies,
v9_tpo_data, v9_system_signals, v9_system_markers, v9_trades,
v9_trade_management_log, v9_daily_quality_reports,
v9_system_configs, v9_account_status

API: /api/v9/bars/{name}, /api/v9/signals/{system_id},
     /api/v9/markers/{system_id}, /api/v9/trades/, /api/v9/configs/{system_id}

WebSocket: /ws/v9/bars/{name}, /ws/v9/markers/{system_id},
           /ws/v9/signals/{system_id}, /ws/v9/trades, /ws/v9/account, /ws/v9/levels

JSON field names (frontend MUST match):
- ts (NOT timestamp)
- ask_vol (NOT ask_volume)
- poc_vol (NOT poc_price)
- classification (NOT signal_type)
- dominant_system (NOT system_id for firing system)
- direction (NOT dir)
- tick_size (NOT tick_count)

## LESSONS FROM PAST MISTAKES

1. W4 broke real-time by adding "if last bar" guards.
   Real cause: GetVAPArrayAtBarIndex didn't exist.
   Lesson: Find root cause. Don't disable features.

2. W1.5 found 0/11 Woodies studies missing (assumed they existed).
   Lesson: Always audit assumptions.

3. 200-bar lookback compromise reduced data accuracy.
   Lesson: Performance compromises must be measured.

4. NAMING-AUDIT found 7+ mismatches across layers.
   Lesson: Use NAMING section above. Verify before commit.

5. DLL memory leak: Sierra hit 123 GB.
   Root cause: throttle AFTER heavy allocations (maps, vectors).
   Lesson: Throttle FIRST, allocate AFTER.

## PER-WINDOW CHECKLIST (before W*_DONE)

1. Code compiles/lints clean
2. Every spec section has code
3. Edge cases handled
4. Tests > 80% coverage
5. Docs in docs/v9/
6. Naming matches this SKILL exactly
7. No hardcoded paths/secrets
8. V8 features preserved
9. Real-time preserved (no batched)
10. No memory leaks (static analysis)
11. Commits pushed
12. Self-verification report

## ESCALATION TRIGGERS (ask user)

- Task requires DO-NOT-TOUCH files
- Spec is ambiguous
- V8 conflicts with V9 plan
- Performance issue requires architectural change
- Test fails after 3 attempts
- Risk to LIVE config
- Memory/CPU seems excessive
- Anything "too big" for window scope

## LOCATIONS

- Code: /Users/michael/Downloads/mems26_web_git/
- Sierra source: ~/SierraChart/ACS_Source/MES_AI_DataExport.cpp
- Sierra output: ~/SierraChart/Data/v9_export/*.json
- Signals: /tmp/mems26_signals/
- QA reports: /tmp/mems26_qa_reports/
- Bridge log: /tmp/bridge.log
- Docs: docs/v9/*.md

Drive specs (search by title):
- MEMS26_DAY_TYPE_SPEC_V3_1
- MEMS26_5MIN_CHART_SPEC_V3_PATTERNS_INTEGRATED
- MEMS26_FOOTPRINT_TICK_SPEC_V3_STANDALONE
- MEMS26_KILLZONE_SPEC_V1
- MEMS26_3_MODE_TRADING_SPEC_V3_FINAL_LOCKED
- MEMS26_DASHBOARD_SPEC_V1_LOCKED
- MEMS26_OPTION_C_PATH_TO_READY (master plan)

## COMMUNICATION

- Hebrew responses OK (code in English)
- Short and practical
- ASCII diagrams (visual learner)
- Brief progress updates
- End with concrete next actions
