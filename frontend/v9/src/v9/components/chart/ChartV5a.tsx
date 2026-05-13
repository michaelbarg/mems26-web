'use client';
import { useEffect, useState, useMemo, useRef } from 'react';
import { usePriceStore } from '../../stores/priceStore';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Bar { ts: string; o: number; h: number; l: number; c: number; v: number }
interface TpoState { poc: number | null; vah: number | null; val: number | null; ib_high: number | null; ib_low: number | null; hydrated: boolean }
interface TpoSession { poc_price: number | null; vah_price: number | null; val_price: number | null }
interface KzState { current_zone: { name: string; edge_class: string; minutes_remaining: number } }
interface FireState { sys2_firing: boolean; sys4_firing: boolean; sys1_firing: boolean }

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

  // Fetch bars
  useEffect(() => {
    const f = () => fetch(`${API}/api/v9/chart/bars5min?limit=60`).then(r => r.json()).then(d => { if (Array.isArray(d)) setBars(d); }).catch(() => {});
    f(); const id = setInterval(f, 30000); return () => clearInterval(id);
  }, []);

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

  // Fetch Killzone
  useEffect(() => {
    const f = () => fetch(`${API}/api/v9/killzone/current`).then(r => r.json()).then(setKz).catch(() => {});
    f(); const id = setInterval(f, 30000); return () => clearInterval(id);
  }, []);

  // All bars = closed + forming
  const allBars = useMemo(() => {
    const result = [...bars];
    if (formingBar) result.push(formingBar);
    return result;
  }, [bars, formingBar]);

  // Price range from all bars
  const { pMin, pMax } = useMemo(() => {
    if (allBars.length === 0) {
      const p = price ?? 7400;
      return { pMin: p - 10, pMax: p + 10 };
    }
    let lo = Infinity, hi = -Infinity;
    for (const b of allBars) { if (b.l < lo) lo = b.l; if (b.h > hi) hi = b.h; }
    if (price != null) { if (price < lo) lo = price; if (price > hi) hi = price; }
    return { pMin: lo - 1, pMax: hi + 1 };
  }, [allBars, price]);

  const yOf = (p: number) => MT + (1 - (p - pMin) / (pMax - pMin)) * CH;
  const barW = allBars.length > 0 ? Math.min(14, CW / allBars.length - 1) : 12;
  const maxVol = Math.max(1, ...allBars.map(b => b.v || 1));

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: '100%', minHeight: 310, background: '#0a0a0a' }}>
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
        const candleOpacity = (isForming && fireColor) ? 0.85 : (isForming ? 0.95 : 0.85);
        return (
          <g key={i}>
            <line x1={x} y1={yOf(b.h)} x2={x} y2={yOf(b.l)} stroke={candleColor} strokeWidth={0.5} />
            <rect x={x - barW / 2} y={bodyTop} width={barW} height={bodyH}
              fill={candleColor} opacity={candleOpacity} rx={0.5}
              stroke={isForming ? '#facc15' : 'none'} strokeWidth={isForming ? 0.5 : 0} />
          </g>
        );
      })}

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

      {/* TPO Stepped POC (5 periods, fading) */}
      {(() => {
        const pocPrices = tpoSessions
          .map(s => s.poc_price)
          .filter((p): p is number => p != null);
        // If no sessions but current TPO has POC, use that as period 0
        if (pocPrices.length === 0 && tpo?.poc != null) pocPrices.push(tpo.poc);
        if (pocPrices.length === 0) return null;
        // Pad to align: last = period 0 (current)
        const offset = POC_STEPS.length - pocPrices.length;
        return pocPrices.map((poc, i) => {
          const step = POC_STEPS[offset + i];
          if (!step) return null;
          return <line key={`poc-${i}`} x1={ML} y1={yOf(poc)} x2={W - MR} y2={yOf(poc)}
            stroke="#ec4899" strokeWidth={step.width} opacity={step.opacity} />;
        });
      })()}

      {/* POC transition verticals (dashed magenta) */}
      {(() => {
        const pocPrices = tpoSessions
          .map(s => s.poc_price)
          .filter((p): p is number => p != null);
        if (pocPrices.length < 2) return null;
        return pocPrices.slice(1).map((poc, i) => {
          const prev = pocPrices[i];
          if (prev === poc) return null;
          // Place transition at roughly the session boundary
          const x = ML + ((i + 1) / pocPrices.length) * CW;
          return <line key={`poct-${i}`} x1={x} y1={yOf(prev)} x2={x} y2={yOf(poc)}
            stroke="#ec4899" strokeWidth={0.6} opacity={0.35} strokeDasharray="2 2" />;
        });
      })()}

      {/* VAH/VAL lines */}
      {tpo?.vah != null && <line x1={ML} y1={yOf(tpo.vah)} x2={W - MR} y2={yOf(tpo.vah)} stroke="#ec4899" strokeWidth={0.5} opacity={0.55} strokeDasharray="3 3" />}
      {tpo?.val != null && <line x1={ML} y1={yOf(tpo.val)} x2={W - MR} y2={yOf(tpo.val)} stroke="#ec4899" strokeWidth={0.5} opacity={0.55} strokeDasharray="3 3" />}

      {/* Current price line */}
      {price != null && <line x1={ML} y1={yOf(price)} x2={W - MR} y2={yOf(price)} stroke="#facc15" strokeWidth={0.4} opacity={0.4} />}

      {/* IB H/L */}
      {tpo?.ib_high != null && <line x1={ML} y1={yOf(tpo.ib_high)} x2={W - MR} y2={yOf(tpo.ib_high)} stroke="#4ade80" strokeWidth={0.8} opacity={0.5} />}
      {tpo?.ib_low != null && <line x1={ML} y1={yOf(tpo.ib_low)} x2={W - MR} y2={yOf(tpo.ib_low)} stroke="#4ade80" strokeWidth={0.8} opacity={0.5} />}

      {/* TR countdown badge */}
      {kz?.current_zone && (
        <g>
          <rect x={12} y={6} width={90} height={16} rx={3} fill="rgba(249,115,22,0.12)" stroke="#f97316" strokeWidth={0.5} />
          <text x={16} y={17} fontSize={10} fill="#f97316" fontFamily="ui-monospace, monospace" fontWeight={500}>
            {kz.current_zone.name} · {kz.current_zone.minutes_remaining}m
          </text>
        </g>
      )}

      {/* Right price scale — PRC pill (live, flashing) */}
      {price != null && (() => {
        const y = yOf(price);
        if (y < MT || y > H - MB) return null;
        return (
          <g>
            <rect x={W - MR + 2} y={y - 7} width={56} height={14} rx={2} fill="#facc15" opacity={prcFlash ? 0.6 : 1} />
            <text x={W - MR + 5} y={y + 3} fontSize={9} fill="#0a0a0a" fontFamily="ui-monospace, monospace" fontWeight={600}>
              PRC {price.toFixed(2)}
            </text>
          </g>
        );
      })()}

      {/* Right price scale — other labels */}
      {[
        { price: tpo?.ib_high, label: 'IB H', fill: 'rgba(6,78,59,0.30)', text: '#4ade80' },
        { price: tpo?.vah, label: 'VAH', fill: 'rgba(236,72,153,0.15)', text: '#ec4899' },
        { price: tpo?.poc, label: 'POC', fill: '#ec4899', text: '#fff' },
        { price: tpo?.val, label: 'VAL', fill: 'rgba(236,72,153,0.15)', text: '#ec4899' },
        { price: tpo?.ib_low, label: 'IB L', fill: 'rgba(6,78,59,0.30)', text: '#4ade80' },
      ].map(l => {
        if (l.price == null) return null;
        const y = yOf(l.price);
        if (y < MT || y > H - MB) return null;
        return (
          <g key={l.label}>
            <rect x={W - MR + 2} y={y - 7} width={56} height={14} rx={2} fill={l.fill} opacity={0.8} />
            <text x={W - MR + 5} y={y + 3} fontSize={9} fill={l.text} fontFamily="ui-monospace, monospace" fontWeight={500}>
              {l.label} {l.price.toFixed(2)}
            </text>
          </g>
        );
      })}

      {/* No bars message */}
      {allBars.length === 0 && (
        <text x={W / 2} y={H / 2} textAnchor="middle" fontSize={12} fill="#737373">No bars yet</text>
      )}
    </svg>
  );
}
