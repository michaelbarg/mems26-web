'use client';
import { useState } from 'react';
import { SYSTEM_META } from '../../design/system_colors';
import { SIZES, COLORS } from '../../design/tokens';
import { EmptyState } from '../atoms/EmptyState';

const TABS = ['Now', 'Plan', 'Shadow', 'Hist', 'Chart'] as const;
type LensTab = typeof TABS[number];

interface LensProps {
  systemId: number;
}

export function Lens({ systemId }: LensProps) {
  const [activeTab, setActiveTab] = useState<LensTab>('Now');
  const meta = SYSTEM_META[systemId];
  if (!meta) return null;

  return (
    <div
      style={{
        borderRadius: SIZES.lensCardRadius,
        border: `${SIZES.lensCardBorder}px solid ${meta.color}`,
        overflow: 'hidden',
        background: COLORS.bgSurface3,
      }}
    >
      {/* Sticky header with system color tint */}
      <div style={{
        background: `${meta.color}2e`, // 0.18 opacity per V5 §4.4
        padding: '4px 0 0 0',
        position: 'sticky',
        top: 0,
      }}>
        <div style={{
          display: 'flex',
          gap: 0,
        }}>
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                flex: 1,
                padding: '4px 0',
                fontSize: 9,
                fontWeight: activeTab === tab ? 600 : 400,
                color: activeTab === tab ? meta.color : COLORS.textTertiary,
                background: 'transparent',
                border: 'none',
                borderBottom: activeTab === tab
                  ? `${SIZES.lensTabBorderActive}px solid ${meta.color}`
                  : `1px solid transparent`,
                cursor: 'pointer',
              }}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div style={{
        padding: SIZES.lensPadding,
        minHeight: 60,
      }}>
        {activeTab === 'Now' && (
          <div style={{ color: COLORS.textTertiary, fontSize: 9, textAlign: 'center' }}>
            {meta.name} / Now
          </div>
        )}
        {activeTab === 'Plan' && (
          <EmptyState badge="P" title="Coming in Wave 3" description="System plan + entry conditions." />
        )}
        {activeTab === 'Shadow' && (
          <EmptyState badge="S" title="Coming after Day 14" description="7d performance: WR, R, Net." />
        )}
        {activeTab === 'Hist' && (
          <EmptyState badge="H" title="Coming with backfill" description="Last 30d events + trades." />
        )}
        {activeTab === 'Chart' && (
          <EmptyState badge="C" title="Coming in Phase 4" description="System-specific visualizations." />
        )}
      </div>
    </div>
  );
}
