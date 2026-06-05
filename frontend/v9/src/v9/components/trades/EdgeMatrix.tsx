'use client';
/**
 * EdgeMatrix — generic grouped aggregation, ADAPTED from PatternPerformanceStrip.
 *
 * Reuses the same aggregation math (win%, PF, expectancy, by-direction, scratch)
 * but generalizes the grouping key: system | pattern | day_type | killzone | direction.
 *
 * day_type + killzone are gated "pending G1" — shown greyed-out with label.
 * When G1 lands (day_type_at_entry / session_at_entry fields on Trade), remove the gating.
 */
import { useMemo, useState } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import { patternKey } from './PatternPerformanceStrip';
import type { Trade } from '../../types';

type Dim = 'system' | 'pattern' | 'day_type' | 'killzone' | 'direction';
const DIM_OPTIONS: { value: Dim; label: string; gated?: boolean }[] = [
  { value: 'pattern', label: 'Pattern' },
  { value: 'system', label: 'System' },
  { value: 'direction', label: 'Direction' },
  { value: 'day_type', label: 'Day Type', gated: true },
  { value: 'killzone', label: 'Killzone', gated: true },
];

const SYSTEM_NAMES: Record<number, string> = { 1: 'Day Type', 2: '5-Min', 3: 'Footprint', 4: 'Woodies', 5: 'TPO', 6: 'Killzone' };

function groupKey(t: Trade, dim: Dim): string {
  switch (dim) {
    case 'system': return `S${t.system}: ${SYSTEM_NAMES[t.system] ?? t.system}`;
    case 'pattern': return patternKey(t);
    case 'day_type': return t.day_type ?? '(unknown)';
    case 'killzone': return '(pending G1)'; // session_at_entry not yet on Trade type
    case 'direction': return t.direction || '(unknown)';
  }
}

type Direction = 'LONG' | 'SHORT';
interface DirAgg { total: number; wins: number; losses: number; net: number; }
interface GroupAgg {
  key: string;
  total: number;
  closed: number;
  wins: number;
  losses: number;
  scratch: number;
  netUsd: number;
  grossWin: number;
  grossLoss: number;
  byDir: Record<Direction, DirAgg>;
}

function emptyDir(): DirAgg { return { total: 0, wins: 0, losses: 0, net: 0 }; }

function aggregateByDim(trades: Trade[], dim: Dim): GroupAgg[] {
  const map = new Map<string, GroupAgg>();
  for (const t of trades) {
    const k = groupKey(t, dim);
    let row = map.get(k);
    if (!row) {
      row = { key: k, total: 0, closed: 0, wins: 0, losses: 0, scratch: 0, netUsd: 0, grossWin: 0, grossLoss: 0, byDir: { LONG: emptyDir(), SHORT: emptyDir() } };
      map.set(k, row);
    }
    row.total += 1;
    const isClosed = t.state === 'CLOSED' || (t.pnl_usd != null && t.outcome !== 'OPEN');
    if (isClosed) row.closed += 1;
    const pnl = t.pnl_usd ?? 0;
    const counted = t.pnl_usd != null;
    if (counted) {
      row.netUsd += pnl;
      if (pnl > 0) { row.wins += 1; row.grossWin += pnl; }
      else if (pnl < 0) { row.losses += 1; row.grossLoss += Math.abs(pnl); }
      else { row.scratch += 1; }
    }
    const dir = (t.direction === 'SHORT' ? 'SHORT' : 'LONG') as Direction;
    row.byDir[dir].total += 1;
    if (counted) {
      row.byDir[dir].net += pnl;
      if (pnl > 0) row.byDir[dir].wins += 1;
      else if (pnl < 0) row.byDir[dir].losses += 1;
    }
  }
  return Array.from(map.values()).sort((a, b) => b.total - a.total);
}

function winRate(w: number, l: number): number | null { const n = w + l; return n > 0 ? (w / n) * 100 : null; }
function pf(gw: number, gl: number): number | null { return gl <= 0 ? (gw > 0 ? Infinity : null) : gw / gl; }
function exp(net: number, closed: number): number | null { return closed > 0 ? net / closed : null; }
function fmtPct(p: number | null): string { return p == null ? '—' : `${p.toFixed(1)}%`; }
function fmtUsd(v: number): string { const s = v >= 0 ? '+' : '-'; return `${s}$${Math.abs(v).toFixed(2)}`; }
function fmtPF(v: number | null): string { return v == null ? '—' : !Number.isFinite(v) ? '∞' : v.toFixed(2); }
function wrColor(p: number | null): string {
  if (p == null) return 'var(--text-muted)';
  if (p >= 55) return 'var(--green)';
  if (p >= 45) return 'var(--text-primary)';
  return p >= 30 ? '#eab308' : 'var(--red)';
}
function pnlColor(v: number): string { return v > 0 ? 'var(--green)' : v < 0 ? 'var(--red)' : 'var(--text-secondary)'; }

export function EdgeMatrix() {
  const filteredTrades = useTradeStore((s) => s.filteredTrades);
  const allTrades = filteredTrades();
  const trades = useMemo(() => allTrades.filter((t) => !t.is_synthetic), [allTrades]);
  const [dim, setDim] = useState<Dim>('pattern');
  const [open, setOpen] = useState(false);
  const isGated = DIM_OPTIONS.find((d) => d.value === dim)?.gated;

  const rows = useMemo(() => aggregateByDim(trades, dim), [trades, dim]);

  if (trades.length === 0) {
    return (
      <div className="px-4 py-2 border-b shrink-0" style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}>
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Edge Matrix: no trades in filter</span>
      </div>
    );
  }

  return (
    <div className="border-b shrink-0" style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}>
      <div className="flex items-center justify-between px-4 py-2">
        <div className="flex items-center gap-3">
          <span className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
            Edge Matrix · {rows.length} groups · {trades.length} trades
          </span>
          <div className="flex items-center gap-1">
            {DIM_OPTIONS.map((d) => (
              <button
                key={d.value}
                onClick={() => setDim(d.value)}
                className="text-[10px] px-2 py-0.5 rounded"
                style={{
                  background: dim === d.value ? 'rgba(88,166,255,0.15)' : 'transparent',
                  color: d.gated ? 'var(--text-muted)' : dim === d.value ? 'var(--sys1)' : 'var(--text-secondary)',
                  border: `1px solid ${dim === d.value ? 'var(--sys1)' : 'var(--border)'}`,
                  opacity: d.gated ? 0.6 : 1,
                }}
              >
                {d.label}{d.gated ? ' (G1)' : ''}
              </button>
            ))}
          </div>
        </div>
        <button onClick={() => setOpen((o) => !o)} className="text-[10px] uppercase tracking-wide hover:underline" style={{ color: 'var(--text-secondary)' }}>
          {open ? '▾ Collapse' : '▸ Expand'}
        </button>
      </div>
      {open && (
        <div className="overflow-x-auto px-2 pb-2">
          {isGated && (
            <div className="text-[10px] px-2 py-1 mb-1 rounded" style={{ background: 'rgba(124,140,255,0.08)', color: 'var(--text-muted)' }}>
              pending G1 — {dim === 'day_type' ? 'day_type_at_entry' : 'session_at_entry'} not yet on Trade. Values shown are from trade.{dim === 'day_type' ? 'day_type' : '(missing)'} field (may not reflect entry-time state).
            </div>
          )}
          <table className="w-full text-xs font-mono border-collapse" style={{ minWidth: '800px' }}>
            <thead>
              <tr className="uppercase tracking-wide" style={{ color: 'var(--text-muted)', fontSize: '9px' }}>
                <th className="text-left px-2 py-1.5 font-medium">{dim}</th>
                <th className="text-right px-2 py-1.5 font-medium">Total</th>
                <th className="text-right px-2 py-1.5 font-medium">W</th>
                <th className="text-right px-2 py-1.5 font-medium">L</th>
                <th className="text-right px-2 py-1.5 font-medium">Scratch</th>
                <th className="text-right px-2 py-1.5 font-medium">Win%</th>
                <th className="text-right px-2 py-1.5 font-medium">Net $</th>
                <th className="text-right px-2 py-1.5 font-medium">Exp $</th>
                <th className="text-right px-2 py-1.5 font-medium">PF</th>
                <th className="text-left px-2 py-1.5 font-medium">LONG</th>
                <th className="text-left px-2 py-1.5 font-medium">SHORT</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const wr = winRate(r.wins, r.losses);
                const closedN = r.wins + r.losses + r.scratch;
                const ex = exp(r.netUsd, closedN);
                const pfv = pf(r.grossWin, r.grossLoss);
                const lWr = winRate(r.byDir.LONG.wins, r.byDir.LONG.losses);
                const sWr = winRate(r.byDir.SHORT.wins, r.byDir.SHORT.losses);
                return (
                  <tr key={r.key} className="border-b" style={{ borderColor: 'var(--border)', opacity: isGated ? 0.5 : 1 }}>
                    <td className="px-2 py-1 font-semibold" style={{ color: isGated ? 'var(--text-muted)' : 'var(--text-primary)' }}>{r.key}</td>
                    <td className="text-right px-2 py-1" style={{ color: 'var(--text-secondary)' }}>{r.total}</td>
                    <td className="text-right px-2 py-1" style={{ color: r.wins > 0 ? 'var(--green)' : 'var(--text-muted)' }}>{r.wins}</td>
                    <td className="text-right px-2 py-1" style={{ color: r.losses > 0 ? 'var(--red)' : 'var(--text-muted)' }}>{r.losses}</td>
                    <td className="text-right px-2 py-1" style={{ color: 'var(--text-muted)' }}>{r.scratch}</td>
                    <td className="text-right px-2 py-1 font-bold" style={{ color: wrColor(wr) }}>{fmtPct(wr)}</td>
                    <td className="text-right px-2 py-1 font-bold" style={{ color: pnlColor(r.netUsd) }}>{fmtUsd(r.netUsd)}</td>
                    <td className="text-right px-2 py-1" style={{ color: ex != null ? pnlColor(ex) : 'var(--text-muted)' }}>{ex != null ? fmtUsd(ex) : '—'}</td>
                    <td className="text-right px-2 py-1" style={{ color: 'var(--text-secondary)' }}>{fmtPF(pfv)}</td>
                    <td className="px-2 py-1" style={{ color: 'var(--text-secondary)' }}>
                      {r.byDir.LONG.total > 0 ? <>{r.byDir.LONG.total}: <span style={{ color: wrColor(lWr) }}>{fmtPct(lWr)}</span> <span style={{ color: pnlColor(r.byDir.LONG.net) }}>{fmtUsd(r.byDir.LONG.net)}</span></> : '—'}
                    </td>
                    <td className="px-2 py-1" style={{ color: 'var(--text-secondary)' }}>
                      {r.byDir.SHORT.total > 0 ? <>{r.byDir.SHORT.total}: <span style={{ color: wrColor(sWr) }}>{fmtPct(sWr)}</span> <span style={{ color: pnlColor(r.byDir.SHORT.net) }}>{fmtUsd(r.byDir.SHORT.net)}</span></> : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
