# CC Master — offline sweep 2026-06-07 (everything that needs no live market)

Michael approved executing all of these now, in this order. After EACH step,
write the raw output to the listed file (Cowork reads them), then continue.
Rule 5 throughout: command + raw output, never "confirmed".

## Step 1 — 🔴 BLOCKING: Postgres vs SQLite check
Execute `docs/handoff/CC_CHECK_DB_URL_RESTART_2026-06-07.md` exactly.
Output → `docs/reports/DB_URL_CHECK_2026-06-07.txt`.
If the backend is NOT on `postgresql://localhost/mems26` after this step, STOP
the sweep and report — nothing else is trustworthy until the DB is right.

## Step 2 — I-9 verify: EOD agent timing
The EOD agents fire at the wrong time (ran 09:25 CT / mid-RTH; see
`docs/reports/EOD_SCHEDULER_LOG.md`). Read-only verify, no fixes yet:
```
ls ~/Documents/Claude/Scheduled/
for d in ~/Documents/Claude/Scheduled/*/; do echo "== $d"; grep -nE "cron|schedule|when|guard|15:00|23:" "$d/SKILL.md" 2>/dev/null | head -8; done
tail -10 docs/reports/EOD_SCHEDULER_LOG.md
```
Questions to answer: (a) what cron/TZ does each EOD agent use now, (b) is the
`now_ct>=15:00` guard present, (c) did the last run fire after-close or
mid-session? Output → `docs/reports/I9_EOD_CRON_VERIFY_2026-06-07.txt`.

## Step 3 — B-14: 5-min candle duplication fix
Execute `docs/handoff/CC_PROMPT_B14_CHART_5MIN_DUP_2026-06-05.md`.
Diagnose-first per the prompt; smallest fix + regression test; commit with
explicit paths (the repo has ~200 untracked docs — never `git add -A`).
Output/report → `docs/reports/B14_FIX_REPORT_2026-06-07.md`.

## Step 4 — P5-0: gateway audit (the long one)
Execute `docs/handoff/CC_PROMPT_P5_0_GATEWAY_AUDIT_2026-06-08.md` in full.
Read-only. Output → `docs/reports/P5_0_GATEWAY_AUDIT.md` (as the prompt says),
ending with a recommendation per each of the 4 decisions + the Apex replace-map.

## When done
Write a 5-line summary (one line per step: done/blocked + the output file) to
`docs/reports/SWEEP_SUMMARY_2026-06-07.txt` and tell Michael "sweep done".

## NOT in scope (deliberately)
- Stop-anchor work — waiting on Michael's anchor definitions.
- Anything needing live RTH (I-21/I-20 diagnosis runs Monday per
  `CC_PROMPT_I21_I20_RTH_DIAGNOSE_2026-06-08.md`).
- Machine migration — runs on the NEW machine, separate session.
