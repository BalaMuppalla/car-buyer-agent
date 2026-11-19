/* art.js - original cartoon car pictures, drawn in code.
   No real car models, photos or brand logos are used anywhere. */

const PALETTE = ['#ff5a4e', '#ff9f1c', '#2ec4b6', '#4cc9f0', '#7b61ff', '#ff4d9d', '#8ac926', '#f5d547'];

function hashStr(text) {
  let h = 0;
  for (const ch of text) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return h;
}

/* Every car gets its own colour, always the same one. Classics get a deep red. */
function colorFor(car) {
  return car.vintage ? '#d62839' : PALETTE[hashStr(car.name) % PALETTE.length];
}

/* Side-on outlines, all facing right. "body" is the metal, "win" is the glass. */
const BODIES = {
  sedan: {
    body: 'M18 80 L20 66 Q22 60 40 58 L76 56 Q94 32 122 32 L150 32 Q172 34 184 54 L210 60 Q224 64 224 78 L224 82 L18 82 Z',
    win: 'M86 54 Q100 38 122 38 L148 38 Q162 40 172 54 Z',
  },
  hatchback: {
    body: 'M18 80 L20 64 Q22 58 38 56 L70 52 Q84 34 108 32 L156 32 Q176 34 188 54 L212 60 Q224 64 224 78 L224 82 L18 82 Z',
    win: 'M80 52 Q92 38 110 38 L152 38 Q166 40 176 54 Z',
  },
  suv: {
    body: 'M16 82 L16 56 Q18 48 32 46 L60 44 Q72 26 96 26 L164 26 Q182 28 192 46 L214 52 Q226 56 226 76 L226 82 Z',
    win: 'M72 44 Q82 32 98 32 L162 32 Q174 34 182 46 Z',
  },
  truck: {
    body: 'M14 82 L14 58 L84 58 L84 40 Q86 30 100 28 L140 28 Q160 30 172 48 L212 54 Q226 58 226 76 L226 82 Z',
    win: 'M96 34 L138 34 Q152 36 162 48 L96 48 Z',
  },
  minivan: {
    body: 'M16 82 L16 54 Q18 38 40 34 L150 30 Q176 32 190 50 L214 56 Q226 60 226 76 L226 82 Z',
    win: 'M34 50 L34 40 L84 38 L84 50 Z M92 50 L92 38 L146 36 Q160 38 170 50 Z',
  },
  coupe: {
    body: 'M18 80 L20 68 Q24 62 44 60 L84 58 Q106 38 134 38 L156 40 Q176 44 190 58 L214 62 Q226 66 226 78 L226 82 L18 82 Z',
    win: 'M96 56 Q112 44 134 44 L154 46 Q168 50 178 58 Z',
  },
};

let clipCounter = 0;

function wheel(cx) {
  return `<g><circle cx="${cx}" cy="84" r="17" fill="#141824"/>` +
         `<circle cx="${cx}" cy="84" r="9" fill="#cfd6e4"/>` +
         `<circle cx="${cx}" cy="84" r="3.2" fill="#141824"/></g>`;
}

/* A car picture as SVG text: carArt('suv', '#ff5a4e') */
function carArt(type, color) {
  const shape = BODIES[type] || BODIES.sedan;
  const id = 'car' + (++clipCounter);
  return `<svg viewBox="0 0 240 110" class="car-svg" aria-hidden="true" focusable="false">
    <defs>
      <clipPath id="${id}"><path d="${shape.body}"/></clipPath>
      <linearGradient id="${id}g" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#fff" stop-opacity=".38"/>
        <stop offset=".55" stop-color="#fff" stop-opacity="0"/>
      </linearGradient>
    </defs>
    <ellipse cx="122" cy="101" rx="106" ry="5" fill="#000" opacity=".4"/>
    <path d="${shape.body}" fill="${color}" stroke="#141824" stroke-width="3" stroke-linejoin="round"/>
    <g clip-path="url(#${id})">
      <rect width="240" height="110" fill="url(#${id}g)"/>
      <rect x="0" y="70" width="240" height="22" fill="#000" opacity=".18"/>
      <path d="M14 67 L228 62" stroke="#fff" stroke-opacity=".3" stroke-width="3"/>
    </g>
    <path d="${shape.win}" fill="#bfe9ff" stroke="#141824" stroke-width="3" stroke-linejoin="round"/>
    ${wheel(62)}${wheel(182)}
    <ellipse cx="221" cy="66" rx="5" ry="3.5" fill="#fff3b0" stroke="#141824" stroke-width="1.5"/>
    <rect x="15" y="62" width="6" height="9" rx="2" fill="#ff3b3b"/>
    <path d="M46 42 l2 -6 l2 6 l6 2 l-6 2 l-2 6 l-2 -6 l-6 -2z" fill="#fff" opacity=".85"/>
  </svg>`;
}


/* A sleek, original car drawn with code (no outlines, soft light). kind: coupe | suv | sedan */
let carCounter = 0;
function sleekCar(color, kind = 'coupe') {
  const id = 'sc' + (carCounter++);
  const v = {
    coupe: { rt: 22, a: 128, b: 178, c: 250, d: 288 },
    sedan: { rt: 20, a: 120, b: 165, c: 268, d: 312 },
    suv:   { rt: 10, a: 112, b: 138, c: 300, d: 340 },
  }[kind];
  const body = `M10 80 C10 68 22 64 48 60 L${v.a - 14} 52 C${v.a + 8} 40 ${v.b - 20} ${v.rt + 2} ${v.b + 30} ${v.rt} L${v.c - 10} ${v.rt} C${v.c + 20} ${v.rt + 2} ${v.d - 14} 38 ${v.d + 14} 54 L352 58 C380 62 392 70 392 80 L392 88 L10 88 Z`;
  const glass = `M${v.a + 6} 52 C${v.a + 20} 40 ${v.b - 14} ${v.rt + 8} ${v.b + 30} ${v.rt + 7} L${v.c - 8} ${v.rt + 7} C${v.c + 16} ${v.rt + 9} ${v.d - 18} 40 ${v.d + 4} 52 Z`;
  const wheel = (cx) => `<circle cx="${cx}" cy="88" r="27" fill="#07080b"/><circle cx="${cx}" cy="88" r="21" fill="#15171d"/>
    <circle cx="${cx}" cy="88" r="13" fill="url(#${id}r)"/><circle cx="${cx}" cy="88" r="4" fill="#0b0c10"/>
    <path d="M${cx} 75 V101 M${cx - 13} 88 H${cx + 13} M${cx - 9} 79 L${cx + 9} 97 M${cx + 9} 79 L${cx - 9} 97" stroke="#0b0c10" stroke-width="2.2"/>`;
  return `<svg viewBox="0 0 400 118" aria-hidden="true">
    <defs>
      <linearGradient id="${id}b" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${color}"/><stop offset=".55" stop-color="${color}"/><stop offset="1" stop-color="#000" stop-opacity=".55"/></linearGradient>
      <linearGradient id="${id}g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7fa6c9"/><stop offset=".5" stop-color="#1b2a3c"/><stop offset="1" stop-color="#0a1018"/></linearGradient>
      <radialGradient id="${id}r"><stop offset="0" stop-color="#e8ecf4"/><stop offset="1" stop-color="#8a92a4"/></radialGradient>
    </defs>
    <ellipse cx="200" cy="108" rx="188" ry="9" fill="#000" opacity=".4"/>
    <path d="${body}" fill="url(#${id}b)"/>
    <path d="${glass}" fill="url(#${id}g)"/>
    <path d="M${v.b + 12} ${v.rt + 7} L${v.b - 4} 52" stroke="#05080d" stroke-width="3"/>
    <path d="M26 70 C130 62 270 62 376 72" stroke="#fff" stroke-opacity=".28" stroke-width="2.5" fill="none" stroke-linecap="round"/>
    <path d="M0 0" />
    <path d="M368 66 L392 72 L368 75 Z" fill="#fff6cf"/>
    <rect x="10" y="68" width="10" height="6" rx="2" fill="#ff2b2b"/>
    ${wheel(88)}${wheel(312)}
  </svg>`;
}


/* Plain drawing used when a car has no photo: picks a sleek shape for the body type. */
function fallbackArt(type, color) {
  const kind = { sedan: 'sedan', hatchback: 'sedan', coupe: 'coupe' }[type] || 'suv';
  return sleekCar(color, kind);
}
