'use client';
import { SystemPanelWrapper } from './SystemPanelWrapper';
import { useMarketStore } from '../../stores/marketStore';

export function System5Panel() {
  const { currentPOC, currentVAH, currentVAL, tpoBars } = useMarketStore();

  return (
    <SystemPanelWrapper systemId={5}>
      <div className="space-y-0.5 mt-1 font-mono" style={{ color: 'var(--text-secondary)' }}>
        <div className="flex justify-between">
          <span className="opacity-60">POC:</span>
          <span style={{ color: '#79c0ff' }}>{currentPOC?.toFixed(2) || '\u2014'}</span>
        </div>
        <div className="flex justify-between">
          <span className="opacity-60">VAH:</span>
          <span>{currentVAH?.toFixed(2) || '\u2014'}</span>
        </div>
        <div className="flex justify-between">
          <span className="opacity-60">VAL:</span>
          <span>{currentVAL?.toFixed(2) || '\u2014'}</span>
        </div>
        <div className="flex justify-between">
          <span className="opacity-60">Letters:</span>
          <span>{tpoBars.length}</span>
        </div>
      </div>
    </SystemPanelWrapper>
  );
}
