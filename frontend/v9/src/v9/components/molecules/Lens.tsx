'use client';
import { useState } from 'react';
import { SYSTEM_META } from '../../design/system_colors';
import { SIZES, COLORS } from '../../design/tokens';

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
        background: `${meta.color}14`, // 0.08 opacity
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

      {/* Tab content — placeholder for Prompts 4-9 */}
      <div style={{
        padding: SIZES.lensPadding,
        minHeight: 60,
        color: COLORS.textTertiary,
        fontSize: 9,
        textAlign: 'center',
      }}>
        {meta.name} / {activeTab}
      </div>
    </div>
  );
}
