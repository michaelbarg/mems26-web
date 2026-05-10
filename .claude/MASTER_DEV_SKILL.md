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
DONE: W1, W1.5, W2, W2.5, W3, W4, W5, W6, W7, W8, W9, W10
OPEN BUGS:
- CRITICAL: DLL memory leak (Sierra hit 123GB!), WebSocket missing,
  3 Bridge streams missing (woodies/tpo/5min), Frontend types wrong
- HIGH: BRIDGE_TOKEN hardcoded, LTRIM silent fail, wrong tables, markers as icons

NOT BUILT: Phase 3 (W11-W15), R3 validator

## §7 — BUG LOG

| # | Bug | Root Cause | Fix |
|---|-----|-----------|-----|
| 14 | Sierra remote build missing headers | cpp uses #include "v9_*.h" but Build only uploaded MES_AI_DataExport.cpp | (a) verify all headers in ~/SierraChart/ACS_Source/ before Build (b) Sierra Custom Studies DLL Build ��� ensure all .h files in ACS_Source/ |

| 15 | Sierra remote build header missing | Sierra remote build (build.sierrachart.com) only uploads the main .cpp file specified in dialog; #include'd headers in same dir are NOT uploaded | Create monolithic combined .cpp via inline-headers script before Sierra Build |

| 16 | Monolith SCDLLName pushed too deep | Headers inlined before SCDLLName — Sierra requires it in first 10 lines | Monolith template: sierrachart.h line 4-5, SCDLLName line 6-7, then headers. scripts/build_monolithic_cpp.sh enforces this |

## CRITICAL RULES — NEVER VIOLATE

1. SCOPE — Only ALLOWED FILES. Outside? STOP and ask user.
2. REAL-TIME — V8 was real-time. V9 must be. NEVER add "if last bar" guards.
3. ROOT CAUSE — Find the cause. Don't disable features to silence errors.
4. V8 IS REFERENCE — Regressions = critical bugs.
5. SPEC IS LAW — Specs in Drive are LOCKED. Ambiguity? Ask user.
6. NEVER DECLARE DONE WITH BUGS — W*_DONE means works per spec.
7. NAMING CONSISTENCY — Use exact names below.

## §9 — TECHNICAL CONSTRAINTS

- Sierra Build is REMOTE (build.sierrachart.com). Headers MUST be in
  ~/SierraChart/ACS_Source/ alongside the .cpp. Local existence in repo
  is not enough — they must be copied there.
- Sierra Build is REMOTE → server uploads ONLY the .cpp specified
- Multi-file project = MUST inline headers into .cpp before deploy
- Workflow: edit modular files in sc_study/v9_*.h → run monolith generator → deploy combined cpp
- Pattern: scripts/build_monolithic_cpp.sh (TBD: create as proper script)

## §10 — WORKER PROMPT TEMPLATE (Sierra deploy task)

Every Sierra deploy task MUST include:
```bash
cp sc_study/MES_AI_DataExport.cpp ~/SierraChart/ACS_Source/
cp sc_study/v9_*.h                ~/SierraChart/ACS_Source/   # include ALL headers
ls ~/SierraChart/ACS_Source/v9_*.h  # verify before Build
```

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

16. Sierra remote build is server-side. ALL #include'd headers must exist in
    ~/SierraChart/ACS_Source/ at build time, not just the main .cpp.
    Verify with `ls ~/SierraChart/ACS_Source/v9_*.h` before EVERY Build.

17. Sierra Build is REMOTE and uploads ONE FILE. Multi-file projects (cpp + headers)
    must be combined into a single monolithic cpp before Build. Maintain modular source
    in repo (sc_study/), but generate monolithic file for ~/SierraChart/ACS_Source/.

18. SCDLLName + #include "sierrachart.h" MUST be in first 10 lines of the .cpp file.
    Sierra parser scans top of file only. Monolith generator (scripts/build_monolithic_cpp.sh)
    enforces this. IsNotEmpty() is not valid ACSIL — use time(nullptr) instead.

19. SCID format is the authoritative tick source on Sierra Chart Mac.
    No DLL modification needed — raw ticks (bid/ask classified at exchange)
    are exported by Sierra natively to ~/SierraChart/Data/*.scid.
    Future tick-based features should read SCID, not extend the DLL.

20. ALWAYS investigate existing local data before designing new DLL features.
    The "we need to add X to the DLL" assumption was wrong twice on this project.
    First check: what does Sierra already export? 15-minute audit can save
    days of unnecessary DLL work.

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
- MEMS26_WOODIES_SPEC_V1_DERIVED (id: 1NtKDNZNVwWi8Dio_C-42Yj0c6DPFGEfnFSo3Vx4rp0k) — DERIVED per §6.5
- MEMS26_KILLZONE_SPEC_V1
- MEMS26_3_MODE_TRADING_SPEC_V3_FINAL_LOCKED
- MEMS26_DASHBOARD_SPEC_V1_LOCKED
- MEMS26_OPTION_C_PATH_TO_READY (master plan)

## §6.0 — STEP 0: PATH VALIDATION (mandatory pre-QA)

Before any QA scan:
```bash
SYSTEM_DIR="backend/v9/systems/<system>/"
FILE_COUNT=$(ls "$SYSTEM_DIR"*.py 2>/dev/null | wc -l)
if [ "$FILE_COUNT" -eq 0 ]; then
  echo "🔴 PATH_NOT_FOUND — ABORT QA"
  exit 1
fi
```

## §6.5 — SPEC GAP AUTO-RESOLUTION

When no spec in Drive:
1. Search local repo (find . -iname "*<name>*")
2. Check DLL headers
3a. Local found → upload to Drive, add to §0
3b. DLL header → derive contract spec, mark "DERIVED"
3c. Nothing → ask user

## §6.6 — WARN SEVERITY TIERS

- WARN-S1 CRITICAL → Must fix before LIVE (user confirm required)
- WARN-S2 HIGH     → Must fix before SHADOW (batch approve OK)
- WARN-S3 MEDIUM   → Phase 3.5 backlog
- WARN-S4 LOW      → Don't even mention

## §17 — DATA INTEGRITY & GAP RESOLUTION

### Active Violations
(none)

### Resolved (2026-05-10)
✅ Footprint VAP — DLL v9.2.0 has MaintainVolumeAtPriceData=0 but Bridge
   VAP_PYTHON_RECOMPUTE reads SCID ticks and recomputes real bid/ask split.
   Verified 2026-05-10: bid=167 ask=458 (NOT identical). SHADOW unblocked.
✅ W5 confidence threshold 0.85 → 0.70 (commit 5dc2006)
✅ W5 Decision Matrix 4 cells fixed to V2 spec (commit 5dc2006)
✅ W5 config params now configurable via DayTypeConfig (commit 5dc2006)
✅ W8 VEGAS positive tests added (commit 5dc2006)
✅ W8 signal persistence POST /process (commit 5dc2006)
✅ W8 Woodies spec gap RESOLVED — DERIVED spec uploaded to Drive (id: 1NtKDNZNVwWi8Dio_C-42Yj0c6DPFGEfnFSo3Vx4rp0k) from woodies_audit.md + v9_woodies_export.h per §6.5

### Backlog (Phase 3.5)
🟡 W9 Stage F EOD — deferred, non-blocking for SHADOW
🟡 W9 Naked POC lookback — deferred
🟡 W9 time-gated classification — deferred

### Infrastructure
🛠️ V9 backend not deployed to Render
🛠️ DLL v9.1.2 quarantined (Bug #11)
[x] scripts/build_monolithic_cpp.sh created — monolith generator with verification
    Enforces SCDLLName in first 10 lines, checks IsNotEmpty/std::max, deploys with --deploy flag

### Architectural Principles

DATA SOURCE HIERARCHY (when adding new features):
1. Read existing Sierra exports (SCID, DLY, JSON) → 15 min audit
2. Compute in Python Bridge from existing data → preferred for new features
3. Extend DLL → ONLY if computation infeasible in Python (latency, complexity)

## §18 — DATA INTEGRITY PRINCIPLE

See: .claude/DATA_INTEGRITY_PRINCIPLE.md (LOCKED)
Audit: scripts/data_integrity_audit.sh
Rule: ANY 🔴 in audit → PHASE TRANSITION BLOCKED

## COMMUNICATION

- Hebrew responses OK (code in English)
- Short and practical
- ASCII diagrams (visual learner)
- Brief progress updates
- End with concrete next actions
