'use client';
import { SwitcherSlot } from '../molecules/SwitcherSlot';
import { useSystemStateStore } from '../../store/systemStateStore';
import type { PillState } from '../atoms/Pill';

const SHAPE_ABBREV: Record<string, string> = {
  D: 'D', b: 'b', P: 'P', double: 'DD', trend: 'TRD', neutral: 'NEU', NA: '—',
};

export function TPOPill({ isSelected = false, onSelect }: { isSelected?: boolean; onSelect?: () => void }) {
  const sysState = useSystemStateStore((s) => s.systems[5]);
  const label = sysState.state ? (SHAPE_ABBREV[sysState.state] ?? sysState.state.slice(0, 3)) : '—';

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
