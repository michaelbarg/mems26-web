'use client';
import { usePriceStream } from '../hooks/usePriceStream';

/**
 * Temporary debug panel — shows live price ticks from the Event Bus.
 * Displays in bottom-right corner. Remove after Prompt 1 verification.
 */
export function PriceDebugConsole() {
  const { connected, lastTick, tickCount } = usePriceStream();

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 16,
        right: 16,
        width: 320,
        background: '#1a1a2e',
        border: `1px solid ${connected ? '#56d364' : '#f85149'}`,
        borderRadius: 8,
        padding: 12,
        fontFamily: 'monospace',
        fontSize: 12,
        color: '#e6edf3',
        zIndex: 9999,
        boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <span style={{ fontWeight: 'bold', color: '#58a6ff' }}>Event Bus Debug</span>
        <span style={{ color: connected ? '#56d364' : '#f85149' }}>
          {connected ? 'CONNECTED' : 'DISCONNECTED'}
        </span>
      </div>

      {lastTick ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#8b949e' }}>Price:</span>
            <span style={{ fontWeight: 'bold', fontSize: 14, color: '#f0f6fc' }}>
              {lastTick.price?.toFixed(2) ?? '—'}
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#8b949e' }}>Bid/Ask:</span>
            <span>
              {lastTick.bid?.toFixed(2) ?? '—'} / {lastTick.ask?.toFixed(2) ?? '—'}
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#8b949e' }}>Ticks:</span>
            <span>{tickCount}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#8b949e' }}>Corr ID:</span>
            <span style={{ color: '#8b949e' }}>{lastTick.correlation_id ?? '—'}</span>
          </div>
          <div style={{ marginTop: 4, color: '#484f58', fontSize: 10 }}>
            ts: {lastTick.ts_ms ? new Date(lastTick.ts_ms).toLocaleTimeString() : '—'}
          </div>
        </div>
      ) : (
        <div style={{ color: '#8b949e', textAlign: 'center', padding: 8 }}>
          Waiting for price ticks...
        </div>
      )}
    </div>
  );
}
