'use client';
import { useState, useEffect } from 'react';
import { useLayoutStore } from '../../stores/layoutStore';
import { fetchConfig, updateConfig } from '../../lib/api';
import { SYSTEM_COLORS, SYSTEM_NAMES, SYSTEM_BORDER_STYLE } from '../../types';
import type { SystemId, TradeMode } from '../../types';

export function SettingsDrawer() {
  const { settingsSystemId, closeSettings } = useLayoutStore();
  const systemId = settingsSystemId as SystemId;
  const [mode, setMode] = useState<TradeMode>('SHADOW');
  const [params, setParams] = useState<Record<string, any>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!systemId) return;
    fetchConfig(systemId, mode)
      .then((cfg) => setParams(cfg?.params || {}))
      .catch(() => setParams({}));
  }, [systemId, mode]);

  if (!systemId) return null;

  const color = SYSTEM_COLORS[systemId];
  const name = SYSTEM_NAMES[systemId];

  const handleSave = async () => {
    setSaving(true);
    try { await updateConfig(systemId, mode, params); } catch (err) { console.error('Failed to save:', err); }
    setSaving(false);
  };

  const handleParamChange = (key: string, value: any) => {
    setParams((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <>
      <div className="fixed inset-0 z-40" style={{ background: 'rgba(0,0,0,0.5)' }} onClick={closeSettings} />
      <div
        className="fixed right-0 top-0 bottom-0 z-50 w-[320px] flex flex-col border-l"
        style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b" style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ background: color }} />
            <span className="font-medium" style={{ color }}>System {systemId}: {name}</span>
          </div>
          <button onClick={closeSettings} className="text-lg hover:opacity-70" style={{ color: 'var(--text-secondary)' }}>
            \u00D7
          </button>
        </div>

        {/* Mode Toggle */}
        <div className="p-3 border-b" style={{ borderColor: 'var(--border)' }}>
          <div className="text-[11px] mb-2" style={{ color: 'var(--text-secondary)' }}>Trading Mode</div>
          <div className="flex gap-1">
            {(['SHADOW', 'SIM', 'LIVE'] as TradeMode[]).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className="flex-1 py-1.5 rounded text-xs font-medium"
                style={{
                  background: mode === m ? 'var(--bg-tertiary)' : 'transparent',
                  color: mode === m ? 'var(--text-primary)' : 'var(--text-muted)',
                  border: SYSTEM_BORDER_STYLE[m] === 'none'
                    ? `1px solid ${mode === m ? color : 'var(--border)'}`
                    : `1px ${SYSTEM_BORDER_STYLE[m]} ${mode === m ? color : 'var(--border)'}`,
                }}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        {/* Parameters */}
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          <div className="text-[11px] mb-1" style={{ color: 'var(--text-secondary)' }}>Parameters ({mode})</div>
          {Object.entries(params).map(([key, value]) => (
            <div key={key} className="space-y-1">
              <label className="text-[10px] block" style={{ color: 'var(--text-muted)' }}>
                {key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
              </label>
              {typeof value === 'boolean' ? (
                <button
                  onClick={() => handleParamChange(key, !value)}
                  className="px-2 py-1 rounded text-xs"
                  style={{
                    background: value ? color : 'var(--bg-tertiary)',
                    color: value ? '#0d1117' : 'var(--text-secondary)',
                  }}
                >
                  {value ? 'ON' : 'OFF'}
                </button>
              ) : typeof value === 'number' ? (
                <div className="flex items-center gap-2">
                  <input
                    type="range"
                    min={0}
                    max={value > 1 ? value * 3 : 1}
                    step={value > 1 ? 1 : 0.01}
                    value={value}
                    onChange={(e) => handleParamChange(key, parseFloat(e.target.value))}
                    className="flex-1"
                    style={{ accentColor: color }}
                  />
                  <span className="text-xs font-mono w-12 text-right" style={{ color: 'var(--text-secondary)' }}>
                    {value > 1 ? value.toFixed(0) : value.toFixed(2)}
                  </span>
                </div>
              ) : (
                <input
                  type="text"
                  value={String(value)}
                  onChange={(e) => handleParamChange(key, e.target.value)}
                  className="w-full px-2 py-1 rounded text-xs border"
                  style={{ background: 'var(--bg-primary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}
                />
              )}
            </div>
          ))}
          {Object.keys(params).length === 0 && (
            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>No parameters configured for this mode.</div>
          )}
        </div>

        {/* Save */}
        <div className="p-3 border-t" style={{ borderColor: 'var(--border)' }}>
          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full py-2 rounded text-sm font-medium"
            style={{ background: color, color: '#0d1117', opacity: saving ? 0.5 : 1 }}
          >
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>
    </>
  );
}
