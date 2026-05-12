'use client';
import { SwitcherSlot } from '../molecules/SwitcherSlot';
import { DayTypePill } from '../systems/DayTypePill';
import { FiveMinPill } from '../systems/FiveMinPill';
import { FootprintPill } from '../systems/FootprintPill';
import { WoodiesPill } from '../systems/WoodiesPill';
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
      {/* Firing row — Systems 1, 2, 4 */}
      <div>
        <div style={{ fontSize: 7, color: COLORS.textDim, letterSpacing: '0.5px', marginBottom: 3, textTransform: 'uppercase' }}>
          Firing — entry decisions
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <DayTypePill isSelected={selectedSystem === 1} onSelect={() => onSelectSystem(1)} />
          <FiveMinPill isSelected={selectedSystem === 2} onSelect={() => onSelectSystem(2)} />
          <WoodiesPill isSelected={selectedSystem === 4} onSelect={() => onSelectSystem(4)} />
        </div>
      </div>
      {/* Observing row */}
      <div>
        <div style={{ fontSize: 7, color: COLORS.textDim, letterSpacing: '0.5px', marginBottom: 3, textTransform: 'uppercase' }}>
          Observing — context
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <FootprintPill isSelected={selectedSystem === 3} onSelect={() => onSelectSystem(3)} />
          {OBSERVING_SYSTEMS.filter(id => id !== 3).map((id) => (
            <SwitcherSlot
              key={id}
              systemId={id}
              state={'idle' as PillState}
              isSelected={selectedSystem === id}
              onSelect={() => onSelectSystem(id)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
