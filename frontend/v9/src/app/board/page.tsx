// /board — the live task board + System 6 supervisor activity.
// Non-invasive standalone route: does NOT touch the trading dashboard.
// Both panels are client components; this page just composes them.

import { LiveLedgerPanel } from '../../v9/components/board/LiveLedgerPanel';
import { PagesPanel } from '../../v9/components/board/PagesPanel';
import { NewsCalendarPanel } from '../../v9/components/board/NewsCalendarPanel';
import { ProposedDiffsPanel } from '../../v9/components/board/ProposedDiffsPanel';
import { AccountStatePanel } from '../../v9/components/board/AccountStatePanel';
import { SierraLiveCheckPanel } from '../../v9/components/board/SierraLiveCheckPanel';
import { StatusBoardPanel } from '../../v9/components/board/StatusBoardPanel';
import { System6SupervisorPanel } from '../../v9/components/board/System6SupervisorPanel';

export const metadata = { title: 'MEMS26 — Board' };

export default function BoardPage() {
  return (
    <main style={{
      // globals.css locks html/body to overflow:hidden (for the dashboard) —
      // the board must scroll INTERNALLY (Michael 07-09: "אי אפשר לגלול")
      height: '100vh', overflowY: 'auto', background: 'var(--bg, #010409)', padding: 20,
      color: 'var(--text-secondary, #c9d1d9)',
    }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* למידה-v3: הצעות-כיול ממתינות לפסיקה — מוצג רק כשיש דיפים */}
        <ProposedDiffsPanel />
        {/* W1b: עמוד-חשבון-אמת — sierra_state.json (מייקל 07-25) */}
        <AccountStatePanel />
        {/* T1: בדיקת-אמת שהמערכת מזהה את סיירה (מייקל 07-14) */}
        <SierraLiveCheckPanel />
        {/* לוח-החדשות — חלון-NO_TRADE (מייקל 07-13) */}
        <NewsCalendarPanel />
        <LiveLedgerPanel />
        <div id="system6"><System6SupervisorPanel /></div>
        <div id="tasks"><StatusBoardPanel /></div>
        <PagesPanel />
      </div>
    </main>
  );
}
