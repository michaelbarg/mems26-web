// /board — the live task board + System 6 supervisor activity.
// Non-invasive standalone route: does NOT touch the trading dashboard.
// Both panels are client components; this page just composes them.

import { LiveLedgerPanel } from '../../v9/components/board/LiveLedgerPanel';
import { StatusBoardPanel } from '../../v9/components/board/StatusBoardPanel';
import { System6SupervisorPanel } from '../../v9/components/board/System6SupervisorPanel';

export const metadata = { title: 'MEMS26 — Board' };

export default function BoardPage() {
  return (
    <main style={{
      minHeight: '100vh', background: 'var(--bg, #010409)', padding: 20,
      color: 'var(--text-secondary, #c9d1d9)',
    }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <LiveLedgerPanel />
        <System6SupervisorPanel />
        <StatusBoardPanel />
      </div>
    </main>
  );
}
