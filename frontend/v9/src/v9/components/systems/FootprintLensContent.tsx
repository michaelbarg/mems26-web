'use client';
import { useSystemStateStore } from '../../store/systemStateStore';
import { COLORS } from '../../design/tokens';
import { systemColor } from '../../design/system_colors';

export function FootprintLensContent({ activeTab }: { activeTab: string }) {
  const state = useSystemStateStore((s) => s.systems[3]);
  const color = systemColor(3);

  if (activeTab === 'Now') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color }}>Footprint (Observer)</div>
        <div style={{ fontSize: 9, color: COLORS.textSecondary }}>
          Classification: {state?.state || '—'}
        </div>
        <div style={{ fontSize: 9, color: COLORS.textTertiary }}>
          Pattern: {state?.subState || 'none'} | Confluence: {Math.round((state?.confidence || 0) * 10)}
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
