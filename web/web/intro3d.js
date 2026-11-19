/* intro3d.js - the cinematic intro, rendered live in 3D (WebGL) with three.js.
   A real 3D supercar model, a physically lit sunrise sky, a glittering sea, a road with parked cars.
   If WebGL or the assets are not available, intro.js quietly falls back to the simpler 2D intro.

   3D car model: "Car Concept" by Eric Chadwick (CC BY 4.0), from the Khronos glTF Sample Assets.
   Everything else (sky, sea, road, smoke, glass) is drawn by this code. */

(async () => {
  let THREE, GLTFLoader, EffectComposer, RenderPass, UnrealBloomPass, OutputPass;
  try {
    THREE = await import('three');
    ({ GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js'));
    ({ EffectComposer } = await import('three/addons/postprocessing/EffectComposer.js'));
    ({ RenderPass } = await import('three/addons/postprocessing/RenderPass.js'));
    ({ UnrealBloomPass } = await import('three/addons/postprocessing/UnrealBloomPass.js'));
    ({ OutputPass } = await import('three/addons/postprocessing/OutputPass.js'));
  } catch (e) {
    console.warn('3D intro unavailable, using the simple intro:', e);
    window.Intro3D = { canPlay: () => false, preload: () => Promise.resolve(false) };
    return;
  }

  const MODEL_URL = 'assets/CarConcept.glb';
  let gltf = null, loading = null, loadError = null;

  function webglOK() {
    try { return !!document.createElement('canvas').getContext('webgl2'); } catch (e) { return false; }
  }

  function preload(onProgress) {
    if (!loading) {
      loading = new GLTFLoader().loadAsync(MODEL_URL, (e) => onProgress && e.total && onProgress(e.loaded / e.total))
        .then((g) => { gltf = g; return true; })
        .catch((e) => { loadError = e; console.warn('Car model failed to load', e); return false; });
    }
    return loading;
  }

  /* ---------------- small helpers ---------------- */
  const clamp01 = (x) => Math.min(1, Math.max(0, x));
  const smooth = (a, b, x) => { const t = clamp01((x - a) / (b - a)); return t * t * (3 - 2 * t); };
  const rand = (lo, hi) => lo + Math.random() * (hi - lo);

  function canvasTex(size, draw, repeat) {
    const c = document.createElement('canvas');
    c.width = c.height = size;
    draw(c.getContext('2d'), size);
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    if (repeat) t.repeat.set(repeat[0], repeat[1]);
    t.anisotropy = 8;
    return t;
  }
  function noiseFill(ctx, size, base, spread, count, dot) {
    ctx.fillStyle = base; ctx.fillRect(0, 0, size, size);
    for (let i = 0; i < count; i++) {
      const v = Math.floor(rand(-spread, spread));
      ctx.fillStyle = `rgba(${128 + v},${128 + v},${128 + v},${rand(0.05, 0.4)})`;
      ctx.fillRect(Math.random() * size, Math.random() * size, rand(1, dot), rand(1, dot));
    }
  }

  /* Sunrise sky: gradient + glowing sun + soft clouds, written as a tiny shader. */
  function makeSky(sunDir) {
    const mat = new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: false,
      uniforms: { sunDir: { value: sunDir.clone() } },
      vertexShader: 'varying vec3 vDir; void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
      fragmentShader: `
        varying vec3 vDir; uniform vec3 sunDir;
        float h(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453); }
        float n(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
          return mix(mix(h(i),h(i+vec2(1,0)),f.x), mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x), f.y); }
        float fbm(vec2 p){ float a=.5, s=0.; for(int i=0;i<5;i++){ s+=a*n(p); p*=2.02; a*=.5; } return s; }
        void main(){
          vec3 d = normalize(vDir);
          float e = clamp(d.y, -0.2, 1.0);
          vec3 horizon = vec3(1.0, 0.62, 0.36);
          vec3 low = vec3(0.95, 0.38, 0.45);
          vec3 mid = vec3(0.42, 0.22, 0.52);
          vec3 top = vec3(0.06, 0.10, 0.30);
          vec3 col = mix(horizon, low, smoothstep(0.0, 0.10, e));
          col = mix(col, mid, smoothstep(0.08, 0.38, e));
          col = mix(col, top, smoothstep(0.30, 0.85, e));
          float sd = max(dot(d, normalize(sunDir)), 0.0);
          col += vec3(1.0, 0.55, 0.22) * pow(sd, 6.0) * 0.55;
          col += vec3(1.0, 0.75, 0.45) * pow(sd, 60.0) * 1.0;
          col += vec3(1.0, 0.95, 0.8) * smoothstep(0.9994, 0.99985, sd) * 14.0;
          vec2 cp = d.xz / max(d.y + 0.12, 0.08) * 0.9;
          float c = smoothstep(0.52, 0.85, fbm(cp * 1.6 + vec2(0.0, 3.0)));
          vec3 cloudLit = mix(vec3(1.0, 0.55, 0.42), vec3(0.55, 0.28, 0.5), smoothstep(0.0, 0.5, e)) * (1.0 + pow(sd, 3.0) * 1.8);
          col = mix(col, cloudLit, c * smoothstep(0.0, 0.07, e) * 0.85);
          if (d.y < 0.0) col = mix(horizon * 0.9, vec3(0.2, 0.12, 0.2), smoothstep(0.0, -0.2, d.y));
          gl_FragColor = vec4(col, 1.0);
        }`,
    });
    return new THREE.Mesh(new THREE.SphereGeometry(500, 48, 24), mat);
  }

  /* ---------------- the car ---------------- */
  function makeCar({ paint = null, headlightsOn = false } = {}) {
    const model = gltf.scene.clone(true);
    // each car gets its own copies of the materials we want to tint or light
    model.traverse((o) => {
      if (!o.isMesh) return;
      o.castShadow = true; o.receiveShadow = true;
      const m = o.material;
      if (!m) return;
      if (/^Paint/i.test(m.name) && paint) {
        o.material = m.clone();
        o.material.color.set(paint);
        if (o.material.map) o.material.map = null;
      }
      if (m.name === 'Headlight' || m.name === 'Brakelight') o.material = m.clone();
      if (m.name === 'License') o.visible = false;             // hide the plate (it shows a logo)
    });
    // measure and standardise: nose along +X, length 4.8, wheels on y=0
    const box = new THREE.Box3().setFromObject(model);
    const size = box.getSize(new THREE.Vector3());
    const alongZ = size.z > size.x;
    const headNode = model.getObjectByName('BodyHeadlights');
    const hb = headNode ? new THREE.Box3().setFromObject(headNode).getCenter(new THREE.Vector3()) : box.getCenter(new THREE.Vector3());
    const c = box.getCenter(new THREE.Vector3());
    const noseSign = alongZ ? Math.sign(hb.z - c.z) || 1 : Math.sign(hb.x - c.x) || 1;
    const pivot = new THREE.Group();
    pivot.add(model);
    model.position.set(-c.x, -box.min.y, -c.z);
    // rotate so the nose points to +X
    pivot.rotation.y = alongZ ? (noseSign > 0 ? -Math.PI / 2 : Math.PI / 2) : (noseSign > 0 ? 0 : Math.PI);
    const length = alongZ ? size.z : size.x;
    const scale = 4.8 / length;
    pivot.scale.setScalar(scale);
    const body = new THREE.Group();     // pitch / roll
    body.add(pivot);
    const rig = new THREE.Group();      // position / yaw
    rig.add(body);
    // double-check the nose really points to +X (flip if the headlights ended up at the back)
    rig.updateMatrixWorld(true);
    if (headNode) {
      const hc2 = new THREE.Box3().setFromObject(headNode).getCenter(new THREE.Vector3());
      if (hc2.x < 0) { pivot.rotation.y += Math.PI; rig.updateMatrixWorld(true); }
    }
    rig.userData = { body, model, scale, wheels: ['WheelFrontL', 'WheelFrontR', 'WheelRearL', 'WheelRearR'].map((n) => model.getObjectByName(n)).filter(Boolean), headlights: [], width: (alongZ ? size.x : size.z) * scale };
    rig.userData.headMats = [];
    model.traverse((o) => { if (o.isMesh && o.material && (o.material.name === 'Headlight')) rig.userData.headMats.push(o.material); });
    rig.userData.tailMats = [];
    model.traverse((o) => { if (o.isMesh && o.material && (o.material.name === 'Brakelight')) rig.userData.tailMats.push(o.material); });
    // headlight spot lights at the two front corners
    const half = rig.userData.width * 0.34;
    const mk = (z) => {
      const s = new THREE.SpotLight(0xffe2b0, 0, 45, 0.45, 0.8, 1.6);
      s.position.set(2.6, 0.6, z);
      s.target.position.set(12, 0.2, z * 1.4);
      rig.add(s, s.target);
      return s;
    };
    rig.userData.spots = [mk(half), mk(-half)];
    setHeadlights(rig, headlightsOn ? 1 : 0);
    return rig;
  }

  function setHeadlights(rig, k, tail = 0.2) {
    rig.userData.headMats.forEach((m) => { m.emissive = new THREE.Color(1, 0.86, 0.6); m.emissiveIntensity = k * 2.2; m.needsUpdate = true; });
    rig.userData.tailMats.forEach((m) => { m.emissiveIntensity = 1 + tail * 6; });
    rig.userData.spots.forEach((s) => { s.intensity = k * 30; });
  }

  function spinWheels(rig, dist) {
    const axis = new THREE.Vector3(0, 0, 1).transformDirection(rig.matrixWorld);
    const r = 0.36;
    rig.userData.wheels.forEach((w) => w.rotateOnWorldAxis(axis, -dist / r));
  }

  /* ---------------- the show ---------------- */
  function canPlay() { return webglOK() && !loadError; }

  async function play({ root, withSound, Sound, finish, onReady }) {
    const ok = await preload();
    if (!ok) return false;
    const W = () => window.innerWidth, H = () => window.innerHeight;
    const S = (name, ...a) => { if (withSound && Sound.enabled) Sound[name](...a); };

    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.setSize(W(), H());
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    const canvas = renderer.domElement;
    canvas.className = 'gl';
    root.innerHTML = '';
    root.appendChild(canvas);

    const pmrem = new THREE.PMREMGenerator(renderer);

    /* ===== Scene A: darkness and the headlights ===== */
    const sceneA = new THREE.Scene();
    sceneA.background = new THREE.Color(0x000000);
    sceneA.fog = new THREE.FogExp2(0x000000, 0.06);
    const nightEnv = new THREE.Scene();
    nightEnv.add(new THREE.Mesh(new THREE.SphereGeometry(50, 16, 8), new THREE.MeshBasicMaterial({ side: THREE.BackSide, color: 0x0a1020 })));
    const strip = new THREE.Mesh(new THREE.PlaneGeometry(40, 3), new THREE.MeshBasicMaterial({ color: new THREE.Color(0.6, 0.7, 1.2), side: THREE.DoubleSide }));
    strip.position.set(0, 14, -10); strip.rotation.x = Math.PI / 2.4; strip.material.color.setRGB(0.25, 0.3, 0.6); nightEnv.add(strip);
    sceneA.environment = pmrem.fromScene(nightEnv, 0.05).texture;
    sceneA.environmentIntensity = 0.5;
    const floorA = new THREE.Mesh(new THREE.PlaneGeometry(80, 80),
      new THREE.MeshStandardMaterial({ color: 0x08090c, roughness: 0.55, metalness: 0.2, envMapIntensity: 0.25 }));
    floorA.rotation.x = -Math.PI / 2; floorA.receiveShadow = true; sceneA.add(floorA);
    const carA = makeCar({ paint: '#b3121f' });
    carA.rotation.y = -Math.PI / 2;            // nose toward the camera (+Z)
    sceneA.add(carA);
    const rimL = new THREE.DirectionalLight(0x5d7dff, 1.4); rimL.position.set(-8, 6, -8); sceneA.add(rimL);
    const rimR = new THREE.DirectionalLight(0xff8a4d, 0.9); rimR.position.set(8, 3, -6); sceneA.add(rimR);
    const camA = new THREE.PerspectiveCamera(36, W() / H(), 0.05, 200);

    /* ===== Scene B: sunrise on the beach road ===== */
    const sunDir = new THREE.Vector3(0.28, 0.05, -1).normalize();
    const sceneB = new THREE.Scene();
    const sky = makeSky(sunDir);
    sceneB.add(sky);
    sceneB.environment = pmrem.fromScene(Object.assign(new THREE.Scene(), { children: [] }).add(makeSky(sunDir)), 0.0, 0.1, 1000, { size: 512 }).texture;
    sceneB.environmentIntensity = 0.75;
    sceneB.fog = new THREE.Fog(0xe9917f, 80, 520);
    // sun light
    const sunLight = new THREE.DirectionalLight(0xffb070, 4.2);
    sunLight.position.copy(sunDir).multiplyScalar(120);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.set(2048, 2048);
    Object.assign(sunLight.shadow.camera, { left: -34, right: 34, top: 22, bottom: -22, near: 1, far: 300 });
    sunLight.shadow.bias = -0.0004; sunLight.shadow.normalBias = 0.03;
    sceneB.add(sunLight);
    sceneB.add(new THREE.HemisphereLight(0x9a86d8, 0x4a3030, 0.55));

    // road
    const asphalt = canvasTex(512, (g, s) => noiseFill(g, s, '#3a3a40', 70, 5200, 3), [60, 3]);
    const road = new THREE.Mesh(new THREE.PlaneGeometry(400, 7), new THREE.MeshStandardMaterial({ map: asphalt, color: 0x9a9aa4, roughness: 0.5, metalness: 0.15, envMapIntensity: 0.9 }));
    road.rotation.x = -Math.PI / 2; road.receiveShadow = true; sceneB.add(road);
    const dashTex = canvasTex(256, (g, s) => { g.fillStyle = '#000'; g.fillRect(0, 0, s, s); g.fillStyle = '#fff'; g.fillRect(0, s * 0.35, s * 0.55, s * 0.3); }, [130, 1]);
    const dashes = new THREE.Mesh(new THREE.PlaneGeometry(400, 0.26), new THREE.MeshStandardMaterial({ color: 0xffd16b, alphaMap: dashTex, transparent: true, roughness: 0.6, emissive: 0x442200 }));
    dashes.rotation.x = -Math.PI / 2; dashes.position.y = 0.012; sceneB.add(dashes);
    const kerb = new THREE.Mesh(new THREE.BoxGeometry(400, 0.18, 0.5), new THREE.MeshStandardMaterial({ color: 0x8e8a92, roughness: 0.8 }));
    kerb.position.set(0, 0.09, -3.75); kerb.castShadow = kerb.receiveShadow = true; sceneB.add(kerb);
    // sand / promenade
    const sandTex = canvasTex(512, (g, s) => noiseFill(g, s, '#d2a77f', 40, 9000, 3), [50, 6]);
    const sand = new THREE.Mesh(new THREE.PlaneGeometry(400, 22), new THREE.MeshStandardMaterial({ map: sandTex, roughness: 0.95, color: 0xffffff }));
    sand.rotation.x = -Math.PI / 2; sand.position.set(0, -0.005, -15); sand.receiveShadow = true; sceneB.add(sand);
    // sea
    const waves = canvasTex(512, (g, s) => {
      const img = g.createImageData(s, s);
      for (let y = 0; y < s; y++) for (let x = 0; x < s; x++) {
        const nx = Math.sin(x * 0.07 + Math.sin(y * 0.03) * 3) * 0.5 + Math.sin(x * 0.19 + y * 0.05) * 0.25 + Math.sin(y * 0.11) * 0.25;
        const ny = Math.sin(y * 0.09 + Math.sin(x * 0.04) * 3) * 0.5 + Math.sin(y * 0.23 - x * 0.04) * 0.25;
        const i = (y * s + x) * 4;
        img.data[i] = 128 + nx * 60; img.data[i + 1] = 128 + ny * 60; img.data[i + 2] = 255; img.data[i + 3] = 255;
      }
      g.putImageData(img, 0, 0);
    }, [90, 90]);
    const sea = new THREE.Mesh(new THREE.PlaneGeometry(2400, 2400), new THREE.MeshStandardMaterial({ color: 0x1b2d52, roughness: 0.09, metalness: 0.1, normalMap: waves, normalScale: new THREE.Vector2(0.6, 0.6), envMapIntensity: 1.3 }));
    sea.rotation.x = -Math.PI / 2; sea.position.set(0, -0.45, -1212); sceneB.add(sea);
    const foam = new THREE.Mesh(new THREE.PlaneGeometry(400, 1.6), new THREE.MeshBasicMaterial({ color: 0xffe9d6, transparent: true, opacity: 0.35 }));
    foam.rotation.x = -Math.PI / 2; foam.position.set(0, 0.0, -25.4); sceneB.add(foam);
    // distant headland
    const hill = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x5a3f5e, fog: true }));
    hill.scale.set(150, 24, 40); hill.position.set(-170, -0.4, -360); sceneB.add(hill);
    const hill2 = hill.clone(); hill2.scale.set(110, 16, 30); hill2.position.set(210, -0.4, -380); sceneB.add(hill2);

    // parked cars: real 3D models in different paints
    const paints = ['#f2f2f4', '#1b1b20', '#2f6bff', '#ffbe1a', '#ff6a1f', '#16a34a', '#8a8f9c', '#7a2cff', '#e11d48', '#0ea5e9'];
    const parked = [];
    for (let i = 0; i < 10; i++) {
      const car = makeCar({ paint: paints[i % paints.length] });
      car.position.set(-29 + i * 6.1 + rand(-0.4, 0.4), 0, -7.2 + rand(-0.3, 0.3));
      car.rotation.y = rand(-0.03, 0.03);
      sceneB.add(car); parked.push(car);
    }
    const hero = makeCar({ paint: '#c0121f', headlightsOn: true });
    hero.position.set(-60, 0, 0.2);
    sceneB.add(hero);
    const camB = new THREE.PerspectiveCamera(34, W() / H(), 0.1, 2000);
    camB.position.set(-14, 1.15, 9.2);

    // smoke puffs and skid marks
    const puffTex = canvasTex(128, (g, s) => {
      const gr = g.createRadialGradient(s / 2, s / 2, 2, s / 2, s / 2, s / 2);
      gr.addColorStop(0, 'rgba(235,225,225,0.9)'); gr.addColorStop(1, 'rgba(235,225,225,0)');
      g.clearRect(0, 0, s, s); g.fillStyle = gr; g.fillRect(0, 0, s, s);
    });
    const puffs = [];
    function addPuff(pos) {
      const m = new THREE.Sprite(new THREE.SpriteMaterial({ map: puffTex, transparent: true, depthWrite: false, opacity: 0.7, color: 0xf0dcd0 }));
      m.position.copy(pos); m.scale.setScalar(rand(0.8, 1.4));
      m.userData = { age: 0, life: rand(1.3, 2.2), v: new THREE.Vector3(rand(-0.4, 0.4), rand(0.5, 1.1), rand(0.1, 0.9)), s0: m.scale.x };
      sceneB.add(m); puffs.push(m);
    }
    const marks = [];
    [-0.82, 0.82].forEach((zz) => {
      const mk = new THREE.Mesh(new THREE.PlaneGeometry(1, 0.22), new THREE.MeshBasicMaterial({ color: 0x050505, transparent: true, opacity: 0.8 }));
      mk.rotation.x = -Math.PI / 2; mk.position.y = 0.02; mk.visible = false; mk.userData.z = zz; sceneB.add(mk); marks.push(mk);
    });

    /* ===== post-processing ===== */
    const composer = new EffectComposer(renderer);
    const pass = new RenderPass(sceneA, camA);
    composer.addPass(pass);
    const bloom = new UnrealBloomPass(new THREE.Vector2(W(), H()), 0.6, 0.45, 1.0);
    composer.addPass(bloom);
    composer.addPass(new OutputPass());
    const onResize = () => {
      renderer.setSize(W(), H()); composer.setSize(W(), H());
      camA.aspect = camB.aspect = W() / H(); camA.updateProjectionMatrix(); camB.updateProjectionMatrix();
    };
    window.addEventListener('resize', onResize);

    /* ===== overlays: cinema bars, vignette, glass, button, words ===== */
    const bars = document.createElement('div');
    bars.className = 'cine';
    bars.innerHTML = '<i></i><i></i><b></b><span>3D car model "Car Concept" by Eric Chadwick, CC BY 4.0</span>';
    root.appendChild(bars);
    const glassHost = document.createElement('div');
    glassHost.className = 'glass-host';
    root.appendChild(glassHost);

    const wrap = document.createElement('div');
    wrap.className = 'start-wrap';
    wrap.innerHTML = '<p>Press to start the engine</p><button class="engine-btn" aria-label="Engine start"><span>Engine<br>Start<br>Stop</span></button>';
    const welcome = document.createElement('div');
    welcome.className = 'welcome';
    welcome.innerHTML = 'Welcome to Paradise.<br>Time to wake the beasts.';
    root.append(wrap, welcome);
    const skip = document.createElement('button');
    skip.className = 'intro-skip'; skip.type = 'button'; skip.textContent = 'Skip intro'; skip.onclick = finish;
    root.appendChild(skip);
    const button = wrap.querySelector('button');

    /* ===== glass shatter, using a snapshot of the last frame ===== */
    function shatter(snapshot) {
      const w = W(), h = H(), cx = w / 2, cy = h * 0.5, D = Math.hypot(w, h);
      const svgNS = 'http://www.w3.org/2000/svg';
      const svg = document.createElementNS(svgNS, 'svg');
      svg.setAttribute('viewBox', `0 0 ${w} ${h}`); svg.setAttribute('preserveAspectRatio', 'none');
      svg.setAttribute('class', 'glass');
      svg.innerHTML = `<defs><pattern id="snap" patternUnits="userSpaceOnUse" width="${w}" height="${h}"><image href="${snapshot}" width="${w}" height="${h}" preserveAspectRatio="none"/></pattern></defs>`;
      const radii = [0, 0.07, 0.17, 0.33, 0.6, 1.2], N = 18;
      const rings = radii.map((r, ri) => Array.from({ length: N }, (_, i) => {
        const ang = ((i + (ri ? rand(-0.3, 0.3) : 0)) / N) * Math.PI * 2, rr = r * D * (ri ? rand(0.85, 1.15) : 1);
        return [cx + Math.cos(ang) * rr, cy + Math.sin(ang) * rr];
      }));
      const shards = [];
      const add = (pts) => {
        const p = document.createElementNS(svgNS, 'polygon');
        p.setAttribute('points', pts.map((q) => q.map((n) => n.toFixed(1)).join(',')).join(' '));
        p.setAttribute('fill', 'url(#snap)'); p.setAttribute('stroke', 'rgba(210,235,255,.85)'); p.setAttribute('stroke-width', '1.4');
        p.style.transformBox = 'fill-box'; p.style.transformOrigin = 'center';
        svg.appendChild(p);
        const mx = pts.reduce((s, q) => s + q[0], 0) / pts.length, my = pts.reduce((s, q) => s + q[1], 0) / pts.length;
        shards.push({ node: p, dx: mx - cx, dy: my - cy, dist: Math.hypot(mx - cx, my - cy) });
      };
      for (let ri = 0; ri < radii.length - 1; ri++) for (let i = 0; i < N; i++) {
        const j = (i + 1) % N;
        if (ri === 0) add([[cx, cy], rings[1][i], rings[1][j]]);
        else { add([rings[ri][i], rings[ri + 1][i], rings[ri + 1][j]]); add([rings[ri][i], rings[ri + 1][j], rings[ri][j]]); }
      }
      glassHost.appendChild(svg);
      const flash = document.createElement('div');
      flash.className = 'flash'; root.appendChild(flash);
      flash.animate([{ opacity: 0.85 }, { opacity: 0 }], { duration: 450, fill: 'forwards' });
      setTimeout(() => {
        shards.forEach((s) => {
          const push = 1 + 500 / (s.dist + 120);
          const dx = (s.dx / (s.dist || 1)) * rand(120, 420) * push * 0.5;
          const dy = rand(500, 1100) + (s.dy / (s.dist || 1)) * 140, rot = rand(-260, 260);
          s.node.animate([
            { transform: 'translate(0,0) rotate(0deg)', opacity: 1 },
            { transform: `translate(${dx * 0.6}px, ${dy * 0.12 - 40}px) rotate(${rot * 0.4}deg)`, opacity: 1, offset: 0.3 },
            { transform: `translate(${dx}px, ${dy}px) rotate(${rot}deg)`, opacity: 0.2 },
          ], { duration: rand(900, 1500), delay: (s.dist / 1800) * 260, easing: 'cubic-bezier(.4,0,.9,.6)', fill: 'forwards' });
        });
      }, 230);
      setTimeout(() => svg.remove(), 2600);
    }

    /* ===== the timeline ===== */
    let stopped = false;
    const t0 = performance.now();
    let last = t0, lastNow = t0;
    let phase = 'A', tB = 0, pressed = false, pressT = 0;
    let snapNeeded = false, snapshot = null;
    const events = new Set();
    const once = (key, fn) => { if (!events.has(key)) { events.add(key); fn(); } };
    const shake = (amt) => new THREE.Vector3(rand(-1, 1) * amt, rand(-1, 1) * amt, 0);
    let heroX = -60, heroV = 0, skidding = false, skidStartX = -14, skidT = 0;
    const V0 = 34, DECEL = 35;
    const camTarget = new THREE.Vector3();
    onReady && onReady();
    bars.classList.add('on');

    function frame(now) {
      if (stopped) return;
      if (!window.__introManual) requestAnimationFrame(frame);
      const dt = Math.min(window.__introManual ? 0.3 : 0.05, (now - last) / 1000); last = now; lastNow = now;
      const t = (now - t0) / 1000;

      if (phase === 'A') {
        // 0.0-0.6 dark; 0.6-1.7 eyes open; 1.9 blink; 2.6- charge; 4.35 impact
        once('growl', () => { if (t >= 0.5) S('growl'); });
        let k = smooth(0.6, 1.7, t);
        if (t > 1.9 && t < 2.2) k *= 0.08 + 0.92 * Math.abs((t - 2.05) / 0.15);
        if (t > 2.6) k = 1 + (t - 2.6) * 0.5;
        setHeadlights(carA, k, k);
        const charge = Math.max(0, t - 2.6);
        if (t > 2.6) once('rev', () => S('rev', 0, 1.9));
        carA.position.z = 0.5 * 2.6 * charge * charge;
        const base = new THREE.Vector3(0, 0.62, 7.6 - Math.min(t, 2.6) * 0.18);
        camA.position.copy(base).add(shake(t > 2.6 ? 0.012 + charge * 0.02 : 0.002));
        camA.lookAt(0, 0.55, 0);
        bloom.strength = 0.25 + Math.min(k, 2) * 0.1;
        renderer.toneMappingExposure = 1 + charge * 0.12;
        if (t >= 4.35) { snapNeeded = true; }
        composer.render();
        if (snapNeeded) {
          snapshot = canvas.toDataURL('image/jpeg', 0.88);
          S('shatter', 0);
          shatter(snapshot);
          phase = 'B'; tB = now; bloom.strength = 0.22; renderer.toneMappingExposure = 0.95;
          pass.scene = sceneB; pass.camera = camB;
        }
        return;
      }

      // ===== Scene B =====
      const s = (now - tB) / 1000;
      // the hero car (simulated in small steps so big frame gaps never change the result)
      let rest = dt;
      while (rest > 1e-6) {
        const h = Math.min(rest, 1 / 120); rest -= h;
        if (!skidding) {
          heroV = V0; heroX += heroV * h;
          if (heroX >= skidStartX) { skidding = true; S('skid', 0); }
        } else {
          skidT += h;
          heroV = Math.max(0, heroV - DECEL * h);
          heroX += heroV * h;
        }
      }
      const skidDur = V0 / DECEL;
      const tau = clamp01(skidT / skidDur);
      hero.position.x = heroX;
      if (skidding) {
        hero.rotation.y = 0.30 * Math.sin(tau * Math.PI * 1.5) * (1 - tau);
        hero.userData.body.rotation.z = -0.035 * Math.sin(tau * Math.PI) ;
        hero.userData.body.rotation.x = 0.02 * Math.sin(tau * Math.PI * 2) * (1 - tau);
        if (heroV > 0.5) {
          hero.updateMatrixWorld(true);
          [-0.82, 0.82].forEach((zz) => { if (Math.random() < 0.9) addPuff(hero.localToWorld(new THREE.Vector3(-1.5, 0.2, zz))); });
          marks.forEach((mk, i) => {
            mk.visible = true;
            const p0 = skidStartX - 1.5, p1 = hero.position.x - 1.5;
            mk.scale.x = Math.max(0.01, p1 - p0); mk.position.x = (p0 + p1) / 2; mk.position.z = mk.userData.z + (i ? 0.05 : -0.05) + hero.position.z * 0.0;
          });
        }
      }
      hero.updateMatrixWorld(true);
      if (!skidding || heroV > 0.5) spinWheels(hero, heroV * dt * (skidding ? 0.25 : 1));
      // smoke
      for (let i = puffs.length - 1; i >= 0; i--) {
        const p = puffs[i], d = p.userData;
        d.age += dt;
        const a = d.age / d.life;
        if (a >= 1) { sceneB.remove(p); p.material.dispose(); puffs.splice(i, 1); continue; }
        p.position.addScaledVector(d.v, dt);
        p.scale.setScalar(d.s0 * (1 + a * 3.4));
        p.material.opacity = 0.7 * (1 - a);
      }
      // camera: starts wide on the left, follows the car, then settles into a low hero angle
      const e = smooth(0, 5.5, s);
      const push = pressed ? (lastNow - pressT) / 1000 : 0;
      camB.position.set(-14 + e * 10.2 + push * 1.0, 1.15 - e * 0.32, 9.2 - e * 2.9 - push * 0.9);
      camTarget.set(Math.max(-9, Math.min(1.6, heroX * 0.5)), 0.8, 0);
      camB.lookAt(camTarget);
      // sea shimmer
      waves.offset.x += dt * 0.004; waves.offset.y += dt * 0.0025;
      // after the stop: engine button
      if (skidding && heroV <= 0.5) {
        once('button', () => setTimeout(() => {
          if (stopped) return;
          wrap.classList.add('show');
          wrap.animate([{ opacity: 0, transform: 'translateY(20px)' }, { opacity: 1, transform: 'none' }], { duration: 600, easing: 'ease-out', fill: 'forwards' });
        }, 900));
      }
      if (pressed) {
        const pt = (now - pressT) / 1000;
        setHeadlights(hero, 1 + Math.min(pt, 0.4) * 4, 1);
        bloom.strength = 0.22 + Math.min(pt, 1.5) * 0.4;
        hero.userData.body.position.y = Math.sin(pt * 70) * 0.004 * (pt < 2.2 ? 1 : 0);
        renderer.toneMappingExposure = 1.05 + Math.max(0, pt - 2.1) * 1.4;
      }
      composer.render();
    }

    // ---- start button ----
    button.onclick = () => {
      if (pressed) return;
      pressed = true; pressT = lastNow;
      button.classList.add('on');
      wrap.querySelector('p').textContent = 'Engine running';
      S('ignition', 0);
      root.classList.add('shake');
      setTimeout(() => root.classList.remove('shake'), 900);
      setTimeout(() => welcome.animate([{ opacity: 0, transform: 'translateY(14px)' }, { opacity: 1, transform: 'none' }], { duration: 800, easing: 'ease-out', fill: 'forwards' }), 700);
      setTimeout(() => finish(), 3300);
    };

    // expose cleanup
    play.stop = () => {
      stopped = true;
      window.removeEventListener('resize', onResize);
      try { composer.dispose(); renderer.dispose(); pmrem.dispose(); } catch (e) { /* ignore */ }
    };
    if (window.__introManual) window.__introStep = (ms) => frame(t0 + ms);   // test hook: step time by hand
    else requestAnimationFrame(frame);
    return true;
  }

  window.Intro3D = {
    canPlay,
    preload,
    play,
    stop: () => play.stop && play.stop(),
    get loaded() { return !!gltf; },
  };
})();
