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

  useEffect(() => {
    const poll = async () => {
      try {
        // Try chop_score endpoint (built by W2 P-LAYER0 — may not exist yet)
        const resp = await fetch(`${API}/api/v9/chop_score/current`).catch(() => null);
        if (resp && resp.ok) {
          const d = await resp.json();
          setChop({
            vegas_flips_60m: d.vegas_flips_60m ?? null,
            cci_zl_crossings_30m: d.cci_zl_crossings_30m ?? null,
            poc_migration_stuck: d.poc_migration_stuck ?? null,
            ib_breakouts_recent: d.ib_breakouts_recent ?? null,
            range_atr_ratio: d.range_atr_ratio ?? null,
            poc_vwap_distance: d.poc_vwap_distance ?? null,
          });
          setNews(d.news_window ?? null);
        }
      } catch { /* silent — endpoint may not exist yet */ }
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

      {/* News window */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <span style={{ fontSize: 9, color: news === 'upcoming' ? '#f59e0b' : news === 'recent' ? '#dc2626' : '#525252', fontFamily: 'ui-monospace' }}>
          News {news === 'upcoming' ? '\u25B2' : news === 'recent' ? '\u25BC' : '\u2014'}
        </span>
      </div>
    </div>
  );
}
