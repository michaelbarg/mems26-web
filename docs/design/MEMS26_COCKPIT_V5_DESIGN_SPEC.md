# MEMS26 Cockpit V5 — Design Specification

**Version:** v1.0
**Date:** 17 May 2026
**Status:** Designer Handoff
**Authors:** Designer chat (Claude) + Michael
**Target:** Implementation by Claude Code (CC) / Frontend developer

---

## 0. Document Purpose

מסמך זה הוא **handoff מעצב→מיישם** עבור MEMS26 Cockpit V5. כל רכיב כולל:

1. **Purpose** — מה הרכיב עושה ולמי
2. **Visual spec** — מידות, צבעים, פונטים, מבנה
3. **States** — מצבים אפשריים (open/closed, IDLE/active, etc.)
4. **File reference** — איפה נמצא ה-mockup המאושר
5. **Implementation notes** — דברים שחייבים לזכור ב-code

המסמך מסומן ב-3 רמות סטטוס:
- 🟢 **NAILED** — מאושר, מוכן ליישום
- 🟡 **PREP** — עיצוב קיים אבל לא לייצור עכשיו
- 🔴 **BLOCKED** — ממתין להחלטה / data schema חיצוני

---

## 1. Project Context

**MEMS26** — מערכת מסחר אוטונומית ב-MES Futures, מבוססת על Hebrew OFA (Order Flow Analysis) של זוהר + Steidlmayer/Dalton auction theory.

**Cockpit V5** — ממשק המסחר העיקרי שבו הסוחר רואה ומקבל החלטות.

**6 מערכות עצמאיות:**
- S1: Day Type (Observer — debated)
- S2: 5-min patterns (Firing)
- S3: Footprint + Tick Reversal (Firing per Designer Brief / Observer per V3 spec — **conflict**)
- S4: Woodies CCI (Firing)
- S5: TPO Charts (Observer)
- S6: Killzone (Observer)

**3 מצבי מסחר:** SHADOW (סימולציה) → DEMO (paper) → LIVE (כסף אמת)

---

## 2. Design Principles

1. **Data integrity קודמת לאסתטיקה.** עיצוב לא מכסה על בעיות data, אלא חושף אותן.
2. **Dark theme חובה.** סוחר עובד שעות ארוכות, אור בהיר מתיש.
3. **Information density גבוהה.** סוחר זקוק להרבה מידע, לא ל-empty space דקורטיבי.
4. **Hierarchy ברורה.** קריטי לעין אחת לזהות: מה הסטטוס? מה השאלה? מה ה-action?
5. **Mode awareness תמיד.** SHADOW vs DEMO vs LIVE חייב להיות ברור — בLIVE לא לפספס שכסף אמת.
6. **Sierra Chart fidelity** לרכיבים שמועתקים ממנו (Woody CCI).
7. **לא להמציא מחדש** מה שעובד ב-Sierra. רק לתרגם לdark theme עם דגשי dashboard.

---

## 3. Visual Foundation

### 3.1 Color Tokens

#### Background palette
```
--bg-primary:     #0A0A0A   (page background)
--bg-panel:       #0F0F10   (cards / panels)
--bg-elevated:    #15151A   (toolbars / headers)
--bg-input:       #1F1F22   (input fields / borders)
--bg-woody:       #2D5555   (Sierra-faithful teal, S4 Woody panel only)
--bg-toolbar-dim: #2A4A4A   (Woody time axis strip)
```

#### Border palette
```
--border-subtle:  #1F1F22
--border-faint:   #1A3A3A   (within Woody)
--border-divider: #1A1A1D
```

#### Text palette
```
--text-primary:   #FFFFFF
--text-secondary: #E5E7EB
--text-tertiary:  #A3A39C
--text-muted:     #888780
--text-dim:       #5F5E5A
--text-faded:     #3A3A37
```

#### System colors (per-system identity)
```
--s1-day-type:    #6366F1   (indigo)
--s2-five-min:    #06B6D4   (cyan)
--s3-footprint:   #A855F7   (purple)
--s4-woodies:     #fb950b   (orange · Sierra-defined)
--s5-tpo:         #EAB308   (yellow)
--s6-killzone:    #14B8A6   (teal)
```

#### Status colors
```
--success:        #5DCAA5   (subdued green for general OK)
--success-strong: #16A34A   (BUY direction, signals active)
--warning:        #EF9F27   (caution, waiting)
--warning-strong: #F97316   (urgent caution)
--danger:         #DC2626   (LIVE mode, blockers, SELL)
--danger-soft:    #F09595   (red text on dark)
--danger-bg:      #1A0808   (LIVE topbar tint)
--info:           #06B6D4
--accent-yellow:  #FCDE5A   (live price marker, current bar)
```

#### Mode colors
```
--mode-shadow:    #FCDE5A   (outline yellow)
--mode-demo:      #06B6D4   (filled cyan)
--mode-live:      #DC2626   (filled red, pulse)
```

#### Woody-specific (Sierra 1:1)
```
--woody-bg:       #2D5555
--woody-bar-blue: #1E54E8
--woody-bar-red:  #E03030
--woody-bar-yellow: #DDDD20
--woody-cci-line: #000000   (CCI-14, black)
--woody-tcci-line: #DDDD20  (CCI-6, yellow)
--woody-line-200: #DC2020   (±200 dashed)
--woody-line-100: #22BBBB   (±100 dashed cyan)
--woody-line-0:   #22CC22   (0 dashed green)
--woody-axis-cyan: #5EB8FF
--woody-axis-red:  #FF2020
--woody-text-green: #00DD00
--woody-text-magenta: #FF66FF
--woody-zlr-up:    #00CC00
--woody-zlr-down:  #FF2020
```

### 3.2 Typography

**Font stack:**
```
-apple-system, system-ui, sans-serif  (UI)
monospace                              (numbers, prices, times)
Arial, sans-serif                      (Woody Sierra panel — match Sierra style)
```

**Sizes:**
- 22px / 500 — large PnL display
- 16px / bold — Woody live price "7442.50 L"
- 14px / 500 — section titles
- 13px / 500 — system identifier in card
- 12px / 500 — primary values, button text
- 12px / regular — labels
- 11px / 500 — chip labels, secondary values
- 11px / regular — Layer0 text
- 10px / 500 — column headers, badges (letter-spacing 0.6)
- 10px / regular — meta info
- 9px / regular — micro-labels in dense areas
- 8px — Woody axis numbers, sub-bar volumes

### 3.3 Spacing System

```
4px   tiny gap (chip internal)
6px   small (icon-text)
8px   default
12px  comfortable
16px  section gap
20px  major section
24px  page-level
```

### 3.4 Border radius

```
2px   chips, badges
3px   small buttons, mode badge
4px   cards, panels
6px   page-level containers
```

### 3.5 Iconography style

- **System icons:** monoline SVG paths, stroke 1.2-1.4, color = system color
- **Pattern icons:** 14×10px viewBox, simple geometric, stroke only (no fill)
- **Status indicators:** 3-4px circles in status color

---

## 4. Layout & Grid

### 4.1 Dashboard zones (top to bottom)

```
┌─────────────────────────────────────────────────────────────────┐
│  TopBar                32px                                     │
├─────────────────────────────────────────────────────────────────┤
│  Layer0                16-18px                                  │
├─────────────────┬─────────────────────────────────┬─────────────┤
│                 │                                 │             │
│  Left Zone      │                                 │  Right Zone │
│  (Woody +       │       Main Chart                │  (Card +    │
│   Big Trades)   │       (5-min)                   │   Switcher +│
│                 │                                 │   Lens)     │
│  Toggle tabs    │                                 │             │
│  for S3/S4/S5   │                                 │             │
│                 │                                 │             │
├─────────────────┴─────────────────────────────────┴─────────────┤
│  Recent Trades Strip                            ║  Shadow Soak  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Resize logic

- **Left Zone width** resizable: 320px (min) — 600px (max)
- **Woody and Big Trades** widths are **linked** (move together)
- **Chart minimum width:** 400px
- **Right Zone width:** fixed 280px
- **Vertical resize** within Left Zone: Woody and Big Trades have independent heights
- **Persistence:** localStorage save/load per user

### 4.3 Z-index hierarchy

```
0  — base canvas (chart, panels)
10 — toggle tabs (on chart edge)
20 — floating overlays (Woody, Big Trades when toggled)
30 — modals (confirmation prompts)
40 — tooltips
50 — notifications (LIVE mode warnings)
```

---

## 5. Components

### 5.1 🟢 Active Trade Card (v6)

**File:** `active_trade_overlay_v6.html`

**Purpose:** הצגת הטרייד הפעיל הנוכחי — system, direction, pattern, R:R, prices, PnL, status.

**Dimensions:** 270×460 (in side panel)

**Color accent bar:** top edge 3px, צבע המערכת הירוית

**Sections (top to bottom):**
1. **Header** — system circle + name + direction (LONG/SHORT)
2. **Sub-header** — category description (e.g., "Reactive Long category · 5-min TF")
3. **TRIGGER** — Pattern (with icon!) · Pattern size · Confluence · Context
4. **PLANNED R:R** — T1/T2/T3 ratios
5. **LIVE PRICES** — ST/EN/T1/T2/T3 chips with values
6. **OPEN PNL** — large pt display + status + duration

**Pattern row spec:**
- Label "Pattern" left at x=412
- Icon: 14×10 SVG at x=548 (left-aligned), system color, stroke 1.4
- Text "Cup & Handle" at x=572, left-aligned, white, weight 500
- 6px gap between icon end and text start

**Chip styling (LIVE PRICES section):**
- 30px wide × 16px tall, border-radius 2
- Each row: chip + label text + value (monospace) + secondary info
- **ST**: outline red (#E24B4A), text #F09595
- **EN**: outline gray (#A3A39C), text white
- **T1 (hit)**: filled cyan #06B6D4, text dark #083344
- **T2/T3 (pending)**: outline cyan, text cyan
- Current price chip on chart: filled yellow #FCDE5A, text black, no label

**Chart-side chips** (price scale right edge):
- 60px wide × 18px tall, same color rules as card
- Format: `T3 7465` (label + price, monospace, 11px)
- T1 hit shows ✓ inside
- Current price chip 17px wide, no label

**State variants (to design later):**
- IDLE — no active trade ("Awaiting setup")
- EXIT — trade just closed (highlight + transition)
- SHORT direction — same layout, mirrored prices
- BLOCKED — system rejected entry
- DEGRADED — data integrity issue

### 5.2 🟢 Pattern Icon Library v1

**File:** `pattern_icon_library_v1.html`

**Purpose:** ספרייה מאוחדת של 26 אייקוני תבניות, אחד לכל pattern קנוני של 3 המערכות היורות.

**Icon spec:**
- 14×10 px viewBox
- Stroke only (no fill except where critical)
- Stroke width 1.4 (1.0 for secondary lines)
- Color = system color
- Simple geometric paths

**S2 Five-Min (cyan, 9 icons):**
| Icon | Path snippet | Use case |
|---|---|---|
| Cup & Handle | `M 0,2 C 0,9 2,10 5,10 L 11,10 C 14,10 14,9 14,2 + M 14,2 L 15,3 L 17,1 L 18,2` | bullish continuation 20-40 bars |
| Double Bottom | `M 0,2 L 4,10 L 9,5 L 14,10 L 18,2` | bullish reversal |
| Double Top | `M 0,10 L 4,2 L 9,7 L 14,2 L 18,10` | bearish reversal |
| Head & Shoulders | `M 0,9 L 3,5 L 6,8 L 9,1 L 12,8 L 15,5 L 18,9` | bearish reversal |
| Bull Flag | `M 0,10 L 6,2` + rect 7,2 11,6 | continuation |
| Bear Flag | `M 0,2 L 6,10` + rect 7,4 11,6 | continuation |
| Triangle (Asc) | line 0,2-18,2 + line 0,10-18,2 | bullish |
| Pennant | line 0,2-14,6 + line 0,10-14,6 | continuation |
| OFA | dashed 0-line + path 0,10 L 6,2 L 12,8 L 18,2 | 4-5 bars |

**S3 Footprint (purple, 9 icons):** V-Shape Reversal, Stair-step, Compression+Pop, Stacked Imbalance, Absorption/Belly, Liquidity Sweep, Exhaustion, POC Migration, Accumulation+Break

**S4 Woodies (orange, 8 icons):** ZLR, TLB, TT, GB100, VEGAS, GHOST, FAMIR, HTLB

**Library page layout:**
- 3 sections by system, each titled with system color + identifier
- Each card 220×60: icon + name + 1-line description + system color top border
- 3 cards per row

### 5.3 🟢 Woody CCI Panel (Sierra 1:1)

**File:** `v14_data_right_aligned.html`

**Purpose:** הקלון המדויק של Sierra Chart "Woodies CCI Trend" indicator — הכלי המקצועי של S4.

**Dimensions:** 480 × 360 (panel content)
- With chrome (title 22px + toolbar 22px): 480 × 404

**Background:** `#2D5555` (Sierra teal, slightly darkened)

**Title bar** (22px, #2D5555):
- "Woodies CCI Trend" — white, 11px bold
- "[CCI:147.24]" — gray #7A8080, 11px bold
- "TrendDown: 0.00" — #B33B3B, 11px bold
- "TrendNeutral: 0.00" — #B0A030, 11px bold
- "TrendUp: 0.00" — #5588FF, 11px bold
- "(6..." — #5588FF, truncated

**Chart area columns (left to right):**
1. **Chart bars + lines** (x=22 to x=295)
2. **Data values** (CCIDiff, ProjHi/Lo, prices) — right-aligned to x=447
3. **Frame separator** at x=450 (1px, #1A3A3A)
4. **Axis numbers** (240..-240) — right-aligned to x=498

**5 dashed reference lines (THICK DOTS):**
```
stroke-width: 3.5
stroke-linecap: round
stroke-dasharray: 0.5 7
length: x=22 to x=320 (stop before data text)
```
- +200: `#DC2020` (red)
- +100: `#22BBBB` (cyan)
- 0: `#22CC22` (green)
- -100: `#22BBBB` (cyan)
- -200: `#DC2020` (red)

Plus tiny circle markers at left edge (r=2.2) in green or cyan per line.

**Histogram bars:**
- 6px wide, 3px gap → 9px per bar slot
- 30 bars total in 296-22 = 274 width (covers most of chart area)
- Colors per trend_state:
  - BLUE uptrend: `#1E54E8`
  - RED downtrend: `#E03030`
  - YELLOW transition: `#DDDD20`

**Lines:**
- CCI-14: BLACK `#000000`, stroke-width 2.5, round join+cap
- TCCI/CCI-6: YELLOW `#DDDD20`, stroke-width 2.5

**ZLR markers:**
- Red down arrows above +200 line: triangle pointing down + "ZLR" label red 9px bold
- Green up arrow below -200 line: triangle pointing up + "ZLR" label green

**Current bar X:** white, stroke-width 2, at the rightmost bar's CCI value

**Right axis numbers (13 values, right-aligned to x=498):**
240, 200, 160, 120, 80, 40, 0, -40, -80, -120, -160, -200, -240
- All cyan `#5EB8FF` except ±200 in red `#FF2020` and 0 in green `#22CC22`
- 10px monospace bold

**Data values column (right-aligned to x=447):**
```
101.38 CCIDiff   green  #00DD00
101.38 CCIDiff   white  #FFFFFF
101.38 CCIDiff   magenta #FF66FF
7439.75 7444.20  green
7442.50 L        22px bold BLACK (large)
7435.25 7437.50  black
7737.75 ProjHi   cyan
7144.00 ProjLo   magenta
147.2 147.2 CC   black
-49.7° Low Pre   black
```

**Bottom time axis (height 18, #2A4A4A bg):**
- "2026-5-15" then 6:05, 6:20, 6:35, ... 7:35
- YELLOW `#DDDD20`, monospace 10px bold

**"9 L E" badge** (bottom-right corner):
- Green `#22CC22` background, 25-44 wide × 18 tall
- White text "9 L E" 10px bold centered

**Position on dashboard:** bottom-left of 5-min chart, over older bars area. Active price action on the right side of chart stays visible.

**Toggle behavior:** vertical tab on left edge of chart (12px wide, S4 orange), rotated label "S4 WOODY ◀", click opens/closes overlay.

**Chrome wrap (NOT inside the 480×360, wraps around it):**
- Title bar 22px: drag dots ⋮⋮ + "S4 Woody · BLUE · ZLR · A4" + ─ ▢ ✕
- Toolbar 22px: ◀ ▶ scroll + − + zoom + timeframe pills (30m/5m/15m) + ⤢ resize + "last 2s"

### 5.4 🟢 Big Trades Panel

**File:** `big_trades_panel_v1.html`

**Purpose:** סינון של עסקאות גדולות (institutional size) — מאפשר לראות לאן הולך הכסף הגדול.

**Dimensions:** 480 × 280 (matches Woody width when linked)

**Position:** מתחת ל-Woody בLeft Zone, או independent stack

**Header strip (28px):**
- ▼ / ▶ collapse arrow + "Big Trades" 12px white
- "filter ≥" label + value field (default 80, configurable 50-200) cyan
- Slider 80px wide, cyan track on dark
- Right side: "today · 14 trades" counter

**Column headers (18px):**
TIME · PRICE · SIZE · DIRECTION (right-aligned)

**Data rows (20px each):**
```
TIME      PRICE      SIZE (signed)   DIRECTION bar              LABEL
09:42:15  7445.25    +180  (green)   ████████████████ (BUY)    BUY
09:41:48  7444.75    +145  (green)   ███████████      (BUY)    BUY
09:41:22  7443.50    -120  (red)     ██████           (SELL)   SELL
```

**Direction bar styling:**
- Background bar: subtle dark green (#163828) for BUY area, subtle dark red (#391616) for SELL area
- Foreground bar: solid green `#16A34A` for BUY, solid red `#DC2626` for SELL
- Foreground length: proportional to size (180 = ~92% of 262px max, 80 = ~41%)

**Sorting:** newest first (top = newest)

**Scope:** entire trading day (since open)

**Imbalance footer:** NONE (explicitly removed per spec)

**Collapsed state:** 22px strip showing "Big Trades · collapsed · 14 trades today" + preview of last big trade

**Scroll:** vertical when >11 visible rows; "↓ X more · scroll" indicator at bottom

**Real-time behavior (TBD):**
- ❓ New trade highlight animation? (open question)
- ❓ Pagination beyond 100 trades? (open question)
- ❓ Filter by direction or time range? (open question)

### 5.5 🟢 Mode Badge (3 states)

**File:** `mode_badge_3_states.html`

**Purpose:** זיהוי מצב המסחר הנוכחי בעין אחת. בLIVE — לא לפספס שכסף אמת.

**3 states:**

#### SHADOW (subtle)
- **Visual:** outline only, 60×16 px (small) / 92×26 (large)
- **Color:** yellow #FCDE5A border 0.6-0.8px, transparent bg
- **Dot:** small filled yellow circle on left
- **Text:** "SHADOW" yellow 10px/500 + counter "#14" muted
- **Topbar:** unchanged, regular dark
- **Card border:** unchanged (system color)

#### DEMO (informational)
- **Visual:** filled cyan, 50×16 / 92×26
- **Color:** bg `#06B6D4` filled
- **Dot:** white circle
- **Text:** "DEMO" white 10px/500 + "#2" in lighter cyan
- **Topbar:** cyan accent on bottom border (2px, opacity 0.4)
- **Card border:** unchanged

#### LIVE (critical, cannot be missed)
- **Visual:** filled red + pulse ring, 48×16 / 92×26
- **Color:** bg `#DC2626` solid
- **Dot:** larger white circle (2.5px radius)
- **Text:** "LIVE" white 10px/700 bold + "#1" white 500
- **Pulse ring:** concentric circles around badge, stroke red opacity 0.4-0.6
- **Topbar background:** tinted dark red `#1A0808`
- **Topbar separator:** 2px solid `#DC2626`
- **Active Trade Card border:** 1.2px red `#DC2626`
- **Active Trade Card header:** red background bar (replaces system color)
- **Card text:** white instead of muted gray
- **PnL display:** dollars shown ALONGSIDE points (e.g., "+12.5 pt · +$62.50")

**Pause LIVE button** ✅ approved:
- Located in TopBar near the LIVE badge
- Click → confirmation prompt "Pause LIVE and return to SHADOW?" → on confirm, switches mode immediately, closes any active trade gracefully
- Button visible only when in LIVE mode

### 5.6 🟢 Toggle Tab pattern (left edge of chart)

**Purpose:** entry point for system panels (S3/S4/S5) that open as overlays.

**Position:** vertical strip on chart's left edge

**Dimensions:**
- 12-14px wide
- Height: divided between 3 systems (S3 top, S4 middle, S5 bottom), each ~30% of chart height

**Styling per toggle:**
- Background: `#1F1F22` (dark)
- Overlay tint when active/highlighted: system color at 8-18% opacity
- Rotated label (90° counter-clockwise): "S3 FOOT ◀" / "S4 WOODY ◀" / "S5 TPO ◀"
- Text: system color, 9px bold, letter-spacing 1

**Behavior:**
- Click → opens overlay panel in bottom-left of chart
- Open state: tint brighter, "◀" rotates to "▼"
- ❓ **Open question:** radio (one at a time) or stacked (multiple simultaneous)?

### 5.7 🟢 Big Trades Toggle (bottom edge of chart)

**Purpose:** entry point for Big Trades panel

**Position:** horizontal strip at chart's bottom edge

**Dimensions:** full chart width × 14px

**Styling:**
- Background `#1F1F22`
- "▶ Big Trades 80+ · collapsed · 14 today" left aligned
- "▲" indicator right aligned

**Click → opens panel below chart**

### 5.8 🟢 Plan Tab Redesign (v8)

**File:** `v8_woody_sierra_plan_trader.html` (Section 2)

**Purpose:** ב-Lens panel, ה"Plan" tab של כל מערכת מציג מה היא צריכה כדי לעבוד / לירות.

**4-section hierarchy (top to bottom):**

#### 1. STATE (badge גדול)
- Large prominent badge with state name
- States: `SCANNING` (orange) · `APPROACHING` (purple/yellow) · `BLOCKED` (red border + bg) · `READY` (green) · `FIRING` (system color, pulse)
- Color codes:
  - SCANNING: bg `#412402` border/text `#EF9F27`
  - APPROACHING: bg `#1B0E2D` border/text system-color
  - BLOCKED: bg `#3D0E0E` border `#DC2626` text `#DC2626` (badge + outer card border)
  - READY: filled green
  - FIRING: filled system-color, pulse

#### 2. BUILDING (אנטיציפציה)
- Pattern/signal that's currently forming
- Progress bar showing completion %
- ETA text ("~3-5 bars to confirm")
- Pattern icon next to name

#### 3. TO FIRE (gap conditions)
- 3-4 rows, each:
  - Status dot: ✓ green / ⚠ orange / ● red
  - Condition text
  - Target/actual value (right-aligned)
- Color of row text matches status:
  - Green: condition met
  - Orange: waiting, not blocker
  - Red: BLOCKER

#### 4. DATA HEALTH (footer)
- Small status row
- Green dot = all healthy / Red dot + label = specific issue
- "last update Xs ago" timestamp

**Status:** 🟢 approved structure, ready for implementation across all 6 systems

**Open question:** Plan tab structure for observers (S1, S5, S6) — same 4 sections or modified? (since they don't "fire")

### 5.9 🟡 S3 Footprint Panel (PREP only)

**File:** `s3_footprint_s5_tpo_overlays.html` (top section)

**Status:** prep design exists, NOT for immediate implementation

**When unblocked:** Apply same toggle/overlay pattern as Woody, purple `#A855F7`

### 5.10 🟡 S5 TPO Panel (PREP only)

**File:** `s3_footprint_s5_tpo_overlays.html` (bottom section)

**Status:** prep design exists, NOT for immediate implementation

**When unblocked:** Apply same toggle/overlay pattern, yellow `#EAB308`

### 5.11 🔴 Trade Detail Drawer (PENDING SCHEMA)

**Purpose:** "Why fired?" drill-down — opens from card footer link

**Blocking:** Trade Snapshot Schema from Strategic Architect

**Content (planned):**
- Pattern details + bars + zone (high/low/POC)
- Required conditions vs actual values
- Waited-for conditions
- Fire decision path
- Cross-system snapshot (state of all 6 systems at time of fire)

### 5.12 🔴 Recent Trades Strip (PENDING SCHEMA)

**Purpose:** היסטוריה של טריידים אחרונים בתחתית ה-dashboard, click → opens Trade Detail Drawer

**Blocking:** Trade Snapshot Schema

**Content (planned):**
- Last 5-10 trades, 1-line each
- System icon, P&L, time, direction
- Hover → quick preview tooltip
- Click → opens drawer

### 5.13 🔴 SHADOW Panel (PENDING SCHEMA)

**Purpose:** Full analytical dashboard, dedicated page, active in SHADOW/DEMO/LIVE

**Blocking:** Trade Snapshot Schema

**Content (planned):**
- Cross-system performance
- All trades history with cross-system snapshots
- Per-system deep state
- Performance breakdowns (WR / PnL / MFE / MAE by system/pattern/opening type)

---

## 6. Interaction Patterns

### 6.1 Toggle behavior (system panels)

- Click toggle tab → overlay slides in from left, appears in bottom-left of chart
- Click again (or ✕ on chrome) → overlay slides out, tab returns to dim state
- Toggle tab tint changes from 8% to 18% system color when panel is open
- System's cube in Switcher glows when its panel is open (visual link)

### 6.2 Resize behavior

- Hover over panel border → cursor changes (col-resize / row-resize / nwse-resize)
- Drag border → panel resizes, throttled to 60fps
- Min/max sizes enforced (can't break layout)
- localStorage saves size per panel per user
- Woody and Big Trades widths are LINKED (move together)

### 6.3 Mode transitions

- SHADOW → DEMO: requires confirmation modal "Switch to DEMO?" Yes/No
- DEMO → LIVE: requires stronger confirmation "Switch to LIVE? Real money at risk." Type "CONFIRM" to proceed
- LIVE → SHADOW (via Pause LIVE button): one-click with brief confirmation, gracefully closes any active trade
- Mode change triggers visual cascade: badge updates → topbar updates → card border updates → all simultaneously

### 6.4 Active Trade lifecycle

- IDLE → SCANNING/APPROACHING: card stays IDLE display, Plan tab content updates
- APPROACHING → FIRING: card animates open (slide-in), chips populate, chart markers appear
- FIRING → RUNNING: target chips activate as hit (filled vs outline)
- RUNNING → CLOSED: card fades to summary view, moves to Recent Trades Strip
- BLOCKED: card flashes red briefly, returns to IDLE
- DEGRADED: card border yellow, data health indicator on

### 6.5 Pattern icon usage

- One icon per active pattern, shown in TRIGGER row of Active Trade Card
- Icon position: 6px before pattern name text, left-aligned in the value area
- Icon color = system color (matches card accent)
- Library document (pattern_icon_library_v1) is accessible via "Why fired? →" link or settings

---

## 7. Open Items (Decisions Needed)

### 7.1 System architecture conflicts

🔴 **S3 firing vs observer:** Designer Brief (16/5) says S3 is FIRING. V3 spec (9/5) says S3 is OBSERVER only.
- Impact: if observer, no S3 trade snapshots in Active Trade Card
- **Recommend:** lock by Strategic Architect before final implementation

🔴 **S1 firing vs observer:** Similar conflict for Day Type
- Impact: Switcher row layout, Plan tab structure

### 7.2 Interaction details

🟡 **Toggle behavior — radio or stacked?**
- Option A: only one overlay open at a time (radio)
- Option B: multiple overlays open simultaneously (stacked, carousel, or tiled)
- Need to decide before implementing toggle logic

🟡 **Big Trades real-time:**
- Highlight animation on new trade arrival?
- Pagination/infinite scroll beyond 100 trades?
- Additional filters (direction, time range)?

🟡 **Plan tab for observers (S1/S5/S6):**
- Same 4-section structure?
- Or different (since they don't "fire")?

### 7.3 Active Trade Card states

🟡 **Missing state designs:**
- IDLE (no active trade)
- EXIT (trade just closed, transition)
- SHORT direction
- BLOCKED (entry rejected)
- DEGRADED (data integrity issue)
- All need explicit visual design

---

## 8. Pending External Dependencies

### 8.1 Trade Snapshot Schema (from Strategic Architect)

**Required for:**
- Trade Detail Drawer (5.11)
- Recent Trades Strip (5.12)
- SHADOW Panel (5.13)
- Cross-system snapshot display

**Content needed:**
- Per-trade JSON schema
- Per-system state object
- Entry logic + waited-for conditions
- Live state + exit data
- API endpoints to fetch (current, recent, full snapshot, performance)

**Prompt for Strategic Architect:** delivered separately in earlier session.

---

## 9. Implementation Notes for CC

### 9.1 RTL/LTR handling

- Hebrew prose text uses `dir="rtl"`
- SVG content must be wrapped in `<div dir="ltr">` to prevent text positioning bugs
- Mixed content: use `.he` and `.ltr-svg` classes to isolate

### 9.2 Pattern icons in code

- Store as SVG path strings in a single constants file
- Reference by pattern name: `PATTERN_ICONS['cup_and_handle']`
- Renderer applies system color via fill/stroke
- Sized via viewBox, scaled by container

### 9.3 Mode-specific styling

- Use CSS data attributes: `<body data-mode="live">`
- Cascade styles via `[data-mode="live"] .topbar { background: var(--danger-bg); }`
- Easier to switch dynamically than class swap

### 9.4 Resize logic

- Use native DOM events (mousedown/mousemove/mouseup)
- CSS variables for dynamic widths: `--left-zone-width: 480px`
- Throttle resize events to ~16ms (60fps)
- Save to localStorage on mouseup, not during drag

### 9.5 Performance considerations

- Woody panel renders ~30 bars + 2 lines + axis: minimal cost
- Big Trades virtualize if >50 rows visible
- Chart updates: only re-render bars that changed (delta updates)
- Polling: avoid duplicate endpoints (current implementation has `/api/v9/day_type/current` + `/api/v9/day_type/v9/current` — pick one)

### 9.6 Sierra fidelity

- Woody panel colors are NON-NEGOTIABLE for Sierra fidelity
- Only the background `#2D5555` can be slightly adjusted for dashboard cohesion
- All other colors (bars, lines, dots, axis numbers) match Sierra exactly
- Don't substitute "modern" replacements for any element

---

## 10. File Index

All deliverables in `/mnt/user-data/outputs/`:

| File | Status | Component |
|---|---|---|
| `active_trade_overlay_v4.html` | 🟢 | Active Trade Card baseline |
| `active_trade_overlay_v6.html` | 🟢 | + Cup & Handle icon integration |
| `pattern_icon_library_v1.html` | 🟢 | 26 pattern icons reference |
| `v14_data_right_aligned.html` | 🟢 | Woody Sierra 1:1 final |
| `big_trades_panel_v1.html` | 🟢 | Big Trades 80+ panel |
| `mode_badge_3_states.html` | 🟢 | SHADOW/DEMO/LIVE badges |
| `woody_chrome_toggle_context.html` | 🟢 | Chrome + toggle architecture |
| `v8_woody_sierra_plan_trader.html` | 🟢 | Plan tab redesign |
| `s3_footprint_s5_tpo_overlays.html` | 🟡 | S3 + S5 prep (not for implementation) |
| `v7_woody_overlay_plan_redesign.html` | 🟡 | Earlier iteration (reference only) |

---

## 11. Glossary

- **CCI** — Commodity Channel Index, technical indicator (S4 uses CCI-14 and CCI-6)
- **TCCI** — Turbo CCI (CCI-6), faster oscillator
- **TPO** — Time Price Opportunity, Market Profile letters showing 30-min periods
- **VAH / VAL / POC** — Value Area High / Low / Point of Control
- **IB** — Initial Balance, first hour high/low
- **ZLR** — Zero Line Reject, S4 pattern (A1 in decision tree)
- **OFA** — Order Flow Analysis, foundational framework (Zohar)
- **MES** — Micro E-mini S&P 500 futures contract
- **OFA short patterns:** First-hour patterns < 12 bars
- **Confluence** — number of supporting signals from multiple sources
- **Shadow / Demo / Live** — 3 trading modes (sim / paper / real money)

---

## 12. Document Maintenance

**This document is versioned as v1.0.** Updates should:

1. Increment version (1.1, 1.2, etc.)
2. Add changelog entry at bottom
3. Update file timestamp in header
4. If a component changes status (PREP → NAILED), update both Section 5 and Section 10 table

**Owner:** Designer chat session 17/5/2026
**Next review:** After Strategic Architect returns Trade Snapshot Schema
**Hand-off audience:** Claude Code (CC) / human frontend developer

---

## Changelog

- **v1.0** (17 May 2026) — Initial handoff document covering Active Trade Card, Pattern Icons, Woody Sierra panel, Big Trades, Mode Badge, Toggle pattern, Plan tab redesign. S3/S5 panels in PREP status. Trade Detail Drawer, Recent Trades Strip, SHADOW Panel pending external schema.
