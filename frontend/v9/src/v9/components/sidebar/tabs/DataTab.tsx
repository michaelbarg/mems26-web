'use client';
import { useMemo } from 'react';
import { useMarketStore } from '../../../stores/marketStore';
import { useSystemStore } from '../../../stores/systemStore';

interface MetricRow {
  label: string;
  value: string;
  ok: boolean;
}

export function DataTab() {
  const market = useMarketStore();
  const signals = useSystemStore((s) => s.signals);

  const indicators = useMemo((): MetricRow[] => {
    const checks: MetricRow[] = [
      { label: 'POC', value: market.currentPOC?.toFixed(2) ?? '--', ok: market.currentPOC !== null },
      { label: 'VAH', value: market.currentVAH?.toFixed(2) ?? '--', ok: market.currentVAH !== null },
      { label: 'VAL', value: market.currentVAL?.toFixed(2) ?? '--', ok: market.currentVAL !== null },
      { label: 'PDH', value: market.pdh?.toFixed(2) ?? '--', ok: market.pdh !== null },
      { label: 'PDL', value: market.pdl?.toFixed(2) ?? '--', ok: market.pdl !== null },
      { label: 'ONH', value: market.onh?.toFixed(2) ?? '--', ok: market.onh !== null },
      { label: 'ONL', value: market.onl?.toFixed(2) ?? '--', ok: market.onl !== null },
      { label: 'OPEN', value: market.openPrice?.toFixed(2) ?? '--', ok: market.openPrice !== null },
      { label: 'Vegas 12', value: market.vegasEma12?.toFixed(2) ?? '--', ok: market.vegasEma12 !== null },
      { label: 'Vegas 144', value: market.vegasEma144?.toFixed(2) ?? '--', ok: market.vegasEma144 !== null },
      { label: '5min Bars', value: String(market.bars5min.length), ok: market.bars5min.length > 0 },
      { label: 'Tick Rev', value: String(market.tickReversalBars.length), ok: market.tickReversalBars.length > 0 },
      { label: 'Signals', value: String(signals.length), ok: signals.length > 0 },
    ];
    return checks;
  }, [market, signals]);

  const okCount = indicators.filter((i) => i.ok).length;

  // Trend metrics from latest bar
  const lastBar = market.bars5min[market.bars5min.length - 1];

  return (
    <div className="flex flex-col gap-3 text-xs">
      {/* Indicator Status */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Indicators: {okCount}/{indicators.length}
        </div>
        <div className="flex flex-col gap-0.5">
          {indicators.map((ind) => (
            <div key={ind.label} className="flex justify-between items-center">
              <span className="flex items-center gap-1">
                <span
                  className="w-2 h-2 rounded-full inline-block"
                  style={{ background: ind.ok ? 'var(--green)' : 'var(--red)' }}
                />
                {ind.label}
              </span>
              <span style={{ color: 'var(--text-muted)' }}>{ind.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Trend Metrics */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Trend Metrics
        </div>
        <div style={{ color: 'var(--text-secondary)' }}>
          <div>CVD: {lastBar?.cumulative_delta?.toFixed(0) ?? '--'}</div>
          <div>VWAP dist: {market.currentPOC && lastBar ? (lastBar.c - market.currentPOC).toFixed(2) : '--'}</div>
          <div>POC dist: {market.currentPOC && lastBar ? (lastBar.c - market.currentPOC).toFixed(2) : '--'}</div>
        </div>
      </div>
    </div>
  );
}
