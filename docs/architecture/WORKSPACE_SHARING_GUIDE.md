# 🤝 BlackBox Sentinel — Team Workspace Sharing & Collaboration Guide

This guide explains how you and your team members can work in the **exact same workspace configuration** using **Antigravity** and **Visual Studio Code**, share live sessions, run 1-click debuggers, and keep code synchronized with GitHub.

---

## 🚀 Quick Start for Team Members

### Step 1: Clone the Repository
```bash
git clone https://github.com/Blackbox-Sentinel/Blackbox_Sentinel.git
cd Blackbox_Sentinel
```

### Step 2: 1-Click Environment Setup
* **On Windows**: Double-click `setup_workspace.bat` (or run `python sync_workspace.py` in your terminal).
* **On Linux / macOS**: Run `chmod +x setup_workspace.sh && ./setup_workspace.sh`.

This automatically sets up Python dependencies, checks port availability (`8080` and `5000`), and verifies all project modules.

---

## 💻 Opening in Antigravity & Visual Studio Code

### Method 1: Open the Multi-Root Workspace (Recommended)
Open **Antigravity** or **VS Code**, go to **File** &rarr; **Open Workspace from File...**, and select:
📁 `blackbox-sentinel.code-workspace`

#### What this provides:
* Automatically mounts and organizes all 4 project modules:
  * 🔌 `M1 • Hardware & HAL`
  * 🖥️ `M2 • Systems & Bridge`
  * 🧠 `M3 • ML & Immutable Ledger`
  * 🌐 `M4 • Ubuntu GUI & 3D CAD Studio`
* Pre-configures Python autocomplete, linting, formatting, and file nesting.

---

## ⚡ 1-Click Run & Debug Presets (F5)

Press `F5` or switch to the **Run & Debug** panel (Ctrl+Shift+D) in Antigravity / VS Code to launch preconfigured targets:

| Preset Name | Description | Port / Command |
| :--- | :--- | :--- |
| 🚀 **Run Sentinel Pipeline (Sim Mode + GUI)** | Boots the unified hardware abstraction, bridge simulation, and launches the UI | `python sentinel_pipeline.py --mode sim --gui` |
| 🌐 **Start Ubuntu Web Kiosk & 3D CAD Studio** | Starts the web server hosting the desktop OS and 3D CAD viewer | `http://localhost:8080` |
| ⚡ **Start Hardware Bridge Simulator Server** | Starts the virtual GPIO, relay air-gap, and tamper REST backend | `http://localhost:5000` |
| 🧠 **Train Isolation Forest & Ledger (M3)** | Trains the scikit-learn anomaly model and initializes the ledger | `python m3-ml-ledger/src/train.py` |
| 🔬 **Run Pytest Suite** | Runs all automated unit and integration tests | `pytest -v` |

---

## 👥 Real-Time Collaboration (Live Share Feature)

You and your friends can code simultaneously on the same running instance in real time using **Live Share**:

1. Install the **Live Share** extension in Antigravity / VS Code (pre-configured in `.vscode/extensions.json`).
2. Click **Live Share** in the bottom status bar and select **Start Collaboration Session**.
3. Copy the invite link and send it to your teammates.
4. When they join:
   * They can edit code and see your cursor in real time.
   * Ports `8080` (Web UI/CAD) and `5000` (API) are **automatically tunneled**, allowing them to test the live web app in their own local browser directly from your machine!

---

## 🔄 Keeping Workspace in Sync

To run a diagnostic health check on your environment at any time:
```bash
python sync_workspace.py
```
