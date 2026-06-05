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

const barStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 12,
  flexWrap: 'wrap',
  padding: '9px 14px',
  marginTop: 9,
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border)',
  borderRadius: 8,
  fontFamily: 'var(--mono)',
  fontSize: 12,
};

const labStyle: React.CSSProperties = {
  color: 'var(--text-muted)',
  fontSize: 10,
  textTransform: 'uppercase',
  letterSpacing: 0.5,
};

const selectStyle: React.CSSProperties = {
  background: 'var(--bg-primary)',
  color: 'var(--text-primary)',
  border: '1px solid var(--border)',
  borderRadius: 6,
  fontFamily: 'var(--mono)',
  fontSize: 11,
  padding: '3px 8px',
  cursor: 'pointer',
};

const inputStyle: React.CSSProperties = {
  background: 'var(--bg-primary)',
  color: 'var(--text-primary)',
  border: '1px solid var(--border)',
  borderRadius: 6,
  fontSize: 11,
  padding: '3px 8px',
  width: 140,
};

const sepStyle: React.CSSProperties = {
  width: 1,
  height: 16,
  background: 'var(--border)',
};

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
    <>
      {/* Primary filter bar */}
      <div style={barStyle}>
        <span style={labStyle}>Mode</span>
        <select
          value={filters.mode}
          onChange={(e) => setFilters({ mode: e.target.value as TradeMode | 'ALL' })}
          style={selectStyle}
        >
          <option value="ALL">All Modes</option>
          <option value="SHADOW">Shadow</option>
          <option value="SIM">Sim</option>
          <option value="LIVE">Live</option>
        </select>

        <span style={labStyle}>System</span>
        <select
          value={String(filters.systemId)}
          onChange={(e) => setFilters({ systemId: e.target.value === 'ALL' ? 'ALL' : (parseInt(e.target.value) as SystemId) })}
          style={selectStyle}
        >
          <option value="ALL">All Systems</option>
          {([1, 2, 3, 4, 5, 6] as SystemId[]).map((id) => (
            <option key={id} value={String(id)}>S{id}: {SYSTEM_NAMES[id]}</option>
          ))}
        </select>

        <span style={labStyle}>Direction</span>
        <select
          value={filters.direction || 'ALL'}
          onChange={(e) => setFilters({ direction: e.target.value === 'ALL' ? null : e.target.value })}
          style={selectStyle}
        >
          <option value="ALL">All</option>
          <option value="LONG">Long</option>
          <option value="SHORT">Short</option>
        </select>

        <span style={labStyle}>Stop</span>
        <select
          value={filters.stopMove}
          onChange={(e) => setFilters({ stopMove: e.target.value as 'all' | 'moved' | 'static' })}
          style={selectStyle}
        >
          <option value="all">Any stop</option>
          <option value="moved">Moved to BE</option>
          <option value="static">Static (-1R)</option>
        </select>

        <div style={sepStyle} />

        <span style={labStyle}>Quick</span>
        {datePresets().map((p) => {
          const isActive = filters.dateFrom === p.from && filters.dateTo === p.to;
          return (
            <button
              key={p.label}
              onClick={() => setFilters(isActive ? { dateFrom: null, dateTo: null } : { dateFrom: p.from, dateTo: p.to })}
              style={{
                fontFamily: 'var(--mono)',
                fontSize: 10.5,
                padding: '3px 9px',
                borderRadius: 6,
                background: isActive ? 'rgba(88,166,255,0.12)' : 'var(--bg-tertiary)',
                color: isActive ? 'var(--sys1)' : 'var(--text-secondary)',
                border: `1px solid ${isActive ? 'var(--sys1)' : 'var(--border)'}`,
                cursor: 'pointer',
                fontWeight: isActive ? 600 : 400,
              }}
            >
              {p.label}
            </button>
          );
        })}
        {(filters.dateFrom || filters.dateTo) && (
          <button
            onClick={() => setFilters({ dateFrom: null, dateTo: null })}
            style={{ color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 10 }}
            title="Clear date filter"
          >
            ✕
          </button>
        )}

        <div style={sepStyle} />

        <input
          type="text"
          placeholder="Search pattern..."
          value={filters.pattern || ''}
          onChange={(e) => setFilters({ pattern: e.target.value || null })}
          style={inputStyle}
        />

        <span style={{ flex: 1 }} />

        <button
          onClick={() => setShowMore((s) => !s)}
          style={{
            fontFamily: 'var(--mono)',
            fontSize: 10.5,
            padding: '3px 9px',
            borderRadius: 6,
            color: showMore || advActive ? 'var(--sys1)' : 'var(--text-secondary)',
            border: `1px solid ${showMore || advActive ? 'var(--sys1)' : 'var(--border)'}`,
            background: advActive ? 'rgba(88,166,255,0.12)' : 'var(--bg-tertiary)',
            cursor: 'pointer',
          }}
        >
          {showMore ? '▴ Less' : '▾ More'}{advActive ? ` (${advActive})` : ''}
        </button>
      </div>

      {/* Advanced filters row */}
      {showMore && (
        <div style={{ ...barStyle, marginTop: 0, borderTop: 'none', borderRadius: '0 0 8px 8px' }}>
          <span style={labStyle}>Outcome</span>
          <select
            value={filters.outcome}
            onChange={(e) => setFilters({ outcome: e.target.value as TradeOutcome | 'ALL' })}
            style={selectStyle}
          >
            <option value="ALL">All</option>
            <option value="WIN">Win</option>
            <option value="LOSS">Loss</option>
            <option value="BE">Breakeven</option>
            <option value="SCRATCH">Scratch</option>
            <option value="OPEN">Open</option>
          </select>

          <span style={labStyle}>From</span>
          <input
            type="date"
            value={filters.dateFrom || ''}
            onChange={(e) => setFilters({ dateFrom: e.target.value || null })}
            style={{ ...inputStyle, width: 120 }}
          />
          <span style={labStyle}>To</span>
          <input
            type="date"
            value={filters.dateTo || ''}
            onChange={(e) => setFilters({ dateTo: e.target.value || null })}
            style={{ ...inputStyle, width: 120 }}
          />

          <span style={labStyle}>Overlap</span>
          <select
            value={filters.overlap}
            onChange={(e) => setFilters({ overlap: e.target.value as 'all' | 'parallel' | 'sequential' })}
            style={selectStyle}
          >
            <option value="all">All trades</option>
            <option value="parallel">Parallel only</option>
            <option value="sequential">Sequential only</option>
          </select>

          <span style={labStyle}>LIVE-eligible</span>
          <select
            value={filters.liveGated}
            onChange={(e) => setFilters({ liveGated: e.target.value as 'all' | 'eligible' | 'skipped' })}
            style={selectStyle}
          >
            <option value="all">All (no gating)</option>
            <option value="eligible">LIVE-eligible only</option>
            <option value="skipped">Skipped by LIVE-gate</option>
          </select>

          <span style={labStyle}>Confluence</span>
          <select
            value={filters.confluence}
            onChange={(e) => setFilters({ confluence: e.target.value as 'all' | 'agree' | 'disagree' })}
            style={selectStyle}
          >
            <option value="all">Any confluence</option>
            <option value="agree">All systems agree</option>
            <option value="disagree">1+ system opposes</option>
          </select>

          <span style={labStyle}>Sort</span>
          <select
            value={filters.sort}
            onChange={(e) => setFilters({ sort: e.target.value as 'new' | 'old' | 'pnl_dn' | 'pnl_up' | 'dur_dn' | 'rr_dn' })}
            style={selectStyle}
          >
            <option value="new">Newest first</option>
            <option value="old">Oldest first</option>
            <option value="pnl_dn">P&amp;L high to low</option>
            <option value="pnl_up">P&amp;L low to high</option>
            <option value="dur_dn">Duration long to short</option>
            <option value="rr_dn">R:R high to low</option>
          </select>
        </div>
      )}
    </>
  );
}
