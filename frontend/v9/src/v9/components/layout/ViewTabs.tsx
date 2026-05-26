'use client';
import { COLORS } from '../../design/tokens';

export type DashboardView = 'main' | 'build_status';

interface ViewTabsProps {
  active: DashboardView;
  onChange: (view: DashboardView) => void;
}

const TABS: Array<{ id: DashboardView; label: string }> = [
  { id: 'main', label: 'Dashboard' },
  { id: 'build_status', label: 'Build Status' },
];

export function ViewTabs({ active, onChange }: ViewTabsProps) {
  return (
    <div
      data-testid="view-tabs"
      style={{
        display: 'flex',
        alignItems: 'stretch',
        height: 26,
        background: COLORS.bgSurface2,
        borderBottom: `1px solid ${COLORS.borderTertiary}`,
        flexShrink: 0,
      }}
    >
      {TABS.map((t) => {
        const isActive = active === t.id;
        return (
          <button
            key={t.id}
            onClick={() => onChange(t.id)}
            style={{
              padding: '0 16px',
              background: isActive ? COLORS.bgSurface4 : 'transparent',
              color: isActive ? COLORS.textPrimary : COLORS.textSecondary,
              border: 'none',
              borderRight: `1px solid ${COLORS.borderFaint}`,
              borderBottom: isActive ? `2px solid ${COLORS.modeShadow}` : '2px solid transparent',
              fontSize: 11,
              fontFamily: 'ui-monospace, monospace',
              fontWeight: isActive ? 600 : 400,
              cursor: 'pointer',
              letterSpacing: '0.3px',
              transition: 'background 150ms, color 150ms',
            }}
            onMouseEnter={(e) => {
              if (!isActive) (e.currentTarget.style.background = COLORS.bgSurface3);
            }}
            onMouseLeave={(e) => {
              if (!isActive) (e.currentTarget.style.background = 'transparent');
            }}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}
