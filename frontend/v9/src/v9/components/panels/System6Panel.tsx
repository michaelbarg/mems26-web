'use client';
import { useMemo } from 'react';
import { SystemPanelWrapper } from './SystemPanelWrapper';
import { useSystemStore } from '../../stores/systemStore';

export function System6Panel() {
  const allSignals = useSystemStore((s) => s.signals);
  const signals = useMemo(() => allSignals.filter((sg) => sg.system_id === 6), [allSignals]);
  const latest = signals[signals.length - 1];

  const now = new Date();
  const hour = now.getUTCHours();
  const isLondon = hour >= 8 && hour < 11;
  const isNY = hour >= 13 && hour < 16;
  const isAsian = hour >= 0 && hour < 4;
  const activeZone = isLondon ? 'London' : isNY ? 'New York' : isAsian ? 'Asian' : 'None';

  // Determine session phase from signal payload
  const sessionPhase = (latest?.payload?.session_phase as string) || activeZone;
  const qualityLevel = latest?.payload?.quality as string;

  return (
    <SystemPanelWrapper systemId={6}>
      <div className="space-y-1 mt-1" style={{ color: 'var(--text-secondary)' }}>
        <div>
          <span className="opacity-60">Mode: </span>
          <span>gate</span>
        </div>
        <div>
          <span className="opacity-60">Zone: </span>
          <span style={{ color: activeZone !== 'None' ? '#8b949e' : 'var(--text-muted)' }}>
            {sessionPhase}
          </span>
        </div>
        <div>
          <span className="opacity-60">Gate: </span>
          <span style={{ color: latest?.payload?.gate_open ? 'var(--green)' : 'var(--red)' }}>
            {latest?.payload?.gate_open ? 'OPEN' : 'CLOSED'}
          </span>
        </div>
        {latest && (
          <>
            <div>
              <span className="opacity-60">Volume: </span>
              <span>{(latest.payload?.session_volume as string) || '\u2014'}</span>
            </div>
            {qualityLevel && (
              <div>
                <span className="opacity-60">Quality: </span>
                <span style={{
                  color: qualityLevel === 'HIGH' ? 'var(--green)' : qualityLevel === 'LOW' ? 'var(--red)' : 'var(--orange)',
                }}>
                  {qualityLevel}
                </span>
              </div>
            )}
          </>
        )}
      </div>
    </SystemPanelWrapper>
  );
}
