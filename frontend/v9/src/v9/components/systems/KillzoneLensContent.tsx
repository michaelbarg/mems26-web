'use client';
import { useSystemStateStore } from '../../store/systemStateStore';
import { COLORS } from '../../design/tokens';
import { systemColor } from '../../design/system_colors';
import { KeyLevelsCard } from './KeyLevelsCard';
import { ShadowTab, HistTab } from '../sidepanel/lens/trades/TradesTab';

export function KillzoneLensContent({ activeTab }: { activeTab: string }) {
  const state = useSystemStateStore((s) => s.systems[6]);
  const color = systemColor(6);
  const raw = (state as any)?.raw || {};
  const cz = raw.current_zone || {};
  const nz = raw.next_zone || {};

  if (activeTab === 'Now') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color }}>Killzone</div>
        <div style={{ fontSize: 11, color: COLORS.textPrimary }}>
          {cz.name || state?.state || '—'} <span style={{ fontSize: 9, color: COLORS.textTertiary }}>({cz.edge_class || '—'})</span>
        </div>
        <div style={{ fontSize: 9, color: COLORS.textSecondary }}>
          Remaining: {cz.minutes_remaining ?? '—'} min
        </div>
        <div style={{ fontSize: 9, color: COLORS.textTertiary }}>
          Next: {nz.name || '—'} in {nz.starts_in_minutes ?? '—'} min
        </div>
        <div style={{ fontSize: 8, color: COLORS.textDim }}>OBSERVER — session quality gate for other systems</div>
        <KeyLevelsCard />
      </div>
    );
  }
  if (activeTab === 'Plan') {
    const { KillzonePlan } = require('../sidepanel/lens/plan/KillzonePlan');
    return <KillzonePlan />;
  }

  if (activeTab === 'Shadow') {
    return <ShadowTab />;
  }
  if (activeTab === 'Hist') {
    return <HistTab />;
  }

  return (
    <div style={{ fontSize: 9, color: COLORS.textTertiary, textAlign: 'center', padding: 8 }}>
      {activeTab} — coming in later prompts
    </div>
  );
}
