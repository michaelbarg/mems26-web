# Sierra Studies Configuration — 2026-05-19

**Source:** Michael's manual capture from Sierra Chart `MESM26_FUT_CME` chart.
**Logged:** 2026-05-19 ≈23:24 ET.
**Stored for:** Claude Code's reference when writing the new
`v9_tpo_to_json` routine inside `MES_AI_DataExport.cpp` (see inbox §3 G4
and §4-4).

These four studies are **Sierra native** (not part of our DLL). The DLL
must read their subgraph values via `sc.GetStudyArrayFromChartUsingID()`
to populate `tpo.json` going forward.

---

## Study ID:1 — TPO Value Area Lines · Yesterday (locked)

| Setting | Value | Purpose |
|---|---|---|
| Latency | 0 ms | — |
| Based On | `<Main Price Graph>` | Bound to host chart |
| Chart Region | 1 | Overlay on price |
| Draw Developing Value Area Lines (In:1) | **No** | Locked yesterday's profile only |
| Price Increment in Ticks (In:2) | 1 | 0.25 pt levels (MES) |
| Time Period Type (In:3) | **Days** | One day per period |
| Time Period Length (In:4) | 1 | Single day |
| TPO Letter Time Length (In:6) | 30 min | Standard letter |
| TPO Value Area % (In:8) | **0.7** | 70 % volume = VA |
| **Reference n Periods Back (In:9)** | **1** | **YESTERDAY** |
| One Period Only at End of Chart (In:11) | No | Full history |
| 30-min Letter Sub-period (In:13) | Standard | — |
| Count 2 Levels at a Time (In:14) | No | 1-level granularity |
| Base on Day Session Only (In:15) | No | Globex+RTH |
| Subgraphs of interest | POC (SG[?]), VAH (SG[?]), VAL (SG[?]) | Need to read in DLL |

**DLL action:** read POC/VAH/VAL subgraph values at the latest index. Feed
them into `tpo.json`'s `previous_session.poc/vah/val` block.

---

## Study ID:3 — TPO Value Area Lines · Today (developing)

| Setting | Value | Purpose |
|---|---|---|
| Latency | 64 ms | — |
| Based On | `<Main Price Graph>` | Bound to host chart |
| Chart Region | 1 | Overlay on price |
| Hide Study | **Yes** | UI-hidden, still computed |
| Draw Study Underneath | Yes | Background context |
| Draw Developing Value Area Lines (In:1) | **Yes** | Real-time developing VA |
| Price Increment in Ticks (In:2) | 1 | 0.25 pt levels |
| Time Period Type (In:3) | Days | — |
| Time Period Length (In:4) | 1 | Today only |
| TPO Letter Time Length (In:6) | 30 min | — |
| TPO Value Area % (In:8) | **0.7** | 70 % VA |
| **Reference n Periods Back (In:9)** | **0** | **TODAY** |
| All other inputs | Same as ID:1 | — |
| Subgraphs of interest | POC dev, VAH dev, VAL dev | Need to read in DLL |

**DLL action:** read developing POC/VAH/VAL at the latest index. Feed
into `tpo.json`'s `session.poc/vah/val` block. Also use the same study's
session high/low to fill `session.session_high` and `session.session_low`.

---

## Study ID:6 — Initial Balance

| Setting | Value | Purpose |
|---|---|---|
| Latency | 0 ms | — |
| Based On | `<Main Price Graph>` | Bound to host chart |
| Chart Region | 1 | Overlay |
| Initial Balance Type (In:1) | **Daily** | One IB per RTH day |
| Start Time (In:2) | **09:30:00** | RTH open |
| End Time (In:3) | **10:29:59** | RTH +1 h |
| Weekly Number of Days (In:4) | 2 | n/a (Daily) |
| Round Extensions to TickSize (In:5) | Yes | snap to 0.25 |
| Number of Days to Calculate (In:6) | 100000 | history depth |
| Intraday Number of Minutes (In:7) | 15 | n/a (Daily) |
| Start End Time Method (In:8) | Use StartEnd Time | — |
| Period End As Minutes (In:9) | 30 | n/a |
| Extension Multipliers (In:11–16) | **0.5 / 1 / 1.5 / 2 / 2.5 / 3** | Targets |
| Subgraphs of interest | IB High, IB Low, IB Mid (=midpoint), Ext1±…Ext6± | Need to read in DLL |

**DLL action:** read IB High, IB Low, and compute / read IB Mid. Feed
into `tpo.json`'s `ib.{found,high,mid,low}` block. Mid = (high+low)/2 if
the study does not expose it directly. IB is locked at 10:30 ET so a
later read returns the same values until 16:00 ET roll.

---

## Study ID:9 — Cumulative Delta Bars · Volume

| Setting | Value | Purpose |
|---|---|---|
| Latency | 0 ms | — |
| Based On | `<Main Price Graph>` | Bound to host chart |
| Chart Region | **3** | Separate sub-pane |
| Hide Study | Yes | Computed but not drawn |
| Perform Rolling Calculation (In:1) | **No** | Raw CVD |
| Rolling Calculation Length (In:2) | 10 | (n/a, rolling off) |
| Reset at Start of Trading Day (In:3) | **Yes** | Reset at 09:30 ET |
| Reset at Both Session Start Times (In:4) | No | Reset only at RTH open |

**DLL action:** the DLL already publishes `cumulative_delta.json` from its
own `sc.AskVolume / sc.BidVolume` math (`MES_AI_DataExport.cpp:763–812`).
This native study is independent confirmation that the data Sierra
displays in Region 3 matches what the DLL emits. No additional plumbing
needed for CVD — only the G3 enhancements (`t`, `output_interval`).

---

## Verification commands (after DLL redeploy)

```bash
# 1. tpo.json must become fresh (<30 s)
watch -n 5 'python3 -c "import os,time;p=\"/Users/michael/SierraChart_Data/v9_export/tpo.json\";print(round(time.time()-os.path.getmtime(p),1),\"s\")"'

# 2. session block must match Sierra magenta lines on the live chart
curl -s http://localhost:8000/api/v9/tpo/current \
  | jq '.session, .ib, .previous_session.poc, .previous_session.vah, .previous_session.val'

# 3. CVD output_interval must arrive (G3)
curl -s http://localhost:8000/api/v9/cumulative_delta/current \
  | jq '.output_interval, .points[-1].t'
```

The cockpit should then stop showing `—` or stale TPO values, and the
white/magenta lines in `SierraLevelsOverlay.tsx` should hit the exact
levels Michael sees on Sierra Chart at the same minute.
