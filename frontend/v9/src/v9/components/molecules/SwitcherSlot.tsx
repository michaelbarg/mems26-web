'use client';
import { Pill, type PillState } from '../atoms/Pill';
import { SYSTEM_META } from '../../design/system_colors';
import { useSystemStateStore } from '../../store/systemStateStore';

interface SwitcherSlotProps {
  systemId: number;
  state?: PillState;
  isSelected?: boolean;
  stateLabel?: string | null;
  onSelect?: (systemId: number) => void;
}

export function SwitcherSlot({ systemId, state, isSelected = false, stateLabel, onSelect }: SwitcherSlotProps) {
  const meta = SYSTEM_META[systemId];
  const health = useSystemStateStore((s) => s.systems[systemId]?.health ?? 'unknown');
  if (!meta) return null;

  // Priority: selected > explicit state > health-derived
  const healthState: PillState = health === 'healthy' ? 'healthy' : health === 'warn' ? 'warn' : health === 'error' ? 'error' : 'idle';
  const pillState: PillState = isSelected ? 'selected' : (state ?? healthState);

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
      {stateLabel != null && (
        <span style={{
          fontSize: 6,
          color: meta.color,
          fontWeight: 500,
          lineHeight: 1,
          textAlign: 'center',
          maxWidth: 44,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          opacity: 0.7,
        }}>
          {stateLabel}
        </span>
      )}
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
