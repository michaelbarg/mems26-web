/**
 * SoundManager — V5 §3.8 notification sounds.
 *
 * Uses Web Audio API tone synthesis (no external files needed).
 * 5 events: fire ding, stop alarm, veto chime, news tone, cooldown.
 * User settings: mute + volume persisted in localStorage.
 */

const LS_MUTE_KEY = 'mems26:sound:muted';
const LS_VOL_KEY = 'mems26:sound:volume';

let audioCtx: AudioContext | null = null;

function getCtx(): AudioContext {
  if (!audioCtx) {
    audioCtx = new AudioContext();
  }
  return audioCtx;
}

function isMuted(): boolean {
  if (typeof window === 'undefined') return true;
  return localStorage.getItem(LS_MUTE_KEY) === 'true';
}

function getVolume(): number {
  if (typeof window === 'undefined') return 0.5;
  const v = localStorage.getItem(LS_VOL_KEY);
  return v ? parseFloat(v) : 0.5;
}

function playTone(freq: number, duration: number, type: OscillatorType = 'sine') {
  if (isMuted()) return;
  try {
    const ctx = getCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    gain.gain.value = getVolume() * 0.3;
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + duration);
  } catch { /* AudioContext not available */ }
}

/** Soft ding on pattern fire (V5 §3.8) */
export function playFireDing() {
  playTone(880, 0.15, 'sine');
  setTimeout(() => playTone(1108, 0.12, 'sine'), 80);
}

/** Alarm on stop hit (V5 §3.8) */
export function playStopAlarm() {
  playTone(440, 0.2, 'square');
  setTimeout(() => playTone(330, 0.3, 'square'), 150);
}

/** Chime on veto (V5 §3.8) */
export function playVetoChime() {
  playTone(660, 0.1, 'triangle');
  setTimeout(() => playTone(550, 0.1, 'triangle'), 100);
  setTimeout(() => playTone(440, 0.15, 'triangle'), 200);
}

/** Low tone on news window (V5 §3.8) */
export function playNewsTone() {
  playTone(220, 0.4, 'sine');
}

/** Ascending tone on cooldown (V5 §3.8) */
export function playCooldownTone() {
  playTone(330, 0.1, 'sine');
  setTimeout(() => playTone(440, 0.1, 'sine'), 100);
  setTimeout(() => playTone(550, 0.15, 'sine'), 200);
}

/** Set mute state */
export function setMuted(muted: boolean) {
  localStorage.setItem(LS_MUTE_KEY, String(muted));
}

/** Set volume (0.0-1.0) */
export function setVolume(vol: number) {
  localStorage.setItem(LS_VOL_KEY, String(Math.max(0, Math.min(1, vol))));
}

/** Get current settings */
export function getSoundSettings() {
  return { muted: isMuted(), volume: getVolume() };
}
