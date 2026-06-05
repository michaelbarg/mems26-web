'use client';
/**
 * Build Status tab — unified with /build route (BuildTreeView).
 *
 * Previously a separate legacy view; now renders the same redesigned
 * BuildTreeView so there is ONE design, not two competing versions.
 */
import { BuildTreeView } from '../build_tree/BuildTreeView';

export function BuildStatusTab() {
  return <BuildTreeView />;
}
