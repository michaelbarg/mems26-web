'use client';
import { useMemo } from 'react';
import { useSystemStore } from '../../../stores/systemStore';
import { SYSTEM_COLORS, SYSTEM_NAMES, SYSTEM_ROLES, type SystemId } from '../../../types';

const ALL_SYSTEMS: SystemId[] = [1, 2, 3, 4, 5, 6];

export function SystemsTab() {
  const activeSignals = useSystemStore((s) => s.activeSignals);
  const signals = useSystemStore((s) => s.signals);

  const systemData = useMemo(() => {
    return ALL_SYSTEMS.map((sysId) => {
      const active = activeSignals[sysId];
      const sysSignals = signals.filter((s) => s.system_id === sysId);
      return {
        sysId,
        name: SYSTEM_NAMES[sysId],
        role: SYSTEM_ROLES[sysId],
        color: SYSTEM_COLORS[sysId],
        active,
        signalCount: sysSignals.length,
        classification: active?.classification ?? '--',
        confidence: active?.confidence ?? null,
        direction: active?.direction ?? null,
      };
    });
  }, [activeSignals, signals]);

  return (
    <div className="flex flex-col gap-2 text-xs">
      {/* System Grid — 2 columns */}
      <div className="grid grid-cols-2 gap-2">
        {systemData.map((sys) => (
          <div
            key={sys.sysId}
            className="p-2 rounded"
            style={{
              background: 'var(--bg-tertiary)',
              borderLeft: `3px solid ${sys.color}`,
            }}
          >
            <div className="flex items-center justify-between mb-0.5">
              <span className="font-bold" style={{ color: sys.color, fontSize: 10 }}>
                S{sys.sysId}
              </span>
              <span
                className="px-1 rounded"
                style={{
                  fontSize: 9,
                  background: sys.role === 'firing' ? '#56d36420' : sys.role === 'gate' ? '#f8514920' : '#58a6ff20',
                  color: sys.role === 'firing' ? 'var(--green)' : sys.role === 'gate' ? 'var(--red)' : '#58a6ff',
                }}
              >
                {sys.role}
              </span>
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: 10 }}>
              {sys.name}
            </div>
            <div className="mt-1" style={{ color: 'var(--text-primary)' }}>
              {sys.classification}
            </div>
            {sys.confidence !== null && (
              <div style={{ color: 'var(--text-muted)', fontSize: 10 }}>
                {(sys.confidence * 100).toFixed(0)}%
              </div>
            )}
            {sys.direction && (
              <div style={{
                color: sys.direction === 'LONG' ? 'var(--green)' : sys.direction === 'SHORT' ? 'var(--red)' : 'var(--text-muted)',
                fontSize: 10,
              }}>
                {sys.direction}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Consensus
        </div>
        <div style={{ color: 'var(--text-secondary)' }}>
          {(() => {
            const firing = systemData.filter((s) => s.role === 'firing' && s.direction);
            const longs = firing.filter((s) => s.direction === 'LONG').length;
            const shorts = firing.filter((s) => s.direction === 'SHORT').length;
            if (longs > shorts) return `LONG bias (${longs}/${firing.length} firing)`;
            if (shorts > longs) return `SHORT bias (${shorts}/${firing.length} firing)`;
            if (firing.length === 0) return 'No active signals';
            return 'Mixed / Neutral';
          })()}
        </div>
      </div>
    </div>
  );
}
