'use client';
// TradeMarkChart — in-dashboard marking chart (2026-06-15, parity build).
// Standalone-tool parity, live for any (incl. historical) trade:
//   • candles + volume; bar-time x-axis (ET) + precise ENTRY time
//   • day levels POC/VAH/VAL/IB + pivots PP/R1-3/S1-3 + PDH/PDL (toggle)
//   • system entry/stop/T1/T2/exit + labeled price-tag stickers per line
//   • ENTRY ▲/▼ + EXIT ⊗ on the actual bars; setup bracket on the entry candle
//   • CVD histogram (green/red) + Woodies CCI; crosshair + readout
//   • per-level calc (stop→risk pts, target→+pts+R)
//   • ZOOM PRICE & TIME like a regular chart (mouse-wheel: over the price axis =
//     price zoom, over the chart = time zoom) + buttons + drag-to-resize height
//   • click the price panel to mark entry/stop1-3/T1-3, + "would not enter" + note
//   • SUBMIT → saves marks to the DB (v9_trades.quality.review) so they persist
//     across browsers/origins and I can derive lessons.
// Data: GET /api/v9/chart/replay?date=<trade ET date>.
import { useCallback, useEffect, useRef, useState } from 'react';
import type { Trade } from '../../types';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const TOKEN = process.env.NEXT_PUBLIC_BRIDGE_TOKEN || 'michael-mems26-2026';
const TICK = 0.25;
const PL = 46, PR = 116, PT = 8, AX = 18, GAP = 14;
const H_MIN = 360, H_MAX = 960, H_DEF = 540;
const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));

type LevelKey = 'entry' | 'stop1' | 'stop2' | 'stop3' | 't1' | 't2' | 't3';
const LEVELS: Array<{ key: LevelKey; label: string; color: string }> = [
  { key: 'entry', label: 'Entry', color: '#e3b341' }, { key: 'stop1', label: 'Stop-1', color: '#f85149' },
  { key: 'stop2', label: 'Stop-2 (after T1)', color: '#ff9d76' }, { key: 'stop3', label: 'Stop-3 (after T2)', color: '#ffc1a1' },
  { key: 't1', label: 'T1', color: '#56d364' }, { key: 't2', label: 'T2', color: '#58a6ff' }, { key: 't3', label: 'T3', color: '#bc8cff' },
];

interface MarkEntry { no_entry?: boolean; note?: string; pat?: string; day_type?: string; dir?: string; [k: string]: unknown; }
type MarksMap = Record<string, MarkEntry>;
interface Bar { t: number; o: number; h: number; l: number; c: number; v: number; cci: number | null; cum: number | null; }
interface Levels { poc?: number | null; vah?: number | null; val?: number | null; ib_high?: number | null; ib_low?: number | null; pdh?: number | null; pdl?: number | null; pp?: number | null; r1?: number | null; r2?: number | null; r3?: number | null; s1?: number | null; s2?: number | null; s3?: number | null; }
interface DrawState { all: Bar[]; levels: Levels; }
interface Geom { vis: Bar[]; lo: number; hi: number; y0p: number; y1p: number; }

function loadMarks(): MarksMap { try { return JSON.parse(localStorage.getItem('mems26_marks') || '{}') as MarksMap; } catch { return {}; } }
function saveMarks(m: MarksMap) { try { localStorage.setItem('mems26_marks', JSON.stringify(m)); } catch { /* ignore */ } }
const roundTick = (p: number) => Math.round(p / TICK) * TICK;
const num = (v: unknown) => (typeof v === 'number' ? String(v) : '—');
const etDate = (iso: string) => { try { return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(iso)); } catch { return iso.slice(0, 10); } };
const _hhmm = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', hour12: false });
const _hms = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
const hhmm = (s: number) => _hhmm.format(new Date(s * 1000));
const hms = (s: number) => _hms.format(new Date(s * 1000));
const lum = (hex: string) => { const n = parseInt(hex.slice(1), 16); return (0.299 * ((n >> 16) & 255) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255; };
const txtOn = (hex: string) => (lum(hex) > 0.6 ? '#0d1117' : '#ffffff');

export function TradeMarkChart({ trade, onChange }: { trade: Trade; onChange?: () => void }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const readoutRef = useRef<HTMLDivElement>(null);
  const drawState = useRef<DrawState | null>(null);
  const geomRef = useRef<Geom | null>(null);
  const markRef = useRef<MarkEntry>({});
  const activeRef = useRef<LevelKey>('entry');
  const winRef = useRef<number>(60);
  const pzRef = useRef<number>(1);
  const showLvlRef = useRef<boolean>(true);
  const mouseRef = useRef<{ x: number; y: number } | null>(null);
  const hRef = useRef<number>(H_DEF);
  const drag = useRef<{ on: boolean; y0: number; h0: number }>({ on: false, y0: 0, h0: H_DEF });
  const axisDrag = useRef<{ mode: '' | 'price' | 'time'; x0: number; y0: number; pz0: number; win0: number }>({ mode: '', x0: 0, y0: 0, pz0: 1, win0: 60 });

  const [active, setActive] = useState<LevelKey>('entry');
  const [mark, setMark] = useState<MarkEntry>({});
  const [status, setStatus] = useState<string>('loading…');
  const [winMin, setWinMin] = useState<number>(60);
  const [priceZoom, setPriceZoom] = useState<number>(1);
  const [showLevels, setShowLevels] = useState<boolean>(true);
  const [chartH, setChartH] = useState<number>(H_DEF);
  const [submitMsg, setSubmitMsg] = useState<string>('');

  useEffect(() => { activeRef.current = active; }, [active]);
  useEffect(() => { markRef.current = mark; }, [mark]);
  useEffect(() => { winRef.current = winMin; }, [winMin]);
  useEffect(() => { pzRef.current = priceZoom; }, [priceZoom]);
  useEffect(() => { showLvlRef.current = showLevels; }, [showLevels]);
  useEffect(() => { hRef.current = chartH; }, [chartH]);

  const persist = useCallback((next: MarkEntry) => {
    const all = loadMarks();
    all[String(trade.id)] = { ...next, pat: trade.pattern_id ?? undefined, day_type: trade.day_type ?? undefined, dir: trade.direction };
    saveMarks(all); setMark(all[String(trade.id)]); setSubmitMsg(''); onChange?.();
  }, [trade.id, trade.pattern_id, trade.day_type, trade.direction, onChange]);
  const persistRef = useRef(persist);
  useEffect(() => { persistRef.current = persist; }, [persist]);

  const entryS = trade.entry_ts ? Math.floor(new Date(trade.entry_ts).getTime() / 1000) : 0;
  const exitS = trade.exit_ts ? Math.floor(new Date(trade.exit_ts).getTime() / 1000) : entryS + 1800;
  const isLong = trade.direction === 'LONG';
  const sysStop = trade.stop_initial ?? trade.stop;

  const draw = useCallback(() => {
    const cv = canvasRef.current, ds = drawState.current;
    if (!cv || !ds) return;
    const ctx = cv.getContext('2d'); if (!ctx) return;
    const W = cv.width, H = cv.height;
    const inner = H - PT - AX - 2 * GAP;
    const priceH = Math.round(inner * 0.62), cvdH = Math.round(inner * 0.19), cciH = inner - priceH - cvdH;
    const Y0p = PT, Y1p = PT + priceH, Y0c = Y1p + GAP, Y1c = Y0c + cvdH, Y0i = Y1c + GAP, Y1i = Y0i + cciH;

    const win = winRef.current * 60;
    const vis = ds.all.filter((b) => b.t >= entryS - win && b.t <= exitS + win);
    if (vis.length === 0) return;
    const cur = markRef.current, lv = ds.levels;

    const sysVals = [trade.entry_price, sysStop, trade.t1, trade.t2, trade.exit_price].filter((v): v is number => v != null);
    const markVals = Object.values(cur).filter((v): v is number => typeof v === 'number');
    const loB = Math.min(...vis.map((b) => b.l), ...sysVals, ...markVals) - 2;
    const hiB = Math.max(...vis.map((b) => b.h), ...sysVals, ...markVals) + 2;
    // price zoom around midpoint
    const mid = (loB + hiB) / 2, half = ((hiB - loB) / 2) / pzRef.current;
    const lo = mid - half, hi = mid + half;
    geomRef.current = { vis, lo, hi, y0p: Y0p, y1p: Y1p };

    const n = vis.length, plotW = W - PL - PR, span = hi - lo || 1;
    const X = (i: number) => PL + (n > 1 ? (i * plotW) / (n - 1) : plotW / 2);
    const Yp = (p: number) => Y0p + ((hi - p) * (Y1p - Y0p)) / span;
    const cw = Math.max(2, (plotW / Math.max(n, 1)) * 0.6);

    ctx.clearRect(0, 0, W, H); ctx.fillStyle = '#0d1117'; ctx.fillRect(0, 0, W, H);
    ctx.font = '10px ui-monospace, monospace'; ctx.textBaseline = 'middle';
    const step = span > 60 ? 20 : span > 40 ? 10 : span > 16 ? 5 : span > 6 ? 2 : 1;
    ctx.textAlign = 'right';
    for (let p = Math.ceil(lo / step) * step; p <= hi; p += step) {
      const y = Yp(p); ctx.strokeStyle = '#1b2027'; ctx.beginPath(); ctx.moveTo(PL, y); ctx.lineTo(W - PR, y); ctx.stroke();
      ctx.fillStyle = '#8b949e'; ctx.fillText(p.toFixed(p % 1 ? 2 : 0), PL - 5, y);  // Y-axis price label
    }
    ctx.textAlign = 'left';

    const ei = vis.findIndex((b) => Math.abs(b.t - entryS) < 150);
    const xi = vis.findIndex((b) => Math.abs(b.t - exitS) < 150);
    if (ei >= 0) { ctx.fillStyle = 'rgba(227,179,65,0.10)'; ctx.fillRect(X(ei) - cw, Y0p, cw * 2, Y1p - Y0p); }
    if (xi >= 0) { ctx.fillStyle = 'rgba(163,113,247,0.10)'; ctx.fillRect(X(xi) - cw, Y0p, cw * 2, Y1p - Y0p); }

    const vmax = Math.max(1, ...vis.map((b) => b.v || 0)), volH = (Y1p - Y0p) * 0.18;
    ctx.fillStyle = 'rgba(110,118,129,0.30)';
    vis.forEach((b, i) => { const h = (volH * (b.v || 0)) / vmax; ctx.fillRect(X(i) - cw / 2, Y1p - h, cw, h); });
    vis.forEach((b, i) => {
      const x = X(i), up = b.c >= b.o; ctx.strokeStyle = up ? '#3fb950' : '#f85149'; ctx.fillStyle = ctx.strokeStyle;
      ctx.beginPath(); ctx.moveTo(x, Yp(b.h)); ctx.lineTo(x, Yp(b.l)); ctx.stroke();
      const yo = Yp(b.o), yc = Yp(b.c); ctx.fillRect(x - cw / 2, Math.min(yo, yc), cw, Math.max(1, Math.abs(yo - yc)));
    });

    type Tag = { y: number; color: string; text: string };
    const tags: Tag[] = [];
    const line = (price: number | null | undefined, color: string, label: string, dash: number[]) => {
      if (price == null) return; const y = Yp(price); if (y < Y0p - 1 || y > Y1p + 1) return;
      ctx.save(); ctx.strokeStyle = color; ctx.setLineDash(dash); ctx.lineWidth = dash.length ? 1 : 1.6;
      ctx.beginPath(); ctx.moveTo(PL, y); ctx.lineTo(W - PR, y); ctx.stroke(); ctx.restore();
      tags.push({ y, color, text: `${label} ${price}` });
    };
    if (showLvlRef.current) {
      line(lv.poc, '#d2a8ff', 'POC', [1, 3]); line(lv.vah, '#a5d6ff', 'VAH', [1, 3]); line(lv.val, '#a5d6ff', 'VAL', [1, 3]);
      line(lv.ib_high, '#ffa657', 'IBH', [1, 5]); line(lv.ib_low, '#ffa657', 'IBL', [1, 5]);
      line(lv.pp, '#ff7bf2', 'PP', [1, 4]); line(lv.r1, '#ff6b6b', 'R1', [1, 6]); line(lv.r2, '#ff6b6b', 'R2', [1, 6]); line(lv.r3, '#ff6b6b', 'R3', [1, 6]);
      line(lv.s1, '#3fb950', 'S1', [1, 6]); line(lv.s2, '#3fb950', 'S2', [1, 6]); line(lv.s3, '#3fb950', 'S3', [1, 6]);
      line(lv.pdh, '#7ee787', 'PDH', [2, 4]); line(lv.pdl, '#ffa198', 'PDL', [2, 4]);
    }
    line(trade.entry_price, '#c9a227', 'sysEntry', [3, 3]); line(sysStop, '#d05050', 'sysStop', [3, 3]);
    line(trade.t1, '#3fb07a', 'sysT1', [3, 3]); line(trade.t2, '#5a8acb', 'sysT2', [3, 3]); line(trade.exit_price, '#a371f7', 'Exit', [3, 3]);
    LEVELS.forEach((l) => { const v = cur[l.key]; if (typeof v === 'number') line(v, l.color, '✎' + l.label, []); });
    tags.sort((a, b) => a.y - b.y);
    for (let i = 1; i < tags.length; i++) if (tags[i].y - tags[i - 1].y < 12) tags[i].y = tags[i - 1].y + 12;
    ctx.font = 'bold 9px ui-monospace, monospace';
    tags.forEach((t) => {
      const tw = ctx.measureText(t.text).width, bw = tw + 7, bx = W - PR + 3, by = clamp(t.y, Y0p + 6, Y1p - 6), rr = 3;
      ctx.fillStyle = t.color; ctx.beginPath();
      ctx.moveTo(bx + rr, by - 6); ctx.arcTo(bx + bw, by - 6, bx + bw, by + 6, rr); ctx.arcTo(bx + bw, by + 6, bx, by + 6, rr); ctx.arcTo(bx, by + 6, bx, by - 6, rr); ctx.arcTo(bx, by - 6, bx + bw, by - 6, rr); ctx.fill();
      ctx.fillStyle = txtOn(t.color); ctx.fillText(t.text, bx + 4, by);
    });

    // setup bracket on entry candle
    if (ei >= 0) {
      const ex = X(ei);
      const br: Array<[number | null | undefined, string]> = [[trade.entry_price, '#e3b341'], [sysStop, '#f85149'], [trade.t1, '#56d364'], [trade.t2, '#58a6ff']];
      const ys = br.filter(([p]) => p != null).map(([p]) => Yp(p as number));
      if (ys.length > 1) { ctx.strokeStyle = '#3b4048'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(ex, Math.min(...ys)); ctx.lineTo(ex, Math.max(...ys)); ctx.stroke(); }
      br.forEach(([p, c]) => { if (p == null) return; const y = Yp(p as number); ctx.strokeStyle = c; ctx.fillStyle = c; ctx.lineWidth = 1.6; ctx.beginPath(); ctx.moveTo(ex - 5, y); ctx.lineTo(ex + 5, y); ctx.stroke(); ctx.beginPath(); ctx.arc(ex, y, 2.5, 0, 7); ctx.fill(); }); ctx.lineWidth = 1;
    }
    ctx.font = 'bold 13px ui-monospace, monospace';
    if (ei >= 0 && trade.entry_price != null) {
      const x = X(ei), y = Yp(trade.entry_price), col = isLong ? '#56d364' : '#f85149'; ctx.fillStyle = col; ctx.beginPath();
      if (isLong) { ctx.moveTo(x, y + 12); ctx.lineTo(x - 6, y + 22); ctx.lineTo(x + 6, y + 22); } else { ctx.moveTo(x, y - 12); ctx.lineTo(x - 6, y - 22); ctx.lineTo(x + 6, y - 22); }
      ctx.closePath(); ctx.fill(); ctx.fillText((isLong ? '▲ ' : '▼ ') + 'ENTRY', x + 8, y + (isLong ? 20 : -18));
    }
    if (xi >= 0 && trade.exit_price != null) {
      const x = X(xi), y = Yp(trade.exit_price); ctx.strokeStyle = '#a371f7'; ctx.fillStyle = '#a371f7'; ctx.lineWidth = 1.6;
      ctx.beginPath(); ctx.arc(x, y, 5, 0, 7); ctx.stroke(); ctx.beginPath(); ctx.moveTo(x - 4, y - 4); ctx.lineTo(x + 4, y + 4); ctx.moveTo(x + 4, y - 4); ctx.lineTo(x - 4, y + 4); ctx.stroke();
      ctx.fillText('⊗ EXIT' + (trade.exit_reason ? ' ' + trade.exit_reason : ''), x + 8, y); ctx.lineWidth = 1;
    }

    ctx.font = '10px ui-monospace, monospace';
    const cums = vis.map((b) => b.cum).filter((x): x is number => x != null);
    if (cums.length) {
      const clo = Math.min(0, ...cums), chi = Math.max(0, ...cums), cspan = chi - clo || 1;
      const Yc = (val: number) => Y0c + ((chi - val) * (Y1c - Y0c)) / cspan;
      ctx.strokeStyle = '#30363d'; ctx.beginPath(); ctx.moveTo(PL, Yc(0)); ctx.lineTo(W - PR, Yc(0)); ctx.stroke();
      let prev: number | null = null;
      vis.forEach((b, i) => { if (b.cum == null) return; const x = X(i), y0 = Yc(0), y1 = Yc(b.cum); ctx.fillStyle = prev != null && b.cum < prev ? '#f85149' : '#56d364'; ctx.fillRect(x - cw / 2, Math.min(y0, y1), cw, Math.max(1, Math.abs(y1 - y0))); prev = b.cum; });
      ctx.fillStyle = '#8b949e'; ctx.fillText('CVD (cumulative delta)', PL + 2, Y0c + 8);
    }
    const ccis = vis.map((b) => b.cci).filter((x): x is number => x != null);
    if (ccis.length) {
      const cmax = Math.max(120, ...ccis.map((c) => Math.abs(c)));
      const Yi = (val: number) => Y0i + ((cmax - val) * (Y1i - Y0i)) / (2 * cmax);
      [100, 0, -100].forEach((g) => { ctx.strokeStyle = g === 0 ? '#30363d' : '#23282f'; ctx.beginPath(); ctx.moveTo(PL, Yi(g)); ctx.lineTo(W - PR, Yi(g)); ctx.stroke(); ctx.fillStyle = '#6e7681'; ctx.fillText(String(g), W - PR + 5, Yi(g)); });
      ctx.fillStyle = '#8b949e'; ctx.fillText('Woodies CCI', PL + 2, Y0i + 8);
      ctx.strokeStyle = '#d2a8ff'; ctx.lineWidth = 1.3; ctx.beginPath(); let s2 = false;
      vis.forEach((b, i) => { if (b.cci == null) { s2 = false; return; } const x = X(i), y = Yi(b.cci); if (!s2) { ctx.moveTo(x, y); s2 = true; } else ctx.lineTo(x, y); }); ctx.stroke(); ctx.lineWidth = 1;
    }

    const axisY = Y1i + 12; ctx.fillStyle = '#8b949e'; ctx.textBaseline = 'middle';
    const tstep = Math.max(1, Math.floor(n / 8));
    for (let i = 0; i < n; i += tstep) ctx.fillText(hhmm(vis[i].t), X(i) - 14, axisY);
    if (ei >= 0) { const x = X(ei); ctx.strokeStyle = isLong ? '#56d364' : '#f85149'; ctx.setLineDash([2, 2]); ctx.beginPath(); ctx.moveTo(x, Y0p); ctx.lineTo(x, Y1i); ctx.stroke(); ctx.setLineDash([]); ctx.fillStyle = isLong ? '#56d364' : '#f85149'; ctx.font = 'bold 10px ui-monospace, monospace'; ctx.fillText('ENTRY ' + hms(entryS), clamp(x - 24, PL, W - PR - 78), axisY); ctx.font = '10px ui-monospace, monospace'; }

    const mo = mouseRef.current;
    if (mo && readoutRef.current) {
      const idx = Math.round(((mo.x - PL) / plotW) * (n - 1)), bi = clamp(idx, 0, n - 1), b = vis[bi];
      ctx.strokeStyle = '#3b4048'; ctx.setLineDash([3, 3]); ctx.beginPath(); ctx.moveTo(X(bi), Y0p); ctx.lineTo(X(bi), Y1i); ctx.stroke();
      if (mo.y >= Y0p && mo.y <= Y1p) { ctx.beginPath(); ctx.moveTo(PL, mo.y); ctx.lineTo(W - PR, mo.y); ctx.stroke(); } ctx.setLineDash([]);
      const price = hi - ((clamp(mo.y, Y0p, Y1p) - Y0p) * span) / (Y1p - Y0p);
      readoutRef.current.textContent = `${(Math.round(price * 4) / 4).toFixed(2)} · ${hms(b.t)}  O:${b.o} H:${b.h} L:${b.l} C:${b.c}${b.cci != null ? '  CCI:' + b.cci.toFixed(0) : ''}`;
    }
  }, [trade.entry_price, sysStop, trade.t1, trade.t2, trade.exit_price, trade.exit_reason, entryS, exitS, isLong]);

  useEffect(() => {
    const wrap = wrapRef.current, cv = canvasRef.current;
    if (!wrap || !cv || !trade.entry_ts) { setStatus('no entry timestamp'); return; }
    let disposed = false;
    const loaded = loadMarks()[String(trade.id)] || {}; setMark(loaded); setStatus('loading…'); setSubmitMsg('');
    (async () => {
      try {
        const res = await fetch(`${API}/api/v9/chart/replay?date=${etDate(trade.entry_ts!)}`);
        if (disposed) return; if (!res.ok) { setStatus(`data unavailable (${res.status})`); return; }
        const d = (await res.json()) as { bars: Array<{ ts: string; o: number; h: number; l: number; c: number; v: number; cci: number | null; cum_delta: number | null }>; levels: Levels };
        if (disposed) return;
        const all: Bar[] = (d.bars || []).map((b) => ({ t: Math.floor(new Date(b.ts).getTime() / 1000), o: b.o, h: b.h, l: b.l, c: b.c, v: b.v, cci: b.cci, cum: b.cum_delta })).sort((a, b) => a.t - b.t);
        if (all.length === 0) { setStatus('no bars for this date'); return; }
        cv.width = wrap.clientWidth || 900; cv.height = hRef.current;
        drawState.current = { all, levels: d.levels || {} }; setStatus(''); draw();
      } catch (e) { if (!disposed) setStatus('chart error'); console.warn('TradeMarkChart load failed', e); }
    })();
    return () => { disposed = true; };
  }, [trade.id, trade.entry_ts, draw]);

  useEffect(() => { const cv = canvasRef.current; if (cv && drawState.current) { cv.height = chartH; draw(); } }, [mark, winMin, priceZoom, showLevels, chartH, draw]);
  useEffect(() => { const wrap = wrapRef.current, cv = canvasRef.current; if (!wrap || !cv) return; const ro = new ResizeObserver(() => { if (drawState.current && wrap.clientWidth) { cv.width = wrap.clientWidth; draw(); } }); ro.observe(wrap); return () => ro.disconnect(); }, [draw]);
  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (drag.current.on) { setChartH(clamp(drag.current.h0 + (e.clientY - drag.current.y0), H_MIN, H_MAX)); return; }
      const ad = axisDrag.current; if (!ad.mode) return;
      const cv = canvasRef.current; if (!cv) return; const r = cv.getBoundingClientRect();
      const x = (e.clientX - r.left) * (cv.width / r.width), y = (e.clientY - r.top) * (cv.height / r.height);
      if (ad.mode === 'price') setPriceZoom(clamp(ad.pz0 * Math.exp((ad.y0 - y) / 150), 0.25, 8));
      else setWinMin(clamp(Math.round(ad.win0 / Math.exp((x - ad.x0) / 200)), 10, 600));
    };
    const onUp = () => { drag.current.on = false; axisDrag.current.mode = ''; };
    window.addEventListener('mousemove', onMove); window.addEventListener('mouseup', onUp);
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
  }, []);
  // mouse-wheel zoom: over the price axis = price; over the chart = time
  useEffect(() => {
    const cv = canvasRef.current; if (!cv) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault(); const r = cv.getBoundingClientRect(); const x = (e.clientX - r.left) * (cv.width / r.width);
      if (x > cv.width - PR) setPriceZoom((z) => clamp(z * (e.deltaY < 0 ? 1.12 : 1 / 1.12), 0.25, 8));
      else setWinMin((w) => clamp(Math.round(w * (e.deltaY < 0 ? 1 / 1.12 : 1.12)), 10, 600));
    };
    cv.addEventListener('wheel', onWheel, { passive: false }); return () => cv.removeEventListener('wheel', onWheel);
  }, []);

  const toCanvas = (e: React.MouseEvent<HTMLCanvasElement>) => { const cv = canvasRef.current!; const r = cv.getBoundingClientRect(); return { x: (e.clientX - r.left) * (cv.width / r.width), y: (e.clientY - r.top) * (cv.height / r.height) }; };
  const onMove = (e: React.MouseEvent<HTMLCanvasElement>) => { mouseRef.current = toCanvas(e); draw(); };
  const onLeave = () => { mouseRef.current = null; draw(); if (readoutRef.current) readoutRef.current.textContent = 'hover a bar · scroll over chart = zoom time · scroll over price axis = zoom price'; };
  const onClick = (e: React.MouseEvent<HTMLCanvasElement>) => { const g = geomRef.current; if (!g) return; const { x, y } = toCanvas(e); const cv = canvasRef.current!; if (x < PL || x > cv.width - PR || y < g.y0p || y > g.y1p) return; const price = g.hi - ((y - g.y0p) * (g.hi - g.lo)) / (g.y1p - g.y0p); persistRef.current({ ...(loadMarks()[String(trade.id)] || {}), [activeRef.current]: roundTick(price) }); };
  // drag the PRICE axis (right) to zoom price, or the TIME axis (bottom) to zoom time
  const onDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const cv = canvasRef.current!; const { x, y } = toCanvas(e);
    if (x > cv.width - PR) axisDrag.current = { mode: 'price', x0: x, y0: y, pz0: pzRef.current, win0: winRef.current };
    else if (y > cv.height - 30) axisDrag.current = { mode: 'time', x0: x, y0: y, pz0: pzRef.current, win0: winRef.current };
  };

  const toggleNoEntry = () => persist({ ...markRef.current, no_entry: !markRef.current.no_entry });
  const saveNote = (note: string) => persist({ ...markRef.current, note });
  const clearLevels = () => persist({ no_entry: mark.no_entry, note: mark.note });
  const submit = async () => {
    setSubmitMsg('saving…');
    try { const res = await fetch(`${API}/api/v9/trades/${trade.id}/review`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${TOKEN}` }, body: JSON.stringify({ marks: loadMarks()[String(trade.id)] || {} }) }); setSubmitMsg(res.ok ? 'submitted ✓ (saved to DB)' : `submit failed (${res.status})`); onChange?.(); }
    catch { setSubmitMsg('submit failed (network)'); }
  };

  const sgn = isLong ? 1 : -1;
  const me = typeof mark.entry === 'number' ? (mark.entry as number) : null;
  const ms = typeof mark.stop1 === 'number' ? (mark.stop1 as number) : null;
  const risk = me != null && ms != null ? Math.abs(me - ms) : null;
  const sysRisk = trade.entry_price != null && sysStop != null ? Math.abs(trade.entry_price - sysStop) : null;
  const sysR = (lvl: number | null | undefined) => (lvl != null && trade.entry_price != null && sysRisk ? (Math.abs(lvl - trade.entry_price) / sysRisk).toFixed(2) + 'R' : '—');
  const rTo = (lvl: unknown) => (typeof lvl === 'number' && me != null && risk && risk > 0 ? (Math.abs((lvl as number) - me) / risk).toFixed(2) + 'R' : '—');
  const calcFor = (k: LevelKey): string => {
    const v = mark[k]; if (typeof v !== 'number') return '';
    if (k === 'entry') return `${v}`;
    if (k.startsWith('stop')) { const r = (me ?? v) != null && me != null ? (me - v) * sgn : null; return me != null ? `${v} (${r != null && r >= 0 ? 'risk ' + r.toFixed(1) : 'lock +' + Math.abs(r ?? 0).toFixed(1)}pt)` : `${v}`; }
    const rew = me != null ? (v - me) * sgn : null; const R = rew != null && risk ? (rew / risk).toFixed(2) + 'R' : ''; return me != null ? `${v} (+${(rew ?? 0).toFixed(1)}pt${R ? ' ' + R : ''})` : `${v}`;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
        <span style={{ background: isLong ? '#1a7f37' : '#b62324', color: '#fff', padding: '2px 8px', borderRadius: 5, fontWeight: 700, fontSize: 12 }}>{isLong ? '▲ LONG' : '▼ SHORT'}</span>
        {trade.day_type && <span style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', color: '#d2a8ff', padding: '2px 8px', borderRadius: 5, fontSize: 11 }}>{trade.day_type}</span>}
        <span style={{ color: 'var(--text-secondary)', fontSize: 11, marginInlineStart: 6 }}>Mark:</span>
        {LEVELS.map((l) => (<button key={l.key} onClick={() => setActive(l.key)} style={{ padding: '3px 9px', borderRadius: 6, cursor: 'pointer', fontSize: 12, border: `1px solid ${active === l.key ? l.color : 'var(--border)'}`, outline: active === l.key ? `1px solid ${l.color}` : 'none', background: active === l.key ? 'rgba(255,255,255,0.06)' : 'transparent', color: l.color, fontWeight: active === l.key ? 700 : 400 }}>{l.label}{typeof mark[l.key] === 'number' ? ` ·${num(mark[l.key])}` : ''}</button>))}
        <button onClick={clearLevels} style={{ padding: '3px 9px', borderRadius: 6, cursor: 'pointer', fontSize: 12, border: '1px solid var(--border)', background: 'transparent', color: 'var(--text-secondary)' }}>Clear</button>
        <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 3, marginInlineStart: 4 }}><input type="checkbox" checked={showLevels} onChange={(e) => setShowLevels(e.target.checked)} /> levels</label>
        <span style={{ marginInlineStart: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ display: 'flex', gap: 3, alignItems: 'center' }}><span style={{ fontSize: 10, color: 'var(--text-secondary)' }}>price</span><button onClick={() => setPriceZoom((z) => clamp(z / 1.3, 0.25, 8))} style={btn}>−</button><button onClick={() => setPriceZoom((z) => clamp(z * 1.3, 0.25, 8))} style={btn}>+</button></span>
          <span style={{ display: 'flex', gap: 3, alignItems: 'center' }}><span style={{ fontSize: 10, color: 'var(--text-secondary)' }}>time</span><button onClick={() => setWinMin((w) => clamp(Math.round(w * 1.5), 10, 600))} style={btn}>−</button><span style={{ fontSize: 11, color: 'var(--text-secondary)', fontFamily: 'var(--mono)' }}>±{winMin}m</span><button onClick={() => setWinMin((w) => clamp(Math.round(w / 1.5), 10, 600))} style={btn}>+</button></span>
        </span>
      </div>

      {/* top summary row: day type · system risk/reward · your risk/reward after marking */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', fontFamily: 'var(--mono)', fontSize: 12, padding: '3px 8px', background: 'var(--bg-secondary)', borderRadius: 6 }}>
        <span>Day <b style={{ color: '#d2a8ff' }}>{trade.day_type ?? '—'}</b></span>
        <span style={{ color: 'var(--text-secondary)' }}>·</span>
        <span style={{ color: 'var(--text-secondary)' }}>System:</span>
        <span>risk <b style={{ color: '#f85149' }}>{sysRisk != null ? sysRisk.toFixed(2) + 'pt' : '—'}</b></span>
        <span>→T1 <b style={{ color: '#56d364' }}>{sysR(trade.t1)}</b></span>
        <span>→T2 <b style={{ color: '#58a6ff' }}>{sysR(trade.t2)}</b></span>
        <span style={{ color: 'var(--text-secondary)' }}>· You:</span>
        <span>risk <b style={{ color: '#f85149' }}>{risk != null ? risk.toFixed(2) + 'pt' : '—'}</b></span>
        <span>→T1 <b style={{ color: '#56d364' }}>{rTo(mark.t1)}</b></span>
        <span>→T2 <b style={{ color: '#58a6ff' }}>{rTo(mark.t2)}</b></span>
      </div>
      <div ref={readoutRef} style={{ fontFamily: 'var(--mono)', fontSize: 12, color: '#e3b341', minHeight: 16 }}>hover a bar · scroll or drag the price axis = zoom price · scroll over chart or drag the time axis = zoom time</div>

      <div ref={wrapRef} style={{ width: '100%', height: chartH, background: '#0d1117', borderRadius: 4, position: 'relative' }}>
        <canvas ref={canvasRef} height={chartH} onMouseDown={onDown} onClick={onClick} onMouseMove={onMove} onMouseLeave={onLeave} style={{ width: '100%', height: chartH, display: 'block', cursor: 'crosshair' }} />
        {status && <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#8b949e', fontSize: 13, pointerEvents: 'none' }}>{status}</div>}
      </div>
      <div onMouseDown={(e) => { drag.current = { on: true, y0: e.clientY, h0: chartH }; e.preventDefault(); }} title="drag to resize chart" style={{ height: 8, cursor: 'ns-resize', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)', background: 'var(--bg-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', fontSize: 9, lineHeight: '8px' }}>⋯ drag to resize ⋯</div>

      {/* per-level calc */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', fontFamily: 'var(--mono)', fontSize: 12 }}>
        {(['entry', 'stop1', 't1', 't2', 't3'] as LevelKey[]).map((k) => { const c = calcFor(k); return c ? <span key={k} style={{ color: LEVELS.find((l) => l.key === k)!.color }}>{LEVELS.find((l) => l.key === k)!.label}: {c}</span> : null; })}
        {risk == null && <span style={{ color: 'var(--text-secondary)' }}>mark Entry + Stop-1 to see risk/R…</span>}
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <button onClick={toggleNoEntry} style={{ padding: '4px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 12, border: `1px solid ${mark.no_entry ? '#f85149' : 'var(--border)'}`, background: mark.no_entry ? '#f85149' : 'transparent', color: mark.no_entry ? '#fff' : '#f85149', fontWeight: mark.no_entry ? 700 : 400 }}>🚫 {mark.no_entry ? "Wouldn't enter (marked)" : "I wouldn't enter this"}</button>
        <button onClick={submit} style={{ padding: '4px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 12, border: 'none', background: '#1f6feb', color: '#fff', fontWeight: 700 }}>⤴ Submit (save to DB)</button>
        {submitMsg && <span style={{ fontSize: 12, color: submitMsg.includes('✓') ? '#56d364' : submitMsg.includes('fail') ? '#f85149' : 'var(--text-secondary)' }}>{submitMsg}</span>}
      </div>
      <textarea value={typeof mark.note === 'string' ? mark.note : ''} onChange={(e) => saveNote(e.target.value)} placeholder={mark.no_entry ? 'Why not? (this becomes a rule)' : 'Notes: why here, the general rule…'} rows={2} style={{ width: '100%', background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border)', borderRadius: 6, padding: 6, fontSize: 13, boxSizing: 'border-box', resize: 'vertical' }} />
    </div>
  );
}

const btn: React.CSSProperties = { padding: '1px 8px', borderRadius: 6, cursor: 'pointer', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text-primary)', fontSize: 13 };
