'use client';
import { useEffect, useState } from 'react';

const API_URL = 'https://mems26-web.onrender.com';

interface VersionData {
  web: { version: string };
  bridge: { version: string; heartbeat_age_sec: number; status: string };
  dll: { version: string; built_at: string };
  changelog: { version: string; date: string; scope: string; items: string[] }[];
  mismatch: boolean;
  warnings: string[];
}

export default function VersionModal({ onClose }: { onClose: () => void }) {
  const [data, setData] = useState<VersionData | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/versions`).then(r => r.json()).then(setData).catch(() => {});
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  if (!data) return (
    <div style={overlay} onClick={onClose}>
      <div style={modal} onClick={e => e.stopPropagation()}>
        <div style={{ padding: 32, textAlign: 'center', color: '#4a5568' }}>Loading...</div>
      </div>
    </div>
  );

  const statusDot = (s: string) => s === 'online' ? '#22c55e' : '#ef5350';

  return (
    <div style={overlay} onClick={onClose}>
      <div style={modal} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <span style={{ fontSize: 14, fontWeight: 800, color: '#e2e8f0' }}>MEMS26 System Versions</span>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#6b7280', fontSize: 18, cursor: 'pointer' }}>X</button>
        </div>

        {data.mismatch && (
          <div style={{ background: '#7f1d1d', border: '1px solid #ef5350', borderRadius: 6, padding: '8px 12px', marginBottom: 12, fontSize: 11, color: '#fca5a5' }}>
            {data.warnings.join(' | ')}
          </div>
        )}

        <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 16, fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #1e2738', color: '#4a5568' }}>
              <th style={{ textAlign: 'left', padding: '6px 8px' }}>Component</th>
              <th style={{ textAlign: 'left', padding: '6px 8px' }}>Version</th>
              <th style={{ textAlign: 'left', padding: '6px 8px' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: '1px solid #111827' }}>
              <td style={cell}>Web (Netlify)</td>
              <td style={{ ...cell, fontFamily: 'monospace', color: '#e2e8f0' }}>{data.web.version}</td>
              <td style={cell}><span style={{ color: '#22c55e' }}>deployed</span></td>
            </tr>
            <tr style={{ borderBottom: '1px solid #111827' }}>
              <td style={cell}>Bridge (Local)</td>
              <td style={{ ...cell, fontFamily: 'monospace', color: '#e2e8f0' }}>{data.bridge.version}</td>
              <td style={cell}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: statusDot(data.bridge.status), display: 'inline-block', marginRight: 4 }} />
                {data.bridge.status} ({data.bridge.heartbeat_age_sec}s)
              </td>
            </tr>
            <tr>
              <td style={cell}>DLL (Sierra)</td>
              <td style={{ ...cell, fontFamily: 'monospace', color: '#e2e8f0' }}>{data.dll.version}</td>
              <td style={cell}><span style={{ color: '#4a5568' }}>{data.dll.built_at}</span></td>
            </tr>
          </tbody>
        </table>

        <div style={{ fontSize: 11, fontWeight: 700, color: '#4a5568', marginBottom: 8 }}>CHANGELOG</div>
        <div style={{ maxHeight: '40vh', overflowY: 'auto' }}>
          {data.changelog.map(e => (
            <div key={e.version} style={{ marginBottom: 10, paddingBottom: 8, borderBottom: '1px solid #111827' }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 12, fontWeight: 800, color: '#e2e8f0', fontFamily: 'monospace' }}>{e.version}</span>
                <span style={{ fontSize: 10, color: '#4a5568' }}>{e.date}</span>
                <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, background: '#1e2738', color: '#94a3b8' }}>{e.scope}</span>
              </div>
              {e.items.map((it, i) => (
                <div key={i} style={{ fontSize: 11, color: '#94a3b8', paddingLeft: 12 }}>- {it}</div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const overlay: React.CSSProperties = {
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 10000,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
};
const modal: React.CSSProperties = {
  background: '#0f172a', border: '1px solid #1e2738', borderRadius: 10,
  padding: 20, width: 520, maxWidth: '90vw', maxHeight: '80vh', overflowY: 'auto',
};
const cell: React.CSSProperties = { padding: '6px 8px', color: '#94a3b8' };
