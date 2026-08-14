# FORENSIC — mac-2 ⇄ mac-1 decision parity, candidate by candidate (2026-08-14)

**Investigator:** cowork-dev · **Position:** on mac-1, read-only against mac-2 over ZeroTier
**Window sampled:** 19:23–19:45 IDT · **Nothing was changed on either machine.**
**Supersedes/extends:** `docs/reports/FORENSIC_MAC2_NOFIRE_2026-08-14.md` (17:55 snapshot, pre-IB-fix)

Sources — mac-1: `~/SierraChart_Data/v9_export/gateway_decisions.jsonl` + `postgresql://localhost/mems26`
+ `http://localhost:8000`. mac-2: `http://10.1.118.70:8000/api/v9/gateway/decisions?limit=200`
(file-backed buffer, survives restarts) + `postgresql://michael@10.1.118.70/mems26`.

All timestamps below are **UTC** (= IDT − 3h = ET + 4h). RTH open 13:30 UTC.

---

## 0. Executive verdict

mac-1 produced **34** gateway decisions today (2 routed live at the gateway, 8 shadow_only,
24 blocked → 14 rows in `v9_trades`, 4 of them `mode=live`). mac-2 produced **25** decisions,
**0 fired, 0 shadow**.

**The R:R blockade that killed mac-2's morning is GONE.** After the `IB_BARS_VALIDATE_V1`
correction went live on mac-2 (its backend reseeded at **15:21:40 UTC**), mac-2 recorded
**zero** `rr_hard_floor` and **zero** `rr_entry_gate` blocks. From 15:50 UTC onward the two
machines agree gate-for-gate on every shared candidate.

**Three root inputs still differ, in descending order of impact:**

| # | Differing input | mac-1 | mac-2 | Consequence |
|---|---|---|---|---|
| **RC-A** | `opening_type` (frozen at 10:00 ET, never revised) | `OPEN_DRIVE` | `OPEN_AUCTION_IN` | different `day_type` all day → different `daytype_playbook` rows, Auth-Table cells and structural-target branch → **different T1** on the same bar |
| **RC-B** | `5min` channel cadence | continuous (**3842** pushes) | **105** pushes = 1 per closed bar | mac-1's gateway prices a **forming** bar, mac-2 a **closed** bar → entry differs 0.25–0.75 pt → different `entry_not_confirmed` verdicts and different candidate sets |
| **RC-C** | trade state feedback | had live positions | flat all day | mac-1's `pattern_stop_cooldown` / shadow-mode outcomes exist only because it traded |

**RC-A is the inversion Michael needs to know about: on `opening_type`, mac-2 is CORRECT and
mac-1 is the anomaly.** Proven below by executing the production classifiers on the shared
bar tape. Making mac-2 "a parallel of mac-1" on this input would mean copying a defect.

---

## 1. Paired decision table — every mac-1 candidate against mac-2's at the same bar

Matched on (bar minute, pattern, direction). `✓` = same gate. `✗` = divergence.

| UTC | pattern / dir | mac-1 entry → outcome (blocked_by) | mac-2 entry → outcome (blocked_by) | |
|---|---|---|---|---|
| 06:42:14 ×5 | ZLR SHORT | 7601.25 / 7599.00 → 4× `rr_entry_gate`, 1× shadow | *(no decision — backend down)* | ✗ |
| 13:30:04 | GB100 SHORT | 7825.25 → `awaiting_release` | *(none)* | ✗ |
| 13:58:33/36 | ZLR SHORT | 7823.75 → `awaiting_release` | 7823.50 → **`cold_start_guard`** (bars_today=0<3) | ✗ |
| 14:00:03/05 | ZLR SHORT | 7825.00 → `awaiting_release` | 7824.75 → **`cold_start_guard`** (0<3) | ✗ |
| 14:00:10/13 | ZLR SHORT | 7825.00 → `lsma_flat` | 7825.00 → **`cold_start_guard`** (1<3) | ✗ |
| 14:10:04 | TREND_STEP LONG | 7827.75 → `lsma_flat` | *(none)* | ✗ |
| 14:15:03–08 | ZLR SHORT ×2 | 7825.75 / 7825.25 → `cont_trend_filter` | 7825.75 / 7825.50 → `cont_trend_filter` | ✓ |
| 14:25:01/03 | FAMIR LONG | 7818.00 → `direction_context` | 7817.75 → `awaiting_release` | ✗ |
| 14:30:03 | FAMIR LONG | *(none)* | 7816.25 → `daytype_playbook` (SKIP on **Normal**) | ✗ |
| **14:35:02/04** | **TREND_STEP SHORT** | **7811.25 → ROUTED — live #668** (stop 7816.50, t1 7807.75, R:R 0.667) | **7811.00 → `rr_hard_floor`** R:R 0.10 (T1_dist 0.50, stop_dist 5.25) | **✗✗** |
| 14:40:00/05 | TREND_STEP SHORT | 7817.00 → `entry_not_confirmed` (c 7817.00) | 7816.75 → `entry_not_confirmed` (c 7816.75) | ✓* |
| 14:40:04/05 | FAMIR LONG | 7815.50 → `daytype_playbook` (SKIP on **Trend_Normal**) | 7815.75 → `awaiting_release` | ✗ |
| 14:45:02 | TREND_STEP SHORT | 7813.75 → `pattern_stop_cooldown` | 7813.75 → `rr_entry_gate` R:R 0.62 | ✗ |
| 14:50:02 | TREND_STEP SHORT | *(none)* | 7814.75 → `entry_not_confirmed` | ✗ |
| **14:55:02/07** | **ZLR SHORT** | **7812.50 → ROUTED — live #670** (t1 7807.50) | **7812.25 → `rr_entry_gate`** R:R 0.35 (T1_dist 1.75) · **7812.50 → `rr_entry_gate`** R:R 0.40 (T1_dist 2.00) | **✗✗** |
| 15:00:03 / 15:05:00 | S2 BEAR_FLAG SHORT | 7809.75 → `entry_not_confirmed` (c 7810.50) | 7809.75 → `entry_not_confirmed` (c 7811.75) | ✓* |
| 15:08:21/25 | ZLR SHORT | 7809.75 → shadow #671 (t1 7807.00) | 7809.75 → `rr_hard_floor` R:R 0.10 (T1_dist 0.50 → **T1 = 7809.25**) | ✗ |
| 15:10:02–05 | ZLR SHORT | 7809.00 → shadow #672 (t1 7806.00) | 7809.25 → `rr_hard_floor` 0.24 · 7809.00 → `rr_hard_floor` 0.19 (**T1 = 7808.00**) | ✗ |
| 15:15:03 | TREND_STEP SHORT | 7807.25 → `entry_not_confirmed` | *(none)* | ✗ |
| 15:20:01/06 | TREND_STEP SHORT | 7808.75 → `entry_not_confirmed` | 7808.25 → `rr_entry_gate` R:R 0.30 | ✗ |
| 15:25:03 | TREND_STEP SHORT | 7802.25 → shadow #674 | *(none)* | ✗ |
| 15:30:03 | TREND_STEP SHORT | 7805.00 → shadow #675 | *(none)* | ✗ |
| 15:35:03/06 | TREND_STEP SHORT | 7804.00 → shadow #676 | 7804.75 → `entry_not_confirmed` | ✗ |
| 15:40:02 ×2 | ZLR + TREND_STEP SHORT | 7803.25 → shadow #677 / #678 | *(none)* | ✗ |
| 15:50:01–06 | ZLR SHORT ×2 | 7800.75 / 7801.00 → `structural_targets_wrong_side` | 7801.00 / 7800.75 → `structural_targets_wrong_side` | ✓ |
| 16:09:10/11 | ZLR SHORT | 7804.50 → `lsma_flat` | 7804.75 → `direction_context` | ✗ |
| 16:10:02 | ZLR SHORT | 7804.50 → `direction_context` | *(none)* | ✗ |
| 16:10:19 | ZLR SHORT | 7804.00 → `direction_context` (LSMA UP + CVD +0) | 7804.00 → `direction_context` (identical reason string) | ✓ |
| 16:15:02/04 | GB100 LONG | 7807.50 → `awaiting_release` (close 7807.50 vs 7808.00) | 7807.75 → `awaiting_release` (close 7807.75 vs 7808.00) | ✓ |

`✓*` = same gate, different numeric snapshot (RC-B).

**Gate totals** — mac-1 `rr_entry_gate 4 · awaiting_release 4 · entry_not_confirmed 4 ·
lsma_flat 3 · direction_context 3 · cont_trend_filter 2 · structural_targets_wrong_side 2 ·
daytype_playbook 1 · pattern_stop_cooldown 1`.
mac-2 `rr_hard_floor 4 · rr_entry_gate 4 · entry_not_confirmed 4 · cold_start_guard 3 ·
awaiting_release 3 · cont_trend_filter 2 · structural_targets_wrong_side 2 ·
direction_context 2 · daytype_playbook 1`.

**mac-1 has zero `rr_hard_floor`; mac-2 has four — all before 15:21 UTC. That is the entire
trade-loss signature, and it is closed.**

---

## 2. Per-divergence root input, proven from both machines

### 2.1 — 14:35 and 14:55 (the two trades mac-1 took): **T1 = mac-2's wrong `ib_low`**

| | mac-1 | mac-2 |
|---|---|---|
| 14:35 entry / stop / stop_dist | 7811.25 / 7816.50 / **5.25** | 7811.00 / — / **5.25** (identical) |
| 14:35 **T1 / T1_dist** | **7807.75 / 3.50** | **7810.50 / 0.50** |
| 14:55 **T1 / T1_dist** | **7807.50 / 5.00** | **7810.50 / 2.00** |

`stop_dist` is identical to the tick. **T1 is the only variable, and mac-2's T1 equals its
`ib_low = 7810.50` on both candidates.** Read at 17:50 IDT from both endpoints:

```
mac-2 /api/v9/tpo/current : ib_high 7817.50  ib_low 7810.50  ib_width  7.0  ib_source sierra_live
mac-1 /api/v9/tpo/current : ib_high 7830.75  ib_low 7813.75  ib_width 17.0  ib_source sierra_live
```
`poc / vah / val / session_high / session_low / session_opened_ts / version` were identical —
only the IB differed. Mechanism: `backend/v9/systems/target_structure_clamp.py:52-98`
(`clamp_targets_to_ib` → `edge = ib_low` for SHORT, `setup["t1"] = float(edge)` at line 97),
wired at `backend/v9/gateway/trading_gateway.py:2472-2490`. `rr_hard_floor` is emitted at
`trading_gateway.py:2636`, `rr_entry_gate` at `:2670` / `:2693`.

**Status: CLOSED by `aa49bcdf`.** Verified live at 19:25 IDT — see §3(b).

### 2.2 — 15:08 and 15:10: **T1 = mac-2's VAL, because its `day_type` was `Trend_DD` not `Variation`**

mac-2's T1 was **7809.25** (15:08) and **7808.00** (15:10). Those are not `ib_low`. Read from
mac-1's own `v9_trades.cross_context` for the twin shadow trades at the same second:

```
trade 671 (15:08:25) tpo_system: poc 7813.75  vah 7823.75  val 7809.25   ufl 7809.25
trade 672 (15:10:02) tpo_system: poc 7813.75  vah 7823.50  val 7808.00   ufl 7808.00
```

**mac-2's T1 is the Value-Area Low / Unfinished-Low to the tick on both bars.** mac-1's T1 on
the same bars was 7807.00 and 7806.00 — i.e. it selected a rung *beyond* VAL.
The branch selector is the day-type: `backend/v9/systems/structural_targets.py`
(`_resolve_normal` :184-191 vs `_resolve_variation` :216-239). From `v9_day_type_state`:

| 15:08–15:10 UTC | mac-1 | mac-2 |
|---|---|---|
| day_type | **Variation** (`day_type_at_entry=Variation` on #671/#672) | **Trend_DD** (set 15:00 UTC, flipped to Variation at 15:10) |

**Single differing input: `day_type` → different structural-target branch → different T1.**

### 2.3 — 14:25 / 14:30 / 14:40 FAMIR, and every `daytype_playbook` row: **`opening_type`**

mac-1 blocked FAMIR with `FAMIR SKIP on **Trend_Normal**`; mac-2 with `FAMIR SKIP on
**Normal**`. Same pattern, same bar, different playbook row — because the day-type differs,
which traces to `opening_type`, which is frozen for the whole session.

#### PROOF — the shared bar tape classifies as `OPEN_AUCTION_IN`, i.e. mac-2 is right

The classifier is bar-count-triggered on the **first 3 RTH bars** and frozen thereafter
(`backend/v9/systems/day_type/state_machine.py:565-592`; `self.opening` is assigned only
there and in `reset()`). Inputs are OHLC + prior-day H/L only — **no IB**
(`backend/v9/systems/day_type/detector.py:162-234`).

Executed against the real bars (identical on both machines) on mac-1:

```
$ python3 /tmp/prove_opening.py            # production detect_opening_type()
bars 16:30..16:40 IDT (09:30-09:40 ET) -> OPEN_AUCTION_IN dir=NEUTRAL conf=0.40  ratio=0.171
bars 16:35..16:45                      -> OPEN_AUCTION_IN                        ratio=0.243
bars 16:40..16:50                      -> OPEN_AUCTION_IN                        ratio=0.515
bars 16:45..16:55                      -> OPEN_AUCTION_IN                        ratio=0.061
bars 16:50..17:00                      -> OPEN_AUCTION_IN                        ratio=0.658
bars 16:55..17:05                      -> OPEN_REJECTION_REVERSE
bars 17:00..17:10                      -> OPEN_AUCTION_IN
bars 17:05..17:15                      -> OPEN_AUCTION_IN
bars 17:10..17:20                      -> OPEN_DRIVE  DOWN conf=0.95   <-- first OPEN_DRIVE
bars 17:15..17:25                      -> OPEN_AUCTION_IN
bars 17:20..17:30                      -> OPEN_DRIVE  DOWN conf=0.95

$ python3 /tmp/prove_cvd.py                # same window, S1_CVD_OPENING off AND on
S1_CVD_OPENING = False -> OPEN_AUCTION_IN NEUTRAL 0.40
S1_CVD_OPENING = True  -> OPEN_AUCTION_IN NEUTRAL 0.40   (cvd_is_live=False, shadow=UNKNOWN)

$ python3 /tmp/prove_v2.py                 # the v2 canonical detector
opening_detector_v2.detect_opening_type(bars[:3]) = OPEN_AUCTION_IN 0.4
opening_detector_v2.detect_opening_type(bars[:6]) = OPEN_AUCTION_IN 0.4

$ python3 /tmp/prove_shift.py              # every 3-bar window 16:00..16:45 incl. pre-RTH
16:00..16:10 OPEN_TEST_DRIVE · 16:05..16:15 OPEN_REJECTION_REVERSE · 16:10..16:20 OPEN_AUCTION_IN
16:15..16:25 OPEN_AUCTION_IN · 16:20..16:30 OPEN_REJECTION_REVERSE · 16:25..16:35 OPEN_AUCTION_IN
16:30..16:40 OPEN_AUCTION_IN · 16:35..16:45 OPEN_AUCTION_IN        (no OPEN_DRIVE anywhere)
```

**Three independent production detectors, both flag states, and every 3-bar window in the
opening 45 minutes — all return `OPEN_AUCTION_IN`. `OPEN_DRIVE` is not reachable from the
tape before 17:10 IDT.**

Yet mac-1 persisted `OPEN_DRIVE` at **14:00:02 UTC (17:00:02 IDT)**, forty minutes before the
first window that could produce it. The state rows show how:

```
MAC1 v9_day_type_state          MAC2 v9_day_type_state
13:28:26 stage=A2 open=NA       (no session row yet)
13:40:04 stage=A3 open=NA       13:45:01 stage=A3 open=OPEN_AUCTION_IN   <- on time, 09:45 ET
14:00:02 stage=A3 open=OPEN_DRIVE  14:00:05 stage=A3 open=OPEN_AUCTION_IN

MAC1 v9_day_type_history id=66 date=2026-08-14 opening_type=OPEN_DRIVE
     ib_high=7830.75 ib_low=7813.75 ib_width=17.0 created_at=17:00:02.146859+03
MAC2 v9_day_type_history id=10 date=2026-08-14 opening_type=OPEN_AUCTION_IN
     ib_high=7830.75 ib_low=7813.75 ib_width=17.0 created_at=17:00:05.589633+03
```

Both history rows carry the **same IB** — so the opening-type split is **not** IB-caused.
mac-1 was already at stage **A3 at 09:40 ET with only two closed RTH bars and
`opening_type=NA`**; `_stage_a2` cannot advance to A3 below three bars, so mac-1's machine
left A2 through a non-A2 path and its `opening` was filled later from a non-bar source
(the `day_type_seed` / `DAYTYPE_BOOT_SEED_CANONICAL_V1` hydrate path,
`backend/v9/api/v9/day_type_seed.py:148,156` — `if machine.opening is None`).

**Honest limit:** I cannot read mac-1's in-process `opening_bars` list, and neither
`/tmp/backend.log` nor `/tmp/backend.err.log` carries an opening-type line, so the exact
non-bar source on mac-1 is inferred, not read. Everything else above is measured.
The command that settles it is in §5 step 6.

**Downstream day-type divergence, now (19:25 IDT):**

| field | mac-1 | mac-2 |
|---|---|---|
| opening_type | OPEN_DRIVE | OPEN_AUCTION_IN |
| direction | with_extension(**DOWN**) | with_extension |
| day_type / confidence | Variation / 0.00 | Variation / 0.00 |
| rib | **2.619** | **1.8088** |
| lock_state | **LOCKED_LOW_CONF** | **PENDING** |
| hydration.day_type.reached_state | LOCKED_LOW_CONF | PENDING |

`rib = (session_high − session_low) / ib_width` (`relative_features.py:228`). mac-2's
`1.8088 = 30.75 / 17.0` — i.e. mac-2 is using the **corrected** IB. mac-1's `2.619` implies
`30.75 / 11.74`; mac-1's own internally-accumulated IB has drifted from the 17.0 its TPO
reports. **On `rib` too, mac-2 is the machine using the correct number.**

`lock_state=PENDING` on mac-2 is a restart artefact: `day_type_seed.py:112-117` reloads only
`opening_type, day_type, confidence` and never restores `lock_state`, so every mid-session
restart drops it to PENDING until stage C1 runs again.

### 2.4 — every 0.25–0.75 pt entry difference and the `entry_not_confirmed` splits: **`5min` cadence**

```
$ /api/v9/health/streams          (19:25 IDT)
                     MAC1 status/age/push        MAC2 status/age/push
5min                 healthy / 1.5s / 3842       stale / 110.0s / 105     <<< DIFF
woodies_5min         healthy / 0.7s / 3840       healthy / 2.6s / 1627
live_price           healthy / 0.3s / 11235      healthy / 0.1s / 4819
(all other 10 streams: same status on both; footprint no_data on both — standing S3_MUTE)
```

mac-1 receives **3842** `5min` pushes (sub-second, the raw Sierra `5min.json` export);
mac-2 receives **105** — one per closed 5-minute bar, delivered by the `e37263b9` woodies
failover because mac-2's Sierra does not export `5min.json` at all.

Consequence, measured on the paired table: mac-1's gateway prices a **forming** bar and
mac-2 a **closed** one. Every paired row shows it — 14:35 `7811.25` vs `7811.00`,
14:25 `7818.00` vs `7817.75`, 15:20 `7808.75` vs `7808.25`, 15:35 `7804.00` vs `7804.75`,
16:15 `7807.50` vs `7807.75`. It also explains the `entry_not_confirmed` reason strings
carrying different closes for the same bar (15:00/15:05: `c=7810.50` vs `c=7811.75`), and the
four bars where mac-1 emitted a candidate and mac-2 emitted none (15:15, 15:25, 15:30, 15:40)
plus the two where mac-2 emitted and mac-1 did not (14:30, 14:50).

This is the same class as commit `c3c37742` ("live-port reads a FORMING bar"). **It cannot be
closed by configuration on mac-2 — it needs mac-2's Sierra to export `5min.json`, or the
forming-bar read to be made deterministic on both.** It is a *jitter* source, not a blocker:
no gate on mac-2 was decided by it today except the timing of `entry_not_confirmed`.

### 2.5 — 13:58–14:00 `cold_start_guard` ×3: **mac-2 restarted mid-session**

`bars_processed_today=0 → 1 < 3 — system not hydrated`, at 13:58:33 / 14:00:05 / 14:00:13.
mac-1 had zero. Three candidates lost. mac-2 restarted **again** at 15:21:40 UTC to take the
IB fix (visible as the malformed reseed row below). Not relevant to a clean session.

### 2.6 — A real bug found in passing: enum repr leaking into the DB

mac-2's `v9_day_type_state` at 18:21:40 IDT:

```
2026-08-14 18:21:40 | B2 | Variation | conf=0.48 | opening_type='OpeningType.OPEN_AUCTION_IN' | dir=None | rib=None | PENDING
```

The literal string `OpeningType.OPEN_AUCTION_IN` was persisted. Source:
`backend/main.py:845-850` — the `DAYTYPE_BOOT_SEED_CANONICAL_V1` reseed path calls
`str(...opening_type)` where the live path at `main.py:260-263` correctly uses `.value`.
`OpeningType` is a `str, Enum` (not `StrEnum`), so `str()` yields the repr
(`backend/v9/systems/day_type/schemas.py:31`). Any consumer matching on the label sees an
unknown value for that row. **Not implicated in today's no-fire; log as a fix-forward.**

---

## 3. PASS / FAIL — the four fixes on mac-2

### (a) Is mac-2's S2 blocked on any `data.*` internals right now? — **PASS**

```
$ /api/v9/build/pattern-status
MAC1  total patterns=24  armed=19  with data.* blockers=4
      S3 Absorption / Stacked Imbalance / Sweep Return / Exhaustion -> ['data.buffer_size','data.bars_today']
      S4 Zero Line Reject -> status=fired
MAC2  total patterns=24  armed=20  with data.* blockers=4
      S3 Absorption / Stacked Imbalance / Sweep Return / Exhaustion -> ['data.buffer_size','data.bars_today']
```

**Zero `data.*` blockers on S1/S2/S4 on either machine.** The only four are S3/footprint,
identical on both, expected under the standing `S3_MUTE` decision. mac-2 has **20** armed vs
mac-1's 19 (mac-1's ZLR is in `fired` state, not `armed`).
`readiness` on both: `{"verdict":"READY","reason":"all checks passed"}` — the false-red
`BLOCKED — dead: bars_5min` board from the 17:55 report has cleared.

### (b) Does mac-2's `/api/v9/tpo/current` show `ib_source=bars_derived_correction` with 7830.75 / 7813.75? — **PASS**

```
field                  MAC1                         MAC2                         same?
ib_high                7830.75                      7830.75                      OK
ib_low                 7813.75                      7813.75                      OK
ib_mid                 7822.25                      7822.25                      OK
ib_width               17.0                         17.0                         OK
ib_source              sierra_live                  bars_derived_correction      *** DIFF ***
ib_found / ib_locked   True / True                  True / True                  OK
session_high/low       7830.75 / 7800.0             7830.75 / 7800.0             OK
poc / vah / val        7813.75 / 7820.5 / 7800.0    7813.75 / 7820.5 / 7800.0    OK
source / version       sierra_tpo_json / v9.4.5-wc-fix  (identical)              OK
```

The `ib_source` difference is the **intended** signal: the correction is *active* on mac-2 and
*dormant* on mac-1, exactly as `aa49bcdf` designed. Because it is active, **mac-2's raw Sierra
IB is still wrong** — the code is compensating, not curing. It only engages after **10:30 ET**
with **≥12** RTH bars in `v9_bars_5min_woodies` and a mismatch **> 0.25**
(`backend/v9/api/v9/tpo_routes.py:328-375`), so between 09:30 and 10:30 ET tomorrow mac-2 will
again serve its Sierra's raw IB. The correction does reach every consumer, not just the
endpoint — it lives inside `_normalize_sierra_tpo`, which `_load_sierra_tpo` calls
(`tpo_routes.py:486`), feeding the day-type machine (`backend/main.py:249-253`), the TPO
system, S2, the trade manager and the gateway clamp.

⚠ **Caveat with teeth:** the day-type machine accumulates its IB with `max`/`min`
(`state_machine.py:605-608`), so a corrected value arriving after a wrong one has been
absorbed cannot shrink it, and `ib_class` freezes once stage A4 runs. The flag must be ON
**before** A4 locks (i.e. at boot) to be clean.

### (c) Is mac-2's `v9_bars_5min_woodies` identical to mac-1's for today? — **PASS**

```
count / min ts / max ts   MAC1: 222 | 2026-08-14 01:00:00+03 | 2026-08-14 19:25:00+03
                          MAC2: 222 | 2026-08-14 01:00:00+03 | 2026-08-14 19:25:00+03

row-by-row diff over (open,high,low,close,volume,cci_14,lsma_value,trend_state):
  DIFFERING FIELD-CELLS: 2      by field: {'volume': 2}
  2026-08-14 11:05:00+03  volume  mac1=1011  mac2=1013
  2026-08-14 19:25:00+03  volume  mac1=1925  mac2=2073     (bar still forming)
```

**OHLC, CCI-14, LSMA and trend_state are identical on all 222 bars.** The only two
differences are volume: a 2-tick discrepancy on an 11:05 Globex bar and the currently-forming
19:25 bar.

*Method note (matters):* an `md5(string_agg(close::text ...))` checksum **does** differ between
the two machines (`4149a349…` vs `2dda1ba8…`). That is a numeric-scale text artefact, not a
value difference — the row-by-row typed comparison above is authoritative. Do not use a
text-md5 as the parity test for this table.

`v9_bars_5min` (legacy) still diverges — mac-1 36 rows to 19:25, mac-2 25 rows frozen at
17:20 — and is still **not load-bearing** (S2/S4/TREND_STEP all read the woodies table).

### (d) Do the four new DB objects exist on mac-2? — **PASS**

```
pg_tables ∩ {v9_exit_decisions, v9_s7_shadow_log, v9_tsf_shadow_log}
   MAC1: v9_exit_decisions, v9_s7_shadow_log, v9_tsf_shadow_log
   MAC2: v9_exit_decisions, v9_s7_shadow_log, v9_tsf_shadow_log
information_schema.columns v9_trades.pnl_sierra
   MAC1: pnl_sierra | double precision      MAC2: pnl_sierra | double precision
```

All four present on both. Populated on mac-1 only (`v9_exit_decisions` 5244 rows vs 0) —
expected, mac-2 has taken no trades.

---

## 4. Remaining RUNTIME differences that would still make mac-2 decide differently tomorrow

| axis | mac-1 | mac-2 | verdict |
|---|---|---|---|
| `MEMS26_MODE` (`/api/v9/status.mode`) | `live` | `live` | same |
| `.env` var count | 245 lines / **231 applied** (`[env_loader] applied 231 vars`) | **not readable remotely** | ⚠ unverified |
| ruled flags | `config/RULED_FLAGS.yaml` = **176** entries; HEAD `aa49bcdf` claims flag_guard **174** | last signed report = **173/173** at 13:15 IDT (`LIVE_CHANNEL.md`) | ⚠ must be re-run |
| git HEAD | `aa49bcdf` (2026-08-14 18:17:44 +0300) | inferred ≥ `aa49bcdf` (IB correction is live) | ⚠ unverified directly |
| backend restarts today | continuous since ~13:2x UTC | **≥2** — ~13:5x UTC and **15:21:40 UTC** | ⚠ |
| `bar_router.received` | 37,134 | 13,640 | consistent with the later boot |
| `bar_router.subscribers` | `{tick_reversal_15:3, 5min:7, day_type_classification:1, tick_reversal_12:1, woodies_5min:2}` | **identical map** | same |
| `hydration.bars_in_db` | 2135 | 2356 | benign |
| `hydration.day_type.reached_state` | `LOCKED_LOW_CONF` | **`PENDING`** | ✗ restart artefact (§2.3) |
| `5min` stream | healthy 1.5s / 3842 | **stale 110s / 105** | ✗ RC-B |
| `v9_system_signals` today | 19,401 | **438,671 (22.6×)** | ✗ unexplained hot writer |
| trades today | 14 rows (4 `mode=live`: #668 −71.25, #670 +45.00, #673 +11.25, #680 0.00 MAE_SCRATCH) | **0** | — |
| `is_sim` | column does not exist in `v9_trades` on either machine — parity by absence | same | n/a |
| contracts | not exposed by any read-only endpoint on either machine | same | ⚠ verify locally |

**`v9_system_signals` at 22.6× mac-1's volume is the one unexplained item that got worse**
(it was 21× at 17:55). It is not implicated in any block today, but a hot writer on the
trading machine is a stability risk before LIVE.

---

## 5. Exact ordered commands to run **ON mac-2** to close what remains

> Read-only through step 4. Per CLAUDE.md, snapshot before touching any out-of-git surface.
> Do **not** re-enable `AGGREGATOR_5MIN_PUBLISH_V1` (STANDING-OFF).

```bash
cd ~/mems26_web_git

# ── 1. Confirm the code identity (settles the one thing I could not read) ────
git rev-parse --short HEAD
#    EXPECT: aa49bcdf   (or newer). Anything older ⇒ the IB fix is not from this tree.

grep -c "^[A-Za-z_][A-Za-z0-9_]*=" .env
#    EXPECT: 245        (mac-1's count). A LOWER number ⇒ the known `sed -i ''` .env
#            corruption ate lines — diff against mac-1 before trusting any flag.

python3 scripts/flag_guard.py | tail -3
#    EXPECT: 174/174 PASS   (173 + IB_BARS_VALIDATE_V1 from aa49bcdf)

grep -a "env_loader" /tmp/backend.err.log | tail -1
#    EXPECT: [env_loader] applied 231 vars from .../.env | ... DAYTYPE_PLAYBOOK=1
#            The number must be 231. Fewer ⇒ .env drift.

grep -aE "IB_BARS_VALIDATE_V1|S1_CVD_OPENING|S1_NEW_CLASSIFIER|DAYTYPE_BOOT_SEED_CANONICAL_V1|TARGET_STRUCTURE_CLAMP_V1|S1_IB_SANITY_V1" .env
#    EXPECT (must match mac-1 exactly):
#      S1_CVD_OPENING=true · S1_IB_SANITY_V1=1 · TARGET_STRUCTURE_CLAMP_V1=1
#      DAYTYPE_BOOT_SEED_CANONICAL_V1=1 · IB_BARS_VALIDATE_V1=1

# ── 2. Confirm the IB correction is live (should already pass) ───────────────
curl -s localhost:8000/api/v9/tpo/current \
 | python3 -c "import json,sys;d=json.load(sys.stdin);print({k:d[k] for k in ('ib_high','ib_low','ib_width','ib_source')})"
#    EXPECT: {'ib_high': 7830.75, 'ib_low': 7813.75, 'ib_width': 17.0,
#             'ib_source': 'bars_derived_correction'}
#    'bars_derived_correction' = the correction is DOING WORK ⇒ Sierra is still wrong (step 5).

# ── 3. Confirm no S2 candidate is blocked on internals ───────────────────────
curl -s localhost:8000/api/v9/build/pattern-status \
 | python3 -c "
import json,sys
d=json.load(sys.stdin)
bad=[(s['name'],p['pattern'],p['blockers']) for s in d['systems'] for p in s.get('patterns',[])
     if any(str(b).startswith('data.') for b in (p.get('blockers') or [])) and 'Footprint' not in s['name']]
print('readiness:',d['readiness']['verdict']); print('non-S3 data.* blockers:',bad)"
#    EXPECT: readiness: READY   /   non-S3 data.* blockers: []

# ── 4. Confirm the R:R blockade is gone ─────────────────────────────────────
curl -s "localhost:8000/api/v9/gateway/decisions?limit=200" \
 | python3 -c "import json,sys;print(json.load(sys.stdin)['today'])"
#    EXPECT: 'rr_hard_floor' absent, or a count that has NOT increased since 15:21 UTC.
#    Any NEW rr_hard_floor after a restart ⇒ the IB correction is not reaching the gateway.

# ── 5. THE REAL REMAINING BLOCKER — mac-2's Sierra still exports a wrong IB ──
#    In Sierra on mac-2, on the MES chart that writes ~/SierraChart_Data/v9_export/ :
#      a) Chart → Chart Settings → Session Times: RTH 09:30–16:00 US/Eastern,
#         "Use session times" ON. Compare field-by-field with the same chart on mac-1.
#      b) Analysis → Studies → MES_AI_DataExport: Input 4 "V9 Export Directory"
#         = /Users/michael/SierraChart_Data/v9_export/ ; check the IB/session inputs.
#      c) Chart → Reload.
#    Tomorrow at 10:31 ET, BEFORE arming, verify the raw value is right on its own:
curl -s localhost:8000/api/v9/tpo/current | grep -Eo '"ib_(high|low|width|source)":[^,]*'
#    PASS = ib_source "sierra_live"  (not bars_derived_correction) with 09:30–10:30 ET values
#           matching mac-1. bars_derived_correction is a safety net, not a fix.

# ── 6. Settle RC-A — which machine has the right opening_type (run on BOTH) ──
python3 - <<'PY'
import os,sys; sys.path.insert(0,os.path.expanduser("~/mems26_web_git"))
from backend.v9.systems.day_type.api import get_state   # or: read app.state.day_type_machine
PY
#    Simpler, no code: compare the persisted labels after tomorrow's 09:45 ET —
psql postgresql://localhost/mems26 -Atc \
 "SELECT ts,stage,opening_type,lock_state FROM v9_day_type_state
   WHERE ts::date=CURRENT_DATE ORDER BY ts LIMIT 5;"
#    EXPECT on a healthy machine: a row at ~09:45 ET with a REAL opening_type
#    (not 'NA', not 'OpeningType.X'). If mac-1 again shows stage=A3 + opening_type='NA'
#    at 09:40 ET, mac-1 is the machine to fix — NOT mac-2.

# ── 7. mac-2's 5min channel — cadence, not a fix (informational) ─────────────
curl -s localhost:8000/api/v9/health/streams \
 | python3 -c "import json,sys;d=json.load(sys.stdin);s=d.get('streams',d);print({k:(v.get('status'),v.get('push_count')) for k,v in s.items() if k in ('5min','woodies_5min')})"
#    EXPECT: 5min push_count ≈ 1 per closed 5-min bar (mac-1 gets ~1 per second).
#    This is the woodies failover doing its job because mac-2's Sierra exports no 5min.json.
#    Do NOT "fix" it with AGGREGATOR_5MIN_PUBLISH_V1 — that flag is STANDING-OFF.

# ── 8. The 22.6× signal-log writer (stability, before LIVE) ──────────────────
psql postgresql://localhost/mems26 -Atc \
 "SELECT system, count(*) FROM v9_system_signals WHERE ts>=CURRENT_DATE
   GROUP BY 1 ORDER BY 2 DESC LIMIT 5;"
#    mac-1 total today = 19,401 · mac-2 = 438,671. Find which system dominates on mac-2.
```

---

## 6. Verification quotes (Pre-LIVE Rule 5)

```
$ python3 /tmp/dump_dec.py "http://10.1.118.70:8000/api/v9/gateway/decisions?limit=200" MAC2
### MAC2  n=25  today={"fired": 0, "blocked": 25, "shadow_only": 0, "by_gate": {"cold_start_guard": 3,
    "cont_trend_filter": 2, "awaiting_release": 3, "daytype_playbook": 1, "rr_hard_floor": 4,
    "entry_not_confirmed": 4, "rr_entry_gate": 4, "structural_targets_wrong_side": 2, "direction_context": 2}}
14:35:02 | S4 | TREND_STEP | SHORT | entry=7811.0  | blocked | rr_hard_floor | R:R 0.10 < hard floor 0.30 (T1_dist=0.50 stop_dist=5.25) — un-rescuable
14:55:02 | S4 | ZLR        | SHORT | entry=7812.25 | blocked | rr_entry_gate | T1_dist=1.75 < stop_dist=5.00 × min=0.65 (R:R=0.35)
15:08:21 | S4 | ZLR        | SHORT | entry=7809.75 | blocked | rr_hard_floor | R:R 0.10 < hard floor 0.30 (T1_dist=0.50 stop_dist=5.00) — un-rescuable
16:15:04 | S4 | GB100      | LONG  | entry=7807.75 | blocked | awaiting_release | ... (close 7807.75 vs 7808.0)

$ curl -s localhost:8000/api/v9/gateway/decisions?limit=3 | .today
{"fired":2,"blocked":24,"shadow_only":8,"by_gate":{"rr_entry_gate":4,"awaiting_release":4,"lsma_flat":3,
 "cont_trend_filter":2,"direction_context":3,"entry_not_confirmed":4,"daytype_playbook":1,
 "pattern_stop_cooldown":1,"structural_targets_wrong_side":2}}      # note: NO rr_hard_floor on mac-1

$ python3 /tmp/diff_bars.py
mac1 rows 222 mac2 rows 222
DIFFERING FIELD-CELLS: 2   by field: {'volume': 2}
  2026-08-14 11:05:00+03  volume  mac1=1011  mac2=1013
  2026-08-14 19:25:00+03  volume  mac1=1925  mac2=2073

$ python3 /tmp/cmp_api.py      # /api/v9/tpo/current, 19:25 IDT
ib_high 7830.75 / 7830.75  ·  ib_low 7813.75 / 7813.75  ·  ib_width 17.0 / 17.0
ib_source  sierra_live (mac-1)  /  bars_derived_correction (mac-2)

$ python3 /tmp/ps2.py
MAC1 total patterns=24 armed=19 with data.* blockers=4  (all four = S3 · Footprint)
MAC2 total patterns=24 armed=20 with data.* blockers=4  (all four = S3 · Footprint)

$ python3 /tmp/final_checks.py    # /api/v9/health/streams
5min   MAC1 ('healthy', 1.5, 3842)   MAC2 ('stale', 110.0, 105)     <<< DIFF
(11 other streams: same status both machines)

$ python3 /tmp/trades.py
[MAC1] trades today = 14   (live: #668 -71.25 · #670 +45.00 · #673 +11.25 · #680 0.00 MAE_SCRATCH)
       v9_system_signals today: 19401   ·  v9_exit_decisions rows: 5244
[MAC2] trades today = 0
       v9_system_signals today: 438671  ·  v9_exit_decisions rows: 0

$ python3 /tmp/dt_hist_table.py
MAC1 v9_day_type_history id=66 date=2026-08-14 opening_type=OPEN_DRIVE
     ib_high=7830.75 ib_low=7813.75 ib_width=17.0 created_at=2026-08-14 17:00:02.146859+03
MAC2 v9_day_type_history id=10 date=2026-08-14 opening_type=OPEN_AUCTION_IN
     ib_high=7830.75 ib_low=7813.75 ib_width=17.0 created_at=2026-08-14 17:00:05.589633+03
```

---

## 7. What I could NOT read (stated, not glossed)

1. mac-2's `git rev-parse HEAD`, `.env`, `/tmp/backend.err.log`, `scripts/flag_guard.py`
   output — no remote shell by design. Steps 1 of §5 close all four.
2. mac-2's in-process `day_type_machine.opening_bars` — and mac-1's. The exact non-bar source
   of mac-1's `OPEN_DRIVE` is therefore inferred from the state/history rows, not read.
3. `contracts` / `is_sim` — not exposed by any read-only endpoint on either machine
   (`v9_trades` has no `is_sim` column on either), and mac-2 has no trades to infer from.
4. mac-2's `v9_trades.cross_context` for the 15:08/15:10 candidates — the table is empty, so
   the VAL identification in §2.2 is anchored on mac-1's twin shadow trades at the same second
   plus mac-2's own `T1_dist` arithmetic. Both agree to the tick.

---

**Nothing on either machine was modified. This report is the only artifact written.**
חתום: cowork-dev · 2026-08-14 19:45 IDT
