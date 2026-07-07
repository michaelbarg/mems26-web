# CC → produce a VERIFIABLE ground-truth report (2026-07-07, before RTH 16:30)

Owner: Claude Code (Sierra machine). Reader/verifier: Cowork. Decider: Michael.

## Why this exact format (read first)
Cowork CANNOT see your machine — not the Sierra Message Log, not `~/SierraChart_Data/`,
not the live Postgres (`localhost` is yours, not Cowork's). So a prose "✅ done / it works"
is unverifiable and does NOT count (Rule 5). The ONLY things Cowork can check are files that
land **inside the git repo**. Therefore every claim below must be backed by a **raw artifact
copied into the repo** that Cowork can open and **cross-check against a second source**
(Rule 3 triangulation: export JSON ↔ DB row ↔ log line must agree). No screenshots, no
retyping numbers — copy the actual files + paste the actual command output.

## Deliverable (commit all of it)
1. One report: `docs/reports/GROUND_TRUTH_2026-07-07.md` (template at the bottom).
2. One evidence folder: `docs/reports/evidence_2026-07-07/` holding the copied raw artifacts.
3. `git add` + commit both. Tell Michael the commit hash. Then Cowork verifies each box.

SIM ONLY. Snapshot before any `.env` change. Do NOT flip Sim Mode OFF / send real money —
that decision is Michael's, AFTER Cowork confirms the boxes from the artifacts.

---
## STEP A — status matrix FIRST (so we don't collide or assume)
Fill this table at the top of the report — one row per item, honest y/n:

| Item | BUILT? | RAN on SIM? | RESULT | evidence file |
|------|--------|-------------|--------|---------------|
| P0 SIM proof (1 + 2 contract) | — | — | — | |
| P1.1 EOD auto-flatten | ✅(1b66813) | ? | | |
| P1.2 orphan/fill-drop → CRITICAL + rebuild | ? | ? | | |
| P1.3 reconcile mode=live in loop | ? | ? | | |
| P2.4 System6 advisory in per-bar loop | ✅(1b66813) | ? | | |
| P3.8 contracts=2 on the live command | ✅ code | ? | | |

If an item is NOT built, say so in STEP C (NOT-DONE) — do not fake a result. P1.2/P1.3 may
still be unbuilt; if so, Cowork will build them — just declare it.

---
## STEP B — evidence per box (exact command → what to copy → pass criterion)

### P0 — the SIM order round-trip is REAL (most important)
```bash
mkdir -p docs/reports/evidence_2026-07-07
# 1. prove the fix is in the DEPLOYED binary (not just source)
ls -la ~/SierraChart*/ACS_Source/MES_AI_DataExport_64.dll | tee docs/reports/evidence_2026-07-07/p0_dll_mtime.txt
shasum -a256 ~/SierraChart*/ACS_Source/MES_AI_DataExport_64.dll | tee -a docs/reports/evidence_2026-07-07/p0_dll_mtime.txt
# 2. fire a 2-contract SIM BUY (Sim Mode ON), then copy the three export JSONs
cp ~/SierraChart_Data/v9_export/trade_command.json docs/reports/evidence_2026-07-07/p0_command.json
cp ~/SierraChart_Data/v9_export/trade_fills.json   docs/reports/evidence_2026-07-07/p0_fills.json
cp ~/SierraChart_Data/v9_export/trade_result.json  docs/reports/evidence_2026-07-07/p0_result.json 2>/dev/null || true
# 3. the DB row(s) for that trade — raw
psql postgresql://localhost/mems26 -c \
 "SELECT id,mode,direction,contracts,entry_price,stop,t1,state,exit_price,entry_ts \
  FROM v9_trades ORDER BY id DESC LIMIT 4;" | tee docs/reports/evidence_2026-07-07/p0_db_rows.txt
# 4. paste the raw Sierra Message Log lines (ORDER_SUBMITTED + ENTRY fill) into p0_msglog.txt
```
Pass criterion (what Cowork will check, all must hold):
- `p0_dll_mtime.txt` mtime **after 2026-07-07 06:42** (else the fix isn't deployed).
- `p0_command.json` has `"contracts": 2` and a numeric price.
- `p0_fills.json` shows **2 ENTRY fills** at a real numeric price (not 0, not the stop).
- `p0_result.json` / msglog = `ORDER_SUBMITTED` — **NOT** `GENERAL_ERROR_OR_NOT_ENABLED`.
- **Triangulate:** the fill price in `p0_fills.json` == `entry_price` in `p0_db_rows.txt` == the
  Message Log fill line. If these three disagree → NOT green.

### P1.1 — auto-flatten actually closes a SIM position at RTH close
Set `EOD_FLATTEN_V1=1`, open a SIM position, force ET clock ≥15:59 (or call the flatten path).
Copy: `p1_1_flatten_command.json` (the CANCEL), `p1_1_flatten_fills.json` (the flat fill),
`p1_1_db_row.txt` (trade now CLOSED). Paste the `[BarLevelDetector] EOD FLATTEN...` log line.
Pass: a CANCEL command exists → a flat fill came back → the DB row is CLOSED (via the fill, not
hand-marked). Confirm the log says "awaiting Sierra flat fill" (I-62 path).

### P1.2 — orphan / fill-drop is loud (not silently dropped)
With a SIM position open, restart the backend (`launchctl kickstart -k gui/$UID/com.mems26.backend`).
Paste the fill_poller log after restart → either "fallback to most recent … trade" (re-adopted)
OR a **CRITICAL** "fill dropped" alert. Copy `p1_2_restart_log.txt` + the DB/slot state after.
Pass: the live fill is re-adopted, OR the drop is raised to CRITICAL (a WARNING that Michael won't
see does NOT pass). If P1.2 isn't built yet → say so; Cowork builds it.

### P1.3 — reconcile runs for LIVE and shows agreement
With a live/SIM slot active, trigger one reconcile pass. Copy `p1_3_reconcile.txt` = the raw 3-way
output (gateway slot ↔ DB ↔ Sierra position). Pass: verdict MATCH, and the three quantities are
shown (not just the word "MATCH"). If not built → say so.

### P2.4 — System 6 diagnoses the real SIM trade every bar
Set `SYSTEM6_SUPERVISOR=1` (keep `SYSTEM6_AUTOCORRECT=0`), restart. On the open SIM trade, copy
one bar's diagnosis into `p2_4_system6_bar.txt` — the `[System6]` lines (the 9 checks + any
"recommended (SYSTEM6_AUTOCORRECT off)"). Also paste the `[env_loader]` boot line proving the flag
is live. Pass: `[System6]` lines appear on a REAL trade id, once per bar.

### P3.8 — the live command carries contracts=2
Covered by `p0_command.json` (`"contracts": 2`). No extra work if P0 is done.

---
## STEP C — mandatory NOT-DONE section
List every box you could NOT green and the exact reason (Sierra setting, feed closed, not built,
etc.). Never leave a box implied-green. This section is required even if empty ("none").

## STEP D — the loop
When Michael says "CC finished," Cowork will: open every file in `evidence_2026-07-07/`,
run the pass criteria + triangulation above, and return a per-box GREEN / NOT-GREEN verdict with
the reason. Only boxes Cowork confirms from the artifacts count toward the 16:30 real-money gate.

## Report template (`docs/reports/GROUND_TRUTH_2026-07-07.md`)
```
# Ground-truth evidence — 2026-07-07
Commit: <hash>   Sim Mode: ON   Account: 37138283
## Status matrix
<the table from STEP A, filled>
## P0 ... (command run + raw output + evidence file paths)
## P1.1 ... ## P1.2 ... ## P1.3 ... ## P2.4 ... ## P3.8 ...
## NOT-DONE
<items + reasons, or "none">
```
