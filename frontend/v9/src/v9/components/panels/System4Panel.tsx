'use client';
import { SystemPanelWrapper } from './SystemPanelWrapper';
import { useMarketStore } from '../../stores/marketStore';

export function System4Panel() {
  const woodiesBars = useMarketStore((s) => s.woodiesBars);
  const latest = woodiesBars[woodiesBars.length - 1];

  return (
    <SystemPanelWrapper systemId={4}>
      {latest && (
        <div className="space-y-0.5 mt-1 font-mono" style={{ color: 'var(--text-secondary)' }}>
          <div className="flex justify-between">
            <span className="opacity-60">CCI-14:</span>
            <span style={{ color: latest.cci_14 > 0 ? 'var(--green)' : 'var(--red)' }}>
              {latest.cci_14.toFixed(1)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="opacity-60">TCCI:</span>
            <span>{latest.tcci.toFixed(1)}</span>
          </div>
          <div className="flex justify-between">
            <span className="opacity-60">CCI-34:</span>
            <span>{latest.cci_34.toFixed(1)}</span>
          </div>
          {latest.zlr_pattern && (
            <div className="mt-1 px-1 rounded text-center" style={{
              background: 'rgba(251,149,11,0.15)',
              color: '#fb950b',
            }}>
              {latest.zlr_pattern}
            </div>
          )}
        </div>
      )}
    </SystemPanelWrapper>
  );
}
