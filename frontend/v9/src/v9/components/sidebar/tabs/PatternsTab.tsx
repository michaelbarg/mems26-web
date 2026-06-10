'use client';
import { useState } from 'react';
import { useBuildStatus } from '../../../hooks/useBuildStatus';
import { COLORS } from '../../../design/tokens';
import type { Pattern, FormulaCondition } from '../../build_status/types';

const SYS_META: Record<string, { label: string; color: string; type: string }> = {
  day_type: { label: 'S1 · סיווג יום', color: '#a78bfa', type: 'OBSERVING' },
  five_min: { label: 'S2 · Five-Min', color: '#06b6d4', type: 'FIRING' },
  woodies:  { label: 'S4 · Woodies CCI', color: '#f59e0b', type: 'FIRING' },
};

function BuildBar({ pct }: { pct: number | null | undefined }) {
  if (pct == null) return null;
  const color = pct >= 80 ? COLORS.bull : pct >= 50 ? '#eab308' : COLORS.bearLight;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4, minWidth: 50 }}>
      <div style={{ flex: 1, height: 4, background: '#333', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 2 }} />
      </div>
      <span style={{ fontSize: 8, color, fontWeight: 600 }}>{pct}%</span>
    </div>
  );
}

function FormulaRow({ f }: { f: FormulaCondition }) {
  return (
    <div style={{ display: 'flex', gap: 4, fontSize: 9, padding: '1px 0',
                  color: f.met ? COLORS.textSecondary : COLORS.textTertiary }}>
      <span style={{ width: 12, textAlign: 'center' }}>{f.met ? '✓' : '✗'}</span>
      <span style={{ flex: 1 }}>{f.label}</span>
      <span style={{ color: COLORS.textTertiary, maxWidth: 60, overflow: 'hidden',
                     textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {f.actual ?? '—'}
      </span>
    </div>
  );
}

function PatternRow({ p }: { p: Pattern }) {
  const [open, setOpen] = useState(false);
  const hasFormula = p.formula && p.formula.length > 0;
  return (
    <div style={{ borderBottom: `1px solid ${COLORS.borderFaint}` }}>
      <div
        onClick={() => hasFormula && setOpen(!open)}
        style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '2px 4px',
                 cursor: hasFormula ? 'pointer' : 'default' }}
      >
        {hasFormula && <span style={{ fontSize: 8, color: COLORS.textTertiary }}>{open ? '▼' : '▶'}</span>}
        <span style={{ fontSize: 10, color: p.status === 'blocked' ? COLORS.textTertiary : COLORS.textPrimary,
                       flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {p.name}
        </span>
        <BuildBar pct={p.build_pct} />
      </div>
      {open && hasFormula && (
        <div style={{ padding: '2px 8px 4px 20px', background: COLORS.bgSurface1 }}>
          {p.formula!.map((f, i) => <FormulaRow key={i} f={f} />)}
        </div>
      )}
    </div>
  );
}

export function PatternsTab() {
  const { data, loading, lastFetchedAt, refresh } = useBuildStatus();
  const systems = (data?.systems ?? []).filter(s => s.id in SYS_META);

  return (
    <div style={{ fontSize: 11, fontFamily: 'ui-monospace, monospace' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <span style={{ fontWeight: 700, color: COLORS.textPrimary }}>זיהוי תבניות</span>
        <button onClick={refresh} disabled={loading}
          style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, border: 'none',
                   background: COLORS.bgSurface3, color: COLORS.textSecondary, cursor: 'pointer' }}>
          {loading ? '...' : '↻'}
        </button>
      </div>

      {systems.map(sys => {
        const meta = SYS_META[sys.id];
        if (!meta) return null;
        return (
          <div key={sys.id} style={{ marginBottom: 8, borderRadius: 4, overflow: 'hidden',
                                     border: `1px solid ${COLORS.borderFaint}` }}>
            <div style={{ padding: '3px 6px', background: COLORS.bgSurface3,
                          display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: meta.color, fontWeight: 700, fontSize: 10 }}>{meta.label}</span>
              <span style={{ fontSize: 8, padding: '1px 4px', borderRadius: 2,
                             background: meta.type === 'FIRING' ? '#0e3a1f' : '#1a1a3a',
                             color: meta.type === 'FIRING' ? COLORS.bull : '#818cf8' }}>{meta.type}</span>
            </div>
            {sys.id === 'day_type' ? (
              <div style={{ padding: '3px 6px', fontSize: 9 }}>
                {(sys.interpretations ?? []).map((i, idx) => (
                  <div key={idx} style={{ color: COLORS.textSecondary }}>
                    {i.key}: <span style={{ color: COLORS.textPrimary }}>{i.value}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div>
                {sys.patterns.map(p => <PatternRow key={p.id} p={p} />)}
              </div>
            )}
          </div>
        );
      })}

      {lastFetchedAt && (
        <div style={{ textAlign: 'center', fontSize: 8, color: COLORS.textTertiary }}>
          {lastFetchedAt.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' })}
        </div>
      )}
    </div>
  );
}
