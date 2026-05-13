'use client';
import { SwitcherSlot } from '../molecules/SwitcherSlot';
import { useSystemStateStore } from '../../store/systemStateStore';
import type { PillState } from '../atoms/Pill';

const MIG_ABBREV: Record<string, string> = {
  UP: '\u2191', DOWN: '\u2193', STUCK: '=', NA: '\u2014',
  D: 'D', b: 'b', P: 'P', double: 'DD', trend: 'TRD', neutral: 'NEU',
};

export function TPOPill({ isSelected = false, onSelect }: { isSelected?: boolean; onSelect?: () => void }) {
  const sysState = useSystemStateStore((s) => s.systems[5]);
  const label = sysState.state ? (MIG_ABBREV[sysState.state] ?? sysState.state.slice(0, 3)) : '\u2014';

  return (
    <SwitcherSlot
      systemId={5}
      state={'idle' as PillState}
      isSelected={isSelected}
      stateLabel={label}
      onSelect={onSelect ? () => onSelect() : undefined}
    />
  );
}
