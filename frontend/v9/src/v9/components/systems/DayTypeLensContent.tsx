'use client';
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';
import { systemColor } from '../../design/system_colors';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface DayTypeV9Data {
  session_date: string;
  day_type: string;
  probability: number | null;
  directional_certainty: string | null;
  trading_confidence: string | null;
  ib_h: number | null;
  ib_l: number | null;
  ib_width: number | null;
  ib_range: number | null;
  ib_width_class: string | null;
  ib_locked: boolean;
  opening_type: string | null;
  last_updated_at: string | null;
  reasoning_notes: string | null;
  active_zohar_rules: string[];
}

interface LensContentProps {
  activeTab: string;
}

export function DayTypeLensContent({ activeTab }: LensContentProps) {
  const [current, setCurrent] = useState<DayTypeV9Data | null>(null);
  const [classified, setClassified] = useState(false);
  const [developing, setDeveloping] = useState(false);
  const color = systemColor(1);

  useEffect(() => {
    fetch(`${API_BASE}/api/v9/day_type/v9/current`)
      .then((r) => r.json())
      .then((d) => {
        setClassified(d?.classified ?? false);
        setDeveloping(d?.developing ?? false);
        setCurrent(d?.data ?? null);
      })
      .catch(() => {});
  }, [activeTab]);

  const ibStatusLabel = classified ? 'CLASSIFIED' : developing ? 'IB DEVELOPING' : 'PENDING';
  const ibStatusColor = classified
    ? COLORS.textTertiary
    : developing
    ? '#FACC15'
    : COLORS.textTertiary;

  if (activeTab === 'Now') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 12, fontWeight: 700, color }}>
            {classified
              ? (current?.day_type?.replace(/_/g, ' ') ?? '\u2014')
              : developing
              ? 'Building IB\u2026'
              : '\u2014'}
          </span>
          <span style={{ fontSize: 9, color: ibStatusColor, fontWeight: developing ? 700 : 400 }}>
            {ibStatusLabel}
          </span>
        </div>
        {current && (
          <>
            {classified && (
              <div style={{ fontSize: 9, color: COLORS.textSecondary }}>
                Probability: {current.probability != null ? `${Math.round(current.probability * 100)}%` : '\u2014'}
                {current.directional_certainty && (
                  <span style={{ marginLeft: 8, color: COLORS.textTertiary }}>
                    Dir: {current.directional_certainty}
                  </span>
                )}
                {current.trading_confidence && (
                  <span style={{ marginLeft: 8, color: COLORS.textTertiary }}>
                    Trade: {current.trading_confidence}
                  </span>
                )}
              </div>
            )}
            <div style={{ fontSize: 9, color: COLORS.textTertiary }}>
              {(current.ib_h != null && current.ib_l != null) ? (
                <>
                  <span style={{ color: developing ? '#FACC15' : COLORS.textSecondary }}>
                    IBH {current.ib_h.toFixed(2)}
                  </span>
                  {' / '}
                  <span style={{ color: developing ? '#FACC15' : COLORS.textSecondary }}>
                    IBL {current.ib_l.toFixed(2)}
                  </span>
                  {(current.ib_range ?? current.ib_width) != null && (
                    <span style={{ marginLeft: 6, color: developing ? '#FACC15' : COLORS.textSecondary, fontWeight: 700 }}>
                      {(current.ib_range ?? current.ib_width)!.toFixed(1)} pt
                      {developing ? ' 🔄' : current.ib_locked ? ' 🔒' : ''}
                    </span>
                  )}
                </>
              ) : (
                <span>IB: \u2014</span>
              )}
            </div>
            <div style={{ fontSize: 9, color: COLORS.textTertiary }}>
              Opening: {current.opening_type || '\u2014'}
              {current.ib_width_class && current.ib_width_class !== 'DEVELOPING' && (
                <span style={{ marginLeft: 8 }}>{current.ib_width_class}</span>
              )}
            </div>
            {current.active_zohar_rules && current.active_zohar_rules.length > 0 && (
              <div style={{ fontSize: 9, color: COLORS.textTertiary }}>
                Zohar: {current.active_zohar_rules.join(', ')}
              </div>
            )}
          </>
        )}
      </div>
    );
  }

  if (activeTab === 'Plan') {
    const { DayTypePlan } = require('../sidepanel/lens/plan/DayTypePlan');
    return <DayTypePlan />;
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
