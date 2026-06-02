'use client';
import { useTradeStore } from '../../stores/tradeStore';
import { SYSTEM_NAMES } from '../../types';
import type { SystemId, TradeMode, TradeOutcome } from '../../types';

export function TradeFilters() {
  const { filters, setFilters } = useTradeStore();

  return (
    <div
      className="flex items-center gap-3 px-4 py-2 border-b flex-wrap"
      style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}
    >
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
      <div className="flex items-center gap-1">
        <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>From:</span>
        <input
          type="date"
          value={filters.dateFrom || ''}
          onChange={(e) => setFilters({ dateFrom: e.target.value || null })}
          className="text-xs px-1 py-0.5 rounded border"
          style={{ background: 'var(--bg-primary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}
        />
      </div>
      <div className="flex items-center gap-1">
        <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>To:</span>
        <input
          type="date"
          value={filters.dateTo || ''}
          onChange={(e) => setFilters({ dateTo: e.target.value || null })}
          className="text-xs px-1 py-0.5 rounded border"
          style={{ background: 'var(--bg-primary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}
        />
      </div>
      <input
        type="text"
        placeholder="Search pattern..."
        value={filters.pattern || ''}
        onChange={(e) => setFilters({ pattern: e.target.value || null })}
        className="text-xs px-2 py-1 rounded border"
        style={{ background: 'var(--bg-primary)', borderColor: 'var(--border)', color: 'var(--text-primary)', width: '140px' }}
      />
      <div className="basis-full mt-1" />
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
        title="Sequential gating: simulates LIVE (max 1 open trade). Eligible = would have fired. Skipped = blocked by an earlier open trade."
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
        title="systems_agreement at entry. Agree = no system opposes direction. Disagree = at least one system votes against."
        value={filters.confluence}
        options={[
          { value: 'all', label: 'Any confluence' },
          { value: 'agree', label: 'All systems agree' },
          { value: 'disagree', label: '≥1 system opposes' },
        ]}
        onChange={(v) => setFilters({ confluence: v as 'all' | 'agree' | 'disagree' })}
      />
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
      <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{label}:</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="text-xs px-1 py-0.5 rounded border appearance-none"
        style={{ background: 'var(--bg-primary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}
      >
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}
