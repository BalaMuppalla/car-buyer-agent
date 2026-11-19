/* intro.js - the opening movie.
   Dark screen -> two glowing headlight "eyes" -> a growl -> the car charges the glass -> it shatters ->
   sunrise on a beach road with cars parked at the side -> the car skids in -> engine start button -> the website.
   Plays once per visit. Add ?intro=1 to the address (or use "Replay intro" at the bottom) to see it again. */

(() => {
  const root = document.getElementById('intro');
  const params = new URLSearchParams(location.search);
  const seen = (() => { try { return sessionStorage.getItem('roarwell-intro-seen') === '1'; } catch (e) { return false; } })();
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const force = params.get('intro') === '1';
  const skipIntro = params.get('intro') === '0';

  let timers = [];
  let animations = [];
  let finished = false;

  const at = (ms, fn) => { timers.push(setTimeout(fn, ms)); };
  const el = (cls, html = '', tag = 'div') => {
    const e = document.createElement(tag);
    e.className = cls;
    e.innerHTML = html;
    return e;
  };
  const anim = (node, frames, opts) => {
    const a = node.animate(frames, { fill: 'forwards', ...opts });
    animations.push(a);
    return a;
  };
  const rand = (lo, hi) => lo + Math.random() * (hi - lo);

  function finish() {
    if (finished) return;
    finished = true;
    timers.forEach(clearTimeout);
    try { window.Intro3D && Intro3D.stop && Intro3D.stop(); } catch (e) { /* ignore */ }
    animations.forEach((a) => { try { a.cancel(); } catch (e) { /* already done */ } });
    try { sessionStorage.setItem('roarwell-intro-seen', '1'); } catch (e) { /* ignore */ }
    root.style.transition = 'opacity .7s';
    root.style.opacity = '0';
    setTimeout(() => {
      root.hidden = true;
      root.innerHTML = '';
      root.style.opacity = '';
      root.style.transition = '';
      document.documentElement.classList.remove('intro-on');
      document.dispatchEvent(new Event('roarwell-intro-done'));
    }, 700);
  }

  /* The two glowing eyes: sharp, slanted, golden. */
  function eyesSVG() {
    const left = '80,175 260,120 430,205 405,255 205,238';
    const right = '920,175 740,120 570,205 595,255 795,238';
    const core = (pts, flip) => `<polygon points="${pts}" fill="url(#eyeFill)"/>`;
    return `<svg viewBox="0 0 1000 380" aria-hidden="true">
      <defs>
        <radialGradient id="eyeFill" cx="50%" cy="55%" r="60%"><stop offset="0" stop-color="#fffbe6"/><stop offset=".45" stop-color="#ffd36b"/><stop offset="1" stop-color="#ff7a1a"/></radialGradient>
        <radialGradient id="hood" cx="50%" cy="0%" r="70%"><stop offset="0" stop-color="#ff9a3c" stop-opacity=".28"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
        <filter id="blurBig" x="-30%" y="-80%" width="160%" height="260%"><feGaussianBlur stdDeviation="26"/></filter>
        <filter id="blurSm" x="-30%" y="-80%" width="160%" height="260%"><feGaussianBlur stdDeviation="7"/></filter>
      </defs>
      <ellipse cx="500" cy="330" rx="470" ry="70" fill="url(#hood)"/>
      <g filter="url(#blurBig)" opacity=".85"><polygon points="${left}" fill="#ff8a2a"/><polygon points="${right}" fill="#ff8a2a"/></g>
      <g filter="url(#blurSm)" opacity=".9"><polygon points="${left}" fill="#ffc15a"/><polygon points="${right}" fill="#ffc15a"/></g>
      ${core(left)}${core(right)}
      <path d="M130 270 L395 292 M870 270 L605 292" stroke="#ffe7a3" stroke-width="5" stroke-linecap="round" opacity=".8"/>
    </svg>`;
  }

  /* Cracked glass: pie-slice triangles around the point where the car hits. */
  function buildGlass(W, H) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'glass');
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.setAttribute('preserveAspectRatio', 'none');
    const cx = W / 2, cy = H * 0.46, D = Math.hypot(W, H);
    const radii = [0, 0.07, 0.17, 0.33, 0.6, 1.2];
    const N = 18;
    const rings = radii.map((r, ri) => Array.from({ length: N }, (_, i) => {
      const ang = ((i + (ri ? rand(-0.3, 0.3) : 0)) / N) * Math.PI * 2;
      const rr = r * D * (ri ? rand(0.85, 1.15) : 1);
      return [cx + Math.cos(ang) * rr, cy + Math.sin(ang) * rr];
    }));
    const shards = [];
    const add = (pts) => {
      const p = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
      p.setAttribute('points', pts.map((q) => q.map((n) => n.toFixed(1)).join(',')).join(' '));
      svg.appendChild(p);
      const mx = pts.reduce((s, q) => s + q[0], 0) / pts.length, my = pts.reduce((s, q) => s + q[1], 0) / pts.length;
      shards.push({ node: p, dx: mx - cx, dy: my - cy, dist: Math.hypot(mx - cx, my - cy) });
    };
    for (let ri = 0; ri < radii.length - 1; ri++) {
      for (let i = 0; i < N; i++) {
        const j = (i + 1) % N;
        if (ri === 0) add([[cx, cy], rings[1][i], rings[1][j]]);
        else {
          add([rings[ri][i], rings[ri + 1][i], rings[ri + 1][j]]);
          add([rings[ri][i], rings[ri + 1][j], rings[ri][j]]);
        }
      }
    }
    return { svg, shards, D };
  }

  function play2D(withSound) {
    const W = window.innerWidth, H = window.innerHeight;
    const S = (name, ...args) => { if (withSound && Sound.enabled) Sound[name](...args); };
    root.innerHTML = '';

    /* --- scene (bottom layer) --- */
    const scene = el('scene');
    scene.append(el('sky'), el('sun'));
    [[12, 18, 24], [26, 30, 16], [52, 14, 30], [72, 24, 20], [88, 34, 14]].forEach(([l, t, w]) => {
      const c = el('cloud'); c.style.left = l + '%'; c.style.top = t + '%'; c.style.width = w + '%'; scene.appendChild(c);
    });
    scene.append(el('sea'), el('sand'), el('road'));
    const types = ['suv', 'sedan', 'coupe', 'suv', 'coupe', 'sedan', 'suv', 'coupe', 'sedan', 'suv'];
    const colors = ['#4f7cff', '#e9e9ef', '#2ec4b6', '#ffb703', '#9b5de5', '#ff4d6d', '#8ac926', '#4cc9f0', '#ff7a1a', '#c9c9d4'];
    types.forEach((t, i) => {
      const p = el('parked', sleekCar(colors[i], t));
      p.style.left = (2 + i * 10) + '%';
      p.style.bottom = (27.6 + (i % 2) * 1.2) + '%';
      scene.appendChild(p);
    });
    const hero = el('hero-car', sleekCar('#ff5a1f', 'coupe') + '<div class="beam"></div><div class="lines"></div>');
    scene.appendChild(hero);
    root.appendChild(scene);
    const heroW = hero.getBoundingClientRect().width || Math.min(Math.max(240, W * 0.38), 600);
    const finalX = W / 2 - heroW / 2;
    hero.style.transform = `translateX(${-heroW - 80}px)`;

    /* --- dark glass + eyes (top layers) --- */
    const { svg: glass, shards } = buildGlass(W, H);
    root.appendChild(glass);
    const eyes = el('eyes', eyesSVG());
    root.appendChild(eyes);
    const flash = el('flash');
    root.appendChild(flash);

    /* --- start button + welcome words --- */
    const wrap = el('start-wrap', '<p>Press to start the engine</p><button class="engine-btn" aria-label="Engine start"><span>Engine<br>Start<br>Stop</span></button>');
    const welcome = el('welcome', 'Welcome to Paradise.<br>Time to wake the beasts.');
    root.append(wrap, welcome);
    const button = wrap.querySelector('button');

    const skip = el('intro-skip', 'Skip intro', 'button');
    skip.type = 'button';
    skip.onclick = finish;
    root.appendChild(skip);

    /* --- the timeline (milliseconds from the click) --- */
    const eyeSvg = eyes.querySelector('svg');
    at(500, () => { anim(eyes, [{ opacity: 0 }, { opacity: 1 }], { duration: 1100, easing: 'ease-out' }); S('growl'); });
    at(1900, () => anim(eyeSvg, [{ transform: 'scaleY(1)' }, { transform: 'scaleY(.12)' }, { transform: 'scaleY(.8)' }], { duration: 380, easing: 'ease-in-out' }));
    at(2600, () => {
      S('rev', 0, 1.9);
      root.classList.add('shake');
      anim(eyeSvg, [{ transform: 'scale(.8)', filter: 'brightness(1)' }, { transform: 'scale(5.2)', filter: 'brightness(1.6)' }],
        { duration: 1900, easing: 'cubic-bezier(.6,0,.9,.5)' });
    });
    // impact: cracks appear
    at(4350, () => {
      S('shatter', 0);
      shards.forEach((s) => anim(s.node, [{ stroke: '#020304' }, { stroke: 'rgba(200,230,255,.9)' }], { duration: 120 }));
      anim(flash, [{ opacity: 0.9 }, { opacity: 0 }], { duration: 420 });
    });
    // glass falls away
    at(4650, () => {
      root.classList.remove('shake');
      eyes.style.display = 'none';
      shards.forEach((s) => {
        const push = 1 + 500 / (s.dist + 120);
        const dx = (s.dx / (s.dist || 1)) * rand(120, 420) * push * 0.5;
        const dy = rand(500, 1100) + (s.dy / (s.dist || 1)) * 140;
        const rot = rand(-260, 260);
        anim(s.node, [
          { transform: 'translate(0,0) rotate(0deg)', opacity: 1 },
          { transform: `translate(${dx * 0.6}px, ${dy * 0.12 - 40}px) rotate(${rot * 0.4}deg)`, opacity: 1, offset: 0.3 },
          { transform: `translate(${dx}px, ${dy}px) rotate(${rot}deg)`, opacity: 0.2 },
        ], { duration: rand(900, 1500), delay: (s.dist / 1800) * 260, easing: 'cubic-bezier(.4,0,.9,.6)' });
      });
    });
    at(6300, () => { glass.remove(); });
    // the car arrives and skids
    const x1 = finalX - W * 0.27;
    at(4800, () => {
      hero.classList.add('lit');
      hero.querySelector('.lines').style.opacity = '1';
      anim(hero, [
        { transform: `translateX(${-heroW - 80}px) rotate(0deg)`, easing: 'linear' },
        { transform: `translateX(${x1}px) rotate(0deg)`, offset: 0.4, easing: 'cubic-bezier(.12,.75,.3,1)' },
        { transform: `translateX(${finalX}px) rotate(1.6deg)`, offset: 0.8, easing: 'ease-out' },
        { transform: `translateX(${finalX}px) rotate(0deg)` },
      ], { duration: 2600 });
    });
    at(4800 + 2600 * 0.4, () => {
      S('skid');
      hero.querySelector('.lines').style.opacity = '0';
      const roadTop = H * 0.72, markY = H * (1 - 0.14) - heroW * 0.092;   // under the rear wheel, roughly
      const wheelX = x1 + heroW * 0.22;
      const mark = el('skid-mark');
      mark.style.cssText = `left:${wheelX}px; top:${H * 0.775}px; width:0`;
      scene.insertBefore(mark, hero);
      anim(mark, [{ width: '0px' }, { width: `${finalX - x1}px` }], { duration: 1000, easing: 'cubic-bezier(.15,.7,.25,1)' });
      for (let i = 0; i < 9; i++) {
        const puff = el('smoke');
        const size = rand(50, 120);
        puff.style.cssText = `width:${size}px;height:${size}px;left:${wheelX + i * 14}px;top:${H * 0.70}px;opacity:0`;
        scene.appendChild(puff);
        anim(puff, [
          { opacity: 0.8, transform: 'translate(0,0) scale(.4)' },
          { opacity: 0, transform: `translate(${rand(-60, 60)}px, ${rand(-110, -50)}px) scale(1.7)` },
        ], { duration: 1300, delay: i * 90 });
      }
    });
    // the start button
    at(7500, () => {
      wrap.classList.add('show');
      anim(wrap, [{ opacity: 0, transform: 'translateY(20px)' }, { opacity: 1, transform: 'none' }], { duration: 600, easing: 'ease-out' });
    });

    button.onclick = () => {
      button.onclick = null;
      button.classList.add('on');
      wrap.querySelector('p').textContent = 'Engine running';
      S('ignition');
      root.classList.add('shake');
      anim(hero, [{ transform: `translateX(${finalX}px) translateY(0)` }, { transform: `translateX(${finalX}px) translateY(-3px)` }, { transform: `translateX(${finalX}px) translateY(0)` }],
        { duration: 90, iterations: 28 });
      at(900, () => root.classList.remove('shake'));
      at(700, () => anim(welcome, [{ opacity: 0, transform: 'translateY(14px)' }, { opacity: 1, transform: 'none' }], { duration: 700, easing: 'ease-out' }));
      at(2900, () => {
        anim(scene, [{ transform: 'scale(1)', filter: 'brightness(1)' }, { transform: 'scale(1.35)', filter: 'brightness(2.2)' }], { duration: 800, easing: 'ease-in' });
      });
      at(3500, finish);
    };
  }

  /* Wait (briefly) for the 3D module to load; null if it never shows up. */
  function whenIntro3D(ms = 6000) {
    return new Promise((resolve) => {
      const t0 = Date.now();
      (function poll() {
        if (window.Intro3D) return resolve(window.Intro3D);
        if (Date.now() - t0 > ms) return resolve(null);
        setTimeout(poll, 100);
      })();
    });
  }

  /* Try the 3D movie first; if anything is missing, play the simpler 2D one. */
  async function startShow(withSound) {
    root.innerHTML = '<div class="gate"><div class="brand">Roarwell Motors</div><h2>Warming up the engine...</h2></div>';
    const skip = el('intro-skip', 'Skip intro', 'button');
    skip.type = 'button'; skip.onclick = finish;
    root.appendChild(skip);
    const I3 = await whenIntro3D();
    let ok = false;
    if (I3 && I3.canPlay() && !finished) {
      try { ok = await I3.play({ root, withSound, Sound, finish }); } catch (e) { console.warn('3D intro failed:', e); }
    }
    if (!ok && !finished) play2D(withSound);
  }

  function showGate() {
    root.hidden = false;
    document.documentElement.classList.add('intro-on');
    const gate = el('gate', `
      <div class="brand">Roarwell Motors</div>
      <h2>Ready to wake the beasts?</h2>
      <div class="row">
        <button class="go" data-sound="1">Enter with sound</button>
        <button data-sound="0">Enter quietly</button>
      </div>
      <small>Tip: turn your volume up a little.</small>`);
    root.appendChild(gate);
    const skip = el('intro-skip', 'Skip intro', 'button');
    skip.type = 'button';
    skip.onclick = finish;
    root.appendChild(skip);
    whenIntro3D().then((i) => i && i.canPlay() && i.preload());     // start loading the car while the gate is showing
    gate.querySelectorAll('button').forEach((b) => {
      b.onclick = () => {
        const withSound = b.dataset.sound === '1';
        if (withSound) Sound.set(true);
        gate.remove();
        if (withSound) Sound.pop();          // this click also wakes up the browser's sound system
        const sb = document.getElementById('btn-sound');
        if (sb) sb.setAttribute('aria-pressed', String(Sound.enabled));
        finished = false;
        startShow(withSound);
      };
    });
  }

  document.getElementById('replay-intro').addEventListener('click', (e) => {
    e.preventDefault();
    finished = false; timers = []; animations = [];
    window.scrollTo(0, 0);
    showGate();
  });

  window.Intro = { replay: showGate };

  if (skipIntro || (!force && (seen || reduced))) {
    root.hidden = true;
  } else {
    showGate();
  }
})();
