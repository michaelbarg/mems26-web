'use client';
import { useSystemStateStore } from '../../store/systemStateStore';
import { COLORS } from '../../design/tokens';
import { systemColor } from '../../design/system_colors';

export function WoodiesLensContent({ activeTab }: { activeTab: string }) {
  const state = useSystemStateStore((s) => s.systems[4]);
  const color = systemColor(4);

  if (activeTab === 'Now') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color }}>Woodies CCI(14)</div>
        <div style={{ fontSize: 9, color: COLORS.textSecondary }}>
          Signal: {state?.state || '—'} | Dir: {state?.subState || 'none'}
        </div>
        <div style={{ fontSize: 9, color: COLORS.textTertiary }}>
          Strength: {Math.round((state?.confidence || 0) * 3)}/3
        </div>
        <div style={{ fontSize: 8, color: COLORS.textDim }}>FIRING — STANDALONE (no Day Type input)</div>
      </div>
    );
  }
  if (activeTab === 'Plan') {
    const { WoodiesPlan } = require('../sidepanel/lens/plan/WoodiesPlan');
    return <WoodiesPlan />;
  }

  return (
    <div style={{ fontSize: 9, color: COLORS.textTertiary, textAlign: 'center', padding: 8 }}>
      {activeTab} — coming in later prompts
    </div>
  );
}
