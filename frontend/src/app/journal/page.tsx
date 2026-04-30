'use client';

import { Suspense, useEffect, useState, useMemo, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  LineChart, Line, BarChart, Bar, ScatterChart, Scatter,
  PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts';

const API_URL = 'https://mems26-web.onrender.com';

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

  // Data
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
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
      params.set('limit', '500');
      params.set('types', Array.from(tradeTypes).join(','));
      if (viewMode === 'executed') params.set('min_score', '70');
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

  const pagedTrades = filteredTrades.slice(0, (page + 1) * PAGE_SIZE);

  // ── KPIs ───────────────────────────────────────────────────────────────────

  const kpis = useMemo(() => {
    const t = filteredTrades.filter(t => t.status === 'CLOSED');
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
      avgMae: avgMae,
      avgMfe: avgMfe,
      shadowCount: shadows.length,
      liveCount: live.length,
    };
  }, [filteredTrades]);

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
                    <th className="px-1 py-1.5 text-left cursor-pointer" onClick={() => handleSort('day_type')}>Day{sortArrow('day_type')}</th>
                    <th className="px-1 py-1.5 text-left">KZ</th>
                    <th className="px-1 py-1.5 text-right cursor-pointer" onClick={() => handleSort('entry_price')}>Entry{sortArrow('entry_price')}</th>
                    <th className="px-1 py-1.5 text-right">Stop</th>
                    <th className="px-1 py-1.5 text-right">Risk</th>
                    <th className="px-1 py-1.5 text-right cursor-pointer" onClick={() => handleSort('exit_price')}>Exit{sortArrow('exit_price')}</th>
                    <th className="px-1 py-1.5 text-right cursor-pointer" onClick={() => handleSort('pnl_pts')}>PnL{sortArrow('pnl_pts')}</th>
                    <th className="px-1 py-1.5 text-right cursor-pointer" onClick={() => handleSort('mae_pts')}>MAE{sortArrow('mae_pts')}</th>
                    <th className="px-1 py-1.5 text-right cursor-pointer" onClick={() => handleSort('mfe_pts')}>MFE{sortArrow('mfe_pts')}</th>
                    <th className="px-1 py-1.5 text-right cursor-pointer" onClick={() => handleSort('duration_min')}>Dur{sortArrow('duration_min')}</th>
                    <th className="px-1 py-1.5 text-center cursor-pointer" onClick={() => handleSort('setup_quality_score')}>Q{sortArrow('setup_quality_score')}</th>
                    <th className="px-1 py-1.5 text-center">Path</th>
                    <th className="px-1 py-1.5 text-center">Obs</th>
                    <th className="px-1 py-1.5 text-left">Type</th>
                    <th className="px-1 py-1.5 text-center">Result</th>
                    <th className="px-1 py-1.5 text-left">Reasoning</th>
                  </tr>
                </thead>
                <tbody>
                  {pagedTrades.map(t => {
                    const pnl = t.pnl_pts || 0;
                    const isAttempt = t.source === 'attempt';
                    const bgClass = isAttempt ? 'bg-purple-950/10' : t.status !== 'CLOSED' ? '' : pnl > 0 ? 'bg-green-950/30' : pnl < 0 ? 'bg-red-950/30' : '';
                    return (
                      <tr key={`${t.source}_${t.id}`} className={`border-b border-gray-900 hover:bg-gray-800/50 cursor-pointer ${bgClass}`}
                        onClick={() => setSelectedTrade(t)}>
                        <td className="px-1 py-1" onClick={e => e.stopPropagation()}>
                          <input type="checkbox" checked={compareIds.has(t.id)}
                            onChange={() => {
                              const next = new Set(compareIds);
                              if (next.has(t.id)) next.delete(t.id);
                              else if (next.size < 3) next.add(t.id);
                              setCompareIds(next);
                            }}
                            className="accent-blue-500" />
                        </td>
                        <td className="px-1 py-1">
                          {isAttempt
                            ? <span className="bg-purple-900/50 text-purple-300 px-1 rounded text-[9px]">Shadow</span>
                            : <span className="bg-cyan-900/50 text-cyan-300 px-1 rounded text-[9px]">Trade</span>}
                        </td>
                        <td className="px-1 py-1 whitespace-nowrap">{tsToDate(t.entry_ts || 0)}</td>
                        <td className="px-1 py-1 whitespace-nowrap">{tsToTime(t.entry_ts || 0)}</td>
                        <td className={`px-1 py-1 font-bold ${t.direction === 'LONG' ? 'text-green-400' : 'text-red-400'}`}>
                          {t.direction}
                        </td>
                        <td className="px-1 py-1">{t.setup_type}</td>
                        <td className="px-1 py-1">{t.day_type}</td>
                        <td className="px-1 py-1">{t.killzone}</td>
                        <td className="px-1 py-1 text-right font-mono">{(t.entry_price || 0).toFixed(2)}</td>
                        <td className="px-1 py-1 text-right font-mono">{(t.stop || 0).toFixed(2)}</td>
                        <td className="px-1 py-1 text-right font-mono">{(t.risk_pts || 0).toFixed(1)}</td>
                        <td className="px-1 py-1 text-right font-mono">{t.exit_price ? t.exit_price.toFixed(2) : '-'}</td>
                        <td className={`px-1 py-1 text-right font-mono font-bold ${pnl > 0 ? 'text-green-400' : pnl < 0 ? 'text-red-400' : ''}`}>
                          {fmtPts(pnl)}
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
                        <td className="px-1 py-1 text-center text-[10px]">{
                          t.close_reason?.includes('T3') ? <span className="text-emerald-400 font-bold">T3</span>
                          : t.close_reason?.includes('T2') ? <span className="text-green-400">T2</span>
                          : t.close_reason?.includes('T1') ? <span className="text-green-300">T1</span>
                          : t.close_reason === 'STOP' ? <span className="text-red-400">STOP</span>
                          : t.close_reason?.includes('EOD') ? <span className="text-yellow-400">EOD</span>
                          : t.status === 'EXECUTED' ? <span className="text-blue-400">EXEC</span>
                          : t.status === 'CLOSED' ? <span className="text-gray-400">DONE</span>
                          : <span className="text-gray-600">-</span>
                        }</td>
                        <td className="px-1 py-1 text-[9px] text-gray-500 max-w-[200px] truncate" title={t.score_reasons || ''}>
                          {t.score_reasons ? t.score_reasons.split(' | ').slice(0, 2).join(' | ') : '-'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {/* Pagination */}
              {filteredTrades.length > (page + 1) * PAGE_SIZE && (
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
      {selectedTrade && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={() => setSelectedTrade(null)}>
          <div className="bg-gray-900 border border-gray-700 rounded-lg max-w-lg w-full max-h-[80vh] overflow-y-auto p-4" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-3">
              <h3 className="font-bold text-sm">
                {selectedTrade.is_shadow ? '\uD83D\uDC41\uFE0F Shadow' : '\uD83D\uDCBC Live'} Trade Detail
              </h3>
              <button onClick={() => setSelectedTrade(null)} className="text-gray-500 hover:text-white text-lg">\u00D7</button>
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              <DetailRow label="ID" value={selectedTrade.id} />
              <DetailRow label="Direction" value={selectedTrade.direction} />
              <DetailRow label="Entry" value={selectedTrade.entry_price?.toFixed(2)} />
              <DetailRow label="Exit" value={selectedTrade.exit_price?.toFixed(2) || '-'} />
              <DetailRow label="Stop" value={selectedTrade.stop?.toFixed(2)} />
              <DetailRow label="Risk" value={`${selectedTrade.risk_pts?.toFixed(1)}pt`} />
              <DetailRow label="PnL" value={fmtPts(selectedTrade.pnl_pts)} highlight={selectedTrade.pnl_pts} />
              <DetailRow label="PnL $" value={fmtUsd(selectedTrade.pnl_usd)} highlight={selectedTrade.pnl_usd} />
              <DetailRow label="MAE" value={`${(selectedTrade.mae_pts || 0).toFixed(1)}pt`} />
              <DetailRow label="MFE" value={`${(selectedTrade.mfe_pts || 0).toFixed(1)}pt`} />
              <DetailRow label="Duration" value={`${(selectedTrade.duration_min || 0).toFixed(0)}min`} />
              <DetailRow label="Close Reason" value={selectedTrade.close_reason} />
              <DetailRow label="Setup" value={selectedTrade.setup_type} />
              <DetailRow label="Day Type" value={selectedTrade.day_type} />
              <DetailRow label="Killzone" value={selectedTrade.killzone} />
              <DetailRow label="CB Respected" value={selectedTrade.cb_respected ? 'Yes' : 'No'} />
            </div>
            {/* 15 Strategic Tags */}
            <h4 className="text-xs font-bold text-gray-400 mt-4 mb-2">Strategic Tags</h4>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              <DetailRow label="Day Type @ Entry" value={selectedTrade.day_type_at_entry} />
              <DetailRow label="Killzone @ Entry" value={selectedTrade.killzone_at_entry} />
              <DetailRow label="Min Into Session" value={selectedTrade.minutes_into_session?.toString()} />
              <DetailRow label="CB State" value={selectedTrade.cb_state_at_entry} />
              <DetailRow label="News State" value={selectedTrade.news_state_at_entry} />
              <DetailRow label="Day PnL Before" value={selectedTrade.day_pnl_before_entry ? `$${selectedTrade.day_pnl_before_entry.toFixed(0)}` : '-'} />
              <DetailRow label="Setup # Today" value={selectedTrade.setup_number_today?.toString()} />
              <DetailRow label="RelVol" value={selectedTrade.rel_vol_at_entry?.toFixed(2)} />
              <DetailRow label="CVD Direction" value={selectedTrade.cvd_direction_at_entry} />
              <DetailRow label="MTF Aligned" value={selectedTrade.mtf_aligned ? 'Yes' : 'No'} />
              <DetailRow label="VWAP Side" value={selectedTrade.vwap_side} />
              <DetailRow label="Sweep Wick" value={selectedTrade.sweep_wick_pts_tag ? `${selectedTrade.sweep_wick_pts_tag.toFixed(1)}pt` : '-'} />
              <DetailRow label="FVG Size" value={selectedTrade.fvg_size_pts ? `${selectedTrade.fvg_size_pts.toFixed(1)}pt` : '-'} />
              <DetailRow label="Stacked Vol" value={selectedTrade.stacked_dominant_vol ? 'Yes' : 'No'} />
              <DetailRow label="Bars Building" value={selectedTrade.bars_building_before_live?.toString()} />
            </div>
            <DetailRow label="Pillar Detail" value={selectedTrade.pillar_detail} />
            {/* Component Scores */}
            {(selectedTrade.vegas_score != null || selectedTrade.tpo_score != null) && (
              <div className="mt-3 border-t border-gray-800 pt-2">
                <h4 className="text-xs font-bold text-gray-400 mb-1">Component Scores</h4>
                <div className="grid grid-cols-4 gap-1 text-[10px]">
                  {[
                    { label: 'Vegas', val: selectedTrade.vegas_score, max: 30 },
                    { label: 'TPO', val: selectedTrade.tpo_score, max: 25 },
                    { label: 'FVG', val: selectedTrade.fvg_score, max: 25 },
                    { label: 'FP', val: selectedTrade.footprint_score, max: 20 },
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
            {/* Score Reasoning */}
            {selectedTrade.score_reasons && (
              <div className="mt-3 border-t border-gray-800 pt-2">
                <h4 className="text-xs font-bold text-gray-400 mb-1">Score Reasoning</h4>
                <div className="space-y-0.5">
                  {selectedTrade.score_reasons.split(' | ').map((r: string, i: number) => {
                    const hasPlus = /\(\+\d+\)/.test(r);
                    const opposes = /OPPOSES|no.*data|too narrow/i.test(r);
                    const color = hasPlus ? 'text-green-400' : opposes ? 'text-red-400' : 'text-amber-400';
                    const icon = hasPlus ? '\u2713' : opposes ? '\u2717' : '\u26A0';
                    return <div key={i} className={`text-[10px] ${color}`}>{icon} {r}</div>;
                  })}
                </div>
                {selectedTrade.setup_type && (
                  <div className="mt-1 text-[10px] text-gray-500">Type: {selectedTrade.setup_type}
                    {selectedTrade.peak_score ? ` | Peak: ${selectedTrade.peak_score}` : ''}
                    {selectedTrade.observation_count ? ` | Obs: ${selectedTrade.observation_count}` : ''}</div>
                )}
              </div>
            )}
            {/* Strategic Tags — show what's collected vs null */}
            <div className="mt-3 border-t border-gray-800 pt-2">
              <h4 className="text-xs font-bold text-gray-400 mb-1">Strategic Tags</h4>
              <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[10px]">
                {[
                  { label: 'RelVol', val: selectedTrade.rel_vol_at_entry, fmt: (v: any) => v?.toFixed(2) },
                  { label: 'CVD Dir', val: selectedTrade.cvd_direction_at_entry },
                  { label: 'MTF Aligned', val: selectedTrade.mtf_aligned, fmt: (v: any) => v ? 'Yes' : 'No' },
                  { label: 'VWAP Side', val: selectedTrade.vwap_side },
                  { label: 'Killzone', val: selectedTrade.killzone },
                  { label: 'Day Type', val: selectedTrade.day_type },
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
            {/* V6.5: Entry Narrative */}
            {selectedTrade.entry_narrative && (
              <NarrativeDisplay narrative={selectedTrade.entry_narrative} />
            )}
            {selectedTrade.setup_quality_score !== undefined && (
              <div className="mt-3 flex items-center gap-2">
                <span className="text-gray-500 text-xs">Quality Score:</span>
                <span className={`font-bold text-sm ${
                  selectedTrade.setup_quality_score >= 9 ? 'text-yellow-400' :
                  selectedTrade.setup_quality_score >= 7 ? 'text-green-400' :
                  selectedTrade.setup_quality_score >= 5 ? 'text-blue-400' : 'text-gray-500'
                }`}>
                  {selectedTrade.setup_quality_score}/10
                  {selectedTrade.entry_narrative?.score?.rating && ` ${selectedTrade.entry_narrative.score.rating}`}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

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
