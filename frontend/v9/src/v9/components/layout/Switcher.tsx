'use client';
// Switcher — systems strip (UI round 2, 2026-07-02).
//
// The old firing row rendered three 36px pills whose visible content was in
// practice just the system number ("2 3 4"). Rebuilt as labeled rows that show
// each system's actual state (Michael's fix #4):
//   S2 Five-Min  — arming mode + last detected pattern + last-fire time
//   S3 Footprint — "מושתק" badge (muted by STANDING DECISION — CLAUDE.md
//                  §"S2 ⟂ S3" / S3_MUTE / I-11; do NOT re-enable without Michael)
//   S4 Woodies   — active pattern (armed) / last signal + last-fire time
//   S1 סיווג-יום — current day-type chip colored via lib/dayType (same canonical
//                  classify_replay value the TopBar badge shows — systems[1])
// each with a status dot (idle/armed/fired-recent/error — Pill dot convention).
//
// Data:
// - useSystemStateStore systems 1-4 — ALREADY polled by useSystemStatePolling
//   (5000ms floor, V9Dashboard.tsx) → zero new requests for state.
//   S2 raw = five_min_system.get_state() (five_min_system.py:1569-1581);
//   "armed" modes = FIRST_HOUR_TACTICAL / DAY_TYPE_MODE / LIVE_ONLY (the backend
//   itself calls DAY_TYPE_MODE "armed" — five_min_system.py:1032-1034).
//   S4 raw = woodies_system.current_state (active_patterns — woodies_system.py:917).
// - Last-fire time is NOT carried by any store (verified: get_state has no fire ts;
//   gateway route result has none; the signals WS only pushes {count}) → one
//   fetch of the EXISTING /api/v9/trades/recent (system = firing_system) at the
//   documented 30000ms history floor — the same endpoint + interval
//   TradeHistoryStrip already uses (CLAUDE.md Frontend Polling Floors).
// Selection/lens behavior and the trade-firing highlight are unchanged.
import { useEffect, useState } from 'react';
import { TPOPill } from '../systems/TPOPill';
import { KillzonePill } from '../systems/KillzonePill';
import { OpeningTypeChip } from '../systems/OpeningTypeChip';
import { SYSTEM_META } from '../../design/system_colors';
import { COLORS } from '../../design/tokens';
import { useSystemStateStore } from '../../store/systemStateStore';
import { useDirectionNow } from '../../hooks/useDirectionNow';
import { dayTypeColor } from '../../lib/dayType';
import { fetchRecentTrades } from '../../lib/api';
import { fmtTimeET } from '../../lib/tradeTime';
import type { Trade } from '../../types';

interface SwitcherProps {
  selectedSystem: number;
  onSelectSystem: (id: number) => void;
  /** System that opened the active trade (highlights row + entry) */
  tradeFiringSystemId?: number | null;
  tradeEntryPrice?: number | null;
}

// Same abbreviation families the old pills taught (FiveMinPill.tsx:13-21).
const S2_MODE_ABBREV: Record<string, string> = {
  FIRST_HOUR_TACTICAL: 'FH', DAY_TYPE_MODE: 'RTH', OVERNIGHT_MODE: 'ON',
  WEEKEND: 'WE', MAINTENANCE: 'MT', WAITING_OPEN: 'WAIT', LIVE_ONLY: 'LIVE',
};
const S2_PATTERN_ABBREV: Record<string, string> = {
  REACTIVE_LONG: 'R-L', REACTIVE_SHORT: 'R-S',
  INITIATIVE_LONG: 'I-L', INITIATIVE_SHORT: 'I-S',
};
// S2 modes in which the system evaluates patterns ("armed" per five_min_system.py:1032-1034).
const S2_ARMED_MODES = new Set(['FIRST_HOUR_TACTICAL', 'DAY_TYPE_MODE', 'LIVE_ONLY']);

// Pill dot convention (atoms/Pill.tsx DOT_COLORS).
const DOT = { idle: '#525252', armed: '#facc15', fired: '#16a34a', error: '#dc2626', muted: '#3a3a3a' } as const;
const FIRED_RECENT_MS = 30 * 60 * 1000; // fire within 30min → green dot

function dotColor(o: { muted?: boolean; error?: boolean; firedRecent?: boolean; armed?: boolean }): string {
  if (o.muted) return DOT.muted;
  if (o.error) return DOT.error;
  if (o.firedRecent) return DOT.fired;
  if (o.armed) return DOT.armed;
  return DOT.idle;
}

interface RowProps {
  systemId: number;
  nameHe: string;
  isSelected: boolean;
  onSelect: (id: number) => void;
  isTradeFiring: boolean;
  tradeEntryPrice?: number | null;
  dot: string;
  dotTitle: string;
  children: React.ReactNode;
  /** last fire: ET HH:MM + tooltip (from /trades/recent, 30s refresh) */
  fireLabel?: string | null;
  fireTitle?: string;
}

function SystemRow({
  systemId, nameHe, isSelected, onSelect, isTradeFiring, tradeEntryPrice,
  dot, dotTitle, children, fireLabel, fireTitle,
}: RowProps) {
  const meta = SYSTEM_META[systemId];
  if (!meta) return null;
  return (
    <button
      onClick={() => onSelect(systemId)}
      title={dotTitle}
      style={{
        display: 'flex', alignItems: 'center', gap: 5, width: '100%',
        minHeight: 24, padding: '2px 5px', borderRadius: 4, cursor: 'pointer',
        border: isSelected || isTradeFiring ? `1px solid ${meta.color}` : `1px solid ${COLORS.borderFaint}`,
        background: isSelected ? `${meta.color}1f` : isTradeFiring ? `${meta.color}14` : COLORS.bgSurface5,
        textAlign: 'left',
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: dot, flexShrink: 0 }} title={dotTitle} />
      <span style={{ fontSize: 8, fontWeight: 700, color: meta.color, fontFamily: 'ui-monospace', flexShrink: 0 }}>
        S{systemId}
      </span>
      <span style={{ fontSize: 8, color: isSelected ? COLORS.textPrimary : COLORS.textSecondary, flexShrink: 0, minWidth: 44 }}>
        {nameHe}
      </span>
      <span style={{ display: 'flex', alignItems: 'center', gap: 4, flex: 1, minWidth: 0, overflow: 'hidden' }}>
        {children}
        {isTradeFiring && tradeEntryPrice != null && (
          <span dir="ltr" style={{ fontSize: 7, fontFamily: 'ui-monospace', fontWeight: 700, color: meta.color }}>
            @{tradeEntryPrice.toFixed(2)}
          </span>
        )}
      </span>
      {fireLabel && (
        <span
          dir="ltr"
          title={fireTitle}
          style={{ fontSize: 8, fontFamily: 'ui-monospace', color: COLORS.textTertiary, flexShrink: 0 }}
        >
          ⚡{fireLabel}
        </span>
      )}
    </button>
  );
}

export function Switcher({
  selectedSystem,
  onSelectSystem,
  tradeFiringSystemId = null,
  tradeEntryPrice = null,
}: SwitcherProps) {
  const systems = useSystemStateStore((s) => s.systems);

  // Last routed fire per firing system — from the EXISTING /api/v9/trades/recent
  // (rows already entry_ts-desc — trades.py:375-381; system == firing_system via
  // mapTradeRow). 30000ms = the TradeHistoryStrip floor for this exact endpoint.
  const [lastFire, setLastFire] = useState<Record<number, Trade | undefined>>({});
  useEffect(() => {
    let alive = true;
    let inFlight = false;
    const load = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const rows = await fetchRecentTrades(20); // never throws — [] on failure
        if (!alive) return;
        const next: Record<number, Trade | undefined> = {};
        for (const t of rows) {
          const sys = t.system;
          if (sys != null && next[sys] === undefined) next[sys] = t; // first = newest
        }
        setLastFire(next);
      } finally {
        inFlight = false;
      }
    };
    load();
    const id = setInterval(load, 30000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  const nowMs = Date.now(); // re-evaluated on every store-driven render (≤5s stale)
  const fireInfo = (sysId: number) => {
    const t = lastFire[sysId];
    if (!t || !t.entry_ts) return { label: null as string | null, title: undefined as string | undefined, recent: false };
    const ts = new Date(t.entry_ts).getTime();
    return {
      label: fmtTimeET(t.entry_ts),
      title: `ירי אחרון S${sysId}: ${t.pattern_id ?? t.classification ?? t.trigger ?? '?'} ${t.direction ?? ''} · ${fmtTimeET(t.entry_ts)} ET (#${t.id} · ${t.mode})`,
      recent: Number.isFinite(ts) && nowMs - ts < FIRED_RECENT_MS,
    };
  };

  // ── S2 Five-Min (systems-snapshot raw = five_min_system.get_state()) ──
  const s2 = systems[2];
  const s2raw = (s2?.raw ?? {}) as { mode?: string | null; last_pattern?: string | null; running?: boolean; opening_type?: string | null };
  const s2mode = s2raw.mode ?? s2?.subState ?? null;
  const s2armed = !!s2raw.running && !!s2mode && S2_ARMED_MODES.has(s2mode);
  const s2fire = fireInfo(2);
  const s2patternRaw = s2raw.last_pattern ?? null;
  const s2pattern = s2patternRaw ? (S2_PATTERN_ABBREV[s2patternRaw] ?? s2patternRaw.slice(0, 6)) : null;

  // ── S3 Footprint — MUTED by standing decision (CLAUDE.md §"S2 ⟂ S3", 2026-06-08) ──
  const s3Title =
    'S3 Footprint מושתק בהחלטה קבועה (S3_MUTE / I-11, CLAUDE.md §S2⟂S3):\n' +
    'אישור COT/AMT לא נדרש ל-S2; טיפול ב-S3 נדחה לאחרי LIVE.\n' +
    'הפעלה מחדש = שינוי משטח-סיכון → אישור מפורש של מיכאל.';

  // ── S4 Woodies (systems-snapshot raw = woodies_system.current_state) ──
  const s4 = systems[4];
  const s4raw = (s4?.raw ?? {}) as {
    active_patterns?: Array<{ pattern_id?: string; direction?: string; confidence?: number }>;
    signal?: string | null;
  };
  const s4active = Array.isArray(s4raw.active_patterns) && s4raw.active_patterns.length > 0
    ? s4raw.active_patterns[0]
    : null;
  const s4fire = fireInfo(4);
  const s4state = s4?.state ?? null;
  // T12: setup direction (pattern) ≠ gate-allowed (direction_now). D1 will add blocked_by.
  const dirNow = useDirectionNow();
  const gateDir =
    dirNow?.dir === 'UP' ? 'LONG' : dirNow?.dir === 'DOWN' ? 'SHORT' : dirNow?.dir || null;
  const setupDir = (s4active?.direction || '').toUpperCase() || null;
  const setupVsGate =
    setupDir && gateDir && setupDir !== 'NEUTRAL' && gateDir !== 'NEUTRAL' && setupDir !== gateDir;

  // ── S1 Day-Type — same canonical classify_replay value as the TopBar badge
  //    (systemStateStore.overrideS1; systems-snapshot sys-1 is skipped) ──
  const s1 = systems[1];
  const s1type = s1?.state ?? null;
  const s1status = s1?.subState ?? null; // FORMING / PROVISIONAL / CLASSIFIED
  const s1color = dayTypeColor(s1type);
  const s1suffix = s1status === 'PROVISIONAL' ? '·prov' : s1status === 'FORMING' ? '·forming' : '';

  const rowCommon = (id: number) => ({
    isSelected: selectedSystem === id,
    onSelect: onSelectSystem,
    isTradeFiring: tradeFiringSystemId === id,
    tradeEntryPrice: tradeFiringSystemId === id ? tradeEntryPrice : null,
  });

  return (
    <div style={{ padding: '6px 8px', display: 'flex', flexDirection: 'column', gap: 6 }}>
      {/* Firing rows — S2/S3/S4 per Constitution V3 D-049 (T1/T3/T2) */}
      <div>
        <div style={{ fontSize: 7, color: COLORS.textDim, letterSpacing: '0.5px', marginBottom: 3, textTransform: 'uppercase' }}>
          Firing — החלטות כניסה
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* Opening Type chip — above S2 per Phase 5.2 spec */}
          <OpeningTypeChip />
          <SystemRow
            systemId={2} nameHe="Five-Min" {...rowCommon(2)}
            dot={dotColor({ error: s2?.health === 'error', firedRecent: s2fire.recent, armed: s2armed })}
            dotTitle={`S2 · חמוש כש-mode פעיל (FH/RTH/LIVE) · ${s2mode ?? '—'}${s2patternRaw ? ` · תבנית אחרונה: ${s2patternRaw}` : ''}`}
            fireLabel={s2fire.label} fireTitle={s2fire.title}
          >
            <span dir="ltr" style={{ fontSize: 8, fontFamily: 'ui-monospace', color: s2armed ? '#67e8f9' : COLORS.textTertiary }}
              title={`מצב S2: ${s2mode ?? 'לא ידוע'}`}>
              {s2mode ? (S2_MODE_ABBREV[s2mode] ?? s2mode.slice(0, 4)) : '—'}
            </span>
            {s2pattern && (
              <span dir="ltr" style={{ fontSize: 8, fontFamily: 'ui-monospace', fontWeight: 700, color: SYSTEM_META[2].color }}
                title={`תבנית אחרונה שזוהתה: ${s2patternRaw}`}>
                {s2pattern}
              </span>
            )}
          </SystemRow>

          <SystemRow
            systemId={3} nameHe="Footprint" {...rowCommon(3)}
            dot={dotColor({ muted: true })}
            dotTitle={s3Title}
          >
            <span
              title={s3Title}
              style={{
                fontSize: 8, fontWeight: 700, padding: '0 5px', borderRadius: 3,
                color: '#a85751', background: 'rgba(168,87,81,0.12)', border: '1px solid rgba(168,87,81,0.45)',
              }}
            >
              מושתק
            </span>
            <span style={{ fontSize: 7, color: COLORS.textDim }}>עד אחרי LIVE</span>
          </SystemRow>

          <SystemRow
            systemId={4} nameHe="Woodies" {...rowCommon(4)}
            dot={dotColor({ error: s4?.health === 'error', firedRecent: s4fire.recent, armed: !!s4active })}
            dotTitle={`S4 · חמוש כשיש תבנית פעילה בבר האחרון${s4active ? ` · ${s4active.pattern_id ?? ''} ${s4active.direction ?? ''}` : ' · אין תבנית כרגע'}`}
            fireLabel={s4fire.label} fireTitle={s4fire.title}
          >
            {s4active ? (
              <span dir="ltr" style={{ fontSize: 8, fontFamily: 'ui-monospace', fontWeight: 700, color: SYSTEM_META[4].color }}
                title={`setup=${setupDir ?? '?'} · allowed(gate)=${gateDir ?? '—'} · תבנית: ${s4active.pattern_id ?? '?'}${s4active.confidence != null ? ` · ${(s4active.confidence * 100).toFixed(0)}%` : ''}${setupVsGate ? ' · setup≠allowed' : ''}`}>
                {(s4active.pattern_id ?? '?').slice(0, 8)}
                <span style={{ opacity: 0.75 }}> setup{setupDir === 'LONG' ? '▲' : setupDir === 'SHORT' ? '▼' : ''}</span>
                {setupVsGate && (
                  <span style={{ color: '#d29922', marginInlineStart: 3 }}>≠{gateDir === 'LONG' ? '▲' : '▼'}</span>
                )}
              </span>
            ) : (
              <span dir="ltr" style={{ fontSize: 8, fontFamily: 'ui-monospace', color: COLORS.textTertiary }}
                title={`אין תבנית פעילה · gate=${gateDir ?? '—'}`}>
                {s4state ? s4state.slice(0, 10) : '—'}
              </span>
            )}
          </SystemRow>
        </div>
      </div>

      {/* Observing — S1/S5/S6 per Constitution V3 D-049 */}
      <div>
        <div style={{ fontSize: 7, color: COLORS.textDim, letterSpacing: '0.5px', marginBottom: 3, textTransform: 'uppercase' }}>
          Observing — הקשר
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* S1 dot: green = CLASSIFIED · yellow = FORMING/PROVISIONAL · gray = none */}
          <SystemRow
            systemId={1} nameHe="סיווג-יום" {...rowCommon(1)}
            dot={s1status === 'CLASSIFIED' ? DOT.fired
              : dotColor({ armed: s1status === 'PROVISIONAL' || s1status === 'FORMING' })}
            dotTitle={`S1 · המסווג הקנוני (classify_replay) · ${s1type ?? 'אין סיווג עדיין'}${s1status ? ` · ${s1status}` : ''}`}
          >
            <span
              dir="ltr"
              style={{
                fontSize: 8, fontWeight: 700, padding: '0 5px', borderRadius: 3,
                color: s1type ? s1color : COLORS.textTertiary,
                background: s1type ? `${s1color}1f` : 'transparent',
                border: `1px solid ${s1type ? `${s1color}66` : COLORS.borderTertiary}`,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 116,
              }}
              title={`סוג-יום נוכחי: ${s1type ?? '—'}${s1status ? ` (${s1status})` : ''}`}
            >
              {s1type ? `${s1type.replace(/_/g, ' ')}${s1suffix}` : 'DT —'}
            </span>
          </SystemRow>
          <div style={{ display: 'flex', gap: 6, minHeight: 28 }}>
            <TPOPill isSelected={selectedSystem === 5} onSelect={() => onSelectSystem(5)} />
            <KillzonePill isSelected={selectedSystem === 6} onSelect={() => onSelectSystem(6)} />
          </div>
        </div>
      </div>
    </div>
  );
}
