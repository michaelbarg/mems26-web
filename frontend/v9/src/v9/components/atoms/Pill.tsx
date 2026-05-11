'use client';
import { SYSTEM_META } from '../../design/system_colors';
import { SIZES } from '../../design/tokens';

export type PillState = 'idle' | 'armed' | 'fired' | 'selected';

interface PillProps {
  systemId: number;
  state?: PillState;
  onClick?: () => void;
}

const DOT_COLORS: Record<string, string> = {
  idle: '#525252',
  armed: '#facc15',
  fired: '#16a34a',
  selected: '#e5e5e5',
};

export function Pill({ systemId, state = 'idle', onClick }: PillProps) {
  const meta = SYSTEM_META[systemId];
  if (!meta) return null;

  const isFiring = meta.type === 'FIRING';
  const size = isFiring ? SIZES.pillFiring : SIZES.pillObserving;
  const isSelected = state === 'selected';
  const isFired = state === 'fired';

  return (
    <button
      onClick={onClick}
      style={{
        width: size.w,
        height: size.h,
        borderRadius: SIZES.pillBorderRadius,
        border: isSelected
          ? `${SIZES.pillBorderSelected}px solid ${meta.color}`
          : '1px solid #262626',
        background: isSelected
          ? `${meta.color}2e`  // 0.18 opacity
          : '#1a1a1a',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 2,
        cursor: 'pointer',
        padding: 0,
        animation: isFired ? 'pulseFire 1.6s ease-in-out infinite' : undefined,
      }}
    >
      <span style={{ fontSize: 9, fontWeight: 600, color: meta.color, lineHeight: 1 }}>
        {meta.id}
      </span>
      <div style={{
        width: 16, height: 3, borderRadius: 1,
        background: meta.color,
      }} />
      <div style={{
        width: 5, height: 5, borderRadius: '50%',
        background: DOT_COLORS[state] ?? DOT_COLORS.idle,
      }} />
    </button>
  );
}
