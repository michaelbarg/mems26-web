'use client';
import { useSystemStateStore } from '../../store/systemStateStore';
import { COLORS } from '../../design/tokens';
import { systemColor } from '../../design/system_colors';

export function WoodiesLensContent({ activeTab }: { activeTab: string }) {
  const state = useSystemStateStore((s) => s.systems[4]);
  const color = systemColor(4);

  if (activeTab === 'Now') {
    const raw = (state?.raw ?? {}) as Record<string, unknown>;
    const dt = (raw.decision_tree ?? {}) as Record<string, unknown>;
    const failed = (dt.failed_stages ?? raw.failed_stages) as string[] | undefined;
    const pending = (dt.pending_stages ?? raw.pending_stages) as string[] | undefined;
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color }}>Woodies CCI(14)</div>
        <div style={{ fontSize: 9, color: COLORS.textSecondary }}>
          Signal: {state?.state || '—'} | Dir: {state?.subState || 'none'}
        </div>
        <div style={{ fontSize: 9, color: COLORS.textTertiary }}>
          Strength: {Math.round((state?.confidence || 0) * 3)}/3
          {raw.ready_to_route ? ' · READY' : ''}
        </div>
        {(failed?.length ?? 0) > 0 && (
          <div style={{ fontSize: 8, color: COLORS.bear }}>Blocked: {failed!.join(', ')}</div>
        )}
        {(pending?.length ?? 0) > 0 && (
          <div style={{ fontSize: 8, color: COLORS.warning }}>Pending: {pending!.join(', ')}</div>
        )}
        <div style={{ fontSize: 8, color: COLORS.textDim }}>
          {String(raw.classification ?? 'NO_SETUP')} · buffer {String(raw.buffer_size ?? 0)}
        </div>
        <div style={{ fontSize: 8, color: COLORS.textDim }}>FIRING — Plan tab shows A1–A7 tree</div>
      </div>
    );
  }
  if (activeTab === 'Plan') {
    const { WoodiesPlan } = require('../sidepanel/lens/plan/WoodiesPlan');
    return <WoodiesPlan />;
  }
  if (activeTab === 'Chart') {
    return (
      <div style={{ fontSize: 9, color: COLORS.textTertiary, padding: 4 }}>
        CCI panel on 5m chart (bottom-left). Data: Sierra woodies_5min.json via /api/v9/woodies/chart.
      </div>
    );
  }

  return (
    <div style={{ fontSize: 9, color: COLORS.textTertiary, textAlign: 'center', padding: 8 }}>
      {activeTab} — coming in later prompts
    </div>
  );
}
