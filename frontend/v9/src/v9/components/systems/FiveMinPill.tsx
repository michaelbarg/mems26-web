'use client';
import { SwitcherSlot } from '../molecules/SwitcherSlot';
import { useSystemStateStore } from '../../store/systemStateStore';
import type { PillState } from '../atoms/Pill';

interface FiveMinPillProps {
  isSelected?: boolean;
  onSelect?: () => void;
}

const MODE_ABBREV: Record<string, string> = {
  FIRST_HOUR_TACTICAL: 'FH', DAY_TYPE_MODE: 'IDLE', OVERNIGHT_MODE: 'ON',
  WEEKEND: 'WE', MAINTENANCE: 'MT', WAITING_OPEN: 'WAIT', LIVE_ONLY: 'LIVE',
};

const PATTERN_ABBREV: Record<string, string> = {
  REACTIVE_LONG: 'R-L', REACTIVE_SHORT: 'R-S',
  INITIATIVE_LONG: 'I-L', INITIATIVE_SHORT: 'I-S',
};

export function FiveMinPill({ isSelected = false, onSelect }: FiveMinPillProps) {
  const sysState = useSystemStateStore((s) => s.systems[2]);
  const raw = sysState.state ?? '';
  const label = PATTERN_ABBREV[raw] ?? MODE_ABBREV[raw] ?? (raw ? raw.slice(0, 4) : 'IDLE');

  return (
    <SwitcherSlot
      systemId={2}
      state={'idle' as PillState}
      isSelected={isSelected}
      stateLabel={label}
      onSelect={onSelect ? () => onSelect() : undefined}
    />
  );
}
