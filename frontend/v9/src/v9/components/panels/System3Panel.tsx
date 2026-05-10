'use client';
import { useMemo } from 'react';
import { SystemPanelWrapper } from './SystemPanelWrapper';
import { useSystemStore } from '../../stores/systemStore';

export function System3Panel() {
  const allSignals = useSystemStore((s) => s.signals);
  const signals = useMemo(() => allSignals.filter((sg) => sg.system_id === 3), [allSignals]);
  const markers = useSystemStore((s) => s.markers);
  const sys3Markers = useMemo(() => markers.filter((m) => m.system_id === 3), [markers]);
  const strategicMarks = useMemo(() => sys3Markers.filter((m) => m.type === 'strategic').length, [sys3Markers]);
  const tacticalMarks = useMemo(() => sys3Markers.filter((m) => m.type === 'tactical').length, [sys3Markers]);
  const latest = signals[signals.length - 1];

  return (
    <SystemPanelWrapper systemId={3}>
      <div className="space-y-1 mt-1" style={{ color: 'var(--text-secondary)' }}>
        <div>
          <span className="opacity-60">Mode: </span>
          <span>observer</span>
        </div>
        <div>
          <span className="opacity-60">Strategic: </span>
          <span>{strategicMarks}</span>
        </div>
        <div>
          <span className="opacity-60">Tactical: </span>
          <span>{tacticalMarks}</span>
        </div>
        {latest && (
          <div className="border-t pt-1 mt-1" style={{ borderColor: 'var(--border)' }}>
            <div className="text-[10px] opacity-50 mb-0.5">Latest signal:</div>
            <div>
              <span>{latest.classification || '\u2014'}</span>
            </div>
            {latest.direction && (
              <div>
                <span className="opacity-60">Direction: </span>
                <span style={{ color: latest.direction === 'LONG' || latest.direction === 'UP' ? 'var(--green)' : 'var(--red)' }}>
                  {latest.direction}
                </span>
              </div>
            )}
            {latest.confidence != null && (
              <div>
                <span className="opacity-60">Confluence: </span>
                <span>{(latest.confidence * 10).toFixed(0)}/10</span>
              </div>
            )}
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
      </div>
    </SystemPanelWrapper>
  );
}
