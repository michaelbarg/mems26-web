'use client';
// DayTypeConditionsTable — the live S1 "Build Status" table (2026-06-20).
// Shows EVERY day-type (7) + opening-type (5) with its exact conditions, marks in real-time
// which conditions are MET from the live signals, and highlights the currently-identified type.
// Data: GET /api/v9/day_type/classify_replay?date=today (the NEW state-machine classifier —
// the same one we validated). Read-only; no engine change. Per the locked table in
// docs/spec_authority/S1_DAYTYPE_INDEX.md.
import { useCallback, useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const todayISO = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());

const DT_COLOR: Record<string, string> = {
  FORMING: '#8b949e', Nontrend: '#a85751', Normal: '#d2a106', Normal_Variation: '#bfae3b',
  Neutral_Center: '#58a6ff', Neutral_Extreme: '#bc8cff', Trend_DD: '#3fb950', Trend_Normal: '#56d364',
};

interface Sig {
  sides?: number | null; rib?: number | null; close_pos?: number | null; one_tf?: string | null;
  vol_ratio?: number | null; narrow_ib?: boolean; neck?: number | null; invalidated?: boolean;
}
interface Cond { label: string; met: boolean | null }   // null = signal not available yet
const C = (label: string, met: boolean | null): Cond => ({ label, met });
const ge = (v: number | null | undefined, t: number) => (v == null ? null : v >= t);
const le = (v: number | null | undefined, t: number) => (v == null ? null : v <= t);
const eq = (v: number | null | undefined, t: number) => (v == null ? null : v === t);
const extreme = (cp: number | null | undefined) => (cp == null ? null : cp >= 0.85 || cp <= 0.15);

// the 7 day-types in precedence order, each → its live conditions from the signals
const DAY_ROWS: Array<{ name: string; conds: (s: Sig) => Cond[] }> = [
  { name: 'Nontrend', conds: (s) => [C('sides==0', eq(s.sides, 0)), C('vol≤0.5', le(s.vol_ratio, 0.5)), C('rib≤1.15', le(s.rib, 1.15))] },
  { name: 'Neutral_Center', conds: (s) => [C('sides==2', eq(s.sides, 2)), C('close mid', s.close_pos == null ? null : !extreme(s.close_pos))] },
  { name: 'Neutral_Extreme', conds: (s) => [C('sides==2', eq(s.sides, 2)), C('close extreme', extreme(s.close_pos))] },
  { name: 'Trend_DD', conds: (s) => [C('sides==1', eq(s.sides, 1)), C('IB narrow', s.narrow_ib ?? null), C('neck≥0.60', ge(s.neck, 0.60)), C('close extreme', s.close_pos == null ? null : (s.close_pos <= 0.2 || s.close_pos >= 0.8))] },
  { name: 'Trend_Normal', conds: (s) => [C('sides==1', eq(s.sides, 1)), C('open held', s.invalidated == null ? null : !s.invalidated), C('one_tf', s.one_tf == null ? null : (s.one_tf === 'UP' || s.one_tf === 'DOWN')), C('close extreme', extreme(s.close_pos)), C('rib≥2.5', ge(s.rib, 2.5))] },
  { name: 'Normal_Variation', conds: (s) => [C('sides==1', eq(s.sides, 1)), C('(else)', eq(s.sides, 1))] },
  { name: 'Normal', conds: (s) => [C('sides==0', eq(s.sides, 0)), C('rib≤1.3', le(s.rib, 1.3)), C('vol normal', s.vol_ratio == null ? null : s.vol_ratio > 0.5), C('IB not-narrow', s.narrow_ib == null ? null : !s.narrow_ib)] },
];

const OPEN_ROWS: Array<{ name: string; desc: string }> = [
  { name: 'OPEN_DRIVE', desc: 'פתיחה=קצה + מחזיק מעבר לטווח-הפתיחה + סגירה כיוונית, בלי חזרה' },
  { name: 'OPEN_TEST_DRIVE', desc: 'נגיעה קצרה מעבר לרפרנס שנכשלה → היפוך ונהיגה לצד השני' },
  { name: 'OPEN_REJECTION_REVERSE', desc: 'מהלך התחלתי → היפוך מלא בחזרה דרך הפתיחה' },
  { name: 'OPEN_AUCTION_IN', desc: 'רוטציה (≥2 חציות), פתיחה בתוך טווח-אתמול' },
  { name: 'OPEN_AUCTION_OUT', desc: 'רוטציה, פתיחה מחוץ לטווח-אתמול' },
];

function Chip({ c }: { c: Cond }) {
  const bg = c.met === true ? '#1a7f37' : c.met === false ? '#3d1417' : '#21262d';
  const fg = c.met === true ? '#3fb950' : c.met === false ? '#f85149' : '#6e7681';
  const mark = c.met === true ? '✓' : c.met === false ? '✗' : '·';
  return <span style={{ background: bg, color: fg, border: `1px solid ${fg}33`, borderRadius: 3, padding: '1px 6px', fontSize: 10, whiteSpace: 'nowrap' }}>{mark} {c.label}</span>;
}

export function DayTypeConditionsTable() {
  const [date] = useState<string>(todayISO());
  const [sig, setSig] = useState<Sig | null>(null);
  const [active, setActive] = useState<{ day_type: string; status: string; gate?: string | null; replay?: string | null } | null>(null);
  const [opening, setOpening] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('loading…');

  const load = useCallback(() => {
    // T14 / G-16: conditions from classify_replay, ACTIVE highlight = gate live label.
    Promise.all([
      fetch(`${API}/api/v9/day_type/classify_replay?date=${date}`)
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status)))),
      fetch(`${API}/api/v9/day_type/live`).then((r) => (r.ok ? r.json() : null)).catch(() => null),
    ])
      .then(([d, live]) => {
        const m = d.measured || {}; const bar = d.second_distribution?.bar || {}; const f = d.final || {};
        setSig({ sides: m.sides, rib: m.rib, close_pos: m.close_pos, one_tf: m.one_tf, vol_ratio: m.vol_ratio, narrow_ib: bar.narrow_ib, neck: bar.neck, invalidated: f.invalidated });
        const gate = live?.day_type ? String(live.day_type) : null;
        // P0-2 (one-source): live=null → honest "—" (FORMING); replay kept as audit only
        const shown = gate ?? '—';
        setActive({ day_type: shown, status: gate ? f.status : 'FORMING', gate, replay: f.day_type });
        setOpening(d.opening_type || null);
        const ov = gate && f.day_type && gate !== f.day_type ? ` · gate≠replay(${f.day_type})` : '';
        setStatus(d.n_bars ? `${d.n_bars} bars · ${date}${ov}` : 'no bars yet');
      })
      .catch((e) => setStatus((e as Error).message.includes('HTTP') ? 'offline — restart backend' : 'offline'));
  }, [date]);

  useEffect(() => { load(); const id = setInterval(load, 30000); return () => clearInterval(id); }, [load]);

  const s = sig || {};
  return (
    <div style={{ background: '#0d1117', color: '#c9d1d9', fontFamily: 'ui-monospace, monospace', fontSize: 12, border: '1px solid #21262d', borderRadius: 6, padding: 10, marginBottom: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
        <strong style={{ color: '#e6edf3' }}>סוג היום — תנאים חיים</strong>
        <span style={{ color: '#6e7681', fontSize: 10 }}>{status}</span>
        {active && (
          <span style={{ marginRight: 'auto', color: DT_COLOR[active.day_type] || '#8b949e', fontWeight: 700 }}>
            → {active.day_type} <span style={{ fontSize: 10, color: '#6e7681' }}>[{active.status}]</span>
            {active.gate && active.replay && active.gate !== active.replay && (
              <span style={{ fontSize: 10, color: '#d29922' }} title="display=gate · conditions from classify_replay"> · gate</span>
            )}
          </span>
        )}
        <button onClick={load} style={{ background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d', borderRadius: 4, padding: '2px 8px', fontSize: 11, cursor: 'pointer' }}>↻</button>
      </div>
      {/* live signals strip */}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', fontSize: 10, color: '#8b949e', marginBottom: 8, paddingBottom: 6, borderBottom: '1px solid #21262d' }}>
        <span>sides <b style={{ color: '#c9d1d9' }}>{s.sides ?? '—'}</b></span>
        <span>rib <b style={{ color: '#c9d1d9' }}>{s.rib ?? '—'}</b></span>
        <span>close <b style={{ color: '#c9d1d9' }}>{s.close_pos ?? '—'}</b></span>
        <span>1TF <b style={{ color: '#c9d1d9' }}>{s.one_tf ?? '—'}</b></span>
        <span>vol <b style={{ color: (s.vol_ratio ?? 1) <= 0.5 ? '#f85149' : '#c9d1d9' }}>{s.vol_ratio ?? '—'}×</b></span>
        <span>IB-narrow <b style={{ color: '#c9d1d9' }}>{s.narrow_ib == null ? '—' : s.narrow_ib ? 'yes' : 'no'}</b></span>
        <span>neck <b style={{ color: '#c9d1d9' }}>{s.neck ?? '—'}</b></span>
        {s.invalidated && <span style={{ color: '#f85149', fontWeight: 700 }}>INVALIDATED (oi)</span>}
      </div>
      {/* day-type rows */}
      {DAY_ROWS.map((row) => {
        const isActive = active?.day_type === row.name;
        return (
          <div key={row.name} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '3px 4px', borderRadius: 4, background: isActive ? (DT_COLOR[row.name] || '#8b949e') + '22' : 'transparent' }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: DT_COLOR[row.name] || '#8b949e', flexShrink: 0 }} />
            <span style={{ width: 130, flexShrink: 0, color: isActive ? '#e6edf3' : '#c9d1d9', fontWeight: isActive ? 700 : 400 }}>{row.name}{isActive ? ' ◄' : ''}</span>
            <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>{row.conds(s).map((c, i) => <Chip key={i} c={c} />)}</div>
          </div>
        );
      })}
      {/* opening-type rows */}
      <div style={{ color: '#6e7681', margin: '8px 0 3px', fontSize: 10 }}>סוג פתיחה (זוהה: <b style={{ color: '#bc8cff' }}>{opening ? opening.replace('OPEN_', '') : '—'}</b>)</div>
      {OPEN_ROWS.map((row) => {
        const isActive = opening === row.name;
        return (
          <div key={row.name} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '2px 4px', borderRadius: 4, background: isActive ? '#bc8cff22' : 'transparent' }}>
            <span style={{ width: 150, flexShrink: 0, color: isActive ? '#e6edf3' : '#8b949e', fontWeight: isActive ? 700 : 400 }}>{row.name.replace('OPEN_', '')}{isActive ? ' ◄' : ''}</span>
            <span style={{ fontSize: 10, color: '#6e7681' }}>{row.desc}</span>
          </div>
        );
      })}
    </div>
  );
}
