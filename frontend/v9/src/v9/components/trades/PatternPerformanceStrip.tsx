'use client';
import { useMemo, useState } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import type { Trade } from '../../types';

type Direction = 'LONG' | 'SHORT';

interface DirAgg {
  total: number;
  wins: number;
  losses: number;
  net: number;
}

interface PatternAgg {
  pattern: string;
  total: number;
  closed: number;
  open: number;
  wins: number;
  losses: number;
  scratch: number;
  netUsd: number;
  grossWin: number;
  grossLoss: number;
  byDir: Record<Direction, DirAgg>;
}

/** Pattern label fallback chain: pattern_id → classification → trigger → "(none)". */
export function patternKey(t: Trade): string {
  const raw = t.pattern_id || t.classification || t.trigger || '';
  const v = String(raw).trim();
  if (!v || v === '-' || v === '—' || /^system_\d+$/i.test(v) || /^S\d+$/.test(v)) {
    return '(none)';
  }
  return v.toUpperCase();
}

function emptyDir(): DirAgg {
  return { total: 0, wins: 0, losses: 0, net: 0 };
}

function aggregateByPattern(trades: Trade[]): PatternAgg[] {
  const map = new Map<string, PatternAgg>();
  for (const t of trades) {
    const key = patternKey(t);
    let row = map.get(key);
    if (!row) {
      row = {
        pattern: key,
        total: 0,
        closed: 0,
        open: 0,
        wins: 0,
        losses: 0,
        scratch: 0,
        netUsd: 0,
        grossWin: 0,
        grossLoss: 0,
        byDir: { LONG: emptyDir(), SHORT: emptyDir() },
      };
      map.set(key, row);
    }
    row.total += 1;
    const isClosed =
      t.state === 'CLOSED' || (t.pnl_usd != null && t.outcome !== 'OPEN');
    if (isClosed) row.closed += 1;
    else row.open += 1;
    const pnl = t.pnl_usd ?? 0;
    const counted = t.pnl_usd != null;
    if (counted) {
      row.netUsd += pnl;
      if (pnl > 0) {
        row.wins += 1;
        row.grossWin += pnl;
      } else if (pnl < 0) {
        row.losses += 1;
        row.grossLoss += Math.abs(pnl);
      } else {
        row.scratch += 1;
      }
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

function winRatePct(wins: number, losses: number): number | null {
  const n = wins + losses;
  return n > 0 ? (wins / n) * 100 : null;
}

function profitFactor(grossWin: number, grossLoss: number): number | null {
  if (grossLoss <= 0) return grossWin > 0 ? Infinity : null;
  return grossWin / grossLoss;
}

function expectancy(netUsd: number, closed: number): number | null {
  return closed > 0 ? netUsd / closed : null;
}

function winRateColor(pct: number | null): string {
  if (pct == null) return 'var(--text-muted)';
  if (pct >= 55) return 'var(--green)';
  if (pct >= 45) return 'var(--text-primary)';
  if (pct >= 30) return '#eab308'; // amber
  return 'var(--red)';
}

function pnlColor(v: number): string {
  if (v > 0) return 'var(--green)';
  if (v < 0) return 'var(--red)';
  return 'var(--text-secondary)';
}

function fmtUsd(v: number, signed = true): string {
  const sign = v >= 0 ? (signed ? '+' : '') : '-';
  return `${sign}$${Math.abs(v).toFixed(2)}`;
}

function fmtPF(pf: number | null): string {
  if (pf == null) return '—';
  if (!Number.isFinite(pf)) return '∞';
  return pf.toFixed(2);
}

function fmtPct(p: number | null): string {
  return p == null ? '—' : `${p.toFixed(1)}%`;
}

export function PatternPerformanceStrip() {
  const filteredTrades = useTradeStore((s) => s.filteredTrades);
  const filters = useTradeStore((s) => s.filters);
  const setFilters = useTradeStore((s) => s.setFilters);
  const allTrades = filteredTrades();
  // Exclude synthetic from pattern performance aggregates
  const trades = useMemo(() => allTrades.filter((t) => !t.is_synthetic), [allTrades]);
  const [open, setOpen] = useState(false);

  const rows = useMemo(() => aggregateByPattern(trades), [trades]);

  const activePattern = (filters.pattern ?? '').trim().toUpperCase();

  if (rows.length === 0) {
    return (
      <div
        className="px-4 py-2 border-b shrink-0"
        style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}
      >
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
          By Pattern: no trades in filter
        </span>
      </div>
    );
  }

  return (
    <div
      className="border-b shrink-0"
      style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}
    >
      <div className="flex items-center justify-between px-4 py-2">
        <div className="flex items-center gap-3">
          <span className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
            By Pattern (filtered) · {rows.length} patterns · {trades.length} trades
          </span>
          {activePattern && (
            <button
              onClick={() => setFilters({ pattern: null })}
              className="text-[10px] px-2 py-0.5 rounded"
              style={{
                background: 'rgba(59,130,246,0.15)',
                color: 'var(--sys1)',
                border: '1px solid var(--sys1)',
              }}
              title="Clear pattern filter"
            >
              filter: {activePattern} ✕
            </button>
          )}
        </div>
        <button
          onClick={() => setOpen((o) => !o)}
          className="text-[10px] uppercase tracking-wide hover:underline"
          style={{ color: 'var(--text-secondary)' }}
        >
          {open ? '▾ Collapse' : '▸ Expand'}
        </button>
      </div>
      {open && (
        <div className="overflow-x-auto px-2 pb-2">
          <table
            className="w-full text-xs font-mono border-collapse"
            style={{ minWidth: '980px' }}
          >
            <thead>
              <tr
                className="uppercase tracking-wide"
                style={{ color: 'var(--text-muted)', fontSize: '9px' }}
              >
                <th className="text-left px-2 py-1.5 font-medium">Pattern</th>
                <th className="text-right px-2 py-1.5 font-medium" title="Total trades (open in parens)">Total</th>
                <th className="text-right px-2 py-1.5 font-medium">W</th>
                <th className="text-right px-2 py-1.5 font-medium">L</th>
                <th className="text-right px-2 py-1.5 font-medium">Win%</th>
                <th className="text-right px-2 py-1.5 font-medium">Net $</th>
                <th className="text-right px-2 py-1.5 font-medium" title="Average winner / loser in $">Avg W / L</th>
                <th className="text-right px-2 py-1.5 font-medium" title="Expectancy = Net $ / closed trades">Exp $</th>
                <th className="text-right px-2 py-1.5 font-medium" title="Profit Factor = gross wins / gross losses">PF</th>
                <th className="text-left px-2 py-1.5 font-medium" title="LONG side: count → W/L → Win% → Net $">LONG</th>
                <th className="text-left px-2 py-1.5 font-medium" title="SHORT side: count → W/L → Win% → Net $">SHORT</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const wr = winRatePct(r.wins, r.losses);
                const closedForExp = r.wins + r.losses + r.scratch;
                const exp = expectancy(r.netUsd, closedForExp);
                const pf = profitFactor(r.grossWin, r.grossLoss);
                const avgW = r.wins > 0 ? r.grossWin / r.wins : 0;
                const avgL = r.losses > 0 ? r.grossLoss / r.losses : 0;
                const longWr = winRatePct(r.byDir.LONG.wins, r.byDir.LONG.losses);
                const shortWr = winRatePct(r.byDir.SHORT.wins, r.byDir.SHORT.losses);
                const isActive = activePattern === r.pattern;
                return (
                  <tr
                    key={r.pattern}
                    className="border-b cursor-pointer hover:bg-[var(--bg-primary)]"
                    style={{
                      borderColor: 'var(--border)',
                      background: isActive ? 'rgba(59,130,246,0.08)' : undefined,
                    }}
                    onClick={() =>
                      setFilters({
                        pattern: isActive ? null : r.pattern,
                      })
                    }
                    title={isActive ? 'Click to clear' : `Filter table to ${r.pattern} only`}
                  >
                    <td className="px-2 py-1 font-semibold" style={{ color: 'var(--text-primary)' }}>
                      {r.pattern}
                    </td>
                    <td className="text-right px-2 py-1" style={{ color: 'var(--text-secondary)' }}>
                      {r.total}
                      {r.open > 0 && (
                        <span className="ml-1 text-[10px]" style={{ color: 'var(--text-muted)' }}>
                          ({r.open})
                        </span>
                      )}
                    </td>
                    <td className="text-right px-2 py-1" style={{ color: r.wins > 0 ? 'var(--green)' : 'var(--text-muted)' }}>
                      {r.wins}
                    </td>
                    <td className="text-right px-2 py-1" style={{ color: r.losses > 0 ? 'var(--red)' : 'var(--text-muted)' }}>
                      {r.losses}
                    </td>
                    <td className="text-right px-2 py-1 font-bold" style={{ color: winRateColor(wr) }}>
                      {fmtPct(wr)}
                    </td>
                    <td className="text-right px-2 py-1 font-bold" style={{ color: pnlColor(r.netUsd) }}>
                      {fmtUsd(r.netUsd)}
                    </td>
                    <td className="text-right px-2 py-1" style={{ color: 'var(--text-secondary)' }}>
                      <span style={{ color: 'var(--green)' }}>{r.wins > 0 ? fmtUsd(avgW) : '—'}</span>
                      <span style={{ color: 'var(--text-muted)' }}> / </span>
                      <span style={{ color: 'var(--red)' }}>{r.losses > 0 ? fmtUsd(-avgL) : '—'}</span>
                    </td>
                    <td className="text-right px-2 py-1" style={{ color: exp != null ? pnlColor(exp) : 'var(--text-muted)' }}>
                      {exp != null ? fmtUsd(exp) : '—'}
                    </td>
                    <td className="text-right px-2 py-1" style={{ color: 'var(--text-secondary)' }}>
                      {fmtPF(pf)}
                    </td>
                    <td className="px-2 py-1" style={{ color: 'var(--text-secondary)' }}>
                      <DirCell agg={r.byDir.LONG} wr={longWr} />
                    </td>
                    <td className="px-2 py-1" style={{ color: 'var(--text-secondary)' }}>
                      <DirCell agg={r.byDir.SHORT} wr={shortWr} />
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

function DirCell({ agg, wr }: { agg: DirAgg; wr: number | null }) {
  if (agg.total === 0) {
    return <span style={{ color: 'var(--text-muted)' }}>—</span>;
  }
  return (
    <span>
      <span style={{ color: 'var(--text-primary)' }}>{agg.total}</span>
      <span style={{ color: 'var(--text-muted)' }}>{': '}</span>
      <span style={{ color: 'var(--green)' }}>{agg.wins}</span>
      <span style={{ color: 'var(--text-muted)' }}>/</span>
      <span style={{ color: 'var(--red)' }}>{agg.losses}</span>
      <span style={{ color: 'var(--text-muted)' }}>{' '}</span>
      <span style={{ color: winRateColor(wr) }}>{fmtPct(wr)}</span>
      {agg.net !== 0 && (
        <>
          <span style={{ color: 'var(--text-muted)' }}>{' · '}</span>
          <span style={{ color: pnlColor(agg.net) }}>{fmtUsd(agg.net)}</span>
        </>
      )}
    </span>
  );
}
