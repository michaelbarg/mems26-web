'use client';
import { useSystemStateStore } from '../../store/systemStateStore';
import { COLORS } from '../../design/tokens';
import { systemColor } from '../../design/system_colors';

export function TPOLensContent({ activeTab }: { activeTab: string }) {
  const state = useSystemStateStore((s) => s.systems[5]);
  const color = systemColor(5);

  if (activeTab === 'Now') {
    const raw = (state as any)?.raw || {};
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color }}>TPO Profile</div>
        <div style={{ fontSize: 9, color: COLORS.textSecondary }}>
          Shape: {state?.state || '—'} | Letters: {raw.letter_count ?? 0}
        </div>
        <div style={{ fontSize: 9, color: COLORS.textTertiary }}>
          POC: {raw.poc?.toFixed(2) ?? '—'} | VAH: {raw.vah?.toFixed(2) ?? '—'} | VAL: {raw.val?.toFixed(2) ?? '—'}
        </div>
        <div style={{ fontSize: 9, color: COLORS.textTertiary }}>
          IB: {raw.ib_high?.toFixed(2) ?? '—'} / {raw.ib_low?.toFixed(2) ?? '—'}
          {raw.ib_locked ? ` (LOCKED · ${raw.ib_class ?? '—'} · ${raw.ib_width?.toFixed(1) ?? '—'}pt)` : ''}
        </div>
        <div style={{ fontSize: 8, color: COLORS.textDim }}>OBSERVER — publishes POC/VAH/VAL to Day Type</div>
      </div>
    );
  }
  return (
    <div style={{ fontSize: 9, color: COLORS.textTertiary, textAlign: 'center', padding: 8 }}>
      {activeTab} — coming in later prompts
    </div>
  );
}
