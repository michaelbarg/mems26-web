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
  /** Active SHADOW trade fired from this system — show entry price on pill */
  isTradeFiring?: boolean;
  tradeEntryPrice?: number | null;
}

export function SwitcherSlot({
  systemId,
  state,
  isSelected = false,
  stateLabel,
  onSelect,
  isTradeFiring = false,
  tradeEntryPrice,
}: SwitcherSlotProps) {
  const meta = SYSTEM_META[systemId];
  const health = useSystemStateStore((s) => s.systems[systemId]?.health ?? 'unknown');
  if (!meta) return null;

  // Priority: selected > explicit state > health-derived
  const healthState: PillState = health === 'healthy' ? 'healthy' : health === 'warn' ? 'warn' : health === 'error' ? 'error' : 'idle';
  const pillState: PillState = isTradeFiring ? 'selected' : (isSelected ? 'selected' : (state ?? healthState));

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 2,
        padding: isTradeFiring ? '2px 4px' : 0,
        borderRadius: 4,
        border: isTradeFiring ? `1px solid ${meta.color}` : '1px solid transparent',
        background: isTradeFiring ? `${meta.color}18` : 'transparent',
      }}
    >
      <Pill systemId={systemId} state={pillState} onClick={() => onSelect?.(systemId)} />
      {isTradeFiring && tradeEntryPrice != null && (
        <span style={{
          fontSize: 7,
          fontFamily: 'ui-monospace',
          fontWeight: 700,
          color: meta.color,
          lineHeight: 1,
        }}>
          @{tradeEntryPrice.toFixed(2)}
        </span>
      )}
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
