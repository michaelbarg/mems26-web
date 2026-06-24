'use client';
import { SwitcherSlot } from '../molecules/SwitcherSlot';
import { useSystemStateStore } from '../../store/systemStateStore';
import { useLiveDayType } from '../../hooks/useLiveDayType';


interface DayTypePillProps {
  isSelected?: boolean;
  onSelect?: () => void;
}

const ABBREV: Record<string, string> = {
  UNKNOWN: 'UNKN', FORMING: 'FORM', Trend_Normal: 'TREND', Trend_DD: 'TDD',
  Variation: 'VAR', Normal_Variation: 'VAR', Normal: 'NORM',
  Neutral: 'NEUT', Neutral_Center: 'NEUC', Neutral_Extreme: 'NEUX', Nontrend: 'NONT',
};

export function DayTypePill({ isSelected = false, onSelect }: DayTypePillProps) {
  // Prefer the NEW validated state-machine classifier (live shadow); fall back to the old live
  // engine's store value only when the classify endpoint is offline (Michael 2026-06-20).
  const live = useLiveDayType();
  const sysState = useSystemStateStore((s) => s.systems[1]);
  const state = live?.day_type || sysState.state;
  const label = state ? (ABBREV[state] ?? state.slice(0, 5)) : '—';

  return (
    <SwitcherSlot
      systemId={1}
      
      isSelected={isSelected}
      stateLabel={label}
      onSelect={onSelect ? () => onSelect() : undefined}
    />
  );
}
