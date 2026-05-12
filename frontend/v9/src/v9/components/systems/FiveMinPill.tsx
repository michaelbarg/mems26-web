'use client';
import { SwitcherSlot } from '../molecules/SwitcherSlot';
import type { PillState } from '../atoms/Pill';

interface FiveMinPillProps {
  isSelected?: boolean;
  onSelect?: () => void;
}

export function FiveMinPill({ isSelected = false, onSelect }: FiveMinPillProps) {
  return (
    <SwitcherSlot
      systemId={2}
      state={'idle' as PillState}
      isSelected={isSelected}
      onSelect={onSelect ? () => onSelect() : undefined}
    />
  );
}
