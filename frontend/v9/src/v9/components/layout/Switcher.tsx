'use client';
import { SwitcherSlot } from '../molecules/SwitcherSlot';
import { DayTypePill } from '../systems/DayTypePill';
import { FiveMinPill } from '../systems/FiveMinPill';
import { FootprintPill } from '../systems/FootprintPill';
import { WoodiesPill } from '../systems/WoodiesPill';
import { TPOPill } from '../systems/TPOPill';
import { KillzonePill } from '../systems/KillzonePill';
import { OBSERVING_SYSTEMS } from '../../design/system_colors';
import { COLORS } from '../../design/tokens';
import type { PillState } from '../atoms/Pill';

interface SwitcherProps {
  selectedSystem: number;
  onSelectSystem: (id: number) => void;
}

export function Switcher({ selectedSystem, onSelectSystem }: SwitcherProps) {
  return (
    <div style={{ padding: '6px 8px', display: 'flex', flexDirection: 'column', gap: 6 }}>
      {/* Firing row — S2/S3/S4 per Constitution V3 D-049 (T1/T3/T2) */}
      <div>
        <div style={{ fontSize: 7, color: COLORS.textDim, letterSpacing: '0.5px', marginBottom: 3, textTransform: 'uppercase' }}>
          Firing — entry decisions
        </div>
        <div style={{ display: 'flex', gap: 6, minHeight: 32 }}>
          <FiveMinPill isSelected={selectedSystem === 2} onSelect={() => onSelectSystem(2)} />
          <FootprintPill isSelected={selectedSystem === 3} onSelect={() => onSelectSystem(3)} />
          <WoodiesPill isSelected={selectedSystem === 4} onSelect={() => onSelectSystem(4)} />
        </div>
      </div>
      {/* Observing row — S1/S5/S6 per Constitution V3 D-049 */}
      <div>
        <div style={{ fontSize: 7, color: COLORS.textDim, letterSpacing: '0.5px', marginBottom: 3, textTransform: 'uppercase' }}>
          Observing — context
        </div>
        <div style={{ display: 'flex', gap: 6, minHeight: 28 }}>
          <DayTypePill isSelected={selectedSystem === 1} onSelect={() => onSelectSystem(1)} />
          <TPOPill isSelected={selectedSystem === 5} onSelect={() => onSelectSystem(5)} />
          <KillzonePill isSelected={selectedSystem === 6} onSelect={() => onSelectSystem(6)} />
        </div>
      </div>
    </div>
  );
}
