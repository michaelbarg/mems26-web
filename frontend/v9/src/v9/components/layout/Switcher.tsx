'use client';
import { useState } from 'react';
import { SwitcherSlot } from '../molecules/SwitcherSlot';
import { FIRING_SYSTEMS, OBSERVING_SYSTEMS } from '../../design/system_colors';
import { COLORS } from '../../design/tokens';
import type { PillState } from '../atoms/Pill';

interface SwitcherProps {
  selectedSystem: number;
  onSelectSystem: (id: number) => void;
}

export function Switcher({ selectedSystem, onSelectSystem }: SwitcherProps) {
  return (
    <div style={{ padding: '6px 8px', display: 'flex', flexDirection: 'column', gap: 6 }}>
      {/* Firing row */}
      <div>
        <div style={{ fontSize: 7, color: COLORS.textDim, letterSpacing: '0.5px', marginBottom: 3, textTransform: 'uppercase' }}>
          Firing — entry decisions
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {FIRING_SYSTEMS.map((id) => (
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
      {/* Observing row */}
      <div>
        <div style={{ fontSize: 7, color: COLORS.textDim, letterSpacing: '0.5px', marginBottom: 3, textTransform: 'uppercase' }}>
          Observing — context
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {OBSERVING_SYSTEMS.map((id) => (
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
