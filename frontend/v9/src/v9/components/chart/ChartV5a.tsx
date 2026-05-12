'use client';
import { useEffect, useState, useMemo } from 'react';
import { usePriceStore } from '../../stores/priceStore';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Bar { ts: string; o: number; h: number; l: number; c: number; v: number }
interface TpoState { poc: number | null; vah: number | null; val: number | null; ib_high: number | null; ib_low: number | null; hydrated: boolean }
interface KzState { current_zone: { name: string; edge_class: string; minutes_remaining: number } }

const W = 800, H = 280;
const ML = 8, MR = 62, MT = 28, MB = 4;
const CW = W - ML - MR, CH = H - MT - MB;

export function ChartV5a() {
  const [bars, setBars] = useState<Bar[]>([]);
  const [tpo, setTpo] = useState<TpoState | null>(null);
  const [kz, setKz] = useState<KzState | null>(null);
  const price = usePriceStore((s) => s.price);

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

  // Fetch Killzone
  useEffect(() => {
    const f = () => fetch(`${API}/api/v9/killzone/current`).then(r => r.json()).then(setKz).catch(() => {});
    f(); const id = setInterval(f, 30000); return () => clearInterval(id);
  }, []);

  // Price range from bars
  const { pMin, pMax } = useMemo(() => {
    if (bars.length === 0) {
      const p = price ?? 7400;
      return { pMin: p - 10, pMax: p + 10 };
    }
    let lo = Infinity, hi = -Infinity;
    for (const b of bars) { if (b.l < lo) lo = b.l; if (b.h > hi) hi = b.h; }
    return { pMin: lo - 1, pMax: hi + 1 };
  }, [bars, price]);

  const yOf = (p: number) => MT + (1 - (p - pMin) / (pMax - pMin)) * CH;
  const barW = bars.length > 0 ? Math.min(14, CW / bars.length - 1) : 12;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: '100%', minHeight: 280, background: '#0a0a0a' }}>
      {/* Grid */}
      {[0.25, 0.5, 0.75].map(f => (
        <line key={f} x1={ML} y1={MT + f * CH} x2={W - MR} y2={MT + f * CH} stroke="#1a1a1a" strokeWidth={0.5} />
      ))}

      {/* 5-min candles */}
      {bars.map((b, i) => {
        const x = ML + (i / bars.length) * CW + barW / 2;
        const bull = b.c >= b.o;
        const bodyTop = yOf(bull ? b.c : b.o);
        const bodyBot = yOf(bull ? b.o : b.c);
        const bodyH = Math.max(1, bodyBot - bodyTop);
        return (
          <g key={i}>
            <line x1={x} y1={yOf(b.h)} x2={x} y2={yOf(b.l)} stroke={bull ? '#16a34a' : '#dc2626'} strokeWidth={0.5} />
            <rect x={x - barW / 2} y={bodyTop} width={barW} height={bodyH} fill={bull ? '#16a34a' : '#dc2626'} opacity={0.85} rx={0.5} />
          </g>
        );
      })}

      {/* TPO POC line */}
      {tpo?.poc != null && (
        <line x1={ML} y1={yOf(tpo.poc)} x2={W - MR} y2={yOf(tpo.poc)} stroke="#ec4899" strokeWidth={1.8} opacity={0.95} />
      )}
      {/* TPO VAH dashed */}
      {tpo?.vah != null && (
        <line x1={ML} y1={yOf(tpo.vah)} x2={W - MR} y2={yOf(tpo.vah)} stroke="#ec4899" strokeWidth={0.5} opacity={0.55} strokeDasharray="3 3" />
      )}
      {/* TPO VAL dashed */}
      {tpo?.val != null && (
        <line x1={ML} y1={yOf(tpo.val)} x2={W - MR} y2={yOf(tpo.val)} stroke="#ec4899" strokeWidth={0.5} opacity={0.55} strokeDasharray="3 3" />
      )}

      {/* Current price line */}
      {price != null && (
        <line x1={ML} y1={yOf(price)} x2={W - MR} y2={yOf(price)} stroke="#facc15" strokeWidth={0.4} opacity={0.4} />
      )}

      {/* IB H/L placeholders */}
      {tpo?.ib_high != null && (
        <line x1={ML} y1={yOf(tpo.ib_high)} x2={W - MR} y2={yOf(tpo.ib_high)} stroke="#4ade80" strokeWidth={0.7} opacity={0.5} />
      )}
      {tpo?.ib_low != null && (
        <line x1={ML} y1={yOf(tpo.ib_low)} x2={W - MR} y2={yOf(tpo.ib_low)} stroke="#4ade80" strokeWidth={0.7} opacity={0.5} />
      )}

      {/* TR countdown badge (top-left) */}
      {kz?.current_zone && (
        <g>
          <rect x={12} y={6} width={90} height={16} rx={3} fill="rgba(249,115,22,0.12)" stroke="#f97316" strokeWidth={0.5} />
          <text x={16} y={17} fontSize={10} fill="#f97316" fontFamily="ui-monospace, monospace" fontWeight={500}>
            {kz.current_zone.name} · {kz.current_zone.minutes_remaining}m
          </text>
        </g>
      )}

      {/* Right price scale */}
      {(() => {
        const labels: { price: number | null; label: string; fill: string; text: string; solid?: boolean }[] = [
          { price: tpo?.ib_high ?? null, label: 'IB H', fill: 'rgba(74,222,128,0.15)', text: '#4ade80' },
          { price: tpo?.vah ?? null, label: 'VAH', fill: 'rgba(236,72,153,0.15)', text: '#ec4899' },
          { price: price ?? null, label: 'PRC', fill: '#facc15', text: '#0a0a0a', solid: true },
          { price: tpo?.poc ?? null, label: 'POC', fill: '#ec4899', text: '#fff', solid: true },
          { price: tpo?.val ?? null, label: 'VAL', fill: 'rgba(236,72,153,0.15)', text: '#ec4899' },
          { price: tpo?.ib_low ?? null, label: 'IB L', fill: 'rgba(74,222,128,0.15)', text: '#4ade80' },
        ];
        return labels.map((l, i) => {
          if (l.price == null) return null;
          const y = yOf(l.price);
          if (y < MT || y > H - MB) return null;
          return (
            <g key={l.label}>
              <rect x={W - MR + 2} y={y - 7} width={56} height={14} rx={2} fill={l.fill} opacity={l.solid ? 1 : 0.8} />
              <text x={W - MR + 5} y={y + 3} fontSize={9} fill={l.text} fontFamily="ui-monospace, monospace" fontWeight={500}>
                {l.label} {l.price.toFixed(2)}
              </text>
            </g>
          );
        });
      })()}

      {/* No bars message */}
      {bars.length === 0 && (
        <text x={W / 2} y={H / 2} textAnchor="middle" fontSize={12} fill="#737373">No bars yet</text>
      )}
    </svg>
  );
}
