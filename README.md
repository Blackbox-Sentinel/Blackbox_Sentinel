# 🛡️ BlackBox Sentinel

> **Real-time network anomaly detection & tamper-proof logging system**

[![GitHub Issues](https://img.shields.io/github/issues/YOUR_USERNAME/blackbox-sentinel)](https://github.com/YOUR_USERNAME/blackbox-sentinel/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/YOUR_USERNAME/blackbox-sentinel)](https://github.com/YOUR_USERNAME/blackbox-sentinel/pulls)

---

## 📋 Project Overview

BlackBox Sentinel is a 4-module embedded + software system that captures network traffic, detects anomalies using machine learning, and presents findings through an interactive GUI — all backed by a tamper-proof hash-chained log.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     BlackBox Sentinel                           │
├──────────────┬──────────────┬───────────────┬───────────────────┤
│  M1-Hardware │  M2-Systems  │  M3-ML-Ledger │   M4-GUI-Venture  │
│  ESP32 +     │  Scapy +     │  Isolation    │   Tkinter 800x480 │
│  SIM800L     │  Bridge      │  Forest +     │   Dashboard +     │
│              │              │  Hash Chain   │   Pitch Deck      │
└──────────────┴──────────────┴───────────────┴───────────────────┘
```

## 📁 Repository Structure

```text
blackbox-sentinel/
├── m1-hardware/          # ESP32 code, SIM800L scripts, circuit diagrams
│   ├── src/              # Arduino/PlatformIO source files
│   ├── schematics/       # Circuit diagrams & Wokwi links
│   └── README.md         # M1 module documentation
│
├── m2-systems/           # Scapy packet capture, network bridge, systemd services
│   ├── src/              # Python scripts for packet capture & bridging
│   ├── config/           # systemd service files & configuration
│   └── README.md         # M2 module documentation
│
├── m3-ml-ledger/         # Isolation Forest model, hash-chained log
│   ├── src/              # ML training & inference scripts
│   ├── models/           # Trained model artifacts
│   ├── data/             # Sample pcap files & datasets
│   └── README.md         # M3 module documentation
│
├── m4-gui-venture/       # Tkinter screen interface, pitch deck, docs
│   ├── src/              # GUI application code
│   ├── assets/           # Icons, images, fonts
│   ├── pitch/            # Pitch deck & presentation materials
│   └── README.md         # M4 module documentation
│
├── docs/                 # Cross-module documentation & integration guides
├── .github/              # Issue templates & PR templates
└── README.md             # This file
```

## 👥 Team & Branches

| Member | Role | Branch | Module |
|--------|------|--------|--------|
| M1 | Hardware Engineer | `m1-dev` | `m1-hardware/` |
| M2 | Systems Engineer | `m2-dev` | `m2-systems/` |
| M3 | ML Engineer | `m3-dev` | `m3-ml-ledger/` |
| M4 | GUI/Venture Lead | `m4-dev` | `m4-gui-venture/` |

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Arduino IDE / PlatformIO (for M1)
- Git
- VS Code with Live Share extension

### Clone & Setup

```bash
git clone https://github.com/YOUR_USERNAME/blackbox-sentinel.git
cd blackbox-sentinel

# Switch to your development branch
git checkout m1-dev   # or m2-dev, m3-dev, m4-dev
```

### Branch Workflow

1. **Always work on your own branch** (`m1-dev`, `m2-dev`, `m3-dev`, `m4-dev`)
2. **Push regularly** so the team can see your progress
3. **Create a Pull Request** when your feature is ready for review
4. **Merge to `main`** only after at least 1 teammate approves

```bash
# Daily workflow
git add .
git commit -m "M3: trained isolation forest on campus pcap data"
git push origin m3-dev
```

## 🔗 Integration Points

| From → To | Interface | Description |
|-----------|-----------|-------------|
| M1 → M2 | Serial/USB | ESP32 sends raw packet bytes to bridge |
| M2 → M3 | `.pcap` files | Captured packets fed to ML pipeline |
| M3 → M4 | JSON API / SQLite | Anomaly scores & log entries for dashboard |
| M1 → M4 | Status LED codes | Hardware health indicators on GUI |

## 📡 Real-Time Collaboration

### Discord Channels
- `#general` — Team-wide announcements
- `#m1-hardware` — ESP32, SIM800L, circuit discussions
- `#m2-systems` — Packet capture, bridge, systemd
- `#m3-ml` — Model training, anomaly detection
- `#m4-gui` — Dashboard UI, pitch deck

### Live Coding
- **VS Code Live Share** for pair programming sessions
- **Wokwi** simulation links in `m1-hardware/schematics/`

---

> **⚡ Remember:** Push often, write clear commit messages, and move your Kanban cards!
