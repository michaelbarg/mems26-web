'use client';
import { SwitcherSlot } from '../molecules/SwitcherSlot';
import { useSystemStateStore } from '../../store/systemStateStore';
import type { PillState } from '../atoms/Pill';

const ZONE_ABBREV: Record<string, string> = {
  ASIA: 'ASIA', LONDON: 'LON', NY_PREMARKET: 'PRE',
  NY_OPEN: 'OPEN', MIDDAY: 'MID', NY_PM: 'PM',
  POST_MARKET: 'POST', CLOSED: 'OFF', WEEKEND: 'WE', UNKNOWN: '—',
};

export function KillzonePill({ isSelected = false, onSelect }: { isSelected?: boolean; onSelect?: () => void }) {
  const sysState = useSystemStateStore((s) => s.systems[6]);
  const label = sysState.state ? (ZONE_ABBREV[sysState.state] ?? sysState.state.slice(0, 4)) : '—';

  return (
    <SwitcherSlot
      systemId={6}
      state={'idle' as PillState}
      isSelected={isSelected}
      stateLabel={label}
      onSelect={onSelect ? () => onSelect() : undefined}
    />
  );
}
