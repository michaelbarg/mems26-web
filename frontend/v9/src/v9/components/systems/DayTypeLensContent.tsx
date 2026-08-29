'use client';
// DayTypeLensContent — the S1 (Day-Type) side-panel lens, tidied (P-UI day-type round,
// 2026-07-02). One clear read-only panel:
//   1. Current classification — type (colored, same palette as the labeler/build-status
//      tables) + status (FORMING/PROVISIONAL/CLASSIFIED) + since-when + stance + reason.
//   2. The classifier's own context — IB width/class/source · VA width · opening · volume.
//   3. Key levels (IBH/IBL + POC/VAH/VAL + ranges) — the existing KeyLevelsCard
//      (/api/v9/key_levels, 15s hook — reused, not duplicated).
//   4. The 7-type legend with the trader meaning per type (playbook one-liners).
//
// Data source: useLiveDayType → GET /api/v9/day_type/classify_replay (the CANONICAL
// 7-type classifier — docs/SOURCE_OF_TRUTH.md §Day-type ✅ / S1_ACTIVE_CANONICAL.md),
// 30s poll, one existing hook mount — no new endpoints, no new intervals.
// REMOVED (dead sources, retired from the frontend 2026-06-22 per SOURCE_OF_TRUTH.md):
//   GET /api/v9/day_type/v9/current (returns data:null → the old block never rendered)
//   GET /api/v9/day_type/state (legacy wrapper; meta was its only use here).
import { COLORS } from '../../design/tokens';
import { systemColor } from '../../design/system_colors';
import { KeyLevelsCard } from './KeyLevelsCard';
import { ShadowTab } from '../sidepanel/lens/trades/TradesTab';
import { useLiveDayType } from '../../hooks/useLiveDayType';
import { DAY_TYPE_LEGEND, DAY_TYPE_DIRECTION_HE, dayTypeColor } from '../../lib/dayType';

interface LensContentProps {
  activeTab: string;
}

function Meta({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <span style={{ whiteSpace: 'nowrap' }}>
      <span style={{ color: COLORS.textDisabled }}>{label} </span>
      <b style={{ color: color ?? COLORS.textSecondary, fontWeight: 600 }}>{value}</b>
    </span>
  );
}

export function DayTypeLensContent({ activeTab }: LensContentProps) {
  const color = systemColor(1);
  // Canonical 7-type classifier (live shadow) — existing 30s hook.
  const live = useLiveDayType();

  if (activeTab === 'Now') {
    const dtc = dayTypeColor(live?.day_type);
    const classified = live?.status === 'CLASSIFIED';
    const stance = live?.direction ? (DAY_TYPE_DIRECTION_HE[live.direction] ?? live.direction) : null;
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {/* 1. Current classification */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6 }}>
          {live?.day_type ? (
            <span style={{
              fontSize: 12, fontWeight: 700, color: dtc,
              padding: '1px 7px', borderRadius: 3,
              background: `${dtc}${classified ? '26' : '14'}`,
              border: `1px solid ${dtc}${classified ? 'cc' : '55'}`,
            }}>
              {live.day_type.replace(/_/g, ' ')}
              {live.invalidated ? ' ⚠' : ''}
            </span>
          ) : (
            <span style={{ fontSize: 12, fontWeight: 700, color }}>—</span>
          )}
          <span style={{
            fontSize: 9, fontWeight: classified ? 400 : 700,
            color: classified ? COLORS.textTertiary : '#FACC15',
          }}>
            {live?.status ?? 'מסווג לא זמין'}
          </span>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, fontSize: 9, color: COLORS.textTertiary }}>
          {live?.since && <Meta label="מאז" value={`${live.since} ET`} />}
          {stance && <Meta label="גישה" value={stance} color={dtc} />}
          {live?.n_bars != null && <Meta label="ברים" value={String(live.n_bars)} />}
        </div>
        {live?.invalidated && (
          <div style={{ fontSize: 9, color: '#f85149' }}>
            ⚠ הפתיחה נחצתה (INVALIDATED) — יציאה + סיווג מחדש
          </div>
        )}
        {live?.reason && (
          <div style={{ fontSize: 9, color: COLORS.textDisabled }} title="נימוק המסווג (reason)">
            {live.reason}
          </div>
        )}
        {!live && (
          <div style={{ fontSize: 9, color: COLORS.textDisabled }}>
            classify_replay לא זמין (offline / אין ברים עדיין) — אין ערך מומצא.
          </div>
        )}

        {/* 2. What the classifier measured today (same response — no extra fetch) */}
        {live && (
          <div style={{
            display: 'flex', flexWrap: 'wrap', gap: 8, fontSize: 9,
            color: COLORS.textTertiary, paddingTop: 4, borderTop: `1px solid ${COLORS.borderFaint}`,
          }}>
            {live.ib_width != null && (
              <Meta
                label="IB"
                value={`${live.ib_width.toFixed(1)}pt${live.ib_class && live.ib_class !== 'UNKNOWN' ? ` ${live.ib_class}` : ''}`}
                color="#e3b341"
              />
            )}
            {live.ib_source && <Meta label="מקור-IB" value={live.ib_source} color={live.ib_source === 'sierra_tpo' ? COLORS.textSecondary : '#FACC15'} />}
            {live.va_width != null && <Meta label="VA" value={`${live.va_width.toFixed(1)}pt`} />}
            {live.opening_type && <Meta label="פתיחה" value={live.opening_type.replace('OPEN_', '')} color="#bc8cff" />}
            {live.vol_ratio != null && <Meta label="ווליום" value={`${live.vol_ratio}×`} color={live.vol_ratio <= 0.5 ? '#f85149' : undefined} />}
          </div>
        )}

        {/* 3. Key levels — IBH/IBL + POC/VAH/VAL + ranges (existing reusable fetch) */}
        <KeyLevelsCard />

        {/* 4. The 7 types — trader meaning (playbook one-liners) */}
        <div style={{ marginTop: 8, paddingTop: 6, borderTop: `1px solid ${COLORS.borderFaint}` }}>
          {/* ביקורת-UX 29.08 (RTL): בלי dir="rtl" ה-"7" הפותח מקבל כיוון-LTR ונדחף
              לקצה השמאלי — כלומר לסוף המשפט לקורא עברית ("סוגי-יום … 7").
              נמדד: x(7)=0 מול x(ס)=184 ב-ltr; ב-rtl ה-7 חוזר לימין (591 מול 576). */}
          <div dir="rtl" style={{
            fontSize: 7, fontWeight: 700, color: COLORS.textDisabled,
            letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 3,
          }}>
            7 סוגי-יום — משמעות למסחר
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {DAY_TYPE_LEGEND.map((row) => {
              const active = live?.day_type === row.type
                || (row.type === 'Normal_Variation' && live?.day_type === 'Variation');
              const c = dayTypeColor(row.type);
              return (
                <div key={row.type} style={{
                  display: 'flex', gap: 5, alignItems: 'baseline',
                  opacity: live?.day_type && !active ? 0.75 : 1,
                }}>
                  <span style={{
                    width: 8, height: 8, borderRadius: 2, background: c,
                    flexShrink: 0, alignSelf: 'center',
                    outline: active ? `1px solid ${COLORS.textSecondary}` : 'none',
                  }} />
                  <span style={{
                    fontSize: 9, fontWeight: active ? 700 : 600, color: c,
                    whiteSpace: 'nowrap', flexShrink: 0, minWidth: 74,
                  }}>
                    {row.label}
                  </span>
                  <span style={{ fontSize: 8.5, color: active ? COLORS.textSecondary : COLORS.textTertiary, lineHeight: 1.35 }}>
                    {row.meaning}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  if (activeTab === 'Plan') {
    const { DayTypePlan } = require('../sidepanel/lens/plan/DayTypePlan');
    return <DayTypePlan />;
  }

  if (activeTab === 'Shadow') {
    return <ShadowTab />;
  }

  if (activeTab === 'Hist') {
    return (
      <div style={{ fontSize: 9, color: COLORS.textTertiary, textAlign: 'center', padding: 8 }}>
        Last 30 days — will populate from /api/v9/day_type/v9/history
      </div>
    );
  }

  return (
    <div style={{ fontSize: 9, color: COLORS.textTertiary, textAlign: 'center', padding: 8 }}>
      {activeTab} — coming in later prompts
    </div>
  );
}
