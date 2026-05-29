'use client';
import { COLORS } from '../../design/tokens';
import { useKeyLevels } from '../../hooks/useKeyLevels';

function px(v: number | null | undefined, dec = 2): string {
  return v != null ? v.toFixed(dec) : '—';
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', gap: 4, alignItems: 'baseline' }}>
      <span style={{
        fontSize: 8,
        fontWeight: 700,
        color: COLORS.textDisabled,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        minWidth: 64,
        flexShrink: 0,
      }}>{label}</span>
      <span style={{
        fontSize: 9,
        color: COLORS.textSecondary,
        fontFamily: 'ui-monospace, monospace',
        lineHeight: 1.4,
      }}>
        {children}
      </span>
    </div>
  );
}

function Hl({ v, color }: { v: string; color?: string }) {
  return <span style={{ color: color ?? COLORS.textSecondary }}>{v}</span>;
}

/**
 * Compact key levels block embedded in each system's Now tab.
 * Order matches Michael's spec (2026-05-28):
 *   1. Today POC/VAH/VAL  · sierra session (Study ID:3)
 *   2. Yest  POC/VAH/VAL  · sierra previous_session (Study ID:1)
 *   3. IB Today           · sierra ib (Study ID:6)
 *   4. Y IB               · sierra previous_session.ib_* (Input 19 → Yesterday IB study)
 *   5. Yest Range         · sierra prior_day
 *   6. Today Range        · sierra session_high/low
 */
export function KeyLevelsCard() {
  const { data: kl, loading } = useKeyLevels(15_000);
  const t = kl.today;
  const p = kl.prev_day;

  const widthColor = (klass: string | null): string => {
    if (klass === 'NARROW') return '#16a34a';
    if (klass === 'WIDE') return '#dc2626';
    if (klass === 'MEDIUM') return '#f59e0b';
    return COLORS.textTertiary;
  };
  const ibClassColor = widthColor(t.ib_class);
  const prevIbClassColor = widthColor(p.ib_class);

  const ibTodayEmpty =
    t.ib_status === 'pre_open' ? 'pre-open'
      : t.ib_status === 'missing' ? 'missing'
      : '—';

  return (
    <div style={{
      marginTop: 8,
      paddingTop: 6,
      borderTop: `1px solid ${COLORS.borderFaint}`,
      opacity: loading ? 0.5 : 1,
      display: 'flex',
      flexDirection: 'column',
      gap: 3,
    }}>
      <div style={{
        fontSize: 7,
        fontWeight: 700,
        color: COLORS.textDisabled,
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        marginBottom: 1,
      }}>
        Key Levels
      </div>

      {/* 1. TODAY POC */}
      <Row label="TODAY POC">
        <Hl v={`POC ${px(t.poc)}`} color="#a78bfa" />{' / '}
        <Hl v={`VAH ${px(t.vah)}`} color="#c4b5fd" />{' / '}
        <Hl v={`VAL ${px(t.val)}`} color="#c4b5fd" />
      </Row>

      {/* 2. YEST POC */}
      <Row label={`YEST POC${p.session_date ? ` ${p.session_date.slice(5)}` : ''}`}>
        <Hl v={`POC ${px(p.poc)}`} color="#818cf8" />{' / '}
        <Hl v={`VAH ${px(p.vah)}`} color="#6366f1" />{' / '}
        <Hl v={`VAL ${px(p.val)}`} color="#6366f1" />
      </Row>

      {/* 3. IB TODAY */}
      <Row label="IB TODAY">
        {t.ib_high == null && t.ib_low == null ? (
          <span style={{ color: COLORS.textDisabled }}>{ibTodayEmpty}</span>
        ) : (
          <>
            <Hl v={`H ${px(t.ib_high)}`} color="#f59e0b" />{' / '}
            <Hl v={`L ${px(t.ib_low)}`} color="#f59e0b" />
            {t.ib_width != null && (
              <span style={{ marginLeft: 4, color: ibClassColor, fontWeight: 700 }}>
                {px(t.ib_width, 1)}pt {t.ib_class ?? ''}
              </span>
            )}
          </>
        )}
      </Row>

      {/* 4. Y IB */}
      <Row label="Y IB">
        {p.ib_high == null && p.ib_low == null ? (
          <span style={{ color: COLORS.textDisabled }}>dll_missing</span>
        ) : (
          <>
            <Hl v={`H ${px(p.ib_high)}`} color="#d97706" />{' / '}
            <Hl v={`L ${px(p.ib_low)}`} color="#b45309" />
            {p.ib_width != null && (
              <span style={{ marginLeft: 4, color: prevIbClassColor, fontWeight: 700 }}>
                {px(p.ib_width, 1)}pt {p.ib_class ?? ''}
              </span>
            )}
          </>
        )}
      </Row>

      {/* 5. YEST RANGE */}
      <Row label="YEST RANGE">
        {p.range_high == null && p.range_low == null ? (
          <span style={{ color: COLORS.textDisabled }}>—</span>
        ) : (
          <>
            <Hl v={`H ${px(p.range_high)}`} color="#16a34a" />{' / '}
            <Hl v={`L ${px(p.range_low)}`} color="#dc2626" />
            {p.range != null && (
              <span style={{ color: COLORS.textTertiary }}> ({px(p.range, 1)}pt)</span>
            )}
            {p.close != null && (
              <span style={{ color: COLORS.textDisabled }}> · C {px(p.close)}</span>
            )}
          </>
        )}
      </Row>

      {/* 6. TODAY RANGE */}
      <Row label="TODAY RANGE">
        {t.rth_high == null && t.rth_low == null ? (
          <span style={{ color: COLORS.textDisabled }}>pre-open</span>
        ) : (
          <>
            <Hl v={`H ${px(t.rth_high)}`} color="#16a34a" />{' / '}
            <Hl v={`L ${px(t.rth_low)}`} color="#dc2626" />
            {t.rth_range != null && (
              <span style={{ color: COLORS.textTertiary }}> ({px(t.rth_range, 1)}pt)</span>
            )}
          </>
        )}
      </Row>
    </div>
  );
}
