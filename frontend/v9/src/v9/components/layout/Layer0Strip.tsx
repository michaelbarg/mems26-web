'use client';
import { useEffect, useState } from 'react';
import { COLORS, SIZES } from '../../design/tokens';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ChopScore {
  vegas_flips_60m: number | null;
  cci_zl_crossings_30m: number | null;
  poc_migration_stuck: boolean | null;
  ib_breakouts_recent: number | null;
  range_atr_ratio: number | null;
  poc_vwap_distance: number | null;
}

function Chip({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <span style={{
      fontSize: 9, fontWeight: 500, padding: '1px 6px', borderRadius: 3,
      background: 'rgba(255,255,255,0.04)', color,
    }}>
      {label} <b>{value}</b>
    </span>
  );
}

export function Layer0Strip() {
  const [chop, setChop] = useState<ChopScore>({
    vegas_flips_60m: null, cci_zl_crossings_30m: null, poc_migration_stuck: null,
    ib_breakouts_recent: null, range_atr_ratio: null, poc_vwap_distance: null,
  });
  const [news, setNews] = useState<string | null>(null);
  const [chopScore, setChopScore] = useState<number | null>(null);
  const [chopState, setChopState] = useState<string | null>(null);
  const [sufferingSide, setSufferingSide] = useState<string | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const resp = await fetch(`${API}/api/v9/layer0/state`).catch(() => null);
        if (resp && resp.ok) {
          const d = await resp.json();
          const ind = d.indicators || d;
          setChop({
            vegas_flips_60m: ind.vegas_flips_60m ?? null,
            cci_zl_crossings_30m: ind.cci_zl_crossings_30m ?? null,
            poc_migration_stuck: ind.poc_migration_stuck ?? null,
            ib_breakouts_recent: ind.ib_breakouts_recent ?? null,
            range_atr_ratio: ind.range_atr_ratio ?? null,
            poc_vwap_distance: ind.poc_vwap_distance ?? null,
          });
          setChopScore(d.chop_score ?? null);
          setChopState(d.state ?? null);
          setNews(d.news_window ?? null);
        }
      } catch { /* silent */ }
      // Suffering Side from veto endpoint
      try {
        const vr = await fetch(`${API}/api/v9/veto/state`).catch(() => null);
        if (vr && vr.ok) {
          const v = await vr.json();
          setSufferingSide(v.suffering_side ?? null);
        }
      } catch { /* silent */ }
    };
    poll();
    const id = setInterval(poll, 5000);
    return () => clearInterval(id);
  }, []);

  const fmt = (v: number | null, dec = 0) => v != null ? v.toFixed(dec) : '\u2014';
  const boolFmt = (v: boolean | null) => v == null ? '\u2014' : v ? 'YES' : 'no';

  return (
    <div
      id="layer0-strip"
      style={{
        height: SIZES.layer0Height,
        background: COLORS.bgSurface2,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingLeft: 12,
        paddingRight: 12,
        gap: 8,
        borderBottom: `1px solid ${COLORS.borderFaint}`,
        flexShrink: 0,
      }}
    >
      {/* 6 Chop Score indicators per Constitution V3 Layer 0 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <Chip label="VF" value={fmt(chop.vegas_flips_60m)} color="#f97316" />
        <Chip label="ZLx" value={fmt(chop.cci_zl_crossings_30m)} color="#06b6d4" />
        <Chip label="POC" value={boolFmt(chop.poc_migration_stuck)} color="#ec4899" />
        <Chip label="IBx" value={fmt(chop.ib_breakouts_recent)} color="#4ade80" />
        <Chip label="R/A" value={fmt(chop.range_atr_ratio, 2)} color="#a78bfa" />
        <Chip label="P-V" value={fmt(chop.poc_vwap_distance, 1)} color="#facc15" />
      </div>

      {/* κ.6: Chop Score + State pill + κ.7: Suffering Side + News */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        {/* Chop state pill */}
        {chopState && (() => {
          const stateColors: Record<string, string> = {
            SEARCHING: '#dc2626', RESPECTING: '#16a34a', EXPANDING: '#3b82f6', FOUND: '#f59e0b',
          };
          const isFound = chopState === 'FOUND';
          return (
            <span style={{
              fontSize: 8, fontWeight: 700, padding: '1px 6px', borderRadius: 3,
              background: stateColors[chopState] || '#525252',
              color: isFound ? '#0a0a0a' : '#ffffff',
            }}>
              {chopScore != null ? `${chopScore.toFixed(0)} ` : ''}{chopState}
            </span>
          );
        })()}
        {/* Suffering Side pill */}
        {sufferingSide && sufferingSide !== 'NONE' && (
          <span style={{
            fontSize: 8, fontWeight: 600, padding: '1px 5px', borderRadius: 3,
            background: 'rgba(168,85,247,0.15)', color: '#a855f7',
          }}>
            SS {sufferingSide}
          </span>
        )}
        {/* News window */}
        <span style={{ fontSize: 9, color: news === 'upcoming' ? '#f59e0b' : news === 'recent' ? '#dc2626' : '#525252', fontFamily: 'ui-monospace' }}>
          News {news === 'upcoming' ? '\u25B2' : news === 'recent' ? '\u25BC' : '\u2014'}
        </span>
      </div>
    </div>
  );
}
