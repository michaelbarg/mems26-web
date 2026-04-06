'use client';

import { useEffect, useRef, useCallback } from 'react';
export interface SetupZone {
  entry:      number;
  stop:       number;
  t1:         number;
  t2:         number;
  t3:         number;
  direction:  "LONG" | "SHORT";
  sweepTs:    number;
  visible:    boolean;
  start_ts?:  number;
  end_ts?:    number;
}

interface Candle {
  ts: number;
  o: number; h: number; l: number; c: number;
  buy?: number; sell?: number; delta?: number;
}

interface Signal {
  direction: 'LONG' | 'SHORT' | 'NO_TRADE';
  entry: number; stop: number;
  target1: number; target2: number; target3: number;
  tl_color?: string;
}

interface SweepData {
  dir: 'long' | 'short';
  sweepBarTs: number;
  entryBarTs: number;
  setupBarTs: number[];
  entry: number;
  stop: number;
  t1: number;
  t2: number;
  t3?: number;
  delta: number;
  relVol: number;
  score: number;
  // Future bar timestamps for markers
  stopBarTs?: number;
  t1BarTs?: number;
  t2BarTs?: number;
  t3BarTs?: number;
  status?: string;
}

interface Props {
  candles: Candle[];
  livePrice?: number;
  liveBar?: { ts: number; o: number; h: number; l: number; c: number; buy?: number; sell?: number } | null;
  vwap?: number;
  levels?: { prev_high?: number; prev_low?: number; daily_open?: number; overnight_high?: number; overnight_low?: number };
  profile?: { poc?: number; vah?: number; val?: number };
  session?: { ibh?: number; ibl?: number };
  signal?: Signal | null;
  activeSetups?: { name: string; dir: 'long'|'short'; col: string }[];
  sweepData?: SweepData;
  sweepEvents?: Array<{ id:string; ts:number; dir:'long'|'short'; levelName:string; score:number; sweepBarTs:number }>;
  detectedSetups?: Array<{ id:string; dir:'long'|'short'; type:string; levelName:string; score:number; detectionBarTs:number; entryBarTs:number; entry:number; stop:number; c1:number; status:string }>;
  onSweepClick?: (sweepTs: number) => void;
  patterns?: Array<{id:string; nameHeb:string; direction:string; confidence:number; keyLevel:number; breakoutLevel?:number; stopLevel?:number; col:string; barIndex?:number}>;
  selectedPatternId?: string;
  height?: number;
  zone?: SetupZone | null;
  scannedPatterns?: Array<{pattern:string;direction:string;entry:number;stop:number;t1:number;t2:number;neckline:number;confidence:number;label:string;start_ts:number;end_ts:number}>;
}

export default function LightweightChart({
  candles, livePrice, liveBar, vwap, levels, profile, session, signal, activeSetups, sweepData, sweepEvents, detectedSetups, onSweepClick, patterns, selectedPatternId, height, zone, scannedPatterns
}: Props) {
  const containerRef     = useRef<HTMLDivElement>(null);
  const chartRef         = useRef<any>(null);
  const seriesRef        = useRef<any>(null);
  const cvdRef           = useRef<any>(null);
  const cvdMaRef         = useRef<any>(null);
  const linesRef         = useRef<any[]>([]);
  const rthBgRef         = useRef<any>(null);
  const canvasRef        = useRef<HTMLCanvasElement>(null);
  const sweepEventsRef   = useRef(sweepEvents);
  const onSweepClickRef  = useRef(onSweepClick);
  const sweepDataRef     = useRef(sweepData);
  sweepEventsRef.current  = sweepEvents;
  onSweepClickRef.current = onSweepClick;
  sweepDataRef.current    = sweepData;
  const loadedRef            = useRef(false);
  const zoneCanvasRef        = useRef<HTMLCanvasElement>(null);
  const volRef               = useRef<any>(null);
  const patternLinesRef      = useRef<any[]>([]);
  const patternTLRef         = useRef<any[]>([]);

  // ── Canvas overlay: Volume Profile + Sweep Zone ─────────────────────
  const drawOverlays = useCallback(() => {
    const canvas = canvasRef.current;
    const chart = chartRef.current;
    const series = seriesRef.current;
    if (!canvas || !chart || !series) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.parentElement?.getBoundingClientRect();
    if (!rect) return;

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, rect.width, rect.height);

      // ── Sweep Zone ───────────────────────────────────────────────────
      const sd = sweepDataRef.current;
      if (sd && sd.entry > 0) {
        const ts = chart.timeScale();
        const x1 = ts.timeToCoordinate(Math.floor(sd.sweepBarTs));
        const x2 = ts.timeToCoordinate(Math.floor(sd.entryBarTs || sd.sweepBarTs));
        if (x1 !== null && x2 !== null) {
          const isLong  = sd.dir === 'long';
          const entryY  = series.priceToCoordinate(sd.entry);
          const stopY   = series.priceToCoordinate(sd.stop);
          const t1Y     = series.priceToCoordinate(sd.t1);
          const t2Y     = series.priceToCoordinate(sd.t2);
          if (entryY !== null && stopY !== null && t1Y !== null && t2Y !== null) {

            const risk      = Math.abs(sd.entry - sd.stop);
            const riskDollar = Math.round(risk * 5);
            const t1pts     = Math.abs(sd.t1 - sd.entry);
            const t2pts     = Math.abs(sd.t2 - sd.entry);

            // ── X bounds: Sweep נר עד Entry נר בלבד ────────────────
            const BOX_L  = Math.min(x1, x2) - 6;
            const BOX_R  = Math.max(x1, x2) + 6;  // מסתיים בנר הכניסה
            const LINE_R = rect.width - 4;          // קווי T1/T2 ממשיכים עד קצה

            // ── Y bounds ────────────────────────────────────────────
            const BOX_T = Math.min(stopY, t2Y) - 12;
            const BOX_B = Math.max(stopY, t2Y) + 8;
            const BOX_W = BOX_R - BOX_L;
            const BOX_H = BOX_B - BOX_T;

            // ── fills ────────────────────────────────────────────────
            // risk zone
            const rT = Math.min(entryY, stopY), rB = Math.max(entryY, stopY);
            ctx.fillStyle = 'rgba(180,20,50,0.12)';
            ctx.fillRect(BOX_L, rT, BOX_W, rB - rT);

            // reward T1
            const r1T = Math.min(entryY, t1Y), r1B = Math.max(entryY, t1Y);
            ctx.fillStyle = isLong ? 'rgba(0,188,212,0.06)' : 'rgba(233,30,99,0.06)';
            ctx.fillRect(BOX_L, r1T, BOX_W, r1B - r1T);

            // reward T2
            const r2T = Math.min(t1Y, t2Y), r2B = Math.max(t1Y, t2Y);
            ctx.fillStyle = isLong ? 'rgba(0,188,212,0.11)' : 'rgba(233,30,99,0.11)';
            ctx.fillRect(BOX_L, r2T, BOX_W, r2B - r2T);

            // ── מלבן חיצוני ─────────────────────────────────────────
            ctx.shadowColor = isLong ? 'rgba(0,188,212,0.2)' : 'rgba(233,30,99,0.2)';
            ctx.shadowBlur  = 16;
            ctx.strokeStyle = isLong ? 'rgba(0,188,212,0.65)' : 'rgba(233,30,99,0.65)';
            ctx.lineWidth   = 1.5;
            ctx.setLineDash([]);
            ctx.beginPath();
            ctx.roundRect(BOX_L, BOX_T, BOX_W, BOX_H, 6);
            ctx.stroke();
            ctx.shadowBlur = 0; ctx.shadowColor = 'transparent';

            // ── קווים ────────────────────────────────────────────────
            // STOP — מקווקו אדום, בתוך המלבן בלבד
            ctx.strokeStyle = 'rgba(220,40,80,0.85)';
            ctx.lineWidth   = 1.5;
            ctx.setLineDash([5, 4]);
            ctx.beginPath();
            ctx.moveTo(BOX_L, stopY);
            ctx.lineTo(BOX_R, stopY);
            ctx.stroke();

            // ENTRY — לבן מלא, מהמלבן עד קצה ימין
            ctx.strokeStyle = 'rgba(255,255,255,0.9)';
            ctx.lineWidth   = 2;
            ctx.setLineDash([]);
            ctx.beginPath();
            ctx.moveTo(BOX_L, entryY);
            ctx.lineTo(LINE_R, entryY);
            ctx.stroke();

            // T1 — ציאן מקווקו, מהנר הכניסה עד קצה ימין
            ctx.strokeStyle = 'rgba(0,188,212,0.55)';
            ctx.lineWidth   = 1;
            ctx.setLineDash([3, 4]);
            ctx.beginPath();
            ctx.moveTo(BOX_L, t1Y);
            ctx.lineTo(LINE_R, t1Y);
            ctx.stroke();

            // T2 — ציאן מלא, מהנר הכניסה עד קצה ימין
            ctx.strokeStyle = 'rgba(0,210,220,0.85)';
            ctx.lineWidth   = 1.5;
            ctx.setLineDash([]);
            ctx.beginPath();
            ctx.moveTo(BOX_L, t2Y);
            ctx.lineTo(LINE_R, t2Y);
            ctx.stroke();

            // ── קווים אנכיים על נרות מיוחדים ───────────────────────
            ctx.strokeStyle = 'rgba(255,165,0,0.35)';
            ctx.lineWidth   = 1;
            ctx.setLineDash([2, 3]);
            ctx.beginPath();
            ctx.moveTo(x1, BOX_T);
            ctx.lineTo(x1, BOX_B);
            ctx.stroke();

            ctx.strokeStyle = 'rgba(0,230,118,0.3)';
            ctx.beginPath();
            ctx.moveTo(x2, BOX_T);
            ctx.lineTo(x2, BOX_B);
            ctx.stroke();
            ctx.setLineDash([]);

            // ── עיגולי עיגון ─────────────────────────────────────────
            // Stop — על נר ה-sweep
            ctx.fillStyle = '#e91e63';
            ctx.beginPath(); ctx.arc(x1, stopY, 5, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = 'rgba(255,255,255,0.85)'; ctx.lineWidth = 1.5;
            ctx.beginPath(); ctx.arc(x1, stopY, 5, 0, Math.PI * 2); ctx.stroke();

            // Entry — על נר הכניסה
            ctx.fillStyle = '#00e676';
            ctx.beginPath(); ctx.arc(x2, entryY, 5, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = 'rgba(255,255,255,0.85)'; ctx.lineWidth = 1.5;
            ctx.beginPath(); ctx.arc(x2, entryY, 5, 0, Math.PI * 2); ctx.stroke();

            // ── חץ כניסה ─────────────────────────────────────────────
            const aD = isLong ? -1 : 1;
            ctx.fillStyle   = '#00e676';
            ctx.beginPath();
            ctx.moveTo(x2, entryY + aD * 8);
            ctx.lineTo(x2 - 9, entryY + aD * 22);
            ctx.lineTo(x2 + 9, entryY + aD * 22);
            ctx.closePath(); ctx.fill();

            // ── פונקציית pill ─────────────────────────────────────────
            const pill = (
              txt: string, px: number, py2: number,
              bg: string, tc: string, align: 'left' | 'right' = 'right'
            ) => {
              ctx.font = 'bold 9px monospace';
              const m = ctx.measureText(txt);
              const pw = 7, bh = 15, r = 3;
              const bx = align === 'right' ? px - m.width - pw * 2 : px;
              ctx.fillStyle = bg;
              ctx.beginPath();
              ctx.roundRect(bx, py2 - 7, m.width + pw * 2, bh, r);
              ctx.fill();
              ctx.strokeStyle = 'rgba(255,255,255,0.18)';
              ctx.lineWidth = 0.5;
              ctx.beginPath();
              ctx.roundRect(bx, py2 - 7, m.width + pw * 2, bh, r);
              ctx.stroke();
              ctx.fillStyle = tc;
              ctx.textAlign = align;
              ctx.fillText(txt, align === 'right' ? px - pw : px + pw, py2 + 4);
            };

            // ── labels ימין (על הקווים הממשיכים) ────────────────────
            pill(`T2  +${t2pts.toFixed(0)}pt`, LINE_R - 4, t2Y,
              isLong ? 'rgba(0,35,45,0.96)' : 'rgba(45,0,18,0.96)',
              isLong ? '#00e5ff' : '#ff4081');

            pill(`T1  +${t1pts.toFixed(0)}pt`, LINE_R - 4, t1Y,
              isLong ? 'rgba(0,28,38,0.92)' : 'rgba(38,0,14,0.92)',
              isLong ? 'rgba(0,200,215,0.9)' : 'rgba(230,70,110,0.9)');

            pill(isLong ? '▲ ENTRY' : '▼ ENTRY', LINE_R - 4, entryY,
              'rgba(28,28,28,0.96)', '#ffffff');

            pill(`✕ STOP  −${riskDollar}$`, LINE_R - 4, stopY,
              'rgba(45,0,8,0.96)', '#ff5252');

            // ── labels שמאל (מחיר) ────────────────────────────────────
            pill(sd.t2.toFixed(2), BOX_L + 4, t2Y,
              'rgba(0,25,35,0.92)',
              isLong ? '#00e5ff' : '#ff4081', 'left');

            pill(sd.t1.toFixed(2), BOX_L + 4, t1Y,
              'rgba(0,20,28,0.88)',
              isLong ? 'rgba(0,195,210,0.85)' : 'rgba(225,65,105,0.85)', 'left');

            pill(sd.entry.toFixed(2), BOX_L + 4, entryY,
              'rgba(22,22,22,0.92)', '#ffffff', 'left');

            pill(sd.stop.toFixed(2), BOX_L + 4, stopY,
              'rgba(40,0,6,0.92)', '#ff5252', 'left');

            // ── כותרת מלבן ────────────────────────────────────────────
            const titleTxt = isLong ? '▲ LONG · LSR' : '▼ SHORT · LSR';
            const titleBg  = isLong ? 'rgba(0,50,60,0.97)' : 'rgba(55,0,18,0.97)';
            const titleCol = isLong ? '#00e5ff' : '#ff4081';
            ctx.font = 'bold 10px monospace';
            const tm = ctx.measureText(titleTxt);
            const tx = BOX_L + (BOX_W - tm.width) / 2 - 4;
            ctx.fillStyle = titleBg;
            ctx.beginPath();
            ctx.roundRect(tx - 6, BOX_T + 2, tm.width + 12, 17, 4);
            ctx.fill();
            ctx.fillStyle = titleCol;
            ctx.textAlign = 'left';
            ctx.fillText(titleTxt, tx, BOX_T + 14);

            // R:R badge
            ctx.font = 'bold 9px monospace';
            const rrTxt = `R:R 1:2`;
            const rm = ctx.measureText(rrTxt);
            ctx.fillStyle = 'rgba(15,15,5,0.92)';
            ctx.beginPath();
            ctx.roundRect(BOX_R - rm.width - 18, BOX_B - 16, rm.width + 12, 14, 3);
            ctx.fill();
            ctx.fillStyle = '#ffd600';
            ctx.textAlign = 'right';
            ctx.fillText(rrTxt, BOX_R - 4, BOX_B - 5);
          }
        }
      }
  }, []);

  // ── Setup Zones heatmap overlay ─────────────────────────────────────
  const zoneRef = useRef(zone);
  zoneRef.current = zone;

  const drawZones = useCallback(() => {
    const canvas = zoneCanvasRef.current;
    const series = seriesRef.current;
    const container = canvas?.parentElement;

    if (!canvas || !container) return;

    const W = container.clientWidth;
    const H = container.clientHeight;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = W + "px";
    canvas.style.height = H + "px";

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, W, H);

    const z = zoneRef.current;
    if (!series || !z || !z.visible) return;

    const p2y = (price: number): number | null => {
      try { return series.priceToCoordinate(price); }
      catch { return null; }
    };

    const { entry, stop, t1, t2, t3, direction } = z;
    const yEnt = p2y(entry), yStp = p2y(stop);
    const yT1 = p2y(t1), yT2 = p2y(t2), yT3 = p2y(t3);
    if (yEnt === null || yStp === null || yT3 === null) return;

    const scaleW = 72;
    const chartW = W - scaleW;
    const chart = chartRef.current;

    // ── Convert timestamps to X pixels ──
    let xStart = 0;
    let xEnd = chartW;

    if (chart && z.start_ts) {
      try {
        const x = chart.timeScale().timeToCoordinate(z.start_ts as any);
        if (x !== null) xStart = Math.max(0, x);
      } catch {}
    }
    if (chart && z.end_ts) {
      try {
        const x = chart.timeScale().timeToCoordinate(z.end_ts as any);
        if (x !== null) xEnd = Math.min(chartW, x + 6);
      } catch {}
    }

    if (xStart >= chartW || xEnd <= 0 || xStart >= xEnd) {
      ctx.clearRect(0, 0, W, H);
      return;
    }
    const zoneW = xEnd - xStart;

    // ── Reward zones (entry → T3) — 3 layers increasing intensity ──
    const rewardZones: [number | null, number | null, string][] = [
      [yEnt, yT1, "rgba(0,188,212,0.04)"],
      [yT1, yT2, "rgba(0,188,212,0.07)"],
      [yT2, yT3, "rgba(0,188,212,0.12)"],
    ];
    rewardZones.forEach(([ya, yb, color]) => {
      if (ya === null || yb === null) return;
      const top = Math.min(ya, yb);
      const bot = Math.max(ya, yb);
      ctx.fillStyle = color;
      ctx.fillRect(xStart, top, zoneW, bot - top);
      ctx.fillStyle = color.replace(/[\d.]+\)$/, "0.7)");
      ctx.fillRect(xStart, top, 3, bot - top);
    });

    // ── Risk zone (entry → stop) — gradient ──
    {
      const top = Math.min(yEnt, yStp);
      const bot = Math.max(yEnt, yStp);
      const gRisk = ctx.createLinearGradient(0, top, 0, bot);
      if (direction === "LONG") {
        gRisk.addColorStop(0, "rgba(233,30,99,0.03)");
        gRisk.addColorStop(1, "rgba(233,30,99,0.10)");
      } else {
        gRisk.addColorStop(0, "rgba(233,30,99,0.10)");
        gRisk.addColorStop(1, "rgba(233,30,99,0.03)");
      }
      ctx.fillStyle = gRisk;
      ctx.fillRect(xStart, top, zoneW, bot - top);
      ctx.fillStyle = "rgba(233,30,99,0.7)";
      ctx.fillRect(xStart, top, 3, bot - top);
    }

    // ── Border lines ──
    const risk = Math.abs(entry - stop);
    const borders: [number | null, string, number][] = [
      [yT3, "rgba(0,188,212,0.85)", 1.5],
      [yT2, "rgba(0,188,212,0.55)", 0.8],
      [yT1, "rgba(0,188,212,0.40)", 0.8],
      [yEnt, "rgba(255,255,255,0.85)", 2],
      [yStp, "rgba(233,30,99,0.85)", 1.5],
    ];
    borders.forEach(([y, color, lw]) => {
      if (y === null) return;
      ctx.strokeStyle = color;
      ctx.lineWidth = lw;
      ctx.setLineDash([]);
      ctx.beginPath(); ctx.moveTo(xStart, y); ctx.lineTo(xEnd, y); ctx.stroke();
    });

    // ── Labels ──
    const labels: [number | null, string, string, string][] = [
      [yT3, `T3  ${t3.toFixed(2)}`, `R:R ${(Math.abs(t3 - entry) / risk).toFixed(1)}:1`, "rgba(0,210,220,0.9)"],
      [yT2, `T2  ${t2.toFixed(2)}`, `R:R ${(Math.abs(t2 - entry) / risk).toFixed(1)}:1`, "rgba(0,188,212,0.8)"],
      [yT1, `T1  ${t1.toFixed(2)}`, `R:R ${(Math.abs(t1 - entry) / risk).toFixed(1)}:1`, "rgba(0,170,200,0.7)"],
      [yEnt, `ENT ${entry.toFixed(2)}`, direction === "LONG" ? "LONG" : "SHORT", "rgba(255,255,255,0.9)"],
      [yStp, `STP ${stop.toFixed(2)}`, `${risk.toFixed(2)} pt`, "rgba(233,30,99,0.9)"],
    ];
    labels.forEach(([y, line1, line2, color]) => {
      if (y === null) return;
      ctx.font = "bold 10px monospace";
      ctx.fillStyle = color;
      ctx.textAlign = "right";
      ctx.fillText(line1, xEnd - 6, y - 3);
      ctx.font = "9px monospace";
      ctx.fillStyle = color.replace(/[\d.]+\)$/, "0.55)");
      ctx.fillText(line2, xEnd - 6, y + 9);
    });
  }, []);


  const initChart = useCallback(() => {
    if (!containerRef.current || chartRef.current) return;
    const LW = (window as any).LightweightCharts;
    if (!LW) return;

    const chart = LW.createChart(containerRef.current, {
      width:  containerRef.current.clientWidth,
      height: height ?? (containerRef.current?.clientHeight ?? 500),
      layout: {
        background: { color: '#0d1117' },
        textColor:  '#94a3b8',
        fontSize:   12,
        fontFamily: 'JetBrains Mono, Fira Code, monospace',
      },
      grid: {
        vertLines: { color: '#161d2a', style: 1 },
        horzLines: { color: '#161d2a', style: 1 },
      },
      crosshair: {
        mode: 1,
        vertLine: { color: '#4a5568', width: 1, style: 0, labelBackgroundColor: '#1e2738' },
        horzLine: { color: '#4a5568', width: 1, style: 0, labelBackgroundColor: '#1e2738' },
      },
      rightPriceScale: {
        borderColor:    '#1e2738',
        textColor:      '#94a3b8',
        scaleMargins:   { top: 0.02, bottom: 0.25 },
      },
      timeScale: {
        borderColor:    '#1e2738',
        timeVisible:    true,
        secondsVisible: false,
        barSpacing:     8,
        rightOffset:    5,
      },
      handleScroll:  { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true },
      handleScale:   { mouseWheel: true, axisPressedMouseMove: true, pinch: true },
    });

    // Candlestick
    const series = chart.addCandlestickSeries({
      upColor:          '#26a69a',
      downColor:        '#ef5350',
      wickUpColor:      '#26a69a',
      wickDownColor:    '#ef5350',
      borderVisible:    false,
      priceLineVisible: false,
      lastValueVisible: true,
    });

    // CVD (cumulative volume delta) — bottom band
    const cvdLine = chart.addLineSeries({
      color:           '#00e676',
      lineWidth:       2,
      priceScaleId:    'cvd',
      lastValueVisible: true,
      priceLineVisible: false,
    });
    chart.priceScale('cvd').applyOptions({
      scaleMargins: { top: 0.78, bottom: 0.01 },
    });

    // CVD MA20 — dashed overlay
    const cvdMaLine = chart.addLineSeries({
      color:           '#ffeb3b',
      lineWidth:       1,
      lineStyle:       2,
      priceScaleId:    'cvd',
      lastValueVisible: false,
      priceLineVisible: false,
    });

    // Volume histogram — bottom band
    const volHist = chart.addHistogramSeries({
      color:           '#5b6a8a',
      priceScaleId:    'vol',
      priceFormat:     { type: 'volume' },
      lastValueVisible: false,
      priceLineVisible: false,
    });
    chart.priceScale('vol').applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
      visible: false,
    });

    chartRef.current  = chart;
    seriesRef.current = series;
    cvdRef.current    = cvdLine;
    cvdMaRef.current  = cvdMaLine;
    volRef.current    = volHist;
    // RTH background overlay — covers full chart height
    const rthBg = chart.addHistogramSeries({
      priceScaleId:    'rth-bg',
      lastValueVisible: false,
      priceLineVisible: false,
    });
    chart.priceScale('rth-bg').applyOptions({
      scaleMargins: { top: 0, bottom: 0 },
      visible: false,
    });
    rthBgRef.current = rthBg;

    // Click handler — find nearest sweep event
    chart.subscribeClick((param: any) => {
      if (!param.time || !sweepEventsRef.current || !onSweepClickRef.current) return;
      const clickTs = param.time as number;
      // Find sweep within ±2 bars (±360 sec)
      const match = sweepEventsRef.current.find((ev: any) =>
        Math.abs(ev.sweepBarTs - clickTs) <= 360
      );
      if (match) onSweepClickRef.current(match.sweepBarTs);
    });

    // Resize
    const ro = new ResizeObserver(() => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
        drawOverlays();
        drawZones();
      }
    });
    ro.observe(containerRef.current);

    // Redraw overlays on scroll/zoom
    chart.timeScale().subscribeVisibleLogicalRangeChange(() => {
      drawOverlays();
      drawZones();
    });
  }, [height, drawOverlays, drawZones]);

  // Load script once
  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;

    if ((window as any).LightweightCharts) {
      initChart();
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js';
    script.async = true;
    script.onload = initChart;
    document.head.appendChild(script);

    return () => { chartRef.current?.remove(); chartRef.current = null; seriesRef.current = null; };
  }, [initChart]);

  // Track last candles fingerprint to avoid unnecessary setData calls
  const lastCandlesFingerprintRef = useRef('');

  // Update candles (only when candle data actually changes)
  useEffect(() => {
    if (!seriesRef.current) return;
    if (candles.length === 0) return;

    // Check if candles actually changed (by length + last candle ts)
    const fingerprint = `${candles.length}-${candles[0]?.ts}-${candles[candles.length-1]?.ts}`;
    if (fingerprint === lastCandlesFingerprintRef.current) return;
    lastCandlesFingerprintRef.current = fingerprint;

    const sorted = [...candles].reverse().filter(c => c.ts > 0);

    const cData = sorted.map(c => ({
      time:  Math.floor(c.ts) as any,
      open:  c.o, high: c.h, low: c.l, close: c.c,
    }));

    // Add/update live bar
    if (liveBar) {
      const lb = {
        time: Math.floor(liveBar.ts) as any,
        open: liveBar.o, high: liveBar.h, low: liveBar.l,
        close: livePrice ?? liveBar.c,
      };
      if (cData.length > 0 && cData[cData.length - 1].time === lb.time) {
        cData[cData.length - 1] = lb;
      } else {
        cData.push(lb);
      }
    }

    seriesRef.current.setData(cData);

    // CVD (cumulative volume delta) + MA20
    if (cvdRef.current && cvdMaRef.current) {
      let cvd = 0;
      let prevDay = -1;
      const win20: number[] = [];
      const cvdData: any[] = [];
      const maData: any[] = [];

      for (const c of sorted) {
        const buyVal = c.buy || 0;
        const sellVal = c.sell || 0;
        let delta: number;
        if (buyVal + sellVal > 0) {
          delta = buyVal - sellVal;
        } else {
          const spread = c.h - c.l;
          delta = spread > 0 ? 100 * ((c.c - c.l) - (c.h - c.c)) / spread : 0;
        }

        // Daily reset
        const dayNum = Math.floor(c.ts / 86400);
        if (dayNum !== prevDay && prevDay !== -1) cvd = 0;
        prevDay = dayNum;

        cvd += delta;
        const t = Math.floor(c.ts) as any;
        cvdData.push({ time: t, value: cvd });

        win20.push(cvd);
        if (win20.length > 20) win20.shift();
        const ma = win20.reduce((s, v) => s + v, 0) / win20.length;
        maData.push({ time: t, value: ma });
      }

      if (liveBar) {
        const lb = liveBar;
        const buyVal = lb.buy || 0;
        const sellVal = lb.sell || 0;
        let delta: number;
        if (buyVal + sellVal > 0) {
          delta = buyVal - sellVal;
        } else {
          const spread = lb.h - lb.l;
          delta = spread > 0 ? 100 * ((lb.c - lb.l) - (lb.h - lb.c)) / spread : 0;
        }
        const dayNum = Math.floor(lb.ts / 86400);
        if (dayNum !== prevDay && prevDay !== -1) cvd = 0;
        cvd += delta;
        const t = Math.floor(lb.ts) as any;
        cvdData.push({ time: t, value: cvd });
        win20.push(cvd);
        if (win20.length > 20) win20.shift();
        const ma = win20.reduce((s, v) => s + v, 0) / win20.length;
        maData.push({ time: t, value: ma });
      }

      cvdRef.current.setData(cvdData);
      cvdMaRef.current.setData(maData);
    }

    // Volume histogram
    if (volRef.current) {
      const volData = sorted.map(c => {
        const vol = (c.buy || 0) + (c.sell || 0);
        const isBuy = c.c >= c.o;
        return {
          time: Math.floor(c.ts) as any,
          value: vol > 0 ? vol : 100,
          color: isBuy ? 'rgba(38,166,154,0.4)' : 'rgba(239,83,80,0.4)',
        };
      });
      if (liveBar) {
        const vol = (liveBar.buy || 0) + (liveBar.sell || 0);
        const isBuy = (livePrice ?? liveBar.c) >= liveBar.o;
        volData.push({
          time: Math.floor(liveBar.ts) as any,
          value: vol > 0 ? vol : 100,
          color: isBuy ? 'rgba(38,166,154,0.4)' : 'rgba(239,83,80,0.4)',
        });
      }
      volRef.current.setData(volData);
    }

    // Redraw overlays (volume profile + sweep zone) — delay to let chart render
    requestAnimationFrame(() => drawOverlays());

  }, [candles, drawOverlays]);

  // Update live candle in real-time (lightweight update, no full setData)
  useEffect(() => {
    if (!seriesRef.current || !liveBar) return;
    const price = livePrice ?? liveBar.c;
    seriesRef.current.update({
      time:  Math.floor(liveBar.ts) as any,
      open:  liveBar.o,
      high:  Math.max(liveBar.h, price),
      low:   Math.min(liveBar.l, price),
      close: price,
    });

    // Update CVD for live bar too
    if (cvdRef.current && cvdMaRef.current) {
      const buyVal = liveBar.buy || 0;
      const sellVal = liveBar.sell || 0;
      let delta: number;
      if (buyVal + sellVal > 0) {
        delta = buyVal - sellVal;
      } else {
        const spread = liveBar.h - liveBar.l;
        delta = spread > 0 ? 100 * ((liveBar.c - liveBar.l) - (liveBar.h - liveBar.c)) / spread : 0;
      }
      const t = Math.floor(liveBar.ts) as any;
      cvdRef.current.update({ time: t, value: delta });
    }

    // Update volume for live bar
    if (volRef.current) {
      const vol = (liveBar.buy || 0) + (liveBar.sell || 0);
      const isBuy = price >= liveBar.o;
      volRef.current.update({
        time: Math.floor(liveBar.ts) as any,
        value: vol > 0 ? vol : 100,
        color: isBuy ? 'rgba(38,166,154,0.4)' : 'rgba(239,83,80,0.4)',
      });
    }
  }, [liveBar, livePrice]);

  // Update level lines + setup markers
  useEffect(() => {
    if (!seriesRef.current) return;

    linesRef.current.forEach(l => { try { seriesRef.current.removePriceLine(l); } catch {} });
    linesRef.current = [];

    const add = (price: number | undefined, color: string, title: string, style = 2, width = 1) => {
      if (!price || price <= 0) return;
      const l = seriesRef.current.createPriceLine({ price, color, lineWidth: width, lineStyle: style, axisLabelVisible: true, title });
      linesRef.current.push(l);
    };

    add(levels?.prev_high,      '#ef444466', 'PDH ', 3, 1);
    add(levels?.prev_low,       '#ef444466', 'PDL ', 3, 1);
    add(levels?.daily_open,     '#60a5fa66', 'DO  ', 3, 1);
    add(levels?.overnight_high, '#a78bfa66', 'ONH ', 3, 1);
    add(levels?.overnight_low,  '#a78bfa66', 'ONL ', 3, 1);
    add(profile?.vah,           '#22c55e66', 'VAH ', 3, 1);
    add(profile?.val,           '#22c55e66', 'VAL ', 3, 1);
    add(profile?.poc,           '#f9731666', 'POC ', 3, 1);
    add(session?.ibh,           '#38bdf866', 'IBH ', 3, 1);
    add(session?.ibl,           '#38bdf866', 'IBL ', 3, 1);
    add(vwap,                   '#f6c90e66', 'VWAP', 3, 1);

    // Pattern selected — הוסף קווי כניסה וסטופ
    if (patterns && selectedPatternId) {
      const selP = patterns.find(p => p.id === selectedPatternId);
      if (selP) {
        if (selP.breakoutLevel) add(selP.breakoutLevel, selP.col, `▶ ${selP.nameHeb}`, 0, 2);
        if (selP.stopLevel)     add(selP.stopLevel, '#ef5350', '✕ סטופ', 2, 1);
        if (selP.keyLevel)      add(selP.keyLevel, selP.col+'99', '— רמה', 4, 1);
        // Target = כניסה + distance (R:R 1:1)
        if (selP.breakoutLevel && selP.stopLevel) {
          const risk = Math.abs(selP.breakoutLevel - selP.stopLevel);
          const t1 = selP.direction === 'long' ? selP.breakoutLevel + risk : selP.breakoutLevel - risk;
          const t2 = selP.direction === 'long' ? selP.breakoutLevel + risk*2 : selP.breakoutLevel - risk*2;
          add(t1, '#22c55e', `⊕ T1 ${selP.confidence}%`, 2, 1);
          add(t2, '#16a34a', `⊕ T2 ${Math.round(selP.confidence*0.7)}%`, 2, 1);
        }
      }
    }

    // ── Sweep trade lines — entry/stop/C1/C2/C3 as price lines ──────
    if (sweepData && sweepData.entry > 0) {
      const risk = Math.abs(sweepData.entry - sweepData.stop);
      add(sweepData.entry, '#ffffff',    `→ ENTRY ${sweepData.entry.toFixed(2)}`, 0, 2);
      add(sweepData.stop,  '#ef5350',    `✕ STOP ${sweepData.stop.toFixed(2)} (−${risk.toFixed(1)}pt)`, 2, 1);
      add(sweepData.t1,    '#22c55e',    `① C1 50% ${sweepData.t1.toFixed(2)} (+${Math.abs(sweepData.t1-sweepData.entry).toFixed(1)}pt)`, 2, 1);
      add(sweepData.t2,    '#16a34a',    `② C2 25% ${sweepData.t2.toFixed(2)} (+${Math.abs(sweepData.t2-sweepData.entry).toFixed(1)}pt)`, 2, 1);
      if (sweepData.t3) add(sweepData.t3, '#86efac66', `③ C3 Run ${sweepData.t3.toFixed(2)}`, 3, 1);
    }

    // ── Markers: Setup + Pattern ──────────────────────────
    if (seriesRef.current) {
      try {
        const allMarkers: any[] = [];

        // ── Sweep markers — on actual + future candles ──────────
        if (sweepData && sweepData.sweepBarTs > 0) {
          const isLong = sweepData.dir === 'long';
          const pos = isLong ? 'belowBar' : 'aboveBar';
          const entryPts = Math.abs(sweepData.entry - sweepData.stop);

          // Sweep candle
          allMarkers.push({
            time: Math.floor(sweepData.sweepBarTs) as any,
            position: pos, color: isLong ? '#22c55e' : '#ef5350',
            shape: isLong ? 'arrowUp' : 'arrowDown',
            text: `⚡ SWEEP`, size: 2,
          });

          // Entry candle (reversal bar)
          if (sweepData.entryBarTs > 0) {
            allMarkers.push({
              time: Math.floor(sweepData.entryBarTs) as any,
              position: pos, color: '#ffffff',
              shape: isLong ? 'arrowUp' : 'arrowDown',
              text: `→ ENTRY ${sweepData.entry.toFixed(2)}`, size: 2,
            });
          }

          // Setup candles
          if (sweepData.setupBarTs) {
            sweepData.setupBarTs.forEach(ts => {
              if (ts > 0) allMarkers.push({ time: Math.floor(ts) as any, position: pos, color: '#4a556866', shape: 'circle' as any, text: 'setup', size: 0 });
            });
          }

          // Stop/C1/C2/C3 are now shown as horizontal price lines above (not markers)
        }

        // ── Detected setup markers — on specific candles ──────
        if (detectedSetups && detectedSetups.length > 0) {
          detectedSetups.forEach((ds: any) => {
            if (ds.status === 'expired') return;
            const isLong = ds.dir === 'long';
            const pos = isLong ? 'belowBar' : 'aboveBar';
            const col = ds.status === 'stopped' ? '#ef5350' : ds.status === 'c1_hit' || ds.status === 'c2_hit' ? '#22c55e' : isLong ? '#22c55e' : '#ef5350';

            // Detection marker
            if (ds.detectionBarTs > 0) {
              allMarkers.push({
                time: Math.floor(ds.detectionBarTs) as any,
                position: pos, color: col + 'aa',
                shape: isLong ? 'arrowUp' : 'arrowDown',
                text: `${ds.type.slice(0,3).toUpperCase()} ${ds.levelName}`, size: 1,
              });
            }
            // Entry marker (if different from detection)
            if (ds.entryBarTs > 0 && ds.entryBarTs !== ds.detectionBarTs) {
              allMarkers.push({
                time: Math.floor(ds.entryBarTs) as any,
                position: pos, color: '#ffffff',
                shape: isLong ? 'arrowUp' : 'arrowDown',
                text: `E ${ds.entry.toFixed(0)}`, size: 1,
              });
            }
          });
        }

        // ── Historical sweep dots (tiny circles, no text) ──
        if (sweepEvents && sweepEvents.length > 0 && !sweepData) {
          sweepEvents.forEach((ev: any) => {
            allMarkers.push({
              time: Math.floor(ev.sweepBarTs) as any,
              position: ev.dir === 'long' ? 'belowBar' : 'aboveBar',
              color: ev.dir === 'long' ? '#22c55e55' : '#ef535055',
              shape: 'circle' as any,
              text: '',
              size: 0,
            });
          });
        }

        // Pattern markers — על הנר הרלוונטי
        if (patterns && patterns.length > 0 && candles.length > 0) {
          // candles מגיעים ישן→חדש
          const sortedCandles = [...candles].sort((a,b) => a.ts - b.ts);
          patterns.forEach(p => {
            const isSelected = p.id === selectedPatternId;
            // barIndex מחושב מהסוף — הופכים לאינדקס בsortedCandles
            const idx = p.barIndex !== undefined
              ? Math.max(0, sortedCandles.length - 1 - p.barIndex)
              : sortedCandles.length - 1;
            const candle = sortedCandles[idx];
            if (!candle) return;

            // Marker על נר התבנית
            allMarkers.push({
              time: candle.ts as any,
              position: p.direction === 'long' ? 'belowBar' : 'aboveBar',
              color: isSelected ? p.col : p.col + '99',
              shape: p.direction === 'long' ? 'arrowUp' : p.direction === 'short' ? 'arrowDown' : 'circle',
              text: `${p.nameHeb} ${p.confidence}%`,
              size: isSelected ? 2 : 1,
            });

            // אם נבחר — הוסף marker גם על נר הפריצה (עכשיו)
            if (isSelected && p.breakoutLevel && liveBar) {
              allMarkers.push({
                time: liveBar.ts as any,
                position: p.direction === 'long' ? 'belowBar' : 'aboveBar',
                color: '#a78bfa',
                shape: p.direction === 'long' ? 'arrowUp' : 'arrowDown',
                text: `⚡ כניסה ${p.breakoutLevel?.toFixed(2)}`,
                size: 2,
              });
            }
          });
        }

        // מיין לפי זמן (חובה ב-LightweightCharts)
        allMarkers.sort((a,b) => (a.time as number) - (b.time as number));
        seriesRef.current.setMarkers(allMarkers);
      } catch {}
    }

  }, [levels, profile, session, vwap, signal, activeSetups, sweepData, sweepEvents, detectedSetups, liveBar, patterns, selectedPatternId]);

  // Redraw sweep zone overlay when sweepData changes
  useEffect(() => {
    drawOverlays();
  }, [sweepData, drawOverlays]);

  // Redraw zones when zone changes
  useEffect(() => {
    drawZones();
  }, [zone, drawZones]);


  const drawPatternLines = useCallback(() => {
    const chart  = chartRef.current;
    const series = seriesRef.current;
    if (!chart || !series) return;

    patternLinesRef.current.forEach(l => { try { series.removePriceLine(l); } catch {} });
    patternLinesRef.current = [];
    patternTLRef.current.forEach(s => { try { chart.removeSeries(s); } catch {} });
    patternTLRef.current = [];

    if (!scannedPatterns || scannedPatterns.length === 0) return;
    const p = scannedPatterns[0];

    if (p.neckline) {
      const nl = series.createPriceLine({ price: p.neckline, color: 'rgba(255,215,0,0.85)', lineWidth: 1.5, lineStyle: 2, axisLabelVisible: true, title: `Neck ${p.neckline.toFixed(2)}` });
      patternLinesRef.current.push(nl);
    }
    if (p.stop) {
      const sl = series.createPriceLine({ price: p.stop, color: 'rgba(233,30,99,0.7)', lineWidth: 1, lineStyle: 1, axisLabelVisible: false, title: 'Support' });
      patternLinesRef.current.push(sl);
    }
    if (p.entry) {
      const el = series.createPriceLine({ price: p.entry, color: 'rgba(0,230,118,0.9)', lineWidth: 2, lineStyle: 0, axisLabelVisible: true, title: `Entry ${p.entry.toFixed(2)}` });
      patternLinesRef.current.push(el);
    }

    if ((p.pattern === 'TRI_ASC' || p.pattern === 'TRI_DESC') && p.start_ts && p.end_ts) {
      const isAsc = p.pattern === 'TRI_ASC';
      const upperTL = chart.addLineSeries({ color: isAsc ? 'rgba(233,30,99,0.6)' : 'rgba(233,30,99,0.8)', lineWidth: 1.5, lineStyle: 0, lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false });
      const upperStart = isAsc ? p.neckline : (p.neckline + (p.entry - p.stop) * 0.3);
      const upperEnd = isAsc ? p.neckline : p.neckline;
      upperTL.setData([{ time: p.start_ts as any, value: upperStart }, { time: p.end_ts as any, value: upperEnd }]);
      patternTLRef.current.push(upperTL);

      const lowerTL = chart.addLineSeries({ color: isAsc ? 'rgba(0,188,212,0.8)' : 'rgba(0,188,212,0.6)', lineWidth: 1.5, lineStyle: 0, lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false });
      const lowerStart = p.stop;
      const lowerEnd = isAsc ? (p.stop + (p.neckline - p.stop) * 0.6) : p.stop;
      lowerTL.setData([{ time: p.start_ts as any, value: lowerStart }, { time: p.end_ts as any, value: lowerEnd }]);
      patternTLRef.current.push(lowerTL);
    }

    if ((p.pattern === 'HS' || p.pattern === 'IHS') && p.start_ts && p.end_ts && p.neckline) {
      const neckTL = chart.addLineSeries({ color: 'rgba(255,215,0,0.7)', lineWidth: 1.5, lineStyle: 2, lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false });
      neckTL.setData([{ time: p.start_ts as any, value: p.neckline }, { time: p.end_ts as any, value: p.neckline }]);
      patternTLRef.current.push(neckTL);
    }
  }, [scannedPatterns]);

  useEffect(() => { drawPatternLines(); }, [scannedPatterns, drawPatternLines]);

  return (
    <div style={{ position: 'relative', width: '100%', height: height ?? '100%', minHeight: height ?? 400 }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%', background: '#0d1117', borderRadius: 8, overflow: 'hidden' }} />
      <canvas ref={zoneCanvasRef} style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 2 }} />
      <canvas ref={canvasRef} style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 4 }} />
    </div>
  );
}
