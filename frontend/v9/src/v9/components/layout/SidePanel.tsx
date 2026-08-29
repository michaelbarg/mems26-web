'use client';
import { useState } from 'react';
import { Switcher } from './Switcher';
import { Lens } from '../molecules/Lens';
import { DayTypeLensContent } from '../systems/DayTypeLensContent';
import { FiveMinLensContent } from '../systems/FiveMinLensContent';
import { FootprintLensContent } from '../systems/FootprintLensContent';
import { WoodiesLensContent } from '../systems/WoodiesLensContent';
import { TPOLensContent } from '../systems/TPOLensContent';
import { KillzoneLensContent } from '../systems/KillzoneLensContent';
import { ActiveTradeCard } from '../sidepanel/ActiveTradeCard';
import { NearestFireStrip } from '../sidepanel/NearestFireStrip';
import { COLORS, SIZES } from '../../design/tokens';
import { KeyLevelsStrip } from '../strips/KeyLevelsStrip';
import { SYSTEM_META } from '../../design/system_colors';

export function SidePanel() {
  const [selectedSystem, setSelectedSystem] = useState(1);
  const [tradeCtx, setTradeCtx] = useState<{ firingSystemId: number; entryPrice: number } | null>(null);

  return (
    <div
      style={{
        width: SIZES.sidePanelWidth,
        height: '100%',
        background: COLORS.bgSurface1,
        borderLeft: `1px solid ${COLORS.borderTertiary}`,
        display: 'flex',
        flexDirection: 'column',
        // מייקל 27.08: "בפאנל כולו צריך אפשרות לגלול — לא רואה את החלק התחתון".
        // overflow:hidden חתך את התחתית כשהתוכן גבוה מהחלון; עכשיו הפאנל כולו
        // נגלל, והעדשה שומרת על הגלילה הפנימית שלה.
        overflowY: 'auto',
        overflowX: 'hidden',
        flexShrink: 0,
      }}
    >
      {/* Active Trade Card */}
      <ActiveTradeCard onTradeContext={setTradeCtx} />

      {/* מייקל 27.08: התבנית הקרובה-ביותר לירי — תמיד גלויה בראש הפאנל */}
      <NearestFireStrip />

      {/* Switcher */}
      <div style={{ borderBottom: `1px solid ${COLORS.borderFaint}` }}>
        <Switcher
          selectedSystem={selectedSystem}
          onSelectSystem={setSelectedSystem}
          tradeFiringSystemId={tradeCtx?.firingSystemId ?? null}
          tradeEntryPrice={tradeCtx?.entryPrice ?? null}
        />
      </div>

      {/* Lens — header tint per selected system (κ.5 §4.4) */}
      <div style={{
        flex: 1, overflow: 'auto', padding: 6,
        borderTop: `2px solid ${SYSTEM_META[selectedSystem]?.color || COLORS.borderFaint}`,
      }}>
        {selectedSystem === 1 ? (
          <LensWithCustomContent systemId={1} ContentComponent={DayTypeLensContent} />
        ) : selectedSystem === 2 ? (
          <LensWithCustomContent systemId={2} ContentComponent={FiveMinLensContent} />
        ) : selectedSystem === 3 ? (
          <LensWithCustomContent systemId={3} ContentComponent={FootprintLensContent} />
        ) : selectedSystem === 4 ? (
          <LensWithCustomContent systemId={4} ContentComponent={WoodiesLensContent} />
        ) : selectedSystem === 5 ? (
          <LensWithCustomContent systemId={5} ContentComponent={TPOLensContent} />
        ) : selectedSystem === 6 ? (
          <LensWithCustomContent systemId={6} ContentComponent={KillzoneLensContent} />
        ) : (
          <Lens systemId={selectedSystem} />
        )}
      </div>

      {/* מייקל 05.08: "מגירת-מידע-משני" — רכיב מתקפל בתחתית הפאנל לכל מה שלא
          רלוונטי-כרגע (מתחיל עם שורת-הרמות; מוסיפים לכאן כל מידע-משני עתידי).
          סגור כברירת-מחדל; הבחירה נשמרת. */}
      <SecondaryDrawer>
        <div style={{ display: 'inline-block', minWidth: 'max-content' }}>
          <KeyLevelsStrip />
        </div>
      </SecondaryDrawer>

      {/* מייקל 29.08: "שיהיה לינק באפליקציה ובמערכת פרונטאנד". תיק-המוכנות
          הוא דף סטטי ב-public/, שנוצר מ-docs/plans/TASK_LOG.md ע"י
          scripts/gen_readiness_page.py. תצוגה בלבד — אין קריאת-API, אין
          פולינג, ואין נגיעה בלוגיקת-המסחר (CLAUDE.md § Frontend Polling Floors). */}
      <ReadinessLink />
    </div>
  );
}

/** קישור לתיק-המוכנות (T-135). נפתח בלשונית חדשה כדי לא לאבד את הדשבורד. */
function ReadinessLink() {
  const [hover, setHover] = useState(false);
  return (
    <a
      href="/readiness.html"
      target="_blank"
      rel="noopener noreferrer"
      title="תיק-המוכנות — פתוח / בוצע / מאורכב, נגזר מלוג-המשימות"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: 'block', flexShrink: 0, textAlign: 'right', direction: 'rtl',
        padding: '4px 8px', fontSize: 9, fontWeight: 700, textDecoration: 'none',
        color: hover ? COLORS.textPrimary : COLORS.textTertiary,
        background: hover ? COLORS.bgSurface3 : 'transparent',
        borderTop: `1px solid ${COLORS.borderFaint}`,
      }}
    >
      📋 תיק-מוכנות ↗
    </a>
  );
}

/** מגירת-מידע-משני מתקפלת (מייקל 05.08) */
function SecondaryDrawer({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  useState(() => {
    if (typeof window !== 'undefined' && localStorage.getItem('sidepanel-secondary-open') === '1') setOpen(true);
    return undefined;
  });
  return (
    <div style={{ borderTop: `1px solid ${COLORS.borderFaint}`, flexShrink: 0 }}>
      <div
        onClick={() => setOpen(o => { localStorage.setItem('sidepanel-secondary-open', o ? '0' : '1'); return !o; })}
        style={{
          padding: '3px 8px', fontSize: 9, fontWeight: 700, color: COLORS.textTertiary,
          cursor: 'pointer', userSelect: 'none',
        }}>
        {open ? '▾' : '▸'} מידע משני (רמות ועוד)
      </div>
      {open && (
        <div style={{ overflowX: 'auto', whiteSpace: 'nowrap', maxHeight: 60 }}>
          {children}
        </div>
      )}
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
      <div style={{ padding: activeTab === 'Plan' ? 4 : SIZES.lensPadding }}>
        <ContentComponent activeTab={activeTab} />
      </div>
    </div>
  );
}
