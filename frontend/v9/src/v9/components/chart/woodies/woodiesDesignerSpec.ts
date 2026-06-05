/**
 * Woody CCI Panel — Designer Spec v1.0 (17 May 2026)
 * Coordinates are in 480×360 content space unless noted.
 */

export type WoodiesChartBar = {
  ts_unix: number;
  cci_14: number;
  cci_14_prev?: number | null;
  cci_14_3ago?: number | null;
  cci_6_tcci?: number | null;
  ccidiff?: number | null;
  /** Sierra export (Agent 2) — CCI-14 minus TCCI at bar High */
  ccidiff_h?: number | null;
  /** Sierra export (Agent 2) — CCI-14 minus TCCI at bar Low */
  ccidiff_l?: number | null;
  predictor_cci_high?: number | null;
  predictor_cci_low?: number | null;
  prev_high?: number | null;
  prev_low?: number | null;
  trend_state: string;
  trend_color: string;
  zlr_detected?: boolean;
  zlr_direction?: string;
  hfe_detected?: boolean;
  hfe_direction?: string | null;
  close?: number | null;
  open?: number | null;
  high?: number | null;
  low?: number | null;
  lsma_value?: number | null;
  lsma_above_price?: boolean;
  predictor_next_cci?: number | null;
  proj_hi?: number | null;
  proj_lo?: number | null;
  low_prev_angle?: number | null;
  swi_value?: number | null;
  czi_value?: number | null;
  ema_34?: number | null;
};

export const CONTENT_W = 480;
export const CONTENT_H = 360;
export const TITLE_H = 22;
export const TOOLBAR_H = 22;
export const FULL_H = TITLE_H + CONTENT_H + TOOLBAR_H;

export const MIN_PANEL_W = 380;
export const MAX_PANEL_W = 600;
export const MIN_PANEL_H = 240;
export const MAX_PANEL_H = 500;

export const ROW = {
  CHART_TOP: 44,
  CHART_BOTTOM: 340,
  BASELINE: 192,
  TIME_TOP: 340,
  TIME_BOTTOM: 360,
} as const;

export const COL = {
  CHART_L: 22,
  /** Histogram + CCI lines end here; data HUD sits right of this */
  CHART_R: 318,
  /** Dotted guides + CCI/TCCI end here (§5.3 — not into frame/axis) */
  REF_END: 432,
  /** Data values right-aligned just left of frame (§5.11) */
  DATA_R: 432,
  /** Vertical separator (§5.10) */
  FRAME_X: 434,
  /** Axis labels start here — entire label must stay right of FRAME_X (§5.10) */
  AXIS_LABEL_X: 448,
  /** Legacy right-anchor (Sierra x=498); prefer AXIS_LABEL_X + left align in UI */
  AXIS_ANCHOR_X: CONTENT_W - 2,
} as const;

/** Chart + margin above time strip (§2 rows) */
export const CHART_REGION_H = ROW.TIME_TOP;
export const TIME_REGION_H = CONTENT_H - ROW.TIME_TOP;

export const BAR = {
  WIDTH: 6,
  GAP: 3,
  SLOT: 9,
  COUNT: 30,
  FIRST_X: 28,
  LAST_X: 312,
} as const;

export const REF_LINES = [
  { v: 200, y: 69, color: '#DC2020', marker: '#22CC22' },
  { v: 100, y: 130, color: '#22BBBB', marker: '#22BBBB' },
  { v: 0, y: 192, color: '#22CC22', marker: '#22CC22' },
  { v: -100, y: 254, color: '#22BBBB', marker: '#22BBBB' },
  { v: -200, y: 315, color: '#DC2020', marker: '#22CC22' },
] as const;

export const AXIS_TICKS = [
  { v: 240, y: 48, color: '#5EB8FF', size: 9 },
  { v: 200, y: 72, color: '#FF2020', size: 9 },
  { v: 160, y: 96, color: '#5EB8FF', size: 9 },
  { v: 120, y: 120, color: '#5EB8FF', size: 9 },
  { v: 80, y: 144, color: '#5EB8FF', size: 9 },
  { v: 40, y: 168, color: '#5EB8FF', size: 9 },
  { v: 0, y: 195, color: '#22CC22', size: 10 },
  { v: -40, y: 216, color: '#5EB8FF', size: 9 },
  { v: -80, y: 240, color: '#5EB8FF', size: 9 },
  { v: -120, y: 264, color: '#5EB8FF', size: 9 },
  { v: -160, y: 288, color: '#5EB8FF', size: 9 },
  { v: -200, y: 318, color: '#FF2020', size: 9 },
  { v: -240, y: 342, color: '#5EB8FF', size: 9 },
] as const;

/** §5.12 — 4 above Last @ CCI 0, 5 below; 11px bold HUD, 22px Last */
export const DATA_SLOTS = [
  { id: 'diff-g', y: 56, color: '#00DD00', size: 11, bold: true },
  { id: 'diff-w', y: 88, color: '#FFFFFF', size: 11, bold: true },
  { id: 'diff-m', y: 120, color: '#FF66FF', size: 11, bold: true },
  { id: 'hi', y: 156, color: '#00DD00', size: 11, bold: true },
  /** Last Price on CCI zero line (§5.12 y=192) — largest HUD row */
  { id: 'last', y: ROW.BASELINE, color: '#000000', size: 22, bold: true },
  { id: 'lo', y: 232, color: '#000000', size: 11, bold: true },
  { id: 'phi', y: 262, color: '#5EB8FF', size: 11, bold: true },
  { id: 'plo', y: 290, color: '#FF66FF', size: 11, bold: true },
  { id: 'cci', y: 318, color: '#000000', size: 11, bold: true },
  { id: 'angle', y: 346, color: '#000000', size: 11, bold: true },
] as const;

export const DATA_ABOVE_LAST = 4;
export const DATA_BELOW_LAST = 5;

export const TIME_TICK_X = [24, 79, 109, 139, 169, 199, 229, 259] as const;

export const COLORS = {
  BG: '#2D5555',
  BORDER: '#1A3A3A',
  TIME_BG: '#2A4A4A',
  TIME_TEXT: '#DDDD20',
  TITLE_ORANGE: '#fb950b',
  /** §5.6 — CCI-14 main line (black in Sierra — histogram follows this line) */
  CCI_14: '#000000',
  /** §5.7 — TCCI / CCI-6 turbo line (yellow in Sierra) */
  TCCI: '#DDDD20',
  ZLR_DOWN: '#FF2020',
  ZLR_UP: '#00CC00',
  LE_BADGE: '#22CC22',
} as const;

/** §5.6 / §5.7 stroke width for CCI series lines */
export const CCI_LINE_WIDTH = 2.5;

export const DEFAULT_CCI_MAX = 250;
export const MIN_CCI_MAX = 50;
export const MAX_CCI_MAX = 400;
export const DEFAULT_BAR_COUNT = 100;
export const MIN_BAR_COUNT = 10;
export const MAX_BAR_COUNT = 200;
export const API_BAR_LIMIT = 200;

/** Snap Y-scale to integer steps; default ±240 (§5.10). */
export function snapCciMax(raw: number): number {
  const n = Math.round(raw);
  return Math.min(MAX_CCI_MAX, Math.max(MIN_CCI_MAX, n));
}

export function formatAxisTickLabel(v: number): string {
  if (v === 0) return '0';
  return String(v);
}

const Y_TOP = 48;
const Y_ZERO = ROW.BASELINE;

/** Map CCI → spec Y; at default zoom use fixed §5.3 / §5.10 coordinates */
export function cciToSpecY(cci: number, cciMax = DEFAULT_CCI_MAX): number {
  if (cciMax === DEFAULT_CCI_MAX) {
    const fixed = REF_LINES.find((r) => r.v === cci);
    if (fixed) return fixed.y;
    const axis = AXIS_TICKS.find((t) => t.v === cci);
    if (axis) return axis.y;
  }
  return Y_ZERO - (cci / cciMax) * (Y_ZERO - Y_TOP);
}

export function refLinesForRange(cciMax: number) {
  if (cciMax === DEFAULT_CCI_MAX) {
    return REF_LINES.map((r) => ({
      v: r.v,
      y: r.y,
      color: r.color,
      marker: r.marker,
    }));
  }
  const levels = [200, 100, 0, -100, -200];
  return levels
    .filter((v) => Math.abs(v) <= cciMax)
    .map((v) => {
      const base = REF_LINES.find((r) => r.v === v);
      return {
        v,
        y: cciToSpecY(v, cciMax),
        color: base?.color ?? '#22BBBB',
        marker: base?.marker ?? '#22BBBB',
      };
    });
}

export type AxisTick = { v: number; y: number; color: string; size: number };

/** Axis labels rescale when Y zoom changes (§6.7); fixed layout at default zoom */
export function buildAxisTicksForRange(cciMax: number): AxisTick[] {
  if (cciMax === DEFAULT_CCI_MAX) {
    return AXIS_TICKS.map((t) => ({ v: t.v, y: t.y, color: t.color, size: t.size }));
  }
  const raw = [240, 200, 160, 120, 80, 40, 0, -40, -80, -120, -160, -200, -240];
  const scale = cciMax / DEFAULT_CCI_MAX;
  const seen = new Set<number>();
  const out: AxisTick[] = [];
  for (const base of raw) {
    const v = Math.round(base * scale);
    if (Math.abs(v) > cciMax || seen.has(v)) continue;
    seen.add(v);
    let color = '#5EB8FF';
    if (v === 0) color = '#22CC22';
    else if (Math.abs(v) === Math.round((200 * cciMax) / DEFAULT_CCI_MAX)) color = '#FF2020';
    out.push({ v, y: cciToSpecY(v, cciMax), color, size: v === 0 ? 11 : 10 });
  }
  return out.sort((a, b) => b.v - a.v);
}

export function sliceBarWindow(
  bars: WoodiesChartBar[],
  endIndex: number,
  count: number,
): WoodiesChartBar[] {
  if (bars.length === 0) return [];
  const end = Math.max(0, Math.min(bars.length - 1, endIndex));
  const start = Math.max(0, end - count + 1);
  return bars.slice(start, end + 1);
}

/** Shallow clone bars for historical chart freeze (HUD stays on live tick). */
export function cloneBarWindow(bars: WoodiesChartBar[]): WoodiesChartBar[] {
  return bars.map((b) => ({ ...b }));
}

/**
 * Historical view: chart must not tick with market; only refresh snapshot when pan/zoom key changes.
 */
export function resolveChartPaintBars(
  atLive: boolean,
  liveWindow: WoodiesChartBar[],
  frozen: WoodiesChartBar[] | null,
  viewKey: string,
  frozenKey: string,
): { bars: WoodiesChartBar[]; frozen: WoodiesChartBar[] | null; frozenKey: string } {
  if (atLive) {
    return { bars: liveWindow, frozen: null, frozenKey: '' };
  }
  if (frozen && frozenKey === viewKey) {
    return { bars: frozen, frozen, frozenKey };
  }
  const snap = cloneBarWindow(liveWindow);
  return { bars: snap, frozen: snap, frozenKey: viewKey };
}

export function visibleBars(bars: WoodiesChartBar[]): WoodiesChartBar[] {
  return bars.length <= BAR.COUNT ? bars : bars.slice(-BAR.COUNT);
}

export function barCenterX(index: number, barCount: number): number {
  if (barCount <= 1) return BAR.FIRST_X;
  const span = BAR.LAST_X - BAR.FIRST_X;
  return BAR.FIRST_X + (index / (barCount - 1)) * span;
}

/** §5.3 — dotted guides end at chart/HUD boundary (x≈318), not into data values. */
export function refGuideLineEndX(_showDataColumn?: boolean): number {
  return COL.CHART_R;
}

export function chartSeriesClipRight(_showDataColumn?: boolean): number {
  return COL.CHART_R;
}

/** §5.2 — Sierra title shows 1.00 on active trend bucket, 0.00 on others. */
export function trendHeaderValues(bar: WoodiesChartBar | null): {
  down: number;
  neutral: number;
  up: number;
} {
  const s = (bar?.trend_state || 'GRAY').toUpperCase();
  return {
    down: s === 'RED' ? 1 : 0,
    neutral: s === 'YELLOW' ? 1 : 0,
    up: s === 'BLUE' ? 1 : 0,
  };
}

/** Narrower histogram rects when many bars are visible (50–60 default). */
export function histogramBarWidth(barCount: number): number {
  if (barCount <= 1) return BAR.WIDTH;
  const slot = (BAR.LAST_X - BAR.FIRST_X) / (barCount - 1);
  return Math.min(BAR.WIDTH, Math.max(2, Math.floor(slot) - 1));
}

/** Min horizontal gap between time-label centers (§5.13 — no overlap). */
export const TIME_LABEL_MIN_GAP_PX = 48;

export type TimeAxisLabel = { key: string; label: string; x: number; align: 'left' | 'center' };

/** Resolve per-bar timestamps when export repeats the same ts on every tick. */
export function barTimestampsUnix(bars: WoodiesChartBar[], barStepS = 300): number[] {
  const n = bars.length;
  if (n === 0) return [];
  const endTs = bars[n - 1].ts_unix;
  return bars.map((bar, idx) => {
    const raw = bar.ts_unix;
    if (idx > 0 && raw === bars[idx - 1].ts_unix) {
      return endTs - (n - 1 - idx) * barStepS;
    }
    return raw;
  });
}

/**
 * Date at first bar (left-aligned); time ticks decimated to MIN_GAP so labels never stack.
 */
export function buildTimeAxisLabels(
  bars: WoodiesChartBar[],
  formatDate: (tsUnix: number) => string,
  formatTime: (tsUnix: number) => string,
  minGapPx = TIME_LABEL_MIN_GAP_PX,
): TimeAxisLabel[] {
  const n = bars.length;
  if (n === 0) return [];

  const tsList = barTimestampsUnix(bars);
  const xs = Array.from({ length: n }, (_, i) => barCenterX(i, n));
  const span = Math.max(1, xs[n - 1] - xs[0]);
  const maxTicks = Math.max(2, Math.floor(span / minGapPx) + 1);

  const out: TimeAxisLabel[] = [
    { key: 'date', label: formatDate(tsList[0]), x: xs[0], align: 'left' },
  ];

  const timeTickBudget = Math.max(1, maxTicks - 1);
  const rawIndices: number[] = [];
  if (timeTickBudget === 1) {
    rawIndices.push(n - 1);
  } else {
    for (let k = 0; k < timeTickBudget; k++) {
      rawIndices.push(Math.round((k / (timeTickBudget - 1)) * (n - 1)));
    }
  }

  const seenIdx = new Set<number>();
  let lastX = xs[0];
  const minGapFromDate = minGapPx + 12;

  for (const idx of rawIndices) {
    if (seenIdx.has(idx)) continue;
    seenIdx.add(idx);
    if (idx === 0) continue;

    const x = xs[idx];
    const gap = idx === 1 ? minGapFromDate : minGapPx;
    if (x - lastX < gap) continue;

    const label = formatTime(tsList[idx]);
    if (out.some((t) => t.label === label)) continue;

    out.push({ key: `t-${idx}`, label, x, align: 'center' });
    lastX = x;
  }

  if (n > 1 && !seenIdx.has(n - 1)) {
    const x = xs[n - 1];
    const label = formatTime(tsList[n - 1]);
    if (
      x - lastX >= minGapPx &&
      !out.some((t) => t.label === label) &&
      x - xs[0] >= minGapFromDate
    ) {
      out.push({ key: `t-${n - 1}`, label, x, align: 'center' });
    }
  }

  return out;
}

/** Core CCIDiff (white row): CCI-14 minus TCCI at current bar. */
export function cciMinusTcci(bar: WoodiesChartBar): number | null {
  if (bar.cci_6_tcci == null) return null;
  return bar.cci_14 - bar.cci_6_tcci;
}

/** Geometric angle (degrees) of the line through two bar lows (§5.12 row 10). */
export function computeLowLineAngleDeg(prevLow: number, curLow: number): number {
  const dy = curLow - prevLow;
  const dx = BAR.SLOT;
  return Math.round((Math.atan2(dy, dx) * 180) / Math.PI * 10) / 10;
}

export function previousBarForDisplay(
  allBars: WoodiesChartBar[],
  displayBar: WoodiesChartBar | null,
  windowBars: WoodiesChartBar[],
): WoodiesChartBar | null {
  if (!displayBar) return null;
  const inWindow = windowBars.findIndex((b) => b.ts_unix === displayBar.ts_unix);
  if (inWindow > 0) return windowBars[inWindow - 1] ?? null;
  const inAll = allBars.findIndex((b) => b.ts_unix === displayBar.ts_unix);
  if (inAll > 0) return allBars[inAll - 1] ?? null;
  if (windowBars.length >= 2) return windowBars[windowBars.length - 2] ?? null;
  if (allBars.length >= 2) return allBars[allBars.length - 2] ?? null;
  return null;
}

/** Sierra §5.12: "47.01 CCIDiff H" | "47.01 CCIDiff" | "47.01 CCIDiff L" */
function formatCciDiffRow(
  value: number | null | undefined,
  variant: 'H' | 'mid' | 'L',
): string {
  if (value == null || !Number.isFinite(value)) return '—';
  const suffix =
    variant === 'mid' ? ' CCIDiff' : variant === 'H' ? ' CCIDiff H' : ' CCIDiff L';
  return `${value.toFixed(2)}${suffix}`;
}

export function buildDataTexts(
  bar: WoodiesChartBar,
  prevBar?: WoodiesChartBar | null,
): Record<string, string> {
  // Use Sierra Panel's CCIDiff when available (bar.ccidiff), fallback to local computation
  const midDiff = bar.ccidiff ?? cciMinusTcci(bar);

  const prevHigh = prevBar?.high ?? bar.prev_high;
  const prevLow = prevBar?.low ?? bar.prev_low;
  const hi =
    prevHigh != null && bar.high != null
      ? `${prevHigh.toFixed(2)} ${bar.high.toFixed(2)} Hig`
      : '—';
  const last = bar.close != null ? `${bar.close.toFixed(2)} Last` : '—';
  const lo =
    prevLow != null && bar.low != null
      ? `${prevLow.toFixed(2)} ${bar.low.toFixed(2)} Low`
      : '—';

  const phi = bar.proj_hi != null ? `${bar.proj_hi.toFixed(2)} ProjHigh` : '—';
  const plo = bar.proj_lo != null ? `${bar.proj_lo.toFixed(2)} ProjLow` : '—';

  let cci = '—';
  if (bar.predictor_next_cci != null) {
    const predHi = bar.predictor_cci_high ?? bar.predictor_next_cci;
    const predLo = bar.predictor_cci_low ?? bar.predictor_next_cci;
    cci = `${predHi.toFixed(1)}  ${predLo.toFixed(1)} CCI Pre`;
  }

  let angle = '—';
  if (bar.low_prev_angle != null && Number.isFinite(bar.low_prev_angle)) {
    angle = `${bar.low_prev_angle.toFixed(1)}° Low Prev/Cur`;
  } else if (prevLow != null && bar.low != null) {
    angle = `${computeLowLineAngleDeg(prevLow, bar.low).toFixed(1)}° Low Prev/Cur`;
  }

  return {
    'diff-g': formatCciDiffRow(bar.ccidiff_h, 'H'),
    'diff-w':
      midDiff != null && Number.isFinite(midDiff) ? formatCciDiffRow(midDiff, 'mid') : '—',
    'diff-m': formatCciDiffRow(bar.ccidiff_l, 'L'),
    hi,
    last,
    lo,
    phi,
    plo,
    cci,
    angle,
  };
}

export function pctX(x: number): string {
  return `${(x / CONTENT_W) * 100}%`;
}

export function pctY(y: number): string {
  return `${(y / CONTENT_H) * 100}%`;
}
