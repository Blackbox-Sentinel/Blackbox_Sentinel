/**
 * BLACKBOX SENTINEL — Visual Hardware Simulator Client
 * Polls /api/state every 150ms and updates the interactive schematic.
 */

let prevState = null;
let canvasCtx = null;

document.addEventListener("DOMContentLoaded", () => {
    const c = document.getElementById("score-mini-canvas");
    if (c) canvasCtx = c.getContext("2d");
    pollState();
});

// ── API Communication ────────────────────────────────────────────────────
function apiAction(action) {
    fetch(`/api/action?do=${action}`)
        .then(r => r.json())
        .then(d => console.log("Action:", d))
        .catch(e => console.error("API error:", e));
}

function pollState() {
    fetch("/api/state")
        .then(r => r.json())
        .then(state => {
            updateUI(state);
            prevState = state;
        })
        .catch(() => {});
    setTimeout(pollState, 150);
}

// ── Master UI Update ─────────────────────────────────────────────────────
function updateUI(s) {
    // Device State Badge
    const ring = document.getElementById("state-ring");
    const sname = document.getElementById("state-name");
    const sphase = document.getElementById("state-phase");
    sname.textContent = s.device_state;
    sphase.textContent = `Phase: ${s.phase}`;
    ring.className = "state-ring";
    if (s.device_state === "ARMED") { ring.classList.add("armed"); sname.style.color = "#38b44a"; }
    else if (s.device_state === "LOCKDOWN") { ring.classList.add("lockdown"); sname.style.color = "#df382c"; }
    else if (s.device_state === "CALIBRATING") { ring.classList.add("calibrating"); sname.style.color = "#f39c12"; }
    else { sname.style.color = "#8a91a4"; }

    // Metrics
    document.getElementById("mm-pkts").textContent = s.packets_total;
    document.getElementById("mm-anomalies").textContent = s.anomalies_total;
    document.getElementById("mm-blocks").textContent = s.ledger_blocks.length;
    document.getElementById("mm-sms").textContent = s.cellular.sms_log.length;

    // Pi Module States
    document.getElementById("pi-bridge-state").textContent = s.bridge.state;
    document.getElementById("pi-ml-state").textContent = s.device_state;
    document.getElementById("pi-ledger-count").textContent = `${s.ledger_blocks.length} blocks`;
    document.getElementById("pi-pkt-count").textContent = s.packets_total;

    const piMlVal = document.getElementById("pi-ml-state");
    piMlVal.style.color = s.device_state === "ARMED" ? "#38b44a" :
                          s.device_state === "LOCKDOWN" ? "#df382c" :
                          s.device_state === "CALIBRATING" ? "#f39c12" : "#8a91a4";

    // Relay
    const relayStatus = document.getElementById("relay-status");
    const relayArm = document.getElementById("relay-arm");
    const relayContact = document.getElementById("relay-contact");
    const chipRelay = document.getElementById("chip-relay");

    if (s.relay.state === "ISOLATED") {
        relayStatus.textContent = "ISOLATED (CUT)";
        relayStatus.style.color = "#df382c";
        relayArm.classList.add("open");
        relayContact.classList.add("open");
        chipRelay.classList.add("state-alert");
        chipRelay.classList.remove("state-active");
    } else {
        relayStatus.textContent = "ENGAGED";
        relayStatus.style.color = "#38b44a";
        relayArm.classList.remove("open");
        relayContact.classList.remove("open");
        chipRelay.classList.remove("state-alert");
        chipRelay.classList.add("state-active");
    }

    // Ethernet status
    document.getElementById("eth0-status").textContent = s.bridge.eth0;
    document.getElementById("eth1-status").textContent = s.bridge.eth1;

    const eth1Status = document.getElementById("eth1-status");
    const chipEth1 = document.getElementById("chip-eth1");
    const wireEth1Line = document.getElementById("wire-eth1-line");

    if (s.bridge.eth1 === "CUT") {
        eth1Status.style.color = "#df382c";
        eth1Status.textContent = "CUT";
        chipEth1.classList.add("state-alert");
        if (wireEth1Line) wireEth1Line.classList.add("cut");
    } else {
        eth1Status.style.color = "#38b44a";
        chipEth1.classList.remove("state-alert");
        if (wireEth1Line) wireEth1Line.classList.remove("cut");
    }

    // Data flow animation
    const flowEth0 = document.getElementById("flow-eth0");
    const flowRelay = document.getElementById("flow-relay");
    const flowEth1 = document.getElementById("flow-eth1");
    const isFlowing = s.device_state !== "IDLE" && s.device_state !== "LOCKDOWN";
    [flowEth0, flowRelay, flowEth1].forEach(f => {
        if (f) {
            if (isFlowing) { f.classList.add("active"); f.classList.remove("stopped"); }
            else { f.classList.remove("active"); f.classList.add("stopped"); }
        }
    });

    // LED
    const ledBulb = document.getElementById("led-bulb");
    const ledStatus = document.getElementById("led-status");
    ledBulb.className = "led-bulb";
    if (s.led.state === "SOLID" && s.led.color === "green") {
        ledBulb.classList.add("solid-green");
        ledStatus.textContent = "SOLID GREEN";
        ledStatus.style.color = "#38b44a";
    } else if ((s.led.state === "BLINK" || s.led.state === "BLINK_FAST") && s.led.color === "red") {
        ledBulb.classList.add("blink-red");
        ledStatus.textContent = "BLINK RED";
        ledStatus.style.color = "#df382c";
    } else {
        ledStatus.textContent = "OFF";
        ledStatus.style.color = "#8a91a4";
    }

    // Tamper Grid
    const tamperGrid = document.getElementById("tamper-grid");
    const tamperStatus = document.getElementById("tamper-status");
    const chipTamper = document.getElementById("chip-tamper");

    if (s.tamper.state === "BREACHED") {
        tamperGrid.classList.add("breached");
        tamperStatus.textContent = "BREACHED";
        tamperStatus.style.color = "#df382c";
        chipTamper.classList.add("state-alert");
        chipTamper.style.borderColor = "#df382c";
    } else {
        tamperGrid.classList.remove("breached");
        tamperStatus.textContent = "CONTINUOUS";
        tamperStatus.style.color = "#38b44a";
        chipTamper.classList.remove("state-alert");
        chipTamper.style.borderColor = "#38b44a";
    }

    // SIM800L
    document.getElementById("sim-sms-count").textContent = s.cellular.sms_log.length;

    // ESP32 Mesh
    document.getElementById("esp-broadcast-count").textContent = s.mesh.broadcasts.length;
    const espMeshState = document.getElementById("esp-mesh-state");
    if (s.mesh.broadcasts.length > 0) {
        espMeshState.textContent = "BROADCASTING";
        espMeshState.style.color = "#f39c12";
    }

    // Keystore
    const ksIcon = document.getElementById("keystore-icon");
    const ksStatus = document.getElementById("keystore-status");
    const chipKs = document.getElementById("chip-keystore");
    if (s.keystore.state === "ZEROIZED") {
        ksIcon.textContent = "💀";
        ksStatus.textContent = "ZEROIZED";
        ksStatus.style.color = "#df382c";
        chipKs.classList.add("state-alert");
    } else {
        ksIcon.textContent = "🔐";
        ksStatus.textContent = "MOUNTED";
        ksStatus.style.color = "#38b44a";
        chipKs.classList.remove("state-alert");
    }

    // Score
    const scoreVal = document.getElementById("live-score");
    const scoreVerdict = document.getElementById("score-verdict");
    const scoreNum = s.current_score;
    scoreVal.textContent = scoreNum.toFixed(4);
    if (scoreNum < -0.02) {
        scoreVal.style.color = "#df382c";
        scoreVerdict.textContent = "ANOMALY";
        scoreVerdict.style.color = "#df382c";
    } else if (scoreNum > 0) {
        scoreVal.style.color = "#38b44a";
        scoreVerdict.textContent = "NORMAL";
        scoreVerdict.style.color = "#38b44a";
    } else {
        scoreVal.style.color = "#8a91a4";
        scoreVerdict.textContent = s.device_state;
        scoreVerdict.style.color = "#8a91a4";
    }

    // Score Mini Canvas
    renderMiniGraph(s.score_history);

    // Calibration Progress
    const calCard = document.getElementById("calibration-card");
    if (s.device_state === "CALIBRATING") {
        calCard.style.display = "block";
        const pct = Math.min(100, (s.calibration_progress / s.calibration_max) * 100);
        document.getElementById("cal-progress-fill").style.width = `${pct}%`;
        document.getElementById("cal-progress-label").textContent = `${s.calibration_progress} / ${s.calibration_max} samples`;
    } else {
        calCard.style.display = "none";
    }

    // Event Log
    updateEventLog(s.event_log);

    // Ledger Blocks
    updateLedgerMini(s.ledger_blocks);
}

// ── Mini Score Graph ─────────────────────────────────────────────────────
function renderMiniGraph(history) {
    if (!canvasCtx || history.length < 2) return;
    const ctx = canvasCtx;
    const w = ctx.canvas.width;
    const h = ctx.canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Threshold line
    const midY = h / 2;
    ctx.strokeStyle = "rgba(223, 56, 44, 0.4)";
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(0, midY); ctx.lineTo(w, midY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Score line
    ctx.lineWidth = 2;
    ctx.beginPath();
    const step = w / Math.max(history.length - 1, 1);
    history.forEach((val, i) => {
        const x = i * step;
        const y = midY - (val * h * 2);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });

    const lastVal = history[history.length - 1];
    ctx.strokeStyle = lastVal < -0.02 ? "#df382c" : "#E95420";
    ctx.shadowBlur = 6;
    ctx.shadowColor = lastVal < -0.02 ? "rgba(223,56,44,0.6)" : "rgba(233,84,32,0.6)";
    ctx.stroke();
    ctx.shadowBlur = 0;
}

// ── Event Log Renderer ──────────────────────────────────────────────────
let lastLogCount = 0;
function updateEventLog(events) {
    if (events.length === lastLogCount) return;
    lastLogCount = events.length;

    const container = document.getElementById("event-log-scroll");
    container.innerHTML = "";
    events.forEach(ev => {
        const div = document.createElement("div");
        div.className = `log-line log-${ev.level}`;
        div.textContent = `[${ev.time}] ${ev.msg}`;
        container.appendChild(div);
    });
    container.scrollTop = container.scrollHeight;
}

// ── Ledger Mini List ─────────────────────────────────────────────────────
let lastBlockCount = 0;
function updateLedgerMini(blocks) {
    if (blocks.length === lastBlockCount) return;
    lastBlockCount = blocks.length;

    const container = document.getElementById("ledger-mini-list");
    container.innerHTML = "";
    [...blocks].reverse().forEach(b => {
        const div = document.createElement("div");
        div.className = "ledger-mini-item";
        div.innerHTML = `<span>#${b.index} ${b.event_type}</span><span style="color:#00a3e0">${b.hash}</span>`;
        container.appendChild(div);
    });
}
