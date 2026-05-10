'use client';
import { useMemo } from 'react';
import { SystemPanelWrapper } from './SystemPanelWrapper';
import { useSystemStore } from '../../stores/systemStore';

export function System1Panel() {
  const allSignals = useSystemStore((s) => s.signals);
  const signals = useMemo(() => allSignals.filter((sg) => sg.system_id === 1), [allSignals]);
  const latest = signals[signals.length - 1];

  return (
    <SystemPanelWrapper systemId={1}>
      {latest && (
        <div className="space-y-1 mt-1">
          <div style={{ color: 'var(--text-secondary)' }}>
            <span className="opacity-60">Type: </span>
            <span>{(latest.payload?.day_type as string) || '\u2014'}</span>
          </div>
          <div style={{ color: 'var(--text-secondary)' }}>
            <span className="opacity-60">IB Range: </span>
            <span>{(latest.payload?.ib_range as string) || '\u2014'}</span>
          </div>
          <div style={{ color: 'var(--text-secondary)' }}>
            <span className="opacity-60">Mode: </span>
            <span>{(latest.payload?.mode as string) || '\u2014'}</span>
          </div>
        </div>
      )}
    </SystemPanelWrapper>
  );
}
