'use client';
import { System1Panel } from './System1Panel';
import { System2Panel } from './System2Panel';
import { System3Panel } from './System3Panel';
import { System4Panel } from './System4Panel';
import { System5Panel } from './System5Panel';
import { System6Panel } from './System6Panel';

export function SystemPanelsBar() {
  return (
    <div
      className="flex border-t shrink-0 overflow-x-auto"
      style={{
        background: 'var(--bg-secondary)',
        borderColor: 'var(--border)',
        height: '120px',
        minHeight: '120px',
      }}
    >
      <System1Panel />
      <System2Panel />
      <System3Panel />
      <System4Panel />
      <System5Panel />
      <System6Panel />
    </div>
  );
}
