'use client';
import { useMemo } from 'react';
import { useSystemStore } from '../../../stores/systemStore';
import { useMarketStore } from '../../../stores/marketStore';

export function SignalTab() {
  const allSignals = useSystemStore((s) => s.signals);
  const activeSignals = useSystemStore((s) => s.activeSignals);
  const bars = useMarketStore((s) => s.bars5min);

  // Day classification from System 1
  const dayClassification = useMemo(() => {
    const sig = activeSignals[1];
    return {
      type: (sig?.payload?.day_type as string) ?? '--',
      description: (sig?.payload?.description as string) ?? '',
      classification: sig?.classification ?? '--',
    };
  }, [activeSignals]);

  // IB metrics from System 1
  const ibMetrics = useMemo(() => {
    const sig = activeSignals[1];
    return {
      range: (sig?.payload?.ib_range as number) ?? null,
      locked: (sig?.payload?.ib_locked as boolean) ?? false,
    };
  }, [activeSignals]);

  // Session phase from System 6
  const sessionPhase = useMemo(() => {
    const sig = activeSignals[6];
    return {
      phase: (sig?.payload?.session_phase as string) ?? '--',
      gateOpen: (sig?.payload?.gate_open as boolean) ?? false,
    };
  }, [activeSignals]);

  // Traffic light based on active signals
  const trafficLight = useMemo(() => {
    const firingSigs = [activeSignals[1], activeSignals[2], activeSignals[4]].filter(Boolean);
    if (firingSigs.length === 0) return 'red';
    const hasHigh = firingSigs.some((s) => (s?.confidence ?? 0) >= 0.7);
    return hasHigh ? 'green' : 'yellow';
  }, [activeSignals]);

  const trafficColors: Record<string, string> = {
    green: 'var(--green)',
    yellow: '#FACC15',
    red: 'var(--red)',
  };

  return (
    <div className="flex flex-col gap-3 text-xs">
      {/* Day Classification */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Day Classification
        </div>
        <div className="text-sm font-bold" style={{ color: '#58a6ff' }}>
          {dayClassification.type}
        </div>
        {dayClassification.description && (
          <div className="mt-0.5" style={{ color: 'var(--text-muted)' }}>
            {dayClassification.description}
          </div>
        )}
      </div>

      {/* IB Metrics */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          IB Metrics
        </div>
        <div style={{ color: 'var(--text-secondary)' }}>
          <div>Range: {ibMetrics.range !== null ? `${ibMetrics.range.toFixed(1)}pt` : '--'}</div>
          <div>IB Locked: {ibMetrics.locked ? 'Yes' : 'No'}</div>
        </div>
      </div>

      {/* Session Phase */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Session Phase
        </div>
        <div style={{ color: 'var(--text-secondary)' }}>
          <div>{sessionPhase.phase}</div>
          <div style={{ color: sessionPhase.gateOpen ? 'var(--green)' : 'var(--red)' }}>
            Gate: {sessionPhase.gateOpen ? 'OPEN' : 'CLOSED'}
          </div>
        </div>
      </div>

      {/* Traffic Light */}
      <div className="p-2 rounded flex items-center gap-2" style={{ background: 'var(--bg-tertiary)' }}>
        <div
          className="w-4 h-4 rounded-full"
          style={{ background: trafficColors[trafficLight] }}
        />
        <span style={{ color: 'var(--text-primary)' }}>
          {trafficLight === 'green' ? 'GO' : trafficLight === 'yellow' ? 'CAUTION' : 'STOP'}
        </span>
      </div>

      {/* AI Signal Status */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          AI Status
        </div>
        <div style={{ color: 'var(--text-secondary)' }}>
          {trafficLight === 'green' ? 'ready' : trafficLight === 'yellow' ? 'waiting' : 'blocked'}
        </div>
      </div>

      {/* Active Signals Count */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Signals Today
        </div>
        <div style={{ color: 'var(--text-secondary)' }}>
          Total: {allSignals.length}
        </div>
      </div>
    </div>
  );
}
