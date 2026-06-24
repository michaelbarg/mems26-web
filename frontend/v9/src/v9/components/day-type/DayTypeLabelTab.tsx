'use client';
// DayTypeLabelTab — manual day-type labeler (2026-06-20).
// Pick a date → see that day's RTH 5-min bars + key levels → CLICK the chart to
// split the day into time segments → tag each segment with a day-type. This is the
// human ground-truth for calibrating the S1 classifier (config/daytype_trading_plan.yaml)
// day-by-day. Persists to localStorage (key mems26_daytype_labels), like the marker tool.
// Data: GET /api/v9/chart/replay?date=YYYY-MM-DD (same read-only aggregator).
import { useCallback, useEffect, useRef, useState } from 'react';
import { DayTypeConditionsTable } from '../build_status/DayTypeConditionsTable';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const DAY_TYPES = [
  'FORMING', 'Nontrend', 'Normal', 'Normal_Variation',
  'Neutral_Center', 'Neutral_Extreme', 'Trend_DD', 'Trend_Normal',
] as const;
type DayTypeName = (typeof DAY_TYPES)[number];
const DT_COLOR: Record<string, string> = {
  FORMING: '#8b949e', Nontrend: '#a85751', Normal: '#d2a106', Normal_Variation: '#bfae3b',
  Neutral_Center: '#58a6ff', Neutral_Extreme: '#bc8cff', Trend_DD: '#3fb950', Trend_Normal: '#56d364',
};

interface Bar { t: number; o: number; h: number; l: number; c: number; v: number; }
interface Levels { poc?: number | null; vah?: number | null; val?: number | null; ib_high?: number | null; ib_low?: number | null; pdh?: number | null; pdl?: number | null; }
interface Segment { startBar: number; dayType: DayTypeName; }
interface DayLabel { segments: Segment[]; note?: string; }
type LabelMap = Record<string, DayLabel>;

const LS = 'mems26_daytype_labels';
const loadLabels = (): LabelMap => { try { return JSON.parse(localStorage.getItem(LS) || '{}') as LabelMap; } catch { return {}; } };
const saveLabels = (m: LabelMap) => { try { localStorage.setItem(LS, JSON.stringify(m)); } catch { /* ignore */ } };

const PL = 48, PR = 64, PT = 26, AX = 20;
const todayISO = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
const etHM = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', hour12: false });
const hhmm = (s: number) => etHM.format(new Date(s * 1000));
const isRTH = (s: number) => { const [h, m] = etHM.format(new Date(s * 1000)).split(':').map(Number); const mins = h * 60 + m; return mins >= 570 && mins < 960; }; // 09:30–16:00 ET
const shiftDate = (d: string, days: number) => { const dt = new Date(d + 'T12:00:00'); dt.setDate(dt.getDate() + days); return dt.toISOString().slice(0, 10); };

export function DayTypeLabelTab() {
  const [date, setDate] = useState<string>(todayISO());
  const [bars, setBars] = useState<Bar[]>([]);
  const [levels, setLevels] = useState<Levels>({});
  const [status, setStatus] = useState<string>('loading…');
  const [labels, setLabels] = useState<LabelMap>(() => loadLabels());
  const [autoSegs, setAutoSegs] = useState<Array<{ startBar: number; day_type: string; status: string; time: string; reason?: string }>>([]);
  const [autoFinal, setAutoFinal] = useState<{ day_type: string; status: string; opening_invalidated?: boolean } | null>(null);
  const [autoN, setAutoN] = useState<number>(0);
  const [autoIB, setAutoIB] = useState<{ width: number | null; klass: string | null } | null>(null);
  const [autoDrivers, setAutoDrivers] = useState<{ opening?: string | null; loc?: string | null; pocdrift?: number | null; dd?: boolean; vol?: number | null } | null>(null);
  const [autoStatus, setAutoStatus] = useState<string>('');
  const [autoMeasured, setAutoMeasured] = useState<{ sides?: number; rib?: number; close_pos?: number; one_tf?: string | null; cvd_pos?: number | null } | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const geom = useRef<{ x0: number; bw: number; n: number } | null>(null);

  const label: DayLabel = labels[date] || { segments: [{ startBar: 0, dayType: 'FORMING' }] };

  useEffect(() => {
    let cancel = false;
    setStatus('loading…');
    fetch(`${API}/api/v9/chart/replay?date=${date}`)
      .then((r) => r.json())
      .then((d) => {
        if (cancel) return;
        const bs: Bar[] = (d.bars || [])
          .map((b: Record<string, unknown>) => ({ t: Math.floor(new Date(b.ts as string).getTime() / 1000), o: +(b.o as number), h: +(b.h as number), l: +(b.l as number), c: +(b.c as number), v: +((b.v as number) || 0) }))
          .filter((b: Bar) => isRTH(b.t));
        setBars(bs); setLevels((d.levels as Levels) || {});
        setStatus(bs.length ? `${bs.length} RTH bars · ${hhmm(bs[0].t)}–${hhmm(bs[bs.length - 1].t)}` : 'no RTH bars for this date');
      })
      .catch((e) => { if (!cancel) setStatus('error: ' + (e as Error).message); });
    return () => { cancel = true; };
  }, [date]);

  // how the ALGORITHM classifies the day (the auto-classifier timeline) — shown next to the manual label
  useEffect(() => {
    let cancel = false;
    setAutoStatus('…'); setAutoSegs([]); setAutoFinal(null); setAutoN(0); setAutoIB(null); setAutoDrivers(null); setAutoMeasured(null);
    fetch(`${API}/api/v9/day_type/classify_replay?date=${date}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))))
      .then((d) => { if (cancel) return; setAutoSegs(d.segments || []); setAutoFinal(d.final || null); setAutoN(d.n_bars || 0); setAutoIB({ width: d.ib_width ?? null, klass: d.ib_class ?? null }); setAutoDrivers({ opening: d.opening_type, loc: d.open_location, pocdrift: d.poc_drift, dd: d.second_distribution?.detected, vol: d.vol_ratio }); setAutoMeasured(d.measured || null); setAutoStatus(d.n_bars ? '' : 'no bars'); })
      .catch((e) => { if (!cancel) setAutoStatus((e as Error).message.includes('404') ? 'offline — restart backend' : 'offline'); });
    return () => { cancel = true; };
  }, [date]);

  const commit = useCallback((segs: Segment[]) => {
    const next = { ...labels, [date]: { ...(labels[date] || {}), segments: [...segs].sort((a, b) => a.startBar - b.startBar) } };
    setLabels(next); saveLabels(next);
  }, [labels, date]);

  const addSplit = (barIdx: number) => {
    if (barIdx <= 0 || label.segments.some((s) => s.startBar === barIdx)) return;
    const prev = [...label.segments].reverse().find((s) => s.startBar <= barIdx)?.dayType || 'FORMING';
    commit([...label.segments, { startBar: barIdx, dayType: prev }]);
  };
  const removeSplit = (barIdx: number) => { if (barIdx !== 0) commit(label.segments.filter((s) => s.startBar !== barIdx)); };
  const setSegType = (startBar: number, dt: DayTypeName) => commit(label.segments.map((s) => (s.startBar === startBar ? { ...s, dayType: dt } : s)));

  const draw = useCallback(() => {
    const cv = canvasRef.current; if (!cv) return;
    const ctx = cv.getContext('2d'); if (!ctx) return;
    const W = cv.width, H = cv.height;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#0d1117'; ctx.fillRect(0, 0, W, H);
    if (!bars.length) { geom.current = null; return; }
    const x0 = PL, x1 = W - PR, y0 = PT, y1 = H - AX;
    const n = bars.length, bw = (x1 - x0) / n;
    geom.current = { x0, bw, n };
    const lvlVals = [levels.poc, levels.vah, levels.val, levels.ib_high, levels.ib_low, levels.pdh, levels.pdl].filter((v): v is number => v != null);
    const lo = Math.min(...bars.map((b) => b.l), ...lvlVals) - 1;
    const hi = Math.max(...bars.map((b) => b.h), ...lvlVals) + 1;
    const Y = (p: number) => y0 + (hi - p) / (hi - lo) * (y1 - y0);
    const segs = [...label.segments].sort((a, b) => a.startBar - b.startBar);
    const segEnd = (i: number) => (i + 1 < segs.length ? segs[i + 1].startBar : n);

    // segment bands + labels
    segs.forEach((s, i) => {
      const xa = x0 + s.startBar * bw, xb = x0 + segEnd(i) * bw;
      ctx.fillStyle = DT_COLOR[s.dayType] + '22'; ctx.fillRect(xa, y0, xb - xa, y1 - y0);
      ctx.fillStyle = DT_COLOR[s.dayType]; ctx.font = '10px ui-monospace, monospace'; ctx.textAlign = 'left';
      ctx.fillText(s.dayType, xa + 3, y0 - 14);
      ctx.fillStyle = '#6e7681'; ctx.fillText(hhmm(bars[s.startBar].t), xa + 3, y0 - 3);
      if (s.startBar > 0) { ctx.strokeStyle = DT_COLOR[s.dayType]; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(xa, y0); ctx.lineTo(xa, y1); ctx.stroke(); }
    });

    // level lines
    const drawLvl = (v: number | null | undefined, col: string, lab: string) => {
      if (v == null) return; const y = Y(v);
      ctx.strokeStyle = col; ctx.lineWidth = 1; ctx.setLineDash([4, 3]); ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = col; ctx.font = '9px ui-monospace, monospace'; ctx.textAlign = 'left'; ctx.fillText(lab, x1 + 2, y + 3);
    };
    drawLvl(levels.pdh, '#6e7681', 'PDH'); drawLvl(levels.pdl, '#6e7681', 'PDL');
    drawLvl(levels.vah, '#c9d1d9', 'VAH'); drawLvl(levels.val, '#c9d1d9', 'VAL');
    drawLvl(levels.poc, '#d2a8ff', 'POC');
    drawLvl(levels.ib_high, '#e3b341', 'IBH'); drawLvl(levels.ib_low, '#e3b341', 'IBL');

    // candles
    bars.forEach((b, i) => {
      const xc = x0 + (i + 0.5) * bw; const up = b.c >= b.o; const col = up ? '#3fb950' : '#f85149';
      ctx.strokeStyle = col; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(xc, Y(b.h)); ctx.lineTo(xc, Y(b.l)); ctx.stroke();
      const bodyW = Math.max(1, bw * 0.6); ctx.fillStyle = col;
      const yo = Y(b.o), yc = Y(b.c); ctx.fillRect(xc - bodyW / 2, Math.min(yo, yc), bodyW, Math.max(1, Math.abs(yc - yo)));
    });

    // time axis (every ~12 bars = hour)
    ctx.fillStyle = '#6e7681'; ctx.font = '9px ui-monospace, monospace'; ctx.textAlign = 'center';
    for (let i = 0; i < n; i += 12) ctx.fillText(hhmm(bars[i].t), x0 + (i + 0.5) * bw, H - 6);
  }, [bars, levels, label]);

  useEffect(() => { draw(); }, [draw]);

  const onCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const g = geom.current, cv = canvasRef.current; if (!g || !cv) return;
    const rect = cv.getBoundingClientRect();
    const x = (e.clientX - rect.left) * (cv.width / rect.width);
    const idx = Math.round((x - g.x0) / g.bw);
    if (idx > 0 && idx < g.n) addSplit(idx);
  };

  const labeledDates = Object.keys(labels).filter((d) => (labels[d]?.segments?.length || 0) > 0).sort().reverse();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#0d1117', color: '#c9d1d9', fontFamily: 'ui-monospace, monospace', fontSize: 12 }}>
      {/* header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', borderBottom: '1px solid #21262d', flexShrink: 0, flexWrap: 'wrap' }}>
        <strong style={{ color: '#e6edf3' }}>Day-Type Labeler</strong>
        <button onClick={() => setDate(shiftDate(date, -1))} style={btn}>‹ prev</button>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} style={{ ...btn, padding: '3px 6px' }} />
        <button onClick={() => setDate(shiftDate(date, 1))} style={btn}>next ›</button>
        <span style={{ color: '#8b949e' }}>{status}</span>
        {autoIB?.width != null && (
          <span style={{ color: '#e3b341', fontWeight: 600 }}>
            IB {autoIB.width}pt{autoIB.klass && autoIB.klass !== 'UNKNOWN' ? ` · ${autoIB.klass}` : ''}
          </span>
        )}
        <span style={{ marginLeft: 'auto', color: '#6e7681' }}>click the chart to split · {label.segments.length} segment(s)</span>
      </div>
      {/* Live identification table — how the system reads day-type + opening-type right now */}
      <div style={{ padding: '8px 12px 0', maxHeight: 320, overflowY: 'auto', flexShrink: 0 }}>
        <DayTypeConditionsTable />
      </div>
      {/* AUTO — how the algorithm classifies the day, next to your manual label */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px 0' }}>
        <span style={{ width: 116, color: '#6e7681', flexShrink: 0 }}>Algorithm sees:</span>
        {autoSegs.length && autoN ? (
          <div style={{ display: 'flex', flex: 1, height: 16, borderRadius: 3, overflow: 'hidden', border: '1px solid #21262d' }}>
            {autoSegs.map((s, i) => {
              const end = i + 1 < autoSegs.length ? autoSegs[i + 1].startBar : autoN;
              const span = Math.max(1, end - s.startBar);
              const op = s.status === 'CLASSIFIED' ? 'cc' : s.status === 'PROVISIONAL' ? '88' : '44';  // FORMING dimmest
              return (
                <div key={s.startBar} title={`${s.time} · ${s.day_type} (${s.status})${s.reason ? ' — ' + s.reason : ''}`} style={{ flexGrow: span, flexBasis: 0, background: (DT_COLOR[s.day_type] || '#8b949e') + op, borderRight: '1px solid #0d1117', fontSize: 9, color: '#0d1117', textAlign: 'center', lineHeight: '16px', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                  {span > 3 ? s.day_type.replace('Normal_Variation', 'N.Var').replace('Neutral_', 'Neu.') : ''}
                </div>
              );
            })}
          </div>
        ) : <span style={{ flex: 1, color: '#6e7681' }}>{autoStatus || '—'}</span>}
        {autoFinal && <span style={{ color: DT_COLOR[autoFinal.day_type] || '#8b949e', flexShrink: 0 }}>→ {autoFinal.day_type}{autoFinal.opening_invalidated ? ' (oi)' : ''}</span>}
      </div>
      {/* קבע לפי — the inputs that DETERMINED the day-type (the new state-machine classifier).
          Primary signals first (sides/rib/close/one_tf), then context (IB/vol/opening/DD). */}
      {(autoDrivers || autoMeasured) && (
        <div style={{ padding: '3px 12px 0', display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center', fontSize: 10, color: '#8b949e' }}>
          <span style={{ color: '#6e7681' }}>קבע לפי:</span>
          {autoMeasured?.sides != null && <span>sides <b style={{ color: autoMeasured.sides === 2 ? '#58a6ff' : autoMeasured.sides === 1 ? '#56d364' : '#c9d1d9' }}>{autoMeasured.sides}</b></span>}
          {autoMeasured?.rib != null && <span>rib <b style={{ color: '#c9d1d9' }}>{autoMeasured.rib}</b></span>}
          {autoMeasured?.close_pos != null && <span>close <b style={{ color: '#c9d1d9' }}>{autoMeasured.close_pos}</b></span>}
          {autoMeasured?.one_tf && <span>1TF <b style={{ color: '#56d364' }}>{autoMeasured.one_tf}</b></span>}
          {autoIB?.width != null && <span>IB <b style={{ color: '#e3b341' }}>{autoIB.width}</b> {autoIB.klass}</span>}
          {autoDrivers?.vol != null && <span>vol <b style={{ color: autoDrivers.vol <= 0.5 ? '#f85149' : '#c9d1d9' }}>{autoDrivers.vol}×</b></span>}
          {autoDrivers?.opening && <span>open <b style={{ color: '#bc8cff' }}>{String(autoDrivers.opening).replace('OPEN_', '')}</b></span>}
          {autoDrivers?.loc && <span>loc {autoDrivers.loc}</span>}
          <span>DD <b style={{ color: autoDrivers?.dd ? '#3fb950' : '#6e7681' }}>{autoDrivers?.dd ? 'yes' : 'no'}</b></span>
        </div>
      )}
      <div style={{ padding: '0 12px 2px', fontSize: 9, color: '#6e7681' }}>
        מקרא: sides=צדדי-IB שנפרצו עם ווליום≥8% (0/1/2) · rib=טווח÷IB · close=מיקום-סגירה 0–1 · 1TF=one-timeframe · IB=שעה ראשונה (צר=≤0.7×חציון) · vol=ווליום מול חציון (≤0.5×→Nontrend) · open=סוג-פתיחה (5) · DD=דאבל-דיסטריביושן (IB-צר+צוואר-2POC+ערך-מוחזק) · בהיר=PROVISIONAL · עמום=FORMING · (רחף על מקטע ב-"Algorithm sees" לסיבה+status)
      </div>
      {/* chart */}
      <div style={{ padding: 8 }}>
        <canvas ref={canvasRef} width={1180} height={460} onClick={onCanvasClick} style={{ width: '100%', height: 460, cursor: 'crosshair', borderRadius: 4 }} />
      </div>
      {/* segment editor */}
      <div style={{ padding: '4px 12px', display: 'flex', flexDirection: 'column', gap: 4, overflowY: 'auto' }}>
        <div style={{ color: '#8b949e', marginBottom: 2 }}>Segments — set the day-type for each (from its start time):</div>
        {[...label.segments].sort((a, b) => a.startBar - b.startBar).map((s) => (
          <div key={s.startBar} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 60, color: '#6e7681' }}>{bars[s.startBar] ? hhmm(bars[s.startBar].t) : `bar ${s.startBar}`}</span>
            <span style={{ width: 10, height: 10, background: DT_COLOR[s.dayType], borderRadius: 2, display: 'inline-block' }} />
            <select value={s.dayType} onChange={(e) => setSegType(s.startBar, e.target.value as DayTypeName)} style={{ ...btn, minWidth: 150 }}>
              {DAY_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            {s.startBar > 0 && <button onClick={() => removeSplit(s.startBar)} style={{ ...btn, color: '#f85149' }}>× remove split</button>}
          </div>
        ))}
      </div>
      {/* labeled-days footer */}
      <div style={{ marginTop: 'auto', padding: '6px 12px', borderTop: '1px solid #21262d', color: '#6e7681', flexShrink: 0 }}>
        Labeled: {labeledDates.length ? labeledDates.map((d) => <button key={d} onClick={() => setDate(d)} style={{ ...btn, marginRight: 4, color: d === date ? '#e6edf3' : '#8b949e' }}>{d}</button>) : '— none yet'}
      </div>
    </div>
  );
}

const btn: React.CSSProperties = { background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d', borderRadius: 4, padding: '3px 8px', fontSize: 11, fontFamily: 'ui-monospace, monospace', cursor: 'pointer' };
