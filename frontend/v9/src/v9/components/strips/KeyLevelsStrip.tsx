'use client';
import { COLORS } from '../../design/tokens';
import { useKeyLevels } from '../../hooks/useKeyLevels';
import { useLiveDayType } from '../../hooks/useLiveDayType';

function px(v: number | null | undefined, dec = 2): string {
  return v != null ? v.toFixed(dec) : '—';
}

function Sep() {
  return (
    <span style={{ color: COLORS.borderStrong, fontSize: 9, userSelect: 'none' }}>│</span>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <span style={{
      fontSize: 8,
      color: COLORS.textTertiary,
      fontWeight: 600,
      letterSpacing: '0.04em',
      textTransform: 'uppercase',
    }}>
      {children}
    </span>
  );
}

function Val({
  v,
  color = COLORS.textSecondary,
  bold = false,
}: {
  v: string;
  color?: string;
  bold?: boolean;
}) {
  return (
    <span style={{
      fontSize: 10,
      color,
      fontWeight: bold ? 700 : 500,
      fontFamily: 'ui-monospace, monospace',
    }}>
      {v}
    </span>
  );
}

function PocBlock({
  label,
  poc,
  vah,
  val,
  color,
}: {
  label: string;
  poc: number | null;
  vah: number | null;
  val: number | null;
  color: string;
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
      <Label>{label}</Label>
      <Val v={`POC ${px(poc)}`} color={color} bold />
      <span style={{ color: COLORS.textDisabled, fontSize: 9 }}>/</span>
      <Val v={`VAH ${px(vah)}`} color={color} />
      <span style={{ color: COLORS.textDisabled, fontSize: 9 }}>/</span>
      <Val v={`VAL ${px(val)}`} color={color} />
    </div>
  );
}

function RangeBlock({
  label,
  high,
  low,
  range,
  hColor,
  lColor,
  rColor,
  emptyText,
}: {
  label: string;
  high: number | null;
  low: number | null;
  range: number | null;
  hColor: string;
  lColor: string;
  rColor: string;
  emptyText?: string;
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
      <Label>{label}</Label>
      {high == null && low == null ? (
        <Val v={emptyText ?? '—'} color={COLORS.textDisabled} />
      ) : (
        <>
          <Val v={`H ${px(high)}`} color={hColor} />
          <span style={{ color: COLORS.textDisabled, fontSize: 9 }}>/</span>
          <Val v={`L ${px(low)}`} color={lColor} />
          {range != null && (
            <>
              <span style={{ color: COLORS.textDisabled, fontSize: 9 }}>(</span>
              <Val v={`${px(range)}pt`} color={rColor} />
              <span style={{ color: COLORS.textDisabled, fontSize: 9 }}>)</span>
            </>
          )}
        </>
      )}
    </div>
  );
}

function IbBlock({
  label,
  high,
  low,
  width,
  klass,
  emptyText,
  primary,
}: {
  label: string;
  high: number | null;
  low: number | null;
  width: number | null;
  klass: string | null;
  emptyText: string;
  primary: boolean;
}) {
  const klassColor = (() => {
    if (klass === 'NARROW') return COLORS.bull;
    if (klass === 'MEDIUM') return '#f59e0b';
    if (klass === 'WIDE') return COLORS.bear;
    return COLORS.textTertiary;
  })();
  const ibColor = primary ? '#f59e0b' : '#d97706';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
      <Label>{label}</Label>
      {high == null && low == null ? (
        <Val v={emptyText} color={COLORS.textDisabled} />
      ) : (
        <>
          <Val v={`H ${px(high)}`} color={ibColor} bold={primary} />
          <span style={{ color: COLORS.textDisabled, fontSize: 9 }}>/</span>
          <Val v={`L ${px(low)}`} color={ibColor} />
          {width != null && (
            <span style={{
              fontSize: 8,
              fontWeight: 700,
              padding: '1px 4px',
              borderRadius: 2,
              background: `${klassColor}22`,
              color: klassColor,
              marginLeft: 2,
            }}>
              {px(width)}pt {klass ?? ''}
            </span>
          )}
        </>
      )}
    </div>
  );
}

export function KeyLevelsStrip() {
  const { data: kl, loading } = useKeyLevels(15_000);
  const t = kl.today;
  const p = kl.prev_day;
  // Day-type: useLiveDayType overlays gate label from /day_type/live (override-aware).
  // Falls back to key_levels.today.day_type only when live is unavailable.
  const live = useLiveDayType();
  const dtDisplay = live?.day_type ?? t.day_type;
  const dtOverridden = !!(live?.overridden);

  const ibTodayEmpty =
    t.ib_status === 'pre_open' ? 'pre-open'
      : t.ib_status === 'missing' ? 'missing'
      : '—';

  return (
    <div
      id="key-levels-strip"
      style={{
        background: COLORS.bgSurface1,
        borderBottom: `1px solid ${COLORS.borderFaint}`,
        flexShrink: 0,
        padding: '4px 12px',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        // מייקל 04.08: שורה אחת בלבד (בפאנל-הצדדי עם גלילה-אופקית) — בלי wrap
        flexWrap: 'nowrap',
        opacity: loading ? 0.4 : 1,
        transition: 'opacity 0.3s',
      }}
    >
      {/* 1. Today POC/VAH/VAL */}
      <PocBlock label="TODAY POC" poc={t.poc} vah={t.vah} val={t.val} color="#a78bfa" />

      <Sep />

      {/* 2. Yest POC/VAH/VAL */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
        {p.session_date && (
          <span style={{
            fontSize: 8,
            color: COLORS.textDisabled,
            fontFamily: 'ui-monospace, monospace',
          }}>
            {p.session_date.slice(5)}
          </span>
        )}
        <PocBlock label="YEST POC" poc={p.poc} vah={p.vah} val={p.val} color="#818cf8" />
      </div>

      <Sep />

      {/* 3+4. IB Today / Y IB — מייקל 04.08 ("מה שלא רלוונטי אין צורך"):
          כשאין ערך (pre-open / dll_missing) הבלוק לא מוצג בכלל. */}
      {t.ib_status !== 'pre_open' && t.ib_high != null && (<>
        <IbBlock
          label="IB TODAY"
          high={t.ib_high}
          low={t.ib_low}
          width={t.ib_width}
          klass={t.ib_class}
          emptyText={ibTodayEmpty}
          primary
        />
        <Sep />
      </>)}
      {p.ib_high != null && (<>
        <IbBlock
          label="Y IB"
          high={p.ib_high}
          low={p.ib_low}
          width={p.ib_width}
          klass={p.ib_class}
          emptyText="dll_missing"
          primary={false}
        />
        <Sep />
      </>)}

      {/* 5. Yest Range */}
      <RangeBlock
        label="YEST RANGE"
        high={p.range_high}
        low={p.range_low}
        range={p.range}
        hColor={COLORS.bull}
        lColor={COLORS.bear}
        rColor={COLORS.textTertiary}
      />

      <Sep />

      {/* 6. Today Range (RTH) */}
      <RangeBlock
        label="TODAY RANGE"
        high={t.rth_high}
        low={t.rth_low}
        range={t.rth_range}
        hColor={COLORS.bull}
        lColor={COLORS.bear}
        rColor={COLORS.textTertiary}
        emptyText="pre-open"
      />

      {/* Day type + opening pills (far right) */}
      {(dtDisplay || t.opening_type) && (
        <>
          <div style={{ flex: 1 }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            {t.opening_type && t.opening_type !== 'NA' && (
              <span style={{
                fontSize: 8,
                fontWeight: 700,
                padding: '1px 5px',
                borderRadius: 2,
                background: 'rgba(6,182,212,0.12)',
                color: '#06b6d4',
              }}>
                {t.opening_type.replace(/_/g, ' ')}
              </span>
            )}
            {dtDisplay && (
              <span style={{
                fontSize: 8,
                fontWeight: 600,
                padding: '1px 5px',
                borderRadius: 2,
                background: dtOverridden ? 'rgba(210,153,34,0.15)' : 'rgba(167,139,250,0.1)',
                color: dtOverridden ? '#d29922' : '#a78bfa',
              }} title={dtOverridden ? 'gate override ≠ classify_replay' : 'get_live_day_type (override-aware)'}>
                {dtDisplay.replace(/_/g, ' ')}{dtOverridden ? ' ·gate' : ''}
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );
}
