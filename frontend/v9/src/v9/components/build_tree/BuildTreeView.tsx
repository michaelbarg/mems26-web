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
 * These are rule-book constants (📖 אפיון), NOT live values. The PROJECTION of
 * these onto live $/R prices remains a ⧗ backend gap (TARGETS/STOP stage).
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
import { COLORS } from '../../design/tokens';
import type {
  BuildStatusResponse,
  SystemBlock,
  Pattern,
  Component,
  Readiness,
  ReadinessCheck,
} from '../build_status/types';

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
  day_type: { color: '#5b9bff', role: 'observer', label: 'S1 · Day Type' },
  five_min: { color: '#2dd4a7', role: 'firing', label: 'S2 · 5-Min Patterns' },
  footprint: { color: '#a78bfa', role: 'firing', label: 'S3 · Footprint' },
  woodies: { color: '#fb923c', role: 'firing', label: 'S4 · Woodies CCI' },
  tpo: { color: '#22b8cf', role: 'observer', label: 'S5 · TPO' },
  killzone: { color: '#8b8b96', role: 'gate', label: 'S6 · Killzone' },
  bridge: { color: '#8b8b96', role: 'gate', label: 'Bridge · Streams' },
};

// Systems we expect per the spec but the aggregator may not wire yet.
const EXPECTED_SYSTEMS = ['day_type', 'five_min', 'footprint', 'woodies', 'tpo', 'killzone'];

const CANONICAL_SOURCES = new Set(['sierra_export', 'db', 'clock']);

const C = COLORS;
const MONO = 'ui-monospace, monospace';

// Local tints for the "live vs ממתין ל-backend vs אפיון" language (no token yet).
const PEND = '#7c8cff';
const PEND_BG = '#16172e';
const CFG = '#22b8cf';
const CFG_BG = '#0e2a30';

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
/* Static rule-book (📖 אפיון) — keep in sync until backend-exposed.    */
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

// 1R = ATR14 × multiplier, by pattern family (atr_caps.py ATR_MULTIPLIERS).
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
  return SYS_META[id] ?? { color: C.textTertiary, role: 'observer', label: id };
}

function isCanonical(src: string | null | undefined): boolean {
  return !!src && CANONICAL_SOURCES.has(src);
}

// isProxyGate REMOVED (2026-06-04): P0-2 (commit 8eb5747) replaced the
// confidence proxy with r_t1_gate in both S2+S4 inspectors. No component
// now carries key="confidence" in S2/S4. The ⧗ de-trust is no longer needed.

function fmtLag(lag: number | null | undefined): string {
  if (lag == null) return '?';
  if (lag < 1) return '<1s';
  if (lag < 60) return `${Math.round(lag)}s`;
  if (lag < 3600) return `${Math.round(lag / 60)}m`;
  return `${Math.round(lag / 3600)}h`;
}

/** 3-tier freshness: FRESH (<60s green), WARMING (60-threshold amber), STALE (>threshold red).
 * Woodies 5-min data naturally ages to ~300s between bars — that's WARMING, not broken. */
type FreshTier = 'fresh' | 'warming' | 'stale';
function freshTier(lag: number | null | undefined, threshold: number): FreshTier {
  if (lag == null) return 'stale';
  if (lag < 60) return 'fresh';
  if (lag < threshold) return 'warming';
  return 'stale';
}
const TIER_COLOR: Record<FreshTier, string> = { fresh: C.bull, warming: C.caution, stale: C.bear };
const TIER_BG: Record<FreshTier, string> = { fresh: C.bgSurface1, warming: '#2e2410', stale: '#2e1414' };
const TIER_BORDER: Record<FreshTier, string> = { fresh: C.borderTertiary, warming: '#f5a62345', stale: '#ef444445' };
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
/* Tiny presentational atoms                                           */
/* ------------------------------------------------------------------ */

type TagKind = 'live' | 'pend' | 'cfg';
function Tag({ kind, label }: { kind: TagKind; label?: string }) {
  const map: Record<TagKind, { fg: string; bg: string; bd: string; t: string }> = {
    live: { fg: C.bullLight, bg: '#0e3a1f', bd: '#22c55e30', t: '● חי' },
    pend: { fg: PEND, bg: PEND_BG, bd: '#7c8cff40', t: '⧗ ממתין ל-backend' },
    cfg: { fg: CFG, bg: CFG_BG, bd: '#22b8cf40', t: '📖 אפיון' },
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
    <div style={{ marginTop: 7, fontFamily: MONO, fontSize: 10.5, color: C.textSecondary, display: 'flex', gap: 6, lineHeight: 1.5 }}>
      <span style={{ color: C.textTertiary, flex: '0 0 auto' }}>↳ לתיקון:</span>
      <span style={{ color: pend ? PEND : C.warning }}>{children}</span>
    </div>
  );
}

/** Inline code path (LTR, monospace, tinted). */
function Path({ children, pend }: { children: ReactNode; pend?: boolean }) {
  return (
    <code style={{ direction: 'ltr', unicodeBidi: 'isolate', fontFamily: MONO, fontSize: 10, padding: '1px 6px', borderRadius: 4, color: pend ? PEND : C.warning, background: pend ? PEND_BG : '#2e2410' }}>
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
        fontSize: 9,
        padding: '1px 6px',
        borderRadius: 4,
        marginInlineStart: 6,
        color: canon ? C.bullLight : C.caution,
        background: canon ? '#0e3a1f' : '#2e2410',
        border: canon ? 'none' : `1px solid ${C.warning}`,
      }}
    >
      {source}
      {canon ? '' : ' ⚠'}
    </span>
  );
}

function StatusDot({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span style={{ fontSize: 10, color: C.textSecondary, fontFamily: MONO }}>
      <span style={{ color: ok ? C.bull : C.bear, marginInlineEnd: 3 }}>●</span>
      {label}
    </span>
  );
}

type StepKind = 'ok' | 'bad' | 'wait' | 'info' | 'pend';
function StepIcon({ kind }: { kind: StepKind }) {
  const map: Record<StepKind, { bg: string; fg: string; ch: string }> = {
    ok: { bg: '#0e3a1f', fg: C.bull, ch: '✓' },
    bad: { bg: '#3a1a1a', fg: C.bear, ch: '✕' },
    wait: { bg: '#2e2410', fg: C.caution, ch: '…' },
    info: { bg: C.bgSurface5, fg: C.textSecondary, ch: 'i' },
    pend: { bg: PEND_BG, fg: PEND, ch: '⧗' },
  };
  const s = map[kind];
  return (
    <span
      style={{
        width: 22,
        height: 22,
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
    <div style={{ display: 'grid', gridTemplateColumns: '22px 1fr', gap: 12, paddingBottom: last ? 0 : 14 }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <StepIcon kind={kind} />
        {!last && <div style={{ flex: 1, width: 2, background: C.borderTertiary, marginTop: 2 }} />}
      </div>
      <div>
        <div style={{ fontFamily: MONO, fontSize: 12, fontWeight: 600, color: C.textPrimary, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>{title}</div>
        {children && <div style={{ marginTop: 5, fontSize: 11.5, color: C.textSecondary, lineHeight: 1.6 }}>{children}</div>}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Component table (drill-down)                                        */
/* ------------------------------------------------------------------ */

function ComponentTable({ components }: { components: Component[] }) {
  if (!components || components.length === 0) {
    return <div style={{ padding: 8, fontSize: 10, color: C.textTertiary, fontStyle: 'italic' }}>אין נתוני רכיבים.</div>;
  }
  const th: CSSProperties = { padding: '4px 8px', fontWeight: 500, textAlign: 'start', color: C.textTertiary };
  return (
    <div style={{ background: C.bgSurface1, padding: '6px 12px 8px 28px', overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: MONO, fontSize: 10 }}>
        <thead>
          <tr>
            <th style={th}>stage</th>
            <th style={th}>key</th>
            <th style={th}>required</th>
            <th style={{ ...th, direction: 'ltr' }}>live</th>
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
            <tr key={`${c.stage}-${c.key}-${i}`} style={{ borderTop: i > 0 ? `1px solid ${C.borderFaint}` : 'none', color: c.present ? C.textPrimary : C.bearLight }}>
              <td style={{ padding: '3px 8px', color: C.textSecondary }}>{c.stage}</td>
              <td style={{ padding: '3px 8px', color: C.textSecondary }}>{c.key}</td>
              <td style={{ padding: '3px 8px', color: C.textTertiary }}>{c.required ?? c.spec ?? '—'}</td>
              <td style={{ padding: '3px 8px', direction: 'ltr', color: C.textPrimary }}>{c.live ?? c.value ?? '—'}</td>
              <td style={{ padding: '3px 8px', textAlign: 'center' }}>
                {c.present ? (
                  <span style={{ color: C.bull }}>✓</span>
                ) : (
                  <span style={{ color: C.bear }}>✕</span>
                )}
              </td>
              <td style={{ padding: '3px 8px' }}>{c.freshness?.source ? <SrcPill source={c.freshness.source} /> : <span style={{ color: C.textTertiary }}>—</span>}</td>
              <td style={{ padding: '3px 8px', textAlign: 'center', fontFamily: MONO, fontSize: 9 }}>
                {cLag != null ? (
                  <span style={{ color: TIER_COLOR[cTier], padding: '1px 5px', borderRadius: 3, background: TIER_BG[cTier] }}>
                    {fmtLag(cLag)}
                  </span>
                ) : (
                  <span style={{ color: C.textTertiary }}>—</span>
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
  fired: { fg: C.bull, bg: '#0e3a1f' },
  armed: { fg: C.caution, bg: '#2e2410' },
  blocked: { fg: C.bear, bg: '#3a1a1a' },
  vetoed: { fg: C.bearLight, bg: '#3a1a1a' },
  not_applicable: { fg: C.textTertiary, bg: C.bgSurface5 },
  unknown: { fg: C.textTertiary, bg: C.bgSurface5 },
};

function PatternRow({ pattern }: { pattern: Pattern }) {
  const [open, setOpen] = useState(false);
  const b = PATTERN_BADGE[pattern.status] ?? PATTERN_BADGE.unknown;
  return (
    <div style={{ borderTop: `1px solid ${C.borderFaint}` }}>
      <div
        onClick={() => setOpen((o) => !o)}
        style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 10px', cursor: 'pointer', background: open ? C.bgSurface2 : 'transparent' }}
      >
        <span style={{ color: C.textTertiary, fontSize: 10 }}>{open ? '▼' : '▶'}</span>
        <span style={{ fontFamily: MONO, fontSize: 11, fontWeight: 600, color: C.textPrimary, minWidth: 150 }}>
          {pattern.name}
          <span style={{ display: 'block', fontSize: 9, fontWeight: 400, color: C.textTertiary }}>{pattern.id}</span>
        </span>
        <span style={{ fontFamily: MONO, fontSize: 10, fontWeight: 700, color: b.fg, background: b.bg, padding: '2px 9px', borderRadius: 5 }}>
          {pattern.label || pattern.status}
        </span>
        <span style={{ flex: 1, fontSize: 11, color: C.textSecondary }}>{pattern.reason}</span>
        <span style={{ fontFamily: MONO, fontSize: 10, color: pattern.fired_today ? C.bull : C.textTertiary }}>{fmtET(pattern.last_fire_ts)}</span>
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
    <div style={{ display: 'flex', alignItems: 'center', gap: 18, flexWrap: 'wrap', marginTop: 14, padding: '10px 16px', borderRadius: 9, background: C.bgSurface1, border: `1px solid ${C.borderTertiary}`, fontFamily: MONO, fontSize: 11.5 }}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, color: C.textSecondary }}>
        <Tag kind="live" /> <b style={{ color: C.textPrimary }}>נפלט מ-/api/v9/build/pattern-status</b>
      </span>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, color: C.textSecondary }}>
        <Tag kind="pend" /> <b style={{ color: C.textPrimary }}>השדה לא נפלט עדיין — לא מסונתז ב-frontend</b>
      </span>
      <span style={{ flex: 1 }} />
      <span style={{ color: C.textTertiary }}>מקור-אמת · CLAUDE.md Rule 1: חסר = "ממתין ל-backend", לא ערך מומצא</span>
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

  const th: CSSProperties = { padding: '5px 8px', fontWeight: 500, textAlign: 'start', color: C.textTertiary, fontSize: 9, textTransform: 'uppercase' };
  const td: CSSProperties = { padding: '4px 8px', fontFamily: MONO, fontSize: 10 };

  const renderCheckTable = (checks: typeof PRE_FIRE_CHECKS, label: string, fix: string) => (
    <div style={{ border: `1px solid ${C.borderFaint}`, borderRadius: 9, background: C.bgSurface1, padding: '14px 16px', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 9, flexWrap: 'wrap', marginBottom: 10 }}>
        <span style={{ fontFamily: MONO, fontSize: 13, fontWeight: 700, color: C.textPrimary }}>{label}</span>
        <Tag kind="pend" label="⧗ ממתין לחשיפה · P0" />
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={th}>בדיקה</th>
            <th style={th}>spec</th>
            <th style={th}>required</th>
            <th style={{ ...th, textAlign: 'center' }}>status</th>
            <th style={th}>source</th>
          </tr>
        </thead>
        <tbody>
          {checks.map((ch, i) => {
            const live = findLive(ch.key);
            const present = live?.present;
            return (
              <tr key={ch.key} style={{ borderTop: i > 0 ? `1px solid ${C.borderFaint}` : 'none' }}>
                <td style={{ ...td, color: C.textSecondary }}>{ch.key}</td>
                <td style={{ ...td, color: C.textTertiary }}>{ch.spec}</td>
                <td style={{ ...td, color: C.textTertiary }}>{ch.required}</td>
                <td style={{ ...td, textAlign: 'center' }}>
                  {live != null ? (
                    <span style={{ color: present ? C.bull : C.bear }}>{present ? '✓' : '✕'}</span>
                  ) : (
                    <span style={{ color: PEND, fontSize: 9 }}>⧗</span>
                  )}
                </td>
                <td style={{ ...td, color: C.textTertiary, fontSize: 9 }}>{ch.source}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <FixRef pend>
        חשוף מ-<Path pend>{fix}</Path> → <Path pend>aggregator.py</Path>
      </FixRef>
    </div>
  );

  return (
    <div style={{ marginTop: 18 }}>
      <SLab>
        שערי-אש גלובליים · חלים על כל מערכת יורה <Tag kind="pend" label="⧗ ממתין · P0" />
      </SLab>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(360px,1fr))', gap: 12 }}>
        {renderCheckTable(PRE_FIRE_CHECKS, 'pre_fire_validator · 7 בדיקות', 'backend/v9/shared/pre_fire_validator.py')}
        {renderCheckTable(RISK_CHECKS, 'risk_checks · LIVE caps', 'backend/v9/gateway/risk_checks.py')}
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
    <div style={{ marginTop: 20 }}>
      <SLab>
        שכבה 0 · מקורות חיים — Sierra → bridge → API <Tag kind="live" label="● חי · data_freshness" />
      </SLab>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(170px,1fr))', gap: 10 }}>
        {sources.map((s) => {
          const lag = s.data_freshness?.lag_seconds;
          const thresh = s.data_freshness?.threshold_seconds ?? 300;
          const tier = freshTier(lag, thresh);
          const meta = sysMeta(s.id);
          return (
            <div key={s.id} style={{ padding: '11px 12px', borderRadius: 9, background: TIER_BG[tier], border: `1px solid ${TIER_BORDER[tier]}` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontFamily: MONO, fontSize: 12, color: C.textPrimary, fontWeight: 600 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: TIER_COLOR[tier], flex: '0 0 auto' }} />
                {meta.label.replace(/^S\d+ · /, '')}
              </div>
              <div style={{ marginTop: 6, fontFamily: MONO, fontSize: 10, color: TIER_COLOR[tier] }}>
                {TIER_LABEL[tier]} {fmtLag(lag)}
                <span style={{ color: C.textTertiary }}> · סף {thresh}s</span>
              </div>
              {tier === 'warming' && (
                <div style={{ marginTop: 3, fontFamily: MONO, fontSize: 9, color: C.textTertiary }}>
                  ממתין לבר הבא — נתון תקין
                </div>
              )}
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
    <div style={{ fontSize: 10, color: C.textTertiary, textTransform: 'uppercase', letterSpacing: '.6px', fontFamily: MONO, margin: '0 2px 10px', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
      {children}
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
      <div style={{ fontFamily: MONO, fontSize: 11, color: C.textTertiary, padding: '6px 0' }}>
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
          <div key={pid} style={{ border: `1px solid ${C.borderFaint}`, borderRadius: 6, background: C.bgSurface5, padding: '8px 12px' }}>
            <div style={{ fontFamily: MONO, fontSize: 11, fontWeight: 700, color: C.textPrimary, marginBottom: 6 }}>{pid}</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '3px 16px', fontFamily: MONO, fontSize: 11 }}>
              {/* Stop */}
              <div style={{ color: C.textSecondary }}>stop</div>
              <div style={{ direction: 'ltr', color: stopLive === '—' ? PEND : C.textPrimary }}>{stopLive === '—' ? '⧗ ממתין' : stopLive}</div>
              {/* R:R gate */}
              <div style={{ color: C.textSecondary }}>r_t1</div>
              <div style={{ direction: 'ltr', color: r_t1Live == null ? PEND : r_t1Ok ? C.bull : C.bear }}>
                {r_t1Live == null || r_t1Live === 'null' ? '⧗ ממתין' : r_t1Live}
                {r_t1Live != null && r_t1Live !== 'null' && <span style={{ color: r_t1Ok ? C.bull : C.bear, marginInlineStart: 6 }}>{r_t1Ok ? '✓' : '✕'}</span>}
              </div>
              {/* Targets */}
              <div style={{ color: C.textSecondary }}>targets</div>
              <div style={{ direction: 'ltr', color: tgtLive === '—' ? PEND : C.textPrimary }}>{tgtLive === '—' ? '⧗ ממתין' : tgtLive}</div>
              {/* Sizing / time_stop (S2 only) */}
              {sizeC && (
                <>
                  <div style={{ color: C.textSecondary }}>sizing / time</div>
                  <div style={{ direction: 'ltr', color: C.textPrimary }}>{sizeC.live ?? sizeC.value ?? '—'}</div>
                </>
              )}
              {/* Day-Type Matrix verdict (S4 only) */}
              {matrixC && (
                <>
                  <div style={{ color: C.textSecondary }}>matrix</div>
                  <div style={{ direction: 'ltr', color: matrixC.present ? C.bull : C.bear }}>{matrixC.live ?? matrixC.value ?? '—'}</div>
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
/* Day-Type Matrix verdict for S4 — ✅/⚠️/❌ per pattern×day_type      */
/* ------------------------------------------------------------------ */

// Woodies pattern families mapped to their day-type compatibility.
// Source: targets_table.py + atr_caps.py + Day-Type decision matrix.
const WOODIES_PATTERNS = [
  'ZLR', 'GB100', 'GB50', 'RB100', 'RB50',
  'TLB', 'HFE', 'FAMIR', 'GHOST',
];

/** Map day_type to which pattern families are allowed/limited. */
function dayTypePatternVerdict(dayType: string | null, patternId: string): '✅' | '⚠️' | '❌' {
  if (!dayType) return '⚠️'; // unknown day → cautious
  const d = dayType.toLowerCase();
  const p = patternId.toUpperCase();
  // Nontrend = no trade for any pattern
  if (d === 'nontrend') return '❌';
  // Trend days: all patterns allowed
  if (d.startsWith('trend')) return '✅';
  // Variation: most allowed, GHOST/FAMIR limited
  if (d === 'variation') return (p === 'GHOST' || p === 'FAMIR') ? '⚠️' : '✅';
  // Normal: only reactive patterns (ZLR, GB, RB)
  if (d === 'normal') return (p.startsWith('ZLR') || p.startsWith('GB') || p.startsWith('RB')) ? '✅' : '❌';
  // Neutral_Extreme / Neutral_Center: only ZLR
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
  // Show matrix of known Woodies patterns × active day_type
  const pids = patterns.length > 0
    ? patterns.map((p) => p.id.replace(/^woodies_/, '').toUpperCase())
    : WOODIES_PATTERNS;

  const hasMatrix = patterns.some((p) => (p.components ?? []).some((c) => c.key === 'day_type_matrix'));

  return (
    <Step kind={activeDay ? 'ok' : 'pend'} title={<>Day-Type Matrix · S4 verdict {activeDay ? <Tag kind="live" /> : <Tag kind="pend" />}</>}>
      {!activeDay ? (
        <span style={{ color: C.textTertiary }}>Day Type לא סווג — אין verdict.</span>
      ) : (
        <div>
          <div style={{ fontFamily: MONO, fontSize: 11, color: C.textSecondary, marginBottom: 8 }}>
            יום חי: <b style={{ color: '#5b9bff' }}>{activeDay}</b> · {entryHint(activeDay)} · {t1Ref(activeDay)}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 8px', fontFamily: MONO, fontSize: 11 }}>
            {pids.map((pid) => {
              const v = dayTypePatternVerdict(activeDay, pid);
              // Check if backend provides a live matrix verdict
              const liveComp = patterns.find((p) => p.id.toUpperCase().includes(pid))
                ?.components?.find((c) => c.key === 'day_type_matrix');
              const displayV = liveComp ? (liveComp.present ? '✅' : '❌') : v;
              const color = displayV === '✅' ? C.bull : displayV === '⚠️' ? C.caution : C.bear;
              return (
                <span key={pid} style={{ padding: '3px 8px', borderRadius: 5, border: `1px solid ${C.borderFaint}`, background: C.bgSurface5 }}>
                  <span style={{ color }}>{displayV}</span>{' '}
                  <span style={{ color: C.textSecondary }}>{pid}</span>
                  {liveComp && <SrcPill source="in_memory" />}
                </span>
              );
            })}
          </div>
          {!hasMatrix && (
            <div style={{ marginTop: 6, fontFamily: MONO, fontSize: 10, color: C.textTertiary }}>
              verdict מחושב מטבלת-אפיון סטטית · backend matrix = <span style={{ color: PEND }}>⧗ ממתין</span>
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
    verdict.kind === 'fired' ? C.bull : verdict.kind === 'armed' ? C.caution : verdict.kind === 'blocked' ? C.bear : C.textTertiary;
  const vbBg =
    verdict.kind === 'fired' ? '#0e3a1f' : verdict.kind === 'armed' ? '#2e2410' : verdict.kind === 'blocked' ? '#3a1a1a' : C.bgSurface5;

  const lag = sys.data_freshness?.lag_seconds;
  const thresh = sys.data_freshness?.threshold_seconds ?? 300;
  const tier = freshTier(lag, thresh);
  const gates = sys.global_gates ?? [];
  const inputs = sys.live_inputs ?? [];
  const interps = sys.interpretations ?? [];
  const gatesOk = gates.length > 0 ? gates.every((g) => g.present) : null;

  return (
    <div style={{ border: `1px solid ${C.borderFaint}`, borderRadius: 8, marginBottom: 12, background: C.bgSurface1, overflow: 'hidden' }}>
      {/* header */}
      <div
        onClick={() => setOpen((o) => !o)}
        style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '13px 14px', cursor: 'pointer', borderInlineStart: `3px solid ${meta.color}` }}
      >
        <span style={{ color: C.textTertiary, fontSize: 11 }}>{open ? '▼' : '▶'}</span>
        <span style={{ fontFamily: MONO, fontWeight: 700, fontSize: 14, color: meta.color }}>{meta.label}</span>
        <span style={{ fontSize: 9, fontFamily: MONO, padding: '2px 7px', borderRadius: 5, textTransform: 'uppercase', color: meta.role === 'firing' ? meta.color : C.textSecondary, border: `1px solid ${C.borderTertiary}` }}>
          {meta.role}
        </span>
        <StatusDot ok={!!sys.running} label={`run ${sys.running ? 'on' : 'off'}`} />
        <StatusDot ok={!!sys.hydrated} label={`hyd ${sys.hydrated ? 'ok' : 'no'}`} />
        <span style={{ flex: 1 }} />
        <span style={{ fontFamily: MONO, fontSize: 10, color: TIER_COLOR[tier] }}>lag {fmtLag(lag)}{tier === 'warming' ? ' ⏳' : ''}</span>
        <span style={{ fontFamily: MONO, fontSize: 11, fontWeight: 700, color: vbColor, background: vbBg, padding: '4px 11px', borderRadius: 6 }}>{verdict.label}</span>
      </div>

      {open && (
        <div style={{ borderTop: `1px solid ${C.borderFaint}`, padding: '16px 18px' }}>
          {/* 1 SOURCE */}
          <Step kind={tier === 'fresh' ? 'ok' : tier === 'warming' ? 'wait' : 'bad'} title={<>מקור · stream freshness <Tag kind="live" /></>}>
            <span style={{ color: TIER_COLOR[tier] }}>{tier === 'fresh' ? 'טרי' : tier === 'warming' ? 'ממתין לבר הבא' : 'תקוע'}</span> · lag {fmtLag(lag)} · סף {thresh}s · last_bar {fmtET(sys.data_freshness?.last_bar_ts)}
            {tier === 'warming' && (
              <div style={{ marginTop: 4, fontFamily: MONO, fontSize: 10, color: C.textTertiary }}>
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
          <Step kind={inputs.length ? 'ok' : 'info'} title={<>קלט · live inputs {inputs.length ? <Tag kind="live" /> : <Tag kind="pend" />}</>}>
            {inputs.length === 0 ? (
              <>
                <span style={{ color: C.textTertiary }}>ממתין ל-backend — ה-inspector לא פולט live_inputs למערכת זו.</span>
                {INSPECTOR_PATH[sys.id] && (
                  <FixRef pend>
                    הוסף live_inputs ב-<Path pend>{INSPECTOR_PATH[sys.id]}</Path>
                  </FixRef>
                )}
              </>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '3px 16px', fontFamily: MONO }}>
                {inputs.map((inp, i) => (
                  <span key={i} style={{ fontSize: 11 }}>
                    <span style={{ color: C.textTertiary }}>{inp.field}=</span>
                    <span style={{ color: inp.fresh === false ? C.bearLight : C.textPrimary }}>{inp.value ?? '—'}</span>
                    {inp.source && <SrcPill source={inp.source} />}
                  </span>
                ))}
              </div>
            )}
          </Step>

          {/* 3 INTERPRETATION */}
          <Step kind={interps.length ? 'ok' : 'info'} title={<>פרשנות · derived {interps.length ? <Tag kind="live" /> : <Tag kind="pend" />}</>}>
            {interps.length === 0 ? (
              <span style={{ color: C.textTertiary }}>ממתין ל-backend — אין interpretations.</span>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '3px 16px', fontFamily: MONO }}>
                {interps.map((it, i) => (
                  <span key={i} style={{ fontSize: 11 }}>
                    <span style={{ color: C.bull }}>{it.key}:</span> <span style={{ color: C.textPrimary }}>{it.value ?? '—'}</span>
                    {it.from_input && <span style={{ color: C.textTertiary, fontSize: 9 }}> ←{it.from_input}</span>}
                  </span>
                ))}
              </div>
            )}
          </Step>

          {/* 4 GATES */}
          <Step kind={gatesOk == null ? 'info' : gatesOk ? 'ok' : 'bad'} title={<>שערים · stream / global gates</>}>
            {gates.length === 0 ? (
              <span style={{ color: C.textTertiary }}>אין global_gates למערכת זו.</span>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 10px', fontFamily: MONO, fontSize: 11 }}>
                {gates.map((g) => {
                  return (
                    <span key={g.key} style={{ color: g.present ? C.textSecondary : C.bearLight }}>
                      <span style={{ color: g.present ? C.bull : C.bear }}>{g.present ? '✓' : '✕'}</span> {g.key}
                      {g.live != null && <span style={{ color: C.textTertiary }}> ={g.live}</span>}
                      {g.freshness?.source && <SrcPill source={g.freshness.source} />}
                    </span>
                  );
                })}
              </div>
            )}
            {isFiring && (
              <div style={{ marginTop: 6, color: PEND, fontFamily: MONO, fontSize: 11 }}>
                ⧗ {sys.id === 'woodies' ? 'A7 · anti-patterns' : sys.id === 'five_min' ? 'S6 Killzone · S/R proximity · COT>AMT' : 'שערים נוספים'} <Tag kind="pend" />
                <FixRef pend>
                  שערים אמיתיים ב-<Path pend>{INSPECTOR_PATH[sys.id] ?? 'inspector'}</Path>
                </FixRef>
              </div>
            )}
          </Step>

          {/* 4.5 DAY-TYPE MATRIX — S4 only: ✅/⚠️/❌ per pattern×day_type */}
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

          {/* 6 TARGETS/STOP — firing only, live from P0-2 (8eb5747) */}
          {isFiring && (
            <Step kind={sys.patterns.some((p) => (p.components ?? []).some((c) => c.stage === 'targets_stop' && c.present)) ? 'ok' : 'info'} last title={<>TARGETS / STOP</>}>
              <TargetsStopLive patterns={sys.patterns} />
            </Step>
          )}

          {/* patterns */}
          {sys.patterns.length > 0 && (
            <div style={{ marginTop: 12, border: `1px solid ${C.borderFaint}`, borderRadius: 6, overflow: 'hidden' }}>
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
          <span style={{ color: C.bull }}>● מחווט</span> <Tag kind="live" />
          <br />
          {tpoSys.global_gates.length > 0 ? (
            <span style={{ fontFamily: MONO, fontSize: 10 }}>
              {tpoSys.global_gates.map((g) => (
                <span key={g.key} style={{ marginInlineEnd: 8 }}>
                  <span style={{ color: g.present ? C.bull : C.bear }}>{g.present ? '✓' : '✕'}</span> {g.key}
                </span>
              ))}
            </span>
          ) : (
            <>POC/VAH/VAL · IB · profile_shape · otf_clarity</>
          )}
          <br />
          <span style={{ fontSize: 10, color: C.textTertiary }}>A5 = advisory בלבד (לא חוסם ירי)</span>
        </>
      ) : (
        <>
          <span style={{ color: PEND }}>⧗ לא מחווט כלל</span> — חסר <span style={{ direction: 'ltr' }}>tpo_inspector</span>.
          <br />
          POC/VAH/VAL · IB · profile_shape · otf_clarity
          <br />
          <span style={{ fontSize: 10, color: C.textTertiary }}>A5 = advisory בלבד (לא חוסם ירי)</span>
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
          <span style={{ color: C.bull }}>● מחווט</span> <Tag kind="live" />
          <br />
          {kzSys.global_gates.length > 0 ? (
            <span style={{ fontFamily: MONO, fontSize: 10 }}>
              {kzSys.global_gates.map((g) => (
                <span key={g.key} style={{ marginInlineEnd: 8 }}>
                  <span style={{ color: g.present ? C.bull : C.bear }}>{g.present ? '✓' : '✕'}</span> {g.key}
                  {g.live != null && <span style={{ color: C.textTertiary }}> ={g.live}</span>}
                </span>
              ))}
            </span>
          ) : (
            <>is_gate_open · quality · sizing_modifier · block_reason</>
          )}
          {kzSys.interpretations?.map((it) => (
            <div key={it.key} style={{ fontFamily: MONO, fontSize: 10, color: C.textSecondary }}>
              {it.key}: {it.value}
            </div>
          ))}
        </>
      ) : (
        <>
          <span style={{ color: PEND }}>⧗ לא מחווט כלל</span> — חסר <span style={{ direction: 'ltr' }}>killzone_inspector</span>.
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
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(220px,1fr))', gap: 10 }}>
        {cards.map((c) => {
          const meta = sysMeta(c.id);
          return (
            <div key={c.id} style={{ borderRadius: 9, border: `1px ${c.wired ? 'solid' : 'dashed'} ${c.wired ? C.borderTertiary : `${PEND}45`}`, background: c.wired ? C.bgSurface1 : PEND_BG, padding: '11px 13px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: MONO, fontSize: 12, color: C.textPrimary, fontWeight: 600 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: meta.color, flex: '0 0 auto' }} />
                {meta.label}
                <span style={{ fontSize: 9, color: C.textSecondary, textTransform: 'uppercase' }}>{meta.role}</span>
              </div>
              <div style={{ marginTop: 6, fontFamily: MONO, fontSize: 11, color: C.textSecondary, lineHeight: 1.6 }}>{c.lines}</div>
              {c.fix && <FixRef pend>צור / חווט: {c.fix}</FixRef>}
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

const VERDICT_STYLE: Record<string, { fg: string; bg: string }> = {
  READY: { fg: C.bull, bg: '#0e3a1f' },
  DEGRADED: { fg: C.warning, bg: '#2e2410' },
  BLOCKED: { fg: C.bear, bg: '#3a1a1a' },
};

function Blocker({ readiness }: { readiness: Readiness | undefined }) {
  if (!readiness) return null;
  const checks = readiness.checks ?? [];
  const blocker = checks.find((c) => !c.passed && c.severity === 'block');
  const degraded = checks.filter((c) => !c.passed && c.severity === 'degrade');
  if (!blocker && degraded.length === 0) return null;
  const isBlock = !!blocker;
  return (
    <div style={{ margin: '14px 0 0', borderRadius: 8, padding: '14px 16px', background: isBlock ? '#2e1414' : '#2e2410', border: `1px solid ${isBlock ? C.bear : C.warning}55` }}>
      <div style={{ fontSize: 14, fontWeight: 700, color: isBlock ? C.bearLight : C.caution, direction: 'rtl' }}>
        {isBlock ? `למה לא נכנסנו עכשיו — ${blockerHebrew(blocker!)}` : `מצב מוגבל — ${degraded.map(blockerHebrew).join(' · ')}`}
      </div>
      {readiness.reason && <div style={{ marginTop: 6, fontSize: 11.5, color: C.textSecondary, fontFamily: MONO }}>{readiness.reason}</div>}
      {isBlock && (
        <FixRef>
          בדוק <Path>/tmp/bridge.err.log</Path> · runbook <Path>docs/runbooks/SIERRA_DLL_OPS.md</Path>
        </FixRef>
      )}
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
  const th: CSSProperties = { padding: '9px 12px', fontSize: 10, textTransform: 'uppercase', letterSpacing: '.5px', color: C.textTertiary, textAlign: 'start', borderBottom: `1px solid ${C.borderFaint}` };
  return (
    <div>
      <div style={{ fontSize: 10, color: C.textTertiary, textTransform: 'uppercase', letterSpacing: '.6px', fontFamily: MONO, margin: '6px 2px 12px' }}>
        כל שדה שמערכת צורכת — הערך, המקור, והאם קנוני
      </div>
      {rows.length === 0 ? (
        <div style={{ color: C.textTertiary, fontSize: 12, padding: 16 }}>אין שדות עם מקור לתצוגה (ה-inspector עוד לא פולט freshness.source).</div>
      ) : (
        <div style={{ border: `1px solid ${C.borderFaint}`, borderRadius: 8, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: MONO, fontSize: 12 }}>
            <thead>
              <tr>
                <th style={th}>שדה</th>
                <th style={{ ...th, direction: 'ltr' }}>ערך חי</th>
                <th style={th}>מקור</th>
                <th style={{ ...th, textAlign: 'center' }}>קנוני</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => {
                const canon = isCanonical(r.source);
                return (
                  <tr key={i} style={{ borderTop: `1px solid ${C.borderFaint}`, background: canon ? 'transparent' : '#2e2410' }}>
                    <td style={{ padding: '10px 12px', color: canon ? C.textPrimary : C.caution }}>{r.field}</td>
                    <td style={{ padding: '10px 12px', direction: 'ltr', color: C.textSecondary }}>{r.value}</td>
                    <td style={{ padding: '10px 12px' }}>{r.source ? <SrcPill source={r.source} /> : '—'}</td>
                    <td style={{ padding: '10px 12px', textAlign: 'center' }}>{canon ? <span style={{ color: C.bull }}>✓</span> : <span style={{ color: C.bear }}>✕</span>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {derived.length > 0 && (
        <div style={{ marginTop: 16, border: `1px solid ${C.warning}55`, borderRadius: 8, background: '#2e2410', padding: '14px 16px' }}>
          <div style={{ fontSize: 13, color: C.caution, fontFamily: MONO }}>⚠ {derived.length} שדות ממקור לא-קנוני</div>
          <p style={{ margin: '6px 0 0', fontSize: 12, color: C.textSecondary, lineHeight: 1.6 }}>
            ערך שמסומן present אך מקורו אינו sierra_export/db הוא סיכון לפי כלל "Honest failure &gt; synthetic value". אל תסמוך על איתות שתלוי בו עד אימות מול המקור הקנוני.
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
/* Day-type tables tab (אפיון · config mirror)                         */
/* ------------------------------------------------------------------ */

function DayTypeTables({ activeDay }: { activeDay: string | null }) {
  const initial = DAY_TARGETS.find((d) => d.key === activeDay)?.key ?? 'Trend_Normal';
  const [sel, setSel] = useState<string>(initial);
  const day = DAY_TARGETS.find((d) => d.key === sel) ?? DAY_TARGETS[0];

  const th: CSSProperties = { padding: '9px 12px', fontSize: 10, textTransform: 'uppercase', letterSpacing: '.5px', color: C.textTertiary, textAlign: 'start', borderBottom: `1px solid ${C.borderFaint}` };
  const td: CSSProperties = { padding: '10px 12px', borderBottom: `1px solid ${C.borderFaint}`, color: C.textSecondary, fontFamily: MONO, fontSize: 12 };

  const Cell = ({ k, v, sub, hl, color }: { k: string; v: string; sub?: string; hl?: boolean; color?: string }) => (
    <div style={{ border: `1px solid ${hl ? '#2dd4a740' : C.borderTertiary}`, borderRadius: 9, background: hl ? '#10201c' : C.bgSurface1, padding: '13px 15px' }}>
      <div style={{ fontFamily: MONO, fontSize: 10, color: C.textTertiary, textTransform: 'uppercase', letterSpacing: '.5px', marginBottom: 6 }}>{k}</div>
      <div style={{ fontFamily: MONO, fontSize: v.length > 6 ? 13 : 17, fontWeight: 700, color: color ?? C.textPrimary }}>{v}</div>
      {sub && <div style={{ fontFamily: MONO, fontSize: 10, color: C.textSecondary, marginTop: 3 }}>{sub}</div>}
    </div>
  );

  return (
    <div>
      <SLab>
        טבלאות החלטה לכל סוג יום — יעדים · חוזים · time-stop · מרחק סטופ <Tag kind="cfg" label="📖 אפיון · rule-book" />
      </SLab>
      <div style={{ fontFamily: MONO, fontSize: 11, color: C.textTertiary, margin: '0 2px 16px', lineHeight: 1.6 }}>
        מקור: <span style={{ direction: 'ltr' }}>day_type/targets_table.py</span> + <span style={{ direction: 'ltr' }}>five_min/atr_caps.py</span>. ערכי קונפיג סטטיים (ספר-החוקים), לא חיים — verbatim. סוג היום החי{' '}
        {activeDay ? <b style={{ color: '#5b9bff' }}>{activeDay}</b> : <span style={{ color: C.textTertiary }}>(לא סווג)</span>} מודגש ונבחר אוטומטית.
      </div>

      {/* master overview */}
      <div style={{ border: `1px solid ${C.borderFaint}`, borderRadius: 8, overflow: 'hidden', background: C.bgSurface1, marginBottom: 18 }}>
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
                <tr key={d.key} style={{ borderTop: `1px solid ${C.borderFaint}`, background: isActive ? '#10201c' : 'transparent' }}>
                  <td style={{ ...td, color: d.noTrade ? C.bear : isActive ? C.bullLight : C.textPrimary }}>
                    {d.key}
                    {isActive && <span style={{ marginInlineStart: 7, fontSize: 9, padding: '1px 6px', borderRadius: 9, background: '#0e3a1f', color: C.bullLight }}>● היום</span>}
                  </td>
                  {d.noTrade ? (
                    <td style={{ ...td, color: C.bear, textAlign: 'center' }} colSpan={6}>
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
                  <td style={{ ...td, textAlign: 'center', color: d.noTrade ? C.bear : C.textPrimary, fontWeight: 700 }}>{d.contracts}</td>
                  <td style={td}>{d.sizing}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* day sub-tabs */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', margin: '0 0 18px' }}>
        {DAY_TARGETS.map((d) => {
          const on = d.key === sel;
          return (
            <div
              key={d.key}
              onClick={() => setSel(d.key)}
              style={{ padding: '8px 14px', borderRadius: 8, fontFamily: MONO, fontSize: 12, fontWeight: 600, cursor: 'pointer', color: on ? C.textPrimary : d.noTrade ? C.bear : C.textSecondary, background: on ? C.bgSurface5 : C.bgSurface1, boxShadow: `inset 0 0 0 1px ${on ? C.borderSecondary : C.borderTertiary}`, display: 'flex', alignItems: 'center', gap: 7 }}
            >
              {d.key}
              {d.key === activeDay && <span style={{ fontSize: 8.5, padding: '1px 6px', borderRadius: 9, background: '#0e3a1f', color: C.bullLight }}>● היום</span>}
            </div>
          );
        })}
      </div>

      {/* selected day plan */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 14 }}>
        <span style={{ fontFamily: MONO, fontSize: 17, fontWeight: 700, color: day.noTrade ? C.bear : day.key === activeDay ? C.bull : C.textPrimary }}>{day.key}</span>
        {day.key === activeDay && <Tag kind="live" label="● סוג היום החי" />}
        {day.noTrade && <span style={{ fontFamily: MONO, fontSize: 11, padding: '3px 10px', borderRadius: 6, background: '#3a1a1a', color: C.bearLight, fontWeight: 700 }}>NO TRADE</span>}
      </div>

      {!day.noTrade && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(150px,1fr))', gap: 12, marginBottom: 16 }}>
          <Cell k="כניסה" v="trigger התבנית" sub="סטופ = 1R" hl color={C.bull} />
          <Cell k="T1" v={day.t1} color={C.bull} />
          <Cell k="T2" v={day.t2} color={C.bull} />
          <Cell k="T3" v={day.t3} color={C.bull} />
          <Cell k="חוזים" v={String(day.contracts)} sub={day.sizing} hl color={C.bull} />
          <Cell k="time-stop" v={day.timeStop} />
          <Cell k="trail" v={day.trail} />
        </div>
      )}

      <div style={{ fontFamily: MONO, fontSize: 11, color: C.textSecondary, lineHeight: 1.6, borderInlineStart: `3px solid ${C.borderSecondary}`, padding: '4px 0 4px 12px', marginBottom: 16 }}>
        <b style={{ color: C.textPrimary }}>אפיון:</b> {day.note}
      </div>
      {day.override && (
        <div style={{ fontFamily: MONO, fontSize: 11, color: C.warning, lineHeight: 1.6, borderInlineStart: `3px solid ${C.warning}`, padding: '4px 0 4px 12px', marginBottom: 16 }}>
          <b style={{ color: C.textPrimary }}>Override:</b> {day.override}
        </div>
      )}

      {/* ATR multipliers */}
      <SLab>
        מרחק הסטופ (1R) = ATR14 × מכפיל לפי משפחת-תבנית <Tag kind="cfg" label="📖 atr_caps.py" />
      </SLab>
      <div style={{ border: `1px solid ${C.borderFaint}`, borderRadius: 8, overflow: 'hidden', background: C.bgSurface1, marginBottom: 18 }}>
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
              <tr key={name} style={{ borderTop: `1px solid ${C.borderFaint}` }}>
                <td style={{ ...td, color: C.textPrimary }}>{name}</td>
                <td style={{ ...td, textAlign: 'center', color: C.textPrimary, fontWeight: 700 }}>×{mult.toFixed(1)}</td>
                <td style={td}>{ns}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* pattern time stops */}
      <SLab>
        time-stop לפי ציר-תבנית (Layer-3 backstop) — בפועל <span style={{ direction: 'ltr' }}>min(day, pattern)</span> <Tag kind="cfg" label="📖 atr_caps.py · D-094 §3.C" />
      </SLab>
      <div style={{ border: `1px solid ${C.borderFaint}`, borderRadius: 8, overflow: 'hidden', background: C.bgSurface1 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: MONO, fontSize: 12 }}>
          <thead>
            <tr>
              <th style={th}>תבנית</th>
              <th style={{ ...th, textAlign: 'center' }}>time-stop (דק׳)</th>
            </tr>
          </thead>
          <tbody>
            {PATTERN_TIME_STOPS.map(([name, mins]) => (
              <tr key={name} style={{ borderTop: `1px solid ${C.borderFaint}` }}>
                <td style={{ ...td, color: C.textPrimary }}>{name}</td>
                <td style={{ ...td, textAlign: 'center' }}>{mins}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: 18, fontSize: 11, color: C.textTertiary, lineHeight: 1.7, fontFamily: MONO }}>
        הערה: טבלאות אלה הן אפיון סטטי (config) — מותר להציגן verbatim. ה-<b style={{ color: C.textPrimary }}>הקרנה</b> שלהן למחירים חיים (entry/stop/T1‑T3 ב-$) היא שלב TARGETS/STOP שעדיין <span style={{ color: PEND }}>⧗ ממתין ל-backend</span>: ה-1R החי חייב להגיע מ-inspector, לא להיגזר ב-frontend.
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
    P0: { fg: C.bearLight, bg: '#3a1a1a' },
    P1: { fg: C.caution, bg: '#2e2410' },
    P2: { fg: C.textSecondary, bg: C.bgSurface5 },
  };
  return (
    <div>
      <div style={{ fontSize: 10, color: C.textTertiary, textTransform: 'uppercase', letterSpacing: '.6px', fontFamily: MONO, margin: '6px 2px 12px' }}>
        רכיבים שהאפיון דורש אך ה-backend עוד לא פולט — ראה docs/plans/BUILD_STATUS_COMPONENT_AUDIT.md
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(300px,1fr))', gap: 12 }}>
        {MISSING.map((m, i) => {
          const pc = priColor[m.pri];
          return (
            <div key={i} style={{ border: `1px solid ${C.borderFaint}`, borderRadius: 8, background: C.bgSurface1, padding: '14px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <span style={{ fontSize: 9, fontFamily: MONO, fontWeight: 700, padding: '2px 8px', borderRadius: 5, color: pc.fg, background: pc.bg }}>{m.pri}</span>
                <span style={{ fontSize: 13, color: C.textPrimary }}>{m.title}</span>
              </div>
              <p style={{ margin: 0, fontSize: 11.5, color: C.textSecondary, lineHeight: 1.6 }}>{m.body}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main view                                                           */
/* ------------------------------------------------------------------ */

type Tab = 'tree' | 'integrity' | 'tables' | 'missing';

export function BuildTreeView() {
  const { data, error, loading, lastFetchedAt, refresh } = useBuildStatus();
  const [tab, setTab] = useState<Tab>('tree');

  const verdict = data?.readiness?.verdict ?? 'BLOCKED';
  const vs = VERDICT_STYLE[verdict] ?? VERDICT_STYLE.BLOCKED;
  const rtb = data?.rtb_session;

  const wiredIds = useMemo(() => new Set((data?.systems ?? []).map((s) => s.id)), [data]);
  const missingSystems = useMemo(() => EXPECTED_SYSTEMS.filter((id) => !wiredIds.has(id)), [wiredIds]);
  const activeDay = useMemo(() => (data ? currentDayType(data) : null), [data]);

  const tabBtn = (id: Tab): CSSProperties => ({
    padding: '9px 18px',
    borderRadius: '8px 8px 0 0',
    border: `1px solid ${tab === id ? C.borderTertiary : 'transparent'}`,
    borderBottom: 'none',
    background: tab === id ? C.bgSurface4 : 'transparent',
    color: tab === id ? C.textPrimary : C.textSecondary,
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 600,
    fontFamily: 'system-ui, sans-serif',
  });

  return (
    <div dir="rtl" style={{ minHeight: '100vh', background: C.bgBase, color: C.textPrimary }}>
      {/* header */}
      <div style={{ position: 'sticky', top: 0, zIndex: 30, display: 'flex', alignItems: 'center', gap: 14, padding: '11px 18px', background: C.bgSurface2, borderBottom: `1px solid ${C.borderTertiary}` }}>
        <Link href="/" style={{ fontFamily: MONO, fontWeight: 700, letterSpacing: '1px', color: '#5b9bff', fontSize: 14, textDecoration: 'none' }}>
          MEMS26
        </Link>
        <span style={{ color: C.textSecondary, fontSize: 12 }}>/ Build · עץ החלטות</span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '5px 14px', borderRadius: 8, fontWeight: 700, fontSize: 14, fontFamily: MONO, color: vs.fg, background: vs.bg }}>
          ● {verdict}
        </span>
        <div style={{ display: 'flex', gap: 16, color: C.textSecondary, fontSize: 11, fontFamily: MONO }}>
          {rtb && (
            <span>
              RTH{' '}
              {rtb.in_session ? (
                <b style={{ color: C.bull }}>פתוח · -{rtb.minutes_to_close}m</b>
              ) : (
                <b style={{ color: C.textTertiary }}>סגור · +{rtb.minutes_to_open}m</b>
              )}
            </span>
          )}
          {data && <span>build <b style={{ color: C.textPrimary }}>{data.build_version}</b></span>}
          {activeDay && <span>day <b style={{ color: '#5b9bff' }}>{activeDay}</b></span>}
        </div>
        <span style={{ flex: 1 }} />
        <span style={{ fontSize: 10, color: C.textTertiary, fontFamily: MONO }}>{lastFetchedAt ? `רענון אחרון ${lastFetchedAt.toLocaleTimeString()}` : '—'}</span>
        <button
          onClick={refresh}
          disabled={loading}
          style={{ padding: '6px 14px', borderRadius: 7, border: `1px solid ${C.borderTertiary}`, background: loading ? C.bgSurface4 : C.bgSurface5, color: loading ? C.textTertiary : C.textPrimary, fontFamily: MONO, fontSize: 11, fontWeight: 600, cursor: loading ? 'wait' : 'pointer' }}
        >
          {loading ? '⟳ טוען…' : '⟳ רענן'}
        </button>
      </div>

      <div style={{ maxWidth: 1320, margin: '0 auto', padding: '0 18px 48px' }}>
        <Legend />

        {error && (
          <div style={{ margin: '14px 0 0', padding: '10px 14px', borderRadius: 8, background: '#2e1414', color: C.bearLight, fontFamily: MONO, fontSize: 11, border: `1px solid ${C.bear}` }}>
            טעינה נכשלה · {error} · נסה רענון. (אם ה-endpoint /api/v9/build/pattern-status לא רץ — זה ייכשל עד שה-backend יעלה.)
          </div>
        )}

        {!data && !error && (
          <div style={{ padding: 40, textAlign: 'center', color: C.textTertiary, fontFamily: MONO, fontSize: 12 }}>{loading ? 'טוען build status…' : 'אין נתונים. לחץ רענן.'}</div>
        )}

        {data && (
          <>
            <Blocker readiness={data.readiness} />

            {/* tabs */}
            <div style={{ display: 'flex', gap: 6, marginTop: 20, borderBottom: `1px solid ${C.borderTertiary}` }}>
              <div style={tabBtn('tree')} onClick={() => setTab('tree')}>עץ החלטות</div>
              <div style={tabBtn('integrity')} onClick={() => setTab('integrity')}>שלמות מקור</div>
              <div style={tabBtn('tables')} onClick={() => setTab('tables')}>טבלאות אפיון</div>
              <div style={tabBtn('missing')} onClick={() => setTab('missing')}>
                מה חסר <span style={{ marginInlineStart: 6, fontSize: 10, padding: '1px 7px', borderRadius: 9, background: PEND_BG, color: PEND, fontFamily: MONO }}>{MISSING.length}</span>
              </div>
            </div>

            <div style={{ paddingTop: 18 }}>
              {tab === 'tree' && (
                <>
                  {data.errors && data.errors.length > 0 && (
                    <div style={{ padding: '6px 10px', marginBottom: 12, borderRadius: 6, background: '#2e2410', color: C.caution, border: `1px solid ${C.warning}`, fontFamily: MONO, fontSize: 10 }}>
                      warnings: {data.errors.join(' · ')}
                    </div>
                  )}

                  <GlobalFirewall data={data} />

                  <SourcesStrip systems={data.systems} />

                  <div style={{ marginTop: 20 }}>
                    <SLab>שכבה 1 · מערכות — לחץ לפתיחת הזרימה (מקור → קלט → פרשנות → שערים → פסיקה → TARGETS/STOP)</SLab>
                    {data.systems.map((sys, i) => (
                      <SystemBranch key={sys.id} sys={sys} defaultOpen={i === 0} activeDay={activeDay} />
                    ))}

                    {missingSystems.length > 0 && (
                      <div style={{ marginTop: 8, border: `1px dashed ${C.borderTertiary}`, borderRadius: 8, padding: '12px 14px', fontFamily: MONO, fontSize: 11, color: C.textTertiary }}>
                        לא מחובר ל-build status (דורש inspector ב-backend): {missingSystems.map((id) => sysMeta(id).label).join(' · ')}
                      </div>
                    )}
                  </div>

                  <ObserverCards wiredIds={wiredIds} data={data} />
                </>
              )}
              {tab === 'integrity' && <IntegrityTab data={data} />}
              {tab === 'tables' && <DayTypeTables activeDay={activeDay} />}
              {tab === 'missing' && <MissingTab />}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
