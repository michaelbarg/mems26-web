/** MEMS26 System Colors — AP-DESIGN01: use these, never hardcode.
 *  Per Master Visual Reference V5 + Cockpit UX Spec V5.
 */

export type SystemType = 'FIRING' | 'OBSERVING';

export interface SystemMeta {
  id: number;
  name: string;
  color: string;
  type: SystemType;
}

export const SYSTEM_META: Record<number, SystemMeta> = {
  // Constitution V3 D-049: FIRING = S2(T1)/S3(T3)/S4(T2), OBSERVING = S1/S5/S6
  1: { id: 1, name: 'Day Type',    color: '#6366f1', type: 'OBSERVING' },
  2: { id: 2, name: '5-Min',       color: '#06b6d4', type: 'FIRING' },
  3: { id: 3, name: 'Footprint',   color: '#a855f7', type: 'FIRING' },
  4: { id: 4, name: 'Woodies',     color: '#f97316', type: 'FIRING' },
  5: { id: 5, name: 'TPO',         color: '#eab308', type: 'OBSERVING' },
  6: { id: 6, name: 'Killzone',    color: '#14b8a6', type: 'OBSERVING' },
} as const;

/** Firing systems: make entry decisions per V3 D-049 (row 1 in Switcher) */
export const FIRING_SYSTEMS = [2, 3, 4] as const;

/** Observing systems: provide context per V3 D-049 (row 2 in Switcher) */
export const OBSERVING_SYSTEMS = [1, 5, 6] as const;

/** Get system color by ID */
export function systemColor(id: number): string {
  return SYSTEM_META[id]?.color ?? '#888888';
}
