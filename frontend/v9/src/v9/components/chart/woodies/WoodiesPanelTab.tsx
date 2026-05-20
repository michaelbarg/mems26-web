'use client';

/** §1 — S4 WOODY toggle on main 5m chart left edge.
 *
 * P30 2026-05-20: `open` is derived from `localStorage` in `ChartV5b`
 * (`useState` initializer reads `mems26-woodies-panel-open`). SSR sees no
 * localStorage and renders with `open=false`, the client hydrates with
 * `open=true` if the user previously opened the panel — React then throws
 * a hydration mismatch warning. `suppressHydrationWarning` tells React
 * to keep the client value silently (the visual is correct after the
 * first paint, no functional bug).
 */
export function WoodiesPanelTab({
  open,
  onToggle,
}: {
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      suppressHydrationWarning
      type="button"
      data-testid="woodies-panel-tab"
      aria-pressed={open}
      title={open ? 'Hide Woodies CCI panel' : 'Show Woodies CCI panel'}
      onClick={onToggle}
      style={{
        position: 'absolute',
        left: 0,
        bottom: 96,
        zIndex: 25,
        width: 22,
        padding: '6px 2px',
        borderTop: `1px solid ${open ? '#fb950b' : '#1A3A3A'}`,
        borderRight: `1px solid ${open ? '#fb950b' : '#1A3A3A'}`,
        borderBottom: `1px solid ${open ? '#fb950b' : '#1A3A3A'}`,
        borderLeft: 'none',
        borderTopRightRadius: 4,
        borderBottomRightRadius: 4,
        background: open ? 'rgba(251, 149, 11, 0.25)' : 'rgba(45, 85, 85, 0.92)',
        color: open ? '#fb950b' : '#A3E0E0',
        fontSize: 8,
        fontWeight: 800,
        fontFamily: 'ui-monospace, monospace',
        letterSpacing: 0.5,
        writingMode: 'vertical-rl',
        textOrientation: 'mixed',
        cursor: 'pointer',
        lineHeight: 1.1,
      }}
    >
      WOODY
    </button>
  );
}
