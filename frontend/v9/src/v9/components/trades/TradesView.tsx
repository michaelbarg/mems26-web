'use client';
import { useEffect } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import { fetchTrades } from '../../lib/api';
import { TradeCardList } from './TradeCardList';
import { SelectedTradePanel } from './SelectedTradePanel';
import { TradeFilters } from './TradeFilters';
import { EdgeKpiRow } from './EdgeKpiRow';
import { PatternPerformanceStrip } from './PatternPerformanceStrip';
import { EdgeMatrix } from './EdgeMatrix';
import { ExecModeToggle } from './ExecModeToggle';
import { EquityCurveStrip } from './EquityCurveStrip';
import { TargetDistStrip } from './TargetDistStrip';
import { HeatMaeStrip } from './HeatMaeStrip';
import { StopBehaviorPanel } from './StopBehaviorPanel';
import Link from 'next/link';

export function TradesView() {
  const { setTrades } = useTradeStore();

  useEffect(() => {
    fetchTrades()
      .then(setTrades)
      .catch((err) => console.error('Failed to load trades:', err));
  }, [setTrades]);

  return (
    <div className="h-screen flex flex-col" style={{ background: 'var(--bg-primary)' }}>
      <div
        className="h-[40px] flex items-center justify-between px-4 border-b shrink-0"
        style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}
      >
        <div className="flex items-center gap-4">
          <Link href="/" className="text-sm font-bold tracking-wider" style={{ color: 'var(--sys1)' }}>
            MEMS26
          </Link>
          <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>/ Trades</span>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="text-[10px] hover:underline"
            style={{ color: 'var(--text-secondary)', fontFamily: 'ui-monospace, monospace' }}
          >
            Dashboard
          </Link>
          <Link
            href="/?view=build_status"
            className="text-[10px] hover:underline"
            style={{ color: 'var(--text-secondary)', fontFamily: 'ui-monospace, monospace' }}
          >
            Build Status
          </Link>
        </div>
      </div>
      <TradeFilters />
      <ExecModeToggle />
      <EdgeKpiRow />
      <PatternPerformanceStrip />
      <EdgeMatrix />
      <EquityCurveStrip />
      <TargetDistStrip />
      <HeatMaeStrip />
      <StopBehaviorPanel />
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-auto">
          <TradeCardList />
        </div>
        <div
          className="w-[224px] xl:w-[290px] shrink-0 overflow-auto border-r"
          style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}
        >
          <SelectedTradePanel />
        </div>
      </div>
    </div>
  );
}
