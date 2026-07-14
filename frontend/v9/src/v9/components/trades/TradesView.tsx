'use client';
// TradesView — Trade Review page (/trades), reorganized for review comfort:
//   1. Summary strip (today per mode + filtered KPIs)
//   2. Filter bar (mode / direction / pattern / date — default today)
//   3. Trades table (sortable; row click → inline detail with MgmtTimeline +
//      TradeChart via TradeRowExpand) — with a cards-view toggle preserving
//      the previous TradeCardList workflow
//   4. Selected-trade side summary (existing SelectedTradePanel)
//   5. Analytics strips folded into a collapsible section (everything that was
//      previously always-on: KPIs / pattern edge / matrix / distributions /
//      equity / stop behavior)
//
// Auto-refresh: 30000ms exactly — matches the slowest documented polling floor
// (CLAUDE.md "Frontend Polling Floors": TradeHistoryStrip 30000ms, "History,
// not real-time"). In-flight guard prevents request pile-up on a slow backend.
import { useEffect, useState } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import { fetchTrades } from '../../lib/api';
import { TradeCardList } from './TradeCardList';
import { TradesTable } from './TradesTable';
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
import { TradeDetailsModal } from './TradeDetailsModal';
import Link from 'next/link';

const REFRESH_MS = 30000; // floor: TradeHistoryStrip 30000ms (CLAUDE.md) — do not lower

type ListView = 'table' | 'cards';

export function TradesView() {
  const { setTrades, setSelectedTradeId } = useTradeStore();
  const [listView, setListView] = useState<ListView>('table');
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  useEffect(() => {
    let dead = false;
    let inFlight = false;
    const load = () => {
      if (inFlight) return;
      inFlight = true;
      fetchTrades()
        .then((rows) => {
          if (dead) return;
          setTrades(rows);
          setLastRefresh(new Date());
        })
        .catch((err) => console.error('Failed to load trades:', err))
        .finally(() => { inFlight = false; });
    };
    load();
    const id = setInterval(load, REFRESH_MS);
    return () => { dead = true; clearInterval(id); };
  }, [setTrades]);

  // מייקל 07-10: deep-link ?trade={id} — פותח את פירוט-העסקה (מה-drawer בדשבורד / קישור "פתח ב-TradeReview").
  useEffect(() => {
    const p = new URLSearchParams(window.location.search).get('trade');
    const id = p ? Number(p) : NaN;
    if (Number.isFinite(id)) setSelectedTradeId(id);
  }, [setSelectedTradeId]);

  const viewBtn = (v: ListView): React.CSSProperties => ({
    fontFamily: 'var(--mono)',
    fontSize: 10.5,
    padding: '3px 10px',
    borderRadius: 6,
    cursor: 'pointer',
    background: listView === v ? 'rgba(88,166,255,0.12)' : 'var(--bg-tertiary)',
    color: listView === v ? 'var(--sys1)' : 'var(--text-secondary)',
    border: `1px solid ${listView === v ? 'var(--sys1)' : 'var(--border)'}`,
    fontWeight: listView === v ? 600 : 400,
  });

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
          {lastRefresh && (
            <span style={{ color: 'var(--text-muted)', fontSize: 9, marginInlineStart: 10, fontFamily: 'var(--mono)' }} title="רענון אוטומטי כל 30 שניות">
              עודכן {lastRefresh.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 14, fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--text-secondary)' }}>
          <Link href="/" style={{ color: 'inherit', textDecoration: 'none' }}>Dashboard</Link>
          <Link href="/?view=build_status" style={{ color: 'inherit', textDecoration: 'none' }}>Build Status</Link>
          {/* External review tools (static pages in /public) — new tab */}
          <a href="/patterns-visual.html" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'none' }} title="Playbook תבניות — נפתח בטאב חדש">
            תבניות · Playbook
          </a>
          <a href="/trade-placement.html" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'none' }} title="מיקומי-מימוש — נפתח בטאב חדש">
            מיקומי-מימוש
          </a>
          <a href="https://docs.google.com/spreadsheets/d/1iqLsTZc9CxMVSldV918nZbEx4AXcqzuEVZkcXKRtL2k/edit" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--green, #2ea043)', textDecoration: 'none', fontWeight: 600 }} title="לוג-עסקאות-לייב בזמן-אמת (Sierra → Google Sheets) — נפתח בטאב חדש">
            📈 Google Sheets
          </a>
        </div>
      </header>

      {/* Summary strip — today per mode + filtered KPIs */}
      <TradesSummaryStrip />

      {/* Main scrollable content */}
      <div style={{ maxWidth: 1340, margin: '0 auto', padding: '0 16px 60px' }}>
        <TradeFilters />

        {/* List view toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10, marginBottom: 6 }}>
          <button onClick={() => setListView('table')} style={viewBtn('table')}>טבלה</button>
          <button onClick={() => setListView('cards')} style={viewBtn('cards')}>כרטיסים</button>
          <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>
            לחיצה על שורה פותחת פירוט מלא (צ׳ארט + ציר-זמן ניהול)
          </span>
        </div>

        {/* Trade list — table (sortable) or the previous cards workflow */}
        {listView === 'table' ? <TradesTable /> : <TradeCardList />}

        {/* Selected trade detail panel (compact side summary) */}
        <div style={{ marginTop: 14, border: '1px solid var(--border)', borderRadius: 8, background: 'var(--bg-secondary)', overflow: 'hidden' }}>
          <SelectedTradePanel />
        </div>

        {/* Analytics — collapsed by default to keep the review flow comfortable */}
        <div style={{ marginTop: 14 }}>
          <button
            onClick={() => setShowAnalytics((s) => !s)}
            style={{
              width: '100%',
              textAlign: 'start',
              fontFamily: 'var(--mono)',
              fontSize: 11,
              padding: '7px 12px',
              borderRadius: 8,
              cursor: 'pointer',
              background: 'var(--bg-secondary)',
              color: showAnalytics ? 'var(--sys1)' : 'var(--text-secondary)',
              border: `1px solid ${showAnalytics ? 'var(--sys1)' : 'var(--border)'}`,
            }}
          >
            {showAnalytics ? '▾' : '▸'} אנליטיקה (KPIs · תבניות · מטריצה · התפלגויות · עקומת הון · ניהול סטופ)
          </button>
          {showAnalytics && (
            <div>
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
              <StopBehaviorPanel />
            </div>
          )}
        </div>
      </div>

      {/* מייקל 07-10: drawer פירוט-עסקה — נפתח מ-deep-link ?trade={id} ("פתח ב-TradeReview") ומלחיצה על שורה */}
      <TradeDetailsModal />
    </div>
  );
}
