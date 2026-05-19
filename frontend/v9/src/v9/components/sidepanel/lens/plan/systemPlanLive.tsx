'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { useSystemStateStore, type HealthStatus, type SystemState } from '../../../../store/systemStateStore';
import { COLORS } from '../../../../design/tokens';
import { SYSTEM_META, type SystemMeta } from '../../../../design/system_colors';
import {
  LIFECYCLE_HELP,
  SECTION_HELP,
  STATUS_HELP,
  rowHelpForWoodiesStage,
  woodiesStageId,
  PLAN_RTL_STYLE,
  type FireRowStatus,
  type PlanLifecycle,
} from './planHelp';
import {
  diagnoseFiringSystem,
  diagnoseWoodies,
  lifecycleFromDiagnosis,
  type FireDiagnosis,
  type GatewaySnap,
} from './planFireDiagnosis';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export type { FireRowStatus, PlanLifecycle };

export interface FireRow {
  id: string;
  status: FireRowStatus;
  label: string;
  value?: string;
  help: string;
}

const LIFECYCLE_STYLES: Record<
  PlanLifecycle,
  { bg: string; border: string; color: string; pulse?: boolean }
> = {
  SCANNING: { bg: '#412402', border: '#EF9F27', color: '#EF9F27' },
  APPROACHING: { bg: '#1B0E2D', border: '#a855f7', color: '#c4b5fd' },
  BLOCKED: { bg: '#3D0E0E', border: '#DC2626', color: '#DC2626' },
  READY: { bg: '#14532d', border: '#16a34a', color: '#86efac' },
  FIRING: { bg: '#1a1a1a', border: '#06b6d4', color: '#67e8f9', pulse: true },
};

const ROW_COLOR: Record<FireRowStatus, string> = {
  ok: COLORS.bull,
  wait: COLORS.warning,
  block: COLORS.bear,
};

const DOT: Record<FireRowStatus, string> = {
  ok: '✓',
  wait: '⚠',
  block: '●',
};

const COMPACT = {
  pad: 6,
  gap: 5,
  label: 7,
  body: 8,
  title: 9,
  badgePad: '3px 8px',
  badgeFont: 9,
  barH: 3,
  rowFont: 8,
};

function ageSec(lastUpdate: number): number {
  if (!lastUpdate) return -1;
  return Math.max(0, Math.round((Date.now() - lastUpdate) / 1000));
}

function healthLabel(h: HealthStatus): string {
  if (h === 'healthy') return 'Feeds OK';
  if (h === 'warn') return 'Degraded';
  if (h === 'error') return 'Stale/error';
  return 'Unknown';
}

function mapStageStatus(status: unknown): FireRowStatus {
  const s = String(status ?? '').toUpperCase();
  if (s === 'PASS' || s === 'DELEGATED') return 'ok';
  if (s === 'FAIL') return 'block';
  return 'wait';
}

function woodiesPreFireRows(raw: Record<string, unknown>): FireRow[] {
  const dt = (raw.decision_tree ?? {}) as Record<string, unknown>;
  const pre = dt.pre_fire;
  if (!Array.isArray(pre) || pre.length === 0) {
    return [
      {
        id: 'dt-wait',
        status: 'wait',
        label: 'Decision tree',
        value: 'awaiting bar',
        help: 'מחכה לבר woodies_5min הבא מגשר Sierra. בלי בר — אין evaluate_bar.',
      },
      {
        id: 'cci-buf',
        status: 'wait',
        label: 'CCI buffer',
        value: `${raw.buffer_size ?? 0}/14`,
        help: 'כמה ברים עם CCI14 טעונים ב-buffer. מינימום ~14 לחישוב יציב.',
      },
    ];
  }
  return pre.slice(0, 8).map((row: Record<string, unknown>, i: number) => {
    const sid = String(row.stage_id ?? '?');
    const msg = String(row.message ?? '').trim();
    const status = mapStageStatus(row.status);
    const label = msg ? `${sid} ${msg}`.slice(0, 52) : sid;
    return {
      id: `stage-${sid}-${i}`,
      status,
      label,
      value: String(row.status ?? ''),
      help: rowHelpForWoodiesStage(sid, status, msg),
    };
  });
}

function deriveFiringLifecycle(
  meta: SystemMeta,
  raw: Record<string, unknown>,
  health: HealthStatus,
  topState: string | null,
): PlanLifecycle {
  if (health === 'error') return 'BLOCKED';

  if (meta.id === 4) {
    if (raw.ready_to_route === true) return 'READY';
    const failed = raw.failed_stages as string[] | undefined;
    const dt = (raw.decision_tree ?? {}) as Record<string, unknown>;
    const failedDt = dt.failed_stages as string[] | undefined;
    if ((failed?.length ?? 0) > 0 || (failedDt?.length ?? 0) > 0) return 'BLOCKED';
    const patterns = raw.active_patterns;
    if (Array.isArray(patterns) && patterns.length > 0) return 'APPROACHING';
    if (raw.classification && raw.classification !== 'NO_SETUP') return 'APPROACHING';
    if (topState && topState !== 'NEUTRAL' && topState !== 'NO_SETUP') return 'APPROACHING';
    return 'SCANNING';
  }

  if (meta.id === 2) {
    const mode = String(raw.mode ?? '');
    if (raw.last_pattern) return 'READY';
    if (mode === 'FIRST_HOUR_TACTICAL' || mode === 'DAY_TYPE_MODE') return 'APPROACHING';
    if (mode === 'MAINTENANCE' || mode === 'WEEKEND') return 'BLOCKED';
    return 'SCANNING';
  }

  if (meta.id === 3) {
    const cls = String(raw.last_classification ?? raw.combined_class ?? 'NO_SETUP');
    const lastFire = raw.last_fire as Record<string, unknown> | undefined;
    if (lastFire?.blocked_by) return 'BLOCKED';
    if (cls !== 'NO_SETUP') return 'APPROACHING';
    return 'SCANNING';
  }

  return 'SCANNING';
}

function deriveObserverLifecycle(
  meta: SystemMeta,
  raw: Record<string, unknown>,
  health: HealthStatus,
  topState: string | null,
): PlanLifecycle {
  if (health === 'error') return 'BLOCKED';

  if (meta.id === 1) {
    const dt = raw.day_type ?? topState;
    if (dt && dt !== 'UNKNOWN' && dt !== 'SEARCHING') return 'READY';
    const prob = Number(raw.probability ?? 0);
    if (prob > 0.3) return 'APPROACHING';
    return 'SCANNING';
  }

  if (meta.id === 5) {
    if (raw.ib_locked) return 'READY';
    const letters = Number(raw.letter_count ?? 0);
    if (letters >= 4) return 'APPROACHING';
    return 'SCANNING';
  }

  if (meta.id === 6) {
    const gate = raw.gate_open ?? raw.is_open;
    if (gate === true) return 'READY';
    if (topState && topState !== 'UNKNOWN') return 'APPROACHING';
    return 'SCANNING';
  }

  return topState ? 'APPROACHING' : 'SCANNING';
}

function row(
  id: string,
  status: FireRowStatus,
  label: string,
  value: string | undefined,
  help: string,
): FireRow {
  return { id, status, label, value, help };
}

function buildPlan(
  meta: SystemMeta,
  sys: SystemState,
): {
  lifecycle: PlanLifecycle;
  building: string;
  buildingHelp: string;
  progress: number;
  fireRows: FireRow[];
  stateDetail: string;
} {
  const raw = (sys.raw ?? {}) as Record<string, unknown>;
  const lifecycle =
    meta.type === 'FIRING'
      ? deriveFiringLifecycle(meta, raw, sys.health, sys.state)
      : deriveObserverLifecycle(meta, raw, sys.health, sys.state);

  let building = '—';
  let buildingHelp = SECTION_HELP.building.meaning;
  let progress = 0;
  let fireRows: FireRow[] = [];
  let stateDetail = '';

  if (meta.id === 4) {
    const patterns = raw.active_patterns as Array<Record<string, unknown>> | undefined;
    const top = patterns?.[0];
    building = top
      ? `${top.pattern_id ?? 'pattern'} ${top.direction ?? ''}`.trim()
      : String(raw.classification ?? raw.signal ?? 'No pattern');
    buildingHelp = top
      ? `תבנית פעילה: ${top.pattern_id}, כיוון ${top.direction}, conf ${top.confidence ?? '—'}.`
      : 'אין active_patterns — ממתין לזיהוי CCI.';
    const buf = Number(raw.buffer_size ?? 0);
    progress = Math.min(100, Math.round((buf / 14) * 100));
    fireRows = woodiesPreFireRows(raw);
    const failed = ((raw.decision_tree as Record<string, unknown>)?.failed_stages ??
      raw.failed_stages) as string[] | undefined;
    stateDetail = failed?.length
      ? `חסום: שלבים ${failed.join(', ')}`
      : raw.ready_to_route
        ? 'כל pre-fire עבר — ready_to_route'
        : `classification=${raw.classification}, signal=${raw.signal}`;
    if (raw.ready_to_route === true) {
      fireRows = [
        row('pre-pass', 'ok', 'Pre-fire summary', 'PASS', 'כל שלבי A ללא FAIL/PENDING.'),
        ...fireRows.slice(0, 6),
      ];
    }
  } else if (meta.id === 2) {
    building = raw.last_pattern
      ? String(raw.last_pattern)
      : `Mode: ${raw.mode ?? sys.subState ?? '—'}`;
    const buf = Number(raw.buffer_size ?? 0);
    progress = raw.last_pattern ? 100 : Math.min(100, Math.round((buf / 4) * 100));
    buildingHelp = '4-bar Reactive/Initiative — buffer סופי לפני FIRE.';
    stateDetail = `mode=${raw.mode}, opening=${raw.opening_type ?? '—'}`;
    fireRows = [
      row('fm-mode', raw.mode ? 'ok' : 'wait', 'Session mode', String(raw.mode ?? '—'),
        'מוד SessionClassifier: FIRST_HOUR_TACTICAL, DAY_TYPE_MODE, … — לא שעון גולמי.'),
      row('fm-buf', buf >= 4 ? 'ok' : 'wait', 'Bar buffer', `${buf}/4`,
        'מינימום 4 ברים ל-5m לפני דפוס Reactive/Initiative.'),
      row('fm-open', raw.opening_type ? 'ok' : 'wait', 'Opening type', String(raw.opening_type ?? 'pending'),
        'סוג פתיחה מהיום — משפיע על sizing והקשר.'),
      row('fm-pat', raw.last_pattern ? 'ok' : 'wait', 'Pattern', String(raw.last_pattern ?? 'none'),
        'דפוס אחרון שזוהה; READY כשיש last_pattern.'),
    ];
    const notes = raw.last_reasoning_notes as string | undefined;
    if (notes) {
      fireRows.push(row('fm-notes', 'ok', 'Reasoning', notes.slice(0, 32), notes));
    }
  } else if (meta.id === 3) {
    building = String(
      raw.combined_class ?? raw.last_classification ?? raw.dominance ?? 'Watching flow',
    );
    const conf = Number(raw.last_confluence ?? 0);
    progress = conf > 0 ? Math.min(100, conf * 10) : 15;
    buildingHelp = 'מצב footprint + tick reversal משולב.';
    fireRows = [
      row('fp-dom', raw.dominance ? 'ok' : 'wait', 'Dominance', String(raw.dominance ?? '—'),
        'מי שולט בזרימה (buy/sell/balanced) מהדלתא המצטברת.'),
      row('fp-cot', raw.cot != null && raw.amt != null ? 'ok' : 'wait', 'COT vs AMT',
        `${raw.cot ?? '—'} / ${raw.amt ?? '—'}`,
        'COT = מצטבר דלתא; AMT = ממוצע 90 דק — S2 משתמש להשוואה.'),
      row('fp-cls', raw.combined_class && raw.combined_class !== 'NO_SETUP' ? 'ok' : 'wait',
        'Combined class', String(raw.combined_class ?? 'NO_SETUP'),
        'סיווג סופי T3 לפני pre_fire_validator.'),
    ];
    const lastFire = raw.last_fire as Record<string, unknown> | undefined;
    if (lastFire?.blocked_by) {
      fireRows.push(row('fp-block', 'block', 'Last fire blocked',
        String(lastFire.route_reason ?? lastFire.blocked_by),
        'ניסיון ירי אחרון נחסם — לא אישור ידני.'));
    }
  } else if (meta.id === 1) {
    building = `Day type: ${raw.day_type ?? sys.state ?? '…'}`;
    const prob = Number(raw.probability ?? sys.confidence ?? 0);
    progress = Math.min(100, Math.round(prob * 100));
    buildingHelp = 'סיווג יום — ננעל אחרי IB+5דק; לא יורה עסקאות.';
    fireRows = [
      row('dt-conf', prob >= 0.6 ? 'ok' : 'wait', 'Probability', `${Math.round(prob * 100)}%`,
        'הסתברות לסוג היום הנוכחי מהמכונה.'),
      row('dt-tc', raw.trading_confidence ? 'ok' : 'wait', 'Trading conf.',
        String(raw.trading_confidence ?? '—'), 'ביטחון מסחר לשימוש S2/S3/S4.'),
      row('dt-role', 'ok', 'Role', 'Advisory', 'שכבת הקשר בלבד — Layer 0 קורא.'),
    ];
  } else if (meta.id === 5) {
    building = raw.ib_locked
      ? `IB ${raw.ib_class ?? '—'} ${raw.ib_width ?? '—'}pt`
      : `Letters ${raw.letter_count ?? 0}`;
    progress = raw.ib_locked
      ? 100
      : Math.min(100, Math.round((Number(raw.letter_count ?? 0) / 13) * 100));
    buildingHelp = 'פרופיל TPO + IB — observer ל-Day Type ולמערכות יורות.';
    fireRows = [
      row('tpo-ib', raw.ib_locked ? 'ok' : 'wait', 'IB lock',
        raw.ib_locked ? 'LOCKED' : 'open',
        'IB ננעל 10:30 ET — רוחב וסיווג NARROW/MEDIUM/WIDE.'),
      row('tpo-poc', raw.poc != null ? 'ok' : 'wait', 'POC',
        raw.poc != null ? String(Number(raw.poc).toFixed(2)) : '—', 'מחיר עם הכי הרבה TPO.'),
      row('tpo-mig', raw.poc_migration ? 'ok' : 'wait', 'POC migration',
        String((raw.poc_migration as Record<string, unknown>)?.direction ?? '—'),
        'כיוון תזוזת POC — UP/DOWN/STUCK.'),
    ];
  } else if (meta.id === 6) {
    const zone = (raw.current_zone ?? {}) as Record<string, unknown>;
    building = String(zone.name ?? sys.state ?? 'Session');
    const mins = Number(zone.minutes_remaining ?? 0);
    progress = mins > 0 ? Math.min(100, Math.round((mins / 60) * 100)) : 50;
    buildingHelp = 'שלבי זמן מסחר — gate לירי במערכות FIRING.';
    const gateOpen = raw.gate_open ?? raw.is_open;
    fireRows = [
      row('kz-gate', gateOpen === true ? 'ok' : gateOpen === false ? 'block' : 'wait', 'Gate',
        gateOpen === true ? 'OPEN' : gateOpen === false ? 'CLOSED' : '—',
        'OPEN רק ב-Cash Hours — חוסם fire אם CLOSED.'),
      row('kz-edge', zone.edge_class ? 'ok' : 'wait', 'Edge', String(zone.edge_class ?? '—'),
        'עוצמת קצה זמן (high/medium/low).'),
      row('kz-zone', zone.name ? 'ok' : 'wait', 'Zone', String(zone.name ?? '—'),
        'שם אזור נוכחי (First Hour, Cash Hours, …).'),
    ];
  }

  return { lifecycle, building, buildingHelp, progress, fireRows, stateDetail };
}

function SectionLabel({ children, hint }: { children: ReactNode; hint?: string }) {
  return (
    <div style={{ marginBottom: 2 }}>
      <div
        style={{
          fontSize: COMPACT.label,
          fontWeight: 700,
          color: COLORS.textTertiary,
          letterSpacing: 0.4,
          textTransform: 'uppercase',
        }}
      >
        {children}
      </div>
      {hint && (
        <div style={{ fontSize: 6, color: COLORS.textDim, marginTop: 1, ...PLAN_RTL_STYLE }}>{hint}</div>
      )}
    </div>
  );
}

function PlanDetail({
  title,
  statusLine,
  body,
  onClose,
}: {
  title: string;
  statusLine?: string;
  body: string;
  onClose: () => void;
}) {
  return (
    <div
      dir="rtl"
      lang="he"
      style={{
        marginTop: COMPACT.gap,
        padding: 5,
        borderRadius: 4,
        background: COLORS.bgSurface5,
        border: `1px solid ${COLORS.borderSecondary}`,
        fontSize: COMPACT.body,
        lineHeight: 1.45,
        color: COLORS.textSecondary,
        ...PLAN_RTL_STYLE,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 4, marginBottom: 3 }}>
        <span
          dir="ltr"
          style={{
            fontWeight: 700,
            color: COLORS.textPrimary,
            fontSize: COMPACT.title,
            textAlign: 'left',
          }}
        >
          {title}
        </span>
        <button
          type="button"
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: COLORS.textTertiary,
            cursor: 'pointer',
            fontSize: 10,
            padding: 0,
            lineHeight: 1,
          }}
          aria-label="סגור"
        >
          ×
        </button>
      </div>
      {statusLine && (
        <div style={{ color: COLORS.warning, fontSize: 7, marginBottom: 3, ...PLAN_RTL_STYLE }}>
          {statusLine}
        </div>
      )}
      <div style={{ whiteSpace: 'pre-wrap', ...PLAN_RTL_STYLE }}>{body}</div>
    </div>
  );
}

function FireDiagnosisPanel({
  diagnosis,
  onSelect,
  selected,
}: {
  diagnosis: FireDiagnosis;
  onSelect: () => void;
  selected: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      style={{
        width: '100%',
        marginBottom: COMPACT.gap,
        padding: 6,
        borderRadius: 4,
        border: selected ? `1px solid ${COLORS.borderPrimary}` : `1px solid ${COLORS.borderTertiary}`,
        background: COLORS.bgSurface5,
        cursor: 'pointer',
        ...PLAN_RTL_STYLE,
      }}
    >
      <div style={{ fontSize: 8, fontWeight: 700, color: COLORS.warning, marginBottom: 4 }}>
        סטאפ וירי — לחץ לפירוט
      </div>
      <div style={{ fontSize: 9, color: COLORS.textPrimary, fontWeight: 600, marginBottom: 3 }}>
        {diagnosis.setupLine}
      </div>
      <div style={{ fontSize: 8, color: COLORS.textTertiary, marginBottom: 4, whiteSpace: 'pre-wrap' }}>
        {diagnosis.treeLine}
      </div>
      {diagnosis.whyNotFire.length > 0 && (
        <div style={{ fontSize: 8, color: COLORS.bear, marginBottom: 2 }}>
          <span style={{ fontWeight: 700 }}>למה לא ירה: </span>
          {diagnosis.whyNotFire[0]}
        </div>
      )}
      {diagnosis.whyNotFire.length === 0 && diagnosis.situation === 'ROUTED_SHADOW' && (
        <div style={{ fontSize: 8, color: COLORS.bull }}>
          נרשם ב-SHADOW — אין הוראת ברוקר
        </div>
      )}
      {diagnosis.wouldFireWhen[0] && (
        <div style={{ fontSize: 7, color: COLORS.textDim, marginTop: 2 }}>
          יירה כש: {diagnosis.wouldFireWhen[0]}
        </div>
      )}
    </button>
  );
}

function ClickableRow({
  row: r,
  selected,
  onSelect,
}: {
  row: FireRow;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 4,
        width: '100%',
        padding: '2px 3px',
        margin: 0,
        border: selected ? `1px solid ${COLORS.borderPrimary}` : '1px solid transparent',
        borderRadius: 3,
        background: selected ? COLORS.bgSurface5 : 'transparent',
        cursor: 'pointer',
        fontSize: COMPACT.rowFont,
        color: ROW_COLOR[r.status],
        textAlign: 'left',
      }}
    >
      <span style={{ width: 10, flexShrink: 0 }}>{DOT[r.status]}</span>
      <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.label}</span>
      {r.value != null && (
        <span
          style={{
            color: COLORS.textTertiary,
            flexShrink: 0,
            maxWidth: '38%',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {r.value}
        </span>
      )}
    </button>
  );
}

/** Live Plan tab (§5.8) — compact + tap for what each row measures. */
export function SystemPlanLive({
  systemId,
  spec,
}: {
  systemId: number;
  spec?: ReactNode;
}) {
  const sys = useSystemStateStore((s) => s.systems[systemId]);
  const kzRaw = useSystemStateStore((s) => s.systems[6]?.raw) as Record<string, unknown> | undefined;
  const meta = SYSTEM_META[systemId];
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [gateway, setGateway] = useState<GatewaySnap | null>(null);

  useEffect(() => {
    if (!meta || meta.type !== 'FIRING') return;
    const load = () => {
      fetch(`${API}/api/v9/gateway/status`)
        .then((r) => (r.ok ? r.json() : null))
        .then((d) => setGateway(d))
        .catch(() => setGateway(null));
    };
    load();
    const id = setInterval(load, 3000);
    return () => clearInterval(id);
  }, [meta?.type, systemId]);

  if (!sys || !meta) return null;

  const raw = (sys.raw ?? {}) as Record<string, unknown>;
  const killzoneOpen =
    kzRaw?.gate_open === true || kzRaw?.is_open === true
      ? true
      : kzRaw?.gate_open === false || kzRaw?.is_open === false
        ? false
        : null;

  const diagnosis: FireDiagnosis | null =
    meta.type === 'FIRING'
      ? meta.id === 4
        ? diagnoseWoodies(raw, gateway, killzoneOpen)
        : diagnoseFiringSystem(meta.id, raw, gateway)
      : null;

  const { lifecycle: planLifecycle, building, buildingHelp, progress, fireRows, stateDetail } =
    buildPlan(meta, sys);
  const lifecycle =
    diagnosis != null ? lifecycleFromDiagnosis(diagnosis, sys.health) : planLifecycle;
  const accent = meta.color;
  const stateLabel = diagnosis?.badgeLabel ?? planLifecycle;
  const age = ageSec(sys.lastUpdate);
  const healthDot =
    sys.health === 'healthy' ? COLORS.bull : sys.health === 'error' ? COLORS.bear : COLORS.warning;
  const sectionTitle = meta.type === 'FIRING' ? 'TO FIRE' : 'CONTEXT';

  const toggle = (id: string) => setSelectedId((prev) => (prev === id ? null : id));

  let detailTitle = '';
  let detailStatus = '';
  let detailBody = '';

  if (selectedId === 'diagnosis' && diagnosis) {
    detailTitle = 'סטאפ וירי';
    detailBody = [
      diagnosis.identifiedLine,
      '',
      diagnosis.treeLine,
      '',
      diagnosis.whyNotFire.length
        ? `למה לא ירה:\n${diagnosis.whyNotFire.map((w) => `• ${w}`).join('\n')}`
        : 'לא חסום כרגע — בדוק אם נרשם SHADOW.',
      '',
      diagnosis.wouldFireWhen.length
        ? `מתי יירה:\n${diagnosis.wouldFireWhen.map((w) => `• ${w}`).join('\n')}`
        : '',
      raw.last_route
        ? `\nlast_route: ${JSON.stringify(raw.last_route).slice(0, 200)}`
        : '',
    ].join('\n');
  } else if (selectedId === 'state') {
    const h = LIFECYCLE_HELP[lifecycle];
    detailTitle = diagnosis?.badgeLabel ?? h.title;
    detailStatus = STATUS_HELP[
      lifecycle === 'BLOCKED' ? 'block' : lifecycle === 'READY' ? 'ok' : 'wait'
    ];
    detailBody = diagnosis
      ? [
          diagnosis.setupLine,
          diagnosis.treeLine,
          '',
          diagnosis.whyNotFire.length
            ? `למה לא ירה:\n${diagnosis.whyNotFire.join('\n')}`
            : 'העץ מאשר — ייתכן שנרשם SHADOW.',
          '',
          h.meaning,
        ].join('\n')
      : `${h.measures}\n\n${h.meaning}${stateDetail ? `\n\nעכשיו: ${stateDetail}` : ''}`;
  } else if (selectedId === 'building') {
    detailTitle = 'BUILDING';
    detailBody = `${SECTION_HELP.building.measures}\n\n${buildingHelp}\n\nהתקדמות: ${progress}%`;
  } else if (selectedId === 'health') {
    detailTitle = 'DATA HEALTH';
    detailBody = `${SECTION_HELP.health.measures}\n\n${SECTION_HELP.health.meaning}\n\nhealth=${sys.health}, poll ${age >= 0 ? `${age}s` : 'never'}`;
  } else {
    const fr = fireRows.find((r) => r.id === selectedId);
    if (fr) {
      detailTitle = fr.label;
      detailStatus = STATUS_HELP[fr.status];
      detailBody = fr.help;
      const sid = woodiesStageId(fr.label);
      if (sid && meta.id === 4) {
        detailTitle = `Woodies ${sid}`;
      }
    }
  }

  const style = LIFECYCLE_STYLES[lifecycle];
  const borderColor = lifecycle === 'APPROACHING' ? accent : style.border;

  return (
    <div
      style={{
        padding: COMPACT.pad,
        fontSize: COMPACT.body,
        color: COLORS.textSecondary,
        lineHeight: 1.35,
        border:
          lifecycle === 'BLOCKED' ? `1px solid ${COLORS.bear}` : `1px solid ${COLORS.borderTertiary}`,
        borderRadius: 4,
        margin: 2,
      }}
    >
      <div
        style={{
          fontWeight: 700,
          color: COLORS.textPrimary,
          marginBottom: COMPACT.gap,
          fontSize: COMPACT.title,
        }}
      >
        S{meta.id} {meta.name}
        <span style={{ fontWeight: 400, color: COLORS.textDim, marginLeft: 4, fontSize: 7 }}>
          {meta.type === 'FIRING' ? 'FIR' : 'OBS'}
        </span>
      </div>

      {diagnosis && (
        <FireDiagnosisPanel
          diagnosis={diagnosis}
          selected={selectedId === 'diagnosis'}
          onSelect={() => toggle('diagnosis')}
        />
      )}

      <div style={{ marginBottom: COMPACT.gap }}>
        <SectionLabel hint="לחץ badge">STATE</SectionLabel>
        <button
          type="button"
          onClick={() => toggle('state')}
          style={{
            display: 'inline-block',
            padding: COMPACT.badgePad,
            borderRadius: 4,
            fontSize: COMPACT.badgeFont,
            fontWeight: 800,
            letterSpacing: 0.4,
            background: style.bg,
            border: `1px solid ${selectedId === 'state' ? COLORS.textPrimary : borderColor}`,
            color: lifecycle === 'APPROACHING' ? accent : style.color,
            cursor: 'pointer',
          }}
        >
          {stateLabel}
        </button>
        {(sys.state || sys.subState) && (
          <div
            style={{ marginTop: 3, fontSize: 7, color: COLORS.textTertiary, lineHeight: 1.3 }}
          >
            {sys.state}
            {sys.subState ? ` · ${sys.subState}` : ''}
            {sys.confidence > 0 ? ` · ${Math.round(sys.confidence * 100)}%` : ''}
          </div>
        )}
      </div>

      <div style={{ marginBottom: COMPACT.gap }}>
        <SectionLabel hint="לחץ שורה">BUILDING</SectionLabel>
        <button
          type="button"
          onClick={() => toggle('building')}
          style={{
            width: '100%',
            padding: 0,
            margin: 0,
            border: 'none',
            background: 'transparent',
            cursor: 'pointer',
            textAlign: 'left',
          }}
        >
          <div style={{ color: COLORS.textPrimary, fontWeight: 600, fontSize: COMPACT.title }}>{building}</div>
          <div
            style={{
              marginTop: 3,
              height: COMPACT.barH,
              borderRadius: 2,
              background: COLORS.bgSurface5,
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'row-reverse',
            }}
          >
            <div style={{ width: `${progress}%`, height: '100%', background: accent }} />
          </div>
        </button>
      </div>

      <div style={{ marginBottom: COMPACT.gap }}>
        <SectionLabel hint="לחץ שורה">{sectionTitle}</SectionLabel>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 1, maxHeight: 88, overflowY: 'auto' }}>
          {fireRows.map((r) => (
            <ClickableRow
              key={r.id}
              row={r}
              selected={selectedId === r.id}
              onSelect={() => toggle(r.id)}
            />
          ))}
        </div>
      </div>

      <button
        type="button"
        onClick={() => toggle('health')}
        style={{
          width: '100%',
          padding: '3px 0 0',
          margin: 0,
          border: 'none',
          borderTop: `1px solid ${COLORS.borderFaint}`,
          background: 'transparent',
          cursor: 'pointer',
          fontSize: 7,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          color: COLORS.textTertiary,
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          <span
            style={{
              width: 5,
              height: 5,
              borderRadius: '50%',
              background: healthDot,
              display: 'inline-block',
            }}
          />
          {healthLabel(sys.health)}
        </span>
        <span style={{ color: COLORS.textDim }}>{age >= 0 ? `${age}s` : '—'}</span>
      </button>

      {selectedId && detailBody && (
        <PlanDetail
          title={detailTitle}
          statusLine={detailStatus}
          body={detailBody}
          onClose={() => setSelectedId(null)}
        />
      )}

      {spec != null && (
        <details style={{ marginTop: 4 }}>
          <summary style={{ cursor: 'pointer', fontSize: 7, color: COLORS.textDim }}>Spec</summary>
          <div style={{ marginTop: 4, fontSize: 8 }}>{spec}</div>
        </details>
      )}
    </div>
  );
}
