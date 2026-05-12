'use client';
import { SwitcherSlot } from '../molecules/SwitcherSlot';
import { useSystemStateStore } from '../../store/systemStateStore';
import type { PillState } from '../atoms/Pill';

interface DayTypePillProps {
  isSelected?: boolean;
  onSelect?: () => void;
}

const ABBREV: Record<string, string> = {
  UNKNOWN: 'UNKN', Trend_Normal: 'TREND', Trend_DD: 'TDD',
  Variation: 'VAR', Normal: 'NORM', Neutral: 'NEUT', Nontrend: 'NONT',
};

export function DayTypePill({ isSelected = false, onSelect }: DayTypePillProps) {
  const sysState = useSystemStateStore((s) => s.systems[1]);
  const label = sysState.state ? (ABBREV[sysState.state] ?? sysState.state.slice(0, 5)) : '—';

  return (
    <SwitcherSlot
      systemId={1}
      state={'idle' as PillState}
      isSelected={isSelected}
      stateLabel={label}
      onSelect={onSelect ? () => onSelect() : undefined}
    />
  );
}
