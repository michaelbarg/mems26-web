'use client';
import { useMemo } from 'react';
import { SystemPanelWrapper } from './SystemPanelWrapper';
import { useSystemStore } from '../../stores/systemStore';

export function System2Panel() {
  const allSignals = useSystemStore((s) => s.signals);
  const recent = useMemo(
    () => allSignals.filter((sg) => sg.system_id === 2).slice(-3).reverse(),
    [allSignals],
  );

  return (
    <SystemPanelWrapper systemId={2}>
      <div className="space-y-0.5 mt-1">
        {recent.map((s) => (
          <div key={s.id} className="flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
            <span className="text-[10px] opacity-50">
              {new Date(s.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
            <span>{s.classification}</span>
            {s.direction && (
              <span style={{ color: s.direction === 'LONG' ? 'var(--green)' : 'var(--red)' }}>
                {s.direction}
              </span>
            )}
          </div>
        ))}
        {recent.length === 0 && (
          <div style={{ color: 'var(--text-muted)' }}>No patterns detected</div>
        )}
      </div>
    </SystemPanelWrapper>
  );
}
