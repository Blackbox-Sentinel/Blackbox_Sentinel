#!/usr/bin/env python3
"""
BlackBox Sentinel — Team Workspace Sync & Diagnostics Tool
Cross-platform environment setup and health check for collaborators using Antigravity and VS Code.
"""

import os
import sys
import subprocess
import socket
import json
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).parent.resolve()

def print_header(title):
    print("\n" + "=" * 65)
    print(f"  [BLACKBOX SENTINEL] {title}")
    print("=" * 65)

def check_python():
    print("\n[1/5] Checking Python Version...")
    v = sys.version_info
    print(f"   Python: {v.major}.{v.minor}.{v.micro} ({sys.executable})")
    if v.major < 3 or (v.major == 3 and v.minor < 9):
        print("   [!] WARNING: Python 3.9+ is recommended.")
        return False
    print("   [OK] Python version OK")
    return True

def check_and_install_dependencies():
    print("\n[2/5] Checking Required Dependencies...")
    req_file = ROOT_DIR / "requirements.txt"
    if not req_file.exists():
        print("   [!] requirements.txt not found!")
        return False

    required = [
        ("flask", "flask"),
        ("flask_cors", "flask-cors"),
        ("requests", "requests"),
        ("numpy", "numpy"),
        ("sklearn", "scikit-learn"),
        ("joblib", "joblib"),
        ("cryptography", "cryptography")
    ]
    missing = []
    for mod, pkg in required:
        try:
            __import__(mod)
            print(f"   [+] {pkg:15} : Installed")
        except ImportError:
            print(f"   [-] {pkg:15} : Missing")
            missing.append(pkg)

    if missing:
        print(f"\n   [*] Installing missing packages from requirements.txt...")
        cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
        res = subprocess.run(cmd)
        if res.returncode != 0:
            print("   [!] Error installing dependencies.")
            return False
        print("   [OK] All dependencies installed successfully.")
    else:
        print("   [OK] All core dependencies satisfied.")
    return True

def check_ports():
    print("\n[3/5] Checking Port Availability...")
    ports = {
        8080: "Ubuntu Kiosk OS & 3D CAD Studio Web Server",
        5000: "Hardware Bridge REST API Server"
    }
    for port, desc in ports.items():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            result = s.connect_ex(("127.0.0.1", port))
            if result == 0:
                print(f"   [*] Port {port} ({desc}) is currently ACTIVE / IN USE.")
            else:
                print(f"   [+] Port {port} ({desc}) is AVAILABLE.")
    return True

def check_workspace_files():
    print("\n[4/5] Validating Workspace Structure...")
    critical_paths = [
        "sentinel_pipeline.py",
        "blackbox-sentinel.code-workspace",
        ".vscode/launch.json",
        ".vscode/settings.json",
        "common/hal/drivers_sim.py",
        "m3-ml-ledger/src/predict.py",
        "m4-gui-venture/server.py",
        "m4-gui-venture/web/cad_viewer.html"
    ]
    all_ok = True
    for p in critical_paths:
        full = ROOT_DIR / p
        if full.exists():
            print(f"   [+] Found: {p}")
        else:
            print(f"   [-] Missing: {p}")
            all_ok = False
    return all_ok

def show_launch_menu():
    print_header("WORKSPACE READY FOR COLLABORATION")
    print("""
Quick Start Commands:
  1. Full Pipeline (Virtual Hardware + Web GUI):
     python sentinel_pipeline.py --mode sim --gui

  2. Launch Web Kiosk & 3D CAD Studio only:
     python m4-gui-venture/server.py
     -> Open http://localhost:8080

  3. Start Hardware Bridge Simulator Server:
     python m4-gui-venture/hw_simulator_server.py
     -> Open http://localhost:5000

  4. Run Unit Tests:
     pytest -v

In Antigravity / Visual Studio Code:
  - Open 'blackbox-sentinel.code-workspace' to load all project tiers.
  - Press F5 or go to 'Run & Debug' tab to start with 1-click presets.
  - Use VS Code Live Share to invite teammates for live pair-programming!
    """)

def main():
    print_header("WORKSPACE DIAGNOSTICS & SYNC")
    check_python()
    check_and_install_dependencies()
    check_ports()
    check_workspace_files()
    show_launch_menu()

if __name__ == "__main__":
    main()
