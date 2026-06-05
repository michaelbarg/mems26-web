'use client';
/**
 * Execution-mode toggle — "All" vs "Sequential (one-at-a-time)" comparison.
 *
 * Consumes existing auxStatus (isParallel/liveEligible) from tradeStore — no new gating logic.
 * Shows win% all vs sequential side-by-side.
 */
import { useMemo } from 'react';
import { useTradeStore } from '../../stores/tradeStore';

function winPct(trades: { pnl_usd: number | null }[]): number | null {
  let w = 0, l = 0;
  for (const t of trades) {
    if (t.pnl_usd == null) continue;
    if (t.pnl_usd > 0) w++;
    else if (t.pnl_usd < 0) l++;
  }
  const n = w + l;
  return n > 0 ? (w / n) * 100 : null;
}

function fmtPct(p: number | null): string { return p == null ? '---' : `${p.toFixed(1)}%`; }
function fmtUsd(v: number | null): string {
  if (v == null) return '---';
  return v >= 0 ? `+$${v.toFixed(2)}` : `($${Math.abs(v).toFixed(2)})`;
}
function wrColor(p: number | null): string {
  if (p == null) return 'var(--text-muted)';
  return p >= 55 ? 'var(--green)' : p >= 45 ? 'var(--text-primary)' : p >= 30 ? '#eab308' : 'var(--red)';
}
function pnlColor(v: number): string { return v > 0 ? 'var(--green)' : v < 0 ? 'var(--red)' : 'var(--text-secondary)'; }

function netUsd(trades: { pnl_usd: number | null }[]): number {
  return trades.reduce((s, t) => s + (t.pnl_usd ?? 0), 0);
}
function expUsd(trades: { pnl_usd: number | null }[]): number | null {
  const closed = trades.filter(t => t.pnl_usd != null);
  return closed.length > 0 ? netUsd(trades) / closed.length : null;
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

const segStyle: React.CSSProperties = {
  display: 'inline-flex',
  border: '1px solid var(--border)',
  borderRadius: 7,
  overflow: 'hidden',
};

function segBtn(isOn: boolean): React.CSSProperties {
  return {
    fontFamily: 'var(--mono)',
    fontSize: 11,
    padding: '5px 11px',
    background: isOn ? 'var(--sys1)' : 'var(--bg-primary)',
    color: isOn ? '#06121f' : 'var(--text-secondary)',
    border: 'none',
    cursor: 'pointer',
    fontWeight: isOn ? 700 : 400,
    borderInlineStart: '1px solid var(--border)',
  };
}

const cmpBoxStyle = (live: boolean): React.CSSProperties => ({
  padding: '4px 11px',
  borderRadius: 7,
  background: 'var(--bg-primary)',
  border: `1px solid ${live ? '#58a6ff66' : 'var(--border)'}`,
});

export function ExecModeToggle() {
  const filteredTrades = useTradeStore((s) => s.filteredTrades);
  const auxStatus = useTradeStore((s) => s.auxStatus);
  const filters = useTradeStore((s) => s.filters);
  const setFilters = useTradeStore((s) => s.setFilters);

  const allTrades = filteredTrades();
  const trades = useMemo(() => allTrades.filter((t) => !t.is_synthetic), [allTrades]);

  const seqTrades = useMemo(
    () => trades.filter((t) => auxStatus.get(t.id)?.liveEligible === true),
    [trades, auxStatus]
  );

  const allWr = useMemo(() => winPct(trades), [trades]);
  const seqWr = useMemo(() => winPct(seqTrades), [seqTrades]);

  const mode = filters.liveGated === 'eligible' ? 'live' : filters.overlap === 'parallel' ? 'parallel' : 'all';

  if (trades.length === 0) return null;

  const allNet = netUsd(trades);
  const allExp = expUsd(trades);
  const seqNet = netUsd(seqTrades);
  const seqExp = expUsd(seqTrades);

  return (
    <div style={barStyle}>
      <span style={{ color: 'var(--text-muted)', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>Display</span>
      <span style={segStyle}>
        <button
          onClick={() => setFilters({ liveGated: 'all', overlap: 'all' })}
          style={{ ...segBtn(mode === 'all'), borderInlineStart: 'none' }}
        >
          All
        </button>
        <button
          onClick={() => setFilters({ overlap: 'parallel', liveGated: 'all' })}
          style={segBtn(mode === 'parallel')}
        >
          Parallel
        </button>
        <button
          onClick={() => setFilters({ liveGated: 'eligible', overlap: 'all' })}
          style={segBtn(mode === 'live')}
        >
          Sequential (LIVE)
        </button>
      </span>

      <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>
        Parallel = overlapped another trade. Sequential = what would run in LIVE.
      </span>

      <span style={{ display: 'flex', gap: 14, marginInlineStart: 'auto', flexWrap: 'wrap' }}>
        {/* All comparison box */}
        <span style={cmpBoxStyle(false)}>
          <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>All (SHADOW)</div>
          <div style={{ display: 'flex', gap: 11, marginTop: 2 }}>
            <span>Net <b style={{ color: pnlColor(allNet) }}>{fmtUsd(allNet)}</b></span>
            <span>Win <b style={{ color: 'var(--text-primary)' }}>{fmtPct(allWr)}</b></span>
            <span>Exp <b style={{ color: pnlColor(allExp ?? 0) }}>{fmtUsd(allExp)}</b></span>
          </div>
        </span>
        {/* Sequential comparison box */}
        <span style={cmpBoxStyle(true)}>
          <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>Sequential (LIVE)</div>
          <div style={{ display: 'flex', gap: 11, marginTop: 2 }}>
            <span>Net <b style={{ color: pnlColor(seqNet) }}>{fmtUsd(seqNet)}</b></span>
            <span>Win <b style={{ color: 'var(--text-primary)' }}>{fmtPct(seqWr)}</b></span>
            <span>Exp <b style={{ color: pnlColor(seqExp ?? 0) }}>{fmtUsd(seqExp)}</b></span>
          </div>
        </span>
      </span>
    </div>
  );
}
