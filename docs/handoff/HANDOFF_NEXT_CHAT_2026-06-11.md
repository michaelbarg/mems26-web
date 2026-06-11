# Handoff → next Cowork chat · MEMS26 S2/S4 fire work (2026-06-11)

You are **Cowork**, orchestrating + **verifying** on Michael's Mac. Claude Code (CC) executes code changes; you prepare fixes, verify via **repo + live DB** (Rule 5 — paste raw command+output, **never** accept CC's "✅"), and stop for Michael at trading-logic gates. **Cowork cannot git push/commit/restart** — Michael/CC do those.

**Environment:** repo `/Users/michael/Downloads/mems26_web_git` · local Postgres `postgresql://localhost/mems26` · backend `uvicorn backend.main:app` :8000 (SHADOW, restarted today) · frontend Next.js :3000. Run python on the Mac via Desktop Commander, prefix `set -a && . ./.env && set +a`. main.py loads .env at startup (`_load_dotenv_file`) so `os.getenv` sees the flags.

---

## ✅ What shipped today — commit `319e303` (+ boards `1e85ba6`), branch `stabilize/mems26-local-truth-2026-05-16` (UNPUSHED). All flag-gated, SHADOW.

The week-long **no-fire root cause**: `pre_fire_validator` measured R:R on **T1 (the scalp, 0.4–0.8R by design)** instead of the runner → EVERY valid setup blocked (logs: 7 S2 + 13 S4 detections on 06-10, all rejected). Four fixes:
1. **pre_fire R:R on the runner/T2** (D-094); when T2=None (Option 1) uses `expected_t2_r_mult` (2.0 CONT / 1.5 REV). `backend/v9/shared/pre_fire_validator.py`.
2. **S1 provisional day_type@30** — `state_machine._maybe_provisional_classify` classifies from the **developing Sierra IB** at the half-IB mark so S2+S4 aren't blind until the 60-min lock (root of the recurring "day_type=UNKNOWN@30"). Flag `S1_PROVISIONAL_DAYTYPE`.
3. **bars.py staleness** — price-band stale check now only for the 5min stream; woodies/tpo were blocked by the shared `_latest_known_price` (**18,567 woodies bars blocked = S4-silence root**). `backend/v9/api/v9/bars.py`.
4. **Stop-sanity gates** — `MEMS_MIN_RISK_POINTS` (reject degenerate <2pt stops: the S2 1-pt Initiative/Bull-Flag) + `MEMS_MAX_RISK_POINTS` (reject oversized >60pt reversal anchors). `pre_fire_validator`, default OFF.

**Flags ON in .env (SHADOW):** `S1_PROVISIONAL_DAYTYPE=1 · STOP_ANCHORS_V2=1 · MEMS_MIN_RISK_POINTS=2 · MEMS_MAX_RISK_POINTS=60` — verified reaching `os.getenv` in the running process.
**Tests 18 green:** `tests/v9/regression/{test_s1_provisional_daytype,test_pre_fire_risk_gates,test_a7_rr_on_runner,test_pre_fire_t2_none}.py`.
**Sim:** `scripts/sim_woodies_replay.py` (replays 06-09 woodies bars through the REAL detectors+dispatcher+`SA.t1_price`+pre_fire+forward-fill). 06-09: S4 6 trades 5W/1L **+137.5pts / +$614** (real 3/2/1c sizing). Report `docs/reports/SIM_0609_POSTFIX_2026-06-11.html`.
**LIVE today (SHADOW):** S4 fired 2× — `v9_trades` id 28 (CLOSED +0.27R, 09:30 ET), id 30 (09:50 ET, T1 hit → stop moved to BE@entry).

---

## 🔴 OPEN — Michael's live questions to answer THIS session (top priority)

### 1. Trades page shows nothing (frontend display bug)
Already diagnosed: **data + backend + config all correct** — 10 trades in `v9_trades` (incl. 2 today); `curl /api/v9/trades` (token `michael-mems26-2026`) → 200 with rows; `/api/v9/trades/recent` (token-less) → 10 rows; frontend `NEXT_PUBLIC_API_URL=localhost:8000` + matching token; `DEFAULT_FILTERS` all-pass; CORS ok (apiFetch uses no credentials mode). `apiFetch` swallows errors → returns `[]` silently. ⇒ **browser-side, likely a STALE frontend build/dev-server** (CC restarted the backend, NOT the frontend on :3000, PID 69953).
**NEXT:** open `localhost:3000` Trades page in Chrome (2 browsers: MACBOOK `43c856d0-8611-4c73-a79a-1649081c90f4`, Home MAC `9dfdb5d7-7265-4124-bda8-e9df01526648`), read console + network for `/api/v9/trades`. Likely fix: **restart/rebuild the frontend**. Files: `frontend/v9/src/v9/components/trades/TradesView.tsx` (→ `fetchTrades()` → `tradeStore`), `frontend/v9/src/v9/lib/api.ts`.

### 2. T1/T2 placement review — "trades should've produced more profit" (Michael)
Michael feels **T1 looks too tight (scalp) and T2 illogical**. Facts: S4 T1 = `SA.t1_price` ladder (0–25pt risk → 1.0/0.75/0.65/0.5/0.4R). S4 **T2/T3 = None** (Option 1, CCI-cross deferred §1.6) → after T1 the runner only gets **BE+1T** (`services/trade_manager/manager.py::_apply_smart_be_after_t1`) with **NO progressive trail** (`gateway/trade_management.py` C.2/C.4 are orphan, not called) → runners leave profit on the table. Investigate whether the ladder-T1 + T2/T3=None + no-trail is why trades underperform; propose options (wider T1 / different ladder; implement the **CCI-cross T2/T3 monitor §1.6**; and/or a real progressive trail). Trading-logic → flag-gated + Michael approval.

### 3. Full per-trade failure report — "where exactly did they fail" (Michael)
Produce a per-trade report for **today's live trades** (`v9_trades` + `v9_trade_management_log`: T1_HIT, SMART_BE, stop moves) AND the sim's losers: entry / stop / T1 / T2 / where-price-went bar-by-bar / exit-reason / **the exact bar+reason it failed** / P&L. (06-09 sim's 1 loser = TLB-SHORT 14:40, −19.5pt, stopped in late chop. Today id 28 closed +0.27R only — explain why so small.) Michael wants a complete report, not a summary.

---

## Other open threads
- Scheduled task `verify-s2s4-fire-rth30-0611` fired at RTH+40 today — read its report (it checks day_type@30 + S4 fires live).
- **#16** EOD day-1 counterfactual audit agent (CC building `eod_shadow_audit.py`, spec `docs/handoff/CC_AGENT_EOD_SHADOW_AUDIT_2026-06-10.md`).
- **#26** pipeline dead-code cleanup (audit done): remove `stages/a1-a7+b1-b14`, `active_phase.py` stub, duplicate `services/trading_gateway/`, dead wrappers+EventDispatcher, `day_type/api.py _engine`, `woodies/api.py`; hide degraded build-status panels (S3 footprint, choppiness row, between-fire targets_stop). Separate commit.
- **#29** correct `docs/plans/SOLUTION_S2_S4_FIRE_2026-06-11.md` (built on a stale code-read) + boards.
- **#1** git push (Michael, from Mac — commits unpushed).
- `v9_bars_5min` ↔ `v9_bars_5min_woodies` ~3h timestamp misalignment (I-18 follow-up; the sim used woodies, which is correctly timed — high 7491 @ 09:45 ET).
- D-002 ("don't BE on T1 — stop-hunt zone") vs the live Smart-BE+1T-on-T1 — confirm with Michael which policy is intended.

## Disciplines (non-negotiable)
Rule 5 (raw evidence, never trust "✅") · trading-logic = flag-gated default-OFF + anti-tautological regression test (RED-on-revert) + strategic-stop + **Michael approval before LIVE** (SHADOW now; LIVE is a separate gate) · Standing Decisions: chop gates + `S2_REQUIRE_COT_AMT` stay OFF · local Postgres only (never cloud) · bridge localhost-only · don't raise polling · don't touch `sc_study`/bridge/market-data without §7a · source-of-truth: never synthesize CCI/study/OHLC, propagate None (Rule 1) · boards auto-update after every task · no `present_files` for tracking files (roadmap/STATUS_BOARD/CLAUDE.md).
