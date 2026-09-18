/* ══════════════════════════════════════════════════════════════
   BlackBox Sentinel — V2 Tactical Console JavaScript
   Handles: Telemetry polling, view switching, canvas graphs,
            action buttons, PIN pad, toast notifications
   ══════════════════════════════════════════════════════════════ */

const COL = {
    violet: '#8B5CF6', violetDark: '#1A1030',
    coral: '#FF4F6D', coralDark: '#2A0F18',
    emerald: '#34D399',
    amber: '#F59E0B',
    border: '#1A1A2E', borderGlow: '#2D2B55',
    bg: '#050508', surface: '#0C0C14',
    text: '#FFFFFF', textDim: '#6B7280', textFaint: '#374151'
};

const state = {
    pinBuffer: '',
    rateHistory: [],
    scoreHistory: [],
    peakRate: 0,
    relayState: 'ENGAGED'
};

// ── Polling ──
setInterval(fetchTelemetry, 500);
setInterval(fetchHardwareStats, 2000);

// ══════════════════════════════════════════════════════════════
//  DATA FETCHING
// ══════════════════════════════════════════════════════════════

async function fetchTelemetry() {
    try {
        const res = await fetch('/api/telemetry');
        if (!res.ok) return;
        const d = await res.json();

        state.rateHistory = d.rate_history || [];
        state.scoreHistory = d.score_history || [];

        // ── Overview widgets ──
        setText('ov-packets', d.packets.toLocaleString());
        setText('ov-anomalies', d.anomalies);
        setText('ov-blocks', d.blocks);
        setText('ov-uptime', d.uptime);

        // ── Status badge ──
        const badge = document.getElementById('status-badge');
        badge.textContent = d.state_str;
        badge.className = 'status-badge';
        if (d.state_str.includes('CALIBRATING')) badge.classList.add('badge-amber');
        else if (d.state_str.includes('ARMED')) badge.classList.add('badge-emerald');
        else badge.classList.add('badge-coral');

        // ── Footer status ──
        const footer = document.getElementById('footer-status');
        if (d.state_str.includes('LOCKDOWN')) {
            footer.textContent = '🚨 LOCKDOWN ACTIVE';
            footer.style.color = COL.coral;
            state.relayState = 'ISOLATED';
        } else {
            footer.textContent = 'STATUS: NORMAL';
            footer.style.color = COL.textDim;
            state.relayState = 'ENGAGED';
        }

        // ── Threat gauge ──
        const score = d.score_history.length > 0 ? d.score_history[d.score_history.length - 1] : 0;
        drawThreatGauge(Math.abs(score));

        // ── Sparkline ──
        drawSparkline();

        // ── Signals view ──
        const rate = d.rate_history.length > 0 ? d.rate_history[d.rate_history.length - 1] : 0;
        setText('sig-pkt-rate', rate.toFixed(1));
        setText('sig-score', Math.abs(score).toFixed(3));
        state.peakRate = Math.max(state.peakRate, ...d.rate_history);
        setText('sig-peak', `PEAK ${state.peakRate.toFixed(1)}/s ↗`);
        const avg = d.score_history.length > 0
            ? (d.score_history.reduce((a, b) => a + Math.abs(b), 0) / d.score_history.length)
            : 0;
        setText('sig-avg', `AVG SCORE ${avg.toFixed(3)} —`);
        drawSignalsGraph();

        // ── Health view ──
        updateHealthView(d);

        // ── Journal ──
        updateJournal(d.logs);

    } catch (e) {
        console.error('Telemetry fetch error:', e);
    }
}

async function fetchHardwareStats() {
    try {
        const res = await fetch('/api/system_stats');
        if (!res.ok) return;
        const d = await res.json();
        setText('hw-rpi-temp', d.temp + '°C');
        setText('hw-esp-temp', d.esp32_temp + '°C');
        setText('hw-ram', d.ram + '%');
    } catch (e) { /* silently fail */ }
}

// ══════════════════════════════════════════════════════════════
//  VIEW SWITCHING
// ══════════════════════════════════════════════════════════════

function switchView(viewId) {
    document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
    document.getElementById('view-' + viewId).classList.add('active');
    const views = ['overview', 'signals', 'actions', 'journal', 'health'];
    const idx = views.indexOf(viewId);
    if (idx >= 0) document.querySelectorAll('.nav-btn')[idx].classList.add('active');
}

// ══════════════════════════════════════════════════════════════
//  CANVAS: THREAT GAUGE
// ══════════════════════════════════════════════════════════════

function drawThreatGauge(score) {
    const c = document.getElementById('gauge-canvas');
    if (!c) return;
    const ctx = c.getContext('2d');
    const cx = 50, cy = 38, r = 30;
    ctx.clearRect(0, 0, c.width, c.height);

    // Track arc
    ctx.beginPath();
    ctx.arc(cx, cy, r, degToRad(210), degToRad(-30), true);
    ctx.strokeStyle = COL.border;
    ctx.lineWidth = 5;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Value arc
    const s = Math.min(1.0, Math.max(0.0, score));
    const color = s < 0.3 ? COL.emerald : (s < 0.7 ? COL.amber : COL.coral);
    const endAngle = 210 - 240 * s;
    if (s > 0.01) {
        ctx.beginPath();
        ctx.arc(cx, cy, r, degToRad(210), degToRad(endAngle), true);
        ctx.strokeStyle = color;
        ctx.lineWidth = 5;
        ctx.lineCap = 'round';
        ctx.stroke();
    }

    // Center text
    ctx.fillStyle = COL.text;
    ctx.font = 'bold 11px Consolas';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(s.toFixed(2), cx, cy - 2);
}

function degToRad(deg) { return (deg * Math.PI) / 180; }

// ══════════════════════════════════════════════════════════════
//  CANVAS: MINI SPARKLINE (Overview)
// ══════════════════════════════════════════════════════════════

function drawSparkline() {
    const c = document.getElementById('sparkline-canvas');
    if (!c) return;
    const ctx = c.getContext('2d');
    const w = c.offsetWidth || c.width;
    const h = c.height;
    c.width = w; // reset for HiDPI
    ctx.clearRect(0, 0, w, h);

    const data = state.rateHistory;
    if (data.length < 2) return;
    const maxVal = Math.max(...data, 1.0);

    const pts = data.map((v, i) => ({
        x: 4 + i * (w - 8) / Math.max(1, data.length - 1),
        y: h - 4 - (v / maxVal) * (h - 12)
    }));

    // Fill
    ctx.beginPath();
    ctx.moveTo(pts[0].x, h);
    pts.forEach(p => ctx.lineTo(p.x, p.y));
    ctx.lineTo(pts[pts.length - 1].x, h);
    ctx.closePath();
    ctx.fillStyle = COL.violetDark;
    ctx.fill();

    // Line
    ctx.beginPath();
    pts.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
    ctx.strokeStyle = COL.violet;
    ctx.lineWidth = 1.5;
    ctx.stroke();
}

// ══════════════════════════════════════════════════════════════
//  CANVAS: SIGNALS GRAPH (Dual-axis)
// ══════════════════════════════════════════════════════════════

function drawSignalsGraph() {
    const c = document.getElementById('signals-canvas');
    if (!c) return;
    const ctx = c.getContext('2d');
    const w = c.offsetWidth || c.width;
    const h = c.offsetHeight || c.height;
    c.width = w;
    c.height = h;
    ctx.clearRect(0, 0, w, h);

    // Grid lines
    ctx.strokeStyle = COL.textFaint;
    ctx.setLineDash([2, 6]);
    for (let i = 0; i < 5; i++) {
        const y = 8 + i * (h - 16) / 4;
        ctx.beginPath(); ctx.moveTo(4, y); ctx.lineTo(w - 4, y); ctx.stroke();
    }
    ctx.setLineDash([]);

    function drawSeries(values, lineColor, fillColor, scale) {
        if (values.length < 2) return;
        const pts = values.map((v, i) => ({
            x: 6 + i * (w - 12) / Math.max(1, values.length - 1),
            y: h - 8 - Math.min(1.0, Math.max(0.0, v / scale)) * (h - 24)
        }));

        // Fill
        ctx.beginPath();
        ctx.moveTo(pts[0].x, h - 4);
        pts.forEach(p => ctx.lineTo(p.x, p.y));
        ctx.lineTo(pts[pts.length - 1].x, h - 4);
        ctx.closePath();
        ctx.fillStyle = fillColor;
        ctx.fill();

        // Line
        ctx.beginPath();
        pts.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
        ctx.strokeStyle = lineColor;
        ctx.lineWidth = 2;
        ctx.stroke();
    }

    drawSeries(state.rateHistory, COL.violet, COL.violetDark, 20.0);
    drawSeries(state.scoreHistory.map(Math.abs), COL.coral, COL.coralDark, 1.0);
}

// ══════════════════════════════════════════════════════════════
//  CANVAS: CHAIN INTEGRITY RING
// ══════════════════════════════════════════════════════════════

function drawIntegrityRing() {
    const c = document.getElementById('integrity-canvas');
    if (!c) return;
    const ctx = c.getContext('2d');
    ctx.clearRect(0, 0, c.width, c.height);
    const cx = 35, cy = 30, r = 22;

    // Track
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = COL.border;
    ctx.lineWidth = 4;
    ctx.stroke();

    // Full ring (always valid for now)
    ctx.beginPath();
    ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2);
    ctx.strokeStyle = COL.emerald;
    ctx.lineWidth = 4;
    ctx.stroke();

    // Text
    ctx.fillStyle = COL.emerald;
    ctx.font = 'bold 8px Consolas';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('VALID', cx, cy);
}

// ══════════════════════════════════════════════════════════════
//  HEALTH VIEW UPDATE
// ══════════════════════════════════════════════════════════════

function updateHealthView(d) {
    // Relay status
    const relayDot = document.getElementById('h-relay-dot');
    const relayStatus = document.getElementById('h-relay-status');
    const ctrlRelay = document.getElementById('h-ctrl-relay');

    if (d.state_str.includes('LOCKDOWN')) {
        relayDot.className = 'pill-dot text-coral';
        relayStatus.className = 'pill-status text-coral';
        relayStatus.textContent = 'ISOLATED';
        ctrlRelay.textContent = 'ISOLATED';
        ctrlRelay.className = 'text-coral';
    } else {
        relayDot.className = 'pill-dot text-emerald';
        relayStatus.className = 'pill-status text-emerald';
        relayStatus.textContent = 'ARMED';
        ctrlRelay.textContent = 'ENGAGED';
        ctrlRelay.className = 'text-emerald';
    }

    // Tamper
    const tamper = document.getElementById('h-ctrl-tamper');
    if (d.tamper_state === 'BREACHED') {
        tamper.textContent = 'BREACHED';
        tamper.className = 'text-coral';
    } else {
        tamper.textContent = 'SECURE';
        tamper.className = 'text-emerald';
    }

    // Link
    const link = document.getElementById('h-ctrl-link');
    link.textContent = d.link_state || 'UNKNOWN';
    link.className = d.link_state === 'HEALTHY' ? 'text-emerald' : 'text-amber';

    // Blocks
    setText('h-ctrl-blocks', d.blocks);
    setText('h-chain-info', `${d.blocks} blocks · SHA-256`);

    drawIntegrityRing();
}

// ══════════════════════════════════════════════════════════════
//  JOURNAL
// ══════════════════════════════════════════════════════════════

function updateJournal(logs) {
    const container = document.getElementById('journal-log');
    if (!container) return;

    // Only re-render if count changed
    if (container.childElementCount === logs.length) return;

    container.innerHTML = '';
    logs.forEach(log => {
        const div = document.createElement('div');
        div.className = 'log-entry';

        if (/ANOMALY|ALERT|LOCKDOWN|TAMPER/.test(log)) div.classList.add('log-alert');
        else if (/RELAY|CUT|ISOLATED|ZEROIZ/.test(log)) div.classList.add('log-critical');
        else if (/✅|ARMED|RESTORED|complete|ACCEPTED/.test(log)) div.classList.add('log-success');
        else if (/⚡|SIMULATOR|injection|Scheduled/.test(log)) div.classList.add('log-warning');
        else if (/Receipt|hash|Hash|AI|VISION/.test(log)) div.classList.add('log-info');
        else div.classList.add('log-default');

        div.textContent = log;
        container.appendChild(div);
    });
    container.scrollTop = container.scrollHeight;
    setText('journal-count', `${logs.length} entries`);
}

// ══════════════════════════════════════════════════════════════
//  ACTION HANDLERS
// ══════════════════════════════════════════════════════════════

async function injectAttack(type) {
    showToast(`⚡ Injecting ${type}...`);
    try {
        const res = await fetch('/api/inject', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ attack: type })
        });
        if (res.ok) showToast(`✅ ${type} injected — watch for containment`);
        else showToast('❌ Injection failed');
    } catch (e) {
        showToast('❌ Network error');
    }
}

async function triggerBreach() {
    showToast('🚨 Triggering casing breach...');
    try {
        const res = await fetch('/api/tamper', { method: 'POST' });
        if (res.ok) showToast('🚨 Tamper event triggered — keys zeroized');
        else showToast('❌ Breach trigger failed');
    } catch (e) {
        showToast('❌ Network error');
    }
}

async function toggleManualLineCut() {
    showToast('✂ Isolating relay...');
    try {
        const res = await fetch('/api/relay_trigger', { method: 'POST' });
        if (res.ok) {
            const d = await res.json();
            showToast(`⚡ ${d.message}`);
        }
    } catch (e) {
        showToast('❌ Relay trigger failed');
    }
}

async function triggerHwCheck() {
    showToast('🔧 Running hardware check...');
    try {
        const res = await fetch('/api/hardware_check', { method: 'POST' });
        if (res.ok) showToast('✅ Hardware check complete');
        else showToast('❌ Hardware check failed');
    } catch (e) {
        showToast('❌ Network error');
    }
}

// ══════════════════════════════════════════════════════════════
//  PIN PAD
// ══════════════════════════════════════════════════════════════

function showPinPad() {
    state.pinBuffer = '';
    document.getElementById('pin-display').textContent = '_ _ _ _';
    document.getElementById('pin-display').style.color = COL.text;
    document.getElementById('pin-modal').classList.add('active');
}

function hidePinPad() {
    document.getElementById('pin-modal').classList.remove('active');
}

function pressPin(d) {
    if (state.pinBuffer.length < 4) {
        state.pinBuffer += d;
        const display = Array.from(state.pinBuffer).map(() => '●').join(' ')
            + ' ' + Array(4 - state.pinBuffer.length).fill('_').join(' ');
        document.getElementById('pin-display').textContent = display.trim();
    }
}

function clearPin() {
    state.pinBuffer = '';
    document.getElementById('pin-display').textContent = '_ _ _ _';
    document.getElementById('pin-display').style.color = COL.text;
}

async function submitPin() {
    try {
        const res = await fetch('/api/pin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pin: state.pinBuffer })
        });
        if (res.ok) {
            hidePinPad();
            showToast('✅ PIN accepted — Relay Restored & ARMED');
        } else {
            state.pinBuffer = '';
            document.getElementById('pin-display').textContent = 'REJECT';
            document.getElementById('pin-display').style.color = COL.coral;
            setTimeout(() => {
                document.getElementById('pin-display').textContent = '_ _ _ _';
                document.getElementById('pin-display').style.color = COL.text;
            }, 1000);
        }
    } catch (e) {
        showToast('❌ Network error');
        clearPin();
    }
}

// ══════════════════════════════════════════════════════════════
//  TOAST
// ══════════════════════════════════════════════════════════════

let toastTimer;
function showToast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove('show'), 3200);
}

// ══════════════════════════════════════════════════════════════
//  UTILITIES
// ══════════════════════════════════════════════════════════════

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}
