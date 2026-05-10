'use client';
import { useLayoutStore } from '../../stores/layoutStore';
import { useSystemStore } from '../../stores/systemStore';
import { SYSTEM_COLORS, SYSTEM_NAMES, SYSTEM_ROLES } from '../../types';
import type { SystemId } from '../../types';

interface Props {
  systemId: SystemId;
  children: React.ReactNode;
}

export function SystemPanelWrapper({ systemId, children }: Props) {
  const { openSettings } = useLayoutStore();
  const activeSignal = useSystemStore((s) => s.activeSignals[systemId]);
  const color = SYSTEM_COLORS[systemId];
  const name = SYSTEM_NAMES[systemId];
  const role = SYSTEM_ROLES[systemId];

  return (
    <div
      className="flex-1 min-w-[160px] border-r flex flex-col"
      style={{ borderColor: 'var(--border)' }}
    >
      <div
        className="flex items-center justify-between px-2 py-1 border-b cursor-pointer"
        style={{ borderColor: 'var(--border)' }}
        onClick={() => openSettings(systemId)}
      >
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full" style={{ background: color }} />
          <span className="text-[11px] font-medium" style={{ color }}>S{systemId}</span>
          <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>{name}</span>
        </div>
        <span
          className="text-[9px] px-1 rounded"
          style={{ background: 'var(--bg-tertiary)', color: 'var(--text-muted)' }}
        >
          {role}
        </span>
      </div>
      <div className="flex-1 p-2 overflow-y-auto text-[11px]">
        {activeSignal ? (
          <div className="flex items-center gap-1 mb-1">
            <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: color }} />
            <span style={{ color }}>{activeSignal.classification}</span>
            {activeSignal.direction && (
              <span style={{ color: activeSignal.direction === 'LONG' ? 'var(--green)' : 'var(--red)' }}>
                {activeSignal.direction}
              </span>
            )}
            <span style={{ color: 'var(--text-muted)' }}>
              {activeSignal.confidence != null ? `${(activeSignal.confidence * 100).toFixed(0)}%` : ''}
            </span>
          </div>
        ) : (
          <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>No active signal</div>
        )}
        {children}
      </div>
    </div>
  );
}
