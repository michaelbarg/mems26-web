# MEMS26 — Onboarding Handoff for a NEW Claude session (2026-07-02)

You are picking up an autonomous **MES (Micro E-mini S&P 500) 5-minute RTH futures** trading
stack running **locally** on Michael's Mac. Goal of this doc: get you oriented fast, teach you
to navigate via the **living index** (not blind grep), show you the current state + how to
continue, and hand you the open thread — **organizing the pattern set**. Read this, then the
files in §1, before touching anything.

---

## 0 · The 6 rules that override everything (read `CLAUDE.md` in full first)
1. **Use the index FIRST** to locate any file/function/system (see §1). A stale index is a bug.
2. **Verify, don't trust (Rule 5).** Diagnose from the DB/log/code — never from theory or a
   prior "✅". When you claim something works, paste the command + raw output.
3. **Local Postgres ONLY** (`postgresql://localhost/mems26`). NEVER a cloud/Render DB. Bridge pushes only to `localhost:8000`.
4. **Standing decisions are PERMANENT** until Michael revokes in writing (chop gates OFF, S2⟂S3 COT/AMT OFF, HFE_DISABLED). Don't "restore" a disabled gate. See `CLAUDE.md §Standing Decisions`.
5. **Any trading-risk-surface change is flag-gated (default OFF/SHADOW) + needs Michael sign-off** to go live. Snapshot before any out-of-git change (`.env`/DLL/LaunchAgent): `scripts/mems26_snapshot.sh`.
6. **Smallest correct change + a regression test per fix.** Finish + report one thread before the next.

## 1 · Navigate via these (consult BEFORE grepping) — all verified present
- **`CLAUDE.md`** (repo root) — the guardrails. Non-negotiable.
- **`SYSTEM_INDEX.md`** + per-dir `_INDEX.md` — the canonical file-locator (one-line purpose per file). Regenerate after structural changes: `python3 scripts/gen_index.py`.
- **`docs/SOURCE_OF_TRUTH.md`** — WHICH data source is the canonical LIVE truth per signal (bars, day-type, levels, trades) and which are stale/dead. Verify a source's last row is recent before trusting it.
- **`docs/FLAG_INDEX.md`** (generated from `docs/FLAG_REGISTRY.yaml` + live code by `scripts/gen_flag_index.py`) — every behavior/trading flag: state, default, meaning, file:line. Consult BEFORE claiming a flag's state.
- **`docs/SYSTEM_MANIFEST.md`** — every runtime surface, git-tracked AND out-of-git (DLL, `.env`, LaunchAgents).
- **`docs/plans/ROADMAP_TO_LIVE.html`** (at-a-glance) + **`docs/plans/STATUS_BOARD.md`** (source of record) — where we are, what's open. Update BOTH after every task (mandatory).
- **`scripts/mems26_verify.sh`** — one-shot consistency check (services · DLL↔repo · index drift · feed fresh · DB lag).

## 2 · The systems (what fires, where it lives)
- **S1 — day-type classifier (7 types):** Trend_Normal, Trend_DD, Variation, Normal, Neutral_Center, Neutral_Extreme, Nontrend. `S1_NEW_CLASSIFIER=1`. Feeds gates + `day_type_at_entry`. Live table `v9_day_type_state`. Only S1 defines day-type.
- **S2 — FiveMin (Reactive/Initiative + chart patterns):** `backend/v9/systems/five_min/`. Emits `T1Setup` via `setup_emitter.py`; sizing from `get_quality_tier_v2` (Auth Table).
- **S3 — footprint:** MUTED (`S3_MUTE`/I-11). Do NOT use pre-LIVE; S2⟂S3 (COT/AMT not required).
- **S4 — Woodies CCI:** `backend/v9/systems/woodies/`. ZLR/TLB/TT/GB100 (CONT), VEGAS/GHOST/FAMIR/HTLB (REV). HFE disabled. Sizing from `compute_v2_sizing` (`stop_anchors/sizing.py`).
- **Gateway (~18 gates):** `backend/v9/gateway/trading_gateway.py`. `route_setup` → SHADOW (always records) + DEMO (single `demo_slot`) + LIVE. Family gate `daytype_position_gate` (currently `DAYTYPE_POSITION_GATE=0` — TEMP validation override; revert to 1 on Michael's word).
- **Pipeline-5 — demo execution/management:** `services/trading_gateway/executors/demo.py` → `command_from_setup` (`services/sierra_command.py`) → `trade_command.json` → Sierra. Per-contract mgmt (C1/C2/C3 + BE-after-T1 + trail) via BarLevelDetector. (Internal "system 5" in logs = TPO/value-area — different thing.)
- **Feed path:** Sierra Chart DLL export → bridge → API/DB. Live bars: `v9_bars_5min_woodies` (per SoT, not the gapped `v9_bars_5min`). Source of truth = Sierra exports; do NOT synthesize OHLC/TPO/CVD/Woodies fields.

## 3 · Current state (as of 2026-07-02, pre-market)
The signal side is **firing**: S1 classifies, S2 (BULL_FLAG/REACTIVE/INITIATIVE) and S4
(ZLR/HTLB/FAMIR/VEGAS) emit + route; `DAYTYPE_POSITION_GATE=0` verified effective. Full
live-readiness audit + evidence: **`docs/handoff/CC_READINESS_AUDIT_2026-07-01.md`**.

**Just landed (committed, NOT yet live — running process predates them):**
- `6ec3209` **GAP-1 contracts fix (Cowork)** — `FIXED_CONTRACTS_3` was dead-wired (only patched `compute_v2_sizing`; the real command qty is `setup["contracts"]` from `get_quality_tier_v2`, tier-based 2/3 → MED/LOW fired **2**). Now forced 3 at the S2 sizing source + the command choke point. 3 tests pass (`tests/v9/regression/test_fixed_contracts_3_command.py`). See memory/`project_contracts_sizing_paths`.
- CC: structural target resolver (`168391c`+`e6add5d`, flag `DAYTYPE_TARGETS_STRUCTURAL=1`), warm-start (`faa1056`), demo-slot free-on-close (`e72f7f7`), opposite-pattern exit (`0930229`, `OPPOSITE_EXIT_V1` default OFF), P5 e2e test (`5d70763`).

**Immediate next action (Michael's decision):** finalize CC's uncommitted WIP, then **ONE clean
restart** brings all of the above live → **`docs/handoff/CC_FINALIZE_WIP_AND_RESTART_2026-07-02.md`**
(includes the post-restart verification checklist — prove contracts=3 and sane targets from the
live `trade_command.json`, not from tests).

## 4 · How to continue (priority order)
Master queue: **`docs/handoff/CC_WORK_QUEUE_2026-07-01.md`**. In short:
1. Finalize WIP + clean restart + verify (the handoff above).
2. Confirm live post-restart: contracts=3 on a MED/LOW fire · targets structural/capped (no −92) · demo slot frees on a normal close (not just EOD).
3. Then revisit: revert `DAYTYPE_POSITION_GATE=1` after validation; SHADOW-validate the structural resolver if not yet trusted live.
Verify each with Rule 5 + the four UAT axes (Quality/Recency/Cardinality/Latency) before any live enable.

## 5 · The pattern set — "organize the patterns" (the open thread Michael wants)
**16 active patterns** = 7 CONT (ZLR · TLB · TT · GB100 · INITIATIVE · BULL_FLAG · BEAR_FLAG)
+ 9 REV (REACTIVE · VEGAS · GHOST · FAMIR · HTLB · DOUBLE_TOP_AA · DOUBLE_BOTTOM_EE ·
INVERSE_HNS · HNS_TOP). **HFE muted · Cup&Handle NOT in system.**

Canonical pattern docs (all in `docs/spec_authority/`):
- **`PATTERN_PLAYBOOK_CANDLES.html`** — per-pattern candle geometry + structure + volume + day-type ladder, **editable** (Michael edits notes here). Built by Cowork; this is the human-facing spec.
- **`RESOLVER_TARGETS_BY_DAYTYPE.html`** — C1/C2/C3 target ladders per day-type (Michael's split: C2 = nearest structure closer than VA edge; C3 = VA edge, the runner).
- `PATTERN_PAGE.html` · `PATTERN_DEFINITIONS_INDEX.md` · `PATTERN_ACCESS_MAP.md` — index/definitions/where-each-is-wired.
- `S2_AUTH_TABLE_V1.md` + `MEMS26_Auth_Table_V2_*.csv` — pattern × day-type × tier → verdict/contracts (the S2 sizing source).
- `S4_WOODIES_PATTERN_TABLES_V1.xlsx` — S4 pattern definitions.
- `S1_TRADE_MANAGEMENT_3CONTRACTS.md` — the 3-contract management intent per day-type.
- Structural resolver code: `backend/v9/systems/structural_targets.py` (+ build spec `CC_STRUCTURAL_TARGET_RESOLVER_BUILD_2026-07-01.md`, research `RESEARCH_STRUCTURAL_TARGET_RESOLVER_TOOLCONSTRAINED_2026-07-01.md`).

**The organizing task:** reconcile these into one coherent, non-contradictory pattern spec —
verify the playbook's per-pattern structure/volume/targets match the Auth Table + the resolver
code + the day-type ladders; flag any pattern whose spec, sizing, and target logic disagree; and
keep Michael's editable HTML as the source the code is validated against. Do NOT invent patterns
or targets — every rule must trace to the §2 tools/data we actually have.

## 6 · Tools + verification
- **DB:** `/Applications/Postgres.app/Contents/Versions/18/bin/psql postgresql://localhost/mems26` (psql not on PATH; local only). Key tables: `v9_trades`, `v9_day_type_state`, `v9_bars_5min_woodies`, `v9_tpo_history`.
- **Logs:** `/tmp/backend.err.log` (fires, `[env_loader]` boot-line = runtime flags, `T1Setup emitted`, `V2 sizing`), `/tmp/bridge.err.log`.
- **Restart backend:** `launchctl kickstart -k gui/$(id -u)/com.mems26.backend` (check no dup listener on :8000; RTH must be closed/pre-market).
- **Verify flags LIVE** via the `[env_loader]` boot-line, NOT `ps eww` (that's exec env, not runtime `os.environ`).
- **Pre-trade checklist:** `docs/runbooks/PRE_TRADE_PROTOCOL.md`.

## 7 · Do NOT
Start services unless asked · re-enable a standing-decision gate · trust a single endpoint over
the real path+DB · synthesize missing Sierra fields · enable a risk change live without SHADOW +
Michael sign-off · let the index/roadmap/STATUS_BOARD lag reality · claim "done" without pasted verification.
