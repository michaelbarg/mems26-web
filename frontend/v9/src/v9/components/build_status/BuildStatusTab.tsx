'use client';
/**
 * Build Status tab — unified with /build route (BuildTreeView).
 *
 * Previously a separate legacy view; now renders the same redesigned
 * BuildTreeView so there is ONE design, not two competing versions.
 */
import { BuildTreeView } from '../build_tree/BuildTreeView';
import { DayTypeConditionsTable } from './DayTypeConditionsTable';

export function BuildStatusTab() {
  // The live S1 day-type conditions table (NEW state-machine classifier) sits above the
  // existing S1–S6 build tree — one Build Status surface (Michael 2026-06-20).
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto' }}>
      <div style={{ padding: '10px 10px 0' }}>
        <DayTypeConditionsTable />
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <BuildTreeView />
      </div>
    </div>
  );
}
