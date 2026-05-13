'use client';
import { useSystemStateStore } from '../../store/systemStateStore';
import { COLORS } from '../../design/tokens';
import { systemColor } from '../../design/system_colors';

export function FootprintLensContent({ activeTab }: { activeTab: string }) {
  const state = useSystemStateStore((s) => s.systems[3]);
  const color = systemColor(3);

  if (activeTab === 'Now') {
    const raw = (state as any)?.raw || {};
    const af = raw.aggressive_flow || {};
    const deltaVal = raw.delta;
    const deltaColor = deltaVal != null ? (deltaVal >= 0 ? COLORS.bull : COLORS.bear) : COLORS.textTertiary;
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color }}>Footprint (Observer)</div>
        <div style={{ fontSize: 9, color: COLORS.textSecondary }}>
          Classification: {state?.state || '—'} | Confluence: {Math.round((state?.confidence || 0) * 10)}
        </div>
        <div style={{ fontSize: 9, color: COLORS.textTertiary }}>
          Flow ({raw.forces_source ?? '—'}):
        </div>
        <div style={{ fontSize: 8, fontFamily: 'ui-monospace', color: COLORS.textSecondary, paddingLeft: 8 }}>
          AGG Buy: {af.agg_buy_vol?.toFixed(0) ?? '—'} | Sell: {af.agg_sell_vol?.toFixed(0) ?? '—'}
        </div>
        <div style={{ fontSize: 8, fontFamily: 'ui-monospace', color: COLORS.textDim, paddingLeft: 8 }}>
          PAS: N/A (L2 not available)
        </div>
        <div style={{ fontSize: 9, color: COLORS.textTertiary }}>
          Delta: <span style={{ color: deltaColor, fontFamily: 'ui-monospace' }}>{deltaVal?.toFixed(0) ?? '—'}</span> | CumDelta: {raw.cumulative_delta?.toFixed(0) ?? '—'}
        </div>
        <div style={{ fontSize: 9, color: COLORS.textTertiary }}>
          Dominance: {raw.dominance ?? '—'} | AMT: {raw.amt?.toFixed(2) ?? '—'}
        </div>
        <div style={{ fontSize: 8, color: COLORS.textDim }}>STANDALONE observer — no trade decisions</div>
      </div>
    );
  }
  return (
    <div style={{ fontSize: 9, color: COLORS.textTertiary, textAlign: 'center', padding: 8 }}>
      {activeTab} — coming in later prompts
    </div>
  );
}
