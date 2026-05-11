'use client';
import { Pill, type PillState } from '../atoms/Pill';
import { SYSTEM_META } from '../../design/system_colors';

interface SwitcherSlotProps {
  systemId: number;
  state?: PillState;
  isSelected?: boolean;
  onSelect?: (systemId: number) => void;
}

export function SwitcherSlot({ systemId, state = 'idle', isSelected = false, onSelect }: SwitcherSlotProps) {
  const meta = SYSTEM_META[systemId];
  if (!meta) return null;

  const pillState: PillState = isSelected ? 'selected' : state;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 2,
      }}
    >
      <Pill systemId={systemId} state={pillState} onClick={() => onSelect?.(systemId)} />
      <span style={{
        fontSize: 8,
        color: isSelected ? meta.color : '#737373',
        fontWeight: isSelected ? 600 : 400,
        lineHeight: 1,
        textAlign: 'center',
        maxWidth: 40,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {meta.name}
      </span>
    </div>
  );
}
