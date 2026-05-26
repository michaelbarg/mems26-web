'use client';
import type { PatternStatus } from './types';
import { COLORS } from '../../design/tokens';

interface StatusPillProps {
  status: PatternStatus;
  label?: string;
}

const STATUS_STYLES: Record<PatternStatus, { bg: string; fg: string; icon: string; label: string }> = {
  fired:          { bg: '#0e3a1f', fg: COLORS.bull,     icon: '✓', label: 'Fired' },
  armed:          { bg: '#3a2e0a', fg: COLORS.caution,  icon: '◐', label: 'Armed' },
  blocked:        { bg: '#3a1a1a', fg: COLORS.bear,     icon: '✕', label: 'Blocked' },
  vetoed:         { bg: '#3a280a', fg: COLORS.warning,  icon: '⚠', label: 'Vetoed' },
  not_applicable: { bg: '#1a1a1a', fg: COLORS.textDisabled, icon: '−', label: 'N/A' },
  unknown:        { bg: '#1a1a1a', fg: COLORS.textTertiary, icon: '?', label: 'Unknown' },
};

export function StatusPill({ status, label }: StatusPillProps) {
  const s = STATUS_STYLES[status] || STATUS_STYLES.unknown;
  const displayLabel = label || s.label;
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '2px 8px',
        borderRadius: 4,
        background: s.bg,
        color: s.fg,
        fontSize: 10,
        fontFamily: 'ui-monospace, monospace',
        fontWeight: 600,
        whiteSpace: 'nowrap',
        minWidth: 80,
        justifyContent: 'center',
      }}
    >
      <span style={{ fontSize: 11 }}>{s.icon}</span>
      <span>{displayLabel}</span>
    </span>
  );
}
