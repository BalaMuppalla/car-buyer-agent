/* sound.js - tiny sound effects made with the browser's built-in sound tools.
   Nothing is downloaded, so there are no licences to worry about.
   Browsers only allow sound after the visitor clicks something, which is fine
   because every sound here is triggered by a click. */

const Sound = (() => {
  let ctx = null;
  let enabled = true;
  try { enabled = localStorage.getItem('roarwell-sound') !== 'off'; } catch (e) { /* storage blocked: keep default */ }

  function context() {
    if (!ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return null;
      ctx = new AudioCtx();
    }
    if (ctx.state === 'suspended') ctx.resume();
    return ctx;
  }

  /* One short beep: pitch (Hz), when to start (seconds from now), how long, wave shape, loudness */
  function tone(freq, start, dur, type = 'square', vol = 0.05, slideTo = null) {
    const c = context();
    if (!c || !enabled) return;
    const osc = c.createOscillator();
    const gain = c.createGain();
    const t0 = c.currentTime + start;
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    if (slideTo) osc.frequency.exponentialRampToValueAtTime(slideTo, t0 + dur);
    gain.gain.setValueAtTime(vol, t0);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    osc.connect(gain).connect(c.destination);
    osc.start(t0);
    osc.stop(t0 + dur + 0.02);
  }

  /* ----- bigger sounds for the intro, all made from simple waves and noise ----- */
  function noiseBuffer(c, seconds) {
    const buf = c.createBuffer(1, Math.floor(c.sampleRate * seconds), c.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    return buf;
  }
  /* A burst of noise through a filter: type = 'lowpass' | 'highpass' | 'bandpass' */
  function noise(start, dur, type, f0, f1, vol) {
    const c = context();
    if (!c || !enabled) return;
    const src = c.createBufferSource(), filt = c.createBiquadFilter(), gain = c.createGain();
    const t0 = c.currentTime + start;
    src.buffer = noiseBuffer(c, dur + 0.1);
    filt.type = type;
    filt.frequency.setValueAtTime(f0, t0);
    filt.frequency.exponentialRampToValueAtTime(f1, t0 + dur);
    gain.gain.setValueAtTime(0.0001, t0);
    gain.gain.exponentialRampToValueAtTime(vol, t0 + Math.min(0.08, dur / 3));
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    src.connect(filt).connect(gain).connect(c.destination);
    src.start(t0);
    src.stop(t0 + dur + 0.1);
  }
  /* A rumbling engine-like tone: pitch glides f0 -> f1, wobbles at 'wobble' Hz */
  function rumble(start, dur, f0, f1, wobble, vol, cutoff = 500) {
    const c = context();
    if (!c || !enabled) return;
    const t0 = c.currentTime + start;
    const gain = c.createGain(), filt = c.createBiquadFilter(), lfo = c.createOscillator(), lfoGain = c.createGain();
    filt.type = 'lowpass';
    filt.frequency.setValueAtTime(cutoff, t0);
    filt.frequency.exponentialRampToValueAtTime(cutoff * 2.2, t0 + dur);
    gain.gain.setValueAtTime(0.0001, t0);
    gain.gain.exponentialRampToValueAtTime(vol, t0 + Math.min(0.3, dur / 3));
    gain.gain.setValueAtTime(vol, t0 + dur * 0.7);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    lfo.frequency.value = wobble;
    lfoGain.gain.value = vol * 0.6;
    lfo.connect(lfoGain).connect(gain.gain);               // the wobble makes it growl
    [1, 1.01, 0.5].forEach((mult) => {
      const o = c.createOscillator();
      o.type = 'sawtooth';
      o.frequency.setValueAtTime(f0 * mult, t0);
      o.frequency.exponentialRampToValueAtTime(f1 * mult, t0 + dur);
      o.connect(filt);
      o.start(t0); o.stop(t0 + dur + 0.05);
    });
    filt.connect(gain).connect(c.destination);
    lfo.start(t0); lfo.stop(t0 + dur + 0.05);
  }

  return {
    get enabled() { return enabled; },
    set(on) {
      enabled = on;
      try { localStorage.setItem('roarwell-sound', on ? 'on' : 'off'); } catch (e) { /* ignore */ }
    },
    /* Beep beep! (little racing car clicked) */
    honk() { tone(440, 0, 0.12); tone(554, 0.14, 0.14); },
    /* A soft pop (saving a car) */
    pop() { tone(520, 0, 0.09, 'sine', 0.06, 880); },
    /* Low animal growl: a slow rumble with a fast wobble, plus a rough breath of noise */
    growl(start = 0) {
      rumble(start, 2.4, 55, 85, 24, 0.22, 420);
      noise(start, 2.2, 'bandpass', 300, 900, 0.07);
    },
    /* Engine revving up */
    rev(start = 0, dur = 1.8) {
      rumble(start, dur, 70, 330, 38, 0.2, 700);
      noise(start, dur, 'lowpass', 400, 2200, 0.05);
    },
    /* Glass breaking: a crack, a crunch, and lots of tiny tinkles */
    shatter(start = 0) {
      noise(start, 0.35, 'highpass', 2500, 6000, 0.35);
      noise(start, 0.9, 'bandpass', 3500, 1800, 0.18);
      for (let i = 0; i < 26; i++) tone(2200 + Math.random() * 4500, start + 0.05 + Math.random() * 1.1, 0.12, 'sine', 0.035);
      rumble(start, 0.7, 90, 40, 12, 0.25, 300);
    },
    /* Tyres skidding */
    skid(start = 0) {
      noise(start, 1.1, 'bandpass', 1800, 900, 0.16);
      tone(1100, start, 1.0, 'sawtooth', 0.025, 700);
    },
    /* Pressing the start button: starter motor, the engine catches, then idles */
    ignition(start = 0) {
      tone(95, start, 0.9, 'square', 0.05, 150);
      noise(start, 0.9, 'bandpass', 600, 900, 0.05);
      rumble(start + 0.85, 0.5, 60, 140, 30, 0.3, 700);     // it catches with a bark
      rumble(start + 1.3, 2.2, 45, 48, 14, 0.2, 380);       // settles into an idle
    },
    /* A cheerful rising chime (choosing a car) */
    ding() { [523, 659, 784, 1047].forEach((f, i) => tone(f, i * 0.09, 0.22, 'triangle', 0.06)); },
  };
})();
