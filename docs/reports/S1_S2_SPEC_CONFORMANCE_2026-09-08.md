# S1 / S2 — does each system trade its own definition? (08.09.2026)

**השאלה (מייקל, 08.09 18:55):** *"אני רוצה שתהיה עסקה לפי מערכת 1 ומערכת 2 בהתאם למערכת והגדרתה."*

Read-only run. Nothing started, nothing changed, no order placed.

---

## 0 · What this run could and could not measure (Rule 1 — honest failure > synthetic value)

| Wanted | Status |
|---|---|
| Fresh DB (`v9_trades`, `v9_bars_5min_woodies`) | ❌ **unreachable** — `localhost:5432` / `127.0.0.1:5432` → `Connection refused` from this sandbox. Repo SQLite (`data/mems26_local.db`) is the dead pre-06-03 file: `v9_five_min_setups` = 0 rows, `v9_bars_5min_woodies` = *database disk image is malformed*. |
| `~/SierraChart_Data/v9_export/decisions_archive/*.jsonl` | ❌ **outside the connected folders** — not readable by any tool in this session. |
| Decisions actually read | ✅ `data_handoff/מק-1/2026-09-06/gateway_decisions.jsonl` + `.../2026-09-07/...` — **215 `GATE_DECISION` rows → 58 unique setups** (dedup on `candidate_id`). 2 sessions, not 10. |
| Bars for pricing | ❌ none in-repo for 06–07.09. **Part 3 therefore cites prior measured studies; it does not re-derive them.** |

Every §1–§2 claim below is from code/spec and carries `file:line`. Every §3 number carries its source report.

---

## 1 · THE SPEC

### 1.1 S1 — the spec defines a **LABEL**, not a trade. Explicitly.

**Verdict: there is no such thing as "a trade per S1."** S1 emits a classification and a target *table*; the only systems that call the gateway are S2/S3/S4.

- `docs/handoff/agents/AGENT_S1_DAYTYPE_OBSERVER_SPEC.md:3` — *"**System:** S1 Day Type · **Type:** OBSERVER — **never fires trades**"*, and its test matrix, `:45`: *"No `route_setup` / no firing_system=1 | grep gateway calls | **must be zero**"*.
- `docs/spec_authority/S1_TRADE_MANAGEMENT_3CONTRACTS.md:3` — *"זהו ה-spec הקובע ל**ניהול העסקה פר-סוג-יום**, **הגשר** שמחבר את זיהוי-סוג-היום (S1) לתבניות-הירי (S2/S4)"*; `:36-37` — *"## הגשר למערכות היורות (S2/S4) — כל תבנית-ירי … צריכה להיכנס תחת **המשמעת של סוג-היום**"*.
- Zero emission sites: every `route_setup(...)` in the repo passes `2`, `3` or `4` — `five_min_system.py:1510,1560,1627,1805,2233,2336,2371,2404,3247` (all `2`), `woodies_system.py:1338` (`4`), `footprint_system.py:457` (`3`). No file under `backend/v9/systems/day_type/` imports the gateway at all.
- `firing_system=1` is written **only in test fixtures** (`tests/v9/db/test_models.py:97`, `tests/v9/services/test_trade_context.py:20`, …). `backend/v9/db/models/trades.py:20` comments `# 1, 2, or 4` — an unused slot.
- The "opening entry" is **S2, not S1**: `backend/v9/systems/opening_entry.py:310-311` returns `"firing_system": 2`.

**So S1's product is:** a 7-type label (`classify_session` → `classifier_core.py`, canonical per `docs/spec_authority/S1_ACTIVE_CANONICAL.md:16-19`), stamped as `day_type_at_entry` (`trade_context.extract_g1_entry_context`, `S1_ACTIVE_CANONICAL.md:42-55`), plus an **R-multiple** target/time-stop table (`day_type/targets_table.py:32-131`) and a no-trade flag (`:117-130`, `Nontrend → "no_trade": True`).

**⇒ "a trade per S1" can only mean one thing: every S2/S4 trade must carry S1's discipline — its targets, its time-stop, its contract count. §2.3 shows that today it does not.**

### 1.2 S2 — three authorities, and the one Michael approved was never built

| Document | Status in its own words | Implemented? |
|---|---|---|
| **Constitution V3 §T1** `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt:59-82` | the original 4-bar geometry | ✅ **this is what runs** |
| **S2 Authority Table V1** `docs/spec_authority/S2_AUTH_TABLE_V1.md:3` | *"🔒 LOCKED · 2026-05-25 … Michael chat approval"* | ✅ sizing only |
| **REACTIVE spec** `docs/spec_authority/REACTIVE_SPEC_DRAFT.md:3` | *"נכתב 2026-06-28 … **לא יושם בקוד** — מסמך-אישור בלבד"* — then `:89-91` record Michael closing three of its four open items on 28.06 | ❌ **still not built, 72 days later** |
| **INITIATIVE spec** `docs/spec_authority/INITIATIVE_SPEC_TOOLCONSTRAINED_2026-06-30.md:3` | *"**All numbers are PRIORS to calibrate, not measured facts.**"* | ❌ never built |

**Constitution V3 (what the code claims to trade)** — `MEMS26_CONSTITUTION_V3_FINAL.txt:63-82`:
> Reactive LONG: *"בר 1: מוכרים שולטים, מגיע לתמיכה · בר 2: drop 90% volume מוכרים · בר 3: בטן קונים נוצרת + POC_VOL עולה · בר 4: confirmation · COT > AMT"*
> Initiative LONG: *"בר 1: הרחבה ראשונה (6-7 ticks) · בר 2: בחינה (Higher Low / חזרה ל-POC) · בר 3: הצטרפות (גדולה מ-1) · **בר 4: בחינה שנייה = entry** · COT < AMT"*

The Constitution defines the **event and the entry bar only**. It defines no stop and no target. That is the gap the 28.06 REACTIVE spec was written to fill:

- **event** — `REACTIVE_SPEC_DRAFT.md:35-37`: 4 bars, B2 volume collapse `B2_vol ≤ 0.85 × B1_vol`, at the value edge (SHORT with the high at VAH / LONG with the low at VAL), **entry on the *second* test of the level** (*"הכניסה על הבדיקה ה-**שנייה** (שנכשלה)"*).
- **entry** — `:45`: *"על אישור B4 **של הבדיקה-השנייה** של הרמה"*.
- **stop** — `:53`: *"**2 טיק** מתחת לבר הנמוך ביותר במבנה (LONG) / 2 טיק מעל הגבוה ביותר (SHORT). (`2T מעבר ל-min(low B1..B3)`)"*
- **targets** — `:62-66`: *"היעדים = **נקודות-עצירה** (HVN … ) + POC + VAH … **T1** = ה-HVN הראשון **לפני POC**. **אם אין HVN לפני POC** → T1 = **POC**. **T2** = הנקודה הבאה … **T3** = הבאה אחריה (HVN · או **VAH** כברירת-מחדל)."* — **price levels, never R-multiples.**
- **contracts** — `:56`: *"**C1 → T1 · C2 → T2 · C3 → T3** — חוזה לכל נקודת-עצירה (מאושר Michael 2026-06-28)"*, with *"רצפת-3-נק' ל-T1"* and BE+1T on the runners after C1 (`:58`).
- **eligibility** — `:27-29`: REACTIVE is a fade to POC ⇒ **balanced days only**; *"⛔ Variation / Trend_Normal / Trend_DD → **לא REACTIVE**"*.
- And the spec names its own unclosed gap, `:81`: *"שער-המיקום **עיוור-לתבנית** — הוא מקבל את ארגומנט ה-`pattern` אבל **מתעלם ממנו** … כדי שכלל-סוג-היום של REACTIVE יהיה אמיתי → צריך להפוך את השער לפטרן-מודע … או שהתבנית (S2) תישא את הלוגיקה."*

**INITIATIVE** (`INITIATIVE_SPEC_TOOLCONSTRAINED_2026-06-30.md`) — §A: *"Initiative = **location + acceptance, not the action**"*; STATE 5 requires `accept_N` consecutive closes beyond the reference; STATE 7 caps entry distance at `min(1.0 × IB-width, 1.0 × ATR)`; D1 is *"tight by default, ATR-floored"* with the R coming **from the trail, not the initial stop**. None of acceptance, reference-distance, or the trail-first thesis exists in `_detect_initiative`.

---

## 2 · THE LIVE PATH — where it diverges

### 2.1 The entry

Spec: the confirmed B4 of the **second** test of the level (`REACTIVE_SPEC_DRAFT.md:37,45`).
Code: `five_min_system.py:2599-2600` — `_completed_bar = _det_buf[-1]`, `entry_price = _completed_bar["c"]`. **Any** B4 close; there is no second-test test anywhere in `_detect_reactive` (`:874-1129`) — the only occurrence of "second test" in the file is the INITIATIVE docstring at `:1138`. The value-edge location requirement is likewise absent from the detector and lives only in the gateway playbook (see §2.4). **Entry price: conformant. Entry condition: not.**

### 2.2 The stop — the producer's anchor is computed and then discarded, twice

1. **S2 computes the spec's anchor and drops it.** `_detect_reactive` returns `structural_anchor = min/max of b1..b3` (`five_min_system.py:1044`, `:1114`; INITIATIVE `:1243`, `:1275`). But with `STOP_ANCHORS_V2=1` (live) the Reactive/OFA branch takes `a["type"] in ("support_zone","breakout_bar") and a.get("window")` → `resolve_anchor_from_window(...)` (`:2651-2676`) and the pattern anchor is **never read**. `config/stop_anchors.yaml:94` gives `Reactive: window 4`, `:95` `OFA_Initiative: window 1` — and `STOP_STRUCTURE_EXTREME_V1=1` widens both to `structure_window_bars` (`five_min_system.py:2669-2670`), i.e. **`config/stop_anchors.yaml:17` = 12 bars = one hour**. Offset is `anchor_offset_ticks: 6` (`:16`), not the spec's 2.
   **⇒ spec stop = 3-bar structure + 2 ticks. Live stop = 12-bar (60-min) extreme + 6 ticks.** Different window, different offset, and the anchor the pattern itself identified is thrown away.
2. **The gateway replaces it again.** `STOP_RESOLVER_V1=1` walks bar-extreme rungs and keeps only one inside `[max(0.5×ATR,1.0), min(1.2×ATR,25)]` (`stop_anchors/stop_resolver.py:87,104-105,126-156`), then `trading_gateway.py:2952` `setup["stop"] = _sr_res.stop_price`. The ATR is a 12-bar mean (`trading_gateway.py:2827-2838`) floored by yesterday's RTH ATR under `EARLY_ATR_FLOOR_V1` (`:2846-2877`).
3. **And once more.** `STEP_SCALED_LADDER_V1=1` runs *after* and overwrites stop **and all three targets**: `trading_gateway.py:3385-3389`, formula `stop_dist = max(4.0, 0.6 × median_zigzag_leg)` (`step_scaled_ladder.py:196`). The code's own arbitration log exists because *"0 of 15 stops on 17.08 were the resolver's"* (`trading_gateway.py:3360-3365`). It is skipped only for `_STEP_NATIVE_STOP_SOURCES = ("TREND_STEP_LEG",)` (`trading_gateway.py:62`) — **REACTIVE and INITIATIVE are not exempt.**

The failure mode is documented in the repo, in code, by today's own fix (`trading_gateway.py:3667-3674`):
> *"Measured live 08.09 18:20:04 — DOUBLE_BOTTOM_EE_LONG … S2 emitted entry 7701.25 stop 7676.00 t1 7711.12 · STOP ARBITRATION cut the stop 7676.00 → 7693.75 · §3 STRUCT_TARGETS_WIN cut t1 7707.50 → 7703.25 · BLOCKED rr_hard_floor: R:R 0.27. Ten points of reward became two, and the trade was then refused for the ratio the chain had just made."*
`RR_NO_SELF_INFLICTED_V1` (`:3681-3707`, `=1`) restores **t1 only** — `_stop_dist` is not reverted (`:3703-3707`). The stop rewrite still stands.

### 2.3 The targets — five writers, all ON at once, none of them the spec

Spec T1/T2/T3 = HVN → POC → VAH (`REACTIVE_SPEC_DRAFT.md:62-66`). What actually writes them, in execution order, with today's `.env`:

| # | writer | flag (`.env`) | what it puts there |
|---|---|---|---|
| 0 | S2 R-ladder / structure-end | `T1_STRUCTURE_END_V1=1` | `five_min_system.py:3084-3102` R-multiples off the stop, or `:3135` the 12-bar profit-side extreme |
| 1 | #68 structural | `DAYTYPE_TARGETS_STRUCTURAL=1` | `trading_gateway.py:3183/3189/3192` — IB/POC/VA levels |
| 2 | zones | `TARGET_ZONES_V1=1` | `:3319/3321` — t2/t3 from confluence clusters |
| 3 | step ladder | `STEP_SCALED_LADDER_V1=1` | `:3386-3388` — 0.5/1.0/1.5 × median leg |
| 4 | struct-wins | `STRUCT_TARGETS_WIN_V1=1` | `:3435-3439` — re-applies #68, *"Applied AFTER step-scaled-ladder so it wins"* (`:3407`) |
| 5 | realism / IB clamp | `TARGET_REALISM_V1=1`, `TARGET_STRUCTURE_CLAMP_V1` | `:3550`, `:3494-3521` — tighten-only |

`day_type_targets.compute_targets_for_day_type` (`day_type/day_type_targets.py:50-52`) is pure `entry ± t1_r × R`. **S1's table is R-multiples; the REACTIVE spec's targets are market structure. They are not the same object, and neither survives to the order anyway.**

**Observed in the tape.** `2026-09-07 16:35:10` and `16:40:08`, `REACTIVE_LONG`, blocked at `daytype_playbook` — gate #12 at `trading_gateway.py:1611`, which is **before** every rewrite above, so the logged `mfe_track` (written at `:919-923`) is the *producer's* own bracket:

| ts | entry | stop | risk | t1 | t2 | t3 |
|---|---|---|---|---|---|---|
| 16:35:10 | 7708.75 | 7701.25 | 7.50 | 7720.00 = **1.50 R** | 7723.75 = **2.00 R** | None |
| 16:40:08 | 7709.50 | 7701.25 | 8.25 | 7721.875 = **1.50 R** | 7726.00 = **2.00 R** | None |

Two facts follow. (a) `t1 = 7721.875` is **not on a 0.25 tick** — it is an arithmetic multiple, not a structural price; the spec's T1 is always a level. (b) `t2 = exactly 2.00 R` is the **generic fallback** at `five_min_system.py:3095-3096` / `:3077`, *not* the `Variation` row of S1's own table (`targets_table.py:64-65` → `t2_r: 2.5`) — while the gateway rejected the very same setup with *"REACTIVE responsive LONG not at VAL (mid_value) **on Variation**"*. **S2 priced the trade with no day-type; S1's label was applied only to veto it.**

### 2.4 Day-type eligibility is a gate, not a producer rule

`_detect_reactive` (`five_min_system.py:874-1129`) has **no** day-type eligibility test — it fires on any day. Eligibility appears twice downstream: the Auth Table inside `emit_t1_setup` (`setup_emitter.py:119-124`) and `daytype_playbook` in the gateway (`trading_gateway.py:1611`). This is exactly the shape the spec itself predicted at `REACTIVE_SPEC_DRAFT.md:81`, and it is why on 07.09 REACTIVE fired twice on a Variation day — a day on which, per `REACTIVE_SPEC_DRAFT.md:28`, REACTIVE **does not exist**.

There is also a spec-vs-spec contradiction to settle: `S2_AUTH_TABLE_V1.md:63-64` grants `REACTIVE_LONG/SHORT` ⚠️ 2/1/0 and 2/2/0 on **Trend_Normal / Trend_DD**, and ✅ 3/2/2 on **Variation** — days on which the 28.06 REACTIVE ruling forbids it outright.

### 2.5 Contracts

`REACTIVE_SPEC_DRAFT.md:56` = 3 contracts, one per stopping point. `S2_AUTH_TABLE_V1.md:63-71` = 3/2/2 (REACTIVE), 3/2/1 (INITIATIVE), max 3 (`:19`, *"cap at 3 · ×0.75"*). Standing ruling = **5** (`config/RULED_FLAGS.yaml:306`, `FIXED_CONTRACTS_5=1`). Resolution: `sierra_command.py:747-775` takes `_fixed = ruled_contracts()` = 5, reads the Auth-Table number from `metadata.sizing` (`five_min_system.py:284`) and returns `min(_fixed, _cut)` — **so the ruled 5 is silently capped to ≤3 for every REACTIVE/INITIATIVE fire.** The ruling and the locked table disagree and the table wins, quietly. That needs one line from Michael, not a code change.

### 2.6 Gate census — the 2 sessions this run could read

`data_handoff/מק-1/{2026-09-06,2026-09-07}/gateway_decisions.jsonl` · 215 `GATE_DECISION` rows → **58 unique setups** (dedup on `candidate_id`; the raw feed repeats one `S2_DELTA_DBL_LONG` candidate 160 times). **All 58 blocked — zero fires in these two sessions' logs.**

- **S2, n=26 unique:** first-blocker `awaiting_release` 16 · `daytype_playbook` 3 · `entry_location_quality` 2 · `direction_compass` 2 · `structural_targets_wrong_side` 1 · `entry_not_confirmed` 1 · `eod_entry_cutoff` 1. Patterns: `S2_DELTA_DBL_LONG` 10, `REACTIVE_*` 4, `INITIATIVE_*` 4, `DOUBLE_TOP_AA_SHORT` 2, one each of `FAILED_BREAK_*`, `VA_FADE_LONG`, `DALTON_EDGE_LONG`, `CEILING_FLIP_LONG`, `OPENING_DRIVE`.
- **S4, n=32:** `extreme_chase_guard` 8 · `eod_entry_cutoff` 7 · `awaiting_release` 5 · `daytype_playbook` 4 · rest ≤2.
- The four REACTIVE/INITIATIVE named-spec setups on 07.09 died at: `direction_compass` (14:00), `daytype_playbook` ×3 (15:00, 16:35, 16:40) — i.e. **at day-type/direction gates, never at their own geometry.**

Note `RELEASE_ENTRY_GATE_V1` was ruled OFF today at 17:20 (`config/RULED_FLAGS.yaml:19`, `.env` now `=0`), so the 16 `awaiting_release` blocks above are from **before** that ruling and do not describe tomorrow's chain.

---

## 3 · THE GAP, PRICED (cited — not re-derived; see §0)

No DB and no bars in this session, so per the caller's own rule I do not compute a new number. What is already measured and binds here:

- **Replacing the sent stop with the structural stop is worse, not better.** n=54 priced live trades / 17 sessions (10.08→07.09): as-traded **+$283.80** vs structural same-size **−$845.00**; 7 losers became winners, **23 winners became losers**; 30 of 54 structural stops exceed the 15-pt risk budget and would be refused outright, and those 30 booked +$561.25 of the +$523.75 realised. `docs/reports/STRUCTURAL_STOP_REPLAY_2026-09-08.md:9-13,29,49-51`. **⇒ §2.2's divergence is real but the naive spec-side fix is measured negative. This is the second time today a spec-side change priced worse than the live one.**
- **Target clamping to the IB edge:** n=9 decisive episodes, net **+$230.00**, all shadow, 0 live — *"n קטן מדי כדי להכריע"*; but 10/10 Variation sessions left the IB (median +17.00 pt), so the premise behind the clamp is falsified even where the money is not. `docs/reports/IB_CLAMP_COST_2026-09-08.md:102-105,136-141`.
- **Which gate actually holds S2/S4 back:** `awaiting_release` n=150 saved/blocked **0.83**, `daytype_playbook` n=47 **0.48**, `entry_location_quality` n=60 **0.54**, all-441 baseline 0.95 (08-10→09-07). `docs/reports/ASYMMETRY_17D_2026-09-08.md:90-100`.
- **REACTIVE/INITIATIVE live P&L to 22.08** (the only per-pattern split on record): REACTIVE_SHORT 17 trades **+$161.25** · REACTIVE_LONG 10 **+$535.00** · INITIATIVE_LONG 8 **+$57.50** · INITIATIVE_SHORT 7 **+$51.25** — all four **positive live**, all four heavily negative in shadow. `docs/reports/DEAD_SYSTEMS_AUDIT_2026-08-22.md:63-70`.
- **The moments are seen, not missed:** 16 of 17 best moments over 6 days were produced by S2/S4 on the right bar; 13 were blocked. `docs/reports/SIX_DAYS_MOMENTS_2026-09-08.md:283-286`.

⚠️ MES = $5/point. Contract counts above are as stated in each source report (mostly 2c; the ASYMMETRY/STRUCTURAL sets are broker-priced live). Do not mix them.

---

## 4 · WHAT TO CHANGE (smallest set)

Ordered by ruling status. **Nothing here is proposed for enabling on in-sample evidence.**

| # | Change | File / flag | Ruling status | The measurement that closes it |
|---|---|---|---|---|
| **1** | **Stop what the producer names is discarded.** Exempt `REACTIVE`/`OFA_Initiative` from the *window* override so the pattern's own `structural_anchor` (`five_min_system.py:1044,1114,1243,1275`) is the anchor — the 12-bar widening at `:2669-2670` was ruled for structure-window families, and silently swallowed the two patterns that already carry their own structure. | `five_min_system.py:2651-2676` · `STOP_STRUCTURE_EXTREME_V1` | **Implements an existing ruling** (28.06 REACTIVE §5) — but §3 shows the naive version prices **−$845**. ⇒ **build in shadow, do not enable.** | Replay the 54-trade set with anchor = `min(low b1..b3) ± 2T` **and the resolver band left ON**, split by whether the resolver then rejects. If it is not ≥ the as-traded +$283.80 out-of-sample, it dies. |
| **2** | **Add REACTIVE/INITIATIVE to `_STEP_NATIVE_STOP_SOURCES`** so the step ladder cannot overwrite a stop the pattern owns — the same exemption `TREND_STEP_LEG` already has. | `trading_gateway.py:62` | **New** — needs one ruling. | Count, over ≥10 sessions, how often the ladder currently moves an S2 stop and by how much; the arbitration log already prints it (`:3391-3399`). Zero-cost to measure, no flag needed. |
| **3** | **Move REACTIVE's day-type eligibility into the producer.** `_detect_reactive` returns nothing on Trend/Variation days instead of firing and being vetoed at `trading_gateway.py:1611`. | `five_min_system.py:874-1129` | **Implements 28.06 §1** (`REACTIVE_SPEC_DRAFT.md:28`) — *but* it contradicts the LOCKED Auth Table (`S2_AUTH_TABLE_V1.md:63-64`, REACTIVE allowed on TN/TDD/NV). ⇒ **strategic stop: Michael must say which of his two documents wins.** | Once ruled: the 4 REACTIVE fires in the 2 sessions read here all died at day-type gates — the change is behaviour-neutral on that sample and the measurement is only "did the block count go to zero at the producer". |
| **4** | **One day-type per fire.** S2 priced the 07.09 16:35/16:40 setups with `_targets = None` (generic 2R) while the gateway judged them "Variation". Pass the resolved label into the target computation, or refuse to price without one (Rule 1). | `five_min_system.py:3084-3102` | **Bug, not a ruling** — `S2_DETECTION_LIVE_DAYTYPE_V1` (`RULED_FLAGS.yaml:148`, ON) already rules that S2 must read the live label. | Log `day_type` alongside every `mfe_track`; a conformant fire has `t2 = t2_r × R` from `targets_table.py` for its own label, never the 2.0R fallback. |
| **5** | **Build the REACTIVE target definition at all** — T1/T2/T3 as HVN→POC→VAH price levels (`REACTIVE_SPEC_DRAFT.md:62-66`). | new; `hvn_zones` source | **Ruled 28.06, never built.** Blocked by data: the spec's own `:67` says `v9_tpo_sessions.hvn_zones` is empty ⇒ **no historical backtest is possible**; forward-shadow only. | Record `hvn_zones` at every fire starting now; the study cannot begin before that. Say so to Michael rather than substituting an R-ladder for it a fourth time. |
| **6** | **Reconcile 5 contracts vs. the Auth Table's 3.** Today `min(5, auth)` silently makes the standing ruling inoperative for S2. | `sierra_command.py:747-775` · `FIXED_CONTRACTS_5` | **Two live rulings collide** (`RULED_FLAGS.yaml:306` vs `S2_AUTH_TABLE_V1.md:19`) — needs one line from Michael, no code question. | Count actual `contracts` on S2 live fills over 17 sessions; memory already records the modal value as 2, not 5. |
| **7** | **Housekeeping that is currently lying:** `docs/FLAG_INDEX.md:389` still shows `RELEASE_ENTRY_GATE_V1` ✅ ON after today's 17:20 OFF ruling; `STRUCT_TARGETS_WIN_V1`, `RR_NO_SELF_INFLICTED_V1`, `FIXED_CONTRACTS_5`, `T3_REQUIRED_V1` have **no row at all**; `MORNING_LABEL_CONFIRM_V1` shows ON against an explicit OFF ruling (`RULED_FLAGS.yaml:115`). | `scripts/gen_flag_index.py` | none — regeneration | `python3 scripts/gen_flag_index.py --check` must pass. Until it does, no flag answer from `FLAG_INDEX.md` is admissible. |

**S1 has no change item, and that is the answer to the question.** S1 cannot be made to "trade its own definition" because its definition is a label (§1.1). The nearest true statement of Michael's request is item **4** plus item **6**: an S2 trade should carry S1's targets, S1's time-stop and S1's contract count — and today it carries none of the three.

---

*cowork-dev · 08.09.2026 · read-only · no service started, no `.env` touched, no order placed.*
