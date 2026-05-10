'use client';
import { useMemo } from 'react';
import { useSystemStore } from '../../../stores/systemStore';
import { SYSTEM_COLORS, type SystemId } from '../../../types';

export function PatternsTab() {
  const signals = useSystemStore((s) => s.signals);

  const patternData = useMemo(() => {
    // Patterns come from System 2 (5-min) and System 4 (Woodies)
    const patternSystems: SystemId[] = [2, 4];
    const patternSignals = signals.filter(
      (s) => patternSystems.includes(s.system_id as SystemId) && s.classification
    );

    const active = patternSignals.filter(
      (s) => s.payload?.pattern_status === 'building' || s.payload?.pattern_status === 'active'
    );

    const bySystem = patternSystems.map((sysId) => {
      const sysPatterns = patternSignals.filter((s) => s.system_id === sysId);
      return { sysId, patterns: sysPatterns };
    });

    return { active, bySystem, total: patternSignals.length };
  }, [signals]);

  return (
    <div className="flex flex-col gap-3 text-xs">
      {/* Active Patterns */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Active Patterns
        </div>
        {patternData.active.length === 0 ? (
          <div style={{ color: 'var(--text-muted)' }}>No active patterns</div>
        ) : (
          patternData.active.map((p) => (
            <div key={p.id} className="py-0.5" style={{ color: 'var(--text-secondary)' }}>
              <span style={{ color: SYSTEM_COLORS[p.system_id as SystemId] }}>S{p.system_id}</span>
              {' '}{p.classification}
            </div>
          ))
        )}
      </div>

      {/* Pattern History by System */}
      {patternData.bySystem.map(({ sysId, patterns }) => (
        <div key={sysId} className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
          <div className="font-bold mb-1" style={{ color: SYSTEM_COLORS[sysId] }}>
            S{sysId} Patterns ({patterns.length})
          </div>
          {patterns.length === 0 ? (
            <div style={{ color: 'var(--text-muted)' }}>None today</div>
          ) : (
            patterns.slice(-5).map((p) => (
              <div key={p.id} className="py-0.5 flex justify-between" style={{ color: 'var(--text-secondary)' }}>
                <span>{p.classification}</span>
                <span style={{ color: 'var(--text-muted)' }}>
                  {new Date(p.ts).toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            ))
          )}
        </div>
      ))}

      <div className="p-2 rounded text-center" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-muted)' }}>
        Total patterns today: {patternData.total}
      </div>
    </div>
  );
}
