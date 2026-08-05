/**
 * BLACKBOX SENTINEL — ULTRA HIGH-FIDELITY INDUSTRIAL 3D CAD STUDIO
 * Features:
 * - Studio HDRI Environment Reflections & ACES Filmic Tone Mapping
 * - Component-level Micro-SMD Geometry (Resistors, Capacitors, Quartz Crystals, Inductors)
 * - Animated Active Cooling Fan on Heatsink with 7 Aerodynamic Blades
 * - DSI Flexible Flat Cable (FFC) & RG178 RF Coaxial Cable
 * - Detailed Ports: Dual USB 3.0/2.0 with internal contacts, RJ45 with 8 spring pins & LEDs, Micro-HDMI, USB-C
 * - Authentic ICs: Broadcom BCM2711, RAM, BCM54213 PHY, VL805 USB, ESP32-S3 RF Can, PC817 Opto, SIM800L, 1000µF Cap
 * - Dual Panasonic NCR18650B cells with PMIC 4-LED Fuel Gauge
 * - Unibody Carbon-PETG Chassis with 24x Honeycomb Vents & Laser-Engraved Serial Badge
 * - Interactive 3D Touchscreen UI with Real-time Waveforms and Live Defense Triggers
 */

let scene, camera, renderer, controls;
let raycaster, mouse;
let explodeFactor = 0;
let targetExplode = 0;
let autoRotate = true;
let currentRenderMode = "solid";
let gridHelper, dimensionGroup;
let animatedTime = 0;
let fanBladesMesh;
let screenCanvas, screenCtx, screenTexture;
let relayLedMesh, rj45Led1, rj45Led2, pmicLeds = [];
let isRelayIsolated = false;
let isTamperTriggered = false;

// Component Groups
const parts = {};
const originalY = {};
let selectedPartName = null;
let wiresGroup;
let chassisWallsGroup;

// ── Technical Component Specs Database ──────────────────────────────────────
const COMPONENT_DATA = {
    topLid: {
        name: "Top Enclosure Lid (CNC Carbon-PETG)",
        tier: "TIER 0 &bull; CHASSIS COVER",
        dims: "140 × 100 × 10 mm",
        material: "Carbon-Fiber Reinforced PETG (30% Gyroid) + 4x M3 Socket Screws",
        role: "Precision top housing with 45° chamfered bezel, flush display recess, silicone O-ring gasket, and integrated anti-tamper latching.",
        specs: [
            ["Wall Thickness", "3.0 mm (UL94 V-0 Flame Retardant)"],
            ["Display Bezel", "5.0-inch flush recess with 0.8mm perimeter lip"],
            ["Fasteners", "4x M3 Black Oxide Stainless Steel Socket Cap Bolts"],
            ["Weight", "52.4 grams"]
        ]
    },
    screen: {
        name: '5.0" IPS Capacitive Touch Display',
        tier: "TIER 0 &bull; HMI INTERFACE",
        dims: "121 × 76 × 6.5 mm",
        material: "Optically Bonded 2.5D Toughened Glass + DSI Ribbon",
        role: "800×480 High-DPI IPS Display running Ubuntu 24.04 Yaru Dark Sentinel OS. Real-time traffic oscilloscope, CPU thermals & PIN keypad.",
        specs: [
            ["Resolution", "800 × 480 px @ 60 FPS (TrueColor IPS)"],
            ["Touch IC", "Goodix GT911 5-Point Capacitive Multi-touch"],
            ["Interface", "15-Pin Flexible Flat Ribbon (DSI / MIPI)"],
            ["Backlight", "PWM Dimmable LED (450 nits brightness)"]
        ]
    },
    chassisWalls: {
        name: "Unibody 4-Wall Chassis & Honeycomb Vents",
        tier: "TIER 0 &bull; CHASSIS HOUSING",
        dims: "140 × 100 × 38 mm",
        material: "Carbon-Fiber Reinforced PETG + Brass Heat-Set Inserts",
        role: "Main appliance shell with 24x honeycomb intake/exhaust vents, laser-engraved serial badge, and front LED light pipes.",
        specs: [
            ["Ventilation", "24x Hexagonal Honeycomb Convection Cutouts"],
            ["Port Cutouts", "2x RJ45 (ETH0/ETH1), 1x USB-C, 1x SMA Brass Port"],
            ["Front Panel", "Laser-Engraved Serial Badge + 3x Acrylic Light Pipes"],
            ["Inserts", "4x M3 Brass Threaded Heat-Set Inserts"]
        ]
    },
    tamper: {
        name: "Interleaved Copper Anti-Tamper Shield",
        tier: "TIER 1 &bull; HARDWARE SECURITY",
        dims: "130 × 90 × 1.2 mm",
        material: "Dual-Layer 0.2mm Copper Trace FPC + Omron Microswitches",
        role: "Continuous active-low security loop. Physical chassis breach severs circuit in <5µs, zeroizing all encryption keys in RAM.",
        specs: [
            ["Interrupt Pin", "ESP32 GPIO 27 (Internal Pull-Up)"],
            ["Detection Latency", "3.2 microseconds (Hardware ISR)"],
            ["Action Triggered", "Zeroizes volatile RAM /run/sentinel/keys"],
            ["Quiescent Current", "0.04 mA (Ultra-low power)"]
        ]
    },
    heatsink: {
        name: "Armor CNC Aluminum SoC Heatsink & Active Fan",
        tier: "TIER 2 &bull; THERMAL MANAGEMENT",
        dims: "68 × 56 × 15 mm",
        material: "Black Anodized 6061-T6 Aluminum + 30mm PWM Fan",
        role: "Direct SoC cooling for Broadcom BCM2711 & RAM with 7-blade active brushless fan spinning at 4500 RPM for heavy ML loads.",
        specs: [
            ["Thermal Interface", "1.5mm 6.0 W/mK silicone thermal pad"],
            ["Fan Specs", "3010 5V Brushless PWM Fan (4,500 RPM)"],
            ["SoC Delta Temp", "-24.8°C under 100% CPU inference load"],
            ["Mounting", "M2.5 brass standoffs directly to Pi 4 holes"]
        ]
    },
    pi4: {
        name: "Raspberry Pi 4 Model B (4GB/8GB)",
        tier: "TIER 2 &bull; HOST SBC",
        dims: "85 × 56 × 17 mm",
        material: "FR-4 Multi-layer PCB + Broadcom BCM2711 SoC + SMD Grid",
        role: "Main compute appliance. Runs Linux kernel 6.6.20, Layer-2 bridge br0, and Isolation Forest ML pipeline.",
        specs: [
            ["Processor", "Broadcom BCM2711 Quad Cortex-A72 @ 1.8 GHz"],
            ["System Memory", "4GB / 8GB LPDDR4-3200 SDRAM"],
            ["Ethernet Port", "Native Gigabit Ethernet RJ45 (eth0) with 8 gold pins"],
            ["USB Ports", "2x USB 3.0 (Blue) + 2x USB 2.0 (Black) via VL805"],
            ["Micro-HDMI", "2x Micro-HDMI 4K60 Ports"],
            ["Storage Slot", "MicroSD Card Slot (SanDisk Extreme 64GB)"]
        ]
    },
    esp32: {
        name: "ESP32-S3 DevKit Co-Processor",
        tier: "TIER 2 &bull; RF & HARDWARE HAL",
        dims: "48 × 26 × 8 mm",
        material: "Dual-Core Xtensa LX7 @ 240MHz + PCB Antenna",
        role: "Drives 5V relay actuation, monitors anti-tamper interrupt lines, and runs ESP-NOW P2P threat mesh.",
        specs: [
            ["Mesh Protocol", "ESP-NOW 2.4GHz Connectionless Gossip"],
            ["Relay Driver", "GPIO 18 (Active-High Opto-isolated Trigger)"],
            ["UART Interface", "GPIO 16 (RX) / 17 (TX) @ 115200 Baud to Pi 4"],
            ["Tamper Line", "GPIO 27 (Falling-edge hardware interrupt)"]
        ]
    },
    relay: {
        name: "Songle 5V Mechanical Isolation Relay",
        tier: "TIER 3 &bull; PHYSICAL AIR-GAP",
        dims: "34 × 26 × 18 mm",
        material: "Songle SRD-05VDC-SL-C + PC817 Optocoupler Isolation",
        role: "Physically snaps open outbound Ethernet TX lines in 0.04ms upon anomaly detection, creating total air-gap.",
        specs: [
            ["Switching Time", "0.04 ms response trigger time"],
            ["Contact Rating", "10A 250VAC / 10A 30VDC (AgSnO2 Contacts)"],
            ["Default State", "Normally Closed (NC = Connected at 0V)"],
            ["Dielectric Strength","1500 VAC between coil and contacts"]
        ]
    },
    sim800: {
        name: "SIM800L Quad-Band GSM Cellular Modem",
        tier: "TIER 3 &bull; OUT-OF-BAND COMM",
        dims: "25 × 23 × 7 mm",
        material: "Quad-Band GSM + IPEX Coaxial Pigtail + 1000µF Cap",
        role: "Dispatches emergency Out-of-Band SMS alert to Admin when LAN is mechanically severed.",
        specs: [
            ["Frequencies", "GSM 850/900/1800/1900 MHz Quad-Band"],
            ["Peak Current", "2.0 A (Buffered by onboard 1000µF 16V Cap)"],
            ["Coaxial Cable", "RG178 Shielded Pigtail to Panel SMA Jack"],
            ["Antenna Port", "Panel-Mount Gold SMA Female Jack with 2dBi Stub"]
        ]
    },
    battery: {
        name: "Dual 18650 Battery Holder & PMIC",
        tier: "TIER 4 &bull; POWER SUBSYSTEM",
        dims: "100 × 50 × 24 mm",
        material: "2x Panasonic NCR18650B (6800mAh total) + PMIC + 4-LED Fuel Gauge",
        role: "Provides up to 4.5 hours of uninterrupted battery runtime during server rack power cuts.",
        specs: [
            ["Battery Chemistry","Li-ion 3.7V (2x 3400mAh in Parallel = 6800mAh)"],
            ["Fuel Gauge", "4x Blue LEDs (25%, 50%, 75%, 100% capacity)"],
            ["Output Rails", "5.0V @ 3.0A (Pi/Screen) + 4.0V @ 2.0A (SIM800L)"],
            ["Input Port", "USB-C 5V 2A Fast Charge / Passthrough UPS"]
        ]
    },
    bottomCase: {
        name: "Bottom Chassis Base & Dampers",
        tier: "TIER 4 &bull; CHASSIS BASE",
        dims: "140 × 100 × 12 mm",
        material: "Matte Charcoal Carbon-PETG + 4x Silicone Feet",
        role: "Chassis base plate supporting battery tray, M3 mounting standoffs, and non-slip silicone feet.",
        specs: [
            ["Dampers", "4x High-Grip Silicone Isolator Pads"],
            ["Mounting", "M2.5 & M3 Standoff Alignment Grid"],
            ["Cooling", "Bottom Convective Air Intake Vents"],
            ["Fasteners", "4x Countersunk M3 Socket Bolts"]
        ]
    }
};

// ── Initialization ──────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    initThreeJS();
    buildParametricAppliance();
    setupRaycaster();
    animate();
    document.getElementById("loading-overlay").classList.add("hidden");
    selectComponent("pi4");
});

// ── Three.js Studio Scene Setup ────────────────────────────────────────────
function initThreeJS() {
    const container = document.getElementById("cad-canvas-container");
    const canvas = document.getElementById("webgl-canvas");

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0c12);

    camera = new THREE.PerspectiveCamera(38, container.clientWidth / container.clientHeight, 1, 2000);
    camera.position.set(215, 165, 245);

    renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: false, powerPreference: "high-performance" });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.3;

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 + 0.02;
    controls.minDistance = 60;
    controls.maxDistance = 750;
    controls.autoRotate = autoRotate;
    controls.autoRotateSpeed = 0.75;

    // ── Generate Procedural Studio HDRI Environment Map ────────────────────
    generateStudioEnvironment();

    // ── Studio Lighting System ─────────────────────────────────────────────
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
    scene.add(ambientLight);

    // Key Studio Softbox (Top-Right Front)
    const keyLight = new THREE.DirectionalLight(0xfffaee, 1.45);
    keyLight.position.set(160, 280, 190);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 4096;
    keyLight.shadow.mapSize.height = 4096;
    keyLight.shadow.camera.near = 10;
    keyLight.shadow.camera.far = 700;
    keyLight.shadow.camera.left = -160;
    keyLight.shadow.camera.right = 160;
    keyLight.shadow.camera.top = 160;
    keyLight.shadow.camera.bottom = -160;
    keyLight.shadow.bias = -0.0003;
    scene.add(keyLight);

    // Cool Cyan Fill Softbox (Left)
    const fillLight = new THREE.DirectionalLight(0x38bdf8, 0.8);
    fillLight.position.set(-220, 140, -120);
    scene.add(fillLight);

    // Warm Orange Rim Backlight
    const rimLight = new THREE.DirectionalLight(0xe95420, 1.15);
    rimLight.position.set(0, -30, -220);
    scene.add(rimLight);

    // Internal PCB Status Point Light
    const pcbGlow = new THREE.PointLight(0x38b44a, 0.95, 160);
    pcbGlow.position.set(-15, 12, 0);
    scene.add(pcbGlow);

    // Ground Grid & Studio Shadow Receiver
    gridHelper = new THREE.GridHelper(500, 50, 0x222a3a, 0x111520);
    gridHelper.position.y = -44;
    scene.add(gridHelper);

    const planeGeo = new THREE.PlaneGeometry(700, 700);
    const planeMat = new THREE.ShadowMaterial({ opacity: 0.55 });
    const shadowPlane = new THREE.Mesh(planeGeo, planeMat);
    shadowPlane.rotation.x = -Math.PI / 2;
    shadowPlane.position.y = -44.1;
    shadowPlane.receiveShadow = true;
    scene.add(shadowPlane);

    // Window Resize
    window.addEventListener("resize", () => {
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    });
}

// ── Procedural Studio HDRI Reflection Map ───────────────────────────────────
function generateStudioEnvironment() {
    const cvsEnv = document.createElement("canvas");
    cvsEnv.width = 512; cvsEnv.height = 256;
    const ctx = cvsEnv.getContext("2d");

    // Studio Gradient Backdrop
    const grad = ctx.createLinearGradient(0, 0, 0, 256);
    grad.addColorStop(0, "#2e3648");
    grad.addColorStop(0.5, "#151824");
    grad.addColorStop(1, "#0a0c12");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 512, 256);

    // Softbox 1 (Warm Key)
    ctx.fillStyle = "#ffffff";
    ctx.filter = "blur(12px)";
    ctx.fillRect(80, 40, 140, 80);

    // Softbox 2 (Cool Cyan Rim)
    ctx.fillStyle = "#38bdf8";
    ctx.fillRect(320, 60, 100, 70);

    // Softbox 3 (Orange Accent)
    ctx.fillStyle = "#e95420";
    ctx.fillRect(220, 160, 80, 50);
    ctx.filter = "none";

    const envTex = new THREE.CanvasTexture(cvsEnv);
    envTex.mapping = THREE.EquirectangularReflectionMapping;
    scene.environment = envTex;
}

// ── Realistic Procedural Textures & Materials ──────────────────────────────
function createHighResTextures() {
    // 1. High-Detail Carbon Fiber / Textured PETG Casing Texture
    const cvsPetg = document.createElement("canvas");
    cvsPetg.width = 256; cvsPetg.height = 256;
    const ctxP = cvsPetg.getContext("2d");
    ctxP.fillStyle = "#161922";
    ctxP.fillRect(0, 0, 256, 256);
    for (let x = 0; x < 256; x += 8) {
        for (let y = 0; y < 256; y += 8) {
            ctxP.fillStyle = (x / 8 + y / 8) % 2 === 0 ? "#1c202b" : "#12141c";
            ctxP.fillRect(x, y, 8, 8);
            ctxP.fillStyle = "rgba(255,255,255,0.03)";
            ctxP.fillRect(x + 1, y + 1, 6, 2);
        }
    }
    const petgTex = new THREE.CanvasTexture(cvsPetg);
    petgTex.wrapS = THREE.RepeatWrapping;
    petgTex.wrapT = THREE.RepeatWrapping;
    petgTex.repeat.set(6, 4);

    // 2. Authentic Raspberry Pi 4 Model B PCB Silkscreen Texture
    const cvsPi = document.createElement("canvas");
    cvsPi.width = 1024; cvsPi.height = 680;
    const ctxPi = cvsPi.getContext("2d");
    ctxPi.fillStyle = "#12421b"; // Authentic Pi Green
    ctxPi.fillRect(0, 0, 1024, 680);

    // Gold Traces
    ctxPi.strokeStyle = "rgba(225, 185, 60, 0.45)";
    ctxPi.lineWidth = 2.0;
    for (let i = 0; i < 45; i++) {
        ctxPi.beginPath();
        const startX = Math.random() * 1024;
        const startY = Math.random() * 680;
        ctxPi.moveTo(startX, startY);
        ctxPi.lineTo(startX + (Math.random() * 200 - 100), startY);
        ctxPi.lineTo(startX + (Math.random() * 200 - 100), startY + (Math.random() * 200 - 100));
        ctxPi.stroke();
    }

    // High-Res Silkscreen Text & Logo
    ctxPi.fillStyle = "#ffffff";
    ctxPi.font = "bold 26px 'Ubuntu Mono', monospace";
    ctxPi.fillText("Raspberry Pi 4 Model B", 60, 80);
    ctxPi.font = "18px 'Ubuntu Mono', monospace";
    ctxPi.fillText("Raspberry Pi (Trading) Ltd. 2018", 60, 115);
    ctxPi.fillText("FCC ID: 2ABCB-RPI4B • IC: 20953-RPI4B", 60, 145);
    ctxPi.fillText("AEDN-RACK-01 • BLACKBOX SENTINEL", 60, 620);

    ctxPi.fillStyle = "#d4af37";
    ctxPi.font = "bold 22px monospace";
    ctxPi.fillText("BROADCOM BCM2711", 340, 360);
    ctxPi.font = "16px monospace";
    ctxPi.fillText("4GB LPDDR4-3200", 340, 390);

    const piTex = new THREE.CanvasTexture(cvsPi);

    // 3. Songle Relay Stamped Specification Texture
    const cvsRelay = document.createElement("canvas");
    cvsRelay.width = 256; cvsRelay.height = 256;
    const ctxR = cvsRelay.getContext("2d");
    ctxR.fillStyle = "#0a4b9c"; // Songle Royal Blue
    ctxR.fillRect(0, 0, 256, 256);
    ctxR.fillStyle = "#ffffff";
    ctxR.font = "bold 24px 'Inter', sans-serif";
    ctxR.fillText("SONGLE", 30, 45);
    ctxR.font = "bold 16px 'Ubuntu Mono', monospace";
    ctxR.fillText("SRD-05VDC-SL-C", 30, 75);
    ctxR.font = "12px 'Ubuntu Mono', monospace";
    ctxR.fillText("10A 250VAC  10A 125VAC", 30, 110);
    ctxR.fillText("10A 30VDC   10A 28VDC", 30, 130);
    ctxR.fillText("AIR-GAP ISOLATION", 30, 180);
    ctxR.strokeStyle = "#ffffff";
    ctxR.lineWidth = 2;
    ctxR.strokeRect(30, 200, 40, 30);
    ctxR.strokeRect(100, 200, 40, 30);

    const relayTex = new THREE.CanvasTexture(cvsRelay);

    // 4. 18650 Battery Cell Shrink-Wrap Label Texture
    const cvsBat = document.createElement("canvas");
    cvsBat.width = 512; cvsBat.height = 256;
    const ctxB = cvsBat.getContext("2d");
    ctxB.fillStyle = "#008080"; // Teal Li-ion shrink wrap
    ctxB.fillRect(0, 0, 512, 256);
    ctxB.fillStyle = "#ffffff";
    ctxB.font = "bold 24px 'Ubuntu Mono', monospace";
    ctxB.fillText("PANASONIC NCR18650B", 40, 60);
    ctxB.font = "16px 'Ubuntu Mono', monospace";
    ctxB.fillText("Li-ion MH12210 3400mAh 3.7V", 40, 95);
    ctxB.fillText("MADE IN JAPAN • RECHARGEABLE", 40, 130);
    ctxB.fillStyle = "#ffcc00";
    ctxB.fillText("⚠ CAUTION: DO NOT SHORT OR INCINERATE", 40, 180);

    const batTex = new THREE.CanvasTexture(cvsBat);

    // 5. Aluminum Laser-Engraved Serial Badge Texture
    const cvsBadge = document.createElement("canvas");
    cvsBadge.width = 512; cvsBadge.height = 128;
    const ctxBd = cvsBadge.getContext("2d");
    ctxBd.fillStyle = "#1e222b";
    ctxBd.fillRect(0, 0, 512, 128);
    ctxBd.strokeStyle = "#38bdf8";
    ctxBd.lineWidth = 2;
    ctxBd.strokeRect(4, 4, 504, 120);
    ctxBd.fillStyle = "#ffffff";
    ctxBd.font = "bold 20px 'Ubuntu Mono', monospace";
    ctxBd.fillText("BLACKBOX SENTINEL // RACK-01", 16, 36);
    ctxBd.fillStyle = "#8a91a4";
    ctxBd.font = "14px 'Ubuntu Mono', monospace";
    ctxBd.fillText("PN: AEDN-SENTINEL-PI4-2026", 16, 68);
    ctxBd.fillText("SN: 88402-991A-L2BR-SEC", 16, 96);
    // Draw Barcode
    ctxBd.fillStyle = "#ffffff";
    for (let bx = 340; bx < 490; bx += 4) {
        if (Math.random() > 0.3) ctxBd.fillRect(bx, 20, 2.5, 88);
    }
    const badgeTex = new THREE.CanvasTexture(cvsBadge);

    return { petgTex, piTex, relayTex, batTex, badgeTex };
}

const textures = createHighResTextures();

// PBR Materials Palette
const materials = {
    caseMat: new THREE.MeshStandardMaterial({
        color: 0x161922,
        map: textures.petgTex,
        roughness: 0.65,
        metalness: 0.15
    }),
    caseMatXray: new THREE.MeshPhysicalMaterial({
        color: 0x243048,
        roughness: 0.1,
        metalness: 0.1,
        transparent: true,
        opacity: 0.25,
        transmission: 0.75,
        ior: 1.4
    }),
    caseChamferAccent: new THREE.MeshStandardMaterial({
        color: 0xe95420,
        roughness: 0.35,
        metalness: 0.4
    }),
    screenGlass: new THREE.MeshPhysicalMaterial({
        color: 0x05070a,
        roughness: 0.04,
        metalness: 0.1,
        clearcoat: 1.0,
        clearcoatRoughness: 0.04,
        reflectivity: 0.95
    }),
    pcbPi4: new THREE.MeshStandardMaterial({
        color: 0x184c24,
        map: textures.piTex,
        roughness: 0.35,
        metalness: 0.25
    }),
    pcbDark: new THREE.MeshStandardMaterial({
        color: 0x12141a,
        roughness: 0.5,
        metalness: 0.4
    }),
    relayMat: new THREE.MeshStandardMaterial({
        color: 0x0e52a8,
        map: textures.relayTex,
        roughness: 0.35,
        metalness: 0.2
    }),
    pcbRed: new THREE.MeshStandardMaterial({
        color: 0x8a1c1c,
        roughness: 0.35,
        metalness: 0.3
    }),
    aluminumBlack: new THREE.MeshStandardMaterial({
        color: 0x1c2028,
        roughness: 0.25,
        metalness: 0.9
    }),
    metalSilver: new THREE.MeshStandardMaterial({
        color: 0xdde2ea,
        roughness: 0.18,
        metalness: 0.96
    }),
    metalSteelScrew: new THREE.MeshStandardMaterial({
        color: 0x8892a0,
        roughness: 0.22,
        metalness: 0.92
    }),
    brassGold: new THREE.MeshStandardMaterial({
        color: 0xd4af37,
        roughness: 0.22,
        metalness: 0.88
    }),
    copperWire: new THREE.MeshStandardMaterial({
        color: 0xca7838,
        roughness: 0.25,
        metalness: 0.92
    }),
    batteryMat: new THREE.MeshStandardMaterial({
        color: 0x008080,
        map: textures.batTex,
        roughness: 0.28,
        metalness: 0.5
    }),
    badgeMat: new THREE.MeshStandardMaterial({
        map: textures.badgeTex,
        roughness: 0.3,
        metalness: 0.8
    }),
    smdComponent: new THREE.MeshStandardMaterial({
        color: 0x1b1e26,
        roughness: 0.3,
        metalness: 0.7
    }),
    smdCap: new THREE.MeshStandardMaterial({
        color: 0x966842,
        roughness: 0.3,
        metalness: 0.4
    }),
    ribbonMat: new THREE.MeshStandardMaterial({
        color: 0xf5f6f8,
        roughness: 0.4,
        metalness: 0.1
    }),
    ledGreenActive: new THREE.MeshBasicMaterial({ color: 0x38b44a }),
    ledRedActive: new THREE.MeshBasicMaterial({ color: 0xdf382c }),
    ledBlueActive: new THREE.MeshBasicMaterial({ color: 0x00a3e0 }),
    wireRed: new THREE.MeshStandardMaterial({ color: 0xdf382c, roughness: 0.45 }),
    wireBlack: new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.45 }),
    wireOrange: new THREE.MeshStandardMaterial({ color: 0xe95420, roughness: 0.45 }),
    wirePurple: new THREE.MeshStandardMaterial({ color: 0x9b59b6, roughness: 0.45 }),
    wireBlue: new THREE.MeshStandardMaterial({ color: 0x00a3e0, roughness: 0.45 })
};

// ── Build Full 3D Parametric Appliance Assembly ────────────────────────────
function buildParametricAppliance() {
    const root = new THREE.Group();
    scene.add(root);

    // ══════════════════════════════════════════════════════════════════════════
    // ── Tier 0 (Top): Enclosure Top Lid + Screen + M3 Hex Fasteners
    // ══════════════════════════════════════════════════════════════════════════
    const topLidGroup = new THREE.Group();
    topLidGroup.name = "topLid";

    // Main Lid with Chamfered Corners (140 x 100 x 10 mm)
    const lidGeo = new THREE.BoxGeometry(140, 10, 100);
    const lidMesh = new THREE.Mesh(lidGeo, materials.caseMat);
    lidMesh.castShadow = true;
    lidMesh.receiveShadow = true;
    topLidGroup.add(lidMesh);

    // Subtle Orange Cyber Display Frame Accent
    const frameGeo = new THREE.BoxGeometry(126, 1.2, 82);
    const frameMesh = new THREE.Mesh(frameGeo, materials.caseChamferAccent);
    frameMesh.position.y = 5.1;
    topLidGroup.add(frameMesh);

    // 4x Stainless Steel M3 Socket Hex Screws in 4 corners
    [-62, 62].forEach(x => {
        [-42, 42].forEach(z => {
            const screwHead = new THREE.Mesh(new THREE.CylinderGeometry(3.2, 3.2, 2.2, 16), materials.metalSteelScrew);
            screwHead.position.set(x, 5.2, z);
            topLidGroup.add(screwHead);
            const socket = new THREE.Mesh(new THREE.CylinderGeometry(1.6, 1.6, 1.0, 6), materials.pcbDark);
            socket.position.set(x, 6.0, z);
            topLidGroup.add(socket);
        });
    });

    // 5.0" Screen (120 x 76 mm)
    const screenGroup = new THREE.Group();
    screenGroup.name = "screen";

    const screenBezel = new THREE.Mesh(new THREE.BoxGeometry(124, 2.2, 80), materials.pcbDark);
    screenBezel.position.y = 5.2;
    screenGroup.add(screenBezel);

    const screenMesh = new THREE.Mesh(new THREE.BoxGeometry(120, 2.4, 76), materials.screenGlass);
    screenMesh.position.y = 5.4;
    screenGroup.add(screenMesh);

    // High-DPI Animated Ubuntu Yaru Dashboard
    createAnimatedScreenCanvas();
    const uiMat = new THREE.MeshBasicMaterial({ map: screenTexture });
    const uiPlane = new THREE.Mesh(new THREE.PlaneGeometry(116, 72), uiMat);
    uiPlane.rotation.x = -Math.PI / 2;
    uiPlane.position.y = 6.7;
    screenGroup.add(uiPlane);

    topLidGroup.add(screenGroup);
    parts.topLid = topLidGroup;
    parts.screen = screenGroup;
    originalY.topLid = 26;
    topLidGroup.position.y = originalY.topLid;
    root.add(topLidGroup);

    // ══════════════════════════════════════════════════════════════════════════
    // ── Tier 0 (Middle): Solid 4-Sided Chassis Body with Honeycomb Vents
    // ══════════════════════════════════════════════════════════════════════════
    chassisWallsGroup = new THREE.Group();
    chassisWallsGroup.name = "chassisWalls";

    // Front Wall with Laser-Engraved Serial Badge
    const frontWall = new THREE.Mesh(new THREE.BoxGeometry(140, 36, 4), materials.caseMat);
    frontWall.position.set(0, 3, 48);
    frontWall.castShadow = true;
    chassisWallsGroup.add(frontWall);

    // Laser-Engraved Serial Plate Badge
    const badge = new THREE.Mesh(new THREE.PlaneGeometry(48, 12), materials.badgeMat);
    badge.position.set(20, 6, 50.3);
    chassisWallsGroup.add(badge);

    // Front LED Light-Pipes (Arm = Green, Anomaly = Red, Mesh = Blue)
    const ledArm = new THREE.Mesh(new THREE.CylinderGeometry(2, 2, 5, 12), materials.ledGreenActive);
    ledArm.rotation.x = Math.PI / 2;
    ledArm.position.set(-50, 6, 50.5);
    chassisWallsGroup.add(ledArm);

    const ledAlert = new THREE.Mesh(new THREE.CylinderGeometry(2, 2, 5, 12), materials.ledRedActive);
    ledAlert.rotation.x = Math.PI / 2;
    ledAlert.position.set(-38, 6, 50.5);
    chassisWallsGroup.add(ledAlert);

    const ledMesh = new THREE.Mesh(new THREE.CylinderGeometry(2, 2, 5, 12), materials.ledBlueActive);
    ledMesh.rotation.x = Math.PI / 2;
    ledMesh.position.set(-26, 6, 50.5);
    chassisWallsGroup.add(ledMesh);

    // Back Wall
    const backWall = new THREE.Mesh(new THREE.BoxGeometry(140, 36, 4), materials.caseMat);
    backWall.position.set(0, 3, -48);
    backWall.castShadow = true;
    chassisWallsGroup.add(backWall);

    // Left Wall with 12 Honeycomb Ventilation Hex Cutouts
    const leftWall = new THREE.Mesh(new THREE.BoxGeometry(4, 36, 96), materials.caseMat);
    leftWall.position.set(-68, 3, 0);
    leftWall.castShadow = true;
    chassisWallsGroup.add(leftWall);

    for (let r = -2; r <= 2; r++) {
        for (let c = -2; c <= 2; c++) {
            const hexVent = new THREE.Mesh(new THREE.CylinderGeometry(3.0, 3.0, 5, 6), materials.pcbDark);
            hexVent.rotation.z = Math.PI / 2;
            hexVent.position.set(-68, 3 + (r * 6), c * 8 + (r % 2 === 0 ? 0 : 4));
            chassisWallsGroup.add(hexVent);
        }
    }

    // Right Wall (with Dual RJ45 Port Cutouts)
    const rightWall = new THREE.Mesh(new THREE.BoxGeometry(4, 36, 96), materials.caseMat);
    rightWall.position.set(68, 3, 0);
    rightWall.castShadow = true;
    chassisWallsGroup.add(rightWall);

    parts.chassisWalls = chassisWallsGroup;
    originalY.chassisWalls = 0;
    chassisWallsGroup.position.y = originalY.chassisWalls;
    root.add(chassisWallsGroup);

    // ══════════════════════════════════════════════════════════════════════════
    // ── Tier 1: Anti-Tamper Copper Mesh + Microswitches
    // ══════════════════════════════════════════════════════════════════════════
    const tamperGroup = new THREE.Group();
    tamperGroup.name = "tamper";

    // Continuous Fine Copper Trace Mesh
    const meshGeo = new THREE.PlaneGeometry(130, 90, 28, 20);
    const meshMesh = new THREE.Mesh(meshGeo, new THREE.MeshStandardMaterial({
        color: 0xd47a38,
        wireframe: true,
        roughness: 0.28,
        metalness: 0.9
    }));
    meshMesh.rotation.x = -Math.PI / 2;
    tamperGroup.add(meshMesh);

    // 4x Omron Tactile Microswitches
    [-58, 58].forEach(x => {
        [-38, 38].forEach(z => {
            const swBase = new THREE.Mesh(new THREE.BoxGeometry(6, 4, 6), materials.pcbDark);
            swBase.position.set(x, 2, z);
            tamperGroup.add(swBase);
            const lever = new THREE.Mesh(new THREE.BoxGeometry(4, 1.2, 7), materials.metalSilver);
            lever.position.set(x, 4.2, z);
            lever.rotation.x = 0.2;
            tamperGroup.add(lever);
        });
    });

    parts.tamper = tamperGroup;
    originalY.tamper = 18;
    tamperGroup.position.y = originalY.tamper;
    root.add(tamperGroup);

    // ══════════════════════════════════════════════════════════════════════════
    // ── Tier 2: Raspberry Pi 4 + Heatsink with Active Fan + ESP32-S3
    // ══════════════════════════════════════════════════════════════════════════
    const pi4Group = new THREE.Group();
    pi4Group.name = "pi4";

    // Pi 4 Multi-layer PCB (85 x 56 x 1.8 mm)
    const pcbGeo = new THREE.BoxGeometry(85, 1.8, 56);
    const pcbMesh = new THREE.Mesh(pcbGeo, materials.pcbPi4);
    pcbMesh.position.set(-16, 0, 0);
    pcbMesh.castShadow = true;
    pcbMesh.receiveShadow = true;
    pi4Group.add(pcbMesh);

    // 4x M2.5 Gold-Plated Mounting Holes with Solder Rings
    [[-54, -24], [-54, 24], [22, -24], [22, 24]].forEach(([hx, hz]) => {
        const ring = new THREE.Mesh(new THREE.CylinderGeometry(2.5, 2.5, 1.9, 16), materials.brassGold);
        ring.position.set(hx, 0, hz);
        pi4Group.add(ring);
    });

    // Broadcom BCM2711 SoC with Laser Etching
    const socGeo = new THREE.BoxGeometry(15, 2.2, 15);
    const socMesh = new THREE.Mesh(socGeo, materials.metalSilver);
    socMesh.position.set(-20, 1.6, 2);
    pi4Group.add(socMesh);

    // LPDDR4 RAM Chip (Silver-Black IC)
    const ramMesh = new THREE.Mesh(new THREE.BoxGeometry(12, 1.6, 10), materials.smdComponent);
    ramMesh.position.set(-20, 1.4, -14);
    pi4Group.add(ramMesh);

    // Broadcom BCM54213 Gigabit PHY & VLI VL805 USB Controller ICs
    const phyMesh = new THREE.Mesh(new THREE.BoxGeometry(8, 1.2, 8), materials.smdComponent);
    phyMesh.position.set(4, 1.2, 16);
    pi4Group.add(phyMesh);

    const vl805Mesh = new THREE.Mesh(new THREE.BoxGeometry(9, 1.2, 9), materials.smdComponent);
    vl805Mesh.position.set(4, 1.2, -8);
    pi4Group.add(vl805Mesh);

    // Grid of Realistic 0402 SMD Ceramic Capacitors & Resistors around SoC
    for (let c = 0; c < 24; c++) {
        const smd = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.8, 0.8), c % 2 === 0 ? materials.smdCap : materials.smdComponent);
        smd.position.set(-32 + Math.random() * 26, 1.2, -10 + Math.random() * 22);
        pi4Group.add(smd);
    }

    // MicroSD Card Slot (Bottom side) + SanDisk Red/Gold MicroSD Card
    const sdSlot = new THREE.Mesh(new THREE.BoxGeometry(14, 1.6, 12), materials.metalSilver);
    sdSlot.position.set(-54, -1.2, 0);
    pi4Group.add(sdSlot);

    const sdCard = new THREE.Mesh(new THREE.BoxGeometry(11, 0.8, 8), materials.pcbRed);
    sdCard.position.set(-59, -1.2, 0);
    pi4Group.add(sdCard);

    // Dual Micro-HDMI 4K Ports & USB-C Power Port
    [-12, -22].forEach(z => {
        const mhdmi = new THREE.Mesh(new THREE.BoxGeometry(7, 3.5, 6), materials.metalSilver);
        mhdmi.position.set(-16, 2.2, z - 12);
        pi4Group.add(mhdmi);
    });

    const usbcPort = new THREE.Mesh(new THREE.BoxGeometry(9, 4, 7), materials.metalSilver);
    usbcPort.position.set(-42, 2.4, -26);
    pi4Group.add(usbcPort);

    // DSI Display Ribbon Cable (Connecting Pi to Screen)
    const dsiRibbon = new THREE.Mesh(new THREE.BoxGeometry(14, 0.4, 28), materials.ribbonMat);
    dsiRibbon.position.set(-48, 4.5, 8);
    pi4Group.add(dsiRibbon);

    // Native Gigabit RJ45 Shielded Connector with 8 Gold Spring Pins
    const rj45Pi = new THREE.Mesh(new THREE.BoxGeometry(21, 14, 16), materials.metalSilver);
    rj45Pi.position.set(20, 7.5, 18);
    rj45Pi.castShadow = true;
    pi4Group.add(rj45Pi);

    // RJ45 Internal Cavity & Gold Pins
    const rj45Hole = new THREE.Mesh(new THREE.BoxGeometry(2, 10, 12), materials.pcbDark);
    rj45Hole.position.set(30.6, 7.5, 18);
    pi4Group.add(rj45Hole);

    for (let pin = -4; pin <= 4; pin += 1.2) {
        const gPin = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.2, 5, 6), materials.brassGold);
        gPin.rotation.z = Math.PI / 2;
        gPin.position.set(28, 5, 18 + pin);
        pi4Group.add(gPin);
    }

    // Green & Amber Activity LEDs on RJ45
    rj45Led1 = new THREE.Mesh(new THREE.BoxGeometry(2, 2, 2), materials.ledGreenActive);
    rj45Led1.position.set(30.6, 12, 14);
    pi4Group.add(rj45Led1);

    rj45Led2 = new THREE.Mesh(new THREE.BoxGeometry(2, 2, 2), materials.ledRedActive);
    rj45Led2.position.set(30.6, 12, 22);
    pi4Group.add(rj45Led2);

    // Dual Stacked USB 3.0 & USB 2.0 Jacks (Blue & Black)
    const usb3Jack = new THREE.Mesh(new THREE.BoxGeometry(18, 15, 14), materials.metalSilver);
    usb3Jack.position.set(19, 8, -2);
    pi4Group.add(usb3Jack);
    const usb3Blue = new THREE.Mesh(new THREE.BoxGeometry(2, 12, 12), new THREE.MeshStandardMaterial({ color: 0x0066cc }));
    usb3Blue.position.set(28.2, 8, -2);
    pi4Group.add(usb3Blue);

    const usb2Jack = new THREE.Mesh(new THREE.BoxGeometry(18, 15, 14), materials.metalSilver);
    usb2Jack.position.set(19, 8, -18);
    pi4Group.add(usb2Jack);

    // 40-Pin Gold GPIO Header
    const gpioBase = new THREE.Mesh(new THREE.BoxGeometry(50, 4.5, 5), materials.pcbDark);
    gpioBase.position.set(-24, 3, -24);
    pi4Group.add(gpioBase);
    for (let p = -22; p <= 22; p += 2.4) {
        const pin1 = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.4, 6, 6), materials.brassGold);
        pin1.position.set(-24 + p, 6, -25.2);
        pi4Group.add(pin1);
        const pin2 = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.4, 6, 6), materials.brassGold);
        pin2.position.set(-24 + p, 6, -22.8);
        pi4Group.add(pin2);
    }

    // Aluminum Armor Heatsink + Active 7-Blade Spinning Fan
    const heatsinkGroup = new THREE.Group();
    heatsinkGroup.name = "heatsink";
    const hsBase = new THREE.Mesh(new THREE.BoxGeometry(56, 4, 44), materials.aluminumBlack);
    hsBase.position.set(-22, 3.5, 0);
    hsBase.castShadow = true;
    heatsinkGroup.add(hsBase);

    for (let f = -18; f <= 18; f += 3.6) {
        const fin = new THREE.Mesh(new THREE.BoxGeometry(54, 7, 1.6), materials.aluminumBlack);
        fin.position.set(-22, 7.5, f);
        heatsinkGroup.add(fin);
    }

    // Active Fan Housing & Blades
    const fanHousing = new THREE.Mesh(new THREE.BoxGeometry(30, 8, 30), materials.pcbDark);
    fanHousing.position.set(-22, 10, 0);
    heatsinkGroup.add(fanHousing);

    fanBladesMesh = new THREE.Group();
    const fanHub = new THREE.Mesh(new THREE.CylinderGeometry(4.5, 4.5, 4, 16), materials.aluminumBlack);
    fanBladesMesh.add(fanHub);

    for (let b = 0; b < 7; b++) {
        const bladeGeo = new THREE.BoxGeometry(10, 0.8, 2.5);
        const blade = new THREE.Mesh(bladeGeo, materials.pcbDark);
        blade.position.x = 7.5;
        blade.rotation.y = 0.35;
        const bladeArm = new THREE.Group();
        bladeArm.rotation.y = (b / 7) * Math.PI * 2;
        bladeArm.add(blade);
        fanBladesMesh.add(bladeArm);
    }
    fanBladesMesh.position.set(-22, 10.5, 0);
    heatsinkGroup.add(fanBladesMesh);

    pi4Group.add(heatsinkGroup);
    parts.heatsink = heatsinkGroup;

    // ESP32-S3 Co-Processor (Mounted beside Pi 4)
    const espGroup = new THREE.Group();
    espGroup.name = "esp32";
    const espPcb = new THREE.Mesh(new THREE.BoxGeometry(48, 1.8, 26), materials.pcbDark);
    espPcb.position.set(40, 0, -20);
    espPcb.castShadow = true;
    espGroup.add(espPcb);

    // ESP32 Metal RF Can (Silver with laser text)
    const espCan = new THREE.Mesh(new THREE.BoxGeometry(18, 3.2, 16), materials.metalSilver);
    espCan.position.set(42, 2.4, -20);
    espGroup.add(espCan);

    // ESP32 Meander PCB Antenna (Gold)
    const antTrace = new THREE.Mesh(new THREE.BoxGeometry(6, 0.2, 14), materials.brassGold);
    antTrace.position.set(60, 1.0, -20);
    espGroup.add(antTrace);

    // Tactile EN & BOOT Buttons
    [-4, 4].forEach(z => {
        const btn = new THREE.Mesh(new THREE.BoxGeometry(3, 2, 3), materials.metalSilver);
        btn.position.set(24, 1.8, -20 + z);
        espGroup.add(btn);
    });

    pi4Group.add(espGroup);
    parts.esp32 = espGroup;

    parts.pi4 = pi4Group;
    originalY.pi4 = 6;
    pi4Group.position.y = originalY.pi4;
    root.add(pi4Group);

    // ══════════════════════════════════════════════════════════════════════════
    // ── Tier 3: 5V Songle Relay + SIM800L Cellular Modem + Cap + RF Coax
    // ══════════════════════════════════════════════════════════════════════════
    const relayGroup = new THREE.Group();
    relayGroup.name = "relay";

    // Blue Songle Relay Box with Stamped Label Texture
    const relayCube = new THREE.Mesh(new THREE.BoxGeometry(28, 16, 20), materials.relayMat);
    relayCube.position.set(-32, 0, 20);
    relayCube.castShadow = true;
    relayGroup.add(relayCube);

    // Optocoupler PC817 IC & SMD Transistor Driver
    const optoIc = new THREE.Mesh(new THREE.BoxGeometry(6, 3, 5), materials.smdComponent);
    optoIc.position.set(-15, 2, 24);
    relayGroup.add(optoIc);

    // Active Relay Status LED Indicator
    relayLedMesh = new THREE.Mesh(new THREE.CylinderGeometry(1.5, 1.5, 2, 12), materials.ledGreenActive);
    relayLedMesh.position.set(-20, 8.5, 20);
    relayGroup.add(relayLedMesh);

    // 3-Pin Green Screw Terminal Block
    const termBlock = new THREE.Mesh(new THREE.BoxGeometry(9, 13, 18), new THREE.MeshStandardMaterial({ color: 0x1f7a34, roughness: 0.4 }));
    termBlock.position.set(-49, -1.5, 20);
    relayGroup.add(termBlock);

    [-5, 0, 5].forEach(z => {
        const scr = new THREE.Mesh(new THREE.CylinderGeometry(1.4, 1.4, 2, 12), materials.brassGold);
        scr.position.set(-49, 5.2, 20 + z);
        relayGroup.add(scr);
    });

    parts.relay = relayGroup;
    originalY.relay = -6;
    relayGroup.position.y = originalY.relay;
    root.add(relayGroup);

    // SIM800L Cellular Modem Group
    const simGroup = new THREE.Group();
    simGroup.name = "sim800";

    const simPcb = new THREE.Mesh(new THREE.BoxGeometry(26, 1.8, 24), materials.pcbRed);
    simPcb.position.set(24, 0, 20);
    simPcb.castShadow = true;
    simGroup.add(simPcb);

    // MicroSIM Gold Socket Holder
    const simSlot = new THREE.Mesh(new THREE.BoxGeometry(16, 2.0, 14), materials.metalSilver);
    simSlot.position.set(24, 1.8, 20);
    simGroup.add(simSlot);

    // 1000µF Low-ESR Filter Capacitor (Silver can with cross vent notch)
    const capCan = new THREE.Mesh(new THREE.CylinderGeometry(4.2, 4.2, 14, 20), materials.metalSilver);
    capCan.position.set(8, 6.5, 20);
    capCan.castShadow = true;
    simGroup.add(capCan);
    const capNotch = new THREE.Mesh(new THREE.CylinderGeometry(4.25, 4.25, 2.5, 20), materials.pcbDark);
    capNotch.position.set(8, 12, 20);
    simGroup.add(capNotch);

    // IPEX U.FL Gold Mini Connector on SIM800L
    const ipex = new THREE.Mesh(new THREE.CylinderGeometry(1.5, 1.5, 1.5, 12), materials.brassGold);
    ipex.position.set(34, 1.6, 28);
    simGroup.add(ipex);

    // Panel-Mount Brass SMA Antenna Connector
    const smaHex = new THREE.Mesh(new THREE.CylinderGeometry(3.5, 3.5, 12, 6), materials.brassGold);
    smaHex.rotation.z = Math.PI / 2;
    smaHex.position.set(64, 0, 25);
    simGroup.add(smaHex);

    // Flexible Shielded RF Coaxial Pigtail Cable (IPEX to SMA)
    const coaxCurve = new THREE.CatmullRomCurve3([
        new THREE.Vector3(34, 1.6, 28),
        new THREE.Vector3(48, 6, 29),
        new THREE.Vector3(60, 0, 25)
    ]);
    const coaxTube = new THREE.Mesh(new THREE.TubeGeometry(coaxCurve, 16, 0.7, 8, false), materials.aluminumBlack);
    simGroup.add(coaxTube);

    // Rubber Duck GSM Stub Antenna
    const antPole = new THREE.Mesh(new THREE.CylinderGeometry(2.4, 3.2, 36, 16), materials.pcbDark);
    antPole.position.set(74, 14, 25);
    antPole.rotation.z = -0.15;
    antPole.castShadow = true;
    simGroup.add(antPole);

    parts.sim800 = simGroup;
    originalY.sim800 = -6;
    simGroup.position.y = originalY.sim800;
    root.add(simGroup);

    // ══════════════════════════════════════════════════════════════════════════
    // ── Tier 4 (Bottom): Dual 18650 Battery Pack + PMIC + 4-LED Fuel Gauge
    // ══════════════════════════════════════════════════════════════════════════
    const batteryGroup = new THREE.Group();
    batteryGroup.name = "battery";

    // Molded Injection Battery Tray (Black ABS)
    const batTray = new THREE.Mesh(new THREE.BoxGeometry(78, 12, 46), materials.pcbDark);
    batTray.position.set(0, -4, 0);
    batteryGroup.add(batTray);

    // 2x 18650 Cylindrical Cells with authentic Panasonic text
    [-14, 14].forEach(z => {
        const cell = new THREE.Mesh(new THREE.CylinderGeometry(9.2, 9.2, 65, 24), materials.batteryMat);
        cell.rotation.z = Math.PI / 2;
        cell.position.set(0, 0, z);
        cell.castShadow = true;
        batteryGroup.add(cell);

        const cap = new THREE.Mesh(new THREE.CylinderGeometry(3.2, 3.2, 2.5, 16), materials.brassGold);
        cap.rotation.z = Math.PI / 2;
        cap.position.set(33.5, 0, z);
        batteryGroup.add(cap);

        const spring = new THREE.Mesh(new THREE.CylinderGeometry(4.5, 4.5, 3, 12), materials.metalSilver);
        spring.rotation.z = Math.PI / 2;
        spring.position.set(-33.5, 0, z);
        batteryGroup.add(spring);
    });

    // PMIC 4-LED Battery Fuel Gauge (Blue SMD LEDs)
    pmicLeds = [];
    [-6, -2, 2, 6].forEach(x => {
        const fuelLed = new THREE.Mesh(new THREE.BoxGeometry(1.2, 1.2, 1.2), materials.ledBlueActive);
        fuelLed.position.set(x, 2.5, 21);
        batteryGroup.add(fuelLed);
        pmicLeds.push(fuelLed);
    });

    parts.battery = batteryGroup;
    originalY.battery = -18;
    batteryGroup.position.y = originalY.battery;
    root.add(batteryGroup);

    // Bottom Base Plate (140 x 100 x 12 mm)
    const bottomGroup = new THREE.Group();
    bottomGroup.name = "bottomCase";

    const baseMesh = new THREE.Mesh(new THREE.BoxGeometry(140, 10, 100), materials.caseMat);
    baseMesh.position.y = -14;
    baseMesh.receiveShadow = true;
    baseMesh.castShadow = true;
    bottomGroup.add(baseMesh);

    // 4x Silicone Anti-Vibration Feet
    [-62, 62].forEach(x => {
        [-42, 42].forEach(z => {
            const foot = new THREE.Mesh(new THREE.CylinderGeometry(5.5, 6.0, 3.5, 20), materials.pcbDark);
            foot.position.set(x, -20.5, z);
            bottomGroup.add(foot);
        });
    });

    parts.bottomCase = bottomGroup;
    originalY.bottomCase = -24;
    bottomGroup.position.y = originalY.bottomCase;
    root.add(bottomGroup);

    // 4x Brass M2.5 Standoffs Linking Tiers
    buildStandoffs(root);

    // Realistic 3D Curved Flexible Wiring Harnesses + Zip-Ties
    build3DWiringHarnesses(root);

    // Live Dimension Bounding Box Overlay
    buildDimensionOverlay(root);
}

// ── Realistic 3D Wiring Harnesses & Zip-Ties ────────────────────────────────
function build3DWiringHarnesses(root) {
    wiresGroup = new THREE.Group();

    // 1. Red 5V Power Wire (PMIC Battery to Pi 4 GPIO Pin 2)
    createCurvedWire(
        new THREE.Vector3(20, -16, 10),
        new THREE.Vector3(-10, -5, 5),
        new THREE.Vector3(-24, 6, -23),
        materials.wireRed,
        1.1
    );

    // 2. Black Ground Wire (PMIC Battery to Pi 4 GPIO Pin 6)
    createCurvedWire(
        new THREE.Vector3(20, -16, -10),
        new THREE.Vector3(-8, -4, -10),
        new THREE.Vector3(-20, 6, -23),
        materials.wireBlack,
        1.1
    );

    // 3. Orange Relay Control Wire (ESP32 GPIO 18 to Relay Module IN)
    createCurvedWire(
        new THREE.Vector3(40, 2, -12),
        new THREE.Vector3(10, 8, 10),
        new THREE.Vector3(-28, 2, 20),
        materials.wireOrange,
        0.9
    );

    // 4. Purple Tamper Interrupt Wire (Tamper Switch to ESP32 GPIO 27)
    createCurvedWire(
        new THREE.Vector3(55, 18, 35),
        new THREE.Vector3(50, 10, 0),
        new THREE.Vector3(42, 2, -26),
        materials.wirePurple,
        0.8
    );

    // 5. Blue UART Serial Data Wire (Pi 4 TX to ESP32 RX)
    createCurvedWire(
        new THREE.Vector3(-14, 6, -23),
        new THREE.Vector3(15, 10, -28),
        new THREE.Vector3(36, 2, -26),
        materials.wireBlue,
        0.85
    );

    // White Cable Zip-Ties
    [-6, 12].forEach(y => {
        const zipTie = new THREE.Mesh(new THREE.TorusGeometry(3.5, 0.6, 8, 16), new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.3 }));
        zipTie.rotation.x = Math.PI / 2;
        zipTie.position.set(-6, y, 0);
        wiresGroup.add(zipTie);
    });

    root.add(wiresGroup);
}

function createCurvedWire(p1, p2, p3, mat, thickness = 1.0) {
    const curve = new THREE.CatmullRomCurve3([p1, p2, p3]);
    const tubeGeo = new THREE.TubeGeometry(curve, 24, thickness, 8, false);
    const wireMesh = new THREE.Mesh(tubeGeo, mat);
    wireMesh.castShadow = true;
    wiresGroup.add(wireMesh);
}

// ── Standoffs ──────────────────────────────────────────────────────────────
function buildStandoffs(root) {
    const standoffGeo = new THREE.CylinderGeometry(1.8, 1.8, 52, 12);
    [-63, 63].forEach(x => {
        [-43, 43].forEach(z => {
            const m = new THREE.Mesh(standoffGeo, materials.brassGold);
            m.position.set(x, 1, z);
            m.castShadow = true;
            root.add(m);
        });
    });
}

// ── Dimension Bounding Box Overlay ─────────────────────────────────────────
function buildDimensionOverlay(root) {
    dimensionGroup = new THREE.Group();
    const boxGeo = new THREE.BoxGeometry(144, 58, 104);
    const wireGeo = new THREE.WireframeGeometry(boxGeo);
    const wireMat = new THREE.LineBasicMaterial({ color: 0xe95420, transparent: true, opacity: 0.45 });
    const wireBox = new THREE.LineSegments(wireGeo, wireMat);
    wireBox.position.y = 1;
    dimensionGroup.add(wireBox);
    root.add(dimensionGroup);
}

// ── Screen Animated UI Texture Generator ───────────────────────────────────
function createAnimatedScreenCanvas() {
    screenCanvas = document.createElement("canvas");
    screenCanvas.width = 512;
    screenCanvas.height = 307;
    screenCtx = screenCanvas.getContext("2d");
    screenTexture = new THREE.CanvasTexture(screenCanvas);
    renderScreenUI();
}

function renderScreenUI() {
    if (!screenCtx) return;
    const ctx = screenCtx;
    animatedTime += 0.06;

    // Spin Fan Blades smoothly
    if (fanBladesMesh) {
        fanBladesMesh.rotation.y += 0.25;
    }

    // Yaru Dark Background
    ctx.fillStyle = isTamperTriggered ? "#2b0a0a" : "#181b24";
    ctx.fillRect(0, 0, 512, 307);

    // Top GNOME Bar
    ctx.fillStyle = "#0e1017";
    ctx.fillRect(0, 0, 512, 28);
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 13px Ubuntu, sans-serif";
    ctx.fillText("Activities", 14, 18);
    ctx.fillText("Ubuntu 24.04 • Sentinel OS", 175, 18);
    ctx.fillText("15:35", 460, 18);

    // Status Banner
    if (isTamperTriggered) {
        ctx.fillStyle = "rgba(223, 56, 44, 0.25)";
        ctx.fillRect(16, 38, 480, 48);
        ctx.strokeStyle = "#df382c";
        ctx.lineWidth = 2.0;
        ctx.strokeRect(16, 38, 480, 48);

        ctx.fillStyle = "#df382c";
        ctx.font = "bold 15px Ubuntu, sans-serif";
        ctx.fillText("🚨 HARDWARE TAMPER BREACH • ZEROIZED", 30, 64);
        ctx.fillStyle = "#ffaaaa";
        ctx.font = "11px 'Ubuntu Mono', monospace";
        ctx.fillText("Keys wiped from tmpfs | Relay: ISOLATED | Cellular Alert DISPATCHED", 30, 78);
    } else if (isRelayIsolated) {
        ctx.fillStyle = "rgba(233, 84, 32, 0.25)";
        ctx.fillRect(16, 38, 480, 48);
        ctx.strokeStyle = "#e95420";
        ctx.lineWidth = 2.0;
        ctx.strokeRect(16, 38, 480, 48);

        ctx.fillStyle = "#e95420";
        ctx.font = "bold 15px Ubuntu, sans-serif";
        ctx.fillText("⚡ PHYSICAL AIR-GAP ISOLATION ACTIVE", 30, 64);
        ctx.fillStyle = "#ffccaa";
        ctx.font = "11px 'Ubuntu Mono', monospace";
        ctx.fillText("Bridge br0 severed | Relay: OPEN | Enter PIN to restore", 30, 78);
    } else {
        ctx.fillStyle = "rgba(56, 180, 74, 0.18)";
        ctx.fillRect(16, 38, 480, 48);
        ctx.strokeStyle = "#38b44a";
        ctx.lineWidth = 1.5;
        ctx.strokeRect(16, 38, 480, 48);

        ctx.fillStyle = "#38b44a";
        ctx.font = "bold 15px Ubuntu, sans-serif";
        ctx.fillText("● SYSTEM ARMED & DEFENDING", 30, 64);
        ctx.fillStyle = "#aaaaaa";
        ctx.font = "11px 'Ubuntu Mono', monospace";
        ctx.fillText("Bridge: br0 (eth0+eth1) | Relay: ENGAGED | Model: IsolationForest", 30, 78);
    }

    // 4 Metrics Cards
    ctx.fillStyle = "#222734";
    ctx.fillRect(16, 94, 110, 58);
    ctx.fillRect(136, 94, 110, 58);
    ctx.fillRect(256, 94, 110, 58);
    ctx.fillRect(376, 94, 120, 58);

    ctx.fillStyle = isRelayIsolated || isTamperTriggered ? "#df382c" : "#38b44a";
    ctx.font = "bold 18px 'Ubuntu Mono', monospace";
    ctx.fillText("3,680", 28, 128);
    ctx.fillText(isRelayIsolated ? "1" : "0", 178, 128);
    ctx.fillText(isRelayIsolated ? "ISOLATED" : "ENGAGED", 262, 128);
    ctx.fillText("41.2°C", 388, 128);

    ctx.fillStyle = "#8a91a4";
    ctx.font = "9px Ubuntu, sans-serif";
    ctx.fillText("PACKETS", 28, 142);
    ctx.fillText("ANOMALIES", 158, 142);
    ctx.fillText("5V RELAY", 276, 142);
    ctx.fillText("CPU TEMP", 392, 142);

    // Live Oscillating ML Threat Spectrum
    ctx.fillStyle = "#10121a";
    ctx.fillRect(16, 160, 480, 130);

    ctx.strokeStyle = isRelayIsolated ? "#df382c" : "#e95420";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    for (let x = 0; x < 480; x += 8) {
        const freq = isRelayIsolated ? 0.12 : 0.05;
        const amp = isRelayIsolated ? 28 : 16;
        const y = 225 + Math.sin((x * freq) + animatedTime) * amp + Math.cos((x * 0.02) - animatedTime) * 6;
        if (x === 0) ctx.moveTo(16 + x, y);
        else ctx.lineTo(16 + x, y);
    }
    ctx.stroke();

    if (screenTexture) screenTexture.needsUpdate = true;
}

// ── Interactive Raycasting (Component Selection) ───────────────────────────
function setupRaycaster() {
    raycaster = new THREE.Raycaster();
    mouse = new THREE.Vector2();

    const canvas = document.getElementById("webgl-canvas");
    canvas.addEventListener("click", (e) => {
        const rect = canvas.getBoundingClientRect();
        mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObjects(scene.children, true);

        if (intersects.length > 0) {
            let obj = intersects[0].object;
            while (obj.parent && obj.parent !== scene && !parts[obj.name]) {
                obj = obj.parent;
            }
            if (obj && parts[obj.name]) {
                selectComponent(obj.name);
            }
        }
    });
}

// ── Select and Inspect Component ───────────────────────────────────────────
function selectComponent(partKey) {
    const data = COMPONENT_DATA[partKey];
    if (!data) return;

    selectedPartName = partKey;

    // Highlight in Assembly Tree
    document.querySelectorAll(".tree-item").forEach(item => {
        if (item.getAttribute("onclick")?.includes(partKey)) {
            item.classList.add("selected");
        } else {
            item.classList.remove("selected");
        }
    });

    // Populate Right Inspector Sheet
    const container = document.getElementById("inspect-content");
    document.getElementById("inspect-title").textContent = data.name.toUpperCase();

    let specsHtml = "";
    data.specs.forEach(s => {
        specsHtml += `<tr><td>${s[0]}</td><td>${s[1]}</td></tr>`;
    });

    container.innerHTML = `
        <div class="inspect-card">
            <span class="inspect-header-badge">${data.tier}</span>
            <div class="inspect-name">${data.name}</div>
            <div class="inspect-desc">${data.role}</div>
            <table class="inspect-table">
                <tr><td>Dimensions</td><td>${data.dims}</td></tr>
                <tr><td>Material / Tech</td><td>${data.material}</td></tr>
                ${specsHtml}
            </table>
        </div>
    `;
}

// ── Exploded View Dynamic Animation ────────────────────────────────────────
function onExplodeSlider(val) {
    targetExplode = parseFloat(val) / 100;
    document.getElementById("explode-percent").textContent = `${Math.round(val)}%`;
}

function animateExplodeTo(val) {
    document.getElementById("explode-slider").value = val;
    onExplodeSlider(val);
}

function updateExplodePositions() {
    explodeFactor += (targetExplode - explodeFactor) * 0.1;

    // Separate tiers vertically with clear clearance
    if (parts.topLid) parts.topLid.position.y = originalY.topLid + (explodeFactor * 135);
    if (parts.chassisWalls) parts.chassisWalls.position.y = originalY.chassisWalls + (explodeFactor * 45);
    if (parts.tamper) parts.tamper.position.y = originalY.tamper + (explodeFactor * 90);
    if (parts.pi4) parts.pi4.position.y = originalY.pi4 + (explodeFactor * 35);
    if (parts.relay) parts.relay.position.y = originalY.relay - (explodeFactor * 25);
    if (parts.sim800) parts.sim800.position.y = originalY.sim800 - (explodeFactor * 25);
    if (parts.battery) parts.battery.position.y = originalY.battery - (explodeFactor * 85);
    if (parts.bottomCase) parts.bottomCase.position.y = originalY.bottomCase - (explodeFactor * 135);

    // Smoothly fade chassis walls when exploded so internal chips are 100% visible
    if (chassisWallsGroup) {
        chassisWallsGroup.visible = explodeFactor < 0.85;
    }

    if (wiresGroup) {
        wiresGroup.visible = explodeFactor < 0.65;
    }
}

// ── Live 3D Interactive Defense Triggers ────────────────────────────────────
function trigger3DRelay() {
    isRelayIsolated = !isRelayIsolated;
    if (relayLedMesh) {
        relayLedMesh.material = isRelayIsolated ? materials.ledRedActive : materials.ledGreenActive;
    }
    if (rj45Led1) {
        rj45Led1.material = isRelayIsolated ? materials.ledRedActive : materials.ledGreenActive;
    }
}

function trigger3DTamper() {
    isTamperTriggered = !isTamperTriggered;
    isRelayIsolated = isTamperTriggered;
    if (relayLedMesh) {
        relayLedMesh.material = isTamperTriggered ? materials.ledRedActive : materials.ledGreenActive;
    }
}

// ── Render Modes ───────────────────────────────────────────────────────────
function setRenderMode(mode) {
    currentRenderMode = mode;
    document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
    document.getElementById(`btn-mode-${mode}`)?.classList.add("active");

    const isWire = mode === "wire";
    const isXray = mode === "xray";
    const isClay = mode === "clay";

    scene.traverse((obj) => {
        if (obj.isMesh) {
            if (obj.material) {
                obj.material.wireframe = isWire;
                if (isClay) {
                    obj.material.color.setHex(0xd0d4dc);
                    obj.material.metalness = 0.0;
                    obj.material.roughness = 0.9;
                }
            }
        }
    });

    if (parts.topLid && parts.bottomCase && parts.chassisWalls) {
        const lidMesh = parts.topLid.children[0];
        const baseMesh = parts.bottomCase.children[0];
        const wallMeshes = parts.chassisWalls.children;
        if (lidMesh) lidMesh.material = isXray ? materials.caseMatXray : materials.caseMat;
        if (baseMesh) baseMesh.material = isXray ? materials.caseMatXray : materials.caseMat;
        for (let i = 0; i < wallMeshes.length; i++) {
            if (wallMeshes[i].isMesh) {
                wallMeshes[i].material = isXray ? materials.caseMatXray : materials.caseMat;
            }
        }
    }
}

// ── Presets & Views ────────────────────────────────────────────────────────
function setPresetView(preset) {
    document.querySelectorAll(".preset-btn").forEach(b => b.classList.remove("active"));
    event.target.classList.add("active");

    controls.autoRotate = false;
    document.getElementById("btn-rotate").textContent = "🔄 Auto-Rotate: OFF";

    if (preset === "iso") camera.position.set(215, 165, 245);
    else if (preset === "top") camera.position.set(0, 320, 0);
    else if (preset === "front") camera.position.set(0, 20, 280);
    else if (preset === "side") camera.position.set(280, 20, 0);

    controls.target.set(0, 0, 0);
}

function toggleAutoRotate() {
    autoRotate = !autoRotate;
    controls.autoRotate = autoRotate;
    document.getElementById("btn-rotate").textContent = `🔄 Auto-Rotate: ${autoRotate ? "ON" : "OFF"}`;
}

function resetCamera() {
    setPresetView("iso");
}

function toggleDimensions(show) {
    if (dimensionGroup) dimensionGroup.visible = show;
}

function toggleGrid(show) {
    if (gridHelper) gridHelper.visible = show;
}

function exportCADReport() {
    const bom = {
        project: "BlackBox Sentinel Edge Defense Appliance",
        hardware_profile: "Raspberry Pi 4 Model B (4GB/8GB) + ESP32-S3",
        dimensions_mm: "140 × 100 × 55",
        total_layers: 4,
        bom_components: Object.values(COMPONENT_DATA)
    };
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(bom, null, 2));
    const dl = document.createElement('a');
    dl.setAttribute("href", dataStr);
    dl.setAttribute("download", "sentinel_hardware_bom_cad.json");
    document.body.appendChild(dl);
    dl.click();
    dl.remove();
}

// ── Main Render Loop ───────────────────────────────────────────────────────
function animate() {
    requestAnimationFrame(animate);
    updateExplodePositions();
    renderScreenUI();
    controls.update();
    renderer.render(scene, camera);
}
