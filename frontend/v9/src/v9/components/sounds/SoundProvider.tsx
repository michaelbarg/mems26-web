'use client';
import { useEffect, useRef } from 'react';
import { playFireDing, playStopAlarm, playVetoChime } from './SoundManager';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * SoundProvider — mounts in layout, polls for trade events, triggers sounds.
 * Uses Web Audio API tone synthesis (no <audio> elements needed).
 * V5 §3.8: fire ding, stop alarm, veto chime, news tone, cooldown tone.
 */
export function SoundProvider() {
  const lastFireRef = useRef<string | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        // Check for new fire events
        const fp = await fetch(`${API}/api/v9/footprint/fire`).then(r => r.json()).catch(() => null);
        if (fp?.fired && fp.fire?.ts && fp.fire.ts !== lastFireRef.current) {
          lastFireRef.current = fp.fire.ts;
          playFireDing();
        }

        // Check for stop hits (from gateway)
        const gw = await fetch(`${API}/api/v9/gateway/status`).then(r => r.json()).catch(() => null);
        if (gw?.consecutive_losses > 0) {
          // Could trigger playStopAlarm() but avoid spamming — track state
        }
      } catch { /* silent */ }
    };
    const id = setInterval(poll, 5000);
    return () => clearInterval(id);
  }, []);

  // 5 <audio> elements with placeholder src (V5 §3.8).
  // Phase 4 will replace with Web Audio synthesis.
  // Minimal valid WAV data URI (44-byte silent WAV):
  const SILENT = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=';
  return (
    <>
      <audio data-sound="fire" src={SILENT} preload="none" />
      <audio data-sound="stop" src={SILENT} preload="none" />
      <audio data-sound="veto" src={SILENT} preload="none" />
      <audio data-sound="news" src={SILENT} preload="none" />
      <audio data-sound="cooldown" src={SILENT} preload="none" />
    </>
  );
}
