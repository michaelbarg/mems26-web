'use client';
import { useMemo } from 'react';
import { SystemPanelWrapper } from './SystemPanelWrapper';
import { useSystemStore } from '../../stores/systemStore';

export function System3Panel() {
  const allSignals = useSystemStore((s) => s.signals);
  const signals = useMemo(() => allSignals.filter((sg) => sg.system_id === 3), [allSignals]);
  const latest = signals[signals.length - 1];

  return (
    <SystemPanelWrapper systemId={3}>
      {latest && (
        <div className="space-y-1 mt-1" style={{ color: 'var(--text-secondary)' }}>
          <div>
            <span className="opacity-60">Imbalance: </span>
            <span>{(latest.payload?.imbalance_count as string) || '\u2014'}</span>
          </div>
          <div>
            <span className="opacity-60">Stacked: </span>
            <span>{(latest.payload?.stacked_count as string) || '\u2014'}</span>
          </div>
          <div>
            <span className="opacity-60">Delta: </span>
            <span style={{
              color: (latest.payload?.delta as number) >= 0 ? 'var(--green)' : 'var(--red)',
            }}>
              {(latest.payload?.delta as string) || '\u2014'}
            </span>
          </div>
        </div>
      )}
    </SystemPanelWrapper>
  );
}
