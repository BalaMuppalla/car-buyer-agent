/* alex.js - the chat window for Alex, the AI agent.
   This file only shows messages and carries Alex's memory. The thinking happens on the server (agent.py).
   Each time you send a message we also send the recent chat and what Alex has learned about you. */

const Alex = (() => {
  const $ = (id) => document.getElementById(id);
  const log = $('alex-log'), quick = $('alex-quick'), input = $('alex-input'), send = $('alex-send');
  const money = (n) => '$' + Math.round(n).toLocaleString('en-US');

  let memory = {};
  let history = [];          // [{role: 'user'|'alex', text}]
  let started = false;
  let busy = false;

  function scroll() { log.scrollTop = log.scrollHeight; }

  function say(text, who) {
    const m = document.createElement('div');
    m.className = 'msg ' + who;
    m.textContent = text;
    log.appendChild(m);
    scroll();
    return m;
  }

  function problem(text, detail) {
    const m = say(text, 'alex');
    m.classList.add('problem');
    if (detail) {
      const d = document.createElement('details');
      d.innerHTML = '<summary>Technical details</summary>';
      const pre = document.createElement('pre');
      pre.textContent = detail;
      d.appendChild(pre);
      m.appendChild(d);
    }
  }

  function setChips(options) {
    quick.innerHTML = '';
    (options || []).forEach((o) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = o;
      b.onclick = () => ask(o);
      quick.appendChild(b);
    });
  }

  function carCards(cars) {
    if (!cars || !cars.length) return;
    const box = document.createElement('div');
    box.className = 'mini-cars';
    cars.forEach((c) => {
      const full = window.Site && Site.byId(c.id);
      if (!full) return;
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'mini';
      b.innerHTML = `<span class="thumb">${Site.photo(full)}</span>
        <span class="info"><b></b><small></small></span><span class="go">View</span>`;
      b.querySelector('b').textContent = c.name;
      b.querySelector('small').textContent = `${money(c.price)} · worth about ${money(c.resale_value)} after 5 years`;
      b.onclick = () => Site.openCar(c.id);
      box.appendChild(b);
    });
    if (box.children.length) { log.appendChild(box); scroll(); }
  }

  /* Things Alex asked the website to do. */
  function runActions(actions) {
    (actions || []).forEach((a) => {
      if (!window.Site) return;
      if (a.type === 'show') { Site.showOnly(a.ids); }
      else if (a.type === 'open') { Site.openCar(a.id); }
      else if (a.type === 'save') { Site.save(a.id); }
      else if (a.type === 'deal') { Site.showDeal(a.deal); }
      else if (a.type === 'testdrive') { Site.showDrive(a.drive); }
    });
    if ((actions || []).some((a) => a.type === 'show')) toggle(false);
  }

  function typing() {
    const m = document.createElement('div');
    m.className = 'msg alex typing';
    m.innerHTML = '<i></i><i></i><i></i>';
    log.appendChild(m);
    scroll();
    return m;
  }

  let startP = null;
  function begin() { return (startP = startP || doBegin()); }
  async function doBegin() {
    started = true;
    const wait = typing();
    try {
      const data = await (await fetch('/api/alex/start')).json();
      wait.remove();
      say(data.reply, 'alex');
      history.push({ role: 'alex', text: data.reply });
      if (!data.ok) problem(data.problem || 'Alex could not start.', data.detail);
      setChips(data.chips);
    } catch (e) {
      wait.remove();
      problem('I could not reach the server. Is it still running in your terminal?', String(e));
    }
    input.focus();
  }

  async function ask(text) {
    text = (text || '').trim();
    if (!text || busy) return;
    busy = true; send.disabled = true;
    say(text, 'me');
    setChips([]);
    input.value = '';
    const wait = typing();
    try {
      const res = await fetch('/api/agent', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, history: history.slice(-10), memory }),
      });
      const data = await res.json();
      wait.remove();
      history.push({ role: 'user', text });
      if (data.ok) {
        memory = data.memory || memory;
        say(data.reply, 'alex');
        history.push({ role: 'alex', text: data.reply });
        carCards(data.cards);
        setChips(data.chips);
        runActions(data.ui);
      } else {
        problem(data.reply + ' ' + (data.problem || ''), data.detail);
      }
    } catch (e) {
      wait.remove();
      problem('Sorry, I lost the connection. Please try again.', String(e));
    }
    busy = false; send.disabled = false;
    scroll();
    input.focus();
  }

  function toggle(open) {
    const panel = $('alex-panel');
    const on = open ?? !panel.classList.contains('open');
    panel.classList.toggle('open', on);
    $('alex-fab').style.display = on ? 'none' : '';
    if (on && !started) begin();
    if (on) input.focus();
  }

  function reset() {
    log.innerHTML = ''; setChips([]); memory = {}; history = []; started = false; startP = null; begin();
  }

  $('alex-fab').onclick = () => toggle(true);
  $('alex-close').onclick = () => toggle(false);
  $('alex-reset').onclick = reset;
  $('alex-form').addEventListener('submit', (e) => { e.preventDefault(); ask(input.value); });

  return {
    /* Open the chat, and optionally send a first message right away. */
    /* Alex speaks first (for example after the customer picks a car). */
    async offer(text, chips) {
      toggle(true);
      await begin();                        // let the greeting come first
      say(text, 'alex');
      history.push({ role: 'alex', text });
      setChips(chips || []);
    },
    open(text) {
      toggle(true);
      if (text) {
        const go = () => ask(text);
        if (started && !log.querySelector('.typing')) go(); else setTimeout(go, 900);
      }
    },
  };
})();
window.Alex = Alex;   // so app.js can call Alex.open(...) and Alex.offer(...)
