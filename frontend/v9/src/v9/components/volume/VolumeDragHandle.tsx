'use client';
import { useState, useCallback, useEffect } from 'react';
import { COLORS } from '../../design/tokens';

const LS_KEY = 'mems26:volume:height';
const MIN_H = 20;
const MAX_H = 120;
const DEFAULT_H = 48;

interface VolumeDragHandleProps {
  onHeightChange: (h: number) => void;
}

/**
 * 3-dot grip handle at top edge of volume strip.
 * Drag to resize volume panel height (20-120px).
 * Persists last height in localStorage (V5 Q2).
 */
export function VolumeDragHandle({ onHeightChange }: VolumeDragHandleProps) {
  const [dragging, setDragging] = useState(false);
  const [startY, setStartY] = useState(0);
  const [startH, setStartH] = useState(DEFAULT_H);

  // Hydrate from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem(LS_KEY);
    if (saved) {
      const h = Math.max(MIN_H, Math.min(MAX_H, parseInt(saved, 10)));
      onHeightChange(h);
    }
  }, [onHeightChange]);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setDragging(true);
    setStartY(e.clientY);
    const saved = localStorage.getItem(LS_KEY);
    setStartH(saved ? parseInt(saved, 10) : DEFAULT_H);
  }, []);

  useEffect(() => {
    if (!dragging) return;
    const onMove = (e: MouseEvent) => {
      const dy = startY - e.clientY; // up = bigger
      const newH = Math.max(MIN_H, Math.min(MAX_H, startH + dy));
      onHeightChange(newH);
      localStorage.setItem(LS_KEY, String(newH));
    };
    const onUp = () => setDragging(false);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [dragging, startY, startH, onHeightChange]);

  return (
    <div
      onMouseDown={onMouseDown}
      style={{
        height: 6,
        cursor: 'ns-resize',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: COLORS.bgSurface3,
        borderTop: `1px solid ${COLORS.borderFaint}`,
        userSelect: 'none',
      }}
    >
      {/* 3-dot grip */}
      <div style={{ display: 'flex', gap: 3 }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            width: 3, height: 3, borderRadius: '50%',
            background: COLORS.textDisabled,
          }} />
        ))}
      </div>
    </div>
  );
}
