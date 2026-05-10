'use client';
import { useMemo } from 'react';
import { SystemPanelWrapper } from './SystemPanelWrapper';
import { useSystemStore } from '../../stores/systemStore';
import { useTradeStore } from '../../stores/tradeStore';

export function System2Panel() {
  const allSignals = useSystemStore((s) => s.signals);
  const sys2Signals = useMemo(() => allSignals.filter((sg) => sg.system_id === 2), [allSignals]);
  const recent = useMemo(() => sys2Signals.slice(-3).reverse(), [sys2Signals]);
  const trades = useTradeStore((s) => s.trades);
  const sys2Trades = useMemo(() => trades.filter((t) => t.system === 2), [trades]);
  const shadowTrades = useMemo(() => sys2Trades.filter((t) => t.mode === 'SHADOW'), [sys2Trades]);
  const demoTrades = useMemo(() => sys2Trades.filter((t) => t.mode === 'SIM'), [sys2Trades]);
  const shadowWins = shadowTrades.filter((t) => t.outcome === 'WIN').length;
  const shadowLosses = shadowTrades.filter((t) => t.outcome === 'LOSS').length;
  const shadowPnl = shadowTrades.reduce((sum, t) => sum + (t.pnl_usd ?? 0), 0);
  const demoPnl = demoTrades.reduce((sum, t) => sum + (t.pnl_usd ?? 0), 0);
  const activeDemoCount = demoTrades.filter((t) => t.outcome === 'OPEN').length;

  return (
    <SystemPanelWrapper systemId={2}>
      <div className="space-y-0.5 mt-1" style={{ color: 'var(--text-secondary)' }}>
        <div>
          <span className="opacity-60">Setups: </span>
          <span>{sys2Signals.length}</span>
        </div>
        <div>
          <span className="opacity-60">SHADOW: </span>
          <span>{shadowTrades.length} ({shadowWins}W {shadowLosses}L)</span>
        </div>
        {demoTrades.length > 0 && (
          <div>
            <span className="opacity-60">DEMO: </span>
            <span>{activeDemoCount > 0 ? `${activeDemoCount} active` : `${demoTrades.length}`}</span>
          </div>
        )}
        <div>
          <span className="opacity-60">PnL: </span>
          <span style={{ color: shadowPnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
            ${shadowPnl.toFixed(0)}
          </span>
          {demoTrades.length > 0 && (
            <span style={{ color: 'var(--text-muted)' }}> / ${demoPnl.toFixed(0)}</span>
          )}
        </div>
        {/* Latest signals */}
        {recent.length > 0 && (
          <div className="border-t pt-1 mt-1" style={{ borderColor: 'var(--border)' }}>
            <div className="text-[10px] opacity-50 mb-0.5">Latest:</div>
            {recent.map((s) => (
              <div key={s.id} className="flex items-center gap-1">
                <span className="text-[10px] opacity-50">
                  {new Date(s.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
                <span>{s.classification}</span>
                {s.direction && (
                  <span style={{ color: s.direction === 'LONG' ? 'var(--green)' : 'var(--red)' }}>
                    {s.direction}
                  </span>
                )}
                {s.confidence != null && (
                  <span className="opacity-50">{(s.confidence * 10).toFixed(0)}/10</span>
                )}
              </div>
            ))}
          </div>
        )}
        {recent.length === 0 && (
          <div style={{ color: 'var(--text-muted)' }}>No patterns detected</div>
        )}
      </div>
    </SystemPanelWrapper>
  );
}
