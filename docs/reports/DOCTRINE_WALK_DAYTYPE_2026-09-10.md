# Doctrine walk — THE DAY TYPE (S1) · 2026-09-10

**Authority:** `docs/spec_authority/DALTON_DOCTRINE.md` §1.4, §1.5, §1.8, §2, §3.1, §6.
**Method:** READ-ONLY. Code read at `git HEAD c3a5323a`. Every number below is a query result or a
log line pasted from this session; nothing is asserted from memory (Pre-LIVE Rule 5).
**Measurement harness:** `classify_session()` re-run bar-by-bar on `v9_bars_5min_woodies`
(RTH 09:30–16:00 ET), IB always recomputed from the **first 12 RTH bars** — never a stored IB.
Live `.env` flags, `DELTA_FEATURES_V1=0` (see gap G-7: the live delta file leaks into replays).
Scripts: `/tmp/dtwalk/measure.py`, `/tmp/dtwalk/evt.py`.

---

## 0 · Answer to Michael's framing

> *"מערכת 1 גם צריכה לזהות את סוג היום לאורך כל יום המסחר — איפה המחיר מתחיל, איפה נמצאת הבטן, כל הנתונים שיש לך"*

**Confirmed in part.** The classifier *does* re-run every bar and the label *can* move both ways —
that half works. Three things do not:

1. **It does not run at all for the first hour.** `backend/main.py:406` gates the entire canonical
   classifier behind `day_type_machine.ib_locked`, and `backend/main.py:483` behind
   `len(_cls_rth_bars) >= 12`. So `S1_COMMITTED_PROVISIONAL_V1=1` — the 30-minute committed
   provisional built for exactly this — **never executes on the live path**. What fills the first
   hour is the *legacy* engine. Measured live 09-09: the published label was `Trend_Normal` from
   17:02 to 17:36 IL, then `[S1-NEW-CLS] promoted: Trend_Normal → Normal` at 17:30:06 IL.
   Two engines, opposite labels, in the hour the gates are open.
2. **The belly is not the belly.** The classifier's value area is a volume-at-typical-price proxy
   computed from 5-min bars (`value_migration.py:41-60`), not Sierra's TPO value area. POC/VAH/VAL
   from Sierra reach the *location gate*, not the classifier's own value-migration feature.
3. **The label the gates act on is 10 minutes behind the label S1 published** (§2 below, measured).

---

## 1 · Doctrine rule → code → status

| # | Doctrine rule (quote ≤12 words · line) | Code (file:line) | Status | Evidence |
|---|---|---|---|---|
| 1.3 | "IB = the first two half-hour periods… the *base* of the day" (L49) | `daytype_trading_plan.yaml:50` `ib_lock_minutes: 60`; `daytype_classifier.py:228` | **ALIGNED** | 12 bars = 60 min, per Dalton's "slightly longer in the S&P" |
| 1.4 | "any move beyond the IB; means the OTF entered" (L58) | `relative_features.py:157-173` → `sides`; `DAYTYPE_SIDES_MECHANICAL_V1=1` | **ALIGNED** | side = price extension ≥ max(2pt, 20%×IB); acceptance reserved for reclass |
| 1.4 | RE *count/persistence* not scored (L63) | `ext_up_bars`/`ext_dn_bars` → `_confidence` only, `daytype_classifier.py:129` | **PARTIAL** | feeds confidence, never the type |
| 1.5 | "Value area = ~70% of the day's business, one σ around POC" (L66-67) | `value_migration.py:41-60` `developing_value()` | **CONTRADICTS** | VA built from **volume at (H+L+C)/3 buckets on 5-min bars**, not TPO letters. Dalton's VA is TPO-based (`docs/…DOCTRINE.md:67` "TPO VA method p.333"). Sierra's real POC/VAH/VAL never enter the classifier's value feature |
| 1.5 | developing VA per bar; prior-day VA as frame (L68) | `classifier_core.py:218-226`; live `main.py:446-451` prior VA | **ALIGNED** | developing VA recomputed each bar; prior VA loaded once at lock |
| 1.7 | acceptance at VA/gap/balance refs, not only IB (L89-91) | `classifier_core.py:142-173` `_refs` = PDH/PDL/prior_VA/IB | **ALIGNED** (P0-1 v2 shipped) | `S1_ACCEPTANCE_RECLASS_V1=1`. Measured ref mix over 77 live trades: PDH 22 · PDL 20 · prior_VA 12 · IB 8 · none 15 |
| **1.8** | "Logic creates the impetus… structure provides the confirmation" (L96) | `daytype_classifier.py:328-331` FORMING until 12 bars, **and** `main.py:406` `ib_locked` gate | **CONTRADICTS** | the canonical classifier is silent for 60 min on the live path — see §0.1 |
| 1.8 | "waiting for full structural proof… is doctrinally wrong" (L97-99) | `daytype_classifier.py:436` `rib>=2.5` + close-at-extreme | **PARTIAL — mitigated** | three waivers now exist and are ON: OPEN_DRIVE `:445-454`, control-path (3 stair-steps, rib≥1.8) `:462-501`, elongation `:509-522` |
| 2·Normal | "More the exception than the rule" (L112) | `daytype_classifier.py:535-543` rib≤1.30 + normal vol + IB-not-narrow; catch-all `:546` | **CONTRADICTS** | still a catch-all "Normal-leaning". **Measured: `Normal` was the label at IB lock in 19/20 sessions and the final label in 0/20** |
| 2·NV | "extends one side substantially, ~doubling the IB" (L113) | `daytype_classifier.py:526-527` catch-all for sides==1 | **PARTIAL** | book band 1.30–2.00 (`yaml:40`) but the code has **no upper bound** — NV absorbs everything from rib 1.30 to 2.50. **Measured: NV is the final label in 14/20 sessions (70%)** |
| 2·Trend | "one-timeframe: each period ≥/≤ prior" (L114) | `relative_features.py` `one_tf`; `daytype_classifier.py:436` | **PARTIAL** | one_tf is full-session; one violated early period kills it forever — the control path at `:476-482` deliberately drops the requirement |
| 2·Trend | "profile thin, elongated, ≤4–5 TPO wide" (L114) | — | **MISSING** | P1-5 elongation/P-b-D still unbuilt; `S1_TREND_ELONGATION_V1=1` uses **rib≥2.5** as a range proxy, not TPO width |
| 2·DD | narrow IB + single-print neck + new value held (L115) | `dd_features.py:37-105`; `daytype_classifier.py:422-433` | **ALIGNED** | + neck-refill invalidation now live (`S1_DD_INVALIDATION_V1=1`, `:428-430`) — doctrine contradiction-5 CLOSED |
| 2·Nontrend | "narrow initial range… no RE ever comes" (L116) | `daytype_classifier.py:367` sides==0 + vol≤0.5 + rib≤1.15 | **PARTIAL** | code rib ceiling 1.15 vs doctrine 1.5 (L116). `vol_ratio=None` → unreachable. **0/20 sessions classified Nontrend** |
| 2·Neutral-C/E | "RE on both sides"; close mid vs extreme (L117-118) | `daytype_classifier.py:373-403` + hysteresis `:388-397` | **ALIGNED** | 4/20 sessions ended Neutral |
| 2·Nonconviction | "no OTF signature at all… stay out" (L119) | `daytype_classifier.py:341-357`, `S1_NONCONVICTION_V1=1` | **ALIGNED** (built since doctrine written) | fired once in 20 sessions (08-28 @ lock) — doctrine contradiction-8 CLOSED |
| 3.1 | "The market's open often foreshadows the day's outcome" (L126) | `_provisional_from_open` `daytype_classifier.py:67-95` | **CONTRADICTS — dead code live** | the function exists and the flag is ON, but `main.py:406` never calls `classify_session` before IB lock. Doctrine contradiction-1 is **still open**, contrary to §7 L264 which marks P0-2 ✅ |
| 6·#3 | canonical confidence (L252) | `_confidence` `:98-149`, `S1_CONFIDENCE_V2=1` + smoothing `:176-205` | **ALIGNED** | one value across engine/replay/UI |

---

## 2 · Continuous reclassification, staging, antiflap — and T-286

**Does it re-run every bar, both ways?** Yes, after IB lock. `main.py:1092` subscribes
`_day_type_on_bar` to the 5-min bar router; `classify_session` is a first-match-wins ladder with no
never-downgrade rule. Measured: **73 label changes over 20 sessions = 3.65/session**, in both
directions.

**Staging gates vs Michael's ruling (`opening@15 / day_type@30 / IB-lock@60`):**

| Stage | Ruled | Code | Reality |
|---|---|---|---|
| opening@15min | opening_type committed | `opening_detector_v2.detect_opening_type` on first 6 bars, `classifier_core.py:104` | runs, but **only inside `classify_session`** → not before IB lock |
| day_type@30min | committed provisional | `daytype_classifier.py:331-336` (`forming_lock_minutes: 30`, `yaml:51`) | **never reached live** — `main.py:406` |
| IB-lock@60min | confirm | `daytype_classifier.py:228,330` | works |

**Antiflap / hysteresis — there are THREE stacked layers:**

1. `_antiflap_day_type` — `backend/v9/services/trade_context.py:490-517`, called at `:622-625`.
   `DAYTYPE_ANTIFLAP_V1=1`, **`DAYTYPE_ANTIFLAP_HOLD_S=600`** → a change must persist **10 minutes
   (2 bars)** before it reaches any gate.
2. Gateway Trend-hysteresis — `trading_gateway.py:1069-1093`. Trend→other needs 2 confirmations;
   other→Trend is immediate (doctrinally right, p.25). ⚠ the counter increments **per gateway
   evaluation, not per bar** (`:1082`) — on 09-09 two evaluations landed 5 s apart (18:05:01,
   18:05:06), so "2 bars" can elapse in seconds.
3. Neutral sub-type hysteresis — `daytype_classifier.py:388-397`, `NEUTRAL_HYSTERESIS_PTS=0.05`.

**T-286 — VERIFIED, and worse than stated.** From `/tmp/backend.err.log` (clock = IL):

```
2026-09-09 18:10:09 [INFO] [...day_type.consumer] DayTypeConsumer upserted: date=2026-09-09 type=Variation prob=0.50
2026-09-09 18:15:02 [INFO] [...trading_gateway] BLOCKED by dalton_intent: ... (phase=C cond=day_type == Normal bias=BOTH)
2026-09-09 18:20:07 [INFO] [...trading_gateway] BLOCKED by dalton_intent: ... (phase=C cond=day_type == Normal bias=BOTH)
```
and `[S1-NEW-CLS] promoted: Normal → Variation` at 18:10:09. DB corroborates
(`v9_day_type_state`, created_at is naive-UTC): `15:05:06 Normal` → `15:10:09 Variation`.

Distinct gate labels used all day 09-09:
```
   4 2026-09-09 17 Normal
   7 2026-09-09 18 Normal
```
**The gateway used `Normal` in 11/11 evaluations on 09-09 and never once used `Variation`** — S1's
label from 18:10 onward. Lag measured at the last evaluation: 9 min 58 s, i.e. exactly the
`DAYTYPE_ANTIFLAP_HOLD_S=600` window (promotion would have landed at 18:20:09; the last setup was
evaluated at 18:20:07, two seconds early).

**Cost of the lag (arithmetic bound, labelled as such):** 73 changes × up to 600 s = up to 730 min
of stale label over 20 sessions ≈ **up to 37 min per 390-min session (9.4%)**. The antiflap is not
gratuitous — **44% of all label changes (32/73) are pure `Normal ↔ Normal_Variation` oscillation**
— but it pays for that noise in lag rather than removing it.

---

## 3 · §1.8 "structure lags" — independent verification, and the design question

**The morning claim (4 Trend sessions / 10 trades / +$639 / 90% win / Trend at entry 2 of 10) does
not reproduce with this method.** Over the 40-session window `2026-07-13 … 2026-09-09`, recomputing
the final label from bars, only **3 sessions end as Trend** (08-05 Trend_DD, 08-17 Trend_DD, 09-03
Trend_Normal) carrying **7 live trades, net +$206.25, 4/6 priced wins (67%)**. The classifier called
Trend **at the entry bar in 4 of 7 (57%)**, not 2 of 10:

```
2026-08-05  final=Trend_DD    #627 17:40 label=Normal_Variation  pnl=171.25  no
                              #633 18:25 label=Trend_DD          pnl= 75.00  YES
2026-08-17  final=Trend_DD    #693 16:55 label=Normal_Variation  pnl= 40.00  no
                              #699 20:50 label=Trend_Normal      pnl= 63.75  YES
                              #708 22:32 label=Trend_DD          pnl=  0.00  YES
2026-09-03  final=Trend_Normal #981 17:20 label=Trend_Normal     pnl= None   YES
                              #987 20:20 label=Normal_Variation  pnl=-143.75 no
```
The divergence is almost certainly the "final label" source: `v9_day_type_history` (the *published*
row) lists 7 Trend days since 07-01, my bars-recompute lists 3 — the same publish-vs-classify split
that `DAYTYPE_RECLASS_STABILITY_V1`'s ruling note documents. **Do not carry the 2-of-10 / +$639
number forward without re-deriving it; state which source defined "ended as Trend".**

### Should entry rules key on the label, or on the observable event?

Measured over the **last 20 sessions, 77 live trades (71 priced, net −$426.25, 45% win)**:

| Basis at the entry bar | n | priced | net | win |
|---|---|---|---|---|
| an `accepted_break` exists (any direction) | 62 | 56 | −$601.25 | 45% |
| no `accepted_break` | 15 | 15 | **+$175.00** | 47% |
| **trade direction == break direction** | 43 | 38 | −$286.25 | **47%** |
| **trade direction AGAINST the break** | 19 | 18 | **−$315.00** | **39%** |
| label was `Trend*` | 6 | 4 | +$6.25 | 50% |
| label was `Normal_Variation` | 57 | 54 | −$635.00 | 46% |
| label was `Normal` | 9 | 8 | +$38.75 | 38% |
| label at entry **==** final EOD label | 49 | 45 | −$185.00 | 47% |
| label at entry **!=** final EOD label | 28 | 26 | −$241.25 | 42% |

**The evidence both ways, honestly:**

- *For the event:* the sharpest separation in the whole table is directional and event-based —
  **with the break 47% / −$286 vs against the break 39% / −$315 over just 19 trades.** That
  reproduces T-295 ("counter-extension is the whole loss") on an independent recompute. The event
  is also available **immediately** (the bar it happens), where the label is 10 minutes late (§2).
- *For the label:* label-correctness is worth something but far less — 47% vs 42%, a 5-point
  spread — and `Normal_Variation` covers **57 of 77 trades (74%)**, so the label is carrying almost
  no information at entry time. A basis that is the same value three quarters of the time cannot
  be a discriminator.
- *Against pure event-keying:* an accepted break alone is **not** an edge — 45% win, −$601 across
  62 trades. The break has to be *directional and with the trade*. And the `NO accepted_break`
  bucket is the only positive one (+$175), which is a small-n (15) result, not a rule.

**Conclusion:** entry rules should key on **the observable event with a direction** (accepted break
beyond a reference, and which side), and use the day-type label only as a *management* frame
(runner / target / stop shape), never as the entry discriminator. Two pieces of this already exist
and are wired: `VARIATION_SUBTYPE_V1` (`trading_gateway.py:1591-1611`) splits Variation into
directional-vs-rotational **using `accepted_break` itself** — but it is `=0` in `.env`; and
`dalton_intent` already keys on `entry_kind` (`BREAK` / `EDGE_FADE` / `VALUE_RETURN`) with the
day-type only choosing the allowed set.

---

## 4 · Value / the belly — and the `v9_tpo_history` TZ question

**Live path (per 5-min bar, `tpo_system.py`):**
- POC/VAH/VAL ← Sierra `tpo.json` `_update_va_from_sierra` (`tpo_system.py:518-562`). These are the
  **developing** session values (Sierra Study ID:3), overwritten every bar; only used when
  `vah>val` and spread ≥1.0 pt, otherwise the bar-derived value stands (`:544-552`).
- IB ← Sierra `tpo.json` `_update_ib` (`tpo_system.py:482-516`), only when `ib_found` is true.
- **The classifier does NOT consume those.** `classify_session` gets `prior_vah/prior_val` from the
  *settled prior* session (`main.py:446-451`, `v9_tpo_sessions`), and computes today's value itself
  from bars (`classifier_core.py:222-226` → `value_migration.developing_value`). `poc_now` comes
  from `tpo_system.current_state["poc"]` (`main.py:489-492`) but `poc_drift` is **consumed by no
  branch of `classify()`** (grep: `poc_drift` appears 0 times in `daytype_classifier.py`).
- Cadence: developing value updates **every 5-min bar**; the classifier's own prior-day context is
  loaded **once, at IB lock** (`main.py:412`, `_cls_ctx_cache`) and never refreshed.

**The `ts`-runs-3-hours-early finding — confirmed, and LIVE IS NOT AFFECTED:**

```
2026-08-20  n= 13  (created_at-ts) avg=180.5min   2026-08-31  n= 13  avg=0.7min
2026-08-21  n= 13  avg=188.0min                   2026-09-01  n= 13  avg=0.1min
…                                                 …
2026-08-28  n= 13  avg=181.6min                   2026-09-09  n= 13  avg=2.5min
```
Exactly the boundary the morning study reported: ~180 min skew through 2026-08-28, ~0 from
2026-08-31. `backend/v9/replay/kernel.py:123` already tags the source
`v9_tpo_history.created_at_as_observed_availability`.

**LIVE consumers that read `ts`:** exactly one — `backend/v9/systems/location_gate.py:276-295`,
the *previous-session VA* fallback, filtered to `ts::time BETWEEN 09:30 AND 16:00 ET` on the prior
date. With a 3-hour-early `ts` that window selected the wrong rows (a true 09:30 ET observation was
stamped 06:30 ET and fell **out** of the filter). Two reasons this is not a live risk today:
(a) the skew is gone since 08-31 — measured above; (b) it is a **fallback**, reached only when
Sierra's `tpo.json` `previous_session` is unreadable (`location_gate.py:262-273`), and that block
is live right now (`previous_session: {found: True, poc: 7695.0, vah: 7711.0, val: 7679.0}`).
The other `ts` reader, `daytype_classify_routes.py:187`, is the replay endpoint only.

**Plain answer: historical replays over sessions ≤ 2026-08-28 are affected and their TPO-derived
numbers should be re-derived on `created_at`; live trading today is not affected.**

---

## 5 · The IB — build, lock, and the mid-IB restart

- **Build/lock:** Sierra Study ID:6 is the source (`tpo_system.py:482-516`); `ib_locked` mirrors
  Sierra's own flag, set once the Study finishes 09:30–10:30 ET. `_update_ib` overwrites
  `ib_high/ib_low` from Sierra on **every** bar where `ib_found` is true — the lock does not
  short-circuit it (`:493-495`).
- **`S1_IB_SANITY_V1=1`** at the classifier layer: `classifier_core.py:64-93`, two detectors
  (bars poke >2 ticks beyond the claimed IB; claimed IB >2 pt wider than the bars). Requires
  `n >= 12`.

**Commit `1bb6879b` — does it do what its message claims? YES, with one uncovered hole.**
`tpo_system.py:114-194` now runs the *same two detectors* against
`_first12_rth_extremes()` (`:84-112`) inside `hydrate()`, logs `[TPO] IB SANITY:` and tags
`current_state["ib_source"] = "bars_fallback_stored_inconsistent"`. That matches the message.

**But a mid-IB restart still produces yesterday's IB.** `_first12_rth_extremes()` returns `None`
when fewer than 12 RTH bars exist (`tpo_system.py:102-103`) — correct per Rule 1, but it means the
sanity check is **inert for the entire 09:30–10:30 ET window**, which is exactly when the incident
happened. Recovery then depends on Sierra pushing `ib_found`. Log of the 09-09 incident:
```
2026-09-09 16:54:52 [TPO] Hydrated IB from DB: H=7717.75 L=7680.00 locked=True W=37.75   ← yesterday's
2026-09-09 16:58:29 [TPO] IB LOCKED (from Sierra): H=7663.75 L=7652.00 W=11.75 class=NARROW
```
(the corrupt window was 3 min 37 s, shorter than the commit's own "16:54:52 → ~17:35" estimate).

**🔴 Live exposure for TODAY, verified in the DB minutes ago:**
```
id=2336 trading_date=2026-09-10 session_type=GLOBEX ib_high=7663.75 ib_low=7644.25 ib_locked=1
                                                    ib_locked_ts=2026-09-10T04:00:02Z
id=2333 trading_date=2026-09-09 session_type=CASH   ib_high=7663.75 ib_low=7644.25 ib_locked=1
```
Today's row **already carries yesterday's cash IB with `ib_locked=1`**, and
`hydrate()`'s query — `SELECT * FROM v9_tpo_sessions WHERE trading_date=:today ORDER BY id DESC
LIMIT 1` (`tpo_system.py:120-123`) — has **no `session_type` filter**, so it will pick that GLOBEX
row. Today's live `tpo.json` currently reports `ib_found=None` and
`previous_session.ib_found=False, ib_high=0.0`. Consequence: **a backend restart between 16:30 and
~17:30 IL today hydrates 7644.25/7663.75 as "today's locked IB"** and the new fix cannot catch it.
Affected consumers: `BEYOND_IB_EDGE` stops, `rib`, the StopResolver "35% of IB" floor.

---

## 6 · Who consumes `day_type` — snapshot vs live

| Consumer | file:line | Reads | Note |
|---|---|---|---|
| `dalton_intent` gate (the one that blocked 11/11 on 09-09) | `trading_gateway.py:1067-1093` | **LIVE** `get_live_day_type()` | + its own Trend hysteresis, `:1069-1093` |
| day-type **playbook** verdict | `trading_gateway.py:1591, 1612-1614` | **SNAPSHOT** `day_type_at_entry` | |
| `VARIATION_SUBTYPE_V1` | `trading_gateway.py:1591-1611` | SNAPSHOT + live `accepted_break` | flag `=0` |
| location gate | `trading_gateway.py:1842` | **SNAPSHOT** | |
| dalton playbook (2nd site) | `trading_gateway.py:1878` | **SNAPSHOT** | |
| §5a NO_LABEL → shadow-only | `trading_gateway.py:1174-1178` | **LIVE** | IB locked + `day_type=None` → shadow |
| R:R fallback | `trading_gateway.py:742` | **LIVE** | |
| entry-budget / edge gates | `trading_gateway.py:2406, 2582, 2805` | **LIVE** | |
| StopResolver | `trading_gateway.py:3050-3090` | **LIVE** (`:3050`) **and SNAPSHOT** (`:3084`) — *both, in the same block* | |
| structural targets | `trading_gateway.py:3573-3597` | **LIVE** | |
| trail config | `trading_gateway.py:3669` | **SNAPSHOT** | |
| **targets table** | `targets_table.py:176-210` `get_targets/resolve_trail_config` | caller-supplied — mixed | |
| **C4 target (ruling 6)** | `sierra_command.py:949-977` | **SNAPSHOT** | Variation→stop-only, Normal/Neutral→opposite edge, Trend→T3 |
| **RUNNER_BY_DAYTYPE_V1** | `sierra_command.py:985-1010` | **LIVE** | `=1`; runner only on `Trend*` |
| S2 detection/auth/sizing (4 sites) | `five_min_system.py:946, 977, 1059, 2840` | **LIVE** | |
| S4 Woodies | `woodies_system.py:665-677` | **LIVE** | |
| trade row stamp | `trade_context.py:694-745` → `manager.py:583` | writes `day_type_at_entry` from `get_live_day_type()` | i.e. the **10-min-lagged** value |
| postmortem / trail engine | `postmortem/analyzer.py:75,137`; `trail_engine.py:545` | SNAPSHOT | |

**`day_type_at_entry` quality, measured over 77 live trades (last 20 sessions):**
`NULL` on **28** · differs from the recomputed canonical label at that bar on **13** of the 49
non-null → **41/77 = 53% of live trades carry a null or wrong day-type stamp.**
(Corroborates the ruled note in `config/RULED_FLAGS.yaml:329`: "42 of 72 live stamps (58%) differ
from the canonical label at that moment".) Sample mismatches:
`08-14 17:35 #668 stored=Trend_Normal / recomputed=Normal_Variation` ·
`09-01 17:20 #942 stored=Trend_Normal / recomputed=Normal_Variation` ·
`09-03 17:20 #981 stored=Normal / recomputed=Trend_Normal`.

---

## 7 · The measurement — 20 sessions

IB = first 12 RTH bars, recomputed. `@lock` = bar 12. Times are IL.

```
date          ibW  @lock            @19:00            @21:00            FINAL             chg  tr  bad
2026-08-12   30.5  Normal           Normal_Variation  Normal_Variation  Normal_Variation    2   1   0
2026-08-13  51.75  Normal           Normal_Variation  Normal_Variation  Normal_Variation    3   4   1
2026-08-14   17.0  Normal           Normal_Variation  Normal_Variation  Normal_Variation    4   5   0
2026-08-17  20.25  Normal           Normal            Normal_Variation  Trend_DD            6   3   2
2026-08-18  18.75  Normal           Normal_Variation  Normal_Variation  Normal_Variation    3   0   0
2026-08-19   25.5  Normal           Normal_Variation  Normal_Variation  Normal_Variation    2   7   1
2026-08-20  24.75  Normal           Neutral_Center    Neutral_Extreme   Neutral_Extreme     7   1   1
2026-08-21  19.75  Normal           Normal_Variation  Normal_Variation  Normal_Variation    4   7   0
2026-08-24  27.75  Normal           Normal            Normal_Variation  Normal_Variation    2   0   0
2026-08-25   21.5  Normal           Normal_Variation  Normal_Variation  Normal_Variation    2   0   0
2026-08-26  23.25  Normal           Normal            Normal_Variation  Neutral_Center      4   4   4
2026-08-27  27.75  Normal           Normal_Variation  Normal_Variation  Normal_Variation    5   5   0
2026-08-28   34.0  Nonconviction    Normal_Variation  Neutral_Extreme   Neutral_Extreme     7   8   6
2026-08-31   29.5  Normal           Normal            Normal            Normal_Variation    3   7   4
2026-09-01  28.75  Normal           Normal_Variation  Normal_Variation  Neutral_Center      5   3   3
2026-09-02  39.25  Normal           Normal_Variation  Normal_Variation  Normal_Variation    3   4   1
2026-09-03   26.0  Normal           Normal_Variation  Trend_Normal      Trend_Normal        4   2   1
2026-09-04   21.5  Normal           Normal_Variation  Normal_Variation  Normal_Variation    1   5   1
2026-09-08  37.75  Normal           Normal            Normal            Normal_Variation    3   3   2
2026-09-09   19.5  Normal           Normal_Variation  Normal_Variation  Normal_Variation    3   2   0

SESSIONS=20  changes=73  avg=3.65/session  live trades=77
trades fired under a label that later changed = 27 of 71 priced (38%)
label @IB-lock == final EOD label:  0/20        label @19:00 == final: 11/20
label @21:00   == final:           15/20        first committed label == final: 12/20
label changes that are pure Normal <-> Normal_Variation: 32/73 (44%)
final-label distribution: Normal_Variation 14 · Neutral_Extreme 2 · Neutral_Center 2 · Trend_DD 1 · Trend_Normal 1
label @IB-lock distribution: Normal 19 · Nonconviction 1
```

The `@lock`-vs-`FINAL` column is the headline: **the IB-lock label was wrong in 20 of 20 sessions**,
and 19 of those 20 locks said `Normal` — the catch-all the doctrine calls "the exception, not the
rule" (`DOCTRINE.md:112`). The classifier is not identifying the day at lock; it is defaulting.

---

## 8 · Gaps ranked by money-relevance

| # | Gap | Evidence | Smallest fix | Ruling status |
|---|---|---|---|---|
| **G-1** | **Gate label lags S1 by 10 min**; 73 changes/20 sessions, 44% pure oscillation | §2 (09-09 log, 11/11 evaluations used the stale `Normal`) | Turn on `DAYTYPE_RECLASS_STABILITY_V1` (built: `label_stability.py:104` `confirm_label`, wired `main.py:592-607, 1058`; N from `DAYTYPE_RECLASS_CONFIRM_BARS`, default 2). Its own replay: 200→135 jumps, the 12 self-contradicting days (Σ −$728.75) collapse to one label, 12/12 match the retrospective classification, only 18 stamps change (5 live, +$115). Then `DAYTYPE_ANTIFLAP_HOLD_S` can drop 600→300 because the flapping is fixed at the source, not masked at the read | **SHIPPABLE — already ruled.** Michael 2026-08-19, re-confirmed 08-20 (`config/RULED_FLAGS.yaml:329`). `.env:297` still `=0`, **21 days after the ruling**, and its `RULED_FLAGS` line is commented out so `flag_guard` cannot see the drift (`flag_guard.py` → PASS, 251 flags). Per CLAUDE.md "Rulings are one-time and standing", this ships without a second approval |
| **G-2** | **Counter-extension is the loss**: 19 trades against the accepted break = 39% / −$315 | §3 table | Enable `VARIATION_SUBTYPE_V1` (`.env` `=0`; built at `trading_gateway.py:1592-1611`, keys on the live `accepted_break`) so rotational-Variation stops authorising with-break entries and directional-Variation stops authorising fades | **NEEDS MICHAEL** — changes which setups fire (trading-risk surface). Note the memory entry: `grep -c dalton_intent:bias ⇒ 0` — the bias gate does not exist yet |
| **G-3** | **Mid-IB restart still hydrates yesterday's IB**, and today's `2026-09-10` GLOBEX row already carries it with `locked=1` | §5, DB rows id 2336/2333 | Two lines: add `AND session_type='CASH'` to `tpo_system.py:121`, and when `_first12_rth_extremes()` returns `None` **and** the stored `ib_locked_ts` is not today's ET date, drop `ib_locked` instead of trusting it | **SHIPPABLE** — implements the standing "one truthful IB" ruling (same basis as `1bb6879b`). **Today's mitigation without any code: do not restart the backend between 16:30 and 17:30 IL** |
| **G-4** | **53% of live trades carry a null/wrong `day_type_at_entry`**, and 8 gates read that snapshot | §6 | Stamp the row from the same call the gate used in that evaluation instead of re-calling `get_live_day_type()` later (`trade_context.py:694-745`) | **SHIPPABLE** (observability/consistency, no new behaviour) — but G-1 removes most of it first |
| **G-5** | **No canonical classification in the first hour**; legacy engine publishes `Trend_Normal` where the canonical engine says `Normal` (09-09 17:02→17:36) | §0.1, §2 | Move the `ib_locked` gate off `main.py:406` and let `classify_session` run from bar 6 — the `FORMING`/provisional ladder inside `classify()` already handles <12 bars (`:328-336`). `DAYTYPE_HONEST_PRELOCK_V1=1` is already on, so a pre-lock label informs but cannot veto | **NEEDS MICHAEL** — publishes a label into the first hour where none exists today; it is the doctrine's own P0-2 (`DOCTRINE.md:173-178`) which §7 wrongly marks ✅ |
| **G-6** | **`Normal_Variation` is 74% of entries and 70% of EOD labels** — the label carries almost no information | §3, §7 | Bound the NV band at the doctrine's 2.00 (`yaml:40`) and route 2.00–2.50 to the elongation/control Trend paths already built | **NEEDS MICHAEL** — changes the type distribution, i.e. every per-day-type playbook row |
| **G-7** | **Replay contamination:** `classifier_core.py:241-256` reads the single live file `~/SierraChart_Data/v9_export/cumulative_delta.json` (no date key) with `DELTA_FEATURES_V1=1`, so every historical replay sees **today's** delta | file has 90 live points, `export_ts=1789022203` | Pass delta in as an argument, or skip the block when the caller signals replay | **SHIPPABLE** (replay fidelity only; no live behaviour change). Until then every delta-dependent replay number is suspect |
| **G-8** | Classifier's value area is volume-at-typical-price, not TPO | §4, `value_migration.py:41-60` | Feed Sierra's developing VAH/VAL into `classify_session` alongside the bar-derived one and log the disagreement before changing any branch | **MEASURE FIRST** per `LEARNING_DOCTRINE_2026-09-09` — "הוראה חדשה ⇒ קודם ריפליי, אחר-כך דגל" |

---

## 9 · Bottom line for 16:30 today

**Is day-type identification good enough to trade on today? Conditionally yes — but only as a
management frame, not as an entry filter.** The classifier is self-consistent, runs every bar, moves
both ways, and its Neutral/DD/Nonconviction branches are doctrine-aligned. What is not good enough:
the label at IB lock was wrong in 20/20 sessions, it is `Normal_Variation` 70% of the time, and the
value the gates act on is 10 minutes stale. Trading *off* that label today means trading off a
coin-flip; trading *with* it as the runner/target/stop frame (`RUNNER_BY_DAYTYPE_V1`,
`C4_RULING6_V1`) is defensible, because those decisions are slower than the lag.

**The single thing that would most improve it: turn on `DAYTYPE_RECLASS_STABILITY_V1` (`.env:297`,
currently `0`).** It is already built, already tested (21 regression tests), already ruled by
Michael on 2026-08-19 and re-confirmed 08-20, and it attacks the root — the publish-side flapping —
rather than the symptom the 600-second antiflap is masking. Its own replay evidence says the 12
self-contradicting days worth −$728.75 collapse into one correct label. Nothing else on this list
buys as much for as little risk.

**One operational instruction that costs nothing and needs no code: do not restart the backend
between 16:30 and 17:30 IL today** (§5, G-3) — today's `v9_tpo_sessions` row already holds
yesterday's IB with `ib_locked=1`, and neither the classifier's `S1_IB_SANITY_V1` nor last night's
`1bb6879b` can catch it before 12 RTH bars exist.
