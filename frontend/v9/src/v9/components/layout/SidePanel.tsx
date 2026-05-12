'use client';
import { useState } from 'react';
import { Switcher } from './Switcher';
import { Lens } from '../molecules/Lens';
import { DayTypeLensContent } from '../systems/DayTypeLensContent';
import { FiveMinLensContent } from '../systems/FiveMinLensContent';
import { COLORS, SIZES } from '../../design/tokens';
import { SYSTEM_META } from '../../design/system_colors';

export function SidePanel() {
  const [selectedSystem, setSelectedSystem] = useState(1);

  return (
    <div
      style={{
        width: SIZES.sidePanelWidth,
        height: '100%',
        background: COLORS.bgSurface1,
        borderLeft: `1px solid ${COLORS.borderTertiary}`,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        flexShrink: 0,
      }}
    >
      {/* Active Trade placeholder */}
      <div style={{
        padding: 8,
        borderBottom: `1px solid ${COLORS.borderFaint}`,
        color: COLORS.textTertiary,
        fontSize: 9,
        textAlign: 'center',
        minHeight: 40,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        No Active Trade
      </div>

      {/* Switcher */}
      <div style={{ borderBottom: `1px solid ${COLORS.borderFaint}` }}>
        <Switcher selectedSystem={selectedSystem} onSelectSystem={setSelectedSystem} />
      </div>

      {/* Lens */}
      <div style={{ flex: 1, overflow: 'auto', padding: 6 }}>
        {selectedSystem === 1 ? (
          <LensWithCustomContent systemId={1} ContentComponent={DayTypeLensContent} />
        ) : selectedSystem === 2 ? (
          <LensWithCustomContent systemId={2} ContentComponent={FiveMinLensContent} />
        ) : (
          <Lens systemId={selectedSystem} />
        )}
      </div>
    </div>
  );
}

/** Lens with custom content component for any system */
function LensWithCustomContent({ systemId, ContentComponent }: {
  systemId: number;
  ContentComponent: React.ComponentType<{ activeTab: string }>;
}) {
  const [activeTab, setActiveTab] = useState('Now');
  const meta = SYSTEM_META[systemId];
  if (!meta) return null;

  const TABS = ['Now', 'Plan', 'Shadow', 'Hist', 'Chart'] as const;

  return (
    <div style={{
      borderRadius: SIZES.lensCardRadius,
      border: `${SIZES.lensCardBorder}px solid ${meta.color}`,
      overflow: 'hidden',
      background: COLORS.bgSurface3,
    }}>
      <div style={{
        background: `${meta.color}14`,
        padding: '4px 0 0 0',
        position: 'sticky',
        top: 0,
      }}>
        <div style={{ display: 'flex' }}>
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
                  : '1px solid transparent',
                cursor: 'pointer',
              }}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>
      <div style={{ padding: SIZES.lensPadding }}>
        <ContentComponent activeTab={activeTab} />
      </div>
    </div>
  );
}
