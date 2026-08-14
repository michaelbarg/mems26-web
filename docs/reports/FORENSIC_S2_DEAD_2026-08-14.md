# FORENSIC — "System 2 is not functioning on BOTH machines" (2026-08-14)

**Author:** cowork-dev (Cowork/MacBook) · read-only forensic
**Scope:** why S2 (five-minute pattern system) produced 0 candidates today on mac-1 and mac-2.
**Discipline:** no code, flag, config or service was changed. Every number below is a
measured live value or a DB/log/file quote (Pre-LIVE Rule 5).

---

## 0. Verdict (one paragraph)

S2 is **not crashed and not blind on mac-1** — it is *starved*, and the starvation is the
direct, predicted consequence of a **correct** bug-fix. Until 2026-08-12 the BarRouter
`5min` topic had **two publishers**; the second one (local tick aggregator) carried
**cumulative volume 100–800× real**, which inflated S2's `_rolling_avg` so much that the
D-RVX volume gate (`variant: UNION`) passed **~99.5 %** of the time. Commit **`66619922`
(F2, 2026-08-12 06:49)** removed that publisher. With honest single-source Sierra volume
the same gate passes **26.5 %** of the time — so S2's detection rate fell from ~24 to ~4/day
and, on a quiet day like today, to **0**. **The July fire rate was the bug; the current
silence is the un-calibrated gate.** mac-2 is a *different and much older* failure: its S2
buffer is still fed by that poisoned aggregator series (volume ≈ 950,000 vs mac-1's 12,493),
so the volume-drop gate can **never** pass there — S2 on mac-2 has produced **zero
detections since 2026-07-16**.

---

## 1. The S2 input path (code trace)

| Hop | File:line | What it does |
|---|---|---|
| Subscription | `backend/v9/systems/five_min/five_min_system.py:225-228` | `subscribed_channels = ["mems26:events:bar.5min", "mems26:events:system.day_type.classification"]` |
| Publisher A (canonical) | `backend/v9/api/v9/bars.py:764` | `_route_bar("5min", _flat_5min_for_router(last_valid_bar, …))` — Sierra `5min.json` **closed** bar, `vol>100k` guard applied |
| Publisher B (removed) | `backend/v9/services/bar_aggregator_5min.py:190-218` | local tick aggregator. **Gated OFF in code since F2** behind `AGGREGATOR_5MIN_PUBLISH_V1` |
| Publisher C (new, today) | `backend/v9/api/v9/bars.py:1461-1496` | `e37263b9` failover — republishes `last_flat` on `5min` after `BAR5_FAILOVER_SECONDS` (120s) of raw-channel silence |
| Consumer | `five_min_system.py:1130 process_bar` | mode transition → key normalise → **dedup on `_canon_bar_ts`** (1203-1216) → ATR → FHB → opening-entry → detectors |
| Hydration | `five_min_system.py:274-459` | day_type from `v9_day_type_state`; bars from `v9_bars_5min` → **fallback** `v9_bars_5min_woodies` (`ad868148`); FHB rebuild; buffer truncated to **last 20 bars** (385-386) |
| Emit gate | `five_min/setup_emitter.py:75-138` | Auth-Table verdict; `SKIP` → `return None` unless opening-window override or `AUTH_LOWCONF_REDUCED_V1` |
| Inspector | `build_status/s2_inspector.py` | independent re-implementation; freshness from `v9_bars_5min_woodies` (`ad868148`) |

### Full dependency list before any S2 pattern can arm
`bar recency < 660 s` · `bar buffer ≥ 14` (CCI history) · `day_type ∈ known ∧ ≠ Nontrend` ·
`auth_table[pattern][day_type] ≠ SKIP` · `mode ∈ {FIRST_HOUR_TACTICAL, DAY_TYPE_MODE}` ·
`FHB ∉ {ACCUMULATING, UNKNOWN}` · `choppiness_ok` (gate DISABLED by standing decision) ·
per-pattern geometry probe · `r_t1 ≥ 1.0`.

---

## 2. Live measurement — both machines, 2026-08-14 ~17:40–17:46 IDT

Source: `GET /api/v9/build/pattern-status` on each host.

| Dependency | mac-1 (localhost) | mac-2 (10.1.118.70) | Threshold | Verdict |
|---|---|---|---|---|
| `five_min_bar_recency` | **10.7 s** | **96.5 s** | < 660 s | PASS / PASS |
| `cci_14_history` (buffer) | **19** (state ctr 47) | **19** (state ctr 70) | ≥ 14 | PASS / PASS |
| `mode_context` | DAY_TYPE_MODE | DAY_TYPE_MODE | trading | PASS / PASS |
| `fhb_eligible` | MATURE@bar12 | eligible | ≠ ACCUMULATING | PASS / PASS |
| `day_type_known` | **Trend_Normal** | **Normal** | ≠ UNKNOWN | PASS / PASS |
| `nt_skip` | Trend_Normal | Normal | ≠ Nontrend | PASS / PASS |
| `choppiness_ok` | 69 (gate off) | gate off | disabled | PASS / PASS |
| `auth_table_cell` | **SKIP on 4/10** | **SKIP on 2/10** | ≠ SKIP | PARTIAL |
| **`b2_volume_drop` (REACTIVE)** | **b2=12,493 b1=17,000 ratio 0.73** ✗ | **b2=920,000 b1=950,000 ratio 0.97** ✗ | ≤ 0.70 | **FAIL / FAIL** |
| `fired_today_count` | **0** | **0** | — | — |

**Every infrastructure gate is green on both machines.** Nothing is stale, nothing is
un-hydrated, the 13.08 `ad868148` root-fix is holding (freshness reads the canonical table).
S2 dies **inside detection**, not in the data layer.

### 2a. mac-1 per-pattern blockers (live)
- `REACTIVE_LONG` → `b2_volume_drop` ratio **0.73** vs required ≤ 0.70 — *marginal miss*.
- `REACTIVE_SHORT` → `b1_buyers` (b1 was bearish) — legitimate geometry miss.
- `INITIATIVE_L/S` → `b1_expansion` range 5.50 vs need [7.7, 14.8] — legitimate.
- `BULL_FLAG` → `flag_retrace` 337 %; `BEAR_FLAG` → no pole — legitimate.
- `INVERSE_HNS`, `HNS_TOP`, `DOUBLE_BOTTOM_EE`, `DOUBLE_TOP_AA` → **`auth_table_cell = SKIP`**
  (all four are SKIP on `Trend_Normal`).
- **`DOUBLE_TOP_AA_SHORT` passed EVERY detection component and every target/stop check**
  (`peak_pair` ✓, `adam_variant` ✓, `neckline_breakout` ✓, `r_t1 = 1.0000`,
  `stop = 7818.00`, `t1/t2/t3 = 7816/7815/7813`, `sizing = 3`) and was killed **solely** by
  `auth_table[DOUBLE_TOP_AA_SHORT][Trend_Normal] = SKIP`. A complete, fully-priced setup
  discarded by the table.

### 2b. mac-2 per-pattern blockers (live)
`DOUBLE_TOP_AA_SHORT` shows **zero failing components** — infra, auth (`Normal` = FULL),
geometry and targets all pass — yet `fired_today_count = 0`. Either the engine↔probe
re-implementations have diverged, or `_fire_dedup` (30-bar cooldown for `DOUBLE_TOP_AA`)
suppressed it. **Open — must be settled on mac-2 with the engine log.**

---

## 3. Historical evidence — S2 vs S4 (mac-1 Postgres)

`v9_five_min_setups` = S2 detection-time rows. `v9_trades.firing_system` = routed fires.

| session | S2 detections | S2 trades | S2 P&L | S4 trades | S4 P&L |
|---|---|---|---|---|---|
| 2026-08-14 | **0** | **0** | 0 | 2 | -150.00 |
| 2026-08-13 | 5 | 4 | -18.75 | 4 | 368.75 |
| 2026-08-12 | 4 | **0** | 0 | 3 | 200.63 |
| 2026-08-11 | 11 | **0** | 0 | 0 | 0 |
| 2026-08-10 | 4 | 2 | -127.50 | 0 | 0 |
| 2026-08-07 | 9 | **0** | 0 | 4 | -251.25 |
| 2026-08-06 | 25 | 11 | -410.00 | 2 | 36.25 |
| 2026-08-05 | 12 | 6 | 435.00 | 4 | 672.50 |
| 2026-08-04 | 9 | 6 | 1330.00 | 9 | 831.25 |
| 2026-08-03 | 11 | 2 | 151.25 | 22 | 368.75 |
| 2026-07-31 | 24 | 13 | -298.75 | 0 | 0 |
| 2026-07-30 | 17 | 7 | 322.50 | 3 | 125.00 |

All-time: **S2 = 234 trades / −$4,536.25** · **S4 = 344 trades / −$1,786.98**.
Last S2 trade of any kind: **2026-08-13 17:45:59 IDT**.

### Gateway decision log by system
`~/SierraChart_Data/v9_export/gateway_decisions.jsonl` + `decisions_archive/`:

| file | total | sys 2 | sys 4 |
|---|---|---|---|
| `gateway_decisions.2026-08-11.jsonl` | 5,938 | **2,329** (REACTIVE_SHORT ×1,727) | 3,609 |
| `gateway_decisions.2026-08-12.jsonl` | 32 | **3** | 29 |
| `gateway_decisions.2026-08-13.jsonl` | 15 | **4** | 11 |
| `gateway_decisions.jsonl` (today) | 17 | **0** | 17 |

> **Honesty caveat:** the 5,938 → 32 collapse is **not** purely signal loss. F2 also
> normalised the dedup key, so before 08-12 each bar was re-evaluated on ~20 bridge pushes.
> The *detection* table (`v9_five_min_setups`, already deduped) is the fair metric:
> **24 → 4–5 → 0**, a genuine ~5× drop.

### mac-2 history (remote DB)
- `v9_five_min_setups` **last row = 2026-07-16**. Nothing for ~4 weeks.
- `v9_trades` in the last 14 days: **zero rows of any system**.
- mac-2 S2 is not "quiet today" — it has been **structurally dead for a month**.

---

## 4. The breaking commit + proof

**`66619922` — "F2: single-source the '5min' channel — aggregator publish OFF by default +
canonical dedup key" (2026-08-12 06:49:32 +0300)**, implementing the finding of
`ff54529c` (2026-08-11 S2 48-session audit).

The audit itself named the mechanism: the aggregator published *"cumulative volume 100–800×
real"* which *"poisons `_rolling_avg` in the D-RVX volume gate and makes `_rvol_pass`
trivially true under variant: UNION."*

### Quantified proof (replay over 57 real sessions of `v9_bars_5min_woodies`)

Re-implementing `_detect_reactive`'s volume gate exactly
(`five_min_system.py:736-757`, `variant: UNION` from `config/s2_firing.yaml`,
`S2_VSA_VOLUME=1` in `.env`) against real single-source volume, versus the same
computation with `_rolling_avg` inflated ×10 to simulate the pre-F2 mixed series:

| rolling-avg source | REACTIVE price-geometry hits | pass volume gate (UNION) | A_VSA | B_RVOL |
|---|---|---|---|---|
| **real, single-source (post-F2 = today)** | 392 | **104 (26.5 %)** | 94 | 43 |
| **inflated ×10 (pre-F2 poisoned)** | 392 | **390 (99.5 %)** | 167 | **390** |

`B_RVOL` (`b2_vol ≤ 0.5 × _rolling_avg`) goes **43 → 390**. Because the selector is
`UNION` (`_vsa_pass or _rvol_pass or _strict_pass`), a trivially-true `B_RVOL` made the
whole volume gate a **no-op** for three months. Removing the poison restored the gate — and
nobody re-calibrated its thresholds against honest volume.

RTH-only replay (overnight warm-up allowed, closest match to the live 20-bar buffer)
against actual REACTIVE rows shows the convergence:

| session | model: geometry | model: passes vol-gate | actual REACTIVE detections |
|---|---|---|---|
| 2026-07-29 | 11 | 2 | **24** |
| 2026-08-06 | 12 | 1 | **18** |
| 2026-08-12 | 6 | 1 | **1** |
| 2026-08-13 | 11 | 1 | **4** |
| 2026-08-14 | 2 | 1 | **0** |

Before F2 the live system fired **5–20× more** than an honest-volume model predicts.
After F2 the live count **collapsed onto the model**. That is the signature of the fix
removing a false-positive source, not of a new defect.

**Secondary contributor — `ad868148` is NOT the culprit.** It is holding correctly:
freshness reads `v9_bars_5min_woodies` (`lag = 10.7 s`) and the buffer hydrates.

---

## 5. The `day_type_gate.auth_table_cell` dependency

**What it is.** `AUTH_TABLE[pattern][day_type] → (verdict, HIGH, MEDIUM, LOW)`,
verdict ∈ {FULL, REDUCED, SKIP}. `SKIP` = pattern forbidden for that day type.

**Where it comes from — TWO copies, one spec:**
- Engine: `backend/v9/systems/five_min/auth_table_v1.py` — loads `config/auth_matrix.yaml`
  when present, else a hardcoded fallback (`auth_table_v1.py:128-131`).
- Inspector: `backend/v9/systems/build_status/auth_table_lookup.py` — an **independent
  hardcoded const dict**, no YAML.
- Spec of record: `docs/spec_authority/S2_AUTH_TABLE_V1.md` §4 (🔒 LOCKED 2026-05-25).

Both agree today (verified by diffing the SKIP sets), but the inspector copy **cannot see
`auth_matrix.yaml`** — an edit to the YAML silently desynchronises the dashboard from the
engine. `S2_AUTH_MATRIX_SINGLE_SOURCE_V1=1` is set in `.env`, which makes the second
hardcoded copy an active drift hazard.

**Is it satisfiable today? Yes — partially.** Per day type, patterns NOT skipped:

| day_type | allowed patterns (10 total) |
|---|---|
| `Trend_Normal` (mac-1 now) | REACTIVE ×2 (REDUCED), INITIATIVE ×2 (FULL), FLAGS ×2 (FULL) — **6/10; the 4 chart patterns SKIP** |
| `Normal` (mac-2 now) | REACTIVE ×2, HNS ×2, DOUBLE ×2 (FULL), FLAGS ×2 (REDUCED) — **8/10; INITIATIVE ×2 SKIP** |
| `Nontrend` | **0/10 — everything SKIP** |

So the auth table is *not* the primary killer today, but it **did** kill one fully-formed,
priced setup on mac-1 (`DOUBLE_TOP_AA_SHORT`, §2a).

**Aggravating factor — the day-type label is flapping.** `v9_day_type_state`, today, mac-1:
`13:40 UNKNOWN → 14:00 Trend_Normal → 14:30 Normal → 14:40 Variation` (UTC). mac-2 is worse,
with confidences attached: `UNKNOWN(0.0) → Normal(0.35) → Normal(0.67) → Trend_DD(0.42) →
Variation(0.17) → Trend_DD(0.0)`. The auth verdict for a given pattern therefore changes
every 30 minutes. `AUTH_LOWCONF_REDUCED_V1=1` degrades a SKIP to REDUCED-2 when confidence
< `DAYTYPE_PLAYBOOK_MIN_CONF` (0.4), which partly rescues mac-2 but not mac-1
(`Trend_Normal` arrived with high confidence).

---

## 6. Two more live killers found today (mac-1)

**(a) `OPENING_DIR_FUSION` returned `None` and killed 3 opening signals.**
`/tmp/backend.err.log`, 2026-08-14:
```
16:55:02 [FiveMin] OPENING_DIR_FUSION = None
17:05:03 [FiveMin] OPENING_DIR_FUSION gate dropped ORR LONG (fusion=None)
17:20:04 [FiveMin] OPENING_DIR_FUSION gate dropped DRIVE SHORT (fusion=None)
17:25:02 [FiveMin] OPENING_DIR_FUSION gate dropped DRIVE SHORT (fusion=None)
```
`five_min_system.py:1366-1371` drops a trigger when `fusion is None` — i.e. **fail-closed on
a low-conviction *or a broken* fusion computation.** `get_opening_dir_fusion`
(`services/trade_context.py:922+`) reads `v9_tpo_sessions` for prior-day VAH/VAL; TPO is
`[DEAD] since 2023-11-25` per the bridge gates, so the fusion inputs are partly unavailable.
Three S2 opening candidates were destroyed today by a gate whose input is dead.

**(b) `OPENING_FIRST_TRADE_STRICT` held the first trade on `opening confidence 0.0`.**
```
16:40:04 / 16:50:05 [FiveMin] OPENING_FIRST_TRADE_STRICT held DRIVE SHORT —
                    opening confidence 0.0 < 0.6 — no certainty, no first trade
```

**(c) Red herring ruled out.** The `[FiveMin] Hydrated 60 bars…` lines at 16:51 and 17:40
are **not** a mid-session re-hydration of the live system. `backend/v9/api/v9/status.py:252`
constructs a **throwaway** `FiveMinSystem()` and hydrates that. The live `app.state`
instance is untouched. (Still wasteful and log-poisoning, but not a state bug.)

---

## 7. mac-2 — a separate, older root cause

**Measured:** mac-2's S2 buffer carries `b1_vol = 950,000`, `b2_vol = 920,000`.
mac-2's own DB (`v9_bars_5min_woodies`, read remotely) holds **4,019 / 8,245 / 12,370 /
15,139** for the same period — real MES 5-min volume. So **the bar series reaching S2 on
mac-2 is not the DB/Sierra series.**

**Ruled out:** the new failover (`e37263b9`) republishes `last_flat`, which is the DLL's
`current_bar`. mac-1's live `woodies_5min.json` shows `current_bar.ohlc.vol = 7551` —
a real volume. The failover is therefore **not** the source of the 950,000.

**Remaining explanation:** the local tick aggregator (`bar_aggregator_5min.py`), whose
volume is **cumulative** and which the 08-11 audit measured at *"V = 142,786…990,000"* —
950,000 sits squarely in that range. mac-2 is therefore running with
`AGGREGATOR_5MIN_PUBLISH_V1=1`, or on backend code older than F2.

**Why this makes S2 mathematically impossible on mac-2:** cumulative volume is monotonically
non-decreasing within a session, so
- `b2_vol < b1_vol` → essentially never → **A_VSA never passes**
- `b2_vol ≤ 0.5 × rolling_avg` → never (b2 ≈ avg) → **B_RVOL never passes**
- `C_STRICT` requires A_VSA → never
- `UNION` = never → **REACTIVE can never fire on mac-2.**
Live proof: the inspector's `ratio = 0.97` (needs ≤ 0.70). Consistent with
`v9_five_min_setups` being empty since 2026-07-16.

**Also live on mac-2:** raw `bars_5min` stream = **`[DEAD] 3,096 s ago · last 13:55:00`** —
dead through the entire RTH session, exactly the condition `e37263b9` was written for.

**Not verifiable from here (read-only, no mac-2 filesystem):** which of the two candidates
is true. **Settle it on mac-2 with:**
```bash
grep -n "AGGREGATOR_5MIN_PUBLISH_V1" /path/to/mems26_web_git/.env
git -C /path/to/mems26_web_git log --oneline -1
grep -a "FAILOVER: republished" /tmp/backend.err.log | tail -5
grep -a "\[Aggregator\] Bar closed" /tmp/backend.err.log | tail -5
```

---

## 8. Prioritised fix list

> Every item below is a **trading-risk-surface** change → strategic stop + Michael sign-off
> before enabling, per CLAUDE.md. Nothing here has been applied.

### P0 — mac-2: restore an honest `5min` publisher
**Change:** confirm §7 with the four commands, then ensure `AGGREGATOR_5MIN_PUBLISH_V1=0`
(code default) on mac-2, `git pull` to `e37263b9`, restart backend so the woodies failover is
active.
**Expected effect:** mac-2's S2 buffer carries real 1k–20k volumes instead of ~950,000; the
volume-drop gate becomes *evaluable* for the first time since 07-16.
**Verify:** `/api/v9/build/pattern-status` on mac-2 → `REACTIVE_LONG.b2_volume_drop.live`
must show a `b2_vol` in the 1,000–25,000 range; `grep "FAILOVER: republished" /tmp/backend.err.log`
non-empty; a new row appears in `v9_five_min_setups`.

### P0b — fix the failover to publish the CLOSED bar, not `current_bar`
**Change:** at `bars.py:1489` the failover publishes `last_flat`, which lines 1409-1419
**overwrite** with the DLL's in-progress `current_bar`. The commit message claims
"re-publish this same **closed** bar". Capture the closed-bar dict before the override and
publish that.
**Expected effect:** on any machine running the failover, S2 detects on completed bars (as
on mac-1) instead of the first partial push of each bar — `process_bar` runs detection
exactly once per new ts, i.e. on the *most partial* version.
**Verify:** new regression asserting the dict published on `"5min"` equals the pre-override
closed bar; then on mac-2 compare `_bar_buffer[-2]` OHLC against `v9_bars_5min_woodies`.

### P1 — re-calibrate the D-RVX volume gate against honest volume
**Change:** the gate has never been tuned on single-source data. Options, in order of
smallest correct change: (a) `config/s2_firing.yaml: variant: A_VSA` (drops the trivially-
true `B_RVOL` leg — 94 of 104 UNION passes already come from A_VSA); (b) relax the A_VSA
constant `0.7 × _rolling_avg` (`five_min_system.py:741`) to a replay-chosen value —
today's live miss was **0.73 vs 0.70**; (c) make `_rolling_avg` volume-of-day normalised
rather than a flat 17-bar mean.
**Expected effect:** measured — moving UNION→A_VSA changes 104→94 passes over 57 sessions;
relaxing the 0.7 constant is the lever that recovers marginal misses like today's 0.73.
**Verify:** replay over the 57 sessions in `v9_bars_5min_woodies` with the 4-contract model
(same harness as `ff54529c`); accept only if expectancy improves, then sim-drill before live.

### P2 — single-source the Auth Table
**Change:** delete the hardcoded `AUTH_TABLE` in
`build_status/auth_table_lookup.py` and import `five_min/auth_table_v1.get_auth_cell`, so
the inspector and the engine read the same `config/auth_matrix.yaml`.
**Expected effect:** no behaviour change today (the copies agree); removes the silent-drift
class that `S2_AUTH_MATRIX_SINGLE_SOURCE_V1` was supposed to close.
**Verify:** a test that mutates `auth_matrix.yaml` and asserts the inspector's
`auth_table_cell` verdict changes with it.

### P3 — stop `OPENING_DIR_FUSION=None` from silently killing signals
**Change:** `five_min_system.py:1366-1371` treats "fusion unavailable" and "fusion
disagrees" identically. Separate them: drop only on **disagreement**; when the inputs are
missing (prior-day VAH/VAL from the dead `v9_tpo_sessions`), log `WARNING` and pass through.
**Expected effect:** the 3 opening triggers killed today (ORR LONG 17:05, DRIVE SHORT 17:20
and 17:25) would have reached the gateway for a normal decision.
**Verify:** re-run today's bars through the opening engine; assert 3 triggers survive to
`route_setup`; confirm `v9_tpo_sessions` recency separately (it currently reads 2023-11-25).

### P4 — stabilise the day-type label before the Auth Table reads it
**Change:** the label flips every 30 min (`UNKNOWN → Trend_Normal → Normal → Variation` on
mac-1; six flips with confidence 0.0–0.67 on mac-2). Add hysteresis / a minimum-dwell before
a new label is allowed to change an auth verdict.
**Expected effect:** removes the "pattern was legal at 14:00, SKIP at 14:30" class; makes
`DOUBLE_TOP_AA_SHORT`-type kills reproducible instead of timing-dependent.
**Verify:** replay day-type over the last 20 sessions, count label changes/session
before-vs-after; assert no regression in the 7-type classifier's end-of-day verdict.

### P5 — resolve the mac-2 engine↔inspector divergence
**Change:** none yet — diagnose first. `DOUBLE_TOP_AA_SHORT` on mac-2 shows **zero failing
components** and still `fired_today = 0`.
**Expected effect:** either a probe bug (inspector over-reports readiness — the exact
"Bug #5" class the inspector's `buffer[:-1]` alignment was meant to kill) or a legitimate
`_fire_dedup` 30-bar cooldown.
**Verify:** on mac-2, `grep -a "DOUBLE_TOP\|_fire_dedup" /tmp/backend.err.log`; compare the
probe's window against `_detect_double_top`'s.

### P6 — consider widening the 20-bar buffer cap
**Change:** `five_min_system.py:385-386` truncates `_bar_buffer` to 20; the inspector then
evaluates 19. `INVERSE_HNS`/`HNS_TOP` need **≥3 swing highs/lows** — today mac-1 found 2 and
mac-2 found 1. The chart patterns may be structurally under-served by a 19-bar window.
**Expected effect:** more HNS/Double candidates. **Note:** these are exactly the patterns
`Trend_Normal` marks SKIP, so pair this with P2/P4 or the extra candidates are discarded anyway.
**Verify:** replay swing-count distribution at buffer 20 vs 40 over 57 sessions before changing anything.

---

## 9. Commands used (for reproduction)

```bash
curl -s http://localhost:8000/api/v9/build/pattern-status        # mac-1
curl -s http://10.1.118.70:8000/api/v9/build/pattern-status      # mac-2
psql postgresql://localhost/mems26                               # via python3+psycopg2 (no psql on PATH)
psql postgresql://michael@10.1.118.70/mems26?connect_timeout=25
git log --oneline --since=2026-07-25 -- backend/v9/systems/five_min/ backend/v9/systems/build_status/
grep -a "FiveMin" /tmp/backend.err.log
python3 -c "…"  < ~/SierraChart_Data/v9_export/gateway_decisions.jsonl + decisions_archive/*.jsonl
```
Replay scripts used for §4 live in `/tmp/s2f/` (throwaway; not committed).

---

**Nothing in this investigation changed code, flags, services or data.**
