# DALTON DOCTRINE — "Mind over Markets" as the S1 spec authority

**Source:** `docs/spec_authority/source/Dalton_Mind_over_Markets.pdf` (Dalton/Jones/Dalton, Traders Press 1993/1999, 356 PDF pages).
**Page citations:** `p.N` = printed book page. **PDF page = book page + 14** (verified: book p.11 → PDF 25, p.16 → PDF 30).
**Status:** doctrine + gap analysis + backlog. READ-ONLY — no code changed. Every backlog item that alters classification
is a trading-risk-surface change → Michael sign-off before build (Pre-LIVE Discipline).
**Written:** 2026-07-08 (Cowork doctrine agent). Companion docs: `S1_ACTIVE_CANONICAL.md`, `S1_CLASSIFIER_AS_BUILT.md`,
`docs/reports/DAYTYPE_DEFINITION_AUDIT_2026-06-30.md` (file:line evidence base), `MOM_GAP_ANALYSIS_2026-07-02.md`.

---

## 0 · תקציר למיכאל (עברית)

הספר של דלתון הוא "התורה" של S1, ואלה חמש השורות התחתונות שלו מולנו:
1. **המבנה מאחר.** "Structure provides the confirmation" — הלוגיקה יוצרת את הדחף, הזמן נותן את האות, המבנה רק מאשר (p.38).
   מי שממתין לאישור מבני מלא — מאחר. זה בדיוק הפער של 08-07: פריצה עם acceptance חייבת להפוך את הסיווג מייד.
2. **הפתיחה מנבאת את היום.** ארבעת סוגי-הפתיחה + מיקום הפתיחה מול ה-Value של אתמול נותנים כיוון וסוג-יום צפוי
   כבר בדקות הראשונות (pp.63–74). אצלנו המסווג הקנוני עדיין FORMING עד 60 דק' — סתירה ישירה לספר ולפסיקת D1.
3. **יום-מגמה מזוהה בשליטה, לא בכפולת-טווח.** one-timeframe (מדרגות), פרופיל צר ומוארך, הרחבות-טווח עוקבות (p.25, p.40) —
   לא rib≥2.5. אי-זיהוי יום-מגמה = "הטעות היקרה ביותר" (p.25).
4. **Acceptance מול Rejection הוא כלל-ההכרעה בכל רמה:** דאבל-פרינטים בתוך ערך = מעבר מלא (p.278), מילוי-גאפ בשעה
   הראשונה (p.293), חזרה דרך הפתיחה/הצוואר = ביטול (p.65, p.27). זה צריך להריץ גם reclass וגם יציאות.
5. **רוב הימים אינם Trend** (20–30% בלבד, p.54) — Nontrend-first נכון; ו-Normal אמיתי הוא דווקא נדיר (p.20) —
   ברירת-המחדל "Normal-נוטה" שלנו סותרת את הספר. ביום Nontrend/Nonconviction — לא נכנסים בכלל (p.300–302).

---

## 1 · Core auction concepts

### 1.1 The auction & the two big questions
- **Doctrine:** price auctions up until the last buyer has bought, down until the last seller has sold — always advertising
  for the opposite party (pp.10–11). Everything reduces to two questions: *Which way is the market trying to go?* and
  *Is it doing a good job getting there?* (pp.57–58).
- **Signature:** attempted direction (RE, tails, TPO count direction) vs performance (volume, value migration, elongation).
- **S1 status:** implicit only. `classify()` encodes structure, not the two questions as explicit outputs.
- **Gap:** no per-bar "attempted direction + performance" pair; would make the briefing and confidence self-explaining.

### 1.2 Other-timeframe (OTF) participants & control
- **Doctrine:** locals provide liquidity, the *other timeframe* moves and shapes price (p.14). Control is read from
  (a) **tails/extremes** — ≥2 single TPOs, longer = stronger; a last-period tail is not valid (p.15, p.40);
  (b) **range extension** — repeated, multi-period RE = stronger control, elongated profile (p.40);
  (c) **body / TPO count** — TPOs above vs below POC, singles excluded; imbalance in the developing value area (pp.41–45).
- **Signature:** tail length in ticks per extreme; count of REs per side; TPO-count ratio above/below POC.
- **S1 status:** partial. Extension-with-acceptance = `sides` (`relative_features.py:157-173`); tails built in
  `tpo/profile_builder.py`/`levels.py` but ungated; TPO count **missing** (only `max_tpo_count` width in `zohar_rules.py:135`).
- **Gap:** no tail-quality grading, no TPO-count imbalance input (backlog P2-9).

### 1.3 Initial Balance
- **Doctrine:** IB = the first two half-hour periods ("slightly longer in the S&P"), the *base* of the day (p.11).
  Narrow base → easily upset → RE/trend likely; wide base → likely holds as the day's extremes (p.19).
- **Signature:** IB width absolute + percentile vs recent days; base-width class drives day-type priors.
- **S1 status:** implemented. 60-min IB, Sierra TPO source of truth (`S1_ACTIVE_CANONICAL.md §1`); `ib_narrow` =
  ≤0.7× recent median (`classifier_core.py:112`), abs fallback 7pt (`daytype_classifier.py` Normal branch); `rib` = range/IB.
- **Gap:** narrow-IB is used inside Nontrend/Normal/DD but **not** as an explicit early "trend-watch" prior (p.19 says
  narrow base = expect upset). Feeds backlog P0-2.

### 1.4 Range extension
- **Doctrine:** any move beyond the IB; means the OTF entered — "something has changed" (p.14). Ratified MEMS rule
  (extension = post-B-period break of the first-hour IB) **agrees** with pp.11–14 (D-period example breaks the A–B IB).
- **Signature:** closed-bar break of IB edge + hold + volume acceptance, per side.
- **S1 status:** implemented as `sides`: close beyond edge ±2-tick buffer, ≥2 consecutive bars, ≥8% session volume beyond
  edge (`relative_features.py:101-102,157-173`). The doc-cited "≥0.3×IB" magnitude is dead config (audit D3).
- **Gap:** none structural; but RE *count/persistence* (multiple periods extending — p.40) is not scored → conviction input.

### 1.5 TPO structure & value area
- **Doctrine:** TPO = half-hour letter at a price (p.11). Value area = ~70% of the day's business, one σ around POC;
  POC = longest line closest to range center — the day's fairest price (p.15, pp.42–43; TPO VA method p.333).
- **Signature:** developing VAH/VAL/POC per bar; prior-day VAH/VAL/POC as reference frame.
- **S1 status:** implemented as inputs — prior VA/POC + developing TPO flow into `classify_replay`
  (`backend/v9/api/v9/daytype_classify_routes.py`; audit §B#3). Profile *shape* (P/b/D) computed but consumed by no gate
  (`MOM_GAP_ANALYSIS_2026-07-02.md`).
- **Gap:** shape unconsumed (backlog P1-5); value-*migration* not the classification driver (P1-6).

### 1.6 Initiative vs responsive
- **Doctrine:** the reference is the **previous day's value area**. Buying within-or-above prior VA = initiative; selling
  within-or-below = initiative; responsive is the obverse (buy below value / sell above value) (pp.45–46, 49). An
  initiative RE and the responsive tail that stops it are one and the same event (p.46).
- **Signature:** tag every tail/RE/VA placement initiative|responsive using prior VA.
- **S1 status:** missing in S1. S2 has REACTIVE/INITIATIVE pattern names (`five_min/five_min_system.py`) but S1 emits no
  initiative/responsive tag on the day's activity.
- **Gap:** conviction input lost — initiative activity carries more confidence than responsive (p.45). Feeds P0-3.

### 1.7 Acceptance vs rejection
- **Doctrine:** acceptance = price *spends time* / builds double TPO prints at a level; rejection = tails, swift moves away.
  Applications: accepted inside prior VA → likely traverses the whole VA (Value-Area Rule, p.278); gap not filled within
  ~the first hour → continuation likely (p.293); price back through an Open-Drive origin or into DD neck singles →
  conditions changed, exit (p.65, p.27); balance-area breakout accepted → go with it, "a trade you almost have to do"
  (pp.288–292).
- **S1 status:** partial. Acceptance is implemented **only at IB edges** (`relative_features.py:157-173`) and open-return
  (`relative_features.py:186-192` → `returned_through_open` overlay blocking Trend, `daytype_classifier.py:120`).
- **Gap:** no acceptance test at prior-day VA/range, balance-area, gap, or DD-neck references (backlog P0-1, P1-7, P2-11).

### 1.8 Structure lags — the reclassification-speed doctrine
- **Doctrine:** "Structure acts as the market's translator, and translated information is second-hand" (p.37). Traders
  relying only on structure are late; time and logic signal first. Summary: *"Logic creates the impetus, time generates
  the signal, and structure provides the confirmation"* (p.38). Visible information and opportunity are inversely related (p.37).
- **Consequence for S1:** waiting for full structural proof (rib≥2.5 + close-at-extreme) before naming a Trend is
  doctrinally wrong. The moment one-sided acceptance exists, classification must move (provisionally) — confidence, not
  silence, expresses the residual doubt. This is exactly Michael's 2026-07-08 ruling.

---

## 2 · The day types (Dalton's 6 → MEMS 7 + Nonconviction)

Dalton's six: Normal, Normal Variation, Trend, Double-Distribution Trend, Nontrend, Neutral (p.19–29), with Neutral split
center/extreme (p.29) → MEMS 7-type map is faithful. Day types sit on a **conviction continuum** from Nontrend to Trend;
"by monitoring a day's conviction very early… traders can quickly begin to visualize how the day will develop" (p.29).
Base-width + OTF confidence generate the types (p.19).

| Type | Dalton definition (pages) | Measurable signature | S1 status (file:line) | Gap |
|---|---|---|---|---|
| **Normal** | Swift early OTF entry → **wide IB**, never upset; two-sided balance rest of day; often early news (p.20). "More the exception than the rule" (p.20). | wide IB (≥P67), sides==0, rotation VAH↔VAL, tails both ends, close in VA | `daytype_classifier.py:156` = rib≤1.30 + normal vol + IB-not-narrow. No wide-IB/rotation/inside-IB% gates (audit D5). Catch-all PROVISIONAL "Normal-leaning" `:161`. | Under-specified vs p.20; default-Normal bias **contradicts** "exception not the rule". |
| **Normal Variation** | Less dynamic early; OTF enters later and **extends one side substantially**, ~doubling the IB; then two-timeframe trade, value re-established at new level (p.22). | sides==1, rib ~1.3–2.0, RE holds then balances | `daytype_classifier.py:141` sides==1 catch-all up to rib<2.5 (doc band 2.0 — audit D6). | Band mismatch 2.0 vs 2.5; "then rebalances" (value forms at new level) unmeasured. |
| **Trend (standard)** | OTF in control **open→close**; open forms one extreme in the large majority of cases (p.22); **one-timeframe**: each period ≥/≤ prior, no opposite break (p.25); profile **thin, elongated, ≤4–5 TPO wide** (p.25); draws in new business, higher volume (p.22). Failure to recognize = costliest mistake (p.25). | one_tf periods, stair-step count, elongation ratio, RE persistence, close at extreme | `daytype_classifier.py:120`: sides==1 AND not-oi AND one_tf AND close≥0.85/≤0.15 AND rib≥2.5. `S1_OPEN_DRIVE_TREND` waiver exists, **OFF** (`:129-134`). | **Contradiction:** Dalton keys on control+elongation, not a range multiple; rib≥2.5+close-extreme makes midday recognition late (07-08). |
| **Double-Distribution Trend** | Quiet first hours, **small IB**; later OTF entry drives to a new level where a **second balance region** forms, separated by **single prints**; late refill of those singles (double prints) = second distribution rejected → conditions changed (pp.25–27). | narrow IB + bimodal TPO/vol + deep neck + new value held; neck-refill invalidation | `dd_features.py:37-105`: narrow (≤0.7×median) + bimodal (second≥min) + neck≥0.60 + held → `Trend_DD` (`daytype_classifier.py:115`). | Detector aligned; **neck-refill invalidation trigger missing** (p.27) — no reclass/exit event. |
| **Nontrend** | No conviction at all; often pre-news/holiday; narrow initial range that *looks* like a trend day start but **no RE ever comes**; low participation (p.27). Stay out (p.300). | narrow IB, sides==0, low vol, tiny range | `daytype_classifier.py:97`: sides==0 + vol_ratio≤0.5 + rib≤1.15 (+range≤18pt flag OFF). vol_ratio None → Nontrend unreachable (audit D4). | rib ceiling doc 1.5 vs code 1.15; vol-None hole; Dalton's "waiting for information" (calendar) input absent. |
| **Neutral-Center** | OTF buyer AND seller both active → **RE on both sides**; close in mid-range = balance, no victor (pp.27–29). | sides==2, close_pos 0.33–0.67 | `daytype_classifier.py:103-108` ✅ (volume-accepted two-sided extension). | Aligned. |
| **Neutral-Extreme** | Two-sided day that **closes on an extreme** — a day-timeframe victor; strong next-day continuation bias (p.29; study: 64% better than prior VA in first 90 min, 45% at close, p.277). | sides==2, close_pos ≥0.85/≤0.15; EOD tag → next-day bias | `daytype_classifier.py:104-105` ✅. No EOD continuation tag for the next morning. | Add next-day bias tag (P2-12). |
| **Nonconviction (8th)** | Looks like Normal/NV/Neutral **but no OTF signature at all**: Open-Auction inside prior value, no tails, no RE, random rotation — no reference points; stay out (pp.300–302). | OA-in-value + zero tails + zero RE + mid close | **Missing** (also `MOM_GAP` layer A). | Build as override type → NO_TRADE. |

---

## 3 · Intraday evolution — opens, transitions, invalidation

### 3.1 The open foreshadows the day (pp.63–74)
"The market's open often foreshadows the day's outcome" (p.63). Conviction is readable in the **first few minutes** (p.63).

| Open type (pages) | Dalton meaning | Day-type expectation | Extreme holds? |
|---|---|---|---|
| **Open-Drive** (pp.63–65) | OTF decided pre-open; drives, never re-trades the opening range | **Trend or Normal Variation** (p.65); enter early, "one step ahead of structure" | Vast majority — origin = reliable reference; return through it = exit (p.65) |
| **Open-Test-Drive** (pp.65–67) | Tests a known reference (prior H/L, bracket), fails, drives opposite | **Normal Variation or Trend** (p.67) | 2nd most reliable (p.65) |
| **Open-Rejection-Reverse** (pp.68–70) | Drives, stalls, reverses back through the open | **Normal / Normal Variation**, two-sided; Trend unlikely (p.68) | <50% (p.68) |
| **Open-Auction in range** (pp.70–71) | Rotates around open inside prior range/value — sentiment unchanged | **Nontrend / Normal / Neutral**; "a big day unlikely" (p.71) | Low |
| **Open-Auction out of range** (pp.70–74) | Rotates but **out of balance** → dramatic move potential either way | "often gives rise to **Double-Distribution Trend days**" (p.70–71) | Watch first RE |

Open vs prior day (pp.74–88): within value + acceptance → balance, day range ≈ prior range superimposed from the held
extreme, ±10% (pp.75–79); outside value in range → overlap to one side (p.80); **outside range + acceptance → out of
balance, range unlimited, usually a Trend day** (p.84); outside range + rejection → dynamic move the *other* way (p.84).
Gap = out of balance; if not filled in ~the first hour, continuation likely; stop where the gap is fully erased (pp.88, 292–293).

**S1 status:** opening detector v2 implements exactly these five labels (`opening_detector_v2.py:61,99,129`); gap inputs
exist (`day_type/detector.py:334`, `state_machine.py:431-480`). **But** the canonical classifier returns bare `FORMING`
until 12 bars (`daytype_classifier.py:86`) and uses `opening_type` only in the OFF-flag Trend waiver — the open's
forecast is thrown away for the first hour. The legacy engine's half-IB provisional (`state_machine.py:378-420`) is the
fallback, not the canonical path. **Contradiction with pp.63–74 + ruling D1 (staged classification).**

### 3.2 Transitions & invalidation (the 07-08 case)
- Balance→breakout: acceptance outside a balance area/IB **is** the new state — go with it (pp.288–292); a failed
  breakout that returns inside = rejection → expect rotation to the other extreme (p.292, the "rock").
- Trend that stops holding: value areas overlapping / moving against trend = trend slowing → bracket (p.55). Supports the
  2026-06-30 ruling: acceptance-driven transitions, **not** never-downgrade (audit D2).
- Invalidation references: back through Open-Drive origin (p.65) ✅ implemented as `returned_through_open`
  (`relative_features.py:186-192`); into DD neck singles (p.27) ❌ not wired; gap erased (p.293) ❌ not wired.
- **2026-07-08 live gap:** stair-stepping down day sat LOCKED_LOW_CONF `Trend_DD` conf 0.46 on the legacy surface
  (`state_machine.py:26`; numeric confidence exists only there) while the UI showed Nontrend and reclass lagged the
  breakout. Dalton: structure-lag (p.37) + one-timeframe stair-steps (p.25) + balance-breakout acceptance (p.288) all said
  "Trend down, promptly". Root causes: no early staged type, Trend floor rib≥2.5, no canonical confidence, dual sources.

---

## 4 · S1 improvement backlog (P0/P1/P2)

Every item: WHAT → WHY (Dalton pages) → ACCEPTANCE CRITERION. Build flag-OFF, replay-verified, Michael sign-off to enable.

**P0-1 · Acceptance-driven prompt reclassification** (Michael's 07-08 ruling)
WHAT: on any committed reference break (IB edge, prior range, balance area) with acceptance (≥2 closed bars + vol-accept —
reuse `relative_features.py:157-173`), re-run classification immediately and allow *downgrades/upgrades* both ways;
return inside reference = rejection → revert + tag failed-breakout.
WHY: structure lags (pp.37–38); go-with-breakout (pp.288–292); trend-recognition failure = costliest mistake (p.25).
ACCEPT: replay 2026-07-08 → type flips to Trend_DD/Trend_Normal(DOWN) within ≤2 bars (10 min) of the acceptance bar close;
regression replays 06-29/06-30 unchanged; UI==gate==engine one value (kills the source split).

**P0-2 · Staged early classification wired into the canonical path**
WHAT: replace bare `FORMING` (`daytype_classifier.py:86`) with committed provisional: opening_type@15min → provisional
day-type@30min from {open type × open-vs-prior-value/range × IB-width class} per §3.1 table; IB-lock@60min confirms.
WHY: open foreshadows the day (pp.63–74); OA-out-of-range/narrow IB → DD watch (pp.70–74, 88); ruling D1.
ACCEPT: every replay session emits a provisional type+direction by 30 min (0% bare-FORMING at 30m); report provisional→EOD
hit-rate on ≥20 replay days as calibration baseline; S1_OPEN_DRIVE_TREND case covered.

**P0-3 · Canonical confidence score (kill the 0.46 split)**
WHAT: add confidence ∈[0,1] to `classify()` output = fraction of aligned evidence {open type strength, one_tf, RE
persistence, tail direction, TPO-count direction, CVD, close_pos, elongation, initiative/responsive tag}; surface it in
`classify_replay` + UI + gate; legacy `state_machine.py` confidence/lock_state never shown when S1_ENGINE_NEW_CLASSIFIER=1.
WHY: conviction continuum, "monitor conviction very early" (p.29); 3-1 confluence = tails+RE+TPO agreeing (pp.273–275).
ACCEPT: one confidence value across engine/replay/UI; on 07-08 replay confidence rises monotonically through the down
stair-steps; LOCKED_LOW_CONF string absent from user-facing surfaces.

**P1-4 · One-timeframe running boolean + stair-step counter**
WHAT: expose `one_tf` (`relative_features.py:184`) per 30-min period from period 2 onward + consecutive stair-step count,
as a live feature feeding P0-2/P0-3 (and S6 trailing).
WHY: one-timeframe = OTF control definition (p.25). ACCEPT: 07-08 replay flags DOWN one-timeframe by B/C period.

**P1-5 · Elongation / profile-shape gate**
WHAT: TPO width ratio (mean TPOs-per-price vs range) + P/b/D tag consumed by the Trend branch as an *alternative* to
rib≥2.5 (elongated + one_tf + sides==1 = Trend even at rib<2.5); P-shape blocks CONT-long (MOM_GAP item-13).
WHY: trend profile "thin and elongated, no more than 4–5 TPOs wide" (p.25); elongation = trade facilitation (p.40).
ACCEPT: 07-08 tagged elongated-down; known P-day replay blocks initiative-long in shadow.

**P1-6 · Value-migration classification feature** (ratified: VALUE migration, not geometry)
WHAT: per-bar developing-VA overlap% vs prior VA + POC drift direction/velocity; Trend continuation requires migrating
value; overlapping value = balance/bracket signal.
WHY: trend acceptance read from value-area placement series (p.55); day value initiative/responsive placement (p.49).
ACCEPT: feature emitted per bar in replay; Trend replays show monotone migration, Neutral/Normal show overlap.

**P1-7 · DD neck-refill invalidation trigger**
WHAT: after Trend_DD, monitor the neck singles; double-printing them → emit `dd_invalidated` → reclass + S6 exit signal.
WHY: refilled singles mean the second distribution is rejected — "something has changed" (p.27).
ACCEPT: synthetic + historical replay where neck refills → classification leaves Trend_DD same bar + event logged.

**P1-8 · Nonconviction 8th type (override → NO_TRADE)**
WHAT: OA-in-prior-value + no qualifying tails + sides==0 + mid close → `Nonconviction`; suppresses S2/S4 (shadow first).
WHY: no reference points → stand aside (pp.300–302). ACCEPT: dead-day replay (e.g. 07-03) tags it; zero fires in shadow.

**P2-9 · TPO-count imbalance** — sum TPOs above/below POC excl. singles as OTF body pressure into confidence (pp.41–45).
ACCEPT: feature matches hand count on 3 replay days.
**P2-10 · Day-range estimation** — prior range superimposed from the held extreme ±10% (pp.75–79) → briefing + target sanity.
ACCEPT: estimate emitted once an extreme qualifies; error distribution reported over replays.
**P2-11 · Value-Area Rule flag** — open outside prior VA + double-print acceptance inside → expect full traverse; block
fades against it, target = far VA edge, weighted by distance/width/direction (pp.278–280). ACCEPT: rule fires on replay
days that traversed; no fire on rejected entries.
**P2-12 · EOD continuation tags** — 3-1 / 2I-1R / Neutral-Extreme-close tags (94%/71%/64% first-90-min stats, pp.273–277)
stored at EOD → next-morning briefing bias. ACCEPT: tags in DB for replay set; briefing renders them.

---

## 5 · Daily briefing vocabulary (feeds the morning briefing)

- **Trend_Normal:** one side owns the day from the open. S2: hunt with-trend INITIATIVE/continuation + pullback-to-drive
  entries only — never fade (p.25). S4: ZLR/GB100 with-trend only. Stops: beyond last stair-step (prior period extreme);
  targets: let runners ride to EOD/LSMA — trends "need to be left alone", high profit expectation (p.54).
- **Trend_DD:** narrow IB, late drive to a second value area (pp.25–27). S2: after the neck forms, trade pullbacks toward
  the neck in trend direction; S4: with-trend patterns in the second distribution. Stop: through the neck singles —
  refill = out (p.27). Target: extension of the second distribution.
- **Normal:** wide IB holds all day (p.20). S2: responsive fades of IB/VA extremes back to POC; S4: counter-moves at
  extremes. Stops: just beyond IB extreme/tail; targets: POC then opposite VA edge. Two-sided, modest expectations.
- **Normal_Variation:** early balance, then one-sided RE that re-balances at a new level (p.22). S2: trade the RE direction
  on acceptance, then switch to rotation logic around the new value; S4: with-RE then fade new edges. Stops: inside old
  IB after break; targets: new VA edges (~2×IB move typical).
- **Neutral_Center:** both OTFs active, close mid (pp.27–29). Bracket rules: fade both extremes, take profits quickly,
  "hands-on" (pp.54–55). Tight stops beyond the two-sided extremes; targets: POC. Small size, quick exits.
- **Neutral_Extreme:** two-sided tug-of-war resolved late — trade with the late victor into the close (p.29); carry the
  64%-continuation bias into tomorrow's first 90 min (p.277). Stops: back through POC; target: hold to close.
- **Nontrend:** no participation, no RE (p.27). S2+S4: **NO_TRADE** — "the most obvious market to stay out of" (p.300).
- **Nonconviction:** structure mimics Normal/NV but no OTF footprints — random rotation (pp.300–302). Stand aside entirely.

---

## 6 · Explicit book-vs-current-S1 contradictions (summary)

1. Bare `FORMING` until 60 min (`daytype_classifier.py:86`) vs open-foreshadows doctrine (pp.63–74) + D1 ruling → P0-2.
2. Trend floor rib≥2.5 + close-at-extreme (`daytype_classifier.py:120`) vs control/elongation definition (pp.22–25, 40) → P0-1/P1-5.
3. No canonical confidence; legacy 0.46/LOCKED_LOW_CONF surfaces (`state_machine.py:26,419`) vs conviction-continuum (p.29) → P0-3.
4. Default "Normal-leaning" provisional (`daytype_classifier.py:161`) vs "Normal is the exception" (p.20) + Nontrend-first ruling.
5. DD neck-refill invalidation absent (p.27) though detector computes the neck (`dd_features.py:97-105`) → P1-7.
6. Acceptance tested only at IB edges (`relative_features.py:157-173`) vs VA/gap/balance-area references (pp.278–293) → P0-1/P2-11.
7. Initiative/responsive tagging (pp.45–49) absent from S1 outputs → P0-3 input.
8. Nonconviction day type (pp.300–302) unmodeled → P1-8.
