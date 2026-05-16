# 01 — System Architecture

**Status:** living document
**Last updated:** 2026-05-16
**Read after:** [`00_README.md`](./00_README.md)
**Read before:** [`02_SYSTEMS_SPEC.md`](./02_SYSTEMS_SPEC.md)

This document gives the designer a map of MEMS26 so every screen they design can be traced back to the data it represents and the constraints that data lives under.

---

## 1. The 30-second elevator pitch

```mermaid
flowchart LR
    Sierra["Sierra Chart<br/>(market data + DLL)"]
    Bridge["Bridge<br/>(11 JSON streams)"]
    Backend["FastAPI Backend<br/>(6 systems + gateway)"]
    Frontend["Next.js Frontend<br/>(dashboard)"]
    User(("Michael<br/>👤"))

    Sierra -- "OHLCV<br/>footprint<br/>TPO<br/>delta<br/>live tick" --> Bridge
    Bridge -- "HTTP POST<br/>localhost:8000" --> Backend
    Backend -- "WebSocket + REST<br/>localhost:3000" --> Frontend
    Frontend --> User
    User -- "manual gate<br/>(SHADOW→DEMO→LIVE)" --> Backend
    Backend -. "DEMO/LIVE only" .-> Sierra
```

**Designer's slice = everything between `Frontend` and `User`.** The backend, bridge, and Sierra are off-limits visually except for compact health indicators.

---

## 2. The 6 systems at a glance

```mermaid
flowchart TB
    subgraph OBS["OBSERVING — provide context, never fire"]
        S1[S1 Day Type<br/>color #6366f1<br/>Trend / Variation / Nontrend]
        S5[S5 TPO<br/>color #eab308<br/>POC migration / value area]
        S6[S6 Killzone<br/>color #14b8a6<br/>Time of day + GATE]
    end

    subgraph FIRE["FIRING — emit trade setups"]
        S2[S2 Five-Min T1<br/>color #06b6d4<br/>5-min number bar patterns]
        S3[S3 Footprint T3<br/>color #a855f7<br/>Order-flow patterns]
        S4[S4 Woodies T2<br/>color #f97316<br/>Woodies CCI 5-min]
    end

    PF[pre_fire_validator]
    GW[(TradingGateway<br/>3 slots: SHADOW · DEMO · LIVE)]
    EX_S[ShadowExecutor<br/>DB write only]
    EX_D[DemoExecutor<br/>trade_command.json → Sierra Sim]
    EX_L[LiveExecutor<br/>trade_command.json → Sierra real]
    BLD[BarLevelDetector<br/>closes T1/T2/T3 or stop]

    OBS -. "advisory context" .-> FIRE
    S6 -- "BLOCK if WEEKEND/CLOSED" --> FIRE
    FIRE -- "setup" --> PF
    PF -- "validated fire" --> GW
    GW --> EX_S
    GW -. "first-wins" .-> EX_D
    GW -. "first-wins" .-> EX_L
    EX_S --> BLD
    EX_D --> BLD
    EX_L --> BLD
```

**S2 / S3 / S4** are "firing" — they propose trades. **S1 / S5 / S6** are "observing" — they shape the decision but never propose. **S6 additionally acts as a hard gate**: WEEKEND or CLOSED instantly blocks all firing.

| # | System | Role | Color (canonical) | UI emphasis |
|---|---|---|---|---|
| S1 | Day Type | OBSERVING | `#6366f1` indigo | Compact label (`TRD 73%`); always present in TopBar |
| S2 | Five-Min T1 | FIRING | `#06b6d4` cyan | Active when 5-min bar closes; chart annotation when pattern building |
| S3 | Footprint T3 | FIRING | `#a855f7` purple | Active on tick-reversal close; absorption / sweep / imbalance / exhaustion |
| S4 | Woodies T2 | FIRING | `#f97316` orange | Active on each new 5-min Woodies bar; A1–A7 decision tree |
| S5 | TPO | OBSERVING | `#eab308` yellow | Profile silhouette + POC/VAH/VAL on right axis |
| S6 | Killzone | OBSERVING + GATE | `#14b8a6` teal | Zone name + edge quality; LARGE warning if gate is blocking |

(Full per-system spec in [`02_SYSTEMS_SPEC.md`](./02_SYSTEMS_SPEC.md).)

---

## 3. Decision flow — what happens when a setup fires

```mermaid
sequenceDiagram
    autonumber
    participant Bar as Bar closed<br/>(5-min / tick_reversal / woodies)
    participant Sys as Firing system<br/>(S2 / S3 / S4)
    participant PF as pre_fire_validator
    participant GW as TradingGateway
    participant Exec as Executor<br/>(Shadow / Demo / Live)
    participant BLD as BarLevelDetector
    participant UI as Frontend
    participant DB as DB + WebSocket

    Bar->>Sys: on_bar(bar)
    Sys->>Sys: detect pattern / signal
    alt no setup
        Sys-->>UI: (no event)
    else setup detected
        Sys->>PF: validate(setup)
        alt rejected
            PF->>DB: record block reason
            PF-->>UI: BannerStack / Reason-Tree drawer
        else passed
            PF->>GW: route_setup(setup, system_id)
            GW->>GW: check slot lock (first-wins)<br/>check mode == SHADOW/DEMO/LIVE
            GW->>Exec: dispatch to mode slot
            Exec->>DB: persist trade (status=OPEN)
            Exec->>UI: ActiveTradeCard + TradeMarker on chart
        end
    end

    loop every bar
        BLD->>DB: check open trades vs price
        alt T1 / T2 / T3 hit
            BLD->>DB: update target_hit
        else stop hit OR time-stop
            BLD->>DB: close trade
            BLD->>UI: ShadowSoakStrip update + TradeHistoryStrip
        end
    end
```

**Designer implications**:
- Every state in this diagram needs a visual: setup-detected (transient), pre-fire-rejected (banner + drawer), routed (chart marker), open (ActiveTradeCard), partial-close (T1/T2 hit), closed (history).
- The Reason Tree is auditable per-fire — there must be a way to drill into "why didn't this fire?" or "why did this fire?".

---

## 4. The three modes (state diagram)

```mermaid
stateDiagram-v2
    [*] --> SHADOW : default at install

    SHADOW --> DEMO : Michael UAT gate<br/>(≥10 SHADOW days, ≥20 trades)
    DEMO --> LIVE : Michael UAT gate<br/>(≥7 DEMO days, slippage in budget)

    LIVE --> SHADOW : kill-switch (panic button)<br/>OR risk-cap breach
    DEMO --> SHADOW : kill-switch
    LIVE --> DEMO : manual rollback

    state SHADOW {
        [*] --> ShadowActive
        ShadowActive : color = YELLOW #facc15<br/>label = "SHADOW"<br/>visual: subtle, no pulse<br/>no order leaves machine
    }

    state DEMO {
        [*] --> DemoActive
        DemoActive : color = CYAN #06b6d4<br/>label = "DEMO"<br/>visual: normal weight<br/>writes trade_command.json (Sim)
    }

    state LIVE {
        [*] --> LiveActive
        LiveActive : color = RED #dc2626<br/>label = "LIVE"<br/>visual: pulse 2s, prominent<br/>writes trade_command.json (real)
    }
```

**Visual implication**: the whole UI shifts identity between modes. Top-bar badge color, pulsing effect on LIVE, possibly chart border or accent color, and definitely kill-switch prominence are all affected.

**Constraint**: Only one mode can fire a specific setup at a time (first-wins). SHADOW always runs in parallel as the "what-if" oracle even when DEMO or LIVE is active.

---

## 5. Risk gates (ordering matters)

When a setup arrives at `pre_fire_validator`, gates run in this strict order (`REQ-S-063`). The first gate that rejects wins; the setup is BLOCKED with that single reason recorded in the Reason Tree.

```mermaid
flowchart TD
    in([Setup arrives at pre_fire]) --> g1{Time gate<br/>≤14:30 ET?}
    g1 -- "no" --> b1[BLOCK: time]
    g1 -- "yes" --> g2{News window?<br/>blackout active?}
    g2 -- "yes" --> b2[BLOCK: news]
    g2 -- "no" --> g3{Daily loss<br/>≥ $250?}
    g3 -- "yes" --> b3[BLOCK: loss]
    g3 -- "no" --> g4{Trade count<br/>≥ 5 today?}
    g4 -- "yes" --> b4[BLOCK: trades]
    g4 -- "no" --> g5{Consecutive<br/>losses ≥ 3?}
    g5 -- "yes" --> b5[BLOCK: cooldown]
    g5 -- "no" --> g6{Margin OK?}
    g6 -- "no" --> b6[BLOCK: margin]
    g6 -- "yes" --> g7{Manual<br/>kill engaged?}
    g7 -- "yes" --> b7[BLOCK: manual]
    g7 -- "no" --> g8{Slot already<br/>occupied?}
    g8 -- "yes" --> b8[BLOCK: slot]
    g8 -- "no" --> pass([PASS → gateway])

    b1 & b2 & b3 & b4 & b5 & b6 & b7 & b8 -. "reason logged" .-> rt[(Reason Tree drawer)]
```

**Visual implications**:
- Each gate needs a visual representation (chip, dot, percentage bar) — the user must be able to glance at the screen and see which gate is closest to tripping.
- The Reason Tree drawer needs to show the **exact gate** that blocked, with a timestamp and the gate's threshold vs the actual value.
- The Cap indicator already exists in TopBar (line 174 of `TopBar.tsx`); other gates need equivalent visibility.

---

## 6. The data layer — what powers each pixel

```mermaid
flowchart LR
    subgraph SC["Sierra Chart<br/>(local Windows-emulated via Sierra Mac build)"]
        DLL["DLL plugin"]
    end

    subgraph BR["Bridge — Python, polls JSON exports"]
        ST1[5min<br/>stream]
        ST2[tick_reversal_15<br/>stream]
        ST3[tick_reversal_12<br/>stream]
        ST4[footprint<br/>stream]
        ST5[imbalance_flags<br/>stream]
        ST6[stacked_imbalances<br/>stream]
        ST7[cumulative_delta<br/>stream]
        ST8[volume_profile<br/>stream]
        ST9[tpo<br/>stream]
        ST10[woodies_5min<br/>stream]
        ST11[live_price<br/>stream]
    end

    subgraph BE["Backend — FastAPI"]
        API1[POST /api/v9/bars/*<br/>ingest]
        DB[(SQLite<br/>data/mems26_local.db)]
        API2[GET /api/v9/&lt;system&gt;/current<br/>read]
        WS[WebSocket<br/>/api/v9/ws]
    end

    subgraph FE["Frontend — Next.js + lightweight-charts"]
        Hooks[useSystemStatePolling<br/>useSystemEvents]
        Stores[zustand stores<br/>tradeStore / systemStore / layoutStore]
        Comps[80 React components]
    end

    DLL -- "JSON file writes" --> ST1 & ST2 & ST3 & ST4 & ST5 & ST6 & ST7 & ST8 & ST9 & ST10 & ST11
    ST1 & ST2 & ST3 & ST4 & ST5 & ST6 & ST7 & ST8 & ST9 & ST10 & ST11 -- "HTTP POST" --> API1
    API1 --> DB
    DB --> API2
    API2 -- "REST poll<br/>(2s / 5s / 10s / 30s)" --> Hooks
    DB --> WS
    WS -- "push events" --> Hooks
    Hooks --> Stores
    Stores --> Comps
```

**Two refresh modes**:
- **REST polling** for slow-changing state (`Day Type` every 10 s, `Killzone` every 5 s, `gateway/status` every 5 s, `shadow/today_wr` every 30 s).
- **WebSocket push** for fast-changing state (new bar close, new trade open/close, banner conditions).

The frontend must remain responsive even when one polling channel stalls — degrade gracefully (last-known value with a `stale` indicator), never freeze.

---

## 7. Frontend layout today (high-level)

```mermaid
flowchart TB
    subgraph Viewport["Browser viewport (1280×800 minimum)"]
        Banner["BannerStack<br/>(top, conditional)"]
        Top["TopBar — 40px<br/>connection · mode · symbol · day type · killzone · TF · price · cap · WR · PnL · nav"]
        L0["Layer0Strip — 22px<br/>chop score + 6 indicators + news"]
        Center["Center column"]
        Side["SidePanel — 248px<br/>(ActiveTradeCard · Switcher · Lens)"]
    end

    Banner --- Top
    Top --- L0
    L0 --- Center
    Center --- Side

    subgraph Center["Center column (flex-1)"]
        Chart[ChartV5b<br/>lightweight-charts<br/>candles + volume overlay + TPO lines + trade markers]
        Th[TradeHistoryStrip]
        Sh[ShadowSoakStrip]
    end

    Chart --- Th
    Th --- Sh
```

This is the layout that exists in `frontend/v9/src/v9/components/layout/V9Dashboard.tsx`. The previous-session hardening (2026-05-16) removed `SystemPanelsBar` (bottom S1–S6 strip) and `VolumePanel` (separate pane) — see [`../../reports/handoff/SESSION_LOG_2026-05-16.md`](../../reports/handoff/SESSION_LOG_2026-05-16.md). Whether they come back, in what form, is **the designer's call** ([`04_DESIGN_BRIEF.md`](./04_DESIGN_BRIEF.md) §3).

---

## 8. What the designer does NOT need to design

| Layer | Why off-limits |
|---|---|
| Bridge JSON shapes | Wire-format, dev-only |
| FastAPI endpoint paths | Already named; designer references them, doesn't rename |
| SQLite schema | Internal; no UI mirror |
| `screen` session management | CLI-level, no UI |
| Sierra Chart's own window | Runs in parallel; we never style Sierra |
| Backend admin (`REQ-ADMIN-001..005`) | Dev console, not user-facing |

---

## 9. What the designer absolutely DOES design

| Surface | Document section |
|---|---|
| SHADOW dashboard primary screen | [`04_DESIGN_BRIEF.md`](./04_DESIGN_BRIEF.md) §2.1 |
| DEMO + LIVE visual modes (color/state shifts) | [`04_DESIGN_BRIEF.md`](./04_DESIGN_BRIEF.md) §2.2–2.3 |
| Trades view (full history + per-trade detail) | [`04_DESIGN_BRIEF.md`](./04_DESIGN_BRIEF.md) §2.4 |
| Settings drawer | [`04_DESIGN_BRIEF.md`](./04_DESIGN_BRIEF.md) §2.5 |
| Reason-Tree drawer (per-fire audit) | [`04_DESIGN_BRIEF.md`](./04_DESIGN_BRIEF.md) §2.6 |
| Blocked-Setup drawer (pre_fire rejects) | [`04_DESIGN_BRIEF.md`](./04_DESIGN_BRIEF.md) §2.7 |
| Kill-Switch UI state | [`04_DESIGN_BRIEF.md`](./04_DESIGN_BRIEF.md) §2.8 |
| Stream Health panel | [`04_DESIGN_BRIEF.md`](./04_DESIGN_BRIEF.md) §2.9 |
| Replay timeline (optional, deferred) | [`04_DESIGN_BRIEF.md`](./04_DESIGN_BRIEF.md) §2.10 |

---

*Next: [`02_SYSTEMS_SPEC.md`](./02_SYSTEMS_SPEC.md) — the per-system deep dive.*
