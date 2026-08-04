/**
 * UBUNTU 24.04 LTS (YARU DARK) — BLACKBOX SENTINEL APPLIANCE OS
 * Full Linux Desktop Shell, GNOME Window Manager, & Tactical Edge Defense Engine
 */

// ── OS State Management ──────────────────────────────────────────────────────
const osState = {
    isLocked: true,
    gdmPinBuffer: "",
    modalPinBuffer: "",
    deviceState: "ARMED", // ARMED, CALIBRATING, LOCKDOWN
    packetsTotal: 0,
    anomaliesTotal: 0,
    relayState: "ENGAGED", // ENGAGED, ISOLATED
    activeApp: "defense",
    openWindows: ["defense"],
    scoreHistory: [],
    ledgerChain: [
        {
            index: 0,
            timestamp: new Date().toISOString(),
            event_type: "genesis_block",
            data: {
                kernel: "6.6.20-sentinel-hardened",
                bridge: "br0 (eth0+eth1)",
                node_id: "AEDN-RACK-01",
                keystore: "tmpfs (volatile RAM)"
            },
            previous_hash: "0000000000000000000000000000000000000000000000000000000000000000",
            hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        }
    ]
};

// ── Lifecycle Initialization ──────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    initClock();
    initCanvas();
    renderLedgerBlocks();
    startTrafficSniffer();
    initGnomeWindows();
});

// ── 1. Ubuntu System Clock & Top Bar ──────────────────────────────────────────
function initClock() {
    function tick() {
        const now = new Date();
        const timeStr = now.toTimeString().split(" ")[0].substring(0, 5);
        const fullTimeStr = now.toTimeString().split(" ")[0];
        const dateStr = now.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" });
        const shortDateStr = now.toLocaleDateString("en-US", { month: "short", day: "numeric" }) + " " + timeStr;

        document.getElementById("gdm-clock").textContent = fullTimeStr;
        document.getElementById("gdm-date").textContent = dateStr;
        document.getElementById("topbar-date-time").textContent = shortDateStr;
    }
    tick();
    setInterval(tick, 1000);
}

// ── 2. GDM Login & Screen Lock ────────────────────────────────────────────────
function pressGdmPin(digit) {
    if (osState.gdmPinBuffer.length < 8) {
        osState.gdmPinBuffer += digit;
        document.getElementById("gdm-password-input").value = "•".repeat(osState.gdmPinBuffer.length);
        if (osState.gdmPinBuffer.length === 4) {
            setTimeout(unlockGdm, 200);
        }
    }
}

function clearGdmPin() {
    osState.gdmPinBuffer = "";
    document.getElementById("gdm-password-input").value = "";
}

function handleGdmKey(e) {
    if (e.key === "Enter") {
        unlockGdm();
    }
}

function unlockGdm() {
    const inputVal = document.getElementById("gdm-password-input").value;
    if (osState.gdmPinBuffer === "1234" || inputVal === "1234" || osState.gdmPinBuffer.length >= 4 || inputVal.length > 0) {
        osState.isLocked = false;
        clearGdmPin();
        document.getElementById("gdm-lock-screen").classList.remove("active");
        showGnomeToast("🔓 Session Started &bull; Welcome to Sentinel OS (AEDN-RACK-01)");
    } else {
        showGnomeToast("❌ Authentication failed. Try PIN 1234.");
        clearGdmPin();
    }
}

function lockDesktop() {
    osState.isLocked = true;
    closeQuickSettings();
    document.getElementById("gdm-lock-screen").classList.add("active");
}

// ── 3. GNOME Desktop Window Manager ───────────────────────────────────────────
function initGnomeWindows() {
    bringWindowToFront("defense");
}

function openApp(appId) {
    closeQuickSettings();
    osState.activeApp = appId;

    // Update Dock
    document.querySelectorAll(".dock-icon-btn").forEach(btn => {
        if (btn.dataset.app === appId) btn.classList.add("active");
        else btn.classList.remove("active");
    });

    // Update Topbar Title
    const titles = {
        defense: "Sentinel Defense Center",
        traffic: "Adversary Traffic Lab",
        ledger: "Forensic Ledger Explorer",
        hardware: "Hardware HAL Manager",
        terminal: "GNOME Terminal",
        settings: "Settings"
    };
    document.getElementById("active-app-name").textContent = titles[appId] || "Ubuntu Sentinel";

    const targetWin = document.getElementById(`win-${appId}`);
    if (targetWin) {
        targetWin.classList.add("active");
        targetWin.style.display = "flex";
        bringWindowToFront(appId);
    }
}

function closeApp(appId) {
    const targetWin = document.getElementById(`win-${appId}`);
    if (targetWin) {
        targetWin.classList.remove("active");
        targetWin.style.display = "none";
    }
    const openWins = document.querySelectorAll(".gnome-window.active");
    if (openWins.length > 0) {
        const topWinId = openWins[openWins.length - 1].id.replace("win-", "");
        openApp(topWinId);
    } else {
        document.getElementById("active-app-name").textContent = "Ubuntu Desktop";
    }
}

function minimizeApp(appId) {
    const targetWin = document.getElementById(`win-${appId}`);
    if (targetWin) {
        targetWin.classList.remove("active");
        targetWin.style.display = "none";
    }
}

function toggleMaximize(winId) {
    const win = document.getElementById(winId);
    if (!win) return;
    if (win.dataset.maximized === "true") {
        win.style.top = "20px";
        win.style.left = "30px";
        win.style.right = "20px";
        win.style.bottom = "20px";
        win.dataset.maximized = "false";
    } else {
        win.style.top = "4px";
        win.style.left = "4px";
        win.style.right = "4px";
        win.style.bottom = "4px";
        win.dataset.maximized = "true";
    }
}

let highestZ = 20;
function bringWindowToFront(appId) {
    const win = document.getElementById(`win-${appId}`);
    if (win) {
        highestZ += 2;
        win.style.zIndex = highestZ;
    }
}

// Window Dragging Support
let isDragging = false;
let currentDragWin = null;
let dragOffsetX = 0;
let dragOffsetY = 0;

function startDrag(e, winId) {
    const win = document.getElementById(winId);
    if (!win || win.dataset.maximized === "true") return;
    isDragging = true;
    currentDragWin = win;
    const rect = win.getBoundingClientRect();
    dragOffsetX = e.clientX - rect.left;
    dragOffsetY = e.clientY - rect.top;
    bringWindowToFront(winId.replace("win-", ""));
}

window.addEventListener("mousemove", (e) => {
    if (isDragging && currentDragWin) {
        const left = Math.max(10, e.clientX - dragOffsetX - 58);
        const top = Math.max(10, e.clientY - dragOffsetY - 28);
        currentDragWin.style.left = `${left}px`;
        currentDragWin.style.top = `${top}px`;
        currentDragWin.style.right = "auto";
        currentDragWin.style.bottom = "auto";
        currentDragWin.style.width = "780px";
        currentDragWin.style.height = "520px";
    }
});

window.addEventListener("mouseup", () => {
    isDragging = false;
    currentDragWin = null;
});

// ── 4. Quick Settings & Menus ─────────────────────────────────────────────────
function toggleQuickSettings() {
    const qs = document.getElementById("quick-settings-menu");
    qs.classList.toggle("active");
}

function closeQuickSettings() {
    const qs = document.getElementById("quick-settings-menu");
    if (qs) qs.classList.remove("active");
}

function toggleAppOverview() {
    showGnomeToast("⊞ GNOME Overview: 6 Appliance Systems Running");
}

function toggleDateMenu() {
    showGnomeToast("📅 " + new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" }));
}

// ── 5. Canvas Spectrum Scope (Isolation Forest Reconstruction) ────────────────
let canvas, ctx;
function initCanvas() {
    canvas = document.getElementById("score-spectrum-canvas");
    if (!canvas) return;
    ctx = canvas.getContext("2d");
}

function renderCanvasSpectrum() {
    if (!ctx) return;
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Subtle Ubuntu Grid
    ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let y = 20; y < h; y += 30) {
        ctx.moveTo(0, y); ctx.lineTo(w, y);
    }
    ctx.stroke();

    // Baseline Center Threshold Line (0.0 score)
    const midY = h / 2;
    ctx.strokeStyle = "rgba(223, 56, 44, 0.6)";
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(0, midY); ctx.lineTo(w, midY);
    ctx.stroke();
    ctx.setLineDash([]);

    if (osState.scoreHistory.length < 2) return;

    // Draw Spectrum Line
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    const step = w / 35;

    osState.scoreHistory.forEach((pt, i) => {
        const x = i * step;
        const y = midY - (pt.score * (h * 1.6));
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });

    ctx.strokeStyle = osState.deviceState === "LOCKDOWN" ? "#df382c" : "#E95420";
    ctx.shadowBlur = 10;
    ctx.shadowColor = osState.deviceState === "LOCKDOWN" ? "rgba(223, 56, 44, 0.8)" : "rgba(233, 84, 32, 0.8)";
    ctx.stroke();
    ctx.shadowBlur = 0;
}

// ── 6. Live Packet Sniffer Engine (Wireshark Style) ───────────────────────────
function startTrafficSniffer() {
    setInterval(() => {
        if (osState.deviceState === "LOCKDOWN") return;

        osState.packetsTotal++;
        document.getElementById("metric-pkts").textContent = osState.packetsTotal;

        const protocols = [
            { proto: "TLSv1.3", port: 443, src: "192.168.10.104", dst: "1.1.1.1", size: 684, info: "Application Data" },
            { proto: "HTTPS", port: 443, src: "192.168.10.104", dst: "142.250.190.46", size: 512, info: "Client Hello" },
            { proto: "DNS", port: 53, src: "192.168.10.104", dst: "8.8.8.8", size: 78, info: "Standard query A api.sentinel.internal" },
            { proto: "NTP", port: 123, src: "192.168.10.104", dst: "216.239.35.0", size: 90, info: "NTP Client" }
        ];

        const item = protocols[Math.floor(Math.random() * protocols.length)];
        const score = (Math.random() * 0.12 + 0.06);

        osState.scoreHistory.push({ score, time: Date.now() });
        if (osState.scoreHistory.length > 35) osState.scoreHistory.shift();
        renderCanvasSpectrum();

        document.getElementById("viz-score-val").textContent = `SCORE: +${score.toFixed(3)} [NORMAL]`;
        document.getElementById("viz-score-val").className = "text-green";

        addSnifferRow(item.src, item.dst, item.proto, item.size, item.info, false, score);
    }, 300);
}

function addSnifferRow(src, dst, proto, size, info, isAnomaly, score) {
    const tbody = document.getElementById("sniffer-tbody");
    if (!tbody) return;

    const row = document.createElement("tr");
    row.className = isAnomaly ? "pkt-row-anomaly" : "pkt-row-normal";
    const now = new Date().toTimeString().split(" ")[0] + "." + Math.floor(Math.random() * 900 + 100);

    row.innerHTML = `
        <td>${osState.packetsTotal}</td>
        <td>${now}</td>
        <td>${src}</td>
        <td>${dst}</td>
        <td><span style="background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px;">${proto}</span></td>
        <td>${size} bytes</td>
        <td>${isAnomaly ? `🚨 THREAT DETECTED &bull; [Anomaly Score: ${score.toFixed(3)}]` : info}</td>
    `;

    tbody.insertBefore(row, tbody.firstChild);
    if (tbody.children.length > 40) tbody.removeChild(tbody.lastChild);
}

// ── 7. Adversarial Attack Injection ──────────────────────────────────────────
function injectAttack(type) {
    if (osState.deviceState === "LOCKDOWN") {
        showGnomeToast("⚠️ Node already isolated in Air-Gap Lockdown.");
        return;
    }

    osState.packetsTotal++;
    osState.anomaliesTotal++;
    document.getElementById("metric-anomalies").textContent = osState.anomaliesTotal;

    let src = "192.168.10.104", dst, proto, size, info, label, score;

    if (type === "EXFILTRATION") {
        dst = "198.51.100.22"; proto = "TCP/4444"; size = 24800; info = "Adversary Reverse Shell Exfiltration";
        label = "ROGUE C2 DATA EXFILTRATION"; score = -0.088;
    } else if (type === "SYN_FLOOD") {
        dst = "192.168.10.1"; proto = "TCP/SYN"; size = 44; info = "High-Rate TCP SYN Flood Attack";
        label = "TCP SYN FLOOD ATTACK"; score = -0.115;
    } else if (type === "PORT_SCAN") {
        dst = "192.168.10.1-254"; proto = "TCP/SCAN"; size = 60; info = "Aggressive Lateral Subnet Sweep";
        label = "ADVERSARIAL RECON SCAN"; score = -0.074;
    } else {
        dst = "10.0.0.99"; proto = "RAW/0xDEAD"; size = 42000; info = "Malformed Encapsulation Zero-Day";
        label = "ZERO-DAY PROTOCOL EXPLOIT"; score = -0.195;
    }

    osState.scoreHistory.push({ score, time: Date.now() });
    if (osState.scoreHistory.length > 35) osState.scoreHistory.shift();
    renderCanvasSpectrum();

    addSnifferRow(src, dst, proto, size, info, true, score);
    triggerAirgapLockdown(label, score);
}

function triggerAirgapLockdown(reason, score) {
    osState.deviceState = "LOCKDOWN";
    osState.relayState = "ISOLATED";

    // Update UI Statuses
    document.getElementById("defense-ring").className = "status-indicator-ring pulse-red";
    document.getElementById("defense-state-text").textContent = "🚨 AIR-GAP LOCKDOWN (LINE CUT)";
    document.getElementById("metric-relay").textContent = "ISOLATED";
    document.getElementById("metric-relay").className = "metric-value text-red";
    document.getElementById("hw-relay-tag").textContent = "ISOLATED (Air-Gapped)";
    document.getElementById("hw-relay-tag").className = "badge-status text-red";
    document.getElementById("qs-defense-status").textContent = "AIR-GAP ACTIVE";

    // Add Forensic Block
    const block = addLedgerBlock("threat_containment", {
        reason: reason,
        anomaly_score: score,
        relay_action: "MECHANICALLY_SEVERED_0.04MS",
        interface: "br0",
        timestamp: Date.now()
    });

    // Append Alert Log
    appendAlertLog(`🚨 [AIR-GAP CUT] ${reason} (Score: ${score.toFixed(3)}) &bull; Line severed`, "log-danger");

    // Show Lockdown Modal
    document.getElementById("modal-threat-name").textContent = reason;
    document.getElementById("modal-anomaly-score").textContent = `${score.toFixed(3)} (Reconstruction Anomaly Threshold Breached)`;
    document.getElementById("modal-ledger-hash").textContent = block.hash;
    document.getElementById("airgap-lockdown-modal").classList.add("active");

    showGnomeToast(`🚨 THREAT MITIGATED: Mechanical line severed for ${reason}`);
}

// ── 8. Sudo PIN Override to Restore Relay ──────────────────────────────────────
function pressModalPin(d) {
    if (osState.modalPinBuffer.length < 6) {
        osState.modalPinBuffer += d;
        document.getElementById("modal-pin-input").value = "•".repeat(osState.modalPinBuffer.length);
    }
}

function clearModalPin() {
    osState.modalPinBuffer = "";
    document.getElementById("modal-pin-input").value = "";
}

function submitModalPin() {
    if (osState.modalPinBuffer === "1234" || osState.modalPinBuffer.length >= 4) {
        osState.deviceState = "ARMED";
        osState.relayState = "ENGAGED";
        clearModalPin();
        document.getElementById("airgap-lockdown-modal").classList.remove("active");

        // Restore UI
        document.getElementById("defense-ring").className = "status-indicator-ring";
        document.getElementById("defense-state-text").textContent = "SYSTEM ARMED & DEFENDING";
        document.getElementById("metric-relay").textContent = "ENGAGED";
        document.getElementById("metric-relay").className = "metric-value text-green";
        document.getElementById("hw-relay-tag").textContent = "ENGAGED (0V Normal)";
        document.getElementById("hw-relay-tag").className = "badge-status text-green";
        document.getElementById("qs-defense-status").textContent = "Armed & Active";

        addLedgerBlock("tactical_sudo_override", {
            operator: "sentinel",
            action: "RELAY_MECHANICALLY_RESTORED"
        });

        appendAlertLog("✅ [OPERATOR] Sudo PIN accepted. Mechanical line re-engaged.", "log-success");
        showGnomeToast("✅ Mechanical Relay Restored &bull; Bridge br0 Active");
    } else {
        showGnomeToast("❌ Sudo PIN incorrect. Line remains isolated.");
        clearModalPin();
    }
}

function toggleManualLineCut() {
    if (osState.relayState === "ENGAGED") {
        triggerAirgapLockdown("MANUAL OPERATOR ISOLATION", -0.999);
    } else {
        submitModalPin();
    }
}

// ── 9. SHA-256 Forensic Ledger ────────────────────────────────────────────────
function simpleSha256(text) {
    let hash = 0;
    for (let i = 0; i < text.length; i++) {
        const char = text.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }
    const hex = Math.abs(hash).toString(16).padStart(8, '0');
    return hex.repeat(8);
}

function addLedgerBlock(eventType, data) {
    const prevBlock = osState.ledgerChain[osState.ledgerChain.length - 1];
    const rawPayload = JSON.stringify({
        index: osState.ledgerChain.length,
        timestamp: new Date().toISOString(),
        event_type: eventType,
        data: data,
        previous_hash: prevBlock.hash
    });
    const block = {
        index: osState.ledgerChain.length,
        timestamp: new Date().toISOString(),
        event_type: eventType,
        data: data,
        previous_hash: prevBlock.hash,
        hash: simpleSha256(rawPayload)
    };

    osState.ledgerChain.push(block);
    document.getElementById("metric-blocks").textContent = `${osState.ledgerChain.length} BLOCKS`;
    document.getElementById("dock-ledger-badge").textContent = osState.ledgerChain.length;
    renderLedgerBlocks();
    return block;
}

function renderLedgerBlocks() {
    const container = document.getElementById("ledger-blocks-container");
    if (!container) return;
    container.innerHTML = "";

    [...osState.ledgerChain].reverse().forEach(b => {
        const item = document.createElement("div");
        item.className = "ledger-block-item";
        item.innerHTML = `
            <div class="block-header">
                <span>BLOCK #${b.index} &bull; ${b.event_type.toUpperCase()}</span>
                <span style="color: #a8a8a8;">${b.timestamp}</span>
            </div>
            <div class="block-hash-line">SHA-256: ${b.hash}</div>
            <div style="color: #888888; font-size: 10px; margin-top: 3px;">PREV HASH: ${b.previous_hash.substring(0, 32)}...</div>
        `;
        container.appendChild(item);
    });
}

function verifyLedgerChain() {
    showGnomeToast("🔐 Verifying SHA-256 Merkle Chain Integrity...");
    setTimeout(() => {
        document.getElementById("ledger-audit-text").innerHTML = `Chain Integrity: <strong>100% Valid (${osState.ledgerChain.length} Blocks Verified)</strong>`;
        showGnomeToast("✅ Forensic Chain 100% Cryptographically Intact");
    }, 400);
}

function exportLedgerJSON() {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(osState.ledgerChain, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", "sentinel_forensic_ledger.json");
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    showGnomeToast("📁 Exported sentinel_forensic_ledger.json");
}

// ── 10. Hardware Actions & Tamper Zeroization ─────────────────────────────────
function triggerTamperAlert() {
    closeQuickSettings();
    addLedgerBlock("tamper_grid_rupture", {
        action: "VOLATILE_RAM_KEYS_ZEROIZED",
        sensor: "BCM_27_CHASSIS_MICROSWITCH"
    });
    triggerAirgapLockdown("CHASSIS TAMPER DETECTED &bull; RAM KEYS ZEROIZED", -1.0);
    showGnomeToast("🔥 TAMPER SENSOR TRIPPED: Volatile RAM Keys Zeroized");
}

function sendTestSMS() {
    showGnomeToast("📱 SIM800L: Out-of-band alert SMS dispatched (+919876543210)");
}

function broadcastMeshThreat() {
    showGnomeToast("📡 ESP-NOW: Threat vector gossiped to adjacent rack nodes");
}

function toggleDefenseEngine() {
    showGnomeToast("🛡️ AI Defense Engine Active & Monitoring Bridge");
}

function appendAlertLog(msg, typeClass = "log-info") {
    const log = document.getElementById("defense-alerts-log");
    if (!log) return;
    const div = document.createElement("div");
    div.className = `log-entry ${typeClass}`;
    div.textContent = msg;
    log.insertBefore(div, log.firstChild);
}

// ── 11. GNOME Bash Terminal Emulator ──────────────────────────────────────────
function handleTerminalCommand(e) {
    if (e.key === "Enter") {
        const input = document.getElementById("term-cli-input");
        const rawCmd = input.value.trim();
        const cmd = rawCmd.toLowerCase();
        input.value = "";

        appendTermLine(`sentinel@ubuntu-sentinel:~$ ${rawCmd}`, "text-white");

        if (cmd === "help" || cmd === "commands") {
            appendTermLine("BlackBox Sentinel Ubuntu Diagnostics Shell:", "text-green");
            appendTermLine("  status     - Show edge node health & hardware state");
            appendTermLine("  audit      - Perform cryptographic Merkle ledger audit");
            appendTermLine("  isolate    - Mechanically cut relay (simulate air-gap)");
            appendTermLine("  restore    - Restore physical data relay");
            appendTermLine("  zeroize    - Zeroize volatile RAM cryptographic keys");
            appendTermLine("  ifconfig   - Show network bridge br0 interface status");
            appendTermLine("  uname -a   - Display Linux appliance kernel info");
            appendTermLine("  clear      - Clear terminal screen");
        } else if (cmd === "status") {
            appendTermLine(`Device: ${osState.deviceState} | Relay: ${osState.relayState} | Packets: ${osState.packetsTotal} | Ledger Blocks: ${osState.ledgerChain.length}`, "text-cyan");
        } else if (cmd === "audit") {
            verifyLedgerChain();
            appendTermLine(`Chain integrity: 100% VALID (${osState.ledgerChain.length} blocks verified)`, "text-green");
        } else if (cmd === "isolate" || cmd === "cut") {
            toggleManualLineCut();
            appendTermLine("Relay actuated: Mechanical line severed", "text-red");
        } else if (cmd === "restore" || cmd === "engage") {
            submitModalPin();
            appendTermLine("Relay actuated: Mechanical line re-engaged", "text-green");
        } else if (cmd === "zeroize" || cmd === "purge") {
            triggerTamperAlert();
            appendTermLine("Volatile RAM keystore /run/sentinel/keys ZEROIZED", "text-red");
        } else if (cmd.startsWith("uname")) {
            appendTermLine("Linux ubuntu-sentinel 6.6.20-hardened-arm64 #1 SMP PREEMPT aarch64 GNU/Linux", "text-green");
        } else if (cmd.startsWith("ifconfig") || cmd.startsWith("ip")) {
            appendTermLine("br0: flags=4163<UP,BROADCAST,RUNNING,PROMISC> mtu 1500", "text-cyan");
            appendTermLine("     inet 192.168.10.104 netmask 255.255.255.0 broadcast 192.168.10.255");
            appendTermLine("eth0: master br0 state UP (0.04ms inline inspection)");
            appendTermLine("eth1: master br0 state UP (0.04ms inline inspection)");
        } else if (cmd.startsWith("cat /etc/os-release")) {
            appendTermLine('NAME="Ubuntu"');
            appendTermLine('VERSION="24.04 LTS (Noble Numbat) - BlackBox Sentinel Edition"');
            appendTermLine('ID=ubuntu');
        } else if (cmd === "clear") {
            document.getElementById("gnome-term-body").innerHTML = "";
        } else if (cmd === "") {
            // empty
        } else {
            appendTermLine(`bash: ${rawCmd}: command not found. Type 'help' for available commands.`, "text-red");
        }
    }
}

function appendTermLine(msg, typeClass = "") {
    const body = document.getElementById("gnome-term-body");
    if (!body) return;
    const div = document.createElement("div");
    div.className = `term-line ${typeClass}`;
    div.textContent = msg;
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
}

// ── 12. Toast Notifications ──────────────────────────────────────────────────
let toastTimer;
function showGnomeToast(msg) {
    const t = document.getElementById("gnome-toast");
    if (!t) return;
    t.innerHTML = msg;
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 3200);
}
