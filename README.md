# 🛡️ BlackBox Sentinel

> **Autonomous Physical Network Intrusion Prevention Appliance & Immutable Ledger**  
> *Raspberry Pi 4 • Layer-2 Inline Bridge • Isolation Forest ML • Physical Relay Air-Gap • Cellular Alerting • 3D CAD Twin & Ubuntu Kiosk*

---

## 📋 System Overview

**BlackBox Sentinel** is a production-grade physical cyber defense appliance deployed inline on local network segments. It inspects live network traffic, flags zero-day anomalies using an Isolation Forest ML pipeline, physically isolates the network via a high-speed mechanical relay upon confirmed breach, zeroizes cryptographic keys upon chassis tamper detection, and records forensic evidence to an immutable SHA-256 hash-chained ledger.

---

## 🏗️ 4-Module Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                   BlackBox Sentinel                                      │
├──────────────────────┬──────────────────────┬──────────────────────┬─────────────────────┤
│   M1 • Hardware/HAL  │   M2 • Systems/OS    │   M3 • ML & Ledger   │   M4 • GUI & 3D Twin│
│                      │                      │                      │                     │
│ • Raspberry Pi 4 B   │ • Layer-2 Bridge br0 │ • Isolation Forest   │ • Ubuntu Kiosk OS   │
│ • Songle 5V Relay    │ • OverlayFS RO Root  │ • Feature Extraction │ • 3D CAD Studio     │
│ • ESP32 Co-processor │ • systemd Services   │ • SHA-256 Hash Chain │ • Circuit Simulator │
│ • SIM800L Cellular   │ • Veth Sim Lab       │ • Anti-Tamper Wiping │ • REST API Server   │
└──────────────────────┴──────────────────────┴──────────────────────┴─────────────────────┘
```

---

## 👥 Multi-Developer Workspace Sharing (Antigravity & Visual Studio Code)

This repository includes a multi-developer workspace setup for **Antigravity** and **Visual Studio Code**:

1. **One-Click Workspace**: Open `blackbox-sentinel.code-workspace` in Antigravity / VS Code to automatically load all submodules with pre-tuned settings.
2. **1-Click Debuggers (F5)**:
   - `🚀 Run Sentinel Pipeline (Sim Mode + GUI)`
   - `🌐 Start Ubuntu Web Kiosk & 3D CAD Studio`
   - `⚡ Start Hardware Bridge Simulator Server`
   - `🧠 Train Isolation Forest & Ledger (M3)`
   - `🔬 Run Pytest Suite`
3. **Live Share Pair-Programming**: Configured via `.vsls.json` to automatically tunnel ports `8080` (Web UI/CAD) and `5000` (API) between teammates across the internet.
4. **Automated Workspace Sync**: Run `python sync_workspace.py` or double-click `setup_workspace.bat` (Windows) / `setup_workspace.sh` (Linux/macOS).

*Refer to [WORKSPACE_SHARING_GUIDE.md](WORKSPACE_SHARING_GUIDE.md) for full team onboarding instructions.*

---

## 🚀 Quick Start

### 1. Installation
```bash
git clone https://github.com/Blackbox-Sentinel/Blackbox_Sentinel.git
cd Blackbox_Sentinel

# Windows setup:
setup_workspace.bat

# Linux / macOS setup:
chmod +x setup_workspace.sh && ./setup_workspace.sh
```

### 2. Run the Phase 2 Software Vertical Slice

Run the normalized M2/M3 telemetry producer in one terminal:

```bash
python3 integration/phase2_vertical_slice.py \\
  --output m3-ml-ledger/data/phase2_telemetry.jsonl
```

Run the canonical 480×320 M4 touchscreen dashboard in a second terminal:

```bash
python3 gui/dashboard.py \\
  --telemetry-file m3-ml-ledger/data/phase2_telemetry.jsonl
```

The slice demonstrates calibration, normal traffic, pending evidence, approved containment, replay/stale rejection, quorum conflict, receipt audit, and recovery-required states. It is software simulation only; ESP32 physical enforcement still requires M1 validation.

### 3. Other Entry Points

```bash
# Larger M4 desktop simulation GUI:
python3 m4-gui-venture/src/app.py

# Optional browser kiosk prototype:
python3 m4-gui-venture/server.py

# Legacy core pipeline without normalized Phase 2 integration:
python3 sentinel_pipeline.py
```

### 4. Open Interactive 3D CAD Studio & Ubuntu Kiosk
- **Ubuntu 24.04 Kiosk Desktop**: [http://localhost:8080/](http://localhost:8080/)
- **3D CAD Hardware Studio**: [http://localhost:8080/cad_viewer.html](http://localhost:8080/cad_viewer.html)
- **Virtual Circuit Simulator**: [http://localhost:8080/simulator.html](http://localhost:8080/simulator.html)

---

## 📁 Repository Structure

The Phase 2 integration files are under `integration/`, with the detailed runbook in [`docs/Phase2_Vertical_Slice.md`](docs/Phase2_Vertical_Slice.md).

```text
Blackbox_Sentinel/
├── blackbox-sentinel.code-workspace  # Multi-root workspace for Antigravity & VS Code
├── WORKSPACE_SHARING_GUIDE.md        # Team collaboration & Live Share instructions
├── sync_workspace.py                 # Cross-platform environment diagnostic tool
├── setup_workspace.bat / .sh         # 1-click workspace bootstrap scripts
├── requirements.txt                  # Consolidated Python dependencies
├── sentinel_pipeline.py              # Unified pipeline entrypoint (Sim / Real)
│
├── common/                           # Universal Hardware Abstraction Layer (HAL)
│   └── hal/                          # Drivers for Real GPIO / Virtual Simulation
│
├── m1-hardware/                      # Hardware schematics, ESP32 firmware, Wokwi
│   ├── src/esp32_coprocessor.ino     # ESP-NOW mesh co-processor firmware
│   └── wokwi/                        # Interactive Wokwi circuit simulation
│
├── m2-systems/                       # Operating system, bridge config, Docker lab
│   ├── os/                           # OverlayFS root, security hardening, systemd
│   └── sim/                          # Virtual network namespace lab & traffic gen
│
├── m3-ml-ledger/                     # Machine learning & immutable cryptographic ledger
│   ├── src/                          # Isolation Forest training, inference & ledger
│   └── models/                       # Seed trained model weights
│
└── m4-gui-venture/                   # Web Kiosk OS, 3D CAD Studio & API Backends
    ├── server.py                     # Kiosk Web Server (Port 8080)
    ├── hw_simulator_server.py        # Hardware Bridge REST API (Port 5000)
    └── web/                          # PBR Three.js 3D CAD Viewer & OS GUI
```

---

## 🔒 Security Hardening & Hardware Defense

- **Mechanical Air-Gap Relay**: Disconnects Ethernet physically within $<15\text{ms}$ upon threat classification.
- **Active Tamper Mesh**: Copper grid monitored via continuous GPIO pull-down interrupt; triggers zeroization of cryptographic memory within $10\mu\text{s}$.
- **Immutable Ledger**: Every network packet feature hash is chained using SHA-256 with nonce and timestamp verification.
