'use client';

import { Suspense, useEffect, useState, useMemo, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  LineChart, Line, BarChart, Bar, ScatterChart, Scatter,
  PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts';

const API_URL = 'https://mems26-web.onrender.com';
const API = API_URL;

function DayBadge({ day }: { day: string }) {
  const colors: Record<string, string> = {
    TREND_DAY: 'bg-green-700', TREND: 'bg-green-700',
    NORMAL: 'bg-gray-600',
    DEVELOPING: 'bg-blue-700',
    VOLATILE: 'bg-orange-600',
    RANGE_DAY: 'bg-purple-700', ROTATIONAL: 'bg-purple-700',
    GAP_FILL: 'bg-yellow-700',
    UNKNOWN: 'bg-red-700',
  };
  return (
    <span className={`${colors[day] || 'bg-gray-600'} text-white px-2 py-0.5 rounded text-[10px] font-semibold`}>
      {day}
    </span>
  );
}

// ── Types ────────────────────────────────────────────────────────────────────

interface Trade {
  id: string;
  ts?: number;
  direction: string;
  entry_price?: number;
  entry?: number;
  exit_price?: number;
  stop: number;
  t1: number;
  t2: number;
  t3: number;
  risk_pts?: number;
  pnl_pts: number;
  pnl_usd: number;
  entry_ts?: number;
  exit_ts?: number;
  status: string;
  close_reason: string;
  setup_type?: string;
  day_type: string;
  killzone: string;
  is_shadow: boolean;
  cb_respected?: boolean;
  mae_pts?: number;
  mfe_pts?: number;
  duration_min?: number;
  score?: number;
  source?: string;  // 'trade' | 'attempt'
  [key: string]: any;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function tsToDate(ts: number): string {
  if (!ts) return '-';
  return new Date(ts * 1000).toLocaleDateString('en-US', { timeZone: 'America/New_York', month: 'short', day: 'numeric' });
}

function tsToTime(ts: number): string {
  if (!ts) return '-';
  return new Date(ts * 1000).toLocaleTimeString('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', hour12: false });
}

function fmtPts(v: number | undefined): string {
  if (v === undefined || v === null) return '-';
  return v >= 0 ? `+${v.toFixed(2)}` : v.toFixed(2);
}

function fmtUsd(v: number | undefined): string {
  if (v === undefined || v === null) return '-';
  return v >= 0 ? `+$${v.toFixed(0)}` : `-$${Math.abs(v).toFixed(0)}`;
}

// ── Main Component ───────────────────────────────────────────────────────────

export default function JournalPageWrapper() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-gray-950 text-gray-500 flex items-center justify-center">Loading journal...</div>}>
      <JournalPage />
    </Suspense>
  );
}

const MES_DOLLAR_PER_PT = 5;

function computeExitPrice(s: any): number | null {
  if (!s.close_reason && !s.closed_ts) return null;
  const cr = s.close_reason || '';
  if (cr === 'STOP' || cr === 'FULL_STOP') return s.initial_stop || s.stop;
  if (cr.includes('T3') || cr === 'HIT_C3') return s.c3_target || s.t3;
  if (cr.includes('T2') || cr === 'HIT_C2') return s.c2_target || s.t2;
  if (cr.includes('T1') || cr === 'HIT_C1') return s.c1_target || s.t1;
  // Fallback: compute from pnl
  const entry = s.initial_entry || s.entry_price || s.entry;
  const contracts = s.contracts_used || 1;
  if (entry && s.pnl_pts != null && contracts > 0) {
    const ptsPerC = s.pnl_pts / contracts;
    return s.direction === 'LONG' ? entry + ptsPerC : entry - ptsPerC;
  }
  return null;
}

function fmtHitTime(ts: number | null): string {
  if (!ts) return '';
  return new Date(ts * 1000).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'America/New_York' });
}

function JournalPage() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // Filter state (from URL params)
  const [fromDate, setFromDate] = useState(searchParams.get('from') || '');
  const [toDate, setToDate] = useState(searchParams.get('to') || '');
  const [tradeTypes, setTradeTypes] = useState<Set<string>>(() => {
    const t = searchParams.get('types');
    return t ? new Set(t.split(',')) : new Set(['shadow', 'live']);
  });
  const [dayTypes, setDayTypes] = useState<Set<string>>(() => {
    const d = searchParams.get('day_types');
    return d ? new Set(d.split(',')) : new Set();
  });
  const [killzones, setKillzones] = useState<Set<string>>(() => {
    const k = searchParams.get('killzones');
    return k ? new Set(k.split(',')) : new Set();
  });
  const [setupTypes, setSetupTypes] = useState<Set<string>>(() => {
    const s = searchParams.get('setup_types');
    return s ? new Set(s.split(',')) : new Set();
  });
  const [outcomes, setOutcomes] = useState<Set<string>>(() => {
    const o = searchParams.get('outcomes');
    return o ? new Set(o.split(',')) : new Set();
  });
  const [cbFilter, setCbFilter] = useState(searchParams.get('cb') || 'all');
  const [sortCol, setSortCol] = useState(searchParams.get('sort') || 'entry_ts');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>((searchParams.get('dir') as any) || 'desc');
  const [showFilters, setShowFilters] = useState(true);
  const [viewMode, setViewMode] = useState<'executed' | 'all'>(() => {
    const v = searchParams.get('view');
    return v === 'all' ? 'all' : 'executed';
  });

  // REAL/SHADOW tabs
  const [journalView, setJournalView] = useState<'REAL' | 'SHADOW'>('REAL');
  const [realSummary, setRealSummary] = useState<any>(null);

  useEffect(() => {
    if (journalView !== 'REAL') return;
    let active = true;
    const fetchSummary = async () => {
      try {
        const res = await fetch(`${API_URL}/analytics/setups/sequential_today_summary`);
        if (res.ok && active) setRealSummary(await res.json());
      } catch {}
    };
    fetchSummary();
    const id = setInterval(fetchSummary, 15000);
    return () => { active = false; clearInterval(id); };
  }, [journalView]);

  // Data
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const [setupDetail, setSetupDetail] = useState<any>(null);
  const [currentDayType, setCurrentDayType] = useState('');
  useEffect(() => {
    const fetchDT = async () => {
      try {
        const res = await fetch(`${API}/analytics/setups/recent?limit=1`);
        const data = await res.json();
        const latest = (data.setups || [])[0];
        if (latest?.day_type) setCurrentDayType(latest.day_type);
      } catch {}
    };
    fetchDT();
    const id = setInterval(fetchDT, 30000);
    return () => clearInterval(id);
  }, []);
  const [setupDetailLoading, setSetupDetailLoading] = useState(false);
  const [showObservations, setShowObservations] = useState(false);
  const [compareIds, setCompareIds] = useState<Set<string>>(new Set());
  const [showCompare, setShowCompare] = useState(false);
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 50;

  // Sync filters to URL
  useEffect(() => {
    const params = new URLSearchParams();
    if (fromDate) params.set('from', fromDate);
    if (toDate) params.set('to', toDate);
    if (tradeTypes.size > 0) params.set('types', Array.from(tradeTypes).join(','));
    if (dayTypes.size > 0) params.set('day_types', Array.from(dayTypes).join(','));
    if (killzones.size > 0) params.set('killzones', Array.from(killzones).join(','));
    if (setupTypes.size > 0) params.set('setup_types', Array.from(setupTypes).join(','));
    if (outcomes.size > 0) params.set('outcomes', Array.from(outcomes).join(','));
    if (cbFilter !== 'all') params.set('cb', cbFilter);
    if (sortCol !== 'entry_ts') params.set('sort', sortCol);
    if (sortDir !== 'desc') params.set('dir', sortDir);
    if (viewMode !== 'executed') params.set('view', viewMode);
    const qs = params.toString();
    window.history.replaceState(null, '', qs ? `?${qs}` : '/journal');
  }, [fromDate, toDate, tradeTypes, dayTypes, killzones, setupTypes, outcomes, cbFilter, sortCol, sortDir]);

  // Fetch data — unified journal (trades + shadow attempts)
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('limit', '200');
      params.set('types', Array.from(tradeTypes).join(','));
      if (viewMode === 'executed') params.set('min_score', '70');
      params.set('include_closed', '1');
      if (fromDate) params.set('from_date', fromDate);
      if (toDate) params.set('to_date', toDate);

      const res = await fetch(`${API_URL}/trades/log?${params}`, { cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        // Normalize fields: unified endpoint uses 'entry'/'ts', trades use 'entry_price'/'entry_ts'
        const normalized = (Array.isArray(data) ? data : []).map((r: any) => ({
          ...r,
          entry_price: r.entry_price ?? r.entry ?? 0,
          entry_ts: r.entry_ts ?? r.ts ?? 0,
          score: r.score ?? r.setup_quality_score ?? 0,
          source: r.source ?? 'trade',
        }));
        setTrades(normalized);
      }
    } catch (e) {
      console.error('Journal fetch failed:', e);
    }
    setLoading(false);
  }, [fromDate, toDate, tradeTypes, viewMode]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Fetch enriched setup data when a row is clicked
  const handleRowClick = useCallback(async (t: Trade) => {
    setSelectedTrade(t);
    setSetupDetail(null);
    setShowObservations(false);
    // Try to fetch from /analytics/setups/{id} for enriched data
    const setupId = t.id;
    if (!setupId || t.source === 'trade') return; // real trades don't have setup detail
    setSetupDetailLoading(true);
    try {
      const res = await fetch(`${API_URL}/analytics/setups/${setupId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.ok) setSetupDetail(data);
      }
    } catch { /* fall back to selectedTrade data */ }
    setSetupDetailLoading(false);
  }, []);

  // ── Filtering ──────────────────────────────────────────────────────────────

  const filteredTrades = useMemo(() => {
    let result = [...trades];

    // Trade type filter
    if (tradeTypes.size > 0) {
      result = result.filter(t => {
        if (tradeTypes.has('shadow') && t.is_shadow) return true;
        if (tradeTypes.has('live') && !t.is_shadow) return true;
        return false;
      });
    }

    // Day type
    if (dayTypes.size > 0) {
      result = result.filter(t => dayTypes.has(t.day_type));
    }

    // Killzone
    if (killzones.size > 0) {
      result = result.filter(t => killzones.has(t.killzone));
    }

    // Setup type
    if (setupTypes.size > 0) {
      result = result.filter(t => setupTypes.has(t.setup_type || ''));
    }

    // Outcome
    if (outcomes.size > 0) {
      result = result.filter(t => {
        const win = (t.pnl_pts || 0) > 0;
        if (outcomes.has('win') && win) return true;
        if (outcomes.has('loss') && !win) return true;
        return false;
      });
    }

    // CB respected
    if (cbFilter === 'yes') result = result.filter(t => t.cb_respected);
    if (cbFilter === 'no') result = result.filter(t => !t.cb_respected);

    // Sort
    result.sort((a, b) => {
      const av = a[sortCol] ?? 0;
      const bv = b[sortCol] ?? 0;
      if (typeof av === 'string') return sortDir === 'asc' ? av.localeCompare(bv as string) : (bv as string).localeCompare(av);
      return sortDir === 'asc' ? (av as number) - (bv as number) : (bv as number) - (av as number);
    });

    return result;
  }, [trades, tradeTypes, dayTypes, killzones, setupTypes, outcomes, cbFilter, sortCol, sortDir]);

  // Tab-filtered view
  const viewFiltered = useMemo(() => {
    if (journalView === 'REAL') return filteredTrades.filter(t => t.executed_in_sim === true);
    return filteredTrades;
  }, [filteredTrades, journalView]);

  const pagedTrades = viewFiltered.slice(0, (page + 1) * PAGE_SIZE);

  // ── KPIs ───────────────────────────────────────────────────────────────────

  const kpis = useMemo(() => {
    // REAL tab: use sequential summary for headline KPIs
    if (journalView === 'REAL' && realSummary) {
      const realRows = viewFiltered.filter(t => t.mae_pts != null);
      return {
        total: realSummary.total_executed_in_sim || 0,
        wr: Math.round(realSummary.sequential_wr || 0),
        netPnl: realSummary.sequential_pnl_usd || 0,
        avgMae: realRows.length ? realRows.reduce((s: number, t: any) => s + (t.mae_pts || 0), 0) / realRows.length : 0,
        avgMfe: realRows.length ? realRows.reduce((s: number, t: any) => s + (t.mfe_pts || 0), 0) / realRows.length : 0,
        shadowCount: 0,
        liveCount: realSummary.executed_closed || 0,
      };
    }
    const t = viewFiltered.filter(t => t.status === 'CLOSED');
    const wins = t.filter(t => (t.pnl_pts || 0) > 0);
    const shadows = t.filter(t => t.is_shadow);
    const live = t.filter(t => !t.is_shadow);
    const totalPnl = t.reduce((s, t) => s + (t.pnl_usd || 0), 0);
    const avgMae = t.length > 0 ? t.reduce((s, t) => s + (t.mae_pts || 0), 0) / t.length : 0;
    const avgMfe = t.length > 0 ? t.reduce((s, t) => s + (t.mfe_pts || 0), 0) / t.length : 0;
    return {
      total: t.length,
      wr: t.length > 0 ? Math.round(wins.length / t.length * 100) : 0,
      netPnl: totalPnl,
      avgMae, avgMfe,
      shadowCount: shadows.length,
      liveCount: live.length,
    };
  }, [viewFiltered, journalView, realSummary]);

  // ── Toggle helpers ─────────────────────────────────────────────────────────

  const toggleSet = (set: Set<string>, setFn: (s: Set<string>) => void, val: string) => {
    const next = new Set(set);
    if (next.has(val)) next.delete(val); else next.add(val);
    setFn(next);
    setPage(0);
  };

  const handleSort = (col: string) => {
    if (sortCol === col) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortCol(col);
      setSortDir('desc');
    }
  };

  const sortArrow = (col: string) => sortCol === col ? (sortDir === 'asc' ? ' \u25B2' : ' \u25BC') : '';

  // ── Export ─────────────────────────────────────────────────────────────────

  const handleExport = (format: 'csv' | 'json', all: boolean = false) => {
    const params = new URLSearchParams();
    params.set('format', format);
    if (!all) {
      if (fromDate) params.set('from', fromDate);
      if (toDate) params.set('to', toDate);
      if (tradeTypes.has('shadow') && !tradeTypes.has('live')) params.set('is_shadow', 'true');
      if (tradeTypes.has('live') && !tradeTypes.has('shadow')) params.set('is_shadow', 'false');
    }
    window.open(`${API_URL}/analytics/export/trades?${params}`, '_blank');
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-950 text-gray-200" style={{ fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      {/* Header */}
      <header className="sticky top-0 z-50 bg-gray-900 border-b border-gray-800 px-4 py-2 flex items-center gap-3">
        <a href="/" className="text-xs bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded">
          Back to Dashboard
        </a>
        <h1 className="text-sm font-bold flex-1">MEMS26 Trade Journal</h1>
        <div className="flex gap-1">
          <button onClick={() => { setViewMode('executed'); setPage(0); }}
            className={`text-xs px-3 py-1.5 rounded ${viewMode === 'executed' ? 'bg-green-900 text-green-300' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}>
            Executed (70+)
          </button>
          <button onClick={() => { setViewMode('all'); setPage(0); }}
            className={`text-xs px-3 py-1.5 rounded ${viewMode === 'all' ? 'bg-blue-900 text-blue-300' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}>
            All Detected
          </button>
        </div>
        <button onClick={() => setShowFilters(f => !f)} className="text-xs bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded">
          Filters {showFilters ? '\u25B2' : '\u25BC'}
        </button>
        <button onClick={fetchData} className="text-xs bg-blue-900 hover:bg-blue-800 px-3 py-1.5 rounded">
          Refresh
        </button>
        <div className="relative group">
          <button className="text-xs bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded">
            Export \u25BC
          </button>
          <div className="hidden group-hover:block absolute right-0 top-full mt-1 bg-gray-800 border border-gray-700 rounded shadow-xl z-50 min-w-[160px]">
            <button onClick={() => handleExport('csv')} className="block w-full text-left px-3 py-2 text-xs hover:bg-gray-700">Current view (CSV)</button>
            <button onClick={() => handleExport('json')} className="block w-full text-left px-3 py-2 text-xs hover:bg-gray-700">Current view (JSON)</button>
            <hr className="border-gray-700" />
            <button onClick={() => handleExport('csv', true)} className="block w-full text-left px-3 py-2 text-xs hover:bg-gray-700">All data (CSV)</button>
            <button onClick={() => handleExport('json', true)} className="block w-full text-left px-3 py-2 text-xs hover:bg-gray-700">All data (JSON)</button>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Filter Panel */}
        {showFilters && (
          <aside className="w-56 shrink-0 bg-gray-900 border-r border-gray-800 p-3 space-y-4 text-xs overflow-y-auto" style={{ maxHeight: 'calc(100vh - 44px)' }}>
            {/* Date Range */}
            <div>
              <label className="block text-gray-500 mb-1">Date Range</label>
              <input type="date" value={fromDate} onChange={e => { setFromDate(e.target.value); setPage(0); }}
                className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 mb-1" />
              <input type="date" value={toDate} onChange={e => { setToDate(e.target.value); setPage(0); }}
                className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1" />
              <div className="flex gap-1 mt-1">
                {[['Today', 0], ['7d', 7], ['30d', 30]] .map(([label, days]) => (
                  <button key={label as string} onClick={() => {
                    const d = new Date();
                    setToDate(d.toISOString().slice(0, 10));
                    d.setDate(d.getDate() - (days as number));
                    setFromDate(d.toISOString().slice(0, 10));
                    setPage(0);
                  }} className="bg-gray-800 hover:bg-gray-700 px-2 py-0.5 rounded">{label as string}</button>
                ))}
                <button onClick={() => { setFromDate(''); setToDate(''); setPage(0); }} className="bg-gray-800 hover:bg-gray-700 px-2 py-0.5 rounded">All</button>
              </div>
            </div>

            {/* Trade Type */}
            <div>
              <label className="block text-gray-500 mb-1">Source</label>
              {['shadow', 'live'].map(t => (
                <label key={t} className="flex items-center gap-1.5 mb-0.5">
                  <input type="checkbox" checked={tradeTypes.has(t)} onChange={() => toggleSet(tradeTypes, setTradeTypes, t)} className="accent-blue-500" />
                  <span className="capitalize">{t}</span>
                </label>
              ))}
            </div>

            {/* Day Type */}
            <div>
              <label className="block text-gray-500 mb-1">Day Type</label>
              {['TREND', 'NORMAL', 'VOLATILE', 'ROTATIONAL'].map(d => (
                <label key={d} className="flex items-center gap-1.5 mb-0.5">
                  <input type="checkbox" checked={dayTypes.has(d)} onChange={() => toggleSet(dayTypes, setDayTypes, d)} className="accent-blue-500" />
                  <span>{d}</span>
                </label>
              ))}
            </div>

            {/* Killzone */}
            <div>
              <label className="block text-gray-500 mb-1">Killzone</label>
              {['LONDON', 'NY_OPEN', 'NY_Open', 'NY_CLOSE', 'NY_Close', 'OUTSIDE'].map(k => (
                <label key={k} className="flex items-center gap-1.5 mb-0.5">
                  <input type="checkbox" checked={killzones.has(k)} onChange={() => toggleSet(killzones, setKillzones, k)} className="accent-blue-500" />
                  <span>{k}</span>
                </label>
              ))}
            </div>

            {/* Setup Type */}
            <div>
              <label className="block text-gray-500 mb-1">Setup Type</label>
              {['SWEEP', 'REJECTION', 'MOMENTUM', 'BOUNCE'].map(s => (
                <label key={s} className="flex items-center gap-1.5 mb-0.5">
                  <input type="checkbox" checked={setupTypes.has(s)} onChange={() => toggleSet(setupTypes, setSetupTypes, s)} className="accent-blue-500" />
                  <span>{s}</span>
                </label>
              ))}
            </div>

            {/* Outcome */}
            <div>
              <label className="block text-gray-500 mb-1">Outcome</label>
              {['win', 'loss'].map(o => (
                <label key={o} className="flex items-center gap-1.5 mb-0.5">
                  <input type="checkbox" checked={outcomes.has(o)} onChange={() => toggleSet(outcomes, setOutcomes, o)} className="accent-blue-500" />
                  <span className="capitalize">{o}</span>
                </label>
              ))}
            </div>

            {/* CB Respected */}
            <div>
              <label className="block text-gray-500 mb-1">CB Respected</label>
              <select value={cbFilter} onChange={e => { setCbFilter(e.target.value); setPage(0); }}
                className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1">
                <option value="all">All</option>
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>
          </aside>
        )}

        {/* Main Content */}
        <main className="flex-1 p-4 space-y-4 overflow-x-auto">
          {/* REAL / SHADOW Tabs */}
          <div className="flex gap-2 items-center">
            <button onClick={() => setJournalView('REAL')}
              className={`px-4 py-1.5 rounded text-xs font-semibold ${journalView === 'REAL' ? 'bg-green-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}>
              REAL ({realSummary?.total_executed_in_sim ?? '?'})
            </button>
            <button onClick={() => setJournalView('SHADOW')}
              className={`px-4 py-1.5 rounded text-xs font-semibold ${journalView === 'SHADOW' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}>
              SHADOW ({filteredTrades.length})
            </button>
            {journalView === 'SHADOW' && (
              <span className="text-[10px] text-yellow-400">Shows ALL detected setups, including filtered out</span>
            )}
          </div>

          {/* KPI Strip */}
          <div className="flex gap-3 flex-wrap">
            {[
              { label: 'Total', value: kpis.total },
              { label: 'WR', value: `${kpis.wr}%` },
              { label: 'Net PnL', value: fmtUsd(kpis.netPnl), color: kpis.netPnl >= 0 ? 'text-green-400' : 'text-red-400' },
              { label: 'Avg MAE', value: `${kpis.avgMae.toFixed(1)}pt` },
              { label: 'Avg MFE', value: `${kpis.avgMfe.toFixed(1)}pt` },
              { label: 'Shadow', value: kpis.shadowCount },
              { label: 'Live', value: kpis.liveCount },
            ].map(k => (
              <div key={k.label} className="bg-gray-900 border border-gray-800 rounded px-3 py-2 text-center min-w-[80px]">
                <div className="text-[10px] text-gray-500 uppercase">{k.label}</div>
                <div className={`text-sm font-mono font-bold ${(k as any).color || ''}`}>{k.value}</div>
              </div>
            ))}
          </div>

          {/* Current day type indicator */}
          {currentDayType && (
            <div className="text-[10px] text-gray-500">
              Current day type: <DayBadge day={currentDayType} /> <span className="text-gray-600">— historical setups may show different values</span>
            </div>
          )}

          {/* Loading */}
          {loading && <div className="text-center text-gray-500 py-8">Loading trades...</div>}

          {/* Table */}
          {!loading && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-500">
                    <th className="px-1 py-1.5 text-left w-6">
                      <span title="Compare" className="cursor-pointer">Cmp</span>
                    </th>
                    <th className="px-1 py-1.5 text-left w-12">Source</th>
                    <th className="px-1 py-1.5 text-left cursor-pointer" onClick={() => handleSort('entry_ts')}>Date{sortArrow('entry_ts')}</th>
                    <th className="px-1 py-1.5 text-left">Time</th>
                    <th className="px-1 py-1.5 text-left cursor-pointer" onClick={() => handleSort('direction')}>Side{sortArrow('direction')}</th>
                    <th className="px-1 py-1.5 text-left cursor-pointer" onClick={() => handleSort('setup_type')}>Setup{sortArrow('setup_type')}</th>
                    <th className="px-1 py-1.5 text-left cursor-pointer" onClick={() => handleSort('day_type')} title="Day Type when detected. Evolves during day (e.g. NORMAL early → DEVELOPING mid → TREND late).">Day{sortArrow('day_type')}</th>
                    <th className="px-1 py-1.5 text-left cursor-pointer" onClick={() => handleSort('killzone')}>KZ{sortArrow('killzone')}</th>
                    <th className="px-1 py-1.5 text-right cursor-pointer" onClick={() => handleSort('entry_price')}>Entry{sortArrow('entry_price')}</th>
                    <th className="px-1 py-1.5 text-right cursor-pointer" onClick={() => handleSort('stop')}>Stop{sortArrow('stop')}</th>
                    <th className="px-1 py-1.5 text-right cursor-pointer" onClick={() => handleSort('risk_pts')}>Risk{sortArrow('risk_pts')}</th>
                    <th className="px-1 py-1.5 text-right cursor-pointer" onClick={() => handleSort('exit_price')}>Exit{sortArrow('exit_price')}</th>
                    <th className="px-1 py-1.5 text-right cursor-pointer" onClick={() => handleSort('pnl_pts')}>PnL{sortArrow('pnl_pts')}</th>
                    <th className="px-1 py-1.5 text-right cursor-pointer" onClick={() => handleSort('pnl_usd')}>${ sortArrow('pnl_usd')}</th>
                    <th className="px-1 py-1.5 text-right cursor-pointer" onClick={() => handleSort('mae_pts')}>MAE{sortArrow('mae_pts')}</th>
                    <th className="px-1 py-1.5 text-right cursor-pointer" onClick={() => handleSort('mfe_pts')}>MFE{sortArrow('mfe_pts')}</th>
                    <th className="px-1 py-1.5 text-right cursor-pointer" onClick={() => handleSort('duration_min')}>Dur{sortArrow('duration_min')}</th>
                    <th className="px-1 py-1.5 text-center cursor-pointer" onClick={() => handleSort('setup_quality_score')}>Q{sortArrow('setup_quality_score')}</th>
                    <th className="px-1 py-1.5 text-center cursor-pointer" onClick={() => handleSort('peak_score')}>Path{sortArrow('peak_score')}</th>
                    <th className="px-1 py-1.5 text-center cursor-pointer" onClick={() => handleSort('observation_count')}>Obs{sortArrow('observation_count')}</th>
                    <th className="px-1 py-1.5 text-left cursor-pointer" onClick={() => handleSort('setup_type')}>Type{sortArrow('setup_type')}</th>
                    <th className="px-1 py-1.5 text-center cursor-pointer" onClick={() => handleSort('close_reason')}>Result{sortArrow('close_reason')}</th>
                    <th className="px-1 py-1.5 text-left">Reasoning</th>
                  </tr>
                </thead>
                <tbody>
                  {pagedTrades.map(t => {
                    const pnl = t.pnl_pts || 0;
                    const isAttempt = t.source === 'attempt';
                    const isExec = t.executed_in_sim === true;
                    const bgClass = isExec ? 'bg-green-950/10 border-l-2 border-l-green-700' : isAttempt ? 'bg-purple-950/10' : t.status !== 'CLOSED' ? '' : pnl > 0 ? 'bg-green-950/30' : pnl < 0 ? 'bg-red-950/30' : '';
                    return (
                      <tr key={`${t.source}_${t.id}`} className={`border-b border-gray-900 hover:bg-gray-800/50 cursor-pointer ${bgClass}`}
                        onClick={() => handleRowClick(t)}>
                        <td className="px-1 py-1 text-center" onClick={e => e.stopPropagation()}>
                          {isExec
                            ? <span className="text-[8px] bg-green-900/50 text-green-300 px-1 rounded" title="Would execute in LIVE">EXEC</span>
                            : <input type="checkbox" checked={compareIds.has(t.id)}
                            onChange={() => {
                              const next = new Set(compareIds);
                              if (next.has(t.id)) next.delete(t.id);
                              else if (next.size < 3) next.add(t.id);
                              setCompareIds(next);
                            }}
                            className="accent-blue-500" />}
                        </td>
                        <td className="px-1 py-1">
                          {t.source === 'setup'
                            ? <span className="bg-emerald-900/50 text-emerald-300 px-1 rounded text-[9px]">Setup</span>
                            : isAttempt
                            ? <span className="bg-purple-900/50 text-purple-300 px-1 rounded text-[9px]">Shadow</span>
                            : <span className="bg-cyan-900/50 text-cyan-300 px-1 rounded text-[9px]">Trade</span>}
                        </td>
                        <td className="px-1 py-1 whitespace-nowrap">{tsToDate(t.entry_ts || t.ts || 0)}</td>
                        <td className="px-1 py-1 whitespace-nowrap">{tsToTime(t.entry_ts || t.ts || 0)}</td>
                        <td className={`px-1 py-1 font-bold ${t.direction === 'LONG' ? 'text-green-400' : 'text-red-400'}`}>
                          {t.direction}
                        </td>
                        <td className="px-1 py-1">{t.setup_type}</td>
                        <td className="px-1 py-1"><DayBadge day={t.day_type || 'UNKNOWN'} /></td>
                        <td className="px-1 py-1">{t.killzone}</td>
                        <td className="px-1 py-1 text-right font-mono">{((t.entry_price || t.entry) || 0).toFixed(2)}</td>
                        <td className="px-1 py-1 text-right font-mono">{(t.stop || 0).toFixed(2)}</td>
                        <td className="px-1 py-1 text-right font-mono">{(t.risk_pts || 0).toFixed(1)}</td>
                        <td className="px-1 py-1 text-right font-mono">{(t.exit_price || computeExitPrice(t))?.toFixed(2) || '-'}</td>
                        <td className={`px-1 py-1 text-right font-mono font-bold ${pnl > 0 ? 'text-green-400' : pnl < 0 ? 'text-red-400' : ''}`}>
                          {pnl ? fmtPts(pnl) : '-'}
                        </td>
                        <td className={`px-1 py-1 text-right font-mono text-[10px] ${(t.pnl_usd||0) > 0 ? 'text-green-400' : (t.pnl_usd||0) < 0 ? 'text-red-400' : 'text-gray-600'}`}>
                          {t.pnl_usd ? fmtUsd(t.pnl_usd) : '-'}
                        </td>
                        <td className="px-1 py-1 text-right font-mono">{(t.mae_pts || 0).toFixed(1)}</td>
                        <td className="px-1 py-1 text-right font-mono">{(t.mfe_pts || 0).toFixed(1)}</td>
                        <td className="px-1 py-1 text-right font-mono">{(t.duration_min || 0).toFixed(0)}m</td>
                        <td className={`px-1 py-1 text-center font-mono font-bold ${
                          (t.score || 0) >= 70 ? 'text-emerald-400' :
                          (t.score || 0) >= 50 ? 'text-amber-400' : 'text-zinc-500'
                        }`}>{t.score || '-'}</td>
                        <td className="px-1 py-1 text-center font-mono text-[9px]">{
                          t.peak_score && t.peak_score > (t.score || 0)
                            ? <span>{t.score || '?'}<span className="text-green-500">{'\u2191'}{t.peak_score}</span></span>
                            : t.score ? <span className="text-zinc-500">{t.score}</span> : '-'
                        }</td>
                        <td className="px-1 py-1 text-center font-mono text-[9px] text-zinc-500">{t.observation_count || '-'}</td>
                        <td className="px-1 py-1 text-[10px]">{
                          t.setup_type ? <span className={`px-1 rounded ${
                            t.setup_type === 'FVG' ? 'bg-blue-900/50 text-blue-300' :
                            t.setup_type === 'SWEEP' ? 'bg-purple-900/50 text-purple-300' :
                            'bg-zinc-800 text-zinc-400'
                          }`}>{t.setup_type}</span> : '-'
                        }</td>
                        <td className="px-1 py-1 text-center text-[10px]">{(() => {
                          const cr = t.close_reason || '';
                          if (cr.includes('T3') || t.t3_hit) return <span className="text-emerald-400 font-bold">{'\u2705\u2705\u2705'} T3</span>;
                          if (cr.includes('T2') || (t.t2_hit && (t.stop_hit || cr.includes('STOP')))) return <span className="text-green-400 font-bold">{'\u2705\u2705'} T2</span>;
                          if (cr.includes('T1') || (t.t1_hit && (t.stop_hit || cr.includes('STOP')))) return <span className="text-green-300">{'\u2705'} T1</span>;
                          if (cr === 'STOP' || cr === 'FULL_STOP' || (t.stop_hit && !t.t1_hit)) return <span className="text-red-400 font-bold">{'\u274C'} STOP</span>;
                          if (cr.includes('EOD')) return <span className="text-yellow-400">EOD</span>;
                          if (t.status === 'CLOSED') return <span className="text-gray-400">DONE</span>;
                          if (t.status === 'LIVE' || t.status === 'BUILDING') return <span className="text-cyan-400">{'\u23F0'} OPEN</span>;
                          if (t.status === 'EXECUTED') return <span className="text-blue-400">EXEC</span>;
                          if (t.status === 'EXPIRED') return <span className="text-zinc-500">EXP</span>;
                          return <span className="text-gray-600">-</span>;
                        })()}</td>
                        <td className="px-1 py-1 text-[9px] text-gray-500 max-w-[200px] truncate" title={t.score_reasons || ''}>
                          {t.score_reasons ? t.score_reasons.split(' | ').slice(0, 2).join(' | ') : '-'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {/* Pagination */}
              {viewFiltered.length > (page + 1) * PAGE_SIZE && (
                <div className="text-center mt-3">
                  <button onClick={() => setPage(p => p + 1)} className="bg-gray-800 hover:bg-gray-700 px-4 py-1.5 rounded text-xs">
                    Load more ({filteredTrades.length - pagedTrades.length} remaining)
                  </button>
                </div>
              )}

              {/* Compare button */}
              {compareIds.size >= 2 && (
                <div className="mt-4 text-center">
                  <button onClick={() => setShowCompare(true)}
                    className="bg-blue-800 hover:bg-blue-700 px-4 py-1.5 rounded text-xs">
                    Compare Selected ({compareIds.size})
                  </button>
                </div>
              )}

              {/* Charts Section */}
              {filteredTrades.length > 0 && (
                <JournalCharts trades={filteredTrades.filter(t => t.status === 'CLOSED')} />
              )}
            </div>
          )}
        </main>
      </div>

      {/* Detail Modal */}
      {selectedTrade && (() => {
        const s = setupDetail?.setup || selectedTrade;
        const obs = setupDetail?.observations || [];
        const t = selectedTrade;
        return (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={() => { setSelectedTrade(null); setSetupDetail(null); }}>
          <div className="bg-gray-900 border border-gray-700 rounded-lg max-w-lg w-full max-h-[80vh] overflow-y-auto p-4" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-3">
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-sm">
                  {t.source === 'setup' ? '\uD83D\uDD2C Setup' : t.is_shadow ? '\uD83D\uDC41\uFE0F Shadow' : '\uD83D\uDCBC Live'} Detail
                </h3>
                <button onClick={() => { navigator.clipboard.writeText(t.id); }}
                  className="text-[9px] text-gray-500 hover:text-gray-300 px-1 rounded bg-gray-800" title="Copy ID">
                  {t.id?.toString().slice(0, 8)}... \uD83D\uDCCB
                </button>
              </div>
              <button onClick={() => { setSelectedTrade(null); setSetupDetail(null); }} className="text-gray-500 hover:text-white text-lg">\u00D7</button>
            </div>
            {setupDetailLoading && <div className="text-[10px] text-gray-500 mb-2">Loading enriched data...</div>}

            {/* Core Info */}
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              <DetailRow label="Direction" value={s.direction} />
              <DetailRow label="Setup Type" value={s.setup_type} />
              <DetailRow label="Entry" value={(s.initial_entry || s.entry_price || t.entry_price || s.entry)?.toFixed(2)} />
              <DetailRow label="Stop" value={(s.initial_stop || s.stop || t.stop)?.toFixed(2)} />
              <DetailRow label="Risk" value={`${(s.risk_pts || t.risk_pts || Math.abs((s.initial_entry||s.entry||0)-(s.initial_stop||s.stop||0))).toFixed(1)}pt`} />
              <DetailRow label="Day Type" value={s.day_type} />
              <DetailRow label="Killzone" value={s.killzone} />
              {(() => { const ep = computeExitPrice(s); return ep ? <DetailRow label="Exit" value={ep.toFixed(2)} /> : null; })()}
              {s.close_reason && <DetailRow label="Close Reason" value={s.close_reason} />}
              {(s.pnl_pts != null || t.pnl_pts != null) && <DetailRow label="PnL" value={fmtPts(s.pnl_pts ?? t.pnl_pts)} highlight={s.pnl_pts ?? t.pnl_pts} />}
              {(s.pnl_usd != null || t.pnl_usd != null) && <DetailRow label="PnL $" value={fmtUsd(s.pnl_usd ?? t.pnl_usd)} highlight={s.pnl_usd ?? t.pnl_usd} />}
              {(s.mae_pts != null) && <DetailRow label="MAE" value={`${s.mae_pts.toFixed(1)}pt`} />}
              {(s.mfe_pts != null) && <DetailRow label="MFE" value={`${s.mfe_pts.toFixed(1)}pt`} />}
              {(s.duration_min != null || t.duration_min) && <DetailRow label="Duration" value={`${(s.duration_min ?? t.duration_min ?? 0).toFixed(0)}min`} />}
              {s.contracts_used && <DetailRow label="Contracts" value={s.contracts_used.toString()} />}
              {s.sim_skip_reason && <DetailRow label="Skip Reason" value={s.sim_skip_reason} />}
            </div>

            {/* Targets */}
            {(s.c1_target || s.t1) && (() => {
              const entry = s.initial_entry || s.entry_price || s.entry || 0;
              const isLong = s.direction === 'LONG';
              const sign = isLong ? 1 : -1;
              const targets = [
                { name: 'T1', price: s.c1_target || s.t1, hit: s.t1_hit, hitTs: s.t1_hit_ts },
                { name: 'T2', price: s.c2_target || s.t2, hit: s.t2_hit, hitTs: s.t2_hit_ts },
                { name: 'T3', price: s.c3_target || s.t3, hit: s.t3_hit, hitTs: s.t3_hit_ts },
              ].filter(tg => tg.price && tg.price > 0);
              const stopPrice = s.initial_stop || s.stop || 0;
              return (
                <div className="mt-3 border-t border-gray-800 pt-2">
                  <h4 className="text-xs font-bold text-gray-400 mb-1">Planned Targets</h4>
                  <div className="space-y-1 text-[10px]">
                    {targets.map(tg => {
                      const dist = ((tg.price - entry) * sign);
                      const pot = dist * (s.contracts_used || 1) * 5;
                      return (
                        <div key={tg.name} className="flex justify-between items-center">
                          <span className="text-gray-400">{tg.name}: <span className="font-mono text-gray-300">{tg.price.toFixed(2)}</span> <span className="text-gray-500">({dist >= 0 ? '+' : ''}{dist.toFixed(1)}pt)</span></span>
                          <span>{tg.hit
                            ? <span className="text-green-400">Hit {tg.hitTs ? `@ ${fmtHitTime(tg.hitTs)}` : ''}</span>
                            : <span className="text-gray-600">Not hit</span>}
                            <span className="text-gray-500 ml-2">${pot >= 0 ? '+' : ''}{pot.toFixed(0)}</span>
                          </span>
                        </div>
                      );
                    })}
                    {stopPrice > 0 && (() => {
                      const stopDist = (stopPrice - entry) * sign;
                      return (
                        <div className="flex justify-between items-center border-t border-gray-800 pt-1">
                          <span className="text-gray-400">Stop: <span className="font-mono text-red-400/70">{stopPrice.toFixed(2)}</span> <span className="text-gray-500">({stopDist >= 0 ? '+' : ''}{stopDist.toFixed(1)}pt)</span></span>
                          <span>{s.stop_hit
                            ? <span className="text-red-400">Hit {s.stop_hit_ts ? `@ ${fmtHitTime(s.stop_hit_ts)}` : ''}</span>
                            : <span className="text-gray-600">Not hit</span>}
                          </span>
                        </div>
                      );
                    })()}
                  </div>
                </div>
              );
            })()}

            {/* Score */}
            <div className="mt-3 border-t border-gray-800 pt-2">
              <div className="flex items-center gap-2 text-xs">
                <span className="text-gray-500">Score:</span>
                <span className={`font-bold ${(s.initial_score || s.score || 0) >= 70 ? 'text-emerald-400' : (s.initial_score || s.score || 0) >= 50 ? 'text-amber-400' : 'text-zinc-400'}`}>
                  {s.initial_score ?? s.score ?? '?'}
                </span>
                {s.peak_score && s.peak_score > (s.initial_score || 0) && (
                  <span className="text-green-500 text-[10px]">{'\u2191'} Peak: {s.peak_score}</span>
                )}
                {s.observation_count && <span className="text-gray-500 text-[10px]">({s.observation_count} obs)</span>}
              </div>
            </div>

            {/* Strategic Tags — from enriched setup data */}
            <div className="mt-3 border-t border-gray-800 pt-2">
              <h4 className="text-xs font-bold text-gray-400 mb-1">Strategic Tags</h4>
              <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[10px]">
                {[
                  { label: 'RelVol', val: s.rel_vol_at_entry, fmt: (v: any) => v?.toFixed(2) },
                  { label: 'CVD Dir', val: s.cvd_direction_at_entry },
                  { label: 'MTF Aligned', val: s.mtf_aligned, fmt: (v: any) => v === true ? 'Yes' : v === false ? 'No' : null },
                  { label: 'VWAP Side', val: s.vwap_side },
                  { label: 'Killzone', val: s.killzone },
                  { label: 'Min Into Session', val: s.minutes_into_session, fmt: (v: any) => `${v}min` },
                ].map(tag => (
                  <div key={tag.label} className="flex justify-between">
                    <span className="text-gray-500">{tag.label}:</span>
                    <span className={tag.val != null ? 'text-gray-300' : 'text-zinc-700'}>
                      {tag.val != null ? (tag.fmt ? tag.fmt(tag.val) : String(tag.val)) : 'Not collected'}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Component Scores */}
            {(s.vegas_score != null || s.tpo_score != null) && (
              <div className="mt-3 border-t border-gray-800 pt-2">
                <h4 className="text-xs font-bold text-gray-400 mb-1">Component Scores</h4>
                <div className="grid grid-cols-4 gap-1 text-[10px]">
                  {[
                    { label: 'Vegas', val: s.vegas_score, max: 30 },
                    { label: 'TPO', val: s.tpo_score, max: 25 },
                    { label: 'FVG', val: s.fvg_score, max: 25 },
                    { label: 'FP', val: s.footprint_score, max: 20 },
                  ].map(c => (
                    <div key={c.label} className="text-center">
                      <div className="text-gray-500">{c.label}</div>
                      <div className={`font-mono font-bold ${(c.val||0) > 0 ? 'text-green-400' : 'text-zinc-600'}`}>
                        {c.val ?? '?'}/{c.max}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Planned Targets + Potential PnL */}
            {(() => {
              const entry = s.initial_entry || s.entry_price || s.entry || 0;
              const stop = s.initial_stop || s.stop || 0;
              const dir = s.direction || 'LONG';
              const isLong = dir === 'LONG';
              const contracts = s.contracts_used || 3;
              const targets = [
                { name: 'T1', price: s.c1_target || s.t1, hit: s.t1_hit, hitTs: s.t1_hit_ts },
                { name: 'T2', price: s.c2_target || s.t2, hit: s.t2_hit, hitTs: s.t2_hit_ts },
                ...(s.c3_target || s.t3 ? [{ name: 'T3', price: s.c3_target || s.t3, hit: s.t3_hit, hitTs: s.t3_hit_ts }] : []),
              ];
              if (!entry || (!targets[0]?.price && !stop)) return null;
              const calcPts = (p: number) => isLong ? p - entry : entry - p;
              const calcPnl = (pts: number) => pts * contracts * MES_DOLLAR_PER_PT;
              const maxPotential = targets.reduce((sum, tg) => sum + (tg.price ? calcPnl(calcPts(tg.price)) : 0), 0);
              const actualPnl = s.pnl_usd ?? (s.pnl_pts != null ? s.pnl_pts * MES_DOLLAR_PER_PT : null);
              return (
                <div className="mt-3 border-t border-gray-800 pt-2">
                  <h4 className="text-xs font-bold text-gray-400 mb-1">{'\uD83C\uDFAF'} Planned Targets</h4>
                  <div className="space-y-1 text-[10px]">
                    {targets.map(tg => {
                      if (!tg.price) return null;
                      const pts = calcPts(tg.price);
                      const pnl = calcPnl(pts);
                      return (
                        <div key={tg.name} className="flex items-center gap-2">
                          <span className="text-gray-400 w-6 font-bold">{tg.name}</span>
                          <span className="font-mono text-green-400">{tg.price.toFixed(2)}</span>
                          <span className="text-gray-500">({pts >= 0 ? '+' : ''}{pts.toFixed(1)}pt)</span>
                          <span>{tg.hit ? <span className="text-green-400">{'\u2705'} Hit{tg.hitTs ? ` @ ${fmtHitTime(tg.hitTs)}` : ''}</span> : <span className="text-zinc-600">{'\u274C'} Not hit</span>}</span>
                          <span className="text-gray-500 ml-auto">{'\u2192'} ${pnl >= 0 ? '+' : ''}{pnl.toFixed(0)}</span>
                        </div>
                      );
                    })}
                    {stop > 0 && (
                      <div className="flex items-center gap-2 border-t border-gray-800 pt-1">
                        <span className="text-gray-400 w-6 font-bold">Stop</span>
                        <span className="font-mono text-red-400">{stop.toFixed(2)}</span>
                        <span className="text-gray-500">({calcPts(stop) >= 0 ? '+' : ''}{calcPts(stop).toFixed(1)}pt)</span>
                        <span>{s.stop_hit ? <span className="text-red-400">{'\u2705'} Hit{s.stop_hit_ts ? ` @ ${fmtHitTime(s.stop_hit_ts)}` : ''}</span> : <span className="text-zinc-600">Not hit</span>}</span>
                        <span className="text-red-400/70 ml-auto">{'\u2192'} ${calcPnl(calcPts(stop)).toFixed(0)}</span>
                      </div>
                    )}
                    <div className="flex justify-between border-t border-gray-800 pt-1 text-[10px]">
                      <span className="text-gray-500">Max potential ({contracts}c):</span>
                      <span className="text-green-400 font-mono font-bold">${maxPotential.toFixed(0)}</span>
                    </div>
                    {actualPnl != null && (
                      <div className="flex justify-between text-[10px]">
                        <span className="text-gray-500">Actual P&L:</span>
                        <span className={`font-mono font-bold ${actualPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>${actualPnl >= 0 ? '+' : ''}{actualPnl.toFixed(0)}</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })()}

            {/* Score Reasoning */}
            {s.score_reasons && (
              <div className="mt-3 border-t border-gray-800 pt-2">
                <h4 className="text-xs font-bold text-gray-400 mb-1">Score Reasoning</h4>
                <div className="space-y-0.5">
                  {s.score_reasons.split(' | ').map((r: string, i: number) => {
                    const hasPlus = /\(\+\d+\)/.test(r);
                    const opposes = /OPPOSES|no.*data|too narrow/i.test(r);
                    const color = hasPlus ? 'text-green-400' : opposes ? 'text-red-400' : 'text-amber-400';
                    const icon = hasPlus ? '\u2713' : opposes ? '\u2717' : '\u26A0';
                    return <div key={i} className={`text-[10px] ${color}`}>{icon} {r}</div>;
                  })}
                </div>
              </div>
            )}

            {/* Score Evolution (observations) */}
            {obs.length > 0 && (
              <div className="mt-3 border-t border-gray-800 pt-2">
                <button onClick={() => setShowObservations(!showObservations)}
                  className="text-xs text-gray-400 hover:text-gray-200 flex items-center gap-1">
                  {showObservations ? '\u25BC' : '\u25B6'} Score Evolution ({obs.length} observations)
                </button>
                {showObservations && (
                  <table className="w-full text-[9px] mt-1 border-collapse">
                    <thead>
                      <tr className="text-gray-500 border-b border-gray-800">
                        <th className="text-left py-0.5">Time</th>
                        <th className="text-right py-0.5">Total</th>
                        <th className="text-right py-0.5">V</th>
                        <th className="text-right py-0.5">T</th>
                        <th className="text-right py-0.5">F</th>
                        <th className="text-right py-0.5">FP</th>
                      </tr>
                    </thead>
                    <tbody>
                      {obs.map((o: any, i: number) => (
                        <tr key={i} className="border-b border-gray-900">
                          <td className="py-0.5 text-gray-400">{new Date((o.observation_ts || 0) * 1000).toLocaleTimeString('en-US', {hour:'2-digit',minute:'2-digit',hour12:false})}</td>
                          <td className={`py-0.5 text-right font-mono font-bold ${(o.total_score||0) >= 70 ? 'text-emerald-400' : (o.total_score||0) >= 50 ? 'text-amber-400' : 'text-zinc-400'}`}>{o.total_score}</td>
                          <td className="py-0.5 text-right font-mono text-gray-400">{o.vegas_score}</td>
                          <td className="py-0.5 text-right font-mono text-gray-400">{o.tpo_score}</td>
                          <td className="py-0.5 text-right font-mono text-gray-400">{o.fvg_score}</td>
                          <td className="py-0.5 text-right font-mono text-gray-400">{o.footprint_score}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </div>
        </div>
        );
      })()}

      {/* Compare Modal */}
      {showCompare && compareIds.size >= 2 && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={() => setShowCompare(false)}>
          <div className="bg-gray-900 border border-gray-700 rounded-lg max-w-4xl w-full max-h-[80vh] overflow-y-auto p-4" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-3">
              <h3 className="font-bold text-sm">Compare Trades</h3>
              <button onClick={() => setShowCompare(false)} className="text-gray-500 hover:text-white text-lg">\u00D7</button>
            </div>
            <CompareTable trades={trades.filter(t => compareIds.has(t.id))} />
          </div>
        </div>
      )}
    </div>
  );
}

// ── Sub-Components ───────────────────────────────────────────────────────────

function DetailRow({ label, value, highlight }: { label: string; value?: string; highlight?: number }) {
  const color = highlight !== undefined
    ? highlight > 0 ? 'text-green-400' : highlight < 0 ? 'text-red-400' : ''
    : '';
  return (
    <>
      <div className="text-gray-500">{label}</div>
      <div className={`font-mono ${color}`}>{value || '-'}</div>
    </>
  );
}

function NarrativeDisplay({ narrative }: { narrative: any }) {
  if (!narrative) return null;
  const p1 = narrative.pillar_1 || {};
  const p2 = narrative.pillar_2 || {};
  const p3 = narrative.pillar_3 || {};
  const score = narrative.score || {};
  const GradeBadge = ({ g }: { g?: string }) => {
    if (!g) return null;
    const color = g === 'A+' ? 'text-yellow-400' : g === 'A' ? 'text-green-400' : g === 'B' ? 'text-blue-400' : 'text-gray-500';
    return <span className={`font-bold ${color}`}>{g}</span>;
  };
  return (
    <div className="mt-4 border-t border-gray-800 pt-3">
      <h4 className="text-xs font-bold text-gray-400 mb-2">Entry Narrative</h4>
      {narrative.trigger_summary && (
        <div className="text-xs text-gray-300 mb-2">{narrative.trigger_summary}</div>
      )}
      <div className="grid grid-cols-3 gap-2 text-[10px]">
        <div className="bg-gray-800/50 rounded p-1.5">
          <div className="text-gray-500">P1 ZONE</div>
          <div>{p1.type} @ {p1.level}</div>
          <div>Wick: {p1.wick_pts?.toFixed(1)}pt <GradeBadge g={p1.wick_grade} /></div>
          <div>{p1.depth_rating}</div>
        </div>
        <div className="bg-gray-800/50 rounded p-1.5">
          <div className="text-gray-500">P2 PATTERN</div>
          <div>FVG: {p2.fvg?.size_pts?.toFixed(1)}pt <GradeBadge g={p2.fvg?.size_grade} /></div>
          <div>RelVol: {p2.rel_vol?.value?.toFixed(2)} <GradeBadge g={p2.rel_vol?.grade} /></div>
          <div>Stacked: {p2.stacked?.count} <GradeBadge g={p2.stacked?.count_grade} /></div>
        </div>
        <div className="bg-gray-800/50 rounded p-1.5">
          <div className="text-gray-500">P3 FLOW</div>
          <div>Absorption: {p3.absorption_at_fvg ? 'Yes' : 'No'}</div>
          <div>Delta 1m: {p3.delta_confirmation_1m ? 'Yes' : 'No'}</div>
        </div>
      </div>
      {(narrative.confluence_factors?.length > 0 || narrative.risk_factors?.length > 0) && (
        <div className="mt-2 text-[10px]">
          {narrative.confluence_factors?.map((c: string, i: number) => (
            <div key={i} className="text-green-400/70">+ {c}</div>
          ))}
          {narrative.risk_factors?.map((r: string, i: number) => (
            <div key={i} className="text-red-400/70">- {r}</div>
          ))}
        </div>
      )}
      {score.bonuses && (
        <div className="mt-2 text-[10px] text-gray-500">
          Score: {score.base} base {score.bonuses.map((b: any) => `+${b.points}`).join('')}
          {score.penalties?.map((p: any) => `${p.points}`).join('')} = {score.final}/10
        </div>
      )}
    </div>
  );
}

const CHART_COLORS = ['#22c55e', '#ef5350', '#3b82f6', '#f59e0b', '#8b5cf6', '#06b6d4'];

function JournalCharts({ trades }: { trades: Trade[] }) {
  // 1. PnL over time (cumulative line chart)
  const pnlData = useMemo(() => {
    const sorted = [...trades].sort((a, b) => (a.entry_ts || 0) - (b.entry_ts || 0));
    let cum = 0;
    return sorted.map((t, i) => {
      cum += t.pnl_pts || 0;
      return {
        idx: i + 1,
        date: tsToDate(t.entry_ts || 0),
        pnl: round2(t.pnl_pts || 0),
        cumPnl: round2(cum),
      };
    });
  }, [trades]);

  // 2. Win Rate by Day Type (bar chart)
  const wrByDay = useMemo(() => {
    const groups: Record<string, { total: number; wins: number }> = {};
    for (const t of trades) {
      const dt = t.day_type || 'UNKNOWN';
      if (!groups[dt]) groups[dt] = { total: 0, wins: 0 };
      groups[dt].total++;
      if ((t.pnl_pts || 0) > 0) groups[dt].wins++;
    }
    return Object.entries(groups).map(([name, v]) => ({
      name,
      wr: v.total > 0 ? Math.round(v.wins / v.total * 100) : 0,
      count: v.total,
    }));
  }, [trades]);

  // 3. MAE vs MFE scatter
  const scatterData = useMemo(() => {
    return trades.map(t => ({
      mae: round2(t.mae_pts || 0),
      mfe: round2(t.mfe_pts || 0),
      win: (t.pnl_pts || 0) > 0,
    }));
  }, [trades]);

  // 4. Exit type breakdown (pie chart)
  const exitData = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const t of trades) {
      const reason = t.close_reason || 'UNKNOWN';
      counts[reason] = (counts[reason] || 0) + 1;
    }
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [trades]);

  if (trades.length < 2) return null;

  return (
    <div className="mt-6">
      <h3 className="text-sm font-bold text-gray-400 mb-3">Analytics Charts</h3>
      <div className="grid grid-cols-2 gap-4">
        {/* PnL over time */}
        <div className="bg-gray-900 border border-gray-800 rounded p-3">
          <div className="text-[10px] text-gray-500 mb-2">Cumulative PnL (pts)</div>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={pnlData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2738" />
              <XAxis dataKey="idx" tick={{ fontSize: 9, fill: '#6b7280' }} />
              <YAxis tick={{ fontSize: 9, fill: '#6b7280' }} />
              <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid #333', fontSize: 11 }} />
              <Line type="monotone" dataKey="cumPnl" stroke="#3b82f6" strokeWidth={2} dot={false} name="Cum PnL" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Win Rate by Day Type */}
        <div className="bg-gray-900 border border-gray-800 rounded p-3">
          <div className="text-[10px] text-gray-500 mb-2">Win Rate by Day Type</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={wrByDay}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2738" />
              <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#6b7280' }} />
              <YAxis tick={{ fontSize: 9, fill: '#6b7280' }} domain={[0, 100]} />
              <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid #333', fontSize: 11 }} />
              <Bar dataKey="wr" fill="#22c55e" name="WR%">
                {wrByDay.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* MAE vs MFE scatter */}
        <div className="bg-gray-900 border border-gray-800 rounded p-3">
          <div className="text-[10px] text-gray-500 mb-2">MAE vs MFE (pts)</div>
          <ResponsiveContainer width="100%" height={180}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2738" />
              <XAxis dataKey="mae" name="MAE" tick={{ fontSize: 9, fill: '#6b7280' }} />
              <YAxis dataKey="mfe" name="MFE" tick={{ fontSize: 9, fill: '#6b7280' }} />
              <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid #333', fontSize: 11 }}
                formatter={(val: any, name: any) => [`${val}pt`, name]} />
              <Scatter data={scatterData.filter(d => d.win)} fill="#22c55e" name="Winners" />
              <Scatter data={scatterData.filter(d => !d.win)} fill="#ef5350" name="Losers" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        {/* Exit type breakdown */}
        <div className="bg-gray-900 border border-gray-800 rounded p-3">
          <div className="text-[10px] text-gray-500 mb-2">Exit Type Breakdown</div>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={exitData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={60} label={({ name, percent }: any) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                labelLine={{ stroke: '#4a5568' }}
                fontSize={9}>
                {exitData.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid #333', fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function round2(v: number): number {
  return Math.round(v * 100) / 100;
}

function CompareTable({ trades }: { trades: Trade[] }) {
  const allTags = [
    'id', 'direction', 'entry_price', 'exit_price', 'stop', 'risk_pts',
    'pnl_pts', 'pnl_usd', 'mae_pts', 'mfe_pts', 'duration_min',
    'setup_type', 'day_type', 'killzone', 'close_reason',
    'cb_respected', 'day_type_at_entry', 'killzone_at_entry',
    'minutes_into_session', 'cb_state_at_entry', 'news_state_at_entry',
    'day_pnl_before_entry', 'setup_number_today', 'rel_vol_at_entry',
    'cvd_direction_at_entry', 'mtf_aligned', 'vwap_side',
    'sweep_wick_pts_tag', 'fvg_size_pts', 'stacked_dominant_vol',
    'bars_building_before_live',
  ];

  return (
    <table className="w-full text-xs border-collapse">
      <thead>
        <tr className="border-b border-gray-800 text-gray-500">
          <th className="px-2 py-1 text-left">Field</th>
          {trades.map(t => (
            <th key={t.id} className="px-2 py-1 text-left">{t.id.slice(0, 12)}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {allTags.map(tag => (
          <tr key={tag} className="border-b border-gray-900">
            <td className="px-2 py-1 text-gray-500">{tag}</td>
            {trades.map(t => {
              const v = t[tag];
              const display = v === undefined || v === null ? '-'
                : typeof v === 'boolean' ? (v ? 'Yes' : 'No')
                : typeof v === 'number' ? (Number.isInteger(v) ? v.toString() : v.toFixed(2))
                : String(v);
              return <td key={t.id} className="px-2 py-1 font-mono">{display}</td>;
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
