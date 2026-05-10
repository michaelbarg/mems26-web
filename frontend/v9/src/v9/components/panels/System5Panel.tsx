'use client';
import { useMemo } from 'react';
import { SystemPanelWrapper } from './SystemPanelWrapper';
import { useMarketStore } from '../../stores/marketStore';
import { useSystemStore } from '../../stores/systemStore';

export function System5Panel() {
  const { currentPOC, currentVAH, currentVAL, tpoBars } = useMarketStore();
  const allSignals = useSystemStore((s) => s.signals);
  const sys5Signals = useMemo(() => allSignals.filter((sg) => sg.system_id === 5), [allSignals]);
  const markers = useSystemStore((s) => s.markers);
  const sys5Markers = useMemo(() => markers.filter((m) => m.system_id === 5), [markers]);
  const latest = sys5Signals[sys5Signals.length - 1];

  return (
    <SystemPanelWrapper systemId={5}>
      <div className="space-y-0.5 mt-1 font-mono" style={{ color: 'var(--text-secondary)' }}>
        <div>
          <span className="opacity-60">Mode: </span>
          <span>observer</span>
        </div>
        <div className="flex justify-between">
          <span className="opacity-60">POC:</span>
          <span style={{ color: '#e3b341' }}>{currentPOC?.toFixed(2) || '\u2014'}</span>
        </div>
        <div className="flex justify-between">
          <span className="opacity-60">VAH:</span>
          <span style={{ color: 'var(--green)' }}>{currentVAH?.toFixed(2) || '\u2014'}</span>
        </div>
        <div className="flex justify-between">
          <span className="opacity-60">VAL:</span>
          <span style={{ color: 'var(--red)' }}>{currentVAL?.toFixed(2) || '\u2014'}</span>
        </div>
        <div className="flex justify-between">
          <span className="opacity-60">Letters:</span>
          <span>{tpoBars.length}</span>
        </div>
        <div className="flex justify-between">
          <span className="opacity-60">Marks:</span>
          <span>{sys5Markers.length}</span>
        </div>
        {latest?.payload?.profile_shape != null && (
          <div className="flex justify-between">
            <span className="opacity-60">Shape:</span>
            <span>{String(latest.payload.profile_shape)}</span>
          </div>
        )}
      </div>
    </SystemPanelWrapper>
  );
}
