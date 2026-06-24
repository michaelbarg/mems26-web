#!/usr/bin/env python3
"""
replay_brain_view.py — MEMS26 replay/brain-view JSON -> standalone HTML.

Runs ANYWHERE (no DB, stdlib only). Reads tools/replay_data_<date>.json
(produced by export_replay_data.py on the Mac) and writes a single,
self-contained tools/replay_<date>.html with all data baked in.

The chart is a 3-pane, time-synced TradingView Lightweight-Charts v5 view:
  1. PRICE  (candles) + level price-lines (IBH/IBL/POC/VAH/VAL) +
            playbook expected-direction zone tints + trade entry/exit markers
  2. VOLUME (per-bar up/down histogram)
  3. WOODIES(CCI line + zero line + trend color + ZLR/HFE markers)

Header shows the day-type + a one-line "expectation" derived from the
day-type playbook (config/daytype_playbook.yaml).

HONEST FAILURE (CLAUDE.md Rule 1): any pane / overlay whose data is absent in
the JSON renders a visible "data not exported yet — run export_replay_data.py
on the Mac" note. Nothing is synthesized. Levels / volume / CVD / per-bar
day-type are only shown when actually present.

Usage:
    python3 tools/replay_brain_view.py --date 2026-06-09
    # optional: --data <path.json>  --out <path.html>  --playbook <yaml>
"""

import argparse
import json
import os
import re
import sys

LWC_CDN = "https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_PLAYBOOK = os.path.join(REPO, "config", "daytype_playbook.yaml")


# ─────────────────────────────────────────────────────────────────────────────
# Tiny YAML reader for the playbook.
# We only need `daytype_style.<DayType>.{bias,note,action,fade_edges,ref_points}`.
# Rather than depend on PyYAML (no new pip deps allowed), parse the small,
# regular structure of daytype_playbook.yaml directly. If anything about the
# parse is uncertain we return {} and the renderer degrades to "no playbook
# expectation" — never a fabricated zone.
# ─────────────────────────────────────────────────────────────────────────────
def parse_daytype_style(yaml_path):
    if not os.path.exists(yaml_path):
        return {}
    try:
        with open(yaml_path) as fh:
            lines = fh.readlines()
    except OSError:
        return {}

    out = {}
    in_block = False
    cur = None
    block_indent = None
    for raw in lines:
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())

        if stripped.startswith("daytype_style:"):
            in_block = True
            block_indent = indent
            continue
        if not in_block:
            continue
        # A new top-level key at <= block_indent ends the daytype_style block.
        if indent <= block_indent and stripped.endswith(":") and not stripped.startswith("#"):
            # e.g. "patterns:" — leave the block
            in_block = False
            continue

        # Day-type header, e.g. "  Normal:" (2-space indent under daytype_style)
        m = re.match(r"^(\s+)([A-Za-z_]\w*):\s*$", line)
        if m and (len(m.group(1)) == block_indent + 2):
            cur = m.group(2)
            out[cur] = {}
            continue

        # key: value under a day-type
        if cur is not None:
            km = re.match(r'^\s+([a-z_]+):\s*(.*)$', line)
            if km:
                key, val = km.group(1), km.group(2).strip()
                # strip inline comments + surrounding quotes
                val = re.sub(r'\s+#.*$', '', val).strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                out[cur][key] = val
    return out


def _human_expectation(day_type, style):
    """One-line expectation string from the playbook for the header."""
    if not day_type:
        return None
    blk = style.get(day_type)
    if not blk:
        return None
    bias = blk.get("bias")
    action = blk.get("action")
    note = blk.get("note")
    parts = []
    if action:
        parts.append(action.upper())
    if bias:
        parts.append(bias)
    elif note:
        parts.append(note)
    return " — ".join(parts) if parts else None


# ─────────────────────────────────────────────────────────────────────────────
# Expected-direction zones for the PRICE pane background tint.
# DRIVEN BY the playbook + the levels. We ONLY tint a zone the playbook
# actually speaks to; a zone the playbook is silent on stays neutral (no tint).
#
# Mapping (derived from daytype_style.bias semantics, fade vs with-trend):
#   - "fade VA edges": above VAH => SHORT/fade (red), below VAL => LONG/fade
#     (green); VAL..VAH (value) => neutral mean-revert (faint gray-blue).
#   - Lower extreme on a 2-sided/extreme fade day => still LONG-fade (green).
#   - Trend/Variation/with-IB-expansion days are CONTINUATION not fade, and the
#     playbook does NOT define per-price-zone fade levels for them → we leave
#     the price background NEUTRAL (honest: we don't invent a zone the playbook
#     is silent on). The header still states the with-trend expectation.
#
# Each zone => {from, to, color, label}. `from`/`to` are prices (None = open
# end). The renderer paints horizontal bands across the whole time axis.
# ─────────────────────────────────────────────────────────────────────────────
FADE_DAYTYPES = {"Normal", "Neutral_Center", "Neutral_Extreme"}

def build_zones(day_type, levels, style):
    if not day_type or not levels:
        return []
    blk = style.get(day_type) or {}
    # Only fade day-types get explicit per-zone direction tints.
    if day_type not in FADE_DAYTYPES:
        return []
    vah = levels.get("vah")
    val = levels.get("val")
    poc = levels.get("poc")
    zones = []
    SHORT = "rgba(239, 83, 80, 0.10)"   # fade-short tint (above value)
    LONG = "rgba(38, 166, 154, 0.10)"   # fade-long tint  (below value)
    VALUE = "rgba(120, 144, 156, 0.07)" # inside value: mean-revert / neutral-ish

    if vah is not None:
        zones.append({"from": vah, "to": None, "color": SHORT,
                      "label": "above VAH → fade SHORT"})
    if val is not None:
        zones.append({"from": None, "to": val, "color": LONG,
                      "label": "below VAL → fade LONG"})
    if vah is not None and val is not None:
        zones.append({"from": val, "to": vah, "color": VALUE,
                      "label": "inside value → mean-revert"})
    elif poc is not None:
        # No VA edges but have POC: just mark a faint band around POC as value.
        zones.append({"from": poc, "to": poc, "color": VALUE,
                      "label": "POC (value)"})
    return zones


def load_data(path):
    with open(path) as fh:
        return json.load(fh)


def render_html(data, day_type, expectation, zones, levels, has_volume,
                has_cvd, playbook_found):
    """Build the standalone HTML. All data is JSON-embedded; no network data."""
    payload = {
        "date": data.get("date"),
        "day_type": day_type,
        "expectation": expectation,
        "levels": levels,                 # may be None
        "zones": zones,                   # [] when none
        "bars": data.get("bars", []),
        "cvd": data.get("cvd", []),
        "trades": data.get("trades", []),
        "has_volume": has_volume,
        "has_cvd": has_cvd,
        "playbook_found": playbook_found,
        "generated_at": data.get("generated_at"),
        "source": data.get("source"),
        # Verification-fixture flags: when synthetic is true the renderer shows a
        # loud banner so a fabricated test file can NEVER be mistaken for a real
        # export. Real exports omit these (or set synthetic=false) → no banner.
        "synthetic": bool(data.get("synthetic")),
        "banner": data.get("banner"),
    }
    blob = json.dumps(payload).replace("</", "<\\/")

    title = f"MEMS26 Replay — {data.get('date','?')}"
    # The JS below is intentionally defensive: every overlay is wrapped so a
    # missing array shows an honest note rather than throwing.
    return _TEMPLATE.replace("__TITLE__", title) \
                    .replace("__CDN__", LWC_CDN) \
                    .replace("__DATA__", blob)


# The HTML/JS template. __DATA__ is replaced with the JSON payload.
_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>__TITLE__</title>
<style>
  :root {
    --bg: #0e1117; --panel:#161b22; --grid:#222a35; --txt:#c9d1d9;
    --muted:#8b949e; --up:#26a69a; --down:#ef5350; --accent:#e3b341;
    --warn:#d29922; --short:#ef5350; --long:#26a69a;
  }
  html,body { margin:0; padding:0; background:var(--bg); color:var(--txt);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }
  .wrap { max-width:1280px; margin:0 auto; padding:14px 16px 28px; }
  .synthbanner { display:none; background:repeating-linear-gradient(45deg,
      #5a1f1f, #5a1f1f 12px, #6e2626 12px, #6e2626 24px);
    color:#ffe0e0; border:2px solid #ff6b6b; border-radius:7px;
    padding:9px 14px; margin-bottom:12px; font-size:13px; font-weight:700;
    letter-spacing:.3px; text-align:center; }
  .synthbanner.on { display:block; }
  header.hdr { display:flex; flex-wrap:wrap; align-items:baseline; gap:10px 16px;
    border-bottom:1px solid var(--grid); padding-bottom:10px; margin-bottom:10px; }
  .hdr h1 { font-size:18px; margin:0; font-weight:650; letter-spacing:.2px; }
  .daytype { font-size:14px; font-weight:600; color:var(--accent);
    border:1px solid var(--grid); border-radius:6px; padding:2px 8px; }
  .daytype.missing { color:var(--warn); }
  .expect { font-size:13px; color:var(--muted); flex:1 1 320px; min-width:240px; }
  .meta { font-size:11px; color:var(--muted); }
  #chart { width:100%; height:760px; position:relative; }
  .rthcap { font-size:11px; color:var(--muted); margin:6px 2px 0;
    display:flex; align-items:center; gap:6px; }
  .rthcap .dot { width:7px; height:7px; border-radius:50%; background:var(--accent);
    display:inline-block; }
  .legend { display:flex; flex-wrap:wrap; gap:6px 14px; font-size:11px;
    color:var(--muted); margin:8px 2px 0; }
  .legend b { color:var(--txt); font-weight:600; }
  .chip { display:inline-flex; align-items:center; gap:5px; }
  .sw { width:11px; height:11px; border-radius:2px; display:inline-block; }
  .notes { margin-top:10px; font-size:12px; color:var(--muted); line-height:1.5; }
  .note.miss { color:var(--warn); }
  .panenote { position:absolute; right:14px; background:rgba(210,153,34,.12);
    border:1px solid rgba(210,153,34,.4); color:#f0c674; font-size:11px;
    padding:3px 8px; border-radius:5px; pointer-events:none; z-index:5; }
  table.tr { border-collapse:collapse; margin-top:12px; font-size:12px; width:100%; }
  table.tr th, table.tr td { border:1px solid var(--grid); padding:4px 8px; text-align:right; }
  table.tr th { background:var(--panel); color:var(--txt); }
  table.tr td.l, table.tr th.l { text-align:left; }
  .pos { color:var(--up); } .neg { color:var(--down); }
</style>
</head>
<body>
<div class="wrap">
  <div class="synthbanner" id="synthbanner"></div>
  <header class="hdr">
    <h1>__TITLE__</h1>
    <span id="daytype" class="daytype">day-type: …</span>
    <span id="expect" class="expect"></span>
    <span id="meta" class="meta"></span>
  </header>

  <div id="chart">
    <div id="pricenote"></div>
    <div id="volnote"></div>
    <div id="woodnote"></div>
  </div>

  <div class="rthcap" id="rthcap"><span class="dot"></span><span>RTH default — scroll for Globex</span></div>

  <div class="legend" id="legend"></div>
  <div class="notes" id="notes"></div>
  <div id="tradetable"></div>
</div>

<script src="__CDN__"></script>
<script>
const DATA = __DATA__;

function fmt(n, d) {
  if (n === null || n === undefined || isNaN(n)) return "—";
  return Number(n).toFixed(d === undefined ? 2 : d);
}
// CT wall-clock string "YYYY-MM-DDTHH:MM:SS" -> chart business time.
// The chart's axis/crosshair formatters print getUTCHours()/getUTCMinutes() of
// the series time, so to make labels read in CT we plot every series using the
// CT wall-clock RE-EXPRESSED as UTC seconds (ctToSec). We do NOT plot the raw
// `epoch` (true UTC) because that would shift the axis to UTC hours. ctToSec is
// therefore the single source of chart-time for bars, trades AND the RTH window
// below, so they all line up. (`epoch` is kept in the JSON for other consumers.)
function ctToSec(ts) {
  // ts like "2026-06-09T08:30:00" (already America/Chicago wall-clock)
  if (!ts) return null;
  const m = ts.match(/(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})/);
  if (!m) return null;
  // Treat the wall-clock as if UTC so the chart prints exactly these HH:MM.
  return Date.UTC(+m[1], +m[2]-1, +m[3], +m[4], +m[5], +m[6]) / 1000;
}
// The CT calendar date the session belongs to, taken from the first bar's ts.
// Used to anchor the RTH 08:30–15:00 CT default visible window.
function sessionDateCT(bars) {
  for (const b of (bars || [])) {
    if (b && b.ts) {
      const m = b.ts.match(/(\d{4})-(\d{2})-(\d{2})/);
      if (m) return { y: +m[1], mo: +m[2], d: +m[3] };
    }
  }
  return null;
}

function showPaneNote(id, top, text) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = "panenote";
  el.style.top = top + "px";
  el.textContent = text;
}

(function main() {
  const LWC = window.LightweightCharts;

  // Loud synthetic banner — verification fixtures only. A real Mac export never
  // sets DATA.synthetic, so this stays hidden for genuine data.
  if (DATA.synthetic) {
    const bn = document.getElementById("synthbanner");
    if (bn) {
      bn.className = "synthbanner on";
      bn.textContent = DATA.banner ||
        "SYNTHETIC TEST FIXTURE — fabricated data for renderer verification ONLY. NOT real market data.";
    }
  }

  const dtEl = document.getElementById("daytype");
  const exEl = document.getElementById("expect");
  const metaEl = document.getElementById("meta");

  // Header: day-type + expectation (honest "missing"). The provenance
  // (classify_replay / state-machine / trade-stamped) is shown as a tooltip so
  // the canonical 7-type vs a fallback is never silently conflated.
  if (DATA.day_type) {
    dtEl.textContent = "day-type: " + DATA.day_type;
    if (DATA.day_type_source) dtEl.title = "source: " + DATA.day_type_source;
  } else {
    dtEl.textContent = "day-type: missing (export on Mac)";
    dtEl.classList.add("missing");
  }
  exEl.textContent = DATA.expectation
    ? DATA.expectation
    : (DATA.playbook_found
        ? "no playbook expectation for this day-type"
        : "playbook not found — expectation unavailable");
  const nb = (DATA.bars || []).length;
  metaEl.textContent = "bars: " + nb + " · trades: " + (DATA.trades||[]).length
      + (DATA.generated_at ? " · exported " + DATA.generated_at : "");

  if (!LWC || !LWC.createChart) {
    document.getElementById("notes").innerHTML =
      '<span class="note miss">Lightweight-Charts failed to load from CDN. '
      + 'Open this file with internet access, or vendor the script locally.</span>';
    return;
  }

  const bars = (DATA.bars || []).filter(b => b && b.o != null);
  if (!bars.length) {
    document.getElementById("notes").innerHTML =
      '<span class="note miss">No bars in the JSON — run export_replay_data.py on the Mac for this date.</span>';
    return;
  }

  // Build the chart with explicit CT time formatting.
  const chart = LWC.createChart(document.getElementById("chart"), {
    autoSize: true,
    layout: {
      background: { type: "solid", color: "#0e1117" },
      textColor: "#c9d1d9",
      panes: { separatorColor: "#222a35", separatorHoverColor: "#2d3340",
               enableResize: true },
    },
    grid: { vertLines: { color: "#1b212b" }, horzLines: { color: "#1b212b" } },
    rightPriceScale: { borderColor: "#222a35", scaleMargins: { top: 0.06, bottom: 0.06 } },
    timeScale: {
      borderColor: "#222a35", timeVisible: true, secondsVisible: false,
      // Format the (UTC-shifted) seconds back into HH:MM — these ARE CT.
      tickMarkFormatter: (t) => {
        const d = new Date(t * 1000);
        const hh = String(d.getUTCHours()).padStart(2,"0");
        const mm = String(d.getUTCMinutes()).padStart(2,"0");
        return hh + ":" + mm;
      },
    },
    localization: {
      timeFormatter: (t) => {
        const d = new Date(t * 1000);
        const hh = String(d.getUTCHours()).padStart(2,"0");
        const mm = String(d.getUTCMinutes()).padStart(2,"0");
        return hh + ":" + mm + " CT";
      },
    },
    crosshair: { mode: LWC.CrosshairMode ? LWC.CrosshairMode.Normal : 0 },
  });

  // ── PANE 0: PRICE candles ────────────────────────────────────────────────
  const priceSeries = chart.addSeries(LWC.CandlestickSeries, {
    upColor: "#26a69a", downColor: "#ef5350", borderVisible: false,
    wickUpColor: "#26a69a", wickDownColor: "#ef5350",
    priceLineVisible: false, lastValueVisible: false,
  }, 0);

  // Dedup + sort by time (Lightweight-Charts requires strictly ascending time).
  const seen = new Set();
  const candle = [];
  for (const b of bars) {
    // CT wall-clock first (axis prints CT); epoch only if ts is missing.
    const t = (b.ts != null) ? ctToSec(b.ts) : b.epoch;
    if (t == null || seen.has(t)) continue;
    seen.add(t);
    candle.push({ time: t, open: b.o, high: b.h, low: b.l, close: b.c, _b: b });
  }
  candle.sort((a, z) => a.time - z.time);
  priceSeries.setData(candle.map(({_b, ...d}) => d));

  // ── Expected-direction zone tints (playbook-driven, never invented) ──────
  // Drawn as filled price-range bands behind the candles using a series-less
  // overlay: we approximate with semi-transparent price lines is not enough,
  // so we draw bands via a primitive on the price series.
  if (DATA.zones && DATA.zones.length) {
    drawZones(chart, priceSeries, candle, DATA.zones);
  }

  // ── Level price-lines (IBH / IBL / POC / VAH / VAL), Sierra-style ────────
  const lv = DATA.levels;
  if (lv) {
    // IB label is data-driven: the demo computes IB from real first-hour bars
    // and passes ib_label "IB (from bars)" so it is never confused with the
    // Sierra TPO export. Falls back to plain IBH/IBL when no label is supplied.
    const ibTag = lv.ib_label ? (" — " + lv.ib_label) : "";
    const defs = [
      ["IBH" + ibTag, lv.ibh, "#7e9cff", false],
      ["IBL" + ibTag, lv.ibl, "#7e9cff", false],
      ["VAH", lv.vah, "#b39ddb", true],
      ["VAL", lv.val, "#b39ddb", true],
      ["POC", lv.poc, "#e3b341", true],   // emphasize POC
    ];
    for (const [label, price, color, dashed] of defs) {
      if (price == null) continue;
      priceSeries.createPriceLine({
        price: price,
        color: color,
        lineWidth: label === "POC" ? 2 : 1,
        lineStyle: dashed ? (LWC.LineStyle ? LWC.LineStyle.Dashed : 2) : 0,
        axisLabelVisible: true,
        title: label,
      });
    }
  } else {
    showPaneNote("pricenote", 8,
      "levels: not exported yet — run export_replay_data.py on the Mac");
  }

  // ── Woodies price-scale studies (LSMA / EMA-34 / Proj Hi-Lo) on pane 0 ────
  // These ride on the candle pane, Sierra-style. Only drawn when present in the
  // JSON (Rule 1: no synthetic line).
  function addPriceOverlay(field, color, width, title, dashed) {
    const pts = candle.filter(c => c._b[field] != null)
                      .map(c => ({ time: c.time, value: c._b[field] }));
    if (!pts.length) return;
    const s = chart.addSeries(LWC.LineSeries, {
      color: color, lineWidth: width, priceLineVisible: false,
      lastValueVisible: true, title: title,
      lineStyle: dashed ? (LWC.LineStyle ? LWC.LineStyle.Dashed : 2) : 0,
    }, 0);
    s.setData(pts);
  }
  addPriceOverlay("lsma",   "#ffb74d", 1, "LSMA",   false);
  addPriceOverlay("ema34",  "#4dd0e1", 1, "EMA34",  false);
  addPriceOverlay("proj_hi","#7e9cff", 1, "ProjHi", true);
  addPriceOverlay("proj_lo","#7e9cff", 1, "ProjLo", true);

  // ── Trade entry/exit markers on the price pane ───────────────────────────
  const trades = DATA.trades || [];
  const priceMarkers = [];
  for (const tr of trades) {
    const et = (tr.entry_ts != null) ? ctToSec(tr.entry_ts) : tr.entry_epoch;
    const isShort = (tr.direction || "").toUpperCase() === "SHORT";
    if (et != null && tr.entry_price != null) {
      priceMarkers.push({
        time: et,
        position: isShort ? "aboveBar" : "belowBar",
        color: isShort ? "#ef5350" : "#26a69a",
        shape: isShort ? "arrowDown" : "arrowUp",
        text: (tr.pattern_id || tr.direction || "") +
              (tr.entry_price != null ? " @" + fmt(tr.entry_price) : ""),
      });
    }
    const xt = (tr.exit_ts != null) ? ctToSec(tr.exit_ts) : tr.exit_epoch;
    if (xt != null && tr.exit_price != null) {
      const pnl = tr.pnl_usd;
      const pnlTxt = (pnl == null) ? "" :
        (pnl >= 0 ? " +$" + fmt(pnl,0) : " -$" + fmt(Math.abs(pnl),0));
      priceMarkers.push({
        time: xt,
        position: "inBar",
        color: (pnl != null && pnl < 0) ? "#ef5350" : "#9e9e9e",
        shape: "circle",
        text: "exit" + pnlTxt + (tr.outcome ? " (" + tr.outcome + ")" : ""),
      });
    }
  }
  attachMarkers(LWC, chart, priceSeries, priceMarkers);

  // ── PANE 1: VOLUME histogram ─────────────────────────────────────────────
  const hasVol = DATA.has_volume && candle.some(c => c._b.volume != null && c._b.volume > 0);
  if (hasVol) {
    const volSeries = chart.addSeries(LWC.HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "", lastValueVisible: false, priceLineVisible: false,
    }, 1);
    volSeries.setData(candle.map(c => ({
      time: c.time,
      value: c._b.volume || 0,
      color: c.close >= c.open ? "rgba(38,166,154,0.55)" : "rgba(239,83,80,0.55)",
    })));
  } else {
    // Create an empty pane-1 anchor so the layout still shows the labeled gap.
    const ph = chart.addSeries(LWC.HistogramSeries, { priceScaleId: "" }, 1);
    ph.setData([]);
    showPaneNote("volnote", 430,
      "volume: not exported yet — run export_replay_data.py on the Mac");
  }

  // ── CVD overlay (cumulative_delta) on the volume pane, own price scale ────
  // Drawn as a line riding over the volume histogram so order-flow drift is
  // visible without a 4th pane. Only when real CVD points exist (Rule 1: no
  // synthetic flat line). Aligned to the same ctToSec time space as candles.
  if (DATA.has_cvd && Array.isArray(DATA.cvd) && DATA.cvd.length) {
    const cvdPts = [];
    const cseen = new Set();
    for (const p of DATA.cvd) {
      if (p == null || p.cumulative_delta == null) continue;
      const t = (p.ts != null) ? ctToSec(p.ts) : p.epoch;
      if (t == null || cseen.has(t)) continue;
      cseen.add(t);
      cvdPts.push({ time: t, value: p.cumulative_delta });
    }
    cvdPts.sort((a, z) => a.time - z.time);
    if (cvdPts.length) {
      const cvdSeries = chart.addSeries(LWC.LineSeries, {
        color: "#f0c674", lineWidth: 1, priceScaleId: "cvd",
        lastValueVisible: true, priceLineVisible: false, title: "CVD",
      }, 1);
      cvdSeries.setData(cvdPts);
    }
  }

  // ── PANE 2: WOODIES CCI ──────────────────────────────────────────────────
  const cciPts = candle.filter(c => c._b.cci != null);
  if (cciPts.length) {
    const cciSeries = chart.addSeries(LWC.LineSeries, {
      color: "#90caf9", lineWidth: 2, priceLineVisible: false,
      lastValueVisible: true, title: "Woodies CCI",
    }, 2);
    // Color the line by trend_state when present (segment coloring via points).
    cciSeries.setData(cciPts.map(c => {
      const pt = { time: c.time, value: c._b.cci };
      const ts = (c._b.trend_state || "").toUpperCase();
      if (ts === "BLUE" || ts === "LONG") pt.color = "#26a69a";
      else if (ts === "RED" || ts === "SHORT") pt.color = "#ef5350";
      else if (ts) pt.color = "#9e9e9e";
      return pt;
    }));
    // Zero line.
    cciSeries.createPriceLine({ price: 0, color: "#5b6470", lineWidth: 1,
      lineStyle: LWC.LineStyle ? LWC.LineStyle.Dashed : 2,
      axisLabelVisible: true, title: "0" });
    // +100 / -100 Woodies reference bands.
    cciSeries.createPriceLine({ price: 100, color: "#37414e", lineWidth: 1,
      lineStyle: LWC.LineStyle ? LWC.LineStyle.Dotted : 1, axisLabelVisible: false });
    cciSeries.createPriceLine({ price: -100, color: "#37414e", lineWidth: 1,
      lineStyle: LWC.LineStyle ? LWC.LineStyle.Dotted : 1, axisLabelVisible: false });
    // ±200 — source extreme thresholds (TLB needs the CCI to cross these / the SWI).
    cciSeries.createPriceLine({ price: 200, color: "#5b6470", lineWidth: 1,
      lineStyle: LWC.LineStyle ? LWC.LineStyle.Dotted : 1, axisLabelVisible: true, title: "+200" });
    cciSeries.createPriceLine({ price: -200, color: "#5b6470", lineWidth: 1,
      lineStyle: LWC.LineStyle ? LWC.LineStyle.Dotted : 1, axisLabelVisible: true, title: "-200" });

    // Secondary Woodies oscillators on the same pane (only when present in JSON).
    function addOsc(field, color, title) {
      const pts = cciPts.filter(c => c._b[field] != null)
                        .map(c => ({ time: c.time, value: c._b[field] }));
      if (!pts.length) return;
      const s = chart.addSeries(LWC.LineSeries, {
        color: color, lineWidth: 1, priceLineVisible: false,
        lastValueVisible: false, title: title,
      }, 2);
      s.setData(pts);
    }
    addOsc("tcci", "#ce93d8", "TCCI(6)");
    addOsc("swi",  "#fff176", "SWI");
    addOsc("czi",  "#80cbc4", "CZI");

    // ZLR / HFE markers on the Woodies pane.
    const wMarkers = [];
    for (const c of cciPts) {
      if (c._b.zlr) {
        const up = (c._b.zlr_direction || "").toUpperCase().includes("LONG")
                || (c._b.zlr_direction || "").toUpperCase().includes("UP");
        wMarkers.push({ time: c.time, position: up ? "belowBar" : "aboveBar",
          color: "#e3b341", shape: up ? "arrowUp" : "arrowDown", text: "ZLR" });
      }
      if (c._b.hfe) {
        const up = (c._b.hfe_direction || "").toUpperCase().includes("LONG")
                || (c._b.hfe_direction || "").toUpperCase().includes("UP");
        wMarkers.push({ time: c.time, position: up ? "belowBar" : "aboveBar",
          color: "#ce93d8", shape: "square", text: "HFE" });
      }
    }
    attachMarkers(LWC, chart, cciSeries, wMarkers);
  } else {
    const ph = chart.addSeries(LWC.LineSeries, {}, 2);
    ph.setData([]);
    showPaneNote("woodnote", 560,
      "Woodies CCI: not in JSON for this date");
  }

  // Pane height proportions ~ price 55% / volume 15% / woodies 30%.
  try {
    const panes = chart.panes();
    const H = document.getElementById("chart").clientHeight || 760;
    if (panes[0]) panes[0].setHeight(Math.round(H * 0.55));
    if (panes[1]) panes[1].setHeight(Math.round(H * 0.15));
    if (panes[2]) panes[2].setHeight(Math.round(H * 0.30));
  } catch (e) { /* pane sizing best-effort */ }

  // ── Default visible window = RTH 08:30–15:00 CT (all bars stay loaded; the
  //    user can scroll left into Globex / right into the post-close tail). We
  //    compute the window in the SAME ctToSec space the candles use, then clamp
  //    to the actual data extent so we never request a range with no bars.
  (function setRthDefault() {
    const ts = chart.timeScale();
    const dataFrom = candle[0].time;
    const dataTo = candle[candle.length - 1].time;
    const sd = sessionDateCT(DATA.bars);
    let from = dataFrom, to = dataTo;
    if (sd) {
      // 08:30:00 and 15:00:00 CT on the session date, as ctToSec (UTC-as-CT) sec.
      const rthOpen = Date.UTC(sd.y, sd.mo - 1, sd.d, 8, 30, 0) / 1000;
      const rthClose = Date.UTC(sd.y, sd.mo - 1, sd.d, 15, 0, 0) / 1000;
      // Clamp to loaded data so the range is always populated.
      from = Math.max(rthOpen, dataFrom);
      to = Math.min(rthClose, dataTo);
      if (!(to > from)) { from = dataFrom; to = dataTo; }   // fallback: show all
    }
    try {
      ts.setVisibleRange({ from, to });
    } catch (e) {
      ts.fitContent();   // never leave the chart blank
    }
  })();

  buildLegend(DATA);
  buildNotes(DATA);
  buildTradeTable(DATA, fmt);
})();

// v5 markers helper: prefer createSeriesMarkers, fall back to setMarkers.
function attachMarkers(LWC, chart, series, markers) {
  if (!markers || !markers.length) return;
  markers.sort((a, z) => a.time - z.time);
  try {
    if (LWC.createSeriesMarkers) { LWC.createSeriesMarkers(series, markers); return; }
  } catch (e) {}
  try { if (series.setMarkers) series.setMarkers(markers); } catch (e) {}
}

// Draw expected-direction zones as filled horizontal bands behind candles.
// Implemented with a lightweight series primitive (ISeriesPrimitive) so the
// bands track the price scale. Falls back to nothing if the API shape differs.
function drawZones(chart, series, candle, zones) {
  try {
    const t0 = candle[0].time, t1 = candle[candle.length - 1].time;
    const primitive = {
      _zones: zones, _series: series, _chart: chart, _t0: t0, _t1: t1,
      attached(p) { this._req = p.requestUpdate; },
      updateAllViews() {},
      paneViews() {
        const self = this;
        return [{
          zOrder() { return "bottom"; },
          renderer() {
            return {
              draw(target) {
                target.useBitmapCoordinateSpace((scope) => {
                  const ctx = scope.context;
                  const ts = self._chart.timeScale();
                  const x0 = ts.timeToCoordinate(self._t0);
                  const x1 = ts.timeToCoordinate(self._t1);
                  if (x0 == null || x1 == null) return;
                  const hr = scope.horizontalPixelRatio, vr = scope.verticalPixelRatio;
                  const left = Math.min(x0, x1) * hr;
                  const right = Math.max(x0, x1) * hr;
                  for (const z of self._zones) {
                    let yTop, yBot;
                    const cTop = (z.to != null) ? self._series.priceToCoordinate(z.to) : 0;
                    const cBot = (z.from != null) ? self._series.priceToCoordinate(z.from)
                                                  : scope.bitmapSize.height / vr;
                    yTop = (z.to != null ? cTop : 0) * vr;
                    yBot = (z.from != null ? cBot : scope.bitmapSize.height / vr) * vr;
                    if (yTop == null || yBot == null) continue;
                    ctx.fillStyle = z.color;
                    ctx.fillRect(left, Math.min(yTop, yBot), right - left, Math.abs(yBot - yTop));
                  }
                });
              }
            };
          }
        }];
      }
    };
    if (series.attachPrimitive) series.attachPrimitive(primitive);
  } catch (e) { /* zones are decorative; never block the chart */ }
}

function buildLegend(DATA) {
  const el = document.getElementById("legend");
  const chips = [];
  chips.push('<span class="chip"><span class="sw" style="background:#26a69a"></span>up candle</span>');
  chips.push('<span class="chip"><span class="sw" style="background:#ef5350"></span>down candle</span>');
  if (DATA.levels) {
    const lv = DATA.levels;
    if (lv.poc != null)
      chips.push('<span class="chip"><span class="sw" style="background:#e3b341"></span><b>POC</b></span>');
    if (lv.vah != null || lv.val != null)
      chips.push('<span class="chip"><span class="sw" style="background:#b39ddb"></span>VAH/VAL</span>');
    if (lv.ibh != null || lv.ibl != null)
      chips.push('<span class="chip"><span class="sw" style="background:#7e9cff"></span>IBH/IBL'
        + (lv.ib_label ? ' (' + lv.ib_label + ')' : '') + '</span>');
  }
  // Woodies full-panel study legend.
  chips.push('<span class="chip"><span class="sw" style="background:#90caf9"></span>CCI-14</span>');
  chips.push('<span class="chip"><span class="sw" style="background:#ce93d8"></span>TCCI-6</span>');
  chips.push('<span class="chip"><span class="sw" style="background:#fff176"></span>SWI</span>');
  chips.push('<span class="chip"><span class="sw" style="background:#80cbc4"></span>CZI</span>');
  chips.push('<span class="chip"><span class="sw" style="background:#ffb74d"></span>LSMA</span>');
  chips.push('<span class="chip"><span class="sw" style="background:#4dd0e1"></span>EMA-34</span>');
  chips.push('<span class="chip"><span class="sw" style="background:#7e9cff"></span>Proj Hi/Lo</span>');
  if (DATA.zones && DATA.zones.length) {
    chips.push('<span class="chip"><span class="sw" style="background:rgba(239,83,80,.35)"></span>fade-SHORT zone</span>');
    chips.push('<span class="chip"><span class="sw" style="background:rgba(38,166,154,.35)"></span>fade-LONG zone</span>');
  }
  if (DATA.has_cvd)
    chips.push('<span class="chip"><span class="sw" style="background:#f0c674"></span>CVD (cum. delta)</span>');
  chips.push('<span class="chip"><span class="sw" style="background:#e3b341"></span>ZLR</span>');
  chips.push('<span class="chip"><span class="sw" style="background:#ce93d8"></span>HFE</span>');
  chips.push('<span class="chip">▼ short entry · ▲ long entry · ◆ exit</span>');
  el.innerHTML = chips.join("");
}

function buildNotes(DATA) {
  const el = document.getElementById("notes");
  const out = [];
  const miss = [];
  const lv = DATA.levels;
  if (!lv) {
    miss.push("levels (IBH/IBL/POC/VAH/VAL)");
  } else {
    // Partial-levels honesty: IB may be real (from bars) while the TPO profile
    // levels (POC/VAH/VAL) still need the Mac export.
    const tpoMiss = [];
    if (lv.poc == null) tpoMiss.push("POC");
    if (lv.vah == null) tpoMiss.push("VAH");
    if (lv.val == null) tpoMiss.push("VAL");
    if (tpoMiss.length) miss.push(tpoMiss.join("/") + " (TPO profile)");
  }
  if (!DATA.has_volume) miss.push("per-bar volume");
  if (!DATA.has_cvd) miss.push("CVD (cumulative_delta)");
  if (!DATA.day_type) miss.push("day-type");
  if (miss.length) {
    out.push('<span class="note miss">Not exported yet (run '
      + 'export_replay_data.py on the Mac): ' + miss.join(", ")
      + '. These are shown as "missing" above — never synthesized.</span>');
  }
  if (DATA.zones && DATA.zones.length) {
    out.push('<div style="margin-top:6px">Expected-direction zones (from '
      + 'config/daytype_playbook.yaml): '
      + DATA.zones.map(z => z.label).join(" · ") + '.</div>');
  } else if (DATA.day_type) {
    out.push('<div style="margin-top:6px">No per-price-zone tint for '
      + DATA.day_type + ' (playbook defines continuation/with-trend, not fade '
      + 'levels) — header states the expectation instead. Honest: a zone the '
      + 'playbook is silent on is left neutral.</div>');
  }
  el.innerHTML = out.join("");
}

function buildTradeTable(DATA, fmt) {
  const trades = DATA.trades || [];
  if (!trades.length) return;
  const rows = trades.map(t => {
    const pnl = t.pnl_usd;
    const cls = (pnl == null) ? "" : (pnl >= 0 ? "pos" : "neg");
    const pnlTxt = (pnl == null) ? "—" : (pnl >= 0 ? "+$"+fmt(pnl,0) : "-$"+fmt(Math.abs(pnl),0));
    return "<tr>"
      + "<td class='l'>#" + t.id + "</td>"
      + "<td class='l'>S" + (t.system==null?"?":t.system) + "</td>"
      + "<td class='l'>" + (t.direction||"—") + "</td>"
      + "<td class='l'>" + (t.pattern_id||"—") + "</td>"
      + "<td>" + (t.entry_ts? t.entry_ts.slice(11,16):"—") + "</td>"
      + "<td>" + fmt(t.entry_price) + "</td>"
      + "<td>" + (t.exit_ts? t.exit_ts.slice(11,16):"—") + "</td>"
      + "<td>" + fmt(t.exit_price) + "</td>"
      + "<td class='" + cls + "'>" + pnlTxt + "</td>"
      + "<td class='l'>" + (t.outcome||"—") + "</td>"
      + "<td class='l'>" + (t.day_type||"—") + "</td>"
      + "</tr>";
  }).join("");
  document.getElementById("tradetable").innerHTML =
    "<table class='tr'><thead><tr>"
    + "<th class='l'>id</th><th class='l'>sys</th><th class='l'>dir</th>"
    + "<th class='l'>pattern</th><th>entry</th><th>px</th><th>exit</th>"
    + "<th>px</th><th>pnl</th><th class='l'>outcome</th><th class='l'>day-type</th>"
    + "</tr></thead><tbody>" + rows + "</tbody></table>";
}
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description="Render MEMS26 replay HTML from JSON (no DB).")
    ap.add_argument("--date", required=True, help="Trading date YYYY-MM-DD.")
    ap.add_argument("--data", default=None, help="Input JSON (default tools/replay_data_<date>.json).")
    ap.add_argument("--out", default=None, help="Output HTML (default tools/replay_<date>.html).")
    ap.add_argument("--playbook", default=DEFAULT_PLAYBOOK, help="daytype_playbook.yaml path.")
    args = ap.parse_args()

    data_path = args.data or os.path.join(HERE, f"replay_data_{args.date}.json")
    out_path = args.out or os.path.join(HERE, f"replay_{args.date}.html")

    if not os.path.exists(data_path):
        print(f"ERROR: data file not found: {data_path}\n"
              f"Run on the Mac first: python3 tools/export_replay_data.py --date {args.date}",
              file=sys.stderr)
        sys.exit(1)

    data = load_data(data_path)
    style = parse_daytype_style(args.playbook)
    playbook_found = bool(style)

    day_type = data.get("day_type")
    levels = data.get("levels")
    expectation = _human_expectation(day_type, style)
    zones = build_zones(day_type, levels, style)

    bars = data.get("bars", [])
    has_volume = any((b.get("volume") not in (None, 0)) for b in bars)
    cvd = data.get("cvd", [])
    has_cvd = bool(cvd) and any(p.get("cumulative_delta") is not None for p in cvd)

    html = render_html(data, day_type, expectation, zones, levels,
                       has_volume, has_cvd, playbook_found)
    with open(out_path, "w") as fh:
        fh.write(html)

    print(f"Wrote {out_path}")
    print(f"  bars={len(bars)} trades={len(data.get('trades',[]))} "
          f"levels={'yes' if levels else 'MISSING'} "
          f"volume={'yes' if has_volume else 'MISSING'} "
          f"cvd={'yes' if has_cvd else 'MISSING'} "
          f"day_type={day_type or 'MISSING'} "
          f"zones={len(zones)} playbook={'yes' if playbook_found else 'MISSING'}")


if __name__ == "__main__":
    main()
