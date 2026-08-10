# Dalton day-type research — LIVE session 2026-08-10 (MES)

**Author:** `dalton-research-agent` (Cowork) · **Data cut:** 11:55 ET / 18:55 IDT, session still open
**Scope:** READ-ONLY. No code, flag, config or `.env` was modified by this work.
**Method:** every number below is quoted from a command whose raw output is in §6 (Pre-LIVE Rule 5).

---

## 0. תקציר בעברית (12 שורות)

1. **מה היום הוא בשפת דלתון:** *Normal Variation Day* ("Expanded Typical") שההרחבה שלו **נכשלה** — פתיחה
   בתוך הערך, IB בינוני-צר (20.25), שבירה חד-צדדית למעלה בתקופה C (+5.75), ואז חזרה מלאה אל תוך ה-IB.
2. הקצה התחתון הוא **EXCESS אמיתי** (זנב-דחייה 6.75 נק', מגע יחיד, בלי ביקור-חוזר) — קרקע מוגנת.
   הקצה העליון **NEUTRAL** (זנב 1.5 נק') — מכירה לא-גמורה, כלומר מגנט לבדיקה חוזרת, לא תקרה אמיתית.
3. הקשר רב-יומי: ערך נודד **UP** ‎+33.26 נק'/יום, חפיפת-VA ‎**1%** בלבד ⇒ קונה-OTF בשליטה מובהקת.
   היום = **יום-איזון/הפוגה בתוך מכירה-פומבית עולה**, לא היפוך.
4. **איפה דלתון נכנס ביום כזה:** רספונסיבי בקצה-התחתון של הערך מעל ה-EXCESS, ואינישייטיב רק על
   **ההרחבה המוצלחת הראשונה** — ואז **על הפולבק אליה**, לא על השבירה עצמה.
5. **איפה דלתון אוסר להיכנס:** רדיפה אחרי הרחבה בלי פולבק, וקנייה מעל ה-POC כשכל היעדים מאחוריך.
6. **מה המערכת עשתה בפועל:** חסמה את שתי הכניסות הנכונות של היום (@7777.75 / @7778.25, 09:55) בגלל
   `extreme_chase_guard` מול שיא-סשן בן 25 דקות — ואז **ביצעה לונג חי @7795**, 2 נק' משיא-היום.
7. עלות הפספוס: היום הגיע ל-7797 ⇒ **~19.25 נק' שנחסמו**. העסקה שכן בוצעה: ‎**−$63.75 / −0.75R**.
8. **הממצא החמור:** לפני הירי המערכת עצמה כתבה שישה "לא" — `R:R 0.19`, שלושה `structural_targets ...
   on wrong side of LONG entry`, ושלושה `TargetClamp SKIP` — **וכולם נעקפו**. כשכל היעדים המבניים
   מתחת לכניסה, זו בדיוק ההגדרה של דלתון ל"אין מיקום-מסחר".
9. **ממצא שני (בטיחות):** הירי החי קרה **8 שניות אחרי ריסטארט של הבקאנד** — `bars_processed_today=0`,
   `buffer_size=1`, `profile_shape='NA'`. מערכת לא-מוזנת ירתה 4 חוזים חיים.
10. **ממצא שלישי (באג מאומת):** `_last_atr_daily` הוא ממוצע טווח-נר-5-דקות (6.396), לא ATR יומי (84.25).
    לכן `IB/ATR = 3.17 → EXTREME` במקום `0.24 → NARROW`. מטריצת-ההחלטה מקבלת "EXTREME" כמעט תמיד.
11. **התוצאה של הבאג:** `OPEN_AUCTION_IN × EXTREME → Normal` (fade edges, DBDT=FULL) במקום
    `OPEN_AUCTION_IN × NARROW → Nontrend` (הכול SKIP). זו הסיבה שהעסקה קיבלה **סייז מלא**.
12. **שלוש התוספות המובילות:** (1) וטו קשיח כשכל היעדים המבניים בצד-הלא-נכון; (2) תיקון ה-ATR
    ‎+ בגרות-סשן ל-`extreme_chase_guard` (השוואה ל-IB, לא לשיא בן 25 דק'); (3) כניסת-פולבק
    ‎`RE_PULLBACK_ENTRY_V1` אל שפת-ה-IB שנשברה / POC.

---

## 1. Today's profile — the facts

### 1.1 Price structure (`v9_bars_5min_woodies`, RTH ≥ 09:30 ET)

| Field | Value |
|---|---|
| RTH open | **7773.00** |
| IB (09:30–10:30, 12 bars) high / low / width | **7791.25 / 7771.00 / 20.25** |
| Session high / low (as of 11:55) | **7797.00** (10:45–10:50) / **7771.00** (09:50) |
| Session range | **26.00** |
| Range extension **up** | **+5.75** (28% of IB) |
| Range extension **down** | **0.00** |
| Last price (11:55) | 7788.50 |

Shape of the move: opened at 7773, put in the low 7771 at 09:50, then a near-uninterrupted grind up
through the whole IB to 7797 by 10:45 (period C), then a full retreat back **inside** the IB to 7778
at 11:35, and a recovery to 7788.50. **The up-extension was rejected, not accepted.**

### 1.2 Today's TPO profile (`session_tpo_profile` over the same bars, 5 periods A–E)

| POC | VAH | VAL | High | Low |
|---|---|---|---|---|
| **7783.25** | **7790.50** | **7779.25** | 7797.00 | 7771.00 |

Sierra's own `tpo.json` at the moment of the live fire (17:46:16 IDT):
`POC=7783.25 VAH=7791.25 VAL=7775.50 (spread=15.75)` — POC agrees exactly; VA edges differ by
≤3.75 (Sierra counts 30-min letters from its own clock). Either way the **entry at 7795 was above
both VAH readings.**

**Single prints:** two clusters —
- **7771.00 → 7777.75** — the A-period buying tail off the low.
- **7791.50 → 7797.00** — the entire C-period extension leg. Un-revisited singles above the IB.

**Extremes quality** (`/api/v9/context/radar`):
- **low_quality = `EXCESS`** — "rejection tail 6.75pt, close retreats, no revisit 3 bars", 1 touch.
- **high_quality = `NEUTRAL`** — "ambiguous: tail 1.50pt", 1 touch.

In Dalton's language: **the low is a finished auction (real, defended low); the high is an unfinished
auction** — no excess, so it is a magnet that the market is expected to revisit, not a ceiling.

### 1.3 Multi-day context (`/api/v9/context/multiday`, 6 sessions 07-31 → 08-07)

| Field | Value |
|---|---|
| Composite range | 7427.50 – 7820.25 |
| Composite value (VAL–VAH) | 7467.25 – **7788.75** |
| Composite POC | 7736.25 |
| **value_migration** | **UP, slope +33.26 pts/day** (n=5) |
| **va_overlap_pct** | **0.01** |
| **open_location** | **`in_value`** |
| Yesterday (08-07) POC / VAH / VAL | 7765.00 / 7781.25 / 7762.50 |

Reads:
- The 7773.00 open is **inside the 7-day composite value** *and* **inside yesterday's value**
  (7762.50–7781.25) → a genuine **open-auction-in-range**, the lowest-conviction open type.
- **`va_overlap_pct = 0.01` is the headline number.** Near-zero day-to-day value overlap over 6
  sessions means the market has been in sustained multi-day **imbalance** with the OTF **buyer** in
  control — value has migrated +33 pts/day. Radar concurs: `regime = IMBALANCE, confidence 0.8`.
- Today is a **higher high** (7797 > 7786.75) and **higher low** (7771 > 7743.25) vs 08-07, and
  today's POC 7783.25 is **+18.25** above yesterday's 7765.00 — so value is *still* migrating up,
  but at roughly **half** the 6-day rate, on a range of 26 pts against an 84-pt daily ATR.
  **This is a balancing / pause day inside an upward-migrating auction — not a reversal.**

### 1.4 IB in context — today's IB is the narrowest in 10 sessions

| Date | RTH open | IBH | IBL | **IB width** | Day range | RE up | RE dn |
|---|---|---|---|---|---|---|---|
| 07-28 | 7449.75 | 7476.75 | 7417.00 | 59.75 | 68.75 | 9.00 | 0.00 |
| 07-29 | 7456.50 | 7461.00 | 7398.25 | 62.75 | 139.00 | 4.50 | 71.75 |
| 07-30 | 7414.25 | 7446.50 | 7399.75 | 46.75 | 79.75 | 32.00 | 1.00 |
| 07-31 | 7498.75 | 7515.25 | 7427.50 | 87.75 | 113.50 | 25.75 | 0.00 |
| 08-03 | 7546.00 | 7600.00 | 7542.75 | 57.25 | 95.75 | 38.50 | 0.00 |
| 08-04 | 7657.50 | 7706.25 | 7656.00 | 50.25 | 99.25 | 49.00 | 0.00 |
| 08-05 | 7809.50 | 7820.25 | 7794.75 | 25.50 | 74.50 | 0.00 | 49.00 |
| 08-06 | 7751.75 | 7768.50 | 7740.25 | 28.25 | 44.25 | 0.00 | 16.00 |
| 08-07 | 7757.25 | 7780.50 | 7743.25 | 37.25 | 43.50 | 6.25 | 0.00 |
| **08-10** | **7773.00** | **7791.25** | **7771.00** | **20.25** | **26.00 (partial)** | **5.75** | **0.00** |

Per Dalton's lamp-base metaphor a 20.25 IB is a **narrow base** → high odds of being upset. It *was*
broken (upward, in C) — but the break was not accepted. That combination (narrow base broken, break
rejected) is the signature of a **failed Normal Variation**, and it is also the compression that
usually precedes a genuine expansion later in the session or on the next day.

### 1.5 Day classification history (`v9_day_type_state`, 29 rows today)

Stable read all session: `stage=B2`, `day_type=Variation`, reason
**`"1-sided extension = Expanded Typical"`**, confidence 0.38 → 0.67, `lock_state=PENDING`,
`leg=UP`, `opening_type=OPEN_AUCTION_IN`.

**⚠️ Live contradiction:** the trade's own `cross_context` (captured at fire time) recorded
`day_type_machine: {day_type: 'Normal', ib_width: 'EXTREME', confidence: 0.48}` while
`/api/v9/context/radar` at the same time reported `Variation / 0.67`. **Two different day labels were
live simultaneously**, and the *trade* was sized off the `Normal` one. Root cause in §4.3.

---

## 2. Gateway decisions today — 17 attempts, 1 fill

`~/SierraChart_Data/v9_export/gateway_decisions.jsonl` (ts are **UTC**; ET = UTC−4).

| ET | Sys | Pattern / dir | Entry | Outcome | Blocked by | Verdict |
|---|---|---|---|---|---|---|
| 09:35 | 4 | GB100 SHORT | 7772.25 | blocked | `cont_trend_filter` | ✅ correct — selling into the low |
| 09:44 | 4 | ZLR SHORT | 7774.25 | blocked | `cont_trend_filter` | ✅ correct |
| 09:45 | 4 | ZLR SHORT | 7773.00 | blocked | `cont_trend_filter` | ✅ correct |
| 09:52 | 4 | ZLR SHORT | 7771.25 | blocked | `cont_trend_filter` | ✅ **correct — this was the day's low** |
| **09:55** | 4 | **ZLR LONG** | **7777.75** | blocked | **`extreme_chase_guard`** | ❌ **the trade of the day** |
| **09:55** | 4 | **ZLR LONG** | **7778.25** | blocked | **`extreme_chase_guard`** | ❌ **the trade of the day** |
| 10:30 | 4 | ZLR LONG | 7790.50 | blocked | `extreme_chase_guard` | ~ marginal (+6.5 available) |
| 10:30 | 4 | ZLR LONG | 7790.00 | blocked | `extreme_chase_guard` | ~ marginal |
| 10:42 | 4 | ZLR LONG | 7792.50 | blocked | `extreme_chase_guard` | ✅ correct |
| 10:45 | 4 | ZLR LONG | 7792.75 | blocked | `extreme_chase_guard` | ✅ correct |
| 10:45 | 4 | ZLR LONG | 7792.75 | blocked | `extreme_chase_guard` | ✅ correct |
| **10:46:31** | **2** | **DOUBLE_BOTTOM_EE_LONG** | **7795.00** | **LIVE** | — | ❌ **worst location on the chart** |
| 10:46 | 4 | ZLR LONG | 7795.00 | blocked | `extreme_chase_guard` | ✅ correct |
| 10:46 | 4 | ZLR LONG | 7795.00 | blocked | `extreme_chase_guard` | ✅ correct |
| 11:00 | 4 | GB100 SHORT | 7782.00 | blocked | `awaiting_release` | — |
| 11:10 | 2 | REACTIVE_SHORT | 7782.00 | blocked | `daytype_playbook` | ✅ correct — "not at VAH (near_val)" |
| 11:20 | 4 | GHOST SHORT | 7786.25 | blocked | `lsma_flat` | — |

### 2.1 The two blocks that cost the day

At **09:55**, `session_high` was **7783.25** — the high of a **25-minute-old session**, set by the
first bar. The guard requires `session_high − entry ≥ 6.0`; entries at 7777.75 / 7778.25 were 5.50 /
5.00 away, so both were blocked.

Those two entries were, by Dalton's book, the **correct** longs of the day:
- 6.75–7.25 pts above the **7771 EXCESS low** (a finished auction — a real, defended low),
- **inside** today's developing value and inside the 7-day composite value,
- **with** a 6-day value migration of +33 pts/day and 1% VA overlap (OTF buyer in control),
- with an entirely un-tested IB high above them.

The day subsequently traded to **7797.00** → **+19.25 pts** of unrealised move was gated out.

The guard's `CHASE_MIN_SESSION_BARS = 6` (30 min) maturity bypass exists precisely for this
("an extreme of a 12-minute session is not an extreme") but 09:55 is bar 6 — the bypass had **just**
expired one bar earlier. The threshold is a bar count; the underlying quantity it should measure is
whether the extreme is *structurally meaningful* (i.e. related to the IB), not how old it is.

The same guard blocked five further longs at 7790–7795, and those blocks were **right** — which is
the point: the guard has the correct instinct and the wrong yardstick.

---

## 3. Trade #655 forensics — six overridden objections + a cold-start fire

### 3.1 The trade

`v9_trades` id **655** (live) + id **654** (shadow twin):

| Field | Value |
|---|---|
| Pattern | `DOUBLE_BOTTOM_EE_LONG` (family REV / playbook key `DBDT`) |
| firing_system | 2 (five_min) |
| Entry / stop | **7795.00** / **7790.75** (risk **4.25 pt**) |
| T1 / T2 / T3 | 7797.75 / 7803.50 / 7807.75 |
| Contracts | **4** (`sizing: 4`, size class "half" per the pattern note) |
| `day_type_at_entry` | **`Normal`** |
| Entry time / exit | 10:46:32 ET → 10:51:54 ET |
| Exit reason | `STOP_FILL`, preceded by `S6 MAE SCRATCH: 2.2pt >= 2.2pt threshold (pre-T1)` |
| Result | **`LOSS`, −$63.75, −0.75R** |

Location, in profile terms: **7795 is 2.00 pts below the session high (7797), above VAH on both
readings (7790.50 / 7791.25), above the IB high (7791.25), and 11.75 pts above the POC (7783.25).**
It is the single worst long location available on the chart at that moment.

### 3.2 The six objections the system raised and then overrode

Verbatim from `/tmp/backend.err.log`, in order, all in the ~1 second before the fire:

```
[pre_fire] RR_BREAKOUT_MM: capped-t2 R:R 0.19 rescued by spec multiplier (risk=28.00 t2_reward=5.44 mm_reward=42.00)
[Gateway] release-gate TREND BYPASS: LONG with-move, session displaced (open 7773.0 → 7794.75)
[Gateway] STOP_RESOLVER_V1: stop 7767.00 → 7790.75 (rung=r0, band [4.2, 7.8], atr=5.2)
[structural_targets] c1=7781.12 on wrong side of LONG entry=7795.00 → R-fallback
[structural_targets] c2=7790.00 on wrong side of LONG entry=7795.00 → R-fallback
[structural_targets] c3=7791.25 on wrong side of LONG entry=7795.00 → R-fallback
[TargetClamp] SKIP t1: edge 7791.25 <= entry 7795.00 + 0.25 (wrong-side clamp, LONG)
[TargetClamp] SKIP t2: edge 7791.25 <= entry 7795.00 + 0.25 (wrong-side clamp, LONG)
[TargetClamp] SKIP t3: edge 7791.25 <= entry 7795.00 + 0.25 (wrong-side clamp, LONG)
[Gateway] TARGET_REALISM_V1: t1 7799.12 → 7797.75 (LONG ceiling from session extreme + avg breakout step)
[Gateway] LIVE trade TM id=655: LONG DOUBLE_BOTTOM_EE_LONG system=2 ...
```

Read that list as a Dalton would:

1. **`R:R 0.19`** — the reward/risk gate said no. It was "rescued by spec multiplier".
2. **All three structural targets — half-extension (7781.12), VAH (7790.00), IB high (7791.25) — are
   BELOW the entry.** The machine computed, correctly, that *every profile objective on this day was
   already behind the entry price.* **This is the textbook definition of "no trade location."** It
   was demoted to an R-multiple fallback instead of treated as a veto.
3. **Three `TargetClamp SKIP`s** repeating the same fact.
4. **`STOP_RESOLVER_V1: stop 7767.00 → 7790.75`** — structure wanted a 28-pt stop; the resolver
   compressed it to 4.25. The system was telling itself the structural invalidation was 28 pts away
   and then risked 4.25 — a trade that cannot survive normal noise.
5. **`TARGET_REALISM_V1: t1 7799.12 → 7797.75`** — T1 was clamped to a tick under the session high.
   **Banking T1 required a brand-new session high.** The day high was 7797.00; T1 missed by 0.75.
6. **`release-gate TREND BYPASS`** — the displacement bypass, which is what carried the entry past
   the day-direction machinery.

**No single one of these is a bug.** Together they are a system that generated a complete,
correct Dalton read — *you are buying above value, above the IB, into an unfinished high, with every
objective behind you* — and then executed the opposite.

### 3.3 The trade fired 8 seconds after a backend restart

```
152119:INFO:     Shutting down                     (17:46:23 IDT)
152145:INFO:     Started server process [54050]
152152:INFO:     Application startup complete.
152167:[Gateway] LIVE trade TM id=655: ...          (17:46:32 IDT)
```

The `cross_context` snapshot stored on the trade confirms the systems were **not hydrated**:

```
tpo_system:      bars_processed_today: 0, buffer_size: 0, letter_count: 0,
                 session_high: None, session_low: None, profile_shape: 'NA',
                 opening_type: 'NA', poc_migration: None
five_min_system: buffer_size: 1
footprint_system: bars_processed_today: 0, cot: 0, amt: None, delta: None
```

Yet `five_min_system.last_reasoning_notes` reads
`"DOUBLE_BOTTOM_EE LONG size=half: 3-bar pattern, COT=3047 vs AMT=941, location=far"` — a COT/AMT
comparison sourced from a footprint system reporting `cot: 0, amt: None`. **A live 4-contract order
was placed by a stack with one bar in its buffer, no TPO profile, and no order-flow state.**
This is a safety finding independent of any Dalton consideration.

---

## 4. Dalton's doctrine for exactly this day

### 4.1 The Initial Balance is a *base*, and its width sets your expectations

Direct quote, *Mind Over Markets* (1st ed., 1990), Dalton / Jones / Dalton:

> "Think of the initial balance as a base for the day's trading. The purpose of a base is to provide
> support for something, as the base of a lamp keeps the lamp from tipping over. The narrower the
> base, the easier it is to knock the lamp over. … **If the initial balance is narrow, the odds are
> greater that the base will be upset and range extension will occur. Days that establish a wider
> base provide more support and the initial balance is more likely to maintain the extremes for the
> day.**"
> — via [Time▾Price▴ Research, "Six Types of Market Days: Mind Over Markets"](https://time-price-research-astrofin.blogspot.com/2023/03/six-types-of-market-days-mind-over.html)

**Implication for entry patience** — this is the single most direct answer to the "first hour"
question in the brief:

| IB | Dalton's expectation | Correct posture |
|---|---|---|
| **Narrow** | base will be upset → extension / trend / double-distribution likely | **Be patient inside the IB; do not fade the edges. Wait for the break, then trade the pullback to it.** |
| **Wide** | IB likely holds the day's extremes → rotation | **Fade the edges; targets are the opposite VA / IB edge.** |

Today's IB is 20.25 = **0.24 × the 84-pt daily ATR** — narrow in every sense, and the narrowest of
the last ten sessions. The doctrine-correct posture today was therefore **breakout-and-retrace, not
edge-fading** — which is the exact opposite of the `Normal` (`fade_edges: true`) profile our machine
assigned (§4.3).

### 4.2 The six day types — where today sits

From the same primary source:

- **Trend Day** — open marks one extreme, close the other; widest ranges; *"it is costly to trade
  against the move or to recognise the pattern too late."*
- **Double-Distribution Trend Day** — *"begins quietly, with indecision and a narrow initial balance
  during the first one to two hours. A narrow initial balance is prone to breakout, allowing price to
  auction beyond the range toward new value."*
- **Typical / Normal Day** — *"begins with a wide initial balance … pushes price far enough from
  value to attract responsive participants, who drive it back … Because the initial balance is wide,
  it generally serves as a firm base that is unlikely to be broken."*
- **Expanded Typical Day (= Normal Variation)** — *"the opening move is weaker … the initial balance
  is wider than that of a Double-Distribution Trend Day yet narrower than that of a Typical Day,
  leaving it **vulnerable to violation later in the session**. Eventually, one of the extremes is
  broken, usually through **initiative** buying or selling, and price extends in the direction of the
  breakout … Once an extreme gives way, price expands to establish a new area of value."*
- **Trading Range Day** — both sides auctioned repeatedly; responsive sellers at the top, responsive
  buyers at the bottom; *"providing clear opportunities for timing entries."*
- **Non-Trend / Sideways Day** — narrow IB, no initiative ever develops, *"the risk-reward ratio for
  day traders is low."*

Frequency and target guidance, [FTMO, "Market Profile: Types of Opens and the Anatomy of a Trading
Day"](https://ftmo.com/en/blog/market-profile-types-of-opens-and-the-anatomy-of-a-trading-day/):

> "**Normal Variation Day (NVD)** … The market forms an **average IB** during the first hour. Then,
> in the **third half-hour (TPO "C"), it breaks this range on one side**. **It doesn't test the other
> side of the IB again**, and the market creates a nice drive in one direction. **The target (Take
> Profit) after the breakout is usually 1.5 to 2 times the size of the IB.**"

**Verdict on 2026-08-10.** Everything through 11:00 ET matched NVD precisely — average-to-narrow IB,
one-sided break in period C. Then it failed the defining condition: it **did** come back through the
IB, all the way to 7778 (13 pts back inside), so the extension was **not accepted**. Combined with
`high_quality = NEUTRAL` (no excess at 7797 — an unfinished auction) and a total range of 26 pts on
an 84-pt ATR, today is best labelled:

> **A Normal Variation / Expanded Typical day whose extension failed — decaying toward a
> Typical / Trading-Range day, inside an intact multi-day upward auction.**

Shape: a wide A-period with a buying tail at 7771, value building in the middle band 7779.25–7790.50,
and thin single prints above 7791.50 — a **D / b hybrid leaning D (bell)**, *not* a P (trend) shape.
Our own classifier's label of `Variation / "1-sided extension = Expanded Typical"` is **right**; its
sibling label of `Normal` (via the EXTREME-IB path) is wrong for the wrong reason (§4.3).

### 4.3 Opening type: open-auction-in-range is the lowest-conviction open

[FTMO](https://ftmo.com/en/blog/market-profile-types-of-opens-and-the-anatomy-of-a-trading-day/):

> "**Open Auction:** A calm start. The market has no clear direction and moves just above and below
> the opening price. This usually indicates a **normal, rotational day**, where the opening and
> closing prices of the day tend to be at a very similar level."

And on where the open sits relative to prior value —
[The Nature of Markets / Ratul Bhattacharya, "Opening Types, Open Range Strategy"](https://medium.com/@bhattacharya.ratul/opening-types-open-range-strategy-and-practical-applications-153df89e2bf5):

> "If opening price is **within** yesterday's Value/Range, there are higher odds of a more
> **rotational/balancing day with a smaller range**. If opening price is **outside** yesterday's
> Value/Range, there are higher odds of a more **directional/trending day with a larger range**."

Today opened at 7773.00 — inside yesterday's value (7762.50–7781.25) **and** inside the 7-day
composite value. Range came in at 26 pts vs an 84-pt ATR. **The doctrine's prediction was exactly
right**, and our radar had `opening_type = OPEN_AUCTION_IN` correct from the open.

The corollary that matters commercially: **on an open-auction-in day, the expected range is small,
so the position-sizing and the profit expectation should both be reduced from the outset.** We do
not do this — `config/daytype_playbook.yaml:129-136` maps `OPEN_AUCTION_IN → NO_EDGE` for the
*opening_stance* display, and `opening_type_gate` holds fires only until IB lock; after that the
opening type stops influencing anything, and **nothing maps opening type to contract count.**

### 4.4 Where Dalton *enters* on a day that opens in range and extends one-sided

Three distinct entries, in his order of preference:

**(a) Responsive, at the value/range edge, against a finished auction.**
The Trading-Range/Typical mechanic: *"Responsive sellers enter shorts near the top of the range …
while responsive buyers enter longs near the bottom"* (Mind Over Markets, via
[Time▾Price▴](https://time-price-research-astrofin.blogspot.com/2023/03/six-types-of-market-days-mind-over.html)).
The precondition is that the extreme is **finished** — i.e. shows **excess** (a tail). Today the
**low at 7771 had 6.75 pts of excess and one touch**; the high at 7797 had 1.50 pts and no excess.
So on 2026-08-10 there was a doctrine-sanctioned **responsive long near 7771–7778** and **no**
doctrine-sanctioned responsive short at 7797.

**(b) Initiative, on the first *successful* range extension.**
[WindoTrader Market Profile Glossary](https://www.windotrader.com/market-profile/market-profile-glossary-index/):
range extension *"tends to indicate that the longer time-frame trader has entered the market. **The
tactic is to trade with the first successful range extension.**"* The load-bearing word is
**successful** — acceptance, not merely a print beyond the IB. Acceptance = time and volume built
beyond the edge, typically a TPO period closing outside. Today's extension printed 5.75 pts beyond
IBH and produced only ~1.5 periods of trade up there before folding back — **it was never
successful**, so the initiative long was never validated.

**(c) The pullback — and this is the answer to "does he buy the pullback or go with the break".**
Same glossary source: *"When in a strong directional environment, **enter pullbacks into prior single
prints / minor consolidations**."* And *"a responsive test that **fails to get back into prior
value** serves as a trigger."* The mechanically-stated version for a day that has broken its IB:
*"traders can buy pullbacks by entering on any retracement to value area or POC"*, and *"if there's a
break above Initial Balance high with no return to IB"* the trend read is confirmed
([DayTradingToolkit / market-profile trend-day recognition](https://daytradingtoolkit.com/strategies/the-ultimate-trend-following-strategy-guide)).

So the answer is unambiguous: **Dalton goes with the break only after it is accepted, and he prefers
to enter on the first pullback to the broken edge / the extension's origin / the POC — not on the
break itself, and never at the extension's extreme.**

On today's chart, that pullback entry was **the retest of the broken IB high 7791.25 as support**,
or a deeper retrace to POC 7783.25. The market printed 7791.25 as a level repeatedly from 11:15
onward. **We have no pattern that fires on it** (§5.10).

### 4.5 Where Dalton says NOT to enter

- **Trade location is the whole game.** Dalton's stated principle: the POC is *"the 'fairest' price
  at which to trade, with the principle that **if you're buying above or selling below the POC, the
  odds aren't typically in your favour**"*
  ([summary of Dalton's trade-location teaching](https://www.windotrader.com/market-profile/market-profile-glossary-index/)).
  Trade #655 bought **11.75 pts above the POC**.
- **Never chase the extension's extreme.** The whole point of the NVD/Expanded-Typical structure is
  that after an extreme gives way, price *"expands to establish a new area of value"* — you want to
  be positioned for the establishment of that new value, which means buying the retrace **into** it,
  not the print at its edge.
- **Do not look for counter-trend trades on a trend day** (FTMO, day type 3). Conversely, on a
  rotational day, do not take with-trend continuations at the range edge.
- **Non-trend day: "do not trade at all."** (FTMO, day type 6.) Dalton is explicit that **no-trade is
  a valid, and sometimes the only correct, output.**

### 4.6 Targets and management

| Technique | Dalton's rule | Source |
|---|---|---|
| **NVD measured move** | after the IB break, TP = **1.5–2 × IB width** projected from the broken edge | [FTMO](https://ftmo.com/en/blog/market-profile-types-of-opens-and-the-anatomy-of-a-trading-day/) |
| **Value-area edges** | on rotational days, target the **opposite VA edge**; POC is the first magnet | Mind Over Markets |
| **80% rule** | *"there is an 80% chance when a market opens (or trades) above or below the value area, and then trades in the value area for **two consecutive half-hour periods**, then the market has an 80% chance of **filling the entire value area**"* — first published in *The Profile Reports* (Dalton Capital Management, 1987–1991) | [mypivots](https://www.mypivots.com/dictionary/definition/25/80-rule), [Marketcalls](https://www.marketcalls.in/market-profile/market-profile-how-to-play-80-percentage-rule.html), [FTMO](https://ftmo.com/en/blog/market-profile-master-the-80-trading-strategy-hidden-magnets/) |
| **Single prints** | un-revisited singles are the *"unfinished business"* magnets; on a failed extension they get filled in, on an accepted one they act as support | [WindoTrader glossary](https://www.windotrader.com/market-profile/market-profile-glossary-index/) |
| **Excess** | a tail marks a **finished** auction — it is the structural invalidation level. No excess = unfinished = expect a revisit | Mind Over Markets |

Applied to today, had the 09:55 responsive long at ~7778 been taken:
stop below the **7771 excess** (7770.75, ~7.25 pts); T1 = POC 7783.25; T2 = VAH/IBH 7790.50–7791.25;
T3 = IB measured move `7791.25 + 0.5 × 20.25 = 7801.4` (half-extension) or `+1×IB = 7811.5`.
Actual day high 7797.00 → **T1 and T2 both filled comfortably; T3 partial.** That is the trade the
day offered, and it is the trade our `structural_targets` module already knows how to construct — it
correctly produced 7781.12 / 7790.00 / 7791.25 as the objectives. It simply had them *behind* the
entry, because the entry was 17 pts too high.

### 4.7 "It grinds up and never pulls back" — what does Dalton actually say?

This is the brief's sharpest question, and the answer has three parts.

**(i) First, check whether the premise is true.** Today it was **not**. Between 09:50 and 10:45 there
were four separate 3–6 pt retracements (10:20 bar low 7784.75 after a 7790.50 high; 10:35 low
7788.25; and the 10:50 bar gave back 11.75 pts). The market gave repeated entries — our guard simply
measured them against a stale reference. "No pullbacks" was a **measurement artefact**, not a market
condition. This is worth stating plainly because it changes the remedy: the fix is not a new
"chase-anyway" mode, it is a correct yardstick.

**(ii) When the premise IS true — a real trend day — Dalton's answer is that you must accept worse
entry for better direction, and you enter on *shallow* retracements against a moving reference.**
The recognition rule is a very narrow IB plus an aggressive break by the third half-hour, with
*"half-hour blocks (TPOs) barely overlapping"* and price never returning to the opening range
([FTMO](https://ftmo.com/en/blog/market-profile-types-of-opens-and-the-anatomy-of-a-trading-day/)).
The entry rule is *"enter pullbacks into prior single prints / minor consolidations"* — i.e. into the
**thin** areas the drive left behind, which on a real trend day are only 1–3 ticks deep, with the
prior half-hour's low as the invalidation. Note that this is *conditional on having positively
identified a trend day* — it is not a general licence.

**(iii) When the day is NOT a trend day and offers no location — "no trade" IS the correct answer.**
Dalton is unambiguous on non-trend days (*"do not trade at all"*), and the trade-location principle
means a day where price sits above the POC with all objectives below is simply not a buyable day.
**On 2026-08-10 the correct output after ~10:30 ET was: no new longs; wait for either (a) a pullback
to 7791.25/7783.25 with a rejection, or (b) acceptance above 7797.** Neither occurred before the
system fired at 7795.

So: our chase-guard's *intent* was correct nine times out of eleven today. It was wrong exactly twice
— and it was wrong because of its reference, not its philosophy.

---

## 5. Mapping the doctrine onto our system

Legend: **✅ implemented & live** · **🟡 partial / present but not wired to decisions** ·
**🔴 not implemented** · **🐛 implemented but demonstrably wrong**

### 5.1 IB width → expectation & patience — 🐛 **BROKEN (verified)**

`backend/v9/systems/day_type/detector.py:56-80` `classify_ib_width_atr(ib_range_pt, atr_daily)`
classifies IB/ATR into NARROW <0.5 / MEDIUM <1.0 / WIDE <1.5 / EXTREME ≥1.5. Flag `S1_IB_WIDTH_ATR`
is **ON**.

The `atr_daily` it receives is produced at
`backend/v9/systems/day_type/state_machine.py:337-344`:

```python
bar_range = bar.high - bar.low
if bar_range > 0:
    self._bar_ranges.append(bar_range)
    if len(self._bar_ranges) > 14:
        self._bar_ranges = self._bar_ranges[-14:]
    if len(self._bar_ranges) >= 5:
        self._last_atr_daily = sum(self._bar_ranges) / len(self._bar_ranges)
```

`bar` here is a **5-minute** bar. So `_last_atr_daily` is the **mean 5-minute bar range**, passed to a
function whose thresholds are defined against a **daily** ATR.

**Verified on today's data:**

```
mean 5-min bar range over IB (= what the code calls atr_daily): 6.396
IB width 20.25 / 6.396 = 3.17  -> tier: EXTREME (>1.5)
last 10 RTH day ranges: [68.8, 139.0, 79.8, 113.5, 95.8, 99.2, 74.5, 44.2, 43.5, 26.0]
true daily ATR(9) = 84.25  =>  20.25 / 84.25 = 0.24  -> tier: NARROW (<0.5)
```

The ratio is inflated **~13×**. Since a 5-min mean range will essentially never exceed ⅔ of the IB,
**`IBWidth.EXTREME` is the near-constant output** and NARROW is unreachable in practice.

**Consequence — this is not cosmetic.** `decision_matrix.py:31-70` keys on
`(OpeningType × IBWidth)`:

| Cell | Result |
|---|---|
| `OPEN_AUCTION_IN × EXTREME` (what fired) | **`DayType.Normal`** |
| `OPEN_AUCTION_IN × NARROW` (correct) | **`DayType.Nontrend`** |

And `config/daytype_playbook.yaml`:
- `Normal` → `fade_edges: true`, bias `VAL→LONG · VAH→SHORT`, **`DBDT: FULL`**
- `Nontrend` → **everything `SKIP`** (and `NONTREND_DISABLE_ALL=1` is in the live env boot line)

**So the sizing of the day's only live trade — 4 contracts on a `DBDT` pattern — traces directly to
this bug.** With a correct IB-width tier the day would have been `Nontrend` and the trade would not
have been taken at all. It also explains the §1.5 contradiction: the state-machine path (matrix,
EXTREME) said `Normal` while the feature-based reclassifier (`"1-sided extension = Expanded
Typical"`) said `Variation`.

Note there are **three** coexisting IB-width classifiers: point-based in
`tpo/tpo_system.py:485-491` and duplicated in `api/v9/key_levels_routes.py:50-58` (15/25 pt,
returned `MEDIUM` today — correct-ish by accident), point-based `detector.classify_ib_width` used by
`day_type_seed.py:88` and `backend/main.py:181`, and the ATR one above. They can and today **did**
disagree.

**Patience** is modulated by day type, not IB width: `structural_targets.py` sets
`time_stop_minutes` 30 (Normal) / 60 (Variation) / 90 (Trend_DD) / none (Trend_Normal). Dalton's
narrow-IB → be-patient rule is **🔴 not implemented**.

### 5.2 `extreme_chase_guard` — ✅ live, 🐛 wrong reference

`backend/v9/gateway/trading_gateway.py:1485-1620`, flag `EXTREME_CHASE_GUARD_V1` **ON**.
`EXTREME_MIN_DIST_PTS=6.0`, `PULLBACK_MIN_PTS=3.0`, `CHASE_MIN_SESSION_BARS=6`. Applies to
`_pattern_family == "CONT"` only (`daytype_position_gate.py:33-41`) — which is why the sys-2
`DOUBLE_BOTTOM_EE_LONG` (family REV) was exempt while every sys-4 `ZLR LONG` at the same price was
blocked.

Three defects visible in today's data:

1. **The threshold is an absolute 6.0 pts, unrelated to the day's structure.** On today's 20.25-pt IB
   / 26-pt range, 6.0 pts is 23% of the entire session range — enormous. On 07-29 (139-pt range) the
   same 6.0 was trivial. The playbook's *own* Variation chase check already does this better:
   `max(6.0, CHASE_MIN_DIST_IB_FRAC × ib_width)` (`daytype_playbook.py:319-327`) — but it applies
   only to `REACTIVE`/`HNS`, and it scales the wrong way (it raises, never lowers, the bar).
2. **The maturity bypass is a bar count, not a structural test.** At 09:55 the "session extreme" was
   25 minutes old and 12.25 pts below the eventual IB high. `CHASE_MIN_SESSION_BARS=6` had expired
   one bar earlier.
3. **The family scope is asymmetric in the dangerous direction.** REV patterns — precisely the ones
   that fire *at* extremes — are entirely exempt. Today that exemption produced the only fill, at the
   worst price.

### 5.3 Structural targets & the wrong-side signal — ✅ computed, 🔴 not a veto

`backend/v9/systems/structural_targets.py`, flag `DAYTYPE_TARGETS_STRUCTURAL` **ON**, wired at
`trading_gateway.py:1986-2028`. It correctly implements the Dalton objective ladder including the
**IB measured move** (`_resolve_trend_dd`: C2 = `ibh + 2×ib_width`; `_resolve_variation`: C1 =
`ibh ± 0.5×ib_width`, C3 = VA edge).

**The gap:** when a computed objective lands on the wrong side of the entry, the module logs
`→ R-fallback` and substitutes an R-multiple. `TargetClamp` then logs `SKIP` and does the same. There
is **no path where "all N structural objectives are behind the entry" blocks the trade.** Today that
condition was true for **all three** objectives and the trade proceeded.

This is the highest-value, lowest-risk gap in the entire audit: the signal already exists, is already
computed, is already logged, and is already correct.

### 5.4 Value area as entry location — ✅ live but scoped too narrowly

- `DAYTYPE_LOCATION_GATE` **ON** (`location_gate.py`, gateway `:1163`, block at `:1234`) — REV fades
  allowed only at the correct value edge, with a v2 **probe requirement** (a 5-min bar must pierce
  the edge and close back inside).
- `daytype_playbook._resolve_location` (`:353-372`) — but `_RESPONSIVE_REV = {"REACTIVE", "HNS"}`
  only. `DBDT` (double bottom/top) is **not** in that set, so the double-bottom family never faces
  the VAH/VAL location test in the playbook.
- `REACTIVE_LOCATION_GATE` **OFF** (Michael 07-02, standing).
- The location gate did fire correctly at 11:10 ET: `"REACTIVE responsive SHORT not at VAH
  (near_val) on Variation"` — ✅.
- The `LEG_RIDE_V1` exemption (`trading_gateway.py:1163+`, "leg-ride exemption (live leg agrees)")
  can void the location gate whenever `leg == direction`; radar showed `leg: UP` all session.

### 5.5 Excess / tails / single prints — 🟡 computed, minimally consumed

- `extremes_quality.py:53` `classify_session_extremes` → EXCESS / POOR / NEUTRAL, thresholds
  tail ≥2.0 pt or ≥1.5× body + no revisit in 3 bars. **Working well** — it called today's low EXCESS
  and today's high NEUTRAL, both correct.
- **Consumed only for exit timing**: `target_approach_realize.py:110-131`
  (`EXTREMES_AWARE_REALIZE_V1` **ON**) — POOR suppresses realize, EXCESS realizes after 1 bar.
- **As an entry location:** only behind `EXCESS_COUNTER_ENTRY_V1`, which is **OFF**.
- **As a stop reference: 🔴 not implemented.** Nothing in `stop_anchors/` or
  `config/stop_anchors.yaml` references excess or tails. Today the doctrine-correct stop for a
  responsive long was "below the 7771 excess"; `STOP_RESOLVER_V1` instead produced a band-based 4.25.
- **Single prints:** computed at `tpo/levels.py:134-141` and returned by
  `multiday_profile.session_tpo_profile`, **zero consumers**. `config/daytype_playbook.yaml:100`
  lists `single_print` as a `Trend_DD` ref_point but nothing resolves it. Today's two single-print
  clusters (7771–7777.75 and 7791.50–7797) are exactly the Dalton pullback-entry zones and the
  system cannot see them.

### 5.6 The 80% rule — 🟡 read-only, and it deviates from the canonical rule

`backend/v9/systems/day_type/day_context_extras.py:93-119` `va_rule_read()`. Two deviations:
1. It counts **2 consecutive 5-min bar closes**, not **two consecutive 30-minute periods**.
2. It requires the session to have **opened outside** prior value; the canonical rule fires on
   re-entry from *either* an open outside value **or a trade outside value** during the session.

Consumer: `classifier_core.py:225-227` sets `feat["va_rule"]` with an in-code comment
*"emitted for briefing/UI; no gate yet."* No entry, target, or veto reads it.

Today the rule would not have fired (open was in value) — but the *related* structure did: price
extended above value, was rejected, and re-entered. Under the canonical formulation that is an 80%
signal to traverse to **VAL (7779.25 / 7775.50)** — which the market then did, printing 7778.00 at
11:35. **A correctly-specified 80% rule would have produced the correct short-side read at 10:50
ET**, at precisely the moment we were long from 7795.

### 5.7 Multi-day balance / value migration — 🟡 computed, gate is OFF

`multiday_profile.py` produces `value_migration` (UP, +33.26), `va_overlap_pct` (0.01),
`open_location` (`in_value`). Consumers:
- `market_context.py:188-217` derives `multiday_veto_dir` (SHORT when migration=UP).
- `trading_gateway.py:1407-1434` `MULTIDAY_VETO_V1` — **OFF**. This is the only decision gate that
  reads it.
- `S1_VALUE_MIGRATION_V1` **ON** (`daytype_classifier.py:441`) vetoes Trend promotion on high
  overlap — but it uses the **one-day-back** `day_type/value_migration.py`, not the 7-day module.
- `balance_imbalance_toggle.py:82-93` — overlap >60 = balance, <30 = imbalance.

So the strongest single piece of context available today (**1% VA overlap + 33 pt/day upward
migration = OTF buyer firmly in control**) reached **no** live decision. Note this cuts *for* longs
today, so enabling `MULTIDAY_VETO_V1` would not by itself have prevented #655 — but it is the
context that makes the 09:55 responsive long a high-conviction trade rather than a coin flip.

### 5.8 Opening type — ✅ classified, 🟡 influence expires at IB lock

`opening_detector_v2.py` → `OPENING_TYPE_GATE` **ON** (`opening_type_gate.py:25-110`) blocks
counter-drive entries from RTH open until IB lock, then goes **inert**. `OPENING_TYPE_SEEDS_S1_V1`
**ON** seeds day bias in the first 15 min. `decision_matrix` uses it (poisoned by §5.1).
**No opening-type → sizing or → expected-range mapping exists.** Dalton's "open in range ⇒ smaller
range ⇒ smaller expectations" is 🔴 not implemented.

### 5.9 Range-extension acceptance — 🟡 detection only, no acceptance test

`behavior_phase/phase_detector.py:79-96` (`ib_extended_up/down/both_sides`) and
`relative_features.py:262+` detect that price *printed* beyond the IB.
`S1_RECLASS_REQUIRES_IB_EXT_V1` **ON** requires a real IB break before reclassifying to
Variation/Trend. But **nothing tests whether the extension was *accepted*** — no "did a 30-min period
close beyond the edge", no "did volume/TPO build out there", no "did price fail back inside the IB
within N periods". Today's extension printed and failed; the system's day label stayed `Variation`
with rising confidence (0.38 → 0.67) throughout the failure.

### 5.10 Pullback / retest entries — 🔴 **the biggest structural gap**

There is **no entry pattern anywhere in the codebase that fires on a retest of a profile level.**
What exists:
- `HIGHER_LOW_SECOND_TEST_V1` (`five_min/patterns/higher_low_second_test.py:44`) — **OFF**. Pure
  swing structure (push ≥8 pt → pullback L1 → recovery ≥33% → second dip above L1). No POC / VAH /
  IB-edge reference.
- `OPENING_FIRE_V1` **ON** (`five_min_system.py:1159`) — a genuine pullback entry, but again
  swing-relative (33% retrace of the opening excursion), not level-relative.
- `LEG_RIDE_V1` **ON** — a **gate exemption**, not an entry trigger.
- `ZLR` — a retest of the CCI zero line, an indicator, not a profile level.
- `config/daytype_playbook.yaml:74` literally states the Variation bias as
  *"enter on pullback to broken edge"* with `ref_points: [broken_IB_edge, ...]` — **and nothing in
  the code computes or fires on `broken_IB_edge`.** The doctrine is in our config as prose and
  nowhere in our execution path.
- Already flagged as open in `docs/handoff/CC_S68_DAYTYPE_LOCATION_PLAN_2026-06-21.md:25` and
  `docs/reports/DALTON_GAP_AUDIT_2026-08-02.md:173`.

**This is the pattern today's chart called for and we did not have.** After the 10:45 extension
failed, the market offered the broken-IB-edge retest at 7791.25 repeatedly from 11:15 onward.

### 5.11 Summary table

| # | Dalton technique | Status | Where |
|---|---|---|---|
| 1 | IB as base; narrow ⇒ extension likely | 🐛 broken | `state_machine.py:344` + `detector.py:56` |
| 2 | Narrow IB ⇒ patience, don't fade edges | 🔴 | — |
| 3 | Six day types | ✅ | `decision_matrix.py`, `daytype_classifier.py` |
| 4 | Opening type classification | ✅ | `opening_detector_v2.py` |
| 5 | Opening type ⇒ range expectation / sizing | 🔴 | — |
| 6 | Responsive entry at value edge | ✅ | `location_gate.py` (REACTIVE/HNS only) |
| 7 | Initiative on **accepted** range extension | 🟡 detection only | `phase_detector.py:79` |
| 8 | **Pullback to broken edge / POC / singles** | 🔴 | config prose only |
| 9 | Don't chase the extreme | ✅ intent, 🐛 reference | `trading_gateway.py:1485` |
| 10 | Trade location: not above POC | 🟡 | `reactive_location_gate` (**OFF**) |
| 11 | Targets: VA edges | ✅ | `structural_targets.py` |
| 12 | Targets: IB measured move (1.5–2×) | ✅ | `structural_targets.py:317-388` |
| 13 | **All objectives behind entry ⇒ no trade** | 🔴 | logged, never enforced |
| 14 | 80% rule | 🟡 wrong spec, no gate | `day_context_extras.py:93` |
| 15 | Excess as invalidation / stop anchor | 🔴 | `stop_anchors/` has nothing |
| 16 | Single prints as entry zones | 🔴 | computed, zero consumers |
| 17 | Multi-day value migration ⇒ direction | 🟡 gate OFF | `MULTIDAY_VETO_V1` |
| 18 | "No trade" as a valid output | 🟡 | `Nontrend` exists but is unreachable (§5.1) |

---

## 6. Ranked recommendations — "what to add for days like today"

Ranked by (expected value × confidence) ÷ risk. **All are proposals — nothing below was implemented,
and items marked 🔒 change the trading-risk surface and need Michael's sign-off before enabling.**

### #1 — `STRUCTURAL_TARGETS_WRONG_SIDE_VETO_V1` 🔒
**Change:** in `structural_targets.py`, when **all** resolved objectives (c1, c2, c3) land on the
wrong side of the entry, return a `no_location` verdict; in `trading_gateway.py:1986-2028` treat that
verdict as `blocked_by="no_structural_location"` instead of falling back to R-multiples.
**Why it's #1:** the signal is already computed, already correct, already logged, and cost us the
only live trade of the day. Zero new math. It encodes Dalton's single most central rule (trade
location) using our own existing profile ladder.
**Expected value:** would have prevented #655 (−$63.75) outright. Grep of the log pattern
`on wrong side of` across history will size this precisely — recommend that as the first backtest.
**Risk:** low. It can only *remove* trades, and only those where the system already admitted it had
no objective.

### #2 — Fix `_last_atr_daily` (rename + feed a real daily ATR)
**Change:** `state_machine.py:337-344` — feed `classify_ib_width_atr` a **daily** ATR (14-session RTH
true range), not the mean 5-min bar range. Keep `_DEFAULT_ATR_MES = 20.0` only as a cold-start
fallback and rename the variable to match its meaning. Add a regression test asserting
`IB 20.25 / ATR 84.25 → NARROW`.
**Why:** it is a verified, quantified bug (13× error) that makes `IBWidth.EXTREME` the near-constant
input to the day-type decision matrix, which in turn drives `fade_edges`, per-pattern sizing, and
time-stops. It is the root cause of today's `Normal`-vs-`Variation` split label and of the 4-contract
sizing on #655.
**Caution:** the *correct* value flips `OPEN_AUCTION_IN` days from `Normal` to `Nontrend`, and
`NONTREND_DISABLE_ALL=1` is live — so this fix will **materially reduce trade count**. That is the
intended Dalton behaviour, but it is a risk-surface change: ship the fix behind a flag, run it in
shadow for a week against the day-type labels, then enable with sign-off. 🔒
**Bonus:** collapse the three IB-width classifiers to one while you're in there.

### #3 — `RE_PULLBACK_ENTRY_V1` — the missing Dalton entry 🔒
**Change:** a new five_min pattern. Trigger: (a) IB broken by ≥ `0.15 × ib_width` in period C or
later; (b) price returns to within `tol` of the **broken IB edge** (or POC, or the nearest un-revisited
single-print cluster); (c) a 5-min rejection bar closes back **with** the break direction.
Stop = beyond the retest low/high (or beyond the excess if one exists); C1 = `edge ± 0.5×IB`,
C2 = `edge ± 1×IB`, C3 = `edge ± 2×IB` — all of which `structural_targets` already produces.
**Why:** this is the entry Dalton actually takes on a one-sided-extension day, it is already written
as prose in `config/daytype_playbook.yaml:74` (`"enter on pullback to broken edge"`,
`ref_points: [broken_IB_edge]`), and it has been an open item since 06-21. It converts the
chase-guard from "blocks everything late in a move" into "blocks the chase **and** routes you to the
correct entry".
**Expected value:** on today's chart it would have offered a long at ~7791.25 from 11:15 onward with
objectives at 7801/7811. Build it flag-OFF, sim-verify, then enable.

### #4 — Make `extreme_chase_guard` structure-relative and symmetric
**Change:** three edits in `trading_gateway.py:1485-1620` —
(a) threshold `max(4.0, 0.30 × ib_width)` instead of a flat 6.0 (today: 6.08 — barely different; on
07-29 it would have been 18.8, which is the point);
(b) replace `CHASE_MIN_SESSION_BARS` with a structural maturity test — the guard is inert until the
IB is locked, and thereafter measures distance from the **IB edge**, not from a session extreme that
may be minutes old;
(c) extend the guard to REV patterns firing *with* the prevailing leg (today's `DBDT` long at 7795
was the exact case the guard exists to stop, and it was exempt by family).
**Expected value:** (a)+(b) unblock the 09:55 longs (+19.25 pts of the day's move); (c) blocks #655.
**Risk:** moderate — (c) widens what the guard can veto. Ship (a) and (b) first.

### #5 — Canonical 80% rule, wired as a target-side signal
**Change:** in `day_context_extras.py:93-119`, count **two consecutive 30-minute TPO periods** rather
than two 5-min closes, and fire on re-entry after *any* excursion outside value (not only an outside
open). Then wire `feat["va_rule"]` into `structural_targets` as a target-side override: when active,
C2/C3 become the far VA edge.
**Expected value:** today it would have flagged the traverse to VAL 7779.25 around 10:50–11:20 — the
single largest clean move available in the back half of the session, and the exact opposite of the
position we held.

### #6 — Excess as a stop anchor
**Change:** add an `excess` anchor to `stop_anchors/` (and `config/stop_anchors.yaml`) that, when
`extremes_quality` reports EXCESS on the relevant side and it is within a sane distance, places the
stop beyond the tail rather than inside a band. `extremes_quality.py` already produces the input and
was accurate today (7771 EXCESS, 6.75 pt tail).
**Expected value:** a responsive long from 7778 with a stop at 7770.75 survives the entire session;
the same trade with `STOP_RESOLVER_V1`'s 4.25-pt band stop (7773.75) is stopped out on the 09:50 wick.

### #7 — Consume the single-print clusters
`multiday_profile.session_tpo_profile` and `tpo/levels.py:134-141` both already return them; nothing
reads them. Expose them on `/api/v9/context/radar` and use them as the reference-point set for #3.
Low cost, unlocks the Dalton "enter pullbacks into prior single prints" entry properly.

### #8 — Opening type ⇒ expected range ⇒ sizing 🔒
`OPEN_AUCTION_IN` ⇒ expected range materially below ATR ⇒ reduce contracts and tighten targets from
the open. Today: 26-pt range vs 84-pt ATR, and we sized 4 contracts. Needs a ruling; the empirical
work (open type vs realised range) should come first.

### #9 — Warm-up guard on live fires (**not a Dalton item — a safety item**)
Trade #655 was placed **8 seconds after a backend restart** with `tpo_system.bars_processed_today=0`,
`five_min_system.buffer_size=1`, `profile_shape='NA'`, `footprint cot=0/amt=None`. Recommend a hard
precondition on any **live** `PLACE`: TPO hydrated (`bars_processed_today ≥ 12` in RTH) **and**
`five_min_system.buffer_size ≥ N` **and** a minimum uptime since `Application startup complete`.
This is arguably #1 by severity and is listed here only because it is orthogonal to the research
brief. **Recommend raising it to Michael separately and immediately.**

---

## 7. Raw verification (Rule 5)

All commands run via Desktop Commander on the trading MacBook, 2026-08-10 18:45–18:58 IDT.

**Bars / IB / range** — `env BRIDGE_TOKEN=x DATABASE_URL=postgresql://localhost/mems26 python3` over
`backend.v9.db.read.read_all`, table `v9_bars_5min_woodies`, filter
`(ts AT TIME ZONE 'America/New_York')::date = current_date`, RTH `>= 09:30`:
```
RTH bars 28  first 2026-08-10 09:30:00  last 2026-08-10 11:45:00
IB bars 12  IBH 7791.25  IBL 7771.0  width 20.25
RTH open 7773.0  high 7797.0  low 7771.0  range 26.0
RE up 5.75  RE dn 0.0
```

**Multi-day context** — `curl -s http://localhost:8000/api/v9/context/multiday`:
```
composite   = {"range_high":7820.25,"range_low":7427.5,"vah":7788.75,"val":7467.25,"poc":7736.25,"n_days":6}
value_migration = {"direction":"UP","slope":33.26,"n":5}
va_overlap_pct  = 0.01
open_location   = in_value
today = {"poc":7783.25,"vah":7790.5,"val":7779.25,"high":7797.0,"low":7771.0,"n_periods":5}
dates = ["2026-07-31","2026-08-03","2026-08-04","2026-08-05","2026-08-06","2026-08-07","2026-08-09"]
```

**Radar** — `curl -s http://localhost:8000/api/v9/context/radar`:
```
day_type Variation conf 0.67 stage B2 leg UP
opening_type OPEN_AUCTION_IN   lock_state PENDING   regime IMBALANCE 0.8
extremes {'high_quality':'NEUTRAL','low_quality':'EXCESS','session_high':7797.0,'session_low':7771.0,
          'high_tail_pts':1.5,'low_tail_pts':6.75,'high_touches':1,'low_touches':1}
balance7 {'migration':'UP','migration_slope':33.26,'overlap':0.01,'open_location':'in_value','n_days':6}
trading  {'armed':1,'is_sim':0,'sendorders':1,'position_qty':0,'contracts_allowed':8,'stale':False}
```

**ATR bug** — same python harness:
```
mean 5-min bar range over IB (= what code calls atr_daily): 6.396
IB width 20.25 / that = 3.17 -> tier: EXTREME (>1.5)
last 10 RTH day ranges: [68.8, 139.0, 79.8, 113.5, 95.8, 99.2, 74.5, 44.2, 43.5, 26.0]
true daily ATR(9) = 84.25 => IB/ATR = 0.24 -> tier: NARROW (<0.5)
```

**Trade #655 / #654** — `SELECT ... FROM v9_trades WHERE id IN (654,655)`:
```
655 firing_system=2 mode=live  state=CLOSED entry=7795.00 stop=7790.75 t1=7797.75 t2=7803.50 t3=7807.75
    exit_price=7790.75 exit_reason=STOP_FILL pnl_usd=-63.75 pnl_r=-0.75 outcome=LOSS
    day_type_at_entry='Normal'  pattern='DOUBLE_BOTTOM_EE_LONG'  contracts=4  confidence=0.75
654 (shadow twin) identical prices, exit_reason=STOP_HIT
cross_context.day_type_machine = {'stage':'B2','day_type':'Normal','ib_width':'EXTREME',
                                  'confidence':0.48,'ib_low_live':7771.0,'ib_high_live':7791.25,
                                  'opening_type':'OPEN_AUCTION_IN'}
cross_context.tpo_system = {'poc':7772.5,'vah':7790.0,'val':7772.5,'ib_width':20.25,'ib_class':'MEDIUM',
                            'bars_processed_today':0,'buffer_size':0,'letter_count':0,
                            'profile_shape':'NA','session_high':None,'session_low':None}
```

**Pre-fire log** — `/tmp/backend.err.log` lines 152119–152168 (quoted verbatim in §3.2/§3.3).

**Gateway decisions** — `~/SierraChart_Data/v9_export/gateway_decisions.jsonl`, 17 rows with
`ts` prefix `2026-08-10` (full table in §2).

**Prior-session IB table** — 10-session aggregate over `v9_bars_5min_woodies`, RTH window
`09:30–16:00 ET` (table in §1.4).

---

## 8. Sources

- James F. Dalton, Eric T. Jones, Robert B. Dalton — *Mind Over Markets* (1st ed., 1990), day-type
  and initial-balance passages quoted via
  [Time▾Price▴ Research — "Six Types of Market Days: Mind Over Markets"](https://time-price-research-astrofin.blogspot.com/2023/03/six-types-of-market-days-mind-over.html)
  · book: [Google Books](https://books.google.com/books/about/Mind_Over_Markets.html?id=L8cuFbjYmkkC)
- James F. Dalton, Robert B. Dalton, Eric T. Jones — *Markets in Profile: Profiting from the Auction
  Process* — [Google Books](https://books.google.com/books/about/Markets_in_Profile.html?id=XXuL4s5X-YMC)
- [FTMO — "Market Profile: Types of Opens and the Anatomy of a Trading Day"](https://ftmo.com/en/blog/market-profile-types-of-opens-and-the-anatomy-of-a-trading-day/)
  (open types; six day types; NVD 1.5–2× IB target)
- [FTMO — "Market Profile: Master the 80% Trading Strategy & Hidden Magnets"](https://ftmo.com/en/blog/market-profile-master-the-80-trading-strategy-hidden-magnets/)
- [mypivots — "80% Rule" definition](https://www.mypivots.com/dictionary/definition/25/80-rule)
  (attributes the rule to *The Profile Reports*, Dalton Capital Management 1987–1991)
- [Marketcalls — "Market Profile: How to Play the 80 Percentage Rule"](https://www.marketcalls.in/market-profile/market-profile-how-to-play-80-percentage-rule.html)
- [WindoTrader — Market Profile Glossary Index](https://www.windotrader.com/market-profile/market-profile-glossary-index/)
  (range extension: *"trade with the first successful range extension"*; *"enter pullbacks into prior
  single prints/minor consolidations"*; POC as the fairest price)
- [Ratul Bhattacharya — "Opening Types, Open Range Strategy and Practical Applications"](https://medium.com/@bhattacharya.ratul/opening-types-open-range-strategy-and-practical-applications-153df89e2bf5)
  (open inside vs outside prior value ⇒ rotational vs directional odds)
- [Marketcalls — "Market Profile: Different Types of Profile Days"](https://www.marketcalls.in/market-profile/market-profile-different-types-of-profile-days.html)
- [Jan Firich (2012) — *Futures Trading Based on Market Profile Day Timeframe Structures*](https://docplayer.net/5290852-Futures-trading-based-on-market-profile-day-timeframe-structures.html)
  (day-type frequency statistics: NVD ≈ 41.8%; normal + trend + NVD ≈ 81.5% of days)

**Internal cross-references:** `docs/reports/DALTON_GAP_AUDIT_2026-08-02.md` (§173 flags the
broken-edge pullback gap) · `docs/handoff/CC_S68_DAYTYPE_LOCATION_PLAN_2026-06-21.md:25` ·
`docs/FLAG_INDEX.md` (**note: stale** — it lists `DAYTYPE_PLAYBOOK` as a no-op via
`DAYTYPE_POSITION_GATE=1`, but `.env:99` sets that to `0`, so the playbook matrix is live; and it
lists `RESPONSIVE_WITH_DAY_TREND_V1` as unreferenced, though it is read at `daytype_playbook.py:225`).
