'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  API_BAR_LIMIT,
  BAR,
  buildAxisTicksForRange,
  buildDataTexts,
  previousBarForDisplay,
  CHART_REGION_H,
  COL,
  COLORS,
  CONTENT_H,
  CONTENT_W,
  CCI_LINE_WIDTH,
  TIME_REGION_H,
  DATA_SLOTS,
  DEFAULT_BAR_COUNT,
  DEFAULT_CCI_MAX,
  FULL_H,
  MAX_BAR_COUNT,
  MAX_CCI_MAX,
  MAX_PANEL_H,
  MAX_PANEL_W,
  MIN_BAR_COUNT,
  MIN_CCI_MAX,
  MIN_PANEL_H,
  MIN_PANEL_W,
  refLinesForRange,
  refGuideLineEndX,
  chartSeriesClipRight,
  trendHeaderValues,
  ROW,
  buildTimeAxisLabels,
  histogramBarWidth,
  resolveChartPaintBars,
  sliceBarWindow,
  snapCciMax,
  formatAxisTickLabel,
  TITLE_H,
  TOOLBAR_H,
  barCenterX,
  cciToSpecY,
  type WoodiesChartBar,
} from './woodiesDesignerSpec';

export type { WoodiesChartBar };

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const LS_W = 'mems26-woodies-panel-w';
const LS_H = 'mems26-woodies-panel-h';
const LS_LEFT = 'mems26-woodies-panel-left';
const LS_BOTTOM = 'mems26-woodies-panel-bottom';
const LS_CCI_MAX = 'mems26-woodies-panel-cci-max';

const DEFAULT_W = CONTENT_W;
const DEFAULT_H = FULL_H;

function loadNum(key: string, fallback: number, min: number, max: number): number {
  if (typeof window === 'undefined') return fallback;
  const v = Number(localStorage.getItem(key));
  if (!Number.isFinite(v)) return fallback;
  return Math.min(max, Math.max(min, v));
}

function loadCciMax(): number {
  const v = loadNum(LS_CCI_MAX, DEFAULT_CCI_MAX, MIN_CCI_MAX, MAX_CCI_MAX);
  if (Math.abs(v - Math.round(v)) > 0.01) return DEFAULT_CCI_MAX;
  return snapCciMax(v);
}

const TREND_BAR_COLOR: Record<string, string> = {
  BLUE: '#1E54E8',
  RED: '#E03030',
  YELLOW: '#DDDD20',
  GRAY: '#888888',
};

function histogramTrend(bar: WoodiesChartBar): string | null {
  const s = (bar.trend_state || 'GRAY').toUpperCase();
  return TREND_BAR_COLOR[s] ?? TREND_BAR_COLOR.GRAY;
}

// MES trades on CME (Chicago). Sierra Chart displays in CT (America/Chicago).
// Using New_York (EDT=UTC-4) caused 1h drift vs Sierra in summer (CDT=UTC-5).
function formatEtTime(tsUnix: number): string {
  return new Date(tsUnix * 1000).toLocaleTimeString('en-US', {
    timeZone: 'America/Chicago',
    hour: 'numeric',
    minute: '2-digit',
    hour12: false,
  });
}

function formatEtDate(tsUnix: number): string {
  return new Date(tsUnix * 1000).toLocaleDateString('en-US', {
    timeZone: 'America/Chicago',
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
  });
}

/** ZLR on +200 line (above CCI 0): red marker, tip points down toward zero. */
function drawZlrDown(ctx: CanvasRenderingContext2D, x: number, y: number) {
  ctx.fillStyle = COLORS.ZLR_DOWN;
  ctx.beginPath();
  ctx.moveTo(x, y + 11);
  ctx.lineTo(x - 4, y);
  ctx.lineTo(x + 4, y);
  ctx.closePath();
  ctx.fill();
  ctx.font = 'bold 9px ui-monospace, monospace';
  ctx.fillStyle = COLORS.ZLR_DOWN;
  ctx.textAlign = 'center';
  ctx.fillText('ZLR', x, y - 4);
  ctx.textAlign = 'left';
}

/** ZLR on -200 line (below CCI 0): green marker, tip points up toward zero. */
function drawZlrUp(ctx: CanvasRenderingContext2D, x: number, y: number) {
  ctx.fillStyle = COLORS.ZLR_UP;
  ctx.beginPath();
  ctx.moveTo(x, y - 11);
  ctx.lineTo(x - 4, y);
  ctx.lineTo(x + 4, y);
  ctx.closePath();
  ctx.fill();
  ctx.font = 'bold 9px ui-monospace, monospace';
  ctx.fillStyle = COLORS.ZLR_UP;
  ctx.textAlign = 'center';
  ctx.fillText('ZLR', x, y + 14);
  ctx.textAlign = 'left';
}

/** HFE (Hook From Extreme) marker — small diamond at the CCI value. */
function drawHfe(ctx: CanvasRenderingContext2D, x: number, y: number, direction: string) {
  const color = direction.toUpperCase() === 'DOWN' ? '#FF6600' : '#00BBFF';
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(x, y - 5);
  ctx.lineTo(x + 4, y);
  ctx.lineTo(x, y + 5);
  ctx.lineTo(x - 4, y);
  ctx.closePath();
  ctx.fill();
  ctx.font = 'bold 7px ui-monospace, monospace';
  ctx.fillStyle = color;
  ctx.textAlign = 'center';
  ctx.fillText('HFE', x, y - 8);
  ctx.textAlign = 'left';
}

/** §5.3–5.4 — thick dots alternating line + left-edge marker colors (Sierra). */
function drawAlternatingRefLine(
  ctx: CanvasRenderingContext2D,
  y: number,
  x0: number,
  x1: number,
  colorA: string,
  colorB: string,
) {
  const step = 8;
  let i = 0;
  for (let x = x0; x <= x1; x += step) {
    ctx.fillStyle = i % 2 === 0 ? colorA : colorB;
    ctx.beginPath();
    ctx.arc(x, y, 1.75, 0, Math.PI * 2);
    ctx.fill();
    i += 1;
  }
  ctx.fillStyle = colorB;
  ctx.beginPath();
  ctx.arc(x0 + 2, y, 2.2, 0, Math.PI * 2);
  ctx.fill();
}

function drawCurrentX(ctx: CanvasRenderingContext2D, x: number, y: number) {
  ctx.strokeStyle = '#FFFFFF';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(x - 5, y - 5);
  ctx.lineTo(x + 5, y + 5);
  ctx.moveTo(x - 5, y + 5);
  ctx.lineTo(x + 5, y - 5);
  ctx.stroke();
}

type DrawOpts = {
  cciMax: number;
  showLiveMarker: boolean;
  dimmed: boolean;
  showDataColumn: boolean;
};

/** Canvas paint in 480×360 designer space (§5.3–5.9) */
function drawContentCanvas(
  ctx: CanvasRenderingContext2D,
  bars: WoodiesChartBar[],
  opts: DrawOpts,
) {
  ctx.fillStyle = COLORS.BG;
  ctx.fillRect(0, 0, CONTENT_W, CHART_REGION_H);

  const guideEndX = refGuideLineEndX(opts.showDataColumn);
  const seriesRight = chartSeriesClipRight(opts.showDataColumn);

  for (const ref of refLinesForRange(opts.cciMax)) {
    drawAlternatingRefLine(ctx, ref.y, COL.CHART_L, guideEndX, ref.color, ref.marker);
  }

  const n = bars.length;
  if (n === 0) return;

  const histRight = COL.CHART_R;
  const alpha = opts.dimmed ? 0.5 : 1;

  ctx.save();
  ctx.beginPath();
  ctx.rect(COL.CHART_L, ROW.CHART_TOP, histRight - COL.CHART_L, ROW.CHART_BOTTOM - ROW.CHART_TOP);
  ctx.clip();
  ctx.globalAlpha = alpha;

  const y0 = cciToSpecY(0, opts.cciMax);
  const histW = histogramBarWidth(n);

  // §5.8 — Sidewinder bands: green dots (trending SWI>40) / red dots (flat SWI<20)
  // around zero line, matching Sierra's Sidewinder visual.
  bars.forEach((bar, i) => {
    const swi = bar.swi_value;
    if (swi != null && Number.isFinite(swi)) {
      const cx = barCenterX(i, n);
      const absSWI = Math.abs(swi);
      // Green = trending (|SWI| > 40), Red = flat/chop (|SWI| < 20), Yellow = transition
      let dotColor: string;
      if (absSWI >= 40) dotColor = '#22CC22';      // green — trending
      else if (absSWI <= 20) dotColor = '#CC2020';  // red — flat/chop
      else dotColor = '#CCCC20';                     // yellow — transition
      // Draw small dot above and below zero line
      ctx.fillStyle = dotColor;
      ctx.globalAlpha = 0.7;
      ctx.beginPath();
      ctx.arc(cx, y0 - 4, 1.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(cx, y0 + 4, 1.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = alpha;
    }
  });

  bars.forEach((bar, i) => {
    const cx = barCenterX(i, n);
    const y1 = cciToSpecY(bar.cci_14, opts.cciMax);
    const barColor = histogramTrend(bar);
    if (barColor) {
      const bh = Math.max(2, Math.abs(y1 - y0));
      const by = Math.min(y0, y1);
      ctx.fillStyle = barColor;
      ctx.fillRect(cx - histW / 2, by, histW, bh);
    }
  });
  ctx.globalAlpha = 1;
  ctx.restore();

  ctx.save();
  ctx.beginPath();
  ctx.rect(COL.CHART_L, ROW.CHART_TOP, seriesRight - COL.CHART_L, ROW.CHART_BOTTOM - ROW.CHART_TOP);
  ctx.clip();
  ctx.globalAlpha = alpha;

  const yLine200 = cciToSpecY(200, opts.cciMax);
  const yLineMinus200 = cciToSpecY(-200, opts.cciMax);
  bars.forEach((bar, i) => {
    const cx = barCenterX(i, n);
    if (bar.zlr_detected) {
      const down = (bar.zlr_direction || '').toUpperCase() === 'DOWN';
      if (down) drawZlrDown(ctx, cx, yLine200);
      else drawZlrUp(ctx, cx, yLineMinus200);
    }
    if (bar.hfe_detected) {
      const yCci = cciToSpecY(bar.cci_14, opts.cciMax);
      drawHfe(ctx, cx, yCci, bar.hfe_direction || 'UP');
    }
  });

  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';

  // §5.6 — CCI-14 (yellow, per Sierra) under §5.7 TCCI (black)
  ctx.lineWidth = CCI_LINE_WIDTH;
  ctx.strokeStyle = COLORS.CCI_14;
  ctx.beginPath();
  bars.forEach((bar, i) => {
    const x = barCenterX(i, n);
    const y = cciToSpecY(bar.cci_14, opts.cciMax);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.lineWidth = CCI_LINE_WIDTH;
  ctx.strokeStyle = COLORS.TCCI;
  ctx.beginPath();
  let tcci = false;
  bars.forEach((bar, i) => {
    if (bar.cci_6_tcci == null) return;
    const x = barCenterX(i, n);
    const y = cciToSpecY(bar.cci_6_tcci, opts.cciMax);
    if (!tcci) {
      ctx.moveTo(x, y);
      tcci = true;
    } else ctx.lineTo(x, y);
  });
  if (tcci) ctx.stroke();

  if (opts.showLiveMarker && n > 0) {
    const last = bars[n - 1];
    const lx = barCenterX(n - 1, n);
    const ly = cciToSpecY(last.cci_14, opts.cciMax);
    if (lx <= seriesRight) {
      drawCurrentX(ctx, lx, ly);
    }
  }

  ctx.globalAlpha = 1;
  ctx.restore();
}

function TitleBar({
  bar,
  stale,
  ageS,
  studyCaption,
  maximized,
  onMoveStart,
  onMinimize,
  onMaximize,
  onClose,
}: {
  bar: WoodiesChartBar | null;
  stale: boolean;
  ageS: number | null;
  studyCaption?: string | null;
  maximized: boolean;
  onMoveStart: (e: React.MouseEvent) => void;
  onMinimize: () => void;
  onMaximize: () => void;
  onClose: () => void;
}) {
  const trends = trendHeaderValues(bar);
  const cci = bar?.cci_14;

  return (
    <div
      data-testid="woodies-title-bar"
      onMouseDown={onMoveStart}
      style={{
        height: TITLE_H,
        position: 'relative',
        background: COLORS.BG,
        borderBottom: `2px solid ${stale ? '#EAB308' : COLORS.TITLE_ORANGE}`,
        fontFamily: 'Arial, sans-serif',
        fontSize: 11,
        fontWeight: 700,
        flexShrink: 0,
        cursor: 'move',
      }}
    >
      {[6, 10, 14].map((y) =>
        [6, 10].map((x) => (
          <span
            key={`${x}-${y}`}
            style={{
              position: 'absolute',
              left: x,
              top: y - 4,
              width: 2,
              height: 2,
              borderRadius: '50%',
              background: '#888780',
            }}
          />
        )),
      )}
      <span style={{ position: 'absolute', left: 26, top: 3, color: '#FFFFFF', lineHeight: 1.1 }}>
        Woodies CCI Trend
        {studyCaption ? (
          <span style={{ marginLeft: 6, color: '#7A8080', fontSize: 8, fontWeight: 400 }}>
            {studyCaption}
          </span>
        ) : null}
      </span>
      <span style={{ position: 'absolute', left: 128, top: 4, color: '#7A8080' }}>
        [CCI:{cci != null ? cci.toFixed(2) : '—'}]
      </span>
      <span style={{ position: 'absolute', left: 196, top: 4, color: '#B33B3B' }}>
        TrendDown: {trends.down.toFixed(2)}
      </span>
      <span style={{ position: 'absolute', left: 292, top: 4, color: '#B0A030' }}>
        TrendNeutral: {trends.neutral.toFixed(2)}
      </span>
      <span style={{ position: 'absolute', left: 396, top: 4, color: '#5588FF' }}>
        TrendUp: {trends.up.toFixed(2)}
      </span>
      {stale && ageS != null && (
        <span
          style={{
            position: 'absolute',
            left: 318,
            top: 4,
            color: '#EAB308',
            fontSize: 9,
          }}
        >
          STALE {Math.round(ageS)}s
        </span>
      )}
      <button
        type="button"
        aria-label="Minimize"
        onClick={(e) => {
          e.stopPropagation();
          onMinimize();
        }}
        style={{
          position: 'absolute',
          left: 440,
          top: 2,
          background: 'none',
          border: 'none',
          color: '#888780',
          fontSize: 14,
          cursor: 'pointer',
          padding: 0,
        }}
      >
        ─
      </button>
      <button
        type="button"
        aria-label={maximized ? 'Restore size' : 'Maximize'}
        onClick={(e) => {
          e.stopPropagation();
          onMaximize();
        }}
        style={{
          position: 'absolute',
          left: 455,
          top: 3,
          background: 'none',
          border: 'none',
          color: maximized ? COLORS.TITLE_ORANGE : '#888780',
          fontSize: 12,
          cursor: 'pointer',
          padding: 0,
        }}
      >
        ▢
      </button>
      <button
        type="button"
        aria-label="Close"
        onClick={(e) => {
          e.stopPropagation();
          onClose();
        }}
        style={{
          position: 'absolute',
          left: 470,
          top: 3,
          background: 'none',
          border: 'none',
          color: '#F09595',
          fontSize: 12,
          cursor: 'pointer',
          padding: 0,
        }}
      >
        ✕
      </button>
    </div>
  );
}

const toolBtn: React.CSSProperties = {
  background: 'none',
  border: 'none',
  color: '#A3A39C',
  cursor: 'pointer',
  padding: '0 4px',
  fontFamily: 'inherit',
  fontSize: 10,
};

function Toolbar({
  ageS,
  barCount,
  cciMax,
  onScrollBack,
  onScrollForward,
  onZoomIn,
  onZoomOut,
}: {
  ageS: number | null;
  barCount: number;
  cciMax: number;
  onScrollBack: () => void;
  onScrollForward: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
}) {
  return (
    <div
      style={{
        height: TOOLBAR_H,
        flexShrink: 0,
        background: COLORS.TIME_BG,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '0 8px',
        fontFamily: 'ui-monospace, monospace',
        fontSize: 10,
        color: '#A3A39C',
      }}
    >
      <button type="button" aria-label="Scroll back" onClick={onScrollBack} style={toolBtn}>
        ◀
      </button>
      <button type="button" aria-label="Scroll forward" onClick={onScrollForward} style={toolBtn}>
        ▶
      </button>
      <button type="button" aria-label="Zoom in bars" onClick={onZoomIn} style={toolBtn}>
        −
      </button>
      <button type="button" aria-label="Zoom out bars" onClick={onZoomOut} style={toolBtn}>
        +
      </button>
      <span
        style={{
          padding: '1px 6px',
          borderRadius: 2,
          background: COLORS.TITLE_ORANGE,
          color: '#0A0A0A',
          fontWeight: 700,
        }}
      >
        5m
      </span>
      <span style={{ color: '#5F5E5A' }}>bars {barCount}</span>
      <span style={{ color: '#5F5E5A' }}>Y±{snapCciMax(cciMax)}</span>
      <span style={{ color: '#5F5E5A' }}>poll 2s</span>
      <span style={{ marginLeft: 'auto', color: '#5F5E5A' }}>
        {ageS != null ? `${ageS.toFixed(0)}s` : '—'}
      </span>
    </div>
  );
}

const dataLabelRight = (xPx: number): React.CSSProperties => ({
  position: 'absolute',
  left: xPx,
  transform: 'translate(-100%, -50%)',
  textAlign: 'right',
});

const labelLayer: React.CSSProperties = {
  zIndex: 10,
  pointerEvents: 'none',
};

function ContentViewport({
  allBars,
  windowBars,
  displayBar,
  liveBar,
  scale,
  cciMax,
  atLive,
  stale,
  onTimeZoom,
  onTimeReset,
  onYAxisDrag,
  onYAxisReset,
  onChartWheel,
  onChartPan,
  onChartReset,
  showDataColumn,
  onToggleDataColumn,
}: {
  allBars: WoodiesChartBar[];
  windowBars: WoodiesChartBar[];
  displayBar: WoodiesChartBar | null;
  /** Building bar — Last Price stays live in historical mode (§6.8) */
  liveBar: WoodiesChartBar | null;
  scale: number;
  cciMax: number;
  atLive: boolean;
  stale: boolean;
  /** Time strip drag/wheel: widen/narrow visible bar window */
  onTimeZoom: (dxPx: number) => void;
  onTimeReset: () => void;
  onYAxisDrag: (dyPx: number) => void;
  onYAxisReset: () => void;
  onChartWheel: (deltaY: number) => void;
  onChartPan: (dxPx: number) => void;
  onChartReset: () => void;
  showDataColumn: boolean;
  onToggleDataColumn: () => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  /** HUD always follows live tick (all 10 rows), even when chart is scrolled back */
  const hudBar = liveBar ?? displayBar;
  const prevBar = useMemo(
    () => previousBarForDisplay(allBars, hudBar, windowBars),
    [allBars, hudBar, windowBars],
  );
  const texts = useMemo(() => {
    if (!hudBar) return null;
    return buildDataTexts(hudBar, prevBar);
  }, [hudBar, prevBar]);
  const axisTicks = useMemo(() => buildAxisTicksForRange(cciMax), [cciMax]);

  const timeLabels = useMemo(
    () =>
      buildTimeAxisLabels(windowBars, formatEtDate, formatEtTime),
    [windowBars],
  );

  const timeSpan = useMemo(() => {
    const n = windowBars.length;
    if (n === 0) return { left: 20, width: COL.CHART_R };
    return {
      left: barCenterX(0, n),
      width: Math.max(40, barCenterX(n - 1, n) - barCenterX(0, n)),
    };
  }, [windowBars]);

  const timeDragRef = useRef({ x: 0 });
  const chartPanRef = useRef({ x: 0 });
  const yDragRef = useRef({ y: 0 });

  const bindDrag = (onDelta: (dx: number) => void, getX: () => number, setX: (x: number) => void) => {
    return (e: React.MouseEvent) => {
      e.preventDefault();
      setX(e.clientX);
      const onMove = (ev: MouseEvent) => {
        onDelta(ev.clientX - getX());
        setX(ev.clientX);
      };
      const onUp = () => {
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onUp);
      };
      window.addEventListener('mousemove', onMove);
      window.addEventListener('mouseup', onUp);
    };
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = CONTENT_W * dpr;
    canvas.height = CHART_REGION_H * dpr;
    canvas.style.width = `${CONTENT_W}px`;
    canvas.style.height = `${CHART_REGION_H}px`;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    drawContentCanvas(ctx, windowBars, {
      cciMax,
      showLiveMarker: atLive,
      dimmed: stale,
      showDataColumn,
    });
  }, [windowBars, cciMax, atLive, stale, showDataColumn]);

  const sy = (y: number) => y * scale;
  const sx = (x: number) => x * scale;
  const chartPxH = CHART_REGION_H * scale;

  return (
    <div
      style={{
        position: 'relative',
        width: sx(CONTENT_W),
        height: sy(CONTENT_H),
        overflow: 'hidden',
        flexShrink: 0,
        background: COLORS.BG,
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: CONTENT_W,
          height: CHART_REGION_H,
          transform: `scale(${scale})`,
          transformOrigin: 'top left',
        }}
      >
        <canvas
          ref={canvasRef}
          data-testid="woodies-chart-plot"
          style={{ display: 'block', width: CONTENT_W, height: CHART_REGION_H }}
        />
        <div
          data-testid="woodies-chart-pan-zone"
          style={{
            position: 'absolute',
            left: COL.CHART_L,
            top: ROW.CHART_TOP,
            width: COL.DATA_R - COL.CHART_L,
            height: ROW.CHART_BOTTOM - ROW.CHART_TOP,
            cursor: atLive ? 'grab' : 'grabbing',
            zIndex: 3,
          }}
          onMouseDown={bindDrag(
            onChartPan,
            () => chartPanRef.current.x,
            (x) => {
              chartPanRef.current.x = x;
            },
          )}
        />
        <div
          data-testid="woodies-chart-zone"
          style={{
            position: 'absolute',
            left: COL.CHART_L,
            top: ROW.CHART_TOP,
            width: COL.CHART_R - COL.CHART_L,
            height: ROW.CHART_BOTTOM - ROW.CHART_TOP,
            zIndex: 4,
          }}
          onWheel={(e) => {
            e.preventDefault();
            if (e.shiftKey || Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
              onChartPan(-(e.deltaX || e.deltaY));
            } else {
              onChartWheel(e.deltaY);
            }
          }}
          onDoubleClick={(e) => {
            e.preventDefault();
            onChartReset();
          }}
        />
        <div
          data-testid="woodies-y-axis-zone"
          style={{
            position: 'absolute',
            left: COL.FRAME_X,
            top: ROW.CHART_TOP,
            width: CONTENT_W - COL.FRAME_X,
            height: ROW.CHART_BOTTOM - ROW.CHART_TOP,
            cursor: 'ns-resize',
            zIndex: 5,
          }}
          onMouseDown={(e) => {
            e.preventDefault();
            yDragRef.current.y = e.clientY;
            const onMove = (ev: MouseEvent) => {
              onYAxisDrag(ev.clientY - yDragRef.current.y);
              yDragRef.current.y = ev.clientY;
            };
            const onUp = () => {
              window.removeEventListener('mousemove', onMove);
              window.removeEventListener('mouseup', onUp);
            };
            window.addEventListener('mousemove', onMove);
            window.addEventListener('mouseup', onUp);
          }}
          onDoubleClick={(e) => {
            e.preventDefault();
            onYAxisReset();
          }}
        />
      </div>

      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: sx(CONTENT_W),
          height: chartPxH,
          zIndex: 10,
          pointerEvents: 'none',
        }}
      >
        <div
          aria-hidden
          data-testid="woodies-axis-backdrop"
          style={{
            position: 'absolute',
            left: sx(COL.FRAME_X + 1),
            top: sy(ROW.CHART_TOP),
            width: sx(CONTENT_W - COL.FRAME_X - 1),
            height: sy(ROW.CHART_BOTTOM - ROW.CHART_TOP),
            background: COLORS.BG,
            zIndex: 9,
          }}
        />
        {showDataColumn &&
          texts &&
          DATA_SLOTS.map((slot) => {
            const line = texts[slot.id];
            const empty = line === '—';
            return (
              <div
                key={slot.id}
                data-testid={`woodies-data-${slot.id}`}
                style={{
                  ...dataLabelRight(sx(COL.DATA_R)),
                  top: sy(slot.y),
                  color: slot.color,
                  fontSize: slot.size,
                  fontWeight: slot.bold ? 700 : 400,
                  fontFamily: 'ui-monospace, monospace',
                  whiteSpace: 'nowrap',
                  lineHeight: 1.15,
                  zIndex: 11,
                  maxWidth: sx(COL.DATA_R - COL.CHART_R - 6),
                  overflow: 'hidden',
                  opacity: empty ? 0.35 : 1,
                }}
              >
                {line}
              </div>
            );
          })}
        {axisTicks.map((tick) => (
          <div
            key={tick.v}
            data-testid={`woodies-axis-tick-${tick.v}`}
            style={{
              ...dataLabelRight(sx(COL.AXIS_ANCHOR_X)),
              top: sy(tick.y),
              color: tick.color,
              fontSize: tick.size,
              fontWeight: 700,
              fontFamily: 'ui-monospace, monospace',
              zIndex: 12,
            }}
          >
            {formatAxisTickLabel(tick.v)}
          </div>
        ))}
      </div>

      <div
        data-testid="woodies-data-frame"
        title="Double-click: show/hide data column (4 above + 5 below Last)"
        onDoubleClick={(e) => {
          e.preventDefault();
          onToggleDataColumn();
        }}
        style={{
          position: 'absolute',
          left: sx(COL.FRAME_X - 2),
          top: sy(ROW.CHART_TOP),
          width: 6,
          height: sy(ROW.CHART_BOTTOM - ROW.CHART_TOP),
          cursor: 'col-resize',
          zIndex: 11,
        }}
      >
        <div
          aria-hidden
          style={{
            position: 'absolute',
            left: 2,
            top: 0,
            width: 1,
            height: '100%',
            background: COLORS.BORDER,
          }}
        />
      </div>

      <div
        style={{
          position: 'absolute',
          left: 0,
          top: chartPxH,
          width: sx(CONTENT_W),
          height: sy(TIME_REGION_H),
          display: 'flex',
          flexDirection: 'row',
          borderTop: `1px solid ${COLORS.BORDER}`,
          zIndex: 12,
        }}
      >
        <div
          data-testid="woodies-time-axis"
          style={{
            flex: 1,
            position: 'relative',
            background: COLORS.TIME_BG,
            cursor: 'col-resize',
            minWidth: 0,
            overflow: 'hidden',
          }}
          title={`Drag: widen/narrow bars (default ${DEFAULT_BAR_COUNT}). Dbl-click: reset + NOW`}
          onMouseDown={bindDrag(
            onTimeZoom,
            () => timeDragRef.current.x,
            (x) => {
              timeDragRef.current.x = x;
            },
          )}
          onWheel={(e) => {
            e.preventDefault();
            onTimeZoom(e.deltaY + e.deltaX);
          }}
          onDoubleClick={(e) => {
            e.preventDefault();
            onTimeReset();
          }}
        >
          <div
            aria-hidden
            style={{
              position: 'absolute',
              left: sx(timeSpan.left),
              top: 0,
              width: sx(timeSpan.width),
              height: '100%',
              background: 'rgba(35, 62, 62, 0.9)',
              borderLeft: '1px solid rgba(255,255,255,0.12)',
              borderRight: '1px solid rgba(255,255,255,0.12)',
            }}
          />
          {timeLabels.length === 0 ? (
            <span
              style={{
                position: 'absolute',
                left: 8,
                top: '50%',
                transform: 'translateY(-50%)',
                color: COLORS.TIME_TEXT,
                fontSize: 10,
                fontWeight: 700,
                fontFamily: 'ui-monospace, monospace',
              }}
            >
              —
            </span>
          ) : (
            timeLabels.map((t) => (
              <span
                key={t.key}
                style={{
                  position: 'absolute',
                  left: sx(t.x),
                  top: '50%',
                  transform:
                    t.align === 'left' ? 'translateY(-50%)' : 'translate(-50%, -50%)',
                  textAlign: t.align,
                  color: COLORS.TIME_TEXT,
                  fontSize: 10,
                  fontWeight: 700,
                  fontFamily: 'ui-monospace, monospace',
                  whiteSpace: 'nowrap',
                }}
              >
                {t.label}
              </span>
            ))
          )}
        </div>
        <div
          data-testid="woodies-le-badge"
          style={{
            width: sx(44),
            flexShrink: 0,
            background: COLORS.LE_BADGE,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: 10,
            fontWeight: 700,
            fontFamily: 'ui-monospace, monospace',
          }}
        >
          9 L E
        </div>
      </div>
    </div>
  );

}

type PanelMode = 'loading' | 'ready' | 'empty' | 'disconnected';

const MAXIMIZED_W = MAX_PANEL_W;
const MAXIMIZED_H = MAX_PANEL_H;

/** Designer spec v1.0 — 480×360 content + title + toolbar */
export function WoodiesCciPanel({
  visible,
  onVisibilityChange,
}: {
  visible: boolean;
  onVisibilityChange?: (open: boolean) => void;
}) {
  const [panelW, setPanelW] = useState(() => loadNum(LS_W, DEFAULT_W, MIN_PANEL_W, MAX_PANEL_W));
  const [panelH, setPanelH] = useState(() => loadNum(LS_H, DEFAULT_H, MIN_PANEL_H, MAX_PANEL_H));
  const [panelLeft, setPanelLeft] = useState(() => loadNum(LS_LEFT, 8, 0, 2000));
  const [panelBottom, setPanelBottom] = useState(() => loadNum(LS_BOTTOM, 8, 0, 2000));
  const [minimized, setMinimized] = useState(false);
  const [maximized, setMaximized] = useState(false);
  const sizeBeforeMaxRef = useRef({ w: DEFAULT_W, h: DEFAULT_H });
  const [closed, setClosed] = useState(false);
  const frozenChartRef = useRef<WoodiesChartBar[] | null>(null);
  const frozenKeyRef = useRef('');
  const [allBars, setAllBars] = useState<WoodiesChartBar[]>([]);
  const [current, setCurrent] = useState<WoodiesChartBar | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stale, setStale] = useState(false);
  const [ageS, setAgeS] = useState<number | null>(null);
  const [studyCaption, setStudyCaption] = useState<string | null>(null);
  const [resizeHover, setResizeHover] = useState(false);
  const [mode, setMode] = useState<PanelMode>('loading');
  const [cciMax, setCciMax] = useState(() => loadCciMax());
  const [barCount, setBarCount] = useState(DEFAULT_BAR_COUNT);
  const [scrollEnd, setScrollEnd] = useState(0);
  const [showDataColumn, setShowDataColumn] = useState(true);

  const dragRef = useRef<'move' | 'corner' | null>(null);
  const dragStart = useRef({ x: 0, y: 0, w: 0, h: 0, left: 0, bottom: 0 });

  const contentScale = Math.min(
    panelW / CONTENT_W,
    Math.max(0.5, (panelH - TITLE_H - (minimized ? 0 : TOOLBAR_H)) / CONTENT_H),
  );

  const liveWindow = useMemo(
    () => sliceBarWindow(allBars, scrollEnd, barCount),
    [allBars, scrollEnd, barCount],
  );
  const atLive = allBars.length > 0 && scrollEnd >= allBars.length - 1;
  const chartViewKey = `${scrollEnd}:${barCount}`;

  const chartBars = useMemo(() => {
    const resolved = resolveChartPaintBars(
      atLive,
      liveWindow,
      frozenChartRef.current,
      chartViewKey,
      frozenKeyRef.current,
    );
    frozenChartRef.current = resolved.frozen;
    frozenKeyRef.current = resolved.frozenKey;
    return resolved.bars;
  }, [atLive, liveWindow, chartViewKey]);

  const displayBar = atLive ? current : chartBars[chartBars.length - 1] ?? current;

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v9/woodies/chart?limit=${API_BAR_LIMIT}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      if (!d.bars?.length) {
        setError(d.error || 'No Woodies bars in export');
        setAllBars([]);
        setCurrent(null);
        setMode(d.error ? 'empty' : 'disconnected');
        return;
      }
      setStale(Boolean(d.stale));
      setError(d.stale ? d.error || 'stale' : null);
      setAgeS(typeof d.age_s === 'number' ? d.age_s : null);
      setStudyCaption(typeof d.study_caption === 'string' ? d.study_caption : null);
      const rawList = (d.bars || []) as WoodiesChartBar[];
      const liveTick =
        (d.current_bar as WoodiesChartBar) || rawList[rawList.length - 1] || null;
      let list = rawList;
      if (liveTick && rawList.length > 0) {
        const tail = rawList[rawList.length - 1];
        if (tail.ts_unix === liveTick.ts_unix) {
          list = [...rawList.slice(0, -1), { ...tail, ...liveTick }];
        } else if (tail.ts_unix < liveTick.ts_unix) {
          list = [...rawList, liveTick];
        }
      }
      setAllBars((prevBars) => {
        setScrollEnd((prevEnd) => {
          const max = Math.max(0, list.length - 1);
          if (prevBars.length === 0) return max;
          if (prevEnd >= prevBars.length - 1) return max;
          return Math.min(prevEnd, max);
        });
        return list;
      });
      setCurrent(liveTick);
      setMode(list.length ? 'ready' : 'empty');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'fetch failed');
      setMode('disconnected');
    }
  }, []);

  useEffect(() => {
    if (visible) setClosed(false);
  }, [visible]);

  const toggleMaximize = useCallback(() => {
    setMaximized((was) => {
      if (!was) {
        sizeBeforeMaxRef.current = { w: panelW, h: panelH };
        setPanelW(MAXIMIZED_W);
        setPanelH(MAXIMIZED_H);
        return true;
      }
      setPanelW(sizeBeforeMaxRef.current.w);
      setPanelH(sizeBeforeMaxRef.current.h);
      return false;
    });
  }, [panelW, panelH]);

  useEffect(() => {
    if (!visible || closed) return;
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, [visible, closed, load]);

  useEffect(() => {
    if (!visible) return;
    localStorage.setItem(LS_W, String(panelW));
    localStorage.setItem(LS_H, String(panelH));
    localStorage.setItem(LS_LEFT, String(panelLeft));
    localStorage.setItem(LS_BOTTOM, String(panelBottom));
    localStorage.setItem(LS_CCI_MAX, String(snapCciMax(cciMax)));
  }, [panelW, panelH, panelLeft, panelBottom, cciMax, visible]);

  const scrollByPx = useCallback(
    (dxPx: number) => {
      const delta = -Math.round(dxPx / 6);
      if (delta === 0) return;
      setScrollEnd((end) => {
        if (allBars.length === 0) return 0;
        const max = allBars.length - 1;
        return Math.max(barCount - 1, Math.min(max, end + delta));
      });
    },
    [allBars.length, barCount],
  );

  const jumpNow = useCallback(() => {
    if (allBars.length > 0) setScrollEnd(allBars.length - 1);
  }, [allBars.length]);

  /** Time axis: drag right = more bars (wider time window), left = fewer */
  const zoomTimeByPx = useCallback((dxPx: number) => {
    const delta = Math.round(dxPx / 6);
    if (delta === 0) return;
    setBarCount((c) => Math.min(MAX_BAR_COUNT, Math.max(MIN_BAR_COUNT, c + delta)));
  }, []);

  const resetTimeZoom = useCallback(() => {
    setBarCount(DEFAULT_BAR_COUNT);
    jumpNow();
  }, [jumpNow]);

  const resetYAxis = useCallback(() => {
    setCciMax(DEFAULT_CCI_MAX);
  }, []);

  const resetChartView = useCallback(() => {
    setBarCount(DEFAULT_BAR_COUNT);
    setCciMax(DEFAULT_CCI_MAX);
    jumpNow();
  }, [jumpNow]);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragRef.current) return;
      const dx = e.clientX - dragStart.current.x;
      const dy = e.clientY - dragStart.current.y;
      if (dragRef.current === 'move') {
        setPanelLeft(Math.max(0, dragStart.current.left + dx));
        setPanelBottom(Math.max(0, dragStart.current.bottom - dy));
      } else if (dragRef.current === 'corner') {
        setPanelW(Math.min(MAX_PANEL_W, Math.max(MIN_PANEL_W, dragStart.current.w + dx)));
        setPanelH(Math.min(MAX_PANEL_H, Math.max(MIN_PANEL_H, dragStart.current.h - dy)));
      }
    };
    const onUp = () => {
      dragRef.current = null;
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, []);

  if (!visible || closed) return null;

  const zlrLive = atLive && Boolean(current?.zlr_detected);
  const borderColor =
    mode === 'disconnected'
      ? '#DC2626'
      : stale
        ? '#EAB308'
        : zlrLive
          ? COLORS.TITLE_ORANGE
          : COLORS.BORDER;

  return (
    <div
      data-testid="woodies-cci-panel"
      style={{
        position: 'absolute',
        left: panelLeft,
        bottom: panelBottom,
        zIndex: 20,
        width: panelW,
        height: minimized ? TITLE_H : panelH,
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 4,
        border: `1px solid ${borderColor}`,
        boxShadow: zlrLive
          ? `0 0 0 1px ${COLORS.TITLE_ORANGE}, 0 6px 24px rgba(251,149,11,0.35)`
          : '0 6px 24px rgba(0,0,0,0.65)',
        background: COLORS.BG,
        overflow: 'hidden',
        pointerEvents: 'auto',
        userSelect: 'none',
        isolation: 'isolate',
      }}
    >
      <TitleBar
        bar={current ?? displayBar}
        stale={stale}
        ageS={ageS}
        studyCaption={studyCaption}
        maximized={maximized}
        onMoveStart={(e) => {
          if ((e.target as HTMLElement).closest('button')) return;
          dragRef.current = 'move';
          dragStart.current = {
            x: e.clientX,
            y: e.clientY,
            w: panelW,
            h: panelH,
            left: panelLeft,
            bottom: panelBottom,
          };
        }}
        onMinimize={() => setMinimized((m) => !m)}
        onMaximize={toggleMaximize}
        onClose={() => {
          setClosed(true);
          onVisibilityChange?.(false);
        }}
      />

      {!minimized && (
        <>
          <div
            style={{
              flex: 1,
              minHeight: 0,
              position: 'relative',
              display: 'flex',
              alignItems: 'flex-start',
              justifyContent: 'flex-start',
              overflow: 'hidden',
              opacity: stale ? 0.85 : 1,
            }}
          >
            {!atLive && mode === 'ready' && (
              <button
                type="button"
                onClick={jumpNow}
                style={{
                  position: 'absolute',
                  top: 4,
                  left: '50%',
                  transform: 'translateX(-50%)',
                  zIndex: 20,
                  background: COLORS.TITLE_ORANGE,
                  color: '#0A0A0A',
                  border: 'none',
                  borderRadius: 3,
                  padding: '2px 8px',
                  fontSize: 9,
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                HISTORICAL — chart frozen · HUD live — back to NOW
              </button>
            )}
            <ContentViewport
              allBars={allBars}
              windowBars={chartBars}
              displayBar={displayBar}
              liveBar={current}
              scale={contentScale}
              cciMax={cciMax}
              atLive={atLive}
              stale={stale}
              onTimeZoom={zoomTimeByPx}
              onTimeReset={resetTimeZoom}
              onChartPan={scrollByPx}
              onChartReset={resetChartView}
              onYAxisReset={resetYAxis}
              showDataColumn={showDataColumn}
              onToggleDataColumn={() => setShowDataColumn((v) => !v)}
              onYAxisDrag={(dy) =>
                setCciMax((m) => snapCciMax(m + dy * 0.25))
              }
              onChartWheel={(dy) =>
                setBarCount((c) =>
                  Math.min(
                    MAX_BAR_COUNT,
                    Math.max(MIN_BAR_COUNT, c + (dy > 0 ? 2 : -2)),
                  ),
                )
              }
            />
            {mode === 'loading' && (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'rgba(45,85,85,0.85)',
                  color: '#fff',
                  fontSize: 11,
                  zIndex: 30,
                }}
              >
                Loading…
              </div>
            )}
            {mode === 'disconnected' && (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'rgba(220,38,38,0.35)',
                  color: '#fff',
                  fontSize: 11,
                  zIndex: 30,
                }}
              >
                Disconnected — retrying…
              </div>
            )}
            {stale && error && mode === 'ready' && (
              <div
                style={{
                  position: 'absolute',
                  top: 6,
                  left: 8,
                  right: 8,
                  zIndex: 25,
                  background: 'rgba(234,179,8,0.92)',
                  color: '#0A0A0A',
                  fontSize: 9,
                  fontWeight: 700,
                  padding: '4px 8px',
                  borderRadius: 3,
                  fontFamily: 'ui-monospace, monospace',
                }}
              >
                STALE — {error.slice(0, 72)}. Refresh Sierra woodies_5min.json for LIVE.
              </div>
            )}
            {mode === 'empty' && error && (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: 16,
                  zIndex: 30,
                  background: 'rgba(45,85,85,0.9)',
                  color: '#fbbf24',
                  fontSize: 11,
                  fontWeight: 700,
                  textAlign: 'center',
                  fontFamily: 'ui-monospace, monospace',
                  gap: 8,
                }}
              >
                <span>{error.slice(0, 120)}</span>
                <span style={{ fontWeight: 400, color: '#e2e8f0', fontSize: 10 }}>
                  Sierra must write woodies_5min.json every few seconds (&lt;30s).
                </span>
              </div>
            )}
          </div>
          <Toolbar
            ageS={ageS}
            barCount={barCount}
            cciMax={cciMax}
            onScrollBack={() => scrollByPx(-36)}
            onScrollForward={() => scrollByPx(36)}
            onZoomIn={() => setBarCount((c) => Math.max(MIN_BAR_COUNT, c - 3))}
            onZoomOut={() => setBarCount((c) => Math.min(MAX_BAR_COUNT, c + 3))}
          />
        </>
      )}

      {!minimized && (
        <div
          style={{
            position: 'absolute',
            right: 0,
            bottom: TOOLBAR_H,
            width: 4,
            height: CONTENT_H * contentScale,
            cursor: 'col-resize',
            background: resizeHover ? COLORS.TITLE_ORANGE : 'transparent',
            opacity: resizeHover ? 0.85 : 1,
          }}
          title="Resize width"
          onMouseEnter={() => setResizeHover(true)}
          onMouseLeave={() => setResizeHover(false)}
          onMouseDown={(e) => {
            e.preventDefault();
            dragRef.current = 'corner';
            dragStart.current = { x: e.clientX, y: e.clientY, w: panelW, h: panelH, left: 0, bottom: 0 };
          }}
        />
      )}

      {!minimized && (
        <div
          style={{
            position: 'absolute',
            right: 2,
            bottom: 2,
            width: 14,
            height: 14,
            cursor: 'nwse-resize',
            background: resizeHover ? COLORS.TITLE_ORANGE : 'transparent',
            borderRadius: 2,
            opacity: resizeHover ? 0.85 : 1,
          }}
          title="Resize panel"
          onMouseEnter={() => setResizeHover(true)}
          onMouseLeave={() => setResizeHover(false)}
          onMouseDown={(e) => {
            e.preventDefault();
            dragRef.current = 'corner';
            dragStart.current = { x: e.clientX, y: e.clientY, w: panelW, h: panelH, left: 0, bottom: 0 };
          }}
        />
      )}
    </div>
  );
}
