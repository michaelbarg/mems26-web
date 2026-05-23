# Woody CCI Panel — Designer Specification

**Component:** S4 Woody CCI Panel
**Version:** v1.0
**Date:** 17 May 2026
**Status:** Implementation-ready spec
**Reference mockup:** `v14_data_right_aligned.html`
**Companion:** `MEMS26_Cockpit_V5_Designer_Spec_v1.md` (overall spec)

---

## Table of Contents

1. Overview & Position
2. Final Dimensions
3. Layer Architecture (z-stacked)
4. Interaction Zones (drag/scroll/click) — **with visual diagram**
5. Component Specs (every element, exact coordinates)
6. States to Design
7. Animations & Transitions
8. Edge Cases
9. Handoff Checklist

---

## 1. Overview & Position

### Purpose
Sierra Chart "Woodies CCI Trend" indicator, rendered as a floating overlay panel on the main 5-min chart. Provides S4 system's full analytical view — trend state, CCI values, ZLR detection, projections.

### Position on Dashboard
- **Anchor:** bottom-left of the main 5-min chart
- **Visibility:** controlled by toggle tab on chart's left edge
- **Resize:** width linked with Big Trades panel below; height independent
- **Coexistence:** chart price action on the right side of main chart stays visible underneath/around

### Critical Design Constraint
**Sierra Chart fidelity is NON-NEGOTIABLE for visual elements.**
Only the background color (#2D5555) may be slightly adjusted for dashboard cohesion. All other colors, fonts, layouts, and data placements must match Sierra exactly.

---

## 2. Final Dimensions

### Panel Content Area
```
Width:    480 px
Height:   360 px
```

### Full Panel (with chrome)
```
Title bar height:    22 px
Content area:        360 px (the 480×360 above)
Toolbar height:      22 px (optional, can be moved to chrome wrapper)
─────────────────────────────
Total height:        404 px (with chrome)
Total width:         480 px
```

### Resize Constraints
```
Min width:    380 px
Max width:    600 px
Min height:   240 px
Max height:   500 px
```

### Internal Layout Columns (left to right, within 480×360)

| Zone | X Start | X End | Width | Purpose |
|---|---|---|---|---|
| Left edge markers | 22 | 24 | 2 | Small color dots at each dashed line |
| Chart bars + lines | 22 | 295 | 273 | Histogram + CCI lines + TCCI |
| Dotted lines extension | 295 | 320 | 25 | Dashed reference lines extend into data zone |
| Data values (right-aligned) | 297 | 447 | 150 | CCIDiff, ProjHi/Lo, prices |
| **Frame separator** | 450 | 450 | 1 | Vertical line `#1A3A3A` |
| Axis numbers (right-aligned) | 455 | 498 | 43 | 240, 200, ..., -240 |

### Internal Layout Rows (top to bottom, within 480×360)

| Zone | Y Start | Y End | Height | Purpose |
|---|---|---|---|---|
| Title bar | 0 | 22 | 22 | Sierra title + CCI value + Trend states |
| Top margin | 22 | 44 | 22 | Empty space + ZLR labels |
| Chart area | 44 | 340 | 296 | Bars, lines, dashed levels |
| Margin to time axis | 340 | 363 | 23 | Reserved for axis numbers final row |
| Time axis | 363 | 380 | 17 | Date + times + "9 L E" badge |
| Bottom margin | 380 | — | — | Outside panel content |

---

## 3. Layer Architecture (z-stacked, bottom → top)

```
Layer 0:  Background fill (#2D5555)
Layer 1:  Frame separator (vertical line x=450)
Layer 2:  Dashed reference lines (±200, ±100, 0)
Layer 3:  Left edge color markers (circles)
Layer 4:  Histogram bars (BLUE/RED/YELLOW)
Layer 5:  CCI-14 line (BLACK)
Layer 6:  TCCI line (YELLOW)
Layer 7:  ZLR markers (triangles + labels)
Layer 8:  Current bar X marker (white)
Layer 9:  Axis numbers (right side, 240..-240)
Layer 10: Data values (right-aligned)
Layer 11: Title bar text
Layer 12: Time axis strip + "9 L E" badge
Layer 13: Chrome (title bar background + toolbar) — OUTSIDE the 480×360
Layer 14: Resize handles (visual indicators on edges)
```

---

## 4. Interaction Zones

The panel has **5 distinct drag/click zones**, each with different cursor and behavior.

### Visual Diagram

```
╔══════════════════════════════════════════════════════════════════╗
║  ┌────────────────────────────────────────────────────────────┐ ║
║  │  ZONE 1 · TITLE BAR · drag = MOVE window                   │ ║
║  │  ⋮⋮ Woodies CCI Trend [CCI:147.24] TrendDown..           ─ ✕│ ║
║  ├────────────────────────────────────────────────────┬───────┤ ║
║  │                                                    │       │ ║
║  │                                                    │ ZONE 4│ ║
║  │                                                    │       │ ║
║  │  ZONE 3 · CHART AREA                               │ Y AXIS│ ║
║  │  • drag       = PAN (any direction)                │       │ ║
║  │  • wheel up   = ZOOM IN                            │ drag  │ ║
║  │  • wheel down = ZOOM OUT                           │ here  │ ║
║  │  • shift+drag = BOX ZOOM                           │ verti-│ ║
║  │  • double-click = RESET ZOOM                       │ cally │ ║
║  │                                                    │ ↕     │ ║
║  │                                                    │ ADJUST│ ║
║  │                                                    │ PRICE │ ║
║  │                                                    │ SCALE │ ║
║  │                                                    │       │ ║
║  │                                                    │ 240   │ ║
║  │                                                    │ ...   │ ║
║  │                                                    │ 0     │ ║
║  │                                                    │ ...   │ ║
║  │                                                    │-240   │ ║
║  ├────────────────────────────────────────────────────┼───────┤ ║
║  │  ZONE 2 · TIME AXIS · drag ←→ = SCROLL time        │ 9 L E │ ║
║  │  2026-5-15 · 6:05 · 6:20 · ... · 7:35              │       │ ║
║  └────────────────────────────────────────────────────┴───────┘ ║
║                                                                  ║
║  ZONE 5 · RESIZE HANDLES (on panel edges)                       ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

### Zone Details

#### ZONE 1 — Title Bar (move window)

| Property | Value |
|---|---|
| **Bounds** | x: 0-480, y: 0-22 (full width × 22px tall) |
| **Cursor** | `move` (when over drag handle area) / `default` (over buttons) |
| **Drag behavior** | Move entire window (Woody panel) within dashboard |
| **Drag handle zone** | x: 0-200 (left half of title bar) |
| **Button zones** | x: 440-455 (minimize), 455-470 (maximize), 470-485 (close) |
| **Click action — drag dots** | Initiate window move |
| **Click action — minimize** | Collapse to title bar only (22px height) |
| **Click action — maximize** | Expand to maximum size (600×500) |
| **Click action — close** | Close panel, toggle tab returns to closed state |

#### ZONE 2 — Time Axis (scroll time)

| Property | Value |
|---|---|
| **Bounds** | x: 20-449, y: 363-380 (time strip, excluding 9LE badge) |
| **Cursor** | `ew-resize` (horizontal double-arrow) |
| **Drag behavior** | Horizontal drag scrolls through time |
| **Drag right → left** | Show more recent data (forward in time) |
| **Drag left → right** | Show older data (back in time) |
| **Wheel behavior** | Horizontal scroll (same as drag) |
| **Visual feedback during drag** | Bars and lines reflow leftward/rightward |
| **Visual feedback at edges** | Slight "elastic" bounce when reaching data boundaries |
| **Reset action** | Double-click anywhere in time axis = jump to NOW (rightmost data) |

#### ZONE 3 — Chart Area (pan + zoom)

| Property | Value |
|---|---|
| **Bounds** | x: 22-448, y: 44-362 (chart interior + data column area) |
| **Cursor** | `grab` (idle) / `grabbing` (during drag) |
| **Drag behavior** | Pan in any direction (both X and Y) |
| **Wheel up** | Zoom in (decrease bar count visible, expand x-axis) |
| **Wheel down** | Zoom out (increase bar count visible, compress x-axis) |
| **Shift + drag** | Box zoom — select rectangle, zoom to fit |
| **Double-click** | Reset to default zoom + scroll position |
| **Hover info (TBD)** | Crosshair with price+time tooltip at cursor |

#### ZONE 4 — Y-Axis / Price Scale (adjust Y zoom)

| Property | Value |
|---|---|
| **Bounds** | x: 450-500, y: 22-362 (right strip with numbers 240..-240) |
| **Cursor** | `ns-resize` (vertical double-arrow) |
| **Drag behavior** | Vertical drag adjusts Y-axis scale |
| **Drag up** | Compress Y-axis (more value range visible, lines look smaller) |
| **Drag down** | Expand Y-axis (less value range visible, lines look bigger) |
| **Min Y range** | ±50 (very zoomed in) |
| **Max Y range** | ±400 (very zoomed out) |
| **Default Y range** | ±240 (Sierra standard) |
| **Reset action** | Double-click on axis = reset to ±240 |
| **Visual feedback** | Axis numbers re-distribute as scale changes (e.g., zoomed in shows 50/25/0/-25/-50 instead of 240/200/.../-240) |

#### ZONE 5 — Resize Handles (edges of panel)

| Edge | Bounds | Cursor | Behavior |
|---|---|---|---|
| **Right edge** | x: 478-482, y: 22-362 | `col-resize` | Drag to change width (LINKED with Big Trades width) |
| **Bottom edge** | x: 20-478, y: 378-382 | `row-resize` | Drag to change height (INDEPENDENT from Big Trades) |
| **Bottom-right corner** | x: 475-485, y: 375-385 | `nwse-resize` | Drag to change both |
| **Left edge** | NONE (anchored to dashboard layout) | — | Not resizable |
| **Top edge** | NONE (anchored) | — | Not resizable |

**Resize handle visibility:**
- Default: invisible
- On hover near edge (within 3px): 4×20px orange (#fb950b) indicator appears
- During drag: indicator stays visible, semi-transparent overlay shows new size
- After release: indicator fades out

---

## 5. Component Specs

### 5.1 Background

| Property | Value |
|---|---|
| Fill | `#2D5555` |
| Bounds | Entire 480×360 panel area |

### 5.2 Title Bar

| Property | Value |
|---|---|
| **Bounds** | x: 0-480, y: 0-22 |
| **Background** | `#2D5555` (same as panel) |
| **Bottom separator** | 2px line `#fb950b` at y=22 |
| **Font family** | Arial, sans-serif |

**Title bar contents (left to right):**

| Element | x position | Font | Color |
|---|---|---|---|
| Drag dots (3×2 grid) | 6, 14 | — | `#888780` |
| "Woodies CCI Trend" | 26 | 11px bold | `#FFFFFF` |
| "[CCI:147.24]" | 128 | 11px bold | `#7A8080` |
| "TrendDown: 0.00" | 196 | 11px bold | `#B33B3B` |
| "TrendNeutral: 0.00" | 292 | 11px bold | `#B0A030` |
| "TrendUp: 0.00" | 396 | 11px bold | `#5588FF` |
| "(6..." | 478 | 11px bold | `#5588FF` |
| Minimize "─" | 440 | 14px | `#888780` |
| Maximize "▢" | 455 | 12px | `#888780` |
| Close "✕" | 470 | 12px | `#F09595` |

**Drag dots pattern:**
```
6  •  •
10 •  •
14 •  •
   26 30   (x positions)
   pattern: 3 rows × 2 cols
   radius: 1px each
   color: #888780
```

### 5.3 Dashed Reference Lines (THICK DOTS)

| Property | Value |
|---|---|
| **Stroke width** | 3.5 px |
| **Stroke linecap** | `round` |
| **Stroke dasharray** | `0.5 7` (creates round dots with 7px gaps) |
| **Length** | x=22 to x=320 (stop BEFORE data text starts at x=323) |

**5 lines:**

| Value | Y position | Color | Hex |
|---|---|---|---|
| +200 | 69 | red | `#DC2020` |
| +100 | 130 | cyan | `#22BBBB` |
| 0 | 192 | green | `#22CC22` |
| -100 | 254 | cyan | `#22BBBB` |
| -200 | 315 | red | `#DC2020` |

### 5.4 Left Edge Markers (color circles)

Small dots at left edge of each dashed line:

| Position | Color |
|---|---|
| (22, 69) | `#22CC22` green |
| (22, 130) | `#22BBBB` cyan |
| (22, 192) | `#22CC22` green |
| (22, 254) | `#22BBBB` cyan |
| (22, 315) | `#22CC22` green |

Radius: 2.2 px

### 5.5 Histogram Bars (Trend State)

| Property | Value |
|---|---|
| **Bar width** | 6 px |
| **Gap between bars** | 3 px |
| **Slot width** | 9 px per bar |
| **Bar count** | 30 (default) |
| **First bar X** | 28 |
| **Last bar X** | 289 |
| **Baseline** | y=192 (the "0" line) |

**Trend state colors:**
- BLUE (uptrend) — `#1E54E8` — bars 1-8, 28-30
- YELLOW (transition) — `#DDDD20` — bars 9-12, 24-27
- RED (downtrend) — `#E03030` — bars 13-23

**Direction:**
- Positive CCI: bar grows UP from y=192 toward smaller Y
- Negative CCI: bar grows DOWN from y=192 toward larger Y

### 5.6 CCI-14 Line (BLACK)

| Property | Value |
|---|---|
| **Stroke** | `#000000` |
| **Stroke width** | 2.5 px |
| **Stroke linejoin** | `round` |
| **Stroke linecap** | `round` |
| **Fill** | none |
| **Path** | passes through each bar's CCI value point (top of positive bar / bottom of negative bar) |

### 5.7 TCCI / CCI-6 Line (YELLOW)

| Property | Value |
|---|---|
| **Stroke** | `#DDDD20` |
| **Stroke width** | 2.5 px |
| **Stroke linejoin** | `round` |
| **Stroke linecap** | `round` |
| **Fill** | none |
| **Behavior** | More volatile than CCI-14, oscillates more steeply |
| **Crossings** | Crosses CCI-14 line multiple times per session — important visual signal |

### 5.8 ZLR Markers

#### Red ZLR (DOWN signal, above chart)

**Composition:** triangle + "ZLR" label
**Position examples:** (130, 49) and (166, 49)

| Element | Spec |
|---|---|
| Triangle | polygon `-4,3 4,3 0,11` (downward pointing) |
| Triangle fill | `#FF2020` |
| Label "ZLR" | 9px bold, color `#FF2020`, text-anchor middle, y=0 (above triangle) |

#### Green ZLR (UP signal, below chart)

**Position example:** (238, 335)

| Element | Spec |
|---|---|
| Triangle | polygon `-4,-3 4,-3 0,-11` (upward pointing) |
| Triangle fill | `#00CC00` |
| Label "ZLR" | 9px bold, color `#00CC00`, text-anchor middle, y=3 (below triangle) |

### 5.9 Current Bar X Marker

| Property | Value |
|---|---|
| **Color** | `#FFFFFF` (white) |
| **Stroke width** | 2 px |
| **Size** | 10×10 px |
| **Position** | At the CCI-14 value of the rightmost (current) bar |
| **Shape** | Two crossing lines forming X: `(-5,-5)→(5,5)` and `(-5,5)→(5,-5)` |

### 5.10 Right Axis Numbers

**Position:** right-aligned to x=498, y values per chart scale

| Value | Y position | Color | Notes |
|---|---|---|---|
| 240.00 | 48 | `#5EB8FF` cyan | |
| 200.00 | 72 | `#FF2020` red | extreme high |
| 160.00 | 96 | `#5EB8FF` | |
| 120.00 | 120 | `#5EB8FF` | |
| 80.00 | 144 | `#5EB8FF` | |
| 40.00 | 168 | `#5EB8FF` | |
| 0 | 195 | `#22CC22` green | zero line |
| -40.00 | 216 | `#5EB8FF` | |
| -80.00 | 240 | `#5EB8FF` | |
| -120.00 | 264 | `#5EB8FF` | |
| -160.00 | 288 | `#5EB8FF` | |
| -200.00 | 318 | `#FF2020` red | extreme low |
| -240.00 | 342 | `#5EB8FF` | |

**Font:** 10px bold monospace (except 0 which is 11px bold)
**Text anchor:** `end` (right-aligned at x=498)

### 5.11 Frame Separator

| Property | Value |
|---|---|
| **Position** | Vertical line at x=450 |
| **Y range** | 44 to 362 |
| **Stroke** | `#1A3A3A` |
| **Stroke width** | 1 px |
| **Purpose** | Visually separates data values column from axis numbers |

### 5.12 Right Data Values Column

**Position:** right-aligned to x=447 (just left of frame)

| Element | Y | Font | Color | Notes |
|---|---|---|---|---|
| "101.38 CCIDiff" | 56 | 11px bold | `#00DD00` green | |
| "101.38 CCIDiff" | 88 | 11px bold | `#FFFFFF` white | |
| "101.38 CCIDiff" | 120 | 11px bold | `#FF66FF` magenta | |
| "7439.75 7444.2" | 156 | 11px bold | `#00DD00` green | high prices |
| **"7442.50 L"** | 200 | **22px bold** | `#000000` BLACK | **CURRENT PRICE, LARGEST TEXT** |
| "7435.25 7437.5" | 232 | 11px bold | `#000000` | low prices |
| "7737.75 ProjHi" | 262 | 11px bold | `#5EB8FF` cyan | |
| "7144.00 ProjLo" | 290 | 11px bold | `#FF66FF` magenta | |
| "147.2 147.2 CC" | 318 | 11px bold | `#000000` | CCI summary |
| "-49.7° Low Pre" | 346 | 11px bold | `#000000` | angle prediction |

**Text anchor:** `end` (all right-aligned at x=447)

### 5.13 Bottom Time Axis

| Property | Value |
|---|---|
| **Background** | `#2A4A4A` (darker teal) |
| **Bounds** | x: 20-449, y: 363-380 |
| **Height** | 17 px |

**Time labels:** YELLOW `#DDDD20`, 10px bold monospace

| Label | X position |
|---|---|
| "2026-5-15" | 24 |
| "6:05" | 79 |
| "6:20" | 109 |
| "6:35" | 139 |
| "6:50" | 169 |
| "7:05" | 199 |
| "7:20" | 229 |
| "7:35" | 259 |

### 5.14 "9 L E" Badge

| Property | Value |
|---|---|
| **Position** | x: 455-499, y: 363-380 |
| **Background** | `#22CC22` (green) |
| **Width** | 44 px |
| **Height** | 17 px |
| **Text** | "9 L E" white 10px bold, centered |

### 5.15 Toolbar (Chrome, outside panel content)

**Position:** below the 480×360 content area, height 22px

| Element | Spec |
|---|---|
| ◀ scroll back | 11px `#A3A39C` |
| ▶ scroll forward | 11px `#A3A39C` |
| − zoom out | 11px `#A3A39C` |
| + zoom in | 11px `#A3A39C` |
| Timeframe pill "30m" (active) | 28×14 bg `#fb950b` text `#0A0A0A` |
| Timeframe pill "5m" | 10px `#5F5E5A` |
| Timeframe pill "15m" | 10px `#5F5E5A` |
| ⤢ resize indicator | 10px `#888780` |
| Last update "2s" | 10px `#5F5E5A` right-aligned |

---

## 6. States to Design

The following states need explicit visual treatments:

### 6.1 Loading State
- Initial render before data arrives
- **Treatment:** placeholder skeleton, gray bars/lines, "Loading..." overlay
- Duration: typically <500ms

### 6.2 No Data / Empty State
- After loading, if no bars exist (e.g., pre-market)
- **Treatment:** "Awaiting market data" centered, dashed grid only

### 6.3 Stale Data State
- ZLR feed or DLL stops updating for >30s
- **Treatment:**
  - Panel border changes to `#EAB308` yellow
  - "STALE 4m ago" badge in title bar
  - Histogram bars become 50% opacity
  - Current bar X marker pulses slowly

### 6.4 Disconnected State
- Data bridge crashed
- **Treatment:**
  - Panel border `#DC2626` red
  - Full overlay: "Disconnected — retrying..."
  - All data values dimmed to 30% opacity

### 6.5 Pattern Detected (ZLR Active)
- ZLR pattern triggered
- **Treatment:**
  - ZLR marker pulses subtly (1.0 → 1.2 → 1.0 opacity, 2s cycle)
  - Panel border briefly flashes orange `#fb950b` for 1s
  - Sound cue if enabled (off by default)

### 6.6 Trade Active (S4 fired)
- A trade was triggered from S4 logic
- **Treatment:**
  - Panel chrome shows trade chip in title bar: "🟠 LONG #14"
  - Active Trade Card on right side of dashboard updates
  - Histogram bars at trade time get vertical line marker through them

### 6.7 Zoomed In (Y-axis adjusted)
- User dragged Y-axis to compress range
- **Treatment:**
  - Axis numbers re-distribute (e.g., 50/40/30/20/10/0/-10/-20/...)
  - Dashed lines at ±50/±100 instead of ±100/±200 if very zoomed
  - "ZOOM 50:1" indicator in toolbar

### 6.8 Scrolled Back in Time
- User dragged time axis to view history
- **Treatment:**
  - Current bar X marker disappears (no longer on rightmost bar)
  - "HISTORICAL — back to NOW" button appears at top
  - Live updates pause (data still loaded but display frozen)

### 6.9 Minimized State
- User clicked minimize
- **Treatment:**
  - Panel collapses to 22px title bar only
  - Title bar still shows live CCI value, trend states
  - Click title bar to restore

### 6.10 Maximized State
- User clicked maximize
- **Treatment:**
  - Panel expands to 600×500
  - Chart shows more bars (45 instead of 30)
  - Data values get more breathing room
  - Restore button replaces maximize button

---

## 7. Animations & Transitions

| Action | Duration | Easing | Effect |
|---|---|---|---|
| Panel open (from toggle) | 200ms | ease-out | Slide in from left, fade in |
| Panel close | 150ms | ease-in | Slide out to left, fade out |
| Bar update (new data) | 100ms | linear | Bar height transitions to new value |
| CCI line update | 100ms | linear | Path data updates smoothly |
| ZLR detection | 1000ms | ease-out then in | Border flash + ZLR marker fade in |
| Resize | 0ms (during drag) | — | Live update, no animation during drag |
| Mode change (panel border) | 300ms | ease | Border color transitions |
| Stale data badge | 200ms | ease-out | Fade in with slight scale |
| Hover crosshair | 50ms | — | Snap to nearest bar |
| Title bar minimize | 200ms | ease-in-out | Smooth collapse |

---

## 8. Edge Cases

### 8.1 Very Long Data Values
- E.g., price exceeds 8 digits like "9999.99 L"
- **Solution:** font auto-scales down from 22px → 18px → 14px if needed
- Never wrap; always fit in single line

### 8.2 Multiple ZLR Markers Close Together
- 3 ZLR triggers within 5 bars
- **Solution:** stack markers vertically or compress (smaller arrows + smaller labels)

### 8.3 Bar Count Beyond 30
- User zooms out, now 50 bars visible
- **Solution:** reduce bar width to 4px + 2px gap = 6px slot
- Minimum bar width: 2px (after that, lines only, no bars)

### 8.4 Y-axis Extreme Values
- Outlier bar reaches CCI = 350 (above default ±240 range)
- **Solution:**
  - Auto-rescale: expand axis to ±400 if needed
  - Or: clip bar at axis edge with "↑350" indicator at top

### 8.5 Network Interruption Mid-Drag
- User is dragging time axis, network drops
- **Solution:**
  - Drag still works (uses local cached data)
  - "Offline" indicator appears
  - When reconnected, jump back to NOW (with confirmation)

### 8.6 Title Bar Text Truncation
- "TrendNeutral: 0.00" doesn't fit at smaller widths
- **Solution:** truncate intelligently:
  - At width 480: show full text
  - At width 400: "TrendUp 0.00"
  - At width 350: "▼0 │0│ ▲0"
  - At width <300: just CCI value in title

---

## 9. Designer Handoff Checklist

Before delivering Figma/Sketch/XD file, ensure:

- [ ] Component is at exact 480×360 dimensions (content) + chrome
- [ ] All 30 histogram bars present at correct positions
- [ ] Both CCI lines drawn through correct CCI values
- [ ] All 5 dashed reference lines use thick round dots (3.5px stroke, 0.5/7 dasharray)
- [ ] All 13 axis numbers present and right-aligned to x=498
- [ ] All 10 data values right-aligned to x=447
- [ ] Frame separator at x=450 visible
- [ ] Time axis at bottom with date + 8 timestamps
- [ ] "9 L E" badge in bottom-right corner, green
- [ ] 3 ZLR markers (2 red at top, 1 green at bottom)
- [ ] Current bar X marker (white)
- [ ] Title bar with all 6 text elements + 3 window controls
- [ ] Drag dots in title bar at correct position
- [ ] All states designed (loading, stale, disconnected, pattern detected, trade active, zoomed, scrolled, minimized, maximized)
- [ ] Resize handles shown on right edge, bottom edge, bottom-right corner
- [ ] Interaction zone annotations clear (or separate annotation layer)
- [ ] Color tokens match exact hex values
- [ ] Fonts: Arial for title, monospace for numbers, system font for chrome
- [ ] Animation specs documented (or as transitions in Figma)

---

## 10. Hex Color Reference Card

```
═══ Backgrounds ═══
Panel bg:           #2D5555
Title bar bg:       #2D5555 (same)
Toolbar bg:         #15151A
Time axis bg:       #2A4A4A
Frame separator:    #1A3A3A
"9LE" badge bg:     #22CC22

═══ Histogram Bars ═══
BLUE (uptrend):     #1E54E8
RED (downtrend):    #E03030
YELLOW (trans):     #DDDD20

═══ Lines ═══
CCI-14:             #000000 (BLACK)
TCCI / CCI-6:       #DDDD20 (yellow)

═══ Dashed Levels (Thick Dots) ═══
±200:               #DC2020 (red)
±100:               #22BBBB (cyan)
0:                  #22CC22 (green)

═══ Axis Numbers ═══
Cyan (default):     #5EB8FF
Red (±200 extreme): #FF2020
Green (0):          #22CC22

═══ Data Values ═══
Green:              #00DD00
White:              #FFFFFF
Magenta:            #FF66FF
Cyan (ProjHi):      #5EB8FF
Black (default):    #000000

═══ ZLR Markers ═══
Red (DOWN):         #FF2020
Green (UP):         #00CC00

═══ Title Bar Text ═══
"Woodies CCI Trend":  #FFFFFF
"[CCI:147.24]":       #7A8080
"TrendDown:":         #B33B3B
"TrendNeutral:":      #B0A030
"TrendUp:":           #5588FF
Minimize/Maximize:    #888780
Close:                #F09595
Drag dots:            #888780

═══ Time Axis Text ═══
Yellow:             #DDDD20

═══ Chrome / Toolbar ═══
Icons (inactive):   #A3A39C
Active timeframe:   #fb950b (bg), #0A0A0A (text)
Inactive timeframe: #5F5E5A
Last update:        #5F5E5A

═══ Resize Handle ═══
Indicator:          #fb950b (S4 orange)

═══ State Borders ═══
Default:            #fb950b
Stale data:         #EAB308
Disconnected:       #DC2626
```

---

## 11. Open Questions for Designer

These need designer judgment + Michael's approval:

1. **Crosshair on hover** — Sierra has a crosshair that snaps to bars showing price+time. Include? If yes, what style (white thin lines, dashed cyan, etc.)?

2. **Drag zone visual hints** — should hover near a drag zone show a subtle cursor preview or zone highlight? Or rely purely on cursor change?

3. **Pinch zoom on trackpad** — if a user pinches, should that zoom Y-axis, X-axis, or both?

4. **Right-click context menu** — Sierra has it. Include with options like "Reset zoom", "Save as image", "Settings"?

5. **Color blindness consideration** — should there be an alternate palette mode for deuteranopia (red/green color blindness affects ZLR and dashed lines)?

6. **Print/export view** — if user wants to screenshot for review, should there be a "clean" mode that hides chrome and drag indicators?

---

## 12. Reference Files

| File | Purpose |
|---|---|
| `v14_data_right_aligned.html` | Approved baseline mockup (v14) |
| `MEMS26_Cockpit_V5_Designer_Spec_v1.md` | Overall dashboard spec (companion doc) |
| Sierra Chart screenshot (uploaded by Michael, 17 May 2026) | Original reference for 1:1 fidelity |

---

## Changelog

- **v1.0** (17 May 2026) — Initial Woody-specific spec with all interaction zones, component coordinates, states, animations, edge cases.

