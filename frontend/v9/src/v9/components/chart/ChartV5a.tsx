'use client';
import { useEffect, useState, useMemo, useRef, useCallback } from 'react';
import { usePriceStore } from '../../stores/priceStore';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Bar { ts: string; o: number; h: number; l: number; c: number; v: number }
interface TpoState { poc: number | null; vah: number | null; val: number | null; ib_high: number | null; ib_low: number | null; hydrated: boolean }
interface TpoSession {
  poc_price: number | null; vah_price: number | null; val_price: number | null;
  opened_ts: string | null; closed_ts: string | null;
}
interface KzState { current_zone: { name: string; edge_class: string; minutes_remaining: number } }
interface ActiveTrade { stop_price: number | null; entry_price: number | null; direction: string | null }
interface FireState { sys2_firing: boolean; sys4_firing: boolean; sys1_firing: boolean }
interface FpState { last_classification: string; hydrated: boolean }
interface ObserverMarkers { fp_classified: boolean; tpo_active: boolean; kz_transition: boolean }

const FIRE_COLORS: Record<string, string> = {
  sys2: '#06b6d4', // cyan — 5-Min
  sys4: '#f97316', // orange — Woodies
  sys1: '#6366f1', // indigo — Day Type
};

const POC_STEPS = [
  { width: 1.0, opacity: 0.28 },  // period -4 (oldest)
  { width: 1.0, opacity: 0.40 },  // period -3
  { width: 1.1, opacity: 0.52 },  // period -2
  { width: 1.3, opacity: 0.65 },  // period -1
  { width: 1.9, opacity: 0.95 },  // period 0 (current)
];

// VAH/VAL historical per Spec V1 §4.5: 0.4px dashed, opacity 0.22-0.40 → 0.55 current
const VA_STEPS = [
  { width: 0.4, opacity: 0.22 },  // period -4
  { width: 0.4, opacity: 0.28 },  // period -3
  { width: 0.4, opacity: 0.34 },  // period -2
  { width: 0.4, opacity: 0.40 },  // period -1
  { width: 0.5, opacity: 0.55 },  // period 0 (current)
];


/** Parse bar or session timestamp to epoch ms (handles both formats). */
function toEpoch(ts: string): number {
  // Bar ts: "2026-05-12 11:20:00.000000" — replace space with T for ISO parse
  // Session ts: "2026-05-13T11:35:00-04:00" — already ISO
  return new Date(ts.replace(' ', 'T')).getTime();
}

/** Map session time range to bar-index X coords (PA1.5-1: fixed 3 bugs). */
function sessionXRange(s: TpoSession, bars: {ts:string}[], ml: number, cw: number): [number,number]|null {
  if (!bars.length) return null;
  const openMs = s.opened_ts ? toEpoch(s.opened_ts) : toEpoch(bars[0].ts);
  // null closed_ts = current session → extend to last bar
  const closeMs = s.closed_ts ? toEpoch(s.closed_ts) : toEpoch(bars[bars.length - 1].ts);
  let fi = 0, li = bars.length - 1;
  for (let i = 0; i < bars.length; i++) { if (toEpoch(bars[i].ts) >= openMs) { fi = i; break; } }
  for (let i = bars.length - 1; i >= 0; i--) { if (toEpoch(bars[i].ts) <= closeMs) { li = i; break; } }
  if (fi > li) return null;
  return [ml + (fi / bars.length) * cw, ml + ((li + 1) / bars.length) * cw];
}

function renderSteppedPOC(sessions: TpoSession[], bars: {ts:string}[], fallback: number|null,
  ml: number, mr: number, w: number, cw: number, yOf: (p:number)=>number) {
  const sorted = [...sessions].sort((a, b) => toEpoch(a.opened_ts || '0') - toEpoch(b.opened_ts || '0'));
  const l5 = sorted.slice(-5);
  if (!l5.length && fallback != null)
    return [<line key="poc-fb" x1={ml} y1={yOf(fallback)} x2={w-mr} y2={yOf(fallback)} stroke="#ec4899" strokeWidth={1.9} opacity={0.95}/>];
  const off = POC_STEPS.length - l5.length;
  const out: React.ReactNode[] = [];
  l5.forEach((s,i) => {
    if (s.poc_price == null) return;
    const st = POC_STEPS[off+i]; if (!st) return;
    const r = sessionXRange(s,bars,ml,cw); if (!r) return;
    out.push(<line key={`poc-${i}`} x1={r[0]} y1={yOf(s.poc_price)} x2={r[1]} y2={yOf(s.poc_price)} stroke="#ec4899" strokeWidth={st.width} opacity={st.opacity}/>);
    if (i < l5.length-1) {
      const nx = l5[i+1];
      if (nx.poc_price != null && nx.poc_price !== s.poc_price) {
        const age = (l5.length-1-i)/4;
        out.push(<line key={`poct-${i}`} x1={r[1]} y1={yOf(s.poc_price)} x2={r[1]} y2={yOf(nx.poc_price)} stroke="#ec4899" strokeWidth={0.6+age*0.3} opacity={0.75-age*0.45} strokeDasharray="2 2"/>);
      }
    }
  });
  return out;
}

function renderSteppedVAH(sessions: TpoSession[], bars: {ts:string}[], fallback: number|null,
  ml: number, mr: number, w: number, cw: number, yOf: (p:number)=>number) {
  const sorted = [...sessions].sort((a, b) => toEpoch(a.opened_ts || '0') - toEpoch(b.opened_ts || '0'));
  const l5 = sorted.slice(-5);
  if (!l5.length && fallback != null)
    return [<line key="vah-fb" x1={ml} y1={yOf(fallback)} x2={w-mr} y2={yOf(fallback)} stroke="#ec4899" strokeWidth={0.5} opacity={0.55} strokeDasharray="3 3"/>];
  const off = VA_STEPS.length - l5.length;
  return l5.map((s,i) => {
    if (s.vah_price == null) return null;
    const st = VA_STEPS[off+i]; if (!st) return null;
    const r = sessionXRange(s,bars,ml,cw); if (!r) return null;
    return <line key={`vah-${i}`} x1={r[0]} y1={yOf(s.vah_price)} x2={r[1]} y2={yOf(s.vah_price)} stroke="#ec4899" strokeWidth={st.width} opacity={st.opacity} strokeDasharray="3 3"/>;
  }).filter(Boolean);
}

function renderSteppedVAL(sessions: TpoSession[], bars: {ts:string}[], fallback: number|null,
  ml: number, mr: number, w: number, cw: number, yOf: (p:number)=>number) {
  const sorted = [...sessions].sort((a, b) => toEpoch(a.opened_ts || '0') - toEpoch(b.opened_ts || '0'));
  const l5 = sorted.slice(-5);
  if (!l5.length && fallback != null)
    return [<line key="val-fb" x1={ml} y1={yOf(fallback)} x2={w-mr} y2={yOf(fallback)} stroke="#ec4899" strokeWidth={0.5} opacity={0.55} strokeDasharray="3 3"/>];
  const off = VA_STEPS.length - l5.length;
  return l5.map((s,i) => {
    if (s.val_price == null) return null;
    const st = VA_STEPS[off+i]; if (!st) return null;
    const r = sessionXRange(s,bars,ml,cw); if (!r) return null;
    return <line key={`val-${i}`} x1={r[0]} y1={yOf(s.val_price)} x2={r[1]} y2={yOf(s.val_price)} stroke="#ec4899" strokeWidth={st.width} opacity={st.opacity} strokeDasharray="3 3"/>;
  }).filter(Boolean);
}

const W = 800, H = 310;  // +30 for volume strip
const ML = 8, MR = 62, MT = 28, MB = 32;  // MB includes volume strip
const CW = W - ML - MR, CH = H - MT - MB;
const VOL_H = 28;
const VOL_Y = H - MB + 2;  // Volume strip starts here

export function ChartV5a() {
  const [bars, setBars] = useState<Bar[]>([]);
  const [tpo, setTpo] = useState<TpoState | null>(null);
  const [kz, setKz] = useState<KzState | null>(null);
  const price = usePriceStore((s) => s.price);
  const direction = usePriceStore((s) => s.direction);
  const tickCount = usePriceStore((s) => s.tickCount);

  // PRC flash state
  const [prcFlash, setPrcFlash] = useState(false);
  const prevTickRef = useRef(tickCount);
  useEffect(() => {
    if (tickCount !== prevTickRef.current && price != null) {
      prevTickRef.current = tickCount;
      setPrcFlash(true);
      const t = setTimeout(() => setPrcFlash(false), 200);
      return () => clearTimeout(t);
    }
  }, [tickCount, price]);

  // Forming bar state
  const [formingBar, setFormingBar] = useState<Bar | null>(null);
  useEffect(() => {
    if (price == null) return;
    setFormingBar(prev => {
      // Floor to 5-min boundary
      const now = new Date();
      const min5 = Math.floor(now.getMinutes() / 5) * 5;
      const slotTs = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')} ${String(now.getHours()).padStart(2,'0')}:${String(min5).padStart(2,'0')}:00`;
      if (!prev || prev.ts !== slotTs) {
        return { ts: slotTs, o: price, h: price, l: price, c: price, v: 1 };
      }
      return {
        ...prev,
        h: Math.max(prev.h, price),
        l: Math.min(prev.l, price),
        c: price,
        v: prev.v + 1,
      };
    });
  }, [price, tickCount]);

  // Fetch bars (PA1-1: 60 candles on mount + 5s refresh per Cockpit V5 §3.4)
  // Wave A1.5: 5s poll merges new bars on the right without clobbering pan-loaded history
  useEffect(() => {
    const fetchBars = () => fetch(`${API}/api/v9/chart/bars5min?limit=60`)
      .then(r => r.json())
      .then(d => {
        if (!Array.isArray(d)) return;
        setBars(prev => {
          if (prev.length === 0) return d;
          // Merge: keep older pan-loaded bars, append any new ones from poll
          const existing = new Set(prev.map(b => b.ts));
          const fresh = d.filter((b: Bar) => !existing.has(b.ts));
          return fresh.length > 0 ? [...prev, ...fresh] : prev;
        });
      })
      .catch(() => {});
    fetchBars();
    const id = setInterval(fetchBars, 5000);
    return () => clearInterval(id);
  }, []);

  // Wave A1.5: Pan-to-load older bars
  const [isLoadingOlder, setIsLoadingOlder] = useState(false);
  const [hasMoreHistory, setHasMoreHistory] = useState(true);

  const fetchOlderBars = useCallback(async () => {
    if (isLoadingOlder || !hasMoreHistory || bars.length === 0) return;
    const oldestTs = bars[0].ts;
    setIsLoadingOlder(true);
    try {
      const resp = await fetch(`${API}/api/v9/chart/bars5min?before=${encodeURIComponent(oldestTs)}&limit=60`);
      const data = await resp.json();
      const newBars: Bar[] = Array.isArray(data) ? data : [];
      if (newBars.length === 0) {
        setHasMoreHistory(false);
        return;
      }
      const existing = new Set(bars.map(b => b.ts));
      const deduped = newBars.filter(b => !existing.has(b.ts));
      if (deduped.length > 0) {
        setBars(prev => [...deduped, ...prev]);
      }
      if (newBars.length < 60) setHasMoreHistory(false);
    } catch { /* silent */ } finally {
      setIsLoadingOlder(false);
    }
  }, [isLoadingOlder, hasMoreHistory, bars]);

  // Fetch TPO
  useEffect(() => {
    const f = () => fetch(`${API}/api/v9/tpo/current`).then(r => r.json()).then(setTpo).catch(() => {});
    f(); const id = setInterval(f, 2000); return () => clearInterval(id);
  }, []);

  // Fetch TPO sessions (for stepped POC)
  const [tpoSessions, setTpoSessions] = useState<TpoSession[]>([]);
  useEffect(() => {
    const f = () => fetch(`${API}/api/v9/tpo/sessions`).then(r => r.json()).then(d => {
      const sessions = Array.isArray(d) ? d : d?.sessions || [];
      setTpoSessions(sessions.slice(-5));
    }).catch(() => {});
    f(); const id = setInterval(f, 30000); return () => clearInterval(id);
  }, []);

  // Fetch firing system states (for candle coloring)
  const [fires, setFires] = useState<FireState>({ sys2_firing: false, sys4_firing: false, sys1_firing: false });
  useEffect(() => {
    const f = async () => {
      try {
        const [woodRes, dtRes] = await Promise.allSettled([
          fetch(`${API}/api/v9/woodies/signals`).then(r => r.json()),
          fetch(`${API}/api/v9/day_type/state`).then(r => r.json()),
        ]);
        const wood = woodRes.status === 'fulfilled' ? woodRes.value : null;
        const dt = dtRes.status === 'fulfilled' ? dtRes.value : null;
        // Woodies: sys4 fires on ZLR/TLB signals
        const woodEntries = wood?.entries || [];
        const sys4 = woodEntries.length > 0 && ['ZLR', 'TLB', 'GB100', 'GHOST_BAR'].includes(woodEntries[woodEntries.length - 1]?.signal_type);
        // Day Type: sys1 fires when confidence > 0.7 and stage >= B2
        const dtState = dt?.state || {};
        const sys1 = dtState.confidence > 0.7 && dtState.stage && dtState.stage >= 'B2';
        setFires({ sys2_firing: false, sys4_firing: sys4, sys1_firing: sys1 });
      } catch { /* silent */ }
    };
    f(); const id = setInterval(f, 5000); return () => clearInterval(id);
  }, []);

  // Determine candle color for the forming bar
  const fireColor = useMemo(() => {
    if (fires.sys2_firing) return FIRE_COLORS.sys2;
    if (fires.sys4_firing) return FIRE_COLORS.sys4;
    if (fires.sys1_firing) return FIRE_COLORS.sys1;
    return null;
  }, [fires]);

  // Fetch Footprint observer state
  const [fpState, setFpState] = useState<FpState | null>(null);
  useEffect(() => {
    const f = () => fetch(`${API}/api/v9/footprint/current`).then(r => r.json()).then(setFpState).catch(() => {});
    f(); const id = setInterval(f, 5000); return () => clearInterval(id);
  }, []);

  // Observer markers derived state
  const observers = useMemo<ObserverMarkers>(() => ({
    fp_classified: fpState?.last_classification != null && fpState.last_classification !== 'NO_SETUP',
    tpo_active: (tpo?.hydrated ?? false) && (tpo?.poc != null),
    kz_transition: kz?.current_zone != null,
  }), [fpState, tpo, kz]);

  // Fetch Killzone
  useEffect(() => {
    const f = () => fetch(`${API}/api/v9/killzone/current`).then(r => r.json()).then(setKz).catch(() => {});
    f(); const id = setInterval(f, 30000); return () => clearInterval(id);
  }, []);

  // PG2-2: Active trade state (for stop line + STP pill)
  const [activeTrade, setActiveTrade] = useState<ActiveTrade | null>(null);
  useEffect(() => {
    const f = () => fetch(`${API}/api/v9/gateway/status`)
      .then(r => r.json())
      .then(d => {
        if (d.shadow_active_count > 0 || d.demo_slot || d.live_slot) {
          setActiveTrade({
            stop_price: d.shadow_stop ?? d.demo_stop ?? d.live_stop ?? null,
            entry_price: d.shadow_entry ?? d.demo_entry ?? d.live_entry ?? null,
            direction: d.shadow_direction ?? d.demo_direction ?? d.live_direction ?? null,
          });
        } else {
          setActiveTrade(null);
        }
      })
      .catch(() => {});
    f(); const id = setInterval(f, 2000); return () => clearInterval(id);
  }, []);

  // All bars = closed + forming
  const allBars = useMemo(() => {
    const result = [...bars];
    if (formingBar) result.push(formingBar);
    return result;
  }, [bars, formingBar]);

  // Price range from all bars (PA1-6: 5% padding for breathing room)
  const { pMin, pMax } = useMemo(() => {
    if (allBars.length === 0) {
      const p = price ?? 7400;
      return { pMin: p - 10, pMax: p + 10 };
    }
    let lo = Infinity, hi = -Infinity;
    for (const b of allBars) { if (b.l < lo) lo = b.l; if (b.h > hi) hi = b.h; }
    if (price != null) { if (price < lo) lo = price; if (price > hi) hi = price; }
    const range = hi - lo || 1;
    return { pMin: lo - range * 0.05, pMax: hi + range * 0.05 };
  }, [allBars, price]);

  const yOf = (p: number) => MT + (1 - (p - pMin) / (pMax - pMin)) * CH;
  const barW = allBars.length > 0 ? Math.min(14, CW / allBars.length - 1) : 12;
  const maxVol = Math.max(1, ...allBars.map(b => b.v || 1));

  // Pan/Zoom state (PA1-5)
  const [zoomLevel, setZoomLevel] = useState(1.0);
  const [panOffsetX, setPanOffsetX] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStartX, setDragStartX] = useState(0);
  const [panAtDragStart, setPanAtDragStart] = useState(0);

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.95 : 1.05;
    setZoomLevel(prev => Math.max(0.5, Math.min(5.0, prev * delta)));
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStartX(e.clientX);
    setPanAtDragStart(panOffsetX);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    const dx = e.clientX - dragStartX;
    const newPan = panAtDragStart + dx / zoomLevel;
    setPanOffsetX(newPan);
    // Wave A1.5: pan-to-load — when user drags right past the oldest bar, fetch more
    const chartContentWidth = allBars.length * (barW + 1) * zoomLevel;
    if (newPan > chartContentWidth - CW * 0.8 && hasMoreHistory && !isLoadingOlder) {
      fetchOlderBars();
    }
  };

  const handleMouseUp = () => setIsDragging(false);

  return (
    <svg viewBox={`0 0 ${W} ${H}`}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      style={{ width: '100%', height: '100%', minHeight: 310, background: '#0a0a0a', cursor: isDragging ? 'grabbing' : 'grab' }}>
      {/* Group 1: Zoomable/pannable chart content (PA1-5) */}
      <g transform={`translate(${panOffsetX}, 0) scale(${zoomLevel}, 1)`}>
      {/* Grid */}
      {[0.25, 0.5, 0.75].map(f => (
        <line key={f} x1={ML} y1={MT + f * CH} x2={W - MR} y2={MT + f * CH} stroke="#1a1a1a" strokeWidth={0.5} />
      ))}

      {/* 5-min candles + forming bar */}
      {allBars.map((b, i) => {
        const x = ML + (i / allBars.length) * CW + barW / 2;
        const bull = b.c >= b.o;
        const bodyTop = yOf(bull ? b.c : b.o);
        const bodyBot = yOf(bull ? b.o : b.c);
        const bodyH = Math.max(1, bodyBot - bodyTop);
        const isForming = i === allBars.length - 1 && formingBar != null;
        // System-colored candles: fire color on forming bar, normal on closed
        const candleColor = (isForming && fireColor) ? fireColor : (bull ? '#16a34a' : '#dc2626');
        const candleOpacity = (isForming && fireColor) ? 0.95 : (isForming ? 0.95 : 0.85);
        return (
          <g key={i}>
            <line x1={x} y1={yOf(b.h)} x2={x} y2={yOf(b.l)} stroke={candleColor} strokeWidth={0.5} />
            <rect x={x - barW / 2} y={bodyTop} width={barW} height={bodyH}
              fill={candleColor} opacity={candleOpacity} rx={0.5}
              stroke={isForming ? '#facc15' : 'none'} strokeWidth={isForming ? 0.5 : 0} />
          </g>
        );
      })}

      {/* Observer markers on last bar */}
      {allBars.length > 0 && (() => {
        const lastIdx = allBars.length - 1;
        const lastBar = allBars[lastIdx];
        const x = ML + (lastIdx / allBars.length) * CW + barW / 2;
        return (
          <g>
            {/* System 3 (Footprint): purple triangle above wick */}
            {observers.fp_classified && (
              <polygon points={`${x},${yOf(lastBar.h) - 6} ${x - 3},${yOf(lastBar.h) - 2} ${x + 3},${yOf(lastBar.h) - 2}`}
                fill="#a855f7" opacity={0.7} />
            )}
            {/* System 5 (TPO): yellow dot below wick */}
            {observers.tpo_active && (
              <circle cx={x} cy={yOf(lastBar.l) + 5} r={2} fill="#facc15" opacity={0.6} />
            )}
            {/* System 6 (Killzone): teal underline on time axis */}
            {observers.kz_transition && (
              <line x1={x - barW / 2} y1={H - MB + 1} x2={x + barW / 2} y2={H - MB + 1}
                stroke="#2dd4bf" strokeWidth={2} opacity={0.5} />
            )}
          </g>
        );
      })()}

      {/* Volume strip background */}
      <rect x={ML} y={VOL_Y} width={CW} height={VOL_H} fill="#0d0d0d" />
      <line x1={ML} y1={VOL_Y} x2={W - MR} y2={VOL_Y} stroke="#1a1a1a" strokeWidth={0.5} />

      {/* Volume bars */}
      {allBars.map((b, i) => {
        const x = ML + (i / allBars.length) * CW + barW / 2;
        const vol = b.v || 0;
        const volH = Math.max(1, (vol / maxVol) * (VOL_H - 2));
        const bull = b.c >= b.o;
        return (
          <rect key={`v${i}`} x={x - barW / 2} y={VOL_Y + VOL_H - volH} width={barW} height={volH}
            fill={bull ? '#16a34a' : '#dc2626'} opacity={0.6} rx={0.5} />
        );
      })}

      {/* TPO Stepped POC (5 periods, time-scoped) */}
      {renderSteppedPOC(tpoSessions, allBars, tpo?.poc ?? null, ML, MR, W, CW, yOf)}

      {/* TPO Stepped VAH (time-scoped, dashed) */}
      {renderSteppedVAH(tpoSessions, allBars, tpo?.vah ?? null, ML, MR, W, CW, yOf)}

            {/* TPO Stepped VAL (time-scoped, dashed) */}
      {renderSteppedVAL(tpoSessions, allBars, tpo?.val ?? null, ML, MR, W, CW, yOf)}

      {/* Current price line (PG2-2: upgraded to Spec §4.5 — 1px solid, 0.85 opacity) */}
      {price != null && <line x1={ML} y1={yOf(price)} x2={W - MR} y2={yOf(price)} stroke="#facc15" strokeWidth={1} opacity={0.85} />}

      {/* Stop line (PG2-2: red dashed, only when active trade) */}
      {activeTrade?.stop_price != null && (
        <line x1={ML} y1={yOf(activeTrade.stop_price)} x2={W - MR} y2={yOf(activeTrade.stop_price)}
          stroke="#dc2626" strokeWidth={1} opacity={0.9} strokeDasharray="6 4" />
      )}

      {/* IB H/L */}
      {tpo?.ib_high != null && <line x1={ML} y1={yOf(tpo.ib_high)} x2={W - MR} y2={yOf(tpo.ib_high)} stroke="#4ade80" strokeWidth={0.8} opacity={0.5} />}
      {tpo?.ib_low != null && <line x1={ML} y1={yOf(tpo.ib_low)} x2={W - MR} y2={yOf(tpo.ib_low)} stroke="#4ade80" strokeWidth={0.8} opacity={0.5} />}

      </g>{/* End Group 1: zoomable/pannable */}

      {/* Group 2: Anchored to edges (badges + right-scale pills) */}
      {/* TR countdown badge */}
      {kz?.current_zone && (
        <g>
          <rect x={12} y={6} width={90} height={16} rx={3} fill="rgba(249,115,22,0.12)" stroke="#f97316" strokeWidth={0.5} />
          <text x={16} y={17} fontSize={10} fill="#f97316" fontFamily="ui-monospace, monospace" fontWeight={500}>
            {kz.current_zone.name} · {kz.current_zone.minutes_remaining}m
          </text>
        </g>
      )}

      {/* Right price scale — 7 pills with collision resolver (PA1-4) */}
      {(() => {
        // Build all 7 pills: IB H, VAH, PRC, POC, STP, VAL, IB L
        const pocY = tpo?.poc != null ? yOf(tpo.poc) : null;
        const valY = tpo?.val != null ? yOf(tpo.val) : null;
        // STP pill: use active trade stop_price if available, else midpoint placeholder
        const stopPrice = activeTrade?.stop_price ?? null;
        const stpY = stopPrice != null ? yOf(stopPrice) : (pocY != null && valY != null ? (pocY + valY) / 2 : (pocY ?? H / 2) + 14);

        const rawPills = [
          { label: 'IB H', y: tpo?.ib_high != null ? yOf(tpo.ib_high) : null, priceVal: tpo?.ib_high, fill: 'rgba(74,222,128,0.15)', text: '#4ade80', fontWeight: 500 },
          { label: 'VAH',  y: tpo?.vah != null ? yOf(tpo.vah) : null,         priceVal: tpo?.vah,     fill: 'rgba(236,72,153,0.15)', text: '#ec4899', fontWeight: 500 },
          { label: 'PRC',  y: price != null ? yOf(price) : null,              priceVal: price ?? null, fill: '#facc15', text: '#0a0a0a', fontWeight: 600 },
          { label: 'POC',  y: tpo?.poc != null ? yOf(tpo.poc) : null,         priceVal: tpo?.poc,     fill: '#ec4899', text: '#fff',    fontWeight: 500 },
          { label: 'STP',  y: stpY,                                           priceVal: stopPrice,    fill: 'rgba(220,38,38,0.15)', text: '#dc2626', fontWeight: 500 },
          { label: 'VAL',  y: tpo?.val != null ? yOf(tpo.val) : null,         priceVal: tpo?.val,     fill: 'rgba(236,72,153,0.15)', text: '#ec4899', fontWeight: 500 },
          { label: 'IB L', y: tpo?.ib_low != null ? yOf(tpo.ib_low) : null,   priceVal: tpo?.ib_low,  fill: 'rgba(74,222,128,0.15)', text: '#4ade80', fontWeight: 500 },
        ];

        // Filter to visible pills
        const visible = rawPills.filter(p => p.y != null && p.y >= MT && p.y <= H - MB) as
          (typeof rawPills[number] & { y: number })[];

        // Collision resolver: sort by Y, push down when overlap (PA1-4)
        const minSpacing = 15;
        const sorted = [...visible].sort((a, b) => a.y - b.y);
        const resolved: { y: number; yOriginal: number; label: string; priceVal: number | null | undefined; fill: string; text: string; fontWeight: number }[] = [];
        let lastY = -Infinity;
        for (const pill of sorted) {
          const yAdj = Math.max(pill.y, lastY + minSpacing);
          resolved.push({ ...pill, yOriginal: pill.y, y: yAdj });
          lastY = yAdj;
        }

        return resolved.map(p => (
          <g key={p.label}>
            {/* Connector line when pill shifted from true price */}
            {Math.abs(p.y - p.yOriginal) > 1 && (
              <line x1={W - MR + 1} y1={p.yOriginal} x2={W - MR + 1} y2={p.y}
                stroke={p.text} strokeWidth={0.5} opacity={0.3} />
            )}
            <rect x={W - MR + 2} y={p.y - 7} width={56} height={14} rx={2}
              fill={p.fill} opacity={p.label === 'PRC' ? (prcFlash ? 0.6 : 1) : 0.8} />
            <text x={W - MR + 5} y={p.y + 3} fontSize={9} fill={p.text}
              fontFamily="ui-monospace, monospace" fontWeight={p.fontWeight}>
              {p.label} {p.priceVal != null ? p.priceVal.toFixed(2) : '—'}
            </text>
          </g>
        ));
      })()}

      {/* PA1-6: Right price axis labels (5pt MES intervals) */}
      {(() => {
        const step = 5;
        const startP = Math.ceil(pMin / step) * step;
        const labels: React.ReactNode[] = [];
        for (let p = startP; p <= pMax; p += step) {
          const y = yOf(p);
          if (y < MT + 6 || y > H - MB - 4) continue;
          labels.push(
            <g key={`py-${p}`}>
              <line x1={ML} y1={y} x2={W - MR} y2={y} stroke="#1a1a1a" strokeWidth={0.3} />
              <text x={W - MR + 4} y={y + 3} fontSize={8} fill="#525252"
                fontFamily="ui-monospace, monospace">{p.toFixed(0)}</text>
            </g>
          );
        }
        return labels;
      })()}

      {/* PA1-6 + PA3-2: Bottom time axis labels (sorted + deduped + ET timezone) */}
      {(() => {
        if (allBars.length < 2) return null;
        const labelEvery = allBars.length <= 15 ? 3 : allBars.length <= 30 ? 6 : 12;
        const etFmt = new Intl.DateTimeFormat('en-US', {
          timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', hour12: false,
        });
        // Build tick candidates sorted by index (bars already time-ordered)
        const ticks: { i: number; ms: number; label: string }[] = [];
        for (let i = 0; i < allBars.length; i++) {
          if (i % labelEvery !== 0) continue;
          const ms = toEpoch(allBars[i].ts);
          const label = etFmt.format(ms);
          ticks.push({ i, ms, label });
        }
        // Sort by timestamp (guard against out-of-order bars)
        ticks.sort((a, b) => a.ms - b.ms);
        // Dedup: skip if same label as previous (within 60s)
        const deduped = ticks.filter((t, idx) =>
          idx === 0 || t.label !== ticks[idx - 1].label
        );
        return deduped.map(t => {
          const x = ML + (t.i / allBars.length) * CW + barW / 2;
          return (
            <text key={`tx-${t.i}`} x={x} y={H - 2} fontSize={8} fill="#525252"
              textAnchor="middle" fontFamily="ui-monospace, monospace">{t.label}</text>
          );
        });
      })()}

      {/* No bars message */}
      {allBars.length === 0 && (
        <text x={W / 2} y={H / 2} textAnchor="middle" fontSize={12} fill="#737373">No bars yet</text>
      )}
    </svg>
  );
}
