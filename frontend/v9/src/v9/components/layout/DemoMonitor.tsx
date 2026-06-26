'use client';
import { useEffect, useState } from 'react';

// Pipeline 5 DEMO supervision: a floating button + panel showing the live active trade
// (entry / stop / C1 / runners) and recent trades. Reads the no-auth backend endpoints.
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Trade {
  id?: number; mode?: string; system?: number; direction?: string; state?: string;
  entry_price?: number; stop?: number; stop_initial?: number;
  contracts?: number; size?: number; t1?: number; t2?: number; t3?: number;
  pnl?: number; realized_pnl?: number; exit_price?: number; outcome?: string;
}

const isNum = (n: unknown): n is number => typeof n === 'number';
const fmt = (n: unknown): string =>
  n == null || n === '' ? '—' : isNum(n) ? n.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(n);

function KV({ k, v, hi, dim }: { k: string; v: string; hi?: boolean; dim?: boolean }) {
  return (
    <div style={{ background: '#161b22', border: '1px solid #21262d', borderRadius: 6, padding: '6px 8px' }}>
      <div style={{ fontSize: 10, color: '#8b949e' }}>{k}</div>
      <div style={{ fontSize: 15, fontWeight: 700, marginTop: 2, color: hi ? '#2ea043' : dim ? '#8b949e' : '#e6edf3' }}>{v}</div>
    </div>
  );
}

export function DemoMonitor() {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState<Trade | null>(null);
  const [recent, setRecent] = useState<Trade[]>([]);
  const [mode, setMode] = useState<string>('');

  // Always poll the active trade (drives the button indicator). 5s — within the polling floors.
  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try {
        const r = await fetch(`${API}/api/v9/trades/active`).catch(() => null);
        if (r && r.ok && alive) setActive(await r.json());
      } catch { /* ignore */ }
    };
    poll();
    const t = setInterval(poll, 5000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  // When the panel is open, also poll recent trades + mode.
  useEffect(() => {
    if (!open) return;
    let alive = true;
    const poll = async () => {
      try {
        const [rs, ss] = await Promise.all([
          fetch(`${API}/api/v9/trades/recent?limit=10`).then(r => (r.ok ? r.json() : [])).catch(() => []),
          fetch(`${API}/api/v9/status`).then(r => (r.ok ? r.json() : {})).catch(() => ({})),
        ]);
        if (!alive) return;
        setRecent(Array.isArray(rs) ? rs : []);
        setMode((ss && ss.mode) || '');
      } catch { /* ignore */ }
    };
    poll();
    const t = setInterval(poll, 4000);
    return () => { alive = false; clearInterval(t); };
  }, [open]);

  const hasActive = !!(active && active.id);
  const modeColor = mode === 'demo' ? '#d29922' : mode === 'live' ? '#f85149' : '#6e7681';

  return (
    <>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          position: 'fixed', bottom: 16, insetInlineEnd: 16, zIndex: 60,
          background: '#161b22', color: '#e6edf3', border: '1px solid #30363d', borderRadius: 8,
          padding: '8px 14px', fontSize: 13, fontWeight: 600, cursor: 'pointer',
          boxShadow: '0 4px 14px rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', gap: 8,
        }}
      >
        <span style={{
          width: 9, height: 9, borderRadius: '50%', background: hasActive ? '#2ea043' : '#6e7681',
          boxShadow: hasActive ? '0 0 0 3px rgba(46,160,67,0.25)' : 'none',
        }} />
        מוניטור עסקה{hasActive ? ' · פעילה' : ''}
      </button>

      {open && (
        <div style={{
          position: 'fixed', bottom: 60, insetInlineEnd: 16, zIndex: 60, width: 380, maxHeight: '72vh',
          overflow: 'auto', background: '#0e1117', color: '#e6edf3', border: '1px solid #30363d',
          borderRadius: 10, boxShadow: '0 8px 28px rgba(0,0,0,0.5)', padding: 14, fontSize: 13,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <b>מוניטור פיקוח DEMO</b>
            <span style={{ background: modeColor, color: '#10131a', fontWeight: 700, padding: '2px 10px', borderRadius: 5, fontSize: 12 }}>
              {(mode || 'shadow').toUpperCase()}
            </span>
          </div>

          {hasActive ? (() => {
            const t = active as Trade;
            const dir = t.direction || '';
            const contracts = t.contracts ?? t.size;
            const pnl = t.pnl ?? t.realized_pnl;
            const stopMoved = isNum(t.stop) && isNum(t.stop_initial) && t.stop !== t.stop_initial;
            const runners = isNum(contracts) ? Math.max(contracts - 1, 0) : null;
            return (
              <div style={{ border: '1px solid #30363d', borderRadius: 8, padding: 12, marginBottom: 10 }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontWeight: 800, fontSize: 18, color: dir === 'LONG' ? '#2ea043' : '#f85149' }}>{dir}</span>
                  <span style={{ color: '#8b949e', fontSize: 12 }}>#{t.id} · מערכת {t.system ?? '—'} · {t.state}</span>
                  {isNum(pnl) && (
                    <span style={{ marginInlineStart: 'auto', fontWeight: 800, color: pnl >= 0 ? '#2ea043' : '#f85149' }}>
                      {pnl >= 0 ? '+' : ''}{fmt(pnl)}
                    </span>
                  )}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8 }}>
                  <KV k="כניסה" v={fmt(t.entry_price)} />
                  <KV k="חוזים" v={fmt(contracts)} />
                  <KV k="סטופ" v={fmt(t.stop) + (stopMoved ? ' ↗' : '')} hi={stopMoved} />
                  {isNum(t.t1) && <KV k="T1 (C1)" v={fmt(t.t1)} />}
                  {runners != null && <KV k="Runners" v={String(runners)} />}
                  <KV k="סטופ התחלתי" v={fmt(t.stop_initial)} dim />
                </div>
              </div>
            );
          })() : (
            <div style={{ color: '#8b949e', textAlign: 'center', padding: 18 }}>אין עסקה פעילה — ממתין ל-setup.</div>
          )}

          <div style={{ fontSize: 11, color: '#8b949e', margin: '6px 2px' }}>אחרונות</div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <tbody>
              {recent.length ? recent.map(t => {
                const pnl = t.pnl ?? t.realized_pnl;
                return (
                  <tr key={t.id} style={{ borderBottom: '1px solid #1c222b' }}>
                    <td style={{ padding: '4px 6px', color: '#8b949e' }}>#{t.id}</td>
                    <td style={{ padding: '4px 6px', color: t.direction === 'LONG' ? '#2ea043' : '#f85149' }}>{t.direction}</td>
                    <td style={{ padding: '4px 6px' }}>{fmt(t.entry_price)}</td>
                    <td style={{ padding: '4px 6px', color: '#8b949e' }}>{t.mode}</td>
                    <td style={{ padding: '4px 6px', textAlign: 'end', color: isNum(pnl) ? (pnl >= 0 ? '#2ea043' : '#f85149') : '#8b949e' }}>
                      {isNum(pnl) ? (pnl >= 0 ? '+' : '') + fmt(pnl) : (t.outcome || t.state || '')}
                    </td>
                  </tr>
                );
              }) : (
                <tr><td style={{ color: '#8b949e', padding: 6 }}>—</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
