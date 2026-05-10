'use client';
import { useMemo } from 'react';
import { useSystemStore } from '../../../stores/systemStore';

export function DayTab() {
  const activeSignals = useSystemStore((s) => s.activeSignals);

  const dayInfo = useMemo(() => {
    const sig = activeSignals[1];
    return {
      type: (sig?.payload?.day_type as string) ?? '--',
      description: (sig?.payload?.description as string) ?? '',
      ibRange: (sig?.payload?.ib_range as number) ?? null,
      ibLocked: (sig?.payload?.ib_locked as boolean) ?? false,
      gapStatus: (sig?.payload?.gap_status as string) ?? '--',
      confidence: sig?.confidence ?? null,
      classification: sig?.classification ?? '--',
    };
  }, [activeSignals]);

  const sessionPhase = useMemo(() => {
    const sig = activeSignals[6];
    return (sig?.payload?.session_phase as string) ?? '--';
  }, [activeSignals]);

  const dayTypeIcon: Record<string, string> = {
    Trend: 'arrow-up-right',
    Range: 'minus',
    'Gap-Fill': 'rotate-cw',
    'Vol-Expansion': 'zap',
  };

  return (
    <div className="flex flex-col gap-3 text-xs">
      {/* Day Type */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Day Type
        </div>
        <div className="text-lg font-bold" style={{ color: '#58a6ff' }}>
          {dayInfo.type}
        </div>
        {dayInfo.description && (
          <div className="mt-1" style={{ color: 'var(--text-muted)' }}>
            {dayInfo.description}
          </div>
        )}
        {dayInfo.confidence !== null && (
          <div className="mt-1" style={{ color: 'var(--text-secondary)' }}>
            Confidence: {(dayInfo.confidence * 100).toFixed(0)}%
          </div>
        )}
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
          <div style={{ color: 'var(--text-muted)' }}>IB Range</div>
          <div className="font-bold" style={{ color: 'var(--text-primary)' }}>
            {dayInfo.ibRange !== null ? `${dayInfo.ibRange.toFixed(1)}pt` : '--'}
          </div>
        </div>
        <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
          <div style={{ color: 'var(--text-muted)' }}>IB Locked</div>
          <div className="font-bold" style={{ color: dayInfo.ibLocked ? 'var(--green)' : 'var(--text-primary)' }}>
            {dayInfo.ibLocked ? 'Yes' : 'No'}
          </div>
        </div>
        <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
          <div style={{ color: 'var(--text-muted)' }}>Gap</div>
          <div className="font-bold" style={{ color: 'var(--text-primary)' }}>
            {dayInfo.gapStatus}
          </div>
        </div>
        <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
          <div style={{ color: 'var(--text-muted)' }}>Phase</div>
          <div className="font-bold" style={{ color: 'var(--text-primary)' }}>
            {sessionPhase}
          </div>
        </div>
      </div>

      {/* Decision tree path placeholder */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Decision Path
        </div>
        <div style={{ color: 'var(--text-muted)' }}>
          Phase 7.3: Decision tree visualization coming soon
        </div>
      </div>
    </div>
  );
}
