'use client';
import { SwitcherSlot } from '../molecules/SwitcherSlot';
import { useSystemStateStore } from '../../store/systemStateStore';


const DOM_ABBREV: Record<string, string> = {
  BUYERS_DOMINANT: 'BULL', SELLERS_DOMINANT: 'BEAR', BALANCED: 'BAL',
  NO_SETUP: '—', NEUTRAL: '—',
};

export function FootprintPill({ isSelected = false, onSelect }: { isSelected?: boolean; onSelect?: () => void }) {
  const sysState = useSystemStateStore((s) => s.systems[3]);
  const label = sysState.state ? (DOM_ABBREV[sysState.state] ?? sysState.state.slice(0, 4).toUpperCase()) : '—';

  return (
    <SwitcherSlot
      systemId={3}
      
      isSelected={isSelected}
      stateLabel={label}
      onSelect={onSelect ? () => onSelect() : undefined}
    />
  );
}
