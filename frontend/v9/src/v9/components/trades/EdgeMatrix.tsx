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
  { value: 'system', label: 'System' },
  { value: 'pattern', label: 'Pattern' },
  { value: 'day_type', label: 'Day Type', gated: true },
  { value: 'killzone', label: 'Killzone', gated: true },
  { value: 'direction', label: 'Direction' },
];

const SYSTEM_NAMES: Record<number, string> = { 1: 'Day Type', 2: '5-Min', 3: 'Footprint', 4: 'Woodies', 5: 'TPO', 6: 'Killzone' };

function groupKeyFn(t: Trade, dim: Dim): string {
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
  // target buckets
  t3: number; t2: number; t1: number; stopHit: number; be: number;
}

function emptyDir(): DirAgg { return { total: 0, wins: 0, losses: 0, net: 0 }; }

function aggregateByDim(trades: Trade[], dim: Dim): GroupAgg[] {
  const map = new Map<string, GroupAgg>();
  for (const t of trades) {
    const k = groupKeyFn(t, dim);
    let row = map.get(k);
    if (!row) {
      row = { key: k, total: 0, closed: 0, wins: 0, losses: 0, scratch: 0, netUsd: 0, grossWin: 0, grossLoss: 0, byDir: { LONG: emptyDir(), SHORT: emptyDir() }, t3: 0, t2: 0, t1: 0, stopHit: 0, be: 0 };
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
    // target buckets
    if (t.t3_hit) row.t3++;
    else if (t.t2_hit) row.t2++;
    else if (t.t1_hit) row.t1++;
    else if (pnl === 0) row.be++;
    else if (pnl < 0) row.stopHit++;

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
function pfCalc(gw: number, gl: number): number | null { return gl <= 0 ? (gw > 0 ? Infinity : null) : gw / gl; }
function expCalc(net: number, closed: number): number | null { return closed > 0 ? net / closed : null; }
function fmtPct(p: number | null): string { return p == null ? '---' : `${p.toFixed(1)}%`; }
function fmtUsd(v: number): string { return v >= 0 ? `+$${v.toFixed(2)}` : `($${Math.abs(v).toFixed(2)})`; }
function fmtPF(v: number | null): string { return v == null ? '---' : !Number.isFinite(v) ? '\u221e' : v.toFixed(2); }
function wrColor(p: number | null): string {
  if (p == null) return 'var(--text-muted)';
  if (p >= 55) return 'var(--green)';
  if (p >= 45) return 'var(--text-primary)';
  return p >= 30 ? '#eab308' : 'var(--red)';
}
function pnlColor(v: number): string { return v > 0 ? 'var(--green)' : v < 0 ? 'var(--red)' : 'var(--text-secondary)'; }

const tabStyle = (on: boolean): React.CSSProperties => ({
  padding: '6px 14px',
  borderRadius: '8px 8px 0 0',
  background: on ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
  color: on ? 'var(--text-primary)' : 'var(--text-secondary)',
  fontSize: 12,
  fontWeight: 600,
  border: '1px solid var(--border)',
  borderBottom: 'none',
  cursor: 'pointer',
});

const thStyle: React.CSSProperties = {
  fontSize: 9,
  textTransform: 'uppercase',
  letterSpacing: 0.4,
  color: 'var(--text-muted)',
  fontWeight: 600,
  textAlign: 'right',
  padding: '8px 11px',
  borderBottom: '1px solid var(--border)',
  whiteSpace: 'nowrap',
};

const tdStyle: React.CSSProperties = {
  padding: '7px 11px',
  borderBottom: '1px solid var(--border)',
  color: 'var(--text-secondary)',
};

const DIST_COLORS: Record<string, string> = {
  t3: 'var(--green)',
  t2: 'var(--sys5)',
  t1: 'var(--sys1)',
  stop: 'var(--red)',
  be: 'var(--text-muted)',
};

export function EdgeMatrix() {
  const filteredTrades = useTradeStore((s) => s.filteredTrades);
  const allTrades = filteredTrades();
  const trades = useMemo(() => allTrades.filter((t) => !t.is_synthetic), [allTrades]);
  const [dim, setDim] = useState<Dim>('pattern');

  const rows = useMemo(() => aggregateByDim(trades, dim), [trades, dim]);

  if (trades.length === 0) {
    return (
      <div style={{ marginTop: 20, padding: '0 2px' }}>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.7, fontFamily: 'var(--mono)' }}>
          Edge Matrix: no trades in filter
        </div>
      </div>
    );
  }

  return (
    <div style={{ marginTop: 20 }}>
      {/* Section label */}
      <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.7, fontFamily: 'var(--mono)', margin: '0 2px 8px', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        Edge Matrix
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 5 }}>
        {DIM_OPTIONS.map((d) => (
          <button
            key={d.value}
            onClick={() => setDim(d.value)}
            style={{
              ...tabStyle(dim === d.value),
              opacity: d.gated ? 0.6 : 1,
            }}
          >
            {d.label}{d.gated ? ' (G1)' : ''}
          </button>
        ))}
      </div>

      {/* Card with table */}
      <div style={{ border: '1px solid var(--border)', borderRadius: 8, background: 'var(--bg-secondary)', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--mono)', fontSize: 12 }}>
          <thead>
            <tr>
              <th style={{ ...thStyle, textAlign: 'right' }}>{dim}</th>
              <th style={thStyle}>N</th>
              <th style={thStyle}>W</th>
              <th style={thStyle}>L</th>
              <th style={thStyle}>BE</th>
              <th style={thStyle}>Win%</th>
              <th style={thStyle}>Net $</th>
              <th style={thStyle}>Exp $</th>
              <th style={thStyle}>PF</th>
              <th style={thStyle}>avgR</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Targets</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={11} style={{ ...tdStyle, textAlign: 'center', padding: 18, color: 'var(--text-muted)', borderBottom: 'none' }}>
                  No trades in filter
                </td>
              </tr>
            ) : rows.map((r, idx) => {
              const wr = winRate(r.wins, r.losses);
              const closedN = r.wins + r.losses + r.scratch;
              const ex = expCalc(r.netUsd, closedN);
              const pfv = pfCalc(r.grossWin, r.grossLoss);
              const totalR = r.netUsd; // approximate
              const isLast = idx === rows.length - 1;
              const baseTd = isLast ? { ...tdStyle, borderBottom: 'none' } : tdStyle;

              // Target distribution inline bar
              const distTotal = r.total || 1;
              const distBuckets: [string, number][] = [['t1', r.t1], ['t2', r.t2], ['t3', r.t3], ['stop', r.stopHit], ['be', r.be]];

              return (
                <tr key={r.key} style={{ cursor: 'pointer' }} onMouseOver={(e) => { (e.currentTarget as HTMLElement).style.background = 'var(--bg-tertiary)'; }} onMouseOut={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}>
                  <td style={{ ...baseTd, color: 'var(--text-primary)', fontWeight: 600 }}>{r.key}</td>
                  <td style={baseTd}>{r.total}</td>
                  <td style={{ ...baseTd, color: 'var(--green)' }}>{r.wins}</td>
                  <td style={{ ...baseTd, color: 'var(--red)' }}>{r.losses}</td>
                  <td style={baseTd}>{r.scratch}</td>
                  <td style={{ ...baseTd, color: wrColor(wr), fontWeight: 700 }}>{fmtPct(wr)}</td>
                  <td style={{ ...baseTd, color: pnlColor(r.netUsd), fontWeight: 700 }}>{fmtUsd(r.netUsd)}</td>
                  <td style={{ ...baseTd, color: ex != null ? pnlColor(ex) : 'var(--text-muted)' }}>{ex != null ? fmtUsd(ex) : '---'}</td>
                  <td style={baseTd}>{fmtPF(pfv)}</td>
                  <td style={baseTd}>---</td>
                  <td style={baseTd}>
                    <span style={{ display: 'inline-flex', height: 11, width: 120, borderRadius: 3, overflow: 'hidden', boxShadow: 'inset 0 0 0 1px var(--border)' }}>
                      {distBuckets.map(([key, count]) => count > 0 ? (
                        <i key={key} style={{ display: 'block', height: '100%', width: `${(count / distTotal) * 100}%`, background: DIST_COLORS[key] }} />
                      ) : null)}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div style={{ marginTop: 6, fontSize: 10.5, color: 'var(--text-muted)', fontFamily: 'var(--mono)', lineHeight: 1.7 }}>
        <span style={{ color: 'var(--green)' }}>{'\u25A0'}</span> T3{' '}
        <span style={{ color: 'var(--sys5)' }}>{'\u25A0'}</span> T2{' '}
        <span style={{ color: 'var(--sys1)' }}>{'\u25A0'}</span> T1{' '}
        <span style={{ color: 'var(--red)' }}>{'\u25A0'}</span> Stop{' '}
        <span style={{ color: 'var(--text-muted)' }}>{'\u25A0'}</span> BE/Scr
      </div>
    </div>
  );
}
