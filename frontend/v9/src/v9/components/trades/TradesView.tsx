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
import { TradesSummaryStrip } from './TradesSummaryStrip';
import Link from 'next/link';

export function TradesView() {
  const { setTrades } = useTradeStore();

  useEffect(() => {
    fetchTrades()
      .then(setTrades)
      .catch((err) => console.error('Failed to load trades:', err));
  }, [setTrades]);

  return (
    <div style={{ height: '100vh', overflowY: 'auto', background: 'var(--bg-primary)', color: 'var(--text-primary)', fontFamily: "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif", fontSize: 13 }}>
      {/* Header */}
      <header
        style={{
          height: 40,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
          background: 'var(--bg-secondary)',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <Link href="/" style={{ fontWeight: 700, letterSpacing: 1, color: 'var(--sys1)', fontSize: 13, textDecoration: 'none' }}>
            MEMS26
          </Link>
          <span style={{ color: 'var(--text-secondary)', fontSize: 11, marginInlineStart: 10 }}>/ Trades</span>
        </div>
        <div style={{ display: 'flex', gap: 14, fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--text-secondary)' }}>
          <Link href="/" style={{ color: 'inherit', textDecoration: 'none' }}>Dashboard</Link>
          <Link href="/?view=build_status" style={{ color: 'inherit', textDecoration: 'none' }}>Build Status</Link>
        </div>
      </header>

      {/* Summary strip — top-level KPIs */}
      <TradesSummaryStrip />

      {/* Main scrollable content */}
      <div style={{ maxWidth: 1340, margin: '0 auto', padding: '0 16px 60px' }}>
        <TradeFilters />
        <ExecModeToggle />
        <EdgeKpiRow />
        <PatternPerformanceStrip />
        <EdgeMatrix />

        {/* Target + Heat two-column */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, alignItems: 'start', marginTop: 14 }}>
          <TargetDistStrip />
          <HeatMaeStrip />
        </div>

        <EquityCurveStrip />

        {/* Trade list */}
        <div style={{ marginTop: 8 }}>
          <TradeCardList />
        </div>

        <StopBehaviorPanel />

        {/* Selected trade detail panel */}
        <div style={{ marginTop: 14, border: '1px solid var(--border)', borderRadius: 8, background: 'var(--bg-secondary)', overflow: 'hidden' }}>
          <SelectedTradePanel />
        </div>
      </div>
    </div>
  );
}
