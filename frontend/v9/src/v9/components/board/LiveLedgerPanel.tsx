'use client';

// LIVE ledger — what Sierra ACTUALLY executed (journal L8). Reads
// GET /api/v9/live_ledger: each trade reconstructed from Sierra fills alone
// (entry, exits, contracts, realized P&L from fill prices), reconciled vs the
// backend DB row (CRITICAL divergences flagged), manual interventions tagged.
// This is the record to show investors — reality, not backend claims.

import { useCallback, useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type Exit = { kind: string; price: number | null; ts: number | null; qty: number | null };
type Divergence = { field: string; sierra: unknown; backend: unknown; severity: string };
type ManualEvent = { kind: string; detail: string; price: number | null; tag: string };
type LedgerTrade = {
  entry_order_id: number | string; account: string | null;
  entry_price: number | null; contracts: number | null;
  direction: string | null; direction_source: string;
  exits: Exit[]; realized_pnl: number | null; pnl_basis: string; closed: boolean;
  divergences: Divergence[]; manual_events: ManualEvent[]; backend_trade_id: number | null;
};
type Resp = {
  enabled: boolean; note?: string; error?: string; source?: string;
  generated_at?: string | null; divergence_count?: number; trades?: LedgerTrade[];
};

function pnlColor(p: number | null) {
  if (p === null) return 'var(--text-muted, #8b949e)';
  return p > 0 ? 'var(--green, #3fb950)' : p < 0 ? 'var(--red, #f85149)' : 'var(--text-muted, #8b949e)';
}

export function LiveLedgerPanel() {
  const [r, setR] = useState<Resp | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [at, setAt] = useState('');

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v9/live_ledger`, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setR(await res.json());
      setError(null);
      setAt(new Date().toLocaleTimeString());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'load failed');
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, [load]);

  const shell = (children: React.ReactNode, badge?: React.ReactNode) => (
    <div style={{
      background: 'var(--bg-panel, #0d1117)', border: '1px solid var(--border, #30363d)',
      borderLeft: '3px solid var(--green, #3fb950)', borderRadius: 8, padding: 14,
      color: 'var(--text-secondary, #c9d1d9)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: 6 }}>
        <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text, #e6edf3)' }}>
          Live Ledger — what Sierra executed
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {badge}
          <button onClick={load} style={{
            fontSize: 11, padding: '2px 8px', borderRadius: 4, cursor: 'pointer', background: 'transparent',
            color: 'var(--text-muted, #8b949e)', border: '1px solid var(--border, #30363d)',
          }}>↻</button>
        </div>
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-muted, #8b949e)', marginBottom: 8 }}>
        Sierra fills = ground truth · reconciled vs backend{at ? ` · ${at}` : ''}
      </div>
      {children}
    </div>
  );

  if (error) {
    return shell(
      <div style={{ fontSize: 12, color: 'var(--orange, #d29922)' }}>
        Endpoint unavailable ({error}). Route <code>/api/v9/live_ledger</code> is wired in app.py — if
        this persists the backend needs a restart to pick it up (CC, when flat).
      </div>
    );
  }
  if (!r) return shell(<div style={{ fontSize: 12, opacity: 0.6 }}>loading…</div>);
  if (r.enabled === false) {
    return shell(<div style={{ fontSize: 12, color: 'var(--orange, #d29922)' }}>
      LIVE_LEDGER_V1 is OFF — enable the flag (CC) to serve the Sierra-sourced ledger.{r.note ? ` (${r.note})` : ''}
    </div>);
  }
  if (r.error) {
    return shell(<div style={{ fontSize: 12, color: 'var(--red, #f85149)' }}>{r.error}</div>);
  }

  const trades = r.trades || [];
  const divBadge = (r.divergence_count || 0) > 0
    ? <span style={{ fontSize: 11, fontWeight: 700, color: '#fff', background: 'var(--red,#f85149)', padding: '1px 8px', borderRadius: 4 }}>
        {r.divergence_count} divergence{(r.divergence_count || 0) > 1 ? 's' : ''}
      </span>
    : <span style={{ fontSize: 11, fontWeight: 700, color: '#000', background: 'var(--green,#3fb950)', padding: '1px 8px', borderRadius: 4 }}>reconciled ✓</span>;

  if (trades.length === 0) {
    return shell(<div style={{ fontSize: 13 }}>No live trades in the fills yet.{r.note ? ` (${r.note})` : ''}</div>, divBadge);
  }

  return shell(
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {trades.map((t, i) => (
        <div key={i} style={{
          border: '1px solid var(--border, #30363d)', borderRadius: 6, padding: '8px 10px',
          background: 'rgba(255,255,255,0.02)',
        }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontFamily: 'ui-monospace, monospace', fontWeight: 700, color: 'var(--text, #e6edf3)' }}>
              {t.direction || '?'} · entry {t.entry_price ?? '—'} · {t.contracts ?? '?'}c
            </span>
            <span style={{ fontSize: 11, color: 'var(--text-muted, #8b949e)' }}>
              order {String(t.entry_order_id)}{t.backend_trade_id ? ` · backend #${t.backend_trade_id}` : ' · no backend match'}
            </span>
            <span style={{ marginLeft: 'auto', fontWeight: 700, color: pnlColor(t.realized_pnl) }}>
              {t.realized_pnl === null ? '—' : `$${t.realized_pnl}`}
              <span style={{ fontSize: 10, opacity: 0.6, fontWeight: 400 }}> ({t.pnl_basis})</span>
            </span>
          </div>

          <div style={{ fontSize: 12, color: 'var(--text-secondary, #c9d1d9)', marginTop: 4 }}>
            fills: {t.exits.length === 0 ? 'entry only (open)' : t.exits.map((e, k) => (
              <span key={k} style={{ fontFamily: 'ui-monospace, monospace', marginRight: 8 }}>
                {e.kind}@{e.price ?? '—'}
              </span>
            ))}
            {t.closed ? '' : <span style={{ color: 'var(--orange, #d29922)' }}> · OPEN</span>}
          </div>

          {t.divergences.length > 0 && (
            <div style={{ marginTop: 6 }}>
              {t.divergences.map((d, k) => (
                <div key={k} style={{ fontSize: 12, color: 'var(--red, #f85149)' }}>
                  ⚠ {d.severity} {d.field}: Sierra <b>{String(d.sierra)}</b> ≠ backend <b>{String(d.backend)}</b>
                </div>
              ))}
            </div>
          )}
          {t.manual_events.length > 0 && (
            <div style={{ marginTop: 4 }}>
              {t.manual_events.map((m, k) => (
                <div key={k} style={{ fontSize: 12, color: 'var(--orange, #d29922)' }}>
                  🖐 {m.tag} {m.kind} — {m.detail}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>,
    divBadge,
  );
}
