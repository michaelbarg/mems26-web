'use client';
import { SwitcherSlot } from '../molecules/SwitcherSlot';
import { useSystemStateStore } from '../../store/systemStateStore';
import type { PillState } from '../atoms/Pill';

interface FiveMinPillProps {
  isSelected?: boolean;
  onSelect?: () => void;
}

const ABBREV: Record<string, string> = {
  FIRST_HOUR_TACTICAL: 'FH', DAY_TYPE_MODE: 'DT', OVERNIGHT_MODE: 'ON',
  WEEKEND: 'WE', MAINTENANCE: 'MT', WAITING_OPEN: 'WAIT', LIVE_ONLY: 'LIVE',
};

export function FiveMinPill({ isSelected = false, onSelect }: FiveMinPillProps) {
  const sysState = useSystemStateStore((s) => s.systems[2]);
  const label = sysState.state ? (ABBREV[sysState.state] ?? sysState.state.slice(0, 4)) : '—';

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
