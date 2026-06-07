'use client';
import type { Trade } from '../../types';
import { rLevels, stopMovement } from '../../lib/tradeMath';

/**
 * Relative-R "story" track for a single trade. Div/percent based (crisp at any
 * width). Emphasis reflects importance:
 *   - a coloured segment entry(0) → exit shows WHAT HAPPENED (green win / red loss)
 *   - targets that were REACHED are solid + ✓; UNREACHED targets are dimmed/hollow
 *   - exit is a distinct diamond coloured by outcome (never the system colour)
 *   - stop = -1R (red); SMART_BE move drawn as a dotted -1R→BE segment
 *
 * All values from existing Trade fields (Rule 1) — no synthesis.
 */

interface Lab { x: number; text: string; color: string; dim?: boolean; }

function tier(items: Lab[], minGapPct: number): number[] {
  const last: number[] = [];
  return items.map((it) => {
    let k = 0;
    while (last[k] !== undefined && it.x - last[k] < minGapPct) k++;
    last[k] = it.x;
    return k;
  });
}

export function TradePathVisual({ trade, height = 52 }: { trade: Trade; height?: number; width?: number }) {
  const L = rLevels(trade);

  if (L.risk <= 0 || trade.entry_price == null) {
    return (
      <span style={{ color: 'var(--text-muted)', fontSize: 11, fontFamily: 'ui-monospace, monospace' }}>
        {trade.entry_price != null ? `IN ${trade.entry_price.toFixed(2)}` : '—'}
      </span>
    );
  }

  const moved = stopMovement(trade) === 'moved' && L.movedR != null;
  const closed = trade.exit_price != null;
  const win = (trade.pnl_usd ?? 0) > 0;
  const loss = (trade.pnl_usd ?? 0) < 0;
  const outcomeColor = win ? 'var(--green)' : loss ? 'var(--red)' : 'var(--text-secondary)';
  const mid = height / 2;

  const rs: number[] = [-1, 0];
  if (L.t1R != null) rs.push(L.t1R);
  if (L.t2R != null) rs.push(L.t2R);
  if (L.exitR != null) rs.push(L.exitR);
  if (moved && L.movedR != null) rs.push(L.movedR);
  const lo = Math.min(...rs) - 0.3;
  const hi = Math.max(...rs) + 0.35;
  const sp = hi - lo || 1;
  const X = (r: number) => ((r - lo) / sp) * 100;

  // labels (tiered) — targets above, entry/stop/exit below
  const above: Lab[] = [];
  if (L.t1R != null) above.push({ x: X(L.t1R), text: `+${L.t1R.toFixed(1)}R${trade.t1_hit ? ' ✓' : ''}`, color: trade.t1_hit ? 'var(--sys1)' : '#5a6472', dim: !trade.t1_hit });
  if (L.t2R != null) above.push({ x: X(L.t2R), text: `+${L.t2R.toFixed(1)}R${trade.t2_hit ? ' ✓' : ''}`, color: trade.t2_hit ? 'var(--sys1)' : '#5a6472', dim: !trade.t2_hit });
  if (moved && L.movedR != null) above.push({ x: X(L.movedR), text: 'BE', color: 'var(--green)' });
  above.sort((a, b) => a.x - b.x);
  const below: Lab[] = [{ x: X(-1), text: '-1R', color: 'var(--red)' }, { x: X(0), text: 'in', color: 'var(--text-muted)' }];
  if (L.exitR != null) below.push({ x: X(L.exitR), text: `${L.exitR >= 0 ? '+' : ''}${L.exitR.toFixed(1)}R`, color: outcomeColor });
  below.sort((a, b) => a.x - b.x);
  const aTier = tier(above, 10);
  const bTier = tier(below, 10);

  const a = X(0);
  const b = L.exitR != null ? X(L.exitR) : a;

  return (
    <div style={{ position: 'relative', height, margin: '2px 12px 0', fontFamily: 'ui-monospace, monospace' }}>
      {/* base track */}
      <div style={{ position: 'absolute', top: mid, left: 0, right: 0, height: 2, background: '#21262d', transform: 'translateY(-50%)' }} />
      {/* entry gridline */}
      <div style={{ position: 'absolute', left: `${X(0).toFixed(1)}%`, top: 6, bottom: 6, width: 0, borderLeft: '1px dashed rgba(230,237,243,0.25)' }} />

      {/* unreached/reached targets */}
      {L.t1R != null && (
        <div style={{ position: 'absolute', left: `${X(L.t1R).toFixed(1)}%`, top: mid, transform: 'translate(-50%,-50%)', width: trade.t1_hit ? 10 : 7, height: trade.t1_hit ? 10 : 7, borderRadius: '50%', background: trade.t1_hit ? 'var(--sys1)' : 'transparent', border: `${trade.t1_hit ? 2 : 1.5}px solid ${trade.t1_hit ? 'var(--sys1)' : '#3a4252'}`, opacity: trade.t1_hit ? 1 : 0.55, zIndex: 2 }} />
      )}
      {L.t2R != null && (
        <div style={{ position: 'absolute', left: `${X(L.t2R).toFixed(1)}%`, top: mid, transform: 'translate(-50%,-50%)', width: trade.t2_hit ? 10 : 7, height: trade.t2_hit ? 10 : 7, borderRadius: '50%', background: trade.t2_hit ? 'var(--sys1)' : 'transparent', border: `${trade.t2_hit ? 2 : 1.5}px solid ${trade.t2_hit ? 'var(--sys1)' : '#3a4252'}`, opacity: trade.t2_hit ? 1 : 0.55, zIndex: 2 }} />
      )}

      {/* travel segment entry -> exit (the story) */}
      {L.exitR != null && (
        <div style={{ position: 'absolute', left: `${Math.min(a, b)}%`, width: `${Math.abs(b - a)}%`, top: mid, height: 4, background: outcomeColor, opacity: 0.85, transform: 'translateY(-50%)', borderRadius: 2, borderStyle: closed ? undefined : 'dashed', zIndex: 1 }} />
      )}

      {/* SMART_BE move */}
      {moved && L.movedR != null && (
        <>
          <div style={{ position: 'absolute', left: `${Math.min(X(-1), X(L.movedR))}%`, width: `${Math.abs(X(L.movedR) - X(-1))}%`, top: mid, height: 0, borderTop: '2px dotted var(--green)', transform: 'translateY(-50%)', zIndex: 1 }} />
          <div style={{ position: 'absolute', left: `${X(L.movedR).toFixed(1)}%`, top: mid, transform: 'translate(-50%,-50%)', width: 9, height: 9, borderRadius: '50%', background: 'var(--green)', border: '2px solid var(--green)', zIndex: 3 }} />
        </>
      )}

      {/* stop */}
      <div style={{ position: 'absolute', left: `${X(-1).toFixed(1)}%`, top: mid, transform: 'translate(-50%,-50%)', width: 10, height: 10, borderRadius: '50%', background: moved ? 'var(--bg-primary)' : 'var(--red)', border: '2px solid var(--red)', zIndex: 3 }} />
      {/* entry */}
      <div style={{ position: 'absolute', left: `${X(0).toFixed(1)}%`, top: mid, transform: 'translate(-50%,-50%)', width: 8, height: 8, borderRadius: '50%', background: 'var(--text-primary)', zIndex: 3 }} />
      {/* exit — distinct diamond, outcome-coloured */}
      {L.exitR != null && (
        <div title={closed ? 'exit' : 'open'} style={{ position: 'absolute', left: `${X(L.exitR).toFixed(1)}%`, top: mid, transform: 'translate(-50%,-50%) rotate(45deg)', width: 9, height: 9, background: closed ? outcomeColor : 'var(--bg-primary)', border: `1.5px solid ${outcomeColor}`, zIndex: 4 }} />
      )}

      {/* labels */}
      {above.map((l, i) => (
        <div key={`a${i}`} style={{ position: 'absolute', left: `${l.x.toFixed(1)}%`, top: mid - 14 - aTier[i] * 11, transform: 'translateX(-50%)', fontSize: 9, color: l.color, opacity: l.dim ? 0.7 : 1, whiteSpace: 'nowrap' }}>{l.text}</div>
      ))}
      {below.map((l, i) => (
        <div key={`b${i}`} style={{ position: 'absolute', left: `${l.x.toFixed(1)}%`, top: mid + 8 + bTier[i] * 11, transform: 'translateX(-50%)', fontSize: 9, color: l.color, whiteSpace: 'nowrap' }}>{l.text}</div>
      ))}
    </div>
  );
}
