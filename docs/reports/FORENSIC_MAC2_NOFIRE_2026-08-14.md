# FORENSIC — mac-2 produced 0 trades while mac-1 traded (2026-08-14)

**Investigator:** cowork-dev (remote, read-only, from mac-1)
**Method:** ZeroTier — API `http://10.1.118.70:8000` + `postgresql://michael@10.1.118.70/mems26`
**Window:** 17:39–17:53 IDT, 2026-08-14. **Nothing was changed on mac-2.**

---

## 0. Executive verdict

**The premise "mac-2 produced zero gateway candidates" is FALSE.** mac-2 produced **12
candidates**; mac-1 produced **17**. Both machines saw the same market and the same bars.

**The single blocking root cause is NOT the bar feed — it is a wrong Initial Balance
exported by mac-2's Sierra.** mac-2's IB is `7810.50–7817.50` (width **7.0**); mac-1's is
`7813.75–7830.75` (width **17.0**). POC/VAH/VAL and session high/low are **identical** on
both machines, so only the IB diverges.

That bogus `ib_low = 7810.50` became mac-2's **T1 target**, which collapsed R:R and
blocked the one trade mac-1 actually took:

| 17:35:0x IDT — same TREND_STEP SHORT | mac-1 | mac-2 |
|---|---|---|
| entry | 7811.25 | 7811.00 |
| stop / stop_dist | 7816.50 / **5.25** | — / **5.25** (identical) |
| **T1 / T1_dist** | **7807.75 / 3.50** | **7810.50 / 0.50** ← `= ib_low` |
| R:R | 0.667 (clears the 0.65 floor) | 0.095 |
| outcome | **ROUTED → live trade #668** | **blocked `rr_hard_floor`** |

`stop_dist` is identical (5.25) on both. **T1 is the only variable — and mac-2's T1 is its
wrong `ib_low` to the tick.**

---

## 1. Bars — mac-1 vs mac-2 (Postgres, today)

### `v9_bars_5min_woodies` (canonical per `docs/SOURCE_OF_TRUTH.md`)

| | mac-1 | mac-2 |
|---|---|---|
| rows today | **201** | **201** |
| min ts | 2026-08-14 01:00:00+03 | 2026-08-14 01:00:00+03 |
| max ts | 2026-08-14 **17:40:00**+03 | 2026-08-14 **17:40:00**+03 |
| `cci_14` non-null | 201 | 201 |
| `lsma_value` non-null | 201 | 201 |
| `cci_6_tcci` non-null | 201 | 201 |
| `trend_state` non-null | 201 | 201 |
| per-hour distribution | 12/h, 01:00→16:00; 9 in 17:00 | **identical, 12/h, 9 in 17:00** |

**The canonical bar feed is byte-for-byte equivalent. There is no bar-data divergence.**

### `v9_bars_5min` (legacy table)

| | mac-1 | mac-2 |
|---|---|---|
| rows today | 15 | **6** |
| min ts | 16:30:00+03 (RTH open) | 13:30:00+03 |
| max ts | **17:40:00+03 (current)** | **13:55:00+03 (frozen ≈ 4h)** |

**Divergence point: `v9_bars_5min` only.** mac-2's legacy table froze at 13:55 IDT.
**This is not load-bearing** — S2 (`five_min`), S4 (`woodies`) and the TREND_STEP detector
all read `v9_bars_5min_woodies` (`backend/v9/systems/trend_step/detector.py:220-229`
`live_bars()` → `SELECT ... FROM v9_bars_5min_woodies`). The frozen legacy table only
poisons the **display** (see §2).

---

## 2. Stream health — every stream, both machines

Sampled 17:49–17:51 IDT.

| stream | mac-1 status / age / pushes | mac-2 status / age / pushes | differs? |
|---|---|---|---|
| `live_price` | healthy · 0.4s · 4627 | healthy · 0.6s · 2881 | no |
| `tick_reversal_15` | healthy · 1.2s · 1587 | healthy · 2.6s · 1005 | no |
| `tick_reversal_12` | healthy · 1.2s · 1587 | healthy · 1.4s · 1004 | no |
| `footprint` | **no_data · — · 0** | **no_data · — · 0** | no (S3_MUTE, standing) |
| `volume_profile` | healthy · 1.1s · 1586 | healthy · 1.0s · 1004 | no |
| `imbalance_flags` | healthy · 0.7s · 1586 | healthy · 2.4s · 1004 | no |
| `stacked_imbalances` | healthy · 0.8s · 1587 | healthy · 1.0s · 1004 | no |
| `cumulative_delta` | healthy · 2.5s · 1586 | healthy · 1.0s · 1004 | no |
| `woodies_30min` | healthy · 0.8s · 1587 | healthy · 2.6s · 1004 | no |
| `woodies_5min` | healthy · 0.9s · 1586 | healthy · 1.0s · 1041 | no |
| `tpo` | healthy · 0.7s · 1587 | healthy · 1.0s · 1005 | no |
| **`5min`** | **healthy · 0.8s · 1587** | **stale/red · 1872s · 52 (frozen)** | **YES — the only difference** |
| summary | green 11 / red 1 | green 10 / red 2 | |

**mac-2's `5min` counter is frozen: `push_count = 52`, `last_push_ts = 17:20:02`, unchanged
across four polls spanning 12 minutes while `age_sec` climbed 1167 → 1344 → 1872.**

### The `5min` counter is lying — the channel is actually alive

Proven, not inferred:

1. **Router wiring is identical on both machines.** `/api/v9/status` → `bar_router`:
   `subscribers: {"tick_reversal_15": 3, "5min": 7, "day_type_classification": 1,
   "tick_reversal_12": 1, "woodies_5min": 2}` — **the same on mac-1 and mac-2.**
2. **A brand-new TREND_STEP candidate appeared on mac-2 at 14:50:02 UTC (17:50 IDT)** while
   `5min push_count` stayed at 52.
3. **TREND_STEP can only come from the `5min` channel.** It is produced solely by
   `_trend_step_on_bar` (`backend/main.py:909` → `bar_router.subscribe("5min", ...)`).
   S4's own pattern set is `ZLR, TLB, TT, GB100, Vegas, Ghost, FaMir, HTLB, HFE` —
   TREND_STEP is **not** an S4/woodies pattern.
4. S2's buffer grows on both at the same 1-bar-per-5-min cadence (mac-1 46→49, mac-2 68→71).

**⇒ S2, S1/day-type and TREND_STEP on mac-2 are being fed. They are NOT blind.**
Only `StreamHealthService.record_push("5min")` is not registering — and `_record_push`
swallows every exception silently (`backend/v9/api/v9/bars.py:221-227`,
`except Exception: pass`), so a failing record is invisible by design.

### Consequence: the readiness board lies red

`/api/v9/build/pattern-status → readiness`:

* mac-1: `{"verdict": "READY", "reason": "all checks passed"}`
* mac-2: `{"verdict": "BLOCKED", "reason": "dead: bars_5min"}`, check `bridge_streams_fresh`
  `passed=false`, `severity="block"`.

**This did NOT stop any fire.** `_compute_readiness` is explicitly documented
*"Read-only — does NOT gate firing"* (`backend/v9/systems/build_status/aggregator.py:246-249`).
It is a **display-only symptom that masked the real cause.**

---

## 3. Is mac-2 running commit `e37263b9`?

`e37263b9` is on `origin/stabilize/mems26-local-truth-2026-05-16` (authored **17:08:45 IDT**),
so it is pullable. mac-1 is at `e37263b9` (local == origin).

### What I can PROVE (by elimination): a failover-class publisher IS running on mac-2

Only three code paths publish to `5min`:

| publisher | file | active on mac-2? | evidence |
|---|---|---|---|
| raw Sierra `POST /api/v9/bars/5min` | `bars.py:748-764` | **NO** | it INSERTs into `v9_bars_5min` (line 748) *before* routing (line 764); that table is frozen at 13:55 |
| tick aggregator | `bar_aggregator_5min.py:205-219` | **NO** | gated by `AGGREGATOR_5MIN_PUBLISH_V1`, code default `"0"`, STANDING-OFF in `docs/FLAG_INDEX.md`; cc-mac2 reported flag_guard **173/173 PASS** at 13:15 |
| **woodies failover (`e37263b9`)** | `bars.py:1475-1490` | **only remaining candidate** | the channel demonstrably delivers (§2) |

**⇒ Since `5min` is provably delivering and the other two publishers are provably off,
mac-2 must be running the `e37263b9` failover.** Its routing half works; its
`_record_push("5min")` half does not (hence the frozen counter). Because `_fo_last` stays
pinned at 17:20:02, the failover condition `(now - _fo_last) > 120` is permanently true, so
it republishes on **every** woodies bar close — which matches the observed 1-candidate-per-bar
TREND_STEP cadence exactly.

### What I CANNOT prove, and the one contradiction

* I cannot read mac-2's `git rev-parse HEAD`, its `.env`, or its logs.
* **Contradicting datum:** extrapolating mac-2's push counters backwards
  (`woodies_5min` 1004→1041 over 108s ⇒ 0.34/s; 1041/0.34 ≈ 51 min) puts its backend start at
  **≈16:58–17:00 IDT — about 9 minutes BEFORE `e37263b9` was authored (17:08:45).**
  This is corroborated by `cold_start_guard` blocks at 16:58:33 / 17:00:05 / 17:00:13.
  Either the extrapolation is unreliable (push rates are not constant from boot), or mac-2
  restarted again later without resetting what I measured. **I flag this as unresolved.**

**One command on mac-2 settles it** — see §7 step 1.

---

## 4. Pattern readiness — side by side (`/api/v9/build/pattern-status`)

| system | mac-1 | mac-2 |
|---|---|---|
| S1 `day_type` | **fired** 1 — "Classification COMPLETE: Variation (p=0.62)" | **armed** 1 (not yet fired) |
| S2 `five_min` | 6 armed / **4 blocked** | 8 armed / **2 blocked** |
| S3 `footprint` | 0 armed / 4 blocked | 0 armed / 4 blocked |
| S4 `woodies` | **9 armed / 0 blocked** | **9 armed / 0 blocked** |
| `running` / `hydrated` | True / True (all) | True / True (all) |

### What each S2 block is on — **market conditions, not `data.*` internals**

**mac-1** (day_type gate = `Trend_Normal`):

| pattern | blockers | class |
|---|---|---|
| `INVERSE_HNS_LONG` | `day_type_gate.auth_table_cell`, `detection.swing_lows_found` | market |
| `HNS_TOP_SHORT` | `day_type_gate.auth_table_cell`, `detection.swing_highs_found` | market |
| `DOUBLE_BOTTOM_EE_LONG` | `day_type_gate.auth_table_cell`, `detection.eve_variant` | market |
| `DOUBLE_TOP_AA_SHORT` | `day_type_gate.auth_table_cell` | market |

**mac-2** (day_type gate = `Normal`):

| pattern | blockers | class |
|---|---|---|
| `INITIATIVE_LONG` | `day_type_gate.auth_table_cell`, `detection.b1_expansion` | market |
| `INITIATIVE_SHORT` | `day_type_gate.auth_table_cell`, `detection.b1_expansion` | market |

**Both machines: S2/S4 blocks are Auth-Table (day-type) + shape-detection — i.e. market
conditions. Zero `data.*` blockers on S2 or S4 on either machine.** The only `data.*`
blockers anywhere are S3/footprint (`data.buffer_size`, `data.bars_today`) — identical on
both and expected under the standing `S3_MUTE` decision.

**The two systems block on *different* patterns purely because their day-type differs**
(`Trend_Normal` vs `Normal`) — which traces straight back to the IB (§5).

S2 data components on mac-2 are healthy: `five_min_bar_recency` `present=true`
`lag=289.0s` (required ≤360s), `cci_14_history` `buffer=19` (required ≥14).

---

## 5. Day-type and the Initial Balance — the actual root cause

### `v9_day_type_state` (latest row each)

| field | mac-1 | mac-2 |
|---|---|---|
| ts | 2026-08-14 14:40:05 (UTC) | 2026-08-14 17:40:00+03 (= same instant) |
| stage | B2 | B2 |
| day_type | Variation | Variation |
| confidence | 0.5 | 0.17 |
| **opening_type** | **OPEN_DRIVE** | **OPEN_AUCTION_IN** |
| **direction** | **with_extension(DOWN)** | **with_extension(UP)** |
| rib | 1.6667 | 1.4364 |
| ib_width_class | EXTREME | EXTREME |
| lock_state | LOCKED_LOW_CONF | LOCKED_LOW_CONF |

Both are updating live (row written at the 17:40 bar close on both). **mac-2's day-type
machine is not stalled — it is being fed wrong inputs.** The prior rows show mac-2 flapping
`Normal → Trend_DD → Variation` at 17:30/17:35/17:40.

### `/api/v9/tpo/current` — the smoking gun

| field | mac-1 | mac-2 | same? |
|---|---|---|---|
| `source` / `version` | sierra_tpo_json / v9.4.5-wc-fix | sierra_tpo_json / v9.4.5-wc-fix | ✅ |
| `age_s` / `stale` | 1.33 / False | 1.24 / False | ✅ |
| `session_opened_ts` | 2026-08-14 09:30:00 | 2026-08-14 09:30:00 | ✅ |
| `session_high` | 7830.75 | 7830.75 | ✅ |
| `session_low` | 7810.50 | 7810.50 | ✅ |
| `poc` / `vah` / `val` | 7820.75 / 7830.00 / 7816.75 | 7820.75 / 7830.00 / 7816.75 | ✅ |
| `ib_source` / `ib_found` / `ib_locked` | sierra_live / True / True | sierra_live / True / True | ✅ |
| **`ib_high`** | **7830.75** | **7817.50** | ❌ |
| **`ib_low`** | **7813.75** | **7810.50** | ❌ |
| **`ib_mid`** | **7822.25** | **7814.00** | ❌ |
| **`ib_width`** | **17.0** | **7.0** | ❌ |

Everything the TPO export carries is identical **except the Initial Balance**. mac-1's
`ib_high == session_high == 7830.75` — the true 09:30–10:30 ET range. mac-2's IB
(7810.50–7817.50) is the range of roughly **17:30–17:50 IDT — i.e. a window an hour late**,
and its `ib_low` equals `session_low`. mac-2's Sierra locked its IB over the wrong 60 minutes.

### The causal chain, end to end

```
mac-2 Sierra exports wrong IB (7810.50–7817.50, width 7.0)
        │
        ├─► opening_type OPEN_AUCTION_IN (vs OPEN_DRIVE) and extension UP (vs DOWN)
        │       └─► day_type Normal / Trend_DD (vs Trend_Normal)
        │               └─► different Auth-Table cells + different daytype_playbook rows
        │                   ("FAMIR SKIP on Normal" vs "FAMIR SKIP on Trend_Normal")
        │
        └─► target zones snap T1 to ib_low = 7810.50
                └─► 17:35 TREND_STEP SHORT: T1_dist 0.50 vs stop_dist 5.25 → R:R 0.10
                        └─► rr_hard_floor "un-rescuable"  ✖  THE MISSED TRADE
                └─► 17:45 TREND_STEP SHORT: T1 = 7813.75 − 3.25 = 7810.50 (ib_low again)
                        └─► rr_entry_gate R:R 0.62 < 0.65  ✖
```

`T1 = ib_low = 7810.50` reproduces **exactly** on both mac-2 candidates. This is not a
coincidence — it is the mechanism.

---

## 6. Gateway decisions and trades

### `v9_trades` (today)

| | mac-1 | mac-2 |
|---|---|---|
| trades | **2** | **0** |
| #667 | shadow · S4 SHORT · entry 7811.25 · stop 7816.50 · T1 7807.75 · exit 7816.50 STOP_HIT · **−$78.75** | — |
| #668 | **live** · S4 SHORT · entry 7811.25 · stop 7816.50 · T1 7807.75 · exit 7816.00 STOP_FILL · **−$71.25** | — |

Both mac-1 trades were TREND_STEP on `day_type_at_entry = Trend_Normal`, and **both lost.**
mac-2 not taking this trade was, on the day's P&L, *lucky* — but for the wrong reason.

### `/api/v9/gateway/decisions` — 17 (mac-1) vs 12 (mac-2)

mac-1 `by_gate`: `rr_entry_gate 4 · awaiting_release 3 · lsma_flat 2 · cont_trend_filter 2 ·
direction_context 1 · entry_not_confirmed 1 · daytype_playbook 1 · pattern_stop_cooldown 1`
— **fired 1, shadow 1, blocked 15.**

mac-2 `by_gate`: `cold_start_guard 3 · cont_trend_filter 2 · awaiting_release 2 ·
entry_not_confirmed 2 · daytype_playbook 1 · rr_hard_floor 1 · rr_entry_gate 1`
— **fired 0, blocked 12.**

Aligned by timestamp (UTC):

| ts | mac-1 | mac-2 |
|---|---|---|
| 13:30:04 | GB100 SHORT → `awaiting_release` | *(none)* |
| 13:58:3x | ZLR SHORT → `awaiting_release` | ZLR SHORT → **`cold_start_guard`** (bars_processed_today=0<3) |
| 14:00:0x | ZLR SHORT → `awaiting_release` / `lsma_flat` | ZLR SHORT ×2 → **`cold_start_guard`** (0<3, then 1<3) |
| 14:10:04 | TREND_STEP LONG → `lsma_flat` | *(none)* |
| 14:15:0x | ZLR SHORT ×2 → `cont_trend_filter` | ZLR SHORT ×2 → `cont_trend_filter` **(identical)** |
| 14:25:0x | FAMIR LONG → `direction_context` (day-context DOWN) | FAMIR LONG → `awaiting_release` |
| 14:30:03 | *(none)* | FAMIR LONG → `daytype_playbook` (SKIP on **Normal**) |
| **14:35:0x** | **TREND_STEP SHORT 7811.25 → ROUTED (live #668)** | **TREND_STEP SHORT 7811.00 → `rr_hard_floor` R:R 0.10** |
| 14:40:0x | FAMIR → `daytype_playbook` (SKIP on **Trend_Normal**); TREND_STEP → `entry_not_confirmed` | FAMIR → `awaiting_release`; TREND_STEP → `entry_not_confirmed` |
| 14:45:02 | TREND_STEP SHORT → `pattern_stop_cooldown` (already stopped 17:37) | TREND_STEP SHORT → `rr_entry_gate` R:R 0.62 |
| 14:50:02 | *(n/a at sample time)* | TREND_STEP SHORT → `entry_not_confirmed` |

Note 14:45: mac-1 was blocked by `pattern_stop_cooldown` **only because it had already
traded**. Had it not, it would have met the same `rr_entry_gate`. The machines are running
the same logic — they are fed different levels.

---

## 7. Ranked root causes

### 🔴 RC-1 — mac-2's Sierra exports a wrong Initial Balance (**the blocker**)

*Evidence:* `/api/v9/tpo/current` — mac-2 `ib_high 7817.50 / ib_low 7810.50 / ib_width 7.0`
vs mac-1 `7830.75 / 7813.75 / 17.0`, while `poc/vah/val/session_high/session_low/
session_opened_ts/version/age_s` are **identical**. `ib_source=sierra_live`,
`ib_locked=true`, `ib_found=true` on both.
*Impact:* T1 snapped to `ib_low = 7810.50` on **both** mac-2 TREND_STEP candidates
(17:35 → R:R 0.10 `rr_hard_floor`; 17:45 → R:R 0.62 `rr_entry_gate`), and drove
`opening_type`/`day_type` to `OPEN_AUCTION_IN`/`Normal` instead of `OPEN_DRIVE`/`Trend_Normal`.
*This alone accounts for the 1-trade-vs-0-trades outcome.*
*Prior art:* flagged in `docs/handoff/LIVE_CHANNEL.md` — "IB לא הגיע מ-TPO (צ'ארטבוק מק-2)"
and "IB width/chartbook … בדיקה מחר". **It was not closed.**

### 🟠 RC-2 — `5min` stream-health counter frozen ⇒ readiness board falsely red

*Evidence:* `push_count` pinned at 52 / `last_push_ts` 17:20:02 across 12 minutes while a new
TREND_STEP candidate was produced at 17:50 through that very channel (§2).
`_record_push` swallows exceptions (`bars.py:221-227`).
*Impact:* **No fires lost** — `_compute_readiness` is documented read-only
(`aggregator.py:246-249`). But it turned the board `BLOCKED — dead: bars_5min`, which
**masked RC-1 for the whole session** and would send an operator chasing the bar feed.
*Corollary:* the `e37263b9` failover's re-publish works; its health-recording half does not.

### 🟡 RC-3 — mac-2 backend restarted mid-session (~16:58–17:00 IDT)

*Evidence:* `cold_start_guard` blocked 3 ZLR candidates at 16:58:33 / 17:00:05 / 17:00:13
(`bars_processed_today=0 → 1 < 3 — system not hydrated`); mac-1 had **zero** cold-start
blocks. Push-counter extrapolation independently puts mac-2's boot at ≈16:58–17:00 vs
mac-1's ≈16:27.
*Impact:* 3 candidates lost in the 16:58–17:00 window. Also the source of the §3 timing
contradiction.

### 🟢 RC-4 — `v9_bars_5min` (legacy) frozen at 13:55 on mac-2

*Evidence:* 6 rows 13:30→13:55 vs mac-1's 15 rows 16:30→17:40.
*Impact:* **None on trading.** S2/S4/TREND_STEP all read `v9_bars_5min_woodies`. It feeds the
`bars_5min` freshness label behind RC-2. Cosmetic/diagnostic only.

### ⚪ RC-5 — signal-log volume anomaly (unexplained, non-blocking)

*Evidence:* `v9_system_signals` today — mac-2 **381,574** rows vs mac-1 **17,998** (**21×**).
Both span 00:00→17:44. *Impact:* not implicated in today's no-fire; flagging for a separate
look (possible hot loop / duplicate writer).

### ✅ Ruled out

* Bar data — `v9_bars_5min_woodies` identical (201 rows, same min/max, all fields non-null).
* Router wiring — subscriber map identical (`5min`: 7, `woodies_5min`: 2).
* S2/S4 arming — 9/9 S4 armed on both; no `data.*` blockers on S2 or S4 on either machine.
* S3/footprint dead — identical on both, standing `S3_MUTE` decision.
* Flags — cc-mac2 reported flag_guard 173/173 PASS at 13:15; no flag drift observed in behaviour.

---

## 8. EXACT minimal command sequence to run **ON mac-2**

> Read-only diagnosis first. Per CLAUDE.md, snapshot before touching any out-of-git surface
> (`.env`, LaunchAgent, Sierra Inputs/DLL).

```bash
cd ~/mems26_web_git

# ── 1. Settle §3: which commit is running, and is the failover firing? ─────────
git rev-parse --short HEAD          # expect e37263b9 (or newer)
git log --oneline -1
grep -c "FAILOVER: republished" /tmp/backend.err.log   # >0 ⇒ failover live
grep "5min failover check errored" /tmp/backend.err.log | tail -5
#   ^ if this line appears, RC-2 is confirmed: _record_push("5min") is throwing

# ── 2. Only if HEAD is older than e37263b9 ───────────────────────────────────
scripts/mems26_snapshot.sh "mac2-nofire-2026-08-14"
git pull
launchctl kickstart -k gui/$UID/com.mems26.backend
python3 scripts/flag_guard.py              # expect 173/173 PASS
python3 scripts/mems26_arming_gate.py      # expect ✅ ALL SYSTEMS ARMED

# ── 3. THE ACTUAL BLOCKER (RC-1) — fix the Initial Balance in Sierra ─────────
curl -s localhost:8000/api/v9/tpo/current \
  | python3 -c "import json,sys;d=json.load(sys.stdin);print({k:d[k] for k in ('ib_high','ib_low','ib_width','ib_locked','session_high','session_low','session_opened_ts')})"
#   mac-2 now : ib_high 7817.50 · ib_low 7810.50 · ib_width  7.0   ← WRONG
#   mac-1 now : ib_high 7830.75 · ib_low 7813.75 · ib_width 17.0   ← CORRECT
#
# In Sierra on mac-2, on the MES chart that feeds ~/SierraChart_Data/v9_export/ :
#   a) Chart → Chart Settings → Session Times — RTH must be 09:30–16:00 US/Eastern,
#      "Use session times" ON. Compare field-by-field against the same chart on mac-1.
#   b) Analysis → Studies → MES_AI_DataExport — check the IB / session inputs
#      (Input 4 "V9 Export Directory" = /Users/michael/SierraChart_Data/v9_export/).
#   c) Chart → Reload  (recomputes the profile from historical bars).
#
# verify — must match mac-1:
curl -s localhost:8000/api/v9/tpo/current | grep -Eo '"ib_(high|low|width)":[0-9.]*'
#   PASS = ib_high 7830.75 · ib_low 7813.75 · ib_width 17.0

# ── 4. Confirm the fix propagated through the decision chain ────────────────
curl -s "localhost:8000/api/v9/gateway/decisions?limit=20" \
  | python3 -c "import json,sys;[print(x['ts'][11:19],x.get('pattern'),x.get('blocked_by'),str(x.get('reason'))[:70]) for x in json.load(sys.stdin)['decisions']]"
#   PASS = T1_dist no longer snaps to 7810.50

curl -s localhost:8000/api/v9/build/pattern-status \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['readiness'])"
#   day_type should now read Trend_Normal (matching mac-1), opening_type OPEN_DRIVE
```

**Caveat (be honest about it):** `ib_locked = true` already. A mid-session study reload may
re-lock the IB from *current* bars rather than re-derive 09:30–10:30 ET. If step 3(c) does not
restore `ib_width = 17.0`, **today's IB is not recoverable** and the fix lands for tomorrow's
session — in which case verify at 10:31 ET tomorrow that mac-2's `ib_width` matches mac-1's
before arming.

**Do NOT** "fix" RC-2 by re-enabling `AGGREGATOR_5MIN_PUBLISH_V1` — that flag is STANDING-OFF
(`docs/FLAG_INDEX.md`; F2 of the 12.08 work order) and re-enabling it re-introduces the
double-publisher that poisoned S2's D-RVX.

---

## 9. Verification quotes (Pre-LIVE Rule 5)

```
$ curl -s http://10.1.118.70:8000/api/v9/tpo/current
  ib_high 7817.5 · ib_low 7810.5 · ib_mid 7814.0 · ib_width 7.0 · ib_locked True
  poc 7820.75 · vah 7830.0 · val 7816.75 · session_high 7830.75 · session_low 7810.5
$ curl -s http://localhost:8000/api/v9/tpo/current
  ib_high 7830.75 · ib_low 7813.75 · ib_mid 7822.25 · ib_width 17.0 · ib_locked True
  poc 7820.75 · vah 7830.0 · val 7816.75 · session_high 7830.75 · session_low 7810.5

$ psql mac-2: SELECT count(*),min(ts),max(ts) FROM v9_bars_5min_woodies WHERE ts>='2026-08-14';
  201 | 2026-08-14 01:00:00+03 | 2026-08-14 17:40:00+03      (identical to mac-1)
$ psql mac-2: SELECT count(*),max(ts) FROM v9_bars_5min WHERE ts>='2026-08-14';
  6 | 2026-08-14 13:55:00+03                                  (mac-1: 15 | 17:40:00+03)

$ curl -s http://10.1.118.70:8000/api/v9/health/streams   # 17:51:13 IDT
  woodies_5min push=1041 age=1s last=17:51:13
  5min         push=52   age=1872s last=17:20:02           (frozen; mac-1 push=1587 age=0.8s)

$ curl -s http://10.1.118.70:8000/api/v9/status | .bar_router
  {"received":9254,"dispatched":6249,"subscribers":{"tick_reversal_15":3,"5min":7,
   "day_type_classification":1,"tick_reversal_12":1,"woodies_5min":2}}   (mac-1: same map)

$ curl -s "http://10.1.118.70:8000/api/v9/gateway/decisions?limit=10"   # 17:51 IDT
  14:50:02 TREND_STEP entry_not_confirmed     ← NEW candidate while 5min push stayed 52
  14:45:02 TREND_STEP rr_entry_gate  "T1_dist=3.25 < stop_dist=5.25 × min=0.65 (R:R=0.62)"
  14:35:02 TREND_STEP rr_hard_floor  "R:R 0.10 < hard floor 0.30 (T1_dist=0.50 stop_dist=5.25)"
  today: {'fired': 0, 'blocked': 12}

$ psql mac-1: SELECT id,mode,entry_price,stop,t1,pnl_usd FROM v9_trades WHERE entry_ts>='2026-08-14';
  667 | shadow | 7811.25 | 7816.5 | 7807.75 | -78.75
  668 | live   | 7811.25 | 7816.5 | 7807.75 | -71.25
  mac-2: (0 rows)
```

---

**Nothing on mac-2 was modified. This report is the only artifact written.**
חתום: cowork-dev · 2026-08-14 17:55 IDT
