/* racers.js - small cartoon cars that zoom across the screen at random.
   Original characters: no faces on the cars, no real models, nothing from any film or show.
   Click one for a little surprise. */

const Racers = (() => {
  const front = document.getElementById('racers-front');   // bottom lanes, clickable
  const back = document.getElementById('racers-back');     // far away, behind the page content
  const COLORS = ['#ff5a4e', '#ffb703', '#2ec4b6', '#4cc9f0', '#9b5de5', '#ff4d9d', '#8ac926'];
  const HAIR = ['#2b2d42', '#ef233c', '#3a86ff', '#ffbe0b', '#8338ec', '#06d6a0'];
  const SHOUTS = ['Vroom!', 'Beep beep!', 'Catch me!', 'Zoom!', 'Wheee!', 'Too slow!'];
  const MAX_AT_ONCE = 4;

  let enabled = false;                  // off by default; the Racers button turns them on
  try {
    const saved = localStorage.getItem('roarwell-racers');
    if (saved) enabled = saved === 'on';
  } catch (e) { /* storage blocked: keep default */ }

  let active = 0;
  let timer = null;

  const pick = (list) => list[Math.floor(Math.random() * list.length)];
  const between = (lo, hi) => lo + Math.random() * (hi - lo);

  /* The little racing car, facing right. */
  function racerArt(color, hair, number) {
    return `<svg viewBox="0 0 130 64" class="racer-svg" aria-hidden="true" focusable="false">
      <g class="driver">
        <path class="scarf" d="M63 25 Q50 19 36 27 Q48 26 60 31 Z" fill="#fff" stroke="#141824" stroke-width="1.5" stroke-linejoin="round"/>
        <circle cx="71" cy="18" r="7" fill="#ffd9b8" stroke="#141824" stroke-width="2"/>
        <path d="M63 17 L65 8 L69 14 L73 6 L76 13 L81 10 L79 18 Z" fill="${hair}" stroke="#141824" stroke-width="1.5" stroke-linejoin="round"/>
      </g>
      <path d="M6 34 L6 25 L24 25 L24 31" fill="${color}" stroke="#141824" stroke-width="2.5" stroke-linejoin="round"/>
      <path d="M6 48 L9 37 Q11 32 22 31 L46 29 Q56 23 72 25 L90 27 Q100 29 106 34 L116 37 Q123 39 123 45 L123 48 Z"
            fill="${color}" stroke="#141824" stroke-width="2.5" stroke-linejoin="round"/>
      <path d="M12 41 L118 41" stroke="#fff" stroke-opacity=".75" stroke-width="3"/>
      <path d="M89 27 L101 31 L91 31 Z" fill="#bfe9ff" stroke="#141824" stroke-width="1.5" stroke-linejoin="round"/>
      <circle cx="50" cy="38" r="6" fill="#fff" stroke="#141824" stroke-width="1.5"/>
      <text x="50" y="41" text-anchor="middle" font-size="8" font-weight="800" fill="#141824" font-family="system-ui,sans-serif">${number}</text>
      <ellipse cx="119" cy="41" rx="3.5" ry="2.5" fill="#fff3b0" stroke="#141824" stroke-width="1"/>
      <g class="wheel"><circle cx="30" cy="49" r="9.5" fill="#141824"/><circle cx="30" cy="49" r="5" fill="#cfd6e4"/><path d="M30 44 V54 M25 49 H35" stroke="#141824" stroke-width="1.5"/></g>
      <g class="wheel"><circle cx="98" cy="49" r="9.5" fill="#141824"/><circle cx="98" cy="49" r="5" fill="#cfd6e4"/><path d="M98 44 V54 M93 49 H103" stroke="#141824" stroke-width="1.5"/></g>
      <path d="M110 22 l1.5 -4.5 l1.5 4.5 l4.5 1.5 l-4.5 1.5 l-1.5 4.5 l-1.5 -4.5 l-4.5 -1.5z" fill="#fff" opacity=".9" class="twinkle"/>
    </svg>`;
  }

  function cleanup(el) {
    el.remove();
    active = Math.max(0, active - 1);
  }

  /* Send one car across the screen. */
  function spawn({ far = false, dir = Math.random() < 0.5 ? 1 : -1, lane = null, duration = null, delay = 0 } = {}) {
    const layer = far ? back : front;
    const width = far ? 54 : 96;
    const el = document.createElement('div');
    el.className = 'racer' + (far ? ' far' : '');
    el.style.width = width + 'px';
    if (far) {
      el.style.top = Math.round(between(0.12, 0.6) * window.innerHeight) + 'px';
    } else {
      el.style.bottom = (lane ?? pick([4, 30, 56])) + 'px';
    }
    el.innerHTML = `<div class="racer-flip" style="transform:scaleX(${dir})">
        <div class="racer-bob">${racerArt(pick(COLORS), pick(HAIR), 1 + Math.floor(Math.random() * 99))}</div>
        <div class="speed-lines"></div>
      </div>`;
    layer.appendChild(el);
    active += 1;

    const vw = window.innerWidth;
    const from = dir === 1 ? -width - 60 : vw + 60;
    const to = dir === 1 ? vw + 60 : -width - 60;
    const ms = duration ?? between(far ? 9000 : 5500, far ? 15000 : 9500);
    const run = el.animate(
      [{ transform: `translateX(${from}px)` }, { transform: `translateX(${to}px)` }],
      { duration: ms, delay, easing: 'linear', fill: 'both' }
    );
    run.onfinish = () => cleanup(el);

    if (!far) {
      el.addEventListener('click', () => {
        Sound.honk();
        const bubble = document.createElement('span');
        bubble.className = 'bubble';
        bubble.textContent = pick(SHOUTS);
        el.appendChild(bubble);
        setTimeout(() => bubble.remove(), 900);
        const hop = el.querySelector('.racer-bob');
        hop.animate(
          [{ transform: 'translateY(0) rotate(0)' }, { transform: 'translateY(-34px) rotate(-10deg)' }, { transform: 'translateY(0) rotate(0)' }],
          { duration: 520, easing: 'ease-out' }
        );
        run.playbackRate = 1.8;                       // zooms off faster after a click
        setTimeout(() => { run.playbackRate = 1; }, 1500);
      });
    }
  }

  /* Two cars racing side by side, one slightly faster. */
  function race() {
    const dir = Math.random() < 0.5 ? 1 : -1;
    const slow = between(6500, 8500);
    spawn({ dir, lane: 4, duration: slow });
    spawn({ dir, lane: 30, duration: slow * 0.82, delay: between(150, 500) });
  }

  function schedule() {
    clearTimeout(timer);
    if (!enabled) return;
    timer = setTimeout(() => {
      if (!document.hidden && active < MAX_AT_ONCE) {
        const roll = Math.random();
        if (roll < 0.55) spawn();
        else if (roll < 0.8) spawn({ far: true });
        else if (active <= MAX_AT_ONCE - 2) race();
      }
      schedule();
    }, between(1800, 4200));
  }

  function clearAll() {
    front.innerHTML = '';
    back.innerHTML = '';
    active = 0;
  }

  return {
    get enabled() { return enabled; },
    start() { if (enabled) { spawn(); schedule(); } },
    setEnabled(on) {
      enabled = on;
      try { localStorage.setItem('roarwell-racers', on ? 'on' : 'off'); } catch (e) { /* ignore */ }
      if (on) { spawn(); schedule(); } else { clearTimeout(timer); clearAll(); }
    },
  };
})();
