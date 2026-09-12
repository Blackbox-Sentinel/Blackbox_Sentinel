#!/usr/bin/env bash
set -e

echo "================================================================="
echo "  [BlackBox Sentinel] Multi-Developer Workspace Setup Tool (Linux/macOS)"
echo "================================================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 is not installed or not in PATH!"
    exit 1
fi

echo "[1/3] Creating virtual environment if needed..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

echo "[2/3] Activating virtual environment & installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[3/3] Running workspace sync diagnostics..."
python3 sync_workspace.py

echo ""
echo "================================================================="
echo " Setup Complete!"
echo " Open 'blackbox-sentinel.code-workspace' in VS Code or Antigravity."
echo "================================================================="
