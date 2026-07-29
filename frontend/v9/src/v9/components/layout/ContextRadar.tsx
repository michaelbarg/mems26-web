'use client';
/**
 * ContextRadar — "רדאר זיהוי מסודר" (Michael 2026-07-29).
 *
 * One strip that answers, at a glance: what day is it, which way, what opening,
 * is anything holding fire, can the system actually trade right now, and can
 * the data itself be trusted. Source: GET /api/v9/context/radar (aggregation of
 * existing truth; System-0 fields appear automatically when CC ships
 * MARKET_CONTEXT_V1 — the API shape is frozen).
 *
 * Poll: 5000ms (matches useSystemStatePolling — trading-critical visibility).
 * Missing field renders "—", never a guess.
 */
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';
import { getApiBase } from '../../lib/api';

const API_BASE = getApiBase();

interface Radar {
  day_type?: string | null; stage?: string | null; confidence?: number | null;
  leg?: string | null; lock_state?: string | null;
  opening_type?: string | null; opening_dir?: string | null; opening_conf?: number | null;
  balance_state?: string | null; acceptance?: string | null;
  release_gate?: { state: string; reason?: string | null; age_min?: number | null };
  gates_last_hour?: {
    blocked: number; passed: number; top: [string, number][];
    last_block?: { gate: string; pattern?: string; direction?: string; ts: string } | null;
  };
  trading?: {
    armed?: number | null; is_sim?: number | null; sendorders?: number | null;
    position_qty?: number | null; contracts_allowed?: number | null; stale?: boolean;
  };
  bar_integrity?: string;
}

const G = '#16a34a', R = '#dc2626', Y = '#eab308', C = '#67e8f9';

function legArrow(leg?: string | null): { txt: string; color: string } {
  if (leg === 'UP') return { txt: '▲ UP', color: G };
  if (leg === 'DOWN') return { txt: '▼ DOWN', color: R };
  return { txt: '—', color: COLORS.textTertiary };
}

export function ContextRadar() {
  const [r, setR] = useState<Radar | null>(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v9/context/radar`);
        if (!res.ok) { if (alive) setErr(true); return; }
        const d = await res.json();
        if (alive) { setR(d); setErr(false); }
      } catch { if (alive) setErr(true); }
    };
    load();
    const id = setInterval(load, 5000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  const leg = legArrow(r?.leg);
  const gl = r?.gates_last_hour;
  const rg = r?.release_gate;
  const tr = r?.trading;
  const integrity = r?.bar_integrity;
  const canTrade = tr?.armed === 1 && (tr?.contracts_allowed ?? 0) > 0 && !tr?.stale;

  const Box = ({ label, children, title, alert }:
    { label: string; children: React.ReactNode; title?: string; alert?: boolean }) => (
    <div title={title} style={{
      display: 'flex', flexDirection: 'column', gap: 2, minWidth: 86,
      padding: '4px 8px', borderRadius: 5,
      border: `1px solid ${alert ? R : COLORS.borderFaint}`,
      background: alert ? 'rgba(220,38,38,0.10)' : 'rgba(255,255,255,0.02)',
    }}>
      <span style={{ fontSize: 7, color: COLORS.textDim, letterSpacing: '0.5px' }}>{label}</span>
      <span style={{ fontSize: 10, fontWeight: 700, fontFamily: 'ui-monospace' }}>{children}</span>
    </div>
  );

  return (
    <div style={{
      display: 'flex', alignItems: 'stretch', gap: 8, flexWrap: 'wrap',
      padding: '5px 10px', borderBottom: `1px solid ${COLORS.borderFaint}`,
    }}>
      <span style={{
        alignSelf: 'center', fontSize: 8, fontWeight: 800, letterSpacing: '1px',
        color: C, transform: 'rotate(0deg)',
      }}>רדאר</span>

      <Box label="סוג יום" title={`stage ${r?.stage ?? '—'} · lock ${r?.lock_state ?? '—'}`}>
        {r?.day_type ?? '—'}
        <span style={{ fontWeight: 400, fontSize: 8, color: COLORS.textDim }}>
          {'  '}{r?.confidence != null ? `${Math.round((r.confidence as number) * 100)}%` : ''}
        </span>
      </Box>

      <Box label="רגל" title={`direction: ${r?.leg ?? 'אין'}`}>
        <span style={{ color: leg.color }}>{leg.txt}</span>
      </Box>

      <Box label="פתיחה" title={`ביטחון ${r?.opening_conf ?? '—'}`}>
        {r?.opening_type ?? '—'}
        {r?.opening_dir ? (
          <span style={{ color: r.opening_dir === 'UP' ? G : r.opening_dir === 'DOWN' ? R : COLORS.textDim, fontSize: 9 }}>
            {'  '}{r.opening_dir}
          </span>
        ) : null}
      </Box>

      <Box label="איזון / קבלה" title="שדות מערכת-0 — יתמלאו כש-MARKET_CONTEXT_V1 יעלה">
        {r?.balance_state ?? '—'}
        <span style={{ fontWeight: 400, fontSize: 8, color: COLORS.textDim }}>
          {'  '}{r?.acceptance ?? ''}
        </span>
      </Box>

      <Box label="שער שחרור"
        alert={rg?.state === 'holding'}
        title={rg?.reason ?? 'לא מחזיק כלום'}>
        {rg?.state === 'holding' ? `מחזיק ${rg?.age_min ?? '?'} דק'` : rg?.state === 'released' ? 'שוחרר' : 'פנוי'}
      </Box>

      <Box label="שערים / שעה"
        title={gl?.top?.length ? gl.top.map(([g, n]) => `${g}×${n}`).join(' · ') : 'אין חסימות'}
        alert={(gl?.blocked ?? 0) > 0 && (gl?.passed ?? 0) === 0}>
        <span style={{ color: (gl?.passed ?? 0) > 0 ? G : COLORS.textSecondary }}>{gl?.passed ?? 0} עברו</span>
        <span style={{ color: COLORS.textDim }}> / </span>
        <span style={{ color: (gl?.blocked ?? 0) > 0 ? Y : COLORS.textSecondary }}>{gl?.blocked ?? 0} נחסמו</span>
      </Box>

      {gl?.last_block && (
        <Box label="חסימה אחרונה" title={`${gl.last_block.pattern ?? ''} ${gl.last_block.direction ?? ''}`}>
          <span style={{ fontSize: 9 }}>{gl.last_block.ts} {gl.last_block.gate}</span>
        </Box>
      )}

      <Box label="מסחר"
        alert={!canTrade}
        title={`armed=${tr?.armed} sendorders=${tr?.sendorders} sim=${tr?.is_sim} פוזיציה=${tr?.position_qty}`}>
        {canTrade
          ? <span style={{ color: G }}>✓ מוכן · עד {tr?.contracts_allowed} חוזים</span>
          : <span style={{ color: R }}>{tr?.stale ? 'נתונים לא טריים' : tr?.armed !== 1 ? 'לא חמוש' : 'אין מרג\'ין'}</span>}
      </Box>

      <Box label="שלמות ברים"
        alert={integrity === 'suspect'}
        title="תפר >15 נק' בין ברים סמוכים = זרם חשוד — אל תסמוך על הסיווגים">
        {integrity === 'clean' ? <span style={{ color: G }}>✓ נקי</span>
          : integrity === 'suspect' ? <span style={{ color: R }}>🔴 חשוד</span>
          : <span style={{ color: COLORS.textDim }}>{integrity ?? '—'}</span>}
      </Box>

      {err && <span style={{ alignSelf: 'center', fontSize: 8, color: Y }}>רדאר לא זמין</span>}
    </div>
  );
}
