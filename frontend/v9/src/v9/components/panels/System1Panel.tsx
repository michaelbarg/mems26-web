'use client';
import { SystemPanelWrapper } from './SystemPanelWrapper';
import { useSystemStore } from '../../stores/systemStore';

export function System1Panel() {
  const signals = useSystemStore((s) => s.signals.filter((sg) => sg.system_id === 1));
  const latest = signals[signals.length - 1];

  return (
    <SystemPanelWrapper systemId={1}>
      {latest && (
        <div className="space-y-1 mt-1">
          <div style={{ color: 'var(--text-secondary)' }}>
            <span className="opacity-60">Type: </span>
            <span>{(latest.metadata_json?.day_type as string) || '\u2014'}</span>
          </div>
          <div style={{ color: 'var(--text-secondary)' }}>
            <span className="opacity-60">IB Range: </span>
            <span>{(latest.metadata_json?.ib_range as string) || '\u2014'}</span>
          </div>
          <div style={{ color: 'var(--text-secondary)' }}>
            <span className="opacity-60">Mode: </span>
            <span>{latest.mode}</span>
          </div>
        </div>
      )}
    </SystemPanelWrapper>
  );
}
