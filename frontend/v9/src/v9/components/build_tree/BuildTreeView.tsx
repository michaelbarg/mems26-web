'use client';
/**
 * BuildTreeView — redesigned Build Status page as a decision tree (V2).
 *
 * NON-DESTRUCTIVE to data: this is the NEW route (/build) alongside the legacy
 * BuildStatusTab. It consumes the SAME endpoint (/api/v9/build/pattern-status)
 * via useBuildStatus — no backend or trading-logic changes.
 *
 * Source-of-truth (CLAUDE.md Rule 1): renders ONLY fields the backend emits.
 * Components the backend does not yet surface (TARGETS/STOP, Day-Type Matrix
 * verdict, global pre_fire/risk gates, S5 TPO, S6 Killzone) are shown as
 * "⧗ ממתין ל-backend" placeholders — never synthesized in the frontend.
 *
 * Refresh is MANUAL ONLY (useBuildStatus, per Michael 2026-05-26) — no auto-poll.
 *
 * Day-type tables (tab "טבלאות אפיון") mirror static strategy config VERBATIM
 * from backend/v9/systems/day_type/targets_table.py + five_min/atr_caps.py.
 * These are rule-book constants, NOT live values. The PROJECTION of
 * these onto live $/R prices remains a backend gap (TARGETS/STOP stage).
 * NOTE: keep DAY_TARGETS / ATR_MULTIPLIERS / PATTERN_TIME_STOPS in sync with the
 * two config files until the backend exposes them through the endpoint
 * (gap-list item P0/P2 — see BUILD_STATUS_REDESIGN_SPEC_2026-06-04.md).
 *
 * Design + gap analysis: docs/plans/BUILD_STATUS_REDESIGN_MOCKUP_V2_2026-06-04.html
 * and docs/plans/BUILD_STATUS_COMPONENT_AUDIT.md.
 */
import { useMemo, useState, type ReactNode, type CSSProperties } from 'react';
import Link from 'next/link';
import { useBuildStatus } from '../../hooks/useBuildStatus';
import type {
  BuildStatusResponse,
  SystemBlock,
  Pattern,
  Component,
  Readiness,
  ReadinessCheck,
} from '../build_status/types';

/* ------------------------------------------------------------------ */
/* Design tokens — from mockup V2 CSS variables                        */
/* ------------------------------------------------------------------ */

const T = {
  bg: '#0b0b0d',
  s1: '#121214',
  s2: '#161619',
  s3: '#1c1c20',
  line: '#24242a',
  line2: '#2e2e35',
  tp: '#ececf0',
  ts: '#9a9aa4',
  tt: '#646470',
  green: '#22c55e',
  greenD: '#0f2e1c',
  greenLight: '#9be7b4',
  amber: '#f5b441',
  amberD: '#2e2410',
  red: '#ef4444',
  redD: '#2e1414',
  redLight: '#ffb4b4',
  pend: '#7c8cff',
  pendD: '#16172e',
  sys1: '#5b9bff',
  sys2: '#2dd4a7',
  sys3: '#a78bfa',
  sys4: '#fb923c',
  sys5: '#22b8cf',
  sys6: '#8b8b96',
  mono: 'ui-monospace,SFMono-Regular,Menlo,monospace',
  sans: 'system-ui,-apple-system,sans-serif',
  r: '9px',
} as const;

/* ------------------------------------------------------------------ */
/* Static config                                                       */
/* ------------------------------------------------------------------ */

interface SysMeta {
  color: string;
  role: 'firing' | 'observer' | 'gate';
  label: string;
}

// Keyed by SystemBlock.id as emitted by the aggregator.
const SYS_META: Record<string, SysMeta> = {
  day_type: { color: T.sys1, role: 'observer', label: 'S1 · Day Type' },
  five_min: { color: T.sys2, role: 'firing', label: 'S2 · 5-Min Patterns' },
  footprint: { color: T.sys3, role: 'firing', label: 'S3 · Footprint' },
  woodies: { color: T.sys4, role: 'firing', label: 'S4 · Woodies CCI' },
  tpo: { color: T.sys5, role: 'observer', label: 'S5 · TPO' },
  killzone: { color: T.sys6, role: 'gate', label: 'S6 · Killzone' },
  bridge: { color: T.sys6, role: 'gate', label: 'Bridge · Streams' },
};

// Systems we expect per the spec but the aggregator may not wire yet.
const EXPECTED_SYSTEMS = ['day_type', 'five_min', 'footprint', 'woodies', 'tpo', 'killzone'];

const CANONICAL_SOURCES = new Set(['sierra_export', 'db', 'clock']);

const MONO = T.mono;

// Which inspector owns a firing system's TARGETS/STOP exposure (fix-ref).
const INSPECTOR_PATH: Record<string, string> = {
  five_min: 'backend/v9/systems/build_status/s2_inspector.py',
  woodies: 'backend/v9/systems/build_status/woodies_inspector.py',
  footprint: 'backend/v9/systems/build_status/footprint_inspector.py',
};

/* ------------------------------------------------------------------ */
/* Day-type tables — VERBATIM mirror of backend strategy config.       */
/* Source: backend/v9/systems/day_type/targets_table.py (_TARGETS)     */
/*       + backend/v9/systems/five_min/atr_caps.py                     */
/* Static rule-book — keep in sync until backend-exposed.              */
/* ------------------------------------------------------------------ */

interface DayTarget {
  key: string;
  t1: string;
  t2: string;
  t3: string;
  trail: string;
  timeStop: string;
  contracts: number;
  sizing: string;
  noTrade: boolean;
  note: string;
  override?: string;
}

const DAY_TARGETS: DayTarget[] = [
  { key: 'Trend_Normal', t1: '1R', t2: '2R+TPO', t3: '4R+trail', trail: '✓ אחרי T2', timeStop: '—', contracts: 3, sizing: 'AGGRESSIVE', noTrade: false, note: 'Trend Normal: full 3-contract bracket, no time stop, trail after T2' },
  { key: 'Trend_DD', t1: '1R', t2: 'open (cap 4R)', t3: '4R cap', trail: '—', timeStop: '90m', contracts: 3, sizing: 'AGGRESSIVE', noTrade: false, note: 'Trend DD: T2 open-ended, T3 capped 4R, 90min time stop', override: 'תבנית OFA_Initiative → T3 = 6R+trail (D-094 §3.A · Sheet A row 14)' },
  { key: 'Variation', t1: '1R', t2: '2.5R', t3: 'trail', trail: '✓ אחרי T2', timeStop: '60m', contracts: 2, sizing: 'FULL', noTrade: false, note: 'Variation: 2 contracts, T3 trail only, 60min time stop' },
  { key: 'Normal', t1: '1R', t2: 'POC', t3: 'אין T3', trail: '—', timeStop: '30m', contracts: 1, sizing: 'HALF', noTrade: false, note: 'Normal: T2 at POC, no T3, 30min time stop' },
  { key: 'Neutral_Extreme', t1: '1R', t2: 'extreme', t3: 'אין T3', trail: '—', timeStop: '45m', contracts: 1, sizing: 'HALF', noTrade: false, note: 'NeuE (D-091.Q1): T2 at opposite extreme · 45min window · open at VA edge' },
  { key: 'Neutral_Center', t1: '1R', t2: 'extreme', t3: 'אין T3', trail: '—', timeStop: '30m', contracts: 1, sizing: 'HALF', noTrade: false, note: 'NeuC (D-091.Q1): T2 at opposite extreme · 30min window · open inside VA' },
  { key: 'Nontrend', t1: 'n/a', t2: 'n/a', t3: 'n/a', trail: '—', timeStop: 'NO TRADE', contracts: 0, sizing: '—', noTrade: true, note: 'Nontrend: NO TRADE per EXIT_V6 + D-091 Coverage Matrix' },
];

// 1R = ATR14 x multiplier, by pattern family (atr_caps.py ATR_MULTIPLIERS).
const ATR_MULTIPLIERS: [string, number, string][] = [
  ['Reactive', 1.0, 'legacy'],
  ['OFA', 1.5, 'legacy'],
  ['Flag', 1.5, 'legacy'],
  ['Double_BT', 2.0, 'legacy'],
  ['HnS', 2.0, 'legacy'],
  ['OFA_Reactive', 1.5, 'xlsx'],
  ['OFA_Initiative', 2.0, 'xlsx'],
  ['Pennant', 1.5, 'xlsx'],
  ['Wedge', 2.0, 'xlsx'],
  ['Triangle', 2.0, 'xlsx'],
];

// Pattern-axis time stops (atr_caps.py PATTERN_TIME_STOPS) — min(day, pattern).
const PATTERN_TIME_STOPS: [string, number][] = [
  ['Flag', 20],
  ['Pennant', 20],
  ['OFA_Initiative', 20],
  ['OFA_Reactive', 30],
  ['Triangle', 30],
  ['Wedge', 30],
  ['HnS', 30],
  ['Double_BT', 30],
  ['Wyckoff_Spring', 45],
  ['Wyckoff_Upthrust', 45],
];

/* ------------------------------------------------------------------ */
/* Small helpers                                                       */
/* ------------------------------------------------------------------ */

function sysMeta(id: string): SysMeta {
  return SYS_META[id] ?? { color: T.tt, role: 'observer', label: id };
}

function isCanonical(src: string | null | undefined): boolean {
  return !!src && CANONICAL_SOURCES.has(src);
}

function fmtLag(lag: number | null | undefined): string {
  if (lag == null) return '?';
  if (lag < 1) return '<1s';
  if (lag < 60) return `${Math.round(lag)}s`;
  if (lag < 3600) return `${Math.round(lag / 60)}m`;
  return `${Math.round(lag / 3600)}h`;
}

/** 3-tier freshness: FRESH (<60s green), WARMING (60-threshold amber), STALE (>threshold red). */
type FreshTier = 'fresh' | 'warming' | 'stale';
function freshTier(lag: number | null | undefined, threshold: number): FreshTier {
  if (lag == null) return 'stale';
  if (lag < 60) return 'fresh';
  if (lag < threshold) return 'warming';
  return 'stale';
}
const TIER_COLOR: Record<FreshTier, string> = { fresh: T.green, warming: T.amber, stale: T.red };
const TIER_BG: Record<FreshTier, string> = { fresh: T.s1, warming: T.amberD, stale: T.redD };
const TIER_BORDER: Record<FreshTier, string> = { fresh: T.line, warming: '#f5b44145', stale: '#ef444445' };
const TIER_LABEL: Record<FreshTier, string> = { fresh: 'fresh', warming: 'warming', stale: 'stale' };

function fmtET(ts: string | null | undefined): string {
  if (!ts) return '—';
  try {
    return new Date(ts).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'America/New_York',
    });
  } catch {
    return '—';
  }
}

/** Roll a system up to a single verdict from its patterns. */
function systemVerdict(sys: SystemBlock): { label: string; kind: 'fired' | 'armed' | 'blocked' | 'idle' } {
  const fired = sys.patterns.filter((p) => p.fired_today).length;
  const armed = sys.patterns.filter((p) => p.status === 'armed').length;
  const blocked = sys.patterns.filter((p) => p.status === 'blocked' || p.status === 'vetoed').length;
  if (fired > 0) return { label: `ירה ${fired}× היום`, kind: 'fired' };
  if (armed > 0) return { label: `${armed} armed`, kind: 'armed' };
  if (blocked > 0 && armed === 0) return { label: 'חסום', kind: 'blocked' };
  return { label: 'idle', kind: 'idle' };
}

function blockerHebrew(check: ReadinessCheck): string {
  const key = check.key.toLowerCase();
  const detail = check.detail ?? '';
  if (key.includes('snapshot') || detail.includes('snapshot')) return `אין snapshot עדכני — ${detail || 'לא נמצא בחלון הכניסה'}`;
  if (key.includes('freshness') || key.includes('stale') || key.includes('stream')) return `מידע לא עדכני — ${detail || 'הנתונים ישנים מדי'}`;
  if (key.includes('session') || key.includes('rth')) return `מחוץ לשעות מסחר — ${detail || 'RTH לא פעיל'}`;
  if (key.includes('hydrat')) return `המערכת לא טעונה — ${detail || 'חסר hydration'}`;
  if (key.includes('gate') || key.includes('global')) return `gate חסום — ${detail || check.key}`;
  if (key.includes('bridge') || key.includes('connect')) return `אין חיבור לגשר — ${detail || 'bridge לא מחובר'}`;
  if (key.includes('day_type')) return `Day Type לא סווג — ${detail || check.key}`;
  if (key.includes('gray') || key.includes('trend')) return `מגמה תקועה (GRAY) — ${detail || check.key}`;
  return detail || check.key;
}

/** Live day_type from the day_type system (interpretation/live_input) or readiness. */
function currentDayType(data: BuildStatusResponse): string | null {
  const dt = data.systems.find((s) => s.id === 'day_type');
  if (dt) {
    for (const it of dt.interpretations ?? []) {
      if (it.key === 'day_type' && it.value) return it.value;
    }
    for (const inp of dt.live_inputs ?? []) {
      if (inp.field === 'day_type' && inp.value) return inp.value;
    }
  }
  const chk = data.readiness?.checks?.find((c) => c.key === 's1_day_type_classified');
  if (chk?.detail?.startsWith('day_type=')) {
    const v = chk.detail.slice('day_type='.length).trim();
    if (v && v !== 'None' && v !== 'UNKNOWN' && v !== 'unknown') return v;
  }
  return null;
}

/* ------------------------------------------------------------------ */
/* Pulse animation — injected once via <style> tag                     */
/* ------------------------------------------------------------------ */

const PULSE_CSS = `@keyframes mems26pulse{0%,100%{opacity:1}50%{opacity:.3}}`;

function PulseStyle() {
  return <style dangerouslySetInnerHTML={{ __html: PULSE_CSS }} />;
}

/* ------------------------------------------------------------------ */
/* Tiny presentational atoms                                           */
/* ------------------------------------------------------------------ */

type TagKind = 'live' | 'pend' | 'cfg';
function Tag({ kind, label }: { kind: TagKind; label?: string }) {
  const map: Record<TagKind, { fg: string; bg: string; bd: string; t: string }> = {
    live: { fg: T.greenLight, bg: T.greenD, bd: '#22c55e30', t: '● חי' },
    pend: { fg: T.pend, bg: T.pendD, bd: '#7c8cff40', t: '⧗ ממתין ל-backend' },
    cfg: { fg: T.sys5, bg: '#0e2a30', bd: '#22b8cf40', t: '📖 אפיון' },
  };
  const s = map[kind];
  return (
    <span style={{ fontFamily: MONO, fontSize: 9, fontWeight: 700, padding: '1px 7px', borderRadius: 5, color: s.fg, background: s.bg, boxShadow: `inset 0 0 0 1px ${s.bd}`, whiteSpace: 'nowrap' }}>
      {label ?? s.t}
    </span>
  );
}

/** "↳ לתיקון:" pointer to where a not-OK / pending condition is fixed. */
function FixRef({ children, pend }: { children: ReactNode; pend?: boolean }) {
  return (
    <div style={{ marginTop: 7, fontFamily: MONO, fontSize: 10.5, color: T.ts, display: 'flex', gap: 6, lineHeight: 1.5 }}>
      <span style={{ color: T.tt, flex: '0 0 auto' }}>↳ לתיקון:</span>
      <span style={{ color: pend ? T.pend : T.amber }}>{children}</span>
    </div>
  );
}

/** Inline code path (LTR, monospace, tinted). */
function Path({ children, pend }: { children: ReactNode; pend?: boolean }) {
  return (
    <code style={{ direction: 'ltr', unicodeBidi: 'isolate', fontFamily: MONO, fontSize: 10, padding: '1px 6px', borderRadius: 4, color: pend ? T.pend : T.amber, background: pend ? T.pendD : T.amberD }}>
      {children}
    </code>
  );
}

function SrcPill({ source }: { source: string | null | undefined }) {
  if (!source) return null;
  const canon = isCanonical(source);
  return (
    <span
      style={{
        fontFamily: MONO,
        fontSize: 9.5,
        padding: '2px 7px',
        borderRadius: 5,
        marginInlineStart: 6,
        color: canon ? T.green : T.amber,
        background: canon ? T.greenD : T.amberD,
        boxShadow: canon ? 'none' : 'inset 0 0 0 1px #f5b44140',
      }}
    >
      {source}
      {canon ? '' : ' ⚠'}
    </span>
  );
}

type StepKind = 'ok' | 'bad' | 'wait' | 'info' | 'pend';
function StepIcon({ kind }: { kind: StepKind }) {
  const map: Record<StepKind, { bg: string; fg: string; ch: string }> = {
    ok: { bg: T.greenD, fg: T.green, ch: '✓' },
    bad: { bg: T.redD, fg: T.red, ch: '✕' },
    wait: { bg: T.amberD, fg: T.amber, ch: '!' },
    info: { bg: T.s2, fg: T.ts, ch: 'i' },
    pend: { bg: T.pendD, fg: T.pend, ch: '⧗' },
  };
  const s = map[kind];
  return (
    <span
      style={{
        width: 24,
        height: 24,
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 11,
        fontWeight: 700,
        fontFamily: MONO,
        background: s.bg,
        color: s.fg,
        flex: '0 0 auto',
        zIndex: 1,
      }}
    >
      {s.ch}
    </span>
  );
}

function Step({
  kind,
  last,
  title,
  children,
}: {
  kind: StepKind;
  last?: boolean;
  title: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '24px 1fr', gap: 14, paddingBottom: last ? 0 : 16 }}>
      <div style={{ position: 'relative', display: 'flex', justifyContent: 'center' }}>
        <StepIcon kind={kind} />
        {!last && (
          <div style={{ position: 'absolute', top: 24, bottom: -16, width: 2, background: T.line2 }} />
        )}
      </div>
      <div>
        <div style={{ fontFamily: MONO, fontSize: 12.5, fontWeight: 600, color: T.tp, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>{title}</div>
        {children && <div style={{ marginTop: 5, fontSize: 12, color: T.ts, lineHeight: 1.6 }}>{children}</div>}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Component table (drill-down)                                        */
/* ------------------------------------------------------------------ */

function ComponentTable({ components }: { components: Component[] }) {
  if (!components || components.length === 0) {
    return <div style={{ padding: 8, fontSize: 10, color: T.tt, fontStyle: 'italic' }}>אין נתוני רכיבים.</div>;
  }
  const th: CSSProperties = { padding: '4px 8px', fontWeight: 500, textAlign: 'start', color: T.tt, fontSize: 10, textTransform: 'uppercase' as const, letterSpacing: '.5px' };
  return (
    <div style={{ background: T.s1, padding: '6px 12px 8px 28px', overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: MONO, fontSize: 10 }}>
        <thead>
          <tr>
            <th style={th}>stage</th>
            <th style={th}>key</th>
            <th style={th}>required</th>
            <th style={{ ...th, direction: 'ltr' as const }}>live</th>
            <th style={{ ...th, textAlign: 'center' }}>present</th>
            <th style={th}>source</th>
            <th style={{ ...th, textAlign: 'center' }}>freshness</th>
          </tr>
        </thead>
        <tbody>
          {components.map((c, i) => {
            const cLag = c.freshness?.lag_s;
            const cTier: FreshTier = cLag == null ? 'stale' : cLag < 60 ? 'fresh' : cLag < 660 ? 'warming' : 'stale';
            return (
            <tr key={`${c.stage}-${c.key}-${i}`} style={{ borderTop: i > 0 ? `1px solid ${T.line}` : 'none', color: c.present ? T.tp : T.redLight }}>
              <td style={{ padding: '3px 8px', color: T.ts }}>{c.stage}</td>
              <td style={{ padding: '3px 8px', color: T.ts }}>{c.key}</td>
              <td style={{ padding: '3px 8px', color: T.tt }}>{c.required ?? c.spec ?? '—'}</td>
              <td style={{ padding: '3px 8px', direction: 'ltr' as const, color: T.tp }}>{c.live ?? c.value ?? '—'}</td>
              <td style={{ padding: '3px 8px', textAlign: 'center' }}>
                {c.present ? (
                  <span style={{ color: T.green }}>✓</span>
                ) : (
                  <span style={{ color: T.red }}>✕</span>
                )}
              </td>
              <td style={{ padding: '3px 8px' }}>{c.freshness?.source ? <SrcPill source={c.freshness.source} /> : <span style={{ color: T.tt }}>—</span>}</td>
              <td style={{ padding: '3px 8px', textAlign: 'center', fontFamily: MONO, fontSize: 9 }}>
                {cLag != null ? (
                  <span style={{ color: TIER_COLOR[cTier], padding: '1px 5px', borderRadius: 3, background: TIER_BG[cTier] }}>
                    {fmtLag(cLag)}
                  </span>
                ) : (
                  <span style={{ color: T.tt }}>—</span>
                )}
              </td>
            </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Pattern row                                                         */
/* ------------------------------------------------------------------ */

const PATTERN_BADGE: Record<string, { fg: string; bg: string }> = {
  fired: { fg: T.green, bg: T.greenD },
  armed: { fg: T.amber, bg: T.amberD },
  blocked: { fg: T.red, bg: T.redD },
  vetoed: { fg: T.redLight, bg: T.redD },
  not_applicable: { fg: T.tt, bg: T.s2 },
  unknown: { fg: T.tt, bg: T.s2 },
};

function PatternRow({ pattern }: { pattern: Pattern }) {
  const [open, setOpen] = useState(false);
  const b = PATTERN_BADGE[pattern.status] ?? PATTERN_BADGE.unknown;
  return (
    <div style={{ borderTop: `1px solid ${T.line}` }}>
      <div
        onClick={() => setOpen((o) => !o)}
        style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 10px', cursor: 'pointer', background: open ? T.s2 : 'transparent' }}
      >
        <span style={{ color: T.tt, fontSize: 10 }}>{open ? '▼' : '▶'}</span>
        <span style={{ fontFamily: MONO, fontSize: 11, fontWeight: 600, color: T.tp, minWidth: 150 }}>
          {pattern.name}
          <span style={{ display: 'block', fontSize: 9, fontWeight: 400, color: T.tt }}>{pattern.id}</span>
        </span>
        <span style={{ fontFamily: MONO, fontSize: 10, fontWeight: 700, color: b.fg, background: b.bg, padding: '2px 9px', borderRadius: 5 }}>
          {pattern.label || pattern.status}
        </span>
        <span style={{ flex: 1, fontSize: 11, color: T.ts }}>{pattern.reason}</span>
        <span style={{ fontFamily: MONO, fontSize: 10, color: pattern.fired_today ? T.green : T.tt }}>{fmtET(pattern.last_fire_ts)}</span>
      </div>
      {open && <ComponentTable components={pattern.components} />}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Legend — the defining live vs ממתין ל-backend language              */
/* ------------------------------------------------------------------ */

function Legend() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 18, flexWrap: 'wrap', marginTop: 16, padding: '10px 16px', borderRadius: T.r, background: T.s1, border: `1px solid ${T.line}`, fontFamily: MONO, fontSize: 11.5 }}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, color: T.ts }}>
        <Tag kind="live" /> <b style={{ color: T.tp, fontWeight: 600 }}>נפלט מ-/api/v9/build/pattern-status</b>
      </span>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, color: T.ts }}>
        <Tag kind="pend" /> <b style={{ color: T.tp, fontWeight: 600 }}>השדה לא נפלט עדיין — לא מסונתז ב-frontend</b>
      </span>
      <span style={{ flex: 1 }} />
      <span style={{ color: T.tt }}>מקור-אמת · CLAUDE.md Rule 1: חסר = "ממתין ל-backend", לא ערך מומצא</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Global firewall — pre_fire_validator + risk_checks (P0, pending)    */
/* ------------------------------------------------------------------ */

// Structured pre_fire_validator checks — 7 gate checks per spec.
const PRE_FIRE_CHECKS: { key: string; spec: string; required: string; source: string }[] = [
  { key: 'side_match', spec: 'side == direction from trend', required: 'side ∈ {LONG,SHORT} matches trend_state', source: 'pre_fire_validator.py' },
  { key: 'ordering', spec: 'entry/stop ordering correct', required: 'LONG: entry>stop · SHORT: entry<stop', source: 'pre_fire_validator.py' },
  { key: 'r_r_gate', spec: 'R:R ≥ 1.0', required: 'r_t1 >= 1.0', source: 'pre_fire_validator.py' },
  { key: 'confidence', spec: 'confidence ≥ threshold', required: 'conf >= system.min_conf', source: 'pre_fire_validator.py' },
  { key: 'time_stop', spec: 'time_stop valid', required: 'min(day,pattern) > 0', source: 'pre_fire_validator.py' },
  { key: 'not_provisional', spec: 'entry/stop ≠ provisional', required: 'no provisional values', source: 'pre_fire_validator.py' },
  { key: 'dedup', spec: 'no duplicate fire', required: '!fired_this_bar', source: 'pre_fire_validator.py' },
];

// Structured risk_checks — LIVE caps per spec.
const RISK_CHECKS: { key: string; spec: string; required: string; source: string }[] = [
  { key: 'daily_loss', spec: 'הפסד יומי מצטבר', required: '< $250', source: 'risk_checks.py' },
  { key: 'max_trades', spec: 'עסקאות ביום', required: '≤ 5', source: 'risk_checks.py' },
  { key: 'max_contracts', spec: 'חוזים בו-זמנית', required: '≤ 2', source: 'risk_checks.py' },
  { key: 'cutoff_time', spec: 'שעת חיתוך', required: '< 14:30 ET', source: 'risk_checks.py' },
  { key: 'consec_losses', spec: 'עצירה אחרי הפסדים רצופים', required: 'consecutive_losses < 2', source: 'risk_checks.py' },
  { key: 'news_block', spec: 'חסימת חדשות', required: '±10m from high-impact', source: 'risk_checks.py (לא ממומש)' },
];

function GlobalFirewall({ data }: { data: BuildStatusResponse }) {
  // Try to extract live pre_fire/risk status from any system that exposes them
  const allComps = data.systems.flatMap((s) => s.patterns.flatMap((p) => p.components ?? []));
  const findLive = (key: string) => allComps.find((c) => c.key === key);

  const renderGate = (checks: typeof PRE_FIRE_CHECKS, label: string, sub: string, fix: string) => (
    <div style={{ border: '1px dashed #7c8cff55', borderRadius: T.r, background: T.pendD, padding: '14px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: T.pend, flex: '0 0 auto' }} />
        <span style={{ fontFamily: MONO, fontWeight: 700, fontSize: 13, color: T.tp }}>{label}</span>
        <Tag kind="pend" />
      </div>
      <div style={{ marginTop: 7, fontSize: 11.5, color: T.ts, lineHeight: 1.6 }}>{sub}</div>
      <div style={{ marginTop: 10, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '3px 16px', fontFamily: MONO, fontSize: 11, color: T.ts }}>
        {checks.map((ch) => {
          const live = findLive(ch.key);
          const present = live?.present;
          return (
            <span key={ch.key}>
              {live != null ? (
                <span style={{ color: present ? T.green : T.red }}>{present ? '✓ ' : '✕ '}</span>
              ) : (
                <span style={{ color: T.pend }}>⧗ </span>
              )}
              {ch.spec}
            </span>
          );
        })}
      </div>
      <FixRef pend>
        חשוף מ-<Path pend>{fix}</Path> → <Path pend>aggregator.py</Path>
      </FixRef>
    </div>
  );

  return (
    <div style={{ marginTop: 18 }}>
      <SLab>
        שערי-אש גלובליים · חלים על כל מערכת יורה <Tag kind="pend" label="⧗ ממתין ל-backend · P0" />
      </SLab>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {renderGate(PRE_FIRE_CHECKS, 'pre_fire_validator', '7 בדיקות שרצות לפני כל ירי, היום רק בתוך כל מערכת — לא נפלטות ל-endpoint. צריך שורת gate גלובלית אחת שמראה אילו עברו.', 'backend/v9/shared/pre_fire_validator.py')}
        {renderGate(RISK_CHECKS, 'risk_checks · LIVE caps', 'תקרות הסיכון ל-LIVE — קריטי לפני מסחר אמיתי. כרגע לא מיוצגות בשום מקום בעמוד.', 'backend/v9/gateway/risk_checks.py')}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Layer-0 sources strip (live data_freshness)                         */
/* ------------------------------------------------------------------ */

function SourcesStrip({ systems }: { systems: SystemBlock[] }) {
  const sources = systems.filter((s) => s.id !== 'bridge');
  if (sources.length === 0) return null;
  return (
    <div>
      <SLab>
        שכבה 0 · מקורות חיים — Sierra → bridge → API <Tag kind="live" label="● חי · data_freshness" />
      </SLab>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 10, marginBottom: 24 }}>
        {sources.map((s) => {
          const lag = s.data_freshness?.lag_seconds;
          const thresh = s.data_freshness?.threshold_seconds ?? 300;
          const tier = freshTier(lag, thresh);
          const meta = sysMeta(s.id);
          const isBad = tier === 'stale';
          return (
            <div key={s.id} style={{ padding: '11px 12px', borderRadius: T.r, background: isBad ? T.redD : T.s1, border: `1px solid ${isBad ? '#ef444445' : T.line}` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontFamily: MONO, fontSize: 12, color: T.tp, fontWeight: 600 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: TIER_COLOR[tier], flex: '0 0 auto' }} />
                {meta.label.replace(/^S\d+ · /, '')}
              </div>
              <div style={{ marginTop: 6, fontFamily: MONO, fontSize: 10 }}>
                <span style={{ color: TIER_COLOR[tier] }}>{TIER_LABEL[tier]} {fmtLag(lag)}</span>
                <span style={{ color: T.tt }}> · {s.data_freshness?.fresh !== undefined ? (lag != null ? `סף ${thresh}s` : '') : ''}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Section label                                                       */
/* ------------------------------------------------------------------ */

function SLab({ children }: { children: ReactNode }) {
  return (
    <div style={{ fontSize: 10, color: T.tt, textTransform: 'uppercase' as const, letterSpacing: '.8px', fontFamily: MONO, margin: '0 2px 10px', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
      {children}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Context bar — direction agreement + day type + killzone              */
/* ------------------------------------------------------------------ */

function ContextBar({ data, activeDay }: { data: BuildStatusResponse; activeDay: string | null }) {
  // Compute direction agreement from firing systems
  const firingSystems = data.systems.filter((s) => sysMeta(s.id).role === 'firing');
  let longCount = 0;
  let shortCount = 0;
  let blockedCount = 0;
  for (const sys of firingSystems) {
    const v = systemVerdict(sys);
    if (v.kind === 'blocked') { blockedCount++; continue; }
    // Check interpretations for direction
    const dir = sys.interpretations?.find((it) => it.key === 'direction' || it.key === 'trend_state')?.value;
    if (dir && (dir.toUpperCase().includes('LONG') || dir.toUpperCase() === 'BLUE' || dir.toUpperCase() === 'UP')) longCount++;
    else if (dir && (dir.toUpperCase().includes('SHORT') || dir.toUpperCase() === 'RED' || dir.toUpperCase() === 'DOWN')) shortCount++;
  }

  const kzWired = data.systems.some((s) => s.id === 'killzone');

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 22, flexWrap: 'wrap', padding: '12px 16px', borderRadius: T.r, background: T.s1, border: `1px solid ${T.line}`, fontFamily: MONO, fontSize: 12, marginBottom: 18 }}>
      <span>
        <span style={{ color: T.tt }}>הסכמת כיוון:</span>{' '}
        <span style={{ color: T.tp, fontWeight: 600 }}>
          {longCount > 0 && <span style={{ color: T.green }}>{longCount} LONG</span>}
          {shortCount > 0 && <span style={{ color: T.red }}>{shortCount > 0 && longCount > 0 ? ' / ' : ''}{shortCount} SHORT</span>}
          {blockedCount > 0 && <span style={{ color: T.tt }}>{(longCount > 0 || shortCount > 0) ? ' / ' : ''}{blockedCount} חסום</span>}
          {longCount === 0 && shortCount === 0 && blockedCount === 0 && <span style={{ color: T.tt }}>—</span>}
        </span>
      </span>
      <span style={{ width: 1, height: 16, background: T.line2 }} />
      <span>
        <span style={{ color: T.tt }}>Day Type:</span>{' '}
        <span style={{ color: T.sys1, fontWeight: 600 }}>{activeDay ?? <span style={{ color: T.tt }}>לא סווג</span>}</span>
      </span>
      <span style={{ width: 1, height: 16, background: T.line2 }} />
      <span>
        <span style={{ color: T.tt }}>Killzone:</span>{' '}
        {kzWired ? (
          <span style={{ color: T.tp, fontWeight: 600 }}>מחווט</span>
        ) : (
          <span style={{ color: T.pend, fontWeight: 600 }}>⧗ ממתין · KZ לא מחווט</span>
        )}
      </span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* System branch                                                       */
/* ------------------------------------------------------------------ */

// Field schema synced VERBATIM with CC_PROMPT_P0_2_EXPOSE_TARGETS_STOP_2026-06-04.md.
const TARGETS_SCHEMA: Record<string, [string, string][]> = {
  five_min: [
    ['stop_price', 'structural_anchor / ATR cap / floor'],
    ['risk_1R', 'מרחק הסטופ = 1R'],
    ['t1_price', '+1R'],
    ['t2_price', '+2R / TPO'],
    ['t3_price', '+4R / trail'],
    ['r_t1', 'מול min_r_t1_threshold (הגייט האמיתי)'],
    ['time_stop', 'min(day, pattern)'],
    ['sizing', 'full / half / reject'],
    ['variant_tag', 'VSA variant'],
  ],
  woodies: [
    ['stop_price', 'primary 3 ticks / ATR-cap×group / floor'],
    ['atr_14_ticks', 'לקביעת ה-cap'],
    ['r_t1', 'מול min_r_t1_threshold (הגייט האמיתי)'],
    ['t1_price', 'ticks לפי תבנית'],
    ['t2_price', 'ticks לפי תבנית'],
    ['entry_price', 'trigger'],
    ['matrix_verdict', 'Day-Type Matrix ✅/⚠️/❌'],
  ],
  footprint: [
    ['stop_price', 'min(low, entry−tick)'],
    ['t1', '+risk'],
    ['t2', '+2R'],
    ['time_stop', '15m'],
  ],
};

/**
 * TargetsStopLive — renders TARGETS/STOP from live backend components.
 *
 * Reads components with stage="targets_stop" from the pattern-status response.
 * Rule 1: null/missing → "⧗ ממתין" (never synthesized).
 */
function TargetsStopLive({ patterns }: { patterns: Pattern[] }) {
  // Collect targets_stop components across all patterns
  const entries: { pid: string; comps: Component[] }[] = [];
  for (const p of patterns) {
    const ts = (p.components ?? []).filter((c) => c.stage === 'targets_stop');
    if (ts.length > 0) entries.push({ pid: p.id, comps: ts });
  }

  if (entries.length === 0) {
    return (
      <div style={{ fontFamily: MONO, fontSize: 11, color: T.tt, padding: '6px 0' }}>
        detection pending — stop/targets ייחשפו כש-pattern detected
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {entries.map(({ pid, comps }) => {
        const get = (key: string) => comps.find((c) => c.key === key);
        const stopC = get('stop_price');
        const r_t1C = get('r_t1_gate');
        const tgtC = get('targets');
        const sizeC = get('sizing_time_stop');
        const matrixC = get('day_type_matrix');

        const stopLive = stopC?.live ?? '—';
        const r_t1Live = r_t1C?.live ?? null;
        const r_t1Ok = r_t1C?.present ?? false;
        const tgtLive = tgtC?.live ?? '—';

        return (
          <div key={pid} style={{ border: `1px solid ${T.line}`, borderRadius: 6, background: T.s2, padding: '8px 12px' }}>
            <div style={{ fontFamily: MONO, fontSize: 11, fontWeight: 700, color: T.tp, marginBottom: 6 }}>{pid}</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '3px 16px', fontFamily: MONO, fontSize: 11 }}>
              {/* Stop */}
              <div style={{ color: T.ts }}>stop</div>
              <div style={{ direction: 'ltr', color: stopLive === '—' ? T.pend : T.tp }}>{stopLive === '—' ? '⧗ ממתין' : stopLive}</div>
              {/* R:R gate */}
              <div style={{ color: T.ts }}>r_t1</div>
              <div style={{ direction: 'ltr', color: r_t1Live == null ? T.pend : r_t1Ok ? T.green : T.red }}>
                {r_t1Live == null || r_t1Live === 'null' ? '⧗ ממתין' : r_t1Live}
                {r_t1Live != null && r_t1Live !== 'null' && <span style={{ color: r_t1Ok ? T.green : T.red, marginInlineStart: 6 }}>{r_t1Ok ? '✓' : '✕'}</span>}
              </div>
              {/* Targets */}
              <div style={{ color: T.ts }}>targets</div>
              <div style={{ direction: 'ltr', color: tgtLive === '—' ? T.pend : T.tp }}>{tgtLive === '—' ? '⧗ ממתין' : tgtLive}</div>
              {/* Sizing / time_stop (S2 only) */}
              {sizeC && (
                <>
                  <div style={{ color: T.ts }}>sizing / time</div>
                  <div style={{ direction: 'ltr', color: T.tp }}>{sizeC.live ?? sizeC.value ?? '—'}</div>
                </>
              )}
              {/* Day-Type Matrix verdict (S4 only) */}
              {matrixC && (
                <>
                  <div style={{ color: T.ts }}>matrix</div>
                  <div style={{ direction: 'ltr', color: matrixC.present ? T.green : T.red }}>{matrixC.live ?? matrixC.value ?? '—'}</div>
                </>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Pending TARGETS/STOP slot                                           */
/* ------------------------------------------------------------------ */

function PendingTargetsSlot({ sysId }: { sysId: string }) {
  const schema = TARGETS_SCHEMA[sysId];
  if (!schema) return null;
  return (
    <div style={{ marginTop: 10, border: '1px dashed #7c8cff55', borderRadius: 8, background: T.pendD, padding: '12px 14px' }}>
      <div style={{ fontFamily: MONO, fontSize: 11, color: T.pend, fontWeight: 700, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
        ⧗ סכמת השדות שיוצגו (מ-inspector עתידי, לא מומצא)
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(140px,1fr))', gap: '4px 16px', fontFamily: MONO, fontSize: 11 }}>
        {schema.map(([fk, fs]) => (
          <div key={fk} style={{ display: 'flex', justifyContent: 'space-between', gap: 8, padding: '2px 0', borderBottom: '1px dotted #7c8cff22', color: T.ts }}>
            <span style={{ color: T.tp }}>{fk}</span>
            <span style={{ color: T.tt }}>{fs}</span>
          </div>
        ))}
      </div>
      <FixRef pend>
        חשוף את מנוע ה-stop ב-<Path pend>{INSPECTOR_PATH[sysId] ?? 'inspector'}</Path>
      </FixRef>
      <div style={{ marginTop: 8, fontSize: 10.5, color: T.tt, lineHeight: 1.5 }}>
        סולם-מחיר ויזואלי (entry/stop/T1-T3) ייווצר רק כשכל השדות present=true. עד אז — slot ריק מסומן, לא מספרים.
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Day-Type Matrix verdict for S4 — ✅/⚠️/❌ per pattern×day_type      */
/* ------------------------------------------------------------------ */

// Woodies pattern families mapped to their day-type compatibility.
const WOODIES_PATTERNS = [
  'ZLR', 'GB100', 'GB50', 'RB100', 'RB50',
  'TLB', 'HFE', 'FAMIR', 'GHOST',
];

/** Map day_type to which pattern families are allowed/limited. */
function dayTypePatternVerdict(dayType: string | null, patternId: string): '✅' | '⚠️' | '❌' {
  if (!dayType) return '⚠️'; // unknown day -> cautious
  const d = dayType.toLowerCase();
  const p = patternId.toUpperCase();
  if (d === 'nontrend') return '❌';
  if (d.startsWith('trend')) return '✅';
  if (d === 'variation') return (p === 'GHOST' || p === 'FAMIR') ? '⚠️' : '✅';
  if (d === 'normal') return (p.startsWith('ZLR') || p.startsWith('GB') || p.startsWith('RB')) ? '✅' : '❌';
  if (d.startsWith('neutral')) return p.startsWith('ZLR') ? '⚠️' : '❌';
  return '⚠️';
}

function entryHint(dayType: string | null): string {
  if (!dayType) return '—';
  const d = dayType.toLowerCase();
  if (d === 'nontrend') return 'NO TRADE';
  if (d.startsWith('trend_dd')) return 'full bracket · 90m stop · OFA→6R';
  if (d.startsWith('trend')) return 'full bracket · trail after T2';
  if (d === 'variation') return '2 contracts · T3 trail · 60m stop';
  if (d === 'normal') return '1 contract · T2@POC · 30m stop';
  if (d === 'neutral_extreme') return '1 contract · T2@extreme · 45m · VA edge';
  if (d === 'neutral_center') return '1 contract · T2@extreme · 30m · inside VA';
  return '—';
}

function t1Ref(dayType: string | null): string {
  if (!dayType) return '—';
  const dt = DAY_TARGETS.find((d) => d.key === dayType);
  return dt ? `T1=${dt.t1}` : '—';
}

function DayTypeMatrixVerdict({ patterns, activeDay }: { patterns: Pattern[]; activeDay: string | null }) {
  const pids = patterns.length > 0
    ? patterns.map((p) => p.id.replace(/^woodies_/, '').toUpperCase())
    : WOODIES_PATTERNS;

  const hasMatrix = patterns.some((p) => (p.components ?? []).some((c) => c.key === 'day_type_matrix'));

  return (
    <Step kind={activeDay ? 'ok' : 'pend'} title={<>Day-Type Matrix · S4 verdict {activeDay ? <Tag kind="live" /> : <Tag kind="pend" />}</>}>
      {!activeDay ? (
        <span style={{ color: T.tt }}>Day Type לא סווג — אין verdict.</span>
      ) : (
        <div>
          <div style={{ fontFamily: MONO, fontSize: 11, color: T.ts, marginBottom: 8 }}>
            יום חי: <b style={{ color: T.sys1 }}>{activeDay}</b> · {entryHint(activeDay)} · {t1Ref(activeDay)}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 8px', fontFamily: MONO, fontSize: 11 }}>
            {pids.map((pid) => {
              const v = dayTypePatternVerdict(activeDay, pid);
              const liveComp = patterns.find((p) => p.id.toUpperCase().includes(pid))
                ?.components?.find((c) => c.key === 'day_type_matrix');
              const displayV = liveComp ? (liveComp.present ? '✅' : '❌') : v;
              const color = displayV === '✅' ? T.green : displayV === '⚠️' ? T.amber : T.red;
              return (
                <span key={pid} style={{ padding: '3px 8px', borderRadius: 5, border: `1px solid ${T.line}`, background: T.s2 }}>
                  <span style={{ color }}>{displayV}</span>{' '}
                  <span style={{ color: T.ts }}>{pid}</span>
                  {liveComp && <SrcPill source="in_memory" />}
                </span>
              );
            })}
          </div>
          {!hasMatrix && (
            <div style={{ marginTop: 6, fontFamily: MONO, fontSize: 10, color: T.tt }}>
              verdict מחושב מטבלת-אפיון סטטית · backend matrix = <span style={{ color: T.pend }}>⧗ ממתין</span>
            </div>
          )}
        </div>
      )}
    </Step>
  );
}

function SystemBranch({ sys, defaultOpen, activeDay }: { sys: SystemBlock; defaultOpen?: boolean; activeDay: string | null }) {
  const [open, setOpen] = useState(!!defaultOpen);
  const meta = sysMeta(sys.id);
  const isFiring = meta.role === 'firing';
  const verdict = systemVerdict(sys);
  const vbColor =
    verdict.kind === 'fired' ? T.green : verdict.kind === 'armed' ? T.amber : verdict.kind === 'blocked' ? T.red : T.ts;
  const vbBg =
    verdict.kind === 'fired' ? T.greenD : verdict.kind === 'armed' ? T.amberD : verdict.kind === 'blocked' ? T.redD : T.s2;
  const vbShadow =
    verdict.kind === 'idle' ? `inset 0 0 0 1px ${T.line}` : 'none';

  const lag = sys.data_freshness?.lag_seconds;
  const thresh = sys.data_freshness?.threshold_seconds ?? 300;
  const tier = freshTier(lag, thresh);
  const gates = sys.global_gates ?? [];
  const inputs = sys.live_inputs ?? [];
  const interps = sys.interpretations ?? [];
  const gatesOk = gates.length > 0 ? gates.every((g) => g.present) : null;

  // Check if system is disabled (e.g. FOOTPRINT_DISABLED)
  const isDisabled = !sys.running && !sys.hydrated;

  // Role badge style
  const roleStyle: CSSProperties = {
    fontSize: 9,
    fontFamily: MONO,
    padding: '2px 7px',
    borderRadius: 5,
    textTransform: 'uppercase' as const,
    letterSpacing: '.5px',
    color: meta.role === 'firing' ? meta.color : meta.role === 'observer' ? T.sys1 : T.sys6,
    background: T.s2,
    boxShadow: `inset 0 0 0 1px ${meta.role === 'firing' ? `${meta.color}40` : meta.role === 'observer' ? '#5b9bff40' : '#8b8b9640'}`,
  };

  // Has live targets_stop data?
  const hasLiveTargets = sys.patterns.some((p) => (p.components ?? []).some((c) => c.stage === 'targets_stop' && c.present));

  return (
    <div style={{ border: `1px solid ${T.line}`, borderRadius: T.r, marginBottom: 12, background: T.s1, overflow: 'hidden', opacity: isDisabled ? 0.92 : 1 }}>
      {/* header */}
      <div
        onClick={() => setOpen((o) => !o)}
        style={{ display: 'flex', alignItems: 'center', gap: 13, padding: '14px 16px', cursor: 'pointer' }}
      >
        {/* 4px accent stripe */}
        <span style={{ width: 4, alignSelf: 'stretch', borderRadius: 4, flex: '0 0 auto', margin: '-2px 0', background: meta.color }} />
        <span style={{ fontFamily: MONO, fontWeight: 700, fontSize: 14, color: meta.color }}>{meta.label}</span>
        <span style={roleStyle}>{meta.role}</span>
        <span style={{ flex: 1 }} />
        <span style={{ fontFamily: MONO, fontSize: 10, color: tier === 'stale' ? T.red : T.ts, direction: 'ltr' as const }}>
          {meta.label.replace(/^S\d+ · /, '').toLowerCase()} · {TIER_LABEL[tier]} {fmtLag(lag)}
        </span>
        <span style={{ fontFamily: MONO, fontSize: 11, fontWeight: 700, color: vbColor, background: vbBg, padding: '4px 11px', borderRadius: 6, boxShadow: vbShadow }}>
          {isDisabled ? `מושבת` : verdict.label}
        </span>
        <span style={{ color: T.tt, transition: '.18s', fontSize: 11, transform: open ? 'rotate(-90deg)' : 'none' }}>◀</span>
      </div>

      {open && (
        <div style={{ borderTop: `1px solid ${T.line}`, padding: '18px 20px 20px' }}>
          {/* Disabled banner */}
          {isDisabled && (
            <div style={{ margin: '-4px 0 14px', padding: '9px 12px', borderRadius: 7, background: T.s2, border: `1px solid ${T.line}`, fontFamily: MONO, fontSize: 11, color: T.ts }}>
              ⏻ <b style={{ color: T.amber }}>מושבת</b> — כל העיבוד מדולג. <Tag kind="pend" />
              <FixRef pend>
                הדגל ב-<Path pend>{INSPECTOR_PATH[sys.id] ?? 'inspector'}</Path>
              </FixRef>
            </div>
          )}

          <div className="steps">
            {/* 1 SOURCE */}
            <Step kind={tier === 'fresh' ? 'ok' : tier === 'warming' ? 'wait' : 'bad'} title={
              <>מקור · stream freshness{' '}
                {tier !== 'stale' && <SrcPill source={sys.data_freshness?.fresh !== undefined ? 'sierra_export' : undefined} />}
                {' '}<Tag kind="live" />
              </>
            }>
              <span style={{ color: TIER_COLOR[tier] }}>{tier === 'fresh' ? 'טרי' : tier === 'warming' ? 'ממתין לבר הבא' : 'תקוע'}</span> · lag{' '}
              <span style={{ direction: 'ltr', unicodeBidi: 'isolate' } as CSSProperties}>{fmtLag(lag)}</span> · סף {thresh}s · last_bar{' '}
              <span style={{ direction: 'ltr', unicodeBidi: 'isolate' } as CSSProperties}>{fmtET(sys.data_freshness?.last_bar_ts)}</span>
              {tier === 'warming' && (
                <div style={{ marginTop: 4, fontFamily: MONO, fontSize: 10, color: T.tt }}>
                  נתון 5-דקות מתיישן בין ברים — תקין. stale רק מעל {thresh}s.
                </div>
              )}
              {tier === 'stale' && (
                <FixRef>
                  יצוא Sierra תקוע — runbook <Path>docs/runbooks/SIERRA_DLL_OPS.md</Path> · log <Path>/tmp/bridge.err.log</Path>
                </FixRef>
              )}
            </Step>

            {/* 2 INPUT */}
            <Step kind={inputs.length ? 'ok' : 'info'} title={<>קלט · live_inputs {inputs.length ? <Tag kind="live" /> : <Tag kind="pend" />}</>}>
              {inputs.length === 0 ? (
                <>
                  <span style={{ color: T.tt }}>ממתין ל-backend — ה-inspector לא פולט live_inputs למערכת זו.</span>
                  {INSPECTOR_PATH[sys.id] && (
                    <FixRef pend>
                      הוסף live_inputs ב-<Path pend>{INSPECTOR_PATH[sys.id]}</Path>
                    </FixRef>
                  )}
                </>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(150px,1fr))', gap: '4px 18px', marginTop: 8, fontFamily: MONO, fontSize: 11.5 }}>
                  {inputs.map((inp, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 10, padding: '3px 0', borderBottom: `1px solid ${T.line}` }}>
                      <span style={{ color: T.tt }}>{inp.field}</span>
                      <span style={{ color: inp.fresh === false ? T.amber : T.tp, direction: 'ltr' as const }}>{inp.value ?? '—'}</span>
                    </div>
                  ))}
                </div>
              )}
            </Step>

            {/* 3 INTERPRETATION */}
            <Step kind={interps.length ? 'ok' : 'info'} title={<>פרשנות · derived {interps.length ? <Tag kind="live" /> : <Tag kind="pend" />}</>}>
              {interps.length === 0 ? (
                <span style={{ color: T.tt }}>ממתין ל-backend — אין interpretations.</span>
              ) : (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '3px 16px', fontFamily: MONO }}>
                  {interps.map((it, i) => (
                    <span key={i} style={{ fontSize: 11 }}>
                      <span style={{ color: T.green }}>{it.key}:</span> <span style={{ color: T.tp }}>{it.value ?? '—'}</span>
                      {it.from_input && <span style={{ color: T.tt, fontSize: 9 }}> ←{it.from_input}</span>}
                    </span>
                  ))}
                </div>
              )}
            </Step>

            {/* 4 GATES */}
            <Step kind={gatesOk == null ? 'info' : gatesOk ? 'ok' : 'bad'} title={<>שערים · stream / global gates</>}>
              {gates.length === 0 ? (
                <span style={{ color: T.tt }}>אין global_gates למערכת זו.</span>
              ) : (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 10px', fontFamily: MONO, fontSize: 11 }}>
                  {gates.map((g) => {
                    return (
                      <span key={g.key} style={{ color: g.present ? T.ts : T.redLight }}>
                        <span style={{ color: g.present ? T.green : T.red }}>{g.present ? '✓' : '✕'}</span> {g.key}
                        {g.live != null && <span style={{ color: T.tt }}> ={g.live}</span>}
                        {g.freshness?.source && <SrcPill source={g.freshness.source} />}
                      </span>
                    );
                  })}
                </div>
              )}
              {isFiring && (
                <div style={{ marginTop: 6, color: T.pend, fontFamily: MONO, fontSize: 11 }}>
                  ⧗ {sys.id === 'woodies' ? 'A7 · anti-patterns' : sys.id === 'five_min' ? 'S6 Killzone · S/R proximity · COT>AMT' : 'שערים נוספים'} <Tag kind="pend" />
                  <FixRef pend>
                    שערים אמיתיים ב-<Path pend>{INSPECTOR_PATH[sys.id] ?? 'inspector'}</Path>
                  </FixRef>
                </div>
              )}
            </Step>

            {/* 4.5 DAY-TYPE MATRIX — S4 only */}
            {sys.id === 'woodies' && (
              <DayTypeMatrixVerdict patterns={sys.patterns} activeDay={activeDay} />
            )}

            {/* 5 VERDICT */}
            <Step
              kind={verdict.kind === 'fired' ? 'ok' : verdict.kind === 'armed' ? 'wait' : verdict.kind === 'blocked' ? 'bad' : 'info'}
              last={!isFiring}
              title={<>פסיקה · {verdict.label}</>}
            >
              {sys.patterns.length} תבניות · לחץ על תבנית לפירוט הרכיבים.
            </Step>

            {/* 6 TARGETS/STOP — firing only */}
            {isFiring && (
              <Step kind={hasLiveTargets ? 'ok' : 'pend'} last title={
                <span style={{ color: hasLiveTargets ? T.tp : T.pend }}>
                  TARGETS / STOP {hasLiveTargets ? <Tag kind="live" /> : <Tag kind="pend" label="⧗ ממתין ל-backend · P0" />}
                </span>
              }>
                {hasLiveTargets ? (
                  <TargetsStopLive patterns={sys.patterns} />
                ) : (
                  <>
                    <div style={{ color: T.ts }}>
                      המנוע מחשב את אלה בזמן ירי — אך לא נחשפים ל-endpoint. <b style={{ color: T.tp }}>לא לסנתז ב-frontend.</b>
                    </div>
                    <PendingTargetsSlot sysId={sys.id} />
                  </>
                )}
              </Step>
            )}
          </div>

          {/* patterns */}
          {sys.patterns.length > 0 && (
            <div style={{ marginTop: 12, border: `1px solid ${T.line}`, borderRadius: 6, overflow: 'hidden' }}>
              {sys.patterns.map((p) => (
                <PatternRow key={p.id} pattern={p} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Observer / gate cards (S1 live · S5/S6 not wired)                   */
/* ------------------------------------------------------------------ */

function ObserverCards({ wiredIds, data }: { wiredIds: Set<string>; data: BuildStatusResponse }) {
  const s1Wired = wiredIds.has('day_type');
  const tpoWired = wiredIds.has('tpo');
  const kzWired = wiredIds.has('killzone');

  // Extract live data from systems when wired
  const tpoSys = data.systems.find((s) => s.id === 'tpo');
  const kzSys = data.systems.find((s) => s.id === 'killzone');

  const cards: { id: string; lines: ReactNode; wired: boolean; fix?: ReactNode }[] = [
    {
      id: 'day_type',
      wired: s1Wired,
      lines: (
        <>
          {s1Wired ? 'מסכים ללונג/שורט לפי הסיווג ' : 'לא מחווט '}
          {s1Wired ? <Tag kind="live" /> : <Tag kind="pend" />}
          <br />
          pre-open context · decision matrix · targets <Tag kind="pend" />
        </>
      ),
      fix: s1Wired ? undefined : <Path pend>day_type_inspector.py</Path>,
    },
    {
      id: 'tpo',
      wired: tpoWired,
      lines: tpoWired && tpoSys ? (
        <>
          <span style={{ color: T.green }}>● מחווט</span> <Tag kind="live" />
          <br />
          {tpoSys.global_gates.length > 0 ? (
            <span style={{ fontFamily: MONO, fontSize: 10 }}>
              {tpoSys.global_gates.map((g) => (
                <span key={g.key} style={{ marginInlineEnd: 8 }}>
                  <span style={{ color: g.present ? T.green : T.red }}>{g.present ? '✓' : '✕'}</span> {g.key}
                </span>
              ))}
            </span>
          ) : (
            <>POC/VAH/VAL · IB · profile_shape · otf_clarity</>
          )}
          <br />
          <span style={{ fontSize: 10, color: T.tt }}>A5 = advisory בלבד (לא חוסם ירי)</span>
        </>
      ) : (
        <>
          <span style={{ color: T.pend }}>⧗ לא מחווט כלל</span> — חסר <span style={{ direction: 'ltr' as const }}>tpo_inspector</span>.
          <br />
          POC/VAH/VAL · IB · profile_shape · otf_clarity
          <br />
          <span style={{ fontSize: 10, color: T.tt }}>A5 = advisory בלבד (לא חוסם ירי)</span>
        </>
      ),
      fix: tpoWired ? undefined : (
        <>
          צור <Path pend>tpo_inspector.py</Path> → <Path pend>aggregator.py</Path>
        </>
      ),
    },
    {
      id: 'killzone',
      wired: kzWired,
      lines: kzWired && kzSys ? (
        <>
          <span style={{ color: T.green }}>● מחווט</span> <Tag kind="live" />
          <br />
          {kzSys.global_gates.length > 0 ? (
            <span style={{ fontFamily: MONO, fontSize: 10 }}>
              {kzSys.global_gates.map((g) => (
                <span key={g.key} style={{ marginInlineEnd: 8 }}>
                  <span style={{ color: g.present ? T.green : T.red }}>{g.present ? '✓' : '✕'}</span> {g.key}
                  {g.live != null && <span style={{ color: T.tt }}> ={g.live}</span>}
                </span>
              ))}
            </span>
          ) : (
            <>is_gate_open · quality · sizing_modifier · block_reason</>
          )}
          {kzSys.interpretations?.map((it) => (
            <div key={it.key} style={{ fontFamily: MONO, fontSize: 10, color: T.ts }}>
              {it.key}: {it.value}
            </div>
          ))}
        </>
      ) : (
        <>
          <span style={{ color: T.pend }}>⧗ לא מחווט כלל</span> — חסר <span style={{ direction: 'ltr' as const }}>killzone_inspector</span>.
          <br />
          is_gate_open · quality · sizing_modifier · block_reason
        </>
      ),
      fix: kzWired ? undefined : (
        <>
          צור <Path pend>killzone_inspector.py</Path> → <Path pend>aggregator.py</Path>
        </>
      ),
    },
  ];
  return (
    <div style={{ marginTop: 20 }}>
      <SLab>שכבה 2 · צופים ושער — הקשר בלבד, לא יורים</SLab>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10 }}>
        {cards.map((c) => {
          const meta = sysMeta(c.id);
          return (
            <div key={c.id} style={{ borderRadius: T.r, border: `1px ${c.wired ? 'solid' : 'dashed'} ${c.wired ? T.line : '#7c8cff45'}`, background: c.wired ? T.s1 : T.pendD, overflow: 'hidden' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '11px 13px', fontFamily: MONO, fontSize: 12, color: T.tp, fontWeight: 600 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: meta.color, flex: '0 0 auto' }} />
                {meta.label}
                <span style={{
                  fontSize: 9,
                  fontFamily: MONO,
                  padding: '2px 7px',
                  borderRadius: 5,
                  textTransform: 'uppercase' as const,
                  letterSpacing: '.5px',
                  color: meta.role === 'observer' ? T.sys1 : T.sys6,
                  background: T.s2,
                  boxShadow: `inset 0 0 0 1px ${meta.role === 'observer' ? '#5b9bff40' : '#8b8b9640'}`,
                }}>{meta.role}</span>
              </div>
              <div style={{ padding: '0 13px 12px', fontFamily: MONO, fontSize: 11, color: T.ts, lineHeight: 1.6 }}>
                {c.lines}
                {c.fix && <FixRef pend>צור / חווט: {c.fix}</FixRef>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Verdict header + blocker                                            */
/* ------------------------------------------------------------------ */

const VERDICT_STYLE: Record<string, { fg: string; bg: string; shadow: string }> = {
  READY: { fg: T.green, bg: T.greenD, shadow: 'inset 0 0 0 1px #22c55e33' },
  DEGRADED: { fg: T.amber, bg: T.amberD, shadow: 'inset 0 0 0 1px #f5b44133' },
  BLOCKED: { fg: T.red, bg: T.redD, shadow: 'inset 0 0 0 1px #ef444433' },
};

function Blocker({ readiness, data }: { readiness: Readiness | undefined; data: BuildStatusResponse }) {
  if (!readiness) return null;
  const checks = readiness.checks ?? [];
  const blocker = checks.find((c) => !c.passed && c.severity === 'block');
  const degraded = checks.filter((c) => !c.passed && c.severity === 'degrade');
  if (!blocker && degraded.length === 0) return null;
  const isBlock = !!blocker;

  // Build chain visualization from systems
  const chainNodes: { label: string; ok: boolean }[] = [];
  for (const sys of data.systems) {
    const meta = sysMeta(sys.id);
    const lag = sys.data_freshness?.lag_seconds;
    const thresh = sys.data_freshness?.threshold_seconds ?? 300;
    const tier = freshTier(lag, thresh);
    const v = systemVerdict(sys);
    const shortName = meta.label.replace(/^S\d+ · /, '');
    if (tier === 'stale') {
      chainNodes.push({ label: `${shortName} ✕ stale ${fmtLag(lag)}`, ok: false });
    } else {
      chainNodes.push({ label: `${shortName} ✓`, ok: true });
    }
    if (v.kind === 'blocked') {
      chainNodes.push({ label: `${meta.label.split(' · ')[0]} BLOCKED`, ok: false });
    }
  }

  return (
    <div style={{ margin: '16px 0 0', borderRadius: T.r, padding: '16px 18px', background: isBlock ? 'linear-gradient(180deg,#1d1416,#160f10)' : T.amberD, border: `1px solid ${isBlock ? '#ef444430' : '#f5b44140'}` }}>
      <div style={{ fontSize: 15, fontWeight: 700, color: isBlock ? T.redLight : T.amber, lineHeight: 1.45, direction: 'rtl' as const }}>
        {isBlock ? `למה לא נכנסנו עכשיו — ${blockerHebrew(blocker!)}` : `מצב מוגבל — ${degraded.map(blockerHebrew).join(' · ')}`}
      </div>
      {readiness.reason && <div style={{ marginTop: 8, fontSize: 12.5, color: T.ts }}>{readiness.reason}</div>}
      {isBlock && (
        <FixRef>
          בדוק <Path>/tmp/bridge.err.log</Path> · runbook <Path>docs/runbooks/SIERRA_DLL_OPS.md</Path>
        </FixRef>
      )}
      {/* Chain visualization */}
      {chainNodes.length > 0 && (
        <div style={{ marginTop: 14, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', fontFamily: MONO, fontSize: 11 }}>
          {chainNodes.map((n, i) => (
            <span key={i} style={{ display: 'contents' }}>
              {i > 0 && <span style={{ color: T.tt }}>{n.ok ? '·' : '→'}</span>}
              <span style={{
                padding: '4px 10px',
                borderRadius: 6,
                background: n.ok ? T.s2 : T.redD,
                color: n.ok ? T.greenLight : T.redLight,
                boxShadow: n.ok ? `inset 0 0 0 1px #22c55e30` : `inset 0 0 0 1px #ef444450`,
                fontWeight: n.ok ? 400 : 700,
              }}>
                {n.label}
              </span>
            </span>
          ))}
          {isBlock && (
            <>
              <span style={{ color: T.tt }}>→</span>
              <span style={{ padding: '4px 10px', borderRadius: 6, background: T.redD, color: T.redLight, boxShadow: 'inset 0 0 0 1px #ef444450', fontWeight: 700 }}>
                verdict BLOCKED
              </span>
            </>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Right rail cards                                                    */
/* ------------------------------------------------------------------ */

function RightRail({ data, activeDay }: { data: BuildStatusResponse; activeDay: string | null }) {
  const verdict = data.readiness?.verdict ?? 'BLOCKED';
  const vs = VERDICT_STYLE[verdict] ?? VERDICT_STYLE.BLOCKED;
  const checks = data.readiness?.checks ?? [];
  const blocker = checks.find((c) => !c.passed && c.severity === 'block');

  // Count armed/fired
  const firingSystems = data.systems.filter((s) => sysMeta(s.id).role === 'firing');
  let armedLabel = '';
  let firedLabel = '';
  for (const sys of firingSystems) {
    const v = systemVerdict(sys);
    const shortName = sys.id.toUpperCase().replace('FIVE_MIN', 'S2').replace('WOODIES', 'S4').replace('FOOTPRINT', 'S3');
    if (v.kind === 'armed') armedLabel += (armedLabel ? ', ' : '') + shortName;
    if (v.kind === 'fired') firedLabel += (firedLabel ? ', ' : '') + `${shortName} ×${sys.patterns.filter((p) => p.fired_today).length}`;
  }

  // Heartbeat from freshness
  const minLag = Math.min(...data.systems.map((s) => s.data_freshness?.lag_seconds ?? 999));

  const rcard: CSSProperties = { background: T.s1, border: `1px solid ${T.line}`, borderRadius: T.r, padding: '14px 16px', marginBottom: 14 };
  const rcardPend: CSSProperties = { background: T.pendD, borderTop: '1px dashed #7c8cff45', borderBottom: '1px dashed #7c8cff45', borderLeft: '1px dashed #7c8cff45', borderRight: '1px dashed #7c8cff45', borderRadius: T.r, padding: '14px 16px', marginBottom: 14 };
  const rt: CSSProperties = { fontSize: 10, color: T.tt, textTransform: 'uppercase' as const, letterSpacing: '.8px', fontFamily: MONO, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 7 };
  const rrow: CSSProperties = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, padding: '6px 0', borderBottom: `1px solid ${T.line}`, fontFamily: MONO, fontSize: 12 };

  return (
    <div>
      {/* Status Now */}
      <div style={rcard}>
        <div style={rt}>מצב כעת <Tag kind="live" /></div>
        <div style={rrow}>
          <span style={{ color: T.ts }}>verdict</span>
          <span style={{ color: vs.fg, fontWeight: 600 }}>{verdict}</span>
        </div>
        {blocker && (
          <div style={rrow}>
            <span style={{ color: T.ts }}>חסם יחיד</span>
            <span style={{ color: T.tp, fontWeight: 600 }}>{blocker.key}</span>
          </div>
        )}
        {armedLabel && (
          <div style={rrow}>
            <span style={{ color: T.ts }}>armed</span>
            <span style={{ color: T.amber, fontWeight: 600 }}>{armedLabel}</span>
          </div>
        )}
        {firedLabel && (
          <div style={rrow}>
            <span style={{ color: T.ts }}>ירו היום</span>
            <span style={{ color: T.green, fontWeight: 600 }}>{firedLabel}</span>
          </div>
        )}
        <div style={{ ...rrow, borderBottom: 'none' }}>
          <span style={{ color: T.ts }}>heartbeat</span>
          <span style={{ color: minLag < 60 ? T.green : T.red, fontWeight: 600, direction: 'ltr' as const }}>{fmtLag(minLag)}</span>
        </div>
      </div>

      {/* Trade Plans (pending) */}
      <div style={rcardPend}>
        <div style={rt}>תוכניות מסחר מוקרנות <Tag kind="pend" /></div>
        <div style={{ fontFamily: MONO, fontSize: 11, color: T.ts, lineHeight: 1.7 }}>
          לוח "מוכן לירי" עם entry/stop/T1-T3 ב-$ ו-R ייבנה כאן — <b style={{ color: T.tp }}>רק</b> כשה-TARGETS/STOP יגיע מה-backend. עד אז לא מוצגות תוכניות מסחר כדי לא להמציא מספרים.
        </div>
      </div>

      {/* Freshness sparkline */}
      <div style={rcard}>
        <div style={rt}>פעימת רעננות · 60s <Tag kind="live" /></div>
        <svg viewBox="0 0 264 60" width="100%" height="60" style={{ display: 'block' }}>
          <line x1="0" y1="50" x2="264" y2="50" stroke={T.line} strokeWidth="1" />
          {/* Stable line (placeholder) */}
          <polyline fill="none" stroke={T.green} strokeWidth="1.6" points="0,42 22,40 44,43 66,41 88,42 110,40 132,41 154,40 176,43 198,41 220,40 242,41 264,40" />
        </svg>
        <div style={{ marginTop: 4, fontSize: 11, color: T.ts, fontFamily: MONO }}>
          <span style={{ color: T.green }}>— streams יציב</span>
        </div>
      </div>

      {/* Miss Log (pending) */}
      <div style={rcardPend}>
        <div style={rt}>יומן החמצות <Tag kind="pend" /></div>
        <div style={{ fontFamily: MONO, fontSize: 11, lineHeight: 1.85, color: T.ts, direction: 'ltr' as const, textAlign: 'start' as const }}>
          דורש זיכרון בצד ה-backend (snapshot היסטורי). העמוד היום הוא snapshot בלבד — לוג מתגלגל יחשוף דפוסים.
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Source-integrity tab                                                */
/* ------------------------------------------------------------------ */

interface IntegrityRow {
  field: string;
  value: string;
  source: string | null;
}

function collectIntegrity(data: BuildStatusResponse): IntegrityRow[] {
  const rows: IntegrityRow[] = [];
  for (const sys of data.systems) {
    const m = sysMeta(sys.id);
    for (const inp of sys.live_inputs ?? []) {
      rows.push({ field: `${m.label} · ${inp.field}`, value: inp.value ?? '—', source: inp.source ?? null });
    }
    for (const p of sys.patterns) {
      for (const c of p.components) {
        if (c.freshness?.source) rows.push({ field: `${m.label} · ${c.key}`, value: (c.live ?? c.value ?? '—').toString(), source: c.freshness.source });
      }
    }
  }
  return rows;
}

function IntegrityTab({ data }: { data: BuildStatusResponse }) {
  const rows = useMemo(() => collectIntegrity(data), [data]);
  const derived = rows.filter((r) => !isCanonical(r.source));
  const th: CSSProperties = { padding: '10px 12px', fontSize: 10, textTransform: 'uppercase' as const, letterSpacing: '.5px', color: T.tt, fontWeight: 500, textAlign: 'start', borderBottom: `1px solid ${T.line}` };
  return (
    <div>
      <SLab>
        כל שדה שמערכת יורה צורכת — הערך, המקור בפועל (freshness.source), והאם קנוני <Tag kind="live" />
      </SLab>
      {rows.length === 0 ? (
        <div style={{ color: T.tt, fontSize: 12, padding: 16 }}>אין שדות עם מקור לתצוגה (ה-inspector עוד לא פולט freshness.source).</div>
      ) : (
        <div style={{ border: `1px solid ${T.line}`, borderRadius: T.r, overflow: 'hidden', background: T.s1 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: MONO, fontSize: 12 }}>
            <thead>
              <tr>
                <th style={th}>שדה</th>
                <th style={{ ...th, direction: 'ltr' as const }}>ערך חי</th>
                <th style={th}>מקור בפועל</th>
                <th style={th}>קנוני נדרש</th>
                <th style={{ ...th, textAlign: 'center' }}>תקין</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => {
                const canon = isCanonical(r.source);
                return (
                  <tr key={i} style={{ borderTop: `1px solid ${T.line}`, background: canon ? 'transparent' : T.amberD }}>
                    <td style={{ padding: '11px 12px', color: canon ? T.tp : T.amber }}>{r.field}</td>
                    <td style={{ padding: '11px 12px', direction: 'ltr' as const, color: T.ts }}>{r.value}</td>
                    <td style={{ padding: '11px 12px' }}>{r.source ? <SrcPill source={r.source} /> : '—'}</td>
                    <td style={{ padding: '11px 12px', color: T.ts }}>sierra_export</td>
                    <td style={{ padding: '11px 12px', textAlign: 'center' }}>{canon ? <span style={{ color: T.green }}>✓</span> : <span style={{ color: T.red }}>✕</span>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {derived.length > 0 && (
        <div style={{ marginTop: 16, border: `1px solid #f5b44140`, borderRadius: T.r, background: T.amberD, padding: '16px 18px' }}>
          <h4 style={{ margin: '0 0 8px', fontSize: 13.5, color: T.amber, fontFamily: MONO }}>⚠ {derived.length} שדות ממקור לא-קנוני</h4>
          <p style={{ margin: 0, fontSize: 12.5, color: T.ts, lineHeight: 1.65 }}>
            ערך שמסומן present אך מקורו אינו sierra_export/db הוא סיכון לפי כלל "Honest failure &gt; synthetic value". אל תסמוך על איתות שתלוי בו עד אימות מול המקור הקנוני. <b style={{ color: T.tp }}>החלטה לטריידר:</b> אל תסמוך על איתות שתלוי בשדה זה עד שהמקור יתוקן.
          </p>
          <FixRef>
            החזר <Path>missing</Path> במקום ערך נגזר ב-inspector המתאים · ראה CLAUDE.md § Rule 1
          </FixRef>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Day-type tables tab                                                 */
/* ------------------------------------------------------------------ */

function DayTypeTables({ activeDay }: { activeDay: string | null }) {
  const initial = DAY_TARGETS.find((d) => d.key === activeDay)?.key ?? 'Trend_Normal';
  const [sel, setSel] = useState<string>(initial);
  const day = DAY_TARGETS.find((d) => d.key === sel) ?? DAY_TARGETS[0];

  const th: CSSProperties = { padding: '10px 12px', fontSize: 10, textTransform: 'uppercase' as const, letterSpacing: '.5px', color: T.tt, fontWeight: 500, textAlign: 'start', borderBottom: `1px solid ${T.line}` };
  const td: CSSProperties = { padding: '11px 12px', borderBottom: `1px solid ${T.line}`, color: T.ts, fontFamily: MONO, fontSize: 12 };

  const Cell = ({ k, v, sub, hl, color }: { k: string; v: string; sub?: string; hl?: boolean; color?: string }) => (
    <div style={{ border: `1px solid ${hl ? '#2dd4a740' : T.line}`, borderRadius: T.r, background: hl ? '#10201c' : T.s1, padding: '13px 15px' }}>
      <div style={{ fontFamily: MONO, fontSize: 10, color: T.tt, textTransform: 'uppercase' as const, letterSpacing: '.5px', marginBottom: 6 }}>{k}</div>
      <div style={{ fontFamily: MONO, fontSize: v.length > 6 ? 13 : 17, fontWeight: 700, color: color ?? T.tp }}>{v}</div>
      {sub && <div style={{ fontFamily: MONO, fontSize: 10, color: T.ts, marginTop: 3 }}>{sub}</div>}
    </div>
  );

  return (
    <div>
      <SLab>
        טבלאות החלטה לכל סוג יום — יעדים · חוזים · time-stop · מרחק סטופ <Tag kind="cfg" label="📖 אפיון · rule-book" />
      </SLab>
      <div style={{ fontFamily: MONO, fontSize: 11, color: T.tt, margin: '0 2px 16px', lineHeight: 1.6 }}>
        מקור: <span style={{ direction: 'ltr' as const }}>backend/v9/systems/day_type/targets_table.py</span> + <span style={{ direction: 'ltr' as const }}>five_min/atr_caps.py</span>. ערכי קונפיג <b style={{ color: T.tp }}>סטטיים</b> (ספר-החוקים), לא חיים — verbatim. סוג היום החי{' '}
        {activeDay ? <span style={{ color: T.sys1 }}>{activeDay}</span> : <span style={{ color: T.tt }}>(לא סווג)</span>} מודגש ונבחר אוטומטית.
      </div>

      {/* master overview */}
      <div style={{ border: `1px solid ${T.line}`, borderRadius: T.r, overflow: 'hidden', background: T.s1, marginBottom: 8 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: MONO, fontSize: 12 }}>
          <thead>
            <tr>
              <th style={th}>סוג יום</th>
              <th style={th}>T1</th>
              <th style={th}>T2</th>
              <th style={th}>T3</th>
              <th style={th}>trail</th>
              <th style={th}>time-stop</th>
              <th style={{ ...th, textAlign: 'center' }}>חוזים</th>
              <th style={th}>sizing</th>
            </tr>
          </thead>
          <tbody>
            {DAY_TARGETS.map((d) => {
              const isActive = d.key === activeDay;
              return (
                <tr key={d.key} style={{ borderTop: `1px solid ${T.line}`, background: isActive ? T.amberD : 'transparent' }}>
                  <td style={{ ...td, color: d.noTrade ? T.red : isActive ? T.tp : T.tp }}>
                    {d.key}
                    {isActive && <span style={{ marginInlineStart: 7, fontSize: 8.5, padding: '1px 6px', borderRadius: 9, background: T.greenD, color: T.greenLight }}>● היום</span>}
                  </td>
                  {d.noTrade ? (
                    <td style={{ ...td, color: T.red, textAlign: 'center' }} colSpan={6}>
                      NO TRADE — אין כניסה (EXIT_V6 + D-091)
                    </td>
                  ) : (
                    <>
                      <td style={td}>{d.t1}</td>
                      <td style={td}>{d.t2}</td>
                      <td style={td}>{d.t3}</td>
                      <td style={td}>{d.trail}</td>
                      <td style={td}>{d.timeStop}</td>
                    </>
                  )}
                  <td style={{ ...td, textAlign: 'center', color: d.noTrade ? T.red : T.tp, fontWeight: 700 }}>
                    {d.noTrade ? '0' : <b style={{ color: isActive ? T.green : T.tp }}>{d.contracts}</b>}
                  </td>
                  <td style={td}>{d.sizing}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* day sub-tabs */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', margin: '16px 0 18px' }}>
        {DAY_TARGETS.map((d) => {
          const on = d.key === sel;
          return (
            <div
              key={d.key}
              onClick={() => setSel(d.key)}
              style={{ padding: '8px 14px', borderRadius: 8, fontFamily: MONO, fontSize: 12, fontWeight: 600, cursor: 'pointer', color: on ? T.tp : d.noTrade ? T.red : T.ts, background: on ? T.s3 : T.s1, boxShadow: `inset 0 0 0 1px ${on ? T.line2 : T.line}`, display: 'flex', alignItems: 'center', gap: 7 }}
            >
              {d.key}
              {d.key === activeDay && <span style={{ fontSize: 8.5, padding: '1px 6px', borderRadius: 9, background: T.greenD, color: T.greenLight }}>● היום</span>}
            </div>
          );
        })}
      </div>

      {/* selected day plan */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 14 }}>
        <span style={{ fontFamily: MONO, fontSize: 17, fontWeight: 700, color: day.noTrade ? T.red : day.key === activeDay ? T.green : T.tp }}>{day.key}</span>
        {day.key === activeDay && <Tag kind="live" label="● סוג היום החי" />}
        {day.noTrade && <span style={{ fontFamily: MONO, fontSize: 11, padding: '3px 10px', borderRadius: 6, background: T.redD, color: T.redLight, fontWeight: 700 }}>NO TRADE</span>}
      </div>

      {!day.noTrade && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(150px,1fr))', gap: 12, marginBottom: 18 }}>
          <Cell k="כניסה" v="trigger התבנית" sub="סטופ = 1R · 1R = ATR14 × מכפיל-משפחה" hl color={T.green} />
          <Cell k="T1" v={day.t1} color={T.green} />
          <Cell k="T2" v={day.t2} color={T.green} />
          <Cell k="T3" v={day.t3} color={T.green} />
          <Cell k="חוזים" v={String(day.contracts)} sub={day.sizing} hl color={T.green} />
          <Cell k="time-stop" v={day.timeStop} color={day.timeStop !== '—' ? T.amber : undefined} />
          <Cell k="trail" v={day.trail} />
        </div>
      )}

      <div style={{ fontFamily: MONO, fontSize: 11, color: T.ts, lineHeight: 1.6, borderInlineStart: `3px solid ${T.line2}`, padding: '4px 0 4px 12px', marginBottom: 16 }}>
        <b style={{ color: T.tp }}>אפיון:</b> {day.note}
      </div>
      {day.override && (
        <div style={{ fontFamily: MONO, fontSize: 11, color: T.amber, lineHeight: 1.6, borderInlineStart: `3px solid ${T.amber}`, padding: '4px 0 4px 12px', marginBottom: 16 }}>
          <b style={{ color: T.tp }}>Override:</b> {day.override}
        </div>
      )}

      {/* ATR multipliers */}
      <SLab>
        מרחק הסטופ (1R) = ATR14 × מכפיל לפי משפחת-תבנית <Tag kind="cfg" label="📖 atr_caps.py" />
      </SLab>
      <div style={{ border: `1px solid ${T.line}`, borderRadius: T.r, overflow: 'hidden', background: T.s1, marginBottom: 18 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: MONO, fontSize: 12 }}>
          <thead>
            <tr>
              <th style={th}>משפחת תבנית</th>
              <th style={{ ...th, textAlign: 'center' }}>מכפיל ATR14</th>
              <th style={th}>namespace</th>
            </tr>
          </thead>
          <tbody>
            {ATR_MULTIPLIERS.map(([name, mult, ns]) => (
              <tr key={name} style={{ borderTop: `1px solid ${T.line}` }}>
                <td style={{ ...td, color: T.tp }}>{name}</td>
                <td style={{ ...td, textAlign: 'center', color: T.tp, fontWeight: 700 }}>×{mult.toFixed(1)}</td>
                <td style={td}>{ns}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* pattern time stops */}
      <SLab>
        time-stop לפי ציר-תבנית (Layer-3 backstop) — בפועל <span style={{ direction: 'ltr' as const }}>min(day, pattern)</span> <Tag kind="cfg" label="📖 atr_caps.py · D-094 §3.C" />
      </SLab>
      <div style={{ border: `1px solid ${T.line}`, borderRadius: T.r, overflow: 'hidden', background: T.s1 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: MONO, fontSize: 12 }}>
          <thead>
            <tr>
              <th style={th}>תבנית</th>
              <th style={{ ...th, textAlign: 'center' }}>time-stop (דק׳)</th>
              <th style={th}>תבנית</th>
              <th style={{ ...th, textAlign: 'center' }}>time-stop (דק׳)</th>
            </tr>
          </thead>
          <tbody>
            {[0, 1, 2, 3, 4].map((i) => {
              const left = PATTERN_TIME_STOPS[i];
              const right = PATTERN_TIME_STOPS[i + 5];
              return (
                <tr key={i} style={{ borderTop: `1px solid ${T.line}` }}>
                  {left && <><td style={{ ...td, color: T.tp }}>{left[0]}</td><td style={{ ...td, textAlign: 'center' }}>{left[1]}</td></>}
                  {right && <><td style={{ ...td, color: T.tp }}>{right[0]}</td><td style={{ ...td, textAlign: 'center' }}>{right[1]}</td></>}
                  {!right && <><td style={td} /><td style={td} /></>}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: 18, fontSize: 11, color: T.tt, lineHeight: 1.7, fontFamily: MONO }}>
        הערה ל-Build Status: טבלאות אלה הן <b style={{ color: T.tp }}>אפיון סטטי</b> (config) — מותר להציגן verbatim. ה-<b style={{ color: T.tp }}>הקרנה</b> שלהן למחירים חיים (entry/stop/T1-T3 ב-$) היא שלב TARGETS/STOP שעדיין <span style={{ color: T.pend }}>⧗ ממתין ל-backend</span>: ה-1R החי חייב להגיע מ-inspector, לא להיגזר ב-frontend.
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* What's-missing tab (from the audit doc)                             */
/* ------------------------------------------------------------------ */

const MISSING: { pri: 'P0' | 'P1' | 'P2'; title: string; body: string }[] = [
  { pri: 'P0', title: 'שערי-אש גלובליים (pre_fire_validator + risk_checks)', body: '7 בדיקות לפני כל ירי (R:R≥1.0, ordering, time_stop) + תקרות LIVE ($250 הפסד, 5 עסקאות, 2 חוזים, חיתוך 14:30, 2 הפסדים רצופים). רצים בתוך כל מערכת — לא נפלטים ל-endpoint.' },
  { pri: 'P0', title: 'שלב TARGETS/STOP לכל מערכת יורה', body: 'סטופ שכבתי, 1R, T1/T2/T3, חוזים, time-stop. דורש inspector שיחשוף את מנוע הסטופ (S2 adaptive_stop, S4 atr_stop).' },
  { pri: 'P0', title: 'Day-Type Matrix verdict (S4)', body: 'הערך ✅/⚠️/❌ לכל תבנית × יום + entry_hint + t1_ref. כרגע נבדק רק day_type≠UNKNOWN.' },
  { pri: 'P1', title: 'חיווט S6 Killzone (שער אמיתי)', body: 'is_gate_open, אזור פעיל, quality, sizing_modifier, סיבת חסימה. אין killzone_inspector.' },
  { pri: 'P1', title: 'S/R proximity + COT/AMT כשערים אמיתיים (S2)', body: 'כרגע מוצגים כ-always-pass placeholder; הערכים החיים לא נחשפים.' },
  { pri: 'P1', title: 'anti-patterns + A7 universal (S4)', body: 'AP1/4/5/7/8/9 reject_reason; news/cool-down/loss-cap/stop-range/EOD. תבנית חסומה ב-AP נראית כמו "לא זוהתה".' },
  { pri: 'P1', title: 'freshness ל-3 קובצי Sierra (S2)', body: 'cumulative_delta.json (COT/AMT) · tpo.json (POC) · volume_profile.json (S/R). מקור חסר/ישן צריך להופיע כ-missing.' },
  { pri: 'P1', title: 'dispatch (S4) — winning_pattern לפי r_t1', body: '9 תבניות נראות "armed" עצמאית; המנגנון בוחר אחת לפי r_t1≥threshold (GRAY/YELLOW).' },
  { pri: 'P2', title: 'חיווט S5 TPO', body: 'POC/VAH/VAL, IB, profile_shape, otf_clarity. אין tpo_inspector.' },
  { pri: 'P2', title: 'pre-open context (S1)', body: 'pd_poc/vah/val, on_high/low, gap, overnight_bias + decision matrix + get_targets. ה-inspector לא קורא prev_day.' },
  { pri: 'P2', title: 'באנר "מושבת" (S3)', body: 'מודעות לדגל FOOTPRINT_DISABLED/S3_MUTE (atr.py:101). כרגע מציג armed/blocked על state ישן.' },
  { pri: 'P2', title: 'טבלאות אפיון מ-backend', body: 'targets_table.py + atr_caps.py ממורקרים ב-frontend (verbatim). עדיף שה-endpoint יחשוף אותם כדי למנוע drift.' },
];

function MissingTab() {
  const priColor: Record<string, { fg: string; bg: string }> = {
    P0: { fg: T.redLight, bg: T.redD },
    P1: { fg: T.amber, bg: T.amberD },
    P2: { fg: T.ts, bg: T.s2 },
  };
  return (
    <div>
      <SLab>
        מה חסר — מקור: BUILD_STATUS_COMPONENT_AUDIT.md · כל פריט = שדה שה-backend צריך לחשוף (לא מסונתז)
      </SLab>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        {MISSING.map((m, i) => {
          const pc = priColor[m.pri];
          const isP0Full = m.pri === 'P0' && i === 0; // First P0 gets full width
          return (
            <div key={i} style={{ gridColumn: isP0Full ? '1/-1' : undefined, borderWidth: 1, borderStyle: isP0Full ? 'dashed' : 'solid', borderColor: isP0Full ? '#7c8cff45' : T.line, borderRadius: T.r, background: isP0Full ? T.pendD : T.s1, padding: '15px 16px' }}>
              <h4 style={{ margin: '0 0 7px', fontSize: 13, color: T.tp, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 9, fontFamily: MONO, fontWeight: 700, padding: '2px 8px', borderRadius: 5, letterSpacing: '.5px', color: pc.fg, background: pc.bg }}>{m.pri}</span>
                {m.title}
              </h4>
              <p style={{ margin: 0, fontSize: 12, color: T.ts, lineHeight: 1.65 }}>{m.body}</p>
            </div>
          );
        })}
        {/* Principle card */}
        <div style={{ background: 'transparent', border: `1px dashed ${T.line}`, borderRadius: T.r, padding: '15px 16px' }}>
          <h4 style={{ margin: '0 0 7px', fontSize: 13, color: T.ts }}>עיקרון</h4>
          <p style={{ margin: 0, fontSize: 12, color: T.ts, lineHeight: 1.65 }}>
            שום שדה לא הומצא בעמוד. כל ⧗ הוא שדה אמיתי שהאודיט מצא חסר ב-endpoint. ירוק = כבר נפלט מ-<span style={{ direction: 'ltr' as const }}>/api/v9/build/pattern-status</span>. סגול = ממתין ל-backend.
          </p>
        </div>
      </div>
      <div style={{ marginTop: 18, fontSize: 11, color: T.tt, lineHeight: 1.7, fontFamily: MONO }}>
        סכמה: systems · global_gates · live_inputs · interpretations · patterns[components[stage/key/required/live/present/freshness/source]] · readiness.<br />
        חסר בסכמה (דורש הרחבת types.py): targets_stop · matrix_verdict · global_firewall (pre_fire/risk) · tpo · killzone · disabled_flag.
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main view                                                           */
/* ------------------------------------------------------------------ */

type TabId = 'tree' | 'integrity' | 'tables' | 'missing';

export function BuildTreeView() {
  const { data, error, loading, lastFetchedAt, refresh } = useBuildStatus();
  const [tab, setTab] = useState<TabId>('tree');

  const verdict = data?.readiness?.verdict ?? 'BLOCKED';
  const vs = VERDICT_STYLE[verdict] ?? VERDICT_STYLE.BLOCKED;
  const rtb = data?.rtb_session;

  const wiredIds = useMemo(() => new Set((data?.systems ?? []).map((s) => s.id)), [data]);
  const missingSystems = useMemo(() => EXPECTED_SYSTEMS.filter((id) => !wiredIds.has(id)), [wiredIds]);
  const activeDay = useMemo(() => (data ? currentDayType(data) : null), [data]);

  // Tab badge counts
  const integrityBadge = useMemo(() => {
    if (!data) return 0;
    const rows = collectIntegrity(data);
    return rows.filter((r) => !isCanonical(r.source)).length;
  }, [data]);

  const tabStyle = (id: TabId): CSSProperties => ({
    padding: '9px 18px',
    borderRadius: '8px 8px 0 0',
    background: tab === id ? T.s1 : 'transparent',
    color: tab === id ? T.tp : T.ts,
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 600,
    borderTop: `1px solid ${tab === id ? T.line : 'transparent'}`,
    borderLeft: `1px solid ${tab === id ? T.line : 'transparent'}`,
    borderRight: `1px solid ${tab === id ? T.line : 'transparent'}`,
    borderBottom: tab === id ? `1px solid ${T.s1}` : '1px solid transparent',
    marginBottom: -1,
  });

  return (
    <div dir="rtl" style={{ minHeight: '100vh', background: T.bg, color: T.tp, fontFamily: T.sans, fontSize: 13, lineHeight: 1.5, WebkitFontSmoothing: 'antialiased' } as CSSProperties}>
      <PulseStyle />

      {/* ===== HEADER — sticky, backdrop-filter blur ===== */}
      <header style={{ position: 'sticky', top: 0, zIndex: 30, background: 'rgba(11,11,13,.92)', backdropFilter: 'blur(8px)', borderBottom: `1px solid ${T.line}` }}>
        <div style={{ maxWidth: 1320, margin: '0 auto', padding: '0 22px', display: 'flex', alignItems: 'center', gap: 16, height: 54 }}>
          <Link href="/" style={{ fontFamily: MONO, fontWeight: 700, letterSpacing: '1px', color: T.sys1, fontSize: 14, textDecoration: 'none' }}>
            MEMS26
          </Link>
          <span style={{ color: T.ts, fontSize: 12 }}>/ Build Status · עץ החלטות</span>
          {/* Verdict badge with pulsing dot */}
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 16px', borderRadius: 8, fontWeight: 700, fontSize: 14, letterSpacing: '.4px', fontFamily: MONO, color: vs.fg, background: vs.bg, boxShadow: vs.shadow }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'currentColor', animation: 'mems26pulse 1.6s ease-in-out infinite' }} />
            {verdict}
          </span>
          <span style={{ flex: 1 }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 18, color: T.ts, fontSize: 11, fontFamily: MONO }}>
            {rtb && (
              <span>
                RTH{' '}
                {rtb.in_session ? (
                  <b style={{ color: T.green, fontWeight: 600 }}>פתוח</b>
                ) : (
                  <b style={{ color: T.tt, fontWeight: 600 }}>סגור</b>
                )}
                {rtb.in_session
                  ? <span> · -{rtb.minutes_to_close}m לסגירה</span>
                  : <span> · +{rtb.minutes_to_open}m לפתיחה</span>
                }
              </span>
            )}
            {data && <span>heartbeat <b style={{ color: T.green, fontWeight: 600, direction: 'ltr' as const }}>{fmtLag(Math.min(...data.systems.map((s) => s.data_freshness?.lag_seconds ?? 999)))}</b></span>}
            {activeDay && <span>day <b style={{ color: T.sys1, fontWeight: 600 }}>{activeDay}</b></span>}
          </div>
          <button
            onClick={refresh}
            disabled={loading}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '6px 13px',
              borderRadius: 7,
              fontFamily: MONO,
              fontSize: 11,
              fontWeight: 600,
              cursor: loading ? 'wait' : 'pointer',
              color: loading ? T.ts : T.green,
              background: loading ? T.s2 : T.greenD,
              boxShadow: loading ? `inset 0 0 0 1px ${T.line}` : 'inset 0 0 0 1px #22c55e33',
              border: 'none',
            }}
          >
            {loading ? '⏸ טוען…' : '● Live · refresh'}
          </button>
        </div>
      </header>

      <div style={{ maxWidth: 1320, margin: '0 auto', padding: '0 22px' }}>
        <Legend />

        {error && (
          <div style={{ margin: '14px 0 0', padding: '10px 14px', borderRadius: T.r, background: T.redD, color: T.redLight, fontFamily: MONO, fontSize: 11, border: `1px solid ${T.red}` }}>
            טעינה נכשלה · {error} · נסה רענון. (אם ה-endpoint /api/v9/build/pattern-status לא רץ — זה ייכשל עד שה-backend יעלה.)
          </div>
        )}

        {!data && !error && (
          <div style={{ padding: 40, textAlign: 'center', color: T.tt, fontFamily: MONO, fontSize: 12 }}>{loading ? 'טוען build status…' : 'אין נתונים. לחץ רענן.'}</div>
        )}

        {data && (
          <>
            <Blocker readiness={data.readiness} data={data} />

            {/* Global Firewall — always visible above tabs */}
            <GlobalFirewall data={data} />

            {/* Tabs */}
            <div style={{ display: 'flex', gap: 6, marginTop: 22, borderBottom: `1px solid ${T.line}` }}>
              <div style={tabStyle('tree')} onClick={() => setTab('tree')}>עץ החלטות</div>
              <div style={tabStyle('integrity')} onClick={() => setTab('integrity')}>
                שלמות מקור
                {integrityBadge > 0 && <span style={{ marginInlineStart: 7, fontSize: 10, padding: '1px 7px', borderRadius: 9, background: T.redD, color: T.redLight, fontFamily: MONO }}>{integrityBadge}</span>}
              </div>
              <div style={tabStyle('tables')} onClick={() => setTab('tables')}>טבלאות אפיון</div>
              <div style={tabStyle('missing')} onClick={() => setTab('missing')}>
                מה חסר <span style={{ marginInlineStart: 7, fontSize: 10, padding: '1px 7px', borderRadius: 9, background: T.pendD, color: T.pend, fontFamily: MONO }}>{MISSING.length}</span>
              </div>
            </div>

            <main style={{ padding: '22px 0 56px' }}>
              {tab === 'tree' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 296px', gap: 18, alignItems: 'start' }}>
                  {/* LEFT COLUMN */}
                  <div>
                    {/* Context bar */}
                    <ContextBar data={data} activeDay={activeDay} />

                    {data.errors && data.errors.length > 0 && (
                      <div style={{ padding: '6px 10px', marginBottom: 12, borderRadius: 6, background: T.amberD, color: T.amber, border: `1px solid ${T.amber}`, fontFamily: MONO, fontSize: 10 }}>
                        warnings: {data.errors.join(' · ')}
                      </div>
                    )}

                    <SourcesStrip systems={data.systems} />

                    <div>
                      <SLab>שכבה 1 · מערכות יורות — 5 שלבים קנוניים: מקור → קלט → שערים → תבנית → <b style={{ color: T.pend }}>TARGETS/STOP</b></SLab>
                      {data.systems.filter((s) => sysMeta(s.id).role === 'firing').map((sys, i) => (
                        <SystemBranch key={sys.id} sys={sys} defaultOpen={i === 0} activeDay={activeDay} />
                      ))}

                      {missingSystems.filter((id) => sysMeta(id).role === 'firing').length > 0 && (
                        <div style={{ marginTop: 8, border: `1px dashed ${T.line}`, borderRadius: T.r, padding: '12px 14px', fontFamily: MONO, fontSize: 11, color: T.tt }}>
                          לא מחובר ל-build status (דורש inspector ב-backend): {missingSystems.filter((id) => sysMeta(id).role === 'firing').map((id) => sysMeta(id).label).join(' · ')}
                        </div>
                      )}
                    </div>

                    {/* Observers + non-firing systems */}
                    <div style={{ marginTop: 20 }}>
                      <SLab>שכבה 2 · צופים ושער — הקשר בלבד, לא יורים</SLab>
                      {data.systems.filter((s) => sysMeta(s.id).role !== 'firing').map((sys, i) => (
                        <SystemBranch key={sys.id} sys={sys} defaultOpen={false} activeDay={activeDay} />
                      ))}
                    </div>

                    <ObserverCards wiredIds={wiredIds} data={data} />
                  </div>

                  {/* RIGHT RAIL */}
                  <RightRail data={data} activeDay={activeDay} />
                </div>
              )}
              {tab === 'integrity' && <IntegrityTab data={data} />}
              {tab === 'tables' && <DayTypeTables activeDay={activeDay} />}
              {tab === 'missing' && <MissingTab />}
            </main>
          </>
        )}
      </div>
    </div>
  );
}
