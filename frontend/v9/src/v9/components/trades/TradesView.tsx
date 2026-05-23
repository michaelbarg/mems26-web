'use client';
import { useEffect } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import { fetchTrades } from '../../lib/api';
import { TradesTable } from './TradesTable';
import { TradeFilters } from './TradeFilters';
import { TradesSummaryStrip } from './TradesSummaryStrip';
import { PatternPerformanceStrip } from './PatternPerformanceStrip';
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
      </div>
      <TradeFilters />
      <TradesSummaryStrip />
      <PatternPerformanceStrip />
      <div className="flex-1 overflow-auto">
        <TradesTable />
      </div>
    </div>
  );
}
