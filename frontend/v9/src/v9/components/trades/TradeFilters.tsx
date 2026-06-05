'use client';
import { useState, useMemo } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import { SYSTEM_NAMES } from '../../types';
import type { SystemId, TradeMode, TradeOutcome } from '../../types';

/** ET-aware date string (YYYY-MM-DD) for "today" in America/New_York. */
const _etFmt = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' });
function etToday(): string { return _etFmt.format(new Date()); }
function etYesterday(): string {
  const d = new Date(); d.setDate(d.getDate() - 1); return _etFmt.format(d);
}
function etDaysAgo(n: number): string {
  const d = new Date(); d.setDate(d.getDate() - n); return _etFmt.format(d);
}
function etMonthStart(): string {
  const t = etToday();
  return t.slice(0, 8) + '01';
}

type DatePreset = { label: string; from: string; to: string };
function datePresets(): DatePreset[] {
  const today = etToday();
  return [
    { label: 'Today (RTH)', from: today, to: today },
    { label: 'Yesterday', from: etYesterday(), to: etYesterday() },
    { label: '7d', from: etDaysAgo(7), to: today },
    { label: '30d', from: etDaysAgo(30), to: today },
    { label: 'MTD', from: etMonthStart(), to: today },
  ];
}

export function TradeFilters() {
  const { filters, setFilters } = useTradeStore();
  const [showMore, setShowMore] = useState(false);

  // count active advanced filters so the user knows something is hidden
  const advActive =
    (filters.outcome !== 'ALL' ? 1 : 0) +
    (filters.dateFrom ? 1 : 0) +
    (filters.dateTo ? 1 : 0) +
    (filters.overlap !== 'all' ? 1 : 0) +
    (filters.liveGated !== 'all' ? 1 : 0) +
    (filters.confluence !== 'all' ? 1 : 0);

  return (
    <div
      className="px-4 py-1.5 border-b"
      style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}
    >
      {/* Primary row — always visible */}
      <div className="flex items-center gap-x-3 gap-y-1.5 flex-wrap">
        <FilterSelect
          label="Mode"
          value={filters.mode}
          options={[
            { value: 'ALL', label: 'All Modes' },
            { value: 'SHADOW', label: 'Shadow' },
            { value: 'SIM', label: 'Sim' },
            { value: 'LIVE', label: 'Live' },
          ]}
          onChange={(v) => setFilters({ mode: v as TradeMode | 'ALL' })}
        />
        <FilterSelect
          label="System"
          value={String(filters.systemId)}
          options={[
            { value: 'ALL', label: 'All Systems' },
            ...([1, 2, 3, 4, 5, 6] as SystemId[]).map((id) => ({
              value: String(id),
              label: `S${id}: ${SYSTEM_NAMES[id]}`,
            })),
          ]}
          onChange={(v) => setFilters({ systemId: v === 'ALL' ? 'ALL' : (parseInt(v) as SystemId) })}
        />
        <FilterSelect
          label="Direction"
          value={filters.direction || 'ALL'}
          options={[
            { value: 'ALL', label: 'All' },
            { value: 'LONG', label: 'Long' },
            { value: 'SHORT', label: 'Short' },
          ]}
          onChange={(v) => setFilters({ direction: v === 'ALL' ? null : v })}
        />
        <FilterSelect
          label="Stop"
          title="Did the stop move to breakeven (SMART_BE after T1) or stay at the initial stop?"
          value={filters.stopMove}
          options={[
            { value: 'all', label: 'Any stop' },
            { value: 'moved', label: 'Moved to BE' },
            { value: 'static', label: 'Static (−1R)' },
          ]}
          onChange={(v) => setFilters({ stopMove: v as 'all' | 'moved' | 'static' })}
        />
        <FilterSelect
          label="Sort"
          value={filters.sort}
          options={[
            { value: 'new', label: 'Newest → oldest' },
            { value: 'old', label: 'Oldest → newest' },
            { value: 'pnl_dn', label: 'P&L high → low' },
            { value: 'pnl_up', label: 'P&L low → high' },
            { value: 'dur_dn', label: 'Duration long → short' },
            { value: 'rr_dn', label: 'R:R high → low' },
          ]}
          onChange={(v) => setFilters({ sort: v as 'new' | 'old' | 'pnl_dn' | 'pnl_up' | 'dur_dn' | 'rr_dn' })}
        />
        <input
          type="text"
          placeholder="Search pattern..."
          value={filters.pattern || ''}
          onChange={(e) => setFilters({ pattern: e.target.value || null })}
          className="text-[11px] px-2 py-0.5 rounded border"
          style={{ background: 'var(--bg-primary)', borderColor: 'var(--border)', color: 'var(--text-primary)', width: '130px' }}
        />
        <span className="flex-1" />
        <button
          onClick={() => setShowMore((s) => !s)}
          className="text-[10px] px-2 py-0.5 rounded"
          style={{
            color: showMore || advActive ? 'var(--sys1)' : 'var(--text-secondary)',
            border: `1px solid ${showMore || advActive ? 'var(--sys1)' : 'var(--border)'}`,
            background: advActive ? 'rgba(88,166,255,0.10)' : 'transparent',
          }}
        >
          {showMore ? '▴ Less' : '▾ More'}{advActive ? ` (${advActive})` : ''}
        </button>
      </div>

      {/* Date presets — ET-aware */}
      <div className="flex items-center gap-1.5 mt-1.5">
        <span className="text-[9px] uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Date</span>
        {datePresets().map((p) => {
          const isActive = filters.dateFrom === p.from && filters.dateTo === p.to;
          return (
            <button
              key={p.label}
              onClick={() => setFilters(isActive ? { dateFrom: null, dateTo: null } : { dateFrom: p.from, dateTo: p.to })}
              className="text-[10px] px-2 py-0.5 rounded"
              style={{
                background: isActive ? 'rgba(88,166,255,0.15)' : 'transparent',
                color: isActive ? 'var(--sys1)' : 'var(--text-secondary)',
                border: `1px solid ${isActive ? 'var(--sys1)' : 'var(--border)'}`,
              }}
            >
              {p.label}
            </button>
          );
        })}
        {(filters.dateFrom || filters.dateTo) && (
          <button
            onClick={() => setFilters({ dateFrom: null, dateTo: null })}
            className="text-[10px] px-1"
            style={{ color: 'var(--text-muted)' }}
            title="Clear date filter"
          >
            ✕
          </button>
        )}
      </div>

      {/* Advanced row — collapsed by default */}
      {showMore && (
        <div className="flex items-center gap-x-3 gap-y-1.5 flex-wrap mt-2 pt-2 border-t" style={{ borderColor: 'var(--border)' }}>
          <FilterSelect
            label="Outcome"
            value={filters.outcome}
            options={[
              { value: 'ALL', label: 'All' },
              { value: 'WIN', label: 'Win' },
              { value: 'LOSS', label: 'Loss' },
              { value: 'BE', label: 'Breakeven' },
              { value: 'SCRATCH', label: 'Scratch' },
              { value: 'OPEN', label: 'Open' },
            ]}
            onChange={(v) => setFilters({ outcome: v as TradeOutcome | 'ALL' })}
          />
          <div className="flex items-center gap-1">
            <span className="text-[9px] uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>From</span>
            <input
              type="date"
              value={filters.dateFrom || ''}
              onChange={(e) => setFilters({ dateFrom: e.target.value || null })}
              className="text-[11px] px-1 py-0.5 rounded border"
              style={{ background: 'var(--bg-primary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}
            />
          </div>
          <div className="flex items-center gap-1">
            <span className="text-[9px] uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>To</span>
            <input
              type="date"
              value={filters.dateTo || ''}
              onChange={(e) => setFilters({ dateTo: e.target.value || null })}
              className="text-[11px] px-1 py-0.5 rounded border"
              style={{ background: 'var(--bg-primary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}
            />
          </div>
          <FilterSelect
            label="Overlap"
            title="Parallel = overlapped another trade in time. Sequential = ran alone."
            value={filters.overlap}
            options={[
              { value: 'all', label: 'All trades' },
              { value: 'parallel', label: 'Parallel only (overlapping)' },
              { value: 'sequential', label: 'Sequential only (no overlap)' },
            ]}
            onChange={(v) => setFilters({ overlap: v as 'all' | 'parallel' | 'sequential' })}
          />
          <FilterSelect
            label="LIVE-eligible"
            title="Sequential gating: simulates LIVE (max 1 open trade)."
            value={filters.liveGated}
            options={[
              { value: 'all', label: 'All (no gating)' },
              { value: 'eligible', label: 'LIVE-eligible only' },
              { value: 'skipped', label: 'Skipped by LIVE-gate' },
            ]}
            onChange={(v) => setFilters({ liveGated: v as 'all' | 'eligible' | 'skipped' })}
          />
          <FilterSelect
            label="Confluence"
            title="systems_agreement at entry."
            value={filters.confluence}
            options={[
              { value: 'all', label: 'Any confluence' },
              { value: 'agree', label: 'All systems agree' },
              { value: 'disagree', label: '≥1 system opposes' },
            ]}
            onChange={(v) => setFilters({ confluence: v as 'all' | 'agree' | 'disagree' })}
          />
        </div>
      )}
    </div>
  );
}

function FilterSelect({ label, title, value, options, onChange }: {
  label: string;
  title?: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center gap-1" title={title}>
      <span className="text-[9px] uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="text-[11px] px-1.5 py-0.5 rounded border appearance-none"
        style={{ background: 'var(--bg-primary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}
      >
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}
