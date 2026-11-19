/* app.js - the Roarwell Motors page: filters, car cards, details, shortlist, compare. */

const $ = (id) => document.getElementById(id);
const money = (n) => '$' + Math.round(n).toLocaleString('en-US');
const FUEL_LABEL = { petrol: 'Petrol', hybrid: 'Hybrid', diesel: 'Diesel', electric: 'Electric' };
const TYPE_LABEL = { sedan: 'Sedan', hatchback: 'Hatchback', suv: 'SUV', truck: 'Truck', minivan: 'Minivan', coupe: 'Coupe' };

let CARS = [];
let FUEL_PRICE = {};
let current = null;                     // car shown in the details window
let shortlist = load('roarwell-shortlist', []);
let compare = [];                       // up to two car ids
let onlyIds = null;                     // when set, the grid shows just these cars (Alex's picks)

/* A real photo if we have one; if the picture can't load, a plain drawing takes its place. */
function photo(c) {
  return `<img src="/api/photo/${c.id}" data-car="${c.id}" loading="lazy" alt="${c.name}">`;
}
document.addEventListener('error', (e) => {
  const img = e.target;
  if (!(img instanceof HTMLImageElement) || !img.dataset.car) return;
  const c = byId(img.dataset.car);
  if (!c) return;
  const box = document.createElement('div');
  box.className = 'fallback';
  box.innerHTML = fallbackArt(c.type, colorFor(c));
  img.replaceWith(box);
  if (img.dataset.credit) $('m-credit').textContent = 'Illustration: no free photo was found for this car.';
}, true);

function load(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch (e) { return fallback; }
}
function save(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* storage blocked: skip */ }
}
function toast(text) {
  const t = $('toast');
  t.textContent = text;
  t.classList.add('show');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.remove('show'), 2200);
}
const byId = (id) => CARS.find((c) => c.id === id);
const fuelText = (c) => FUEL_LABEL[c.fuel] || c.fuel;
const mpgUnit = (c) => (c.fuel === 'electric' ? 'MPGe' : 'MPG');
const subtitle = (c) => `${c.vintage ? c.year + ' classic' : 'Modern'} · ${TYPE_LABEL[c.type] || c.type} · ${fuelText(c)} · ${c.seats} seats`;

/* ---------- filters ---------- */
function fillSelect(id, values, labelFn = (v) => v) {
  const sel = $(id);
  values.forEach((v) => {
    const o = document.createElement('option');
    o.value = v;
    o.textContent = labelFn(v);
    sel.appendChild(o);
  });
}

function filters() {
  return {
    budget: Number($('f-budget').value),
    fuel: $('f-fuel').value,
    seats: Number($('f-seats').value) || 0,
    type: $('f-type').value,
    brand: $('f-brand').value,
    era: $('f-era').value,
    sort: $('f-sort').value,
  };
}

function matches(f) {
  const list = CARS.filter((c) =>
    (!onlyIds || onlyIds.includes(c.id)) &&
    c.price <= f.budget &&
    (!f.fuel || c.fuel === f.fuel) &&
    c.seats >= f.seats &&
    (!f.type || c.type === f.type) &&
    (!f.brand || c.brand === f.brand) &&
    (!f.era || (f.era === 'classic') === !!c.vintage));
  const sorts = {
    resale: (a, b) => (a.vintage - b.vintage) || (b.resale_pct - a.resale_pct) || (a.price - b.price),
    price: (a, b) => a.price - b.price,
    priceDesc: (a, b) => b.price - a.price,
    name: (a, b) => a.name.localeCompare(b.name),
  };
  return list.sort(sorts[f.sort]);
}

function render() {
  const f = filters();
  $('budget-label').textContent = f.budget >= 100000 ? 'any' : money(f.budget);
  const list = matches(f);
  const grid = $('grid');
  grid.innerHTML = '';
  const line = $('result-line');
  line.textContent = list.length ? `Showing ${list.length} car${list.length === 1 ? '' : 's'}` : '';
  if (onlyIds) {
    const banner = document.createElement('span');
    banner.className = 'picks-banner';
    banner.innerHTML = "Alex's picks <button id='clear-picks'>Show all cars</button>";
    line.appendChild(banner);
    $('clear-picks').onclick = () => { onlyIds = null; render(); };
  }
  $('empty').hidden = list.length > 0;
  if (!list.length) showEmpty(f);

  list.forEach((c, i) => {
    const card = document.createElement('article');
    card.className = 'card';
    card.id = 'card-' + c.id;
    card.style.animationDelay = Math.min(i, 12) * 25 + 'ms';
    const saved = shortlist.includes(c.id);
    const cmp = compare.includes(c.id);
    card.innerHTML = `
      <button class="card-photo" data-open="${c.id}" aria-label="See details for ${c.name}" data-tip="Click for details">
        ${photo(c)}
        ${c.vintage ? '<span class="badge">Classic</span>' : ''}
      </button>
      <button class="heart" data-save="${c.id}" aria-pressed="${saved}" aria-label="Save ${c.name}" data-tip="${saved ? 'Remove from shortlist' : 'Save to shortlist'}">&#9829;</button>
      <div class="card-body">
        <h3>${c.name}</h3>
        <div class="meta">${subtitle(c)}</div>
        <div class="price">${money(c.price)}</div>
        <div class="keep" data-tip="A guess at how much of its price this car keeps after 5 years. Higher is better.">
          <span>Keeps ${c.resale_pct}%</span><div class="bar"><div style="width:${Math.min(100, c.resale_pct)}%"></div></div>
        </div>
        <div class="card-actions">
          <button class="pill${cmp ? ' on' : ''}" data-compare="${c.id}" data-tip="Pick two cars to see side by side">${cmp ? '&#10003; Added' : '&#8644; Compare'}</button>
          <button class="pill primary" data-open="${c.id}" data-tip="Price, payments and specs">Details</button>
        </div>
      </div>`;
    grid.appendChild(card);
  });
  $('shortlist-count').textContent = shortlist.length;
  $('compare-count').textContent = compare.length;
}

/* When nothing matches, say which single change would help (same idea as Alex). */
function showEmpty(f) {
  const tries = [
    ['budget', 'Raise the budget', { ...f, budget: 100000 }, () => { $('f-budget').value = 100000; }],
    ['fuel', 'Any fuel type', { ...f, fuel: '' }, () => { $('f-fuel').value = ''; }],
    ['seats', 'Any number of seats', { ...f, seats: 0 }, () => { $('f-seats').value = ''; }],
    ['type', 'Any body type', { ...f, type: '' }, () => { $('f-type').value = ''; }],
    ['brand', 'Any brand', { ...f, brand: '' }, () => { $('f-brand').value = ''; }],
    ['era', 'Modern and classic', { ...f, era: '' }, () => { $('f-era').value = ''; }],
  ];
  const box = $('empty-actions');
  box.innerHTML = '';
  let any = false;
  tries.forEach(([key, label, test, apply]) => {
    const active = key === 'budget' ? f.budget < 100000 : key === 'seats' ? f.seats : f[key];
    if (!active) return;
    const n = matches(test).length;
    if (!n) return;
    any = true;
    const b = document.createElement('button');
    b.className = 'pill';
    b.textContent = `${label} (${n} car${n === 1 ? '' : 's'})`;
    b.onclick = () => { apply(); render(); };
    box.appendChild(b);
  });
  $('empty-text').textContent = any
    ? 'Try loosening just one thing:'
    : 'Try the Reset button to start again.';
}

/* ---------- details window ---------- */
function payment(price, downPct, years, apr) {
  const loan = price * (1 - downPct / 100);
  const n = years * 12;
  const r = apr / 100 / 12;
  return r === 0 ? loan / n : (loan * r) / (1 - Math.pow(1 + r, -n));
}
function yearlyFuel(c, miles) {
  return (miles * 365 / c.mpg) * (FUEL_PRICE[c.fuel] ?? 3.5);   // same maths as cars.py
}

function updateMoney() {
  if (!current) return;
  const down = Number($('pay-down').value), years = Number($('pay-years').value), apr = Number($('pay-apr').value);
  const miles = Number($('miles').value);
  $('pay-down-l').textContent = `${down}% (${money(current.price * down / 100)})`;
  $('pay-years-l').textContent = years;
  $('pay-apr-l').textContent = apr + '%';
  $('miles-l').textContent = miles;
  $('pay-out').textContent = `About ${money(payment(current.price, down, years, apr))} a month`;
  $('fuel-out').textContent = `About ${money(yearlyFuel(current, miles))} a year on ${current.fuel === 'electric' ? 'charging' : 'fuel'}`;
}

function openCar(id) {
  const c = byId(id);
  if (!c) return;
  current = c;
  $('m-photo').innerHTML = photo(c).replace('<img ', '<img data-credit="1" ');
  $('m-credit').textContent = 'Loading photo credit...';
  showCredit(c);
  $('m-title').textContent = c.name;
  $('m-sub').textContent = subtitle(c);
  $('m-facts').innerHTML = [
    ['Price', money(c.price)], ['Seats', c.seats], ['Fuel', fuelText(c)], ['Mileage', `${c.mpg} ${mpgUnit(c)}`],
  ].map(([k, v]) => `<div class="fact"><small>${k}</small><b>${v}</b></div>`).join('');
  $('m-bar').style.width = Math.min(100, c.resale_pct) + '%';
  const worth = c.resale_value;
  $('m-resale').textContent = c.vintage
    ? `Expected to roughly hold its value (about ${money(worth)}), but classic prices can go up or down.`
    : `About ${money(worth)} (keeps ${c.resale_pct}% of its price). ${c.resale_source === 'published' ? 'Based on published figures.' : 'This one is an estimate.'}`;
  $('m-specs').hidden = true;
  refreshModalButtons();
  updateMoney();
  $('modal').showModal();
}

async function showCredit(c) {
  const el = $('m-credit');
  try {
    const res = await fetch(`/api/photo/${c.id}/credit`);
    if (!res.ok) throw new Error('none');
    const cr = await res.json();
    if (current !== c) return;
    el.textContent = 'Photo: ' + cr.author + ' · ' + cr.license + ' · ';
    const a = document.createElement('a');
    a.href = cr.page; a.target = '_blank'; a.rel = 'noopener'; a.textContent = 'source';
    el.appendChild(a);
  } catch (e) {
    if (current === c) el.textContent = 'Illustration: no free photo was found for this car.';
  }
}

function refreshModalButtons() {
  if (!current) return;
  const saved = shortlist.includes(current.id);
  $('m-save').innerHTML = saved ? '&#9829; Saved' : '&#9825; Save';
  $('m-save').classList.toggle('on', saved);
  const inCmp = compare.includes(current.id);
  $('m-compare').innerHTML = inCmp ? '&#10003; Added' : '&#8644; Compare';
  $('m-compare').classList.toggle('on', inCmp);
}

function chooseCar() {
  $('m-spec-rows').innerHTML = current.specs.map((s) => `<tr><td>${s.label}</td><td>${s.value}</td></tr>`).join('');
  $('m-specs').hidden = false;
  Sound.ding();
  $('m-specs').scrollIntoView({ behavior: 'smooth', block: 'center' });
  celebrate(false);
  /* Alex pops up with ideas for what to do next. */
  clearTimeout(chooseCar.timer);
  chooseCar.timer = setTimeout(() => {
    if (typeof Alex !== 'undefined' && current) Alex.offer(`Great choice! The ${current.name} is a beauty. Want to talk price and payments, or book a test drive?`,
      ['Make me a deal', 'Book a test drive', 'Show payment options']);
  }, 1400);
}

/* ---------- celebration, deal card, test-drive card ---------- */
function celebrate(big) {
  const colors = ['#ff6a1f', '#ffb347', '#ffffff', '#4cc9f0', '#f72585', '#7bd389'];
  const n = big ? 110 : 40;
  for (let i = 0; i < n; i++) {
    const p = document.createElement('i');
    p.className = 'confetti';
    p.style.left = Math.random() * 100 + 'vw';
    p.style.background = colors[i % colors.length];
    p.style.setProperty('--dx', (Math.random() * 160 - 80) + 'px');
    p.style.animationDuration = (1.8 + Math.random() * 1.6) + 's';
    p.style.animationDelay = Math.random() * 0.5 + 's';
    document.body.appendChild(p);
    setTimeout(() => p.remove(), 4200);
  }
  if (big) { Sound.rev(0, 1.4); setTimeout(() => Sound.ding(), 1200); }
}

function esc(t) { const d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML; }

function showTicket(html) {
  $('deal-body').innerHTML = html + '<div class="actions"><button class="pill" id="t-print">Print</button><button class="pill primary" id="t-close">Close</button></div>';
  $('t-close').onclick = () => $('deal-dlg').close();
  $('t-print').onclick = () => window.print();
  if ($('modal').open) $('modal').close();
  $('deal-dlg').showModal();
}

function showDeal(d) {
  showTicket(`<p class="stamp">Demo reservation</p><h2 id="deal-title">Deal locked in!</h2>
    <p class="big">${esc(d.car)}</p>
    <table><tbody>
      <tr><td>Reservation</td><td>${esc(d.id)}</td></tr>
      <tr><td>For</td><td>${esc(d.customer)}</td></tr>
      <tr><td>Agreed price</td><td>${money(d.price)}</td></tr>
      <tr><td>Down payment</td><td>${money(d.down_payment)}</td></tr>
      <tr><td>Loan</td><td>${d.term_months} months at ${d.apr_percent}% (example rate)</td></tr>
      <tr><td>Monthly payment</td><td><b>${money(d.monthly_payment)}</b></td></tr>
    </tbody></table>
    <p class="fine">Demo only: no real purchase was made and no payment was taken. Rates are examples, not an offer.</p>`);
  celebrate(true);
}

function showDrive(d) {
  showTicket(`<p class="stamp">Demo booking</p><h2 id="deal-title">Test drive booked!</h2>
    <p class="big">${esc(d.car)}</p>
    <table><tbody>
      <tr><td>Booking</td><td>${esc(d.id)}</td></tr>
      <tr><td>For</td><td>${esc(d.customer)}</td></tr>
      <tr><td>When</td><td>${esc(d.date)} at ${esc(d.time)}</td></tr>
    </tbody></table>
    <p class="fine">Demo only: nobody is actually waiting for you. Vroom anyway!</p>`);
  celebrate(false); Sound.rev(0, 1.0);
}

/* ---------- shortlist and compare ---------- */
function toggleSave(id) {
  const had = shortlist.includes(id);
  shortlist = had ? shortlist.filter((x) => x !== id) : [...shortlist, id];
  save('roarwell-shortlist', shortlist);
  if (!had) Sound.pop();
  toast(had ? 'Removed from shortlist' : 'Saved to shortlist');
  render();
  refreshModalButtons();
  if ($('shortlist-dlg').open) showShortlist();
}

function toggleCompare(id) {
  if (compare.includes(id)) compare = compare.filter((x) => x !== id);
  else {
    if (compare.length === 2) compare.shift();       // keep the two newest
    compare.push(id);
  }
  toast(compare.length === 2 ? 'Two cars picked. Press Compare at the top!' : 'Pick one more car to compare');
  render();
  refreshModalButtons();
}

function showShortlist() {
  const items = shortlist.map(byId).filter(Boolean);
  $('s-body').innerHTML = items.length
    ? items.map((c) => `
      <div class="sl-item">
        <div class="sl-art">${photo(c)}</div>
        <div class="grow"><b>${c.name}</b><div class="muted">${money(c.price)} · keeps ${c.resale_pct}%</div></div>
        <button class="pill" data-open="${c.id}">Details</button>
        <button class="pill ghost" data-save="${c.id}" aria-label="Remove ${c.name}">Remove</button>
      </div>`).join('')
    : '<p class="muted">Nothing saved yet. Click the heart on any car to save it here.</p>';
  if (!$('shortlist-dlg').open) $('shortlist-dlg').showModal();
}

function showCompare() {
  if (compare.length < 2) { toast('Pick two cars first: tick "Compare" on two cards'); return; }
  const [a, b] = compare.map(byId);
  const rows = [['Price', (c) => money(c.price), (x, y) => x.price < y.price ? 0 : x.price > y.price ? 1 : -1],
    ['Keeps after 5 years', (c) => c.resale_pct + '%', (x, y) => x.resale_pct > y.resale_pct ? 0 : x.resale_pct < y.resale_pct ? 1 : -1],
    ['Mileage', (c) => `${c.mpg} ${mpgUnit(c)}`, (x, y) => x.mpg > y.mpg ? 0 : x.mpg < y.mpg ? 1 : -1],
    ['Seats', (c) => c.seats, (x, y) => x.seats > y.seats ? 0 : x.seats < y.seats ? 1 : -1]];
  const cell = (c, win) => `<td class="${win ? 'win' : ''}">${win ? '&#9733; ' : ''}${c}</td>`;
  const body = rows.map(([label, fmt, better]) => {
    const w = better(a, b);
    return `<tr><td>${label}</td>${cell(fmt(a), w === 0)}${cell(fmt(b), w === 1)}</tr>`;
  }).join('');
  const extra = ['Engine', 'Power', 'Transmission', 'Drivetrain'].map((label) => {
    const v = (c) => (c.specs.find((s) => s.label === label) || {}).value || '-';
    return `<tr><td>${label}</td><td>${v(a)}</td><td>${v(b)}</td></tr>`;
  }).join('');
  $('c-body').innerHTML = `
    <div class="compare-photos">
      <div class="m-photo">${photo(a)}</div>
      <div class="m-photo">${photo(b)}</div>
    </div>
    <table><thead><tr><th></th><th>${a.name}</th><th>${b.name}</th></tr></thead>
    <tbody>${body}${extra}</tbody></table>
    <p class="muted">A star marks the better number in each row.</p>`;
  $('compare-dlg').showModal();
}

/* ---------- wiring ---------- */
function setToggle(btn, on) { btn.setAttribute('aria-pressed', String(on)); }

document.addEventListener('click', (e) => {
  const t = e.target.closest('[data-open],[data-save],[data-compare],[data-close]');
  if (!t) return;
  if (t.dataset.open) {
    ['shortlist-dlg', 'compare-dlg'].forEach((d) => $(d).open && $(d).close());
    openCar(t.dataset.open);
  } else if (t.dataset.save) toggleSave(t.dataset.save);
  else if (t.dataset.compare) toggleCompare(t.dataset.compare);
  else if (t.hasAttribute('data-close')) t.closest('dialog').close();
});
document.querySelectorAll('dialog').forEach((d) =>
  d.addEventListener('click', (e) => { if (e.target === d) d.close(); }));   // click outside to close

['f-budget', 'f-fuel', 'f-seats', 'f-type', 'f-brand', 'f-era', 'f-sort'].forEach((id) => $(id).addEventListener('input', render));
$('f-reset').onclick = () => {
  $('f-budget').value = 100000;
  ['f-fuel', 'f-seats', 'f-type', 'f-brand', 'f-era'].forEach((id) => { $(id).value = ''; });
  $('f-sort').value = 'resale';
  render();
};
['pay-down', 'pay-years', 'pay-apr', 'miles'].forEach((id) => $(id).addEventListener('input', updateMoney));
$('m-save').onclick = () => toggleSave(current.id);
$('m-compare').onclick = () => toggleCompare(current.id);
$('m-choose').onclick = chooseCar;
$('m-deal').onclick = () => { $('modal').close(); typeof Alex !== 'undefined' && Alex.open(`I'd like to make a deal on the ${current.name}`); };
$('m-drive').onclick = () => { $('modal').close(); typeof Alex !== 'undefined' && Alex.open(`I'd like to book a test drive for the ${current.name}`); };
$('btn-shortlist').onclick = showShortlist;
$('m-ask').onclick = () => { $('modal').close(); typeof Alex !== 'undefined' && Alex.open(`Tell me about the ${current.name}`); };
$('hero-alex').onclick = () => { if (typeof Alex !== 'undefined') Alex.open(); else toast('Alex is still loading, try again in a second'); };
$('btn-compare').onclick = showCompare;
$('btn-racers').onclick = () => { const on = !Racers.enabled; Racers.setEnabled(on); setToggle($('btn-racers'), on); };
$('btn-sound').onclick = () => { const on = !Sound.enabled; Sound.set(on); setToggle($('btn-sound'), on); if (on) Sound.pop(); };

async function start() {
  setToggle($('btn-racers'), Racers.enabled);
  setToggle($('btn-sound'), Sound.enabled);
  try {
    const res = await fetch('/api/cars');
    if (!res.ok) throw new Error('bad status ' + res.status);
    const data = await res.json();
    CARS = data.cars;
    FUEL_PRICE = data.fuel_price;
    fillSelect('f-fuel', [...new Set(CARS.map((c) => c.fuel))], (v) => FUEL_LABEL[v] || v);
    fillSelect('f-type', [...new Set(CARS.map((c) => c.type))], (v) => TYPE_LABEL[v] || v);
    fillSelect('f-brand', data.brands);
    shortlist = shortlist.filter(byId);
    render();
  } catch (err) {
    $('result-line').textContent = 'Could not load the cars. Is the server running?';
    console.error(err);
  }
  Racers.start();
  document.dispatchEvent(new Event('roarwell-ready'));
}

/* Things other scripts (Alex, the intro) are allowed to use. */
window.Site = {
  openCar,
  chooseCar: (id) => { openCar(id); chooseCar(); },
  /* Show only these cars on the page (Alex's picks), and scroll to the grid. */
  showOnly(ids) {
    onlyIds = ids.length ? ids : null;
    render();
    document.querySelector('.result-line').scrollIntoView({ behavior: 'smooth', block: 'start' });
  },
  /* Make sure a car is on the shortlist (never removes it). */
  save(id) { if (byId(id) && !shortlist.includes(id)) toggleSave(id); },
  byId: (id) => byId(id),
  showDeal,
  showDrive,
  photo,
};
start();
