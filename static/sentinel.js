(() => {
  const $ = (id) => document.getElementById(id);
  const views = [...document.querySelectorAll('.view')];
  const nav = [...document.querySelectorAll('.nav-btn')];
  let latest = null;

  function showView(name) {
    views.forEach((view) => view.classList.toggle('active', view.dataset.panel === name));
    nav.forEach((button) => button.classList.toggle('active', button.dataset.view === name));
    if (name === 'signals' && latest) drawChart(latest.rate_history || [], latest.score_history || []);
  }

  nav.forEach((button) => button.addEventListener('click', () => showView(button.dataset.view)));

  function toast(message) {
    const el = $('toast');
    el.textContent = message;
    el.classList.add('show');
    window.clearTimeout(toast.timer);
    toast.timer = window.setTimeout(() => el.classList.remove('show'), 2400);
  }

  function setState(state) {
    const raw = String(state || '').toUpperCase();
    const armed = raw.includes('ARMED');
    const lockdown = raw.includes('LOCKDOWN');
    $('node-state').textContent = lockdown ? 'LOCKDOWN' : armed ? 'ARMED' : 'CALIBRATING';
    $('hero-state').textContent = lockdown ? 'LINE ISOLATED' : armed ? 'ARMED / WATCHING' : 'CALIBRATING';
    $('hero-copy').textContent = lockdown ? 'Containment is active. Review the journal.' : armed ? 'The node is watching for a second signal.' : 'Building a trusted baseline before decisions.';
    $('status-dot').style.background = lockdown ? 'var(--red)' : armed ? 'var(--green)' : 'var(--amber)';
    $('signal-ring').classList.toggle('alert', lockdown);
    $('watch-note').textContent = lockdown ? 'Containment active; operator review required.' : armed ? 'Evidence first; containment second.' : 'Learning normal traffic before decisions.';
  }

  function drawChart(rate, score) {
    const canvas = $('signal-chart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width; const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#0a1016'; ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = '#1c2a36'; ctx.lineWidth = 1;
    for (let i = 1; i < 5; i += 1) { const y = Math.round((h / 5) * i); ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
    const plot = (values, color, max) => {
      if (!values.length) return;
      ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.beginPath();
      values.forEach((value, index) => { const x = (index / Math.max(1, values.length - 1)) * (w - 12) + 6; const y = h - 6 - (Math.max(0, Math.min(max, Number(value) || 0)) / max) * (h - 12); if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); });
      ctx.stroke();
    };
    plot(rate, '#79d8e6', 20); plot(score, '#f18486', 1);
    const lastRate = Number(rate.at(-1) || 0).toFixed(1); const lastScore = Number(score.at(-1) || 0).toFixed(2);
    $('rate-now').textContent = lastRate; $('score-now').textContent = lastScore; $('ring-value').textContent = lastScore;
  }

  function renderJournal(logs) {
    const journal = $('journal');
    if (!logs || !logs.length) { journal.innerHTML = '<div class="empty">Waiting for the first event…</div>'; return; }
    journal.innerHTML = logs.slice(-12).map((line) => `<div class="journal-line">${escapeHtml(line)}</div>`).join('');
    journal.scrollTop = journal.scrollHeight;
  }

  function escapeHtml(value) { return String(value).replace(/[&<>'"]/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char])); }

  function render(data) {
    latest = data;
    setState(data.state_str);
    const rates = data.rate_history || []; const scores = data.score_history || [];
    const score = Number(scores.at(-1) || 0);
    $('metric-packets').textContent = data.packets ?? 0;
    $('metric-anomalies').textContent = data.anomalies ?? 0;
    $('metric-blocks').textContent = data.blocks ?? 0;
    $('metric-uptime').textContent = data.uptime || '00:00:00';
    $('health-ledger').textContent = `${data.blocks ?? 0} BLOCKS`;
    $('score-now').textContent = score.toFixed(2); $('ring-value').textContent = score.toFixed(2);
    renderJournal(data.logs || []);
    if ($('[data-panel="signals"].active')) drawChart(rates, scores);
  }

  async function poll() {
    try {
      const response = await fetch('/api/telemetry', { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      render(await response.json());
      $('connection-label').textContent = 'LOCAL LINK / LIVE';
    } catch (error) {
      $('connection-label').textContent = 'LOCAL LINK / RETRYING';
      $('node-state').textContent = 'OFFLINE';
      $('status-dot').style.background = 'var(--red)';
    }
  }

  async function post(url, body = {}) {
    const response = await fetch(url, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.status || `HTTP ${response.status}`);
    return payload;
  }

  document.querySelectorAll('[data-inject]').forEach((button) => button.addEventListener('click', async () => {
    try { await post('/api/inject', { attack: button.dataset.inject }); toast('Simulation scheduled'); }
    catch (error) { toast(`Action rejected: ${error.message}`); }
  }));
  $('tamper-btn').addEventListener('click', async () => {
    try { await post('/api/tamper'); toast('Tamper signal sent'); }
    catch (error) { toast(`Action rejected: ${error.message}`); }
  });
  const pinDialog = $('pin-dialog');
  $('pin-btn').addEventListener('click', () => { $('pin-input').value = ''; $('pin-result').textContent = ''; pinDialog.showModal(); setTimeout(() => $('pin-input').focus(), 50); });
  $('pin-form').addEventListener('submit', async (event) => {
    if (event.submitter && event.submitter.value === 'cancel') return;
    event.preventDefault();
    try { await post('/api/pin', { pin: $('pin-input').value }); pinDialog.close(); toast('Recovery authorized'); }
    catch (error) { $('pin-result').textContent = 'PIN rejected. Try again.'; }
  });

  setInterval(poll, 500); poll();
  setInterval(() => { $('clock').textContent = new Date().toLocaleTimeString([], {hour12: false}); }, 1000);
})();
