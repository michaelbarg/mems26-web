'use client';
import { SwitcherSlot } from '../molecules/SwitcherSlot';
import { useSystemStateStore } from '../../store/systemStateStore';
import type { PillState } from '../atoms/Pill';

const ABBREV: Record<string, string> = {
  NEUTRAL: 'NEUT', ZLC_BULL: 'ZLC+', ZLC_BEAR: 'ZLC-',
  TREND_BULL: 'TR+', TREND_BEAR: 'TR-',
  OB_ENTER: 'OB', OB_EXIT: 'OBx', OS_ENTER: 'OS', OS_EXIT: 'OSx',
  OVERBOUGHT: 'OB!', OVERSOLD: 'OS!',
  ZLR: 'ZLR', ZLR_BULL: 'ZLR+', ZLR_BEAR: 'ZLR-',
  TLB: 'TLB', TLB_BULL: 'TLB+', TLB_BEAR: 'TLB-',
  TT: 'TT', TT_BULL: 'TT+', TT_BEAR: 'TT-',
  GB100: 'GB', GHOST: 'GHO', FAMIR: 'FAM', HTLB: 'HTL', VEGAS: 'VEG',
};

export function WoodiesPill({ isSelected = false, onSelect }: { isSelected?: boolean; onSelect?: () => void }) {
  const sysState = useSystemStateStore((s) => s.systems[4]);
  const label = sysState.state ? (ABBREV[sysState.state] ?? sysState.state.slice(0, 4)) : '—';

  return (
    <SwitcherSlot
      systemId={4}
      state={'idle' as PillState}
      isSelected={isSelected}
      stateLabel={label}
      onSelect={onSelect ? () => onSelect() : undefined}
    />
  );
}
