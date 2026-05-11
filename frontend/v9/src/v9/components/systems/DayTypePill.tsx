'use client';
import { SwitcherSlot } from '../molecules/SwitcherSlot';
import type { PillState } from '../atoms/Pill';

interface DayTypePillProps {
  isSelected?: boolean;
  onSelect?: () => void;
}

export function DayTypePill({ isSelected = false, onSelect }: DayTypePillProps) {
  return (
    <SwitcherSlot
      systemId={1}
      state={'idle' as PillState}
      isSelected={isSelected}
      onSelect={onSelect ? () => onSelect() : undefined}
    />
  );
}
