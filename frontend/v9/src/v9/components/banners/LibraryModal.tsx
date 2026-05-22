'use client';
import { useState } from 'react';
import { COLORS } from '../../design/tokens';

const TABS = ['Journal', 'Spec', 'Settings'] as const;
type LibTab = typeof TABS[number];

interface LibraryModalProps {
  onClose: () => void;
}

/**
 * Library modal — V5 §3.4.
 * Tabs: Journal / Spec / Settings.
 */
export function LibraryModal({ onClose }: LibraryModalProps) {
  const [tab, setTab] = useState<LibTab>('Journal');

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 999, display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.6)',
    }} onClick={onClose}>
      <div style={{
        background: COLORS.bgSurface3, border: `1px solid ${COLORS.borderSecondary}`,
        borderRadius: 8, padding: 0, maxWidth: 480, width: '90%', maxHeight: '70vh',
        overflow: 'hidden', display: 'flex', flexDirection: 'column',
      }} role="dialog" aria-modal="true" aria-label="Library" onClick={e => e.stopPropagation()}>
        {/* Tab bar */}
        <div style={{ display: 'flex', borderBottom: `1px solid ${COLORS.borderFaint}` }}>
          {TABS.map(t => (
            <button key={t} onClick={() => setTab(t)} style={{
              flex: 1, padding: '8px 0', fontSize: 12, fontWeight: tab === t ? 600 : 400,
              color: tab === t ? COLORS.textPrimary : COLORS.textTertiary,
              background: 'transparent', border: 'none', cursor: 'pointer',
              borderBottom: tab === t ? `2px solid ${COLORS.textPrimary}` : '2px solid transparent',
            }}>
              {t}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div style={{ padding: 16, overflow: 'auto', flex: 1 }}>
          {tab === 'Journal' && <JournalTab />}
          {tab === 'Spec' && <SpecTab />}
          {tab === 'Settings' && <SettingsTab />}
        </div>

        {/* Close button */}
        <div style={{ padding: '8px 16px', borderTop: `1px solid ${COLORS.borderFaint}`, textAlign: 'right' }}>
          <button onClick={onClose} style={{
            padding: '4px 16px', borderRadius: 4, border: `1px solid ${COLORS.borderSecondary}`,
            background: COLORS.bgSurface5, color: COLORS.textSecondary, cursor: 'pointer', fontSize: 12,
          }}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

function JournalTab() {
  return (
    <div style={{ color: COLORS.textTertiary, fontSize: 12, lineHeight: 1.6 }}>
      <div style={{ fontWeight: 600, color: COLORS.textSecondary, marginBottom: 8 }}>Trade Journal</div>
      <p>Recent trade log with per-contract PnL, cross-context snapshots, and reasoning notes.</p>
      <p style={{ marginTop: 8, color: COLORS.textDisabled, fontSize: 11 }}>
        Data populates after SHADOW trades accumulate. View full journal at /trades.
      </p>
    </div>
  );
}

function SpecTab() {
  return (
    <div style={{ color: COLORS.textTertiary, fontSize: 12, lineHeight: 1.6 }}>
      <div style={{ fontWeight: 600, color: COLORS.textSecondary, marginBottom: 8 }}>System Specifications</div>
      <div style={{ fontSize: 11 }}>
        <div style={{ marginBottom: 6 }}><strong style={{ color: COLORS.textSecondary }}>Constitution V3</strong> — 6 systems, 4 layers, trade management rules</div>
        <div style={{ marginBottom: 6 }}><strong style={{ color: COLORS.textSecondary }}>Cockpit V5</strong> — UI/UX spec, switcher, chart, side panel</div>
        <div style={{ marginBottom: 6 }}><strong style={{ color: COLORS.textSecondary }}>3-Mode Spec V3</strong> — SHADOW / DEMO / LIVE routing</div>
        <div><strong style={{ color: COLORS.textSecondary }}>Bootstrap</strong> — Deployment, DLL, Bridge configuration</div>
      </div>
    </div>
  );
}

function SettingsTab() {
  return (
    <div style={{ color: COLORS.textTertiary, fontSize: 12, lineHeight: 1.6 }}>
      <div style={{ fontWeight: 600, color: COLORS.textSecondary, marginBottom: 12 }}>Settings</div>
      <div style={{ fontSize: 10, color: COLORS.textDisabled, marginTop: 16 }}>
        Debug panel: Cmd+Shift+D (Mac) / Ctrl+Shift+D (Win)
      </div>
    </div>
  );
}
