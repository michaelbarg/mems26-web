'use client';
import { SystemPanelWrapper } from './SystemPanelWrapper';
import { useSystemStore } from '../../stores/systemStore';

export function System3Panel() {
  const signals = useSystemStore((s) => s.signals.filter((sg) => sg.system_id === 3));
  const latest = signals[signals.length - 1];

  return (
    <SystemPanelWrapper systemId={3}>
      {latest && (
        <div className="space-y-1 mt-1" style={{ color: 'var(--text-secondary)' }}>
          <div>
            <span className="opacity-60">Imbalance: </span>
            <span>{(latest.metadata_json?.imbalance_count as string) || '\u2014'}</span>
          </div>
          <div>
            <span className="opacity-60">Stacked: </span>
            <span>{(latest.metadata_json?.stacked_count as string) || '\u2014'}</span>
          </div>
          <div>
            <span className="opacity-60">Delta: </span>
            <span style={{
              color: (latest.metadata_json?.delta as number) >= 0 ? 'var(--green)' : 'var(--red)',
            }}>
              {(latest.metadata_json?.delta as string) || '\u2014'}
            </span>
          </div>
        </div>
      )}
    </SystemPanelWrapper>
  );
}
