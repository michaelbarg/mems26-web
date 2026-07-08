'use client';

// System 6 — live trade-supervisor activity. Reads GET /api/v9/system6/diagnose
// (the NEW supervisor: 9 management checks + HOLD gate + exit signals + hit-rates),
// NOT the old session-gate panel. Read-only; diagnoses only, never executes.
// Poll = 15s (diagnostic cadence; the backend is single-worker uvicorn — do not
// tighten without Michael's approval, per CLAUDE.md frontend polling floors).

import { useCallback, useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type Issue = { code: string; severity: string; action: string; detail: string };
type Signal = { kind: string; score: number; fired: boolean; reason: string; action: string };
type Diagnose = {
  active: boolean;
  note?: string;
  trade?: { id: number; direction: string; entry: number | null; stop: number | null; t1_hit: boolean; contracts: number } | null;
  supervisor?: { healthy: boolean; issues: Issue[] } | null;
  hold?: { intact: boolean; continuing: boolean; broke: boolean; score: number; reason: string } | null;
  exit_signals?: Signal[];
  recommendation?: string;
  hit_rates?: Record<string, unknown>;
};

const SEV_COLOR: Record<string, string> = {
  CRITICAL: 'var(--red, #f85149)', WARN: 'var(--orange, #d29922)', WARNING: 'var(--orange, #d29922)',
  INFO: 'var(--text-muted, #8b949e)',
};
const REC_COLOR: Record<string, string> = {
  hold: 'var(--green, #3fb950)', consider_exit: 'var(--orange, #d29922)', exit: 'var(--red, #f85149)',
};

function Dot({ on, color }: { on: boolean; color: string }) {
  return <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 4, background: on ? color : 'var(--border, #30363d)', marginRight: 6 }} />;
}

export function System6SupervisorPanel() {
  const [d, setD] = useState<Diagnose | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [at, setAt] = useState('');

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v9/system6/diagnose`, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setD(await res.json());
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

  const shell = (children: React.ReactNode) => (
    <div style={{
      background: 'var(--bg-panel, #0d1117)', border: '1px solid var(--border, #30363d)',
      borderRadius: 8, padding: 14, color: 'var(--text-secondary, #c9d1d9)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text, #e6edf3)' }}>System 6 — trade supervisor</div>
        <button onClick={load} style={{
          fontSize: 11, padding: '2px 8px', borderRadius: 4, cursor: 'pointer', background: 'transparent',
          color: 'var(--text-muted, #8b949e)', border: '1px solid var(--border, #30363d)',
        }}>↻</button>
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-muted, #8b949e)', marginBottom: 8 }}>
        live diagnosis · read-only{at ? ` · ${at}` : ''}
      </div>
      {children}
    </div>
  );

  if (error) {
    return shell(
      <div style={{ fontSize: 12, color: 'var(--orange, #d29922)' }}>
        Endpoint unavailable ({error}). The route <code>/api/v9/system6/diagnose</code> exists in the
        backend — if this persists, the running backend may predate it and needs a restart (CC, when flat).
      </div>
    );
  }
  if (!d) return shell(<div style={{ fontSize: 12, opacity: 0.6 }}>loading…</div>);

  if (!d.active || !d.trade) {
    return shell(
      <div style={{ fontSize: 13 }}>
        <Dot on={false} color="var(--green,#3fb950)" /> No active trade — System 6 idle.
        {d.note && <div style={{ fontSize: 11, color: 'var(--text-muted,#8b949e)', marginTop: 4 }}>{d.note}</div>}
        {d.hit_rates && Object.keys(d.hit_rates).length > 0 && (
          <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-muted,#8b949e)' }}>
            hit-rates: {JSON.stringify(d.hit_rates)}
          </div>
        )}
      </div>
    );
  }

  const t = d.trade;
  const rec = d.recommendation || 'hold';

  return shell(
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 13 }}>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <span style={{ fontFamily: 'ui-monospace, monospace', fontWeight: 700, color: 'var(--text,#e6edf3)' }}>
          #{t.id} {t.direction}
        </span>
        <span style={{ color: 'var(--text-muted,#8b949e)' }}>entry {t.entry ?? '—'} · stop {t.stop ?? '—'} · {t.contracts}c · T1 {t.t1_hit ? '✓' : '—'}</span>
        <span style={{
          marginLeft: 'auto', fontWeight: 700, padding: '2px 10px', borderRadius: 5,
          color: '#0d1117', background: REC_COLOR[rec] || 'var(--text-muted,#8b949e)',
        }}>{rec.replace(/_/g, ' ').toUpperCase()}</span>
      </div>

      {d.supervisor && (
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>
            <Dot on color={d.supervisor.healthy ? 'var(--green,#3fb950)' : 'var(--red,#f85149)'} />
            9 management checks — {d.supervisor.healthy ? 'healthy' : `${d.supervisor.issues.length} issue(s)`}
          </div>
          {d.supervisor.issues.map((i, k) => (
            <div key={k} style={{ fontSize: 12, marginLeft: 4, marginTop: 3 }}>
              <span style={{ color: SEV_COLOR[i.severity] || 'var(--text-muted,#8b949e)', fontWeight: 600 }}>
                [{i.severity}] {i.code}
              </span>{' '}
              <span style={{ color: '#79c0ff' }}>{i.action}</span>
              <span style={{ color: 'var(--text-muted,#8b949e)' }}> — {i.detail}</span>
            </div>
          ))}
        </div>
      )}

      {d.hold && (
        <div style={{ fontSize: 12 }}>
          <span style={{ fontWeight: 700 }}>HOLD gate: </span>
          <span style={{ color: d.hold.broke ? 'var(--red,#f85149)' : d.hold.continuing ? 'var(--green,#3fb950)' : 'var(--text-muted,#8b949e)' }}>
            {d.hold.broke ? 'BROKE' : d.hold.continuing ? 'continuing' : 'intact'}
          </span>
          <span style={{ color: 'var(--text-muted,#8b949e)' }}> · score {d.hold.score} · {d.hold.reason}</span>
        </div>
      )}

      {d.exit_signals && d.exit_signals.length > 0 && (
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>Exit signals</div>
          {d.exit_signals.map((s, k) => (
            <div key={k} style={{ fontSize: 12, marginLeft: 4, marginTop: 2 }}>
              <Dot on={s.fired} color="var(--orange,#d29922)" />
              <span style={{ fontWeight: 600, color: s.fired ? 'var(--orange,#d29922)' : 'var(--text-muted,#8b949e)' }}>{s.kind}</span>
              <span style={{ color: 'var(--text-muted,#8b949e)' }}> · {s.score} · {s.reason}{s.fired ? ` → ${s.action}` : ''}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
