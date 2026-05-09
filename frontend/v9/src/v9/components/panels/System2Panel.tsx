'use client';
import { SystemPanelWrapper } from './SystemPanelWrapper';
import { useSystemStore } from '../../stores/systemStore';

export function System2Panel() {
  const signals = useSystemStore((s) => s.signals.filter((sg) => sg.system_id === 2));
  const recent = signals.slice(-3).reverse();

  return (
    <SystemPanelWrapper systemId={2}>
      <div className="space-y-0.5 mt-1">
        {recent.map((s) => (
          <div key={s.id} className="flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
            <span className="text-[10px] opacity-50">
              {new Date(s.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
            <span>{s.signal_type}</span>
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
